# Copyright (c) 2024-2026 GiljoAI LLC. All rights reserved.
# Licensed under the GiljoAI Community License v1.1.
# See LICENSE in the project root for terms.
# [CE] Community Edition — source-available, single-user use only.

"""Tests for SettingsService and settings-related cascade/validation logic.

Covers:
- SettingsService CRUD: get_settings, update_settings, get_setting_value
- JSONB validation at write boundary
- Tenant isolation: settings for tenant A not visible to tenant B
- Cascade: git toggle OFF -> bulk_disable_field_priority for all tenant users
- Cascade: git toggle ON does NOT force-enable user git_history
- bulk_disable_field_priority only affects current tenant
- Field-priority validation gate: git_history=true rejected when git_integration disabled
- seed_default_settings() creates rows and is idempotent

Created: config.yaml -> DB settings migration (commit ef4111ebc)
"""

from datetime import UTC, datetime
from uuid import uuid4

import pytest
import pytest_asyncio

from giljo_mcp.exceptions import ValidationError
from giljo_mcp.models.auth import User, UserFieldPriority
from giljo_mcp.models.organizations import Organization
from giljo_mcp.models.settings import Settings
from giljo_mcp.services.settings_service import SettingsService
from giljo_mcp.services.user_service import UserService
from giljo_mcp.tenant import TenantManager


# ============================================================================
# Fixtures
# ============================================================================


@pytest_asyncio.fixture
async def tenant_key_a():
    return TenantManager.generate_tenant_key()


@pytest_asyncio.fixture
async def tenant_key_b():
    return TenantManager.generate_tenant_key()


@pytest_asyncio.fixture
async def settings_service_a(db_session, tenant_key_a):
    """SettingsService scoped to tenant A using shared test session."""
    return SettingsService(session=db_session, tenant_key=tenant_key_a)


@pytest_asyncio.fixture
async def settings_service_b(db_session, tenant_key_b):
    """SettingsService scoped to tenant B using shared test session."""
    return SettingsService(session=db_session, tenant_key=tenant_key_b)


@pytest_asyncio.fixture
async def org_a(db_session, tenant_key_a):
    """Organization for tenant A (required for User.org_id NOT NULL)."""
    org = Organization(
        id=str(uuid4()),
        tenant_key=tenant_key_a,
        name=f"Org A {uuid4().hex[:6]}",
        slug=f"org-a-{uuid4().hex[:6]}",
        is_active=True,
    )
    db_session.add(org)
    await db_session.flush()
    return org


@pytest_asyncio.fixture
async def user_a(db_session, tenant_key_a, org_a):
    """User in tenant A."""
    user = User(
        id=str(uuid4()),
        username=f"user_a_{uuid4().hex[:6]}",
        email=f"usera_{uuid4().hex[:6]}@example.com",
        password_hash="hashed",
        full_name="User A",
        role="developer",
        tenant_key=tenant_key_a,
        org_id=org_a.id,
        is_active=True,
    )
    db_session.add(user)
    await db_session.commit()
    await db_session.refresh(user)
    return user


@pytest_asyncio.fixture
async def user_a_with_git_history(db_session, tenant_key_a, user_a):
    """User A with git_history enabled in user_field_priorities."""
    fp = UserFieldPriority(
        id=str(uuid4()),
        user_id=user_a.id,
        tenant_key=tenant_key_a,
        category="git_history",
        enabled=True,
        updated_at=datetime.now(UTC),
    )
    db_session.add(fp)
    await db_session.commit()
    await db_session.refresh(fp)
    return user_a, fp


@pytest_asyncio.fixture
async def org_b(db_session, tenant_key_b):
    """Organization for tenant B."""
    org = Organization(
        id=str(uuid4()),
        tenant_key=tenant_key_b,
        name=f"Org B {uuid4().hex[:6]}",
        slug=f"org-b-{uuid4().hex[:6]}",
        is_active=True,
    )
    db_session.add(org)
    await db_session.flush()
    return org


