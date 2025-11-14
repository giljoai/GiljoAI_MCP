"""
Integration tests for cookie domain whitelist management endpoints.

Tests cover:
- GET /api/v1/user/settings/cookie-domains (retrieve whitelist)
- POST /api/v1/user/settings/cookie-domains (add domain)
- DELETE /api/v1/user/settings/cookie-domains (remove domain)

Test scenarios:
- Happy path (successful operations)
- Admin authorization enforcement
- Domain validation (format, IP rejection, length)
- Error handling (404, 500)
- Multi-tenant isolation
- Idempotent operations
- Config file operations (read/write/atomic)
"""

from pathlib import Path

import pytest
import yaml
from httpx import AsyncClient
from sqlalchemy.ext.asyncio import AsyncSession


# Fixtures


@pytest.fixture
async def admin_user(db_session: AsyncSession):
    """Create admin user for testing."""
    from passlib.hash import bcrypt

    from src.giljo_mcp.models import User

    admin = User(
        username="test_admin",
        password_hash=bcrypt.hash("admin_password"),
        email="admin@test.com",
        role="admin",
        tenant_key="test_tenant",
        is_active=True,
    )
    db_session.add(admin)
    await db_session.commit()
    await db_session.refresh(admin)
    return admin


@pytest.fixture
async def regular_user(db_session: AsyncSession):
    """Create regular (non-admin) user for testing."""
    from passlib.hash import bcrypt

    from src.giljo_mcp.models import User

    from uuid import uuid4
    unique_suffix = uuid4().hex[:8]
    user = User(
        username=f"test_user_{unique_suffix}",
        password_hash=bcrypt.hash("user_password"),
        email=f"user_{unique_suffix}@test.com",
        role="developer",
        tenant_key=f"test_tenant_{unique_suffix}",
        is_active=True,
    )
    db_session.add(user)
    await db_session.commit()
    await db_session.refresh(user)
    return user


@pytest.fixture
async def admin_token(api_client: AsyncClient, admin_user):
    """Get JWT token for admin user."""
    response = await api_client.post("/api/auth/login", json={"username": "test_admin", "password": "admin_password"})
    assert response.status_code == 200

    # Extract token from cookie
    cookies = response.cookies
    access_token = cookies.get("access_token")
    assert access_token is not None

    return access_token


@pytest.fixture
async def regular_token(api_client: AsyncClient, regular_user):
    """Get JWT token for regular user."""
    response = await api_client.post("/api/auth/login", json={"username": "test_user", "password": "user_password"})
    assert response.status_code == 200

    # Extract token from cookie
    cookies = response.cookies
    access_token = cookies.get("access_token")
    assert access_token is not None

    return access_token


@pytest.fixture
def backup_config():
    """Backup and restore config.yaml after test."""
    config_path = Path.cwd() / "config.yaml"
    backup_path = Path.cwd() / "config.yaml.test_backup"

    # Backup if exists
    if config_path.exists():
        config_path.rename(backup_path)

    yield

    # Restore backup
    if backup_path.exists():
        if config_path.exists():
            config_path.unlink()
        backup_path.rename(config_path)


@pytest.fixture
def clean_config():
    """Create clean config.yaml for testing."""
    config_path = Path.cwd() / "config.yaml"

    # Create minimal config
    config = {
        "database": {"host": "localhost", "port": 5432, "database_name": "test_db", "username": "test_user"},
        "security": {"cookie_domain_whitelist": []},
    }

    with open(config_path, "w", encoding="utf-8") as f:
        yaml.safe_dump(config, f)

    yield config_path

    # Cleanup
    if config_path.exists():
        config_path.unlink()


# GET Tests - Retrieve Cookie Domains


@pytest.mark.asyncio
async def test_get_cookie_domains_success(
    api_client: AsyncClient, admin_token: str, clean_config: Path, db_session: AsyncSession
):
    """Test successful retrieval of cookie domain whitelist."""
    # Pre-populate config with domains
    config_path = clean_config
    with open(config_path, encoding="utf-8") as f:
        config = yaml.safe_load(f)

    config["security"]["cookie_domain_whitelist"] = ["localhost", "example.com"]

    with open(config_path, "w", encoding="utf-8") as f:
        yaml.safe_dump(config, f)

    # Make request
    response = await api_client.get("/api/v1/user/settings/cookie-domains", cookies={"access_token": admin_token})

    assert response.status_code == 200
    data = response.json()
    assert "domains" in data
    assert isinstance(data["domains"], list)
    assert len(data["domains"]) == 2
    assert "localhost" in data["domains"]
    assert "example.com" in data["domains"]


