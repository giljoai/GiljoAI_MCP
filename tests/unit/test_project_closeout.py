"""
Unit tests for Project Closeout MCP Tool (Handover 0138)

TESTING STRATEGY:
- Test learning entry creation and storage
- Test sequential numbering (auto-increment)
- Test GitHub commit fetching when enabled
- Test manual summary fallback when GitHub disabled
- Test multi-tenant isolation
- Test error handling and validation
"""

import pytest
from datetime import datetime, timezone
from typing import Any, Dict
from unittest.mock import AsyncMock, MagicMock, patch
from uuid import uuid4

from giljo_mcp.models.products import Product
from giljo_mcp.models.projects import Project
from giljo_mcp.services.product_service import ProductService


def create_mock_db_session(project_mock, product_mock):
    """
    Helper function to create properly mocked async database session.

    Returns tuple of (mock_session, mock_db_manager) configured to return
    the given project and product mocks when queried.
    """
    mock_session = AsyncMock()
    mock_db_manager = MagicMock()
    mock_db_manager.get_session_async.return_value.__aenter__.return_value = mock_session

    # Mock database queries to return actual objects (not coroutines)
    call_counter = {'count': 0}

    async def mock_execute_side_effect(*args, **kwargs):
        mock_result = MagicMock()  # Use MagicMock not AsyncMock for result
        # Track which call this is (project, then product)
        if call_counter['count'] == 0:
            mock_result.scalar_one_or_none.return_value = project_mock
        else:
            mock_result.scalar_one_or_none.return_value = product_mock

        call_counter['count'] += 1
        return mock_result

    mock_session.execute.side_effect = mock_execute_side_effect
    mock_session.commit = AsyncMock()
    mock_session.refresh = AsyncMock()

    return mock_session, mock_db_manager


@pytest.fixture
def sample_product_id():
    """Sample product UUID"""
    return str(uuid4())


@pytest.fixture
def sample_project_id():
    """Sample project UUID"""
    return str(uuid4())


@pytest.fixture
def tenant_key():
    """Sample tenant key"""
    return f"tk_{uuid4().hex}"


@pytest.fixture
def mock_product(sample_product_id, tenant_key):
    """Mock Product instance with initialized product_memory"""
    product = MagicMock(spec=Product)
    product.id = sample_product_id
    product.tenant_key = tenant_key
    product.name = "Test Product"
    product.product_memory = {
        "github": {},
        "learnings": [],
        "sequential_history": [],
        "context": {}
    }
    product.updated_at = datetime.now(timezone.utc)
    return product


@pytest.fixture
def mock_project(sample_project_id, sample_product_id, tenant_key):
    """Mock Project instance"""
    project = MagicMock(spec=Project)
    project.id = sample_project_id
    project.product_id = sample_product_id
    project.tenant_key = tenant_key
    project.name = "Test Project"
    project.mission = "Test mission"
    project.status = "completed"
    project.created_at = datetime(2025, 11, 1, 10, 0, 0, tzinfo=timezone.utc)
    project.updated_at = datetime(2025, 11, 16, 10, 0, 0, tzinfo=timezone.utc)
    return project


class TestProjectCloseoutBasics:
    """Test basic project closeout functionality"""

    @pytest.mark.asyncio
    async def test_close_project_stores_learning_in_memory(
        self, mock_product, mock_project, tenant_key
    ):
        """
        BEHAVIOR: Project closeout stores rich entry in product_memory.sequential_history (and legacy learnings)

        GIVEN: A product with empty learnings array
        WHEN: close_project_and_update_memory() is called
        THEN: Learning entry is appended to product_memory.learnings with sequence number 1
        """
        from giljo_mcp.tools.project_closeout import close_project_and_update_memory

        mock_session, mock_db_manager = create_mock_db_session(mock_project, mock_product)

        # Call the tool
        result = await close_project_and_update_memory(
            project_id=str(mock_project.id),
            summary="Implemented user authentication with JWT",
            key_outcomes=["Secure token storage", "Refresh token rotation"],
            decisions_made=["Chose JWT over sessions"],
            tenant_key=tenant_key,
            db_manager=mock_db_manager,
        )

        # Assertions
        assert result["success"] is True
        assert "learning_id" in result
        assert result["sequence"] == 1

        # Verify entry was added to product_memory.learnings (legacy)
        assert len(mock_product.product_memory["learnings"]) == 1
        learning = mock_product.product_memory["learnings"][0]
        assert learning["sequence"] == 1
        assert learning["type"] == "project_closeout"
        assert learning["project_id"] == str(mock_project.id)
        assert learning["project_name"] == mock_project.name
        assert learning["summary"] == "Implemented user authentication with JWT"
        assert learning["key_outcomes"] == ["Secure token storage", "Refresh token rotation"]
        assert learning["decisions_made"] == ["Chose JWT over sessions"]
        assert "timestamp" in learning

        # Verify sequential_history rich entry mirrors learning with priority metadata
        history = mock_product.product_memory["sequential_history"]
        assert len(history) == 1
        entry = history[0]
        assert entry["priority"] == 3
        assert entry["significance_score"] == 0.5
        assert entry["sequence"] == 1
        assert entry["summary"] == learning["summary"]

    @pytest.mark.asyncio
    async def test_sequential_numbering_increments(
        self, mock_product, mock_project, tenant_key
    ):
        """
        BEHAVIOR: Sequential numbering auto-increments for each new learning entry

        GIVEN: A product with 2 existing learning entries (sequence 1, 2)
        WHEN: close_project_and_update_memory() is called
        THEN: New learning entry has sequence number 3
        """
        from giljo_mcp.tools.project_closeout import close_project_and_update_memory

        # Setup product with existing learnings
        mock_product.product_memory["learnings"] = [
            {"sequence": 1, "type": "project_closeout", "summary": "First project"},
            {"sequence": 2, "type": "project_closeout", "summary": "Second project"},
        ]

        mock_session, mock_db_manager = create_mock_db_session(mock_project, mock_product)

        result = await close_project_and_update_memory(
            project_id=str(mock_project.id),
            summary="Third project completed",
            key_outcomes=["Achievement 1"],
            decisions_made=["Decision 1"],
            tenant_key=tenant_key,
            db_manager=mock_db_manager,
        )

        # Assertions
        assert result["success"] is True
        assert result["sequence"] == 3
        assert len(mock_product.product_memory["learnings"]) == 3
        assert mock_product.product_memory["learnings"][2]["sequence"] == 3


