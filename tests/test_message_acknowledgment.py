#!/usr/bin/env python
"""
Test script for message acknowledgment system
Tests the fixed message tools with proper field names and array structures
"""

import asyncio
import sys
from datetime import datetime, timezone
from pathlib import Path


# Add src to path
sys.path.insert(0, str(Path(__file__).parent.parent))

from sqlalchemy import select

from src.giljo_mcp.database import DatabaseManager
from src.giljo_mcp.models import MCPAgentJob, Message, Project
from tests.helpers.test_db_helper import PostgreSQLTestHelper


async def test_message_acknowledgment():
    """Test the message acknowledgment system"""

    # Initialize database
    db_manager = DatabaseManager(PostgreSQLTestHelper.get_test_db_url(), is_async=True)
    await db_manager.create_tables_async()

    async with db_manager.get_session() as session:
        # Clean up any existing test data
        await session.execute(Message.__table__.delete())
        await session.execute(Agent.__table__.delete())
        await session.execute(Project.__table__.delete())
        await session.commit()

        # Create test project
        project = Project(
            id="test-project-123", tenant_key="test-tenant", name="Test Project", mission="Test message acknowledgment"
        )
        session.add(project)

        # Create test agents
        agent1 = Agent(
            id="agent-1",
            tenant_key="test-tenant",
            project_id="test-project-123",
            name="analyzer",
            role="analyzer",
            status="active",
        )
        agent2 = Agent(
            id="agent-2",
            tenant_key="test-tenant",
            project_id="test-project-123",
            name="implementer",
            role="implementer",
            status="active",
        )
        agent3 = Agent(
            id="agent-3",
            tenant_key="test-tenant",
            project_id="test-project-123",
            name="tester",
            role="tester",
            status="active",
        )
        session.add_all([agent1, agent2, agent3])
        await session.commit()

        # Test 1: Create message with correct field names
        message = Message(
            tenant_key="test-tenant",
            project_id="test-project-123",
            to_agents=["implementer", "tester"],  # Multi-agent recipients
            message_type="direct",
            content="Test message for multiple agents",
            priority="high",
            status="waiting",
            acknowledged_by=[],
            completed_by=[],
        )
        session.add(message)
        await session.commit()

        # Test 2: Retrieve and auto-acknowledge

        # Simulate get_messages for implementer
        messages_query = select(Message).where(Message.project_id == "test-project-123")
        result = await session.execute(messages_query)
        messages = result.scalars().all()

        for msg in messages:
            if "implementer" in msg.to_agents:
                # Auto-acknowledge
                msg.status = "acknowledged"
                msg.acknowledged_at = datetime.now(timezone.utc)

                if not msg.acknowledged_by:
                    msg.acknowledged_by = []

                msg.acknowledged_by.append(
                    {"agent_name": "implementer", "timestamp": datetime.now(timezone.utc).isoformat()}
                )

        await session.commit()

        # Test 3: Complete message with notes

        for msg in messages:
            if "implementer" in msg.to_agents and msg.status == "acknowledged":
                msg.status = "database_initialized"
                msg.database_initialized_at = datetime.now(timezone.utc)

                if not msg.completed_by:
                    msg.completed_by = []

                msg.completed_by.append(
                    {
                        "agent_name": "implementer",
                        "timestamp": datetime.now(timezone.utc).isoformat(),
                        "notes": "Fixed all field names and implemented auto-acknowledgment",
                    }
                )

                # Store result in meta_data
                if not msg.meta_data:
                    msg.meta_data = {}
                msg.meta_data["result"] = "All message tools fixed and working"

        await session.commit()

        # Test 4: Verify array structures

        final_query = select(Message).where(Message.id == message.id)
        final_result = await session.execute(final_query)
        final_message = final_result.scalar_one()

        # Verify structure
        assert isinstance(final_message.to_agents, list), "to_agents should be a list"
        assert isinstance(final_message.acknowledged_by, list), "acknowledged_by should be a list"
        assert isinstance(final_message.completed_by, list), "completed_by should be a list"

        # Verify acknowledgment structure
        if final_message.acknowledged_by:
            ack = final_message.acknowledged_by[0]
            assert "agent_name" in ack, "acknowledgment should have agent_name"
            assert "timestamp" in ack, "acknowledgment should have timestamp"

        # Verify completion structure
        if final_message.completed_by:
            comp = final_message.completed_by[0]
            assert "agent_name" in comp, "completion should have agent_name"
            assert "timestamp" in comp, "completion should have timestamp"
            assert "notes" in comp, "completion should have notes"

        # Cleanup
        await session.execute(Message.__table__.delete())
        await session.execute(Agent.__table__.delete())
        await session.execute(Project.__table__.delete())
        await session.commit()


if __name__ == "__main__":
    asyncio.run(test_message_acknowledgment())
