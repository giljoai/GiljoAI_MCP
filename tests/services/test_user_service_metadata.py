# Copyright (c) 2024-2026 GiljoAI LLC. All rights reserved.
# Licensed under the GiljoAI Community License v1.1.
# See LICENSE in the project root for terms.
# [CE] Community Edition — source-available, single-user use only.

"""Test suite for UserService.update_user_metadata (HO 1028).

The single sanctioned write path for the skills-version tracking columns on
``users`` (``last_installed_skills_version``, ``last_update_reminder_at``).
"""

from datetime import datetime, timezone
from uuid import uuid4

import bcrypt
import pytest

from giljo_mcp.exceptions import ResourceNotFoundError, ValidationError
from giljo_mcp.models.auth import User


@pytest.mark.asyncio
async def test_update_metadata_persists_skills_version(user_service, test_user, db_session):
    result = await user_service.update_user_metadata(
        test_user.id,
        last_installed_skills_version="1.1.11",
    )
    assert result.last_installed_skills_version == "1.1.11"

    await db_session.refresh(test_user)
    assert test_user.last_installed_skills_version == "1.1.11"


@pytest.mark.asyncio
async def test_update_metadata_persists_reminder_timestamp(user_service, test_user, db_session):
    ts = datetime.now(timezone.utc)
    result = await user_service.update_user_metadata(
        test_user.id,
        last_update_reminder_at=ts,
    )
    assert result.last_update_reminder_at is not None


@pytest.mark.asyncio
async def test_update_metadata_rejects_unknown_field(user_service, test_user):
    with pytest.raises(ValidationError):
        await user_service.update_user_metadata(
            test_user.id,
            email="evil@example.com",  # NOT in metadata allowlist
        )


@pytest.mark.asyncio
async def test_update_metadata_rejects_oversized_version(user_service, test_user):
    with pytest.raises(ValidationError):
        await user_service.update_user_metadata(
            test_user.id,
            last_installed_skills_version="x" * 64,
        )


@pytest.mark.asyncio
async def test_update_metadata_rejects_wrong_type(user_service, test_user):
    with pytest.raises(ValidationError):
        await user_service.update_user_metadata(
            test_user.id,
            last_installed_skills_version=12345,
        )


@pytest.mark.asyncio
async def test_update_metadata_rejects_empty_payload(user_service, test_user):
    with pytest.raises(ValidationError):
        await user_service.update_user_metadata(test_user.id)


@pytest.mark.asyncio
async def test_update_metadata_user_not_found(user_service):
    with pytest.raises(ResourceNotFoundError):
        await user_service.update_user_metadata(
            "nonexistent-id",
            last_installed_skills_version="1.0.0",
        )


@pytest.mark.asyncio
async def test_update_metadata_tenant_isolation(user_service, db_session, test_tenant_key):
    """A user in a different tenant must NOT be writable via this service instance."""
    other_tenant = f"other_tenant_{uuid4().hex[:8]}"
    other_user = User(
        id=str(uuid4()),
        username=f"otheruser_{uuid4().hex[:6]}",
        email=f"other_{uuid4().hex[:6]}@example.com",
        password_hash=bcrypt.hashpw(b"OtherPwd123", bcrypt.gensalt()).decode("utf-8"),
        tenant_key=other_tenant,
        role="developer",
        is_active=True,
    )
    db_session.add(other_user)
    await db_session.commit()

    with pytest.raises(ResourceNotFoundError):
        await user_service.update_user_metadata(
            other_user.id,
            last_installed_skills_version="9.9.9",
        )
