import subprocess
import os
from rich.console import Console

console = Console()

_repos_added: set = set()


def run_helm(cmd: list, kubeconfig: str = "kubeconfig.yaml", check: bool = True):
    """Execute a helm CLI command with the given kubeconfig."""
    env = os.environ.copy()
    env["KUBECONFIG"] = os.path.abspath(kubeconfig)

    full_cmd = ["helm"] + cmd
    console.print(f"[cyan]$ {' '.join(full_cmd)}[/cyan]")

    try:
        return subprocess.run(full_cmd, check=check, env=env)
    except subprocess.CalledProcessError as e:
        console.print(f"[red]Helm command failed (exit {e.returncode})[/red]")
        raise
    except FileNotFoundError:
        console.print("[red]'helm' binary not found. Run: privatecloud doctor[/red]")
        raise RuntimeError("helm is not installed or not in PATH")


def add_repo(name: str, url: str):
    """Add a Helm chart repository (skips if already added this session)."""
    if name in _repos_added:
        return
    run_helm(["repo", "add", name, url, "--force-update"])
    _repos_added.add(name)


def update_repos():
    """Run helm repo update once after all repos have been added."""
    run_helm(["repo", "update"])


def install_chart(
    release_name: str,
    chart: str,
    namespace: str = "default",
    create_namespace: bool = True,
    values: dict = None,
    wait: bool = True,
    timeout: str = "10m",
):
    """Install or upgrade a Helm chart release."""
    cmd = ["upgrade", "--install", release_name, chart, "--namespace", namespace]
    if create_namespace:
        cmd.append("--create-namespace")
    if wait:
        cmd.extend(["--wait", "--timeout", timeout])

    if values:
        for k, v in values.items():
            cmd.extend(["--set", f"{k}={v}"])

    run_helm(cmd)
