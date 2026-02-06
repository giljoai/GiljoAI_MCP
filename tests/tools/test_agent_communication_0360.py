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
import pytest_asyncio

from src.giljo_mcp.models.agent_identity import AgentJob, AgentExecution
from src.giljo_mcp.models.tasks import Message
from src.giljo_mcp.models.projects import Project
from src.giljo_mcp.services.message_service import MessageService


@pytest_asyncio.fixture
async def test_project_0360(db_session):
    """Create test project for message filtering tests."""
    project = Project(
        id="project-0360",
        tenant_key="tenant-0360",
        name="Test Project Message Filtering",
        description="Test project for message filtering",
        mission="Test message filtering",
        status="active"
    )
    db_session.add(project)
    await db_session.commit()
    return project


@pytest_asyncio.fixture
async def agent_a(db_session, test_project_0360):
    """Create Agent A execution for tests."""
    job = AgentJob(
        job_id="job-a-0360",
        tenant_key="tenant-0360",
        project_id="project-0360",
        mission="Test agent A",
        job_type="tdd-implementor",
        status="active"
    )
    db_session.add(job)

    execution = AgentExecution(
        agent_id="agent-a-0360",
        job_id=job.job_id,
        tenant_key="tenant-0360",
        agent_display_name="tdd-implementor",
        status="working")
    db_session.add(execution)
    await db_session.commit()
    return execution


@pytest_asyncio.fixture
async def agent_b(db_session, test_project_0360):
    """Create Agent B execution for tests."""
    job = AgentJob(
        job_id="job-b-0360",
        tenant_key="tenant-0360",
        project_id="project-0360",
        mission="Test agent B",
        job_type="database-expert",
        status="active"
    )
    db_session.add(job)

    execution = AgentExecution(
        agent_id="agent-b-0360",
        job_id=job.job_id,
        tenant_key="tenant-0360",
        agent_display_name="database-expert",
        status="working")
    db_session.add(execution)
    await db_session.commit()
    return execution


@pytest.mark.asyncio
async def test_receive_messages_exclude_self_filters_own_messages(
    db_session, db_manager, tenant_manager, agent_a, agent_b
):
    """Test that exclude_self=True filters out messages from the same agent."""
    # Agent A sends message to Agent B
    msg1 = Message(
        project_id="project-0360",
        tenant_key="tenant-0360",
        to_agents=[agent_b.agent_id],
        content="Message from Agent A",
        message_type="direct",
        priority="normal",
        status="pending",
        meta_data={"_from_agent": agent_a.agent_id},
    )
    db_session.add(msg1)

    # Agent B sends message to itself
    msg2 = Message(
        project_id="project-0360",
        tenant_key="tenant-0360",
        to_agents=[agent_b.agent_id],
        content="Self-reflection message",
        message_type="progress",
        priority="normal",
        status="pending",
        meta_data={"_from_agent": agent_b.agent_id},
    )
    db_session.add(msg2)
    await db_session.commit()

    # Agent B receives with exclude_self=True
    service = MessageService(db_manager, tenant_manager, test_session=db_session)
    messages = await service.receive_messages(
        agent_id=agent_b.agent_id,
        tenant_key="tenant-0360",
        exclude_self=True,
    )

    # Should only receive message from Agent A, not self-message
    assert len(messages) == 1
    assert messages[0]["content"] == "Message from Agent A"
    assert messages[0]["from_agent"] == agent_a.agent_id


@pytest.mark.asyncio
async def test_receive_messages_exclude_self_false_includes_own_messages(
    db_session, db_manager, tenant_manager, agent_b
):
    """Test that exclude_self=False includes messages from the same agent."""
    # Agent sends message to itself
    msg = Message(
        project_id="project-0360",
        tenant_key="tenant-0360",
        to_agents=[agent_b.agent_id],
        content="Self-reflection message",
        message_type="direct",
        priority="normal",
        status="pending",
        meta_data={"_from_agent": agent_b.agent_id},
    )
    db_session.add(msg)
    await db_session.commit()

    # Receive with exclude_self=False
    service = MessageService(db_manager, tenant_manager, test_session=db_session)
    messages = await service.receive_messages(
        agent_id=agent_b.agent_id,
        tenant_key="tenant-0360",
        exclude_self=False,
    )

    assert len(messages) == 1
    assert messages[0]["content"] == "Self-reflection message"


