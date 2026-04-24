import os
import subprocess
import tarfile
import datetime
from pathlib import Path
import shutil

BACKUP_ROOT = Path("backups")


def ensure_backup_dir():
    BACKUP_ROOT.mkdir(exist_ok=True)


def create_backup(name=None):
    ensure_backup_dir()
    if name is None:
        name = f"backup_{datetime.datetime.now().strftime('%Y%m%d_%H%M%S')}"
    backup_path = BACKUP_ROOT / name
    backup_path.mkdir(exist_ok=True)

    print(f"Creating backup: {backup_path}")

    namespaces = subprocess.run(
        ["kubectl", "get", "namespaces", "-o", "name"],
        capture_output=True, text=True
    ).stdout.strip().split("\n")

    namespaces = [n for n in namespaces if n]

    if namespaces:
        namespaces_dir = backup_path / "namespaces"
        namespaces_dir.mkdir(parents=True, exist_ok=True)

        for ns_obj in namespaces:
            ns = ns_obj.replace("namespace/", "")
            ns_dir = namespaces_dir / ns
            ns_dir.mkdir(parents=True, exist_ok=True)

            for resource in ["deployments", "services", "configmaps", "secrets", "pvc", "ingress"]:
                try:
                    out = subprocess.run(
                        ["kubectl", "get", resource, "-n", ns, "-o", "yaml"],
                        capture_output=True, text=True, timeout=30
                    ).stdout
                    (ns_dir / f"{resource}.yaml").write_text(out)
                except Exception:
                    pass

    tf_state = Path("terraform/terraform.tfstate")
    if tf_state.exists():
        (backup_path / "terraform_state").write_text(tf_state.read_text())

    config = Path("privatecloud.yaml")
    if config.exists():
        (backup_path / "privatecloud.yaml").write_text(config.read_text())

    kubeconfig = Path("kubeconfig")
    if kubeconfig.exists():
        shutil.copy(kubeconfig, backup_path / "kubeconfig")

    try:
        volumes = subprocess.run(
            ["kubectl", "get", "volumes.longhorn.io", "-A", "-o", "jsonpath={.items[*].metadata.name}"],
            capture_output=True, text=True, timeout=30
        ).stdout.strip().split()
        if volumes and volumes[0]:
            (backup_path / "longhorn_volumes").write_text("\n".join(volumes))
    except Exception:
        pass

    tar_path = BACKUP_ROOT / f"{name}.tar.gz"
    with tarfile.open(tar_path, "w:gz") as tar:
        tar.add(backup_path, arcname=name)

    shutil.rmtree(backup_path)

    print(f"Backup saved: {tar_path}")
    return str(tar_path)


def list_backups():
    ensure_backup_dir()
    backups = sorted(BACKUP_ROOT.glob("*.tar.gz"), key=os.path.getmtime, reverse=True)
    return [b.name for b in backups]


def restore_backup(backup_name):
    backup_tar = BACKUP_ROOT / backup_name
    if not backup_tar.exists():
        backup_tar = BACKUP_ROOT / f"{backup_name}.tar.gz"
    if not backup_tar.exists():
        print(f"Backup {backup_name} not found")
        return False

    extract_path = BACKUP_ROOT / "restore_temp"
    if extract_path.exists():
        shutil.rmtree(extract_path)
    extract_path.mkdir(parents=True, exist_ok=True)

    with tarfile.open(backup_tar, "r:gz") as tar:
        tar.extractall(extract_path)

    backup_dir_name = backup_name.replace(".tar.gz", "")
    extract_dir = extract_path / backup_dir_name

    if not extract_dir.exists():
        for item in extract_path.iterdir():
            if item.is_dir():
                extract_dir = item
                break

    ns_dir = extract_dir / "namespaces"
    if ns_dir.exists():
        for ns_folder in ns_dir.iterdir():
            if ns_folder.is_dir():
                ns = ns_folder.name
                subprocess.run(["kubectl", "create", "ns", ns], capture_output=True)
                for manifest in ns_folder.glob("*.yaml"):
                    subprocess.run(["kubectl", "apply", "-f", str(manifest)], capture_output=True)

    tf_state = extract_dir / "terraform_state"
    if tf_state.exists():
        tf_dir = Path("terraform")
        tf_dir.mkdir(exist_ok=True)
        tf_dir.joinpath("terraform.tfstate").write_text(tf_state.read_text())
        print("Terraform state restored")

    shutil.rmtree(extract_path)
    print("Restore complete")
    return True


def delete_backup(backup_name):
    backup_tar = BACKUP_ROOT / backup_name
    if not backup_tar.exists():
        backup_tar = BACKUP_ROOT / f"{backup_name}.tar.gz"
    if backup_tar.exists():
        backup_tar.unlink()
        return True
    return False