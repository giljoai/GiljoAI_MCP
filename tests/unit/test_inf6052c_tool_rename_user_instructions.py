# Copyright (c) 2024-2026 GiljoAI LLC. All rights reserved.
# Licensed under the Elastic License 2.0.
# See LICENSE in the project root for terms.
# [CE] Community Edition.

"""Tests for INF-6052c: seeder prose rename + user_instructions refresh + Gemini frontmatter.

Covers:
- Seeder produces new tool names in user_instructions (fresh installs see new names)
- refresh_tenant_template_instructions re-renders user_instructions for default-named rows
- refresh leaves customised / non-default rows untouched
- render_gemini_agent frontmatter carries new underscored token names
- Boot notice banner body lists all 8 rename pairs (CE-only, suppressed in SaaS)

DB tests are parallel-safe: TransactionalTestContext (db_session) + no module globals.

Edition Scope: Both (CE + SaaS). The migration + refresh path run on both; the
boot NOTICE is CE-only.
"""

from uuid import uuid4

import pytest
import pytest_asyncio
from sqlalchemy.ext.asyncio import AsyncSession

from giljo_mcp.database import tenant_session_context
from giljo_mcp.models import AgentTemplate
from giljo_mcp.template_refresh import refresh_tenant_template_instructions
from giljo_mcp.template_seeder import (
    _get_default_templates_v103,
    seed_tenant_templates,
)


_OLD_NAMES = [
    "get_agent_mission",
    "update_agent_mission",
    "fetch_context",
    "write_360_memory",
    "close_project_and_update_memory",
    "inspect_messages",
    "update_product_fields",
    "submit_tuning_review",
]
_NEW_NAMES = [
    "get_job_mission",
    "update_job_mission",
    "get_context",
    "write_memory_entry",
    "write_project_closeout",
    "get_messages",
    "update_product_context",
    "propose_product_context_update",
]

_DEFAULT_TEMPLATE_NAMES = {t["name"] for t in _get_default_templates_v103()}


# ---------------------------------------------------------------------------
# Seeder prose
# ---------------------------------------------------------------------------


class TestSeederProduceNewNames:
    """Seeder source contains new tool names; no old names survive in user_instructions."""

    def test_no_old_names_in_default_templates(self):
        templates = _get_default_templates_v103()
        for template in templates:
            ui = template.get("user_instructions", "")
            for old in _OLD_NAMES:
                assert old not in ui, (
                    f"Old tool name '{old}' still present in template "
                    f"'{template['name']}' user_instructions — rename incomplete"
                )

    def test_orchestrator_has_new_mission_name(self):
        templates = _get_default_templates_v103()
        orch = next(t for t in templates if t["role"] == "orchestrator")
        assert "get_job_mission" in orch["user_instructions"]

    def test_orchestrator_has_new_context_name(self):
        templates = _get_default_templates_v103()
        orch = next(t for t in templates if t["role"] == "orchestrator")
        assert "get_context" in orch["user_instructions"]
        assert "fetch_context" not in orch["user_instructions"]

    def test_orchestrator_has_new_closeout_name(self):
        templates = _get_default_templates_v103()
        orch = next(t for t in templates if t["role"] == "orchestrator")
        assert "write_project_closeout" in orch["user_instructions"]
        assert "close_project_and_update_memory" not in orch["user_instructions"]


# ---------------------------------------------------------------------------
# refresh_tenant_template_instructions re-renders user_instructions
# ---------------------------------------------------------------------------


@pytest_asyncio.fixture
async def seeded_tenant(db_session: AsyncSession):
    """Seed a fresh tenant with default templates and return its key."""
    tenant_key = f"refresh_test_{uuid4().hex[:8]}"
    from giljo_mcp.models.organizations import Organization

    org = Organization(
        id=str(uuid4()),
        tenant_key=tenant_key,
        name=f"Org {tenant_key}",
        slug=tenant_key,
        is_active=True,
    )
    db_session.add(org)
    await db_session.commit()

    await seed_tenant_templates(db_session, tenant_key)
    return tenant_key