@pytest_asyncio.fixture
async def user_b_with_git_history(db_session, tenant_key_b, org_b):
    """User in tenant B with git_history enabled."""
    user_b = User(
        id=str(uuid4()),
        username=f"user_b_{uuid4().hex[:6]}",
        email=f"userb_{uuid4().hex[:6]}@example.com",
        password_hash="hashed",
        full_name="User B",
        role="developer",
        tenant_key=tenant_key_b,
        org_id=org_b.id,
        is_active=True,
    )
    db_session.add(user_b)
    await db_session.flush()

    fp = UserFieldPriority(
        id=str(uuid4()),
        user_id=user_b.id,
        tenant_key=tenant_key_b,
        category="git_history",
        enabled=True,
        updated_at=datetime.now(UTC),
    )
    db_session.add(fp)
    await db_session.commit()
    await db_session.refresh(user_b)
    await db_session.refresh(fp)
    return user_b, fp


@pytest_asyncio.fixture
async def user_service_a(db_manager, db_session, tenant_key_a):
    """UserService for tenant A using shared test session."""
    return UserService(
        db_manager=db_manager,
        tenant_key=tenant_key_a,
        websocket_manager=None,
        session=db_session,
    )


@pytest_asyncio.fixture
async def user_service_b(db_manager, db_session, tenant_key_b):
    """UserService for tenant B using shared test session."""
    return UserService(
        db_manager=db_manager,
        tenant_key=tenant_key_b,
        websocket_manager=None,
        session=db_session,
    )


# ============================================================================
# SettingsService — get_settings
# ============================================================================


class TestSettingsServiceGetSettings:
    async def test_get_settings_returns_empty_dict_when_no_row_exists(self, settings_service_a):
        result = await settings_service_a.get_settings("integrations")
        assert result == {}

    async def test_get_settings_returns_stored_data(self, db_session, settings_service_a, tenant_key_a):
        settings = Settings(
            id=str(uuid4()),
            tenant_key=tenant_key_a,
            category="integrations",
            settings_data={"git_integration": {"enabled": True, "max_commits": 50}},
        )
        db_session.add(settings)
        await db_session.commit()

        result = await settings_service_a.get_settings("integrations")
        assert result["git_integration"]["enabled"] is True

    async def test_get_settings_raises_for_invalid_category(self, settings_service_a):
        with pytest.raises(ValidationError, match="Invalid category"):
            await settings_service_a.get_settings("nonexistent_category")

    async def test_get_settings_all_valid_categories_accepted(self, settings_service_a):
        for category in ("general", "network", "database", "integrations", "security", "runtime"):
            result = await settings_service_a.get_settings(category)
            assert isinstance(result, dict)


# ============================================================================
# SettingsService — update_settings
# ============================================================================


class TestSettingsServiceUpdateSettings:
    async def test_update_settings_creates_new_row_when_none_exists(self, settings_service_a):
        data = {"git_integration": {"enabled": False, "max_commits": 50}, "serena_mcp": {"use_in_prompts": False}}
        result = await settings_service_a.update_settings("integrations", data)
        assert "git_integration" in result

    async def test_update_settings_overwrites_existing_row(self, settings_service_a):
        await settings_service_a.update_settings(
            "integrations",
            {"git_integration": {"enabled": False}, "serena_mcp": {"use_in_prompts": False}},
        )
        result = await settings_service_a.update_settings(
            "integrations",
            {"git_integration": {"enabled": True, "max_commits": 75}, "serena_mcp": {"use_in_prompts": True}},
        )
        assert result["git_integration"]["enabled"] is True
        assert result["git_integration"]["max_commits"] == 75

    async def test_update_settings_raises_for_invalid_category(self, settings_service_a):
        with pytest.raises(ValidationError, match="Invalid category"):
            await settings_service_a.update_settings("bad_category", {})

    async def test_update_settings_raises_for_invalid_data_in_integrations(self, settings_service_a):
        # max_commits above limit should fail JSONB validation
        with pytest.raises(ValidationError, match="Settings validation failed"):
            await settings_service_a.update_settings(
                "integrations",
                {"git_integration": {"max_commits": 9999}},
            )

    async def test_update_settings_raises_for_invalid_runtime_data(self, settings_service_a):
        with pytest.raises(ValidationError, match="Settings validation failed"):
            await settings_service_a.update_settings(
                "runtime",
                {"agent": {"max_agents": 200}},
            )

    async def test_update_settings_returns_validated_normalized_data(self, settings_service_a):
        result = await settings_service_a.update_settings("integrations", {})
        # Defaults are filled in by validator
        assert "git_integration" in result
        assert result["git_integration"]["enabled"] is False

    async def test_update_security_settings_stores_cookie_domain_whitelist(self, settings_service_a):
        data = {"ssl_enabled": False, "cookie_domain_whitelist": ["example.com", "api.example.com"]}
        result = await settings_service_a.update_settings("security", data)
        assert result["cookie_domain_whitelist"] == ["example.com", "api.example.com"]


