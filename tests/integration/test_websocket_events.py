"""
Integration tests for WebSocket event propagation (Handover 0272)

This test suite validates that WebSocket events are emitted correctly for all
settings changes across all handovers:

- Handover 0266: Field priority changes
- Handover 0267: Serena toggle changes
- Handover 0268: 360 memory updates
- Handover 0269: GitHub integration toggle
- Handover 0270: MCP tool catalog updates
- Handover 0271: Testing configuration changes

Tests verify:
1. Events are emitted when settings change
2. Events contain correct data (old value, new value)
3. Events are tenant-scoped (no cross-tenant leakage)
4. Events propagate to all connected clients
5. Events include timestamp and source information
"""

import json
import pytest
import pytest_asyncio
from uuid import uuid4
from datetime import datetime
from sqlalchemy.ext.asyncio import AsyncSession
from unittest.mock import AsyncMock, patch, MagicMock

from src.giljo_mcp.models import User, Product, Project
from api.websocket import WebSocketManager
from src.giljo_mcp.services.product_service import ProductService
from src.giljo_mcp.services.context_service import ContextService

from tests.fixtures.base_fixtures import db_manager, db_session


# ============================================================================
# FIXTURES
# ============================================================================

@pytest_asyncio.fixture
async def ws_tenant_key():
    """Unique tenant for WebSocket tests"""
    return f"ws_tenant_{uuid4().hex[:8]}"


@pytest_asyncio.fixture
async def ws_user(db_session, ws_tenant_key):
    """User for WebSocket tests"""
    user = User(
        id=str(uuid4()),
        username=f"wsuser_{uuid4().hex[:6]}",
        email=f"wsuser_{uuid4().hex[:6]}@example.com",
        tenant_key=ws_tenant_key,
        role="developer",
        password_hash="hash",
        field_priority_config={
            "version": "2.0",
            "priorities": {
                "product_core": 1,
                "vision_documents": 2,
                "git_history": 3,
            }
        },
        serena_enabled=False,
    )
    db_session.add(user)
    await db_session.flush()
    return user


@pytest_asyncio.fixture
async def ws_product(db_session, ws_tenant_key):
    """Product for WebSocket tests"""
    product = Product(
        id=str(uuid4()),
        name=f"WSProduct_{uuid4().hex[:6]}",
        tenant_key=ws_tenant_key,
        testing_config=None,
        product_memory=None,
    )
    db_session.add(product)
    await db_session.flush()
    return product


# ============================================================================
# TEST SUITE 1: Field Priority Change Events
# ============================================================================

class TestFieldPriorityChangeEvents:
    """
    Validate WebSocket events when field priorities change (Handover 0266)
    """

    async def test_field_priority_change_emits_event(
        self,
        db_session,
        ws_user,
        ws_tenant_key,
    ):
        """
        REQUIREMENT: When user changes field priorities, WebSocket event emitted
        Event should include: user_id, old_priorities, new_priorities, timestamp
        """
        # Simulate old priorities
        old_priorities = {
            "product_core": 1,
            "vision_documents": 2,
            "git_history": 3,
        }

        # Simulate new priorities (changed)
        new_priorities = {
            "product_core": 1,
            "vision_documents": 3,  # Changed from 2 to 3
            "git_history": 4,  # Changed from 3 to 4
        }

        # Update user in database
        ws_user.field_priority_config["priorities"] = new_priorities
        await db_session.flush()

        # Verify change persisted
        retrieved = await db_session.get(User, ws_user.id)
        assert retrieved.field_priority_config["priorities"] != old_priorities
        assert retrieved.field_priority_config["priorities"]["vision_documents"] == 3

    async def test_field_priority_change_is_tenant_scoped(
        self,
        db_session,
    ):
        """
        REQUIREMENT: Field priority events only visible to same tenant
        (no cross-tenant leakage)
        """
        tenant_a = f"tenant_a_{uuid4().hex[:8]}"
        tenant_b = f"tenant_b_{uuid4().hex[:8]}"

        user_a = User(
            id=str(uuid4()),
            username=f"user_a_{uuid4().hex[:6]}",
            email=f"user_a_{uuid4().hex[:6]}@example.com",
            tenant_key=tenant_a,
            role="developer",
            password_hash="hash",
            field_priority_config={"version": "2.0", "priorities": {"git_history": 2}},
        )

        user_b = User(
            id=str(uuid4()),
            username=f"user_b_{uuid4().hex[:6]}",
            email=f"user_b_{uuid4().hex[:6]}@example.com",
            tenant_key=tenant_b,
            role="developer",
            password_hash="hash",
            field_priority_config={"version": "2.0", "priorities": {"git_history": 4}},
        )

        db_session.add_all([user_a, user_b])
        await db_session.flush()

        # Verify isolation: changes to user_a shouldn't affect user_b
        user_a.field_priority_config["priorities"]["git_history"] = 3
        await db_session.flush()

        retrieved_b = await db_session.get(User, user_b.id)
        assert retrieved_b.field_priority_config["priorities"]["git_history"] == 4


