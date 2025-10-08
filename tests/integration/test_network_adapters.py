"""
Integration tests for network adapter detection API endpoint.

Tests the /api/network/adapters endpoint that provides detailed network adapter
information for LAN deployment mode configuration. These tests follow TDD methodology.

Author: TDD Implementor Agent
Phase: TDD Red Phase (Tests should FAIL initially)
"""

import json
import pytest
import socket
from pathlib import Path
from fastapi.testclient import TestClient


@pytest.fixture
def client():
    """Create test client with isolated configuration"""
    from api.app import create_app

    app = create_app()
    return TestClient(app)


class TestNetworkAdaptersEndpoint:
    """Test GET /api/network/adapters endpoint"""

    def test_adapters_endpoint_exists(self, client):
        """Test that /api/network/adapters endpoint exists and responds"""
        response = client.get("/api/network/adapters")

        # Should not return 404 (endpoint should exist)
        assert response.status_code != 404, "Network adapters endpoint should exist"
        assert response.status_code == 200, f"Expected 200, got {response.status_code}"

    def test_adapters_returns_json(self, client):
        """Test that endpoint returns valid JSON response"""
        response = client.get("/api/network/adapters")
        assert response.status_code == 200

        # Should return valid JSON
        assert response.headers["content-type"] == "application/json"
        data = response.json()
        assert isinstance(data, dict), "Response should be JSON object"

    def test_adapters_has_required_fields(self, client):
        """Test that response contains all required fields"""
        response = client.get("/api/network/adapters")
        assert response.status_code == 200

        data = response.json()

        # Check required top-level fields
        assert "adapters" in data, "Response should have 'adapters' field"
        assert "recommended" in data, "Response should have 'recommended' field"
        assert isinstance(data["adapters"], list), "adapters should be array"

    def test_adapter_object_structure(self, client):
        """Test that each adapter has required fields with correct types"""
        response = client.get("/api/network/adapters")
        assert response.status_code == 200

        data = response.json()
        adapters = data["adapters"]

        # Should have at least one adapter on any system
        assert len(adapters) > 0, "Should detect at least one network adapter"

        # Check first adapter structure
        adapter = adapters[0]
        required_fields = [
            "name",
            "interface_id",
            "ip_address",
            "is_active",
            "is_virtual",
            "is_loopback",
        ]

        for field in required_fields:
            assert field in adapter, f"Adapter should have '{field}' field"

        # Verify field types
        assert isinstance(adapter["name"], str), "name should be string"
        assert isinstance(adapter["interface_id"], str), "interface_id should be string"
        assert isinstance(adapter["ip_address"], str), "ip_address should be string"
        assert isinstance(adapter["is_active"], bool), "is_active should be boolean"
        assert isinstance(adapter["is_virtual"], bool), "is_virtual should be boolean"
        assert isinstance(adapter["is_loopback"], bool), "is_loopback should be boolean"

    def test_adapters_exclude_loopback(self, client):
        """Test that loopback adapters (127.x.x.x) are excluded"""
        response = client.get("/api/network/adapters")
        assert response.status_code == 200

        data = response.json()
        adapters = data["adapters"]

        # No adapter should have 127.x.x.x IP
        for adapter in adapters:
            ip = adapter["ip_address"]
            assert not ip.startswith("127."), f"Loopback IP should be excluded: {ip}"

    def test_adapters_mark_virtual_adapters(self, client):
        """Test that virtual adapters are correctly marked"""
        response = client.get("/api/network/adapters")
        assert response.status_code == 200

        data = response.json()
        adapters = data["adapters"]

        # Check that adapters have is_virtual field
        for adapter in adapters:
            assert "is_virtual" in adapter
            assert isinstance(adapter["is_virtual"], bool)

            # If interface name contains virtual patterns, should be marked virtual
            interface_name = adapter["interface_id"].lower()
            virtual_patterns = ["docker", "veth", "vbox", "vmnet", "hyper-v", "wsl"]

            if any(pattern in interface_name for pattern in virtual_patterns):
                assert (
                    adapter["is_virtual"] == True
                ), f"Adapter '{adapter['interface_id']}' should be marked as virtual"

    def test_adapters_valid_ip_addresses(self, client):
        """Test that all adapters have valid IPv4 addresses"""
        response = client.get("/api/network/adapters")
        assert response.status_code == 200

        data = response.json()
        adapters = data["adapters"]

        for adapter in adapters:
            ip = adapter["ip_address"]

            # Should be valid IPv4 format
            parts = ip.split(".")
            assert len(parts) == 4, f"IPv4 address should have 4 octets: {ip}"

            for part in parts:
                assert part.isdigit(), f"IP octet should be numeric: {part}"
                octet_value = int(part)
                assert 0 <= octet_value <= 255, f"IP octet out of range: {octet_value}"

    def test_recommended_adapter_selection(self, client):
        """Test that recommended adapter is properly selected"""
        response = client.get("/api/network/adapters")
        assert response.status_code == 200

        data = response.json()
        adapters = data["adapters"]
        recommended = data.get("recommended")

        if len(adapters) > 0:
            # Should have recommended adapter if adapters exist
            assert recommended is not None, "Should recommend an adapter if adapters exist"

            # Recommended adapter should be in the adapters list
            recommended_found = False
            for adapter in adapters:
                if adapter["interface_id"] == recommended["interface_id"]:
                    recommended_found = True
                    break

            assert (
                recommended_found
            ), "Recommended adapter should exist in adapters list"

            # Recommended adapter should NOT be virtual (if non-virtual exist)
            non_virtual_exists = any(not a["is_virtual"] for a in adapters)
            if non_virtual_exists:
                assert (
                    not recommended["is_virtual"]
                ), "Should recommend physical adapter when available"

            # Recommended adapter should be active
            assert recommended["is_active"], "Recommended adapter should be active"

    def test_recommended_adapter_null_if_no_adapters(self, client, monkeypatch):
        """Test that recommended is null if no suitable adapters exist"""
        # This is a theoretical edge case - mock psutil to return no adapters
        def mock_net_if_addrs():
            return {}

        import psutil

        monkeypatch.setattr(psutil, "net_if_addrs", mock_net_if_addrs)

        response = client.get("/api/network/adapters")
        assert response.status_code == 200

        data = response.json()
        assert data["adapters"] == [], "Should have empty adapters list"
        assert data["recommended"] is None, "Recommended should be null if no adapters"

    def test_adapters_include_active_flag(self, client):
        """Test that is_active flag is present and meaningful"""
        response = client.get("/api/network/adapters")
        assert response.status_code == 200

        data = response.json()
        adapters = data["adapters"]

        for adapter in adapters:
            assert "is_active" in adapter, "Adapter should have is_active flag"

            # is_active should correlate with having an IP address
            if adapter["is_active"]:
                assert (
                    adapter["ip_address"]
                ), "Active adapter should have IP address"

    def test_adapters_cross_platform_compatibility(self, client):
        """Test that endpoint works on current platform"""
        import platform

        response = client.get("/api/network/adapters")
        assert response.status_code == 200

        data = response.json()
        adapters = data["adapters"]

        # Should work on Windows, Linux, macOS
        current_platform = platform.system()
        assert current_platform in [
            "Windows",
            "Linux",
            "Darwin",
        ], f"Test running on supported platform: {current_platform}"

        # Should detect at least one adapter on any platform
        assert len(adapters) > 0, f"Should detect adapters on {current_platform}"