class TestGitHubIntegration:
    """Test GitHub commit fetching functionality"""

    @pytest.mark.asyncio
    async def test_fetch_github_commits_when_enabled(
        self, mock_product, mock_project, tenant_key
    ):
        """
        BEHAVIOR: Fetches GitHub commits when integration is enabled

        GIVEN: Product has GitHub integration enabled with repo URL
        WHEN: close_project_and_update_memory() is called
        THEN: Learning entry includes git_commits array with commit data
        """
        from giljo_mcp.tools.project_closeout import close_project_and_update_memory

        # Enable GitHub integration
        mock_product.product_memory["github"] = {
            "enabled": True,
            "repo_url": "https://github.com/user/test-repo",
            "access_token": "ghp_testtoken123",
        }

        mock_session, mock_db_manager = create_mock_db_session(mock_project, mock_product)

        # Mock GitHub API response
        mock_commits = [
            {
                "sha": "abc123",
                "commit": {
                    "message": "feat: Add authentication",
                    "author": {
                        "name": "Dev User",
                        "email": "dev@example.com",
                        "date": "2025-11-15T10:00:00Z"
                    }
                }
            }
        ]

        with patch("giljo_mcp.tools.project_closeout.fetch_github_commits", return_value=mock_commits):
            result = await close_project_and_update_memory(
                project_id=str(mock_project.id),
                summary="Completed authentication feature",
                key_outcomes=["JWT implemented"],
                decisions_made=["Used JWT"],
                tenant_key=tenant_key,
                db_manager=mock_db_manager,
            )

        # Assertions
        assert result["success"] is True
        learning = mock_product.product_memory["learnings"][0]
        assert "git_commits" in learning
        assert len(learning["git_commits"]) == 1
        assert learning["git_commits"][0]["sha"] == "abc123"
        assert learning["git_commits"][0]["message"] == "feat: Add authentication"

    @pytest.mark.asyncio
    async def test_manual_summary_when_github_disabled(
        self, mock_product, mock_project, tenant_key
    ):
        """
        BEHAVIOR: Uses manual summary when GitHub integration is disabled

        GIVEN: Product has GitHub integration disabled
        WHEN: close_project_and_update_memory() is called
        THEN: Learning entry has empty git_commits array and uses manual summary
        """
        from giljo_mcp.tools.project_closeout import close_project_and_update_memory

        # GitHub integration disabled (default state)
        assert mock_product.product_memory["github"] == {}

        mock_session, mock_db_manager = create_mock_db_session(mock_project, mock_product)

        result = await close_project_and_update_memory(
            project_id=str(mock_project.id),
            summary="Manual summary of project work",
            key_outcomes=["Manual outcome"],
            decisions_made=["Manual decision"],
            tenant_key=tenant_key,
            db_manager=mock_db_manager,
        )

        # Assertions
        assert result["success"] is True
        learning = mock_product.product_memory["learnings"][0]
        assert "git_commits" in learning
        assert learning["git_commits"] == []  # Empty when GitHub disabled
        assert learning["summary"] == "Manual summary of project work"


