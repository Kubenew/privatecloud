import subprocess
import time
from typing import List
from rich.console import Console
import os

from .config import PrivateCloudConfig
from .helm import add_repo, update_repos, install_chart

console = Console()


def run(cmd: List[str], check: bool = True):
    """Run a shell command with console output."""
    console.print(f"[cyan]$ {' '.join(cmd)}[/cyan]")
    return subprocess.run(cmd, check=check)


def _ssh_opts(config: PrivateCloudConfig) -> List[str]:
    """Build common SSH options (e.g. identity file)."""
    opts = []
    if config.ssh_key_path:
        opts.extend(["-i", config.ssh_key_path])
    opts.extend(["-o", "StrictHostKeyChecking=no", "-o", "ConnectTimeout=10"])
    return opts


def install_k3s_master(node_host: str, user: str, k3s_version: str, ssh_opts: List[str]):
    cmd = [
        "ssh", *ssh_opts,
        f"{user}@{node_host}",
        f"curl -sfL https://get.k3s.io | INSTALL_K3S_VERSION={k3s_version} sh -"
    ]
    run(cmd)


def install_k3s_agent(node_host: str, user: str, master_ip: str, token: str, k3s_version: str, ssh_opts: List[str]):
    cmd = [
        "ssh", *ssh_opts,
        f"{user}@{node_host}",
        f"curl -sfL https://get.k3s.io | K3S_URL=https://{master_ip}:6443 K3S_TOKEN={token} INSTALL_K3S_VERSION={k3s_version} sh -"
    ]
    run(cmd)


def get_k3s_token(master_host: str, user: str, ssh_opts: List[str]) -> str:
    cmd = ["ssh", *ssh_opts, f"{user}@{master_host}", "sudo cat /var/lib/rancher/k3s/server/node-token"]
    console.print("[yellow]Fetching K3s node token...[/yellow]")
    res = subprocess.check_output(cmd).decode("utf-8").strip()
    return res


def fetch_kubeconfig(master_host: str, user: str, ssh_opts: List[str], retries: int = 3):
    """Fetch kubeconfig from master node, retrying on transient SSH failures."""
    console.print("[yellow]Fetching kubeconfig from master...[/yellow]")
    cmd = ["ssh", *ssh_opts, f"{user}@{master_host}", "sudo cat /etc/rancher/k3s/k3s.yaml"]

    for attempt in range(1, retries + 1):
        try:
            kubeconfig_content = subprocess.check_output(cmd).decode("utf-8")
            break
        except subprocess.CalledProcessError:
            if attempt < retries:
                console.print(f"[yellow]Retry {attempt}/{retries} — waiting for K3s API...[/yellow]")
                time.sleep(10)
            else:
                raise RuntimeError("Failed to fetch kubeconfig after retries")

    # Replace localhost with master IP
    kubeconfig_content = kubeconfig_content.replace("127.0.0.1", master_host)

    with open("kubeconfig.yaml", "w", encoding="utf-8") as f:
        f.write(kubeconfig_content)
    console.print("[green]Saved kubeconfig.yaml[/green]")


def _install_services(config: PrivateCloudConfig):
    """Add all needed Helm repos, update once, then install each enabled service."""
    console.print("[bold green]Installing cluster services via Helm...[/bold green]")

    # --- Register repos first (deduplicated) ---
    if config.services.ingress_nginx:
        add_repo("ingress-nginx", "https://kubernetes.github.io/ingress-nginx")
    if config.services.cert_manager:
        add_repo("jetstack", "https://charts.jetstack.io")
    if config.services.metallb:
        add_repo("metallb", "https://metallb.github.io/metallb")
    if config.services.monitoring:
        add_repo("prometheus-community", "https://prometheus-community.github.io/helm-charts")
    if config.services.longhorn:
        add_repo("longhorn", "https://charts.longhorn.io")

    # --- Single repo update ---
    update_repos()

    # --- Install charts ---
    if config.services.ingress_nginx:
        console.print("[yellow]Installing Ingress NGINX...[/yellow]")
        install_chart("ingress-nginx", "ingress-nginx/ingress-nginx", "ingress-nginx")

    if config.services.cert_manager:
        console.print("[yellow]Installing Cert-Manager...[/yellow]")
        install_chart("cert-manager", "jetstack/cert-manager", "cert-manager", values={"installCRDs": "true"})

    if config.services.metallb:
        console.print("[yellow]Installing MetalLB...[/yellow]")
        install_chart("metallb", "metallb/metallb", "metallb-system")

    if config.services.monitoring:
        console.print("[yellow]Installing Prometheus/Grafana (kube-prometheus-stack)...[/yellow]")
        install_chart("monitoring", "prometheus-community/kube-prometheus-stack", "monitoring")

    if config.services.longhorn:
        console.print("[yellow]Installing Longhorn...[/yellow]")
        install_chart("longhorn", "longhorn/longhorn", "longhorn-system")


def install(config: PrivateCloudConfig):
    """Full installation: K3s on all nodes, then Helm services."""
    if not config.nodes:
        raise RuntimeError("No nodes configured in privatecloud.yaml")

    master = config.nodes[0]
    workers = config.nodes[1:]
    ssh_opts = _ssh_opts(config)

    console.print(f"[bold green]Installing K3s master on {master.host}[/bold green]")
    install_k3s_master(master.host, master.user, config.k3s_version, ssh_opts)

    if workers:
        token = get_k3s_token(master.host, master.user, ssh_opts)

        for w in workers:
            console.print(f"[bold green]Installing K3s worker on {w.host}[/bold green]")
            install_k3s_agent(
                node_host=w.host,
                user=w.user,
                master_ip=master.host,
                token=token,
                k3s_version=config.k3s_version,
                ssh_opts=ssh_opts,
            )

    # Fetch kubeconfig for helm
    fetch_kubeconfig(master.host, master.user, ssh_opts)

    # Install services via Helm
    _install_services(config)

    console.print("[bold green]PrivateCloud installation completed.[/bold green]")
    console.print(f"Manage your cluster:\n  export KUBECONFIG={os.path.abspath('kubeconfig.yaml')}\n  kubectl get nodes")

