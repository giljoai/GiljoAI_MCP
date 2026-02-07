"""
Integration tests for WebSocket events emitted by ProductService.

Handover 0139a: WebSocket Events - Backend Emission

Tests verify that ProductService emits correct WebSocket events when:
- Product memory is updated (product:memory:updated)
- Learning entries are added (product:learning:added)

PRODUCTION-GRADE: Validates real-time event delivery with tenant isolation.
"""

from datetime import datetime, timezone
from unittest.mock import AsyncMock, MagicMock
from uuid import uuid4

import pytest

from src.giljo_mcp.services.product_service import ProductService


@pytest.fixture
def tenant_key():
    """Generate unique tenant key for each test."""
    return f"test_tenant_{uuid4().hex[:8]}"


@pytest.fixture
def mock_websocket_manager():
    """
    Create mock WebSocketManager for testing.

    Captures broadcast_to_tenant calls without actual WebSocket connections.
    """
    manager = MagicMock()
    manager.broadcast_to_tenant = AsyncMock(return_value=1)
    return manager


@pytest.fixture
async def product_service_with_websocket(db_manager, tenant_key, mock_websocket_manager):
    """
    Create ProductService with WebSocket dependency injection.

    Returns:
        ProductService instance with mocked WebSocket manager
    """
    service = ProductService(db_manager, tenant_key)

    # Inject WebSocket manager (will be done via dependency injection in implementation)
    service._websocket_manager = mock_websocket_manager

    return service


