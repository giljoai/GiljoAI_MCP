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

from datetime import datetime, timezone
from unittest.mock import AsyncMock, MagicMock, patch
from uuid import uuid4

import pytest

from src.giljo_mcp.models.products import Product
from src.giljo_mcp.models.projects import Project


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
    call_counter = {"count": 0}

    async def mock_execute_side_effect(*args, **kwargs):
        mock_result = MagicMock()  # Use MagicMock not AsyncMock for result
        # Track which call this is (project, then product)
        if call_counter["count"] == 0:
            mock_result.scalar_one_or_none.return_value = project_mock
        else:
            mock_result.scalar_one_or_none.return_value = product_mock

        call_counter["count"] += 1
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
    product.product_memory = {"github": {}, "learnings": [], "sequential_history": [], "context": {}}
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
    async def test_close_project_stores_learning_in_memory(self, mock_product, mock_project, tenant_key):
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
    async def test_sequential_numbering_increments(self, mock_product, mock_project, tenant_key):
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
    async def test_fetch_github_commits_when_enabled(self, mock_product, mock_project, tenant_key):
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
                    "author": {"name": "Dev User", "email": "dev@example.com", "date": "2025-11-15T10:00:00Z"},
                },
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
    async def test_manual_summary_when_github_disabled(self, mock_product, mock_project, tenant_key):
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
    async def test_tenant_isolation_enforced(self, mock_product, mock_project, tenant_key):
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
    async def test_emits_websocket_event_on_success(self, mock_product, mock_project, tenant_key):
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


