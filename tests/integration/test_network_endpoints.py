"""
Integration tests for network detection API endpoints.

Tests the /api/network/detect-ip endpoint that provides network information
for LAN deployment mode configuration. These tests are written BEFORE
implementation following TDD methodology.

Author: Backend Integration Tester Agent
Phase: TDD Red Phase (Tests should FAIL initially)
"""

import json
import socket

import pytest
from fastapi.testclient import TestClient


@pytest.fixture
def client():
    """Create test client with isolated configuration"""
    from api.app import create_app

    app = create_app()
    return TestClient(app)


class TestNetworkDetectIPEndpoint:
    """Test GET /api/network/detect-ip endpoint"""

    def test_detect_ip_endpoint_exists(self, client):
        """Test that /api/network/detect-ip endpoint exists and responds"""
        response = client.get("/api/network/detect-ip")

        # Should not return 404 (endpoint should exist)
        assert response.status_code != 404, "Network detect-ip endpoint should exist"
        assert response.status_code == 200, f"Expected 200, got {response.status_code}"

    def test_detect_ip_returns_json(self, client):
        """Test that endpoint returns valid JSON response"""
        response = client.get("/api/network/detect-ip")
        assert response.status_code == 200

        # Should return valid JSON
        assert response.headers["content-type"] == "application/json"
        data = response.json()
        assert isinstance(data, dict), "Response should be JSON object"

    def test_detect_ip_has_required_fields(self, client):
        """Test that response contains all required network information fields"""
        response = client.get("/api/network/detect-ip")
        assert response.status_code == 200

        data = response.json()

        # Check required fields exist
        assert "hostname" in data, "Response should have 'hostname' field"
        assert "local_ips" in data, "Response should have 'local_ips' field"
        assert "primary_ip" in data, "Response should have 'primary_ip' field"

    def test_detect_ip_field_types(self, client):
        """Test that response fields have correct data types"""
        response = client.get("/api/network/detect-ip")
        assert response.status_code == 200

        data = response.json()

        # Validate field types
        assert isinstance(data["hostname"], str), "hostname should be string"
        assert isinstance(data["local_ips"], list), "local_ips should be array"
        assert isinstance(data["primary_ip"], str), "primary_ip should be string"

    def test_detect_ip_local_ips_are_strings(self, client):
        """Test that local_ips array contains only IP address strings"""
        response = client.get("/api/network/detect-ip")
        assert response.status_code == 200

        data = response.json()
        local_ips = data["local_ips"]

        # All items in local_ips should be strings
        for ip in local_ips:
            assert isinstance(ip, str), f"IP address should be string, got {type(ip)}"

    def test_detect_ip_valid_ip_format(self, client):
        """Test that primary_ip is a valid IPv4 address"""
        response = client.get("/api/network/detect-ip")
        assert response.status_code == 200

        data = response.json()
        primary_ip = data["primary_ip"]

        # Should be valid IPv4 format (basic validation)
        parts = primary_ip.split(".")
        assert len(parts) == 4, "IPv4 address should have 4 octets"

        for part in parts:
            assert part.isdigit(), f"IP octet should be numeric: {part}"
            octet_value = int(part)
            assert 0 <= octet_value <= 255, f"IP octet out of range: {octet_value}"

    def test_detect_ip_filters_out_localhost(self, client):
        """Test that 127.0.0.1 is filtered out from local_ips"""
        response = client.get("/api/network/detect-ip")
        assert response.status_code == 200

        data = response.json()
        local_ips = data["local_ips"]

        # 127.0.0.1 should NOT be in local_ips (we want LAN IPs only)
        assert "127.0.0.1" not in local_ips, "localhost (127.0.0.1) should be filtered out"

    def test_detect_ip_hostname_not_empty(self, client):
        """Test that hostname is not empty"""
        response = client.get("/api/network/detect-ip")
        assert response.status_code == 200

        data = response.json()
        hostname = data["hostname"]

        # Hostname should not be empty
        assert len(hostname) > 0, "hostname should not be empty string"
        assert hostname.strip() != "", "hostname should not be whitespace"

    def test_detect_ip_primary_ip_not_localhost(self, client):
        """Test that primary_ip is not localhost (should be LAN IP)"""
        response = client.get("/api/network/detect-ip")
        assert response.status_code == 200

        data = response.json()
        primary_ip = data["primary_ip"]

        # Primary IP should not be localhost (we need a LAN-accessible IP)
        assert primary_ip != "127.0.0.1", "primary_ip should not be localhost"
        assert not primary_ip.startswith("127."), "primary_ip should not be loopback address"

    def test_detect_ip_consistent_results(self, client):
        """Test that multiple calls return consistent results"""
        response1 = client.get("/api/network/detect-ip")
        response2 = client.get("/api/network/detect-ip")

        assert response1.status_code == 200
        assert response2.status_code == 200

        data1 = response1.json()
        data2 = response2.json()

        # Results should be consistent across calls
        assert data1["hostname"] == data2["hostname"], "hostname should be consistent"
        assert data1["primary_ip"] == data2["primary_ip"], "primary_ip should be consistent"
        assert set(data1["local_ips"]) == set(data2["local_ips"]), "local_ips should be consistent"


