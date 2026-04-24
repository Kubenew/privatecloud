import yaml
from pathlib import Path
from .config import PrivateCloudConfig


def load_config(path: str = "privatecloud.yaml") -> PrivateCloudConfig:
    """Load and validate the PrivateCloud configuration file."""
    p = Path(path)
    if not p.exists():
        raise FileNotFoundError("privatecloud.yaml not found. Run: privatecloud init")

    data = yaml.safe_load(p.read_text(encoding="utf-8"))
    return PrivateCloudConfig.model_validate(data)


def save_config(config: PrivateCloudConfig, path: str = "privatecloud.yaml"):
    """Write the current configuration back to disk (e.g. after Terraform auto-write)."""
    data = config.model_dump(exclude_none=True)
    with open(path, "w", encoding="utf-8") as f:
        yaml.safe_dump(data, f, sort_keys=False)


def save_default_config(path: str = "privatecloud.yaml"):
    """Generate a starter configuration file with sensible defaults."""
    default = {
        "cluster_name": "my-private-cloud",
        "provider": "bare-metal",
        "k3s_version": "v1.29.0+k3s1",
        "nodes": [
            {"host": "192.168.1.10", "user": "root", "role": "master"},
            {"host": "192.168.1.11", "user": "root", "role": "worker"},
        ],
        "proxmox": {
            "url": "https://192.168.1.100:8006/api2/json",
            "token_id": "root@pam!mytoken",
            "token_secret": "your-secret-here",
            "node": "pve",
            "template": "ubuntu-2204-template",
            "master_count": 1,
            "worker_count": 2,
            "storage": "local-lvm",
            "bridge": "vmbr0",
        },
        "services": {
            "metallb": True,
            "ingress_nginx": True,
            "cert_manager": True,
            "monitoring": True,
            "longhorn": True,
        }
    }

    with open(path, "w", encoding="utf-8") as f:
        yaml.safe_dump(default, f, sort_keys=False)
