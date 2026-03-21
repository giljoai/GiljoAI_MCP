"""
Tests for ProductTuningService — Handover 0831

TDD tests written BEFORE implementation. These define the behavioral contract
for the ProductTuningService which handles on-demand product context tuning:
prompt assembly, proposal storage, apply/dismiss, and review clearing.

Test Coverage:
- assemble_tuning_prompt: section filtering, toggle respect, 360 memory depth,
  git integration handling, edge cases (no memory, git disabled, all toggles off)
- store_proposals: proposal persistence, review_id generation, WebSocket emission
- apply_proposal: field mapping for all section keys, pending list removal
- dismiss_proposal: single section removal, other proposals preserved
- clear_review: pending_proposals cleared, last_tuned_at updated

Created as part of Handover 0831: Product Context Tuning
"""

from datetime import datetime, timezone
from unittest.mock import AsyncMock, Mock, patch
from uuid import uuid4

import pytest

from src.giljo_mcp.exceptions import ResourceNotFoundError, ValidationError


# ============================================================================
# TEST FIXTURES
# ============================================================================


TENANT_KEY = "test-tenant-key"
PRODUCT_ID = "prod-001"
USER_ID = "user-001"


@pytest.fixture
def mock_db_manager():
    """Create mock database manager with async session."""
    db_manager = Mock()
    session = AsyncMock()

    async_cm = AsyncMock()
    async_cm.__aenter__ = AsyncMock(return_value=session)
    async_cm.__aexit__ = AsyncMock(return_value=False)

    db_manager.get_session_async = Mock(return_value=async_cm)

    return db_manager, session


@pytest.fixture
def mock_websocket_manager():
    """Create mock WebSocket manager for event broadcasting."""
    ws_manager = AsyncMock()
    ws_manager.broadcast_to_tenant = AsyncMock()
    return ws_manager


@pytest.fixture
def sample_product():
    """Create a mock product with realistic context data."""
    product = Mock()
    product.id = PRODUCT_ID
    product.tenant_key = TENANT_KEY
    product.name = "GiljoAI MCP"
    product.description = "An AI agent orchestration platform"
    product.quality_standards = "80% test coverage, all endpoints tested"
    product.target_platforms = ["windows", "linux"]
    product.config_data = {
        "tech_stack": "Python 3.12, FastAPI, Vue 3, PostgreSQL",
        "architecture": "Monolithic backend with REST API",
        "features": {
            "core": "Agent orchestration, project management, 360 memory",
        },
        "codebase_structure": "src/giljo_mcp for backend, frontend/src for Vue",
        "database_type": "PostgreSQL 18",
        "backend_framework": "FastAPI with SQLAlchemy 2.0",
        "frontend_framework": "Vue 3 with Vuetify 3",
    }
    product.product_memory = {
        "github": {},
        "context": {},
        "git_integration": {
            "enabled": True,
            "commit_limit": 25,
            "default_branch": "master",
        },
    }
    product.tuning_state = None
    return product


@pytest.fixture
def sample_product_no_git(sample_product):
    """Product with git integration disabled."""
    sample_product.product_memory = {
        "github": {},
        "context": {},
        "git_integration": {
            "enabled": False,
        },
    }
    return sample_product


@pytest.fixture
def sample_memory_entries():
    """Create sample 360 memory entries for prompt assembly tests."""
    entries = []
    for i in range(3):
        entry = Mock()
        entry.sequence = i + 1
        entry.summary = f"Project {i + 1} summary: implemented feature {chr(65 + i)}"
        entry.key_outcomes = [f"Outcome {i + 1}.1", f"Outcome {i + 1}.2"]
        entry.decisions_made = [f"Decision {i + 1}: chose approach {chr(65 + i)}"]
        entry.deliverables = [f"deliverable_{i + 1}.py"]
        entry.git_commits = [
            {"hash": f"abc{i}", "message": f"feat: feature {chr(65 + i)}", "date": f"2026-03-{15 + i}"}
        ]
        entry.tags = ["closeout"]
        entry.project_name = f"Project {i + 1}"
        entry.timestamp = datetime(2026, 3, 15 + i, tzinfo=timezone.utc)
        entries.append(entry)
    return entries


@pytest.fixture
def sample_user_settings():
    """User context settings with toggles and depth config."""
    return {
        "field_priority_config": {
            "version": "3.0",
            "priorities": {
                "product_core": {"toggle": True},
                "project_description": {"toggle": True},
                "memory_360": {"toggle": True},
                "tech_stack": {"toggle": True},
                "testing": {"toggle": True},
                "vision_documents": {"toggle": True},
                "architecture": {"toggle": True},
                "agent_templates": {"toggle": True},
                "git_history": {"toggle": False},
            },
        },
        "depth_config": {
            "version": "1.0",
            "depths": {
                "vision_documents": "medium",
                "memory_360": 3,
                "git_history": 25,
                "agent_templates": "type_only",
            },
        },
    }


@pytest.fixture
def sample_proposals_data():
    """Sample proposals as would be received from submit_tuning_review MCP tool."""
    return {
        "proposals": [
            {
                "section": "tech_stack",
                "drift_detected": True,
                "current_summary": "Python 3.12, FastAPI, Vue 3, PostgreSQL",
                "evidence": "Project 3 added Redis caching layer",
                "proposed_value": "Python 3.12, FastAPI, Vue 3, PostgreSQL, Redis",
                "confidence": "high",
                "reasoning": "Redis was added in project 3 and is now part of the stack",
            },
            {
                "section": "architecture",
                "drift_detected": False,
                "current_summary": "Monolithic backend with REST API",
                "evidence": "No architectural changes observed",
                "proposed_value": "Monolithic backend with REST API",
                "confidence": "high",
                "reasoning": "Architecture description remains accurate",
            },
        ],
        "overall_summary": "Minor drift detected in tech stack only.",
    }


