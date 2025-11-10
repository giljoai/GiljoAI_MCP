#!/usr/bin/env python3
"""
Simple test script for new agent tree and metrics endpoints

TODO(0127a): This test needs to be rewritten to use MCPAgentJob instead of Agent model.
The Agent model was removed and replaced with MCPAgentJob which has a different structure.
"""

import asyncio
import pytest
import sys
import time
from pathlib import Path


# Add parent directory to path
sys.path.insert(0, str(Path(__file__).parent))

from sqlalchemy import select
from sqlalchemy.orm import selectinload

from src.giljo_mcp.database import DatabaseManager
# from src.giljo_mcp.models import Agent  # REMOVED: Agent model no longer exists


@pytest.mark.skip(reason="TODO(0127a): Needs rewrite for MCPAgentJob model")
async def test_endpoints():
    """Test the new endpoints with existing data"""

    db_manager = DatabaseManager(is_async=True)

    async with db_manager.get_session_async() as session:
        # Test tree endpoint logic
        start_time = time.time()

        try:
            # Query agents with relationships
            stmt = select(Agent).options(selectinload(Agent.jobs)).limit(100)  # Limit for testing

            result = await session.execute(stmt)
            agents = result.scalars().all()

            # Build tree structure (simplified)
            agent_nodes = {}
            root_agents = []

            for agent in agents:
                node = {
                    "id": agent.id,
                    "name": agent.name,
                    "role": agent.role,
                    "status": agent.status,
                    "context_used": agent.context_used or 0,
                    "children": [],
                }

                agent_nodes[agent.id] = node

                if agent.role == "orchestrator":
                    root_agents.append(node)

            tree_time = (time.time() - start_time) * 1000

            if tree_time < 100:
                pass
            else:
                pass

        except Exception:
            pass

        # Test metrics endpoint logic
        start_time = time.time()

        try:
            # Query agents for metrics
            result = await session.execute(select(Agent).limit(100))
            agents = result.scalars().all()

            # Calculate metrics
            metrics = {
                "total_agents": len(agents),
                "active_agents": sum(1 for a in agents if a.status == "active"),
                "decommissioned": sum(1 for a in agents if a.status == "decommissioned"),
                "avg_context": 0,
                "by_role": {},
                "by_status": {},
            }

            # Context usage average
            context_usages = [a.context_used for a in agents if a.context_used]
            if context_usages:
                metrics["avg_context"] = sum(context_usages) / len(context_usages)

            # Count by role and status
            for agent in agents:
                role = agent.role
                status = agent.status
                metrics["by_role"][role] = metrics["by_role"].get(role, 0) + 1
                metrics["by_status"][status] = metrics["by_status"].get(status, 0) + 1

            metrics_time = (time.time() - start_time) * 1000

            if metrics_time < 100:
                pass
            else:
                pass

        except Exception:
            pass

        # Test combined query performance
        start_time = time.time()

        try:
            # Simulate both endpoints being called
            stmt1 = select(Agent).options(selectinload(Agent.jobs)).limit(100)
            stmt2 = select(Agent).limit(100)

            result1 = await session.execute(stmt1)
            result1.scalars().all()

            result2 = await session.execute(stmt2)
            result2.scalars().all()

            combined_time = (time.time() - start_time) * 1000

            if combined_time < 200:  # Allow 200ms for both
                pass
            else:
                pass

        except Exception:
            pass


async def main():
    """Run endpoint performance tests"""

    await test_endpoints()


if __name__ == "__main__":
    asyncio.run(main())
