# Copyright (c) 2024-2026 GiljoAI LLC. All rights reserved.
# Licensed under the Elastic License 2.0.
# See LICENSE in the project root for terms.
# [CE] Community Edition.

"""BE-3006c (named fix 2): early_termination routed through ProjectService.

The ``GET /api/.../termination/{project_id}`` endpoint previously raw-wrote
``project.early_termination = True`` and called ``db.commit()`` directly in the
endpoint. It now routes through ``ProjectService.set_early_termination`` -- the
single-writer rule (BE-3006a) plus the transaction-ownership convention
(repositories flush, the session owner commits; the endpoint must not commit).

Two-sided:
* ``test_set_early_termination_persists`` -- the flag persists via the service.
* ``test_termination_endpoint_has_no_raw_write_or_commit`` -- a static census
  proving the endpoint no longer raw-writes the column or commits.

Parallel-safe: the service test owns its setup with a unique tenant key (shared
transactional ``db_session``); the census test only reads source.
"""

import re
import uuid
from datetime import UTC, datetime
from pathlib import Path

import pytest

from giljo_mcp.models import Product, Project


@pytest.mark.asyncio
async def test_set_early_termination_persists(project_service_with_session, db_session, test_tenant_key):
    """set_early_termination flips early_termination -> True and persists it."""
    product = Product(
        id=str(uuid.uuid4()),
        name="P",
        tenant_key=test_tenant_key,
        is_active=True,
        created_at=datetime.now(UTC),
        updated_at=datetime.now(UTC),
    )
    db_session.add(product)
    await db_session.flush()

    project = Project(
        id=str(uuid.uuid4()),
        name="Proj",
        description="early-termination test project",
        mission="m",
        tenant_key=test_tenant_key,
        product_id=product.id,
        status="active",
        early_termination=False,
        created_at=datetime.now(UTC),
        updated_at=datetime.now(UTC),
        series_number=uuid.uuid4().int % 9000 + 1,
    )
    db_session.add(project)
    await db_session.commit()

    await project_service_with_session.set_early_termination(project.id, test_tenant_key)

    await db_session.refresh(project)
    assert project.early_termination is True


_PROMPTS_ENDPOINT = Path(__file__).resolve().parents[2] / "api" / "endpoints" / "prompts.py"
_RAW_COMMIT = re.compile(r"\bdb\.commit\s*\(")
_RAW_EARLY_TERMINATION_WRITE = re.compile(r"\.early_termination\s*=\s*True")


def test_termination_endpoint_has_no_raw_write_or_commit():
    """The endpoint must route through the service: zero raw db.commit() and
    zero raw ``early_termination = True`` assignment in prompts.py."""
    source = _PROMPTS_ENDPOINT.read_text(encoding="utf-8")
    assert not _RAW_COMMIT.search(source), (
        "prompts.py must not commit directly -- route writes through the owning service"
    )
    assert not _RAW_EARLY_TERMINATION_WRITE.search(source), (
        "prompts.py must not raw-write early_termination -- route through ProjectService.set_early_termination"
    )
