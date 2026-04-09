# Copyright (c) 2024-2026 GiljoAI LLC. All rights reserved.
# Licensed under the GiljoAI Community License v1.1.
# See LICENSE in the project root for terms.
# [CE] Community Edition — source-available, single-user use only.

"""Tests for Handover 0814: Template Manager UI Redesign (Phase 5).

Validates the four backend fixes introduced in 0814:
1. create_template() injects canonical MCP bootstrap as system_instructions
2. create_template() stores user_instructions from request body
3. update_template() rejects system_instructions with 403
4. update_template() accepts and stores user_instructions
5. reset_system_instructions() produces canonical bootstrap
6. Export paths produce identical output via render_claude_agent()
"""

from datetime import datetime, timezone
from unittest.mock import AsyncMock, Mock, patch

import pytest
import yaml

from src.giljo_mcp.models import AgentTemplate
from src.giljo_mcp.template_renderer import render_claude_agent
from src.giljo_mcp.template_seeder import _get_mcp_bootstrap_section

# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------

def _make_template(**overrides) -> AgentTemplate:
    """Build an AgentTemplate with sensible defaults for testing."""
    defaults = dict(
        name="test-agent",
        role="implementer",
        cli_tool="claude",
        description="Test agent for 0814 validation",
        system_instructions=_get_mcp_bootstrap_section(),
        user_instructions="You are a testing specialist.",
        model="sonnet",
        behavioral_rules=["Follow coding standards", "Write tests first"],
        success_criteria=["All tests pass", "No linting errors"],
    )
    defaults.update(overrides)
    return AgentTemplate(**defaults)


def _make_mock_session():
    """Create a properly configured mock async session.

    The refresh side-effect simulates what the DB does when committing a new
    record: it fills in server-default columns like ``created_at``.
    """
    session = AsyncMock()
    session.__aenter__ = AsyncMock(return_value=session)
    session.__aexit__ = AsyncMock(return_value=False)
    session.execute = AsyncMock()
    session.commit = AsyncMock()
    session.add = Mock()
    session.delete = Mock()
    session.flush = AsyncMock()
    session.rollback = AsyncMock()

    async def _simulate_refresh(obj, *args, **kwargs):
        """Simulate DB refresh by filling server-default columns."""
        if hasattr(obj, "created_at") and obj.created_at is None:
            obj.created_at = datetime.now(timezone.utc)

    session.refresh = AsyncMock(side_effect=_simulate_refresh)
    return session


def _make_mock_user(tenant_key: str = "tk_test1234567890abcdef1234567890ab"):
    """Create a mock User with tenant context."""
    user = Mock()
    user.id = "user-001"
    user.username = "testuser"
    user.tenant_key = tenant_key
    user.org_id = "org-001"
    user.role = "developer"
    user.organization = Mock()
    user.organization.tenant_key = tenant_key
    return user


# ---------------------------------------------------------------------------
# 1. create_template injects canonical bootstrap as system_instructions
# ---------------------------------------------------------------------------

