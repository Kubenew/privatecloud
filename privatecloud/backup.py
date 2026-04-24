import os
import subprocess
import tarfile
import datetime
import tempfile
import json
from pathlib import Path
import shutil
import sys

BACKUP_ROOT = Path("backups")


def ensure_backup_dir():
    BACKUP_ROOT.mkdir(exist_ok=True)


def run_cmd(cmd, check=False, capture=True, timeout=30):
    try:
        result = subprocess.run(
            cmd,
            capture_output=capture,
            text=True,
            timeout=timeout,
            check=check
        )
        return result
    except subprocess.TimeoutExpired:
        print(f"⚠️  Command timed out: {' '.join(cmd)}")
        return type('obj', (object,), {'returncode': 1, 'stdout': '', 'stderr': 'Timeout'})()
    except Exception as e:
        print(f"⚠️  Command failed: {e}")
        return type('obj', (object,), {'returncode': 1, 'stdout': '', 'stderr': str(e)})()


def create_backup(name=None, encrypt=False, passphrase=None, keep_last=None):
    ensure_backup_dir()
    if name is None:
        name = f"backup_{datetime.datetime.now().strftime('%Y%m%d_%H%M%S')}"
    backup_path = BACKUP_ROOT / name
    backup_path.mkdir(exist_ok=True)

    print(f"📦 Creating backup: {backup_path}")

    namespaces = run_cmd(["kubectl", "get", "namespaces", "-o", "name"]).stdout.strip().split("\n")
    namespaces = [n for n in namespaces if n]

    if namespaces:
        namespaces_dir = backup_path / "namespaces"
        namespaces_dir.mkdir(parents=True, exist_ok=True)

        for ns_obj in namespaces:
            ns = ns_obj.replace("namespace/", "")
            ns_dir = namespaces_dir / ns
            ns_dir.mkdir(parents=True, exist_ok=True)

            for resource in ["deployments", "services", "configmaps", "secrets", "pvc", "ingress", "statefulsets", "daemonsets"]:
                result = run_cmd(["kubectl", "get", resource, "-n", ns, "-o", "yaml"])
                if result.stdout:
                    (ns_dir / f"{resource}.yaml").write_text(result.stdout)

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
        volumes_result = run_cmd(["kubectl", "get", "volumes.longhorn.io", "-A", "-o", "jsonpath={.items[*].metadata.name}"])
        volumes = volumes_result.stdout.strip().split()
        if volumes and volumes[0]:
            (backup_path / "longhorn_volumes").write_text("\n".join(volumes))
            
            if keep_last and int(keep_last) > 0:
                prune_longhorn_snapshots(int(keep_last))
    except Exception:
        pass

    tar_path = BACKUP_ROOT / f"{name}.tar.gz"
    with tarfile.open(tar_path, "w:gz") as tar:
        tar.add(backup_path, arcname=name)

    shutil.rmtree(backup_path)

    if encrypt:
        tar_path = encrypt_backup(tar_path, passphrase)
        if tar_path:
            print(f"🔐 Backup encrypted: {tar_path}")
        else:
            print("⚠️  Encryption failed, keeping unencrypted backup")

    print(f"✅ Backup saved: {tar_path}")
    return str(tar_path)


def encrypt_backup(tar_path, passphrase=None):
    if passphrase is None:
        passphrase = os.environ.get("PRIVATECLOUD_BACKUP_PASS", "")
    
    if not passphrase:
        print("⚠️  No passphrase provided. Set PRIVATECLOUD_BACKUP_PASS env var or use --passphrase")
        return None

    age_path = shutil.which("age")
    if not age_path:
        age_path = shutil.which("age-keygen")
    
    if not age_path:
        print("⚠️  age not found. Install from https://github.com/FiloSottile/age")
        return None

    encrypted_path = Path(str(tar_path) + ".age")
    result = run_cmd([
        "age", "--passphrase", "--output", str(encrypted_path), str(tar_path)
    ], check=False)
    
    if result.returncode == 0:
        tar_path.unlink()
        return str(encrypted_path)
    
    print(f"⚠️  Encryption failed: {result.stderr}")
    return None


