import typer
from rich.console import Console
from rich.table import Table
from rich import print as rprint
import os
from datetime import datetime

from .doctor import check_tools, display_diagnostics
from .scheduler import schedule_backup, remove_schedule, get_schedule_status
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
    download_from_remote, list_all_backups,
)
from .upgrade import upgrade_cluster, get_current_k3s_version, get_cluster_nodes, check_upgrade_available
from .multicluster import list_clusters, add_cluster, remove_cluster, switch_cluster, get_cluster_info
from .addons import AddonManager, list_available_addons, search_addons
from .validate import print_validation_report, lint_config
from .high_availability import create_ha_config, get_cluster_health_ha, validate_ha_setup
from .pitr import (
    check_longhorn_available, get_volumes, get_snapshots, 
    create_volume_snapshot, restore_from_snapshot, delete_old_snapshots,
    create_pvc_from_snapshot, list_snapshots_with_volumes
)
from .changelog import generate_release_notes, write_changelog, get_version_from_pyproject

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
    s3_bucket: str = typer.Option(None, "--s3", help="Upload to S3 bucket"),
    gcs_bucket: str = typer.Option(None, "--gcs", help="Upload to GCS bucket"),
    azure_container: str = typer.Option(None, "--azure", help="Upload to Azure container"),
    etcd_snapshot: bool = typer.Option(False, "--etcd-snapshot", help="Include etcd snapshot"),
):
    """Create a new backup."""
    result = do_backup(name, encrypt=encrypt, passphrase=passphrase, keep_last=keep_last,
                       s3_bucket=s3_bucket, gcs_bucket=gcs_bucket, azure_container=azure_container,
                       etcd_snapshot=etcd_snapshot)
    if result:
        console.print(f"[green]✅ Backup created: {result}[/green]")


@backup_group.command()
def list(
    s3_bucket: str = typer.Option(None, "--s3", help="List backups in S3 bucket"),
    azure_container: str = typer.Option(None, "--azure", help="List backups in Azure container"),
    remote_only: bool = typer.Option(False, "--remote-only", help="Show only remote backups"),
):
    """List all backups."""
    if s3_bucket or azure_container:
        backups = list_all_backups(s3_bucket=s3_bucket, azure_container=azure_container)
    else:
        backups = do_list_backups()
    
    if backups:
        table = Table(title="Available Backups")
        table.add_column("Name", style="cyan")
        table.add_column("Size (KB)", justify="right")
        table.add_column("Encrypted", justify="center")
        table.add_column("Storage", style="dim")
        for b in backups:
            table.add_row(
                b["name"], 
                str(b["size"]), 
                "🔐" if b.get("encrypted") else "",
                b.get("storage", "local")
            )
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


@backup_group.command(name="schedule")
def schedule(
    interval: str = typer.Argument(..., help="Schedule interval (hourly, daily, weekly, monthly)"),
    keep: int = typer.Option(7, "--keep", help="Number of backups to keep"),
    encrypt: bool = typer.Option(False, "--encrypt", help="Encrypt backups"),
    remove: bool = typer.Option(False, "--remove", help="Remove scheduled backup"),
):
    """Schedule automatic backups."""
    if remove:
        if remove_schedule():
            console.print("[green]✅ Scheduled backup removed[/green]")
        else:
            console.print("[red]❌ Failed to remove schedule[/red]")
        return
    
    if schedule_backup(interval, keep, encrypt):
        console.print(f"[green]✅ Scheduled {interval} backups (keeping {keep})[/green]")
    else:
        console.print("[red]❌ Failed to schedule backups[/red]")


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


@app.command()
def upgrade(
    version: str = typer.Argument(..., help="Target K3s version (e.g., v1.30.0+k3s1)"),
    backup: bool = typer.Option(True, "--backup/--no-backup", help="Create backup before upgrade"),
    dry_run: bool = typer.Option(False, "--dry-run", help="Preview upgrade without changes"),
):
    """Upgrade Kubernetes cluster to a new version."""
    current = get_current_k3s_version()
    if current:
        console.print(f"[cyan]Current version: {current}[/cyan]")
    console.print(f"[cyan]Target version: {version}[/cyan]")
    
    if upgrade_cluster(version, backup=backup, dry_run=dry_run):
        if dry_run:
            console.print("[yellow]Dry run complete[/yellow]")
        else:
            console.print(f"[green]✅ Cluster upgrade to {version} initiated[/green]")
    else:
        console.print("[red]❌ Upgrade failed[/red]")
        raise typer.Exit(code=1)


