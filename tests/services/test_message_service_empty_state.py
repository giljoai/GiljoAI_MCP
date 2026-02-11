"""
Unit tests for MessageService empty state handling.

Tests that MessageService methods gracefully handle scenarios where:
- No projects exist
- No agent executions exist
- Database is empty (fresh install)

Critical behaviors:
1. get_messages() returns empty list when no agent exists
2. list_messages() returns empty list when no messages exist
3. No exceptions thrown on empty database queries
4. Proper empty result structures returned

Updated for Handover 0730: Exception-based patterns (no success wrapper)
Updated for actual MessageService API (not fantasy methods)
"""

from datetime import datetime, timezone
from unittest.mock import AsyncMock, MagicMock
from uuid import uuid4

import pytest
from sqlalchemy.ext.asyncio import AsyncSession

from src.giljo_mcp.database import DatabaseManager
from src.giljo_mcp.exceptions import ResourceNotFoundError
from src.giljo_mcp.models.agent_identity import AgentExecution, AgentJob
from src.giljo_mcp.models.products import Product
from src.giljo_mcp.models.projects import Project
from src.giljo_mcp.schemas.service_responses import MessageListResult
from src.giljo_mcp.services.message_service import MessageService
from src.giljo_mcp.tenant import TenantManager


@pytest.fixture
async def test_tenant_key() -> str:
    """Generate unique tenant key for test isolation."""
    return f"test-tenant-{uuid4().hex[:8]}"


@pytest.fixture
async def test_product(db_session: AsyncSession, test_tenant_key: str) -> Product:
    """Create a test product for tests."""
    product = Product(
        id=str(uuid4()),
        tenant_key=test_tenant_key,
        name="Test Product Empty State",
        description="Test product for empty state tests",
        product_memory={},
    )
    db_session.add(product)
    await db_session.commit()
    await db_session.refresh(product)
    return product


@pytest.fixture
async def empty_project(
    db_session: AsyncSession,
    test_tenant_key: str,
    test_product: Product,
) -> Project:
    """Create a test project with NO agents."""
    project = Project(
        id=str(uuid4()),
        tenant_key=test_tenant_key,
        product_id=test_product.id,
        name="Empty Test Project",
        description="Test project with no agents",
        mission="Test mission",
        status="active",
        created_at=datetime.now(timezone.utc),
    )
    db_session.add(project)
    await db_session.commit()
    await db_session.refresh(project)
    return project


@pytest.fixture
def mock_websocket_manager():
    """Mock WebSocket manager for testing without real WebSocket connections."""
    mock = MagicMock()
    mock.broadcast_message_sent = AsyncMock()
    mock.broadcast_message_received = AsyncMock()
    mock.broadcast_message_acknowledged = AsyncMock()
    mock.broadcast_job_message = AsyncMock()
    return mock


@pytest.fixture
async def message_service(
    db_manager: DatabaseManager,
    db_session: AsyncSession,
    mock_websocket_manager: MagicMock,
) -> MessageService:
    """Create MessageService instance with mocked WebSocket manager and test session."""
    from contextlib import asynccontextmanager

    tenant_manager = TenantManager()

    @asynccontextmanager
    async def mock_get_session_async():
        yield db_session

    db_manager.get_session_async = mock_get_session_async

    service = MessageService(
        db_manager=db_manager,
        tenant_manager=tenant_manager,
        websocket_manager=mock_websocket_manager,
        test_session=db_session,
    )
    return service


@pytest.mark.asyncio
async def test_get_messages_nonexistent_agent_returns_empty(
    message_service: MessageService,
):
    """
    get_messages() should return empty list when agent doesn't exist.

    Scenario: Fresh install, user has no agents yet.
    Expected: Returns empty messages list without throwing exceptions.

    Handover 0730: Returns dict with 'messages' key (no success wrapper)
    """
    # Call get_messages for nonexistent agent
    result = await message_service.get_messages(agent_name="nonexistent-agent")

    # Handover 0731c: Returns MessageListResult typed model
    assert isinstance(result, MessageListResult)
    assert result.messages == []


