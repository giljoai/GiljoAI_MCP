"""
Unit tests for SerenaDetector service.

Tests detection of uvx and Serena MCP installation status.
"""

import subprocess
import sys
from pathlib import Path
from unittest.mock import Mock, patch


sys.path.insert(0, str(Path(__file__).parent.parent.parent))

from src.giljo_mcp.services.serena_detector import SerenaDetector


class TestSerenaDetector:
    """Test suite for SerenaDetector"""

    def setup_method(self, method):
        """Setup test method"""
        self.detector = SerenaDetector()

    def test_detect_when_uvx_not_installed(self):
        """Test detection fails gracefully when uvx not available."""
        with patch("subprocess.run") as mock_run:
            # Simulate FileNotFoundError when uvx is not found
            mock_run.side_effect = FileNotFoundError("uvx not found")

            result = self.detector.detect()

            assert result["installed"] is False
            assert result["uvx_available"] is False
            assert result["version"] is None
            assert "uvx not found" in result["error"]

    def test_detect_when_uvx_installed_but_serena_not(self):
        """Test detection succeeds for uvx but fails for Serena."""
        with patch("subprocess.run") as mock_run:
            # First call: uvx --version succeeds
            # Second call: uvx serena --version fails
            mock_run.side_effect = [
                Mock(returncode=0, stdout="uvx 0.4.18\n", stderr=""),  # uvx available
                subprocess.CalledProcessError(1, "uvx serena --version", stderr="Package 'serena' not found"),
            ]

            result = self.detector.detect()

            assert result["installed"] is False
            assert result["uvx_available"] is True
            assert result["version"] is None
            assert "serena" in result["error"].lower() or "not found" in result["error"].lower()

    def test_detect_success(self):
        """Test successful detection returns version."""
        with patch("subprocess.run") as mock_run:
            # Both uvx and serena checks succeed
            mock_run.side_effect = [
                Mock(returncode=0, stdout="uvx 0.4.18\n", stderr=""),  # uvx available
                Mock(returncode=0, stdout="Serena MCP v1.2.3\n", stderr=""),  # serena available
            ]

            result = self.detector.detect()

            assert result["installed"] is True
            assert result["uvx_available"] is True
            assert result["version"] == "1.2.3"
            assert result["error"] is None

    def test_detect_success_with_alternate_version_format(self):
        """Test successful detection with different version output format."""
        with patch("subprocess.run") as mock_run:
            # Both uvx and serena checks succeed with different version format
            mock_run.side_effect = [
                Mock(returncode=0, stdout="uvx 0.4.18\n", stderr=""),
                Mock(returncode=0, stdout="serena 2.0.0-beta\n", stderr=""),
            ]

            result = self.detector.detect()

            assert result["installed"] is True
            assert result["uvx_available"] is True
            assert "2.0.0" in result["version"]
            assert result["error"] is None

    def test_detect_uvx_timeout(self):
        """Test detection handles subprocess timeout for uvx check."""
        with patch("subprocess.run") as mock_run:
            # Simulate timeout on uvx check
            mock_run.side_effect = subprocess.TimeoutExpired("uvx --version", 5)

            result = self.detector.detect()

            assert result["installed"] is False
            assert result["uvx_available"] is False
            assert result["version"] is None
            assert "timeout" in result["error"].lower()

    def test_detect_serena_timeout(self):
        """Test detection handles subprocess timeout for Serena check."""
        with patch("subprocess.run") as mock_run:
            # uvx succeeds, but serena check times out
            mock_run.side_effect = [
                Mock(returncode=0, stdout="uvx 0.4.18\n", stderr=""),
                subprocess.TimeoutExpired("uvx serena --version", 10),
            ]

            result = self.detector.detect()

            assert result["installed"] is False
            assert result["uvx_available"] is True
            assert result["version"] is None
            assert "timeout" in result["error"].lower()

    def test_detect_handles_non_zero_return_code(self):
        """Test detection handles non-zero return codes gracefully."""
        with patch("subprocess.run") as mock_run:
            # uvx check returns non-zero
            mock_run.side_effect = subprocess.CalledProcessError(127, "uvx --version", stderr="Command not found")

            result = self.detector.detect()

            assert result["installed"] is False
            assert result["uvx_available"] is False
            assert result["version"] is None
            assert result["error"] is not None

    def test_detect_handles_empty_version_output(self):
        """Test detection handles empty version output."""
        with patch("subprocess.run") as mock_run:
            # Both commands succeed but with empty output
            mock_run.side_effect = [
                Mock(returncode=0, stdout="", stderr=""),
                Mock(returncode=0, stdout="", stderr=""),
            ]

            result = self.detector.detect()

            # Should still mark as installed if commands succeed
            assert result["uvx_available"] is True
            # Version might be None or "unknown"
            assert result["version"] is None or result["version"] == "unknown"

    def test_detect_cross_platform_path_handling(self):
        """Test that detector works on different platforms."""
        # This test ensures no hardcoded paths are used
        with patch("subprocess.run") as mock_run:
            mock_run.side_effect = [
                Mock(returncode=0, stdout="uvx 0.4.18\n", stderr=""),
                Mock(returncode=0, stdout="Serena MCP v1.2.3\n", stderr=""),
            ]

            result = self.detector.detect()

            # Verify subprocess.run was called with proper cross-platform command
            assert mock_run.call_count == 2
            # First call should be for uvx
            first_call_args = mock_run.call_args_list[0][0][0]
            assert "uvx" in first_call_args
            # Should use shell=False for security
            assert mock_run.call_args_list[0][1].get("shell") is False

    def test_detect_strips_whitespace_from_version(self):
        """Test that version string is properly cleaned."""
        with patch("subprocess.run") as mock_run:
            # Version output with extra whitespace
            mock_run.side_effect = [
                Mock(returncode=0, stdout="uvx 0.4.18\n", stderr=""),
                Mock(returncode=0, stdout="  Serena MCP v1.2.3  \n\n", stderr=""),
            ]

            result = self.detector.detect()

            assert result["installed"] is True
            assert result["version"] == "1.2.3"
            # Verify no leading/trailing whitespace
            assert result["version"].strip() == result["version"]

    def test_detect_returns_structured_dict(self):
        """Test that detect() returns properly structured dictionary."""
        with patch("subprocess.run") as mock_run:
            mock_run.side_effect = [
                Mock(returncode=0, stdout="uvx 0.4.18\n", stderr=""),
                Mock(returncode=0, stdout="Serena MCP v1.2.3\n", stderr=""),
            ]

            result = self.detector.detect()

            # Verify all required keys are present
            assert "installed" in result
            assert "uvx_available" in result
            assert "version" in result
            assert "error" in result

            # Verify types
            assert isinstance(result["installed"], bool)
            assert isinstance(result["uvx_available"], bool)
            assert result["version"] is None or isinstance(result["version"], str)
            assert result["error"] is None or isinstance(result["error"], str)
