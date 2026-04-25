import subprocess
import json
import time
import yaml
from pathlib import Path
from typing import List, Dict, Optional
from datetime import datetime, timedelta


def run_cmd(cmd, timeout=60):
    try:
        return subprocess.run(cmd, capture_output=True, text=True, timeout=timeout, check=False)
    except Exception as e:
        return type('obj', (object,), {'returncode': 1, 'stdout': '', 'stderr': str(e)})()


def check_longhorn_available() -> bool:
    result = run_cmd(["kubectl", "get", "crd", "volumes.longhorn.io"])
    return result.returncode == 0


def get_volumes() -> List[Dict]:
    result = run_cmd(["kubectl", "get", "volumes.longhorn.io", "-A", "-o", "json"])
    if result.returncode != 0:
        return []
    
    try:
        data = json.loads(result.stdout)
        volumes = []
        for item in data.get('items', []):
            volumes.append({
                'name': item['metadata']['name'],
                'namespace': item['metadata']['namespace'],
                'size': item.get('status', {}).get('size', 'unknown'),
                'state': item.get('status', {}).get('state', 'unknown'),
                'frontend': item.get('spec', {}).get('frontend', 'blockdev'),
                'created': item['metadata'].get('creationTimestamp', ''),
            })
        return volumes
    except Exception:
        return []


def get_snapshots(volume_name: str, namespace: str = "longhorn-system") -> List[Dict]:
    result = run_cmd([
        "kubectl", "get", "snapshots.longhorn.io",
        "-n", namespace,
        "-o", "json"
    ])
    
    if result.returncode != 0:
        return []
    
    try:
        data = json.loads(result.stdout)
        snapshots = []
        for item in data.get('items', []):
            if item.get('spec', {}).get('volumeName') == volume_name:
                snapshots.append({
                    'name': item['metadata']['name'],
                    'created': item['metadata'].get('creationTimestamp', ''),
                    'ready': item.get('status', {}).get('ready', True),
                    'size': item.get('status', {}).get('size', 'unknown'),
                })
        return sorted(snapshots, key=lambda s: s['created'], reverse=True)
    except Exception:
        return []


def create_volume_snapshot(volume_name: str, namespace: str = "longhorn-system") -> Optional[str]:
    snapshot_name = f"snapshot-{volume_name}-{datetime.now().strftime('%Y%m%d-%H%M%S')}"
    
    manifest = {
        'apiVersion': 'longhorn.io/v1beta2',
        'kind': 'Snapshot',
        'metadata': {
            'name': snapshot_name,
            'namespace': namespace,
        },
        'spec': {
            'volumeName': volume_name,
        }
    }
    
    manifest_yaml = yaml.dump(manifest)
    
    proc = subprocess.Popen(
        ["kubectl", "apply", "-f", "-"],
        stdin=subprocess.PIPE,
        stdout=subprocess.PIPE,
        stderr=subprocess.PIPE,
        text=True
    )
    stdout, stderr = proc.communicate(input=manifest_yaml, timeout=30)
    
    if proc.returncode == 0:
        print(f"✅ Created snapshot: {snapshot_name}")
        return snapshot_name
    else:
        print(f"❌ Failed to create snapshot: {stderr}")
        return None


def restore_from_snapshot(
    volume_name: str,
    snapshot_name: str,
    new_volume_name: Optional[str] = None,
    namespace: str = "longhorn-system"
) -> bool:
    if new_volume_name is None:
        new_volume_name = f"{volume_name}-restored-{datetime.now().strftime('%Y%m%d')}"
    
    manifest = {
        'apiVersion': 'longhorn.io/v1beta2',
        'kind': 'Volume',
        'metadata': {
            'name': new_volume_name,
            'namespace': namespace,
        },
        'spec': {
            'volume': volume_name,
            'fromBackup': f'',
            'restoreVolume': volume_name,
            'restoreVolumeRecurringJob': 'ignored',
        }
    }
    
    result = run_cmd([
        "kubectl", "get", "volumes.longhorn.io", snapshot_name, "-n", namespace, "-o", "json"
    ])
    
    if result.returncode != 0:
        print("❌ Snapshot not found")
        return False
    
    print(f"⚠️  Restoring volume '{new_volume_name}' from snapshot '{snapshot_name}'")
    print("⚠️  This may take several minutes...")
    
    proc = subprocess.Popen(
        ["kubectl", "create", "-f", "-"],
        stdin=subprocess.PIPE,
        stdout=subprocess.PIPE,
        stderr=subprocess.PIPE,
        text=True
    )
    stdout, stderr = proc.communicate(input=yaml.dump(manifest), timeout=30)
    
    if proc.returncode == 0:
        print(f"✅ Restore initiated: {new_volume_name}")
        return True
    else:
        print(f"❌ Restore failed: {stderr}")
        return False


