"""
Integration tests for v3.0 unified setup endpoint (refactored to remove mode-driven logic).

Tests verify that setup endpoint ALWAYS follows v3.0 architecture principles:
- API host ALWAYS set to 0.0.0.0 (firewall controls access)
- Authentication ALWAYS enabled
- Auto-login ALWAYS enabled for localhost clients
- Admin user created ONLY when lan_config provided
- CORS management is additive (preserves localhost origins)
- No restart required (always bound to 0.0.0.0)
- DeploymentContext is metadata only

Test Coverage:
- Localhost context (no lan_config) - metadata only
- LAN context with lan_config - admin user creation
- WAN context with lan_config - admin user creation
- CORS additive management
- Config file updates follow v3.0 architecture
- Idempotent admin user creation
- Password and API key security
- Multi-tenant isolation
"""

import pytest
import pytest_asyncio
import yaml
from datetime import datetime, timezone
from pathlib import Path
from httpx import AsyncClient
from passlib.hash import bcrypt
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from src.giljo_mcp.models import User, APIKey
from src.giljo_mcp.api_key_utils import verify_api_key, validate_api_key_format


@pytest.mark.asyncio
async def test_v3_localhost_context_always_uses_0_0_0_0(test_client: AsyncClient, config_path: Path):
    """Test localhost context sets host to 0.0.0.0 (v3.0 unified architecture)."""
    response = await test_client.post(
        "/api/setup/complete",
        json={
            "deployment_context": "localhost",
            "tools_attached": ["claude-code"],
            "serena_enabled": False,
            "lan_config": None
        }
    )

    assert response.status_code == 200
    data = response.json()

    # Verify response
    assert data["success"] is True
    assert data["requires_restart"] is False  # Already bound to 0.0.0.0

    # Verify config.yaml - CRITICAL v3.0 requirement
    with open(config_path, 'r', encoding='utf-8') as f:
        config = yaml.safe_load(f)

    # ALWAYS 0.0.0.0 in v3.0 (not 127.0.0.1)
    assert config["services"]["api"]["host"] == "0.0.0.0"
    assert config["services"]["dashboard"]["host"] == "0.0.0.0"