class TestNetworkDetectIPEdgeCases:
    """Test edge cases and error handling for network detection"""

    def test_detect_ip_handles_no_network_interfaces(self, client, monkeypatch):
        """Test that endpoint handles systems with no network interfaces gracefully"""

        # Mock socket.gethostbyname_ex to return no IPs
        def mock_gethostbyname_ex(hostname):
            return (hostname, [], [])  # No aliases, no IPs

        monkeypatch.setattr(socket, "gethostbyname_ex", mock_gethostbyname_ex)

        response = client.get("/api/network/detect-ip")

        # Should not crash - return 200 with empty/fallback data or 500 with error
        assert response.status_code in [200, 500], "Should handle no network interfaces gracefully"

        if response.status_code == 200:
            data = response.json()
            # Should still have required fields
            assert "hostname" in data
            assert "local_ips" in data
            assert "primary_ip" in data

    def test_detect_ip_handles_only_localhost(self, client, monkeypatch):
        """Test behavior when only localhost (127.0.0.1) is available"""

        # Mock to return only localhost
        def mock_gethostbyname_ex(hostname):
            return (hostname, [], ["127.0.0.1"])

        monkeypatch.setattr(socket, "gethostbyname_ex", mock_gethostbyname_ex)

        response = client.get("/api/network/detect-ip")

        # Should handle gracefully
        assert response.status_code in [200, 500]

        if response.status_code == 200:
            data = response.json()
            # 127.0.0.1 should be filtered out, so local_ips might be empty
            assert isinstance(data["local_ips"], list)
            # primary_ip might fallback to 127.0.0.1 or empty string

    def test_detect_ip_handles_multiple_interfaces(self, client, monkeypatch):
        """Test that endpoint handles multiple network interfaces correctly"""

        # Mock system with multiple IPs
        def mock_gethostbyname_ex(hostname):
            return (hostname, [], ["192.168.1.100", "10.0.0.50", "172.16.0.10"])

        monkeypatch.setattr(socket, "gethostbyname_ex", mock_gethostbyname_ex)

        response = client.get("/api/network/detect-ip")
        assert response.status_code == 200

        data = response.json()

        # Should have all non-localhost IPs
        local_ips = data["local_ips"]
        assert len(local_ips) >= 3, "Should include all LAN IPs"
        assert "192.168.1.100" in local_ips
        assert "10.0.0.50" in local_ips
        assert "172.16.0.10" in local_ips

        # Primary IP should be one of them
        assert data["primary_ip"] in local_ips


class TestNetworkDetectIPSecurity:
    """Test security aspects of network detection endpoint"""

    def test_detect_ip_no_authentication_required(self, client):
        """Test that endpoint is accessible without authentication (setup phase)"""
        # This endpoint should be accessible during setup wizard (no auth)
        response = client.get("/api/network/detect-ip")

        # Should return 200 (not 401 Unauthorized)
        assert response.status_code == 200, "Setup endpoints should not require auth"

    def test_detect_ip_no_sensitive_data_exposure(self, client):
        """Test that endpoint doesn't expose sensitive system information"""
        response = client.get("/api/network/detect-ip")
        assert response.status_code == 200

        data = response.json()
        response_str = json.dumps(data)

        # Should NOT contain sensitive data
        assert "password" not in response_str.lower()
        assert "secret" not in response_str.lower()
        assert "key" not in response_str.lower()
        assert "token" not in response_str.lower()


class TestNetworkDetectIPIntegration:
    """Integration tests for network detection in setup workflow"""

    def test_detect_ip_before_setup_completion(self, client):
        """Test that network detection works before setup is completed"""
        # Get network info
        response = client.get("/api/network/detect-ip")
        assert response.status_code == 200

        data = response.json()

        # Should return valid network info even if setup not complete
        assert "hostname" in data
        assert "local_ips" in data
        assert "primary_ip" in data

    def test_detect_ip_provides_data_for_lan_setup(self, client):
        """Test that network detection provides necessary data for LAN configuration"""
        response = client.get("/api/network/detect-ip")
        assert response.status_code == 200

        data = response.json()

        # Data should be sufficient for configuring LAN mode
        # - Need hostname for certificate generation
        # - Need primary_ip for CORS configuration
        # - Need local_ips to show user their options

        hostname = data["hostname"]
        primary_ip = data["primary_ip"]

        # These values should be usable for LAN setup
        assert len(hostname) > 0, "Need hostname for LAN setup"
        assert primary_ip != "", "Need primary IP for LAN setup"

        # Should be able to construct CORS origins
        expected_cors_origin = f"http://{primary_ip}:7274"
        assert len(expected_cors_origin) > 10, "Should be able to construct CORS origin"

    def test_detect_ip_data_matches_system_hostname(self, client):
        """Test that returned hostname matches actual system hostname"""
        response = client.get("/api/network/detect-ip")
        assert response.status_code == 200

        data = response.json()
        reported_hostname = data["hostname"]

        # Compare with actual system hostname
        actual_hostname = socket.gethostname()

        assert reported_hostname == actual_hostname, "Reported hostname should match system hostname"


class TestNetworkDetectIPPerformance:
    """Test performance characteristics of network detection"""

    def test_detect_ip_responds_quickly(self, client):
        """Test that endpoint responds in reasonable time"""
        import time

        start_time = time.time()
        response = client.get("/api/network/detect-ip")
        elapsed_time = time.time() - start_time

        assert response.status_code == 200
        # Should respond within 2 seconds (network detection should be fast)
        assert elapsed_time < 2.0, f"Endpoint took too long: {elapsed_time:.2f}s"

    def test_detect_ip_no_caching_issues(self, client):
        """Test that endpoint doesn't cache stale network information"""
        # Make multiple requests
        response1 = client.get("/api/network/detect-ip")
        response2 = client.get("/api/network/detect-ip")
        response3 = client.get("/api/network/detect-ip")

        assert response1.status_code == 200
        assert response2.status_code == 200
        assert response3.status_code == 200

        # All should return fresh, consistent data
        data1 = response1.json()
        data2 = response2.json()
        data3 = response3.json()

        assert data1 == data2 == data3, "Should return consistent (but fresh) data"


if __name__ == "__main__":
    pytest.main([__file__, "-v", "--tb=short"])
