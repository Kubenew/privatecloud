import subprocess
import json
from typing import Dict, List, Optional
from datetime import datetime


def run_cmd(cmd, timeout=30):
    try:
        result = subprocess.run(
            cmd,
            capture_output=True,
            text=True,
            timeout=timeout,
            check=False
        )
        return result
    except Exception as e:
        return type('obj', (object,), {'returncode': 1, 'stdout': '', 'stderr': str(e)})()


def get_node_metrics() -> List[Dict]:
    result = run_cmd([
        "kubectl", "get", "nodes", "-o", "json",
        "--raw=/api/v1/nodes"
    ])
    
    if result.returncode != 0:
        result = run_cmd(["kubectl", "get", "nodes", "-o", "json"])
    
    if result.returncode != 0:
        return []
    
    try:
        data = json.loads(result.stdout)
        nodes = []
        
        for item in data.get('items', []):
            name = item['metadata']['name']
            allocatable = item['status'].get('allocatable', {})
            capacity = item['status'].get('capacity', {})
            
            cpu_capacity = int(capacity.get('cpu', '0'))
            cpu_allocatable = int(allocatable.get('cpu', '0'))
            mem_capacity = int(allocatable.get('memory', '0').rstrip('Ki')) // 1024 // 1024
            
            conditions = item['status'].get('conditions', [])
            ready = any(c.get('type') == 'Ready' and c.get('status') == 'True' for c in conditions)
            
            nodes.append({
                'name': name,
                'ready': ready,
                'cpu_cores': cpu_allocatable,
                'memory_gb': mem_capacity,
            })
        return nodes
    except Exception:
        return []


def get_pod_metrics() -> List[Dict]:
    result = run_cmd([
        "kubectl", "get", "pods", "--all-namespaces", "-o", "json"
    ], timeout=30)
    
    if result.returncode != 0:
        return []
    
    try:
        data = json.loads(result.stdout)
        pods = []
        
        for item in data.get('items', []):
            ns = item['metadata']['namespace']
            name = item['metadata']['name']
            phase = item['status'].get('phase', 'Unknown')
            restart_count = sum(
                c.get('restartCount', 0) 
                for c in item['status'].get('containerStatuses', [])
            )
            
            pods.append({
                'namespace': ns,
                'name': name,
                'phase': phase,
                'restarts': restart_count,
            })
        return pods
    except Exception:
        return []


def get_longhorn_metrics() -> Dict:
    result = run_cmd([
        "kubectl", "get", "volumes.longhorn.io", "-A", "-o", "json"
    ], timeout=30)
    
    if result.returncode != 0:
        return {'available': False, 'volumes': 0, 'healthy': 0, 'degraded': 0}
    
    try:
        data = json.loads(result.stdout)
        volumes = data.get('items', [])
        
        healthy = sum(1 for v in volumes if v.get('status', {}).get('state') == 'Healthy')
        degraded = sum(1 for v in volumes if v.get('status', {}).get('state') == 'Degraded')
        
        return {
            'available': True,
            'volumes': len(volumes),
            'healthy': healthy,
            'degraded': degraded,
        }
    except Exception:
        return {'available': False, 'volumes': 0, 'healthy': 0, 'degraded': 0}


def get_cert_expiry() -> List[Dict]:
    result = run_cmd([
        "kubectl", "get", "certificates", "-A", "-o", "json"
    ], timeout=30)
    
    if result.returncode != 0:
        return []
    
    try:
        data = json.loads(result.stdout)
        certs = []
        
        for item in data.get('items', []):
            name = item['metadata']['name']
            ns = item['metadata']['namespace']
            not_after = item['status'].get('notAfter', '')
            
            if not_after:
                try:
                    from datetime import datetime
                    expiry = datetime.fromisoformat(not_after.replace('Z', '+00:00'))
                    days_left = (expiry - datetime.now()).days
                    certs.append({
                        'name': name,
                        'namespace': ns,
                        'expires': not_after[:10],
                        'days_left': days_left,
                        'warning': days_left < 30,
                    })
                except Exception:
                    pass
        
        return certs
    except Exception:
        return []


def get_cluster_summary() -> Dict:
    node_metrics = get_node_metrics()
    pod_metrics = get_pod_metrics()
    longhorn_metrics = get_longhorn_metrics()
    
    total_pods = len(pod_metrics)
    running_pods = sum(1 for p in pod_metrics if p['phase'] == 'Running')
    crashed_pods = sum(1 for p in pod_metrics if p['phase'] in ['Failed', 'Unknown'])
    high_restart_pods = sum(1 for p in pod_metrics if p['restarts'] > 5)
    
    return {
        'nodes': {
            'total': len(node_metrics),
            'ready': sum(1 for n in node_metrics if n['ready']),
            'items': node_metrics,
        },
        'pods': {
            'total': total_pods,
            'running': running_pods,
            'failed': crashed_pods,
            'high_restart': high_restart_pods,
            'items': pod_metrics[:50],
        },
        'longhorn': longhorn_metrics,
        'timestamp': datetime.now().isoformat(),
    }


def get_prometheus_metrics(prometheus_url: Optional[str] = None) -> Dict:
    if not prometheus_url:
        result = run_cmd(["kubectl", "get", "svc", "-n", "monitoring", "prometheus-operated", "-o", "jsonpath={.spec.clusterIP}"], timeout=10)
        if result.returncode == 0 and result.stdout.strip():
            prometheus_url = f"http://{result.stdout.strip()}:9090"
    
    if not prometheus_url:
        return {'available': False}
    
    try:
        import urllib.request
        import urllib.error
        
        query_url = f"{prometheus_url}/api/v1/query?query=up"
        with urllib.request.urlopen(query_url, timeout=10) as response:
            data = json.loads(response.read())
            return {
                'available': data.get('status') == 'success',
                'targets': len(data.get('data', {}).get('result', [])),
            }
    except Exception:
        return {'available': False}