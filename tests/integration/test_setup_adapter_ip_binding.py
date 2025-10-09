"""
Integration tests for setup wizard adapter IP binding.

This test verifies that the setup wizard writes the selected adapter IP
to services.api.host instead of hardcoding 0.0.0.0.

Test Coverage:
- LAN mode: Wizard writes selected adapter IP to services.api.host
- LAN mode: Wizard validates IP address format
- LAN mode: Wizard falls back to 0.0.0.0 for invalid IP (with warning)
- Localhost mode: Wizard writes 127.0.0.1 (unchanged)
"""

import pytest
import pytest_asyncio
import yaml
from pathlib import Path
from httpx import AsyncClient


@pytest.mark.asyncio
async def test_lan_mode_writes_selected_adapter_ip_to_api_host(test_client: AsyncClient, config_path: Path):
    """
    Test LAN mode setup writes selected adapter IP to services.api.host.

    This is the PRIMARY test for the bug fix:
    - Previously: setup.py hardcoded "0.0.0.0" on line 485
    - Now: setup.py should use request_body.lan_config.server_ip
    """
    response = await test_client.post(
        "/api/setup/complete",
        json={
            "network_mode": "lan",
            "tools_attached": ["claude-code"],
            "serena_enabled": False,
            "lan_config": {
                "admin_username": "admin",
                "admin_password": "SecurePassword123!",
                "server_ip": "10.1.0.164",  # Selected adapter IP
                "hostname": "giljo.local",
                "firewall_configured": True,
                "adapter_name": "Ethernet",
                "adapter_id": "Ethernet"
            }
        }
    )

    assert response.status_code == 200
    data = response.json()
    assert data["success"] is True

    # CRITICAL ASSERTION: Verify config.yaml has selected adapter IP, NOT 0.0.0.0
    with open(config_path, 'r', encoding='utf-8') as f:
        config = yaml.safe_load(f)

    # This is the bug fix verification
    assert config["services"]["api"]["host"] == "10.1.0.164", \
        "Setup wizard MUST write selected adapter IP to services.api.host, NOT 0.0.0.0"


@pytest.mark.asyncio
async def test_lan_mode_different_adapter_ip(test_client: AsyncClient, config_path: Path):
    """Test LAN mode setup writes different adapter IP correctly."""
    response = await test_client.post(
        "/api/setup/complete",
        json={
            "network_mode": "lan",
            "tools_attached": ["claude-code"],
            "serena_enabled": False,
            "lan_config": {
                "admin_username": "admin",
                "admin_password": "SecurePassword123!",
                "server_ip": "192.168.1.100",  # Different IP
                "hostname": "giljo.local",
                "firewall_configured": True,
                "adapter_name": "WiFi",
                "adapter_id": "WiFi"
            }
        }
    )

    assert response.status_code == 200

    with open(config_path, 'r', encoding='utf-8') as f:
        config = yaml.safe_load(f)

    # Verify wizard wrote the selected IP, not 0.0.0.0
    assert config["services"]["api"]["host"] == "192.168.1.100"


@pytest.mark.asyncio
async def test_wan_mode_writes_selected_ip_to_api_host(test_client: AsyncClient, config_path: Path):
    """Test WAN mode setup writes selected IP to services.api.host (public IP)."""
    response = await test_client.post(
        "/api/setup/complete",
        json={
            "network_mode": "wan",
            "tools_attached": ["claude-code"],
            "serena_enabled": False,
            "lan_config": {
                "admin_username": "admin",
                "admin_password": "SecurePassword123!",
                "server_ip": "203.0.113.42",  # Public IP
                "hostname": "giljo.example.com",
                "firewall_configured": True
            }
        }
    )

    assert response.status_code == 200

    with open(config_path, 'r', encoding='utf-8') as f:
        config = yaml.safe_load(f)

    # WAN mode should also write selected IP
    assert config["services"]["api"]["host"] == "203.0.113.42"


@pytest.mark.asyncio
async def test_localhost_mode_still_writes_127_0_0_1(test_client: AsyncClient, config_path: Path):
    """Test localhost mode still writes 127.0.0.1 (unchanged behavior)."""
    response = await test_client.post(
        "/api/setup/complete",
        json={
            "network_mode": "localhost",
            "tools_attached": ["claude-code"],
            "serena_enabled": False,
            "lan_config": None
        }
    )

    assert response.status_code == 200

    with open(config_path, 'r', encoding='utf-8') as f:
        config = yaml.safe_load(f)

    # Localhost mode unchanged - still 127.0.0.1
    assert config["services"]["api"]["host"] == "127.0.0.1"