@pytest.mark.asyncio
class TestProductMemoryWebSocketEvents:
    """
    Test 1: Product memory update emits WebSocket event
    Validates product:memory:updated event when product_memory changes
    """

    async def test_update_product_memory_emits_websocket_event(
        self, db_session, tenant_key, product_service_with_websocket, mock_websocket_manager
    ):
        """
        PRODUCTION-GRADE: Verify product:memory:updated event emission

        GIVEN: A product with initial memory state
        WHEN: Product memory is updated via update_product()
        THEN: WebSocket event is emitted to tenant with correct payload
        """
        # ARRANGE: Create product
        service = product_service_with_websocket

        create_result = await service.create_product(
            name="WebSocket Test Product", description="Testing WebSocket events"
        )
        assert create_result["success"] is True
        product_id = create_result["product_id"]

        # Reset mock to ignore creation event
        mock_websocket_manager.broadcast_to_tenant.reset_mock()

        # ACT: Update product memory
        updated_memory = {
            "github": {"enabled": True, "repo_url": "https://github.com/test/repo"},
            "learnings": [{"sequence": 1, "summary": "Initial learning"}],
            "context": {"summary": "Updated context"},
        }

        update_result = await service.update_product(product_id=product_id, product_memory=updated_memory)

        # ASSERT: Update succeeded
        assert update_result["success"] is True

        # ASSERT: WebSocket event emitted
        mock_websocket_manager.broadcast_to_tenant.assert_called_once()

        # Verify event parameters
        call_args = mock_websocket_manager.broadcast_to_tenant.call_args
        assert call_args.kwargs["tenant_key"] == tenant_key
        assert call_args.kwargs["event_type"] == "product:memory:updated"

        # Verify event payload
        event_data = call_args.kwargs["data"]
        assert event_data["product_id"] == product_id
        assert "product_memory" in event_data
        assert event_data["product_memory"]["github"]["enabled"] is True
        assert "timestamp" in event_data

    async def test_update_product_memory_event_contains_correct_data(
        self, product_service_with_websocket, mock_websocket_manager, tenant_key
    ):
        """
        PRODUCTION-GRADE: Validate event payload structure and content

        GIVEN: A product to update
        WHEN: Product memory is modified
        THEN: Event payload contains all required fields with correct types
        """
        # ARRANGE
        service = product_service_with_websocket

        create_result = await service.create_product(name="Payload Test Product")
        product_id = create_result["product_id"]

        mock_websocket_manager.broadcast_to_tenant.reset_mock()

        # ACT
        updated_memory = {"github": {"enabled": False}, "learnings": [], "context": {"token_count": 5000}}

        await service.update_product(product_id=product_id, product_memory=updated_memory)

        # ASSERT: Event payload structure
        call_args = mock_websocket_manager.broadcast_to_tenant.call_args
        event_data = call_args.kwargs["data"]

        # Required fields
        assert "product_id" in event_data
        assert "tenant_key" in event_data
        assert "timestamp" in event_data
        assert "product_memory" in event_data

        # Field types
        assert isinstance(event_data["product_id"], str)
        assert isinstance(event_data["tenant_key"], str)
        assert isinstance(event_data["timestamp"], str)
        assert isinstance(event_data["product_memory"], dict)

        # Timestamp format (ISO 8601)
        timestamp = datetime.fromisoformat(event_data["timestamp"].replace("Z", "+00:00"))
        assert timestamp.tzinfo is not None

    """
    Test 2: Learning addition emits WebSocket event
    Validates product:learning:added event when learning entry is appended
    """

    async def test_add_learning_emits_websocket_event(
        self, db_session, db_manager, tenant_key, product_service_with_websocket, mock_websocket_manager
    ):
        """
        PRODUCTION-GRADE: Verify product:learning:added event emission

        GIVEN: A product with product_memory initialized
        WHEN: Learning entry is added via add_learning_to_product_memory()
        THEN: WebSocket event is emitted with learning details
        """
        # ARRANGE
        service = product_service_with_websocket

        create_result = await service.create_product(name="Learning Test Product")
        product_id = create_result["product_id"]

        mock_websocket_manager.broadcast_to_tenant.reset_mock()

        # ACT: Add learning entry
        learning_entry = {
            "type": "project_closeout",
            "project_id": str(uuid4()),
            "summary": "Implemented authentication system",
            "key_outcomes": ["JWT auth", "Role-based access"],
            "timestamp": datetime.now(timezone.utc).isoformat(),
        }

        # Use internal helper method (via session)
        async with db_manager.get_session_async() as session:
            product = await service.add_learning_to_product_memory(
                session=session, product_id=product_id, learning_entry=learning_entry
            )
            await session.commit()

        # ASSERT: WebSocket event emitted
        mock_websocket_manager.broadcast_to_tenant.assert_called_once()

        # Verify event parameters
        call_args = mock_websocket_manager.broadcast_to_tenant.call_args
        assert call_args.kwargs["tenant_key"] == tenant_key
        assert call_args.kwargs["event_type"] == "product:learning:added"

        # Verify event payload
        event_data = call_args.kwargs["data"]
        assert event_data["product_id"] == product_id
        assert "learning" in event_data
        assert event_data["learning"]["summary"] == "Implemented authentication system"
        assert event_data["learning"]["sequence"] == 1  # Auto-assigned

    async def test_add_learning_event_includes_sequence_number(
        self, db_session, db_manager, product_service_with_websocket, mock_websocket_manager, tenant_key
    ):
        """
        PRODUCTION-GRADE: Verify learning event includes auto-incremented sequence

        GIVEN: Multiple learning entries
        WHEN: Each learning is added
        THEN: Event includes correct sequence number (auto-incremented)
        """
        # ARRANGE
        service = product_service_with_websocket

        create_result = await service.create_product(name="Sequence Test Product")
        product_id = create_result["product_id"]

        mock_websocket_manager.broadcast_to_tenant.reset_mock()

        # ACT: Add 3 learning entries
        for i in range(3):
            async with db_manager.get_session_async() as session:
                learning_entry = {
                    "type": "project_closeout",
                    "project_id": str(uuid4()),
                    "summary": f"Learning {i + 1}",
                    "timestamp": datetime.now(timezone.utc).isoformat(),
                }

                await service.add_learning_to_product_memory(
                    session=session, product_id=product_id, learning_entry=learning_entry
                )
                await session.commit()

        # ASSERT: 3 events emitted
        assert mock_websocket_manager.broadcast_to_tenant.call_count == 3

        # Verify sequence numbers
        calls = mock_websocket_manager.broadcast_to_tenant.call_args_list
        for i, call in enumerate(calls):
            event_data = call.kwargs["data"]
            assert event_data["learning"]["sequence"] == i + 1

    """
    Test 4: Multi-tenant isolation in WebSocket events
    Validates events are scoped to correct tenant
    """

    async def test_websocket_events_respect_tenant_isolation(
        self, db_session, product_service_with_websocket, mock_websocket_manager
    ):
        """
        PRODUCTION-GRADE: Verify WebSocket events respect multi-tenant isolation

        GIVEN: Products from different tenants
        WHEN: ProductService emits events
        THEN: Events are broadcast only to correct tenant_key
        """
        # ARRANGE
        service = product_service_with_websocket
        tenant_a = service.tenant_key

        create_result = await service.create_product(name="Tenant A Product")
        product_id = create_result["product_id"]

        mock_websocket_manager.broadcast_to_tenant.reset_mock()

        # ACT: Update product memory
        await service.update_product(
            product_id=product_id,
            product_memory={
                "github": {},
                "learnings": [{"sequence": 1, "summary": "Tenant A learning"}],
                "context": {},
            },
        )

        # ASSERT: Event broadcast to correct tenant
        call_args = mock_websocket_manager.broadcast_to_tenant.call_args
        assert call_args.kwargs["tenant_key"] == tenant_a

        # Verify no cross-tenant leakage by checking tenant_key in data
        event_data = call_args.kwargs["data"]
        assert event_data["tenant_key"] == tenant_a

    """
    Test 5: Event payload validation
    Validates event payloads conform to expected schema
    """

    async def test_memory_updated_event_payload_schema(
        self, product_service_with_websocket, mock_websocket_manager, tenant_key
    ):
        """
        PRODUCTION-GRADE: Validate product:memory:updated event schema

        GIVEN: A product memory update
        WHEN: WebSocket event is emitted
        THEN: Payload conforms to expected schema

        Expected schema:
        {
            "product_id": str,
            "tenant_key": str,
            "timestamp": str (ISO 8601),
            "product_memory": {
                "github": dict,
                "learnings": list,
                "context": dict
            }
        }
        """
        # ARRANGE
        service = product_service_with_websocket

        create_result = await service.create_product(name="Schema Test Product")
        product_id = create_result["product_id"]

        mock_websocket_manager.broadcast_to_tenant.reset_mock()

        # ACT
        updated_memory = {
            "github": {"enabled": True},
            "learnings": [{"sequence": 1, "summary": "Test"}],
            "context": {"summary": "Test context"},
        }

        await service.update_product(product_id=product_id, product_memory=updated_memory)

        # ASSERT: Schema validation
        call_args = mock_websocket_manager.broadcast_to_tenant.call_args
        event_data = call_args.kwargs["data"]

        # Required fields
        required_fields = ["product_id", "tenant_key", "timestamp", "product_memory"]
        for field in required_fields:
            assert field in event_data, f"Missing required field: {field}"

        # product_memory structure
        assert "github" in event_data["product_memory"]
        assert "learnings" in event_data["product_memory"]
        assert "context" in event_data["product_memory"]

        # Types
        assert isinstance(event_data["product_id"], str)
        assert isinstance(event_data["tenant_key"], str)
        assert isinstance(event_data["timestamp"], str)
        assert isinstance(event_data["product_memory"], dict)
        assert isinstance(event_data["product_memory"]["github"], dict)
        assert isinstance(event_data["product_memory"]["learnings"], list)
        assert isinstance(event_data["product_memory"]["context"], dict)

    async def test_learning_added_event_payload_schema(
        self, db_session, db_manager, product_service_with_websocket, mock_websocket_manager, tenant_key
    ):
        """
        PRODUCTION-GRADE: Validate product:learning:added event schema

        Expected schema:
        {
            "product_id": str,
            "tenant_key": str,
            "timestamp": str (ISO 8601),
            "learning": {
                "sequence": int,
                "type": str,
                "summary": str,
                ...
            }
        }
        """
        # ARRANGE
        service = product_service_with_websocket

        create_result = await service.create_product(name="Learning Schema Test")
        product_id = create_result["product_id"]

        mock_websocket_manager.broadcast_to_tenant.reset_mock()

        # ACT
        async with db_manager.get_session_async() as session:
            learning_entry = {
                "type": "project_closeout",
                "project_id": str(uuid4()),
                "summary": "Schema validation test",
                "timestamp": datetime.now(timezone.utc).isoformat(),
            }

            await service.add_learning_to_product_memory(
                session=session, product_id=product_id, learning_entry=learning_entry
            )
            await session.commit()

        # ASSERT: Schema validation
        call_args = mock_websocket_manager.broadcast_to_tenant.call_args
        event_data = call_args.kwargs["data"]

        # Required fields
        required_fields = ["product_id", "tenant_key", "timestamp", "learning"]
        for field in required_fields:
            assert field in event_data, f"Missing required field: {field}"

        # Learning entry structure
        assert "sequence" in event_data["learning"]
        assert "type" in event_data["learning"]
        assert "summary" in event_data["learning"]

        # Types
        assert isinstance(event_data["learning"]["sequence"], int)
        assert isinstance(event_data["learning"]["type"], str)
        assert isinstance(event_data["learning"]["summary"], str)

    """
    Test 6: Event emission failures don't block operations
    Validates graceful degradation when WebSocket fails
    """

    async def test_websocket_failure_does_not_block_update(
        self, product_service_with_websocket, mock_websocket_manager, tenant_key
    ):
        """
        PRODUCTION-GRADE: Verify operations succeed even if WebSocket fails

        GIVEN: WebSocket manager that throws exceptions
        WHEN: ProductService performs update
        THEN: Database update succeeds, WebSocket failure is logged
        """
        # ARRANGE
        service = product_service_with_websocket

        create_result = await service.create_product(name="Resilience Test Product")
        product_id = create_result["product_id"]

        # Make WebSocket broadcast fail
        mock_websocket_manager.broadcast_to_tenant.side_effect = Exception("WebSocket connection lost")

        # ACT: Update should succeed despite WebSocket failure
        update_result = await service.update_product(
            product_id=product_id,
            product_memory={"github": {}, "learnings": [{"sequence": 1, "summary": "Resilience test"}], "context": {}},
        )

        # ASSERT: Database update succeeded
        assert update_result["success"] is True

        # Verify WebSocket was attempted
        mock_websocket_manager.broadcast_to_tenant.assert_called_once()


