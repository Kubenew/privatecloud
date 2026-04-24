import typer
from rich.console import Console
from rich.table import Table
from rich import print as rprint
import os
from datetime import datetime

from .doctor import check_tools, display_diagnostics
from .utils import save_default_config, load_config, save_config
from .installer import install
from .terraform import apply_and_update_config, terraform_destroy
from .security import write_gitignore, mask_dict_secrets
from .backup import (
    create_backup as do_backup, 
    list_backups as do_list_backups, 
    restore_backup as do_restore_backup, 
    delete_backup as do_delete_backup,
    verify_backup as do_verify_backup,
    pre_destroy_backup as do_pre_destroy_backup,
)

app = typer.Typer(help="PrivateCloud: one-command private cloud installer.")
console = Console()


@app.command()
def init():
    save_default_config()
    if write_gitignore():
        console.print("[green]Created .gitignore with PrivateCloud rules[/green]")
    console.print("[green]Created privatecloud.yaml[/green]")


@app.command()
def doctor(diagnostics: bool = typer.Option(False, "--diagnostics", "-d", help="Run full diagnostics")):
    """Check system dependencies and cluster health."""
    if diagnostics:
        display_diagnostics()
    else:
        result = check_tools()

        table = Table(title="PrivateCloud Doctor")
        table.add_column("Tool")
        table.add_column("Status")

        for t in result.missing_required:
            table.add_row(t, "[red]❌ MISSING (required)[/red]")

        for t in result.missing_optional:
            table.add_row(t, "[yellow]⚠️  MISSING (optional)[/yellow]")

        if not result.missing_required and not result.missing_optional:
            table.add_row("all", "[green]✅ OK[/green]")

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
    console.print(mask_dict_secrets(cfg.services.model_dump()))


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
        cfg = apply_and_update_config(cfg, run_dir=cfg.terraform_dir)
        
    install(cfg)


@app.command()
def destroy(
    yes: bool = typer.Option(False, "--yes", help="Skip confirmation prompt"),
    dry_run: bool = typer.Option(False, "--dry-run", help="Preview what would be destroyed"),
    backup: bool = typer.Option(True, "--backup/--no-backup", help="Create backup before destroying"),
    auto_yes: bool = False,
):
    """Destroy the cluster and all associated resources."""
    cfg = load_config()
    if cfg.provider == "bare-metal":
        console.print("[yellow]Destroy is only supported for cloud providers managed by Terraform.[/yellow]")
        return

    pre_destroy_path = None
    if backup and not dry_run:
        pre_destroy_path = do_pre_destroy_backup()
        if pre_destroy_path:
            console.print(f"[yellow]Pre-destroy backup created: {pre_destroy_path}[/yellow]")

    if backup and not dry_run and not auto_yes:
        console.print("[yellow]Creating full backup before destruction...[/yellow]")
        do_backup()

    if not yes and not dry_run and not auto_yes:
        console.print(f"[bold red]⚠️  This will DESTROY the entire cluster '{cfg.cluster_name}'![/bold red]")
        confirm = console.input("\nType 'yes' to confirm: ")
        if confirm.lower() != "yes":
            console.print("Aborted.")
            return

    backup_dir = None
    if backup and not dry_run and not auto_yes:
        timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
        backup_dir = f"backup_{timestamp}"
        os.makedirs(backup_dir, exist_ok=True)
        if os.path.exists("terraform"):
            shutil.copytree("terraform", f"{backup_dir}/terraform")
        if os.path.exists("privatecloud.yaml"):
            shutil.copy("privatecloud.yaml", f"{backup_dir}/privatecloud.yaml")
        console.print(f"[yellow]Backup created at {backup_dir}/[/yellow]")

    console.print(f"[bold red]Destroying cluster {cfg.cluster_name}...[/bold red]")
    terraform_destroy(run_dir=cfg.terraform_dir)

    cfg.nodes = []
    save_config(cfg)

    for f in ["kubeconfig", "terraform/terraform.tfstate", "terraform/terraform.tfstate.backup"]:
        if os.path.exists(f):
            if dry_run:
                console.print(f"[yellow](dry-run) Would remove {f}[/yellow]")
            else:
                if os.path.isdir(f):
                    shutil.rmtree(f)
                else:
                    os.remove(f)

    if dry_run:
        console.print("[yellow]Dry run complete – no changes made.[/yellow]")
    else:
        console.print("[green]✅ Cluster destroyed successfully.[/green]")
        if backup_dir:
            console.print(f"Backup stored in {backup_dir}/")

    return True