def decrypt_backup(backup_path, passphrase=None):
    if passphrase is None:
        passphrase = os.environ.get("PRIVATECLOUD_BACKUP_PASS", "")
    
    if not passphrase:
        return None, None

    if not backup_path.endswith(".age"):
        return backup_path, None

    encrypted_path = Path(backup_path)
    temp_path = BACKUP_ROOT / encrypted_path.stem

    result = run_cmd([
        "age", "--decrypt", "--passphrase", "--output", str(temp_path), str(encrypted_path)
    ], check=False, timeout=120)

    if result.returncode == 0:
        return str(temp_path), str(temp_path)
    
    print(f"⚠️  Decryption failed: {result.stderr}")
    return None, None


def prune_longhorn_snapshots(keep_last=5):
    print(f"🧹 Pruning Longhorn snapshots (keeping {keep_last})...")
    
    result = run_cmd(["kubectl", "get", "snapshots.longhorn.io", "-n", "longhorn-system", "-o", "json"])
    if result.returncode != 0:
        print("⚠️  Could not access Longhorn snapshots")
        return

    try:
        data = json.loads(result.stdout)
        snapshots = data.get("items", [])
        
        by_volume = {}
        for snap in snapshots:
            vol = snap.get("spec", {}).get("volumeName", "unknown")
            by_volume.setdefault(vol, []).append(snap)

        for vol, snaps in by_volume.items():
            sorted_snaps = sorted(snaps, key=lambda s: s.get("metadata", {}).get("creationTimestamp", ""), reverse=True)
            for snap in sorted_snaps[keep_last:]:
                name = snap["metadata"]["name"]
                print(f"  Deleting snapshot: {name}")
                run_cmd(["kubectl", "delete", "snapshots.longhorn.io", name, "-n", "longhorn-system"])
    except json.JSONDecodeError:
        print("⚠️  Could not parse Longhorn snapshots")


def verify_backup(backup_name, passphrase=None):
    print(f"🔍 Verifying backup: {backup_name}")
    
    backup_path = BACKUP_ROOT / backup_name
    if not backup_path.exists():
        backup_path = BACKUP_ROOT / f"{backup_name}.tar.gz"
    if not backup_path.exists():
        backup_path = BACKUP_ROOT / f"{backup_name}.tar.gz.age"
    
    if not backup_path.exists():
        print(f"❌ Backup {backup_name} not found")
        return False

    tar_path, temp_file = decrypt_backup(str(backup_path), passphrase)
    if not tar_path:
        print("❌ Backup is encrypted and decryption failed")
        return False

    extract_path = BACKUP_ROOT / f"verify_temp_{datetime.datetime.now().strftime('%Y%m%d_%H%M%S')}"
    extract_path.mkdir(parents=True, exist_ok=True)

    try:
        with tarfile.open(tar_path, "r:gz") as tar:
            tar.extractall(extract_path)

        errors = []
        for item in extract_path.rglob("*.yaml"):
            rel_path = item.relative_to(extract_path)
            result = run_cmd(["kubectl", "diff", "-f", str(item)], check=False)
            if result.returncode != 0 and "No kind" not in result.stderr:
                errors.append(f"{rel_path}: {result.stderr[:200]}")
        
        if errors:
            print("⚠️  Verification found issues:")
            for e in errors[:10]:
                print(f"  - {e}")
            return False
        else:
            print("✅ Backup verified successfully")
            return True
    finally:
        if extract_path.exists():
            shutil.rmtree(extract_path)
        if temp_file and Path(temp_file).exists():
            Path(temp_file).unlink()


