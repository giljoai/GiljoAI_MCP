"""
Test script for the Mission Template Generator system.

Tests comprehensive mission generation for orchestrator and agents.
"""

import sys
from pathlib import Path


# Add src to path
sys.path.insert(0, str(Path(__file__).parent.parent.parent))

# Note: mission_templates.py was deleted and unified into template_manager.py
from src.giljo_mcp.enums import AgentRole, ProjectType
from src.giljo_mcp.template_adapter import MissionTemplateGeneratorV2 as MissionTemplateGenerator


def test_orchestrator_template():
    """Test orchestrator mission generation."""

    generator = MissionTemplateGenerator()

    # Test basic orchestrator mission
    mission = generator.generate_orchestrator_mission(
        project_name="3.4 GiljoAI Mission Templates",
        project_mission="Implement comprehensive mission templates with vision guardian and scope sheriff roles",
        product_name="GiljoAI-MCP Coding Orchestrator",
    )

    # Verify key components are present
    assert "VISION GUARDIAN" in mission
    assert "SCOPE SHERIFF" in mission
    assert "get_vision()" in mission
    assert "chunked" in mission
    assert "Serena MCP" in mission

    # Test with project type customization
    mission_with_type = generator.generate_orchestrator_mission(
        project_name="Test Project",
        project_mission="Test mission",
        additional_context={"project_type": ProjectType.ORCHESTRATION},
    )

    assert "PROJECT TYPE GUIDANCE" in mission_with_type
    assert "Concurrency" in mission_with_type


def test_agent_templates():
    """Test role-specific agent templates."""

    generator = MissionTemplateGenerator()

    roles_to_test = [AgentRole.ANALYZER, AgentRole.IMPLEMENTER, AgentRole.TESTER, AgentRole.REVIEWER]

    for role in roles_to_test:

        mission = generator.generate_agent_mission(role=role, project_name="Test Project")

        # Print sample

        # Verify behavioral rules
        assert "Acknowledge all messages immediately" in mission
        assert "BEHAVIORAL RULES" in mission
        assert "SUCCESS CRITERIA" in mission


def test_custom_mission():
    """Test custom mission override."""

    generator = MissionTemplateGenerator()

    custom_mission = "Special custom mission for testing edge cases"
    mission = generator.generate_agent_mission(
        role=AgentRole.IMPLEMENTER, project_name="Test Project", custom_mission=custom_mission
    )

    assert custom_mission in mission


def test_handoff_instructions():
    """Test handoff instruction generation."""

    generator = MissionTemplateGenerator()

    instructions = generator.generate_handoff_instructions(
        from_role=AgentRole.ANALYZER,
        to_role=AgentRole.IMPLEMENTER,
        context_summary="Requirements analyzed, architecture designed, specifications complete",
    )

    assert "HANDOFF FROM ANALYZER TO IMPLEMENTER" in instructions
    assert "Acknowledge receipt" in instructions
    assert "CONTINUITY REQUIREMENTS" in instructions


def test_parallel_startup():
    """Test parallel agent startup instructions."""

    generator = MissionTemplateGenerator()

    agents = ["analyzer", "implementer", "tester"]
    instructions = generator.generate_parallel_startup_instructions(agents=agents, project_name="Test Project")

    assert "PARALLEL AGENT STARTUP" in instructions
    assert "analyzer" in instructions
    assert "SYNCHRONIZATION" in instructions


def test_context_limit_instructions():
    """Test context limit handling instructions."""

    generator = MissionTemplateGenerator()

    instructions = generator.generate_context_limit_instructions(
        agent_name="implementer", context_used=24000, context_budget=30000
    )

    assert "CONTEXT LIMIT APPROACHING" in instructions
    assert "80.0%" in instructions
    assert "HANDOFF PREPARATION" in instructions


def test_behavioral_rules():
    """Test behavioral rules extraction."""

    generator = MissionTemplateGenerator()

    for role in [AgentRole.ANALYZER, AgentRole.IMPLEMENTER]:
        rules = generator.get_behavioral_rules(role)

        for _rule in rules[:3]:  # Show first 3 rules
            pass

        assert len(rules) > 5  # Should have common + specific rules
        assert "Acknowledge all messages immediately upon reading" in rules


def test_acknowledgment_instruction():
    """Test acknowledgment instruction generation."""

    generator = MissionTemplateGenerator()
    instruction = generator.generate_acknowledgment_instruction()

    assert "MESSAGE ACKNOWLEDGMENT PROTOCOL" in instruction
    assert "acknowledge_message()" in instruction


def main():
    """Run all tests."""

    try:
        test_orchestrator_template()
        test_agent_templates()
        test_custom_mission()
        test_handoff_instructions()
        test_parallel_startup()
        test_context_limit_instructions()
        test_behavioral_rules()
        test_acknowledgment_instruction()

    except AssertionError:
        raise
    except Exception:
        raise


if __name__ == "__main__":
    main()
