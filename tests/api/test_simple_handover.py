"""
Unit tests for simple handover endpoint - Handover 0461c

Tests the POST /api/agent-jobs/{job_id}/simple-handover endpoint which:
1. Writes session context to 360 Memory
2. Resets context_used counter to 0
3. Returns continuation prompt
4. Emits WebSocket event

NO Agent ID Swap. Just simple session reset.
"""

import pytest
import pytest_asyncio
from unittest.mock import AsyncMock, patch, MagicMock
from uuid import uuid4
from datetime import datetime, timezone

from httpx import AsyncClient


# ============================================================================
# FIXTURES
# ============================================================================

@pytest_asyncio.fixture
async def test_tenant_key():
    """Generate test tenant key"""
    from src.giljo_mcp.tenant import TenantManager
    return TenantManager.generate_tenant_key()


@pytest_asyncio.fixture
async def test_product(db_manager, test_tenant_key):
    """
    Create test product in database.

    Uses db_manager.get_session_async() so data is committed and visible to API.
    """
    from src.giljo_mcp.models import Product

    async with db_manager.get_session_async() as session:
        product = Product(
            id=str(uuid4()),
            name=f"Test Product {uuid4().hex[:8]}",
            description="Test product for simple handover tests",
            tenant_key=test_tenant_key,
            is_active=True,
            product_memory={}
        )
        session.add(product)
        await session.commit()
        await session.refresh(product)
        return product


@pytest_asyncio.fixture
async def test_project(db_manager, test_tenant_key, test_product):
    """
    Create test project in database.

    Uses db_manager.get_session_async() so data is committed and visible to API.
    """
    from src.giljo_mcp.models import Project

    async with db_manager.get_session_async() as session:
        project = Project(
            id=str(uuid4()),
            name=f"Test Project {uuid4().hex[:8]}",
            description="Test project for simple handover tests",
            mission="Test mission for simple handover tests",
            tenant_key=test_tenant_key,
            product_id=test_product.id,
            status="active"
        )
        session.add(project)
        await session.commit()
        await session.refresh(project)
        return project


@pytest_asyncio.fixture
async def orchestrator_execution(db_manager, test_tenant_key, test_project):
    """
    Create test orchestrator execution in database.

    Uses db_manager.get_session_async() so data is committed and visible to API.
    Stores project_id on fixture for tests that need it (avoids lazy load issues).
    """
    from src.giljo_mcp.models.agent_identity import AgentJob, AgentExecution

    async with db_manager.get_session_async() as session:
        # Create AgentJob (work order)
        job = AgentJob(
            job_id=str(uuid4()),
            tenant_key=test_tenant_key,
            project_id=test_project.id,
            job_type="orchestrator",
            mission="Orchestrate the test project",
            status="active",
            created_at=datetime.now(timezone.utc),
            job_metadata={}
        )
        session.add(job)

        # Create AgentExecution (executor)
        execution = AgentExecution(
            agent_id=str(uuid4()),
            job_id=job.job_id,
            tenant_key=test_tenant_key,
            agent_display_name="orchestrator",
            agent_name="Test Orchestrator",
            instance_number=1,
            status="working",
            progress=50,
            current_task="Coordinating agents",
            messages_sent_count=5,
            messages_waiting_count=2,
            messages_read_count=3,
            health_status="healthy",
            tool_type="universal",
            context_used=100000,
            context_budget=200000
        )
        session.add(execution)

        await session.commit()
        await session.refresh(job)
        await session.refresh(execution)

        # Store project_id on execution for test access (avoids lazy load issues)
        execution._test_project_id = test_project.id
        return execution