def list_backups():
    ensure_backup_dir()
    backups = sorted(BACKUP_ROOT.glob("*.tar.gz"), key=os.path.getmtime, reverse=True)
    encrypted = sorted(BACKUP_ROOT.glob("*.tar.gz.age"), key=os.path.getmtime, reverse=True)
    all_backups = sorted(set(backups + encrypted), key=os.path.getmtime, reverse=True)
    return [{"name": b.name, "size": os.path.getsize(b) // 1024, "encrypted": b.suffix == ".age"} for b in all_backups]


def restore_backup(backup_name, force=False, dry_run=False, passphrase=None):
    print(f"🔄 Restoring from: {backup_name}")
    
    backup_path = BACKUP_ROOT / backup_name
    if not backup_path.exists():
        backup_path = BACKUP_ROOT / f"{backup_name}.tar.gz"
    if not backup_path.exists():
        backup_path = BACKUP_ROOT / f"{backup_name}.tar.gz.age"
    
    if not backup_path.exists():
        print(f"❌ Backup {backup_name} not found")
        return False

    tar_path, temp_file = decrypt_backup(str(backup_path), passphrase)
    if not tar_path:
        print("❌ Backup is encrypted and decryption failed. Set PRIVATECLOUD_BACKUP_PASS env var.")
        return False

    extract_path = BACKUP_ROOT / "restore_temp"
    if extract_path.exists():
        shutil.rmtree(extract_path)
    extract_path.mkdir(parents=True, exist_ok=True)

    try:
        with tarfile.open(tar_path, "r:gz") as tar:
            tar.extractall(extract_path)

        backup_dir_name = backup_name.replace(".tar.gz", "").replace(".tar.gz.age", "")
        extract_dir = extract_path / backup_dir_name

        if not extract_dir.exists():
            for item in extract_path.iterdir():
                if item.is_dir():
                    extract_dir = item
                    break

        if dry_run:
            print("📋 [DRY RUN] Would restore the following resources:")
            for item in extract_dir.rglob("*.yaml"):
                rel = item.relative_to(extract_dir)
                print(f"  - {rel}")
            print("\nWould run kubectl diff for each:")
            for item in extract_dir.rglob("*.yaml"):
                result = run_cmd(["kubectl", "diff", "-f", str(item)], check=False)
                if result.stdout:
                    print(f"  Diff for {item.name}:")
                    for line in result.stdout.split("\n")[:10]:
                        print(f"    {line}")
            return True

        ns_dir = extract_dir / "namespaces"
        if ns_dir.exists():
            for ns_folder in ns_dir.iterdir():
                if ns_folder.is_dir():
                    ns = ns_folder.name
                    run_cmd(["kubectl", "create", "ns", ns], check=False)
                    for manifest in ns_folder.glob("*.yaml"):
                        cmd = ["kubectl", "replace", "--force", "-f", str(manifest)] if force else ["kubectl", "apply", "-f", str(manifest)]
                        if dry_run:
                            print(f"  [DRY RUN] {' '.join(cmd)}")
                        else:
                            run_cmd(cmd, check=False)

        tf_state = extract_dir / "terraform_state"
        if tf_state.exists():
            tf_dir = Path("terraform")
            tf_dir.mkdir(exist_ok=True)
            tf_dir.joinpath("terraform.tfstate").write_text(tf_state.read_text())
            print("✅ Terraform state restored")

        print("🎉 Restore complete")
        return True
    finally:
        if extract_path.exists():
            shutil.rmtree(extract_path)
        if temp_file and Path(temp_file).exists():
            Path(temp_file).unlink()


def delete_backup(backup_name):
    backup_tar = BACKUP_ROOT / backup_name
    if not backup_tar.exists():
        backup_tar = BACKUP_ROOT / f"{backup_name}.tar.gz"
    if not backup_tar.exists():
        backup_tar = BACKUP_ROOT / f"{backup_name}.tar.gz.age"
    if backup_tar.exists():
        backup_tar.unlink()
        return True
    return False


def pre_destroy_backup():
    tf_state = Path("terraform/terraform.tfstate")
    if tf_state.exists():
        timestamp = datetime.datetime.now().strftime("%Y%m%d_%H%M%S")
        backup_dir = BACKUP_ROOT / f"pre_destroy_{timestamp}"
        backup_dir.mkdir(parents=True, exist_ok=True)
        shutil.copy(tf_state, backup_dir / "terraform.tfstate")
        
        config = Path("privatecloud.yaml")
        if config.exists():
            shutil.copy(config, backup_dir / "privatecloud.yaml")
        
        print(f"⚠️  Pre-destroy backup saved to: {backup_dir}")
        return str(backup_dir)
    return None