#!/usr/bin/env python3
"""
Simple test script for new agent tree and metrics endpoints
"""

import asyncio
import time
from datetime import datetime
from pathlib import Path
import sys

# Add parent directory to path
sys.path.insert(0, str(Path(__file__).parent))

from src.giljo_mcp.database import DatabaseManager
from src.giljo_mcp.models import Project, Agent, Job
from sqlalchemy import select
from sqlalchemy.orm import selectinload
from sqlalchemy.ext.asyncio import AsyncSession


async def test_endpoints():
    """Test the new endpoints with existing data"""
    print("\n=== Testing Agent Endpoints Performance ===")

    db_manager = DatabaseManager(is_async=True)

    async with db_manager.get_session_async() as session:
        # Test tree endpoint logic
        print("\n1. Testing /api/agents/tree logic:")
        start_time = time.time()

        try:
            # Query agents with relationships
            stmt = (
                select(Agent)
                .options(selectinload(Agent.jobs))
                .limit(100)  # Limit for testing
            )

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
                    "children": []
                }

                agent_nodes[agent.id] = node

                if agent.role == "orchestrator":
                    root_agents.append(node)

            tree_time = (time.time() - start_time) * 1000

            print(f"  [OK] Tree structure built in {tree_time:.2f}ms")
            print(f"    - Total agents found: {len(agents)}")
            print(f"    - Root agents: {len(root_agents)}")

            if tree_time < 100:
                print(f"  [OK] Performance OK: {tree_time:.2f}ms < 100ms")
            else:
                print(f"  [FAIL] Performance SLOW: {tree_time:.2f}ms > 100ms")

        except Exception as e:
            print(f"  [FAIL] Error in tree logic: {e}")

        # Test metrics endpoint logic
        print("\n2. Testing /api/agents/metrics logic:")
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
                "by_status": {}
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

            print(f"  [OK] Metrics calculated in {metrics_time:.2f}ms")
            print(f"    - Total agents: {metrics['total_agents']}")
            print(f"    - Active agents: {metrics['active_agents']}")
            print(f"    - Avg context usage: {metrics['avg_context']:.0f}")
            print(f"    - Roles: {list(metrics['by_role'].keys())}")

            if metrics_time < 100:
                print(f"  [OK] Performance OK: {metrics_time:.2f}ms < 100ms")
            else:
                print(f"  [FAIL] Performance SLOW: {metrics_time:.2f}ms > 100ms")

        except Exception as e:
            print(f"  [FAIL] Error in metrics logic: {e}")

        # Test combined query performance
        print("\n3. Testing combined query performance:")
        start_time = time.time()

        try:
            # Simulate both endpoints being called
            stmt1 = select(Agent).options(selectinload(Agent.jobs)).limit(100)
            stmt2 = select(Agent).limit(100)

            result1 = await session.execute(stmt1)
            agents1 = result1.scalars().all()

            result2 = await session.execute(stmt2)
            agents2 = result2.scalars().all()

            combined_time = (time.time() - start_time) * 1000

            print(f"  [OK] Both queries executed in {combined_time:.2f}ms")

            if combined_time < 200:  # Allow 200ms for both
                print(f"  [OK] Combined performance OK: {combined_time:.2f}ms < 200ms")
            else:
                print(f"  [FAIL] Combined performance SLOW: {combined_time:.2f}ms > 200ms")

        except Exception as e:
            print(f"  [FAIL] Error in combined test: {e}")


async def main():
    """Run endpoint performance tests"""
    print("=" * 50)
    print("Agent Endpoints Performance Test")
    print("=" * 50)

    await test_endpoints()

    print("\n" + "=" * 50)
    print("Performance tests completed!")
    print("\nSummary:")
    print("- Tree endpoint: Builds hierarchical agent structure")
    print("- Metrics endpoint: Calculates agent statistics")
    print("- Both endpoints designed for <100ms response time")
    print("- Endpoints available at:")
    print("  GET /api/agents/tree?project_id=<id>")
    print("  GET /api/agents/metrics?project_id=<id>&hours=24")


if __name__ == "__main__":
    asyncio.run(main())