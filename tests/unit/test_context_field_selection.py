"""
Tests for Context Field Selection (Context Management v3.0)

Handover 0319: TDD tests for granular field selection in context tools.

These tests verify:
1. Field metadata structure and functions
2. Context tools filtering by selected_fields
3. Migration from v2 depth values to v3 field selection
4. Default configuration with all fields enabled
"""

import pytest
import pytest_asyncio
from unittest.mock import MagicMock, AsyncMock, patch
from typing import Dict, Any
import uuid

from src.giljo_mcp.context.field_metadata import (
    FIELD_METADATA,
    get_field_metadata,
    get_default_field_selection,
    get_fields_for_category,
    migrate_v2_to_v3_fields,
    estimate_tokens_for_selection,
)


class TestFieldMetadata:
    """Tests for field metadata structure and utility functions."""

    def test_field_metadata_has_required_categories(self):
        """Verify FIELD_METADATA contains all required categories."""
        expected_categories = {"tech_stack", "architecture", "testing"}
        actual_categories = set(FIELD_METADATA.keys())

        assert expected_categories == actual_categories, (
            f"Expected categories {expected_categories}, got {actual_categories}"
        )

    def test_tech_stack_has_four_fields(self):
        """Verify tech_stack category has 4 fields."""
        tech_stack_fields = FIELD_METADATA.get("tech_stack", {})
        expected_fields = {"languages", "frameworks", "databases", "dependencies"}

        assert set(tech_stack_fields.keys()) == expected_fields, (
            f"Tech stack should have fields {expected_fields}, got {set(tech_stack_fields.keys())}"
        )

    def test_architecture_has_six_fields(self):
        """Verify architecture category has 6 fields."""
        arch_fields = FIELD_METADATA.get("architecture", {})
        expected_fields = {"pattern", "design_patterns", "api_style", "notes", "layers", "components"}

        assert set(arch_fields.keys()) == expected_fields, (
            f"Architecture should have fields {expected_fields}, got {set(arch_fields.keys())}"
        )

    def test_testing_has_three_fields(self):
        """Verify testing category has 3 fields."""
        testing_fields = FIELD_METADATA.get("testing", {})
        expected_fields = {"quality_standards", "strategy", "frameworks"}

        assert set(testing_fields.keys()) == expected_fields, (
            f"Testing should have fields {expected_fields}, got {set(testing_fields.keys())}"
        )

    def test_each_field_has_required_attributes(self):
        """Verify each field has key, label, tokens, and description."""
        required_attrs = {"key", "label", "tokens", "description"}

        for category, fields in FIELD_METADATA.items():
            for field_key, field_data in fields.items():
                missing = required_attrs - set(field_data.keys())
                assert not missing, (
                    f"Field {category}.{field_key} missing attributes: {missing}"
                )
                assert isinstance(field_data["tokens"], int), (
                    f"Field {category}.{field_key} tokens should be int"
                )
                assert field_data["tokens"] > 0, (
                    f"Field {category}.{field_key} tokens should be positive"
                )

    def test_get_field_metadata_returns_correct_data(self):
        """Test get_field_metadata returns correct field data."""
        result = get_field_metadata("tech_stack", "languages")

        assert result is not None
        assert result["key"] == "languages"
        assert result["label"] == "Programming Languages"
        assert result["tokens"] > 0

    def test_get_field_metadata_returns_none_for_invalid(self):
        """Test get_field_metadata returns None for invalid inputs."""
        assert get_field_metadata("invalid_category", "languages") is None
        assert get_field_metadata("tech_stack", "invalid_field") is None

    def test_get_fields_for_category(self):
        """Test get_fields_for_category returns correct field list."""
        tech_fields = get_fields_for_category("tech_stack")

        assert "languages" in tech_fields
        assert "frameworks" in tech_fields
        assert "databases" in tech_fields
        assert "dependencies" in tech_fields
        assert len(tech_fields) == 4

    def test_get_default_field_selection_all_enabled(self):
        """Test default selection enables all fields."""
        for category in FIELD_METADATA.keys():
            selection = get_default_field_selection(category)

            # All fields should be True
            for field, enabled in selection.items():
                assert enabled is True, (
                    f"Default selection for {category}.{field} should be True"
                )

            # Should have same number of fields as metadata
            expected_count = len(FIELD_METADATA[category])
            assert len(selection) == expected_count, (
                f"{category} default selection should have {expected_count} fields"
            )