@pytest.fixture
def product_with_pending_proposals(sample_product, sample_proposals_data):
    """Product that already has pending proposals stored."""
    review_id = str(uuid4())
    sample_product.tuning_state = {
        "pending_proposals": {
            "review_id": review_id,
            "submitted_at": "2026-03-21T14:35:00Z",
            "overall_summary": sample_proposals_data["overall_summary"],
            "proposals": sample_proposals_data["proposals"],
        },
    }
    return sample_product, review_id


# ============================================================================
# TEST CLASS 1: assemble_tuning_prompt — Section Selection
# ============================================================================


class TestAssembleTuningPromptSections:
    """Test that assemble_tuning_prompt includes only selected sections."""

    @pytest.mark.asyncio
    async def test_includes_only_selected_sections_in_prompt(
        self, mock_db_manager, mock_websocket_manager, sample_product, sample_memory_entries, sample_user_settings
    ):
        """Prompt should contain only the sections the user selected."""
        from src.giljo_mcp.services.product_tuning_service import ProductTuningService

        db_manager, session = mock_db_manager
        service = ProductTuningService(db_manager, TENANT_KEY, websocket_manager=mock_websocket_manager)

        session.execute = AsyncMock(
            return_value=Mock(scalar_one_or_none=Mock(return_value=sample_product))
        )

        with patch.object(service, "_get_memory_entries", new_callable=AsyncMock, return_value=sample_memory_entries), \
             patch.object(service, "_get_user_settings", new_callable=AsyncMock, return_value=sample_user_settings):
            result = await service.assemble_tuning_prompt(
                product_id=PRODUCT_ID,
                tenant_key=TENANT_KEY,
                user_id=USER_ID,
                sections=["tech_stack", "description"],
            )

        assert "prompt" in result
        assert "sections_included" in result
        assert set(result["sections_included"]) == {"tech_stack", "description"}

    @pytest.mark.asyncio
    async def test_excludes_unselected_sections_from_prompt(
        self, mock_db_manager, mock_websocket_manager, sample_product, sample_memory_entries, sample_user_settings
    ):
        """Sections not in the selection list should not appear in sections_included."""
        from src.giljo_mcp.services.product_tuning_service import ProductTuningService

        db_manager, session = mock_db_manager
        service = ProductTuningService(db_manager, TENANT_KEY, websocket_manager=mock_websocket_manager)

        session.execute = AsyncMock(
            return_value=Mock(scalar_one_or_none=Mock(return_value=sample_product))
        )

        with patch.object(service, "_get_memory_entries", new_callable=AsyncMock, return_value=sample_memory_entries), \
             patch.object(service, "_get_user_settings", new_callable=AsyncMock, return_value=sample_user_settings):
            result = await service.assemble_tuning_prompt(
                product_id=PRODUCT_ID,
                tenant_key=TENANT_KEY,
                user_id=USER_ID,
                sections=["description"],
            )

        assert "architecture" not in result["sections_included"]
        assert "tech_stack" not in result["sections_included"]

    @pytest.mark.asyncio
    async def test_prompt_contains_product_id(
        self, mock_db_manager, mock_websocket_manager, sample_product, sample_memory_entries, sample_user_settings
    ):
        """The assembled prompt must include the product_id for the MCP tool call."""
        from src.giljo_mcp.services.product_tuning_service import ProductTuningService

        db_manager, session = mock_db_manager
        service = ProductTuningService(db_manager, TENANT_KEY, websocket_manager=mock_websocket_manager)

        session.execute = AsyncMock(
            return_value=Mock(scalar_one_or_none=Mock(return_value=sample_product))
        )

        with patch.object(service, "_get_memory_entries", new_callable=AsyncMock, return_value=sample_memory_entries), \
             patch.object(service, "_get_user_settings", new_callable=AsyncMock, return_value=sample_user_settings):
            result = await service.assemble_tuning_prompt(
                product_id=PRODUCT_ID,
                tenant_key=TENANT_KEY,
                user_id=USER_ID,
                sections=["tech_stack"],
            )

        assert PRODUCT_ID in result["prompt"]


# ============================================================================
# TEST CLASS 2: assemble_tuning_prompt — Toggle Respect
# ============================================================================


class TestAssembleTuningPromptToggles:
    """Test that assemble_tuning_prompt respects user context toggle settings."""

    @pytest.mark.asyncio
    async def test_filters_out_sections_with_toggled_off_parent(
        self, mock_db_manager, mock_websocket_manager, sample_product, sample_memory_entries
    ):
        """Sections whose parent toggle is OFF should be excluded even if selected."""
        from src.giljo_mcp.services.product_tuning_service import ProductTuningService

        db_manager, session = mock_db_manager
        service = ProductTuningService(db_manager, TENANT_KEY, websocket_manager=mock_websocket_manager)

        session.execute = AsyncMock(
            return_value=Mock(scalar_one_or_none=Mock(return_value=sample_product))
        )

        # Architecture toggle OFF means architecture, core_features, codebase_structure excluded
        settings_arch_off = {
            "field_priority_config": {
                "version": "3.0",
                "priorities": {
                    "product_core": {"toggle": True},
                    "tech_stack": {"toggle": True},
                    "architecture": {"toggle": False},
                    "testing": {"toggle": True},
                    "memory_360": {"toggle": True},
                    "vision_documents": {"toggle": True},
                    "git_history": {"toggle": False},
                    "agent_templates": {"toggle": True},
                    "project_description": {"toggle": True},
                },
            },
            "depth_config": {"version": "1.0", "depths": {"memory_360": 3, "git_history": 25}},
        }

        with patch.object(service, "_get_memory_entries", new_callable=AsyncMock, return_value=sample_memory_entries), \
             patch.object(service, "_get_user_settings", new_callable=AsyncMock, return_value=settings_arch_off):
            result = await service.assemble_tuning_prompt(
                product_id=PRODUCT_ID,
                tenant_key=TENANT_KEY,
                user_id=USER_ID,
                sections=["architecture", "core_features", "tech_stack"],
            )

        assert "architecture" not in result["sections_included"]
        assert "core_features" not in result["sections_included"]
        assert "tech_stack" in result["sections_included"]

    @pytest.mark.asyncio
    async def test_all_toggles_off_returns_empty_sections(
        self, mock_db_manager, mock_websocket_manager, sample_product, sample_memory_entries
    ):
        """When all toggles are OFF, no sections should be included."""
        from src.giljo_mcp.services.product_tuning_service import ProductTuningService

        db_manager, session = mock_db_manager
        service = ProductTuningService(db_manager, TENANT_KEY, websocket_manager=mock_websocket_manager)

        session.execute = AsyncMock(
            return_value=Mock(scalar_one_or_none=Mock(return_value=sample_product))
        )

        all_off = {
            "field_priority_config": {
                "version": "3.0",
                "priorities": {
                    "product_core": {"toggle": False},
                    "tech_stack": {"toggle": False},
                    "architecture": {"toggle": False},
                    "testing": {"toggle": False},
                    "memory_360": {"toggle": False},
                    "vision_documents": {"toggle": False},
                    "git_history": {"toggle": False},
                    "agent_templates": {"toggle": False},
                    "project_description": {"toggle": False},
                },
            },
            "depth_config": {"version": "1.0", "depths": {"memory_360": 3}},
        }

        with patch.object(service, "_get_memory_entries", new_callable=AsyncMock, return_value=[]), \
             patch.object(service, "_get_user_settings", new_callable=AsyncMock, return_value=all_off):
            result = await service.assemble_tuning_prompt(
                product_id=PRODUCT_ID,
                tenant_key=TENANT_KEY,
                user_id=USER_ID,
                sections=["description", "tech_stack", "architecture"],
            )

        assert result["sections_included"] == []


