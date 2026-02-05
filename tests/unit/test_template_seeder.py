"""
Comprehensive tests for template_seeder.py dual-field system.

Tests the seeding of system_instructions (protected MCP coordination) and
user_instructions (editable role-specific guidance) in agent templates.

Handover 0106: Dual-Field System
"""
import pytest
from datetime import datetime, timezone
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from src.giljo_mcp.models import AgentTemplate
from src.giljo_mcp.template_seeder import (
    seed_tenant_templates,
    _get_mcp_coordination_section,
    _get_default_templates_v103,
)


@pytest.mark.asyncio
class TestTemplateSeederDualField:
    """Test suite for dual-field template seeding (Handover 0106)."""

    async def test_seeds_system_instructions(self, db_session: AsyncSession):
        """Verify system_instructions populated for all templates."""
        tenant_key = "test_tenant_system"

        # Seed templates
        count = await seed_tenant_templates(db_session, tenant_key)

        # Verify count
        assert count == 6, "Should seed 6 default templates"

        # Fetch all templates
        result = await db_session.execute(
            select(AgentTemplate).where(AgentTemplate.tenant_key == tenant_key)
        )
        templates = result.scalars().all()

        # Verify all have system_instructions
        assert len(templates) == 6, "Should have 6 templates"

        for template in templates:
            assert template.system_instructions is not None, f"{template.role} missing system_instructions"
            assert len(template.system_instructions) > 0, f"{template.role} has empty system_instructions"
            assert "MCP" in template.system_instructions.upper(), f"{template.role} missing MCP content"

    async def test_seeds_user_instructions(self, db_session: AsyncSession):
        """Verify user_instructions populated with role-specific content."""
        tenant_key = "test_tenant_user"

        # Seed templates
        count = await seed_tenant_templates(db_session, tenant_key)

        # Verify count
        assert count == 6

        # Fetch all templates
        result = await db_session.execute(
            select(AgentTemplate).where(AgentTemplate.tenant_key == tenant_key)
        )
        templates = result.scalars().all()

        # Verify all have user_instructions
        for template in templates:
            assert template.user_instructions is not None, f"{template.role} missing user_instructions"
            assert len(template.user_instructions) > 0, f"{template.role} has empty user_instructions"

            # Verify role-specific content (each role should have unique instructions)
            if template.role == "orchestrator":
                assert "orchestrator" in template.user_instructions.lower()
            elif template.role == "implementer":
                assert "implementation" in template.user_instructions.lower() or "implementer" in template.user_instructions.lower()
            elif template.role == "tester":
                assert "test" in template.user_instructions.lower()

    async def test_system_instructions_identical(self, db_session: AsyncSession):
        """Verify all templates get same system_instructions."""
        tenant_key = "test_tenant_identical"

        # Seed templates
        await seed_tenant_templates(db_session, tenant_key)

        # Fetch all templates
        result = await db_session.execute(
            select(AgentTemplate.system_instructions).where(
                AgentTemplate.tenant_key == tenant_key
            )
        )
        system_instructions_list = [row[0] for row in result.fetchall()]

        # Verify all system instructions are identical
        assert len(system_instructions_list) == 6, "Should have 6 templates"
        assert len(set(system_instructions_list)) == 1, "All templates should have identical system_instructions"

    async def test_user_instructions_unique(self, db_session: AsyncSession):
        """Verify each role gets unique user_instructions."""
        tenant_key = "test_tenant_unique"

        # Seed templates
        await seed_tenant_templates(db_session, tenant_key)

        # Fetch all templates
        result = await db_session.execute(
            select(AgentTemplate.role, AgentTemplate.user_instructions).where(
                AgentTemplate.tenant_key == tenant_key
            )
        )
        user_instructions_by_role = {row[0]: row[1] for row in result.fetchall()}

        # Verify each role has unique user instructions
        assert len(user_instructions_by_role) == 6, "Should have 6 unique roles"

        # Verify no duplicates (all user_instructions are unique)
        user_instructions_values = list(user_instructions_by_role.values())
        assert len(set(user_instructions_values)) == 6, "All user_instructions should be unique per role"

        # Verify each role has content matching its role
        assert "orchestrator" in user_instructions_by_role["orchestrator"].lower()
        assert "analyzer" in user_instructions_by_role["analyzer"].lower() or "analysis" in user_instructions_by_role["analyzer"].lower()
        assert "implementer" in user_instructions_by_role["implementer"].lower() or "implementation" in user_instructions_by_role["implementer"].lower()
        assert "tester" in user_instructions_by_role["tester"].lower() or "test" in user_instructions_by_role["tester"].lower()
        assert "reviewer" in user_instructions_by_role["reviewer"].lower() or "review" in user_instructions_by_role["reviewer"].lower()
        assert "documenter" in user_instructions_by_role["documenter"].lower() or "documentation" in user_instructions_by_role["documenter"].lower()

    async def test_system_instructions_populated(self, db_session: AsyncSession):
        """Verify system_instructions populated correctly."""
        tenant_key = "test_tenant_legacy"

        # Seed templates
        await seed_tenant_templates(db_session, tenant_key)

        # Fetch all templates
        result = await db_session.execute(
            select(AgentTemplate).where(AgentTemplate.tenant_key == tenant_key)
        )
        templates = result.scalars().all()

        # Verify system_instructions field populated
        for template in templates:
            # system_instructions should be populated
            assert template.system_instructions, f"Template {template.role} should have system_instructions"

            # Check content is reasonable
            actual = template.system_instructions.strip()
            assert len(actual) > 0, f"Template {template.role} system_instructions should not be empty"

            assert actual == expected, (
                f"{template.role} system_instructions doesn't match system + user\n"
                f"Expected: {expected[:100]}...\n"
                f"Actual: {actual[:100]}..."
            )

    async def test_required_mcp_tools_in_system(self, db_session: AsyncSession):
        """Verify all MCP tools present in system_instructions."""
        tenant_key = "test_tenant_mcp_tools"

        # Seed templates
        await seed_tenant_templates(db_session, tenant_key)

        # Fetch all templates
        result = await db_session.execute(
            select(AgentTemplate).where(AgentTemplate.tenant_key == tenant_key)
        )
        templates = result.scalars().all()

        # Required MCP tools that MUST be in system_instructions
        # Note: Tool names use underscores (_) not dashes (-)
        required_tools = [
            "mcp__giljo_mcp__get_pending_jobs",
            "mcp__giljo_mcp__acknowledge_job",
            "mcp__giljo_mcp__report_progress",
            "mcp__giljo_mcp__get_next_instruction",
            "mcp__giljo_mcp__complete_job",
            "mcp__giljo_mcp__report_error",
            "mcp__giljo_mcp__update_job_status",
        ]

        # Verify all templates have all required MCP tools
        for template in templates:
            system_inst = template.system_instructions

            for tool in required_tools:
                assert tool in system_inst, (
                    f"{template.role} missing required MCP tool: {tool}\n"
                    f"System instructions: {system_inst[:200]}..."
                )

    async def test_system_instructions_not_in_user(self, db_session: AsyncSession):
        """Verify system_instructions content NOT duplicated in user_instructions."""
        tenant_key = "test_tenant_no_dup"

        # Seed templates
        await seed_tenant_templates(db_session, tenant_key)

        # Fetch all templates
        result = await db_session.execute(
            select(AgentTemplate).where(AgentTemplate.tenant_key == tenant_key)
        )
        templates = result.scalars().all()

        # Verify user_instructions don't contain MCP coordination content
        for template in templates:
            user_inst = template.user_instructions.upper()

            # User instructions should NOT contain MCP tools (those are in system)
            assert "MCP__GILJO-MCP__ACKNOWLEDGE_JOB" not in user_inst, (
                f"{template.role} user_instructions contains MCP tools (should be in system only)"
            )
            assert "MCP__GILJO-MCP__REPORT_PROGRESS" not in user_inst, (
                f"{template.role} user_instructions contains MCP tools (should be in system only)"
            )

    async def test_idempotent_seeding(self, db_session: AsyncSession):
        """Verify seeding is idempotent (safe to run multiple times)."""
        tenant_key = "test_tenant_idempotent"

        # Seed first time
        count1 = await seed_tenant_templates(db_session, tenant_key)
        assert count1 == 6, "First seed should create 6 templates"

        # Seed second time (should skip)
        count2 = await seed_tenant_templates(db_session, tenant_key)
        assert count2 == 0, "Second seed should skip (idempotent)"

        # Verify still only 6 templates
        result = await db_session.execute(
            select(AgentTemplate).where(AgentTemplate.tenant_key == tenant_key)
        )
        templates = result.scalars().all()
        assert len(templates) == 6, "Should still have exactly 6 templates after idempotent run"

    async def test_system_instructions_non_null(self, db_session: AsyncSession):
        """Verify system_instructions is never NULL."""
        tenant_key = "test_tenant_non_null"

        # Seed templates
        await seed_tenant_templates(db_session, tenant_key)

        # Fetch all templates and verify system_instructions NOT NULL
        result = await db_session.execute(
            select(AgentTemplate).where(AgentTemplate.tenant_key == tenant_key)
        )
        templates = result.scalars().all()

        for template in templates:
            assert template.system_instructions is not None, f"{template.role} has NULL system_instructions"
            assert len(template.system_instructions) > 0, f"{template.role} has empty system_instructions"

    async def test_user_instructions_can_be_null(self, db_session: AsyncSession):
        """Verify user_instructions can be NULL (optional field)."""
        # This test verifies schema allows NULL user_instructions
        # (though current implementation always populates it)
        tenant_key = "test_tenant_user_null"

        # Create template with NULL user_instructions
        template = AgentTemplate(
            tenant_key=tenant_key,
            name="test_template",
            category="role",
            role="test_role",
            cli_tool="claude",
            background_color="#FFFFFF",
            description="Test template",
            system_instructions="Test system instructions",
            user_instructions=None,  # NULL allowed
            model="sonnet",
            version="1.0.0",
            is_active=True,
            is_default=False,
            tags=["test"],
            created_at=datetime.now(timezone.utc),
        )

        db_session.add(template)
        await db_session.commit()

        # Fetch and verify
        result = await db_session.execute(
            select(AgentTemplate).where(
                AgentTemplate.tenant_key == tenant_key,
                AgentTemplate.name == "test_template",
            )
        )
        fetched = result.scalar_one()

        assert fetched.system_instructions is not None, "system_instructions should not be NULL"
        assert fetched.user_instructions is None, "user_instructions should be NULL as set"

    async def test_multi_tenant_isolation(self, db_session: AsyncSession):
        """Verify templates are isolated by tenant_key."""
        tenant1 = "tenant_a"
        tenant2 = "tenant_b"

        # Seed both tenants
        count1 = await seed_tenant_templates(db_session, tenant1)
        count2 = await seed_tenant_templates(db_session, tenant2)

        assert count1 == 6, "Tenant A should have 6 templates"
        assert count2 == 6, "Tenant B should have 6 templates"

        # Verify isolation
        result1 = await db_session.execute(
            select(AgentTemplate).where(AgentTemplate.tenant_key == tenant1)
        )
        templates1 = result1.scalars().all()

        result2 = await db_session.execute(
            select(AgentTemplate).where(AgentTemplate.tenant_key == tenant2)
        )
        templates2 = result2.scalars().all()

        assert len(templates1) == 6, "Tenant A should have 6 templates"
        assert len(templates2) == 6, "Tenant B should have 6 templates"

        # Verify no cross-tenant contamination
        tenant1_ids = {t.id for t in templates1}
        tenant2_ids = {t.id for t in templates2}
        assert tenant1_ids.isdisjoint(tenant2_ids), "Template IDs should be unique across tenants"