class TestNetworkAdaptersEdgeCases:
    """Test edge cases and error handling"""

    def test_adapters_handles_no_psutil(self, client, monkeypatch):
        """Test graceful degradation if psutil is not available"""
        # Mock psutil import failure
        import sys

        original_import = __builtins__.__import__

        def mock_import(name, *args, **kwargs):
            if name == "psutil":
                raise ImportError("psutil not available")
            return original_import(name, *args, **kwargs)

        monkeypatch.setattr(__builtins__, "__import__", mock_import)

        response = client.get("/api/network/adapters")

        # Should either work with fallback or return 500 with clear error
        assert response.status_code in [200, 500]

        if response.status_code == 500:
            data = response.json()
            assert "error" in data or "detail" in data

    def test_adapters_handles_permission_errors(self, client, monkeypatch):
        """Test handling of permission errors when accessing network info"""

        def mock_net_if_addrs():
            raise PermissionError("Access denied")

        import psutil

        monkeypatch.setattr(psutil, "net_if_addrs", mock_net_if_addrs)

        response = client.get("/api/network/adapters")

        # Should handle gracefully
        assert response.status_code in [200, 500]

    def test_adapters_consistent_results(self, client):
        """Test that multiple calls return consistent results"""
        response1 = client.get("/api/network/adapters")
        response2 = client.get("/api/network/adapters")

        assert response1.status_code == 200
        assert response2.status_code == 200

        data1 = response1.json()
        data2 = response2.json()

        # Adapter count should be consistent
        assert len(data1["adapters"]) == len(data2["adapters"])

        # Recommended adapter should be consistent
        if data1["recommended"]:
            assert data1["recommended"]["interface_id"] == data2["recommended"][
                "interface_id"
            ]


