import os
import yaml
import subprocess
from pathlib import Path
from typing import List, Dict, Optional
from pydantic import BaseModel


class ExternalDBConfig(BaseModel):
    type: str
    host: str
    port: int = 2379
    username: Optional[str] = None
    password_env: Optional[str] = None
    ca_cert: Optional[str] = None
    client_cert: Optional[str] = None
    client_key: Optional[str] = None


SUPPORTED_DATABASES = ["postgresql", "etcd", "mysql"]


def detect_existing_db() -> Optional[Dict]:
    result = run_cmd(["kubectl", "get", "pods", "-A", "-o", "json"])
    if result.returncode != 0:
        return None
    
    import json
    data = json.loads(result.stdout)
    pods = [p['metadata']['name'] for p in data.get('items', [])]
    
    db_indicators = {
        'postgresql': ['postgres', 'postgresql', 'pg'],
        'etcd': ['etcd'],
        'mysql': ['mysql', 'mariadb'],
    }
    
    for db_type, indicators in db_indicators.items():
        if any(ind in ' '.join(pods).lower() for ind in indicators):
            return {'type': db_type, 'detected': True}
    
    return None


def get_ha_install_script(
    master_count: int = 3,
    db_type: str = "embedded",
    db_config: Optional[ExternalDBConfig] = None,
    k3s_version: str = "v1.29.0+k3s1"
) -> str:
    
    if db_type == "embedded":
        install_script = f'''#!/bin/bash
# HA K3s Installation with Embedded etcd
# {master_count} master nodes for HA

curl -sfL https://get.k3s.io | INSTALL_K3S_VERSION={k3s_version} sh - server \\
  --cluster-init \\
  --token=K3S_CLUSTER_TOKEN \\
  --kubelet-arg="eviction-hard=memory.available<500Mi" \\
  --node-arg=--kube-reserved=cpu=100m,memory=256Mi \\
  --disable=traefik
'''
    else:
        db_env_vars = []
        if db_config:
            if db_config.password_env:
                db_env_vars.append(f'  --env="K3S_{db_type.upper()}_PASSWORD=${{{db_config.password_env}}}"')
            if db_config.ca_cert:
                db_env_vars.append(f'  --tls-san={db_config.host}')
        
        install_script = f'''#!/bin/bash
# HA K3s Installation with External {db_type.upper()}
# {master_count} master nodes for HA

curl -sfL https://get.k3s.io | INSTALL_K3S_VERSION={k3s_version} sh - server \\
  --server https://{db_config.host if db_config else "DB_HOST"}:{db_config.port if db_config else 5432}/k3s \\
  --token=K3S_CLUSTER_TOKEN \\
  --kubelet-arg="eviction-hard=memory.available<500Mi" \\
  --disable=traefik
  {" ".join(db_env_vars)}
'''
    
    return install_script


def get_worker_join_script(master_ip: str, token: str) -> str:
    return f'''#!/bin/bash
# Worker Node Join Script
curl -sfL https://get.k3s.io | K3S_URL=https://{master_ip}:6443 K3S_TOKEN={token} sh -
'''


def create_ha_config(
    output_dir: Path,
    master_ips: List[str],
    worker_ips: List[str],
    db_config: Optional[ExternalDBConfig] = None,
    k3s_version: str = "v1.29.0+k3s1"
) -> Dict[str, Path]:
    
    output_dir.mkdir(parents=True, exist_ok=True)
    files = {}
    
    cluster_token = f"k3s-cluster-{os.urandom(16).hex()}"
    
    if db_config is None:
        db_type = "embedded"
    else:
        db_type = db_config.type
    
    install_script = get_ha_install_script(
        master_count=len(master_ips),
        db_type=db_type,
        db_config=db_config,
        k3s_version=k3s_version
    )
    
    master_script = output_dir / "install-masters.sh"
    master_script.write_text(install_script)
    master_script.chmod(0o755)
    files['masters'] = master_script
    
    worker_script = output_dir / "join-workers.sh"
    worker_script.write_text(get_worker_join_script(master_ips[0], cluster_token))
    worker_script.chmod(0o755)
    files['workers'] = worker_script
    
    ha_config = {
        'ha': True,
        'master_count': len(master_ips),
        'worker_count': len(worker_ips),
        'db_type': db_type,
        'k3s_version': k3s_version,
        'cluster_token': cluster_token,
        'masters': [{'ip': ip, 'name': f'master-{i}'} for i, ip in enumerate(master_ips)],
        'workers': [{'ip': ip, 'name': f'worker-{i}'} for i, ip in enumerate(worker_ips)],
    }
    
    if db_config:
        ha_config['external_db'] = {
            'type': db_config.type,
            'host': db_config.host,
            'port': db_config.port,
        }
    
    config_file = output_dir / "ha-config.yaml"
    with open(config_file, 'w') as f:
        yaml.dump(ha_config, f)
    files['config'] = config_file
    
    return files


def validate_ha_setup(master_count: int, db_type: str) -> List[str]:
    warnings = []
    
    if master_count < 3 and db_type == "embedded":
        warnings.append("HA with embedded etcd requires at least 3 masters")
    
    if master_count < 2:
        warnings.append("For HA, use at least 2 master nodes")
    
    return warnings


def get_cluster_health_ha() -> Dict:
    result = run_cmd(["kubectl", "get", "nodes", "-o", "json"])
    if result.returncode != 0:
        return {'healthy': False, 'error': 'Cannot connect to cluster'}
    
    import json
    data = json.loads(result.stdout)
    nodes = data.get('items', [])
    
    masters = [n for n in nodes if n.get('metadata', {}).get('labels', {}).get('node-role.kubernetes.io/master')]
    workers = [n for n in nodes if n not in masters]
    
    ready_masters = sum(1 for n in masters if is_node_ready(n))
    ready_workers = sum(1 for n in workers if is_node_ready(n))
    
    return {
        'healthy': ready_masters >= 2,
        'masters': {'total': len(masters), 'ready': ready_masters},
        'workers': {'total': len(workers), 'ready': ready_workers},
        'ha_status': 'active' if ready_masters >= 2 else 'degraded',
    }


def is_node_ready(node: dict) -> bool:
    return any(
        c.get('type') == 'Ready' and c.get('status') == 'True'
        for c in node.get('status', {}).get('conditions', [])
    )


def run_cmd(cmd, timeout=30):
    try:
        return subprocess.run(cmd, capture_output=True, text=True, timeout=timeout, check=False)
    except Exception as e:
        return type('obj', (object,), {'returncode': 1, 'stdout': '', 'stderr': str(e)})()