class TestMCPCoordinationSection:
    """Test MCP coordination section generation."""

    def test_mcp_section_contains_required_tools(self):
        """Verify MCP section contains all required tools."""
        mcp_section = _get_mcp_coordination_section()

        # Note: Tool names use underscores (_) not dashes (-)
        required_tools = [
            "mcp__giljo_mcp__get_pending_jobs",
            "mcp__giljo_mcp__acknowledge_job",
            "mcp__giljo_mcp__report_progress",
            "mcp__giljo_mcp__get_next_instruction",
            "mcp__giljo_mcp__complete_job",
            "mcp__giljo_mcp__report_error",
            "mcp__giljo_mcp__update_job_status",
        ]

        for tool in required_tools:
            assert tool in mcp_section, f"MCP section missing required tool: {tool}"

    def test_mcp_section_has_proper_structure(self):
        """Verify MCP section has proper markdown structure."""
        mcp_section = _get_mcp_coordination_section()

        # Should have proper markdown headers
        assert "## MCP COMMUNICATION PROTOCOL" in mcp_section.upper()
        assert "### " in mcp_section, "Should have subsections"

        # Should have checkpoint instructions
        assert "CHECKPOINT" in mcp_section.upper()
        assert "Phase 1" in mcp_section or "PHASE 1" in mcp_section.upper()

    def test_mcp_section_includes_status_updates(self):
        """Verify MCP section includes job status update instructions."""
        mcp_section = _get_mcp_coordination_section()

        # Should include status update tool
        assert "mcp__giljo_mcp__update_job_status" in mcp_section

        # Should include status values
        assert "active" in mcp_section.lower()
        assert "blocked" in mcp_section.lower()
        assert "completed" in mcp_section.lower()


