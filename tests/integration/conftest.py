# Copyright (c) 2024-2026 GiljoAI LLC. All rights reserved.
# Licensed under the GiljoAI Community License v1.1.
# See LICENSE in the project root for terms.
# [CE] Community Edition — source-available, single-user use only.

"""
Integration test fixtures for Handover 0316
"""

from uuid import uuid4

import pytest
import pytest_asyncio
from sqlalchemy.ext.asyncio import AsyncSession

from src.giljo_mcp.models import User
from src.giljo_mcp.tenant import TenantManager


@pytest_asyncio.fixture
async def test_user(db_session: AsyncSession):
    """Create test user with tenant"""
    from src.giljo_mcp.models.organizations import Organization

    unique_suffix = uuid4().hex[:8]
    tenant_key = TenantManager.generate_tenant_key()  # 0424m: Generate before org creation

    # Create org first (0424m: org_id is NOT NULL, tenant_key required)
    org = Organization(
        name=f"Test User Org {unique_suffix}",
        slug=f"test-user-org-{unique_suffix}",
        tenant_key=tenant_key,  # 0424m: Required NOT NULL
        is_active=True,
    )
    db_session.add(org)
    await db_session.flush()

    user = User(
        username=f"testuser_{unique_suffix}",
        email=f"test_{uuid4().hex[:8]}@example.com",
        tenant_key=tenant_key,  # 0424m: Use same tenant_key
        role="developer",
        password_hash="hashed_password",
        org_id=org.id,  # Required after 0424j
    )
    db_session.add(user)
    await db_session.commit()
    await db_session.refresh(user)
    return user


@pytest.fixture(autouse=True)
def set_tenant_context(test_user: User):
    """Ensure TenantManager is set to the primary test user's tenant."""
    TenantManager.set_current_tenant(test_user.tenant_key)
    return test_user.tenant_key
