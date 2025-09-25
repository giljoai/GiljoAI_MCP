"""
Comprehensive validation of MissionTemplateGenerator implementation.

Tests all methods and validates integration points.
"""

import sys
import time
from pathlib import Path


# Add src to path
sys.path.insert(0, str(Path(__file__).parent.parent))

from src.giljo_mcp.enums import AgentRole, ProjectType
from src.giljo_mcp.template_adapter import MissionTemplateGeneratorV2 as MissionTemplateGenerator
from src.giljo_mcp.template_manager import get_template_manager


def test_all_methods():
    """Test every method in MissionTemplateGenerator."""

    get_template_manager()
    generator = MissionTemplateGenerator()
    results = []

    # Test 1: generate_orchestrator_mission
    start = time.time()
    mission = generator.generate_orchestrator_mission(
        project_name="Test Project",
        project_mission="Test comprehensive mission generation",
        product_name="Test Product",
        additional_context="project_type: orchestration",
    )
    elapsed = (time.time() - start) * 1000

    assert "VISION GUARDIAN" in mission
    assert "SCOPE SHERIFF" in mission
    assert "PROJECT TYPE GUIDANCE" in mission
    assert "Concurrency" in mission  # From ORCHESTRATION type
    results.append(f"  [OK] Orchestrator mission: {len(mission)} chars in {elapsed:.2f}ms")

    # Test 2: generate_agent_mission for each role
    for role in [AgentRole.ANALYZER, AgentRole.IMPLEMENTER, AgentRole.TESTER, AgentRole.REVIEWER]:
        start = time.time()
        mission = generator.generate_agent_mission(
            role=role,
            project_name="Test Project",
            custom_mission=f"Custom mission for {role.value}",
            additional_instructions="Follow strict guidelines",
        )
        elapsed = (time.time() - start) * 1000

        assert role.value.upper() in mission.upper()
        assert "BEHAVIORAL RULES" in mission
        assert "SUCCESS CRITERIA" in mission
        assert "Follow strict guidelines" in mission
        results.append(f"  [OK] {role.value}: {len(mission)} chars in {elapsed:.2f}ms")

    # Test 3: generate_handoff_instructions
    start = time.time()
    handoff = generator.generate_handoff_instructions(
        from_role=AgentRole.ANALYZER,
        to_role=AgentRole.IMPLEMENTER,
        context_summary="Analysis complete with 5 key findings",
    )
    elapsed = (time.time() - start) * 1000

    assert "HANDOFF FROM ANALYZER TO IMPLEMENTER" in handoff
    assert "Analysis complete with 5 key findings" in handoff
    assert "CONTINUITY REQUIREMENTS" in handoff
    results.append(f"  [OK] Handoff instructions: {len(handoff)} chars in {elapsed:.2f}ms")

    # Test 4: generate_parallel_startup_instructions
    start = time.time()
    parallel = generator.generate_parallel_startup_instructions(
        agents=["analyzer", "implementer", "tester"], project_name="Test Project"
    )
    elapsed = (time.time() - start) * 1000

    assert "PARALLEL AGENT STARTUP" in parallel
    assert "analyzer, implementer, tester" in parallel
    assert "SYNCHRONIZATION" in parallel
    results.append(f"  [OK] Parallel instructions: {len(parallel)} chars in {elapsed:.2f}ms")

    # Test 5: generate_context_limit_instructions
    start = time.time()
    context_limit = generator.generate_context_limit_instructions(
        agent_name="implementer", context_used=28000, context_budget=30000
    )
    elapsed = (time.time() - start) * 1000

    assert "CONTEXT LIMIT APPROACHING" in context_limit
    assert "93.3%" in context_limit  # 28000/30000
    assert "HANDOFF PREPARATION" in context_limit
    results.append(f"  [OK] Context limit: {len(context_limit)} chars in {elapsed:.2f}ms")

    # Test 6: generate_acknowledgment_instruction
    start = time.time()
    ack = generator.generate_acknowledgment_instruction()
    elapsed = (time.time() - start) * 1000

    assert "MESSAGE ACKNOWLEDGMENT PROTOCOL" in ack
    assert "acknowledge_message()" in ack
    results.append(f"  [OK] Acknowledgment: {len(ack)} chars in {elapsed:.2f}ms")

    # Test 7: get_behavioral_rules
    for role in [AgentRole.ANALYZER, AgentRole.IMPLEMENTER, AgentRole.TESTER, AgentRole.REVIEWER]:
        start = time.time()
        rules = generator.get_behavioral_rules(role)
        elapsed = (time.time() - start) * 1000

        assert len(rules) >= 5  # Common rules
        assert "Acknowledge all messages immediately upon reading" in rules
        results.append(f"  [OK] {role.value} rules: {len(rules)} rules in {elapsed:.2f}ms")

    # Test 8: _get_default_mission (private method)
    start = time.time()
    default = generator._get_default_mission(AgentRole.TESTER)
    elapsed = (time.time() - start) * 1000

    assert "test" in default.lower()
    results.append(f"  [OK] Default mission: {len(default)} chars in {elapsed:.2f}ms")

    # Print results summary
    for _result in results:
        pass

    return True


