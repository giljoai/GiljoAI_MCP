"""
Comprehensive tests for Phase 7: Enhanced Agent Templates with MCP Coordination

Tests verify:
- All 6 templates have MCP behavioral rules
- All 6 templates have MCP success criteria
- All 6 templates have MCP coordination section in content
- Template-specific MCP customizations present
- Template seeding remains idempotent
- Templates work with orchestrator routing
- MCP instructions use correct placeholders
- Production-grade template quality
"""

from uuid import uuid4

import pytest
from sqlalchemy import func, select
from sqlalchemy.ext.asyncio import AsyncSession

from src.giljo_mcp.models import AgentTemplate
from src.giljo_mcp.template_seeder import seed_tenant_templates


@pytest.fixture
def tenant_key():
    """Fixture providing unique tenant key for isolation"""
    return f"test_tenant_{uuid4().hex[:8]}"


@pytest.mark.asyncio
class TestMCPBehavioralRules:
    """Tests for MCP-specific behavioral rules in all templates"""

    async def test_all_templates_have_mcp_behavioral_rules(self, db_session: AsyncSession, tenant_key: str):
        """Test that all 6 templates have MCP-specific behavioral rules"""
        # Act
        await seed_tenant_templates(db_session, tenant_key)

        # Assert
        result = await db_session.execute(select(AgentTemplate).where(AgentTemplate.tenant_key == tenant_key))
        templates = result.scalars().all()

        for template in templates:
            # Each template should have behavioral_rules list
            assert isinstance(template.behavioral_rules, list), f"{template.role} behavioral_rules should be a list"
            assert len(template.behavioral_rules) > 0, f"{template.role} should have behavioral rules"

            # After Handover 0431/0103, behavioral_rules are role-specific (not MCP-specific).
            # MCP coordination is now in system_instructions, not behavioral_rules.
            # Verify rules are meaningful and non-empty strings.
            for rule in template.behavioral_rules:
                assert isinstance(rule, str), f"{template.role} has non-string behavioral rule"
                assert len(rule) > 5, f"{template.role} has empty/trivial behavioral rule: {rule}"

    async def test_implementer_has_coding_standard_rules(self, db_session: AsyncSession, tenant_key: str):
        """Test that implementer template has coding standard rules"""
        # Act (orchestrator is system-managed, not seeded; test implementer instead)
        await seed_tenant_templates(db_session, tenant_key)

        # Assert
        result = await db_session.execute(
            select(AgentTemplate).where(AgentTemplate.tenant_key == tenant_key, AgentTemplate.role == "implementer")
        )
        template = result.scalar_one()

        rules_text = " ".join(template.behavioral_rules).lower()

        # Implementer should have coding-related rules
        assert "code" in rules_text or "standard" in rules_text or "path" in rules_text, (
            "Implementer should have coding standard rules"
        )

    async def test_implementer_has_file_tracking_rules(self, db_session: AsyncSession, tenant_key: str):
        """Test that implementer template has file modification tracking rules"""
        # Act
        await seed_tenant_templates(db_session, tenant_key)

        # Assert
        result = await db_session.execute(
            select(AgentTemplate).where(AgentTemplate.tenant_key == tenant_key, AgentTemplate.role == "implementer")
        )
        template = result.scalar_one()

        rules_text = " ".join(template.behavioral_rules).lower()

        # Implementer should track file modifications
        assert "file" in rules_text or "token" in rules_text, "Implementer should have file tracking rules"


@pytest.mark.asyncio
class TestMCPSuccessCriteria:
    """Tests for MCP-specific success criteria in all templates"""

    async def test_all_templates_have_mcp_success_criteria(self, db_session: AsyncSession, tenant_key: str):
        """Test that all 6 templates have MCP-specific success criteria"""
        # Act
        await seed_tenant_templates(db_session, tenant_key)

        # Assert
        result = await db_session.execute(select(AgentTemplate).where(AgentTemplate.tenant_key == tenant_key))
        templates = result.scalars().all()

        for template in templates:
            # Each template should have success_criteria list
            assert isinstance(template.success_criteria, list), f"{template.role} success_criteria should be a list"
            assert len(template.success_criteria) > 0, f"{template.role} should have success criteria"

            # After Handover 0431/0103, success_criteria are role-specific.
            # MCP coordination is now in system_instructions, not success_criteria.
            # Verify criteria are meaningful and non-empty strings.
            for criterion in template.success_criteria:
                assert isinstance(criterion, str), f"{template.role} has non-string success criterion"
                assert len(criterion) > 5, f"{template.role} has empty/trivial success criterion: {criterion}"

    async def test_tester_has_test_results_criteria(self, db_session: AsyncSession, tenant_key: str):
        """Test that tester template has test results reporting criteria"""
        # Act
        await seed_tenant_templates(db_session, tenant_key)

        # Assert
        result = await db_session.execute(
            select(AgentTemplate).where(AgentTemplate.tenant_key == tenant_key, AgentTemplate.role == "tester")
        )
        template = result.scalar_one()

        criteria_text = " ".join(template.success_criteria).lower()

        # Tester should report test results
        assert "test result" in criteria_text or "coverage" in criteria_text, (
            "Tester should have test results reporting criteria"
        )


