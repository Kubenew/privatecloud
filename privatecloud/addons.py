import os
import subprocess
import yaml
from pathlib import Path
from typing import Dict, List, Optional
from enum import Enum


class AddonCategory(Enum):
    MONITORING = "monitoring"
    LOGGING = "logging"
    SECURITY = "security"
    NETWORKING = "networking"
    STORAGE = "storage"
    SERVICE_MESH = "service-mesh"
    DATABASE = "database"
    OTHER = "other"


ADDON_REGISTRY = {
    'monitoring-stack': {
        'name': 'Monitoring Stack',
        'description': 'Prometheus, Grafana, and alerting',
        'category': AddonCategory.MONITORING,
        'charts': ['prometheus-community/kube-prometheus-stack'],
        'namespace': 'monitoring',
        'installed': True,
    },
    'loki-stack': {
        'name': 'Loki Logging',
        'description': 'Centralized logging with Loki, Promtail, and Grafana',
        'category': AddonCategory.LOGGING,
        'charts': ['grafana/loki', 'grafana/promtail'],
        'namespace': 'logging',
        'installed': True,
    },
    'ingress-nginx': {
        'name': 'Ingress NGINX',
        'description': 'HTTP/HTTPS ingress controller',
        'category': AddonCategory.NETWORKING,
        'charts': ['ingress-nginx/ingress-nginx'],
        'namespace': 'ingress-nginx',
        'installed': True,
    },
    'cert-manager': {
        'name': 'cert-manager',
        'description': 'Automated TLS certificate management',
        'category': AddonCategory.SECURITY,
        'charts': ['jetstack/cert-manager'],
        'namespace': 'cert-manager',
        'installed': True,
    },
    'argocd': {
        'name': 'Argo CD',
        'description': 'GitOps continuous delivery',
        'category': AddonCategory.DEPLOYMENT,
        'charts': ['argoproj/argo-cd'],
        'namespace': 'argocd',
        'installed': False,
    },
    'istio': {
        'name': 'Istio Service Mesh',
        'description': 'Service mesh with traffic management',
        'category': AddonCategory.SERVICE_MESH,
        'charts': ['istio/istio'],
        'namespace': 'istio-system',
        'installed': False,
    },
    'vault': {
        'name': 'HashiCorp Vault',
        'description': 'Secrets management',
        'category': AddonCategory.SECURITY,
        'charts': ['hashicorp/vault'],
        'namespace': 'vault',
        'installed': False,
    },
    'redis': {
        'name': 'Redis',
        'description': 'In-memory data store',
        'category': AddonCategory.DATABASE,
        'charts': ['bitnami/redis'],
        'namespace': 'redis',
        'installed': False,
    },
    'postgres': {
        'name': 'PostgreSQL',
        'description': 'SQL database',
        'category': AddonCategory.DATABASE,
        'charts': ['bitnami/postgresql'],
        'namespace': 'postgres',
        'installed': False,
    },
    'elasticsearch': {
        'name': 'Elasticsearch',
        'description': 'Search and analytics engine',
        'category': AddonCategory.LOGGING,
        'charts': ['elastic/elasticsearch', 'elastic/kibana'],
        'namespace': 'elastic',
        'installed': False,
    },
    'jenkins': {
        'name': 'Jenkins',
        'description': 'CI/CD automation server',
        'category': AddonCategory.DEPLOYMENT,
        'charts': ['jenkins/jenkins'],
        'namespace': 'jenkins',
        'installed': False,
    },
    'tekton': {
        'name': 'Tekton Pipelines',
        'description': 'Kubernetes-native CI/CD',
        'category': AddonCategory.DEPLOYMENT,
        'charts': ['tektoncd/tekton'],
        'namespace': 'tekton',
        'installed': False,
    },
}


ADDON_CHARTS = {
    'prometheus-community/kube-prometheus-stack': {
        'repo': 'https://prometheus-community.github.io/helm-charts',
        'version': None,
    },
    'grafana/loki': {
        'repo': 'https://grafana.github.io/helm-charts',
        'version': None,
    },
    'grafana/promtail': {
        'repo': 'https://grafana.github.io/helm-charts',
        'version': None,
    },
    'ingress-nginx/ingress-nginx': {
        'repo': 'https://kubernetes.github.io/ingress-nginx',
        'version': None,
    },
    'jetstack/cert-manager': {
        'repo': 'https://charts.jetstack.io',
        'version': None,
    },
    'argoproj/argo-cd': {
        'repo': 'https://argoproj.github.io/argo-helm',
        'version': None,
    },
    'hashicorp/vault': {
        'repo': 'https://helm.releases.hashicorp.com',
        'version': None,
    },
    'bitnami/redis': {
        'repo': 'https://charts.bitnami.com/bitnami',
        'version': None,
    },
    'bitnami/postgresql': {
        'repo': 'https://charts.bitnami.com/bitnami',
        'version': None,
    },
    'elastic/elasticsearch': {
        'repo': 'https://helm.elastic.co',
        'version': None,
    },
    'elastic/kibana': {
        'repo': 'https://helm.elastic.co',
        'version': None,
    },
    'jenkins/jenkins': {
        'repo': 'https://charts.jenkins.io',
        'version': None,
    },
    'tektoncd/tekton': {
        'repo': 'https://cdfoundation.github.io/tekton-helm-chart',
        'version': None,
    },
}