class TestCreateTemplateInjectsCanonicalBootstrap:
    """create_template() must always set system_instructions to the canonical
    MCP bootstrap from _get_mcp_bootstrap_section(), regardless of what the
    frontend sends."""

    @pytest.mark.asyncio
    async def test_create_template_injects_canonical_bootstrap(self):
        """Created template system_instructions must match canonical bootstrap."""
        from api.endpoints.templates.crud import create_template
        from api.endpoints.templates.models import TemplateCreate

        canonical = _get_mcp_bootstrap_section()
        session = _make_mock_session()
        user = _make_mock_user()

        # Frontend sends custom system_instructions -- endpoint should ignore it
        payload = TemplateCreate(
            role="implementer",
            cli_tool="claude",
            system_instructions="INJECTED EVIL INSTRUCTIONS",
            user_instructions="Legitimate role description.",
        )

        mock_template_service = AsyncMock()
        mock_template_service.check_template_name_exists = AsyncMock(return_value=False)
        mock_template_service.get_default_templates_by_role = AsyncMock(return_value=[])

        # Capture the template that gets added to the session
        captured_template = None
        original_add = session.add

        def capture_add(obj):
            nonlocal captured_template
            if isinstance(obj, AgentTemplate):
                captured_template = obj
            original_add(obj)

        session.add = capture_add

        with patch(
            "api.endpoints.templates.crud.get_tenant_and_product_from_user",
            return_value={"tenant_key": user.tenant_key, "product_id": "prod-001"},
        ):
            await create_template(
                template=payload,
                current_user=user,
                session=session,
                template_service=mock_template_service,
            )

        assert captured_template is not None, "Template should have been added to session"
        assert captured_template.system_instructions == canonical, (
            "system_instructions must be the canonical MCP bootstrap, "
            "not the value sent by the frontend"
        )
        assert "INJECTED EVIL INSTRUCTIONS" not in captured_template.system_instructions

    @pytest.mark.asyncio
    async def test_create_template_bootstrap_contains_required_elements(self):
        """The injected bootstrap must contain health_check, get_agent_mission, full_protocol."""
        from api.endpoints.templates.crud import create_template
        from api.endpoints.templates.models import TemplateCreate

        session = _make_mock_session()
        user = _make_mock_user()

        payload = TemplateCreate(
            role="reviewer",
            cli_tool="claude",
            user_instructions="Review code carefully.",
        )

        mock_template_service = AsyncMock()
        mock_template_service.check_template_name_exists = AsyncMock(return_value=False)
        mock_template_service.get_default_templates_by_role = AsyncMock(return_value=[])

        captured_template = None
        original_add = session.add

        def capture_add(obj):
            nonlocal captured_template
            if isinstance(obj, AgentTemplate):
                captured_template = obj
            original_add(obj)

        session.add = capture_add

        with patch(
            "api.endpoints.templates.crud.get_tenant_and_product_from_user",
            return_value={"tenant_key": user.tenant_key, "product_id": "prod-001"},
        ):
            await create_template(
                template=payload,
                current_user=user,
                session=session,
                template_service=mock_template_service,
            )

        bootstrap = captured_template.system_instructions
        assert "health_check" in bootstrap
        assert "get_agent_mission" in bootstrap
        assert "full_protocol" in bootstrap


# ---------------------------------------------------------------------------
# 2. create_template stores user_instructions from request
# ---------------------------------------------------------------------------

class TestCreateTemplateStoresUserInstructions:
    """create_template() must store user_instructions from the request body."""

    @pytest.mark.asyncio
    async def test_create_template_stores_user_instructions(self):
        """user_instructions from request body should be stored on the template."""
        from api.endpoints.templates.crud import create_template
        from api.endpoints.templates.models import TemplateCreate

        session = _make_mock_session()
        user = _make_mock_user()

        custom_role_description = (
            "You are a senior code reviewer who provides constructive, "
            "actionable feedback on pull requests."
        )

        payload = TemplateCreate(
            role="reviewer",
            cli_tool="claude",
            user_instructions=custom_role_description,
        )

        mock_template_service = AsyncMock()
        mock_template_service.check_template_name_exists = AsyncMock(return_value=False)
        mock_template_service.get_default_templates_by_role = AsyncMock(return_value=[])

        captured_template = None
        original_add = session.add

        def capture_add(obj):
            nonlocal captured_template
            if isinstance(obj, AgentTemplate):
                captured_template = obj
            original_add(obj)

        session.add = capture_add

        with patch(
            "api.endpoints.templates.crud.get_tenant_and_product_from_user",
            return_value={"tenant_key": user.tenant_key, "product_id": "prod-001"},
        ):
            await create_template(
                template=payload,
                current_user=user,
                session=session,
                template_service=mock_template_service,
            )

        assert captured_template is not None
        assert captured_template.user_instructions == custom_role_description

    @pytest.mark.asyncio
    async def test_create_template_empty_user_instructions_defaults_to_empty(self):
        """When user_instructions is omitted, it should default to empty string."""
        from api.endpoints.templates.crud import create_template
        from api.endpoints.templates.models import TemplateCreate

        session = _make_mock_session()
        user = _make_mock_user()

        payload = TemplateCreate(
            role="tester",
            cli_tool="claude",
        )

        mock_template_service = AsyncMock()
        mock_template_service.check_template_name_exists = AsyncMock(return_value=False)
        mock_template_service.get_default_templates_by_role = AsyncMock(return_value=[])

        captured_template = None
        original_add = session.add

        def capture_add(obj):
            nonlocal captured_template
            if isinstance(obj, AgentTemplate):
                captured_template = obj
            original_add(obj)

        session.add = capture_add

        with patch(
            "api.endpoints.templates.crud.get_tenant_and_product_from_user",
            return_value={"tenant_key": user.tenant_key, "product_id": "prod-001"},
        ):
            await create_template(
                template=payload,
                current_user=user,
                session=session,
                template_service=mock_template_service,
            )

        assert captured_template is not None
        assert captured_template.user_instructions == ""