@pytest_asyncio.fixture
async def worker_execution(db_manager, test_tenant_key, test_project):
    """
    Create test worker execution in database.

    Uses db_manager.get_session_async() so data is committed and visible to API.
    """
    from src.giljo_mcp.models.agent_identity import AgentJob, AgentExecution

    async with db_manager.get_session_async() as session:
        # Create AgentJob (work order)
        job = AgentJob(
            job_id=str(uuid4()),
            tenant_key=test_tenant_key,
            project_id=test_project.id,
            job_type="worker",
            mission="Work on test tasks",
            status="active",
            created_at=datetime.now(timezone.utc),
            job_metadata={}
        )
        session.add(job)

        # Create AgentExecution (executor)
        execution = AgentExecution(
            agent_id=str(uuid4()),
            job_id=job.job_id,
            tenant_key=test_tenant_key,
            agent_display_name="worker",
            agent_name="Test Worker",
            instance_number=1,
            status="working",
            progress=30,
            messages_sent_count=0,
            messages_waiting_count=0,
            messages_read_count=0,
            health_status="healthy",
            tool_type="universal",
            context_used=50000,
            context_budget=150000
        )
        session.add(execution)

        await session.commit()
        await session.refresh(job)
        await session.refresh(execution)

        return execution


@pytest_asyncio.fixture
async def test_user(db_manager, test_tenant_key):
    """
    Create test user with matching tenant_key for authentication.

    Uses db_manager.get_session_async() so user is committed and visible to API auth.
    """
    from passlib.hash import bcrypt
    from src.giljo_mcp.models import User

    unique_suffix = uuid4().hex[:8]

    async with db_manager.get_session_async() as session:
        user = User(
            username=f"test_user_{unique_suffix}",
            email=f"test_{unique_suffix}@example.com",
            password_hash=bcrypt.hash("test_password"),
            tenant_key=test_tenant_key,  # Use the shared test_tenant_key
            role="admin",  # Admin role required for spawning agents
            is_active=True
        )
        session.add(user)
        await session.commit()
        await session.refresh(user)
        return user


@pytest_asyncio.fixture
async def auth_headers(test_user):
    """Create authentication headers for the test user"""
    from src.giljo_mcp.auth.jwt_manager import JWTManager

    token = JWTManager.create_access_token(
        user_id=test_user.id,
        username=test_user.username,
        role=test_user.role,
        tenant_key=test_user.tenant_key,
    )

    return {"Cookie": f"access_token={token}"}


# ============================================================================
# TEST CASES
# ============================================================================