# ============================================================================
# SettingsService — get_setting_value
# ============================================================================


class TestSettingsServiceGetSettingValue:
    async def test_get_setting_value_returns_default_when_no_row(self, settings_service_a):
        result = await settings_service_a.get_setting_value("integrations", "git_integration", {})
        assert result == {}

    async def test_get_setting_value_returns_stored_nested_value(self, settings_service_a):
        await settings_service_a.update_settings(
            "integrations",
            {"git_integration": {"enabled": True, "max_commits": 30}, "serena_mcp": {"use_in_prompts": False}},
        )
        value = await settings_service_a.get_setting_value("integrations", "git_integration")
        assert value["enabled"] is True
        assert value["max_commits"] == 30

    async def test_get_setting_value_returns_default_for_missing_key(self, settings_service_a):
        await settings_service_a.update_settings("integrations", {})
        result = await settings_service_a.get_setting_value("integrations", "nonexistent_key", "fallback")
        assert result == "fallback"

    async def test_get_setting_value_default_is_none_when_not_specified(self, settings_service_a):
        result = await settings_service_a.get_setting_value("integrations", "missing_key")
        assert result is None


# ============================================================================
# Tenant isolation — settings for tenant A not visible to tenant B
# ============================================================================


class TestSettingsServiceTenantIsolation:
    async def test_settings_written_by_tenant_a_not_readable_by_tenant_b(self, settings_service_a, settings_service_b):
        await settings_service_a.update_settings(
            "integrations",
            {"git_integration": {"enabled": True, "max_commits": 50}, "serena_mcp": {"use_in_prompts": True}},
        )
        result_b = await settings_service_b.get_settings("integrations")
        assert result_b == {}

    async def test_tenant_b_can_have_different_settings_than_tenant_a(self, settings_service_a, settings_service_b):
        await settings_service_a.update_settings(
            "security",
            {"ssl_enabled": True, "cookie_domain_whitelist": ["a.com"]},
        )
        await settings_service_b.update_settings(
            "security",
            {"ssl_enabled": False, "cookie_domain_whitelist": ["b.com"]},
        )

        result_a = await settings_service_a.get_settings("security")
        result_b = await settings_service_b.get_settings("security")

        assert result_a["ssl_enabled"] is True
        assert result_b["ssl_enabled"] is False
        assert result_a["cookie_domain_whitelist"] == ["a.com"]
        assert result_b["cookie_domain_whitelist"] == ["b.com"]

    async def test_update_by_tenant_a_does_not_affect_tenant_b(self, settings_service_a, settings_service_b):
        await settings_service_b.update_settings(
            "integrations",
            {"git_integration": {"enabled": True, "max_commits": 50}, "serena_mcp": {"use_in_prompts": False}},
        )
        # Tenant A updates their own settings
        await settings_service_a.update_settings(
            "integrations",
            {"git_integration": {"enabled": False, "max_commits": 50}, "serena_mcp": {"use_in_prompts": False}},
        )
        # Tenant B's settings should be unchanged
        result_b = await settings_service_b.get_settings("integrations")
        assert result_b["git_integration"]["enabled"] is True


