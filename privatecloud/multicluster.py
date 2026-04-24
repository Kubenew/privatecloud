import os
import yaml
import subprocess
from pathlib import Path
from typing import Optional, List, Dict
from pydantic import BaseModel


class ClusterConfig(BaseModel):
    name: str
    kubeconfig: str
    context: Optional[str] = None
    provider: str = "unknown"
    current: bool = False


CLUSTERS_DIR = Path.home() / ".privatecloud" / "clusters"


def ensure_clusters_dir():
    CLUSTERS_DIR.mkdir(parents=True, exist_ok=True)


def get_clusters_dir():
    return CLUSTERS_DIR


def list_clusters() -> List[ClusterConfig]:
    ensure_clusters_dir()
    clusters = []
    
    for f in CLUSTERS_DIR.glob("*.yaml"):
        try:
            data = yaml.safe_load(f.read_text())
            clusters.append(ClusterConfig(**data))
        except Exception:
            pass
    
    return sorted(clusters, key=lambda c: (not c.current, c.name))


def get_current_cluster() -> Optional[ClusterConfig]:
    clusters = list_clusters()
    current = [c for c in clusters if c.current]
    return current[0] if current else None


def add_cluster(name: str, kubeconfig_path: str, context: Optional[str] = None, provider: str = "unknown") -> bool:
    ensure_clusters_dir()
    
    clusters = list_clusters()
    for c in clusters:
        if c.name == name:
            print(f"Cluster '{name}' already exists")
            return False
    
    kubeconfig_content = Path(kubeconfig_path).read_text()
    temp_kubeconfig = CLUSTERS_DIR / f"{name}.kubeconfig"
    temp_kubeconfig.write_text(kubeconfig_content)
    
    cluster = ClusterConfig(
        name=name,
        kubeconfig=str(temp_kubeconfig),
        context=context,
        provider=provider,
        current=False
    )
    
    cluster_file = CLUSTERS_DIR / f"{name}.yaml"
    with open(cluster_file, 'w') as f:
        yaml.dump(cluster.model_dump(), f)
    
    print(f"✅ Cluster '{name}' added")
    return True


def remove_cluster(name: str) -> bool:
    ensure_clusters_dir()
    
    cluster_file = CLUSTERS_DIR / f"{name}.yaml"
    kubeconfig_file = CLUSTERS_DIR / f"{name}.kubeconfig"
    
    if not cluster_file.exists():
        print(f"Cluster '{name}' not found")
        return False
    
    cluster = ClusterConfig.model_validate(yaml.safe_load(cluster_file.read_text()))
    
    if cluster.current:
        print("Cannot remove current cluster. Switch to another cluster first.")
        return False
    
    cluster_file.unlink()
    if kubeconfig_file.exists():
        kubeconfig_file.unlink()
    
    print(f"✅ Cluster '{name}' removed")
    return True


def switch_cluster(name: str) -> bool:
    ensure_clusters_dir()
    
    clusters = list_clusters()
    
    for cluster in clusters:
        is_current = cluster.name == name
        cluster.current = is_current
        
        cluster_file = CLUSTERS_DIR / f"{cluster.name}.yaml"
        with open(cluster_file, 'w') as f:
            yaml.dump(cluster.model_dump(), f)
    
    if name in [c.name for c in clusters]:
        os.environ['KUBECONFIG'] = str(CLUSTERS_DIR / f"{name}.kubeconfig")
        print(f"✅ Switched to cluster '{name}'")
        return True
    
    print(f"Cluster '{name}' not found")
    return False


def run_on_cluster(cluster_name: str, cmd: List[str], timeout: int = 30) -> subprocess.CompletedProcess:
    cluster_file = CLUSTERS_DIR / f"{cluster_name}.yaml"
    if not cluster_file.exists():
        raise FileNotFoundError(f"Cluster '{cluster_name}' not found")
    
    cluster = ClusterConfig.model_validate(yaml.safe_load(cluster_file.read_text()))
    kubeconfig = cluster.kubeconfig
    
    env = os.environ.copy()
    env['KUBECONFIG'] = kubeconfig
    
    return subprocess.run(
        cmd,
        env=env,
        capture_output=True,
        text=True,
        timeout=timeout
    )


def get_cluster_info(cluster_name: str) -> Optional[Dict]:
    try:
        result = run_on_cluster(cluster_name, ["kubectl", "cluster-info"], timeout=10)
        if result.returncode != 0:
            return None
        
        result = run_on_cluster(cluster_name, ["kubectl", "get", "nodes", "-o", "json"], timeout=15)
        if result.returncode != 0:
            return None
        
        import json
        data = json.loads(result.stdout)
        nodes = data.get('items', [])
        
        return {
            'name': cluster_name,
            'nodes': len(nodes),
            'ready': sum(1 for n in nodes if is_node_ready(n)),
            'status': 'connected',
        }
    except Exception as e:
        return {'name': cluster_name, 'status': 'error', 'error': str(e)}


def is_node_ready(node: dict) -> bool:
    return any(
        c.get('type') == 'Ready' and c.get('status') == 'True'
        for c in node.get('status', {}).get('conditions', [])
    )


def import_from_kubeconfig(kubeconfig_path: str, name: Optional[str] = None) -> bool:
    kubeconfig = Path(kubeconfig_path).read_text()
    
    try:
        data = yaml.safe_load(kubeconfig)
        contexts = data.get('contexts', [])
        
        if not name and contexts:
            name = contexts[0]['context'].get('cluster', 'imported')
        
        if not name:
            name = f"cluster-{len(list(CLUSTERS_DIR.glob('*.yaml'))) + 1}"
        
        add_cluster(name, kubeconfig_path, provider="imported")
        return True
    except Exception as e:
        print(f"Failed to import kubeconfig: {e}")
        return False


def export_cluster_config(cluster_name: str, export_path: str) -> bool:
    cluster_file = CLUSTERS_DIR / f"{cluster_name}.yaml"
    if not cluster_file.exists():
        print(f"Cluster '{cluster_name}' not found")
        return False
    
    cluster = ClusterConfig.model_validate(yaml.safe_load(cluster_file.read_text()))
    Path(export_path).write_text(Path(cluster.kubeconfig).read_text())
    
    print(f"✅ Exported cluster config to {export_path}")
    return True