# ---------------------------------------------------------------------------
# 3. update_template rejects system_instructions with 403
# ---------------------------------------------------------------------------

class TestUpdateTemplateRejectsSystemInstructions:
    """update_template() must reject attempts to modify system_instructions."""

    @pytest.mark.asyncio
    async def test_update_template_rejects_system_instructions_with_403(self):
        """Sending system_instructions in an update payload should return 403."""
        from fastapi import HTTPException

        from api.endpoints.templates.crud import update_template
        from api.endpoints.templates.models import TemplateUpdate

        session = _make_mock_session()
        user = _make_mock_user()

        existing_template = _make_template()
        existing_template.id = "tmpl-001"
        existing_template.tenant_key = user.tenant_key
        existing_template.role = "implementer"

        mock_template_service = AsyncMock()
        mock_template_service.get_template_by_id = AsyncMock(return_value=existing_template)

        payload = TemplateUpdate(
            system_instructions="Attempt to override bootstrap",
        )

        with patch(
            "api.endpoints.templates.crud.get_tenant_and_product_from_user",
            return_value={"tenant_key": user.tenant_key, "product_id": "prod-001"},
        ):
            with pytest.raises(HTTPException) as exc_info:
                await update_template(
                    template_id="tmpl-001",
                    updates=payload,
                    current_user=user,
                    session=session,
                    template_service=mock_template_service,
                )

        assert exc_info.value.status_code == 403
        assert "system_instructions" in str(exc_info.value.detail).lower()
        assert "read-only" in str(exc_info.value.detail).lower()

    @pytest.mark.asyncio
    async def test_update_template_rejects_system_instructions_even_with_same_value(self):
        """Even if system_instructions matches current value, it should still be rejected."""
        from fastapi import HTTPException

        from api.endpoints.templates.crud import update_template
        from api.endpoints.templates.models import TemplateUpdate

        session = _make_mock_session()
        user = _make_mock_user()
        canonical = _get_mcp_bootstrap_section()

        existing_template = _make_template()
        existing_template.id = "tmpl-002"
        existing_template.tenant_key = user.tenant_key
        existing_template.role = "implementer"

        mock_template_service = AsyncMock()
        mock_template_service.get_template_by_id = AsyncMock(return_value=existing_template)

        payload = TemplateUpdate(
            system_instructions=canonical,
        )

        with patch(
            "api.endpoints.templates.crud.get_tenant_and_product_from_user",
            return_value={"tenant_key": user.tenant_key, "product_id": "prod-001"},
        ):
            with pytest.raises(HTTPException) as exc_info:
                await update_template(
                    template_id="tmpl-002",
                    updates=payload,
                    current_user=user,
                    session=session,
                    template_service=mock_template_service,
                )

        assert exc_info.value.status_code == 403


# ---------------------------------------------------------------------------
# 4. update_template accepts and stores user_instructions
# ---------------------------------------------------------------------------