cluster_group = typer.Typer(help="Multi-cluster management.")
app.add_typer(cluster_group, name="cluster")


@cluster_group.command(name="list")
def cluster_list():
    """List all managed clusters."""
    clusters = list_clusters()
    if clusters:
        table = Table(title="Managed Clusters")
        table.add_column("Name", style="cyan")
        table.add_column("Provider", style="dim")
        table.add_column("Current", justify="center")
        for c in clusters:
            table.add_row(c.name, c.provider, "✅" if c.current else "")
        console.print(table)
    else:
        console.print("[yellow]No clusters managed. Add with 'privatecloud cluster add'[/yellow]")


@cluster_group.command()
def add(
    name: str = typer.Argument(..., help="Cluster name"),
    kubeconfig: str = typer.Argument(..., help="Path to kubeconfig file"),
    provider: str = typer.Option("unknown", "--provider", help="Cluster provider"),
):
    """Add a cluster to management."""
    if add_cluster(name, kubeconfig, provider=provider):
        console.print(f"[green]✅ Cluster '{name}' added[/green]")
    else:
        console.print("[red]❌ Failed to add cluster[/red]")


@cluster_group.command()
def switch(name: str = typer.Argument(..., help="Cluster name")):
    """Switch to a different cluster."""
    if switch_cluster(name):
        console.print(f"[green]✅ Switched to cluster '{name}'[/green]")
    else:
        console.print("[red]❌ Failed to switch cluster[/red]")


@cluster_group.command()
def remove(name: str = typer.Argument(..., help="Cluster name")):
    """Remove a cluster from management."""
    if remove_cluster(name):
        console.print(f"[green]✅ Cluster '{name}' removed[/green]")
    else:
        console.print("[red]❌ Failed to remove cluster[/red]")


addon_group = typer.Typer(help="Add-on marketplace.")
app.add_typer(addon_group, name="addon")


@addon_group.command(name="list")
def addon_list(installed: bool = typer.Option(False, "--installed", help="Show only installed")):
    """List available add-ons."""
    manager = AddonManager()
    addons = manager.list_addons(installed_only=installed)
    
    if addons:
        table = Table(title="Add-ons")
        table.add_column("Name", style="cyan")
        table.add_column("Category", style="dim")
        table.add_column("Status", justify="center")
        table.add_column("Description")
        for a in addons:
            status = "✅" if a['installed'] else "⬜"
            table.add_row(a['name'], a['category'], status, a['description'][:50])
        console.print(table)
    else:
        console.print("[yellow]No add-ons found[/yellow]")


@addon_group.command()
def install(
    name: str = typer.Argument(..., help="Add-on name"),
):
    """Install an add-on."""
    manager = AddonManager()
    if manager.install_addon(name):
        console.print(f"[green]✅ Add-on '{name}' installed[/green]")
    else:
        console.print("[red]❌ Installation failed[/red]")


@addon_group.command()
def uninstall(name: str = typer.Argument(..., help="Add-on name")):
    """Uninstall an add-on."""
    manager = AddonManager()
    if manager.uninstall_addon(name):
        console.print(f"[green]✅ Add-on '{name}' uninstalled[/green]")
    else:
        console.print("[red]❌ Uninstallation failed[/red]")


@addon_group.command()
def search(query: str = typer.Argument(..., help="Search term")):
    """Search for add-ons."""
    results = search_addons(query)
    if results:
        console.print(f"[cyan]Found {len(results)} add-ons:[/cyan]")
        for a in results:
            console.print(f"  • {a['name']} - {a['description']}")
    else:
        console.print("[yellow]No add-ons found[/yellow]")


@app.command()
def lint(
    path: str = typer.Option("privatecloud.yaml", "--config", help="Config file to lint"),
):
    """Validate configuration file."""
    print_validation_report(path)