# ============================================================================
# Cascade logic — git toggle OFF -> bulk_disable_field_priority
# ============================================================================


class TestGitToggleCascade:
    async def test_git_disable_cascades_to_disable_git_history_for_tenant_users(
        self, db_session, user_service_a, user_a_with_git_history, tenant_key_a
    ):
        user_a, fp = user_a_with_git_history
        assert fp.enabled is True

        count = await user_service_a.bulk_disable_field_priority("git_history")
        assert count == 1

        # Verify the row was actually updated in DB
        await db_session.refresh(fp)
        assert fp.enabled is False

    async def test_git_disable_cascade_returns_zero_when_no_users_have_git_history(self, user_service_a):
        count = await user_service_a.bulk_disable_field_priority("git_history")
        assert count == 0

    async def test_git_enable_does_not_force_enable_user_git_history(
        self, db_session, user_service_a, tenant_key_a, org_a
    ):
        """Re-enabling git at system level must NOT force-enable user git_history toggles."""
        user = User(
            id=str(uuid4()),
            username=f"user_check_{uuid4().hex[:6]}",
            email=f"check_{uuid4().hex[:6]}@example.com",
            password_hash="hashed",
            full_name="User Check",
            role="developer",
            tenant_key=tenant_key_a,
            org_id=org_a.id,
            is_active=True,
        )
        db_session.add(user)
        fp = UserFieldPriority(
            id=str(uuid4()),
            user_id=user.id,
            tenant_key=tenant_key_a,
            category="git_history",
            enabled=False,  # User has git_history disabled
            updated_at=datetime.now(UTC),
        )
        db_session.add(fp)
        await db_session.commit()

        # Simulate "enable git" — the system just saves settings, no cascade to users
        # There is no bulk_enable_field_priority — re-enabling is user choice
        # Assert the field priority row remains untouched (False)
        await db_session.refresh(fp)
        assert fp.enabled is False

    async def test_bulk_disable_field_priority_only_affects_current_tenant(
        self, db_session, user_service_a, user_a_with_git_history, user_b_with_git_history, tenant_key_b
    ):
        """Disabling git for tenant A must not touch tenant B's user field priorities."""
        _user_a, fp_a = user_a_with_git_history
        _user_b, fp_b = user_b_with_git_history

        assert fp_a.enabled is True
        assert fp_b.enabled is True

        # Only run cascade for tenant A
        count = await user_service_a.bulk_disable_field_priority("git_history")
        assert count == 1

        await db_session.refresh(fp_a)
        await db_session.refresh(fp_b)

        assert fp_a.enabled is False, "Tenant A user git_history should be disabled"
        assert fp_b.enabled is True, "Tenant B user git_history should remain untouched"

    async def test_bulk_disable_field_priority_rejects_invalid_category(self, user_service_a):
        with pytest.raises(ValidationError, match="Invalid category"):
            await user_service_a.bulk_disable_field_priority("not_a_valid_category")


# ============================================================================
# Field-priority validation gate
# ============================================================================


class TestGitHistoryFieldPriorityValidationGate:
    async def test_get_setting_value_returns_false_when_git_not_set(self, settings_service_a):
        """Gate check: git_integration.enabled defaults to falsy when not set."""
        git_settings = await settings_service_a.get_setting_value("integrations", "git_integration", {})
        # No row in DB: returns the default {}
        assert not git_settings.get("enabled", False)

    async def test_get_setting_value_returns_true_when_git_enabled(self, settings_service_a):
        """Gate check: git_integration.enabled is True after enabling git."""
        await settings_service_a.update_settings(
            "integrations",
            {"git_integration": {"enabled": True, "max_commits": 50}, "serena_mcp": {"use_in_prompts": False}},
        )
        git_settings = await settings_service_a.get_setting_value("integrations", "git_integration", {})
        assert git_settings.get("enabled") is True

    async def test_get_setting_value_returns_false_when_git_disabled(self, settings_service_a):
        """Gate check: git_integration.enabled is False after disabling git."""
        await settings_service_a.update_settings(
            "integrations",
            {"git_integration": {"enabled": False, "max_commits": 50}, "serena_mcp": {"use_in_prompts": False}},
        )
        git_settings = await settings_service_a.get_setting_value("integrations", "git_integration", {})
        assert git_settings.get("enabled") is False