class TestUpdateTemplateAcceptsUserInstructions:
    """update_template() must accept user_instructions and persist them."""

    @pytest.mark.asyncio
    async def test_update_template_stores_user_instructions(self):
        """user_instructions in update payload should be stored on the template."""
        from api.endpoints.templates.crud import update_template
        from api.endpoints.templates.models import TemplateUpdate

        session = _make_mock_session()
        user = _make_mock_user()

        existing_template = _make_template()
        existing_template.id = "tmpl-003"
        existing_template.tenant_key = user.tenant_key
        existing_template.role = "implementer"
        existing_template.user_instructions = "Old instructions"
        existing_template.updated_at = None
        existing_template.last_exported_at = None

        mock_template_service = AsyncMock()
        mock_template_service.get_template_by_id = AsyncMock(return_value=existing_template)
        mock_template_service.create_template_archive = AsyncMock()

        new_instructions = "Updated role description with deep expertise in testing."

        payload = TemplateUpdate(
            user_instructions=new_instructions,
        )

        with patch(
            "api.endpoints.templates.crud.get_tenant_and_product_from_user",
            return_value={"tenant_key": user.tenant_key, "product_id": "prod-001"},
        ), patch(
            "api.endpoints.templates.crud._convert_to_response",
        ) as mock_convert:
            mock_convert.return_value = Mock()

            await update_template(
                template_id="tmpl-003",
                updates=payload,
                current_user=user,
                session=session,
                template_service=mock_template_service,
            )

        assert existing_template.user_instructions == new_instructions
        session.commit.assert_awaited_once()

    @pytest.mark.asyncio
    async def test_update_template_creates_archive_for_user_instructions_change(self):
        """Changing user_instructions should trigger an archive creation."""
        from api.endpoints.templates.crud import update_template
        from api.endpoints.templates.models import TemplateUpdate

        session = _make_mock_session()
        user = _make_mock_user()

        existing_template = _make_template()
        existing_template.id = "tmpl-004"
        existing_template.tenant_key = user.tenant_key
        existing_template.role = "implementer"
        existing_template.updated_at = None
        existing_template.last_exported_at = None

        mock_template_service = AsyncMock()
        mock_template_service.get_template_by_id = AsyncMock(return_value=existing_template)
        mock_template_service.create_template_archive = AsyncMock()

        payload = TemplateUpdate(
            user_instructions="Brand new instructions",
        )

        with patch(
            "api.endpoints.templates.crud.get_tenant_and_product_from_user",
            return_value={"tenant_key": user.tenant_key, "product_id": "prod-001"},
        ), patch(
            "api.endpoints.templates.crud._convert_to_response",
        ) as mock_convert:
            mock_convert.return_value = Mock()

            await update_template(
                template_id="tmpl-004",
                updates=payload,
                current_user=user,
                session=session,
                template_service=mock_template_service,
            )

        mock_template_service.create_template_archive.assert_awaited_once()
        call_kwargs = mock_template_service.create_template_archive.call_args
        assert call_kwargs[1]["archive_reason"] == "Update user instructions"


# ---------------------------------------------------------------------------
# 5. reset_system_instructions produces canonical bootstrap
# ---------------------------------------------------------------------------

class TestResetSystemInstructionsCanonical:
    """reset_system_instructions() must set system_instructions to the canonical
    MCP bootstrap from _get_mcp_bootstrap_section()."""

    @pytest.mark.asyncio
    async def test_reset_produces_canonical_bootstrap(self):
        """After reset, system_instructions must match _get_mcp_bootstrap_section()."""
        from src.giljo_mcp.services.template_service import TemplateService

        canonical = _get_mcp_bootstrap_section()

        template = _make_template(
            system_instructions="Stale or corrupted bootstrap content",
        )

        session = _make_mock_session()
        db_manager = Mock()
        db_manager.get_session_async = Mock(return_value=session)
        tenant_manager = Mock()
        tenant_manager.get_current_tenant = Mock(return_value="test-tenant")

        service = TemplateService(db_manager, tenant_manager)
        await service.reset_system_instructions(session, template)

        assert template.system_instructions == canonical

    @pytest.mark.asyncio
    async def test_reset_canonical_contains_startup_sequence(self):
        """The canonical bootstrap must include the three-step startup sequence."""
        from src.giljo_mcp.services.template_service import TemplateService

        template = _make_template(
            system_instructions="Old content",
        )

        session = _make_mock_session()
        db_manager = Mock()
        db_manager.get_session_async = Mock(return_value=session)
        tenant_manager = Mock()
        tenant_manager.get_current_tenant = Mock(return_value="test-tenant")

        service = TemplateService(db_manager, tenant_manager)
        await service.reset_system_instructions(session, template)

        assert "health_check" in template.system_instructions
        assert "get_agent_mission" in template.system_instructions
        assert "full_protocol" in template.system_instructions
        assert "GiljoAI MCP" in template.system_instructions

    @pytest.mark.asyncio
    async def test_reset_canonical_does_not_contain_protocol_sections(self):
        """The canonical bootstrap must NOT include full protocol sections."""
        from src.giljo_mcp.services.template_service import TemplateService

        template = _make_template(
            system_instructions="Old content with ## CHECK-IN PROTOCOL",
        )

        session = _make_mock_session()
        db_manager = Mock()
        db_manager.get_session_async = Mock(return_value=session)
        tenant_manager = Mock()
        tenant_manager.get_current_tenant = Mock(return_value="test-tenant")

        service = TemplateService(db_manager, tenant_manager)
        await service.reset_system_instructions(session, template)

        assert "## CHECK-IN PROTOCOL" not in template.system_instructions
        assert "## MESSAGING" not in template.system_instructions
        assert "## Agent Guidelines" not in template.system_instructions


