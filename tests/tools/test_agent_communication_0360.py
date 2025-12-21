"""
Test suite for Handover 0360 Feature 1: Message Filtering for receive_messages()

This module tests the new filtering capabilities added to receive_messages():
- exclude_self: Filter out messages from the same agent
- exclude_progress: Filter out progress-type messages
- message_types: Allow-list filtering by message type
- Backward compatibility: Ensure existing callers work without changes

Author: TDD Implementor Agent
Date: 2025-12-21
Handover: 0360 - Medium Priority Tool Enhancements
"""

import pytest
from datetime import datetime, timezone
from uuid import uuid4

from giljo_mcp.database import DatabaseManager
from giljo_mcp.models.agent_identity import AgentJob, AgentExecution
from giljo_mcp.models.tasks import Message
from giljo_mcp.models.projects import Project, Product
from giljo_mcp.services.message_service_0366b import MessageService
from giljo_mcp.tenant import TenantManager


@pytest.fixture
async def db_manager():
    """Create a test database manager."""
    db = DatabaseManager()
    await db.initialize()
    yield db
    await db.cleanup()


@pytest.fixture
async def tenant_manager():
    """Create a test tenant manager."""
    return TenantManager()


@pytest.fixture
async def message_service(db_manager, tenant_manager):
    """Create a MessageService instance for testing."""
    return MessageService(
        db_manager=db_manager,
        tenant_manager=tenant_manager,
        websocket_manager=None
    )


@pytest.fixture
async def test_setup(db_manager):
    """
    Create a complete test environment with product, project, job, and execution.

    Returns:
        dict with keys: tenant_key, product_id, project_id, job_id, agent_id
    """
    async with db_manager.get_session_async() as session:
        tenant_key = f"tenant_{uuid4().hex[:8]}"

        # Create product
        product = Product(
            id=str(uuid4()),
            tenant_key=tenant_key,
            name="Test Product",
            description="Test product for message filtering",
            is_active=True,
            created_at=datetime.now(timezone.utc),
        )
        session.add(product)

        # Create project
        project = Project(
            id=str(uuid4()),
            tenant_key=tenant_key,
            product_id=product.id,
            name="Test Project",
            description="Test project for message filtering",
            status="active",
            created_at=datetime.now(timezone.utc),
        )
        session.add(project)

        # Create agent job
        job = AgentJob(
            job_id=str(uuid4()),
            tenant_key=tenant_key,
            project_id=project.id,
            agent_type="tdd-implementor",
            status="working",
            created_at=datetime.now(timezone.utc),
        )
        session.add(job)

        # Create agent execution
        execution = AgentExecution(
            id=str(uuid4()),
            agent_id=str(uuid4()),  # This is the execution UUID (agent_id)
            job_id=job.job_id,
            tenant_key=tenant_key,
            agent_type="tdd-implementor",
            status="working",
            instance_number=1,
            created_at=datetime.now(timezone.utc),
        )
        session.add(execution)

        await session.commit()

        return {
            "tenant_key": tenant_key,
            "product_id": product.id,
            "project_id": project.id,
            "job_id": job.job_id,
            "agent_id": execution.agent_id,
        }


