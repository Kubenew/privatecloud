import typer
from rich.console import Console
from rich.table import Table

from .doctor import check_tools
from .utils import save_default_config, load_config
from .installer import install

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
    console.print(f"[bold]K3s Version:[/bold] {cfg.k3s_version}")
    console.print("[bold]Nodes:[/bold]")
    for n in cfg.nodes:
        console.print(f"  - {n.user}@{n.host}:{n.port}")

    console.print("[bold]Services:[/bold]")
    console.print(cfg.services.model_dump())


@app.command()
def install_cluster():
    cfg = load_config()
    install(cfg)


@app.command()
def destroy():
    console.print("[yellow]Destroy is not implemented in v0.1.0[/yellow]")


if __name__ == "__main__":
    app()
