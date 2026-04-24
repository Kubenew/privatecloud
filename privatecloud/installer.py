import subprocess
from typing import List
from rich.console import Console
import os
from pathlib import Path

from .config import PrivateCloudConfig
from .helm import add_repo, install_chart

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


def fetch_kubeconfig(master_host: str, user: str):
    console.print("[yellow]Fetching kubeconfig from master...[/yellow]")
    cmd = ["ssh", f"{user}@{master_host}", "sudo cat /etc/rancher/k3s/k3s.yaml"]
    kubeconfig_content = subprocess.check_output(cmd).decode("utf-8")
    
    # Replace localhost with master IP
    kubeconfig_content = kubeconfig_content.replace("127.0.0.1", master_host)
    
    with open("kubeconfig.yaml", "w", encoding="utf-8") as f:
        f.write(kubeconfig_content)
    console.print("[green]Saved kubeconfig.yaml[/green]")


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
            
    # Fetch kubeconfig for helm
    fetch_kubeconfig(master.host, master.user)
    
    # Install services via Helm
    console.print("[bold green]Installing cluster services...[/bold green]")
    
    if config.services.ingress_nginx:
        console.print("[yellow]Installing Ingress NGINX...[/yellow]")
        add_repo("ingress-nginx", "https://kubernetes.github.io/ingress-nginx")
        install_chart("ingress-nginx", "ingress-nginx/ingress-nginx", "ingress-nginx")
        
    if config.services.cert_manager:
        console.print("[yellow]Installing Cert-Manager...[/yellow]")
        add_repo("jetstack", "https://charts.jetstack.io")
        install_chart("cert-manager", "jetstack/cert-manager", "cert-manager", values={"installCRDs": "true"})
        
    if config.services.metallb:
        console.print("[yellow]Installing MetalLB...[/yellow]")
        add_repo("metallb", "https://metallb.github.io/metallb")
        install_chart("metallb", "metallb/metallb", "metallb-system")
        
    if config.services.monitoring:
        console.print("[yellow]Installing Prometheus/Grafana (kube-prometheus-stack)...[/yellow]")
        add_repo("prometheus-community", "https://prometheus-community.github.io/helm-charts")
        install_chart("monitoring", "prometheus-community/kube-prometheus-stack", "monitoring")
        
    if config.services.longhorn:
        console.print("[yellow]Installing Longhorn...[/yellow]")
        add_repo("longhorn", "https://charts.longhorn.io")
        install_chart("longhorn", "longhorn/longhorn", "longhorn-system")

    console.print("[bold green]PrivateCloud installation completed.[/bold green]")
    console.print(f"You can now manage your cluster using:\nexport KUBECONFIG={os.path.abspath('kubeconfig.yaml')}\nkubectl get nodes")