@pytest.mark.asyncio
async def test_receive_messages_exclude_self_filters_own_messages(
    message_service, test_setup, db_manager
):
    """
    Test that exclude_self=True filters out messages from the same agent.

    Scenario:
    - Agent A sends a message to itself
    - Agent A sends a message to Agent B
    - Agent B calls receive_messages(exclude_self=True)
    - Should only receive the message from Agent A, not its own message
    """
    tenant_key = test_setup["tenant_key"]
    project_id = test_setup["project_id"]
    agent_id = test_setup["agent_id"]

    # Create second agent execution for testing
    async with db_manager.get_session_async() as session:
        job = AgentJob(
            job_id=str(uuid4()),
            tenant_key=tenant_key,
            project_id=project_id,
            agent_type="database-expert",
            status="working",
            created_at=datetime.now(timezone.utc),
        )
        session.add(job)

        agent_b_execution = AgentExecution(
            id=str(uuid4()),
            agent_id=str(uuid4()),
            job_id=job.job_id,
            tenant_key=tenant_key,
            agent_type="database-expert",
            status="working",
            instance_number=1,
            created_at=datetime.now(timezone.utc),
        )
        session.add(agent_b_execution)
        await session.commit()

        agent_b_id = agent_b_execution.agent_id

        # Agent A sends message to Agent B
        msg1 = Message(
            id=str(uuid4()),
            project_id=project_id,
            tenant_key=tenant_key,
            to_agents=[agent_b_id],
            content="Message from Agent A",
            message_type="direct",
            priority="normal",
            status="pending",
            meta_data={"_from_agent": agent_id},  # From Agent A
            created_at=datetime.now(timezone.utc),
        )
        session.add(msg1)

        # Agent B sends message to itself (self-message)
        msg2 = Message(
            id=str(uuid4()),
            project_id=project_id,
            tenant_key=tenant_key,
            to_agents=[agent_b_id],
            content="Self-reflection message",
            message_type="progress",
            priority="normal",
            status="pending",
            meta_data={"_from_agent": agent_b_id},  # From Agent B (self)
            created_at=datetime.now(timezone.utc),
        )
        session.add(msg2)

        await session.commit()

    # Agent B receives messages with exclude_self=True (NEW FEATURE)
    messages = await message_service.receive_messages(
        agent_id=agent_b_id,
        tenant_key=tenant_key,
        exclude_self=True,  # NEW PARAMETER
    )

    # Should only receive message from Agent A, not self-message
    assert len(messages) == 1
    assert messages[0]["content"] == "Message from Agent A"
    assert messages[0]["from_agent"] == agent_id


@pytest.mark.asyncio
async def test_receive_messages_exclude_self_false_includes_own_messages(
    message_service, test_setup, db_manager
):
    """
    Test that exclude_self=False includes messages from the same agent.
    """
    tenant_key = test_setup["tenant_key"]
    project_id = test_setup["project_id"]
    agent_id = test_setup["agent_id"]

    async with db_manager.get_session_async() as session:
        # Agent sends message to itself
        msg = Message(
            id=str(uuid4()),
            project_id=project_id,
            tenant_key=tenant_key,
            to_agents=[agent_id],
            content="Self-reflection message",
            message_type="direct",
            priority="normal",
            status="pending",
            meta_data={"_from_agent": agent_id},  # From self
            created_at=datetime.now(timezone.utc),
        )
        session.add(msg)
        await session.commit()

    # Receive with exclude_self=False
    messages = await message_service.receive_messages(
        agent_id=agent_id,
        tenant_key=tenant_key,
        exclude_self=False,  # NEW PARAMETER
    )

    # Should receive own message
    assert len(messages) == 1
    assert messages[0]["content"] == "Self-reflection message"


@pytest.mark.asyncio
async def test_receive_messages_exclude_progress_filters_progress_messages(
    message_service, test_setup, db_manager
):
    """
    Test that exclude_progress=True filters out progress-type messages.

    Scenario:
    - Agent receives a direct message
    - Agent receives a progress message
    - Agent calls receive_messages(exclude_progress=True)
    - Should only receive the direct message
    """
    tenant_key = test_setup["tenant_key"]
    project_id = test_setup["project_id"]
    agent_id = test_setup["agent_id"]

    async with db_manager.get_session_async() as session:
        # Create direct message
        msg1 = Message(
            id=str(uuid4()),
            project_id=project_id,
            tenant_key=tenant_key,
            to_agents=[agent_id],
            content="Direct message for you",
            message_type="direct",
            priority="normal",
            status="pending",
            meta_data={"_from_agent": "orchestrator"},
            created_at=datetime.now(timezone.utc),
        )
        session.add(msg1)

        # Create progress message
        msg2 = Message(
            id=str(uuid4()),
            project_id=project_id,
            tenant_key=tenant_key,
            to_agents=[agent_id],
            content="Progress update: 50% complete",
            message_type="progress",
            priority="normal",
            status="pending",
            meta_data={"_from_agent": "database-expert"},
            created_at=datetime.now(timezone.utc),
        )
        session.add(msg2)

        await session.commit()

    # Receive with exclude_progress=True (NEW FEATURE)
    messages = await message_service.receive_messages(
        agent_id=agent_id,
        tenant_key=tenant_key,
        exclude_progress=True,  # NEW PARAMETER
    )

    # Should only receive direct message, not progress
    assert len(messages) == 1
    assert messages[0]["content"] == "Direct message for you"
    assert messages[0]["type"] == "direct"