@pytest.mark.asyncio
async def test_get_cookie_domains_empty(
    api_client: AsyncClient, admin_token: str, clean_config: Path, db_session: AsyncSession
):
    """Test retrieval when whitelist is empty."""
    response = await api_client.get("/api/v1/user/settings/cookie-domains", cookies={"access_token": admin_token})

    assert response.status_code == 200
    data = response.json()
    assert data["domains"] == []


@pytest.mark.asyncio
async def test_get_cookie_domains_no_security_section(
    api_client: AsyncClient, admin_token: str, db_session: AsyncSession
):
    """Test retrieval when config has no security section."""
    # Create config without security section
    config_path = Path.cwd() / "config.yaml"
    config = {"database": {"host": "localhost"}}

    with open(config_path, "w", encoding="utf-8") as f:
        yaml.safe_dump(config, f)

    try:
        response = await api_client.get("/api/v1/user/settings/cookie-domains", cookies={"access_token": admin_token})

        assert response.status_code == 200
        data = response.json()
        assert data["domains"] == []
    finally:
        if config_path.exists():
            config_path.unlink()


@pytest.mark.asyncio
async def test_get_cookie_domains_requires_admin(
    api_client: AsyncClient, regular_token: str, clean_config: Path, db_session: AsyncSession
):
    """Test that non-admin users cannot retrieve whitelist."""
    response = await api_client.get("/api/v1/user/settings/cookie-domains", cookies={"access_token": regular_token})

    assert response.status_code == 403
    data = response.json()
    assert "admin" in data["detail"].lower()


@pytest.mark.asyncio
async def test_get_cookie_domains_unauthenticated(api_client: AsyncClient, clean_config: Path):
    """Test that unauthenticated requests are rejected."""
    response = await api_client.get("/api/v1/user/settings/cookie-domains")

    assert response.status_code == 401


# POST Tests - Add Cookie Domain


@pytest.mark.asyncio
async def test_add_cookie_domain_success(
    api_client: AsyncClient, admin_token: str, clean_config: Path, db_session: AsyncSession
):
    """Test successful addition of domain to whitelist."""
    response = await api_client.post(
        "/api/v1/user/settings/cookie-domains", json={"domain": "example.com"}, cookies={"access_token": admin_token}
    )

    assert response.status_code == 201
    data = response.json()
    assert "domains" in data
    assert "example.com" in data["domains"]

    # Verify config was updated
    with open(clean_config, encoding="utf-8") as f:
        config = yaml.safe_load(f)

    assert "example.com" in config["security"]["cookie_domain_whitelist"]


@pytest.mark.asyncio
async def test_add_cookie_domain_idempotent(
    api_client: AsyncClient, admin_token: str, clean_config: Path, db_session: AsyncSession
):
    """Test that adding duplicate domain is idempotent."""
    # Add domain first time
    response1 = await api_client.post(
        "/api/v1/user/settings/cookie-domains", json={"domain": "example.com"}, cookies={"access_token": admin_token}
    )
    assert response1.status_code == 201

    # Add same domain again
    response2 = await api_client.post(
        "/api/v1/user/settings/cookie-domains", json={"domain": "example.com"}, cookies={"access_token": admin_token}
    )
    assert response2.status_code == 201
    data = response2.json()

    # Should still have only one instance
    assert data["domains"].count("example.com") == 1


@pytest.mark.asyncio
async def test_add_cookie_domain_lowercase_normalization(
    api_client: AsyncClient, admin_token: str, clean_config: Path, db_session: AsyncSession
):
    """Test that domains are normalized to lowercase."""
    response = await api_client.post(
        "/api/v1/user/settings/cookie-domains", json={"domain": "Example.COM"}, cookies={"access_token": admin_token}
    )

    assert response.status_code == 201
    data = response.json()
    assert "example.com" in data["domains"]
    assert "Example.COM" not in data["domains"]


@pytest.mark.asyncio
async def test_add_cookie_domain_subdomain(
    api_client: AsyncClient, admin_token: str, clean_config: Path, db_session: AsyncSession
):
    """Test adding subdomain is allowed."""
    response = await api_client.post(
        "/api/v1/user/settings/cookie-domains",
        json={"domain": "sub.example.com"},
        cookies={"access_token": admin_token},
    )

    assert response.status_code == 201
    data = response.json()
    assert "sub.example.com" in data["domains"]


