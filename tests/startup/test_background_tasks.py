"""Tests for background tasks initialization module"""
from datetime import datetime, timedelta, timezone
from unittest.mock import AsyncMock, MagicMock, patch

import pytest

from api.app import APIState


@pytest.mark.asyncio
async def test_init_background_tasks_starts_cleanup_task():
    """Should start download token cleanup task"""
    from api.startup.background_tasks import init_background_tasks

    state = APIState()
    state.db_manager = MagicMock()
    state.tenant_manager = MagicMock()

    with patch('api.startup.background_tasks.asyncio.create_task') as mock_create_task, \
         patch('api.startup.background_tasks.purge_expired_deleted_items', new_callable=AsyncMock):

        mock_cleanup_task = MagicMock()
        mock_metrics_task = MagicMock()
        mock_create_task.side_effect = [mock_cleanup_task, mock_metrics_task]

        await init_background_tasks(state)

        # Verify cleanup task was created
        assert state.cleanup_task == mock_cleanup_task
        assert mock_create_task.call_count == 2


@pytest.mark.asyncio
async def test_init_background_tasks_starts_metrics_sync_task():
    """Should start API metrics sync task"""
    from api.startup.background_tasks import init_background_tasks

    state = APIState()
    state.db_manager = MagicMock()
    state.tenant_manager = MagicMock()

    with patch('api.startup.background_tasks.asyncio.create_task') as mock_create_task, \
         patch('api.startup.background_tasks.purge_expired_deleted_items', new_callable=AsyncMock):

        mock_cleanup_task = MagicMock()
        mock_metrics_task = MagicMock()
        mock_create_task.side_effect = [mock_cleanup_task, mock_metrics_task]

        await init_background_tasks(state)

        # Verify metrics sync task was created
        assert state.metrics_sync_task == mock_metrics_task


@pytest.mark.asyncio
async def test_init_background_tasks_runs_one_time_purge():
    """Should run one-time purge of expired deleted items on startup"""
    from api.startup.background_tasks import init_background_tasks

    state = APIState()
    state.db_manager = MagicMock()
    state.tenant_manager = MagicMock()

    with patch('api.startup.background_tasks.asyncio.create_task'), \
         patch('api.startup.background_tasks.purge_expired_deleted_items', new_callable=AsyncMock) as mock_purge:

        await init_background_tasks(state)

        # Verify purge was called once on startup
        mock_purge.assert_awaited_once_with(state.db_manager, state.tenant_manager)


@pytest.mark.asyncio
async def test_cleanup_expired_download_tokens_removes_expired_tokens():
    """Cleanup task should remove expired download tokens every 15 minutes"""
    # This test verifies the internal cleanup_expired_download_tokens function behavior
    # We'll test it by importing and calling it directly
    from api.startup.background_tasks import cleanup_expired_download_tokens

    state = APIState()
    mock_db_manager = MagicMock()
    mock_session = MagicMock()
    mock_session.__aenter__ = AsyncMock(return_value=mock_session)
    mock_session.__aexit__ = AsyncMock()
    mock_db_manager.get_session_async.return_value = mock_session

    state.db_manager = mock_db_manager

    with patch('api.startup.background_tasks.TokenManager') as mock_token_manager, \
         patch('api.startup.background_tasks.asyncio.sleep', side_effect=[None, asyncio.CancelledError]):

        mock_tm_instance = MagicMock()
        mock_tm_instance.cleanup_expired_tokens = AsyncMock(return_value={"total": 5})
        mock_token_manager.return_value = mock_tm_instance

        # Run once then cancel
        import asyncio
        try:
            await cleanup_expired_download_tokens(state)
        except asyncio.CancelledError:
            pass

        # Verify TokenManager was used
        mock_token_manager.assert_called_once_with(mock_session)
        mock_tm_instance.cleanup_expired_tokens.assert_awaited_once()


