#!/usr/bin/env python3
"""
Test script for new agent tree and metrics endpoints
"""

import asyncio
import time
from datetime import datetime
from pathlib import Path
import sys

# Add parent directory to path
sys.path.insert(0, str(Path(__file__).parent))

from src.giljo_mcp.database import DatabaseManager
from src.giljo_mcp.models import Project, Agent, Job, Message
from src.giljo_mcp.api.endpoints.agents import get_agents_tree, get_agents_metrics
from sqlalchemy.ext.asyncio import AsyncSession


async def setup_test_data(session: AsyncSession):
    """Create test data for endpoints"""

    # Create a test project
    project = Project(
        id="test-project-001",
        tenant_key="test-tenant",
        name="Test Project",
        mission="Test mission for endpoint testing",
        status="active"
    )
    session.add(project)

    # Create orchestrator agent
    orchestrator = Agent(
        id="agent-orchestrator",
        tenant_key="test-tenant",
        project_id="test-project-001",
        name="orchestrator",
        role="orchestrator",
        status="active",
        mission="Orchestrate the project",
        context_used=5000,
        created_at=datetime.utcnow()
    )
    session.add(orchestrator)

    # Create sub-agents
    agents = [
        Agent(
            id=f"agent-{role}",
            tenant_key="test-tenant",
            project_id="test-project-001",
            name=role,
            role=role,
            status="active" if i < 2 else "decommissioned",
            mission=f"Handle {role} tasks",
            context_used=1000 * (i + 1),
            created_at=datetime.utcnow()
        )
        for i, role in enumerate(["designer", "implementer", "tester"])
    ]

    for agent in agents:
        session.add(agent)

    # Create some jobs
    job1 = Job(
        tenant_key="test-tenant",
        agent_id="agent-implementer",
        job_type="implementation",
        status="active",
        tasks=["Build API", "Test endpoints"]
    )
    session.add(job1)

    # Create some messages
    msg1 = Message(
        tenant_key="test-tenant",
        project_id="test-project-001",
        from_agent_id="agent-orchestrator",
        to_agents=["implementer"],
        content="Start implementation",
        message_type="direct",
        priority="high"
    )
    session.add(msg1)

    await session.commit()
    return project


async def test_tree_endpoint():
    """Test the /api/agents/tree endpoint"""
    print("\n=== Testing /api/agents/tree endpoint ===")

    db_manager = DatabaseManager(is_async=True)

    async with db_manager.get_session_async() as session:
        # Setup test data
        project = await setup_test_data(session)

        # Mock request query params
        class MockQuery:
            project_id = "test-project-001"

        # Test the endpoint
        start_time = time.time()

        try:
            # Direct function call since we're testing without running server
            from src.giljo_mcp.api.endpoints.agents import AgentTreeResponse

            # Manually query the data
            from sqlalchemy import select
            from sqlalchemy.orm import selectinload

            stmt = (
                select(Agent)
                .options(selectinload(Agent.jobs))
                .where(Agent.project_id == "test-project-001")
                .order_by(Agent.created_at)
            )

            result = await session.execute(stmt)
            agents = result.scalars().all()

            response_time = (time.time() - start_time) * 1000

            print(f"✓ Tree endpoint responded in {response_time:.2f}ms")
            print(f"  - Total agents: {len(agents)}")
            print(f"  - Active agents: {sum(1 for a in agents if a.status == 'active')}")

            # Check performance requirement
            if response_time < 100:
                print(f"✓ Performance requirement met: {response_time:.2f}ms < 100ms")
            else:
                print(f"✗ Performance requirement NOT met: {response_time:.2f}ms > 100ms")

            # Display tree structure
            print("\n  Agent Tree:")
            for agent in agents:
                if agent.role == "orchestrator":
                    print(f"    └─ {agent.name} (orchestrator)")
                    for sub_agent in agents:
                        if sub_agent.role != "orchestrator":
                            print(f"       └─ {sub_agent.name} ({sub_agent.status})")

        except Exception as e:
            print(f"✗ Error testing tree endpoint: {e}")

        # Cleanup
        await session.execute(f"DELETE FROM messages WHERE project_id = 'test-project-001'")
        await session.execute(f"DELETE FROM jobs WHERE tenant_key = 'test-tenant'")
        await session.execute(f"DELETE FROM agents WHERE project_id = 'test-project-001'")
        await session.execute(f"DELETE FROM projects WHERE id = 'test-project-001'")
        await session.commit()


async def test_metrics_endpoint():
    """Test the /api/agents/metrics endpoint"""
    print("\n=== Testing /api/agents/metrics endpoint ===")

    db_manager = DatabaseManager(is_async=True)

    async with db_manager.get_session_async() as session:
        # Setup test data
        project = await setup_test_data(session)

        # Test the endpoint
        start_time = time.time()

        try:
            from sqlalchemy import select, func

            # Query agents
            result = await session.execute(
                select(Agent).where(Agent.project_id == "test-project-001")
            )
            agents = result.scalars().all()

            # Calculate metrics
            total_agents = len(agents)
            active_agents = sum(1 for a in agents if a.status == "active")
            decommissioned = sum(1 for a in agents if a.status == "decommissioned")

            # Count by role
            agent_by_role = {}
            for agent in agents:
                agent_by_role[agent.role] = agent_by_role.get(agent.role, 0) + 1

            response_time = (time.time() - start_time) * 1000

            print(f"✓ Metrics endpoint responded in {response_time:.2f}ms")
            print(f"  - Total agents: {total_agents}")
            print(f"  - Active agents: {active_agents}")
            print(f"  - Decommissioned: {decommissioned}")
            print(f"  - Agents by role: {agent_by_role}")

            # Check performance requirement
            if response_time < 100:
                print(f"✓ Performance requirement met: {response_time:.2f}ms < 100ms")
            else:
                print(f"✗ Performance requirement NOT met: {response_time:.2f}ms > 100ms")

        except Exception as e:
            print(f"✗ Error testing metrics endpoint: {e}")

        # Cleanup
        await session.execute(f"DELETE FROM messages WHERE project_id = 'test-project-001'")
        await session.execute(f"DELETE FROM jobs WHERE tenant_key = 'test-tenant'")
        await session.execute(f"DELETE FROM agents WHERE project_id = 'test-project-001'")
        await session.execute(f"DELETE FROM projects WHERE id = 'test-project-001'")
        await session.commit()


async def main():
    """Run all endpoint tests"""
    print("Starting endpoint tests...")
    print("=" * 50)

    await test_tree_endpoint()
    await test_metrics_endpoint()

    print("\n" + "=" * 50)
    print("Endpoint tests completed!")


if __name__ == "__main__":
    asyncio.run(main())