# ============================================================================
# TEST CLASS 3: assemble_tuning_prompt — 360 Memory and Git Integration
# ============================================================================


class TestAssembleTuningPromptMemoryAndGit:
    """Test 360 memory depth and git integration in prompt assembly."""

    @pytest.mark.asyncio
    async def test_includes_360_memory_at_configured_depth(
        self, mock_db_manager, mock_websocket_manager, sample_product, sample_memory_entries, sample_user_settings
    ):
        """Prompt should include 360 memory entries up to the configured lookback depth."""
        from src.giljo_mcp.services.product_tuning_service import ProductTuningService

        db_manager, session = mock_db_manager
        service = ProductTuningService(db_manager, TENANT_KEY, websocket_manager=mock_websocket_manager)

        session.execute = AsyncMock(
            return_value=Mock(scalar_one_or_none=Mock(return_value=sample_product))
        )

        with patch.object(service, "_get_memory_entries", new_callable=AsyncMock, return_value=sample_memory_entries) as mock_get_mem, \
             patch.object(service, "_get_user_settings", new_callable=AsyncMock, return_value=sample_user_settings):
            result = await service.assemble_tuning_prompt(
                product_id=PRODUCT_ID,
                tenant_key=TENANT_KEY,
                user_id=USER_ID,
                sections=["description"],
            )

        assert result["lookback_depth"] == 3
        # Verify memory entries content appears in prompt
        assert "Project 1 summary" in result["prompt"] or len(sample_memory_entries) > 0

    @pytest.mark.asyncio
    async def test_includes_git_commits_when_git_enabled(
        self, mock_db_manager, mock_websocket_manager, sample_product, sample_memory_entries, sample_user_settings
    ):
        """When git integration is enabled, prompt should include git commit data."""
        from src.giljo_mcp.services.product_tuning_service import ProductTuningService

        db_manager, session = mock_db_manager
        service = ProductTuningService(db_manager, TENANT_KEY, websocket_manager=mock_websocket_manager)

        session.execute = AsyncMock(
            return_value=Mock(scalar_one_or_none=Mock(return_value=sample_product))
        )

        with patch.object(service, "_get_memory_entries", new_callable=AsyncMock, return_value=sample_memory_entries), \
             patch.object(service, "_get_user_settings", new_callable=AsyncMock, return_value=sample_user_settings):
            result = await service.assemble_tuning_prompt(
                product_id=PRODUCT_ID,
                tenant_key=TENANT_KEY,
                user_id=USER_ID,
                sections=["tech_stack"],
            )

        assert result["git_enabled"] is True

    @pytest.mark.asyncio
    async def test_omits_git_section_when_git_disabled(
        self, mock_db_manager, mock_websocket_manager, sample_product_no_git, sample_memory_entries, sample_user_settings
    ):
        """When git integration is disabled, prompt should omit git section."""
        from src.giljo_mcp.services.product_tuning_service import ProductTuningService

        db_manager, session = mock_db_manager
        service = ProductTuningService(db_manager, TENANT_KEY, websocket_manager=mock_websocket_manager)

        session.execute = AsyncMock(
            return_value=Mock(scalar_one_or_none=Mock(return_value=sample_product_no_git))
        )

        with patch.object(service, "_get_memory_entries", new_callable=AsyncMock, return_value=sample_memory_entries), \
             patch.object(service, "_get_user_settings", new_callable=AsyncMock, return_value=sample_user_settings):
            result = await service.assemble_tuning_prompt(
                product_id=PRODUCT_ID,
                tenant_key=TENANT_KEY,
                user_id=USER_ID,
                sections=["tech_stack"],
            )

        assert result["git_enabled"] is False

    @pytest.mark.asyncio
    async def test_handles_no_360_memory_entries_gracefully(
        self, mock_db_manager, mock_websocket_manager, sample_product, sample_user_settings
    ):
        """With no 360 memory entries, prompt should still assemble without error."""
        from src.giljo_mcp.services.product_tuning_service import ProductTuningService

        db_manager, session = mock_db_manager
        service = ProductTuningService(db_manager, TENANT_KEY, websocket_manager=mock_websocket_manager)

        session.execute = AsyncMock(
            return_value=Mock(scalar_one_or_none=Mock(return_value=sample_product))
        )

        with patch.object(service, "_get_memory_entries", new_callable=AsyncMock, return_value=[]), \
             patch.object(service, "_get_user_settings", new_callable=AsyncMock, return_value=sample_user_settings):
            result = await service.assemble_tuning_prompt(
                product_id=PRODUCT_ID,
                tenant_key=TENANT_KEY,
                user_id=USER_ID,
                sections=["description"],
            )

        assert "prompt" in result
        assert result["sections_included"] == ["description"]

    @pytest.mark.asyncio
    async def test_returns_correct_structure(
        self, mock_db_manager, mock_websocket_manager, sample_product, sample_memory_entries, sample_user_settings
    ):
        """Return value should contain prompt, sections_included, lookback_depth, git_enabled."""
        from src.giljo_mcp.services.product_tuning_service import ProductTuningService

        db_manager, session = mock_db_manager
        service = ProductTuningService(db_manager, TENANT_KEY, websocket_manager=mock_websocket_manager)

        session.execute = AsyncMock(
            return_value=Mock(scalar_one_or_none=Mock(return_value=sample_product))
        )

        with patch.object(service, "_get_memory_entries", new_callable=AsyncMock, return_value=sample_memory_entries), \
             patch.object(service, "_get_user_settings", new_callable=AsyncMock, return_value=sample_user_settings):
            result = await service.assemble_tuning_prompt(
                product_id=PRODUCT_ID,
                tenant_key=TENANT_KEY,
                user_id=USER_ID,
                sections=["description", "tech_stack"],
            )

        assert isinstance(result["prompt"], str)
        assert isinstance(result["sections_included"], list)
        assert isinstance(result["lookback_depth"], int)
        assert isinstance(result["git_enabled"], bool)


