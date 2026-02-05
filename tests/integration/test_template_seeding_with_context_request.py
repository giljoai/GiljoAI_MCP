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
        assert count == 6, "Should seed all 6 agent templates"

        # Fetch all templates
        result = await db_session.execute(
            select(AgentTemplate).where(AgentTemplate.tenant_key == tenant_key)
        )
        templates = result.scalars().all()
        assert len(templates) == 6

        # Verify all templates have complete system_instructions
        for template in templates:
            sys_inst = template.system_instructions

            # Must have all three sections in order
            assert "MCP COMMUNICATION PROTOCOL" in sys_inst
            assert "REQUESTING BROADER CONTEXT" in sys_inst
            assert "CHECK-IN PROTOCOL" in sys_inst

            # Verify proper ordering (MCP before Context Request before Check-In)
            mcp_pos = sys_inst.index("MCP COMMUNICATION PROTOCOL")
            ctx_pos = sys_inst.index("REQUESTING BROADER CONTEXT")
            chk_pos = sys_inst.index("CHECK-IN PROTOCOL")

            assert mcp_pos < ctx_pos < chk_pos, (
                f"{template.role} sections in wrong order. "
                f"Expected: MCP ({mcp_pos}) < Context ({ctx_pos}) < Check-In ({chk_pos})"
            )

    async def test_orchestrator_has_response_instructions(self, db_session: AsyncSession):
        """Verify orchestrator template has context response instructions."""
        tenant_key = "integration_test_orchestrator"

        await seed_tenant_templates(db_session, tenant_key)

        # Fetch orchestrator template
        result = await db_session.execute(
            select(AgentTemplate).where(
                AgentTemplate.tenant_key == tenant_key,
                AgentTemplate.role == "orchestrator"
            )
        )
        orchestrator = result.scalar_one()

        # Orchestrator should have response instructions in user_instructions
        user_inst = orchestrator.user_instructions
        assert "RESPONDING TO CONTEXT REQUESTS" in user_inst
        assert "CONTEXT_RESPONSE:" in user_inst
        assert "filtered excerpt" in user_inst.lower()

        # Should also have standard context request in system_instructions
        sys_inst = orchestrator.system_instructions
        assert "REQUESTING BROADER CONTEXT" in sys_inst

    async def test_non_orchestrator_agents_lack_response_instructions(self, db_session: AsyncSession):
        """Verify non-orchestrator agents don't have response instructions."""
        tenant_key = "integration_test_non_orch"

        await seed_tenant_templates(db_session, tenant_key)

        # Fetch non-orchestrator templates
        result = await db_session.execute(
            select(AgentTemplate).where(
                AgentTemplate.tenant_key == tenant_key,
                AgentTemplate.role != "orchestrator"
            )
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

    async def test_legacy_template_includes_new_sections(self, db_session: AsyncSession):
        """Verify legacy template includes context request sections."""
        tenant_key = "integration_test_legacy"

        await seed_tenant_templates(db_session, tenant_key)

        # Fetch all templates
        result = await db_session.execute(
            select(AgentTemplate).where(AgentTemplate.tenant_key == tenant_key)
        )
        templates = result.scalars().all()

        for template in templates:
            # Legacy field should have context request section
            legacy = template.system_instructions
            assert "REQUESTING BROADER CONTEXT" in legacy

            # Verify composition: system_instructions = user + system
            expected = f"{template.user_instructions}\n\n{template.system_instructions}"
            assert legacy.strip() == expected.strip()

    async def test_context_request_mcp_tools_syntax(self, db_session: AsyncSession):
        """Verify context request section uses correct MCP tool syntax."""
        tenant_key = "integration_test_mcp_syntax"

        await seed_tenant_templates(db_session, tenant_key)

        result = await db_session.execute(
            select(AgentTemplate).where(AgentTemplate.tenant_key == tenant_key).limit(1)
        )
        template = result.scalar_one()

        sys_inst = template.system_instructions

        # Verify MCP tool references
        assert "mcp__giljo-mcp__send_message" in sys_inst
        assert "mcp__giljo-mcp__get_next_instruction" in sys_inst
        assert "REQUEST_CONTEXT:" in sys_inst
        assert "tenant_key=" in sys_inst

    async def test_idempotent_seeding_preserves_sections(self, db_session: AsyncSession):
        """Verify idempotent seeding doesn't duplicate or lose sections."""
        tenant_key = "integration_test_idempotent"

        # First seeding
        count1 = await seed_tenant_templates(db_session, tenant_key)
        assert count1 == 6

        # Fetch templates after first seeding
        result1 = await db_session.execute(
            select(AgentTemplate).where(AgentTemplate.tenant_key == tenant_key)
        )
        templates_first = {t.role: t.system_instructions for t in result1.scalars().all()}

        # Second seeding (should skip)
        count2 = await seed_tenant_templates(db_session, tenant_key)
        assert count2 == 0, "Should skip seeding (idempotent)"

        # Fetch templates after second seeding
        result2 = await db_session.execute(
            select(AgentTemplate).where(AgentTemplate.tenant_key == tenant_key)
        )
        templates_second = {t.role: t.system_instructions for t in result2.scalars().all()}

        # Verify templates unchanged
        assert templates_first == templates_second, "Templates should be identical after idempotent run"
