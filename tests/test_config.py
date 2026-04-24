"""Unit tests for config validation."""
import pytest
from privatecloud.config import PrivateCloudConfig, NodeConfig, ProxmoxConfig, ServicesConfig


class TestNodeConfig:
    def test_defaults(self):
        node = NodeConfig(host="10.0.0.1")
        assert node.user == "root"
        assert node.port == 22
        assert node.role == "worker"

    def test_custom_values(self):
        node = NodeConfig(host="10.0.0.2", user="admin", port=2222, role="master")
        assert node.host == "10.0.0.2"
        assert node.user == "admin"
        assert node.port == 2222
        assert node.role == "master"


class TestServicesConfig:
    def test_all_enabled_by_default(self):
        services = ServicesConfig()
        assert services.metallb is True
        assert services.ingress_nginx is True
        assert services.cert_manager is True
        assert services.monitoring is True
        assert services.longhorn is True

    def test_selective_disable(self):
        services = ServicesConfig(longhorn=False, monitoring=False)
        assert services.longhorn is False
        assert services.monitoring is False
        assert services.ingress_nginx is True


class TestProxmoxConfig:
    def test_defaults(self):
        cfg = ProxmoxConfig()
        assert cfg.master_count == 1
        assert cfg.worker_count == 2
        assert cfg.storage == "local-lvm"
        assert cfg.bridge == "vmbr0"


class TestPrivateCloudConfig:
    def test_defaults(self):
        cfg = PrivateCloudConfig()
        assert cfg.cluster_name == "my-private-cloud"
        assert cfg.provider == "bare-metal"
        assert cfg.k3s_version == "v1.29.0+k3s1"
        assert cfg.nodes == []
        assert cfg.proxmox is None

    def test_valid_provider_bare_metal(self):
        cfg = PrivateCloudConfig(provider="bare-metal")
        assert cfg.provider == "bare-metal"

    def test_valid_provider_proxmox(self):
        cfg = PrivateCloudConfig(provider="proxmox")
        assert cfg.provider == "proxmox"

    def test_invalid_provider_raises(self):
        with pytest.raises(ValueError, match="Unsupported provider"):
            PrivateCloudConfig(provider="aws")

    def test_full_config(self):
        cfg = PrivateCloudConfig(
            cluster_name="test-cluster",
            provider="proxmox",
            k3s_version="v1.30.0+k3s1",
            nodes=[
                NodeConfig(host="10.0.0.1", role="master"),
                NodeConfig(host="10.0.0.2", role="worker"),
            ],
            proxmox=ProxmoxConfig(
                url="https://pve.local:8006/api2/json",
                node="pve1",
                master_count=1,
                worker_count=3,
            ),
            services=ServicesConfig(longhorn=False),
        )
        assert cfg.cluster_name == "test-cluster"
        assert len(cfg.nodes) == 2
        assert cfg.nodes[0].role == "master"
        assert cfg.proxmox.worker_count == 3
        assert cfg.services.longhorn is False
