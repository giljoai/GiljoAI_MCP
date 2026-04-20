# Copyright (c) 2024-2026 GiljoAI LLC. All rights reserved.
# Licensed under the GiljoAI Community License v1.1.
# See LICENSE in the project root for terms.
# [CE] Community Edition — source-available, single-user use only.

"""
Tests for TenantConfigurationService (Sprint 003c).

Validates that DB-stored tenant configurations are written through the service
layer with proper tenant isolation and commit discipline.
"""

import json

import pytest
from sqlalchemy import select

from giljo_mcp.models import Configuration
from giljo_mcp.services.tenant_configuration_service import TenantConfigurationService


@pytest.mark.asyncio
class TestTenantConfigurationService:
    """Test suite for TenantConfigurationService."""

    async def test_set_configurations_creates_new(self, db_manager, db_session, test_tenant_key):
        """Service creates new configuration entries."""
        service = TenantConfigurationService(
            db_manager=db_manager,
            tenant_key=test_tenant_key,
            session=db_session,
        )

        count = await service.set_configurations({"theme": "dark", "language": "en"})

        assert count == 2

        result = await db_session.execute(select(Configuration).where(Configuration.tenant_key == test_tenant_key))
        configs = {c.key: c.value for c in result.scalars().all()}
        assert json.loads(configs["theme"]) == "dark"
        assert json.loads(configs["language"]) == "en"

    async def test_set_configurations_updates_existing(self, db_manager, db_session, test_tenant_key):
        """Service updates existing configuration entries."""
        # Seed an existing config
        existing = Configuration(
            tenant_key=test_tenant_key,
            key="theme",
            value=json.dumps("light"),
        )
        db_session.add(existing)
        await db_session.commit()

        service = TenantConfigurationService(
            db_manager=db_manager,
            tenant_key=test_tenant_key,
            session=db_session,
        )

        count = await service.set_configurations({"theme": "dark"})
        assert count == 1

        await db_session.refresh(existing)
        assert json.loads(existing.value) == "dark"

    async def test_delete_all_configurations(self, db_manager, db_session, test_tenant_key):
        """Service deletes all configuration entries for the tenant."""
        for key in ["a", "b", "c"]:
            db_session.add(Configuration(tenant_key=test_tenant_key, key=key, value=json.dumps(key)))
        await db_session.commit()

        service = TenantConfigurationService(
            db_manager=db_manager,
            tenant_key=test_tenant_key,
            session=db_session,
        )

        deleted = await service.delete_all_configurations()
        assert deleted == 3

        result = await db_session.execute(select(Configuration).where(Configuration.tenant_key == test_tenant_key))
        assert len(result.scalars().all()) == 0

    async def test_delete_returns_zero_when_empty(self, db_manager, db_session, test_tenant_key):
        """Service returns 0 when no configs exist for the tenant."""
        service = TenantConfigurationService(
            db_manager=db_manager,
            tenant_key=test_tenant_key,
            session=db_session,
        )

        deleted = await service.delete_all_configurations()
        assert deleted == 0

    async def test_tenant_isolation(self, db_manager, db_session, test_tenant_key):
        """Service only affects configs for its own tenant."""
        other_tenant = "tk_OTHER_TENANT_KEY_1234567890ab"

        # Create config in other tenant
        db_session.add(Configuration(tenant_key=other_tenant, key="secret", value=json.dumps("hidden")))
        await db_session.commit()

        service = TenantConfigurationService(
            db_manager=db_manager,
            tenant_key=test_tenant_key,
            session=db_session,
        )

        # Set config for our tenant
        await service.set_configurations({"theme": "dark"})

        # Delete our tenant's configs
        deleted = await service.delete_all_configurations()
        assert deleted == 1

        # Other tenant's config must still exist
        result = await db_session.execute(select(Configuration).where(Configuration.tenant_key == other_tenant))
        remaining = result.scalars().all()
        assert len(remaining) == 1
        assert remaining[0].key == "secret"