@pytest.mark.asyncio
class TestWebSocketEventEdgeCases:
    """Edge cases and error scenarios for WebSocket events"""

    async def test_no_websocket_manager_does_not_crash(self, db_session, db_manager, tenant_key):
        """
        PRODUCTION-GRADE: Verify service works without WebSocket manager

        GIVEN: ProductService without WebSocket dependency
        WHEN: Operations are performed
        THEN: Operations succeed without WebSocket events
        """
        # ARRANGE: Service without WebSocket manager
        service = ProductService(db_manager, tenant_key)
        # No _websocket_manager injected

        # ACT: Create and update product
        create_result = await service.create_product(name="No WebSocket Test")
        assert create_result["success"] is True

        product_id = create_result["product_id"]

        update_result = await service.update_product(
            product_id=product_id, product_memory={"github": {}, "learnings": [], "context": {"summary": "Test"}}
        )

        # ASSERT: Operations succeed
        assert update_result["success"] is True

    async def test_empty_product_memory_update_emits_event(
        self, product_service_with_websocket, mock_websocket_manager, tenant_key
    ):
        """
        PRODUCTION-GRADE: Verify event emission for empty memory structure

        GIVEN: A product with populated memory
        WHEN: Memory is updated to empty structure
        THEN: Event is emitted with empty structure
        """
        # ARRANGE
        service = product_service_with_websocket

        create_result = await service.create_product(
            name="Empty Memory Test",
            product_memory={
                "github": {"enabled": True},
                "learnings": [{"sequence": 1, "summary": "Test"}],
                "context": {"summary": "Test"},
            },
        )
        product_id = create_result["product_id"]

        mock_websocket_manager.broadcast_to_tenant.reset_mock()

        # ACT: Clear memory
        await service.update_product(
            product_id=product_id, product_memory={"github": {}, "learnings": [], "context": {}}
        )

        # ASSERT: Event emitted
        mock_websocket_manager.broadcast_to_tenant.assert_called_once()

        call_args = mock_websocket_manager.broadcast_to_tenant.call_args
        event_data = call_args.kwargs["data"]

        assert event_data["product_memory"]["github"] == {}
        assert event_data["product_memory"]["learnings"] == []
        assert event_data["product_memory"]["context"] == {}
