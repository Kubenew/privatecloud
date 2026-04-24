"""Unit tests for the doctor module."""
from unittest.mock import patch
from privatecloud.doctor import check_tools, DoctorResult


class TestDoctor:
    def test_all_tools_present(self):
        with patch("shutil.which", return_value="/usr/bin/tool"):
            result = check_tools()
            assert result.ok is True
            assert result.missing_required == []
            assert result.missing_optional == []

    def test_missing_required_tool(self):
        def mock_which(name):
            if name == "terraform":
                return None
            return f"/usr/bin/{name}"

        with patch("shutil.which", side_effect=mock_which):
            result = check_tools()
            assert result.ok is False
            assert "terraform" in result.missing_required

    def test_missing_optional_tool(self):
        def mock_which(name):
            if name == "kubectl":
                return None
            return f"/usr/bin/{name}"

        with patch("shutil.which", side_effect=mock_which):
            result = check_tools()
            assert result.ok is True  # optional tools don't fail
            assert "kubectl" in result.missing_optional
