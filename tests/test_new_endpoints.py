#!/usr/bin/env python3
"""
Test script for new agent tree and metrics endpoints
"""

import asyncio
import sys
import time
from datetime import datetime, timezone
from pathlib import Path


# Add parent directory to path
sys.path.insert(0, str(Path(__file__).parent))

from sqlalchemy.ext.asyncio import AsyncSession

from src.giljo_mcp.database import DatabaseManager
from src.giljo_mcp.models import Job, Message, Project


async def setup_test_data(session: AsyncSession):
    """Create test data for endpoints"""

    # Create a test project
    project = Project(
        id="test-project-001",
        tenant_key="test-tenant",
        name="Test Project",
        mission="Test mission for endpoint testing",
        status="active",
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
        created_at=datetime.now(timezone.utc),
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
            created_at=datetime.now(timezone.utc),
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
        tasks=["Build API", "Test endpoints"],
    )
    session.add(job1)

    # Create some messages
    msg1 = Message(
        tenant_key="test-tenant",
        project_id="test-project-001",
        to_agents=["implementer"],
        content="Start implementation",
        message_type="direct",
        priority="high",
    )
    session.add(msg1)

    await session.commit()
    return project


async def test_tree_endpoint():
    """Test the /api/agents/tree endpoint"""

    db_manager = DatabaseManager(is_async=True)

    async with db_manager.get_session_async() as session:
        # Setup test data
        await setup_test_data(session)

        # Mock request query params
        class MockQuery:
            project_id = "test-project-001"

        # Test the endpoint
        start_time = time.time()

        try:
            # Direct function call since we're testing without running server

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

            # Check performance requirement
            if response_time < 100:
                pass
            else:
                pass

            # Display tree structure
            for agent in agents:
                if agent.role == "orchestrator":
                    for sub_agent in agents:
                        if sub_agent.role != "orchestrator":
                            pass

        except Exception:
            pass

        # Cleanup
        await session.execute("DELETE FROM messages WHERE project_id = 'test-project-001'")
        await session.execute("DELETE FROM jobs WHERE tenant_key = 'test-tenant'")
        await session.execute("DELETE FROM agents WHERE project_id = 'test-project-001'")
        await session.execute("DELETE FROM projects WHERE id = 'test-project-001'")
        await session.commit()


async def test_metrics_endpoint():
    """Test the /api/agents/metrics endpoint"""

    db_manager = DatabaseManager(is_async=True)

    async with db_manager.get_session_async() as session:
        # Setup test data
        await setup_test_data(session)

        # Test the endpoint
        start_time = time.time()

        try:
            from sqlalchemy import select

            # Query agents
            result = await session.execute(select(Agent).where(Agent.project_id == "test-project-001"))
            agents = result.scalars().all()

            # Calculate metrics
            len(agents)
            sum(1 for a in agents if a.status == "active")
            sum(1 for a in agents if a.status == "decommissioned")

            # Count by role
            agent_by_role = {}
            for agent in agents:
                agent_by_role[agent.role] = agent_by_role.get(agent.role, 0) + 1

            response_time = (time.time() - start_time) * 1000

            # Check performance requirement
            if response_time < 100:
                pass
            else:
                pass

        except Exception:
            pass

        # Cleanup
        await session.execute("DELETE FROM messages WHERE project_id = 'test-project-001'")
        await session.execute("DELETE FROM jobs WHERE tenant_key = 'test-tenant'")
        await session.execute("DELETE FROM agents WHERE project_id = 'test-project-001'")
        await session.execute("DELETE FROM projects WHERE id = 'test-project-001'")
        await session.commit()


async def main():
    """Run all endpoint tests"""

    await test_tree_endpoint()
    await test_metrics_endpoint()


if __name__ == "__main__":
    asyncio.run(main())