@pytest.mark.asyncio
async def test_receive_messages_exclude_progress_filters_progress_messages(
    db_session, db_manager, tenant_manager, agent_a, agent_b
):
    """Test that exclude_progress=True filters out progress-type messages."""
    # Create direct message
    msg1 = Message(
        project_id="project-0360",
        tenant_key="tenant-0360",
        to_agents=[agent_b.agent_id],
        content="Direct message",
        message_type="direct",
        priority="normal",
        status="pending",
        meta_data={"_from_agent": agent_a.agent_id},
    )
    db_session.add(msg1)

    # Create progress message
    msg2 = Message(
        project_id="project-0360",
        tenant_key="tenant-0360",
        to_agents=[agent_b.agent_id],
        content="Progress update",
        message_type="progress",
        priority="normal",
        status="pending",
        meta_data={"_from_agent": agent_a.agent_id},
    )
    db_session.add(msg2)
    await db_session.commit()

    # Receive with exclude_progress=True
    service = MessageService(db_manager, tenant_manager, test_session=db_session)
    messages = await service.receive_messages(
        agent_id=agent_b.agent_id,
        tenant_key="tenant-0360",
        exclude_progress=True,
    )

    assert len(messages) == 1
    assert messages[0]["content"] == "Direct message"
    assert messages[0]["type"] == "direct"


@pytest.mark.asyncio
async def test_receive_messages_exclude_progress_false_includes_all(
    db_session, db_manager, tenant_manager, agent_a, agent_b
):
    """Test that exclude_progress=False includes progress messages."""
    # Create direct and progress messages
    for msg_type in ["direct", "progress"]:
        msg = Message(
            project_id="project-0360",
            tenant_key="tenant-0360",
            to_agents=[agent_b.agent_id],
            content=f"{msg_type} message",
            message_type=msg_type,
            priority="normal",
            status="pending",
            meta_data={"_from_agent": agent_a.agent_id},
        )
        db_session.add(msg)
    await db_session.commit()

    # Receive with exclude_progress=False
    service = MessageService(db_manager, tenant_manager, test_session=db_session)
    messages = await service.receive_messages(
        agent_id=agent_b.agent_id,
        tenant_key="tenant-0360",
        exclude_progress=False,
    )

    assert len(messages) == 2
    message_types = {msg["type"] for msg in messages}
    assert message_types == {"direct", "progress"}


@pytest.mark.asyncio
async def test_receive_messages_filter_by_message_types(
    db_session, db_manager, tenant_manager, agent_a, agent_b
):
    """Test that message_types filter allows only specified types."""
    # Create messages of different types
    for msg_type in ["direct", "broadcast", "progress", "status"]:
        msg = Message(
            project_id="project-0360",
            tenant_key="tenant-0360",
            to_agents=[agent_b.agent_id],
            content=f"{msg_type} message",
            message_type=msg_type,
            priority="normal",
            status="pending",
            meta_data={"_from_agent": agent_a.agent_id},
        )
        db_session.add(msg)
    await db_session.commit()

    # Receive with message_types filter
    service = MessageService(db_manager, tenant_manager, test_session=db_session)
    messages = await service.receive_messages(
        agent_id=agent_b.agent_id,
        tenant_key="tenant-0360",
        message_types=["direct", "broadcast"],
    )

    assert len(messages) == 2
    received_types = {msg["type"] for msg in messages}
    assert received_types == {"direct", "broadcast"}


