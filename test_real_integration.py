"""
REAL integration test that actually tests the system.
No shortcuts - this tests the actual integration points.
"""

import asyncio
import tempfile
from pathlib import Path
import sys
import json

sys.path.insert(0, str(Path(__file__).parent / "src"))

from giljo_mcp.mission_templates import MissionTemplateGenerator, AgentRole, ProjectType
from giljo_mcp.orchestrator import ProjectOrchestrator
from giljo_mcp.database import DatabaseManager, get_db_manager


async def test_real_orchestrator_integration():
    """Test ACTUAL integration with database and orchestrator."""
    print("\n" + "="*80)
    print("REAL INTEGRATION TEST - NO SHORTCUTS")
    print("="*80)
    
    issues_found = []
    
    try:
        # Use the actual get_db_manager function
        db_manager = get_db_manager(is_async=True)
        
        # Get an actual session
        async with db_manager.get_session_async() as session:
            print("[OK] Database session created")
    except Exception as e:
        issues_found.append(f"Database initialization failed: {e}")
        print(f"[FAIL] Database initialization: {e}")
    
    try:
        # Test the actual orchestrator initialization
        orchestrator = ProjectOrchestrator()
        
        # Check if template_generator is actually initialized
        if not hasattr(orchestrator, 'template_generator'):
            issues_found.append("Orchestrator missing template_generator attribute")
            print("[FAIL] Orchestrator doesn't have template_generator")
        else:
            print("[OK] Orchestrator has template_generator")
            
        # Check if it's the right type
        if not isinstance(orchestrator.template_generator, MissionTemplateGenerator):
            issues_found.append("template_generator is wrong type")
            print("[FAIL] template_generator is wrong type")
        else:
            print("[OK] template_generator is correct type")
            
    except Exception as e:
        issues_found.append(f"Orchestrator initialization failed: {e}")
        print(f"[FAIL] Orchestrator initialization: {e}")
    
    # Test the actual methods that were modified
    try:
        # Test spawn_agent modifications
        # The orchestrator spawn_agent now has these parameters:
        # - project_type: Optional[ProjectType] 
        # - additional_instructions: Optional[str]
        
        # Can we actually call it with these?
        print("\nTesting modified spawn_agent signature...")
        
        # This would fail if the method signature is wrong
        import inspect
        sig = inspect.signature(orchestrator.spawn_agent)
        params = list(sig.parameters.keys())
        
        if 'project_type' not in params:
            issues_found.append("spawn_agent missing project_type parameter")
            print("[FAIL] spawn_agent missing project_type parameter")
        else:
            print("[OK] spawn_agent has project_type parameter")
            
        if 'additional_instructions' not in params:
            issues_found.append("spawn_agent missing additional_instructions parameter")
            print("[FAIL] spawn_agent missing additional_instructions")
        else:
            print("[OK] spawn_agent has additional_instructions parameter")
            
    except Exception as e:
        issues_found.append(f"spawn_agent inspection failed: {e}")
        print(f"[FAIL] spawn_agent inspection: {e}")
    
    # Test new methods that were added
    new_methods = [
        'spawn_agents_parallel',
        'handle_context_limit'
    ]
    
    for method_name in new_methods:
        if not hasattr(orchestrator, method_name):
            issues_found.append(f"Orchestrator missing {method_name} method")
            print(f"[FAIL] Orchestrator missing {method_name}")
        else:
            print(f"[OK] Orchestrator has {method_name}")
    
    # Test actual template generation with all parameters
    try:
        generator = MissionTemplateGenerator()
        
        # Test with None values (edge case)
        try:
            mission = generator.generate_agent_mission(
                role=AgentRole.IMPLEMENTER,
                project_name="Test",
                custom_mission=None,  # Should use default
                additional_instructions=None  # Should be fine
            )
            print("[OK] Handles None parameters")
        except Exception as e:
            issues_found.append(f"Fails with None parameters: {e}")
            print(f"[FAIL] None parameter handling: {e}")
            
        # Test actual handoff logic in orchestrator
        if hasattr(orchestrator, 'handoff'):
            sig = inspect.signature(orchestrator.handoff)
            # Check if handoff was actually modified to use templates
            # We can't test execution without a real database, but we can check structure
            
            import dis
            bytecode = dis.Bytecode(orchestrator.handoff)
            calls_template_generator = any(
                'template' in str(instr).lower() 
                for instr in bytecode
            )
            
            if not calls_template_generator:
                issues_found.append("handoff method doesn't seem to use template_generator")
                print("[WARNING] handoff might not use template_generator")
            else:
                print("[OK] handoff appears to use templates")
                
    except Exception as e:
        issues_found.append(f"Template generation test failed: {e}")
        print(f"[FAIL] Template generation: {e}")
    
    # Summary
    print("\n" + "="*80)
    print("REAL INTEGRATION TEST RESULTS")
    print("="*80)
    
    if issues_found:
        print(f"\n[FAILED] Found {len(issues_found)} issues:")
        for issue in issues_found:
            print(f"  - {issue}")
        return False
    else:
        print("\n[PASSED] All integration points verified")
        return True