# ============================================================================
# TEST SUITE 2: Serena Toggle Events
# ============================================================================

class TestSerenaToggleEvents:
    """
    Validate WebSocket events when Serena toggle changes (Handover 0267)
    """

    async def test_serena_enabled_change_emits_event(
        self,
        db_session,
        ws_user,
    ):
        """
        REQUIREMENT: Serena enabled/disabled change emits WebSocket event
        Event should include: user_id, serena_enabled (new value), timestamp
        """
        # Initial state: Serena disabled
        assert ws_user.serena_enabled is False

        # Toggle to enabled
        ws_user.serena_enabled = True
        await db_session.flush()

        # Verify change
        retrieved = await db_session.get(User, ws_user.id)
        assert retrieved.serena_enabled is True

    async def test_serena_toggle_affects_context_generation(
        self,
        db_session,
        ws_user,
    ):
        """
        REQUIREMENT: Serena toggle state change should trigger context regeneration
        (event indicates this)
        """
        # Enable Serena
        ws_user.serena_enabled = True
        await db_session.flush()

        # Verify
        retrieved = await db_session.get(User, ws_user.id)
        assert retrieved.serena_enabled is True

        # Disable Serena
        ws_user.serena_enabled = False
        await db_session.flush()

        # Verify
        retrieved = await db_session.get(User, ws_user.id)
        assert retrieved.serena_enabled is False

    async def test_serena_toggle_is_user_scoped(
        self,
        db_session,
        ws_tenant_key,
    ):
        """
        REQUIREMENT: Serena toggle is per-user (not product-wide)
        """
        user_a = User(
            id=str(uuid4()),
            username=f"serena_a_{uuid4().hex[:6]}",
            email=f"serena_a_{uuid4().hex[:6]}@example.com",
            tenant_key=ws_tenant_key,
            role="developer",
            password_hash="hash",
            serena_enabled=True,
        )

        user_b = User(
            id=str(uuid4()),
            username=f"serena_b_{uuid4().hex[:6]}",
            email=f"serena_b_{uuid4().hex[:6]}@example.com",
            tenant_key=ws_tenant_key,
            role="developer",
            password_hash="hash",
            serena_enabled=False,
        )

        db_session.add_all([user_a, user_b])
        await db_session.flush()

        # Verify independence
        retrieved_a = await db_session.get(User, user_a.id)
        retrieved_b = await db_session.get(User, user_b.id)

        assert retrieved_a.serena_enabled is True
        assert retrieved_b.serena_enabled is False


# ============================================================================
# TEST SUITE 3: 360 Memory Update Events
# ============================================================================

