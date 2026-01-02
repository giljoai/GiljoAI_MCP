"""
Integration tests for Broadcast Fan-out at Write (Handover 0387)

Tests verify that broadcast messages are expanded into individual Message records
at write time, with per-recipient acknowledgment and proper database isolation.

Key Behaviors Tested:
1. Broadcast to ["all"] creates individual Message records (one per recipient)
2. Database has NO literal "all" in to_agents after fan-out
3. Each recipient acknowledges independently (isolation)
4. Sender is excluded from broadcast recipients
"""

import pytest
from datetime import datetime, timezone
from uuid import uuid4

from giljo_mcp.services.message_service import MessageService
from giljo_mcp.models import Message, Project, AgentJob, AgentExecution
from sqlalchemy import select, func
from sqlalchemy.dialects.postgresql import JSONB


class TestBroadcastFanout:
    """Integration tests for broadcast fan-out at write"""

    @pytest.mark.asyncio
    async def test_e2e_broadcast_workflow(self, db_manager, tenant_manager):
        """
        Full broadcast lifecycle: send → receive → acknowledge

        GIVEN: Project with orchestrator + 3 executor agents
        WHEN: Orchestrator sends broadcast via send_message(to_agents=["all"])
        THEN: Each agent receives exactly 1 message AND acknowledgment doesn't affect other agents
        """
        from giljo_mcp.tenant import TenantManager

        # Setup: Create isolated test environment
        tenant_key = TenantManager.generate_tenant_key(f"test_fanout_{uuid4().hex[:8]}")
        project_id = str(uuid4())

        # Create project
        async with db_manager.get_session_async() as setup_session:
            project = Project(
                id=project_id,
                tenant_key=tenant_key,
                name="Test Broadcast Project",
                description="Test project for broadcast fan-out",
                mission="Test broadcast fan-out workflow",
                status="active",
                created_at=datetime.now(timezone.utc),
            )
            setup_session.add(project)
            await setup_session.commit()

        # Create orchestrator + 3 executor agents
        agent_ids = []
        async with db_manager.get_session_async() as setup_session:
            # Orchestrator (will be sender - excluded from broadcast)
            orch_job = AgentJob(
                job_id=str(uuid4()),
                tenant_key=tenant_key,
                project_id=project_id,
                job_type="orchestrator",
                mission="Orchestrator mission",
                status="active",
            )
            setup_session.add(orch_job)

            orch_execution = AgentExecution(
                agent_id=str(uuid4()),
                job_id=orch_job.job_id,
                tenant_key=tenant_key,
                agent_type="orchestrator",
                agent_name="Test Orchestrator",
                instance_number=1,
                status="working",
                progress=0,
                messages=[],
                health_status="healthy",
            )
            setup_session.add(orch_execution)

            # Create 3 executor agents
            for i in range(3):
                job = AgentJob(
                    job_id=str(uuid4()),
                    tenant_key=tenant_key,
                    project_id=project_id,
                    job_type="worker",
                    mission=f"Worker {i+1} mission",
                    status="active",
                )
                setup_session.add(job)

                execution = AgentExecution(
                    agent_id=str(uuid4()),
                    job_id=job.job_id,
                    tenant_key=tenant_key,
                    agent_type="implementer",
                    agent_name=f"Worker Agent {i+1}",
                    instance_number=1,
                    status="waiting",
                    progress=0,
                    messages=[],
                    health_status="healthy",
                )
                setup_session.add(execution)
                agent_ids.append(execution.agent_id)

            await setup_session.commit()

        # Set tenant context
        tenant_manager.set_current_tenant(tenant_key)

        # ACTION 1: Orchestrator sends broadcast
        message_service = MessageService(db_manager, tenant_manager)

        send_result = await message_service.send_message(
            to_agents=["all"],
            content="Broadcast message to all agents",
            project_id=project_id,
            message_type="broadcast",
            priority="normal",
            from_agent="orchestrator",
            tenant_key=tenant_key
        )

        # ASSERT: Send succeeded
        assert send_result["success"] is True, f"Send failed: {send_result.get('error', 'unknown')}"

        # ACTION 2: Each agent receives messages
        messages_received = []
        for agent_id in agent_ids:
            result = await message_service.receive_messages(
                agent_id=agent_id,
                limit=10,
                tenant_key=tenant_key
            )
            assert result["success"] is True
            messages_received.append({
                "agent_id": agent_id,
                "messages": result["messages"],
                "count": result["count"]
            })

        # ASSERT: Each agent receives exactly 1 message
        for agent_data in messages_received:
            assert agent_data["count"] == 1, f"Agent {agent_data['agent_id']} received {agent_data['count']} messages, expected 1"
            msg = agent_data["messages"][0]
            assert msg["content"] == "Broadcast message to all agents"
            assert msg["type"] == "broadcast"
            assert msg["acknowledged"] is True  # Auto-acknowledged by receive_messages

        # ASSERT: Acknowledgment is independent per agent
        async with db_manager.get_session_async() as verify_session:
            # Get all messages created by this broadcast
            result = await verify_session.execute(
                select(Message).where(
                    Message.tenant_key == tenant_key,
                    Message.project_id == project_id
                )
            )
            all_messages = result.scalars().all()

            # Should have 3 separate Message records (one per recipient, orchestrator excluded)
            assert len(all_messages) == 3, f"Expected 3 messages, got {len(all_messages)}"

            # Each message should be acknowledged by exactly 1 agent
            for msg in all_messages:
                assert len(msg.acknowledged_by) == 1, f"Message {msg.id} acknowledged by {len(msg.acknowledged_by)} agents"
                assert msg.acknowledged_by[0] in agent_ids, f"Unexpected acknowledger: {msg.acknowledged_by[0]}"

    @pytest.mark.asyncio
    async def test_broadcast_creates_individual_db_records(self, db_manager, tenant_manager):
        """
        Verify database has individual Message records, not literal 'all'

        GIVEN: Broadcast message sent
        WHEN: Query database for to_agents
        THEN: NO messages have to_agents = ["all"], all have single agent_id
        """
        from giljo_mcp.tenant import TenantManager

        # Setup: Create isolated test environment
        tenant_key = TenantManager.generate_tenant_key(f"test_db_records_{uuid4().hex[:8]}")
        project_id = str(uuid4())

        async with db_manager.get_session_async() as setup_session:
            project = Project(
                id=project_id,
                tenant_key=tenant_key,
                name="Test DB Records Project",
                description="Test database record structure",
                mission="Test individual message records",
                status="active",
                created_at=datetime.now(timezone.utc),
            )
            setup_session.add(project)

            # Create 4 agents (orchestrator + 3 workers)
            orch_job = AgentJob(
                job_id=str(uuid4()),
                tenant_key=tenant_key,
                project_id=project_id,
                job_type="orchestrator",
                mission="Orchestrator mission",
                status="active",
            )
            setup_session.add(orch_job)

            orch_execution = AgentExecution(
                agent_id=str(uuid4()),
                job_id=orch_job.job_id,
                tenant_key=tenant_key,
                agent_type="orchestrator",
                agent_name="Test Orchestrator",
                instance_number=1,
                status="working",
            )
            setup_session.add(orch_execution)

            agent_ids = []
            for i in range(3):
                job = AgentJob(
                    job_id=str(uuid4()),
                    tenant_key=tenant_key,
                    project_id=project_id,
                    job_type="worker",
                    mission=f"Worker {i+1} mission",
                    status="active",
                )
                setup_session.add(job)

                execution = AgentExecution(
                    agent_id=str(uuid4()),
                    job_id=job.job_id,
                    tenant_key=tenant_key,
                    agent_type="implementer",
                    agent_name=f"Worker {i+1}",
                    instance_number=1,
                    status="waiting",
                )
                setup_session.add(execution)
                agent_ids.append(execution.agent_id)

            await setup_session.commit()

        # Set tenant context
        tenant_manager.set_current_tenant(tenant_key)

        # Send broadcast
        message_service = MessageService(db_manager, tenant_manager)

        result = await message_service.send_message(
            to_agents=["all"],
            content="Database structure test",
            project_id=project_id,
            message_type="broadcast",
            priority="normal",
            from_agent="orchestrator",
            tenant_key=tenant_key
        )

        assert result["success"] is True

        # QUERY: Look for literal "all" in to_agents
        async with db_manager.get_session_async() as verify_session:
            # Query for messages with to_agents containing literal "all"
            # PostgreSQL JSONB contains operator @>
            query_all_literal = select(Message).where(
                Message.tenant_key == tenant_key,
                func.cast(Message.to_agents, JSONB).op('@>')(func.cast(["all"], JSONB))
            )
            result = await verify_session.execute(query_all_literal)
            messages_with_all = result.scalars().all()

            # ASSERT: NO messages should have literal "all"
            assert len(messages_with_all) == 0, f"Found {len(messages_with_all)} messages with literal 'all' in to_agents"

            # Query all broadcast messages
            query_broadcasts = select(Message).where(
                Message.tenant_key == tenant_key,
                Message.project_id == project_id,
                Message.message_type == "broadcast"
            )
            result = await verify_session.execute(query_broadcasts)
            all_broadcasts = result.scalars().all()

            # ASSERT: Should have 3 individual messages (one per recipient, orchestrator excluded)
            assert len(all_broadcasts) == 3, f"Expected 3 broadcast messages, got {len(all_broadcasts)}"

            # ASSERT: Each message has exactly 1 recipient (single agent_id)
            for msg in all_broadcasts:
                assert len(msg.to_agents) == 1, f"Message {msg.id} has {len(msg.to_agents)} recipients, expected 1"
                assert msg.to_agents[0] in agent_ids, f"Unexpected recipient: {msg.to_agents[0]}"
                assert msg.to_agents[0] != "all", f"Message {msg.id} has literal 'all' in to_agents"

    @pytest.mark.asyncio
    async def test_per_recipient_acknowledgment_isolation(self, db_manager, tenant_manager):
        """
        Each agent's acknowledgment is independent

        GIVEN: Broadcast sent to 3 agents
        WHEN: Agent A reads messages → Agent B reads messages → Agent C does NOT read
        THEN: Agent A's message is acknowledged, Agent B's message is acknowledged, Agent C's message is pending
        """
        from giljo_mcp.tenant import TenantManager

        # Setup: Create isolated test environment
        tenant_key = TenantManager.generate_tenant_key(f"test_ack_isolation_{uuid4().hex[:8]}")
        project_id = str(uuid4())

        async with db_manager.get_session_async() as setup_session:
            project = Project(
                id=project_id,
                tenant_key=tenant_key,
                name="Test Acknowledgment Isolation",
                description="Test per-recipient acknowledgment",
                mission="Test acknowledgment independence",
                status="active",
                created_at=datetime.now(timezone.utc),
            )
            setup_session.add(project)

            # Create orchestrator + 3 workers
            orch_job = AgentJob(
                job_id=str(uuid4()),
                tenant_key=tenant_key,
                project_id=project_id,
                job_type="orchestrator",
                mission="Orchestrator mission",
                status="active",
            )
            setup_session.add(orch_job)

            orch_execution = AgentExecution(
                agent_id=str(uuid4()),
                job_id=orch_job.job_id,
                tenant_key=tenant_key,
                agent_type="orchestrator",
                agent_name="Test Orchestrator",
                instance_number=1,
                status="working",
            )
            setup_session.add(orch_execution)

            agent_ids = []
            for i in range(3):
                job = AgentJob(
                    job_id=str(uuid4()),
                    tenant_key=tenant_key,
                    project_id=project_id,
                    job_type="worker",
                    mission=f"Worker {i+1} mission",
                    status="active",
                )
                setup_session.add(job)

                execution = AgentExecution(
                    agent_id=str(uuid4()),
                    job_id=job.job_id,
                    tenant_key=tenant_key,
                    agent_type="implementer",
                    agent_name=f"Agent {chr(65 + i)}",  # Agent A, B, C
                    instance_number=1,
                    status="waiting",
                )
                setup_session.add(execution)
                agent_ids.append(execution.agent_id)

            await setup_session.commit()

        agent_a_id, agent_b_id, agent_c_id = agent_ids

        # Set tenant context
        tenant_manager.set_current_tenant(tenant_key)

        # Send broadcast to 3 agents
        message_service = MessageService(db_manager, tenant_manager)

        result = await message_service.send_message(
            to_agents=["all"],
            content="Acknowledgment isolation test",
            project_id=project_id,
            message_type="broadcast",
            priority="normal",
            from_agent="orchestrator",
            tenant_key=tenant_key
        )

        assert result["success"] is True

        # ACTION: Agent A reads messages (auto-acknowledge)
        result_a = await message_service.receive_messages(
            agent_id=agent_a_id,
            limit=10,
            tenant_key=tenant_key
        )
        assert result_a["success"] is True
        assert result_a["count"] == 1

        # VERIFY: Agent A's message is acknowledged, Agent B and C are still pending
        async with db_manager.get_session_async() as verify_session:
            result = await verify_session.execute(
                select(Message).where(
                    Message.tenant_key == tenant_key,
                    Message.project_id == project_id
                )
            )
            all_messages = result.scalars().all()

            # Find each agent's message
            msg_a = next((m for m in all_messages if agent_a_id in m.to_agents), None)
            msg_b = next((m for m in all_messages if agent_b_id in m.to_agents), None)
            msg_c = next((m for m in all_messages if agent_c_id in m.to_agents), None)

            assert msg_a is not None, "Agent A's message not found"
            assert msg_b is not None, "Agent B's message not found"
            assert msg_c is not None, "Agent C's message not found"

            # ASSERT: Agent A acknowledged, B and C are pending
            assert msg_a.status == "acknowledged", f"Agent A message status: {msg_a.status}"
            assert agent_a_id in msg_a.acknowledged_by, "Agent A not in acknowledged_by"

            assert msg_b.status == "pending", f"Agent B message should be pending, got: {msg_b.status}"
            assert msg_b.acknowledged_by == [] or msg_b.acknowledged_by is None, f"Agent B acknowledged_by should be empty: {msg_b.acknowledged_by}"

            assert msg_c.status == "pending", f"Agent C message should be pending, got: {msg_c.status}"
            assert msg_c.acknowledged_by == [] or msg_c.acknowledged_by is None, f"Agent C acknowledged_by should be empty: {msg_c.acknowledged_by}"

        # ACTION: Agent B reads messages (auto-acknowledge)
        result_b = await message_service.receive_messages(
            agent_id=agent_b_id,
            limit=10,
            tenant_key=tenant_key
        )
        assert result_b["success"] is True
        assert result_b["count"] == 1

        # VERIFY: Agent A and B acknowledged, Agent C still pending
        async with db_manager.get_session_async() as verify_session:
            result = await verify_session.execute(
                select(Message).where(
                    Message.tenant_key == tenant_key,
                    Message.project_id == project_id
                )
            )
            all_messages = result.scalars().all()

            msg_a = next((m for m in all_messages if agent_a_id in m.to_agents), None)
            msg_b = next((m for m in all_messages if agent_b_id in m.to_agents), None)
            msg_c = next((m for m in all_messages if agent_c_id in m.to_agents), None)

            # ASSERT: A and B acknowledged
            assert msg_a.status == "acknowledged", f"Agent A message status: {msg_a.status}"
            assert agent_a_id in msg_a.acknowledged_by

            assert msg_b.status == "acknowledged", f"Agent B message status: {msg_b.status}"
            assert agent_b_id in msg_b.acknowledged_by

            # ASSERT: C still pending (NOT affected by A and B)
            assert msg_c.status == "pending", f"Agent C message should be pending, got: {msg_c.status}"
            assert msg_c.acknowledged_by == [] or msg_c.acknowledged_by is None, f"Agent C should not be acknowledged: {msg_c.acknowledged_by}"

    @pytest.mark.asyncio
    async def test_sender_excluded_from_broadcast(self, db_manager, tenant_manager):
        """
        Verify sender is excluded from broadcast recipients

        GIVEN: Orchestrator sends broadcast to ["all"]
        WHEN: Orchestrator calls receive_messages
        THEN: Orchestrator receives 0 messages (self-exclusion)
        """
        from giljo_mcp.tenant import TenantManager

        # Setup
        tenant_key = TenantManager.generate_tenant_key(f"test_sender_exclude_{uuid4().hex[:8]}")
        project_id = str(uuid4())

        async with db_manager.get_session_async() as setup_session:
            project = Project(
                id=project_id,
                tenant_key=tenant_key,
                name="Test Sender Exclusion",
                description="Test sender exclusion from broadcast",
                mission="Test sender is not in recipients",
                status="active",
                created_at=datetime.now(timezone.utc),
            )
            setup_session.add(project)

            # Create orchestrator
            orch_job = AgentJob(
                job_id=str(uuid4()),
                tenant_key=tenant_key,
                project_id=project_id,
                job_type="orchestrator",
                mission="Orchestrator mission",
                status="active",
            )
            setup_session.add(orch_job)

            orch_execution = AgentExecution(
                agent_id=str(uuid4()),
                job_id=orch_job.job_id,
                tenant_key=tenant_key,
                agent_type="orchestrator",
                agent_name="Test Orchestrator",
                instance_number=1,
                status="working",
            )
            setup_session.add(orch_execution)
            orch_agent_id = orch_execution.agent_id

            # Create 2 workers
            for i in range(2):
                job = AgentJob(
                    job_id=str(uuid4()),
                    tenant_key=tenant_key,
                    project_id=project_id,
                    job_type="worker",
                    mission=f"Worker {i+1} mission",
                    status="active",
                )
                setup_session.add(job)

                execution = AgentExecution(
                    agent_id=str(uuid4()),
                    job_id=job.job_id,
                    tenant_key=tenant_key,
                    agent_type="implementer",
                    agent_name=f"Worker {i+1}",
                    instance_number=1,
                    status="waiting",
                )
                setup_session.add(execution)

            await setup_session.commit()

        # Set tenant context
        tenant_manager.set_current_tenant(tenant_key)

        # Send broadcast from orchestrator
        message_service = MessageService(db_manager, tenant_manager)

        result = await message_service.send_message(
            to_agents=["all"],
            content="Sender exclusion test",
            project_id=project_id,
            message_type="broadcast",
            priority="normal",
            from_agent="orchestrator",
            tenant_key=tenant_key
        )

        assert result["success"] is True

        # VERIFY: Database has 2 messages (workers only, orchestrator excluded)
        async with db_manager.get_session_async() as verify_session:
            result = await verify_session.execute(
                select(Message).where(
                    Message.tenant_key == tenant_key,
                    Message.project_id == project_id
                )
            )
            all_messages = result.scalars().all()

            # Should have exactly 2 messages (2 workers, orchestrator excluded)
            assert len(all_messages) == 2, f"Expected 2 messages (workers only), got {len(all_messages)}"

            # VERIFY: Orchestrator agent_id is NOT in any to_agents
            for msg in all_messages:
                assert orch_agent_id not in msg.to_agents, f"Orchestrator {orch_agent_id} should not be in recipients: {msg.to_agents}"

        # VERIFY: Orchestrator receives 0 messages when calling receive_messages
        orch_result = await message_service.receive_messages(
            agent_id=orch_agent_id,
            limit=10,
            tenant_key=tenant_key
        )

        assert orch_result["success"] is True
        assert orch_result["count"] == 0, f"Orchestrator should receive 0 messages, got {orch_result['count']}"
