# Copyright (c) 2024-2026 GiljoAI LLC. All rights reserved.
# Licensed under the Elastic License 2.0.
# See LICENSE in the project root for terms.
# [CE] Community Edition.

"""FE-9203 "Add default agents": locking tests for template_import.

The import is ADDITIVE ONLY and repeat-click safe:

- fresh tenant           → all 5 defaults created (orchestrator stays out)
- pristine copy present  → skipped, under its own name OR a -duplicate name
- edited default name    → pristine copy added as "<role>-duplicate",
                           is_default=False, existing row untouched
- repeat click           → no multiplication (the anti-spam core)
- two tenants            → import in one never touches the other

Parallel-safe: every test uses the ``db_session`` rollback fixture.
"""

from datetime import UTC, datetime
from uuid import uuid4

import pytest
from sqlalchemy import select

from giljo_mcp.database import tenant_session_context
from giljo_mcp.models import AgentTemplate
from giljo_mcp.template_import import import_default_templates
from giljo_mcp.template_seeder import seed_tenant_templates


pytestmark = pytest.mark.asyncio

# The 5 importable defaults (orchestrator is system-managed, never a table row).
DEFAULT_NAMES = {"implementer", "tester", "analyzer", "reviewer", "documenter"}


async def _fetch_templates(db_session, tenant_key: str) -> list[AgentTemplate]:
    with tenant_session_context(db_session, tenant_key):
        stmt = select(AgentTemplate).where(
            AgentTemplate.tenant_key == tenant_key,
            AgentTemplate.deleted_at.is_(None),
        )
        return list((await db_session.execute(stmt)).scalars().all())


async def test_fresh_tenant_imports_all_five_defaults(db_session):
    tenant_key = f"fe9203-fresh-{uuid4().hex[:8]}"

    report = await import_default_templates(db_session, tenant_key)

    assert sorted(report.added) == sorted(DEFAULT_NAMES)
    assert report.added_as_duplicate == []
    assert report.skipped_identical == []

    templates = await _fetch_templates(db_session, tenant_key)
    assert {t.name for t in templates} == DEFAULT_NAMES
    # Seed shape: active, default-flagged (no pre-existing role defaults), tagged.
    for t in templates:
        assert t.is_active is True
        assert t.is_default is True
        assert t.tags == ["default", "tenant"]
        assert "orchestrator" not in t.name


async def test_import_into_seeded_tenant_skips_everything(db_session):
    """The anti-spam core: all defaults present and pristine → nothing added."""
    tenant_key = f"fe9203-seeded-{uuid4().hex[:8]}"
    await seed_tenant_templates(db_session, tenant_key)

    report = await import_default_templates(db_session, tenant_key)

    assert report.added == []
    assert report.added_as_duplicate == []
    assert sorted(report.skipped_identical) == sorted(DEFAULT_NAMES)
    assert len(await _fetch_templates(db_session, tenant_key)) == 5


async def test_edited_default_gets_pristine_duplicate_and_stays_untouched(db_session):
    tenant_key = f"fe9203-edited-{uuid4().hex[:8]}"
    await seed_tenant_templates(db_session, tenant_key)

    # User edits the seeded implementer's prose.
    templates = await _fetch_templates(db_session, tenant_key)
    implementer = next(t for t in templates if t.name == "implementer")
    edited_prose = "MY CUSTOM IMPLEMENTER PROSE — do not clobber"
    implementer.user_instructions = edited_prose
    await db_session.commit()

    report = await import_default_templates(db_session, tenant_key)

    # Pristine copy lands under the suffixed name (house spelling of "_duplicate").
    assert report.added_as_duplicate == ["implementer-duplicate"]
    assert report.added == []
    assert sorted(report.skipped_identical) == sorted(DEFAULT_NAMES - {"implementer"})

    templates = await _fetch_templates(db_session, tenant_key)
    by_name = {t.name: t for t in templates}
    # ADDITIVE ONLY: the edited row is byte-identical to what the user wrote.
    assert by_name["implementer"].user_instructions == edited_prose
    # The duplicate is pristine and never steals the default flag.
    duplicate = by_name["implementer-duplicate"]
    assert duplicate.is_default is False
    assert duplicate.role == "implementer"
    assert "do not clobber" not in (duplicate.user_instructions or "")


async def test_repeat_click_never_multiplies_duplicates(db_session):
    """Click N times after an edit: exactly ONE duplicate ever exists."""
    tenant_key = f"fe9203-repeat-{uuid4().hex[:8]}"
    await seed_tenant_templates(db_session, tenant_key)

    templates = await _fetch_templates(db_session, tenant_key)
    implementer = next(t for t in templates if t.name == "implementer")
    implementer.user_instructions = "edited"
    await db_session.commit()

    first = await import_default_templates(db_session, tenant_key)
    second = await import_default_templates(db_session, tenant_key)
    third = await import_default_templates(db_session, tenant_key)

    assert first.added_as_duplicate == ["implementer-duplicate"]
    assert second.added_as_duplicate == []
    assert third.added_as_duplicate == []
    # The pristine duplicate now satisfies the skip check for "implementer".
    assert "implementer" in second.skipped_identical
    assert len(await _fetch_templates(db_session, tenant_key)) == 6


async def test_missing_default_is_recreated_without_stealing_default_flag(db_session):
    """Deleted default + user's own role default → import adds with is_default=False."""
    tenant_key = f"fe9203-flag-{uuid4().hex[:8]}"

    # The user's own implementer template holds the role's default flag.
    with tenant_session_context(db_session, tenant_key):
        db_session.add(
            AgentTemplate(
                id=str(uuid4()),
                tenant_key=tenant_key,
                name="implementer-mine",
                category="role",
                role="implementer",
                system_instructions="x",
                user_instructions="my own implementer",
                is_active=True,
                is_default=True,
                version="1.0.0",
                created_at=datetime.now(UTC),
            )
        )
        await db_session.commit()

    report = await import_default_templates(db_session, tenant_key)

    assert "implementer" in report.added  # name is free — created under its own name
    templates = await _fetch_templates(db_session, tenant_key)
    by_name = {t.name: t for t in templates}
    assert by_name["implementer"].is_default is False  # flag never stolen
    assert by_name["implementer-mine"].is_default is True
    assert by_name["implementer-mine"].user_instructions == "my own implementer"


async def test_two_tenant_isolation(db_session):
    tenant_a = f"fe9203-iso-a-{uuid4().hex[:8]}"
    tenant_b = f"fe9203-iso-b-{uuid4().hex[:8]}"

    report_a = await import_default_templates(db_session, tenant_a)

    assert len(report_a.added) == 5
    assert len(await _fetch_templates(db_session, tenant_a)) == 5
    assert await _fetch_templates(db_session, tenant_b) == []

    # Import for B is unaffected by A's rows.
    report_b = await import_default_templates(db_session, tenant_b)
    assert len(report_b.added) == 5
    assert len(await _fetch_templates(db_session, tenant_a)) == 5
    assert len(await _fetch_templates(db_session, tenant_b)) == 5


async def test_empty_tenant_key_rejected(db_session):
    with pytest.raises(ValueError):
        await import_default_templates(db_session, "")