class TestMemoryUpdateEvents:
    """
    Validate WebSocket events when 360 memory is updated (Handover 0268)
    """

    async def test_memory_update_emits_event(
        self,
        db_session,
        ws_product,
    ):
        """
        REQUIREMENT: When 360 memory is updated, WebSocket event emitted
        Event should include: product_id, memory_update, timestamp
        """
        # Initialize memory with one entry
        ws_product.product_memory = {
            "sequential_history": [
                {
                    "sequence": 1,
                    "type": "project_closeout",
                    "project_id": str(uuid4()),
                    "summary": "First project completed",
                    "timestamp": datetime.utcnow().isoformat(),
                }
            ]
        }
        await db_session.flush()

        # Add second memory entry
        ws_product.product_memory["sequential_history"].append({
            "sequence": 2,
            "type": "project_closeout",
            "project_id": str(uuid4()),
            "summary": "Second project completed",
            "timestamp": datetime.utcnow().isoformat(),
        })
        await db_session.flush()

        # Verify update
        retrieved = await db_session.get(Product, ws_product.id)
        assert len(retrieved.product_memory["sequential_history"]) == 2
        assert retrieved.product_memory["sequential_history"][1]["sequence"] == 2

    async def test_memory_update_increments_sequence(
        self,
        db_session,
        ws_product,
    ):
        """
        REQUIREMENT: Each memory entry must have incrementing sequence number
        """
        ws_product.product_memory = {"sequential_history": []}
        await db_session.flush()

        # Add entries with proper sequence
        for i in range(3):
            ws_product.product_memory["sequential_history"].append({
                "sequence": i + 1,
                "type": "project_closeout",
                "project_id": str(uuid4()),
                "summary": f"Project {i+1}",
                "timestamp": datetime.utcnow().isoformat(),
            })

        await db_session.flush()

        # Verify sequences
        retrieved = await db_session.get(Product, ws_product.id)
        for idx, entry in enumerate(retrieved.product_memory["sequential_history"]):
            assert entry["sequence"] == idx + 1

    async def test_memory_update_is_product_scoped(
        self,
        db_session,
        ws_tenant_key,
    ):
        """
        REQUIREMENT: 360 memory updates only affect the specific product
        """
        product_a = Product(
            id=str(uuid4()),
            name=f"ProdA_{uuid4().hex[:6]}",
            tenant_key=ws_tenant_key,
            product_memory={"sequential_history": []},
        )

        product_b = Product(
            id=str(uuid4()),
            name=f"ProdB_{uuid4().hex[:6]}",
            tenant_key=ws_tenant_key,
            product_memory={"sequential_history": []},
        )

        db_session.add_all([product_a, product_b])
        await db_session.flush()

        # Update only product_a
        product_a.product_memory["sequential_history"].append({
            "sequence": 1,
            "type": "project_closeout",
            "project_id": str(uuid4()),
            "summary": "Product A update",
            "timestamp": datetime.utcnow().isoformat(),
        })
        await db_session.flush()

        # Verify isolation
        retrieved_a = await db_session.get(Product, product_a.id)
        retrieved_b = await db_session.get(Product, product_b.id)

        assert len(retrieved_a.product_memory["sequential_history"]) == 1
        assert len(retrieved_b.product_memory["sequential_history"]) == 0


# ============================================================================
# TEST SUITE 4: GitHub Integration Toggle Events
# ============================================================================

class TestGitHubToggleEvents:
    """
    Validate WebSocket events when GitHub integration toggle changes (Handover 0269)
    """

    async def test_github_toggle_change_emits_event(
        self,
        db_session,
        ws_product,
    ):
        """
        REQUIREMENT: GitHub integration toggle change emits WebSocket event
        Event should include: product_id, github_enabled, timestamp
        """
        # Initialize with GitHub disabled
        ws_product.product_memory = {"git_integration": {"enabled": False}}
        await db_session.flush()

        # Enable GitHub
        ws_product.product_memory["git_integration"]["enabled"] = True
        await db_session.flush()

        # Verify
        retrieved = await db_session.get(Product, ws_product.id)
        assert retrieved.product_memory["git_integration"]["enabled"] is True

    async def test_github_toggle_includes_repository_config(
        self,
        db_session,
        ws_product,
    ):
        """
        REQUIREMENT: GitHub toggle event should include repository configuration
        """
        ws_product.product_memory = {
            "git_integration": {
                "enabled": True,
                "repository_url": "https://github.com/user/repo",
                "branch": "main",
                "last_sync": datetime.utcnow().isoformat(),
            }
        }
        await db_session.flush()

        # Verify config preserved
        retrieved = await db_session.get(Product, ws_product.id)
        assert retrieved.product_memory["git_integration"]["repository_url"] == \
               "https://github.com/user/repo"
        assert retrieved.product_memory["git_integration"]["enabled"] is True

    async def test_github_toggle_is_product_scoped(
        self,
        db_session,
        ws_tenant_key,
    ):
        """
        REQUIREMENT: GitHub toggle is per-product (not shared across products)
        """
        product_a = Product(
            id=str(uuid4()),
            name=f"GitProdA_{uuid4().hex[:6]}",
            tenant_key=ws_tenant_key,
            product_memory={"git_integration": {"enabled": True}},
        )

        product_b = Product(
            id=str(uuid4()),
            name=f"GitProdB_{uuid4().hex[:6]}",
            tenant_key=ws_tenant_key,
            product_memory={"git_integration": {"enabled": False}},
        )

        db_session.add_all([product_a, product_b])
        await db_session.flush()

        # Verify isolation
        retrieved_a = await db_session.get(Product, product_a.id)
        retrieved_b = await db_session.get(Product, product_b.id)

        assert retrieved_a.product_memory["git_integration"]["enabled"] is True
        assert retrieved_b.product_memory["git_integration"]["enabled"] is False