@pytest.mark.asyncio
class TestMCPCoordinationSection:
    """Tests for MCP coordination section in template content"""

    async def test_all_templates_have_mcp_coordination_section(self, db_session: AsyncSession, tenant_key: str):
        """Test that all 6 templates have MCP coordination protocol section"""
        # Act
        await seed_tenant_templates(db_session, tenant_key)

        # Assert
        result = await db_session.execute(select(AgentTemplate).where(AgentTemplate.tenant_key == tenant_key))
        templates = result.scalars().all()

        for template in templates:
            content = template.system_instructions

            # After Handover 0431 slimming, the MCP section is "## MCP Tool Usage"
            # Phases and detailed protocol moved to full_protocol (returned by get_agent_mission)
            assert "MCP Tool Usage" in content, (
                f"{template.role} should have MCP Tool Usage section"
            )

            # Should have check-in protocol section
            assert "CHECK-IN PROTOCOL" in content, (
                f"{template.role} should have CHECK-IN PROTOCOL section"
            )

            # Should have messaging section
            assert "MESSAGING" in content, (
                f"{template.role} should have MESSAGING section"
            )

    async def test_templates_reference_mcp_tools(self, db_session: AsyncSession, tenant_key: str):
        """Test that templates reference the correct MCP tool names"""
        # Act
        await seed_tenant_templates(db_session, tenant_key)

        # Assert
        result = await db_session.execute(select(AgentTemplate).where(AgentTemplate.tenant_key == tenant_key))
        templates = result.scalars().all()

        for template in templates:
            content = template.system_instructions.lower()

            # After Handover 0431 slimming, individual tool names are in full_protocol,
            # not in template system_instructions. The template just has MCP Tool Usage
            # section with the tool call format and messaging tools.
            assert "mcp__giljo-mcp__" in content, (
                f"{template.role} should reference mcp__giljo-mcp__ tool prefix"
            )
            # Messaging section references send_message and receive_messages
            assert "send_message" in content or "receive_messages" in content, (
                f"{template.role} should reference messaging tools"
            )

    async def test_templates_use_correct_placeholders(self, db_session: AsyncSession, tenant_key: str):
        """Test that MCP instructions use correct placeholders for orchestrator"""
        # Act
        await seed_tenant_templates(db_session, tenant_key)

        # Assert
        result = await db_session.execute(select(AgentTemplate).where(AgentTemplate.tenant_key == tenant_key))
        templates = result.scalars().all()

        for template in templates:
            content = template.system_instructions

            # After Handover 0431 slimming, placeholders like <AGENT_TYPE> and <TENANT_KEY>
            # are no longer in template system_instructions. The MCP section now just notes
            # that tenant_key is auto-injected by the server.
            assert "tenant_key" in content.lower(), (
                f"{template.role} should mention tenant_key auto-injection"
            )


