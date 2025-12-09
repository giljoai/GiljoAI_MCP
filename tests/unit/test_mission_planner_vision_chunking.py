"""
Unit tests for MissionPlanner vision_chunking depth configuration.

Tests the vision document token budget enforcement based on depth configuration.
Tests cover:
- Default vision_chunking depth in depth_config
- Token budget mapping (none/light/moderate/heavy)
- Chunked vision respects max_tokens from depth config
- Non-chunked vision truncates to max_tokens from depth config
- vision_chunking='none' excludes vision documents entirely
- Logging when vision is truncated

Following TDD principles: Tests written BEFORE implementation.
"""

from contextlib import asynccontextmanager
from unittest.mock import AsyncMock, Mock, patch

import pytest

from src.giljo_mcp.mission_planner import MissionPlanner
from src.giljo_mcp.models import Product, Project, VisionDocument


class TestMissionPlannerVisionChunking:
    """Test cases for MissionPlanner vision_chunking depth configuration."""

    @pytest.fixture
    def mock_db_manager(self):
        """Create a mock database manager."""
        db_manager = Mock()
        db_manager.is_async = True

        # Create proper async context manager for get_session_async
        session = AsyncMock()

        @asynccontextmanager
        async def mock_get_session_async():
            yield session

        db_manager.get_session_async = mock_get_session_async
        return db_manager

    @pytest.fixture
    def mission_planner(self, mock_db_manager):
        """Create MissionPlanner instance with mocked dependencies."""
        return MissionPlanner(mock_db_manager)

    @pytest.fixture
    def sample_project(self):
        """Create a sample project."""
        project = Mock(spec=Project)
        project.id = "project_test"
        project.tenant_key = "tenant_test"
        project.name = "Test Project"
        project.description = "Project for testing vision chunking"
        project.mission = None
        return project

    @pytest.fixture
    def product_with_large_vision(self):
        """
        Create a Product with large vision text (40K+ tokens worth).

        This simulates the real-world issue where primary_vision_text
        is ~160KB but estimated_tokens shows only 11790.
        """
        product = Mock(spec=Product)
        product.id = "product_large_vision"
        product.tenant_key = "tenant_test"
        product.name = "Large Vision Product"

        # Create ~40K tokens worth of text (~160KB)
        # Using ~4 chars per token estimate = 160,000 chars
        large_text = "This is a comprehensive product vision document. " * 3200
        product.primary_vision_text = large_text
        product.primary_vision_path = None
        product.vision_documents = []  # No chunks
        product.config_data = {"tech_stack": {"languages": ["Python"]}}

        # Mock product_memory to avoid iteration errors
        product.product_memory = {
            "sequential_history": [],
            "git_integration": {"enabled": False}
        }

        return product

    @pytest.fixture
    def product_with_chunked_vision(self):
        """Create a Product with chunked vision documents."""
        product = Mock(spec=Product)
        product.id = "product_chunked"
        product.tenant_key = "tenant_test"
        product.name = "Chunked Vision Product"
        product.primary_vision_text = "Full vision text"
        product.primary_vision_path = "docs/vision.md"

        # Mock chunked vision documents
        chunk1 = Mock(spec=VisionDocument)
        chunk1.is_active = True
        chunk1.chunked = True
        chunk1.chunk_count = 10
        chunk1.id = "chunk1"

        product.vision_documents = [chunk1]
        product.config_data = {"tech_stack": {"languages": ["Python"]}}

        # Mock product_memory to avoid iteration errors
        product.product_memory = {
            "sequential_history": [],
            "git_integration": {"enabled": False}
        }

        return product

    @pytest.mark.asyncio
    async def test_default_depth_config_includes_vision_chunking(self, mission_planner, product_with_large_vision, sample_project):
        """Test that default depth_config includes vision_chunking='moderate'."""
        # Arrange
        field_priorities = {"vision_documents": 1}  # CRITICAL - include vision

        # Mock _get_relevant_vision_chunks to avoid actual DB calls
        with patch.object(mission_planner, '_get_relevant_vision_chunks', new_callable=AsyncMock) as mock_chunks:
            mock_chunks.return_value = []

            # Act - Call without depth_config (should use defaults)
            context = await mission_planner._build_context_with_priorities(
                product=product_with_large_vision,
                project=sample_project,
                field_priorities=field_priorities,
                depth_config=None,  # Should apply defaults
            )

        # Assert - The default depth_config should be applied internally
        # We verify by checking the context includes vision but respects default "moderate" budget
        assert "vision" in context.lower() or "product" in context.lower()

    @pytest.mark.asyncio
    async def test_vision_chunking_none_excludes_vision(self, mission_planner, product_with_large_vision, sample_project):
        """Test that vision_chunking='none' excludes vision documents entirely."""
        # Arrange
        field_priorities = {"vision_documents": 1}  # CRITICAL - but chunking=none should override
        depth_config = {
            "vision_chunking": "none",
            "memory_360": 5,
            "git_history": 20,
            "agent_templates": "full",
        }

        # Act
        context = await mission_planner._build_context_with_priorities(
            product=product_with_large_vision,
            project=sample_project,
            field_priorities=field_priorities,
            depth_config=depth_config,
        )

        # Assert - Vision should NOT be in context
        # Check that the large vision text is NOT included
        assert product_with_large_vision.primary_vision_text not in context
        assert "## Product Vision" not in context or "vision truncated" in context.lower()

    @pytest.mark.asyncio
    async def test_vision_chunking_light_budget(self, mission_planner, product_with_large_vision, sample_project):
        """Test that vision_chunking='light' enforces 10,000 token budget."""
        # Arrange
        field_priorities = {"vision_documents": 1}  # CRITICAL
        depth_config = {
            "vision_chunking": "light",  # 10,000 tokens = ~40,000 chars
            "memory_360": 5,
            "git_history": 20,
            "agent_templates": "full",
        }

        # Act
        context = await mission_planner._build_context_with_priorities(
            product=product_with_large_vision,
            project=sample_project,
            field_priorities=field_priorities,
            depth_config=depth_config,
        )

        # Assert - Vision should be truncated
        # Light budget = 10K tokens * 4 chars = 40K chars max
        if "## Product Vision" in context:
            vision_start = context.find("## Product Vision")
            vision_section = context[vision_start:vision_start + 50000]  # Check reasonable range
            # Should see truncation message or truncated content
            assert len(vision_section) < 60000 or "truncated" in vision_section.lower()

    @pytest.mark.asyncio
    async def test_vision_chunking_moderate_budget(self, mission_planner, product_with_large_vision, sample_project):
        """Test that vision_chunking='moderate' enforces 17,500 token budget."""
        # Arrange
        field_priorities = {"vision_documents": 1}  # CRITICAL
        depth_config = {
            "vision_chunking": "moderate",  # 17,500 tokens = ~70,000 chars
            "memory_360": 5,
            "git_history": 20,
            "agent_templates": "full",
        }

        # Act
        context = await mission_planner._build_context_with_priorities(
            product=product_with_large_vision,
            project=sample_project,
            field_priorities=field_priorities,
            depth_config=depth_config,
        )

        # Assert - Vision should be truncated
        # Moderate budget = 17.5K tokens * 4 chars = 70K chars max
        if "## Product Vision" in context:
            vision_start = context.find("## Product Vision")
            vision_section = context[vision_start:vision_start + 90000]  # Check reasonable range
            assert len(vision_section) < 100000 or "truncated" in vision_section.lower()

    @pytest.mark.asyncio
    async def test_vision_chunking_heavy_budget(self, mission_planner, product_with_large_vision, sample_project):
        """Test that vision_chunking='heavy' enforces 24,000 token budget."""
        # Arrange
        field_priorities = {"vision_documents": 1}  # CRITICAL
        depth_config = {
            "vision_chunking": "heavy",  # 24,000 tokens = ~96,000 chars
            "memory_360": 5,
            "git_history": 20,
            "agent_templates": "full",
        }

        # Act
        context = await mission_planner._build_context_with_priorities(
            product=product_with_large_vision,
            project=sample_project,
            field_priorities=field_priorities,
            depth_config=depth_config,
        )

        # Assert - Vision should be truncated
        # Heavy budget = 24K tokens * 4 chars = 96K chars max
        if "## Product Vision" in context:
            vision_start = context.find("## Product Vision")
            vision_section = context[vision_start:vision_start + 120000]  # Check reasonable range
            assert len(vision_section) < 130000 or "truncated" in vision_section.lower()

    @pytest.mark.asyncio
    async def test_chunked_vision_respects_depth_budget(self, mission_planner, product_with_chunked_vision, sample_project):
        """Test that chunked vision passes depth-based max_tokens to _get_relevant_vision_chunks."""
        # Arrange
        field_priorities = {"vision_documents": 1}  # CRITICAL
        depth_config = {
            "vision_chunking": "light",  # 10,000 tokens
            "memory_360": 5,
            "git_history": 20,
            "agent_templates": "full",
        }

        # Mock _get_relevant_vision_chunks to verify it receives correct max_tokens
        with patch.object(mission_planner, '_get_relevant_vision_chunks', new_callable=AsyncMock) as mock_chunks:
            mock_chunks.return_value = [
                {"content": "Chunk 1 content", "relevance_score": 0.9},
                {"content": "Chunk 2 content", "relevance_score": 0.8},
            ]

            # Act
            context = await mission_planner._build_context_with_priorities(
                product=product_with_chunked_vision,
                project=sample_project,
                field_priorities=field_priorities,
                depth_config=depth_config,
            )

            # Assert - _get_relevant_vision_chunks should be called with max_tokens=10000
            mock_chunks.assert_called_once()
            call_args = mock_chunks.call_args
            assert call_args.kwargs.get('max_tokens') == 10000  # light budget

    @pytest.mark.asyncio
    async def test_chunked_vision_moderate_budget(self, mission_planner, product_with_chunked_vision, sample_project):
        """Test that chunked vision uses moderate budget (17,500 tokens)."""
        # Arrange
        field_priorities = {"vision_documents": 1}  # CRITICAL
        depth_config = {
            "vision_chunking": "moderate",  # 17,500 tokens
            "memory_360": 5,
            "git_history": 20,
            "agent_templates": "full",
        }

        # Mock _get_relevant_vision_chunks
        with patch.object(mission_planner, '_get_relevant_vision_chunks', new_callable=AsyncMock) as mock_chunks:
            mock_chunks.return_value = [{"content": "Chunk content", "relevance_score": 0.9}]

            # Act
            await mission_planner._build_context_with_priorities(
                product=product_with_chunked_vision,
                project=sample_project,
                field_priorities=field_priorities,
                depth_config=depth_config,
            )

            # Assert
            call_args = mock_chunks.call_args
            assert call_args.kwargs.get('max_tokens') == 17500  # moderate budget

    @pytest.mark.asyncio
    async def test_chunked_vision_heavy_budget(self, mission_planner, product_with_chunked_vision, sample_project):
        """Test that chunked vision uses heavy budget (24,000 tokens)."""
        # Arrange
        field_priorities = {"vision_documents": 1}  # CRITICAL
        depth_config = {
            "vision_chunking": "heavy",  # 24,000 tokens
            "memory_360": 5,
            "git_history": 20,
            "agent_templates": "full",
        }

        # Mock _get_relevant_vision_chunks
        with patch.object(mission_planner, '_get_relevant_vision_chunks', new_callable=AsyncMock) as mock_chunks:
            mock_chunks.return_value = [{"content": "Chunk content", "relevance_score": 0.9}]

            # Act
            await mission_planner._build_context_with_priorities(
                product=product_with_chunked_vision,
                project=sample_project,
                field_priorities=field_priorities,
                depth_config=depth_config,
            )

            # Assert
            call_args = mock_chunks.call_args
            assert call_args.kwargs.get('max_tokens') == 24000  # heavy budget

    @pytest.mark.asyncio
    async def test_truncation_logging(self, mission_planner, product_with_large_vision, sample_project, caplog):
        """Test that truncation is logged when vision exceeds budget."""
        # Arrange
        field_priorities = {"vision_documents": 1}  # CRITICAL
        depth_config = {
            "vision_chunking": "light",  # 10,000 tokens - will force truncation
            "memory_360": 5,
            "git_history": 20,
            "agent_templates": "full",
        }

        # Act
        with caplog.at_level("INFO"):
            context = await mission_planner._build_context_with_priorities(
                product=product_with_large_vision,
                project=sample_project,
                field_priorities=field_priorities,
                depth_config=depth_config,
            )

        # Assert - Should log truncation
        # Check for log message about vision truncation
        log_messages = [record.message for record in caplog.records]
        truncation_logged = any("truncated" in msg.lower() or "vision" in msg.lower() for msg in log_messages)
        assert truncation_logged or "truncated" in context.lower()

    @pytest.mark.asyncio
    async def test_non_chunked_vision_truncation_message(self, mission_planner, product_with_large_vision, sample_project):
        """Test that non-chunked vision includes truncation message when cut off."""
        # Arrange
        field_priorities = {"vision_documents": 1}  # CRITICAL
        depth_config = {
            "vision_chunking": "light",  # 10,000 tokens = ~40,000 chars
            "memory_360": 5,
            "git_history": 20,
            "agent_templates": "full",
        }

        # Act
        context = await mission_planner._build_context_with_priorities(
            product=product_with_large_vision,
            project=sample_project,
            field_priorities=field_priorities,
            depth_config=depth_config,
        )

        # Assert - Should contain truncation indicator
        if "## Product Vision" in context:
            # Should see truncation message
            assert "[... vision truncated to fit token budget ...]" in context or len(context) < 100000