@pytest.mark.asyncio
async def test_list_messages_nonexistent_project_returns_empty(
    message_service: MessageService,
):
    """
    list_messages() should return empty list when project doesn't exist.

    Scenario: Query messages for project that doesn't exist.
    Expected: Returns empty list (graceful handling per Handover 0464).

    Handover 0464: No project = no messages, returns empty list not error
    """
    result = await message_service.list_messages(
        project_id="nonexistent-project-id",
        tenant_key="nonexistent-tenant",
    )

    # Handover 0731c: Returns MessageListResult typed model
    assert isinstance(result, MessageListResult)
    assert result.messages == []


@pytest.mark.asyncio
async def test_list_messages_empty_project_returns_empty(
    message_service: MessageService,
    empty_project: Project,
):
    """
    list_messages() should return empty list when project has no messages.

    Scenario: Project exists but has no messages yet.
    Expected: Returns empty messages list.

    Handover 0730: Returns dict with 'messages' key (no success wrapper)
    """
    result = await message_service.list_messages(
        project_id=empty_project.id,
        tenant_key=empty_project.tenant_key,
    )

    # Handover 0731c: Returns MessageListResult typed model
    assert isinstance(result, MessageListResult)
    assert result.messages == []


@pytest.mark.asyncio
async def test_broadcast_to_empty_project_raises_not_found(
    message_service: MessageService,
    empty_project: Project,
):
    """
    broadcast_to_project() should raise ResourceNotFoundError when no agents exist.

    Scenario: User tries to broadcast but no agents are running.
    Expected: Raises ResourceNotFoundError since no active executions.

    Handover 0730: Exception-based error handling
    """
    with pytest.raises(ResourceNotFoundError) as exc_info:
        await message_service.broadcast_to_project(
            project_id=empty_project.id,
            content="Test broadcast",
            from_agent="orchestrator",
            tenant_key=empty_project.tenant_key,
        )

    assert "no active executions" in str(exc_info.value).lower()


@pytest.mark.asyncio
async def test_receive_messages_nonexistent_agent_raises_not_found(
    message_service: MessageService,
):
    """
    receive_messages() should raise ResourceNotFoundError when agent doesn't exist.

    Scenario: Query for messages for nonexistent agent.
    Expected: Raises ResourceNotFoundError.

    Handover 0730: Exception-based error handling
    """
    with pytest.raises(ResourceNotFoundError) as exc_info:
        await message_service.receive_messages(
            agent_id="nonexistent-agent-id",
            tenant_key="nonexistent-tenant",
        )

    assert "not found" in str(exc_info.value).lower()


class TestEmptyStateBoundaryConditions:
    """
    Boundary condition tests for empty state scenarios.

    Tests edge cases like:
    - Limit=0 queries
    - Empty message tables
    - Nonexistent entities
    """

    @pytest.mark.asyncio
    async def test_list_messages_limit_zero_returns_empty(
        self,
        message_service: MessageService,
        empty_project: Project,
    ):
        """
        list_messages() with limit=0 should return empty array.

        Scenario: Request zero messages.
        Expected: Returns empty list.
        """
        result = await message_service.list_messages(
            project_id=empty_project.id,
            tenant_key=empty_project.tenant_key,
            limit=0,
        )

        # Handover 0731c: Returns MessageListResult typed model
        assert isinstance(result, MessageListResult)
        assert result.messages == []

    @pytest.mark.asyncio
    async def test_get_messages_with_filters_empty_returns_empty(
        self,
        message_service: MessageService,
    ):
        """
        get_messages() with status filter should return empty when no matches.

        Scenario: Apply status filter on empty agent.
        Expected: Returns empty list.
        """
        result = await message_service.get_messages(
            agent_name="nonexistent-agent",
            status="pending",
        )

        # Handover 0731c: Returns MessageListResult typed model
        assert isinstance(result, MessageListResult)
        assert result.messages == []