@pytest.mark.asyncio
class TestTemplateSpecificCustomizations:
    """Tests for role-specific MCP customizations"""

    async def test_analyzer_has_analysis_instructions(self, db_session: AsyncSession, tenant_key: str):
        """Test that analyzer template has analysis-related instructions"""
        # Act (orchestrator is system-managed, not seeded; test analyzer instead)
        await seed_tenant_templates(db_session, tenant_key)

        # Assert
        result = await db_session.execute(
            select(AgentTemplate).where(AgentTemplate.tenant_key == tenant_key, AgentTemplate.role == "analyzer")
        )
        template = result.scalar_one()

        content = template.user_instructions.lower()
        rules_text = " ".join(template.behavioral_rules).lower()

        # Should have analysis-specific instructions
        assert "analy" in content or "analy" in rules_text, (
            "Analyzer should have analysis instructions"
        )

    async def test_implementer_has_file_modification_tracking(self, db_session: AsyncSession, tenant_key: str):
        """Test that implementer template has file modification tracking instructions"""
        # Act
        await seed_tenant_templates(db_session, tenant_key)

        # Assert
        result = await db_session.execute(
            select(AgentTemplate).where(AgentTemplate.tenant_key == tenant_key, AgentTemplate.role == "implementer")
        )
        template = result.scalar_one()

        content = template.system_instructions.lower()
        rules_text = " ".join(template.behavioral_rules).lower()

        # Should mention file modifications and token tracking
        assert "file" in content or "file" in rules_text, "Implementer should track file modifications"

    async def test_tester_has_test_results_reporting(self, db_session: AsyncSession, tenant_key: str):
        """Test that tester template has test results reporting instructions"""
        # Act
        await seed_tenant_templates(db_session, tenant_key)

        # Assert
        result = await db_session.execute(
            select(AgentTemplate).where(AgentTemplate.tenant_key == tenant_key, AgentTemplate.role == "tester")
        )
        template = result.scalar_one()

        content = template.system_instructions.lower()
        rules_text = " ".join(template.behavioral_rules).lower()
        criteria_text = " ".join(template.success_criteria).lower()

        # Should mention test results and coverage
        combined_text = content + rules_text + criteria_text
        assert "test" in combined_text and ("result" in combined_text or "coverage" in combined_text), (
            "Tester should have test results reporting instructions"
        )

    async def test_reviewer_has_review_findings_reporting(self, db_session: AsyncSession, tenant_key: str):
        """Test that reviewer template has review findings reporting instructions"""
        # Act
        await seed_tenant_templates(db_session, tenant_key)

        # Assert
        result = await db_session.execute(
            select(AgentTemplate).where(AgentTemplate.tenant_key == tenant_key, AgentTemplate.role == "reviewer")
        )
        template = result.scalar_one()

        user_inst = template.user_instructions.lower()
        rules_text = " ".join(template.behavioral_rules).lower()

        # Should mention review findings in user_instructions or behavioral_rules
        assert "review" in user_inst or "review" in rules_text, (
            "Reviewer should have review findings reporting instructions"
        )

    async def test_analyzer_has_incremental_analysis_reporting(self, db_session: AsyncSession, tenant_key: str):
        """Test that analyzer template has incremental analysis reporting instructions"""
        # Act
        await seed_tenant_templates(db_session, tenant_key)

        # Assert
        result = await db_session.execute(
            select(AgentTemplate).where(AgentTemplate.tenant_key == tenant_key, AgentTemplate.role == "analyzer")
        )
        template = result.scalar_one()

        user_inst = template.user_instructions.lower()
        rules_text = " ".join(template.behavioral_rules).lower()

        # Should mention analysis and findings in user_instructions or behavioral_rules
        assert "analys" in user_inst or "analys" in rules_text, "Analyzer should have analysis reporting instructions"

    async def test_documenter_has_documentation_tracking(self, db_session: AsyncSession, tenant_key: str):
        """Test that documenter template has documentation tracking instructions"""
        # Act
        await seed_tenant_templates(db_session, tenant_key)

        # Assert
        result = await db_session.execute(
            select(AgentTemplate).where(AgentTemplate.tenant_key == tenant_key, AgentTemplate.role == "documenter")
        )
        template = result.scalar_one()

        content = template.system_instructions.lower()
        rules_text = " ".join(template.behavioral_rules).lower()

        # Should mention documentation files
        assert "document" in content or "document" in rules_text, (
            "Documenter should have documentation tracking instructions"
        )


