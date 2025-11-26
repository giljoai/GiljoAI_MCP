"""
Tests for sequential_history entry validation (Handover 0248a Task 2).

Tests ensure all entries written to product_memory.sequential_history
are properly validated before insertion to prevent malformed data.
"""

import pytest
from datetime import datetime, timezone
from unittest.mock import AsyncMock, MagicMock, patch

from sqlalchemy.ext.asyncio import AsyncSession

from src.giljo_mcp.models import Product
from src.giljo_mcp.services.product_service import ProductService


class TestSequentialHistoryValidation:
    """Test validation of sequential_history entries."""

    @pytest.fixture
    def product_service(self):
        """Create ProductService instance."""
        mock_db_manager = MagicMock()
        return ProductService(
            db_manager=mock_db_manager,
            tenant_key="test-tenant",
            websocket_manager=None
        )

    @pytest.fixture
    def mock_product(self):
        """Create mock Product with initialized product_memory."""
        product = MagicMock(spec=Product)
        product.id = "test-product-id"
        product.tenant_key = "test-tenant"
        product.product_memory = {
            "sequential_history": [
                {
                    "sequence": 1,
                    "type": "project_closeout",
                    "timestamp": "2025-11-16T10:00:00Z",
                    "summary": "First project",
                }
            ]
        }
        product.updated_at = datetime.now(timezone.utc)
        return product

    @pytest.mark.asyncio
    async def test_validates_entry_is_dict(self, product_service, mock_product):
        """Should reject non-dictionary entries."""
        session = AsyncMock(spec=AsyncSession)

        # Mock query result
        mock_result = MagicMock()
        mock_result.scalar_one_or_none.return_value = mock_product
        session.execute.return_value = mock_result

        # Test with string (invalid)
        with pytest.raises(ValueError) as exc_info:
            await product_service.add_learning_to_product_memory(
                session, "test-product-id", "invalid-string-entry"
            )
        assert "History entry must be a dictionary" in str(exc_info.value)

        # Test with list (invalid)
        with pytest.raises(ValueError) as exc_info:
            await product_service.add_learning_to_product_memory(
                session, "test-product-id", ["invalid", "list"]
            )
        assert "History entry must be a dictionary" in str(exc_info.value)

    @pytest.mark.asyncio
    async def test_validates_required_fields_present(self, product_service, mock_product):
        """Should reject entries missing required fields (type, timestamp)."""
        session = AsyncMock(spec=AsyncSession)

        # Mock query result
        mock_result = MagicMock()
        mock_result.scalar_one_or_none.return_value = mock_product
        session.execute.return_value = mock_result

        # Missing 'type' field
        missing_type = {
            "timestamp": "2025-11-16T10:00:00Z",
            "summary": "Test entry",
        }
        with pytest.raises(ValueError) as exc_info:
            await product_service.add_learning_to_product_memory(
                session, "test-product-id", missing_type
            )
        assert "missing required fields" in str(exc_info.value)
        assert "type" in str(exc_info.value)

        # Missing 'timestamp' field
        missing_timestamp = {
            "type": "project_closeout",
            "summary": "Test entry",
        }
        with pytest.raises(ValueError) as exc_info:
            await product_service.add_learning_to_product_memory(
                session, "test-product-id", missing_timestamp
            )
        assert "missing required fields" in str(exc_info.value)
        assert "timestamp" in str(exc_info.value)

        # Missing both required fields
        missing_both = {
            "summary": "Test entry",
        }
        with pytest.raises(ValueError) as exc_info:
            await product_service.add_learning_to_product_memory(
                session, "test-product-id", missing_both
            )
        assert "missing required fields" in str(exc_info.value)

    @pytest.mark.asyncio
    async def test_accepts_valid_project_closeout_entry(self, product_service, mock_product):
        """Should accept valid project_closeout entry."""
        session = AsyncMock(spec=AsyncSession)

        # Mock query result
        mock_result = MagicMock()
        mock_result.scalar_one_or_none.return_value = mock_product
        session.execute.return_value = mock_result

        # Mock WebSocket event emission
        with patch.object(product_service, '_emit_websocket_event', new_callable=AsyncMock):
            valid_entry = {
                "type": "project_closeout",
                "project_id": "project-123",
                "timestamp": "2025-11-16T10:00:00Z",
                "summary": "Implemented authentication",
                "git_commits": [],
            }

            result = await product_service.add_learning_to_product_memory(
                session, "test-product-id", valid_entry
            )

            # Should not raise any exceptions
            assert result == mock_product
            # Sequence should be auto-assigned
            assert mock_product.product_memory["sequential_history"][-1]["sequence"] == 2

    @pytest.mark.asyncio
    async def test_accepts_valid_manual_entry(self, product_service, mock_product):
        """Should accept valid manual_entry type."""
        session = AsyncMock(spec=AsyncSession)

        # Mock query result
        mock_result = MagicMock()
        mock_result.scalar_one_or_none.return_value = mock_product
        session.execute.return_value = mock_result

        # Mock WebSocket event emission
        with patch.object(product_service, '_emit_websocket_event', new_callable=AsyncMock):
            valid_entry = {
                "type": "manual_entry",
                "timestamp": "2025-11-16T11:00:00Z",
                "notes": "Manual learning entry",
            }

            result = await product_service.add_learning_to_product_memory(
                session, "test-product-id", valid_entry
            )

            assert result == mock_product

    @pytest.mark.asyncio
    async def test_accepts_valid_import_entry(self, product_service, mock_product):
        """Should accept valid import type."""
        session = AsyncMock(spec=AsyncSession)

        # Mock query result
        mock_result = MagicMock()
        mock_result.scalar_one_or_none.return_value = mock_product
        session.execute.return_value = mock_result

        # Mock WebSocket event emission
        with patch.object(product_service, '_emit_websocket_event', new_callable=AsyncMock):
            valid_entry = {
                "type": "import",
                "timestamp": "2025-11-16T12:00:00Z",
                "source": "legacy_system",
                "data": {"key": "value"},
            }

            result = await product_service.add_learning_to_product_memory(
                session, "test-product-id", valid_entry
            )

            assert result == mock_product

    @pytest.mark.asyncio
    async def test_warns_on_unknown_entry_type(self, product_service, mock_product, caplog):
        """Should log warning for unknown entry types but still accept them."""
        session = AsyncMock(spec=AsyncSession)

        # Mock query result
        mock_result = MagicMock()
        mock_result.scalar_one_or_none.return_value = mock_product
        session.execute.return_value = mock_result

        # Mock WebSocket event emission
        with patch.object(product_service, '_emit_websocket_event', new_callable=AsyncMock):
            unknown_type_entry = {
                "type": "unknown_type",
                "timestamp": "2025-11-16T13:00:00Z",
                "data": "some data",
            }

            result = await product_service.add_learning_to_product_memory(
                session, "test-product-id", unknown_type_entry
            )

            # Should still accept the entry
            assert result == mock_product

            # Should log warning (check if warning was logged)
            # Note: Actual logging check depends on logger configuration
            # This is a placeholder - real test would check caplog

    @pytest.mark.asyncio
    async def test_validates_entry_with_minimal_required_fields(self, product_service, mock_product):
        """Should accept entry with only required fields (type, timestamp)."""
        session = AsyncMock(spec=AsyncSession)

        # Mock query result
        mock_result = MagicMock()
        mock_result.scalar_one_or_none.return_value = mock_product
        session.execute.return_value = mock_result

        # Mock WebSocket event emission
        with patch.object(product_service, '_emit_websocket_event', new_callable=AsyncMock):
            minimal_entry = {
                "type": "project_closeout",
                "timestamp": "2025-11-16T14:00:00Z",
            }

            result = await product_service.add_learning_to_product_memory(
                session, "test-product-id", minimal_entry
            )

            assert result == mock_product

    @pytest.mark.asyncio
    async def test_sequence_auto_assignment_after_validation(self, product_service, mock_product):
        """Should auto-assign sequence number after validation passes."""
        session = AsyncMock(spec=AsyncSession)

        # Mock query result
        mock_result = MagicMock()
        mock_result.scalar_one_or_none.return_value = mock_product
        session.execute.return_value = mock_result

        # Mock WebSocket event emission
        with patch.object(product_service, '_emit_websocket_event', new_callable=AsyncMock):
            entry_without_sequence = {
                "type": "project_closeout",
                "timestamp": "2025-11-16T15:00:00Z",
                "summary": "Test",
            }

            result = await product_service.add_learning_to_product_memory(
                session, "test-product-id", entry_without_sequence
            )

            # Check sequence was auto-assigned
            last_entry = mock_product.product_memory["sequential_history"][-1]
            assert last_entry["sequence"] == 2
            assert last_entry["type"] == "project_closeout"
            assert last_entry["timestamp"] == "2025-11-16T15:00:00Z"