@pytest.mark.asyncio
async def test_receive_messages_exclude_progress_false_includes_all(
    message_service, test_setup, db_manager
):
    """
    Test that exclude_progress=False includes progress messages.
    """
    tenant_key = test_setup["tenant_key"]
    project_id = test_setup["project_id"]
    agent_id = test_setup["agent_id"]

    async with db_manager.get_session_async() as session:
        # Create direct and progress messages
        for msg_type in ["direct", "progress"]:
            msg = Message(
                id=str(uuid4()),
                project_id=project_id,
                tenant_key=tenant_key,
                to_agents=[agent_id],
                content=f"{msg_type} message",
                message_type=msg_type,
                priority="normal",
                status="pending",
                meta_data={"_from_agent": "orchestrator"},
                created_at=datetime.now(timezone.utc),
            )
            session.add(msg)
        await session.commit()

    # Receive with exclude_progress=False
    messages = await message_service.receive_messages(
        agent_id=agent_id,
        tenant_key=tenant_key,
        exclude_progress=False,  # NEW PARAMETER
    )

    # Should receive both messages
    assert len(messages) == 2
    message_types = {msg["type"] for msg in messages}
    assert message_types == {"direct", "progress"}


@pytest.mark.asyncio
async def test_receive_messages_filter_by_message_types(
    message_service, test_setup, db_manager
):
    """
    Test that message_types filter allows only specified types.

    Scenario:
    - Agent receives messages of types: direct, broadcast, progress, status
    - Agent calls receive_messages(message_types=["direct", "broadcast"])
    - Should only receive direct and broadcast messages
    """
    tenant_key = test_setup["tenant_key"]
    project_id = test_setup["project_id"]
    agent_id = test_setup["agent_id"]

    async with db_manager.get_session_async() as session:
        # Create messages of different types
        message_types_to_create = ["direct", "broadcast", "progress", "status"]
        for msg_type in message_types_to_create:
            msg = Message(
                id=str(uuid4()),
                project_id=project_id,
                tenant_key=tenant_key,
                to_agents=[agent_id],
                content=f"{msg_type} message content",
                message_type=msg_type,
                priority="normal",
                status="pending",
                meta_data={"_from_agent": "orchestrator"},
                created_at=datetime.now(timezone.utc),
            )
            session.add(msg)
        await session.commit()

    # Receive with message_types filter (NEW FEATURE)
    messages = await message_service.receive_messages(
        agent_id=agent_id,
        tenant_key=tenant_key,
        message_types=["direct", "broadcast"],  # NEW PARAMETER
    )

    # Should only receive direct and broadcast messages
    assert len(messages) == 2
    received_types = {msg["type"] for msg in messages}
    assert received_types == {"direct", "broadcast"}