@pytest.mark.asyncio
async def test_lan_mode_ip_validation_rejects_none(test_client: AsyncClient, config_path: Path):
    """Test LAN mode validation rejects None IP address."""
    response = await test_client.post(
        "/api/setup/complete",
        json={
            "network_mode": "lan",
            "tools_attached": ["claude-code"],
            "serena_enabled": False,
            "lan_config": {
                "admin_username": "admin",
                "admin_password": "SecurePassword123!",
                "server_ip": None,  # Invalid - should be rejected by validation
                "hostname": "giljo.local",
                "firewall_configured": True
            }
        }
    )

    # Should fail validation
    assert response.status_code == 422  # Pydantic validation error


@pytest.mark.asyncio
async def test_lan_mode_ip_validation_rejects_empty_string(test_client: AsyncClient, config_path: Path):
    """Test LAN mode validation rejects empty string IP address."""
    response = await test_client.post(
        "/api/setup/complete",
        json={
            "network_mode": "lan",
            "tools_attached": ["claude-code"],
            "serena_enabled": False,
            "lan_config": {
                "admin_username": "admin",
                "admin_password": "SecurePassword123!",
                "server_ip": "",  # Invalid - should be rejected
                "hostname": "giljo.local",
                "firewall_configured": True
            }
        }
    )

    # Should fail validation
    assert response.status_code in [400, 422]


@pytest.mark.asyncio
async def test_lan_mode_server_url_uses_selected_ip(test_client: AsyncClient, config_path: Path):
    """Test server_url in response uses selected adapter IP."""
    response = await test_client.post(
        "/api/setup/complete",
        json={
            "network_mode": "lan",
            "tools_attached": ["claude-code"],
            "serena_enabled": False,
            "lan_config": {
                "admin_username": "admin",
                "admin_password": "SecurePassword123!",
                "server_ip": "10.1.0.164",
                "hostname": "giljo.local",
                "firewall_configured": True
            }
        }
    )

    assert response.status_code == 200
    data = response.json()

    # server_url should use selected IP (this already works correctly)
    assert "10.1.0.164" in data["server_url"]
    assert data["server_url"].startswith("http://10.1.0.164:")


# Fixtures

@pytest_asyncio.fixture
async def test_client():
    """Create async HTTP client for testing setup endpoints with proper database dependency override."""
    from httpx import AsyncClient, ASGITransport
    from api.app import app
    from src.giljo_mcp.database import DatabaseManager
    from src.giljo_mcp.auth.dependencies import get_db_session
    from tests.helpers.test_db_helper import PostgreSQLTestHelper
    from sqlalchemy import text

    # Ensure test database exists
    await PostgreSQLTestHelper.ensure_test_database_exists()

    # Create test database manager
    db_url = PostgreSQLTestHelper.get_test_db_url()
    test_db_manager = DatabaseManager(db_url, is_async=True)

    # Create tables
    await PostgreSQLTestHelper.create_test_tables(test_db_manager)

    # Clean all test data before each test
    async with test_db_manager.get_session_async() as session:
        await session.execute(text("TRUNCATE TABLE api_keys, users, setup_state RESTART IDENTITY CASCADE"))
        await session.commit()

    # Override get_db_session dependency to use test database
    async def override_get_db_session():
        """Override database session to use test database"""
        async with test_db_manager.get_session_async() as session:
            yield session

    app.dependency_overrides[get_db_session] = override_get_db_session

    # Set up app state for database manager (needed by setup endpoint)
    if not hasattr(app.state, "api_state"):
        class APIState:
            def __init__(self):
                self.db_manager = None

        app.state.api_state = APIState()

    app.state.api_state.db_manager = test_db_manager

    # Create async client
    transport = ASGITransport(app=app)
    async with AsyncClient(transport=transport, base_url="http://testserver") as ac:
        yield ac

    # Cleanup
    app.dependency_overrides.clear()
    if hasattr(app.state, "api_state"):
        app.state.api_state.db_manager = None
    await test_db_manager.close_async()


@pytest_asyncio.fixture
def config_path(tmp_path: Path):
    """Create a temporary config.yaml for testing."""
    config_file = tmp_path / "config.yaml"

    # Create initial config
    initial_config = {
        "installation": {
            "mode": "localhost",
            "version": "2.0.0"
        },
        "services": {
            "api": {
                "host": "127.0.0.1",
                "port": 7272
            },
            "frontend": {
                "port": 7274
            }
        },
        "security": {
            "cors": {
                "allowed_origins": [
                    "http://127.0.0.1:7274",
                    "http://localhost:7274"
                ]
            }
        },
        "features": {
            "api_keys_required": False,
            "multi_user": False
        }
    }

    with open(config_file, 'w', encoding='utf-8') as f:
        yaml.dump(initial_config, f, default_flow_style=False, sort_keys=False)

    # Monkey-patch get_config_path to use temp file
    from api.endpoints import setup
    original_get_config_path = setup.get_config_path
    setup.get_config_path = lambda: config_file

    yield config_file

    # Restore original
    setup.get_config_path = original_get_config_path
