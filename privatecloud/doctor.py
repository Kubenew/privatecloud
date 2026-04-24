import shutil
import subprocess
import os
import json
from dataclasses import dataclass
from typing import List, Dict, Optional
from rich.console import Console
from rich.table import Table

console = Console()

REQUIRED_TOOLS = ["ssh", "scp", "curl", "helm", "terraform"]
OPTIONAL_TOOLS = ["kubectl"]


@dataclass
class DoctorResult:
    ok: bool
    missing_required: List[str]
    missing_optional: List[str]
    checks: List[Dict[str, str]]


def check_tools() -> DoctorResult:
    missing_required = [t for t in REQUIRED_TOOLS if shutil.which(t) is None]
    missing_optional = [t for t in OPTIONAL_TOOLS if shutil.which(t) is None]

    return DoctorResult(
        ok=(len(missing_required) == 0),
        missing_required=missing_required,
        missing_optional=missing_optional,
        checks=[],
    )


def run_cmd(cmd, timeout=30):
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


def run_diagnostics() -> List[Dict[str, str]]:
    checks = []
    
    checks.append(check_kubectl_connection())
    checks.append(check_helm_version())
    checks.append(check_terraform_version())
    checks.append(check_k3s_status())
    checks.append(check_backup_directory())
    checks.append(check_cert_expiry())
    checks.append(check_longhorn_health())
    
    return checks


def check_kubectl_connection() -> Dict[str, str]:
    result = run_cmd(["kubectl", "cluster-info"], timeout=10)
    if result.returncode == 0:
        return {"name": "kubectl connection", "status": "ok", "message": "Connected to cluster"}
    return {"name": "kubectl connection", "status": "error", "message": "Cannot connect to cluster"}


def check_helm_version() -> Dict[str, str]:
    result = run_cmd(["helm", "version", "--short"], timeout=10)
    if result.returncode == 0:
        version = result.stdout.strip()
        return {"name": "Helm version", "status": "ok", "message": version}
    return {"name": "Helm version", "status": "error", "message": "Helm not found or not configured"}


def check_terraform_version() -> Dict[str, str]:
    result = run_cmd(["terraform", "version"], timeout=10)
    if result.returncode == 0:
        version = result.stdout.strip().split("\n")[0]
        return {"name": "Terraform version", "status": "ok", "message": version}
    return {"name": "Terraform version", "status": "error", "message": "Terraform not found"}


def check_k3s_status() -> Dict[str, str]:
    result = run_cmd(["kubectl", "get", "nodes", "-o", "json"], timeout=30)
    if result.returncode != 0:
        return {"name": "K3s cluster status", "status": "error", "message": "Cannot get cluster status"}
    
    try:
        data = json.loads(result.stdout)
        nodes = data.get("items", [])
        ready_count = sum(1 for n in nodes if is_node_ready(n))
        total_count = len(nodes)
        
        if ready_count == total_count and total_count > 0:
            return {
                "name": "K3s cluster status",
                "status": "ok",
                "message": f"{ready_count}/{total_count} nodes ready"
            }
        elif ready_count > 0:
            return {
                "name": "K3s cluster status",
                "status": "warning",
                "message": f"{ready_count}/{total_count} nodes ready (some not ready)"
            }
        else:
            return {
                "name": "K3s cluster status",
                "status": "error",
                "message": "No nodes in ready state"
            }
    except json.JSONDecodeError:
        return {"name": "K3s cluster status", "status": "error", "message": "Invalid response from API"}


def is_node_ready(node: dict) -> bool:
    conditions = node.get("status", {}).get("conditions", [])
    for cond in conditions:
        if cond.get("type") == "Ready":
            return cond.get("status") == "True"
    return False


