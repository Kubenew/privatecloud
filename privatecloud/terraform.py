import subprocess
import json
import os
from pathlib import Path
from jinja2 import Environment, FileSystemLoader
from rich.console import Console

from .config import PrivateCloudConfig, NodeConfig
from .utils import save_config

console = Console()


def run_tf(cmd: list, cwd: str = ".", check: bool = True, capture_output: bool = False):
    """Run a Terraform CLI command in the given working directory."""
    console.print(f"[cyan]$ {' '.join(cmd)}[/cyan]")
    try:
        return subprocess.run(
            cmd,
            cwd=cwd,
            check=check,
            capture_output=capture_output,
            text=True,
        )
    except subprocess.CalledProcessError as e:
        console.print(f"[red]Terraform command failed (exit {e.returncode})[/red]")
        if e.stderr:
            console.print(f"[red]{e.stderr}[/red]")
        raise
    except FileNotFoundError:
        console.print("[red]'terraform' binary not found. Run: privatecloud doctor[/red]")
        raise RuntimeError("terraform is not installed or not in PATH")


def _render_template(template_name: str, run_dir: str, provider_label: str, **kwargs) -> Path:
    """Render a Jinja2 Terraform template and write main.tf to run_dir."""
    template_dir = Path(__file__).parent / "templates"
    env = Environment(loader=FileSystemLoader(str(template_dir)))
    template = env.get_template(template_name)

    tf_code = template.render(**kwargs)

    tf_file = Path(run_dir) / "main.tf"
    tf_file.write_text(tf_code)
    console.print(f"[green]Generated {tf_file} for {provider_label} provider[/green]")
    return tf_file


def generate_tf(config: PrivateCloudConfig, run_dir: str = "."):
    """Generate a main.tf file from a Jinja2 template for the configured provider."""
    if config.provider == "proxmox":
        if config.proxmox is None:
            raise ValueError("Provider is 'proxmox' but no proxmox config block found in privatecloud.yaml")

        ssh_key = ""
        if config.ssh_key_path and Path(config.ssh_key_path).exists():
            ssh_key = Path(config.ssh_key_path).read_text().strip()

        _render_template("proxmox.tf.j2", run_dir, "Proxmox", config=config, ssh_key=ssh_key)

    elif config.provider == "morpheus":
        if config.morpheus is None:
            raise ValueError("Provider is 'morpheus' but no morpheus config block found in privatecloud.yaml")

        _render_template("morpheus.tf.j2", run_dir, "HPE Morpheus", config=config)

    else:
        raise ValueError(f"Provider '{config.provider}' is not supported via Terraform.")


def terraform_init(run_dir: str = "."):
    run_tf(["terraform", "init"], cwd=run_dir)


def terraform_apply(run_dir: str = "."):
    run_tf(["terraform", "apply", "-auto-approve"], cwd=run_dir)


def terraform_destroy(run_dir: str = "."):
    run_tf(["terraform", "destroy", "-auto-approve"], cwd=run_dir)


def get_outputs(run_dir: str = ".") -> dict:
    res = run_tf(["terraform", "output", "-json"], cwd=run_dir, capture_output=True)
    try:
        return json.loads(res.stdout)
    except json.JSONDecodeError:
        console.print("[yellow]Warning: Could not parse Terraform outputs[/yellow]")
        return {}


def _resolve_ssh_user(config: PrivateCloudConfig, role: str) -> str:
    """Determine the SSH user for provisioned nodes based on provider."""
    if config.provider == "morpheus" and config.morpheus:
        return config.morpheus.ssh_user
    return "root"


def apply_and_update_config(config: PrivateCloudConfig, run_dir: str = ".") -> PrivateCloudConfig:
    """Run full Terraform lifecycle and write resulting IPs back into the config."""
    generate_tf(config, run_dir)
    terraform_init(run_dir)
    terraform_apply(run_dir)

    outputs = get_outputs(run_dir)
    master_ips = outputs.get("master_ips", {}).get("value", [])
    worker_ips = outputs.get("worker_ips", {}).get("value", [])

    master_user = _resolve_ssh_user(config, "master")
    worker_user = _resolve_ssh_user(config, "worker")

    new_nodes = []
    for ip in master_ips:
        if ip:
            new_nodes.append(NodeConfig(host=ip, user=master_user, role="master"))

    for ip in worker_ips:
        if ip:
            new_nodes.append(NodeConfig(host=ip, user=worker_user, role="worker"))

    if not new_nodes:
        if config.provider == "proxmox":
            console.print("[yellow]Warning: Terraform returned no IPs. Is the QEMU agent running inside the VMs?[/yellow]")
        elif config.provider == "morpheus":
            console.print("[yellow]Warning: Terraform returned no IPs. Check Morpheus instance status and network assignment.[/yellow]")
        else:
            console.print("[yellow]Warning: Terraform returned no IPs.[/yellow]")

    config.nodes = new_nodes
    save_config(config)
    console.print(f"[green]Updated privatecloud.yaml with {len(new_nodes)} node(s)[/green]")

    return config
