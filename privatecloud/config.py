from pydantic import BaseModel, Field
from typing import List, Optional, Dict


class NodeConfig(BaseModel):
    host: str
    user: str = "root"
    port: int = 22


class ServicesConfig(BaseModel):
    metallb: bool = True
    ingress_nginx: bool = True
    cert_manager: bool = True
    monitoring: bool = True
    longhorn: bool = True


class PrivateCloudConfig(BaseModel):
    cluster_name: str = "my-private-cloud"
    k3s_version: str = "v1.29.0+k3s1"

    nodes: List[NodeConfig] = Field(default_factory=list)
    services: ServicesConfig = Field(default_factory=ServicesConfig)

    ssh_key_path: Optional[str] = None
    extra_env: Dict[str, str] = Field(default_factory=dict)
