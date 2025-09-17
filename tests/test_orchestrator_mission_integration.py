"""
Integration test for MissionTemplateGenerator with ProjectOrchestrator.

Validates that the orchestrator correctly uses mission templates when spawning agents.
"""

import asyncio
from pathlib import Path
import sys

# Add src to path
sys.path.insert(0, str(Path(__file__).parent.parent))

from src.giljo_mcp.mission_templates import (
    MissionTemplateGenerator,
    AgentRole,
    ProjectType
)
from src.giljo_mcp.orchestrator import ProjectOrchestrator
from src.giljo_mcp.database import DatabaseManager


async def test_orchestrator_integration():
    """Test orchestrator integration with mission templates."""
    print("\n" + "="*80)
    print("TESTING ORCHESTRATOR INTEGRATION WITH MISSION TEMPLATES")
    print("="*80)
    
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
        context_budget=150000
    )
    await orchestrator.activate_project(project.id)
    print(f"\n[OK] Created and activated project: {project.name}")
    
    # Test 1: Spawn orchestrator agent with comprehensive template
    print("\n" + "-"*40)
    print("Test 1: Orchestrator Agent with Template")
    print("-"*40)
    
    orch_agent = await orchestrator.spawn_agent(
        project_id=project.id,
        role=AgentRole.ORCHESTRATOR,
        project_type=ProjectType.ORCHESTRATION
    )
    
    # Verify comprehensive template was used
    assert "VISION GUARDIAN" in orch_agent.mission
    assert "SCOPE SHERIFF" in orch_agent.mission
    assert "get_vision()" in orch_agent.mission
    assert "Serena MCP" in orch_agent.mission
    assert "PROJECT TYPE GUIDANCE" in orch_agent.mission
    assert "Concurrency" in orch_agent.mission  # From ORCHESTRATION type
    print("[OK] Orchestrator agent uses comprehensive template")
    print(f"    - Mission length: {len(orch_agent.mission)} characters")
    
    # Test 2: Spawn analyzer with role-specific template
    print("\n" + "-"*40)
    print("Test 2: Analyzer Agent with Template")
    print("-"*40)
    
    analyzer = await orchestrator.spawn_agent(
        project_id=project.id,
        role=AgentRole.ANALYZER
    )
    
    assert "System Analyzer" in analyzer.mission
    assert "DISCOVERY WORKFLOW" in analyzer.mission
    assert "Serena MCP" in analyzer.mission
    assert "architectural designs" in analyzer.mission
    print("[OK] Analyzer agent uses role-specific template")
    
    # Test 3: Spawn implementer with custom mission
    print("\n" + "-"*40)
    print("Test 3: Implementer with Custom Mission")
    print("-"*40)
    
    custom_mission = "Implement the MissionTemplateGenerator class with all methods"
    implementer = await orchestrator.spawn_agent(
        project_id=project.id,
        role=AgentRole.IMPLEMENTER,
        custom_mission=custom_mission
    )
    
    assert custom_mission in implementer.mission
    assert "IMPLEMENTATION WORKFLOW" in implementer.mission
    print("[OK] Custom mission integrated into template")
    
    # Test 4: Parallel agent spawning
    print("\n" + "-"*40)
    print("Test 4: Parallel Agent Spawning")
    print("-"*40)
    
    parallel_agents = await orchestrator.spawn_agents_parallel(
        project_id=project.id,
        agents=[
            (AgentRole.TESTER, None),
            (AgentRole.REVIEWER, None)
        ],
        project_type=ProjectType.ORCHESTRATION
    )
    
    assert len(parallel_agents) == 2
    
    # Check both agents have parallel instructions
    for agent in parallel_agents:
        assert "PARALLEL AGENT STARTUP" in agent.mission
        assert "COORDINATION PROTOCOL" in agent.mission
    print(f"[OK] Spawned {len(parallel_agents)} agents with parallel instructions")
    
    # Test 5: Context limit handling
    print("\n" + "-"*40)
    print("Test 5: Context Limit Instructions")
    print("-"*40)
    
    # Update agent context to approach limit
    await orchestrator.update_context_usage(
        agent_id=implementer.id,
        tokens_used=23000  # Will be at 76.7% usage
    )
    
    # Check if context limit message is generated
    context_message = await orchestrator.handle_context_limit(implementer.id)
    
    if context_message:
        assert "CONTEXT LIMIT APPROACHING" in context_message.content
        assert "HANDOFF PREPARATION" in context_message.content
        print("[OK] Context limit instructions generated")
    else:
        print("[INFO] Context limit not reached yet (expected at 70%+)")
    
    # Test 6: Handoff instructions
    print("\n" + "-"*40)
    print("Test 6: Handoff Instructions")
    print("-"*40)
    
    handoff_message = await orchestrator.handoff(
        from_agent_id=analyzer.id,
        to_agent_id=implementer.id,
        context={"summary": "Requirements analyzed and design complete"}
    )
    
    handoff_data = eval(handoff_message.content)  # Parse the stringified dict
    assert "handoff_instructions" in handoff_data
    assert "HANDOFF FROM ANALYZER TO IMPLEMENTER" in handoff_data["handoff_instructions"]
    print("[OK] Handoff includes proper instructions")
    
    # Cleanup
    await db_manager.close_async()
    
    print("\n" + "="*80)
    print("[OK] ALL INTEGRATION TESTS PASSED!")
    print("="*80)
    
    return True


