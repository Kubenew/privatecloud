import subprocess
import json
import os
from pathlib import Path
from jinja2 import Environment, FileSystemLoader
from rich.console import Console

from .config import PrivateCloudConfig, NodeConfig
from .utils import save_config

console = Console()

def run_tf(cmd: list, check: bool = True, capture_output: bool = False):
    console.print(f"[cyan]$ {' '.join(cmd)}[/cyan]")
    return subprocess.run(
        cmd,
        check=check,
        capture_output=capture_output,
        text=True
    )

def generate_tf(config: PrivateCloudConfig, run_dir: str = "."):
    if config.provider == "proxmox":
        template_dir = Path(__file__).parent / "templates"
        env = Environment(loader=FileSystemLoader(str(template_dir)))
        template = env.get_template("proxmox.tf.j2")
        
        ssh_key = ""
        if config.ssh_key_path and Path(config.ssh_key_path).exists():
            ssh_key = Path(config.ssh_key_path).read_text().strip()

        tf_code = template.render(config=config, ssh_key=ssh_key)
        
        tf_file = Path(run_dir) / "main.tf"
        tf_file.write_text(tf_code)
        console.print("[green]Generated main.tf for Proxmox provider[/green]")
    else:
        raise ValueError(f"Provider {config.provider} is not supported via Terraform yet.")

def terraform_init(run_dir: str = "."):
    run_tf(["terraform", "init"], check=True)

def terraform_apply(run_dir: str = "."):
    run_tf(["terraform", "apply", "-auto-approve"], check=True)

def terraform_destroy(run_dir: str = "."):
    run_tf(["terraform", "destroy", "-auto-approve"], check=True)

def get_outputs(run_dir: str = ".") -> dict:
    res = run_tf(["terraform", "output", "-json"], check=True, capture_output=True)
    try:
        return json.loads(res.stdout)
    except json.JSONDecodeError:
        return {}

def apply_and_update_config(config: PrivateCloudConfig) -> PrivateCloudConfig:
    generate_tf(config)
    terraform_init()
    terraform_apply()
    
    outputs = get_outputs()
    master_ips = outputs.get("master_ips", {}).get("value", [])
    worker_ips = outputs.get("worker_ips", {}).get("value", [])
    
    new_nodes = []
    for ip in master_ips:
        if ip: # proxmox can sometimes return empty strings initially
            new_nodes.append(NodeConfig(host=ip, user="root")) # Assuming root for templates
            
    for ip in worker_ips:
        if ip:
            new_nodes.append(NodeConfig(host=ip, user="root"))

    if not new_nodes:
        console.print("[yellow]Warning: Terraform returned no IPs. Is the agent running?[/yellow]")
        
    config.nodes = new_nodes
    save_config(config)
    console.print("[green]Updated privatecloud.yaml with new node IPs[/green]")
    
    return config
