import os
import subprocess
import shutil
import tarfile
import datetime
from pathlib import Path
from typing import Optional


def run_cmd(cmd, timeout=60):
    try:
        result = subprocess.run(
            cmd,
            capture_output=True,
            text=True,
            timeout=timeout,
            check=False
        )
        return result
    except subprocess.TimeoutExpired:
        return type('obj', (object,), {'returncode': 124, 'stdout': '', 'stderr': 'Timeout'})()
    except Exception as e:
        return type('obj', (object,), {'returncode': 1, 'stdout': '', 'stderr': str(e)})()


def is_external_etcd() -> bool:
    k3s_dir = Path('/var/lib/rancher/k3s/server/db')
    if k3s_dir.exists() and (k3s_dir / 'etcd').exists():
        return False
    
    result = run_cmd(['kubectl', 'get', 'pods', '-A', '-o', 'jsonpath={.items[*].spec.containers[*].image}'])
    if 'etcd' in result.stdout.lower() or 'rke2' in result.stdout.lower():
        return True
    
    return False


def is_embedded_etcd() -> bool:
    k3s_dir = Path('/var/lib/rancher/k3s/server/db')
    return k3s_dir.exists() and (k3s_dir / 'etcd').exists()


def create_etcd_snapshot(snapshot_name: Optional[str] = None, backup_dir: Optional[Path] = None) -> Optional[str]:
    if not is_embedded_etcd():
        print("ℹ️  Not using embedded etcd (external DB or not k3s)")
        return None
    
    k3s_binary = shutil.which('k3s')
    if not k3s_binary:
        k3s_binary = shutil.which('k3s-server')
    
    if not k3s_binary:
        print("⚠️  k3s binary not found")
        return None
    
    if snapshot_name is None:
        snapshot_name = f"etcd-snapshot-{datetime.datetime.now().strftime('%Y%m%d_%H%M%S')}"
    
    if backup_dir is None:
        backup_dir = Path('backups')
    backup_dir.mkdir(exist_ok=True)
    
    snapshot_path = backup_dir / snapshot_name
    
    print(f"📸 Creating etcd snapshot: {snapshot_name}")
    
    result = run_cmd([
        k3s_binary, 'etcd-snapshot', 'save',
        '--etcd-snapshot-name', snapshot_name,
        '--etcd-snapshot-dir', str(backup_dir)
    ], timeout=300)
    
    if result.returncode == 0:
        created = backup_dir / f"{snapshot_name}"
        if created.exists():
            print(f"✅ etcd snapshot saved: {created}")
            return str(created)
        
        for f in backup_dir.glob('*snapshot*'):
            if snapshot_name.replace('etcd-snapshot-', '') in f.name:
                print(f"✅ etcd snapshot saved: {f}")
                return str(f)
        
        return str(snapshot_path)
    else:
        print(f"⚠️  etcd snapshot failed: {result.stderr}")
        
        result2 = run_cmd([
            'curl', '-sfL', 'https://get.k3s.io', '-o', '/tmp/k3s-install.sh'
        ])
        
        if result2.returncode == 0:
            print("Trying k3s-etcd-snapshot command...")
            result3 = run_cmd([
                'bash', '/tmp/k3s-install.sh', '--etcd-snapshot', snapshot_name
            ], timeout=300)
            
            if result3.returncode == 0:
                etcd_path = Path(f'/var/lib/rancher/k3s/server/db/snapshots/{snapshot_name}')
                if etcd_path.exists():
                    shutil.copy(etcd_path, backup_dir / snapshot_name)
                    print(f"✅ etcd snapshot saved: {backup_dir / snapshot_name}")
                    return str(backup_dir / snapshot_name)
        
        return None


def restore_etcd_snapshot(snapshot_path: str) -> bool:
    if not is_embedded_etcd():
        print("⚠️  External etcd restore not supported")
        return False
    
    k3s_binary = shutil.which('k3s')
    if not k3s_binary:
        k3s_binary = shutil.which('k3s-server')
    
    if not k3s_binary:
        print("⚠️  k3s binary not found")
        return False
    
    print(f"⚠️  Restoring etcd from snapshot: {snapshot_path}")
    print("⚠️  WARNING: This will restart k3s and interrupt workloads!")
    
    result = run_cmd([
        k3s_binary, 'etcd-snapshot', 'restore',
        '--etcd-snapshot-name', Path(snapshot_path).name,
        '--etcd-snapshot-dir', str(Path(snapshot_path).parent)
    ], timeout=300)
    
    if result.returncode == 0:
        print("✅ etcd snapshot restored. k3s will restart.")
        return True
    else:
        print(f"❌ Restore failed: {result.stderr}")
        return False


def list_etcd_snapshots() -> list:
    snapshot_dir = Path('/var/lib/rancher/k3s/server/db/snapshots')
    local_dir = Path('backups')
    
    snapshots = []
    
    if snapshot_dir.exists():
        for f in snapshot_dir.glob('*'):
            snapshots.append({
                'name': f.name,
                'path': str(f),
                'size': f.stat().st_size,
                'modified': datetime.datetime.fromtimestamp(f.stat().st_mtime).isoformat(),
                'location': 'server',
            })
    
    for f in local_dir.glob('etcd-*'):
        snapshots.append({
            'name': f.name,
            'path': str(f),
            'size': f.stat().st_size,
            'modified': datetime.datetime.fromtimestamp(f.stat().st_mtime).isoformat(),
            'location': 'local',
        })
    
    return sorted(snapshots, key=lambda x: x['modified'], reverse=True)


def get_etcd_health() -> dict:
    if is_external_etcd():
        return {'status': 'external', 'healthy': True, 'message': 'Using external etcd'}
    
    if not is_embedded_etcd():
        return {'status': 'unknown', 'healthy': False, 'message': 'Cannot determine etcd status'}
    
    k3s_binary = shutil.which('k3s')
    if not k3s_binary:
        k3s_binary = shutil.which('k3s-server')
    
    if not k3s_binary:
        return {'status': 'unknown', 'healthy': False, 'message': 'k3s binary not found'}
    
    result = run_cmd([k3s_binary, 'etcd-snapshot', 'list'], timeout=30)
    
    if result.returncode == 0:
        return {'status': 'ok', 'healthy': True, 'message': 'etcd snapshots available'}
    else:
        return {'status': 'unknown', 'healthy': False, 'message': 'Cannot list etcd snapshots'}