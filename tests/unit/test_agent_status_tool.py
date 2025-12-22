"""
Comprehensive tests for agent_status.py MCP tool
Target: 95%+ coverage

Tests set_agent_status tool:
- Status updates with validation
- Progress tracking
- Multi-tenant isolation
- WebSocket event broadcasting
- State machine enforcement
- Error handling
"""

import uuid
from datetime import datetime, timedelta, timezone
from unittest.mock import AsyncMock, patch

import pytest
import pytest_asyncio
from sqlalchemy import select

from src.giljo_mcp.models.agent_identity import AgentJob, AgentExecution
from tests.utils.tools_helpers import ToolsTestHelper


class TestAgentStatusTool:
    """Test class for agent status tool"""

    @pytest_asyncio.fixture(autouse=True)
    async def setup_method(self, tools_test_setup):
        """Setup for each test method"""
        self.setup = tools_test_setup
        self.db_manager = tools_test_setup["db_manager"]

        # Create test project
        async with self.db_manager.get_session_async() as session:
            self.project = await ToolsTestHelper.create_test_project(session, "Agent Status Test Project")
            self.tenant_key = self.project.tenant_key

    async def _create_test_job(self, session, status="waiting", progress=0):
        """Helper to create test agent job"""
        job = AgentExecution(
            tenant_key=self.tenant_key,
            project_id=self.project.id,
            job_id=str(uuid.uuid4()),
            agent_type="implementer",
            mission="Test mission",
            status=status,
            progress=progress,
            agent_name="test-agent",
            tool_type="claude-code",
        )
        session.add(job)
        await session.commit()
        await session.refresh(job)
        return job

    @pytest.mark.asyncio
    async def test_set_agent_status_waiting_to_working(self):
        """Test status transition from waiting to working with progress"""
        from src.giljo_mcp.tools.agent_status import set_agent_status

        # Create job in waiting status
        async with self.db_manager.get_session_async() as session:
            job = await self._create_test_job(session, status="waiting")
            job_id = job.job_id

        # Mock WebSocket manager
        with patch("src.giljo_mcp.tools.agent_status.websocket_manager") as mock_ws:
            mock_ws.broadcast_agent_status_update = AsyncMock()

            # Update status to working
            result = await set_agent_status(
                job_id=job_id,
                tenant_key=self.tenant_key,
                status="working",
                progress=25,
                current_task="Implementing feature X",
            )

        # Verify response
        assert result["success"] is True
        assert result["job_id"] == job_id
        assert result["old_status"] == "waiting"
        assert result["new_status"] == "working"
        assert "Working" in result["message"]

        # Verify database update
        async with self.db_manager.get_session_async() as session:
            stmt = select(AgentExecution).where(AgentExecution.job_id == job_id)
            updated_job = (await session.execute(stmt)).scalar_one()
            assert updated_job.status == "working"
            assert updated_job.progress == 25
            assert updated_job.current_task == "Implementing feature X"

        # Verify WebSocket broadcast
        mock_ws.broadcast_agent_status_update.assert_called_once()

    @pytest.mark.asyncio
    async def test_set_agent_status_working_requires_progress(self):
        """Test that working status requires progress parameter"""
        from src.giljo_mcp.tools.agent_status import set_agent_status

        async with self.db_manager.get_session_async() as session:
            job = await self._create_test_job(session, status="waiting")
            job_id = job.job_id

        # Try to set working without progress
        with pytest.raises(ValueError, match="progress.*required.*working"):
            await set_agent_status(job_id=job_id, tenant_key=self.tenant_key, status="working")

    @pytest.mark.asyncio
    async def test_set_agent_status_blocked_requires_reason(self):
        """Test that blocked status requires reason parameter"""
        from src.giljo_mcp.tools.agent_status import set_agent_status

        async with self.db_manager.get_session_async() as session:
            job = await self._create_test_job(session, status="working")
            job_id = job.job_id

        # Try to set blocked without reason
        with pytest.raises(ValueError, match="reason.*required.*blocked"):
            await set_agent_status(job_id=job_id, tenant_key=self.tenant_key, status="blocked")

    @pytest.mark.asyncio
    async def test_set_agent_status_failed_requires_reason(self):
        """Test that failed status requires reason parameter"""
        from src.giljo_mcp.tools.agent_status import set_agent_status

        async with self.db_manager.get_session_async() as session:
            job = await self._create_test_job(session, status="working")
            job_id = job.job_id

        # Try to set failed without reason
        with pytest.raises(ValueError, match="reason.*required.*failed"):
            await set_agent_status(job_id=job_id, tenant_key=self.tenant_key, status="failed")

    @pytest.mark.asyncio
    async def test_set_agent_status_progress_validation(self):
        """Test progress must be 0-100"""
        from src.giljo_mcp.tools.agent_status import set_agent_status

        async with self.db_manager.get_session_async() as session:
            job = await self._create_test_job(session, status="working")
            job_id = job.job_id

        # Test progress > 100
        with pytest.raises(ValueError, match="progress.*0.*100"):
            await set_agent_status(job_id=job_id, tenant_key=self.tenant_key, status="working", progress=150)

        # Test progress < 0
        with pytest.raises(ValueError, match="progress.*0.*100"):
            await set_agent_status(job_id=job_id, tenant_key=self.tenant_key, status="working", progress=-10)

    @pytest.mark.asyncio
    async def test_set_agent_status_invalid_status(self):
        """Test invalid status values are rejected"""
        from src.giljo_mcp.tools.agent_status import set_agent_status

        async with self.db_manager.get_session_async() as session:
            job = await self._create_test_job(session, status="waiting")
            job_id = job.job_id

        with pytest.raises(ValueError, match="Invalid status"):
            await set_agent_status(job_id=job_id, tenant_key=self.tenant_key, status="invalid_status")

    @pytest.mark.asyncio
    async def test_set_agent_status_terminal_state_rejection(self):
        """Test cannot transition from terminal states (complete, failed)"""
        from src.giljo_mcp.tools.agent_status import set_agent_status

        # Test from complete
        async with self.db_manager.get_session_async() as session:
            job = await self._create_test_job(session, status="complete")
            job_id = job.job_id

        with pytest.raises(ValueError, match="Cannot transition from.*complete"):
            await set_agent_status(job_id=job_id, tenant_key=self.tenant_key, status="working", progress=50)

        # Test from failed
        async with self.db_manager.get_session_async() as session:
            job2 = await self._create_test_job(session, status="failed")
            job_id2 = job2.job_id

        with pytest.raises(ValueError, match="Cannot transition from.*failed"):
            await set_agent_status(job_id=job_id2, tenant_key=self.tenant_key, status="working", progress=50)

    @pytest.mark.asyncio
    async def test_set_agent_status_job_not_found(self):
        """Test error when job doesn't exist"""
        from src.giljo_mcp.tools.agent_status import set_agent_status

        fake_job_id = str(uuid.uuid4())

        with pytest.raises(ValueError, match="Job.*not found"):
            await set_agent_status(job_id=fake_job_id, tenant_key=self.tenant_key, status="working", progress=50)

    @pytest.mark.asyncio
    async def test_set_agent_status_multi_tenant_isolation(self):
        """Test cannot update jobs from different tenant"""
        from src.giljo_mcp.tools.agent_status import set_agent_status

        # Create job for tenant A
        async with self.db_manager.get_session_async() as session:
            job = await self._create_test_job(session, status="waiting")
            job_id = job.job_id

        # Try to update from tenant B
        other_tenant = "other-tenant-" + str(uuid.uuid4())

        with pytest.raises(ValueError, match="Job.*not found"):
            await set_agent_status(job_id=job_id, tenant_key=other_tenant, status="working", progress=50)

    @pytest.mark.asyncio
    async def test_set_agent_status_complete_state(self):
        """Test transition to complete state"""
        from src.giljo_mcp.tools.agent_status import set_agent_status

        async with self.db_manager.get_session_async() as session:
            job = await self._create_test_job(session, status="review")
            job_id = job.job_id

        with patch("src.giljo_mcp.tools.agent_status.websocket_manager") as mock_ws:
            mock_ws.broadcast_agent_status_update = AsyncMock()

            result = await set_agent_status(job_id=job_id, tenant_key=self.tenant_key, status="complete")

        assert result["success"] is True
        assert result["new_status"] == "complete"

        # Verify completed_at timestamp set
        async with self.db_manager.get_session_async() as session:
            stmt = select(AgentExecution).where(AgentExecution.job_id == job_id)
            updated_job = (await session.execute(stmt)).scalar_one()
            assert updated_job.status == "complete"
            assert updated_job.completed_at is not None

    @pytest.mark.asyncio
    async def test_set_agent_status_blocked_with_reason(self):
        """Test setting blocked status with reason"""
        from src.giljo_mcp.tools.agent_status import set_agent_status

        async with self.db_manager.get_session_async() as session:
            job = await self._create_test_job(session, status="working")
            job_id = job.job_id

        with patch("src.giljo_mcp.tools.agent_status.websocket_manager") as mock_ws:
            mock_ws.broadcast_agent_status_update = AsyncMock()

            result = await set_agent_status(
                job_id=job_id,
                tenant_key=self.tenant_key,
                status="blocked",
                reason="Waiting for database migration approval",
            )

        assert result["success"] is True
        assert result["new_status"] == "blocked"

        # Verify block_reason stored
        async with self.db_manager.get_session_async() as session:
            stmt = select(AgentExecution).where(AgentExecution.job_id == job_id)
            updated_job = (await session.execute(stmt)).scalar_one()
            assert updated_job.status == "blocked"
            assert updated_job.block_reason == "Waiting for database migration approval"

    @pytest.mark.asyncio
    async def test_set_agent_status_estimated_completion(self):
        """Test setting estimated completion time"""
        from src.giljo_mcp.tools.agent_status import set_agent_status

        async with self.db_manager.get_session_async() as session:
            job = await self._create_test_job(session, status="working", progress=50)
            job_id = job.job_id

        estimated = datetime.now(timezone.utc) + timedelta(hours=2)

        with patch("src.giljo_mcp.tools.agent_status.websocket_manager") as mock_ws:
            mock_ws.broadcast_agent_status_update = AsyncMock()

            result = await set_agent_status(
                job_id=job_id, tenant_key=self.tenant_key, status="working", progress=75, estimated_completion=estimated
            )

        assert result["success"] is True

        # Verify estimated completion stored
        async with self.db_manager.get_session_async() as session:
            stmt = select(AgentExecution).where(AgentExecution.job_id == job_id)
            updated_job = (await session.execute(stmt)).scalar_one()
            assert updated_job.progress == 75
            assert updated_job.estimated_completion is not None
            # Allow 1 second tolerance
            assert abs((updated_job.estimated_completion - estimated).total_seconds()) < 1

    @pytest.mark.asyncio
    async def test_set_agent_status_all_transitions(self):
        """Test valid status transitions according to state machine"""
        from src.giljo_mcp.tools.agent_status import set_agent_status

        # Create job
        async with self.db_manager.get_session_async() as session:
            job = await self._create_test_job(session, status="waiting")
            job_id = job.job_id

        with patch("src.giljo_mcp.tools.agent_status.websocket_manager") as mock_ws:
            mock_ws.broadcast_agent_status_update = AsyncMock()

            # waiting -> preparing
            result = await set_agent_status(job_id=job_id, tenant_key=self.tenant_key, status="preparing")
            assert result["new_status"] == "preparing"

            # preparing -> working
            result = await set_agent_status(job_id=job_id, tenant_key=self.tenant_key, status="working", progress=30)
            assert result["new_status"] == "working"

            # working -> review
            result = await set_agent_status(job_id=job_id, tenant_key=self.tenant_key, status="review")
            assert result["new_status"] == "review"

            # review -> complete
            result = await set_agent_status(job_id=job_id, tenant_key=self.tenant_key, status="complete")
            assert result["new_status"] == "complete"

    @pytest.mark.asyncio
    async def test_set_agent_status_websocket_event_structure(self):
        """Test WebSocket event has correct structure"""
        from src.giljo_mcp.tools.agent_status import set_agent_status

        async with self.db_manager.get_session_async() as session:
            job = await self._create_test_job(session, status="waiting")
            job_id = job.job_id

        with patch("src.giljo_mcp.tools.agent_status.websocket_manager") as mock_ws:
            mock_ws.broadcast_agent_status_update = AsyncMock()

            await set_agent_status(
                job_id=job_id, tenant_key=self.tenant_key, status="working", progress=50, current_task="Testing feature"
            )

            # Verify WebSocket was called with correct parameters
            call_args = mock_ws.broadcast_agent_status_update.call_args
            assert call_args is not None
            kwargs = call_args.kwargs

            assert kwargs["job_id"] == job_id
            assert kwargs["tenant_key"] == self.tenant_key
            assert kwargs["old_status"] == "waiting"
            assert kwargs["new_status"] == "working"
            assert kwargs["progress"] == 50
            assert kwargs["current_task"] == "Testing feature"

    @pytest.mark.asyncio
    async def test_set_agent_status_empty_job_id(self):
        """Test validation for empty job_id"""
        from src.giljo_mcp.tools.agent_status import set_agent_status

        with pytest.raises(ValueError, match="job_id.*cannot be empty"):
            await set_agent_status(job_id="", tenant_key=self.tenant_key, status="working", progress=50)

    @pytest.mark.asyncio
    async def test_set_agent_status_empty_tenant_key(self):
        """Test validation for empty tenant_key"""
        from src.giljo_mcp.tools.agent_status import set_agent_status

        with pytest.raises(ValueError, match="tenant_key.*cannot be empty"):
            await set_agent_status(job_id="some-job-id", tenant_key="", status="working", progress=50)
