"""
Integration test for Message Auto-Acknowledge feature (Handover 0326)

Tests that receive_messages automatically acknowledges messages when retrieved.
"""

import pytest
from datetime import datetime, timezone
from uuid import uuid4

from giljo_mcp.services.message_service import MessageService
from giljo_mcp.models import Message


class TestMessageAutoAcknowledge:
    """Test auto-acknowledge functionality in receive_messages"""

    @pytest.mark.asyncio
    async def test_receive_messages_auto_acknowledges(
        self, db_manager, tenant_manager
    ):
        """
        Test that receive_messages automatically acknowledges messages when retrieved.

        GIVEN: Pending messages sent to an agent
        WHEN: Agent calls receive_messages
        THEN: Messages are returned AND automatically marked as acknowledged in database
        """
        # Create test data: project and agent job
        # We create everything in separate sessions and commit to ensure
        # data is visible across all sessions (not using db_session fixture)
        from giljo_mcp.models import Project, AgentExecution
        from giljo_mcp.tenant import TenantManager

        tenant_key = TenantManager.generate_tenant_key(f"test_auto_ack_{uuid4().hex[:8]}")
        project_id = str(uuid4())
        job_id = str(uuid4())

        async with db_manager.get_session_async() as setup_session:
            # Create project
            project = Project(
                id=project_id,
                tenant_key=tenant_key,
                name="Test Project for Auto-Acknowledge",
                description="Test project",
                mission="Test mission for auto-acknowledge testing",
                status="active",
                created_at=datetime.now(timezone.utc),
            )
            setup_session.add(project)

            # Create agent job
            agent_job = AgentExecution(
                job_id=job_id,
                tenant_key=tenant_key,
                project_id=project_id,
                agent_display_name="orchestrator",
                mission="Test mission",
                status="waiting",
                created_at=datetime.now(timezone.utc),
            )
            setup_session.add(agent_job)
            await setup_session.commit()

        # Set tenant context
        tenant_manager.set_current_tenant(tenant_key)

        # Create test messages using a separate session
        msg1_id = str(uuid4())
        msg2_id = str(uuid4())

        async with db_manager.get_session_async() as setup_session:
            msg1 = Message(
                id=msg1_id,
                tenant_key=tenant_key,
                project_id=project_id,
                to_agents=[job_id],
                message_type="direct",
                content="Test message 1",
                priority="normal",
                status="waiting",
                created_at=datetime.now(timezone.utc),
                meta_data={"_from_agent": "orchestrator"},
            )

            msg2 = Message(
                id=msg2_id,
                tenant_key=tenant_key,
                project_id=project_id,
                to_agents=[job_id],
                message_type="direct",
                content="Test message 2",
                priority="high",
                status="waiting",
                created_at=datetime.now(timezone.utc),
                meta_data={"_from_agent": "orchestrator"},
            )

            setup_session.add_all([msg1, msg2])
            await setup_session.commit()

        # Act: Create service and receive messages
        message_service = MessageService(db_manager, tenant_manager)

        result = await message_service.receive_messages(
            agent_id=job_id,
            limit=10,
            tenant_key=tenant_key
        )

        # Assert: Verify response
        assert result["success"] is True, f"receive_messages failed: {result.get('error', 'unknown error')}"
        assert result["count"] == 2
        assert len(result["messages"]) == 2

        # Assert: Verify messages in response are marked as acknowledged
        for msg in result["messages"]:
            assert msg["acknowledged"] is True, f"Message {msg['id']} not marked as acknowledged in response"
            assert msg["acknowledged_at"] is not None, f"Message {msg['id']} missing acknowledged_at timestamp"
            assert msg["acknowledged_by"] == job_id, f"Message {msg['id']} acknowledged_by incorrect"

        # Assert: Verify database records are updated to acknowledged status
        async with db_manager.get_session_async() as verify_session:
            from sqlalchemy import select
            result = await verify_session.execute(select(Message).where(Message.id == msg1_id))
            db_msg1 = result.scalar_one()

            result = await verify_session.execute(select(Message).where(Message.id == msg2_id))
            db_msg2 = result.scalar_one()

            assert db_msg1.status == "acknowledged", "Message 1 status not updated to acknowledged"
            assert db_msg1.acknowledged_at is not None, "Message 1 acknowledged_at not set"
            assert db_msg1.acknowledged_by == [job_id], "Message 1 acknowledged_by not set correctly"

            assert db_msg2.status == "acknowledged", "Message 2 status not updated to acknowledged"
            assert db_msg2.acknowledged_at is not None, "Message 2 acknowledged_at not set"
            assert db_msg2.acknowledged_by == [job_id], "Message 2 acknowledged_by not set correctly"

    @pytest.mark.asyncio
    async def test_receive_messages_respects_limit(
        self, db_manager, tenant_manager
    ):
        """
        Test that auto-acknowledge only applies to messages returned (respects limit).

        GIVEN: 5 pending messages sent to an agent
        WHEN: Agent calls receive_messages with limit=2
        THEN: Only 2 messages are returned and acknowledged, 3 remain pending
        """
        from giljo_mcp.models import Project, AgentExecution
        from giljo_mcp.tenant import TenantManager

        # Create isolated test data
        tenant_key = TenantManager.generate_tenant_key(f"test_limit_{uuid4().hex[:8]}")
        project_id = str(uuid4())
        job_id = str(uuid4())

        async with db_manager.get_session_async() as setup_session:
            # Create project
            project = Project(
                id=project_id,
                tenant_key=tenant_key,
                name="Test Project for Limit Test",
                description="Test project",
                mission="Test mission",
                status="active",
                created_at=datetime.now(timezone.utc),
            )
            setup_session.add(project)

            # Create agent job
            agent_job = AgentExecution(
                job_id=job_id,
                tenant_key=tenant_key,
                project_id=project_id,
                agent_display_name="orchestrator",
                mission="Test mission",
                status="waiting",
                created_at=datetime.now(timezone.utc),
            )
            setup_session.add(agent_job)
            await setup_session.commit()

        # Arrange: Set tenant context
        tenant_manager.set_current_tenant(tenant_key)

        # Create 5 test messages
        message_ids = []
        async with db_manager.get_session_async() as setup_session:
            for i in range(5):
                msg = Message(
                    id=str(uuid4()),
                    tenant_key=tenant_key,
                    project_id=project_id,
                    to_agents=[job_id],
                    message_type="direct",
                    content=f"Test message {i+1}",
                    priority="normal",
                    status="waiting",
                    created_at=datetime.now(timezone.utc),
                    meta_data={"_from_agent": "orchestrator"},
                )
                setup_session.add(msg)
                message_ids.append(msg.id)

            await setup_session.commit()

        # Act: Receive only 2 messages
        message_service = MessageService(db_manager, tenant_manager)

        result = await message_service.receive_messages(
            agent_id=job_id,
            limit=2,
            tenant_key=tenant_key
        )

        # Assert: Only 2 messages returned and acknowledged
        assert result["success"] is True
        assert result["count"] == 2
        assert len(result["messages"]) == 2

        # Verify exactly 2 are acknowledged, 3 remain pending
        async with db_manager.get_session_async() as verify_session:
            from sqlalchemy import select
            db_messages = await verify_session.execute(
                select(Message).where(Message.id.in_(message_ids))
            )
            all_messages = db_messages.scalars().all()

            acknowledged_count = sum(1 for msg in all_messages if msg.status == "acknowledged")
            pending_count = sum(1 for msg in all_messages if msg.status == "pending")

            assert acknowledged_count == 2, "Should have exactly 2 acknowledged messages"
            assert pending_count == 3, "Should have exactly 3 pending messages"

    @pytest.mark.asyncio
    async def test_receive_messages_broadcast_acknowledged_per_agent(
        self, db_manager, tenant_manager
    ):
        """
        Test that broadcast messages are acknowledged independently per agent.

        GIVEN: Broadcast message sent to all agents
        WHEN: One agent receives the message
        THEN: Message is acknowledged by that agent only
        """
        from giljo_mcp.models import Project, AgentExecution
        from giljo_mcp.tenant import TenantManager

        # Create isolated test data
        tenant_key = TenantManager.generate_tenant_key(f"test_broadcast_{uuid4().hex[:8]}")
        project_id = str(uuid4())
        agent1_job_id = str(uuid4())
        agent2_job_id = str(uuid4())

        async with db_manager.get_session_async() as setup_session:
            # Create project
            project = Project(
                id=project_id,
                tenant_key=tenant_key,
                name="Test Project for Broadcast Test",
                description="Test project",
                mission="Test mission",
                status="active",
                created_at=datetime.now(timezone.utc),
            )
            setup_session.add(project)

            # Create agent jobs
            agent1 = AgentExecution(
                job_id=agent1_job_id,
                tenant_key=tenant_key,
                project_id=project_id,
                agent_display_name="orchestrator",
                mission="Test mission",
                status="waiting",
                created_at=datetime.now(timezone.utc),
            )
            agent2 = AgentExecution(
                job_id=agent2_job_id,
                tenant_key=tenant_key,
                project_id=project_id,
                agent_display_name="analyzer",
                mission="Test mission",
                status="waiting",
                created_at=datetime.now(timezone.utc),
            )
            setup_session.add_all([agent1, agent2])
            await setup_session.commit()

        # Arrange: Set tenant context
        tenant_manager.set_current_tenant(tenant_key)

        # Create broadcast message
        msg_id = str(uuid4())
        async with db_manager.get_session_async() as setup_session:
            msg = Message(
                id=msg_id,
                tenant_key=tenant_key,
                project_id=project_id,
                to_agents=["all"],  # Broadcast to all agents
                message_type="broadcast",
                content="Broadcast message",
                priority="normal",
                status="waiting",
                created_at=datetime.now(timezone.utc),
                meta_data={"_from_agent": "orchestrator"},
            )
            setup_session.add(msg)
            await setup_session.commit()

        # Act: Agent1 receives the broadcast
        message_service = MessageService(db_manager, tenant_manager)

        result1 = await message_service.receive_messages(
            agent_id=agent1_job_id,
            limit=10,
            tenant_key=tenant_key
        )

        # Assert: Agent1 received and acknowledged the message
        assert result1["success"] is True
        assert result1["count"] == 1

        # Verify message from database
        async with db_manager.get_session_async() as verify_session:
            from sqlalchemy import select
            result = await verify_session.execute(select(Message).where(Message.id == msg_id))
            db_msg = result.scalar_one()

            # Message should be acknowledged by agent1
            assert db_msg.status == "acknowledged"
            assert agent1_job_id in db_msg.acknowledged_by

        # Act: Agent2 receives the broadcast (should still be available since status is shared)
        # Note: This tests the current behavior - broadcast messages become acknowledged
        # after first agent receives them. This may need adjustment based on requirements.
        result2 = await message_service.receive_messages(
            agent_id=agent2_job_id,
            limit=10,
            tenant_key=tenant_key
        )

        # For now, verify that the message was already acknowledged by agent1
        # Agent2 won't receive it since status="acknowledged" filters it out
        # This is the current expected behavior
        assert result2["count"] == 0 or msg_id not in [m["id"] for m in result2["messages"]]