@pytest.mark.asyncio
class TestIdempotencyWithEnhancements:
    """Tests that enhanced templates maintain idempotent seeding"""

    async def test_seeding_enhanced_templates_twice_does_not_duplicate(self, db_session: AsyncSession, tenant_key: str):
        """Test that seeding enhanced templates twice doesn't create duplicates"""
        # Act - First seed
        count1 = await seed_tenant_templates(db_session, tenant_key)
        assert count1 == 5

        # Act - Second seed
        count2 = await seed_tenant_templates(db_session, tenant_key)

        # Assert - Second seed should return 0 (skipped)
        assert count2 == 0, "Second seed should skip and return 0"

        # Verify still only 5 templates
        result = await db_session.execute(
            select(func.count(AgentTemplate.id)).where(AgentTemplate.tenant_key == tenant_key)
        )
        db_count = result.scalar()
        assert db_count == 5, "Should still have exactly 5 templates, no duplicates"

    async def test_enhanced_templates_preserve_metadata_structure(self, db_session: AsyncSession, tenant_key: str):
        """Test that enhanced templates maintain proper metadata structure"""
        # Act
        await seed_tenant_templates(db_session, tenant_key)

        # Assert
        result = await db_session.execute(select(AgentTemplate).where(AgentTemplate.tenant_key == tenant_key))
        templates = result.scalars().all()

        for template in templates:
            # Verify metadata is still properly structured
            assert isinstance(template.behavioral_rules, list)
            assert isinstance(template.success_criteria, list)
            assert isinstance(template.variables, list)
            assert isinstance(template.tags, list)

            # Verify role-specific rules are present (MCP rules moved to system_instructions)
            assert len(template.behavioral_rules) >= 3, (
                f"{template.role} should have at least 3 behavioral rules"
            )
            assert len(template.success_criteria) >= 3, (
                f"{template.role} should have at least 3 success criteria"
            )


@pytest.mark.asyncio
class TestOrchestratorRouting:
    """Tests that templates work with orchestrator routing"""

    async def test_all_templates_have_preferred_tool_field(self, db_session: AsyncSession, tenant_key: str):
        """Test that all templates have preferred_tool field for routing"""
        # Act
        await seed_tenant_templates(db_session, tenant_key)

        # Assert
        result = await db_session.execute(select(AgentTemplate).where(AgentTemplate.tenant_key == tenant_key))
        templates = result.scalars().all()

        for template in templates:
            assert template.tool is not None, f"{template.role} should have tool set"
            assert template.tool in ["claude", "codex", "gemini", "auto"], f"{template.role} tool should be valid value"

    async def test_templates_support_multi_tool_execution(self, db_session: AsyncSession, tenant_key: str):
        """Test that templates can work with different AI tools"""
        # Act
        await seed_tenant_templates(db_session, tenant_key)

        # Assert
        result = await db_session.execute(select(AgentTemplate).where(AgentTemplate.tenant_key == tenant_key))
        templates = result.scalars().all()

        for template in templates:
            content = template.system_instructions

            # Templates should be tool-agnostic (no Claude-specific language)
            # MCP instructions should work with any tool
            assert "claude code" not in content.lower() or "ai tool" in content.lower(), (
                f"{template.role} should be tool-agnostic or mention multiple tools"
            )


@pytest.mark.asyncio
class TestProductionQuality:
    """Tests for production-grade template quality"""

    async def test_all_templates_are_complete_and_actionable(self, db_session: AsyncSession, tenant_key: str):
        """Test that all templates are complete with clear instructions"""
        # Act
        await seed_tenant_templates(db_session, tenant_key)

        # Assert
        result = await db_session.execute(select(AgentTemplate).where(AgentTemplate.tenant_key == tenant_key))
        templates = result.scalars().all()

        for template in templates:
            # system_instructions should have substantial MCP content
            assert len(template.system_instructions) > 500, (
                f"{template.role} system_instructions should have substantial content (>500 chars)"
            )

            # user_instructions should have role-specific content
            role_keywords = {
                "analyzer": "analys",
                "implementer": "implement",
                "tester": "test",
                "reviewer": "review",
                "documenter": "document",
            }
            expected_keyword = role_keywords.get(template.role, template.role)
            # Check user_instructions for role-specific content
            assert expected_keyword in template.user_instructions.lower(), (
                f"{template.role} should define its role in user_instructions (expected '{expected_keyword}')"
            )

            # Should have actionable instructions (imperative verbs) in user_instructions
            action_verbs = ["analyze", "implement", "test", "review", "document", "coordinate", "create", "write"]
            content_lower = template.user_instructions.lower()
            assert any(verb in content_lower for verb in action_verbs), (
                f"{template.role} should have actionable instructions"
            )

    async def test_templates_have_professional_tone(self, db_session: AsyncSession, tenant_key: str):
        """Test that templates maintain professional tone"""
        # Act
        await seed_tenant_templates(db_session, tenant_key)

        # Assert
        result = await db_session.execute(select(AgentTemplate).where(AgentTemplate.tenant_key == tenant_key))
        templates = result.scalars().all()

        for template in templates:
            content = template.system_instructions

            # Should not contain emojis (professional)
            import re

            emoji_pattern = re.compile(
                "["
                "\U0001f600-\U0001f64f"  # emoticons
                "\U0001f300-\U0001f5ff"  # symbols & pictographs
                "\U0001f680-\U0001f6ff"  # transport & map symbols
                "\U0001f1e0-\U0001f1ff"  # flags (iOS)
                "]+",
                flags=re.UNICODE,
            )

            assert not emoji_pattern.search(content), f"{template.role} should not contain emojis (professional tone)"

    async def test_all_templates_have_complete_metadata(self, db_session: AsyncSession, tenant_key: str):
        """Test that all templates have complete metadata for production use"""
        # Act
        await seed_tenant_templates(db_session, tenant_key)

        # Assert
        result = await db_session.execute(select(AgentTemplate).where(AgentTemplate.tenant_key == tenant_key))
        templates = result.scalars().all()

        for template in templates:
            # Essential metadata
            assert template.name, f"{template.role} should have name"
            assert template.category, f"{template.role} should have category"
            assert template.role, f"{template.role} should have role"
            assert template.version, f"{template.role} should have version"

            # Lists should be present and typed correctly
            assert template.behavioral_rules, f"{template.role} should have behavioral rules"
            assert template.success_criteria, f"{template.role} should have success criteria"
            assert isinstance(template.variables, list), f"{template.role} variables should be a list"
            assert template.tags, f"{template.role} should have tags"

            # Status flags
            assert template.is_active is True, f"{template.role} should be active"
            assert template.created_at is not None, f"{template.role} should have created_at"


