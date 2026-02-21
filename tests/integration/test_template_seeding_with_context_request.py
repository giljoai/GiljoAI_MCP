"""
Integration test for template seeding with context request instructions (Handover 0109).

Verifies the complete template seeding workflow includes context request sections
in the correct locations (system_instructions for all agents, user_instructions
for orchestrator only).
"""

import pytest
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from src.giljo_mcp.models import AgentTemplate
from src.giljo_mcp.template_seeder import seed_tenant_templates


@pytest.mark.asyncio
class TestTemplateSeededWithContextRequest:
    """Integration test for full template seeding with context request sections."""

    async def test_full_template_seeding_workflow(self, db_session: AsyncSession):
        """Verify complete template seeding includes context request instructions."""
        tenant_key = "integration_test_tenant"

        # Seed templates (simulates first-time tenant setup)
        count = await seed_tenant_templates(db_session, tenant_key)
        assert count == 5, "Should seed 5 agent templates (orchestrator is system-managed)"

        # Fetch all templates
        result = await db_session.execute(select(AgentTemplate).where(AgentTemplate.tenant_key == tenant_key))
        templates = result.scalars().all()
        assert len(templates) == 5

        # Verify all templates have complete system_instructions
        for template in templates:
            sys_inst = template.system_instructions

            # Must have all three sections in order
            assert "MCP Tool Usage" in sys_inst
            assert "REQUESTING BROADER CONTEXT" in sys_inst
            assert "CHECK-IN PROTOCOL" in sys_inst

            # Verify proper ordering (MCP before Context Request before Check-In)
            mcp_pos = sys_inst.index("MCP Tool Usage")
            ctx_pos = sys_inst.index("REQUESTING BROADER CONTEXT")
            chk_pos = sys_inst.index("CHECK-IN PROTOCOL")

            assert mcp_pos < ctx_pos < chk_pos, (
                f"{template.role} sections in wrong order. "
                f"Expected: MCP ({mcp_pos}) < Context ({ctx_pos}) < Check-In ({chk_pos})"
            )

    async def test_orchestrator_response_section_helper(self, db_session: AsyncSession):
        """Verify orchestrator context response section has required content.

        Note: Orchestrator is a SYSTEM_MANAGED_ROLE and not seeded via seed_tenant_templates.
        We test the helper function directly that generates the content.
        """
        from src.giljo_mcp.template_seeder import _get_orchestrator_context_response_section

        response_section = _get_orchestrator_context_response_section()

        # Orchestrator should have response instructions
        assert "RESPONDING TO CONTEXT REQUESTS" in response_section
        assert "CONTEXT_RESPONSE:" in response_section
        assert "filtered excerpt" in response_section.lower()

    async def test_non_orchestrator_agents_lack_response_instructions(self, db_session: AsyncSession):
        """Verify non-orchestrator agents don't have response instructions."""
        tenant_key = "integration_test_non_orch"

        await seed_tenant_templates(db_session, tenant_key)

        # Fetch non-orchestrator templates
        result = await db_session.execute(
            select(AgentTemplate).where(AgentTemplate.tenant_key == tenant_key, AgentTemplate.role != "orchestrator")
        )
        non_orchestrators = result.scalars().all()

        assert len(non_orchestrators) == 5, "Should have 5 non-orchestrator agents"

        for template in non_orchestrators:
            user_inst = template.user_instructions

            # Should NOT have response instructions
            assert "RESPONDING TO CONTEXT REQUESTS" not in user_inst, (
                f"{template.role} should not have orchestrator-specific response instructions"
            )

            # Should have request instructions in system_instructions
            sys_inst = template.system_instructions
            assert "REQUESTING BROADER CONTEXT" in sys_inst

    async def test_seeded_templates_include_context_request_sections(self, db_session: AsyncSession):
        """Verify seeded templates include context request sections in system_instructions."""
        tenant_key = "integration_test_legacy"

        await seed_tenant_templates(db_session, tenant_key)

        # Fetch all templates
        result = await db_session.execute(select(AgentTemplate).where(AgentTemplate.tenant_key == tenant_key))
        templates = result.scalars().all()

        for template in templates:
            # system_instructions should have context request section
            sys_inst = template.system_instructions
            assert "REQUESTING BROADER CONTEXT" in sys_inst

            # user_instructions should be separate (no MCP content)
            user_inst = template.user_instructions
            assert "MCP Tool Usage" not in user_inst, (
                f"{template.role} user_instructions should not contain MCP Tool Usage (that's in system_instructions)"
            )

    async def test_context_request_mcp_tools_syntax(self, db_session: AsyncSession):
        """Verify context request section uses correct MCP tool syntax."""
        tenant_key = "integration_test_mcp_syntax"

        await seed_tenant_templates(db_session, tenant_key)

        result = await db_session.execute(select(AgentTemplate).where(AgentTemplate.tenant_key == tenant_key).limit(1))
        template = result.scalar_one()

        sys_inst = template.system_instructions

        # Verify MCP tool references
        assert "mcp__giljo-mcp__send_message" in sys_inst
        assert "mcp__giljo-mcp__receive_messages" in sys_inst
        assert "REQUEST_CONTEXT:" in sys_inst

    async def test_idempotent_seeding_preserves_sections(self, db_session: AsyncSession):
        """Verify idempotent seeding doesn't duplicate or lose sections."""
        tenant_key = "integration_test_idempotent"

        # First seeding
        count1 = await seed_tenant_templates(db_session, tenant_key)
        assert count1 == 5

        # Fetch templates after first seeding
        result1 = await db_session.execute(select(AgentTemplate).where(AgentTemplate.tenant_key == tenant_key))
        templates_first = {t.role: t.system_instructions for t in result1.scalars().all()}

        # Second seeding (should skip)
        count2 = await seed_tenant_templates(db_session, tenant_key)
        assert count2 == 0, "Should skip seeding (idempotent)"

        # Fetch templates after second seeding
        result2 = await db_session.execute(select(AgentTemplate).where(AgentTemplate.tenant_key == tenant_key))
        templates_second = {t.role: t.system_instructions for t in result2.scalars().all()}

        # Verify templates unchanged
        assert templates_first == templates_second, "Templates should be identical after idempotent run"