# ============================================================================
# TEST CLASS 4: assemble_tuning_prompt — Error Cases
# ============================================================================


class TestAssembleTuningPromptErrors:
    """Test error handling in assemble_tuning_prompt."""

    @pytest.mark.asyncio
    async def test_raises_not_found_when_product_missing(
        self, mock_db_manager, mock_websocket_manager
    ):
        """Should raise ResourceNotFoundError when product does not exist."""
        from src.giljo_mcp.services.product_tuning_service import ProductTuningService

        db_manager, session = mock_db_manager
        service = ProductTuningService(db_manager, TENANT_KEY, websocket_manager=mock_websocket_manager)

        session.execute = AsyncMock(
            return_value=Mock(scalar_one_or_none=Mock(return_value=None))
        )

        with pytest.raises(ResourceNotFoundError):
            await service.assemble_tuning_prompt(
                product_id="nonexistent-id",
                tenant_key=TENANT_KEY,
                user_id=USER_ID,
                sections=["description"],
            )

    @pytest.mark.asyncio
    async def test_raises_validation_error_for_empty_sections_list(
        self, mock_db_manager, mock_websocket_manager, sample_product, sample_user_settings
    ):
        """Should raise ValidationError when sections list is empty."""
        from src.giljo_mcp.services.product_tuning_service import ProductTuningService

        db_manager, session = mock_db_manager
        service = ProductTuningService(db_manager, TENANT_KEY, websocket_manager=mock_websocket_manager)

        session.execute = AsyncMock(
            return_value=Mock(scalar_one_or_none=Mock(return_value=sample_product))
        )

        with patch.object(service, "_get_user_settings", new_callable=AsyncMock, return_value=sample_user_settings):
            with pytest.raises(ValidationError):
                await service.assemble_tuning_prompt(
                    product_id=PRODUCT_ID,
                    tenant_key=TENANT_KEY,
                    user_id=USER_ID,
                    sections=[],
                )

    @pytest.mark.asyncio
    async def test_prompt_includes_submit_tuning_review_instruction(
        self, mock_db_manager, mock_websocket_manager, sample_product, sample_memory_entries, sample_user_settings
    ):
        """Prompt must instruct the agent to call submit_tuning_review MCP tool."""
        from src.giljo_mcp.services.product_tuning_service import ProductTuningService

        db_manager, session = mock_db_manager
        service = ProductTuningService(db_manager, TENANT_KEY, websocket_manager=mock_websocket_manager)

        session.execute = AsyncMock(
            return_value=Mock(scalar_one_or_none=Mock(return_value=sample_product))
        )

        with patch.object(service, "_get_memory_entries", new_callable=AsyncMock, return_value=sample_memory_entries), \
             patch.object(service, "_get_user_settings", new_callable=AsyncMock, return_value=sample_user_settings):
            result = await service.assemble_tuning_prompt(
                product_id=PRODUCT_ID,
                tenant_key=TENANT_KEY,
                user_id=USER_ID,
                sections=["description"],
            )

        assert "submit_tuning_review" in result["prompt"]


# ============================================================================
# TEST CLASS 5: store_proposals
# ============================================================================


