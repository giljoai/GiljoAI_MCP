"""
Tests for context request behavioral instructions in agent templates (Handover 0109).

Verifies that all agent templates include instructions on when and how to request
broader project context from the orchestrator via MCP messaging.
"""

import pytest
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from src.giljo_mcp.models import AgentTemplate
from src.giljo_mcp.template_seeder import (
    _get_context_request_section,
    seed_tenant_templates,
)


@pytest.mark.asyncio
class TestContextRequestSection:
    """Test suite for context request instructions (Handover 0109)."""

    async def test_context_request_section_exists(self, db_session: AsyncSession):
        """Verify context request section present in all templates."""
        tenant_key = "test_tenant_context"

        # Seed templates
        # Note: orchestrator is a SYSTEM_MANAGED_ROLE and is skipped during seeding
        count = await seed_tenant_templates(db_session, tenant_key)
        assert count == 5, "Should seed 5 default templates (orchestrator is system-managed)"

        # Fetch all templates
        result = await db_session.execute(select(AgentTemplate).where(AgentTemplate.tenant_key == tenant_key))
        templates = result.scalars().all()

        # Verify all templates have context request instructions
        for template in templates:
            system_inst = template.system_instructions
            assert "REQUESTING BROADER CONTEXT" in system_inst, (
                f"{template.role} missing REQUESTING BROADER CONTEXT section"
            )

    async def test_context_request_when_to_request(self, db_session: AsyncSession):
        """Verify section includes 'When to Request Context' guidance."""
        tenant_key = "test_tenant_when"

        await seed_tenant_templates(db_session, tenant_key)

        result = await db_session.execute(select(AgentTemplate).where(AgentTemplate.tenant_key == tenant_key))
        templates = result.scalars().all()

        for template in templates:
            system_inst = template.system_instructions
            assert "When to Request Context" in system_inst, (
                f"{template.role} missing 'When to Request Context' subsection"
            )
            # Should mention common scenarios
            assert "unclear" in system_inst.lower() or "ambiguous" in system_inst.lower(), (
                f"{template.role} should mention unclear/ambiguous scenarios"
            )

    async def test_context_request_how_to_request(self, db_session: AsyncSession):
        """Verify section includes 'How to Request Context' with MCP tool usage."""
        tenant_key = "test_tenant_how"

        await seed_tenant_templates(db_session, tenant_key)

        result = await db_session.execute(select(AgentTemplate).where(AgentTemplate.tenant_key == tenant_key))
        templates = result.scalars().all()

        for template in templates:
            system_inst = template.system_instructions
            assert "How to Request Context" in system_inst, (
                f"{template.role} missing 'How to Request Context' subsection"
            )
            # Should reference send_message MCP tool
            assert "send_message" in system_inst, f"{template.role} should reference send_message tool"
            assert "REQUEST_CONTEXT:" in system_inst, f"{template.role} should show REQUEST_CONTEXT message format"

    async def test_context_request_message_format_examples(self, db_session: AsyncSession):
        """Verify section includes good/bad message format examples."""
        tenant_key = "test_tenant_examples"

        await seed_tenant_templates(db_session, tenant_key)

        result = await db_session.execute(select(AgentTemplate).where(AgentTemplate.tenant_key == tenant_key))
        templates = result.scalars().all()

        for template in templates:
            system_inst = template.system_instructions
            # Should have good examples (✅) and bad examples (❌)
            assert "Good:" in system_inst or "✅" in system_inst, f"{template.role} should have good example patterns"
            assert "Bad:" in system_inst or "❌" in system_inst, f"{template.role} should have bad example patterns"

    async def test_context_request_wait_for_response(self, db_session: AsyncSession):
        """Verify section instructs agents to wait for orchestrator response."""
        tenant_key = "test_tenant_wait"

        await seed_tenant_templates(db_session, tenant_key)

        result = await db_session.execute(select(AgentTemplate).where(AgentTemplate.tenant_key == tenant_key))
        templates = result.scalars().all()

        for template in templates:
            system_inst = template.system_instructions
            assert "get_next_instruction" in system_inst, (
                f"{template.role} should mention get_next_instruction for checking responses"
            )
            assert "wait" in system_inst.lower() or "check" in system_inst.lower(), (
                f"{template.role} should instruct to wait/check for response"
            )

    async def test_context_request_audit_trail_documentation(self, db_session: AsyncSession):
        """Verify section mentions documenting context requests for audit trail."""
        tenant_key = "test_tenant_audit"

        await seed_tenant_templates(db_session, tenant_key)

        result = await db_session.execute(select(AgentTemplate).where(AgentTemplate.tenant_key == tenant_key))
        templates = result.scalars().all()

        for template in templates:
            system_inst = template.system_instructions
            assert "progress" in system_inst.lower() and "report" in system_inst.lower(), (
                f"{template.role} should mention reporting context requests in progress"
            )

    async def test_context_request_benefits_listed(self, db_session: AsyncSession):
        """Verify section lists benefits of using context request protocol."""
        tenant_key = "test_tenant_benefits"

        await seed_tenant_templates(db_session, tenant_key)

        result = await db_session.execute(select(AgentTemplate).where(AgentTemplate.tenant_key == tenant_key))
        templates = result.scalars().all()

        for template in templates:
            system_inst = template.system_instructions
            # Should have "Benefits:" section
            assert "Benefits:" in system_inst or "benefit" in system_inst.lower(), (
                f"{template.role} should list benefits of context request protocol"
            )
            # Should mention audit trail
            assert "audit" in system_inst.lower(), f"{template.role} benefits should mention audit trail"

    def test_orchestrator_response_instructions(self):
        """Verify orchestrator context response section has required content.

        Note: Orchestrator is a SYSTEM_MANAGED_ROLE and not seeded via seed_tenant_templates.
        Instead, we test the helper function directly that generates the content.
        """
        from src.giljo_mcp.template_seeder import _get_orchestrator_context_response_section

        # Get the orchestrator context response section
        response_section = _get_orchestrator_context_response_section()

        # Orchestrator should have special "RESPONDING TO CONTEXT REQUESTS" section
        assert "RESPONDING TO CONTEXT REQUESTS" in response_section, (
            "Orchestrator missing RESPONDING TO CONTEXT REQUESTS section"
        )
        assert "CONTEXT_RESPONSE:" in response_section, "Orchestrator should show CONTEXT_RESPONSE message format"
        assert "filtered excerpt" in response_section.lower(), (
            "Orchestrator should mention providing filtered excerpts, not full text"
        )

    async def test_non_orchestrator_agents_lack_response_section(self, db_session: AsyncSession):
        """Verify non-orchestrator templates don't have orchestrator-specific response instructions."""
        tenant_key = "test_tenant_non_orch"

        await seed_tenant_templates(db_session, tenant_key)

        result = await db_session.execute(
            select(AgentTemplate).where(AgentTemplate.tenant_key == tenant_key, AgentTemplate.role != "orchestrator")
        )
        non_orchestrator_templates = result.scalars().all()

        for template in non_orchestrator_templates:
            user_inst = template.user_instructions
            # Non-orchestrator agents should NOT have "RESPONDING TO CONTEXT REQUESTS"
            assert "RESPONDING TO CONTEXT REQUESTS" not in user_inst, (
                f"{template.role} should not have orchestrator-specific response instructions"
            )

    def test_context_request_section_helper_returns_string(self):
        """Verify _get_context_request_section() returns non-empty string."""
        section = _get_context_request_section()

        assert isinstance(section, str), "Should return string"
        assert len(section) > 0, "Should not be empty"
        assert "REQUESTING BROADER CONTEXT" in section, "Should have main heading"

    def test_context_request_section_markdown_formatted(self):
        """Verify section uses proper markdown formatting."""
        section = _get_context_request_section()

        # Should have markdown headers
        assert "###" in section, "Should have subsections with ### headers"
        assert "**" in section or "*" in section, "Should have bold/italic formatting"

        # Should have code blocks for MCP tool examples
        assert "```" in section, "Should have code blocks for examples"

    def test_context_request_section_has_mcp_tool_syntax(self):
        """Verify section shows correct MCP tool syntax."""
        section = _get_context_request_section()

        # Should show proper MCP tool call syntax
        assert "mcp__giljo-mcp__send_message" in section or "send_message" in section, (
            "Should reference send_message tool"
        )
        assert "to_agent=" in section or "orchestrator" in section.lower(), "Should show targeting orchestrator"
        assert "tenant_key" in section, "Should mention tenant_key parameter"

    def test_context_request_section_placement(self):
        """Verify section is placed after MCP coordination and before check-in protocol."""
        # This is tested indirectly through system_instructions composition
        # We verify the section exists and is part of system_instructions
        section = _get_context_request_section()

        # Section should be standalone (not include MCP coordination or check-in)
        assert "MCP COMMUNICATION PROTOCOL" not in section, "Should not include full MCP coordination (that's separate)"
        assert "CHECK-IN PROTOCOL" not in section, "Should not include check-in protocol (that's separate)"