@pytest.mark.asyncio
async def test_receive_messages_combined_filters(
    db_session, db_manager, tenant_manager, agent_a, agent_b
):
    """Test that multiple filters work together correctly."""
    # Create test messages
    test_messages = [
        # Should receive: direct from Agent A
        ("direct", agent_a.agent_id, "Direct from A"),
        # Should filter: progress from Agent A
        ("progress", agent_a.agent_id, "Progress from A"),
        # Should filter: direct from self (Agent B)
        ("direct", agent_b.agent_id, "Direct from self"),
        # Should filter: broadcast (not in message_types)
        ("broadcast", agent_a.agent_id, "Broadcast from A"),
    ]

    for msg_type, from_agent, content in test_messages:
        msg = Message(
            project_id="project-0360",
            tenant_key="tenant-0360",
            to_agents=[agent_b.agent_id],
            content=content,
            message_type=msg_type,
            priority="normal",
            status="pending",
            meta_data={"_from_agent": from_agent},
        )
        db_session.add(msg)
    await db_session.commit()

    # Receive with all filters combined
    service = MessageService(db_manager, tenant_manager, test_session=db_session)
    messages = await service.receive_messages(
        agent_id=agent_b.agent_id,
        tenant_key="tenant-0360",
        exclude_self=True,
        exclude_progress=True,
        message_types=["direct"],
    )

    # Should only receive direct message from Agent A
    assert len(messages) == 1
    assert messages[0]["content"] == "Direct from A"
    assert messages[0]["type"] == "direct"
    assert messages[0]["from_agent"] == agent_a.agent_id


@pytest.mark.asyncio
async def test_receive_messages_backward_compatible_defaults(
    db_session, db_manager, tenant_manager, agent_a, agent_b
):
    """Test that existing callers without new params get sane defaults."""
    # Create messages of various types
    test_messages = [
        ("direct", agent_a.agent_id, "Direct from other"),
        ("progress", agent_a.agent_id, "Progress from other"),
        ("direct", agent_b.agent_id, "Direct from self"),
        ("broadcast", agent_a.agent_id, "Broadcast from other"),
    ]

    for msg_type, from_agent, content in test_messages:
        msg = Message(
            project_id="project-0360",
            tenant_key="tenant-0360",
            to_agents=[agent_b.agent_id],
            content=content,
            message_type=msg_type,
            priority="normal",
            status="pending",
            meta_data={"_from_agent": from_agent},
        )
        db_session.add(msg)
    await db_session.commit()

    # Call with NO new parameters (backward compatibility)
    service = MessageService(db_manager, tenant_manager, test_session=db_session)
    messages = await service.receive_messages(
        agent_id=agent_b.agent_id,
        tenant_key="tenant-0360",
    )

    # With defaults (exclude_self=True, exclude_progress=True):
    # Should receive: direct and broadcast from other agent
    # Should filter: progress (excluded), self messages (excluded)
    assert len(messages) == 2
    contents = {msg["content"] for msg in messages}
    assert "Direct from other" in contents
    assert "Broadcast from other" in contents
    assert "Progress from other" not in contents
    assert "Direct from self" not in contents


@pytest.mark.asyncio
async def test_receive_messages_empty_message_types_returns_nothing(
    db_session, db_manager, tenant_manager, agent_a, agent_b
):
    """Test that message_types=[] returns no messages."""
    msg = Message(
        project_id="project-0360",
        tenant_key="tenant-0360",
        to_agents=[agent_b.agent_id],
        content="Test message",
        message_type="direct",
        priority="normal",
        status="pending",
        meta_data={"_from_agent": agent_a.agent_id},
    )
    db_session.add(msg)
    await db_session.commit()

    # Empty message_types should return nothing
    service = MessageService(db_manager, tenant_manager, test_session=db_session)
    messages = await service.receive_messages(
        agent_id=agent_b.agent_id,
        tenant_key="tenant-0360",
        message_types=[],
    )

    assert len(messages) == 0
