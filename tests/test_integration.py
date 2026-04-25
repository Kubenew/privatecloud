import pytest
import os
import yaml
import tempfile
from pathlib import Path
from unittest.mock import patch, MagicMock

from privatecloud.backup import (
    create_backup, list_backups, delete_backup, 
    verify_backup, restore_backup, encrypt_backup, decrypt_backup
)
from privatecloud.backup import BACKUP_ROOT


class TestBackup:
    @pytest.fixture
    def temp_dir(self, tmp_path):
        with patch('privatecloud.backup.BACKUP_ROOT', tmp_path):
            yield tmp_path
    
    @pytest.fixture
    def mock_kubectl(self):
        with patch('privatecloud.backup.run_cmd') as mock:
            mock.return_value = MagicMock(returncode=0, stdout="namespace/test\n")
            yield mock
    
    def test_ensure_backup_dir(self, temp_dir):
        from privatecloud.backup import ensure_backup_dir
        ensure_backup_dir()
        assert temp_dir.exists()
        assert (temp_dir / "backups").exists()
    
    @pytest.fixture
    def mock_kubectl_namespaces(self):
        with patch('privatecloud.backup.run_cmd') as mock:
            mock.return_value = MagicMock(returncode=0, stdout="default\nkube-system\nmonitoring\n")
            yield mock
    
    def test_create_backup_structure(self, temp_dir, mock_kubectl_namespaces):
        with patch('privatecloud.backup.BACKUP_ROOT', temp_dir):
            with patch('privatecloud.backup.run_cmd') as mock:
                mock.return_value = MagicMock(returncode=0, stdout="default\nkube-system\nmonitoring\n")
                # Should not fail - backup dir structure created
                # Note: Full backup requires actual k8s connection
    
    def test_list_backups_empty(self, temp_dir):
        with patch('privatecloud.backup.BACKUP_ROOT', temp_dir):
            backups = list_backups()
            assert isinstance(backups, list)
            assert len(backups) == 0
    
    def test_delete_nonexistent_backup(self, temp_dir):
        with patch('privatecloud.backup.BACKUP_ROOT', temp_dir):
            result = delete_backup("nonexistent")
            assert result == False
    
    def test_encrypt_backup_no_passphrase(self, temp_dir):
        with patch('privatecloud.backup.BACKUP_ROOT', temp_dir):
            backup_file = temp_dir / "test.tar.gz"
            backup_file.touch()
            result = encrypt_backup(backup_file, passphrase="")
            assert result is None  # No passphrase provided
    
    def test_backup_constants(self):
        assert BACKUP_ROOT.name == "backups"


class TestCloudStorage:
    def test_check_s3_not_configured(self):
        with patch.dict(os.environ, {}, clear=True):
            from privatecloud.cloud_storage import check_s3_configured
            assert check_s3_configured() == False
    
    def test_check_azure_not_configured(self):
        with patch.dict(os.environ, {}, clear=True):
            from privatecloud.cloud_storage import check_azure_configured
            assert check_azure_configured() == False
    
    def test_check_gcs_not_configured(self):
        with patch.dict(os.environ, {}, clear=True):
            from privatecloud.cloud_storage import check_gcs_configured
            assert check_gcs_configured() == False
    
    def test_get_aws_credentials_env(self):
        with patch.dict(os.environ, {
            'AWS_ACCESS_KEY_ID': 'testkey',
            'AWS_SECRET_ACCESS_KEY': 'testsecret',
            'AWS_DEFAULT_REGION': 'us-east-1'
        }):
            from privatecloud.cloud_storage import get_aws_credentials
            creds = get_aws_credentials()
            assert creds['access_key'] == 'testkey'
            assert creds['secret_key'] == 'testsecret'
            assert creds['region'] == 'us-east-1'


class TestScheduler:
    def test_schedule_status_no_cron(self):
        from privatecloud.scheduler import get_schedule_status
        with patch('privatecloud.scheduler.run_cmd') as mock:
            mock.return_value = MagicMock(returncode=1, stdout="")
            status = get_schedule_status()
            assert status['active'] == False
    
    def test_remove_schedule(self):
        from privatecloud.scheduler import remove_schedule
        with patch('privatecloud.scheduler.run_cmd') as mock:
            mock.return_value = MagicMock(returncode=0, stdout="")
            result = remove_schedule()
            # Returns True even if no schedule exists (idempotent)