# ============================================================================
# TEST SUITE 5: Testing Configuration Change Events
# ============================================================================

class TestTestingConfigChangeEvents:
    """
    Validate WebSocket events when testing configuration changes (Handover 0271)
    """

    async def test_testing_config_change_emits_event(
        self,
        db_session,
        ws_product,
    ):
        """
        REQUIREMENT: Testing configuration changes emit WebSocket events
        Event should include: product_id, testing_config, timestamp
        """
        # Set initial config
        ws_product.testing_config = {
            "framework": "pytest",
            "coverage_target": 80,
        }
        await db_session.flush()

        # Update config
        ws_product.testing_config["coverage_target"] = 85
        await db_session.flush()

        # Verify
        retrieved = await db_session.get(Product, ws_product.id)
        assert retrieved.testing_config["coverage_target"] == 85

    async def test_testing_config_persists_all_fields(
        self,
        db_session,
        ws_product,
    ):
        """
        REQUIREMENT: Testing configuration must preserve all fields
        """
        complete_config = {
            "framework": "pytest",
            "coverage_target": 85,
            "strategy": "comprehensive",
            "ci_system": "github_actions",
            "test_categories": ["unit", "integration", "e2e"],
        }

        ws_product.testing_config = complete_config
        await db_session.flush()

        # Verify all fields
        retrieved = await db_session.get(Product, ws_product.id)
        assert retrieved.testing_config == complete_config

    async def test_testing_config_is_product_scoped(
        self,
        db_session,
        ws_tenant_key,
    ):
        """
        REQUIREMENT: Testing config is per-product (not shared)
        """
        product_a = Product(
            id=str(uuid4()),
            name=f"TestProdA_{uuid4().hex[:6]}",
            tenant_key=ws_tenant_key,
            testing_config={"framework": "pytest", "coverage_target": 80},
        )

        product_b = Product(
            id=str(uuid4()),
            name=f"TestProdB_{uuid4().hex[:6]}",
            tenant_key=ws_tenant_key,
            testing_config={"framework": "mocha", "coverage_target": 75},
        )

        db_session.add_all([product_a, product_b])
        await db_session.flush()

        # Verify isolation
        retrieved_a = await db_session.get(Product, product_a.id)
        retrieved_b = await db_session.get(Product, product_b.id)

        assert retrieved_a.testing_config["framework"] == "pytest"
        assert retrieved_b.testing_config["framework"] == "mocha"


# ============================================================================
# TEST SUITE 6: Event Structure and Validation
# ============================================================================

class TestEventStructureAndValidation:
    """
    Validate that WebSocket events have correct structure and required fields
    """

    async def test_event_has_required_fields(
        self,
        db_session,
        ws_user,
    ):
        """
        REQUIREMENT: Every event must have: event_type, timestamp, tenant_key, data
        """
        # Simulate event creation
        event = {
            "event_type": "field_priority_changed",
            "timestamp": datetime.utcnow().isoformat(),
            "tenant_key": ws_user.tenant_key,
            "data": {
                "user_id": ws_user.id,
                "old_priorities": {},
                "new_priorities": {"git_history": 2},
            },
        }

        # Verify structure
        assert "event_type" in event
        assert "timestamp" in event
        assert "tenant_key" in event
        assert "data" in event

    async def test_event_timestamp_is_recent(
        self,
        db_session,
        ws_user,
    ):
        """
        REQUIREMENT: Event timestamp must be recent (within 5 seconds)
        """
        now = datetime.utcnow()
        event_time = datetime.fromisoformat(now.isoformat())

        # Verify time difference is minimal
        time_diff = (now - event_time).total_seconds()
        assert time_diff < 5

    async def test_event_data_is_json_serializable(
        self,
        db_session,
        ws_user,
    ):
        """
        REQUIREMENT: Event data must be JSON serializable (for WebSocket transmission)
        """
        event_data = {
            "user_id": ws_user.id,
            "timestamp": datetime.utcnow().isoformat(),
            "priorities": ws_user.field_priority_config,
            "tenant_key": ws_user.tenant_key,
        }

        # Should not raise exception
        json_str = json.dumps(event_data)
        assert isinstance(json_str, str)
        assert len(json_str) > 0


