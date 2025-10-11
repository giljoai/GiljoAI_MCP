"""
Unit tests for startup.py network IP detection.

Tests the get_network_ip() function's behavior in various scenarios:
- Reading from config.yaml (backward compatibility)
- Runtime detection using psutil (fresh install fallback)
- Virtual adapter filtering
- Cross-platform compatibility
"""

import pytest
from pathlib import Path
from unittest.mock import Mock, mock_open, patch
from types import SimpleNamespace


@pytest.fixture
def mock_psutil_addresses():
    """Mock psutil network addresses structure."""
    def create_addr(family, address):
        """Create a mock address object."""
        addr = SimpleNamespace()
        addr.family = family  # 2 = AF_INET (IPv4)
        addr.address = address
        return addr
    return create_addr


@pytest.fixture
def mock_psutil_stats():
    """Mock psutil interface stats."""
    def create_stats(isup):
        stats = SimpleNamespace()
        stats.isup = isup
        return stats
    return create_stats


class TestGetNetworkIPWithConfig:
    """Test get_network_ip() with existing config.yaml."""

    def test_reads_server_ip_from_config(self):
        """Should read server.ip from config.yaml (legacy format)."""
        config_content = """
server:
  ip: 10.1.0.164
  port: 7272
"""
        with patch("pathlib.Path.exists", return_value=True), \
             patch("builtins.open", mock_open(read_data=config_content)), \
             patch("psutil.net_if_addrs") as mock_psutil:

            # Import after patching to get the mocked version
            from startup import get_network_ip

            result = get_network_ip()

            assert result == "10.1.0.164"
            # psutil should NOT be called when config exists
            mock_psutil.assert_not_called()

    def test_reads_security_network_initial_ip_from_config(self):
        """Should read security.network.initial_ip from config.yaml (v3.0 format)."""
        config_content = """
version: 3.0.0
security:
  network:
    initial_ip: 192.168.1.100
services:
  api:
    port: 7272
"""
        with patch("pathlib.Path.exists", return_value=True), \
             patch("builtins.open", mock_open(read_data=config_content)), \
             patch("psutil.net_if_addrs") as mock_psutil:

            from startup import get_network_ip

            result = get_network_ip()

            assert result == "192.168.1.100"
            mock_psutil.assert_not_called()

    def test_prefers_server_ip_over_security_network_ip(self):
        """Should prefer legacy server.ip if both formats exist."""
        config_content = """
server:
  ip: 10.1.0.164
security:
  network:
    initial_ip: 192.168.1.100
"""
        with patch("pathlib.Path.exists", return_value=True), \
             patch("builtins.open", mock_open(read_data=config_content)):

            from startup import get_network_ip

            result = get_network_ip()

            # Should prefer server.ip (legacy format)
            assert result == "10.1.0.164"

    def test_config_yaml_read_error_falls_back_to_runtime(self, mock_psutil_addresses, mock_psutil_stats):
        """Should fall back to runtime detection if config.yaml read fails."""
        with patch("pathlib.Path.exists", return_value=True), \
             patch("builtins.open", side_effect=PermissionError("Access denied")), \
             patch("psutil.net_if_addrs", return_value={
                 "eth0": [mock_psutil_addresses(2, "10.1.0.164")]
             }), \
             patch("psutil.net_if_stats", return_value={
                 "eth0": mock_psutil_stats(True)
             }):

            from startup import get_network_ip

            result = get_network_ip()

            # Should fall back to runtime detection
            assert result == "10.1.0.164"


