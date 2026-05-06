"""Tests for HPE Morpheus VM Essentials provider support."""
import pytest
import tempfile
from pathlib import Path
from privatecloud.validate import validate_morpheus_config
from privatecloud.config import MorpheusConfig, PrivateCloudConfig, SUPPORTED_CLOUD_TYPES


# ---- Validation Tests ----

class TestValidateMorpheusConfig:
    def test_valid_config(self):
        config = {
            "url": "https://morpheus.test",
            "username": "admin",
            "password": "realpassword",
            "group_name": "Group 1",
            "cloud_name": "Cloud 1"
        }
        issues = validate_morpheus_config(config, "morpheus")
        error_issues = [i for i in issues if i.severity == "error"]
        assert len(error_issues) == 0

    def test_missing_fields(self):
        config = {
            "url": "https://morpheus.test"
        }
        issues = validate_morpheus_config(config, "morpheus")
        error_issues = [i for i in issues if i.severity == "error"]
        # Should flag missing username, password, group_name, cloud_name
        assert len(error_issues) == 4

    def test_invalid_url(self):
        config = {
            "url": "morpheus.test",
            "username": "admin",
            "password": "realpassword",
            "group_name": "Group 1",
            "cloud_name": "Cloud 1"
        }
        issues = validate_morpheus_config(config, "morpheus")
        error_issues = [i for i in issues if i.severity == "error"]
        assert len(error_issues) == 1
        assert "Invalid Morpheus URL" in error_issues[0].message

    def test_placeholder_password(self):
        config = {
            "url": "https://morpheus.test",
            "username": "admin",
            "password": "${MORPHEUS_PASSWORD}",
            "group_name": "Group 1",
            "cloud_name": "Cloud 1"
        }
        issues = validate_morpheus_config(config, "morpheus")
        warning_issues = [i for i in issues if i.severity == "warning"]
        assert len(warning_issues) == 1
        assert "Morpheus password is still default env var placeholder" in warning_issues[0].message

    def test_wrong_provider_with_config(self):
        config = {"url": "https://test"}
        issues = validate_morpheus_config(config, "bare-metal")
        warning_issues = [i for i in issues if i.severity == "warning"]
        assert len(warning_issues) == 1
        assert "Morpheus config provided but provider is not 'morpheus'" in warning_issues[0].message

    def test_invalid_cloud_type(self):
        config = {
            "url": "https://morpheus.test",
            "username": "admin",
            "password": "realpassword",
            "group_name": "Group 1",
            "cloud_name": "Cloud 1",
            "cloud_type": "foobar"
        }
        issues = validate_morpheus_config(config, "morpheus")
        error_issues = [i for i in issues if i.severity == "error"]
        assert any("Unsupported Morpheus cloud_type" in i.message for i in error_issues)

    def test_invalid_master_count(self):
        config = {
            "url": "https://morpheus.test",
            "username": "admin",
            "password": "realpassword",
            "group_name": "Group 1",
            "cloud_name": "Cloud 1",
            "master_count": 0
        }
        issues = validate_morpheus_config(config, "morpheus")
        error_issues = [i for i in issues if i.severity == "error"]
        assert any("master_count must be at least 1" in i.message for i in error_issues)

    def test_large_deployment_warning(self):
        config = {
            "url": "https://morpheus.test",
            "username": "admin",
            "password": "realpassword",
            "group_name": "Group 1",
            "cloud_name": "Cloud 1",
            "master_count": 5,
            "worker_count": 20
        }
        issues = validate_morpheus_config(config, "morpheus")
        warning_issues = [i for i in issues if i.severity == "warning"]
        assert any("Large deployment" in i.message for i in warning_issues)

    def test_empty_config_skips_when_wrong_provider(self):
        issues = validate_morpheus_config({}, "bare-metal")
        assert len(issues) == 0


# ---- Config Model Tests ----

class TestMorpheusConfigModel:
    def test_cloud_type_validation_rejects_invalid(self):
        with pytest.raises(ValueError, match="Unsupported cloud_type"):
            MorpheusConfig(cloud_type="foobar")

    def test_cloud_type_validation_accepts_all_supported(self):
        for ct in SUPPORTED_CLOUD_TYPES:
            cfg = MorpheusConfig(cloud_type=ct)
            assert cfg.cloud_type == ct

    def test_master_count_must_be_positive(self):
        with pytest.raises(ValueError):
            MorpheusConfig(master_count=0)

    def test_worker_count_allows_zero(self):
        cfg = MorpheusConfig(worker_count=0)
        assert cfg.worker_count == 0


# ---- Terraform Template Rendering Tests ----

class TestMorpheusTerraformTemplate:
    def test_generate_morpheus_template(self):
        """Test that generate_tf produces valid Terraform HCL for morpheus."""
        from privatecloud.terraform import generate_tf

        config = PrivateCloudConfig(
            cluster_name="test-morpheus",
            provider="morpheus",
            morpheus=MorpheusConfig(
                url="https://morpheus.local",
                username="testadmin",
                password="testpass",
                group_name="TestGroup",
                cloud_name="TestCloud",
                instance_type_name="Ubuntu 22",
                layout_name="VMware VM",
                plan_name="2 CPU, 4GB Memory",
                master_count=1,
                worker_count=2,
                cloud_type="vmware",
                ssh_user="ubuntu",
            ),
        )

        with tempfile.TemporaryDirectory() as tmpdir:
            generate_tf(config, run_dir=tmpdir)

            tf_file = Path(tmpdir) / "main.tf"
            assert tf_file.exists(), "main.tf was not generated"

            content = tf_file.read_text()

            # Provider block
            assert 'source  = "HPE/hpe"' in content
            assert 'url      = "https://morpheus.local"' in content
            assert 'username = "testadmin"' in content

            # Data sources
            assert 'data "hpe_morpheus_group" "target"' in content
            assert '"TestGroup"' in content
            assert 'data "hpe_morpheus_cloud" "target"' in content
            assert '"TestCloud"' in content

            # Resources
            assert 'resource "hpe_morpheus_instance" "master"' in content
            assert 'resource "hpe_morpheus_instance" "worker"' in content
            assert "test-morpheus-master" in content
            assert "test-morpheus-worker" in content
            assert "count            = 1" in content   # master_count
            assert "count            = 2" in content   # worker_count

            # Cloud type config block
            assert "config_vmware {}" in content

            # Outputs
            assert 'output "master_ips"' in content
            assert 'output "worker_ips"' in content

    def test_generate_morpheus_missing_config_raises(self):
        """generate_tf should raise when provider=morpheus but no morpheus block."""
        from privatecloud.terraform import generate_tf

        config = PrivateCloudConfig(
            cluster_name="test",
            provider="morpheus",
            morpheus=None,
        )

        with tempfile.TemporaryDirectory() as tmpdir:
            with pytest.raises(ValueError, match="no morpheus config block"):
                generate_tf(config, run_dir=tmpdir)