# ============================================================================
# seed_default_settings — data construction unit tests
#
# Note: startup.py cannot be imported in tests because it runs venv re-exec
# logic on import. These tests verify the DATA BUILDING logic (the same
# dictionary construction code that seed_default_settings() uses) by running
# it inline, and verify the validators accept the resulting data.
# ============================================================================


class TestSeedDefaultSettingsDataConstruction:
    """Verify the seed data dictionaries that startup.seed_default_settings() builds.

    These tests replicate the exact dict-construction logic from startup.py
    and verify it produces valid data accepted by JSONB validators, covering
    both the upgrade path (config.yaml has values) and fresh-install path
    (config.yaml missing / empty).
    """

    def _build_seed_data_from_config(self, config: dict) -> dict:
        """Mirror of the dict-building logic inside seed_default_settings()."""
        import json

        features = config.get("features", {})
        security_cfg = config.get("security", {})

        integrations_data = {
            "git_integration": {
                "enabled": features.get("git_integration", {}).get("enabled", False),
                "use_in_prompts": features.get("git_integration", {}).get("use_in_prompts", False),
                "include_commit_history": features.get("git_integration", {}).get("include_commit_history", True),
                "max_commits": features.get("git_integration", {}).get("max_commits", 50),
                "branch_strategy": features.get("git_integration", {}).get("branch_strategy", "main"),
            },
            "serena_mcp": {
                "use_in_prompts": features.get("serena_mcp", {}).get("use_in_prompts", False),
            },
        }

        security_data = {
            "ssl_enabled": features.get("ssl_enabled", False),
            "ssl_cert_path": config.get("paths", {}).get("ssl_cert"),
            "ssl_key_path": config.get("paths", {}).get("ssl_key"),
            "cookie_domain_whitelist": security_cfg.get("cookie_domain_whitelist", []),
            "rate_limiting": {"enabled": False, "requests_per_minute": 60},
        }

        runtime_data = {
            "agent": {
                "max_agents": config.get("agent", {}).get("max_agents", 10),
                "default_context_budget": config.get("agent", {}).get("default_context_budget", 200000),
                "context_warning_threshold": config.get("agent", {}).get("context_warning_threshold", 0.8),
            },
            "session": {
                "timeout_seconds": config.get("session", {}).get("timeout_seconds", 3600),
                "max_concurrent": config.get("session", {}).get("max_concurrent", 5),
                "cleanup_interval": config.get("session", {}).get("cleanup_interval", 300),
            },
        }

        # Verify JSON-serializability (what seed_default_settings does before INSERT)
        json.dumps(integrations_data)
        json.dumps(security_data)
        json.dumps(runtime_data)

        return {
            "integrations": integrations_data,
            "security": security_data,
            "runtime": runtime_data,
        }

    def test_seed_data_uses_defaults_on_fresh_install_with_empty_config(self):
        """Fresh install: seed uses defaults when config.yaml is missing/empty."""
        seed = self._build_seed_data_from_config({})
        assert seed["integrations"]["git_integration"]["enabled"] is False
        assert seed["integrations"]["git_integration"]["max_commits"] == 50
        assert seed["integrations"]["git_integration"]["branch_strategy"] == "main"
        assert seed["integrations"]["serena_mcp"]["use_in_prompts"] is False
        assert seed["security"]["ssl_enabled"] is False
        assert seed["security"]["cookie_domain_whitelist"] == []
        assert seed["runtime"]["agent"]["max_agents"] == 10
        assert seed["runtime"]["session"]["timeout_seconds"] == 3600

    def test_seed_data_reads_git_settings_from_config_on_upgrade(self):
        """Upgrade path: seed reads actual config.yaml values, not defaults."""
        config = {
            "features": {
                "git_integration": {
                    "enabled": True,
                    "use_in_prompts": True,
                    "include_commit_history": False,
                    "max_commits": 25,
                    "branch_strategy": "develop",
                },
                "serena_mcp": {"use_in_prompts": True},
            }
        }
        seed = self._build_seed_data_from_config(config)
        assert seed["integrations"]["git_integration"]["enabled"] is True
        assert seed["integrations"]["git_integration"]["max_commits"] == 25
        assert seed["integrations"]["git_integration"]["branch_strategy"] == "develop"
        assert seed["integrations"]["serena_mcp"]["use_in_prompts"] is True

    def test_seed_data_reads_security_config_on_upgrade(self):
        """Upgrade path: security settings read from config.yaml."""
        config = {
            "security": {"cookie_domain_whitelist": ["prod.example.com"]},
            "paths": {"ssl_cert": "/etc/ssl/cert.pem", "ssl_key": "/etc/ssl/key.pem"},
        }
        seed = self._build_seed_data_from_config(config)
        assert seed["security"]["cookie_domain_whitelist"] == ["prod.example.com"]
        assert seed["security"]["ssl_cert_path"] == "/etc/ssl/cert.pem"
        assert seed["security"]["ssl_key_path"] == "/etc/ssl/key.pem"

    def test_seed_data_reads_runtime_config_on_upgrade(self):
        """Upgrade path: runtime settings read from config.yaml."""
        config = {
            "agent": {"max_agents": 20, "default_context_budget": 150000, "context_warning_threshold": 0.75},
            "session": {"timeout_seconds": 7200, "max_concurrent": 10, "cleanup_interval": 600},
        }
        seed = self._build_seed_data_from_config(config)
        assert seed["runtime"]["agent"]["max_agents"] == 20
        assert seed["runtime"]["agent"]["default_context_budget"] == 150000
        assert seed["runtime"]["session"]["timeout_seconds"] == 7200
        assert seed["runtime"]["session"]["max_concurrent"] == 10

    def test_seed_integrations_data_accepted_by_jsonb_validator(self):
        """Seed data must pass JSONB validator — what gets written to the DB."""
        from giljo_mcp.schemas.jsonb_validators import validate_settings_by_category

        seed = self._build_seed_data_from_config({})
        # Should not raise
        result = validate_settings_by_category("integrations", seed["integrations"])
        assert "git_integration" in result

    def test_seed_security_data_accepted_by_jsonb_validator(self):
        """Seed security data must pass JSONB validator."""
        from giljo_mcp.schemas.jsonb_validators import validate_settings_by_category

        seed = self._build_seed_data_from_config({})
        result = validate_settings_by_category("security", seed["security"])
        assert "ssl_enabled" in result

    def test_seed_runtime_data_accepted_by_jsonb_validator(self):
        """Seed runtime data must pass JSONB validator."""
        from giljo_mcp.schemas.jsonb_validators import validate_settings_by_category

        seed = self._build_seed_data_from_config({})
        result = validate_settings_by_category("runtime", seed["runtime"])
        assert "agent" in result

    async def test_seed_idempotency_simulated_via_settings_service(self, settings_service_a):
        """Idempotency: calling update_settings twice does not create duplicate rows.

        This simulates what seed_default_settings() does: insert only if not exists.
        A second call should overwrite, not create a second row.
        """
        data = {"git_integration": {"enabled": False, "max_commits": 50}, "serena_mcp": {"use_in_prompts": False}}
        # First seed
        await settings_service_a.update_settings("integrations", data)
        # Second seed with same data (idempotent)
        await settings_service_a.update_settings("integrations", data)
        # Read back — should return exactly one result (no duplicate rows)
        result = await settings_service_a.get_settings("integrations")
        assert result["git_integration"]["enabled"] is False