def delete_old_snapshots(volume_name: str, keep_last: int = 5, namespace: str = "longhorn-system") -> int:
    snapshots = get_snapshots(volume_name, namespace)
    
    if len(snapshots) <= keep_last:
        print(f"Only {len(snapshots)} snapshots, none to delete")
        return 0
    
    deleted = 0
    for snapshot in snapshots[keep_last:]:
        result = run_cmd([
            "kubectl", "delete", "snapshots.longhorn.io",
            snapshot['name'], "-n", namespace
        ], timeout=30)
        
        if result.returncode == 0:
            deleted += 1
            print(f"Deleted snapshot: {snapshot['name']}")
        else:
            print(f"Failed to delete {snapshot['name']}")
    
    return deleted


def get_volume_backup_info(volume_name: str, namespace: str = "longhorn-system") -> Dict:
    result = run_cmd([
        "kubectl", "get", "backups.longhorn.io",
        "-n", namespace, "-o", "json"
    ])
    
    backups = []
    if result.returncode == 0:
        try:
            data = json.loads(result.stdout)
            backups = [
                {
                    'name': b['metadata']['name'],
                    'snapshot': b['status'].get('snapshot', ''),
                    'size': b['status'].get('size', ''),
                    'created': b['metadata'].get('creationTimestamp', ''),
                }
                for b in data.get('items', [])
                if b.get('spec', {}).get('volumeName') == volume_name
            ]
        except Exception:
            pass
    
    return {
        'volume': volume_name,
        'namespace': namespace,
        'backups': backups,
    }


def create_pvc_from_snapshot(
    snapshot_name: str,
    pvc_name: str,
    namespace: str = "default",
    storage_class: str = "longhorn"
) -> bool:
    manifest = {
        'apiVersion': 'v1',
        'kind': 'PersistentVolumeClaim',
        'metadata': {
            'name': pvc_name,
            'namespace': namespace,
        },
        'spec': {
            'storageClassName': storage_class,
            'accessModes': ['ReadWriteOnce'],
            'resources': {
                'requests': {
                    'storage': '10Gi'
                }
            },
            'dataSource': {
                'name': snapshot_name,
                'kind': 'Snapshot',
                'apiGroup': 'longhorn.io'
            }
        }
    }
    
    proc = subprocess.Popen(
        ["kubectl", "apply", "-f", "-"],
        stdin=subprocess.PIPE,
        stdout=subprocess.PIPE,
        stderr=subprocess.PIPE,
        text=True
    )
    stdout, stderr = proc.communicate(input=yaml.dump(manifest), timeout=30)
    
    if proc.returncode == 0:
        print(f"✅ PVC created: {pvc_name}")
        return True
    else:
        print(f"❌ Failed to create PVC: {stderr}")
        return False


def monitor_restore_progress(volume_name: str, timeout: int = 600) -> bool:
    print(f"Monitoring restore progress for {volume_name}...")
    
    start_time = time.time()
    last_state = None
    
    while time.time() - start_time < timeout:
        result = run_cmd([
            "kubectl", "get", "volumes.longhorn.io", volume_name,
            "-n", "longhorn-system", "-o", "json"
        ], timeout=10)
        
        if result.returncode == 0:
            try:
                data = json.loads(result.stdout)
                state = data.get('status', {}).get('state', 'unknown')
                
                if state != last_state:
                    print(f"State: {state}")
                    last_state = state
                
                if state == 'attached':
                    print(f"✅ Volume {volume_name} restored successfully!")
                    return True
                
                if state == 'failed':
                    print(f"❌ Restore failed")
                    return False
            except Exception:
                pass
        
        time.sleep(10)
    
    print(f"⏱️  Restore timed out after {timeout}s")
    return False


def list_snapshots_with_volumes() -> List[Dict]:
    result = run_cmd(["kubectl", "get", "volumes.longhorn.io", "-A", "-o", "json"])
    if result.returncode != 0:
        return []
    
    try:
        data = json.loads(result.stdout)
        volume_snapshots = []
        
        for vol in data.get('items', []):
            vol_name = vol['metadata']['name']
            vol_ns = vol['metadata']['namespace']
            snapshots = get_snapshots(vol_name, vol_ns)
            
            volume_snapshots.append({
                'volume': vol_name,
                'namespace': vol_ns,
                'state': vol.get('status', {}).get('state', 'unknown'),
                'snapshots': snapshots,
                'snapshot_count': len(snapshots),
            })
        
        return volume_snapshots
    except Exception:
        return []