class TestGetNetworkIPRuntimeDetection:
    """Test get_network_ip() runtime detection (no config.yaml)."""

    def test_detects_physical_adapter(self, mock_psutil_addresses, mock_psutil_stats):
        """Should detect physical network adapter on fresh install."""
        with patch("pathlib.Path.exists", return_value=False), \
             patch("psutil.net_if_addrs", return_value={
                 "Ethernet": [mock_psutil_addresses(2, "10.1.0.164")]
             }), \
             patch("psutil.net_if_stats", return_value={
                 "Ethernet": mock_psutil_stats(True)
             }):

            from startup import get_network_ip

            result = get_network_ip()

            assert result == "10.1.0.164"

    def test_prefers_physical_over_virtual_adapter(self, mock_psutil_addresses, mock_psutil_stats):
        """Should prefer physical adapter over virtual ones."""
        with patch("pathlib.Path.exists", return_value=False), \
             patch("psutil.net_if_addrs", return_value={
                 "vboxnet0": [mock_psutil_addresses(2, "192.168.56.1")],
                 "Ethernet": [mock_psutil_addresses(2, "10.1.0.164")],
                 "docker0": [mock_psutil_addresses(2, "172.17.0.1")]
             }), \
             patch("psutil.net_if_stats", return_value={
                 "vboxnet0": mock_psutil_stats(True),
                 "Ethernet": mock_psutil_stats(True),
                 "docker0": mock_psutil_stats(True)
             }):

            from startup import get_network_ip

            result = get_network_ip()

            # Should return physical adapter, not virtual ones
            assert result == "10.1.0.164"

    def test_falls_back_to_virtual_if_no_physical(self, mock_psutil_addresses, mock_psutil_stats):
        """Should use virtual adapter if no physical adapter available."""
        with patch("pathlib.Path.exists", return_value=False), \
             patch("psutil.net_if_addrs", return_value={
                 "vboxnet0": [mock_psutil_addresses(2, "192.168.56.1")]
             }), \
             patch("psutil.net_if_stats", return_value={
                 "vboxnet0": mock_psutil_stats(True)
             }):

            from startup import get_network_ip

            result = get_network_ip()

            assert result == "192.168.56.1"

    def test_returns_none_if_no_adapters(self):
        """Should return None if no network adapters found."""
        with patch("pathlib.Path.exists", return_value=False), \
             patch("psutil.net_if_addrs", return_value={}), \
             patch("psutil.net_if_stats", return_value={}):

            from startup import get_network_ip

            result = get_network_ip()

            assert result is None


class TestVirtualAdapterFiltering:
    """Test virtual adapter filtering logic."""

    def test_filters_docker_adapters(self, mock_psutil_addresses, mock_psutil_stats):
        """Should filter out Docker virtual adapters."""
        with patch("pathlib.Path.exists", return_value=False), \
             patch("psutil.net_if_addrs", return_value={
                 "docker0": [mock_psutil_addresses(2, "172.17.0.1")],
                 "br-abc123": [mock_psutil_addresses(2, "172.18.0.1")],
                 "eth0": [mock_psutil_addresses(2, "10.1.0.164")]
             }), \
             patch("psutil.net_if_stats", return_value={
                 "docker0": mock_psutil_stats(True),
                 "br-abc123": mock_psutil_stats(True),
                 "eth0": mock_psutil_stats(True)
             }):

            from startup import get_network_ip

            result = get_network_ip()

            assert result == "10.1.0.164"

    def test_filters_vmware_adapters(self, mock_psutil_addresses, mock_psutil_stats):
        """Should filter out VMware virtual adapters."""
        with patch("pathlib.Path.exists", return_value=False), \
             patch("psutil.net_if_addrs", return_value={
                 "vmnet1": [mock_psutil_addresses(2, "192.168.10.1")],
                 "vmnet8": [mock_psutil_addresses(2, "192.168.20.1")],
                 "eth0": [mock_psutil_addresses(2, "10.1.0.164")]
             }), \
             patch("psutil.net_if_stats", return_value={
                 "vmnet1": mock_psutil_stats(True),
                 "vmnet8": mock_psutil_stats(True),
                 "eth0": mock_psutil_stats(True)
             }):

            from startup import get_network_ip

            result = get_network_ip()

            assert result == "10.1.0.164"

    def test_filters_hyperv_adapters(self, mock_psutil_addresses, mock_psutil_stats):
        """Should filter out Hyper-V virtual adapters."""
        with patch("pathlib.Path.exists", return_value=False), \
             patch("psutil.net_if_addrs", return_value={
                 "vEthernet (Default Switch)": [mock_psutil_addresses(2, "172.19.0.1")],
                 "Hyper-V Virtual Ethernet": [mock_psutil_addresses(2, "172.20.0.1")],
                 "Ethernet": [mock_psutil_addresses(2, "10.1.0.164")]
             }), \
             patch("psutil.net_if_stats", return_value={
                 "vEthernet (Default Switch)": mock_psutil_stats(True),
                 "Hyper-V Virtual Ethernet": mock_psutil_stats(True),
                 "Ethernet": mock_psutil_stats(True)
             }):

            from startup import get_network_ip

            result = get_network_ip()

            assert result == "10.1.0.164"

    def test_filters_wsl_adapters(self, mock_psutil_addresses, mock_psutil_stats):
        """Should filter out WSL virtual adapters."""
        with patch("pathlib.Path.exists", return_value=False), \
             patch("psutil.net_if_addrs", return_value={
                 "WSL": [mock_psutil_addresses(2, "172.21.0.1")],
                 "eth0": [mock_psutil_addresses(2, "10.1.0.164")]
             }), \
             patch("psutil.net_if_stats", return_value={
                 "WSL": mock_psutil_stats(True),
                 "eth0": mock_psutil_stats(True)
             }):

            from startup import get_network_ip

            result = get_network_ip()

            assert result == "10.1.0.164"