class TestNetworkAdaptersRecommendationLogic:
    """Test recommendation algorithm"""

    def test_recommendation_prefers_physical_adapters(self, client):
        """Test that physical adapters are preferred over virtual ones"""
        response = client.get("/api/network/adapters")
        assert response.status_code == 200

        data = response.json()
        adapters = data["adapters"]
        recommended = data.get("recommended")

        # Check if there are both physical and virtual adapters
        has_physical = any(not a["is_virtual"] for a in adapters)
        has_virtual = any(a["is_virtual"] for a in adapters)

        if has_physical and has_virtual and recommended:
            # Recommended should be physical
            assert (
                not recommended["is_virtual"]
            ), "Should prefer physical over virtual adapters"

    def test_recommendation_prefers_active_adapters(self, client):
        """Test that active adapters are preferred"""
        response = client.get("/api/network/adapters")
        assert response.status_code == 200

        data = response.json()
        recommended = data.get("recommended")

        if recommended:
            assert recommended["is_active"], "Recommended adapter must be active"

    def test_recommendation_excludes_loopback(self, client):
        """Test that loopback adapters are never recommended"""
        response = client.get("/api/network/adapters")
        assert response.status_code == 200

        data = response.json()
        recommended = data.get("recommended")

        if recommended:
            assert (
                not recommended["is_loopback"]
            ), "Loopback adapter should never be recommended"


class TestNetworkAdaptersSecurity:
    """Test security aspects"""

    def test_adapters_no_authentication_required(self, client):
        """Test that endpoint is accessible without authentication (setup phase)"""
        response = client.get("/api/network/adapters")

        # Should return 200 (not 401 Unauthorized)
        assert response.status_code == 200, "Setup endpoints should not require auth"

    def test_adapters_no_sensitive_data_exposure(self, client):
        """Test that endpoint doesn't expose sensitive system information"""
        response = client.get("/api/network/adapters")
        assert response.status_code == 200

        data = response.json()
        response_str = json.dumps(data)

        # Should NOT contain sensitive data
        assert "password" not in response_str.lower()
        assert "secret" not in response_str.lower()
        # Note: "key" might be in "interface_key" so we skip that check


class TestNetworkAdaptersPerformance:
    """Test performance characteristics"""

    def test_adapters_responds_quickly(self, client):
        """Test that endpoint responds in reasonable time"""
        import time

        start_time = time.time()
        response = client.get("/api/network/adapters")
        elapsed_time = time.time() - start_time

        assert response.status_code == 200
        # Should respond within 2 seconds
        assert elapsed_time < 2.0, f"Endpoint took too long: {elapsed_time:.2f}s"


class TestNetworkAdaptersIntegration:
    """Integration tests for network adapter detection in setup workflow"""

    def test_adapters_provides_data_for_lan_setup(self, client):
        """Test that adapter detection provides necessary data for LAN configuration"""
        response = client.get("/api/network/adapters")
        assert response.status_code == 200

        data = response.json()
        adapters = data["adapters"]

        # Should provide enough information for user to choose adapter
        if len(adapters) > 0:
            adapter = adapters[0]

            # Each adapter should have user-friendly name
            assert len(adapter["name"]) > 0, "Adapter should have display name"

            # Each adapter should have unique interface_id
            assert (
                len(adapter["interface_id"]) > 0
            ), "Adapter should have interface identifier"

            # Each adapter should have IP for CORS configuration
            assert len(adapter["ip_address"]) > 0, "Adapter should have IP address"

    def test_adapters_recommended_usable_for_binding(self, client):
        """Test that recommended adapter IP can be used for server binding"""
        response = client.get("/api/network/adapters")
        assert response.status_code == 200

        data = response.json()
        recommended = data.get("recommended")

        if recommended:
            ip = recommended["ip_address"]

            # IP should be valid for binding
            assert not ip.startswith("127."), "Recommended IP should not be loopback"

            # Should be able to construct valid bind address
            bind_address = f"{ip}:7272"
            assert len(bind_address) > 10, "Should be able to construct bind address"


if __name__ == "__main__":
    pytest.main([__file__, "-v", "--tb=short"])
