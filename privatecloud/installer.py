import subprocess
from typing import List
from rich.console import Console
from .config import PrivateCloudConfig

console = Console()


def run(cmd: List[str], check: bool = True):
    console.print(f"[cyan]$ {' '.join(cmd)}[/cyan]")
    return subprocess.run(cmd, check=check)


def install_k3s_master(node_host: str, user: str, k3s_version: str):
    cmd = [
        "ssh",
        f"{user}@{node_host}",
        f"curl -sfL https://get.k3s.io | INSTALL_K3S_VERSION={k3s_version} sh -"
    ]
    run(cmd)


def install_k3s_agent(node_host: str, user: str, master_ip: str, token: str, k3s_version: str):
    cmd = [
        "ssh",
        f"{user}@{node_host}",
        f"curl -sfL https://get.k3s.io | K3S_URL=https://{master_ip}:6443 K3S_TOKEN={token} INSTALL_K3S_VERSION={k3s_version} sh -"
    ]
    run(cmd)


def get_k3s_token(master_host: str, user: str) -> str:
    cmd = ["ssh", f"{user}@{master_host}", "sudo cat /var/lib/rancher/k3s/server/node-token"]
    console.print("[yellow]Fetching K3s node token...[/yellow]")
    res = subprocess.check_output(cmd).decode("utf-8").strip()
    return res


def install(config: PrivateCloudConfig):
    if not config.nodes:
        raise RuntimeError("No nodes configured in privatecloud.yaml")

    master = config.nodes[0]
    workers = config.nodes[1:]

    console.print(f"[bold green]Installing K3s master on {master.host}[/bold green]")
    install_k3s_master(master.host, master.user, config.k3s_version)

    if workers:
        token = get_k3s_token(master.host, master.user)

        for w in workers:
            console.print(f"[bold green]Installing K3s worker on {w.host}[/bold green]")
            install_k3s_agent(
                node_host=w.host,
                user=w.user,
                master_ip=master.host,
                token=token,
                k3s_version=config.k3s_version,
            )

    console.print("[bold green]PrivateCloud installation completed.[/bold green]")
