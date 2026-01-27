"""
Unit tests for MessageService empty state handling.

Tests that MessageService methods gracefully handle scenarios where:
- No projects exist
- No agent executions exist
- Database is empty (fresh install)

Critical behaviors:
1. list_messages() returns empty list when no project exists
2. broadcast() handles gracefully when no agents to broadcast to
3. No exceptions thrown on empty database queries
4. Proper empty result structures returned

Handover Reference: Empty state API resilience - service layer
"""

import pytest
from unittest.mock import AsyncMock, MagicMock, patch
from sqlalchemy.ext.asyncio import AsyncSession

from src.giljo_mcp.services.message_service import MessageService


def _create_empty_query_result():
    """
    Helper to create a properly mocked empty query result.

    SQLAlchemy async query chain:
    - session.execute() is async, returns a result object
    - result.scalars() is sync, returns scalars object
    - scalars.all() is sync, returns list
    """
    mock_scalars = MagicMock()
    mock_scalars.all.return_value = []

    # Result object is NOT async - execute() is what's async
    mock_result = MagicMock()
    mock_result.scalars.return_value = mock_scalars

    return mock_result


def _create_service_with_empty_db():
    """
    Helper to create MessageService with mocked empty database.

    Returns tuple of (service, mock_session, mock_db_manager, mock_tenant_manager)
    """
    # Create async mock session
    mock_session = AsyncMock(spec=AsyncSession)

    # Mock execute() to return a MagicMock result (not AsyncMock)
    # execute() itself is async, but its return value is not
    mock_result = _create_empty_query_result()
    mock_session.execute = AsyncMock(return_value=mock_result)

    mock_db_manager = MagicMock()
    mock_tenant_manager = MagicMock()

    service = MessageService(
        db_manager=mock_db_manager,
        tenant_manager=mock_tenant_manager,
        test_session=mock_session
    )

    return service, mock_session, mock_db_manager, mock_tenant_manager


@pytest.mark.asyncio
async def test_list_messages_no_project_returns_empty():
    """
    list_messages() should return empty array when no project exists.

    Scenario: Fresh install, user has no projects yet.
    Expected: Returns [] without throwing exceptions.
    """
    # Create service with empty database
    service, _, _, _ = _create_service_with_empty_db()

    # Call list_messages
    messages = await service.list_messages(
        project_id="nonexistent-project-id",
        agent_id=None,
        status=None,
        limit=10
    )

    # Verify empty array returned
    assert messages == [], "Expected empty array when no messages exist"
    assert isinstance(messages, list), "Expected list type"


@pytest.mark.asyncio
async def test_list_messages_empty_database_returns_empty():
    """
    list_messages() should handle completely empty database.

    Scenario: Fresh install with zero data in any table.
    Expected: Returns [] without database errors.
    """
    # Create service with empty database
    service, _, _, _ = _create_service_with_empty_db()

    # Call without project_id (query all)
    messages = await service.list_messages()

    # Verify empty result
    assert messages == []
    assert isinstance(messages, list)


@pytest.mark.asyncio
async def test_broadcast_no_project_returns_graceful():
    """
    broadcast() should handle gracefully when no agents exist to broadcast to.

    Scenario: User tries to broadcast but no agents are running.
    Expected: Returns success=False or empty result, no exceptions.
    """
    # Mock session
    mock_session = AsyncMock(spec=AsyncSession)

    # Mock query result - no agent executions found
    mock_result = MagicMock()
    mock_result.scalars.return_value.all.return_value = []
    mock_session.execute.return_value = mock_result

    # Mock db_manager and tenant_manager
    mock_db_manager = MagicMock()
    mock_tenant_manager = MagicMock()

    # Create service with test_session
    service = MessageService(
        db_manager=mock_db_manager,
        tenant_manager=mock_tenant_manager,
        test_session=mock_session
    )

    # Attempt broadcast with no agents
    result = await service.send_message(
        from_agent="orchestrator",
        to_agents=["all"],  # Broadcast to all
        content="Test broadcast",
        project_id="test-project-id",
        message_type="broadcast"
    )

    # Verify graceful handling
    # Result should indicate no recipients or return empty result
    # (exact structure depends on implementation)
    assert result is not None, "Expected non-None result"

    # Common patterns:
    # 1. {"success": False, "message": "No recipients"}
    # 2. {"messages_sent": 0, "recipients": []}
    # 3. [] (empty array of sent messages)
    if isinstance(result, dict):
        # If dict, check for indicators of zero recipients
        assert (
            result.get("success") is False or
            result.get("messages_sent") == 0 or
            result.get("recipients") == [] or
            len(result.get("messages", [])) == 0
        ), f"Expected empty/zero result, got {result}"
    elif isinstance(result, list):
        assert result == [], f"Expected empty list, got {result}"


