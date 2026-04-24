"""Unit tests for utility functions."""
import pytest
import yaml
from pathlib import Path

from privatecloud.utils import load_config, save_config, save_default_config
from privatecloud.config import PrivateCloudConfig, NodeConfig


class TestSaveDefaultConfig:
    def test_creates_file(self, tmp_path):
        path = str(tmp_path / "privatecloud.yaml")
        save_default_config(path)
        assert Path(path).exists()

    def test_contains_expected_keys(self, tmp_path):
        path = str(tmp_path / "privatecloud.yaml")
        save_default_config(path)
        data = yaml.safe_load(Path(path).read_text())
        assert "cluster_name" in data
        assert "provider" in data
        assert "k3s_version" in data
        assert "nodes" in data
        assert "services" in data
        assert "proxmox" in data

    def test_default_provider_is_bare_metal(self, tmp_path):
        path = str(tmp_path / "privatecloud.yaml")
        save_default_config(path)
        data = yaml.safe_load(Path(path).read_text())
        assert data["provider"] == "bare-metal"


class TestLoadConfig:
    def test_load_valid_config(self, tmp_path):
        path = str(tmp_path / "privatecloud.yaml")
        save_default_config(path)
        cfg = load_config(path)
        assert isinstance(cfg, PrivateCloudConfig)
        assert cfg.cluster_name == "my-private-cloud"

    def test_load_missing_file_raises(self, tmp_path):
        path = str(tmp_path / "nonexistent.yaml")
        with pytest.raises(FileNotFoundError):
            load_config(path)


class TestSaveConfig:
    def test_roundtrip(self, tmp_path):
        path = str(tmp_path / "privatecloud.yaml")
        original = PrivateCloudConfig(
            cluster_name="roundtrip-test",
            provider="proxmox",
            nodes=[NodeConfig(host="1.2.3.4", role="master")],
        )
        save_config(original, path)
        loaded = load_config(path)
        assert loaded.cluster_name == "roundtrip-test"
        assert loaded.provider == "proxmox"
        assert len(loaded.nodes) == 1
        assert loaded.nodes[0].host == "1.2.3.4"