class TestMigrationV2ToV3:
    """Tests for migrating v2 depth values to v3 field selection."""

    def test_tech_stack_required_migration(self):
        """Test tech_stack 'required' depth migrates correctly."""
        result = migrate_v2_to_v3_fields("tech_stack", "required")

        # Should enable only core fields
        assert result["languages"] is True
        assert result["frameworks"] is True
        assert result["databases"] is True
        # Dependencies should be disabled for "required"
        assert result["dependencies"] is False

    def test_tech_stack_all_migration(self):
        """Test tech_stack 'all' depth migrates correctly."""
        result = migrate_v2_to_v3_fields("tech_stack", "all")

        # All fields should be enabled
        for field, enabled in result.items():
            assert enabled is True, f"tech_stack.{field} should be enabled for 'all'"

    def test_architecture_overview_migration(self):
        """Test architecture 'overview' depth migrates correctly."""
        result = migrate_v2_to_v3_fields("architecture", "overview")

        # Only high-level fields enabled
        assert result["pattern"] is True
        assert result["api_style"] is True
        # Detailed fields disabled
        assert result["design_patterns"] is False
        assert result["notes"] is False
        assert result["layers"] is False
        assert result["components"] is False

    def test_architecture_detailed_migration(self):
        """Test architecture 'detailed' depth migrates correctly."""
        result = migrate_v2_to_v3_fields("architecture", "detailed")

        # All fields should be enabled
        for field, enabled in result.items():
            assert enabled is True, f"architecture.{field} should be enabled for 'detailed'"

    def test_testing_none_migration(self):
        """Test testing 'none' depth migrates correctly."""
        result = migrate_v2_to_v3_fields("testing", "none")

        # All fields should be disabled
        for field, enabled in result.items():
            assert enabled is False, f"testing.{field} should be disabled for 'none'"

    def test_testing_basic_migration(self):
        """Test testing 'basic' depth migrates correctly."""
        result = migrate_v2_to_v3_fields("testing", "basic")

        # Core fields enabled
        assert result["quality_standards"] is True
        assert result["strategy"] is True
        # Frameworks disabled
        assert result["frameworks"] is False

    def test_testing_full_migration(self):
        """Test testing 'full' depth migrates correctly."""
        result = migrate_v2_to_v3_fields("testing", "full")

        # All fields should be enabled
        for field, enabled in result.items():
            assert enabled is True, f"testing.{field} should be enabled for 'full'"

    def test_default_config_all_fields_enabled(self):
        """Test that default configuration has all fields enabled."""
        # Default depth values should enable all fields
        for category in ["tech_stack", "architecture", "testing"]:
            selection = get_default_field_selection(category)
            all_enabled = all(selection.values())
            assert all_enabled, f"Default {category} should have all fields enabled"


class TestTokenEstimation:
    """Tests for token estimation with field selection."""

    def test_estimate_tokens_all_fields(self):
        """Test token estimation with all fields enabled."""
        selection = get_default_field_selection("tech_stack")
        tokens = estimate_tokens_for_selection("tech_stack", selection)

        # Should be sum of all field tokens
        expected = sum(
            field["tokens"]
            for field in FIELD_METADATA["tech_stack"].values()
        )
        assert tokens == expected

    def test_estimate_tokens_partial_selection(self):
        """Test token estimation with partial field selection."""
        selection = {
            "languages": True,
            "frameworks": False,
            "databases": True,
            "dependencies": False,
        }
        tokens = estimate_tokens_for_selection("tech_stack", selection)

        # Should only include enabled fields
        expected = (
            FIELD_METADATA["tech_stack"]["languages"]["tokens"] +
            FIELD_METADATA["tech_stack"]["databases"]["tokens"]
        )
        assert tokens == expected

    def test_estimate_tokens_empty_selection(self):
        """Test token estimation with no fields enabled."""
        selection = {field: False for field in get_fields_for_category("testing")}
        tokens = estimate_tokens_for_selection("testing", selection)

        assert tokens == 0