@pytest.mark.asyncio
async def test_get_message_by_id_nonexistent_returns_none():
    """
    get_message_by_id() should return None when message doesn't exist.

    Scenario: Query for message that doesn't exist in empty database.
    Expected: Returns None, no exceptions.
    """
    # Mock session
    mock_session = AsyncMock(spec=AsyncSession)

    # Mock query result - no message found
    mock_result = MagicMock()
    mock_result.scalar_one_or_none.return_value = None
    mock_session.execute.return_value = mock_result

    # Mock db_manager and tenant_manager
    mock_db_manager = MagicMock()
    mock_tenant_manager = MagicMock()

    # Create service with test_session
    service = MessageService(
        db_manager=mock_db_manager,
        tenant_manager=mock_tenant_manager,
        test_session=mock_session
    )

    # Query nonexistent message
    message = await service.get_message_by_id("nonexistent-message-id")

    # Verify None returned
    assert message is None, "Expected None for nonexistent message"


@pytest.mark.asyncio
async def test_list_messages_with_filters_empty_returns_empty():
    """
    list_messages() with filters should return empty array when no matches.

    Scenario: Apply filters (status, agent_id) on empty database.
    Expected: Returns [] without errors.
    """
    # Mock session
    mock_session = AsyncMock(spec=AsyncSession)

    # Mock empty result
    mock_result = MagicMock()
    mock_result.scalars.return_value.all.return_value = []
    mock_session.execute.return_value = mock_result

    # Mock db_manager and tenant_manager
    mock_db_manager = MagicMock()
    mock_tenant_manager = MagicMock()

    # Create service with test_session
    service = MessageService(
        db_manager=mock_db_manager,
        tenant_manager=mock_tenant_manager,
        test_session=mock_session
    )

    # Apply multiple filters on empty database
    messages = await service.list_messages(
        project_id="test-project",
        agent_id="test-agent",
        status="pending",
        limit=10
    )

    # Verify empty result
    assert messages == []
    assert isinstance(messages, list)


@pytest.mark.asyncio
async def test_count_messages_empty_database_returns_zero():
    """
    count_messages() should return 0 when database is empty.

    Scenario: Count messages in empty database.
    Expected: Returns 0, no exceptions.
    """
    # Mock session
    mock_session = AsyncMock(spec=AsyncSession)

    # Mock count result
    mock_result = MagicMock()
    mock_result.scalar.return_value = 0
    mock_session.execute.return_value = mock_result

    # Mock db_manager and tenant_manager
    mock_db_manager = MagicMock()
    mock_tenant_manager = MagicMock()

    # Create service with test_session
    service = MessageService(
        db_manager=mock_db_manager,
        tenant_manager=mock_tenant_manager,
        test_session=mock_session
    )

    # Count messages
    count = await service.count_messages(
        project_id="test-project",
        status="pending"
    )

    # Verify zero count
    assert count == 0, "Expected count of 0 for empty database"
    assert isinstance(count, int), "Expected integer count"


class TestEmptyStateBoundaryConditions:
    """
    Boundary condition tests for empty state scenarios.

    Tests edge cases like:
    - Pagination with skip > 0 on empty database
    - Complex filters on empty database
    - Aggregation queries on empty database
    """

    @pytest.mark.asyncio
    async def test_list_messages_pagination_skip_on_empty(self):
        """
        list_messages() with skip > 0 should handle empty database.

        Scenario: Request page 2 when no data exists.
        Expected: Returns [], no index errors.
        """
        # Create service with empty database
        service, _, _, _ = _create_service_with_empty_db()

        # Request page 2 (skip=10) on empty database
        messages = await service.list_messages(
            skip=10,
            limit=10
        )

        assert messages == []


    @pytest.mark.asyncio
    async def test_aggregate_stats_empty_database_returns_zeros(self):
        """
        Message statistics/aggregation should return zero counts on empty database.

        Scenario: Request message counts by status when no messages exist.
        Expected: Returns all zeros, no errors.
        """
        # Create service with empty database
        service, mock_session, _, _ = _create_service_with_empty_db()

        # Mock aggregation result for stats query
        mock_result = AsyncMock()
        mock_result.all.return_value = []  # No rows returned
        mock_session.execute.return_value = mock_result

        # Get message counts by status
        stats = await service.get_message_stats(project_id="test-project")

        # Verify zero stats
        # (exact structure depends on implementation)
        if isinstance(stats, dict):
            assert all(v == 0 for v in stats.values() if isinstance(v, (int, float)))
        elif isinstance(stats, list):
            assert stats == []


    @pytest.mark.asyncio
    async def test_delete_messages_empty_database_no_error(self):
        """
        delete_messages() should succeed silently when no messages exist.

        Scenario: Attempt to delete messages from empty database.
        Expected: Returns success (0 deleted), no errors.
        """
        # Create service with empty database
        service, mock_session, _, _ = _create_service_with_empty_db()

        # Mock delete result - zero rows affected
        mock_result = AsyncMock()
        mock_result.rowcount = 0
        mock_session.execute.return_value = mock_result
        mock_session.commit = AsyncMock()

        # Attempt to delete nonexistent messages
        deleted_count = await service.delete_messages(
            project_id="test-project",
            status="read"
        )

        # Verify zero deleted, no errors
        assert deleted_count == 0
        assert isinstance(deleted_count, int)