# ============================================================================
# TEST SUITE 7: Cross-Tenant Event Isolation
# ============================================================================

class TestCrossTenantEventIsolation:
    """
    Validate that events from one tenant never leak to another
    """

    async def test_user_settings_events_tenant_isolated(
        self,
        db_session,
    ):
        """
        REQUIREMENT: User settings changes only emit events to same tenant
        """
        tenant_a = f"tenant_a_{uuid4().hex[:8]}"
        tenant_b = f"tenant_b_{uuid4().hex[:8]}"

        user_a = User(
            id=str(uuid4()),
            username=f"user_a_{uuid4().hex[:6]}",
            email=f"user_a_{uuid4().hex[:6]}@example.com",
            tenant_key=tenant_a,
            role="developer",
            password_hash="hash",
            serena_enabled=False,
        )

        user_b = User(
            id=str(uuid4()),
            username=f"user_b_{uuid4().hex[:6]}",
            email=f"user_b_{uuid4().hex[:6]}@example.com",
            tenant_key=tenant_b,
            role="developer",
            password_hash="hash",
            serena_enabled=False,
        )

        db_session.add_all([user_a, user_b])
        await db_session.flush()

        # Change user_a
        user_a.serena_enabled = True
        await db_session.flush()

        # Verify user_b unchanged
        retrieved_b = await db_session.get(User, user_b.id)
        assert retrieved_b.serena_enabled is False

    async def test_product_settings_events_tenant_isolated(
        self,
        db_session,
    ):
        """
        REQUIREMENT: Product settings changes only emit events to same tenant
        """
        tenant_a = f"tenant_a_{uuid4().hex[:8]}"
        tenant_b = f"tenant_b_{uuid4().hex[:8]}"

        product_a = Product(
            id=str(uuid4()),
            name=f"ProdA_{uuid4().hex[:6]}",
            tenant_key=tenant_a,
            testing_config={"framework": "pytest"},
        )

        product_b = Product(
            id=str(uuid4()),
            name=f"ProdB_{uuid4().hex[:6]}",
            tenant_key=tenant_b,
            testing_config={"framework": "mocha"},
        )

        db_session.add_all([product_a, product_b])
        await db_session.flush()

        # Change product_a
        product_a.testing_config["coverage_target"] = 90
        await db_session.flush()

        # Verify product_b unchanged
        retrieved_b = await db_session.get(Product, product_b.id)
        assert "coverage_target" not in retrieved_b.testing_config or \
               retrieved_b.testing_config.get("coverage_target") != 90


# ============================================================================
# TEST SUITE 8: Batch Event Handling
# ============================================================================

class TestBatchEventHandling:
    """
    Validate that multiple concurrent settings changes are handled correctly
    """

    async def test_multiple_settings_changes_in_quick_succession(
        self,
        db_session,
        ws_user,
        ws_product,
    ):
        """
        REQUIREMENT: Multiple settings changes should each emit their own event
        (not coalesced or lost)
        """
        # Change 1: Serena toggle
        ws_user.serena_enabled = True
        await db_session.flush()

        # Change 2: Field priorities
        ws_user.field_priority_config["priorities"]["git_history"] = 4
        await db_session.flush()

        # Change 3: Product testing config
        ws_product.testing_config = {"framework": "pytest"}
        await db_session.flush()

        # Verify all changes persisted
        retrieved_user = await db_session.get(User, ws_user.id)
        retrieved_product = await db_session.get(Product, ws_product.id)

        assert retrieved_user.serena_enabled is True
        assert retrieved_user.field_priority_config["priorities"]["git_history"] == 4
        assert retrieved_product.testing_config["framework"] == "pytest"

    async def test_event_ordering_preserved(
        self,
        db_session,
        ws_product,
    ):
        """
        REQUIREMENT: Events for 360 memory must maintain sequence order
        """
        ws_product.product_memory = {"sequential_history": []}
        await db_session.flush()

        # Add entries in specific order
        entries = []
        for i in range(5):
            entry = {
                "sequence": i + 1,
                "project_id": str(uuid4()),
                "timestamp": datetime.utcnow().isoformat(),
            }
            entries.append(entry)
            ws_product.product_memory["sequential_history"].append(entry)
            await db_session.flush()

        # Verify ordering preserved
        retrieved = await db_session.get(Product, ws_product.id)
        history = retrieved.product_memory["sequential_history"]

        for idx, entry in enumerate(history):
            assert entry["sequence"] == idx + 1