class TestErrorHandlingAndEdgeCases:
    """Test error handling paths and edge cases for coverage"""

    @pytest.mark.asyncio
    async def test_github_api_failure_doesnt_block_closeout(self, mock_product, mock_project, tenant_key):
        """
        BEHAVIOR: GitHub API failure should not prevent closeout

        GIVEN: GitHub integration enabled but API fails
        WHEN: close_project_and_update_memory() is called
        THEN: Closeout succeeds with empty git_commits array
        """
        from giljo_mcp.tools.project_closeout import close_project_and_update_memory

        # Enable GitHub integration
        mock_product.product_memory["github"] = {
            "enabled": True,
            "repo_url": "https://github.com/user/test-repo",
            "access_token": "ghp_testtoken123",
        }

        mock_session, mock_db_manager = create_mock_db_session(mock_project, mock_product)

        # Mock fetch_github_commits to raise exception
        with patch("giljo_mcp.tools.project_closeout.fetch_github_commits") as mock_fetch:
            mock_fetch.side_effect = Exception("GitHub API Error")

            result = await close_project_and_update_memory(
                project_id=str(mock_project.id),
                summary="Test summary",
                key_outcomes=["Outcome 1"],
                decisions_made=["Decision 1"],
                tenant_key=tenant_key,
                db_manager=mock_db_manager,
            )

            # Should succeed despite GitHub error
            assert result["success"] is True

            # Verify product was updated
            memory = mock_product.product_memory
            assert len(memory["sequential_history"]) == 1
            assert memory["sequential_history"][0]["git_commits"] == []  # Empty due to error

    @pytest.mark.asyncio
    async def test_database_error_rolls_back_transaction(self, mock_product, mock_project, tenant_key):
        """
        BEHAVIOR: Database error should rollback entire transaction

        GIVEN: Database commit fails
        WHEN: close_project_and_update_memory() is called
        THEN: Returns error result
        """
        from giljo_mcp.tools.project_closeout import close_project_and_update_memory

        mock_session, mock_db_manager = create_mock_db_session(mock_project, mock_product)

        # Mock session to fail during commit
        mock_session.commit.side_effect = Exception("DB Error")

        result = await close_project_and_update_memory(
            project_id=str(mock_project.id),
            summary="Test summary",
            key_outcomes=["Outcome 1"],
            decisions_made=["Decision 1"],
            tenant_key=tenant_key,
            db_manager=mock_db_manager,
        )

        # Should fail
        assert result["success"] is False
        assert "error" in result

    @pytest.mark.asyncio
    async def test_closeout_with_empty_arrays(self, mock_product, mock_project, tenant_key):
        """
        BEHAVIOR: Empty arrays for outcomes/decisions should be valid

        GIVEN: Empty key_outcomes and decisions_made arrays
        WHEN: close_project_and_update_memory() is called
        THEN: Closeout succeeds with empty arrays stored
        """
        from giljo_mcp.tools.project_closeout import close_project_and_update_memory

        mock_session, mock_db_manager = create_mock_db_session(mock_project, mock_product)

        result = await close_project_and_update_memory(
            project_id=str(mock_project.id),
            summary="Test summary",
            key_outcomes=[],  # Empty
            decisions_made=[],  # Empty
            tenant_key=tenant_key,
            db_manager=mock_db_manager,
        )

        assert result["success"] is True

        entry = mock_product.product_memory["sequential_history"][0]
        assert entry["key_outcomes"] == []
        assert entry["decisions_made"] == []

    @pytest.mark.asyncio
    async def test_closeout_with_non_list_arrays(self, mock_product, mock_project, tenant_key):
        """
        BEHAVIOR: Non-list arrays should be normalized to empty lists

        GIVEN: key_outcomes and decisions_made are not lists
        WHEN: close_project_and_update_memory() is called
        THEN: They are normalized to empty lists with warning logged
        """
        from giljo_mcp.tools.project_closeout import close_project_and_update_memory

        mock_session, mock_db_manager = create_mock_db_session(mock_project, mock_product)

        result = await close_project_and_update_memory(
            project_id=str(mock_project.id),
            summary="Test summary",
            key_outcomes="not a list",  # Invalid type
            decisions_made="also not a list",  # Invalid type
            tenant_key=tenant_key,
            db_manager=mock_db_manager,
        )

        assert result["success"] is True

        entry = mock_product.product_memory["sequential_history"][0]
        assert entry["key_outcomes"] == []
        assert entry["decisions_made"] == []

    @pytest.mark.asyncio
    async def test_missing_db_manager_fails(self, tenant_key, sample_project_id):
        """
        BEHAVIOR: Missing db_manager should fail gracefully

        GIVEN: db_manager is None
        WHEN: close_project_and_update_memory() is called
        THEN: Returns error about missing db_manager
        """
        from giljo_mcp.tools.project_closeout import close_project_and_update_memory

        result = await close_project_and_update_memory(
            project_id=sample_project_id,
            summary="Test summary",
            key_outcomes=["Outcome 1"],
            decisions_made=["Decision 1"],
            tenant_key=tenant_key,
            db_manager=None,  # Missing
        )

        assert result["success"] is False
        assert "db_manager" in result["error"].lower()

    @pytest.mark.asyncio
    async def test_product_not_found_for_project(self, mock_project, tenant_key):
        """
        BEHAVIOR: Missing product for project should fail

        GIVEN: Project exists but product doesn't
        WHEN: close_project_and_update_memory() is called
        THEN: Returns error about missing product
        """
        from giljo_mcp.tools.project_closeout import close_project_and_update_memory

        mock_session = AsyncMock()
        mock_db_manager = MagicMock()
        mock_db_manager.get_session_async.return_value.__aenter__.return_value = mock_session

        # Project found, but product not found
        call_counter = {"count": 0}

        async def mock_execute_side_effect(*args, **kwargs):
            mock_result = MagicMock()
            if call_counter["count"] == 0:
                # First call: return project
                mock_result.scalar_one_or_none.return_value = mock_project
            else:
                # Second call: product not found
                mock_result.scalar_one_or_none.return_value = None

            call_counter["count"] += 1
            return mock_result

        mock_session.execute.side_effect = mock_execute_side_effect

        result = await close_project_and_update_memory(
            project_id=str(mock_project.id),
            summary="Test summary",
            key_outcomes=["Outcome 1"],
            decisions_made=["Decision 1"],
            tenant_key=tenant_key,
            db_manager=mock_db_manager,
        )

        assert result["success"] is False
        assert "product not found" in result["error"].lower()

    @pytest.mark.asyncio
    async def test_normalized_git_commits_with_invalid_format(self, mock_product, mock_project, tenant_key):
        """
        BEHAVIOR: Git commits with invalid format should be normalized

        GIVEN: GitHub returns commits in unexpected format
        WHEN: close_project_and_update_memory() is called
        THEN: Commits are normalized safely
        """
        from giljo_mcp.tools.project_closeout import close_project_and_update_memory

        # Enable GitHub integration
        mock_product.product_memory["github"] = {
            "enabled": True,
            "repo_url": "https://github.com/user/test-repo",
        }

        mock_session, mock_db_manager = create_mock_db_session(mock_project, mock_product)

        # Mock GitHub API with invalid/mixed format commits
        invalid_commits = [
            "string commit",  # Not a dict
            {"sha": "abc123", "message": "Direct message"},  # Direct message field
            {"sha": "def456", "commit": {"message": "Nested message"}},  # Nested message
        ]

        with patch("giljo_mcp.tools.project_closeout.fetch_github_commits", return_value=invalid_commits):
            result = await close_project_and_update_memory(
                project_id=str(mock_project.id),
                summary="Test summary",
                key_outcomes=["Outcome 1"],
                decisions_made=["Decision 1"],
                tenant_key=tenant_key,
                db_manager=mock_db_manager,
            )

        assert result["success"] is True
        learning = mock_product.product_memory["learnings"][0]
        assert len(learning["git_commits"]) == 3
        # First commit normalized from string
        assert learning["git_commits"][0]["message"] == "string commit"
        # Second commit uses direct message
        assert learning["git_commits"][1]["message"] == "Direct message"
        # Third commit uses nested message
        assert learning["git_commits"][2]["message"] == "Nested message"

    @pytest.mark.asyncio
    async def test_mcp_wrapper_function(self, tenant_key):
        """
        BEHAVIOR: MCP wrapper function injects db_manager correctly

        GIVEN: MCP wrapper is called with project closeout parameters
        WHEN: close_project_and_update_memory_wrapper() is called
        THEN: It delegates to close_project_and_update_memory with db_manager
        """
        from unittest.mock import MagicMock

        from fastmcp import FastMCP

        from giljo_mcp.tools.project_closeout import register_project_closeout_tools

        # Create mock MCP and db_manager
        mock_mcp = MagicMock(spec=FastMCP)
        mock_db_manager = MagicMock()
        mock_tenant_manager = MagicMock()

        # Track the registered tool
        registered_tool = None

        def capture_tool(func=None):
            nonlocal registered_tool
            if func is not None:
                registered_tool = func
                return func

            def decorator(f):
                nonlocal registered_tool
                registered_tool = f
                return f

            return decorator

        mock_mcp.tool = capture_tool

        # Register tools
        register_project_closeout_tools(mock_mcp, mock_db_manager, mock_tenant_manager)

        # Verify tool was registered
        assert registered_tool is not None

        # Test that wrapper correctly passes db_manager
        with patch("giljo_mcp.tools.project_closeout.close_project_and_update_memory") as mock_close:
            mock_close.return_value = {"success": True}

            await registered_tool(
                project_id="test-id",
                summary="Test summary",
                key_outcomes=["Outcome 1"],
                decisions_made=["Decision 1"],
                tenant_key=tenant_key,
            )

            # Verify db_manager was injected
            mock_close.assert_called_once()
            call_kwargs = mock_close.call_args[1]
            assert call_kwargs["db_manager"] == mock_db_manager