# ---------------------------------------------------------------------------
# 6. Export paths produce identical output (render_claude_agent consistency)
# ---------------------------------------------------------------------------

class TestRenderClaudeAgentConsistency:
    """render_claude_agent() must produce consistent, complete output including
    frontmatter, system_instructions, user_instructions, behavioral_rules,
    and success_criteria."""

    def test_output_contains_yaml_frontmatter(self):
        """Output must start with YAML frontmatter containing name, description, model."""
        template = _make_template()
        result = render_claude_agent(template)

        assert result.startswith("---\n")
        # Extract frontmatter
        parts = result.split("---\n")
        assert len(parts) >= 3, "Output must have opening and closing frontmatter delimiters"
        frontmatter = yaml.safe_load(parts[1])
        assert frontmatter["name"] == "test-agent"
        assert "description" in frontmatter
        assert frontmatter["model"] == "sonnet"

    def test_output_contains_system_instructions_bootstrap(self):
        """Output body must include the slim MCP bootstrap from system_instructions."""
        template = _make_template()
        result = render_claude_agent(template)

        assert "GiljoAI MCP Agent" in result
        assert "health_check" in result
        assert "get_agent_mission" in result

    def test_output_contains_user_instructions(self):
        """Output body must include user_instructions role prose."""
        template = _make_template(
            user_instructions="You are a production code specialist with deep TDD expertise.",
        )
        result = render_claude_agent(template)
        assert "production code specialist" in result
        assert "TDD expertise" in result

    def test_output_contains_behavioral_rules(self):
        """Output body must include the behavioral rules section."""
        template = _make_template(
            behavioral_rules=["Always write tests first", "Use pathlib for file ops"],
        )
        result = render_claude_agent(template)
        assert "## Behavioral Rules" in result
        assert "- Always write tests first" in result
        assert "- Use pathlib for file ops" in result

    def test_output_contains_success_criteria(self):
        """Output body must include the success criteria section."""
        template = _make_template(
            success_criteria=["All tests green", "Linting clean"],
        )
        result = render_claude_agent(template)
        assert "## Success Criteria" in result
        assert "- All tests green" in result
        assert "- Linting clean" in result

    def test_output_ordering_bootstrap_before_user_instructions(self):
        """system_instructions (bootstrap) must appear before user_instructions in body."""
        template = _make_template(
            system_instructions=_get_mcp_bootstrap_section(),
            user_instructions="You are a specialized reviewer agent.",
        )
        result = render_claude_agent(template)

        body = result.split("---\n", 2)[-1]
        bootstrap_pos = body.find("GiljoAI MCP Agent")
        user_pos = body.find("specialized reviewer agent")
        assert bootstrap_pos >= 0, "Bootstrap must be present in body"
        assert user_pos >= 0, "User instructions must be present in body"
        assert bootstrap_pos < user_pos, "Bootstrap must appear before user_instructions"

    def test_output_ordering_rules_and_criteria_after_user_instructions(self):
        """Behavioral rules and success criteria must appear after user_instructions."""
        template = _make_template(
            user_instructions="You are the implementer agent.",
            behavioral_rules=["Rule one"],
            success_criteria=["Criteria one"],
        )
        result = render_claude_agent(template)

        user_pos = result.find("implementer agent")
        rules_pos = result.find("## Behavioral Rules")
        criteria_pos = result.find("## Success Criteria")

        assert user_pos < rules_pos, "User instructions must come before behavioral rules"
        assert rules_pos < criteria_pos, "Behavioral rules must come before success criteria"

    def test_render_with_empty_optional_sections(self):
        """Rendering with empty behavioral_rules and success_criteria should still work."""
        template = _make_template(
            behavioral_rules=[],
            success_criteria=[],
        )
        result = render_claude_agent(template)

        assert result.startswith("---\n")
        assert "GiljoAI MCP Agent" in result
        assert "## Behavioral Rules" not in result
        assert "## Success Criteria" not in result

    def test_render_produces_identical_output_for_same_input(self):
        """Calling render_claude_agent twice with the same template produces identical output."""
        template = _make_template()
        result_1 = render_claude_agent(template)
        result_2 = render_claude_agent(template)
        assert result_1 == result_2, "render_claude_agent must be deterministic"