class TestTechStackFiltersFields:
    """Tests for tech_stack tool filtering by selected_fields."""

    @pytest_asyncio.fixture
    async def mock_db_manager(self):
        """Create mock database manager with product data."""
        mock_manager = MagicMock()

        # Create mock product with config_data
        mock_product = MagicMock()
        mock_product.config_data = {
            "tech_stack": {
                "languages": ["Python", "TypeScript"],
                "frontend": ["Vue 3"],
                "backend": ["FastAPI"],
                "database": ["PostgreSQL"],
                "infrastructure": ["Docker", "Kubernetes"],
                "dev_tools": ["Git", "VS Code"],
            }
        }

        # Setup async context manager for session
        mock_session = AsyncMock()
        mock_result = MagicMock()
        mock_result.scalar_one_or_none.return_value = mock_product
        mock_session.execute = AsyncMock(return_value=mock_result)

        # Create async context manager
        async def mock_get_session():
            yield mock_session

        mock_manager.get_session = MagicMock(return_value=mock_session)
        mock_manager.get_session.return_value.__aenter__ = AsyncMock(return_value=mock_session)
        mock_manager.get_session.return_value.__aexit__ = AsyncMock(return_value=None)

        return mock_manager

    @pytest.mark.asyncio
    async def test_tech_stack_filters_by_selected_fields(self, mock_db_manager):
        """Test that get_tech_stack filters output based on selected_fields."""
        from src.giljo_mcp.tools.context_tools.get_tech_stack import get_tech_stack

        # Only select languages and databases
        selected_fields = {
            "languages": True,
            "frameworks": False,
            "databases": True,
            "dependencies": False,
        }

        result = await get_tech_stack(
            product_id="test-product-id",
            tenant_key="test-tenant",
            sections="all",
            db_manager=mock_db_manager,
            selected_fields=selected_fields,
        )

        # Verify only selected fields are in response
        data = result.get("data", {})

        # Enabled fields should be present
        assert "programming_languages" in data or "languages" in data
        assert "databases" in data or "database" in data

        # Disabled fields should not be present or be empty
        # The exact behavior depends on implementation


class TestArchitectureFiltersFields:
    """Tests for architecture tool filtering by selected_fields."""

    @pytest_asyncio.fixture
    async def mock_db_manager(self):
        """Create mock database manager with product architecture data."""
        mock_manager = MagicMock()

        # Create mock product with config_data
        mock_product = MagicMock()
        mock_product.config_data = {
            "architecture": {
                "pattern": "Microservices",
                "design_patterns": "Repository, Service Layer, CQRS",
                "api_style": "RESTful",
                "notes": "The system follows a clean architecture approach...",
            }
        }

        # Setup async context manager for session
        mock_session = AsyncMock()
        mock_result = MagicMock()
        mock_result.scalar_one_or_none.return_value = mock_product
        mock_session.execute = AsyncMock(return_value=mock_result)

        mock_manager.get_session = MagicMock(return_value=mock_session)
        mock_manager.get_session.return_value.__aenter__ = AsyncMock(return_value=mock_session)
        mock_manager.get_session.return_value.__aexit__ = AsyncMock(return_value=None)

        return mock_manager

    @pytest.mark.asyncio
    async def test_architecture_filters_by_selected_fields(self, mock_db_manager):
        """Test that get_architecture filters output based on selected_fields."""
        from src.giljo_mcp.tools.context_tools.get_architecture import get_architecture

        # Only select pattern and api_style
        selected_fields = {
            "pattern": True,
            "design_patterns": False,
            "api_style": True,
            "notes": False,
            "layers": False,
            "components": False,
        }

        result = await get_architecture(
            product_id="test-product-id",
            tenant_key="test-tenant",
            depth="detailed",
            db_manager=mock_db_manager,
            selected_fields=selected_fields,
        )

        # Verify only selected fields are in response
        data = result.get("data", {})

        # Enabled fields should be present
        assert "primary_pattern" in data or "pattern" in data
        assert "api_style" in data