@pytest.mark.asyncio
async def test_receive_messages_filter_by_single_message_type(
    message_service, test_setup, db_manager
):
    """
    Test that message_types filter works with a single type.
    """
    tenant_key = test_setup["tenant_key"]
    project_id = test_setup["project_id"]
    agent_id = test_setup["agent_id"]

    async with db_manager.get_session_async() as session:
        # Create messages of different types
        for msg_type in ["direct", "progress", "broadcast"]:
            msg = Message(
                id=str(uuid4()),
                project_id=project_id,
                tenant_key=tenant_key,
                to_agents=[agent_id],
                content=f"{msg_type} message",
                message_type=msg_type,
                priority="normal",
                status="pending",
                meta_data={"_from_agent": "orchestrator"},
                created_at=datetime.now(timezone.utc),
            )
            session.add(msg)
        await session.commit()

    # Filter for only direct messages
    messages = await message_service.receive_messages(
        agent_id=agent_id,
        tenant_key=tenant_key,
        message_types=["direct"],  # NEW PARAMETER
    )

    # Should only receive direct message
    assert len(messages) == 1
    assert messages[0]["type"] == "direct"


@pytest.mark.asyncio
async def test_receive_messages_combined_filters(
    message_service, test_setup, db_manager
):
    """
    Test that multiple filters work together correctly.

    Scenario:
    - Agent A and Agent B both send messages
    - Agent B receives with exclude_self=True, exclude_progress=True, message_types=["direct"]
    - Should only receive direct messages from Agent A, excluding own messages and progress
    """
    tenant_key = test_setup["tenant_key"]
    project_id = test_setup["project_id"]
    agent_id = test_setup["agent_id"]

    # Create second agent
    async with db_manager.get_session_async() as session:
        job = AgentJob(
            job_id=str(uuid4()),
            tenant_key=tenant_key,
            project_id=project_id,
            agent_type="database-expert",
            status="working",
            created_at=datetime.now(timezone.utc),
        )
        session.add(job)

        agent_b = AgentExecution(
            id=str(uuid4()),
            agent_id=str(uuid4()),
            job_id=job.job_id,
            tenant_key=tenant_key,
            agent_type="database-expert",
            status="working",
            instance_number=1,
            created_at=datetime.now(timezone.utc),
        )
        session.add(agent_b)
        await session.commit()

        agent_b_id = agent_b.agent_id

        # Create test messages
        test_messages = [
            # Should receive: direct from Agent A
            ("direct", agent_id, "Direct from A"),
            # Should filter: progress from Agent A
            ("progress", agent_id, "Progress from A"),
            # Should filter: direct from self (Agent B)
            ("direct", agent_b_id, "Direct from self"),
            # Should filter: broadcast (not in message_types)
            ("broadcast", agent_id, "Broadcast from A"),
        ]

        for msg_type, from_agent, content in test_messages:
            msg = Message(
                id=str(uuid4()),
                project_id=project_id,
                tenant_key=tenant_key,
                to_agents=[agent_b_id],
                content=content,
                message_type=msg_type,
                priority="normal",
                status="pending",
                meta_data={"_from_agent": from_agent},
                created_at=datetime.now(timezone.utc),
            )
            session.add(msg)
        await session.commit()

    # Receive with all filters combined (NEW FEATURE)
    messages = await message_service.receive_messages(
        agent_id=agent_b_id,
        tenant_key=tenant_key,
        exclude_self=True,
        exclude_progress=True,
        message_types=["direct"],
    )

    # Should only receive direct message from Agent A
    assert len(messages) == 1
    assert messages[0]["content"] == "Direct from A"
    assert messages[0]["type"] == "direct"
    assert messages[0]["from_agent"] == agent_id


