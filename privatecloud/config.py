from pydantic import BaseModel, Field, field_validator
from typing import List, Optional, Dict, Literal

SUPPORTED_PROVIDERS = ("bare-metal", "proxmox")


class NodeConfig(BaseModel):
    host: str
    user: str = "root"
    port: int = 22
    role: str = "worker"


class ServicesConfig(BaseModel):
    metallb: bool = True
    ingress_nginx: bool = True
    cert_manager: bool = True
    monitoring: bool = True
    longhorn: bool = True


class ProxmoxConfig(BaseModel):
    url: str = "https://192.168.1.100:8006/api2/json"
    token_id: str = "root@pam!mytoken"
    token_secret: str = "your-secret-here"
    node: str = "pve"
    template: str = "ubuntu-2204-template"
    master_count: int = 1
    worker_count: int = 2
    storage: str = "local-lvm"
    bridge: str = "vmbr0"
    master_cores: int = 2
    master_memory: int = 2048
    master_disk: str = "20G"
    worker_cores: int = 2
    worker_memory: int = 4096
    worker_disk: str = "40G"


class PrivateCloudConfig(BaseModel):
    cluster_name: str = "my-private-cloud"
    provider: str = "bare-metal"
    k3s_version: str = "v1.29.0+k3s1"

    nodes: List[NodeConfig] = Field(default_factory=list)
    proxmox: Optional[ProxmoxConfig] = None
    services: ServicesConfig = Field(default_factory=ServicesConfig)

    ssh_key_path: Optional[str] = None
    extra_env: Dict[str, str] = Field(default_factory=dict)

    @field_validator("provider")
    @classmethod
    def validate_provider(cls, v: str) -> str:
        if v not in SUPPORTED_PROVIDERS:
            raise ValueError(f"Unsupported provider '{v}'. Supported: {', '.join(SUPPORTED_PROVIDERS)}")
        return v