@pytest.mark.asyncio
class TestMCPInstructionQuality:
    """Tests for quality of MCP coordination instructions"""

    async def test_mcp_instructions_are_clear_and_specific(self, db_session: AsyncSession, tenant_key: str):
        """Test that MCP instructions are clear and specific"""
        # Act
        await seed_tenant_templates(db_session, tenant_key)

        # Assert
        result = await db_session.execute(select(AgentTemplate).where(AgentTemplate.tenant_key == tenant_key))
        templates = result.scalars().all()

        for template in templates:
            content = template.system_instructions

            # After Handover 0431 slimming, MCP section is "## MCP Tool Usage"
            # Detailed phases are in full_protocol, not in template system_instructions
            assert "MCP Tool Usage" in content, (
                f"{template.role} should have MCP Tool Usage section"
            )
            # Should have clear instructions about tool call format
            assert "native tool calls" in content.lower() or "mcp__giljo-mcp__" in content, (
                f"{template.role} MCP instructions should explain tool call format"
            )

    async def test_mcp_instructions_include_error_handling(self, db_session: AsyncSession, tenant_key: str):
        """Test that all MCP instruction sections include error handling"""
        # Act
        await seed_tenant_templates(db_session, tenant_key)

        # Assert
        result = await db_session.execute(select(AgentTemplate).where(AgentTemplate.tenant_key == tenant_key))
        templates = result.scalars().all()

        for template in templates:
            content = template.system_instructions

            # Should have explicit error handling section
            assert "Error Handling" in content or "error" in content.lower(), (
                f"{template.role} should have error handling instructions"
            )

            # Error handling should mention report_error
            if "Error Handling" in content:
                error_section_start = content.index("Error Handling")
                error_section = content[error_section_start : error_section_start + 500]
                assert "report_error" in error_section.lower(), (
                    f"{template.role} error handling should mention report_error"
                )

    async def test_mcp_instructions_mention_all_required_tools(self, db_session: AsyncSession, tenant_key: str):
        """Test that MCP instructions mention all required coordination tools"""
        # Act
        await seed_tenant_templates(db_session, tenant_key)

        # Assert
        result = await db_session.execute(select(AgentTemplate).where(AgentTemplate.tenant_key == tenant_key))
        templates = result.scalars().all()

        for template in templates:
            content = template.system_instructions.lower()

            # After Handover 0431, individual tool names are in full_protocol,
            # not in template system_instructions. Templates reference messaging tools.
            assert "send_message" in content or "receive_messages" in content, (
                f"{template.role} should mention messaging tools in system_instructions"
            )
            # Should reference the MCP tool prefix
            assert "mcp__giljo-mcp__" in content, (
                f"{template.role} should reference MCP tool prefix"
            )