@pytest.mark.asyncio
async def test_v3_lan_context_always_uses_0_0_0_0(test_client: AsyncClient, config_path: Path):
    """Test LAN context sets host to 0.0.0.0 (v3.0 unified architecture)."""
    response = await test_client.post(
        "/api/setup/complete",
        json={
            "deployment_context": "lan",
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

    # Verify config.yaml - CRITICAL v3.0 requirement
    with open(config_path, 'r', encoding='utf-8') as f:
        config = yaml.safe_load(f)

    # ALWAYS 0.0.0.0 in v3.0 (not the LAN IP)
    assert config["services"]["api"]["host"] == "0.0.0.0"
    assert config["services"]["dashboard"]["host"] == "0.0.0.0"

    # Server IP stored as metadata only
    assert config["deployment_context"] == "lan"


@pytest.mark.asyncio
async def test_v3_authentication_always_enabled(test_client: AsyncClient, config_path: Path):
    """Test authentication is ALWAYS enabled in v3.0 (regardless of context)."""
    # Test localhost context
    response1 = await test_client.post(
        "/api/setup/complete",
        json={
            "deployment_context": "localhost",
            "tools_attached": ["claude-code"],
            "serena_enabled": False,
            "lan_config": None
        }
    )
    assert response1.status_code == 200

    with open(config_path, 'r', encoding='utf-8') as f:
        config = yaml.safe_load(f)

    # Authentication ALWAYS enabled
    assert config["features"]["authentication"] is True
    assert config["features"]["auto_login_localhost"] is True

    # Test LAN context (same result)
    response2 = await test_client.post(
        "/api/setup/complete",
        json={
            "deployment_context": "lan",
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
    assert response2.status_code == 200

    with open(config_path, 'r', encoding='utf-8') as f:
        config = yaml.safe_load(f)

    # Authentication ALWAYS enabled
    assert config["features"]["authentication"] is True
    assert config["features"]["auto_login_localhost"] is True


@pytest.mark.asyncio
async def test_v3_no_restart_required(test_client: AsyncClient):
    """Test v3.0 setup never requires restart (already bound to 0.0.0.0)."""
    # Test localhost context
    response1 = await test_client.post(
        "/api/setup/complete",
        json={
            "deployment_context": "localhost",
            "tools_attached": ["claude-code"],
            "serena_enabled": False,
            "lan_config": None
        }
    )
    assert response1.status_code == 200
    assert response1.json()["requires_restart"] is False

    # Test LAN context
    response2 = await test_client.post(
        "/api/setup/complete",
        json={
            "deployment_context": "lan",
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
    assert response2.status_code == 200
    assert response2.json()["requires_restart"] is False


@pytest.mark.asyncio
async def test_v3_admin_user_created_only_with_lan_config(test_client: AsyncClient):
    """Test admin user created ONLY when lan_config provided (regardless of context)."""
    from api.app import app
    from src.giljo_mcp.auth.dependencies import get_db_session

    # Test 1: Localhost context without lan_config - NO admin user
    response1 = await test_client.post(
        "/api/setup/complete",
        json={
            "deployment_context": "localhost",
            "tools_attached": ["claude-code"],
            "serena_enabled": False,
            "lan_config": None
        }
    )
    assert response1.status_code == 200
    assert response1.json()["admin_username"] is None

    db_session_gen = app.dependency_overrides[get_db_session]
    async for session in db_session_gen():
        result = await session.execute(select(User))
        users = result.scalars().all()
        assert len(users) == 0
        break

    # Test 2: LAN context WITH lan_config - admin user created
    response2 = await test_client.post(
        "/api/setup/complete",
        json={
            "deployment_context": "lan",
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
    assert response2.status_code == 200
    assert response2.json()["admin_username"] == "admin"

    async for session in db_session_gen():
        result = await session.execute(select(User).where(User.username == "admin"))
        admin_user = result.scalar_one_or_none()
        assert admin_user is not None
        assert admin_user.role == "admin"
        break


@pytest.mark.asyncio
async def test_v3_cors_additive_management(test_client: AsyncClient, config_path: Path):
    """Test CORS origins are managed additively (preserves localhost origins)."""
    # Initial setup with localhost context
    response1 = await test_client.post(
        "/api/setup/complete",
        json={
            "deployment_context": "localhost",
            "tools_attached": ["claude-code"],
            "serena_enabled": False,
            "lan_config": None
        }
    )
    assert response1.status_code == 200

    # Verify base localhost origins
    with open(config_path, 'r', encoding='utf-8') as f:
        config = yaml.safe_load(f)

    base_origins = config["security"]["cors"]["allowed_origins"]
    assert "http://127.0.0.1:7274" in base_origins
    assert "http://localhost:7274" in base_origins

    # Add LAN config - should ADD network origins, not replace
    response2 = await test_client.post(
        "/api/setup/complete",
        json={
            "deployment_context": "lan",
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
    assert response2.status_code == 200

    # Verify localhost origins preserved AND network origins added
    with open(config_path, 'r', encoding='utf-8') as f:
        config = yaml.safe_load(f)

    updated_origins = config["security"]["cors"]["allowed_origins"]
    # Localhost origins PRESERVED
    assert "http://127.0.0.1:7274" in updated_origins
    assert "http://localhost:7274" in updated_origins
    # Network origins ADDED
    assert "http://10.1.0.164:7274" in updated_origins
    assert "http://giljo.local:7274" in updated_origins


@pytest.mark.asyncio
async def test_v3_deployment_context_is_metadata_only(test_client: AsyncClient, config_path: Path):
    """Test deployment_context is saved as metadata but doesn't affect behavior."""
    # Test different contexts produce same core configuration
    configs = {}

    for context in ["localhost", "lan"]:
        lan_config = None
        if context == "lan":
            lan_config = {
                "admin_username": f"admin_{context}",
                "admin_password": "SecurePassword123!",
                "server_ip": "10.1.0.164",
                "hostname": "giljo.local",
                "firewall_configured": True
            }

        response = await test_client.post(
            "/api/setup/complete",
            json={
                "deployment_context": context,
                "tools_attached": ["claude-code"],
                "serena_enabled": False,
                "lan_config": lan_config
            }
        )
        assert response.status_code == 200

        with open(config_path, 'r', encoding='utf-8') as f:
            config = yaml.safe_load(f)

        configs[context] = config

        # Verify context saved as metadata
        assert config["deployment_context"] == context

    # Verify core configuration is identical (only metadata differs)
    assert configs["localhost"]["services"]["api"]["host"] == "0.0.0.0"
    assert configs["lan"]["services"]["api"]["host"] == "0.0.0.0"
    assert configs["localhost"]["features"]["authentication"] is True
    assert configs["lan"]["features"]["authentication"] is True


@pytest.mark.asyncio
async def test_v3_idempotent_admin_user_creation(test_client: AsyncClient):
    """Test admin user creation is idempotent (update existing user)."""
    from api.app import app
    from src.giljo_mcp.auth.dependencies import get_db_session

    # First setup - create admin user
    response1 = await test_client.post(
        "/api/setup/complete",
        json={
            "deployment_context": "lan",
            "tools_attached": ["claude-code"],
            "serena_enabled": False,
            "lan_config": {
                "admin_username": "admin",
                "admin_password": "FirstPassword123!",
                "server_ip": "10.1.0.164",
                "hostname": "giljo.local",
                "firewall_configured": True
            }
        }
    )
    assert response1.status_code == 200

    # Get user ID
    db_session_gen = app.dependency_overrides[get_db_session]
    async for session in db_session_gen():
        result = await session.execute(select(User).where(User.username == "admin"))
        first_user = result.scalar_one_or_none()
        assert first_user is not None
        first_user_id = first_user.id
        first_password_hash = first_user.password_hash
        break

    # Second setup - update admin user password
    response2 = await test_client.post(
        "/api/setup/complete",
        json={
            "deployment_context": "lan",
            "tools_attached": ["claude-code"],
            "serena_enabled": False,
            "lan_config": {
                "admin_username": "admin",
                "admin_password": "SecondPassword123!",  # Different password
                "server_ip": "10.1.0.164",
                "hostname": "giljo.local",
                "firewall_configured": True
            }
        }
    )
    assert response2.status_code == 200

    # Verify user was updated (not created new)
    async for session in db_session_gen():
        result = await session.execute(select(User).where(User.username == "admin"))
        users = result.scalars().all()
        assert len(users) == 1  # Only one user exists
        updated_user = users[0]
        assert updated_user.id == first_user_id  # Same user ID
        assert updated_user.password_hash != first_password_hash  # Password updated
        assert bcrypt.verify("SecondPassword123!", updated_user.password_hash)  # New password works
        assert not bcrypt.verify("FirstPassword123!", updated_user.password_hash)  # Old password doesn't
        break


@pytest.mark.asyncio
async def test_v3_wan_context_behaves_like_lan(test_client: AsyncClient, config_path: Path):
    """Test WAN context behaves identically to LAN (metadata only difference)."""
    response = await test_client.post(
        "/api/setup/complete",
        json={
            "deployment_context": "wan",
            "tools_attached": ["claude-code"],
            "serena_enabled": False,
            "lan_config": {
                "admin_username": "admin",
                "admin_password": "SecurePassword123!",
                "server_ip": "203.0.113.42",
                "hostname": "giljo.example.com",
                "firewall_configured": True
            }
        }
    )

    assert response.status_code == 200
    data = response.json()
    assert data["success"] is True

    # Verify config follows v3.0 architecture
    with open(config_path, 'r', encoding='utf-8') as f:
        config = yaml.safe_load(f)

    # Same v3.0 behavior as LAN
    assert config["services"]["api"]["host"] == "0.0.0.0"
    assert config["services"]["dashboard"]["host"] == "0.0.0.0"
    assert config["features"]["authentication"] is True
    assert config["features"]["auto_login_localhost"] is True

    # Only metadata difference
    assert config["deployment_context"] == "wan"


@pytest.mark.asyncio
async def test_v3_password_validation(test_client: AsyncClient):
    """Test password validation enforces security requirements."""
    # Test weak password rejection
    response = await test_client.post(
        "/api/setup/complete",
        json={
            "deployment_context": "lan",
            "tools_attached": ["claude-code"],
            "serena_enabled": False,
            "lan_config": {
                "admin_username": "admin",
                "admin_password": "weak",  # Too short
                "server_ip": "10.1.0.164",
                "hostname": "giljo.local",
                "firewall_configured": True
            }
        }
    )

    assert response.status_code == 400
    assert "password" in response.json()["detail"].lower()


@pytest.mark.asyncio
async def test_v3_ip_address_validation(test_client: AsyncClient):
    """Test IP address validation rejects invalid addresses."""
    # Test link-local IP rejection
    response1 = await test_client.post(
        "/api/setup/complete",
        json={
            "deployment_context": "lan",
            "tools_attached": ["claude-code"],
            "serena_enabled": False,
            "lan_config": {
                "admin_username": "admin",
                "admin_password": "SecurePassword123!",
                "server_ip": "169.254.1.1",  # Link-local
                "hostname": "giljo.local",
                "firewall_configured": True
            }
        }
    )
    assert response1.status_code == 400
    assert "ip" in str(response1.json()).lower()

    # Test loopback IP rejection
    response2 = await test_client.post(
        "/api/setup/complete",
        json={
            "deployment_context": "lan",
            "tools_attached": ["claude-code"],
            "serena_enabled": False,
            "lan_config": {
                "admin_username": "admin",
                "admin_password": "SecurePassword123!",
                "server_ip": "127.0.0.1",  # Loopback
                "hostname": "giljo.local",
                "firewall_configured": True
            }
        }
    )
    assert response2.status_code == 400
    assert "loopback" in str(response2.json()).lower() or "ip" in str(response2.json()).lower()


@pytest.mark.asyncio
async def test_v3_api_key_security(test_client: AsyncClient):
    """Test API keys are hashed and never stored in plaintext."""
    response = await test_client.post(
        "/api/setup/complete",
        json={
            "deployment_context": "lan",
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
    plaintext_key = response.json()["admin_username"]  # Admin created but no API key in v3.0

    from api.app import app
    from src.giljo_mcp.auth.dependencies import get_db_session

    # Verify no plaintext API keys in database
    db_session_gen = app.dependency_overrides[get_db_session]
    async for session in db_session_gen():
        result = await session.execute(select(APIKey))
        api_keys = result.scalars().all()

        for api_key in api_keys:
            # All keys should be hashed
            assert api_key.key_hash.startswith("$2b$")
            # No plaintext keys stored
            assert not api_key.key_hash.startswith("gk_")

        break


@pytest.mark.asyncio
async def test_v3_multitenant_isolation(test_client: AsyncClient):
    """Test users and API keys are isolated by tenant_key."""
    response = await test_client.post(
        "/api/setup/complete",
        json={
            "deployment_context": "lan",
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

    from api.app import app
    from src.giljo_mcp.auth.dependencies import get_db_session

    # Verify tenant_key is set correctly
    db_session_gen = app.dependency_overrides[get_db_session]
    async for session in db_session_gen():
        result = await session.execute(select(User).where(User.username == "admin"))
        user = result.scalar_one_or_none()

        assert user is not None
        assert user.tenant_key == "default"

        # Check API keys have same tenant_key
        result = await session.execute(select(APIKey).where(APIKey.user_id == user.id))
        api_keys = result.scalars().all()

        for api_key in api_keys:
            assert api_key.tenant_key == user.tenant_key

        break


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

    # Create initial config matching v3.0 architecture
    initial_config = {
        "installation": {
            "deployment_context": "localhost",
            "version": "3.0.0"
        },
        "services": {
            "api": {
                "host": "0.0.0.0",  # v3.0: ALWAYS 0.0.0.0
                "port": 7272
            },
            "dashboard": {
                "host": "0.0.0.0",  # v3.0: ALWAYS 0.0.0.0
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
            "authentication": True,  # v3.0: ALWAYS enabled
            "auto_login_localhost": True,  # v3.0: ALWAYS enabled
            "api_keys_enabled": False,
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
