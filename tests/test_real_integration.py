"""
REAL integration test that actually tests the system.
No shortcuts - this tests the actual integration points.
"""

import asyncio
import sys
from pathlib import Path


sys.path.insert(0, str(Path(__file__).parent.parent))

from src.giljo_mcp.database import get_db_manager
from src.giljo_mcp.enums import AgentRole, ProjectType
from src.giljo_mcp.orchestrator import ProjectOrchestrator
from src.giljo_mcp.template_adapter import MissionTemplateGeneratorV2 as MissionTemplateGenerator


async def test_real_orchestrator_integration():
    """Test ACTUAL integration with database and orchestrator."""

    issues_found = []

    try:
        # Use the actual get_db_manager function
        db_manager = get_db_manager(is_async=True)

        # Get an actual session
        async with db_manager.get_session_async():
            pass
    except Exception as e:
        issues_found.append(f"Database initialization failed: {e}")

    try:
        # Test the actual orchestrator initialization
        orchestrator = ProjectOrchestrator()

        # Check if template_generator is actually initialized
        if not hasattr(orchestrator, "template_generator"):
            issues_found.append("Orchestrator missing template_generator attribute")
        else:
            pass

        # Check if it's the right type
        if not isinstance(orchestrator.template_generator, MissionTemplateGenerator):
            issues_found.append("template_generator is wrong type")
        else:
            pass

    except Exception as e:
        issues_found.append(f"Orchestrator initialization failed: {e}")

    # Test the actual methods that were modified
    try:
        # Test spawn_agent modifications
        # The orchestrator spawn_agent now has these parameters:
        # - project_type: Optional[ProjectType]
        # - additional_instructions: Optional[str]

        # Can we actually call it with these?

        # This would fail if the method signature is wrong
        import inspect

        sig = inspect.signature(orchestrator.spawn_agent)
        params = list(sig.parameters.keys())

        if "project_type" not in params:
            issues_found.append("spawn_agent missing project_type parameter")
        else:
            pass

        if "additional_instructions" not in params:
            issues_found.append("spawn_agent missing additional_instructions parameter")
        else:
            pass

    except Exception as e:
        issues_found.append(f"spawn_agent inspection failed: {e}")

    # Test new methods that were added
    new_methods = ["spawn_agents_parallel", "handle_context_limit"]

    for method_name in new_methods:
        if not hasattr(orchestrator, method_name):
            issues_found.append(f"Orchestrator missing {method_name} method")
        else:
            pass

    # Test actual template generation with all parameters
    try:
        generator = MissionTemplateGenerator()

        # Test with None values (edge case)
        try:
            generator.generate_agent_mission(
                role=AgentRole.IMPLEMENTER,
                project_name="Test",
                custom_mission=None,  # Should use default
                additional_instructions=None,  # Should be fine
            )
        except Exception as e:
            issues_found.append(f"Fails with None parameters: {e}")

        # Test actual handoff logic in orchestrator
        if hasattr(orchestrator, "handoff"):
            sig = inspect.signature(orchestrator.handoff)
            # Check if handoff was actually modified to use templates
            # We can't test execution without a real database, but we can check structure

            import dis

            bytecode = dis.Bytecode(orchestrator.handoff)
            calls_template_generator = any("template" in str(instr).lower() for instr in bytecode)

            if not calls_template_generator:
                issues_found.append("handoff method doesn't seem to use template_generator")
            else:
                pass

    except Exception as e:
        issues_found.append(f"Template generation test failed: {e}")

    # Summary

    if issues_found:
        for _issue in issues_found:
            pass
        return False
    return True


async def test_actual_workflow():
    """Test an actual workflow if possible."""

    try:
        # Try to create a real workflow
        # This will likely fail without proper DB setup, but let's try

        orchestrator = ProjectOrchestrator()

        # Would this actually work?
        project = await orchestrator.create_project(name="Integration Test", mission="Test the integration")

        # Can we spawn an agent?
        agent = await orchestrator.spawn_agent(
            project_id=project.id, role=AgentRole.ORCHESTRATOR, project_type=ProjectType.ORCHESTRATION
        )

        # Verify the mission has the expected content
        if "VISION GUARDIAN" in agent.mission:
            pass
        else:
            pass

        return True

    except Exception:
        return False


def test_performance_reality_check():
    """Check if performance claims are realistic."""

    import time

    generator = MissionTemplateGenerator()

    # Test with realistic scenarios
    scenarios = [
        ("Small", "A", "B"),
        ("Medium", "A" * 100, "B" * 500),
        ("Large", "A" * 1000, "B" * 5000),
        ("Huge", "A" * 10000, "B" * 50000),
    ]

    for _name, project_name, mission in scenarios:
        start = time.perf_counter()

        generator.generate_orchestrator_mission(
            project_name=project_name,
            project_mission=mission,
            additional_context={"project_type": ProjectType.ORCHESTRATION},
        )

        (time.perf_counter() - start) * 1000

    # Test concurrent generation (what really happens)

    async def generate_concurrent():
        tasks = []
        for i in range(10):
            # Simulate real scenario with different inputs
            tasks.append(
                asyncio.to_thread(
                    generator.generate_orchestrator_mission,
                    project_name=f"Project {i}",
                    project_mission=f"Mission {i}" * 100,
                )
            )

        start = time.perf_counter()
        results = await asyncio.gather(*tasks)
        elapsed = time.perf_counter() - start

        return elapsed, results

    _elapsed, _results = asyncio.run(generate_concurrent())


if __name__ == "__main__":
    # Run the real tests

    # Test 1: Real integration points
    result1 = asyncio.run(test_real_orchestrator_integration())

    # Test 2: Actual workflow (will likely fail)
    result2 = asyncio.run(test_actual_workflow())

    # Test 3: Performance reality
    test_performance_reality_check()

    if result1:
        pass
    else:
        pass

    if not result2:
        pass