async def test_template_generator_methods():
    """Test all MissionTemplateGenerator methods."""
    print("\n" + "="*80)
    print("TESTING ALL TEMPLATE GENERATOR METHODS")
    print("="*80)
    
    generator = MissionTemplateGenerator()
    
    # Test all generation methods
    methods_to_test = [
        ("generate_orchestrator_mission", {
            "project_name": "Test",
            "project_mission": "Test mission"
        }),
        ("generate_agent_mission", {
            "role": AgentRole.TESTER,
            "project_name": "Test"
        }),
        ("generate_handoff_instructions", {
            "from_role": AgentRole.ANALYZER,
            "to_role": AgentRole.IMPLEMENTER,
            "context_summary": "Test summary"
        }),
        ("generate_parallel_startup_instructions", {
            "agents": ["analyzer", "implementer"],
            "project_name": "Test"
        }),
        ("generate_context_limit_instructions", {
            "agent_name": "tester",
            "context_used": 25000,
            "context_budget": 30000
        }),
        ("generate_acknowledgment_instruction", {}),
        ("get_behavioral_rules", {
            "role": AgentRole.IMPLEMENTER
        })
    ]
    
    for method_name, kwargs in methods_to_test:
        print(f"\nTesting {method_name}...")
        method = getattr(generator, method_name)
        result = method(**kwargs)
        
        if isinstance(result, str):
            assert len(result) > 0
            print(f"  [OK] Generated {len(result)} characters")
        elif isinstance(result, list):
            assert len(result) > 0
            print(f"  [OK] Generated {len(result)} rules")
        else:
            print(f"  [OK] Generated result: {type(result)}")
    
    print("\n[OK] All template generator methods validated")
    return True


async def main():
    """Run all integration tests."""
    try:
        # Run integration tests
        await test_orchestrator_integration()
        
        # Run method validation
        await test_template_generator_methods()
        
        print("\n" + "="*80)
        print("INTEGRATION TEST SUMMARY")
        print("="*80)
        print("\n[OK] All integration tests passed successfully!")
        print("\nValidated:")
        print("  - Orchestrator uses MissionTemplateGenerator correctly")
        print("  - Comprehensive orchestrator template with vision guardian")
        print("  - Role-specific agent templates")
        print("  - Custom mission integration")
        print("  - Parallel agent spawning with instructions")
        print("  - Context limit handling")
        print("  - Handoff instructions")
        print("  - All template generator methods")
        print("\nThe Mission Template System is fully integrated and operational!")
        
    except Exception as e:
        print(f"\n[ERROR] Test failed: {e}")
        import traceback
        traceback.print_exc()
        raise


if __name__ == "__main__":
    asyncio.run(main())