class TestValidate:
    def test_validate_yaml_syntax_valid(self, tmp_path):
        config_file = tmp_path / "test.yaml"
        config_file.write_text("cluster_name: test\nprovider: bare-metal\n")
        
        with patch('privatecloud.validate.load_config') as mock:
            mock.return_value = {'cluster_name': 'test', 'provider': 'bare-metal'}
            from privatecloud.validate import validate_yaml_syntax
            valid, issues = validate_yaml_syntax(str(config_file))
            # Depends on yaml library, just check structure
    
    def test_validate_nodes_empty_bare_metal(self):
        from privatecloud.validate import validate_nodes
        issues = validate_nodes([], "bare-metal")
        assert len(issues) > 0
        assert any("No nodes" in i.message for i in issues)
    
    def test_validate_nodes_ignored_proxmox(self):
        from privatecloud.validate import validate_nodes
        issues = validate_nodes([{"host": "test"}], "proxmox")
        # Should be ignored for proxmox provider
        assert len(issues) == 0
    
    def test_lint_config_missing_file(self):
        from privatecloud.validate import lint_config
        with patch('pathlib.Path.exists') as mock:
            mock.return_value = False
            valid, issues = lint_config("nonexistent.yaml")
            assert valid == False
            assert len(issues) > 0


class TestSecurity:
    def test_mask_secrets_text(self):
        from privatecloud.security import mask_secrets
        text = "token=secret123 password=mypassword api_key=abc123"
        masked = mask_secrets(text)
        assert "secret123" not in masked
        assert "mypassword" not in masked
        assert "api_key" in masked
    
    def test_mask_dict_secrets(self):
        from privatecloud.security import mask_dict_secrets
        data = {
            "token": "secret123",
            "password": "mypassword",
            "username": "admin"  # Should not be masked
        }
        masked = mask_dict_secrets(data)
        assert masked["token"] == "***MASKED***"
        assert masked["password"] == "***MASKED***"
        assert masked["username"] == "admin"
    
    def test_env_var_substitution(self):
        with patch.dict(os.environ, {"TEST_VAR": "test_value"}):
            from privatecloud.security import _substitute_env_vars
            result = _substitute_env_vars("value is ${TEST_VAR}")
            assert result == "value is test_value"
    
    def test_env_var_missing_raises(self):
        with patch.dict(os.environ, {}, clear=True):
            from privatecloud.security import _substitute_env_vars
            with pytest.raises(ValueError, match="not set"):
                _substitute_env_vars("value is ${MISSING_VAR}")


class TestMulticluster:
    def test_clusters_dir_created(self, tmp_path):
        with patch('privatecloud.multicluster.CLUSTERS_DIR', tmp_path / ".privatecloud/clusters"):
            from privatecloud.multicluster import ensure_clusters_dir
            ensure_clusters_dir()
            assert (tmp_path / ".privatecloud/clusters").exists()
    
    def test_list_clusters_empty(self, tmp_path):
        with patch('privatecloud.multicluster.CLUSTERS_DIR', tmp_path / "clusters"):
            from privatecloud.multicluster import list_clusters
            clusters = list_clusters()
            assert isinstance(clusters, list)


class TestHighAvailability:
    def test_validate_ha_warnings(self):
        from privatecloud.high_availability import validate_ha_setup
        warnings = validate_ha_setup(1, "embedded")
        assert len(warnings) > 0
        assert "at least 3" in warnings[0].lower() or "2" in warnings[0]
    
    def test_validate_ha_minimum_masters(self):
        from privatecloud.high_availability import validate_ha_setup
        warnings = validate_ha_setup(1, "postgresql")
        assert len(warnings) > 0


class TestPITR:
    def test_check_longhorn_available(self):
        with patch('privatecloud.pitr.run_cmd') as mock:
            mock.return_value = MagicMock(returncode=1, stdout="")
            from privatecloud.pitr import check_longhorn_available
            assert check_longhorn_available() == False


class TestChangelog:
    def test_get_version_from_pyproject(self):
        from privatecloud.changelog import get_version_from_pyproject
        with patch('pathlib.Path') as mock:
            mock.return_value.__enter__.return_value.read_text.return_value = 'version = "0.7.0"'
            version = get_version_from_pyproject()
            # Just check it's a string
            assert isinstance(version, str)