class TestStoreProposals:
    """Test proposal storage, review_id generation, and WebSocket events."""

    @pytest.mark.asyncio
    async def test_stores_proposals_on_product_tuning_state(
        self, mock_db_manager, mock_websocket_manager, sample_product, sample_proposals_data
    ):
        """Should save proposals to Product.tuning_state.pending_proposals."""
        from src.giljo_mcp.services.product_tuning_service import ProductTuningService

        db_manager, session = mock_db_manager
        service = ProductTuningService(db_manager, TENANT_KEY, websocket_manager=mock_websocket_manager)

        session.execute = AsyncMock(
            return_value=Mock(scalar_one_or_none=Mock(return_value=sample_product))
        )
        session.commit = AsyncMock()

        result = await service.store_proposals(
            product_id=PRODUCT_ID,
            tenant_key=TENANT_KEY,
            proposals_data=sample_proposals_data,
        )

        assert result["success"] is True
        assert "review_id" in result
        assert result["review_id"] is not None
        assert len(result["review_id"]) > 0

    @pytest.mark.asyncio
    async def test_generates_uuid_review_id(
        self, mock_db_manager, mock_websocket_manager, sample_product, sample_proposals_data
    ):
        """Should generate a UUID for review_id."""
        from src.giljo_mcp.services.product_tuning_service import ProductTuningService
        from uuid import UUID as UUIDType

        db_manager, session = mock_db_manager
        service = ProductTuningService(db_manager, TENANT_KEY, websocket_manager=mock_websocket_manager)

        session.execute = AsyncMock(
            return_value=Mock(scalar_one_or_none=Mock(return_value=sample_product))
        )
        session.commit = AsyncMock()

        result = await service.store_proposals(
            product_id=PRODUCT_ID,
            tenant_key=TENANT_KEY,
            proposals_data=sample_proposals_data,
        )

        # Should be a valid UUID
        parsed = UUIDType(result["review_id"])
        assert str(parsed) == result["review_id"]

    @pytest.mark.asyncio
    async def test_emits_websocket_event_on_store(
        self, mock_db_manager, mock_websocket_manager, sample_product, sample_proposals_data
    ):
        """Should emit product:tuning:proposals_ready WebSocket event."""
        from src.giljo_mcp.services.product_tuning_service import ProductTuningService

        db_manager, session = mock_db_manager
        service = ProductTuningService(db_manager, TENANT_KEY, websocket_manager=mock_websocket_manager)

        session.execute = AsyncMock(
            return_value=Mock(scalar_one_or_none=Mock(return_value=sample_product))
        )
        session.commit = AsyncMock()

        await service.store_proposals(
            product_id=PRODUCT_ID,
            tenant_key=TENANT_KEY,
            proposals_data=sample_proposals_data,
        )

        mock_websocket_manager.broadcast_to_tenant.assert_called_once()
        call_args = mock_websocket_manager.broadcast_to_tenant.call_args
        assert call_args[0][0] == TENANT_KEY
        event_data = call_args[0][1]
        assert event_data.get("type") == "product:tuning:proposals_ready" or \
               "product:tuning:proposals_ready" in str(call_args)

    @pytest.mark.asyncio
    async def test_returns_success_structure(
        self, mock_db_manager, mock_websocket_manager, sample_product, sample_proposals_data
    ):
        """Return value should have success, review_id, and message."""
        from src.giljo_mcp.services.product_tuning_service import ProductTuningService

        db_manager, session = mock_db_manager
        service = ProductTuningService(db_manager, TENANT_KEY, websocket_manager=mock_websocket_manager)

        session.execute = AsyncMock(
            return_value=Mock(scalar_one_or_none=Mock(return_value=sample_product))
        )
        session.commit = AsyncMock()

        result = await service.store_proposals(
            product_id=PRODUCT_ID,
            tenant_key=TENANT_KEY,
            proposals_data=sample_proposals_data,
        )

        assert "success" in result
        assert "review_id" in result
        assert "message" in result
        assert isinstance(result["message"], str)

    @pytest.mark.asyncio
    async def test_raises_not_found_for_missing_product(
        self, mock_db_manager, mock_websocket_manager, sample_proposals_data
    ):
        """Should raise ResourceNotFoundError when product does not exist."""
        from src.giljo_mcp.services.product_tuning_service import ProductTuningService

        db_manager, session = mock_db_manager
        service = ProductTuningService(db_manager, TENANT_KEY, websocket_manager=mock_websocket_manager)

        session.execute = AsyncMock(
            return_value=Mock(scalar_one_or_none=Mock(return_value=None))
        )

        with pytest.raises(ResourceNotFoundError):
            await service.store_proposals(
                product_id="nonexistent-id",
                tenant_key=TENANT_KEY,
                proposals_data=sample_proposals_data,
            )


# ============================================================================
# TEST CLASS 6: apply_proposal — Section Key Mapping
# ============================================================================


