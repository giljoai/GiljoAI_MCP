"""
Integration test for MissionTemplateGenerator with ProjectOrchestrator.

Validates that the orchestrator correctly uses mission templates when spawning agents.
"""

import asyncio
import sys
from pathlib import Path


# Add src to path
sys.path.insert(0, str(Path(__file__).parent.parent))

from src.giljo_mcp.database import DatabaseManager
from src.giljo_mcp.enums import AgentRole, ProjectType
from src.giljo_mcp.orchestrator import ProjectOrchestrator
from src.giljo_mcp.template_manager import get_template_manager


async def test_orchestrator_integration():
    """Test orchestrator integration with mission templates."""

    # Initialize database
    db_manager = DatabaseManager()
    await db_manager.create_tables_async()

    # Create orchestrator
    orchestrator = ProjectOrchestrator()
    orchestrator.db_manager = db_manager

    # Create a test project
    project = await orchestrator.create_project(
        name="3.4 Mission Templates Integration",
        mission="Test mission template integration with orchestrator",
        context_budget=150000,
    )
    await orchestrator.activate_project(project.id)

    # Test 1: Spawn orchestrator agent with comprehensive template

    orch_agent = await orchestrator.spawn_agent(
        project_id=project.id, role=AgentRole.ORCHESTRATOR, project_type=ProjectType.ORCHESTRATION
    )

    # Verify comprehensive template was used
    assert "VISION GUARDIAN" in orch_agent.mission
    assert "SCOPE SHERIFF" in orch_agent.mission
    assert "get_vision()" in orch_agent.mission
    assert "Serena MCP" in orch_agent.mission
    assert "PROJECT TYPE GUIDANCE" in orch_agent.mission
    assert "Concurrency" in orch_agent.mission  # From ORCHESTRATION type

    # Test 2: Spawn analyzer with role-specific template

    analyzer = await orchestrator.spawn_agent(project_id=project.id, role=AgentRole.ANALYZER)

    assert "System Analyzer" in analyzer.mission
    assert "DISCOVERY WORKFLOW" in analyzer.mission
    assert "Serena MCP" in analyzer.mission
    assert "architectural designs" in analyzer.mission

    # Test 3: Spawn implementer with custom mission

    custom_mission = "Implement the MissionTemplateGenerator class with all methods"
    implementer = await orchestrator.spawn_agent(
        project_id=project.id, role=AgentRole.IMPLEMENTER, custom_mission=custom_mission
    )

    assert custom_mission in implementer.mission
    assert "IMPLEMENTATION WORKFLOW" in implementer.mission

    # Test 4: Parallel agent spawning

    parallel_agents = await orchestrator.spawn_agents_parallel(
        project_id=project.id,
        agents=[(AgentRole.TESTER, None), (AgentRole.REVIEWER, None)],
        project_type=ProjectType.ORCHESTRATION,
    )

    assert len(parallel_agents) == 2

    # Check both agents have parallel instructions
    for agent in parallel_agents:
        assert "PARALLEL AGENT STARTUP" in agent.mission
        assert "COORDINATION PROTOCOL" in agent.mission

    # Test 5: Context limit handling

    # Update agent context to approach limit
    await orchestrator.update_context_usage(agent_id=implementer.id, tokens_used=23000)  # Will be at 76.7% usage

    # Check if context limit message is generated
    context_message = await orchestrator.handle_context_limit(implementer.id)

    if context_message:
        assert "CONTEXT LIMIT APPROACHING" in context_message.content
        assert "HANDOFF PREPARATION" in context_message.content
    else:
        pass

    # Test 6: Handoff instructions

    handoff_message = await orchestrator.handoff(
        from_agent_id=analyzer.id,
        to_agent_id=implementer.id,
        context={"summary": "Requirements analyzed and design complete"},
    )

    handoff_data = eval(handoff_message.content)  # Parse the stringified dict
    assert "handoff_instructions" in handoff_data
    assert "HANDOFF FROM ANALYZER TO IMPLEMENTER" in handoff_data["handoff_instructions"]

    # Cleanup
    await db_manager.close_async()

    return True


async def test_template_manager_methods():
    """Test UnifiedTemplateManager methods."""

    template_manager = get_template_manager()

    # Test template generation for each role
    roles_to_test = [
        ("orchestrator", {"project_name": "Test", "project_mission": "Test mission"}),
        ("analyzer", {"custom_mission": "Analyze the system"}),
        ("implementer", {"custom_mission": "Implement features"}),
        ("tester", {"custom_mission": "Test the implementation"}),
        ("reviewer", {"custom_mission": "Review the code"}),
        ("documenter", {"custom_mission": "Document the project"}),
    ]

    for role, variables in roles_to_test:
        template = await template_manager.get_template(role=role, variables=variables)

        assert isinstance(template, str)
        assert len(template) > 0
        assert role in template.lower() or "agent" in template.lower()

    # Test behavioral rules and success criteria
    for role in ["orchestrator", "analyzer", "implementer"]:
        rules = template_manager.get_behavioral_rules(role)
        criteria = template_manager.get_success_criteria(role)

        assert isinstance(rules, list)
        assert isinstance(criteria, list)
        assert len(rules) > 0
        assert len(criteria) > 0

    return True


async def main():
    """Run all integration tests."""
    try:
        # Run integration tests
        await test_orchestrator_integration()

        # Run method validation
        await test_template_manager_methods()

    except Exception:
        import traceback

        traceback.print_exc()
        raise


if __name__ == "__main__":
    asyncio.run(main())