@pytest.mark.asyncio
async def test_receive_messages_backward_compatible_defaults(
    message_service, test_setup, db_manager
):
    """
    Test that existing callers without new params get sane defaults.

    Backward Compatibility Requirements:
    - exclude_self defaults to True (filter own messages by default)
    - exclude_progress defaults to True (filter progress by default)
    - message_types defaults to None (no type filtering)

    This ensures existing code continues to work without modification.
    """
    tenant_key = test_setup["tenant_key"]
    project_id = test_setup["project_id"]
    agent_id = test_setup["agent_id"]

    async with db_manager.get_session_async() as session:
        # Create messages of various types
        test_messages = [
            ("direct", "other-agent", "Direct from other"),
            ("progress", "other-agent", "Progress from other"),
            ("direct", agent_id, "Direct from self"),
            ("broadcast", "other-agent", "Broadcast from other"),
        ]

        for msg_type, from_agent, content in test_messages:
            msg = Message(
                id=str(uuid4()),
                project_id=project_id,
                tenant_key=tenant_key,
                to_agents=[agent_id],
                content=content,
                message_type=msg_type,
                priority="normal",
                status="pending",
                meta_data={"_from_agent": from_agent},
                created_at=datetime.now(timezone.utc),
            )
            session.add(msg)
        await session.commit()

    # Call with NO new parameters (backward compatibility)
    messages = await message_service.receive_messages(
        agent_id=agent_id,
        tenant_key=tenant_key,
        # NO exclude_self, exclude_progress, or message_types parameters
    )

    # With default behavior (exclude_self=True, exclude_progress=True):
    # Should receive: direct and broadcast from other agent
    # Should filter: progress (excluded), self messages (excluded)
    assert len(messages) == 2
    contents = {msg["content"] for msg in messages}
    assert "Direct from other" in contents
    assert "Broadcast from other" in contents
    # Should NOT include progress or self messages
    assert "Progress from other" not in contents
    assert "Direct from self" not in contents


@pytest.mark.asyncio
async def test_receive_messages_empty_message_types_returns_nothing(
    message_service, test_setup, db_manager
):
    """
    Test that message_types=[] returns no messages (strict filtering).
    """
    tenant_key = test_setup["tenant_key"]
    project_id = test_setup["project_id"]
    agent_id = test_setup["agent_id"]

    async with db_manager.get_session_async() as session:
        msg = Message(
            id=str(uuid4()),
            project_id=project_id,
            tenant_key=tenant_key,
            to_agents=[agent_id],
            content="Test message",
            message_type="direct",
            priority="normal",
            status="pending",
            meta_data={"_from_agent": "orchestrator"},
            created_at=datetime.now(timezone.utc),
        )
        session.add(msg)
        await session.commit()

    # Empty message_types should return nothing
    messages = await message_service.receive_messages(
        agent_id=agent_id,
        tenant_key=tenant_key,
        message_types=[],  # Empty allow-list
    )

    assert len(messages) == 0


@pytest.mark.asyncio
async def test_receive_messages_tenant_isolation_with_filters(
    message_service, test_setup, db_manager
):
    """
    Test that filtering respects tenant isolation.

    Messages from other tenants should never appear, even with permissive filters.
    """
    tenant_key = test_setup["tenant_key"]
    other_tenant_key = f"tenant_{uuid4().hex[:8]}"
    project_id = test_setup["project_id"]
    agent_id = test_setup["agent_id"]

    async with db_manager.get_session_async() as session:
        # Create message in our tenant
        msg1 = Message(
            id=str(uuid4()),
            project_id=project_id,
            tenant_key=tenant_key,
            to_agents=[agent_id],
            content="Message in our tenant",
            message_type="direct",
            priority="normal",
            status="pending",
            meta_data={"_from_agent": "orchestrator"},
            created_at=datetime.now(timezone.utc),
        )
        session.add(msg1)

        # Create message in different tenant (should be filtered)
        msg2 = Message(
            id=str(uuid4()),
            project_id=project_id,
            tenant_key=other_tenant_key,  # Different tenant
            to_agents=[agent_id],
            content="Message in other tenant",
            message_type="direct",
            priority="normal",
            status="pending",
            meta_data={"_from_agent": "orchestrator"},
            created_at=datetime.now(timezone.utc),
        )
        session.add(msg2)

        await session.commit()

    # Receive with permissive filters
    messages = await message_service.receive_messages(
        agent_id=agent_id,
        tenant_key=tenant_key,
        exclude_self=False,
        exclude_progress=False,
        message_types=None,
    )

    # Should only receive message from our tenant
    assert len(messages) == 1
    assert messages[0]["content"] == "Message in our tenant"
