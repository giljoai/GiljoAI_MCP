"""
Test script for the Mission Template Generator system.

Tests comprehensive mission generation for orchestrator and agents.
"""

import asyncio
from pathlib import Path
import sys

# Add src to path
sys.path.insert(0, str(Path(__file__).parent.parent.parent))

from src.giljo_mcp.template_manager import UnifiedTemplateManager
# Note: mission_templates.py was deleted and unified into template_manager.py


def test_orchestrator_template():
    """Test orchestrator mission generation."""
    print("\n" + "="*80)
    print("TESTING ORCHESTRATOR TEMPLATE")
    print("="*80)
    
    generator = MissionTemplateGenerator()
    
    # Test basic orchestrator mission
    mission = generator.generate_orchestrator_mission(
        project_name="3.4 GiljoAI Mission Templates",
        project_mission="Implement comprehensive mission templates with vision guardian and scope sheriff roles",
        product_name="GiljoAI-MCP Coding Orchestrator"
    )
    
    print("\nBasic Orchestrator Mission:")
    print("-" * 40)
    print(mission[:500] + "...")  # Print first 500 chars
    
    # Verify key components are present
    assert "VISION GUARDIAN" in mission
    assert "SCOPE SHERIFF" in mission
    assert "get_vision()" in mission
    assert "chunked" in mission
    assert "Serena MCP" in mission
    print("\n[OK] All key components present in orchestrator template")
    
    # Test with project type customization
    mission_with_type = generator.generate_orchestrator_mission(
        project_name="Test Project",
        project_mission="Test mission",
        additional_context={"project_type": ProjectType.ORCHESTRATION}
    )
    
    assert "PROJECT TYPE GUIDANCE" in mission_with_type
    assert "Concurrency" in mission_with_type
    print("[OK] Project type customization working")


def test_agent_templates():
    """Test role-specific agent templates."""
    print("\n" + "="*80)
    print("TESTING AGENT TEMPLATES")
    print("="*80)
    
    generator = MissionTemplateGenerator()
    
    roles_to_test = [
        AgentRole.ANALYZER,
        AgentRole.IMPLEMENTER,
        AgentRole.TESTER,
        AgentRole.REVIEWER
    ]
    
    for role in roles_to_test:
        print(f"\n{role.value.upper()} Template:")
        print("-" * 40)
        
        mission = generator.generate_agent_mission(
            role=role,
            project_name="Test Project"
        )
        
        # Print sample
        print(mission[:400] + "...")
        
        # Verify behavioral rules
        assert "Acknowledge all messages immediately" in mission
        assert "BEHAVIORAL RULES" in mission
        assert "SUCCESS CRITERIA" in mission
        
        print(f"[OK] {role.value} template validated")


def test_custom_mission():
    """Test custom mission override."""
    print("\n" + "="*80)
    print("TESTING CUSTOM MISSION")
    print("="*80)
    
    generator = MissionTemplateGenerator()
    
    custom_mission = "Special custom mission for testing edge cases"
    mission = generator.generate_agent_mission(
        role=AgentRole.IMPLEMENTER,
        project_name="Test Project",
        custom_mission=custom_mission
    )
    
    assert custom_mission in mission
    print("[OK] Custom mission override working")


def test_handoff_instructions():
    """Test handoff instruction generation."""
    print("\n" + "="*80)
    print("TESTING HANDOFF INSTRUCTIONS")
    print("="*80)
    
    generator = MissionTemplateGenerator()
    
    instructions = generator.generate_handoff_instructions(
        from_role=AgentRole.ANALYZER,
        to_role=AgentRole.IMPLEMENTER,
        context_summary="Requirements analyzed, architecture designed, specifications complete"
    )
    
    print("\nHandoff Instructions:")
    print("-" * 40)
    print(instructions[:400] + "...")
    
    assert "HANDOFF FROM ANALYZER TO IMPLEMENTER" in instructions
    assert "Acknowledge receipt" in instructions
    assert "CONTINUITY REQUIREMENTS" in instructions
    print("[OK] Handoff instructions validated")


