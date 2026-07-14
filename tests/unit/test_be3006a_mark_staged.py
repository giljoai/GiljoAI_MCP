# Copyright (c) 2024-2026 GiljoAI LLC. All rights reserved.
# Licensed under the Elastic License 2.0.
# See LICENSE in the project root for terms.
# [CE] Community Edition.

"""BE-3006a single-writer rule — staging-state write owned by the service.

The REST staging endpoint (``api/endpoints/prompts.py``) used to raw-write
``project.staging_status='staged'`` + ``execution_mode`` and ``db.commit()``.
That write now lives in ``ProjectStagingService.mark_staged`` (a twin of
restage/unstage), reached from the endpoint via the lifecycle facade.

These tests exercise the service directly: the staged-state + mode persist, the
implementation_launched_at lock on execution_mode is honoured, and a missing
project raises.
"""

import random
import uuid
from datetime import UTC, datetime
from unittest.mock import MagicMock

import pytest

from giljo_mcp.database import tenant_session_context
from giljo_mcp.domain.project_status import ProjectStatus
from giljo_mcp.exceptions import ResourceNotFoundError
from giljo_mcp.models import Project
from giljo_mcp.models.products import Product
from giljo_mcp.services.project_staging_service import ProjectStagingService


@pytest.fixture
def staging_service(db_session, test_tenant_key):
    """ProjectStagingService backed by the test session (mirrors the existing suite)."""
    tenant_manager = MagicMock()
    tenant_manager.get_current_tenant.return_value = test_tenant_key
    return ProjectStagingService(
        db_manager=MagicMock(),
        tenant_manager=tenant_manager,
        test_session=db_session,
    )


async def _seed_product(session, tenant_key):
    """TSK-8005: seed a real Product instead of relying on projects.product_id=NULL
    (production enforces NOT NULL via ce_0004; NULL also risks a
    uq_project_taxonomy_active NULLS-NOT-DISTINCT collision within a tenant)."""
    product = Product(id=str(uuid.uuid4()), tenant_key=tenant_key, name="Mark-Staged Test Product")
    session.add(product)
    await session.flush()
    return product


async def _seed_project(session, tenant_key, *, staging_status="staging", launched=False, execution_mode=None):
    """Seed a project as the generator leaves it (staging_status='staging')."""
    product = await _seed_product(session, tenant_key)
    project = Project(
        tenant_key=tenant_key,
        product_id=product.id,
        name="Mark-Staged Project",
        description="seeded",
        mission="seeded mission",
        status=ProjectStatus.INACTIVE,
        staging_status=staging_status,
        execution_mode=execution_mode,
        implementation_launched_at=datetime.now(UTC) if launched else None,
        series_number=random.randint(1, 9000),
    )
    session.add(project)
    await session.flush()
    return project


@pytest.mark.asyncio
async def test_mark_staged_persists_staged_and_mode(staging_service, db_session, test_tenant_key):
    """mark_staged flips 'staging' -> 'staged' and writes the resolved mode."""
    with tenant_session_context(db_session, test_tenant_key):
        project = await _seed_project(db_session, test_tenant_key, execution_mode=None)

    await staging_service.mark_staged(str(project.id), "claude_code_cli")

    assert project.staging_status == "staged"
    assert project.execution_mode == "claude_code_cli"


@pytest.mark.asyncio
async def test_mark_staged_respects_launch_lock(staging_service, db_session, test_tenant_key):
    """Once implementation has launched, mark_staged must NOT rewrite execution_mode."""
    with tenant_session_context(db_session, test_tenant_key):
        project = await _seed_project(db_session, test_tenant_key, launched=True, execution_mode="multi_terminal")

    await staging_service.mark_staged(str(project.id), "claude_code_cli")

    assert project.staging_status == "staged"
    # Locked: the original mode survives.
    assert project.execution_mode == "multi_terminal"


@pytest.mark.asyncio
async def test_mark_staged_raises_for_missing_project(staging_service):
    """A non-existent project id raises ResourceNotFoundError (maps to 404)."""
    with pytest.raises(ResourceNotFoundError):
        await staging_service.mark_staged("00000000-0000-0000-0000-000000000000", "multi_terminal")