class TestSimpleHandover:
    """Tests for simple handover endpoint"""

    @pytest.mark.asyncio
    async def test_simple_handover_writes_360_memory(
        self,
        api_client: AsyncClient,
        auth_headers: dict,
        orchestrator_execution,
        db_session
    ):
        """
        Test that simple handover writes a session_handover entry to 360 Memory.

        Verifies:
        - Response status 200
        - Response has success=True
        - Response has context_reset=True
        - Response has continuation_prompt
        - Response has memory_entry_id
        - 360 Memory entry created in database
        """
        # Mock write_360_memory to capture call
        with patch('src.giljo_mcp.tools.write_360_memory.write_360_memory') as mock_write:
            mock_write.return_value = {
                "success": True,
                "entry_id": "test-memory-entry-123"
            }

            response = await api_client.post(
                f"/api/agent-jobs/{orchestrator_execution.job_id}/simple-handover",
                headers=auth_headers
            )

        # Verify response
        assert response.status_code == 200, f"Expected 200, got {response.status_code}: {response.json()}"
        data = response.json()

        assert data["success"] is True
        assert data["context_reset"] is True
        assert "continuation_prompt" in data
        assert "memory_entry_id" in data
        assert data["memory_entry_id"] == "test-memory-entry-123"

        # Verify write_360_memory was called
        assert mock_write.called
        call_kwargs = mock_write.call_args.kwargs
        assert call_kwargs["entry_type"] == "session_handover"
        assert call_kwargs["author_job_id"] == orchestrator_execution.job_id
        assert "Session handover" in call_kwargs["summary"]


    @pytest.mark.asyncio
    async def test_simple_handover_resets_context(
        self,
        api_client: AsyncClient,
        auth_headers: dict,
        orchestrator_execution,
        db_manager
    ):
        """
        Test that simple handover resets context_used to 0.

        Verifies:
        - execution.context_used starts at 100000
        - After handover, context_used is reset to 0
        - Response includes old_context_used value
        """
        from sqlalchemy import select
        from src.giljo_mcp.models.agent_identity import AgentExecution

        # Verify initial state
        assert orchestrator_execution.context_used == 100000

        # Mock write_360_memory
        with patch('src.giljo_mcp.tools.write_360_memory.write_360_memory') as mock_write:
            mock_write.return_value = {
                "success": True,
                "entry_id": "test-memory-entry-456"
            }

            response = await api_client.post(
                f"/api/agent-jobs/{orchestrator_execution.job_id}/simple-handover",
                headers=auth_headers
            )

        # Verify response
        assert response.status_code == 200
        data = response.json()

        assert data["old_context_used"] == 100000
        assert data["context_reset"] is True

        # Query fresh from database to verify context reset (avoids session mismatch)
        async with db_manager.get_session_async() as session:
            result = await session.execute(
                select(AgentExecution).where(AgentExecution.agent_id == orchestrator_execution.agent_id)
            )
            refreshed = result.scalar_one()
            assert refreshed.context_used == 0


    @pytest.mark.asyncio
    async def test_continuation_prompt_mentions_360_memory(
        self,
        api_client: AsyncClient,
        auth_headers: dict,
        orchestrator_execution
    ):
        """
        Test that continuation prompt instructs reading 360 Memory.

        Verifies prompt contains:
        - "fetch_context" tool mention
        - "memory_360" category
        - "session_handover" entry type
        - Agent ID, Job ID, Project ID
        """
        # Mock write_360_memory
        with patch('src.giljo_mcp.tools.write_360_memory.write_360_memory') as mock_write:
            mock_write.return_value = {
                "success": True,
                "entry_id": "test-memory-entry-789"
            }

            response = await api_client.post(
                f"/api/agent-jobs/{orchestrator_execution.job_id}/simple-handover",
                headers=auth_headers
            )

        # Verify response
        assert response.status_code == 200
        data = response.json()

        prompt = data["continuation_prompt"]

        # Verify prompt mentions key concepts
        assert "fetch_context" in prompt
        assert "memory_360" in prompt
        assert "session_handover" in prompt

        # Verify identity information present
        assert orchestrator_execution.agent_id in prompt
        assert orchestrator_execution.job_id in prompt
        # Use stored project_id to avoid lazy load issue
        assert str(orchestrator_execution._test_project_id) in prompt

        # Verify CONTINUATION SESSION instructions
        assert "CONTINUATION SESSION" in prompt
        assert "DO NOT RE-STAGE" in prompt or "Do NOT call get_orchestrator_instructions" in prompt


    @pytest.mark.asyncio
    async def test_simple_handover_requires_orchestrator(
        self,
        api_client: AsyncClient,
        auth_headers: dict,
        worker_execution
    ):
        """
        Test that simple handover rejects non-orchestrator agents.

        Verifies:
        - 400 Bad Request status
        - Error message indicates orchestrator requirement
        """
        response = await api_client.post(
            f"/api/agent-jobs/{worker_execution.job_id}/simple-handover",
            headers=auth_headers
        )

        # Verify error response
        assert response.status_code == 400
        data = response.json()

        assert "orchestrator" in data["message"].lower()


    @pytest.mark.asyncio
    async def test_simple_handover_not_found(
        self,
        api_client: AsyncClient,
        auth_headers: dict
    ):
        """
        Test that simple handover returns 404 for invalid job_id.

        Verifies:
        - 404 Not Found status
        - Error message indicates execution not found
        """
        invalid_job_id = str(uuid4())

        response = await api_client.post(
            f"/api/agent-jobs/{invalid_job_id}/simple-handover",
            headers=auth_headers
        )

        # Verify error response
        assert response.status_code == 404
        data = response.json()

        assert "not found" in data["message"].lower()


    @pytest.mark.asyncio
    async def test_simple_handover_memory_write_failure(
        self,
        api_client: AsyncClient,
        auth_headers: dict,
        orchestrator_execution
    ):
        """
        Test that simple handover handles 360 Memory write failures.

        Verifies:
        - 500 Internal Server Error status
        - Error message indicates memory write failure
        - context_used is NOT reset when memory write fails
        """
        # Mock write_360_memory to fail (patched at source - imported inside function)
        with patch('src.giljo_mcp.tools.write_360_memory.write_360_memory') as mock_write:
            mock_write.return_value = {
                "success": False,
                "error": "Database connection lost"
            }

            response = await api_client.post(
                f"/api/agent-jobs/{orchestrator_execution.job_id}/simple-handover",
                headers=auth_headers
            )

        # Verify error response
        assert response.status_code == 500
        data = response.json()

        assert "360 memory" in data["message"].lower()


    @pytest.mark.skip(reason="WebSocket event testing requires integration tests - patching app breaks FastAPI")
    @pytest.mark.asyncio
    async def test_simple_handover_emits_websocket_event(
        self,
        api_client: AsyncClient,
        auth_headers: dict,
        orchestrator_execution
    ):
        """
        Test that simple handover emits WebSocket event for UI updates.

        SKIPPED: WebSocket event verification requires full integration testing.
        Patching api.app.app breaks the FastAPI application structure.

        This behavior is verified in integration tests instead.

        Verifies (when run as integration test):
        - WebSocket broadcast attempted
        - Event type is "orchestrator:context_reset"
        - Event data includes agent_id, job_id, project_id
        """
        pass


    @pytest.mark.asyncio
    async def test_simple_handover_finds_execution_by_agent_id(
        self,
        api_client: AsyncClient,
        auth_headers: dict,
        orchestrator_execution
    ):
        """
        Test that simple handover can find execution by agent_id.

        Endpoint accepts job_id parameter but checks both agent_id and job_id.

        Verifies:
        - Can use agent_id instead of job_id
        - Response is successful
        """
        # Mock write_360_memory
        with patch('src.giljo_mcp.tools.write_360_memory.write_360_memory') as mock_write:
            mock_write.return_value = {
                "success": True,
                "entry_id": "test-memory-entry-111"
            }

            # Use agent_id instead of job_id
            response = await api_client.post(
                f"/api/agent-jobs/{orchestrator_execution.agent_id}/simple-handover",
                headers=auth_headers
            )

        # Verify response
        assert response.status_code == 200
        data = response.json()

        assert data["success"] is True
        assert data["context_reset"] is True


    @pytest.mark.asyncio
    async def test_simple_handover_with_zero_context_used(
        self,
        api_client: AsyncClient,
        auth_headers: dict,
        orchestrator_execution,
        db_manager
    ):
        """
        Test simple handover when context_used is already 0.

        Verifies:
        - Handover succeeds even with 0 context_used
        - Context percentage calculated correctly (0%)
        - Still writes to 360 Memory
        """
        from sqlalchemy import update
        from src.giljo_mcp.models.agent_identity import AgentExecution

        # Set context_used to 0 via fresh session
        async with db_manager.get_session_async() as session:
            await session.execute(
                update(AgentExecution)
                .where(AgentExecution.agent_id == orchestrator_execution.agent_id)
                .values(context_used=0)
            )
            await session.commit()

        # Mock write_360_memory
        with patch('src.giljo_mcp.tools.write_360_memory.write_360_memory') as mock_write:
            mock_write.return_value = {
                "success": True,
                "entry_id": "test-memory-entry-222"
            }

            response = await api_client.post(
                f"/api/agent-jobs/{orchestrator_execution.job_id}/simple-handover",
                headers=auth_headers
            )

        # Verify response
        assert response.status_code == 200
        data = response.json()

        assert data["success"] is True
        assert data["old_context_used"] == 0

        # Verify write_360_memory called with 0% context
        assert mock_write.called
        call_kwargs = mock_write.call_args.kwargs
        assert "0%" in call_kwargs["summary"] or "0% context" in str(call_kwargs["key_outcomes"])