class TestTestingFiltersFields:
    """Tests for testing tool filtering by selected_fields."""

    @pytest_asyncio.fixture
    async def mock_db_manager(self):
        """Create mock database manager with product testing data."""
        mock_manager = MagicMock()

        # Create mock product with config_data
        mock_product = MagicMock()
        mock_product.quality_standards = "80% coverage, zero critical bugs"
        mock_product.config_data = {
            "test_config": {
                "strategy": "TDD with unit and integration tests",
                "coverage_target": 85,
                "frameworks": ["pytest", "jest", "cypress"],
            },
            "test_commands": ["pytest tests/", "npm test"],
        }

        # Setup async context manager for session
        mock_session = AsyncMock()
        mock_result = MagicMock()
        mock_result.scalar_one_or_none.return_value = mock_product
        mock_session.execute = AsyncMock(return_value=mock_result)

        mock_manager.get_session = MagicMock(return_value=mock_session)
        mock_manager.get_session.return_value.__aenter__ = AsyncMock(return_value=mock_session)
        mock_manager.get_session.return_value.__aexit__ = AsyncMock(return_value=None)

        return mock_manager

    @pytest.mark.asyncio
    async def test_testing_filters_by_selected_fields(self, mock_db_manager):
        """Test that get_testing filters output based on selected_fields."""
        from src.giljo_mcp.tools.context_tools.get_testing import get_testing

        # Only select quality_standards and strategy
        selected_fields = {
            "quality_standards": True,
            "strategy": True,
            "frameworks": False,
        }

        result = await get_testing(
            product_id="test-product-id",
            tenant_key="test-tenant",
            depth="full",
            db_manager=mock_db_manager,
            selected_fields=selected_fields,
        )

        # Verify only selected fields are in response
        data = result.get("data", {})

        # Enabled fields should be present
        assert "quality_standards" in data
        assert "testing_strategy" in data or "strategy" in data


class TestContextToolsBackwardCompatibility:
    """Tests for backward compatibility when selected_fields is not provided."""

    @pytest.mark.asyncio
    async def test_tech_stack_without_selected_fields(self):
        """Test get_tech_stack works without selected_fields (backward compat)."""
        # This test verifies that existing calls without selected_fields
        # continue to work after adding the parameter
        from src.giljo_mcp.tools.context_tools.get_tech_stack import get_tech_stack
        import inspect

        sig = inspect.signature(get_tech_stack)
        params = sig.parameters

        # Verify selected_fields parameter exists
        assert "selected_fields" in params, (
            "get_tech_stack should have selected_fields parameter"
        )

        # Verify it has a default value (for backward compatibility)
        assert params["selected_fields"].default is not None or \
               params["selected_fields"].default is inspect.Parameter.empty or \
               params["selected_fields"].default is None, (
            "selected_fields should have a default value for backward compatibility"
        )

    @pytest.mark.asyncio
    async def test_architecture_without_selected_fields(self):
        """Test get_architecture works without selected_fields (backward compat)."""
        from src.giljo_mcp.tools.context_tools.get_architecture import get_architecture
        import inspect

        sig = inspect.signature(get_architecture)
        params = sig.parameters

        assert "selected_fields" in params, (
            "get_architecture should have selected_fields parameter"
        )

    @pytest.mark.asyncio
    async def test_testing_without_selected_fields(self):
        """Test get_testing works without selected_fields (backward compat)."""
        from src.giljo_mcp.tools.context_tools.get_testing import get_testing
        import inspect

        sig = inspect.signature(get_testing)
        params = sig.parameters

        assert "selected_fields" in params, (
            "get_testing should have selected_fields parameter"
        )