class TestValidationAndErrors:
    """Test input validation and error handling"""

    @pytest.mark.asyncio
    async def test_missing_project_id_fails(self, tenant_key):
        """
        BEHAVIOR: Fails when project_id is missing

        GIVEN: No project_id provided
        WHEN: close_project_and_update_memory() is called
        THEN: Returns error with descriptive message
        """
        from giljo_mcp.tools.project_closeout import close_project_and_update_memory

        mock_db_manager = MagicMock()

        result = await close_project_and_update_memory(
            project_id="",
            summary="Test summary",
            key_outcomes=[],
            decisions_made=[],
            tenant_key=tenant_key,
            db_manager=mock_db_manager,
        )

        assert result["success"] is False
        assert "error" in result
        assert "project_id" in result["error"].lower()

    @pytest.mark.asyncio
    async def test_missing_summary_fails(self, sample_project_id, tenant_key):
        """
        BEHAVIOR: Fails when summary is missing

        GIVEN: Empty summary string
        WHEN: close_project_and_update_memory() is called
        THEN: Returns error with descriptive message
        """
        from giljo_mcp.tools.project_closeout import close_project_and_update_memory

        mock_db_manager = MagicMock()

        result = await close_project_and_update_memory(
            project_id=sample_project_id,
            summary="",
            key_outcomes=[],
            decisions_made=[],
            tenant_key=tenant_key,
            db_manager=mock_db_manager,
        )

        assert result["success"] is False
        assert "error" in result
        assert "summary" in result["error"].lower()

    @pytest.mark.asyncio
    async def test_project_not_found_fails(self, sample_project_id, tenant_key):
        """
        BEHAVIOR: Fails when project doesn't exist

        GIVEN: Invalid project_id
        WHEN: close_project_and_update_memory() is called
        THEN: Returns error with descriptive message
        """
        from giljo_mcp.tools.project_closeout import close_project_and_update_memory

        mock_session = AsyncMock()
        mock_db_manager = MagicMock()
        mock_db_manager.get_session_async.return_value.__aenter__.return_value = mock_session

        # Project not found
        mock_session.execute.return_value.scalar_one_or_none.return_value = None

        result = await close_project_and_update_memory(
            project_id=sample_project_id,
            summary="Test summary",
            key_outcomes=[],
            decisions_made=[],
            tenant_key=tenant_key,
            db_manager=mock_db_manager,
        )

        assert result["success"] is False
        assert "error" in result
        assert "not found" in result["error"].lower()


class TestMultiTenantIsolation:
    """Test multi-tenant data isolation"""

    @pytest.mark.asyncio
    async def test_tenant_isolation_enforced(
        self, mock_product, mock_project, tenant_key
    ):
        """
        BEHAVIOR: Enforces tenant isolation for projects and products

        GIVEN: Project belongs to tenant A
        WHEN: close_project_and_update_memory() is called with tenant B key
        THEN: Operation fails with authorization error
        """
        from giljo_mcp.tools.project_closeout import close_project_and_update_memory

        different_tenant = f"tk_{uuid4().hex}"

        mock_session = AsyncMock()
        mock_db_manager = MagicMock()
        mock_db_manager.get_session_async.return_value.__aenter__.return_value = mock_session

        # Return project but with different tenant
        mock_project.tenant_key = tenant_key
        mock_session.execute.return_value.scalar_one_or_none.return_value = mock_project

        result = await close_project_and_update_memory(
            project_id=str(mock_project.id),
            summary="Test summary",
            key_outcomes=[],
            decisions_made=[],
            tenant_key=different_tenant,  # Different tenant
            db_manager=mock_db_manager,
        )

        assert result["success"] is False
        assert "error" in result
        assert "tenant" in result["error"].lower() or "authorization" in result["error"].lower()


class TestWebSocketEvents:
    """Test WebSocket event emission"""

    @pytest.mark.asyncio
    async def test_emits_websocket_event_on_success(
        self, mock_product, mock_project, tenant_key
    ):
        """
        BEHAVIOR: Emits WebSocket event when memory is updated

        GIVEN: Successful project closeout
        WHEN: Learning is added to product_memory
        THEN: WebSocket event is emitted for real-time UI updates
        """
        from giljo_mcp.tools.project_closeout import close_project_and_update_memory

        mock_session, mock_db_manager = create_mock_db_session(mock_project, mock_product)

        with patch("giljo_mcp.tools.project_closeout.emit_websocket_event") as mock_emit:
            result = await close_project_and_update_memory(
                project_id=str(mock_project.id),
                summary="Test summary",
                key_outcomes=["Outcome 1"],
                decisions_made=["Decision 1"],
                tenant_key=tenant_key,
                db_manager=mock_db_manager,
            )

            # Assertions
            assert result["success"] is True
            mock_emit.assert_called_once()
            call_args = mock_emit.call_args[1]
            assert call_args["event_type"] == "product_memory_updated"
            assert call_args["product_id"] == str(mock_product.id)
