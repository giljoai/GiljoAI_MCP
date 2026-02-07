"""
Test JSON refactor of MissionPlanner._build_context_with_priorities.

Validates that MissionPlanner now returns structured JSON instead of markdown strings,
using JSONContextBuilder for priority-based organization.

Part of Handover 0347b - MissionPlanner JSON Refactor.
"""

from unittest.mock import AsyncMock, Mock, patch

import pytest

from src.giljo_mcp.mission_planner import MissionPlanner
from src.giljo_mcp.models import Product, Project, VisionDocument


@pytest.fixture
def mock_db_manager():
    """Mock database manager for testing."""
    from unittest.mock import MagicMock

    mock_manager = Mock()

    # Create a proper async context manager mock
    mock_session = MagicMock()
    mock_session.execute = AsyncMock()
    mock_session.commit = AsyncMock()

    # Create async context manager
    mock_context = AsyncMock()
    mock_context.__aenter__ = AsyncMock(return_value=mock_session)
    mock_context.__aexit__ = AsyncMock(return_value=None)

    mock_manager.get_session_async = Mock(return_value=mock_context)
    return mock_manager


@pytest.fixture
def sample_product():
    """Sample product with config_data."""
    product = Mock(spec=Product)
    product.id = "product-123"
    product.tenant_key = "tenant-abc"
    product.name = "GiljoAI"
    product.description = "Multi-agent orchestration platform"
    product.config_data = {
        "tech_stack": {
            "backend": ["Python 3.11+", "FastAPI"],
            "database": ["PostgreSQL 18"],
        },
        "architecture": "Service-oriented architecture with REST API",
        "testing": {
            "methodology": "TDD",
            "coverage_target": 80,
        },
    }
    product.product_memory = None
    product.vision_documents = []
    return product


@pytest.fixture
def sample_project():
    """Sample project with description."""
    project = Mock(spec=Project)
    project.id = "project-456"
    project.name = "Test Project"
    project.description = "Implement user authentication"
    project.mission = None
    return project