class AddonManager:
    def __init__(self, kubeconfig: str = "kubeconfig"):
        self.kubeconfig = kubeconfig
        self.env = os.environ.copy()
        self.env['KUBECONFIG'] = kubeconfig
        self._added_repos = set()

    def run_helm(self, cmd: List[str], timeout: int = 120) -> subprocess.CompletedProcess:
        return subprocess.run(
            ['helm'] + cmd,
            env=self.env,
            capture_output=True,
            text=True,
            timeout=timeout
        )

    def add_repo(self, name: str, url: str):
        if name in self._added_repos:
            return
        self.run_helm(['repo', 'add', name, url, '--force-update'])
        self._added_repos.add(name)

    def update_repos(self):
        self.run_helm(['repo', 'update'])

    def install_addon(self, addon_id: str, values: Optional[Dict] = None, wait: bool = True) -> bool:
        if addon_id not in ADDON_REGISTRY:
            print(f"Unknown addon: {addon_id}")
            return False

        addon = ADDON_REGISTRY[addon_id]
        charts = addon.get('charts', [])

        if not charts:
            print(f"No charts defined for addon: {addon_id}")
            return False

        for chart in charts:
            if chart not in ADDON_CHARTS:
                continue

            chart_info = ADDON_CHARTS[chart]
            repo_name = chart.split('/')[0]

            self.add_repo(repo_name, chart_info['repo'])
            self.update_repos()

            release_name = chart.split('/')[-1]
            namespace = addon.get('namespace', 'default')
            chart_full = f"{repo_name}/{chart.split('/')[-1]}"

            cmd = ['upgrade', '--install', release_name, chart_full, '--namespace', namespace, '--create-namespace']

            if wait:
                cmd.extend(['--wait', '--timeout', '5m'])

            if values:
                for k, v in values.items():
                    cmd.extend(['--set', f'{k}={v}'])

            print(f"Installing {chart_full}...")
            result = self.run_helm(cmd)

            if result.returncode != 0:
                print(f"Failed to install {chart_full}: {result.stderr}")
                return False

        print(f"✅ Addon '{addon['name']}' installed")
        return True

    def uninstall_addon(self, addon_id: str) -> bool:
        if addon_id not in ADDON_REGISTRY:
            print(f"Unknown addon: {addon_id}")
            return False

        addon = ADDON_REGISTRY[addon_id]
        charts = addon.get('charts', [])

        for chart in charts:
            release_name = chart.split('/')[-1]
            result = self.run_helm(['uninstall', release_name, '--namespace', addon.get('namespace', 'default')])

        print(f"✅ Addon '{addon['name']}' uninstalled")
        return True

    def list_addons(self, installed_only: bool = False) -> List[Dict]:
        addons = []

        for addon_id, info in ADDON_REGISTRY.items():
            charts = info.get('charts', [])
            is_installed = True

            for chart in charts:
                release_name = chart.split('/')[-1]
                result = self.run_helm(['list', '-n', info.get('namespace', 'default'), '-o', 'json'])
                if result.returncode == 0:
                    import json
                    try:
                        releases = json.loads(result.stdout)
                        is_installed = any(r.get('name') == release_name for r in releases)
                    except:
                        pass

            if installed_only and not is_installed:
                continue

            addons.append({
                'id': addon_id,
                'name': info['name'],
                'description': info['description'],
                'category': info['category'].value,
                'installed': is_installed,
                'namespace': info.get('namespace', 'default'),
            })

        return addons

    def get_addon_status(self, addon_id: str) -> Optional[Dict]:
        if addon_id not in ADDON_REGISTRY:
            return None

        addon = ADDON_REGISTRY[addon_id]
        charts = addon.get('charts', [])

        status = {'addon': addon_id, 'charts': [], 'healthy': True}

        for chart in charts:
            release_name = chart.split('/')[-1]
            result = self.run_helm(['status', release_name, '-n', addon.get('namespace', 'default')])

            if result.returncode == 0:
                status['charts'].append({
                    'name': release_name,
                    'status': 'deployed',
                    'info': result.stdout[:200]
                })
            else:
                status['charts'].append({
                    'name': release_name,
                    'status': 'not found'
                })
                status['healthy'] = False

        return status


def list_available_addons() -> List[Dict]:
    return [
        {
            'id': addon_id,
            'name': info['name'],
            'description': info['description'],
            'category': info['category'].value,
        }
        for addon_id, info in ADDON_REGISTRY.items()
    ]


def search_addons(query: str) -> List[Dict]:
    query_lower = query.lower()
    results = []

    for addon_id, info in ADDON_REGISTRY.items():
        if (query_lower in info['name'].lower() or
            query_lower in info['description'].lower() or
            query_lower in addon_id.lower()):
            results.append({
                'id': addon_id,
                'name': info['name'],
                'description': info['description'],
                'category': info['category'].value,
            })

    return results