class TestLoopbackAndLinkLocalFiltering:
    """Test loopback and link-local IP filtering."""

    def test_filters_loopback_by_name(self, mock_psutil_addresses, mock_psutil_stats):
        """Should filter out loopback adapter by name."""
        with patch("pathlib.Path.exists", return_value=False), \
             patch("psutil.net_if_addrs", return_value={
                 "lo": [mock_psutil_addresses(2, "127.0.0.1")],
                 "eth0": [mock_psutil_addresses(2, "10.1.0.164")]
             }), \
             patch("psutil.net_if_stats", return_value={
                 "lo": mock_psutil_stats(True),
                 "eth0": mock_psutil_stats(True)
             }):

            from startup import get_network_ip

            result = get_network_ip()

            assert result == "10.1.0.164"

    def test_filters_loopback_by_ip(self, mock_psutil_addresses, mock_psutil_stats):
        """Should filter out 127.x.x.x addresses."""
        with patch("pathlib.Path.exists", return_value=False), \
             patch("psutil.net_if_addrs", return_value={
                 "eth0": [
                     mock_psutil_addresses(2, "127.0.0.1"),
                     mock_psutil_addresses(2, "10.1.0.164")
                 ]
             }), \
             patch("psutil.net_if_stats", return_value={
                 "eth0": mock_psutil_stats(True)
             }):

            from startup import get_network_ip

            result = get_network_ip()

            assert result == "10.1.0.164"

    def test_filters_link_local_addresses(self, mock_psutil_addresses, mock_psutil_stats):
        """Should filter out 169.254.x.x (link-local) addresses."""
        with patch("pathlib.Path.exists", return_value=False), \
             patch("psutil.net_if_addrs", return_value={
                 "eth0": [
                     mock_psutil_addresses(2, "169.254.1.1"),
                     mock_psutil_addresses(2, "10.1.0.164")
                 ]
             }), \
             patch("psutil.net_if_stats", return_value={
                 "eth0": mock_psutil_stats(True)
             }):

            from startup import get_network_ip

            result = get_network_ip()

            assert result == "10.1.0.164"

    def test_filters_windows_loopback_adapter(self, mock_psutil_addresses, mock_psutil_stats):
        """Should filter out Windows Loopback Adapter."""
        with patch("pathlib.Path.exists", return_value=False), \
             patch("psutil.net_if_addrs", return_value={
                 "Loopback Pseudo-Interface 1": [mock_psutil_addresses(2, "127.0.0.1")],
                 "Ethernet": [mock_psutil_addresses(2, "10.1.0.164")]
             }), \
             patch("psutil.net_if_stats", return_value={
                 "Loopback Pseudo-Interface 1": mock_psutil_stats(True),
                 "Ethernet": mock_psutil_stats(True)
             }):

            from startup import get_network_ip

            result = get_network_ip()

            assert result == "10.1.0.164"


