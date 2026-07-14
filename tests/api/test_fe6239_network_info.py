# Copyright (c) 2024-2026 GiljoAI LLC. All rights reserved.
# Licensed under the Elastic License 2.0.
# See LICENSE in the project root for terms.
# [CE] Community Edition.

"""FE-6239 — Network settings: real responding Host IP(s) (CE).

Failing layer = ``api/endpoints/configuration.py``:

  - ``get_network_info`` is the server-level endpoint backing the Network
    settings "Host IP / Port" rows. It must report the address(es) the server
    ACTUALLY responds on (bind 0.0.0.0 -> enumerate interface IPs; loopback ->
    "localhost"; a single bound IP -> that IP) rather than blindly echoing config
    ``services.external_host`` (the INF-6236-era bug where a LAN box showed
    "localhost").

The cert trust-anchor download endpoint (``/root-ca``) is retained; INF-6241
reworked it to serve the operator-provided cert instead of a mkcert root CA.
FE-6239 only removed ``/root-ca`` from the admin Network settings tab. The
``/root-ca`` body contract is tested in ``test_inf6241_root_ca.py``.

Pure unit: the endpoint function is called directly with config IO + IP
enumeration monkeypatched, so nothing touches the real install config or host
network. xdist-safe: no module-level mutable state.
"""

from __future__ import annotations

import pytest

from api.endpoints import configuration as cfg


def _patch_config(monkeypatch, services: dict) -> None:
    """Make the endpoint's ``read_config()`` return a config with these services."""
    import giljo_mcp._config_io as cio

    monkeypatch.setattr(cio, "read_config", lambda: {"services": services})


def _patch_ips(monkeypatch, ips: list[str]) -> None:
    import installer.shared.network as net

    monkeypatch.setattr(net, "get_network_ips", lambda *a, **k: list(ips))


class TestNetworkInfoHostComputation:
    """Host IP(s) reflect what the server responds on, not config external_host."""

    @pytest.mark.asyncio
    async def test_bind_all_enumerates_interface_ips(self, monkeypatch):
        # Bound to all interfaces (LAN install) -> list every responding IP.
        _patch_config(monkeypatch, {"api": {"host": "0.0.0.0", "port": 7272}})
        _patch_ips(monkeypatch, ["192.0.2.100", "198.51.100.5"])

        result = await cfg.get_network_info(current_user=None, _ce=None)

        assert result.hosts == ["192.0.2.100", "198.51.100.5"]
        assert result.host_display == "192.0.2.100, 198.51.100.5"
        assert result.bind_all is True
        assert result.port == 7272

    @pytest.mark.asyncio
    async def test_bind_all_with_no_ips_falls_back_to_localhost(self, monkeypatch):
        # All-interfaces bind but no detectable NIC (e.g. isolated host) -> localhost.
        _patch_config(monkeypatch, {"api": {"host": "0.0.0.0", "port": 7272}})
        _patch_ips(monkeypatch, [])

        result = await cfg.get_network_info(current_user=None, _ce=None)

        assert result.hosts == ["localhost"]
        assert result.bind_all is True

    @pytest.mark.asyncio
    async def test_loopback_bind_reports_localhost(self, monkeypatch):
        # Localhost-only install -> "localhost", never an interface IP.
        _patch_config(monkeypatch, {"api": {"host": "127.0.0.1", "port": 7272}})
        # If enumeration were (wrongly) consulted, this would leak a LAN IP.
        _patch_ips(monkeypatch, ["192.0.2.100"])

        result = await cfg.get_network_info(current_user=None, _ce=None)

        assert result.hosts == ["localhost"]
        assert result.bind_all is False

    @pytest.mark.asyncio
    async def test_specific_bound_ip_is_the_only_host(self, monkeypatch):
        # Bound to one explicit IP -> that is the only responding address.
        _patch_config(monkeypatch, {"api": {"host": "203.0.113.5", "port": 9000}})
        _patch_ips(monkeypatch, ["should-not-be-used"])

        result = await cfg.get_network_info(current_user=None, _ce=None)

        assert result.hosts == ["203.0.113.5"]
        assert result.bind_all is False
        assert result.port == 9000

    @pytest.mark.asyncio
    async def test_missing_host_defaults_to_bind_all(self, monkeypatch):
        # No services.api.host configured -> mirrors run_api.get_default_host() (0.0.0.0).
        _patch_config(monkeypatch, {})
        _patch_ips(monkeypatch, ["192.0.2.100"])

        result = await cfg.get_network_info(current_user=None, _ce=None)

        assert result.hosts == ["192.0.2.100"]
        assert result.bind_all is True
        assert result.port == 7272  # default when nothing configured

    @pytest.mark.asyncio
    async def test_port_falls_back_to_frontend_then_default(self, monkeypatch):
        # api.port absent but frontend.port present -> use it.
        _patch_config(monkeypatch, {"api": {"host": "127.0.0.1"}, "frontend": {"port": 8080}})
        _patch_ips(monkeypatch, [])

        result = await cfg.get_network_info(current_user=None, _ce=None)

        assert result.port == 8080
