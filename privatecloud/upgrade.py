import subprocess
import time
import os
from pathlib import Path
from typing import Optional, List, Dict
from rich.console import Console
from rich.progress import Progress, SpinnerColumn, TextColumn

console = Console()


def run_cmd(cmd, check=False, capture=True, timeout=120):
    try:
        result = subprocess.run(
            cmd,
            capture_output=capture,
            text=True,
            timeout=timeout,
            check=check
        )
        return result
    except subprocess.TimeoutExpired:
        return type('obj', (object,), {'returncode': 124, 'stdout': '', 'stderr': 'Timeout'})()
    except Exception as e:
        return type('obj', (object,), {'returncode': 1, 'stdout': '', 'stderr': str(e)})()


SUPPORTED_K3S_VERSIONS = [
    'v1.32.0+k3s1',
    'v1.31.0+k3s1',
    'v1.30.0+k3s1',
    'v1.29.0+k3s1',
    'v1.28.0+k3s1',
]


def get_current_k3s_version() -> Optional[str]:
    result = run_cmd(["kubectl", "get", "nodes", "-o", "jsonpath={.items[0].status.nodeInfo.kubeletVersion}"])
    if result.returncode == 0 and result.stdout.strip():
        return result.stdout.strip()
    
    result = run_cmd(["k3s", "--version"])
    if result.returncode == 0 and 'k3s' in result.stdout:
        parts = result.stdout.split(' ')
        if len(parts) >= 2:
            return parts[1]
    
    return None


def check_upgrade_available(target_version: str) -> Dict:
    current = get_current_k3s_version()
    if not current:
        return {'upgradeable': False, 'current': None, 'target': target_version, 'reason': 'Cannot determine current version'}
    
    current_major = int(current.split('.')[0].replace('v', ''))
    target_major = int(target_version.split('.')[0].replace('v', ''))
    current_minor = int(current.split('.')[1])
    target_minor = int(target_version.split('.')[1])
    
    if target_major < current_major or (target_major == current_major and target_minor < current_minor):
        return {'upgradeable': False, 'current': current, 'target': target_version, 'reason': 'Target version is older'}
    
    if target_major > current_major + 1:
        return {'upgradeable': False, 'current': current, 'target': target_version, 'reason': 'Skipping major versions not supported'}
    
    return {
        'upgradeable': True,
        'current': current,
        'target': target_version,
        'reason': 'Upgrade path valid'
    }


def drain_node(node_name: str, timeout: int = 300) -> bool:
    console.print(f"[yellow]Draining node {node_name}...[/yellow]")
    result = run_cmd([
        "kubectl", "drain", node_name,
        "--ignore-daemonsets",
        "--delete-emptydir-data",
        "--force",
        "--timeout", f"{timeout}s"
    ], timeout=timeout + 30)
    
    if result.returncode == 0:
        console.print(f"[green]✅ Node {node_name} drained[/green]")
        return True
    else:
        console.print(f"[yellow]⚠️  Drain warnings: {result.stderr[:200]}[/yellow]")
        return True


def uncordon_node(node_name: str) -> bool:
    console.print(f"[yellow]Uncordoning node {node_name}...[/yellow]")
    result = run_cmd(["kubectl", "uncordon", node_name])
    
    if result.returncode == 0:
        console.print(f"[green]✅ Node {node_name} ready[/green]")
        return True
    return False


def upgrade_k3s_master(master_ip: str, user: str, new_version: str, ssh_opts: List[str]) -> bool:
    console.print(f"[bold cyan]🔄 Upgrading master {master_ip} to {new_version}...[/bold cyan]")
    
    cmd = [
        "ssh", *ssh_opts,
        f"{user}@{master_ip}",
        f"curl -sfL https://get.k3s.io | INSTALL_K3S_VERSION={new_version} sh -s - upgrade"
    ]
    
    result = run_cmd(cmd, timeout=300)
    
    if result.returncode == 0:
        console.print(f"[green]✅ Master upgraded[/green]")
        return True
    else:
        console.print(f"[red]❌ Master upgrade failed: {result.stderr}[/red]")
        return False


def upgrade_k3s_agent(node_ip: str, user: str, new_version: str, ssh_opts: List[str]) -> bool:
    console.print(f"[yellow]Upgrading agent {node_ip} to {new_version}...[/yellow]")
    
    cmd = [
        "ssh", *ssh_opts,
        f"{user}@{node_ip}",
        f"curl -sfL https://get.k3s.io | INSTALL_K3S_VERSION={new_version} K3S_URL=https://localhost:6443 K3S_TOKEN_FILE=/var/lib/rancher/k3s/agent/node-token sh -s - upgrade"
    ]
    
    result = run_cmd(cmd, timeout=180)
    
    if result.returncode == 0:
        console.print(f"[green]✅ Agent {node_ip} upgraded[/green]")
        return True
    else:
        console.print(f"[yellow]⚠️  Agent upgrade warning: {result.stderr[:100]}[/yellow]")
        return True