def check_backup_directory() -> Dict[str, str]:
    backup_dir = os.path.join(os.getcwd(), "backups")
    if not os.path.exists(backup_dir):
        try:
            os.makedirs(backup_dir, exist_ok=True)
            return {"name": "Backup directory", "status": "ok", "message": "Created backups directory"}
        except Exception as e:
            return {"name": "Backup directory", "status": "error", "message": f"Cannot create: {e}"}
    
    try:
        test_file = os.path.join(backup_dir, ".write_test")
        with open(test_file, "w") as f:
            f.write("test")
        os.remove(test_file)
        return {"name": "Backup directory", "status": "ok", "message": "Writable"}
    except Exception as e:
        return {"name": "Backup directory", "status": "error", "message": f"Not writable: {e}"}


def check_cert_expiry() -> Dict[str, str]:
    result = run_cmd([
        "kubectl", "get", "certificates", "-A", "-o", "json"
    ], timeout=30)
    
    if result.returncode != 0:
        return {"name": "Certificate expiry", "status": "warning", "message": "Cannot check certificates"}
    
    try:
        data = json.loads(result.stdout)
        certs = data.get("items", [])
        warnings = []
        
        for cert in certs[:10]:
            not_after = cert.get("status", {}).get("notAfter", "")
            if not_after:
                from datetime import datetime
                try:
                    expiry = datetime.fromisoformat(not_after.replace("Z", "+00:00"))
                    days_left = (expiry - datetime.now()).days
                    if days_left < 30:
                        name = cert.get("metadata", {}).get("name", "unknown")
                        warnings.append(f"{name}: {days_left} days")
                except Exception:
                    pass
        
        if warnings:
            return {
                "name": "Certificate expiry",
                "status": "warning",
                "message": f"Expiring soon: {', '.join(warnings[:3])}"
            }
        return {"name": "Certificate expiry", "status": "ok", "message": "No expiring certificates"}
    except Exception:
        return {"name": "Certificate expiry", "status": "warning", "message": "Cannot parse certificate data"}


def check_longhorn_health() -> Dict[str, str]:
    result = run_cmd([
        "kubectl", "get", "volumes.longhorn.io", "-A", "-o", "json"
    ], timeout=30)
    
    if result.returncode != 0:
        return {"name": "Longhorn health", "status": "info", "message": "Longhorn not installed"}
    
    try:
        data = json.loads(result.stdout)
        volumes = data.get("items", [])
        
        degraded = [v for v in volumes if v.get("status", {}).get("state") == "Degraded"]
        
        if volumes:
            if degraded:
                return {
                    "name": "Longhorn health",
                    "status": "error",
                    "message": f"{len(degraded)}/{len(volumes)} volumes degraded"
                }
            return {
                "name": "Longhorn health",
                "status": "ok",
                "message": f"All {len(volumes)} volumes healthy"
            }
        return {"name": "Longhorn health", "status": "ok", "message": "No volumes configured"}
    except Exception:
        return {"name": "Longhorn health", "status": "warning", "message": "Cannot check Longhorn status"}


def display_diagnostics():
    result = check_tools()
    
    table = Table(title="🔍 PrivateCloud Diagnostics")
    table.add_column("Check", style="cyan")
    table.add_column("Status", justify="center")
    table.add_column("Details")
    
    for t in result.missing_required:
        table.add_row(t, "[red]❌ MISSING[/red]", "Required tool")
    for t in result.missing_optional:
        table.add_row(t, "[yellow]⚠️  MISSING[/yellow]", "Optional tool")
    
    for check in run_diagnostics():
        status_map = {
            "ok": "[green]✅ OK[/green]",
            "warning": "[yellow]⚠️  WARNING[/yellow]",
            "error": "[red]❌ ERROR[/red]",
            "info": "[blue]ℹ️  INFO[/blue]",
        }
        status = status_map.get(check["status"], check["status"])
        table.add_row(check["name"], status, check["message"])
    
    console.print(table)


def get_overall_status() -> bool:
    result = check_tools()
    if not result.ok:
        return False
    
    checks = run_diagnostics()
    has_errors = any(c["status"] == "error" for c in checks)
    return not has_errors