def test_parallel_startup():
    """Test parallel agent startup instructions."""
    print("\n" + "="*80)
    print("TESTING PARALLEL STARTUP")
    print("="*80)
    
    generator = MissionTemplateGenerator()
    
    agents = ["analyzer", "implementer", "tester"]
    instructions = generator.generate_parallel_startup_instructions(
        agents=agents,
        project_name="Test Project"
    )
    
    print("\nParallel Startup Instructions:")
    print("-" * 40)
    print(instructions[:400] + "...")
    
    assert "PARALLEL AGENT STARTUP" in instructions
    assert "analyzer" in instructions
    assert "SYNCHRONIZATION" in instructions
    print("[OK] Parallel startup instructions validated")


def test_context_limit_instructions():
    """Test context limit handling instructions."""
    print("\n" + "="*80)
    print("TESTING CONTEXT LIMIT INSTRUCTIONS")
    print("="*80)
    
    generator = MissionTemplateGenerator()
    
    instructions = generator.generate_context_limit_instructions(
        agent_name="implementer",
        context_used=24000,
        context_budget=30000
    )
    
    print("\nContext Limit Instructions:")
    print("-" * 40)
    print(instructions[:400] + "...")
    
    assert "CONTEXT LIMIT APPROACHING" in instructions
    assert "80.0%" in instructions
    assert "HANDOFF PREPARATION" in instructions
    print("[OK] Context limit instructions validated")


def test_behavioral_rules():
    """Test behavioral rules extraction."""
    print("\n" + "="*80)
    print("TESTING BEHAVIORAL RULES")
    print("="*80)
    
    generator = MissionTemplateGenerator()
    
    for role in [AgentRole.ANALYZER, AgentRole.IMPLEMENTER]:
        rules = generator.get_behavioral_rules(role)
        
        print(f"\n{role.value} Rules:")
        for rule in rules[:3]:  # Show first 3 rules
            print(f"  - {rule}")
        
        assert len(rules) > 5  # Should have common + specific rules
        assert "Acknowledge all messages immediately upon reading" in rules
    
    print("\n[OK] Behavioral rules extraction working")


def test_acknowledgment_instruction():
    """Test acknowledgment instruction generation."""
    print("\n" + "="*80)
    print("TESTING ACKNOWLEDGMENT INSTRUCTION")
    print("="*80)
    
    generator = MissionTemplateGenerator()
    instruction = generator.generate_acknowledgment_instruction()
    
    print("\nAcknowledgment Instruction:")
    print("-" * 40)
    print(instruction)
    
    assert "MESSAGE ACKNOWLEDGMENT PROTOCOL" in instruction
    assert "acknowledge_message()" in instruction
    print("\n[OK] Acknowledgment instruction validated")


def main():
    """Run all tests."""
    print("\n" + "="*80)
    print("MISSION TEMPLATE SYSTEM TESTS")
    print("="*80)
    
    try:
        test_orchestrator_template()
        test_agent_templates()
        test_custom_mission()
        test_handoff_instructions()
        test_parallel_startup()
        test_context_limit_instructions()
        test_behavioral_rules()
        test_acknowledgment_instruction()
        
        print("\n" + "="*80)
        print("[OK] ALL TESTS PASSED SUCCESSFULLY!")
        print("="*80)
        print("\nThe Mission Template System is ready for use.")
        print("Key features validated:")
        print("  - Comprehensive orchestrator template with vision guardian")
        print("  - Role-specific agent templates with behavioral rules")
        print("  - Dynamic template generation with variable substitution")
        print("  - Handoff and parallel execution instructions")
        print("  - Context limit handling")
        print("  - Message acknowledgment protocols")
        
    except AssertionError as e:
        print(f"\n[ERROR] Test failed: {e}")
        raise
    except Exception as e:
        print(f"\n[ERROR] Unexpected error: {e}")
        raise


if __name__ == "__main__":
    main()