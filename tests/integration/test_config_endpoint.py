"""
Integration tests for /api/v1/config endpoint

Tests verify that the configuration endpoint returns the full config.yaml structure
including installation.mode, services, security settings, etc.

Tests follow TDD methodology - these tests define expected behavior.
"""

import asyncio
import pytest
from httpx import AsyncClient, ASGITransport
import yaml
from pathlib import Path


def get_test_client():
    """Create an AsyncClient for testing the API."""
    from api.app import app
    transport = ASGITransport(app=app)
    return AsyncClient(transport=transport, base_url="http://test")


@pytest.mark.asyncio
async def test_config_endpoint_returns_quickly():
    """
    Test that /api/v1/config endpoint responds within 2 seconds.

    CRITICAL: This endpoint should NOT hang. It must return quickly
    with the full configuration structure.
    """
    async with get_test_client() as client:
        # Set a reasonable timeout - endpoint should respond quickly
        # Use follow_redirects=True to handle trailing slash redirects
        response = await client.get("/api/v1/config", timeout=2.0, follow_redirects=True)

        assert response.status_code == 200, f"Expected 200, got {response.status_code}: {response.text}"


@pytest.mark.asyncio
async def test_config_endpoint_returns_installation_mode():
    """
    Test that config endpoint returns installation.mode field.

    The frontend expects config.installation.mode to determine
    the deployment type (localhost, lan, wan).
    """
    async with get_test_client() as client:
        response = await client.get("/api/v1/config", follow_redirects=True)

        assert response.status_code == 200
        config = response.json()

        # Frontend expects installation.mode
        assert "installation" in config, "Missing 'installation' section"
        assert "mode" in config["installation"], "Missing 'installation.mode'"

        # Mode should be one of the valid values
        mode = config["installation"]["mode"]
        assert mode in ["localhost", "local", "lan", "server", "wan"], f"Invalid mode: {mode}"


@pytest.mark.asyncio
async def test_config_endpoint_returns_services_section():
    """
    Test that config endpoint returns services.api section.

    The frontend expects config.services.api.host and config.services.api.port
    to display API binding information.
    """
    async with get_test_client() as client:
        response = await client.get("/api/v1/config", follow_redirects=True)

        assert response.status_code == 200
        config = response.json()

        # Frontend expects services.api
        assert "services" in config, "Missing 'services' section"
        assert "api" in config["services"], "Missing 'services.api'"
        assert "host" in config["services"]["api"], "Missing 'services.api.host'"
        assert "port" in config["services"]["api"], "Missing 'services.api.port'"

        # Validate types
        assert isinstance(config["services"]["api"]["host"], str)
        assert isinstance(config["services"]["api"]["port"], int)


@pytest.mark.asyncio
async def test_config_endpoint_returns_security_cors():
    """
    Test that config endpoint returns security.cors.allowed_origins.

    The frontend expects config.security.cors.allowed_origins
    to display and manage CORS settings.
    """
    async with get_test_client() as client:
        response = await client.get("/api/v1/config", follow_redirects=True)

        assert response.status_code == 200
        config = response.json()

        # Frontend expects security.cors.allowed_origins
        assert "security" in config, "Missing 'security' section"
        assert "cors" in config["security"], "Missing 'security.cors'"
        assert "allowed_origins" in config["security"]["cors"], "Missing 'security.cors.allowed_origins'"

        # Should be a list
        assert isinstance(config["security"]["cors"]["allowed_origins"], list)


@pytest.mark.asyncio
async def test_config_endpoint_matches_config_yaml_structure():
    """
    Test that config endpoint returns structure matching config.yaml.

    The endpoint should return the actual config.yaml structure,
    not a transformed/flattened version.
    """
    # Load config.yaml to compare structure
    config_path = Path.cwd() / "config.yaml"

    if config_path.exists():
        with open(config_path, 'r') as f:
            file_config = yaml.safe_load(f)

        async with get_test_client() as client:
            response = await client.get("/api/v1/config", follow_redirects=True)

            assert response.status_code == 200
            api_config = response.json()

            # Check key sections exist
            if "installation" in file_config:
                assert "installation" in api_config, "installation section missing from API response"
                assert api_config["installation"]["mode"] == file_config["installation"]["mode"]

            if "services" in file_config:
                assert "services" in api_config, "services section missing from API response"

            if "security" in file_config:
                assert "security" in api_config, "security section missing from API response"


@pytest.mark.asyncio
async def test_config_endpoint_sensitive_data_masked():
    """
    Test that sensitive data is masked in config response.

    Passwords, API keys, and other secrets should NOT be returned.
    """
    async with get_test_client() as client:
        response = await client.get("/api/v1/config", follow_redirects=True)

        assert response.status_code == 200
        config = response.json()

        # Convert to string to search for sensitive patterns
        config_str = str(config).lower()

        # Should not contain actual passwords
        assert "password" not in config_str or "****" in config_str or config_str.count("password") <= 2

        # Database password should be masked if present
        if "database" in config and "password" in config.get("database", {}):
            db_password = config["database"]["password"]
            # Should be empty string or masked
            assert db_password == "" or "*" in db_password or db_password is None


@pytest.mark.asyncio
async def test_config_endpoint_returns_complete_structure():
    """
    Test that config endpoint returns all expected top-level sections.

    The endpoint should provide a comprehensive configuration view
    for the frontend settings page.
    """
    async with get_test_client() as client:
        response = await client.get("/api/v1/config", follow_redirects=True)

        assert response.status_code == 200
        config = response.json()

        # Expected sections based on config.yaml structure
        expected_sections = [
            "installation",
            "database",
            "services",
            "features",
            "security",
            "logging",
        ]

        for section in expected_sections:
            assert section in config, f"Missing expected section: {section}"


@pytest.mark.asyncio
async def test_config_endpoint_concurrent_requests():
    """
    Test that multiple concurrent requests don't cause hanging or errors.

    The endpoint should handle concurrent requests without deadlocks.
    """
    async def make_request(client):
        return await client.get("/api/v1/config", timeout=5.0, follow_redirects=True)

    async with get_test_client() as client:
        # Make 10 concurrent requests
        tasks = [make_request(client) for _ in range(10)]
        responses = await asyncio.gather(*tasks)

        # All should succeed
        for i, response in enumerate(responses):
            assert response.status_code == 200, f"Request {i} failed with {response.status_code}"


@pytest.mark.asyncio
async def test_config_endpoint_performance():
    """
    Test that config endpoint responds quickly (< 500ms).

    Configuration loading should be fast - it's a frequently
    accessed endpoint.
    """
    import time

    async with get_test_client() as client:
        start_time = time.time()
        response = await client.get("/api/v1/config", follow_redirects=True)
        end_time = time.time()

        assert response.status_code == 200

        response_time = (end_time - start_time) * 1000  # Convert to milliseconds
        assert response_time < 500, f"Config endpoint too slow: {response_time:.0f}ms"


@pytest.mark.asyncio
async def test_config_endpoint_returns_valid_json():
    """
    Test that config endpoint returns valid, well-formed JSON.

    Response should be parseable JSON without nested string encoding.
    """
    async with get_test_client() as client:
        response = await client.get("/api/v1/config", follow_redirects=True)

        assert response.status_code == 200
        assert response.headers["content-type"] == "application/json"

        # Should parse without error
        config = response.json()
        assert isinstance(config, dict)

        # All values should be proper JSON types, not stringified
        for key, value in config.items():
            assert not isinstance(value, str) or not value.startswith("{"), \
                f"Section {key} appears to be stringified JSON: {value[:50]}"