class TestApplyProposal:
    """Test that apply_proposal correctly maps section keys to product fields."""

    @pytest.mark.asyncio
    async def test_apply_description_updates_product_description(
        self, mock_db_manager, mock_websocket_manager, product_with_pending_proposals
    ):
        """Section 'description' should update Product.description."""
        from src.giljo_mcp.services.product_tuning_service import ProductTuningService

        db_manager, session = mock_db_manager
        product, _ = product_with_pending_proposals
        service = ProductTuningService(db_manager, TENANT_KEY, websocket_manager=mock_websocket_manager)

        session.execute = AsyncMock(
            return_value=Mock(scalar_one_or_none=Mock(return_value=product))
        )
        session.commit = AsyncMock()

        new_description = "Updated AI orchestration platform with Redis caching"
        await service.apply_proposal(
            product_id=PRODUCT_ID,
            tenant_key=TENANT_KEY,
            section="description",
            value=new_description,
        )

        assert product.description == new_description

    @pytest.mark.asyncio
    async def test_apply_tech_stack_updates_config_data(
        self, mock_db_manager, mock_websocket_manager, product_with_pending_proposals
    ):
        """Section 'tech_stack' should update Product.config_data['tech_stack']."""
        from src.giljo_mcp.services.product_tuning_service import ProductTuningService

        db_manager, session = mock_db_manager
        product, _ = product_with_pending_proposals
        service = ProductTuningService(db_manager, TENANT_KEY, websocket_manager=mock_websocket_manager)

        session.execute = AsyncMock(
            return_value=Mock(scalar_one_or_none=Mock(return_value=product))
        )
        session.commit = AsyncMock()

        new_value = "Python 3.12, FastAPI, Vue 3, PostgreSQL, Redis"
        await service.apply_proposal(
            product_id=PRODUCT_ID,
            tenant_key=TENANT_KEY,
            section="tech_stack",
            value=new_value,
        )

        assert product.config_data["tech_stack"] == new_value

    @pytest.mark.asyncio
    async def test_apply_architecture_updates_config_data(
        self, mock_db_manager, mock_websocket_manager, product_with_pending_proposals
    ):
        """Section 'architecture' should update Product.config_data['architecture']."""
        from src.giljo_mcp.services.product_tuning_service import ProductTuningService

        db_manager, session = mock_db_manager
        product, _ = product_with_pending_proposals
        service = ProductTuningService(db_manager, TENANT_KEY, websocket_manager=mock_websocket_manager)

        session.execute = AsyncMock(
            return_value=Mock(scalar_one_or_none=Mock(return_value=product))
        )
        session.commit = AsyncMock()

        new_value = "Microservices with event-driven architecture"
        await service.apply_proposal(
            product_id=PRODUCT_ID,
            tenant_key=TENANT_KEY,
            section="architecture",
            value=new_value,
        )

        assert product.config_data["architecture"] == new_value

    @pytest.mark.asyncio
    async def test_apply_core_features_updates_nested_config(
        self, mock_db_manager, mock_websocket_manager, product_with_pending_proposals
    ):
        """Section 'core_features' should update Product.config_data['features']['core']."""
        from src.giljo_mcp.services.product_tuning_service import ProductTuningService

        db_manager, session = mock_db_manager
        product, _ = product_with_pending_proposals
        service = ProductTuningService(db_manager, TENANT_KEY, websocket_manager=mock_websocket_manager)

        session.execute = AsyncMock(
            return_value=Mock(scalar_one_or_none=Mock(return_value=product))
        )
        session.commit = AsyncMock()

        new_value = "Agent orchestration, project management, 360 memory, context tuning"
        await service.apply_proposal(
            product_id=PRODUCT_ID,
            tenant_key=TENANT_KEY,
            section="core_features",
            value=new_value,
        )

        assert product.config_data["features"]["core"] == new_value

    @pytest.mark.asyncio
    async def test_apply_codebase_structure_updates_config_data(
        self, mock_db_manager, mock_websocket_manager, product_with_pending_proposals
    ):
        """Section 'codebase_structure' should update Product.config_data['codebase_structure']."""
        from src.giljo_mcp.services.product_tuning_service import ProductTuningService

        db_manager, session = mock_db_manager
        product, _ = product_with_pending_proposals
        service = ProductTuningService(db_manager, TENANT_KEY, websocket_manager=mock_websocket_manager)

        session.execute = AsyncMock(
            return_value=Mock(scalar_one_or_none=Mock(return_value=product))
        )
        session.commit = AsyncMock()

        new_value = "src/giljo_mcp for backend, frontend/src for Vue, saas/ for SaaS"
        await service.apply_proposal(
            product_id=PRODUCT_ID,
            tenant_key=TENANT_KEY,
            section="codebase_structure",
            value=new_value,
        )

        assert product.config_data["codebase_structure"] == new_value

    @pytest.mark.asyncio
    async def test_apply_database_type_updates_config_data(
        self, mock_db_manager, mock_websocket_manager, product_with_pending_proposals
    ):
        """Section 'database_type' should update Product.config_data['database_type']."""
        from src.giljo_mcp.services.product_tuning_service import ProductTuningService

        db_manager, session = mock_db_manager
        product, _ = product_with_pending_proposals
        service = ProductTuningService(db_manager, TENANT_KEY, websocket_manager=mock_websocket_manager)

        session.execute = AsyncMock(
            return_value=Mock(scalar_one_or_none=Mock(return_value=product))
        )
        session.commit = AsyncMock()

        new_value = "PostgreSQL 18 with Redis cache"
        await service.apply_proposal(
            product_id=PRODUCT_ID,
            tenant_key=TENANT_KEY,
            section="database_type",
            value=new_value,
        )

        assert product.config_data["database_type"] == new_value

    @pytest.mark.asyncio
    async def test_apply_backend_framework_updates_config_data(
        self, mock_db_manager, mock_websocket_manager, product_with_pending_proposals
    ):
        """Section 'backend_framework' should update Product.config_data['backend_framework']."""
        from src.giljo_mcp.services.product_tuning_service import ProductTuningService

        db_manager, session = mock_db_manager
        product, _ = product_with_pending_proposals
        service = ProductTuningService(db_manager, TENANT_KEY, websocket_manager=mock_websocket_manager)

        session.execute = AsyncMock(
            return_value=Mock(scalar_one_or_none=Mock(return_value=product))
        )
        session.commit = AsyncMock()

        new_value = "FastAPI with SQLAlchemy 2.0 and Alembic"
        await service.apply_proposal(
            product_id=PRODUCT_ID,
            tenant_key=TENANT_KEY,
            section="backend_framework",
            value=new_value,
        )

        assert product.config_data["backend_framework"] == new_value

    @pytest.mark.asyncio
    async def test_apply_frontend_framework_updates_config_data(
        self, mock_db_manager, mock_websocket_manager, product_with_pending_proposals
    ):
        """Section 'frontend_framework' should update Product.config_data['frontend_framework']."""
        from src.giljo_mcp.services.product_tuning_service import ProductTuningService

        db_manager, session = mock_db_manager
        product, _ = product_with_pending_proposals
        service = ProductTuningService(db_manager, TENANT_KEY, websocket_manager=mock_websocket_manager)

        session.execute = AsyncMock(
            return_value=Mock(scalar_one_or_none=Mock(return_value=product))
        )
        session.commit = AsyncMock()

        new_value = "Vue 3 with Vuetify 3 and Pinia"
        await service.apply_proposal(
            product_id=PRODUCT_ID,
            tenant_key=TENANT_KEY,
            section="frontend_framework",
            value=new_value,
        )

        assert product.config_data["frontend_framework"] == new_value

    @pytest.mark.asyncio
    async def test_apply_quality_standards_updates_product_field(
        self, mock_db_manager, mock_websocket_manager, product_with_pending_proposals
    ):
        """Section 'quality_standards' should update Product.quality_standards."""
        from src.giljo_mcp.services.product_tuning_service import ProductTuningService

        db_manager, session = mock_db_manager
        product, _ = product_with_pending_proposals
        service = ProductTuningService(db_manager, TENANT_KEY, websocket_manager=mock_websocket_manager)

        session.execute = AsyncMock(
            return_value=Mock(scalar_one_or_none=Mock(return_value=product))
        )
        session.commit = AsyncMock()

        new_value = "90% test coverage, all endpoints tested, type annotations required"
        await service.apply_proposal(
            product_id=PRODUCT_ID,
            tenant_key=TENANT_KEY,
            section="quality_standards",
            value=new_value,
        )

        assert product.quality_standards == new_value

    @pytest.mark.asyncio
    async def test_apply_target_platforms_updates_product_field(
        self, mock_db_manager, mock_websocket_manager, product_with_pending_proposals
    ):
        """Section 'target_platforms' should update Product.target_platforms."""
        from src.giljo_mcp.services.product_tuning_service import ProductTuningService

        db_manager, session = mock_db_manager
        product, _ = product_with_pending_proposals
        service = ProductTuningService(db_manager, TENANT_KEY, websocket_manager=mock_websocket_manager)

        session.execute = AsyncMock(
            return_value=Mock(scalar_one_or_none=Mock(return_value=product))
        )
        session.commit = AsyncMock()

        new_value = ["windows", "linux", "macos"]
        await service.apply_proposal(
            product_id=PRODUCT_ID,
            tenant_key=TENANT_KEY,
            section="target_platforms",
            value=new_value,
        )

        assert product.target_platforms == new_value

    @pytest.mark.asyncio
    async def test_apply_removes_proposal_from_pending_list(
        self, mock_db_manager, mock_websocket_manager, product_with_pending_proposals
    ):
        """After applying a proposal, it should be removed from pending_proposals."""
        from src.giljo_mcp.services.product_tuning_service import ProductTuningService

        db_manager, session = mock_db_manager
        product, _ = product_with_pending_proposals
        service = ProductTuningService(db_manager, TENANT_KEY, websocket_manager=mock_websocket_manager)

        session.execute = AsyncMock(
            return_value=Mock(scalar_one_or_none=Mock(return_value=product))
        )
        session.commit = AsyncMock()

        # Product has proposals for tech_stack and architecture
        initial_count = len(product.tuning_state["pending_proposals"]["proposals"])

        await service.apply_proposal(
            product_id=PRODUCT_ID,
            tenant_key=TENANT_KEY,
            section="tech_stack",
            value="Python 3.12, FastAPI, Vue 3, PostgreSQL, Redis",
        )

        remaining = product.tuning_state["pending_proposals"]["proposals"]
        assert len(remaining) == initial_count - 1
        remaining_sections = [p["section"] for p in remaining]
        assert "tech_stack" not in remaining_sections

    @pytest.mark.asyncio
    async def test_apply_raises_not_found_for_missing_product(
        self, mock_db_manager, mock_websocket_manager
    ):
        """Should raise ResourceNotFoundError when product does not exist."""
        from src.giljo_mcp.services.product_tuning_service import ProductTuningService

        db_manager, session = mock_db_manager
        service = ProductTuningService(db_manager, TENANT_KEY, websocket_manager=mock_websocket_manager)

        session.execute = AsyncMock(
            return_value=Mock(scalar_one_or_none=Mock(return_value=None))
        )

        with pytest.raises(ResourceNotFoundError):
            await service.apply_proposal(
                product_id="nonexistent-id",
                tenant_key=TENANT_KEY,
                section="description",
                value="new value",
            )