class TestDefaultTemplatesV103:
    """Test default template definitions."""

    def test_all_six_roles_defined(self):
        """Verify all 6 roles have template definitions."""
        templates = _get_default_templates_v103()

        assert len(templates) == 6, "Should have 6 default templates"

        roles = {t["role"] for t in templates}
        expected_roles = {"orchestrator", "analyzer", "implementer", "tester", "reviewer", "documenter"}

        assert roles == expected_roles, f"Missing roles: {expected_roles - roles}"

    def test_all_templates_have_required_fields(self):
        """Verify all templates have required fields."""
        templates = _get_default_templates_v103()

        required_fields = {
            "name",
            "role",
            "cli_tool",
            "background_color",
            "description",
            "system_instructions",
            "model",
            "behavioral_rules",
            "success_criteria",
            "is_active",
            "is_default",
            "version",
        }

        for template in templates:
            template_fields = set(template.keys())
            missing_fields = required_fields - template_fields

            assert not missing_fields, f"{template['role']} missing fields: {missing_fields}"

    def test_system_instructions_not_empty(self):
        """Verify system_instructions is not empty for all roles."""
        templates = _get_default_templates_v103()

        for template in templates:
            assert template["system_instructions"], f"{template['role']} has empty system_instructions"
            assert len(template["system_instructions"]) > 100, f"{template['role']} system_instructions too short"

    def test_behavioral_rules_not_empty(self):
        """Verify behavioral_rules is not empty for all roles."""
        templates = _get_default_templates_v103()

        for template in templates:
            assert template["behavioral_rules"], f"{template['role']} has empty behavioral_rules"
            assert isinstance(template["behavioral_rules"], list), f"{template['role']} behavioral_rules not a list"
            assert len(template["behavioral_rules"]) >= 3, f"{template['role']} needs more behavioral rules"

    def test_success_criteria_not_empty(self):
        """Verify success_criteria is not empty for all roles."""
        templates = _get_default_templates_v103()

        for template in templates:
            assert template["success_criteria"], f"{template['role']} has empty success_criteria"
            assert isinstance(template["success_criteria"], list), f"{template['role']} success_criteria not a list"
            assert len(template["success_criteria"]) >= 3, f"{template['role']} needs more success criteria"