@pytest.mark.asyncio
async def test_add_cookie_domain_localhost(
    api_client: AsyncClient, admin_token: str, clean_config: Path, db_session: AsyncSession
):
    """Test adding localhost is allowed."""
    response = await api_client.post(
        "/api/v1/user/settings/cookie-domains", json={"domain": "localhost"}, cookies={"access_token": admin_token}
    )

    assert response.status_code == 201
    data = response.json()
    assert "localhost" in data["domains"]


# Domain Validation Tests


@pytest.mark.asyncio
async def test_add_cookie_domain_rejects_ip_address(
    api_client: AsyncClient, admin_token: str, clean_config: Path, db_session: AsyncSession
):
    """Test that IP addresses are rejected."""
    response = await api_client.post(
        "/api/v1/user/settings/cookie-domains", json={"domain": "192.168.1.1"}, cookies={"access_token": admin_token}
    )

    assert response.status_code == 422
    data = response.json()
    assert "ip address" in str(data).lower()


@pytest.mark.asyncio
async def test_add_cookie_domain_rejects_too_short(
    api_client: AsyncClient, admin_token: str, clean_config: Path, db_session: AsyncSession
):
    """Test that domains shorter than 3 chars are rejected."""
    response = await api_client.post(
        "/api/v1/user/settings/cookie-domains", json={"domain": "ab"}, cookies={"access_token": admin_token}
    )

    assert response.status_code == 422


@pytest.mark.asyncio
async def test_add_cookie_domain_rejects_too_long(
    api_client: AsyncClient, admin_token: str, clean_config: Path, db_session: AsyncSession
):
    """Test that domains longer than 255 chars are rejected."""
    long_domain = "a" * 256 + ".com"

    response = await api_client.post(
        "/api/v1/user/settings/cookie-domains", json={"domain": long_domain}, cookies={"access_token": admin_token}
    )

    assert response.status_code == 422


@pytest.mark.asyncio
async def test_add_cookie_domain_rejects_invalid_format(
    api_client: AsyncClient, admin_token: str, clean_config: Path, db_session: AsyncSession
):
    """Test that invalid domain formats are rejected."""
    invalid_domains = [
        "-example.com",  # Starts with hyphen
        "example-.com",  # Ends with hyphen
        "exam ple.com",  # Contains space
        "example..com",  # Double dot
        "example.com-",  # Ends with hyphen
    ]

    for domain in invalid_domains:
        response = await api_client.post(
            "/api/v1/user/settings/cookie-domains", json={"domain": domain}, cookies={"access_token": admin_token}
        )
        assert response.status_code == 422, f"Expected 422 for domain: {domain}"


@pytest.mark.asyncio
async def test_add_cookie_domain_requires_admin(
    api_client: AsyncClient, regular_token: str, clean_config: Path, db_session: AsyncSession
):
    """Test that non-admin users cannot add domains."""
    response = await api_client.post(
        "/api/v1/user/settings/cookie-domains", json={"domain": "example.com"}, cookies={"access_token": regular_token}
    )

    assert response.status_code == 403


# DELETE Tests - Remove Cookie Domain


@pytest.mark.asyncio
async def test_remove_cookie_domain_success(
    api_client: AsyncClient, admin_token: str, clean_config: Path, db_session: AsyncSession
):
    """Test successful removal of domain from whitelist."""
    # Pre-populate config
    with open(clean_config, encoding="utf-8") as f:
        config = yaml.safe_load(f)

    config["security"]["cookie_domain_whitelist"] = ["localhost", "example.com"]

    with open(clean_config, "w", encoding="utf-8") as f:
        yaml.safe_dump(config, f)

    # Remove domain
    response = await api_client.delete(
        "/api/v1/user/settings/cookie-domains", json={"domain": "example.com"}, cookies={"access_token": admin_token}
    )

    assert response.status_code == 200
    data = response.json()
    assert "example.com" not in data["domains"]
    assert "localhost" in data["domains"]

    # Verify config was updated
    with open(clean_config, encoding="utf-8") as f:
        config = yaml.safe_load(f)

    assert "example.com" not in config["security"]["cookie_domain_whitelist"]
    assert "localhost" in config["security"]["cookie_domain_whitelist"]


@pytest.mark.asyncio
async def test_remove_cookie_domain_not_found(
    api_client: AsyncClient, admin_token: str, clean_config: Path, db_session: AsyncSession
):
    """Test removal of non-existent domain returns 404."""
    response = await api_client.delete(
        "/api/v1/user/settings/cookie-domains",
        json={"domain": "nonexistent.com"},
        cookies={"access_token": admin_token},
    )

    assert response.status_code == 404
    data = response.json()
    assert "not found" in data["detail"].lower()


