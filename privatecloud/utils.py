import yaml
from pathlib import Path
from .config import PrivateCloudConfig


def load_config(path: str = "privatecloud.yaml") -> PrivateCloudConfig:
    p = Path(path)
    if not p.exists():
        raise FileNotFoundError("privatecloud.yaml not found. Run: privatecloud init")

    data = yaml.safe_load(p.read_text(encoding="utf-8"))
    return PrivateCloudConfig.model_validate(data)


def save_default_config(path: str = "privatecloud.yaml"):
    default = {
        "cluster_name": "my-private-cloud",
        "k3s_version": "v1.29.0+k3s1",
        "nodes": [
            {"host": "192.168.1.10", "user": "root"},
            {"host": "192.168.1.11", "user": "root"},
        ],
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