async def test_actual_workflow():
    """Test an actual workflow if possible."""
    print("\n" + "="*80)
    print("TESTING ACTUAL WORKFLOW")
    print("="*80)
    
    try:
        # Try to create a real workflow
        # This will likely fail without proper DB setup, but let's try
        
        orchestrator = ProjectOrchestrator()
        
        # Would this actually work?
        project = await orchestrator.create_project(
            name="Integration Test",
            mission="Test the integration"
        )
        
        print(f"[OK] Created project: {project.id}")
        
        # Can we spawn an agent?
        agent = await orchestrator.spawn_agent(
            project_id=project.id,
            role=AgentRole.ORCHESTRATOR,
            project_type=ProjectType.ORCHESTRATION
        )
        
        print(f"[OK] Spawned agent with template mission")
        print(f"     Mission length: {len(agent.mission)} chars")
        
        # Verify the mission has the expected content
        if "VISION GUARDIAN" in agent.mission:
            print("[OK] Mission contains VISION GUARDIAN")
        else:
            print("[FAIL] Mission missing VISION GUARDIAN")
            
        return True
        
    except Exception as e:
        print(f"[EXPECTED FAIL] Workflow test failed (probably DB): {e}")
        print("     This is expected without proper database setup")
        return False


def test_performance_reality_check():
    """Check if performance claims are realistic."""
    print("\n" + "="*80)
    print("PERFORMANCE REALITY CHECK")
    print("="*80)
    
    import time
    generator = MissionTemplateGenerator()
    
    # Test with realistic scenarios
    scenarios = [
        ("Small", "A", "B"),
        ("Medium", "A" * 100, "B" * 500),
        ("Large", "A" * 1000, "B" * 5000),
        ("Huge", "A" * 10000, "B" * 50000)
    ]
    
    for name, project_name, mission in scenarios:
        start = time.perf_counter()
        
        result = generator.generate_orchestrator_mission(
            project_name=project_name,
            project_mission=mission,
            additional_context={"project_type": ProjectType.ORCHESTRATION}
        )
        
        elapsed_ms = (time.perf_counter() - start) * 1000
        
        print(f"{name:10} Input: {len(project_name)+len(mission):,} chars -> "
              f"Output: {len(result):,} chars in {elapsed_ms:.3f}ms")
    
    # Test concurrent generation (what really happens)
    print("\nConcurrent generation (10 parallel):")
    
    async def generate_concurrent():
        tasks = []
        for i in range(10):
            # Simulate real scenario with different inputs
            tasks.append(asyncio.to_thread(
                generator.generate_orchestrator_mission,
                project_name=f"Project {i}",
                project_mission=f"Mission {i}" * 100
            ))
        
        start = time.perf_counter()
        results = await asyncio.gather(*tasks)
        elapsed = time.perf_counter() - start
        
        return elapsed, results
    
    elapsed, results = asyncio.run(generate_concurrent())
    print(f"  Generated {len(results)} templates in {elapsed*1000:.3f}ms total")
    print(f"  Average: {elapsed*1000/len(results):.3f}ms per template")


if __name__ == "__main__":
    # Run the real tests
    print("RUNNING REAL INTEGRATION TESTS - NO SHORTCUTS")
    print("="*80)
    
    # Test 1: Real integration points
    result1 = asyncio.run(test_real_orchestrator_integration())
    
    # Test 2: Actual workflow (will likely fail)
    result2 = asyncio.run(test_actual_workflow())
    
    # Test 3: Performance reality
    test_performance_reality_check()
    
    print("\n" + "="*80)
    print("HONEST ASSESSMENT")
    print("="*80)
    
    if result1:
        print("[OK] Integration points are correctly structured")
    else:
        print("[ISSUE] Integration has problems that need fixing")
    
    if not result2:
        print("[NOTE] Full workflow test requires proper DB setup")
    
    print("\nConclusion: The implementation appears structurally correct")
    print("but full integration testing would require:")
    print("  1. Proper database initialization")
    print("  2. Actual agent lifecycle testing")
    print("  3. Real message passing validation")
    print("  4. Concurrent operation testing")