class TestInactiveAdapterFiltering:
    """Test filtering of inactive network adapters."""

    def test_filters_inactive_adapters(self, mock_psutil_addresses, mock_psutil_stats):
        """Should filter out adapters with isup=False."""
        with patch("pathlib.Path.exists", return_value=False), \
             patch("psutil.net_if_addrs", return_value={
                 "eth0": [mock_psutil_addresses(2, "10.1.0.100")],
                 "eth1": [mock_psutil_addresses(2, "10.1.0.164")]
             }), \
             patch("psutil.net_if_stats", return_value={
                 "eth0": mock_psutil_stats(False),  # Inactive
                 "eth1": mock_psutil_stats(True)    # Active
             }):

            from startup import get_network_ip

            result = get_network_ip()

            assert result == "10.1.0.164"

    def test_returns_none_if_all_adapters_inactive(self, mock_psutil_addresses, mock_psutil_stats):
        """Should return None if all adapters are inactive."""
        with patch("pathlib.Path.exists", return_value=False), \
             patch("psutil.net_if_addrs", return_value={
                 "eth0": [mock_psutil_addresses(2, "10.1.0.164")]
             }), \
             patch("psutil.net_if_stats", return_value={
                 "eth0": mock_psutil_stats(False)
             }):

            from startup import get_network_ip

            result = get_network_ip()

            assert result is None


class TestErrorHandling:
    """Test error handling and edge cases."""

    def test_handles_psutil_import_error(self):
        """Should return None gracefully if psutil is not available."""
        # Mock psutil import to fail when called inside get_network_ip()
        import sys

        # Remove psutil from sys.modules if it exists
        psutil_module = sys.modules.pop('psutil', None)

        try:
            with patch("pathlib.Path.exists", return_value=False), \
                 patch.dict('sys.modules', {'psutil': None}):

                from startup import get_network_ip

                result = get_network_ip()

                assert result is None
        finally:
            # Restore psutil module if it was imported
            if psutil_module is not None:
                sys.modules['psutil'] = psutil_module

    def test_handles_psutil_runtime_error(self):
        """Should return None gracefully if psutil raises exception."""
        with patch("pathlib.Path.exists", return_value=False), \
             patch("psutil.net_if_addrs", side_effect=RuntimeError("Permission denied")):

            from startup import get_network_ip

            result = get_network_ip()

            assert result is None

    def test_handles_missing_interface_stats(self, mock_psutil_addresses):
        """Should handle missing stats for an adapter."""
        with patch("pathlib.Path.exists", return_value=False), \
             patch("psutil.net_if_addrs", return_value={
                 "eth0": [mock_psutil_addresses(2, "10.1.0.164")]
             }), \
             patch("psutil.net_if_stats", return_value={}):

            from startup import get_network_ip

            result = get_network_ip()

            # Should return None because stats indicate interface is not active
            assert result is None


class TestIPv6Filtering:
    """Test that IPv6 addresses are ignored."""

    def test_ignores_ipv6_addresses(self, mock_psutil_addresses, mock_psutil_stats):
        """Should only consider IPv4 addresses (family=2)."""
        with patch("pathlib.Path.exists", return_value=False), \
             patch("psutil.net_if_addrs", return_value={
                 "eth0": [
                     mock_psutil_addresses(10, "fe80::1"),  # IPv6 (AF_INET6 = 10)
                     mock_psutil_addresses(2, "10.1.0.164")  # IPv4 (AF_INET = 2)
                 ]
             }), \
             patch("psutil.net_if_stats", return_value={
                 "eth0": mock_psutil_stats(True)
             }):

            from startup import get_network_ip

            result = get_network_ip()

            assert result == "10.1.0.164"