@pytest.mark.asyncio
async def test_sync_api_metrics_to_db_syncs_counters():
    """Metrics sync task should sync api_call_count and mcp_call_count to database"""
    from api.startup.background_tasks import sync_api_metrics_to_db

    state = APIState()
    state.api_call_count = {"tenant1": 100, "tenant2": 50}
    state.mcp_call_count = {"tenant1": 20, "tenant2": 10}

    mock_db_manager = MagicMock()
    mock_session = MagicMock()
    mock_session.__aenter__ = AsyncMock(return_value=mock_session)
    mock_session.__aexit__ = AsyncMock()
    mock_session.execute = AsyncMock()
    mock_session.commit = AsyncMock()
    mock_db_manager.get_session_async.return_value = mock_session

    state.db_manager = mock_db_manager

    with patch('api.startup.background_tasks.asyncio.sleep', side_effect=[None, asyncio.CancelledError]):
        import asyncio
        try:
            await sync_api_metrics_to_db(state)
        except asyncio.CancelledError:
            pass

        # Verify counters were cleared after sync
        assert len(state.api_call_count) == 0
        assert len(state.mcp_call_count) == 0
        # Verify session execute was called (for insert statements)
        assert mock_session.execute.await_count >= 2


@pytest.mark.asyncio
async def test_purge_expired_deleted_items_purges_projects_and_products():
    """One-time purge should purge both expired deleted projects and products"""
    from api.startup.background_tasks import purge_expired_deleted_items

    mock_db_manager = MagicMock()
    mock_tenant_manager = MagicMock()

    mock_session = MagicMock()
    mock_session.__aenter__ = AsyncMock(return_value=mock_session)
    mock_session.__aexit__ = AsyncMock()

    # Mock database query results
    mock_project_result = MagicMock()
    mock_project_result.fetchall.return_value = [("tenant1",), ("tenant2",)]

    mock_product_result = MagicMock()
    mock_product_result.fetchall.return_value = [("tenant1",)]

    mock_session.execute = AsyncMock(side_effect=[mock_project_result, mock_product_result])
    mock_db_manager.get_session_async.return_value = mock_session

    with patch('api.startup.background_tasks.ProjectService') as mock_project_service, \
         patch('api.startup.background_tasks.ProductService') as mock_product_service:

        mock_ps_instance = MagicMock()
        mock_ps_instance.purge_expired_deleted_projects = AsyncMock(
            return_value={"success": True, "purged_count": 3}
        )
        mock_project_service.return_value = mock_ps_instance

        mock_prod_instance = MagicMock()
        mock_prod_instance.purge_expired_deleted_products = AsyncMock(
            return_value={"success": True, "purged_count": 1}
        )
        mock_product_service.return_value = mock_prod_instance

        await purge_expired_deleted_items(mock_db_manager, mock_tenant_manager)

        # Verify ProjectService was instantiated for each tenant
        assert mock_project_service.call_count == 2

        # Verify ProductService was instantiated for each unique tenant
        assert mock_product_service.call_count == 2


@pytest.mark.asyncio
async def test_purge_expired_deleted_items_handles_empty_result():
    """Purge should handle case when no expired items exist"""
    from api.startup.background_tasks import purge_expired_deleted_items

    mock_db_manager = MagicMock()
    mock_tenant_manager = MagicMock()

    mock_session = MagicMock()
    mock_session.__aenter__ = AsyncMock(return_value=mock_session)
    mock_session.__aexit__ = AsyncMock()

    # Mock empty results
    mock_project_result = MagicMock()
    mock_project_result.fetchall.return_value = []

    mock_product_result = MagicMock()
    mock_product_result.fetchall.return_value = []

    mock_session.execute = AsyncMock(side_effect=[mock_project_result, mock_product_result])
    mock_db_manager.get_session_async.return_value = mock_session

    # Should complete without calling service methods
    await purge_expired_deleted_items(mock_db_manager, mock_tenant_manager)

    # Verify no errors and function completes
    assert True  # If we reach here, test passed