if __name__ == "__main__":
    app()


backup_group = typer.Typer(help="Backup and restore operations.")
app.add_typer(backup_group, name="backup")


@backup_group.command()
def create(
    name: str = typer.Argument(None, help="Optional backup name"),
    encrypt: bool = typer.Option(False, "--encrypt", help="Encrypt backup with passphrase"),
    passphrase: str = typer.Option(None, "--passphrase", help="Encryption passphrase (or use PRIVATECLOUD_BACKUP_PASS env var)"),
    keep_last: int = typer.Option(None, "--keep-last", help="Number of Longhorn snapshots to keep"),
):
    """Create a new backup."""
    result = do_backup(name, encrypt=encrypt, passphrase=passphrase, keep_last=keep_last)
    if result:
        console.print(f"[green]✅ Backup created: {result}[/green]")


@backup_group.command()
def list():
    """List all backups."""
    backups = do_list_backups()
    if backups:
        table = Table(title="Available Backups")
        table.add_column("Name", style="cyan")
        table.add_column("Size (KB)", justify="right")
        table.add_column("Encrypted", justify="center")
        for b in backups:
            table.add_row(b["name"], str(b["size"]), "🔐" if b["encrypted"] else "")
        console.print(table)
    else:
        console.print("[yellow]No backups found[/yellow]")


@backup_group.command()
def restore(
    backup_name: str = typer.Argument(..., help="Backup name to restore"),
    force: bool = typer.Option(False, "--force", "-f", help="Force replace existing resources"),
    dry_run: bool = typer.Option(False, "--dry-run", help="Preview restore without applying changes"),
    passphrase: str = typer.Option(None, "--passphrase", help="Decryption passphrase"),
):
    """Restore from a backup."""
    console.print(f"[yellow]Restoring from {backup_name}...[/yellow]")
    if dry_run:
        console.print("[cyan]Running in dry-run mode...[/cyan]")
    if do_restore_backup(backup_name, force=force, dry_run=dry_run, passphrase=passphrase):
        console.print("[green]✅ Restore complete[/green]")
    else:
        console.print("[red]❌ Restore failed[/red]")
        raise typer.Exit(code=1)


@backup_group.command()
def verify(
    backup_name: str = typer.Argument(..., help="Backup name to verify"),
    passphrase: str = typer.Option(None, "--passphrase", help="Decryption passphrase"),
):
    """Verify backup integrity."""
    console.print(f"[cyan]Verifying backup: {backup_name}[/cyan]")
    if do_verify_backup(backup_name, passphrase=passphrase):
        console.print("[green]✅ Backup verified successfully[/green]")
    else:
        console.print("[red]❌ Verification failed[/red]")


@backup_group.command()
def delete(backup_name: str = typer.Argument(..., help="Backup name to delete")):
    """Delete a backup."""
    if do_delete_backup(backup_name):
        console.print(f"[green]✅ Deleted backup: {backup_name}[/green]")
    else:
        console.print(f"[red]❌ Backup not found: {backup_name}[/red]")


@app.command()
def gui(
    host: str = typer.Option("127.0.0.1", "--host", help="Bind address"),
    port: int = typer.Option(5000, "--port", help="Port"),
    auth: bool = typer.Option(False, "--auth", help="Enable authentication"),
    username: str = typer.Option(None, "--username", help="GUI username (or use PRIVATECLOUD_GUI_USER)"),
    password: str = typer.Option(None, "--password", help="GUI password (or use PRIVATECLOUD_GUI_PASS)"),
):
    """Start web-based GUI dashboard."""
    try:
        from .gui.app import run_gui
        console.print(f"[cyan]🌐 Starting GUI at http://{host}:{port}[/cyan]")
        if auth:
            console.print(f"[yellow]🔐 Authentication enabled[/yellow]")
        run_gui(host=host, port=port, auth=auth, username=username, password=password)
    except ImportError as e:
        console.print(f"[red]Flask not installed. Run: pip install flask[/red]")
        raise typer.Exit(code=1)

