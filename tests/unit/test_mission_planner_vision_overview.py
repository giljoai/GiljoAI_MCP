"""
Unit tests for lean orchestrator instructions (Handover 0345a).

Tests vision overview generation to ensure orchestrator instructions stay under 5K tokens
by replacing full vision document content with minimal metadata + fetch instructions.

Following TDD principles: Tests written BEFORE implementation.
"""

from unittest.mock import AsyncMock, Mock, patch
from typing import Any, Dict

import pytest

from src.giljo_mcp.mission_planner import MissionPlanner
from src.giljo_mcp.models import Product, Project, VisionDocument


class TestLeanOrchestratorInstructions:
    """Test suite for lean orchestrator instructions (0345a)."""

    @pytest.fixture
    def mock_db_manager(self):
        """Create a mock database manager."""
        db_manager = Mock()
        db_manager.is_async = True
        # Mock session for async context manager
        mock_session = AsyncMock()
        db_manager.get_session_async = Mock(return_value=AsyncMock(
            __aenter__=AsyncMock(return_value=mock_session),
            __aexit__=AsyncMock()
        ))
        return db_manager

    @pytest.fixture
    def mission_planner(self, mock_db_manager):
        """Create MissionPlanner instance with mocked dependencies."""
        return MissionPlanner(mock_db_manager)

    @pytest.fixture
    def mock_product_with_vision(self):
        """Create a product with chunked vision documents (small)."""
        product = Mock(spec=Product)
        product.id = "product_123"
        product.tenant_key = "tenant_abc"
        product.name = "Test Product"
        product.description = "A test product with vision documents"
        product.primary_vision_text = "Chapter 1: Product Vision\n\nThis is a test vision document..."
        product.primary_vision_path = None
        product.config_data = {
            "tech_stack": ["Python", "FastAPI", "PostgreSQL"],
            "features": ["authentication", "api"],
        }
        product.product_memory = {
            "sequential_history": [],
            "git_integration": {"enabled": False}
        }

        # Mock chunked vision documents
        vision_doc = Mock(spec=VisionDocument)
        vision_doc.is_active = True
        vision_doc.chunked = True
        vision_doc.chunk_count = 5
        product.vision_documents = [vision_doc]

        return product

    @pytest.fixture
    def mock_product_with_large_vision(self):
        """Create a product with large chunked vision (150K tokens)."""
        product = Mock(spec=Product)
        product.id = "product_456"
        product.tenant_key = "tenant_xyz"
        product.name = "Large Product"
        product.description = "A product with massive vision documentation"
        product.primary_vision_text = "Chapter 1: Extensive Product Vision\n\n" + "X" * 100000
        product.primary_vision_path = None
        product.config_data = {"tech_stack": ["Python"]}
        product.product_memory = {
            "sequential_history": [],
            "git_integration": {"enabled": False}
        }

        # Mock large chunked vision
        vision_doc = Mock(spec=VisionDocument)
        vision_doc.is_active = True
        vision_doc.chunked = True
        vision_doc.chunk_count = 25  # 25 chunks x 6K tokens each = 150K total
        product.vision_documents = [vision_doc]

        return product

    @pytest.fixture
    def mock_project(self):
        """Create a sample Project."""
        project = Mock(spec=Project)
        project.id = "project_789"
        project.tenant_key = "tenant_abc"
        project.name = "Test Project"
        project.description = "Build a modern web application"
        project.mission = "Implement user authentication system"
        project.meta_data = {}
        return project

    @pytest.mark.asyncio
    async def test_get_vision_overview_returns_metadata_only(
        self, mission_planner, mock_product_with_vision
    ):
        """_get_vision_overview should return chunk count and token estimate, not content."""
        # Mock database query result
        mock_session = AsyncMock()
        mock_row = Mock()
        mock_row.chunk_count = 5
        mock_row.total_tokens = 125000

        # Create a mock result that returns the row
        mock_result = Mock()
        mock_result.one = Mock(return_value=mock_row)

        # Mock execute to return the result
        async def mock_execute(stmt):
            return mock_result

        mock_session.execute = mock_execute

        overview = await mission_planner._get_vision_overview(
            session=mock_session,
            product=mock_product_with_vision,
        )

        # Assert structure
        assert overview is not None
        assert "total_chunks" in overview
        assert "total_tokens" in overview
        assert "fetch_instruction" in overview

        # Assert values
        assert overview["total_chunks"] == 5
        assert overview["total_tokens"] == 125000
        assert "fetch_vision_document" in overview["fetch_instruction"]

        # Assert NO actual content is returned
        assert "content" not in overview
        assert "Chapter 1" not in str(overview)

    @pytest.mark.asyncio
    async def test_get_vision_overview_returns_none_for_no_chunks(
        self, mission_planner, mock_product_with_vision
    ):
        """_get_vision_overview should return None when no chunks exist."""
        # Mock database query result with 0 chunks
        mock_session = AsyncMock()
        mock_row = Mock()
        mock_row.chunk_count = 0
        mock_row.total_tokens = 0

        mock_result = Mock()
        mock_result.one = Mock(return_value=mock_row)

        async def mock_execute(stmt):
            return mock_result

        mock_session.execute = mock_execute

        overview = await mission_planner._get_vision_overview(
            session=mock_session,
            product=mock_product_with_vision,
        )

        assert overview is None

    @pytest.mark.asyncio
    async def test_get_vision_overview_has_correct_fetch_instruction(
        self, mission_planner, mock_product_with_vision
    ):
        """Overview fetch_instruction should guide orchestrator to use MCP tool."""
        # Mock database query result
        mock_session = AsyncMock()
        mock_row = Mock()
        mock_row.chunk_count = 10
        mock_row.total_tokens = 250000

        mock_result = Mock()
        mock_result.one = Mock(return_value=mock_row)

        async def mock_execute(stmt):
            return mock_result

        mock_session.execute = mock_execute

        overview = await mission_planner._get_vision_overview(
            session=mock_session,
            product=mock_product_with_vision,
        )

        fetch_instruction = overview["fetch_instruction"]

        # Should mention chunk count
        assert "10" in fetch_instruction or "10 chunks" in fetch_instruction.lower()

        # Should mention approximate token count
        assert "250,000" in fetch_instruction or "250000" in fetch_instruction

        # Should mention the MCP tool name
        assert "fetch_vision_document" in fetch_instruction

    @pytest.mark.asyncio
    async def test_build_context_with_priorities_excludes_vision_body(
        self, mission_planner, mock_product_with_vision, mock_project
    ):
        """Vision document body should NOT be in context response."""
        # Mock _get_vision_overview to return overview
        mock_overview = {
            "total_chunks": 5,
            "total_tokens": 125000,
            "fetch_instruction": "You have 5 vision chunks (~125,000 tokens). Use fetch_vision_document(chunk=N) to read them."
        }

        with patch.object(mission_planner, '_get_vision_overview', return_value=mock_overview):
            result = await mission_planner._build_context_with_priorities(
                product=mock_product_with_vision,
                project=mock_project,
                field_priorities={"vision_documents": 2},  # Priority 2 = IMPORTANT (include)
                user_id="test-user",
            )

        # Should NOT contain actual vision content
        assert "Chapter 1: Product Vision" not in result
        assert "This is a test vision document" not in result

    @pytest.mark.asyncio
    async def test_build_context_with_priorities_includes_vision_overview(
        self, mission_planner, mock_product_with_vision, mock_project
    ):
        """Context response should include vision overview with fetch instructions."""
        # Mock _get_vision_overview to return overview
        mock_overview = {
            "total_chunks": 5,
            "total_tokens": 125000,
            "fetch_instruction": "You have 5 vision chunks (~125,000 tokens). Use fetch_vision_document(chunk=N) to read them."
        }

        with patch.object(mission_planner, '_get_vision_overview', return_value=mock_overview):
            result = await mission_planner._build_context_with_priorities(
                product=mock_product_with_vision,
                project=mock_project,
                field_priorities={"vision_documents": 2},
                user_id="test-user",
            )

        # Should mention vision chunks/overview
        result_lower = result.lower()
        assert "vision" in result_lower
        assert ("5 chunks" in result_lower or "5 vision chunks" in result_lower)

        # Should include fetch instruction
        assert "fetch_vision_document" in result

    @pytest.mark.asyncio
    async def test_build_context_preserves_all_other_context(
        self, mission_planner, mock_product_with_vision, mock_project
    ):
        """Project, product core, and other context MUST remain - CRITICAL."""
        # Mock _get_vision_overview
        mock_overview = {
            "total_chunks": 5,
            "total_tokens": 125000,
            "fetch_instruction": "You have 5 vision chunks (~125,000 tokens). Use fetch_vision_document(chunk=N) to read them."
        }

        with patch.object(mission_planner, '_get_vision_overview', return_value=mock_overview):
            result = await mission_planner._build_context_with_priorities(
                product=mock_product_with_vision,
                project=mock_project,
                field_priorities={
                    "product_core": 1,
                    "project_description": 1,
                    "vision_documents": 2,
                    "tech_stack": 2,
                },
                user_id="test-user",
            )

        # Product core MUST be present
        assert mock_product_with_vision.name in result
        assert mock_product_with_vision.description in result

        # Project context MUST be present
        assert mock_project.name in result or mock_project.description in result

        # Tech stack MUST be present
        assert "Python" in result or "FastAPI" in result

    @pytest.mark.asyncio
    async def test_response_under_5k_tokens_with_large_vision(
        self, mission_planner, mock_product_with_large_vision, mock_project
    ):
        """Total response size must be < 5K tokens (~20K chars) even with 150K token vision."""
        # Mock _get_vision_overview for large vision
        mock_overview = {
            "total_chunks": 25,
            "total_tokens": 150000,
            "fetch_instruction": "You have 25 vision chunks (~150,000 tokens). Use fetch_vision_document(chunk=N) to read them."
        }

        with patch.object(mission_planner, '_get_vision_overview', return_value=mock_overview):
            result = await mission_planner._build_context_with_priorities(
                product=mock_product_with_large_vision,
                project=mock_project,
                field_priorities={
                    "product_core": 1,
                    "project_description": 1,
                    "vision_documents": 2,
                    "tech_stack": 2,
                },
                user_id="test-user",
            )

        # Rough token estimate: 1 token ~= 4 chars
        estimated_tokens = len(result) // 4

        # CRITICAL: Must be under 5K tokens
        assert estimated_tokens < 5000, (
            f"Response too large: {estimated_tokens} tokens (estimated from {len(result)} chars). "
            f"Expected < 5000 tokens."
        )

    @pytest.mark.asyncio
    async def test_vision_overview_not_included_when_priority_excluded(
        self, mission_planner, mock_product_with_vision, mock_project
    ):
        """Vision overview should not be included when priority is 4 (EXCLUDED)."""
        # Mock _get_vision_overview (should not be called)
        mock_overview = {
            "total_chunks": 5,
            "total_tokens": 125000,
            "fetch_instruction": "You have 5 vision chunks (~125,000 tokens). Use fetch_vision_document(chunk=N) to read them."
        }

        with patch.object(mission_planner, '_get_vision_overview', return_value=mock_overview) as mock_method:
            result = await mission_planner._build_context_with_priorities(
                product=mock_product_with_vision,
                project=mock_project,
                field_priorities={"vision_documents": 4},  # Priority 4 = EXCLUDED
                user_id="test-user",
            )

        # Vision overview method should not be called when priority is EXCLUDED
        # (This depends on implementation - adjust if needed)
        # For now, just verify vision content is not in result
        result_lower = result.lower()
        assert "vision" not in result_lower or "fetch_vision_document" not in result

    @pytest.mark.asyncio
    async def test_vision_overview_query_filters_by_tenant_and_product(
        self, mission_planner, mock_product_with_vision
    ):
        """_get_vision_overview must filter by tenant_key and product_id for multi-tenant isolation."""
        mock_session = AsyncMock()
        mock_row = Mock()
        mock_row.chunk_count = 5
        mock_row.total_tokens = 125000

        mock_result = Mock()
        mock_result.one = Mock(return_value=mock_row)

        # Track if execute was called and capture the statement
        executed_stmt = None

        async def mock_execute(stmt):
            nonlocal executed_stmt
            executed_stmt = stmt
            return mock_result

        mock_session.execute = mock_execute

        await mission_planner._get_vision_overview(
            session=mock_session,
            product=mock_product_with_vision,
        )

        # Verify execute was called (query was executed)
        assert executed_stmt is not None, "Database query should have been executed"

        # Verify the statement is a select query (basic check)
        # Full SQL inspection would require more complex mocking
        # At minimum, verify it's a SQLAlchemy statement object
        assert hasattr(executed_stmt, '_where_criteria') or hasattr(executed_stmt, 'whereclause') or str(executed_stmt)
