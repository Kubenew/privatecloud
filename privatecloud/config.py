from pydantic import BaseModel, Field, field_validator
from typing import List, Optional, Dict, Literal

SUPPORTED_PROVIDERS = ("bare-metal", "proxmox", "morpheus")
SUPPORTED_CLOUD_TYPES = ("vmware", "aws", "azure", "gcp", "hvm", "openstack")


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


class MorpheusConfig(BaseModel):
    url: str = "https://morpheus.example.com"
    username: str = "admin"
    password: str = "${MORPHEUS_PASSWORD}"
    insecure: bool = True

    # Morpheus resource names
    group_name: str = "My Group"
    cloud_name: str = "My Cloud"
    instance_type_name: str = "Ubuntu"
    layout_name: str = "VMware VM"
    plan_name: str = "1 CPU, 2GB Memory"

    master_count: int = Field(default=1, ge=1)
    worker_count: int = Field(default=2, ge=0)

    # Cloud type for the Terraform config block (e.g. config_vmware {})
    cloud_type: str = "vmware"

    ssh_user: str = "cloud-user"

    @field_validator("cloud_type")
    @classmethod
    def validate_cloud_type(cls, v: str) -> str:
        if v not in SUPPORTED_CLOUD_TYPES:
            raise ValueError(
                f"Unsupported cloud_type '{v}'. "
                f"Supported: {', '.join(SUPPORTED_CLOUD_TYPES)}"
            )
        return v


class PrivateCloudConfig(BaseModel):
    cluster_name: str = "my-private-cloud"
    provider: str = "bare-metal"
    k3s_version: str = "v1.29.0+k3s1"
    terraform_dir: str = "."

    nodes: List[NodeConfig] = Field(default_factory=list)
    proxmox: Optional[ProxmoxConfig] = None
    morpheus: Optional[MorpheusConfig] = None
    services: ServicesConfig = Field(default_factory=ServicesConfig)

    ssh_key_path: Optional[str] = None
    extra_env: Dict[str, str] = Field(default_factory=dict)

    @field_validator("provider")
    @classmethod
    def validate_provider(cls, v: str) -> str:
        if v not in SUPPORTED_PROVIDERS:
            raise ValueError(f"Unsupported provider '{v}'. Supported: {', '.join(SUPPORTED_PROVIDERS)}")
        return v