@pytest_asyncio.fixture
async def tenant_with_stale_user_instructions(db_session: AsyncSession):
    """Seed a tenant, then overwrite user_instructions with old tool names to simulate
    a pre-rename DB row — the starting condition ce_0049 must heal."""
    tenant_key = f"stale_test_{uuid4().hex[:8]}"
    from giljo_mcp.models.organizations import Organization

    org = Organization(
        id=str(uuid4()),
        tenant_key=tenant_key,
        name=f"Org {tenant_key}",
        slug=tenant_key,
        is_active=True,
    )
    db_session.add(org)
    await db_session.commit()

    await seed_tenant_templates(db_session, tenant_key)

    # Patch user_instructions to inject old names (simulates rows created before rename)
    with tenant_session_context(db_session, tenant_key):
        from sqlalchemy import select

        result = await db_session.execute(select(AgentTemplate).where(AgentTemplate.tenant_key == tenant_key))
        templates = result.scalars().all()
        for t in templates:
            if t.name in _DEFAULT_TEMPLATE_NAMES:
                t.user_instructions = (
                    "Call get_agent_mission(job_id) first. "
                    "Then fetch_context for details. "
                    "Finally close_project_and_update_memory()."
                )
        await db_session.commit()

    return tenant_key


@pytest.mark.asyncio
async def test_refresh_rewrites_user_instructions_for_default_templates(
    db_session: AsyncSession, tenant_with_stale_user_instructions
):
    """refresh(force=True) re-renders user_instructions for default-named rows.

    BE-9019: refresh now PRESERVES diverged (user-edited) default-named prose by
    default; the deliberate operator heal that rewrites stale rows is the force=True
    path (edits are archived first). This test exercises that force path — the
    preserve-by-default contract is covered in test_be9019_template_refresh_preserve.
    """
    tenant_key = tenant_with_stale_user_instructions
    report = await refresh_tenant_template_instructions(db_session, tenant_key, force=True)
    assert report.user_instructions_rewritten > 0

    with tenant_session_context(db_session, tenant_key):
        from sqlalchemy import select

        result = await db_session.execute(select(AgentTemplate).where(AgentTemplate.tenant_key == tenant_key))
        templates = result.scalars().all()

    for t in templates:
        if t.name in _DEFAULT_TEMPLATE_NAMES:
            for old in _OLD_NAMES:
                # Old names injected during setup must be gone after refresh
                assert old not in t.user_instructions, (
                    f"Old tool name '{old}' still in template '{t.name}' after refresh"
                )


@pytest.mark.asyncio
async def test_refresh_leaves_customised_template_untouched(db_session: AsyncSession, seeded_tenant):
    """Custom template (non-default name) keeps user_instructions after refresh."""
    tenant_key = seeded_tenant
    custom_name = "my_custom_agent"
    custom_instructions = "Call get_agent_mission and fetch_context here — USER CUSTOMISED, do not touch."

    custom = AgentTemplate(
        id=str(uuid4()),
        tenant_key=tenant_key,
        name=custom_name,
        category="role",
        role="custom",
        cli_tool="claude",
        background_color="#000000",
        description="Custom agent",
        system_instructions="",
        user_instructions=custom_instructions,
        model="sonnet",
        tools=None,
        variables=[],
        behavioral_rules=[],
        success_criteria=[],
        tool="claude",
        version="1.0.0",
        is_active=True,
        is_default=False,
        tags=["custom"],
    )
    with tenant_session_context(db_session, tenant_key):
        db_session.add(custom)
        await db_session.commit()

    await refresh_tenant_template_instructions(db_session, tenant_key)

    with tenant_session_context(db_session, tenant_key):
        from sqlalchemy import select

        result = await db_session.execute(
            select(AgentTemplate).where(
                AgentTemplate.tenant_key == tenant_key,
                AgentTemplate.name == custom_name,
            )
        )
        reloaded = result.scalar_one()

    # Custom template user_instructions must be exactly unchanged
    assert reloaded.user_instructions == custom_instructions


