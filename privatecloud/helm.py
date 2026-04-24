import subprocess
import os
from rich.console import Console

console = Console()

def run_helm(cmd: list, kubeconfig: str = "kubeconfig.yaml", check: bool = True):
    env = os.environ.copy()
    env["KUBECONFIG"] = os.path.abspath(kubeconfig)
    
    full_cmd = ["helm"] + cmd
    console.print(f"[cyan]$ {' '.join(full_cmd)}[/cyan]")
    
    return subprocess.run(full_cmd, check=check, env=env)

def add_repo(name: str, url: str):
    run_helm(["repo", "add", name, url])
    run_helm(["repo", "update"])

def install_chart(release_name: str, chart: str, namespace: str = "default", create_namespace: bool = True, values: dict = None):
    cmd = ["upgrade", "--install", release_name, chart, "--namespace", namespace]
    if create_namespace:
        cmd.append("--create-namespace")
        
    if values:
        for k, v in values.items():
            cmd.extend(["--set", f"{k}={v}"])
            
    run_helm(cmd)
