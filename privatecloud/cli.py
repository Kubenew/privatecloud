import typer
from rich.console import Console
from rich.table import Table
import os

from .doctor import check_tools
from .utils import save_default_config, load_config, save_config
from .installer import install
from .terraform import apply_and_update_config, terraform_destroy

app = typer.Typer(help="PrivateCloud: one-command private cloud installer.")
console = Console()


@app.command()
def init():
    save_default_config()
    console.print("[green]Created privatecloud.yaml[/green]")


@app.command()
def doctor():
    result = check_tools()

    table = Table(title="PrivateCloud Doctor")
    table.add_column("Tool")
    table.add_column("Status")

    for t in result.missing_required:
        table.add_row(t, "[red]MISSING (required)[/red]")

    for t in result.missing_optional:
        table.add_row(t, "[yellow]MISSING (optional)[/yellow]")

    if not result.missing_required and not result.missing_optional:
        table.add_row("all", "[green]OK[/green]")

    console.print(table)

    if not result.ok:
        raise typer.Exit(code=1)


@app.command()
def plan():
    cfg = load_config()

    console.print(f"[bold]Cluster:[/bold] {cfg.cluster_name}")
    console.print(f"[bold]Provider:[/bold] {cfg.provider}")
    console.print(f"[bold]K3s Version:[/bold] {cfg.k3s_version}")
    
    if cfg.provider == "bare-metal":
        console.print("[bold]Nodes:[/bold]")
        for i, n in enumerate(cfg.nodes):
            role = "master" if i == 0 else "worker"
            console.print(f"  - {n.user}@{n.host}:{n.port} ({role})")
    else:
        console.print("[bold]Nodes:[/bold] [yellow]Will be provisioned dynamically via Terraform[/yellow]")

    console.print("[bold]Services:[/bold]")
    console.print(cfg.services.model_dump())


@app.command()
def install_cluster(dry_run: bool = typer.Option(False, "--dry-run", help="Show what would be installed without actually installing")):
    cfg = load_config()
    
    if dry_run:
        console.print("[bold cyan]=== PrivateCloud Dry Run ===[/bold cyan]")
        console.print(f"\n[bold]Cluster:[/bold] {cfg.cluster_name}")
        console.print(f"[bold]K3s Version:[/bold] {cfg.k3s_version}")
        console.print(f"[bold]Provider:[/bold] {cfg.provider}")
        console.print("\n[bold]Services to be installed:[/bold]")
        console.print("  - K3s Kubernetes")
        if cfg.services.monitoring:
            console.print("  - Prometheus + Grafana (monitoring)")
        if cfg.services.ingress_nginx:
            console.print("  - Ingress NGINX")
        if cfg.services.cert_manager:
            console.print("  - Cert-Manager")
        if cfg.services.metallb:
            console.print("  - MetalLB")
        if cfg.services.longhorn:
            console.print("  - Longhorn (storage)")
        console.print("\n[green]This is a dry run. No changes were made.[/green]")
        return
    
    if cfg.provider != "bare-metal":
        console.print(f"[bold cyan]Provisioning nodes via Terraform ({cfg.provider})...[/bold cyan]")
        cfg = apply_and_update_config(cfg)
        
    install(cfg)


@app.command()
def destroy():
    cfg = load_config()
    if cfg.provider == "bare-metal":
        console.print("[yellow]Destroy is only supported for cloud providers managed by Terraform.[/yellow]")
        return
        
    console.print(f"[bold red]Destroying cluster {cfg.cluster_name}...[/bold red]")
    terraform_destroy()
    
    # Clear nodes list from config
    cfg.nodes = []
    save_config(cfg)
    console.print("[green]Cluster destroyed and config updated.[/green]")


if __name__ == "__main__":
    app()