@pytest.mark.asyncio
async def test_refresh_default_templates_match_seeder_source(
    db_session: AsyncSession, tenant_with_stale_user_instructions
):
    """After a force refresh, default-template user_instructions match what the seeder would produce.

    BE-9019: force=True because the fixture's stale prose diverges from the shipped
    default and would otherwise be preserved (see test_be9019_template_refresh_preserve).
    """
    tenant_key = tenant_with_stale_user_instructions
    await refresh_tenant_template_instructions(db_session, tenant_key, force=True)

    expected_by_name = {t["name"]: t["user_instructions"] for t in _get_default_templates_v103()}

    with tenant_session_context(db_session, tenant_key):
        from sqlalchemy import select

        result = await db_session.execute(select(AgentTemplate).where(AgentTemplate.tenant_key == tenant_key))
        templates = result.scalars().all()

    for t in templates:
        if t.name in expected_by_name:
            # The refreshed prose must contain the expected seed text as a substring.
            # (orchestrator appends context response section on top, so exact equality
            # is not required — just that the seed prose is present.)
            expected_fragment = expected_by_name[t.name][:100]
            assert expected_fragment in t.user_instructions, (
                f"Template '{t.name}': refreshed user_instructions does not start with the seeder-defined prose"
            )


# ---------------------------------------------------------------------------
# render_gemini_agent frontmatter token names
# ---------------------------------------------------------------------------


class TestGeminiFrontmatterTokenNames:
    """render_gemini_agent produces new underscored token names in frontmatter tools list."""

    def _make_template(self, name: str = "orchestrator") -> AgentTemplate:
        return AgentTemplate(
            name=name,
            role=name,
            description=f"{name} template",
            system_instructions="",
            user_instructions="test",
            model="sonnet",
            cli_tool="gemini",
            background_color="#000",
            tools=None,
            behavioral_rules=[],
            success_criteria=[],
        )

    def test_new_mission_token_present(self):
        from giljo_mcp.template_renderer import render_gemini_agent

        result = render_gemini_agent(self._make_template())
        yaml_text = result
        assert "mcp_giljo_mcp_get_job_mission" in yaml_text

    def test_old_mission_token_absent(self):
        from giljo_mcp.template_renderer import render_gemini_agent

        result = render_gemini_agent(self._make_template())
        assert "mcp_giljo_mcp_get_agent_mission" not in result

    def test_new_context_token_present(self):
        from giljo_mcp.template_renderer import render_gemini_agent

        result = render_gemini_agent(self._make_template())
        assert "mcp_giljo_mcp_get_context" in result

    def test_old_context_token_absent(self):
        from giljo_mcp.template_renderer import render_gemini_agent

        result = render_gemini_agent(self._make_template())
        assert "mcp_giljo_mcp_fetch_context" not in result

    def test_new_memory_token_present(self):
        from giljo_mcp.template_renderer import render_gemini_agent

        result = render_gemini_agent(self._make_template())
        assert "mcp_giljo_mcp_write_memory_entry" in result

    def test_old_memory_token_absent(self):
        from giljo_mcp.template_renderer import render_gemini_agent

        result = render_gemini_agent(self._make_template())
        assert "mcp_giljo_mcp_write_360_memory" not in result

    def test_new_closeout_token_present(self):
        from giljo_mcp.template_renderer import render_gemini_agent

        result = render_gemini_agent(self._make_template())
        assert "mcp_giljo_mcp_write_project_closeout" in result

    def test_old_closeout_token_absent(self):
        from giljo_mcp.template_renderer import render_gemini_agent

        result = render_gemini_agent(self._make_template())
        assert "mcp_giljo_mcp_close_project_and_update_memory" not in result


# ---------------------------------------------------------------------------
# Boot notice banner body
# ---------------------------------------------------------------------------