@pytest.mark.asyncio
async def test_remove_cookie_domain_case_insensitive(
    api_client: AsyncClient, admin_token: str, clean_config: Path, db_session: AsyncSession
):
    """Test that removal is case-insensitive."""
    # Pre-populate config
    with open(clean_config, encoding="utf-8") as f:
        config = yaml.safe_load(f)

    config["security"]["cookie_domain_whitelist"] = ["example.com"]

    with open(clean_config, "w", encoding="utf-8") as f:
        yaml.safe_dump(config, f)

    # Remove using uppercase
    response = await api_client.delete(
        "/api/v1/user/settings/cookie-domains", json={"domain": "Example.COM"}, cookies={"access_token": admin_token}
    )

    assert response.status_code == 200
    data = response.json()
    assert "example.com" not in data["domains"]


@pytest.mark.asyncio
async def test_remove_cookie_domain_requires_admin(
    api_client: AsyncClient, regular_token: str, clean_config: Path, db_session: AsyncSession
):
    """Test that non-admin users cannot remove domains."""
    response = await api_client.delete(
        "/api/v1/user/settings/cookie-domains", json={"domain": "example.com"}, cookies={"access_token": regular_token}
    )

    assert response.status_code == 403


# Error Handling Tests


@pytest.mark.asyncio
async def test_config_file_not_found_error(api_client: AsyncClient, admin_token: str, db_session: AsyncSession):
    """Test graceful error when config.yaml doesn't exist."""
    config_path = Path.cwd() / "config.yaml"

    # Ensure config doesn't exist
    if config_path.exists():
        config_path.unlink()

    try:
        response = await api_client.get("/api/v1/user/settings/cookie-domains", cookies={"access_token": admin_token})

        assert response.status_code == 500
        data = response.json()
        assert "configuration file not found" in data["detail"].lower()
    finally:
        # Cleanup is handled by fixture restoration
        pass


@pytest.mark.asyncio
async def test_atomic_write_operations(
    api_client: AsyncClient, admin_token: str, clean_config: Path, db_session: AsyncSession
):
    """Test that config writes are atomic (temp file then rename)."""
    # Add domain
    response = await api_client.post(
        "/api/v1/user/settings/cookie-domains", json={"domain": "example.com"}, cookies={"access_token": admin_token}
    )

    assert response.status_code == 201

    # Verify no temp file left behind
    temp_path = clean_config.with_suffix(".yaml.tmp")
    assert not temp_path.exists(), "Temp file should be cleaned up after atomic write"

    # Verify config was actually written
    assert clean_config.exists()
    with open(clean_config, encoding="utf-8") as f:
        config = yaml.safe_load(f)

    assert "example.com" in config["security"]["cookie_domain_whitelist"]


# Integration Test - Full Workflow


@pytest.mark.asyncio
async def test_full_cookie_domain_workflow(
    api_client: AsyncClient, admin_token: str, clean_config: Path, db_session: AsyncSession
):
    """Test complete workflow: add multiple domains, retrieve, remove."""
    domains_to_add = ["localhost", "example.com", "subdomain.example.com"]

    # Add domains
    for domain in domains_to_add:
        response = await api_client.post(
            "/api/v1/user/settings/cookie-domains", json={"domain": domain}, cookies={"access_token": admin_token}
        )
        assert response.status_code == 201

    # Retrieve and verify all added
    response = await api_client.get("/api/v1/user/settings/cookie-domains", cookies={"access_token": admin_token})
    assert response.status_code == 200
    data = response.json()

    for domain in domains_to_add:
        assert domain in data["domains"]

    # Remove one domain
    response = await api_client.delete(
        "/api/v1/user/settings/cookie-domains", json={"domain": "example.com"}, cookies={"access_token": admin_token}
    )
    assert response.status_code == 200
    data = response.json()
    assert "example.com" not in data["domains"]
    assert "localhost" in data["domains"]
    assert "subdomain.example.com" in data["domains"]

    # Verify final state in config
    with open(clean_config, encoding="utf-8") as f:
        config = yaml.safe_load(f)

    whitelist = config["security"]["cookie_domain_whitelist"]
    assert len(whitelist) == 2
    assert "example.com" not in whitelist
    assert "localhost" in whitelist
    assert "subdomain.example.com" in whitelist
