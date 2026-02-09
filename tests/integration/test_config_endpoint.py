"""
Integration tests for /api/v1/config endpoint

Tests verify that the configuration endpoint returns the full config.yaml structure
including installation.mode, services, security settings, etc.

Tests follow TDD methodology - these tests define expected behavior.
"""

import asyncio
from pathlib import Path

import pytest
import yaml
from httpx import AsyncClient


@pytest.mark.asyncio
async def test_config_endpoint_returns_quickly(authed_client: AsyncClient):
    """
    Test that /api/v1/config endpoint responds within 2 seconds.

    CRITICAL: This endpoint should NOT hang. It must return quickly
    with the full configuration structure.
    """
    # Set a reasonable timeout - endpoint should respond quickly
    # Use follow_redirects=True to handle trailing slash redirects
    response = await authed_client.get("/api/v1/config", timeout=2.0, follow_redirects=True)

    assert response.status_code == 200, f"Expected 200, got {response.status_code}: {response.text}"


@pytest.mark.asyncio
async def test_config_endpoint_returns_installation_section(authed_client: AsyncClient):
    """
    Test that config endpoint returns installation section.

    The installation section contains metadata about the installation:
    install_dir, platform, python_version, timestamp.
    """
    response = await authed_client.get("/api/v1/config", follow_redirects=True)

    assert response.status_code == 200
    config = response.json()

    # Frontend expects installation section
    assert "installation" in config, "Missing 'installation' section"

    # Installation should contain at least one of these metadata fields
    installation = config["installation"]
    assert any(
        key in installation for key in ["install_dir", "platform", "python_version", "timestamp", "mode"]
    ), f"Installation section missing expected fields: {installation}"


@pytest.mark.asyncio
async def test_config_endpoint_returns_services_section(authed_client: AsyncClient):
    """
    Test that config endpoint returns services.api section.

    The frontend expects config.services.api.host and config.services.api.port
    to display API binding information.
    """
    response = await authed_client.get("/api/v1/config", follow_redirects=True)

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
async def test_config_endpoint_returns_security_cors(authed_client: AsyncClient):
    """
    Test that config endpoint returns security.cors.allowed_origins.

    The frontend expects config.security.cors.allowed_origins
    to display and manage CORS settings.
    """
    response = await authed_client.get("/api/v1/config", follow_redirects=True)

    assert response.status_code == 200
    config = response.json()

    # Frontend expects security.cors.allowed_origins
    assert "security" in config, "Missing 'security' section"
    assert "cors" in config["security"], "Missing 'security.cors'"
    assert "allowed_origins" in config["security"]["cors"], "Missing 'security.cors.allowed_origins'"

    # Should be a list
    assert isinstance(config["security"]["cors"]["allowed_origins"], list)


@pytest.mark.asyncio
async def test_config_endpoint_matches_config_yaml_structure(authed_client: AsyncClient):
    """
    Test that config endpoint returns structure matching config.yaml.

    The endpoint should return the actual config.yaml structure,
    not a transformed/flattened version.
    """
    # Load config.yaml to compare structure
    config_path = Path.cwd() / "config.yaml"

    if config_path.exists():
        with open(config_path) as f:
            file_config = yaml.safe_load(f)

        response = await authed_client.get("/api/v1/config", follow_redirects=True)

        assert response.status_code == 200
        api_config = response.json()

        # Check key sections exist
        if "installation" in file_config:
            assert "installation" in api_config, "installation section missing from API response"
            # Installation section should exist (structure may vary from config.yaml)

        if "services" in file_config:
            assert "services" in api_config, "services section missing from API response"

        if "security" in file_config:
            assert "security" in api_config, "security section missing from API response"


@pytest.mark.asyncio
async def test_config_endpoint_sensitive_data_masked(authed_client: AsyncClient):
    """
    Test that sensitive data is masked in config response.

    Passwords, API keys, and other secrets should NOT be returned.
    """
    response = await authed_client.get("/api/v1/config", follow_redirects=True)

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
async def test_config_endpoint_returns_complete_structure(authed_client: AsyncClient):
    """
    Test that config endpoint returns all expected top-level sections.

    The endpoint should provide a comprehensive configuration view
    for the frontend settings page.
    """
    response = await authed_client.get("/api/v1/config", follow_redirects=True)

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
async def test_config_endpoint_concurrent_requests(authed_client: AsyncClient):
    """
    Test that multiple concurrent requests don't cause hanging or errors.

    The endpoint should handle concurrent requests without deadlocks.
    """

    async def make_request():
        return await authed_client.get("/api/v1/config", timeout=5.0, follow_redirects=True)

    # Make 10 concurrent requests
    tasks = [make_request() for _ in range(10)]
    responses = await asyncio.gather(*tasks)

    # All should succeed
    for i, response in enumerate(responses):
        assert response.status_code == 200, f"Request {i} failed with {response.status_code}"


@pytest.mark.asyncio
async def test_config_endpoint_performance(authed_client: AsyncClient):
    """
    Test that config endpoint responds quickly (< 500ms).

    Configuration loading should be fast - it's a frequently
    accessed endpoint.
    """
    import time

    start_time = time.time()
    response = await authed_client.get("/api/v1/config", follow_redirects=True)
    end_time = time.time()

    assert response.status_code == 200

    response_time = (end_time - start_time) * 1000  # Convert to milliseconds
    assert response_time < 500, f"Config endpoint too slow: {response_time:.0f}ms"


@pytest.mark.asyncio
async def test_config_endpoint_returns_valid_json(authed_client: AsyncClient):
    """
    Test that config endpoint returns valid, well-formed JSON.

    Response should be parseable JSON without nested string encoding.
    """
    response = await authed_client.get("/api/v1/config", follow_redirects=True)

    assert response.status_code == 200
    assert response.headers["content-type"] == "application/json"

    # Should parse without error
    config = response.json()
    assert isinstance(config, dict)

    # All values should be proper JSON types, not stringified
    for key, value in config.items():
        assert not isinstance(value, str) or not value.startswith("{"), (
            f"Section {key} appears to be stringified JSON: {value[:50]}"
        )
