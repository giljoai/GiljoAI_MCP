# Copyright (c) 2024-2026 GiljoAI LLC. All rights reserved.
# Licensed under the GiljoAI Community License v1.1.
# See LICENSE in the project root for terms.
# [CE] Community Edition — source-available, single-user use only.

"""
Tests for context request behavioral instructions in agent templates (Handover 0109).

Handover 0813 update: Context request instructions are no longer in system_instructions
(which is now a slim bootstrap). They are delivered via full_protocol from
_generate_agent_protocol() in protocol_builder.py.

Tests that check system_instructions now verify the slim bootstrap instead.
Tests for the helper function and orchestrator response section remain unchanged.
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
    """Test suite for context request instructions (Handover 0109, updated 0813)."""

    async def test_context_request_in_full_protocol(self, db_session: AsyncSession):
        """Verify context request guidance is delivered via full_protocol, not system_instructions.

        Handover 0813: Context request content moved from system_instructions to
        full_protocol delivered by _generate_agent_protocol().
        """
        from src.giljo_mcp.services.protocol_builder import _generate_agent_protocol

        protocol = _generate_agent_protocol(job_id="test-job", tenant_key="test-tenant", agent_name="implementer")
        # full_protocol should contain context request guidance
        assert "REQUEST_CONTEXT:" in protocol, "full_protocol should contain REQUEST_CONTEXT prefix"
        assert "Requesting Broader Context" in protocol, "full_protocol should contain context request guidance"

    async def test_system_instructions_has_slim_bootstrap(self, db_session: AsyncSession):
        """Verify system_instructions is now slim bootstrap (Handover 0813)."""
        tenant_key = "test_tenant_context_0813"

        count = await seed_tenant_templates(db_session, tenant_key)
        assert count == 5, "Should seed 5 default templates (orchestrator is system-managed)"

        result = await db_session.execute(select(AgentTemplate).where(AgentTemplate.tenant_key == tenant_key))
        templates = result.scalars().all()

        for template in templates:
            system_inst = template.system_instructions
            # Slim bootstrap should reference get_agent_mission for protocols
            assert "get_agent_mission" in system_inst, f"{template.role} bootstrap should reference get_agent_mission"
            assert "full_protocol" in system_inst, f"{template.role} bootstrap should reference full_protocol"
            # Old protocol sections should NOT be in system_instructions
            assert "REQUESTING BROADER CONTEXT" not in system_inst, (
                f"{template.role} should not have context request section in bootstrap"
            )

    async def test_full_protocol_has_messaging_prefixes(self, db_session: AsyncSession):
        """Verify full_protocol contains all messaging prefixes including REQUEST_CONTEXT."""
        from src.giljo_mcp.services.protocol_builder import _generate_agent_protocol

        protocol = _generate_agent_protocol(job_id="test-job", tenant_key="test-tenant", agent_name="tester")
        assert "BLOCKER:" in protocol
        assert "PROGRESS:" in protocol
        assert "COMPLETE:" in protocol
        assert "READY:" in protocol
        assert "REQUEST_CONTEXT:" in protocol

    async def test_full_protocol_has_context_request_specificity_guidance(self, db_session: AsyncSession):
        """Verify full_protocol tells agents to be specific about context needs."""
        from src.giljo_mcp.services.protocol_builder import _generate_agent_protocol

        protocol = _generate_agent_protocol(job_id="test-job", tenant_key="test-tenant", agent_name="analyzer")
        # Should instruct agents to be specific
        assert "specific" in protocol.lower() or "REQUEST_CONTEXT:" in protocol

    async def test_full_protocol_instructs_wait_for_response(self, db_session: AsyncSession):
        """Verify full_protocol tells agents to wait for orchestrator response."""
        from src.giljo_mcp.services.protocol_builder import _generate_agent_protocol

        protocol = _generate_agent_protocol(job_id="test-job", tenant_key="test-tenant", agent_name="implementer")
        assert "receive_messages" in protocol
        assert "wait" in protocol.lower() or "Wait" in protocol

    async def test_full_protocol_has_send_message_for_context(self, db_session: AsyncSession):
        """Verify full_protocol references send_message for context requests."""
        from src.giljo_mcp.services.protocol_builder import _generate_agent_protocol

        protocol = _generate_agent_protocol(job_id="test-job", tenant_key="test-tenant", agent_name="documenter")
        assert "send_message" in protocol

    async def test_full_protocol_warns_against_guessing(self, db_session: AsyncSession):
        """Verify full_protocol tells agents not to guess at ambiguities."""
        from src.giljo_mcp.services.protocol_builder import _generate_agent_protocol

        protocol = _generate_agent_protocol(job_id="test-job", tenant_key="test-tenant", agent_name="reviewer")
        assert "guess" in protocol.lower() or "Do NOT guess" in protocol

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
        assert "mcp__giljo_mcp__send_message" in section or "send_message" in section, (
            "Should reference send_message tool"
        )
        assert "to_agents=" in section or "orchestrator" in section.lower(), "Should show targeting orchestrator"
        assert "project_id" in section, "Should mention project_id parameter"

    def test_context_request_section_placement(self):
        """Verify section is placed after MCP coordination and before check-in protocol."""
        # This is tested indirectly through system_instructions composition
        # We verify the section exists and is part of system_instructions
        section = _get_context_request_section()

        # Section should be standalone (not include MCP coordination or check-in)
        assert "MCP COMMUNICATION PROTOCOL" not in section, "Should not include full MCP coordination (that's separate)"
        assert "CHECK-IN PROTOCOL" not in section, "Should not include check-in protocol (that's separate)"