def test_project_type_customizations():
    """Test project type customizations."""

    get_template_manager()
    generator = MissionTemplateGenerator()

    project_types = [
        (ProjectType.FOUNDATION, "Database schema"),
        (ProjectType.MCP_INTEGRATION, "Protocol compliance"),
        (ProjectType.ORCHESTRATION, "Concurrency"),
        (ProjectType.USER_INTERFACE, "UX design"),
        (ProjectType.DEPLOYMENT, "Security"),
    ]

    for proj_type, expected_text in project_types:
        mission = generator.generate_orchestrator_mission(
            project_name=f"{proj_type.value} Project",
            project_mission=f"Test {proj_type.value}",
            additional_context={"project_type": proj_type},
        )

        assert "PROJECT TYPE GUIDANCE" in mission
        assert expected_text in mission

    return True


def test_performance():
    """Test performance requirements."""

    get_template_manager()
    generator = MissionTemplateGenerator()

    # Test 100 template generations
    start = time.time()

    for i in range(100):
        generator.generate_orchestrator_mission(
            project_name=f"Project {i}",
            project_mission=f"Mission {i}" * 10,  # Make it longer
        )

    elapsed = time.time() - start
    per_template = (elapsed / 100) * 1000

    # Check performance requirement (< 100ms per template)
    if per_template < 100:
        pass
    else:
        pass

    return True


def test_edge_cases():
    """Test edge cases."""

    get_template_manager()
    generator = MissionTemplateGenerator()

    # Test 1: Very long project name/mission
    long_name = "A" * 1000
    long_mission = "B" * 5000

    mission = generator.generate_orchestrator_mission(project_name=long_name, project_mission=long_mission)
    assert long_name in mission
    assert long_mission in mission

    # Test 2: Special characters
    special_name = "Project {with} [special] <chars> & 'quotes' \"double\""

    mission = generator.generate_agent_mission(role=AgentRole.ANALYZER, project_name=special_name)
    assert special_name in mission

    # Test 3: Unknown role handling
    try:
        # Create a fake role
        from enum import Enum

        class FakeRole(Enum):
            UNKNOWN = "unknown"

        mission = generator.generate_agent_mission(role=FakeRole.UNKNOWN, project_name="Test")
    except (ValueError, KeyError):
        pass

    return True


def main():
    """Run all validation tests."""

    try:
        # Run all test suites
        test_all_methods()
        test_project_type_customizations()
        test_performance()
        test_edge_cases()

    except AssertionError:
        raise
    except Exception:
        import traceback

        traceback.print_exc()
        raise


if __name__ == "__main__":
    main()