class TestBootNoticeBannerContent:
    """Boot notice banner body lists all 8 rename pairs."""

    def _get_banner_body(self) -> str:
        """Extract the banner body string without hitting the DB."""
        import inspect

        from api.startup import background_tasks

        src = inspect.getsource(background_tasks._emit_tool_rename_notice_banner)
        # The function builds the body string; verify the source contains the pairs.
        return src

    def test_all_old_names_appear_in_banner_source(self):
        src = self._get_banner_body()
        for old in _OLD_NAMES:
            assert old in src, f"Old name '{old}' missing from boot notice banner source"

    def test_all_new_names_appear_in_banner_source(self):
        src = self._get_banner_body()
        for new in _NEW_NAMES:
            assert new in src, f"New name '{new}' missing from boot notice banner source"

    @pytest.mark.asyncio
    async def test_banner_body_lists_eight_pairs(self, monkeypatch, db_manager, db_session, patched_service_banner):
        """The emitted banner body references all 8 old→new renames."""
        from datetime import UTC, datetime
        from uuid import uuid4

        import bcrypt

        from api.startup.background_tasks import _emit_tool_rename_notice_banner
        from giljo_mcp.models.auth import User
        from giljo_mcp.models.organizations import Organization
        from giljo_mcp.services.notification_service import NotificationService

        unique_id = uuid4().hex[:8]
        tenant_key = f"banner_body_{unique_id}"
        org = Organization(
            id=str(uuid4()),
            tenant_key=tenant_key,
            name=f"Org {unique_id}",
            slug=f"org-{unique_id}",
            is_active=True,
        )
        db_session.add(org)
        await db_session.commit()

        svc = NotificationService()
        await _emit_tool_rename_notice_banner(svc, tenant_key, boot_count=1)

        user_id = str(uuid4())
        user = User(
            id=user_id,
            username=f"banner_user_{unique_id}",
            email=f"banner_user_{unique_id}@example.com",
            full_name="Banner User",
            password_hash=bcrypt.hashpw(b"Test1234!", bcrypt.gensalt()).decode("utf-8"),
            role="admin",
            tenant_key=tenant_key,
            is_active=True,
            created_at=datetime.now(UTC),
        )
        db_session.add(user)
        await db_session.commit()

        rows = await svc.list_for_user(tenant_key, user_id, surface="banner")
        notice = [r for r in rows if r.type == "system.tool_rename_notice"]
        assert len(notice) == 1, "Expected exactly one tool_rename_notice banner"

        body = notice[0].body
        for old in _OLD_NAMES:
            assert old in body, f"Old name '{old}' missing from banner body"
        for new in _NEW_NAMES:
            assert new in body, f"New name '{new}' missing from banner body"

    @pytest.mark.asyncio
    async def test_banner_suppressed_in_saas(self, monkeypatch):
        """Boot notice must NOT emit when boot_count is None (SaaS path)."""
        from api.startup.background_tasks import (
            _TOOL_RENAME_NOTICE_DEDUPE_KEY,
            _emit_tool_rename_notice_banner,
        )

        resolved = []
        upserted = []

        class _FakeService:
            async def resolve_by_dedupe_key(self, tk, key):
                resolved.append(key)

            async def upsert_by_dedupe_key(self, **kwargs):
                upserted.append(kwargs)

        await _emit_tool_rename_notice_banner(_FakeService(), "any_tenant", boot_count=None)
        assert len(upserted) == 0, "SaaS (boot_count=None) must not upsert the banner"
        assert _TOOL_RENAME_NOTICE_DEDUPE_KEY in resolved, "SaaS path must resolve/dismiss the banner"


@pytest_asyncio.fixture
def patched_service_banner(monkeypatch, db_manager, db_session):
    """Patch NotificationService so banner tests share the test transaction."""
    from giljo_mcp.services.notification_service import NotificationService

    real_init = NotificationService.__init__

    def _init(self, *, db_manager=db_manager, websocket_manager=None, session=db_session):
        real_init(self, db_manager=db_manager, websocket_manager=websocket_manager, session=db_session)

    monkeypatch.setattr(NotificationService, "__init__", _init)