@app.command()
def snapshot(
    volume: str = typer.Argument(..., help="Volume name"),
    namespace: str = typer.Option("longhorn-system", "--namespace", "-n", help="Namespace"),
):
    """Create a Longhorn volume snapshot."""
    name = create_volume_snapshot(volume, namespace)
    if name:
        console.print(f"[green]✅ Snapshot created: {name}[/green]")
    else:
        console.print("[red]❌ Failed to create snapshot[/red]")


@app.command()
def restore(
    volume: str = typer.Argument(..., help="Volume name"),
    snapshot_name: str = typer.Argument(..., help="Snapshot name"),
    new_name: str = typer.Option(None, "--name", help="New volume name"),
    namespace: str = typer.Option("longhorn-system", "--namespace", "-n", help="Namespace"),
):
    """Restore volume from Longhorn snapshot."""
    if restore_from_snapshot(volume, snapshot_name, new_name, namespace):
        console.print(f"[green]✅ Restore initiated[/green]")
    else:
        console.print("[red]❌ Restore failed[/red]")


@app.command()
def snapshots_list(
    volume: str = typer.Option(None, "--volume", help="Filter by volume name"),
    namespace: str = typer.Option("longhorn-system", "--namespace", "-n", help="Namespace"),
):
    """List Longhorn volume snapshots."""
    if not check_longhorn_available():
        console.print("[yellow]Longhorn not installed[/yellow]")
        return
    
    if volume:
        snaps = get_snapshots(volume, namespace)
        console.print(f"[cyan]Snapshots for {volume}:[/cyan]")
        for s in snaps:
            console.print(f"  - {s['name']} ({s['created'][:10]})")
    else:
        all_volumes = list_snapshots_with_volumes()
        table = Table(title="Volumes & Snapshots")
        table.add_column("Volume", style="cyan")
        table.add_column("Namespace", style="dim")
        table.add_column("State", justify="center")
        table.add_column("Snapshots", justify="right")
        for v in all_volumes:
            table.add_row(v['volume'], v['namespace'], v['state'], str(v['snapshot_count']))
        console.print(table)


@app.command()
def ha(
    action: str = typer.Argument(..., help="Action: status, setup"),
    master_ips: str = typer.Option("", "--masters", help="Comma-separated master IPs"),
    worker_ips: str = typer.Option("", "--workers", help="Comma-separated worker IPs"),
):
    """High availability cluster operations."""
    if action == "status":
        status = get_cluster_health_ha()
        if status.get('healthy'):
            console.print(f"[green]✅ HA Status: {status.get('ha_status')}[/green]")
            console.print(f"Masters: {status['masters']['ready']}/{status['masters']['total']} ready")
            console.print(f"Workers: {status['workers']['ready']}/{status['workers']['total']} ready")
        else:
            console.print(f"[red]❌ HA Status: {status.get('error', 'unhealthy')}[/red]")
    elif action == "setup":
        masters = [m.strip() for m in master_ips.split(',') if m.strip()]
        workers = [w.strip() for w in worker_ips.split(',') if w.strip()]
        
        if len(masters) < 2:
            console.print("[red]❌ Need at least 2 master IPs for HA[/red]")
            return
        
        warnings = validate_ha_setup(len(masters), "embedded")
        for w in warnings:
            console.print(f"[yellow]⚠️  {w}[/yellow]")
        
        from pathlib import Path
        output = Path("ha-setup")
        files = create_ha_config(output, masters, workers)
        
        console.print(f"[green]✅ HA config created in {output}/[/green]")
        console.print(f"  - {files['masters'].name} - Master install script")
        console.print(f"  - {files['workers'].name} - Worker join script")
        console.print(f"  - {files['config'].name} - Configuration")


@app.command()
def changelog_update():
    """Update CHANGELOG.md from git history."""
    write_changelog()
    console.print("[green]✅ CHANGELOG.md updated[/green]")


@app.command()
def release_notes(
    version: str = typer.Argument(None, help="Version number (auto-detected if omitted)"),
):
    """Generate release notes for current version."""
    if not version:
        version = f"v{get_version_from_pyproject()}"
    notes = generate_release_notes(version)
    console.print(notes)