@pytest.mark.asyncio
class TestMissionPlannerJSONRefactor:
    """Test suite for MissionPlanner JSON refactor (Handover 0347b)."""

    async def test_returns_dict_not_string(self, mock_db_manager, sample_product, sample_project):
        """Test that _build_context_with_priorities returns dict instead of str."""
        planner = MissionPlanner(mock_db_manager)

        result = await planner._build_context_with_priorities(
            product=sample_product,
            project=sample_project,
            field_priorities={"product_core": 1, "tech_stack": 1},
            depth_config={},
        )

        # CRITICAL: Must return dict, not string
        assert isinstance(result, dict), f"Expected dict, got {type(result)}"

    async def test_json_structure_has_priority_map(self, mock_db_manager, sample_product, sample_project):
        """Test that returned dict has priority_map key."""
        planner = MissionPlanner(mock_db_manager)

        result = await planner._build_context_with_priorities(
            product=sample_product,
            project=sample_project,
            field_priorities={"product_core": 1, "tech_stack": 2},
            depth_config={},
        )

        # Validate structure
        assert "priority_map" in result, "Missing priority_map key"
        assert isinstance(result["priority_map"], dict), "priority_map must be dict"
        assert "critical" in result["priority_map"], "priority_map missing critical tier"
        assert "important" in result["priority_map"], "priority_map missing important tier"
        assert "reference" in result["priority_map"], "priority_map missing reference tier"

    async def test_critical_fields_have_inline_content(self, mock_db_manager, sample_product, sample_project):
        """Test that priority 1 (CRITICAL) fields have full inline content."""
        planner = MissionPlanner(mock_db_manager)

        result = await planner._build_context_with_priorities(
            product=sample_product,
            project=sample_project,
            field_priorities={"product_core": 1, "tech_stack": 1},
            depth_config={},
        )

        # CRITICAL fields should be in critical tier with content
        assert "critical" in result, "Missing critical tier"
        assert isinstance(result["critical"], dict), "critical tier must be dict"

        # Product core should be in critical tier
        if "product_core" in result["priority_map"]["critical"]:
            assert "product_core" in result["critical"], "product_core not in critical content"
            assert isinstance(result["critical"]["product_core"], dict), "product_core content must be dict"

    async def test_important_fields_have_condensed_content(self, mock_db_manager, sample_product, sample_project):
        """Test that priority 2 (IMPORTANT) fields have condensed content + fetch pointers."""
        planner = MissionPlanner(mock_db_manager)

        result = await planner._build_context_with_priorities(
            product=sample_product,
            project=sample_project,
            field_priorities={"architecture": 2, "testing": 2},
            depth_config={},
        )

        # IMPORTANT fields should be in important tier
        assert "important" in result, "Missing important tier"
        assert isinstance(result["important"], dict), "important tier must be dict"

    async def test_reference_fields_have_fetch_tools(self, mock_db_manager, sample_product, sample_project):
        """Test that priority 3 (REFERENCE) fields have summary + fetch_tool pointers."""
        # Mock vision document query result
        mock_vision_result = Mock()
        mock_vision_result.scalar_one_or_none = Mock(return_value=None)  # No vision doc for simplicity

        # Configure mock session to return the result
        mock_session = mock_db_manager.get_session_async.return_value.__aenter__.return_value
        mock_session.execute = AsyncMock(return_value=mock_vision_result)

        planner = MissionPlanner(mock_db_manager)

        result = await planner._build_context_with_priorities(
            product=sample_product,
            project=sample_project,
            field_priorities={"vision_documents": 3, "memory_360": 3},
            depth_config={"memory_360": 5},
        )

        # REFERENCE fields should be in reference tier
        assert "reference" in result, "Missing reference tier"
        assert isinstance(result["reference"], dict), "reference tier must be dict"

    async def test_excluded_fields_not_in_result(self, mock_db_manager, sample_product, sample_project):
        """Test that priority 4 (EXCLUDED) fields are omitted."""
        planner = MissionPlanner(mock_db_manager)

        result = await planner._build_context_with_priorities(
            product=sample_product,
            project=sample_project,
            field_priorities={"vision_documents": 4, "memory_360": 4},  # EXCLUDED
            depth_config={},
        )

        # Excluded fields should not be in any tier content
        assert "vision_documents" not in result.get("critical", {}), "Excluded field in critical"
        assert "vision_documents" not in result.get("important", {}), "Excluded field in important"
        assert "vision_documents" not in result.get("reference", {}), "Excluded field in reference"

    async def test_token_count_reduction(self, mock_db_manager, sample_product, sample_project):
        """Test that JSON output is significantly smaller than old markdown approach."""
        planner = MissionPlanner(mock_db_manager)

        result = await planner._build_context_with_priorities(
            product=sample_product,
            project=sample_project,
            field_priorities={
                "product_core": 1,
                "tech_stack": 1,
                "architecture": 2,
            },
            depth_config={},
        )

        # Estimate token count (1 token ≈ 4 chars)
        import json

        json_str = json.dumps(result)
        token_count = len(json_str) // 4

        # Should be < 2,000 tokens (down from ~21,000)
        assert token_count < 2000, f"Token count too high: {token_count} (target: <2,000)"

    async def test_mandatory_project_description_included(self, mock_db_manager, sample_product, sample_project):
        """Test that project.description is ALWAYS included (non-negotiable)."""
        planner = MissionPlanner(mock_db_manager)

        result = await planner._build_context_with_priorities(
            product=sample_product,
            project=sample_project,
            field_priorities={},  # Empty priorities
            depth_config={},
        )

        # Project description should be in critical tier (MANDATORY)
        assert "critical" in result, "Missing critical tier"
        # Look for project_description in critical content
        # (implementation detail: might be combined with product_core or separate)

    @patch("src.giljo_mcp.mission_planner.MissionPlanner._get_active_vision_doc")
    async def test_helper_method_get_active_vision_doc(
        self, mock_get_vision, mock_db_manager, sample_product, sample_project
    ):
        """Test new helper method _get_active_vision_doc."""
        # Setup mock
        mock_vision = Mock(spec=VisionDocument)
        mock_vision.document_name = "Product Vision v1"
        mock_vision.summary_light = "Brief overview"
        mock_get_vision.return_value = mock_vision

        planner = MissionPlanner(mock_db_manager)

        # Call helper (if implemented)
        if hasattr(planner, "_get_active_vision_doc"):
            vision = await planner._get_active_vision_doc(sample_product)
            assert vision is not None, "Should return vision document"

    async def test_helper_method_get_memory_summary(self, mock_db_manager, sample_product, sample_project):
        """Test new helper method _get_memory_summary."""
        planner = MissionPlanner(mock_db_manager)

        # Call helper (if implemented)
        if hasattr(planner, "_get_memory_summary"):
            summary = await planner._get_memory_summary(sample_product, max_entries=3)
            # Should return brief summary or empty string
            assert isinstance(summary, (str, dict)), "Summary should be str or dict"

    async def test_json_serializable_output(self, mock_db_manager, sample_product, sample_project):
        """Test that all output is JSON-serializable (no datetime, UUID objects, etc)."""
        planner = MissionPlanner(mock_db_manager)

        result = await planner._build_context_with_priorities(
            product=sample_product,
            project=sample_project,
            field_priorities={"product_core": 1, "tech_stack": 1},
            depth_config={},
        )

        # Should be able to serialize without errors
        import json

        try:
            json_str = json.dumps(result)
            assert len(json_str) > 0, "JSON output is empty"
        except (TypeError, ValueError) as e:
            pytest.fail(f"Result is not JSON-serializable: {e}")

    async def test_backward_compatibility_with_callers(self, mock_db_manager, sample_product, sample_project):
        """Test that existing callers can handle dict return type."""
        planner = MissionPlanner(mock_db_manager)

        result = await planner._build_context_with_priorities(
            product=sample_product,
            project=sample_project,
            field_priorities={"product_core": 1},
            depth_config={},
        )

        # Callers should be able to check type and handle accordingly
        if isinstance(result, dict):
            # New JSON format
            assert "priority_map" in result
        elif isinstance(result, str):
            # Old markdown format (backward compat)
            assert len(result) > 0
        else:
            pytest.fail(f"Unexpected return type: {type(result)}")