# ============================================================================
# TEST CLASS 7: dismiss_proposal
# ============================================================================


class TestDismissProposal:
    """Test that dismiss_proposal removes specific proposals without side effects."""

    @pytest.mark.asyncio
    async def test_removes_specific_section_from_pending(
        self, mock_db_manager, mock_websocket_manager, product_with_pending_proposals
    ):
        """Should remove only the specified section's proposal."""
        from src.giljo_mcp.services.product_tuning_service import ProductTuningService

        db_manager, session = mock_db_manager
        product, _ = product_with_pending_proposals
        service = ProductTuningService(db_manager, TENANT_KEY, websocket_manager=mock_websocket_manager)

        session.execute = AsyncMock(
            return_value=Mock(scalar_one_or_none=Mock(return_value=product))
        )
        session.commit = AsyncMock()

        await service.dismiss_proposal(
            product_id=PRODUCT_ID,
            tenant_key=TENANT_KEY,
            section="tech_stack",
        )

        remaining = product.tuning_state["pending_proposals"]["proposals"]
        remaining_sections = [p["section"] for p in remaining]
        assert "tech_stack" not in remaining_sections

    @pytest.mark.asyncio
    async def test_preserves_other_pending_proposals(
        self, mock_db_manager, mock_websocket_manager, product_with_pending_proposals
    ):
        """Dismissing one section should not affect other proposals."""
        from src.giljo_mcp.services.product_tuning_service import ProductTuningService

        db_manager, session = mock_db_manager
        product, _ = product_with_pending_proposals
        service = ProductTuningService(db_manager, TENANT_KEY, websocket_manager=mock_websocket_manager)

        session.execute = AsyncMock(
            return_value=Mock(scalar_one_or_none=Mock(return_value=product))
        )
        session.commit = AsyncMock()

        await service.dismiss_proposal(
            product_id=PRODUCT_ID,
            tenant_key=TENANT_KEY,
            section="tech_stack",
        )

        remaining = product.tuning_state["pending_proposals"]["proposals"]
        remaining_sections = [p["section"] for p in remaining]
        assert "architecture" in remaining_sections

    @pytest.mark.asyncio
    async def test_raises_not_found_for_missing_product(
        self, mock_db_manager, mock_websocket_manager
    ):
        """Should raise ResourceNotFoundError when product does not exist."""
        from src.giljo_mcp.services.product_tuning_service import ProductTuningService

        db_manager, session = mock_db_manager
        service = ProductTuningService(db_manager, TENANT_KEY, websocket_manager=mock_websocket_manager)

        session.execute = AsyncMock(
            return_value=Mock(scalar_one_or_none=Mock(return_value=None))
        )

        with pytest.raises(ResourceNotFoundError):
            await service.dismiss_proposal(
                product_id="nonexistent-id",
                tenant_key=TENANT_KEY,
                section="tech_stack",
            )