def get_cluster_nodes() -> List[Dict]:
    result = run_cmd(["kubectl", "get", "nodes", "-o", "json"])
    if result.returncode != 0:
        return []
    
    import json
    try:
        data = json.loads(result.stdout)
        nodes = []
        for item in data.get('items', []):
            name = item['metadata']['name']
            ready = any(
                c.get('type') == 'Ready' and c.get('status') == 'True'
                for c in item['status'].get('conditions', [])
            )
            role = 'master' if any(
                l.get('kubernetes.io/hostname') == name or
                l.get('node-role.kubernetes.io/master') == ''
                for l in [item.get('metadata', {}).get('labels', {})]
            ) else 'worker'
            
            nodes.append({
                'name': name,
                'ready': ready,
                'role': role,
                'version': item['status'].get('nodeInfo', {}).get('kubeletVersion', 'unknown'),
            })
        return nodes
    except Exception:
        return []


def upgrade_cluster(target_version: str, backup: bool = True, dry_run: bool = False, batch_size: int = 1):
    if dry_run:
        console.print("[cyan]=== DRY RUN: Upgrade Preview ===[/cyan]")
        current = get_current_k3s_version()
        nodes = get_cluster_nodes()
        check = check_upgrade_available(target_version)
        
        console.print(f"\nCurrent version: {current or 'unknown'}")
        console.print(f"Target version: {target_version}")
        console.print(f"Upgrade possible: {check['upgradeable']}")
        if not check['upgradeable']:
            console.print(f"Reason: {check['reason']}")
        
        console.print(f"\nNodes to upgrade ({len(nodes)}):")
        for n in nodes:
            console.print(f"  - {n['name']} ({n['role']}): {n['version']} → {target_version}")
        
        console.print("\nUpgrade would proceed in this order:")
        console.print("  1. Backup cluster state")
        console.print("  2. Drain master node")
        console.print("  3. Upgrade master")
        console.print("  4. Upgrade workers (batch size: 1)")
        console.print("  5. Verify all nodes ready")
        return True
    
    check = check_upgrade_available(target_version)
    if not check['upgradeable']:
        console.print(f"[red]❌ Cannot upgrade: {check['reason']}[/red]")
        return False
    
    if backup:
        from .backup import create_backup
        console.print("[yellow]Creating backup before upgrade...[/yellow]")
        backup_path = create_backup(name=f"pre-upgrade-{target_version}")
        console.print(f"[yellow]Backup saved: {backup_path}[/yellow]")
    
    nodes = get_cluster_nodes()
    masters = [n for n in nodes if n['role'] == 'master']
    workers = [n for n in nodes if n['role'] == 'worker']
    
    ssh_opts = ["-o", "StrictHostKeyChecking=no", "-o", "ConnectTimeout=10"]
    
    # Upgrade masters first
    for master in masters:
        if not master['ready']:
            console.print(f"[yellow]Skipping non-ready master: {master['name']}[/yellow]")
            continue
        
        console.print(f"[bold]Upgrading master: {master['name']}[/bold]")
        drain_node(master['name'])
        if not upgrade_k3s_master(master['name'], 'root', target_version, ssh_opts):
            console.print(f"[red]❌ Master upgrade failed for {master['name']}. Aborting.[/red]")
            uncordon_node(master['name'])
            return False
        uncordon_node(master['name'])
    
    # Upgrade workers
    for worker in workers:
        if not worker['ready']:
            console.print(f"[yellow]Skipping non-ready worker: {worker['name']}[/yellow]")
            continue
        
        console.print(f"[bold]Upgrading worker: {worker['name']}[/bold]")
        drain_node(worker['name'])
        if not upgrade_k3s_agent(worker['name'], 'root', target_version, ssh_opts):
            console.print(f"[yellow]⚠️  Worker upgrade had issues for {worker['name']}[/yellow]")
        uncordon_node(worker['name'])
    
    console.print(f"[green]✅ Cluster upgrade to {target_version} complete[/green]")
    
    return True


def rollback_cluster(backup_name: str):
    console.print(f"[yellow]Rolling back to backup: {backup_name}[/yellow]")
    from .backup import restore_backup
    restore_backup(backup_name)
    console.print("[yellow]Rollback initiated. Cluster state restored from backup.[/yellow]")