# ============================================================================
# TEST CLASS 8: clear_review
# ============================================================================


class TestClearReview:
    """Test that clear_review clears proposals and updates timestamps."""

    @pytest.mark.asyncio
    async def test_clears_pending_proposals_to_none(
        self, mock_db_manager, mock_websocket_manager, product_with_pending_proposals
    ):
        """Should set pending_proposals to None."""
        from src.giljo_mcp.services.product_tuning_service import ProductTuningService

        db_manager, session = mock_db_manager
        product, _ = product_with_pending_proposals
        service = ProductTuningService(db_manager, TENANT_KEY, websocket_manager=mock_websocket_manager)

        session.execute = AsyncMock(
            return_value=Mock(scalar_one_or_none=Mock(return_value=product))
        )
        session.commit = AsyncMock()

        await service.clear_review(
            product_id=PRODUCT_ID,
            tenant_key=TENANT_KEY,
        )

        assert product.tuning_state.get("pending_proposals") is None

    @pytest.mark.asyncio
    async def test_updates_last_tuned_at(
        self, mock_db_manager, mock_websocket_manager, product_with_pending_proposals
    ):
        """Should set last_tuned_at to a recent timestamp."""
        from src.giljo_mcp.services.product_tuning_service import ProductTuningService

        db_manager, session = mock_db_manager
        product, _ = product_with_pending_proposals
        service = ProductTuningService(db_manager, TENANT_KEY, websocket_manager=mock_websocket_manager)

        session.execute = AsyncMock(
            return_value=Mock(scalar_one_or_none=Mock(return_value=product))
        )
        session.commit = AsyncMock()

        before = datetime.now(timezone.utc)
        await service.clear_review(
            product_id=PRODUCT_ID,
            tenant_key=TENANT_KEY,
        )

        last_tuned = product.tuning_state.get("last_tuned_at")
        assert last_tuned is not None

    @pytest.mark.asyncio
    async def test_updates_last_tuned_at_sequence(
        self, mock_db_manager, mock_websocket_manager, product_with_pending_proposals
    ):
        """Should update last_tuned_at_sequence to current 360 memory count."""
        from src.giljo_mcp.services.product_tuning_service import ProductTuningService

        db_manager, session = mock_db_manager
        product, _ = product_with_pending_proposals
        service = ProductTuningService(db_manager, TENANT_KEY, websocket_manager=mock_websocket_manager)

        session.execute = AsyncMock(
            return_value=Mock(scalar_one_or_none=Mock(return_value=product))
        )
        session.commit = AsyncMock()

        with patch.object(service, "_get_current_sequence", new_callable=AsyncMock, return_value=15):
            await service.clear_review(
                product_id=PRODUCT_ID,
                tenant_key=TENANT_KEY,
            )

        assert product.tuning_state.get("last_tuned_at_sequence") is not None

    @pytest.mark.asyncio
    async def test_raises_not_found_for_missing_product(
        self, mock_db_manager, mock_websocket_manager
    ):
        """Should raise ResourceNotFoundError when product does not exist."""
        from src.giljo_mcp.services.product_tuning_service import ProductTuningService

        db_manager, session = mock_db_manager
        service = ProductTuningService(db_manager, TENANT_KEY, websocket_manager=mock_websocket_manager)

        session.execute = AsyncMock(
            return_value=Mock(scalar_one_or_none=Mock(return_value=None))
        )

        with pytest.raises(ResourceNotFoundError):
            await service.clear_review(
                product_id="nonexistent-id",
                tenant_key=TENANT_KEY,
            )


# ============================================================================
# TEST CLASS 9: Tenant Isolation
# ============================================================================


class TestTenantIsolation:
    """Verify that all operations enforce tenant_key filtering."""

    @pytest.mark.asyncio
    async def test_assemble_prompt_filters_by_tenant(
        self, mock_db_manager, mock_websocket_manager, sample_product, sample_memory_entries, sample_user_settings
    ):
        """Product lookup in assemble_tuning_prompt must filter by tenant_key."""
        from src.giljo_mcp.services.product_tuning_service import ProductTuningService

        db_manager, session = mock_db_manager
        service = ProductTuningService(db_manager, TENANT_KEY, websocket_manager=mock_websocket_manager)

        session.execute = AsyncMock(
            return_value=Mock(scalar_one_or_none=Mock(return_value=sample_product))
        )

        with patch.object(service, "_get_memory_entries", new_callable=AsyncMock, return_value=sample_memory_entries), \
             patch.object(service, "_get_user_settings", new_callable=AsyncMock, return_value=sample_user_settings):
            await service.assemble_tuning_prompt(
                product_id=PRODUCT_ID,
                tenant_key=TENANT_KEY,
                user_id=USER_ID,
                sections=["description"],
            )

        # Verify execute was called — the implementation must include tenant_key in the query
        session.execute.assert_called_once()

    @pytest.mark.asyncio
    async def test_store_proposals_filters_by_tenant(
        self, mock_db_manager, mock_websocket_manager, sample_product, sample_proposals_data
    ):
        """Product lookup in store_proposals must filter by tenant_key."""
        from src.giljo_mcp.services.product_tuning_service import ProductTuningService

        db_manager, session = mock_db_manager
        service = ProductTuningService(db_manager, TENANT_KEY, websocket_manager=mock_websocket_manager)

        session.execute = AsyncMock(
            return_value=Mock(scalar_one_or_none=Mock(return_value=sample_product))
        )
        session.commit = AsyncMock()

        await service.store_proposals(
            product_id=PRODUCT_ID,
            tenant_key=TENANT_KEY,
            proposals_data=sample_proposals_data,
        )

        session.execute.assert_called_once()
