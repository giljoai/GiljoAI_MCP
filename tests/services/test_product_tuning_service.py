"""
Tests for ProductTuningService — Handover 0831

Test Coverage:
- assemble_tuning_prompt: section filtering, toggle respect, 360 memory depth,
  git integration handling, edge cases (no memory, git disabled, all toggles off)
- apply_tuning_updates: direct field write for drift proposals, skip no-drift,
  last_tuned_at stamping, WebSocket context_updated event, tenant isolation

Created as part of Handover 0831: Product Context Tuning
"""

from datetime import datetime, timezone
from unittest.mock import AsyncMock, Mock, patch
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
    """Create a mock product with realistic context data (0840c: normalized relations)."""
    product = Mock()
    product.id = PRODUCT_ID
    product.tenant_key = TENANT_KEY
    product.name = "GiljoAI MCP"
    product.description = "An AI agent orchestration platform"
    product.quality_standards = "80% test coverage, all endpoints tested"
    product.target_platforms = ["windows", "linux"]
    product.core_features = "Agent orchestration, project management, 360 memory"
    product.deleted_at = None

    # Normalized config relations (0840c)
    tech_stack = Mock()
    tech_stack.programming_languages = "Python 3.12"
    tech_stack.frontend_frameworks = "Vue 3"
    tech_stack.backend_frameworks = "FastAPI"
    tech_stack.databases_storage = "PostgreSQL"
    tech_stack.infrastructure = ""
    tech_stack.dev_tools = ""
    product.tech_stack = tech_stack

    architecture = Mock()
    architecture.primary_pattern = "Monolithic backend with REST API"
    architecture.design_patterns = "Repository, Service"
    architecture.api_style = "REST"
    architecture.architecture_notes = ""
    product.architecture = architecture

    test_config = Mock()
    test_config.quality_standards = "80% test coverage, all endpoints tested"
    test_config.test_strategy = "TDD"
    test_config.coverage_target = 80
    test_config.testing_frameworks = "pytest"
    product.test_config = test_config

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
def sample_memory_entries():
    """Create sample 360 memory entries for prompt assembly tests.

    0840d: Service methods use entry.get() (dict access), not attribute access.
    """
    entries = []
    for i in range(3):
        entry = {
            "sequence": i + 1,
            "summary": f"Project {i + 1} summary: implemented feature {chr(65 + i)}",
            "key_outcomes": [f"Outcome {i + 1}.1", f"Outcome {i + 1}.2"],
            "decisions_made": [f"Decision {i + 1}: chose approach {chr(65 + i)}"],
            "deliverables": [f"deliverable_{i + 1}.py"],
            "git_commits": [
                {"sha": f"abc{i}", "message": f"feat: feature {chr(65 + i)}", "date": f"2026-03-{15 + i}"}
            ],
            "tags": ["closeout"],
            "project_name": f"Project {i + 1}",
            "timestamp": datetime(2026, 3, 15 + i, tzinfo=timezone.utc).isoformat(),
        }
        entries.append(entry)
    return entries


@pytest.fixture
def sample_user_settings():
    """User context settings as (toggle_config, depth_config) tuple.

    0840d: _get_user_settings replaced by _get_user_configs which returns a tuple.
    """
    toggle_config = {
        "version": "4.0",
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
    }
    depth_config = {
        "vision_documents": "medium",
        "memory_last_n_projects": 3,
        "git_commits": 25,
        "agent_templates": "type_only",
        "tech_stack_sections": "all",
        "architecture_depth": "overview",
    }
    return toggle_config, depth_config


# ============================================================================
# TEST CLASS 1: assemble_tuning_prompt — Section Selection
# ============================================================================


class TestAssembleTuningPromptSections:
    """Test that assemble_tuning_prompt includes only selected sections."""

    @pytest.mark.asyncio
    async def test_includes_only_selected_sections_in_prompt(
        self, mock_db_manager, mock_websocket_manager, sample_product, sample_user_settings
    ):
        """Prompt should contain only the sections the user selected."""
        from src.giljo_mcp.services.product_tuning_service import ProductTuningService

        db_manager, session = mock_db_manager
        service = ProductTuningService(db_manager, TENANT_KEY, websocket_manager=mock_websocket_manager)

        session.execute = AsyncMock(
            return_value=Mock(scalar_one_or_none=Mock(return_value=sample_product))
        )

        with patch.object(service, "_get_user_configs", new_callable=AsyncMock, return_value=sample_user_settings):
            result = await service.assemble_tuning_prompt(
                product_id=PRODUCT_ID,
                user_id=USER_ID,
                sections=["tech_stack", "description"],
            )

        assert "prompt" in result
        assert "sections_included" in result
        assert set(result["sections_included"]) == {"tech_stack", "description"}

    @pytest.mark.asyncio
    async def test_excludes_unselected_sections_from_prompt(
        self, mock_db_manager, mock_websocket_manager, sample_product, sample_user_settings
    ):
        """Sections not in the selection list should not appear in sections_included."""
        from src.giljo_mcp.services.product_tuning_service import ProductTuningService

        db_manager, session = mock_db_manager
        service = ProductTuningService(db_manager, TENANT_KEY, websocket_manager=mock_websocket_manager)

        session.execute = AsyncMock(
            return_value=Mock(scalar_one_or_none=Mock(return_value=sample_product))
        )

        with patch.object(service, "_get_user_configs", new_callable=AsyncMock, return_value=sample_user_settings):
            result = await service.assemble_tuning_prompt(
                product_id=PRODUCT_ID,
                user_id=USER_ID,
                sections=["description"],
            )

        assert "architecture" not in result["sections_included"]
        assert "tech_stack" not in result["sections_included"]

    @pytest.mark.asyncio
    async def test_prompt_contains_product_id(
        self, mock_db_manager, mock_websocket_manager, sample_product, sample_user_settings
    ):
        """The assembled prompt must include the product_id for the MCP tool call."""
        from src.giljo_mcp.services.product_tuning_service import ProductTuningService

        db_manager, session = mock_db_manager
        service = ProductTuningService(db_manager, TENANT_KEY, websocket_manager=mock_websocket_manager)

        session.execute = AsyncMock(
            return_value=Mock(scalar_one_or_none=Mock(return_value=sample_product))
        )

        with patch.object(service, "_get_user_configs", new_callable=AsyncMock, return_value=sample_user_settings):
            result = await service.assemble_tuning_prompt(
                product_id=PRODUCT_ID,
                user_id=USER_ID,
                sections=["tech_stack"],
            )

        assert PRODUCT_ID in result["prompt"]

    @pytest.mark.asyncio
    async def test_prompt_contains_product_name(
        self, mock_db_manager, mock_websocket_manager, sample_product, sample_user_settings
    ):
        """The assembled prompt must include the product name."""
        from src.giljo_mcp.services.product_tuning_service import ProductTuningService

        db_manager, session = mock_db_manager
        service = ProductTuningService(db_manager, TENANT_KEY, websocket_manager=mock_websocket_manager)

        session.execute = AsyncMock(
            return_value=Mock(scalar_one_or_none=Mock(return_value=sample_product))
        )

        with patch.object(service, "_get_user_configs", new_callable=AsyncMock, return_value=sample_user_settings):
            result = await service.assemble_tuning_prompt(
                product_id=PRODUCT_ID,
                user_id=USER_ID,
                sections=["description"],
            )

        assert sample_product.name in result["prompt"]

    @pytest.mark.asyncio
    async def test_prompt_contains_four_phases(
        self, mock_db_manager, mock_websocket_manager, sample_product, sample_user_settings
    ):
        """The v2 prompt must contain all four interactive phases."""
        from src.giljo_mcp.services.product_tuning_service import ProductTuningService

        db_manager, session = mock_db_manager
        service = ProductTuningService(db_manager, TENANT_KEY, websocket_manager=mock_websocket_manager)

        session.execute = AsyncMock(
            return_value=Mock(scalar_one_or_none=Mock(return_value=sample_product))
        )

        with patch.object(service, "_get_user_configs", new_callable=AsyncMock, return_value=sample_user_settings):
            result = await service.assemble_tuning_prompt(
                product_id=PRODUCT_ID,
                user_id=USER_ID,
                sections=["description"],
            )

        prompt = result["prompt"]
        assert "Phase 1: RESEARCH" in prompt
        assert "Phase 2: QUICK SCAN" in prompt
        assert "Phase 3: INTERACTIVE REVIEW" in prompt
        assert "Phase 4: SUBMIT" in prompt


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
        # 0840d: tuple format (toggle_config, depth_config) for _get_user_configs
        settings_arch_off = (
            {
                "version": "4.0",
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
            {"memory_last_n_projects": 3, "git_commits": 25},
        )

        with patch.object(service, "_get_user_configs", new_callable=AsyncMock, return_value=settings_arch_off):
            result = await service.assemble_tuning_prompt(
                product_id=PRODUCT_ID,
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

        # 0840d: tuple format (toggle_config, depth_config) for _get_user_configs
        all_off = (
            {
                "version": "4.0",
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
            {"memory_last_n_projects": 3},
        )

        with patch.object(service, "_get_user_configs", new_callable=AsyncMock, return_value=all_off):
            with pytest.raises(ValidationError):
                await service.assemble_tuning_prompt(
                    product_id=PRODUCT_ID,
                    user_id=USER_ID,
                    sections=["description", "tech_stack", "architecture"],
                )


# ============================================================================
# TEST CLASS 3: assemble_tuning_prompt — 360 Memory and Git Integration
# ============================================================================


class TestAssembleTuningPromptV2Features:
    """Test v2 interactive prompt features: agent-driven research, vision note, structure."""

    @pytest.mark.asyncio
    async def test_prompt_instructs_agent_to_fetch_context_via_mcp(
        self, mock_db_manager, mock_websocket_manager, sample_product, sample_user_settings
    ):
        """v2 prompt tells the agent to call fetch_context for 360 memory (not pre-serialized)."""
        from src.giljo_mcp.services.product_tuning_service import ProductTuningService

        db_manager, session = mock_db_manager
        service = ProductTuningService(db_manager, TENANT_KEY, websocket_manager=mock_websocket_manager)

        session.execute = AsyncMock(
            return_value=Mock(scalar_one_or_none=Mock(return_value=sample_product))
        )

        with patch.object(service, "_get_user_configs", new_callable=AsyncMock, return_value=sample_user_settings):
            result = await service.assemble_tuning_prompt(
                product_id=PRODUCT_ID,
                user_id=USER_ID,
                sections=["description"],
            )

        assert "fetch_context" in result["prompt"]
        assert "memory_360" in result["prompt"]

    @pytest.mark.asyncio
    async def test_includes_vision_note_when_vision_documents_selected(
        self, mock_db_manager, mock_websocket_manager, sample_product, sample_user_settings
    ):
        """When vision_documents is selected, prompt should include the special handling note."""
        from src.giljo_mcp.services.product_tuning_service import ProductTuningService

        db_manager, session = mock_db_manager
        service = ProductTuningService(db_manager, TENANT_KEY, websocket_manager=mock_websocket_manager)

        session.execute = AsyncMock(
            return_value=Mock(scalar_one_or_none=Mock(return_value=sample_product))
        )

        # Ensure vision_documents is eligible
        toggle_config, depth_config = sample_user_settings
        with patch.object(service, "_get_user_configs", new_callable=AsyncMock, return_value=(toggle_config, depth_config)), \
             patch.object(service, "_get_eligible_sections", return_value=["description", "vision_documents"]):
            result = await service.assemble_tuning_prompt(
                product_id=PRODUCT_ID,
                user_id=USER_ID,
                sections=["description", "vision_documents"],
            )

        assert "Vision Documents are historical records" in result["prompt"]

    @pytest.mark.asyncio
    async def test_omits_vision_note_when_vision_documents_not_selected(
        self, mock_db_manager, mock_websocket_manager, sample_product, sample_user_settings
    ):
        """When vision_documents is NOT selected, prompt should not include the note."""
        from src.giljo_mcp.services.product_tuning_service import ProductTuningService

        db_manager, session = mock_db_manager
        service = ProductTuningService(db_manager, TENANT_KEY, websocket_manager=mock_websocket_manager)

        session.execute = AsyncMock(
            return_value=Mock(scalar_one_or_none=Mock(return_value=sample_product))
        )

        with patch.object(service, "_get_user_configs", new_callable=AsyncMock, return_value=sample_user_settings):
            result = await service.assemble_tuning_prompt(
                product_id=PRODUCT_ID,
                user_id=USER_ID,
                sections=["description"],
            )

        assert "Vision Documents are historical records" not in result["prompt"]

    @pytest.mark.asyncio
    async def test_returns_correct_structure(
        self, mock_db_manager, mock_websocket_manager, sample_product, sample_user_settings
    ):
        """Return value should contain prompt, sections_included, lookback_depth=None, git_enabled=False."""
        from src.giljo_mcp.services.product_tuning_service import ProductTuningService

        db_manager, session = mock_db_manager
        service = ProductTuningService(db_manager, TENANT_KEY, websocket_manager=mock_websocket_manager)

        session.execute = AsyncMock(
            return_value=Mock(scalar_one_or_none=Mock(return_value=sample_product))
        )

        with patch.object(service, "_get_user_configs", new_callable=AsyncMock, return_value=sample_user_settings):
            result = await service.assemble_tuning_prompt(
                product_id=PRODUCT_ID,
                user_id=USER_ID,
                sections=["description", "tech_stack"],
            )

        assert isinstance(result["prompt"], str)
        assert isinstance(result["sections_included"], list)
        assert result["lookback_depth"] is None
        assert result["git_enabled"] is False

    @pytest.mark.asyncio
    async def test_prompt_includes_interactive_wait_instruction(
        self, mock_db_manager, mock_websocket_manager, sample_product, sample_user_settings
    ):
        """v2 prompt must instruct the agent to wait for user approval between sections."""
        from src.giljo_mcp.services.product_tuning_service import ProductTuningService

        db_manager, session = mock_db_manager
        service = ProductTuningService(db_manager, TENANT_KEY, websocket_manager=mock_websocket_manager)

        session.execute = AsyncMock(
            return_value=Mock(scalar_one_or_none=Mock(return_value=sample_product))
        )

        with patch.object(service, "_get_user_configs", new_callable=AsyncMock, return_value=sample_user_settings):
            result = await service.assemble_tuning_prompt(
                product_id=PRODUCT_ID,
                user_id=USER_ID,
                sections=["description"],
            )

        assert "Wait for user approval" in result["prompt"]


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

        with patch.object(service, "_get_user_configs", new_callable=AsyncMock, return_value=sample_user_settings):
            with pytest.raises(ValidationError):
                await service.assemble_tuning_prompt(
                    product_id=PRODUCT_ID,
                    user_id=USER_ID,
                    sections=[],
                )

    @pytest.mark.asyncio
    async def test_prompt_includes_submit_tuning_review_instruction(
        self, mock_db_manager, mock_websocket_manager, sample_product, sample_user_settings
    ):
        """Prompt must instruct the agent to call submit_tuning_review MCP tool."""
        from src.giljo_mcp.services.product_tuning_service import ProductTuningService

        db_manager, session = mock_db_manager
        service = ProductTuningService(db_manager, TENANT_KEY, websocket_manager=mock_websocket_manager)

        session.execute = AsyncMock(
            return_value=Mock(scalar_one_or_none=Mock(return_value=sample_product))
        )

        with patch.object(service, "_get_user_configs", new_callable=AsyncMock, return_value=sample_user_settings):
            result = await service.assemble_tuning_prompt(
                product_id=PRODUCT_ID,
                user_id=USER_ID,
                sections=["description"],
            )

        assert "submit_tuning_review" in result["prompt"]


# ============================================================================
# TEST CLASS 5: apply_tuning_updates
# ============================================================================


DRIFT_PROPOSALS = [
    {
        "section": "description",
        "drift_detected": True,
        "current_summary": "An AI agent orchestration platform",
        "evidence": "Redis caching added",
        "proposed_value": "Updated AI orchestration platform with Redis caching",
        "confidence": "medium",
        "reasoning": "Description should reflect caching addition",
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
    {
        "section": "core_features",
        "drift_detected": True,
        "current_summary": "Agent orchestration, project management, 360 memory",
        "evidence": "Caching layer added",
        "proposed_value": "Agent orchestration, project management, 360 memory, caching",
        "confidence": "medium",
        "reasoning": "Core features expanded",
    },
    {
        "section": "quality_standards",
        "drift_detected": True,
        "current_summary": "80% test coverage, all endpoints tested",
        "evidence": "Coverage target increased",
        "proposed_value": "90% test coverage, all endpoints tested, performance benchmarks",
        "confidence": "high",
        "reasoning": "Quality bar raised",
    },
    {
        "section": "target_platforms",
        "drift_detected": True,
        "current_summary": "windows, linux",
        "evidence": "macOS support added",
        "proposed_value": "windows, linux, macos",
        "confidence": "high",
        "reasoning": "macOS now supported",
    },
]


class TestBuildUpdateKwargs:
    """Test _build_update_kwargs maps proposals to ProductService kwargs correctly."""

    def test_maps_direct_fields(self):
        """Direct-type sections (description, core_features) map to flat kwargs."""
        from src.giljo_mcp.services.product_tuning_service import ProductTuningService

        service = ProductTuningService.__new__(ProductTuningService)
        kwargs, sections = service._build_update_kwargs(DRIFT_PROPOSALS)

        assert kwargs["description"] == "Updated AI orchestration platform with Redis caching"
        assert kwargs["core_features"] == "Agent orchestration, project management, 360 memory, caching"
        assert "description" in sections
        assert "core_features" in sections

    def test_maps_relation_field_to_nested_dict(self):
        """relation_field sections (quality_standards) map to nested test_config dict."""
        from src.giljo_mcp.services.product_tuning_service import ProductTuningService

        service = ProductTuningService.__new__(ProductTuningService)
        kwargs, sections = service._build_update_kwargs(DRIFT_PROPOSALS)

        assert "test_config" in kwargs
        assert kwargs["test_config"]["quality_standards"] == "90% test coverage, all endpoints tested, performance benchmarks"
        assert "quality_standards" in sections

    def test_skips_no_drift_proposals(self):
        """Proposals with drift_detected=False must not appear in kwargs."""
        from src.giljo_mcp.services.product_tuning_service import ProductTuningService

        service = ProductTuningService.__new__(ProductTuningService)
        kwargs, sections = service._build_update_kwargs(DRIFT_PROPOSALS)

        assert "architecture" not in kwargs
        assert "architecture" not in sections

    def test_skips_unknown_sections(self):
        """Proposals with unrecognized section keys are silently skipped."""
        from src.giljo_mcp.services.product_tuning_service import ProductTuningService

        service = ProductTuningService.__new__(ProductTuningService)
        proposals = [{"section": "nonexistent_field", "drift_detected": True, "proposed_value": "x"}]
        kwargs, sections = service._build_update_kwargs(proposals)

        assert kwargs == {}
        assert sections == []

    def test_returns_correct_section_count(self):
        """Should return exactly the drift-detected sections that have valid mappings."""
        from src.giljo_mcp.services.product_tuning_service import ProductTuningService

        service = ProductTuningService.__new__(ProductTuningService)
        kwargs, sections = service._build_update_kwargs(DRIFT_PROPOSALS)

        assert len(sections) == 4
        assert set(sections) == {"description", "core_features", "quality_standards", "target_platforms"}


class TestApplyTuningUpdates:
    """Test that apply_tuning_updates delegates to ProductService.update_product."""

    @pytest.mark.asyncio
    async def test_calls_product_service_update(
        self, mock_db_manager, mock_websocket_manager, sample_product
    ):
        """Should delegate field writes to ProductService.update_product."""
        from src.giljo_mcp.services.product_tuning_service import ProductTuningService

        db_manager, session = mock_db_manager
        service = ProductTuningService(db_manager, TENANT_KEY, websocket_manager=mock_websocket_manager)

        session.execute = AsyncMock(
            return_value=Mock(scalar_one_or_none=Mock(return_value=sample_product))
        )
        session.commit = AsyncMock()

        with patch("src.giljo_mcp.services.product_service.ProductService") as MockPS:
            mock_ps_instance = AsyncMock()
            MockPS.return_value = mock_ps_instance

            result = await service.apply_tuning_updates(
                product_id=PRODUCT_ID,
                proposals=DRIFT_PROPOSALS,
            )

        mock_ps_instance.update_product.assert_called_once()
        call_kwargs = mock_ps_instance.update_product.call_args
        assert call_kwargs.args[0] == PRODUCT_ID
        assert "description" in call_kwargs.kwargs
        assert "core_features" in call_kwargs.kwargs
        assert result["success"] is True
        assert result["applied_count"] == 4

    @pytest.mark.asyncio
    async def test_skips_product_service_when_no_drift(
        self, mock_db_manager, mock_websocket_manager, sample_product
    ):
        """When no proposals have drift, ProductService should not be called."""
        from src.giljo_mcp.services.product_tuning_service import ProductTuningService

        db_manager, session = mock_db_manager
        service = ProductTuningService(db_manager, TENANT_KEY, websocket_manager=mock_websocket_manager)

        session.execute = AsyncMock(
            return_value=Mock(scalar_one_or_none=Mock(return_value=sample_product))
        )
        session.commit = AsyncMock()

        no_drift = [{"section": "description", "drift_detected": False, "proposed_value": "x"}]

        with patch("src.giljo_mcp.services.product_service.ProductService") as MockPS:
            result = await service.apply_tuning_updates(
                product_id=PRODUCT_ID,
                proposals=no_drift,
            )

        MockPS.return_value.update_product.assert_not_called()
        assert result["applied_count"] == 0

    @pytest.mark.asyncio
    async def test_sets_last_tuned_at(
        self, mock_db_manager, mock_websocket_manager, sample_product
    ):
        """Should stamp tuning_state.last_tuned_at after applying updates."""
        from src.giljo_mcp.services.product_tuning_service import ProductTuningService

        db_manager, session = mock_db_manager
        sample_product.tuning_state = None
        service = ProductTuningService(db_manager, TENANT_KEY, websocket_manager=mock_websocket_manager)

        session.execute = AsyncMock(
            return_value=Mock(scalar_one_or_none=Mock(return_value=sample_product))
        )
        session.commit = AsyncMock()

        with patch("src.giljo_mcp.services.product_service.ProductService") as MockPS:
            MockPS.return_value = AsyncMock()
            await service.apply_tuning_updates(
                product_id=PRODUCT_ID,
                proposals=DRIFT_PROPOSALS,
            )

        assert sample_product.tuning_state is not None
        assert sample_product.tuning_state.get("last_tuned_at") is not None

    @pytest.mark.asyncio
    async def test_emits_context_updated_websocket_event(
        self, mock_db_manager, mock_websocket_manager, sample_product
    ):
        """Should emit product:context_updated WebSocket event after applying."""
        from src.giljo_mcp.services.product_tuning_service import ProductTuningService

        db_manager, session = mock_db_manager
        service = ProductTuningService(db_manager, TENANT_KEY, websocket_manager=mock_websocket_manager)

        session.execute = AsyncMock(
            return_value=Mock(scalar_one_or_none=Mock(return_value=sample_product))
        )
        session.commit = AsyncMock()

        with patch("src.giljo_mcp.services.product_service.ProductService") as MockPS:
            MockPS.return_value = AsyncMock()
            await service.apply_tuning_updates(
                product_id=PRODUCT_ID,
                proposals=DRIFT_PROPOSALS,
            )

        mock_websocket_manager.broadcast_to_tenant.assert_called_once()
        call_kwargs = mock_websocket_manager.broadcast_to_tenant.call_args.kwargs
        assert call_kwargs["tenant_key"] == TENANT_KEY
        assert call_kwargs["event_type"] == "product:context_updated"

    @pytest.mark.asyncio
    async def test_raises_not_found_for_missing_product(
        self, mock_db_manager, mock_websocket_manager
    ):
        """Should raise ResourceNotFoundError when product does not exist."""
        from src.giljo_mcp.services.product_tuning_service import ProductTuningService

        db_manager, session = mock_db_manager
        service = ProductTuningService(db_manager, TENANT_KEY, websocket_manager=mock_websocket_manager)

        with patch("src.giljo_mcp.services.product_service.ProductService") as MockPS:
            mock_ps_instance = AsyncMock()
            mock_ps_instance.update_product.side_effect = ResourceNotFoundError(
                message="Product not found", context={"product_id": "nonexistent-id"}
            )
            MockPS.return_value = mock_ps_instance

            with pytest.raises(ResourceNotFoundError):
                await service.apply_tuning_updates(
                    product_id="nonexistent-id",
                    proposals=DRIFT_PROPOSALS,
                )


# ============================================================================
# TEST CLASS 6: Tenant Isolation
# ============================================================================


class TestTenantIsolation:
    """Verify that all operations enforce tenant_key filtering."""

    @pytest.mark.asyncio
    async def test_assemble_prompt_filters_by_tenant(
        self, mock_db_manager, mock_websocket_manager, sample_product, sample_user_settings
    ):
        """Product lookup in assemble_tuning_prompt must filter by tenant_key."""
        from src.giljo_mcp.services.product_tuning_service import ProductTuningService

        db_manager, session = mock_db_manager
        service = ProductTuningService(db_manager, TENANT_KEY, websocket_manager=mock_websocket_manager)

        session.execute = AsyncMock(
            return_value=Mock(scalar_one_or_none=Mock(return_value=sample_product))
        )

        with patch.object(service, "_get_user_configs", new_callable=AsyncMock, return_value=sample_user_settings):
            await service.assemble_tuning_prompt(
                product_id=PRODUCT_ID,
                user_id=USER_ID,
                sections=["description"],
            )

        # Verify execute was called — the implementation must include tenant_key in the query
        session.execute.assert_called_once()

    @pytest.mark.asyncio
    async def test_apply_tuning_updates_passes_tenant_to_product_service(
        self, mock_db_manager, mock_websocket_manager, sample_product
    ):
        """apply_tuning_updates must pass tenant_key to ProductService for isolation."""
        from src.giljo_mcp.services.product_tuning_service import ProductTuningService

        db_manager, session = mock_db_manager
        service = ProductTuningService(db_manager, TENANT_KEY, websocket_manager=mock_websocket_manager)

        session.execute = AsyncMock(
            return_value=Mock(scalar_one_or_none=Mock(return_value=sample_product))
        )
        session.commit = AsyncMock()

        with patch("src.giljo_mcp.services.product_service.ProductService") as MockPS:
            mock_ps_instance = AsyncMock()
            MockPS.return_value = mock_ps_instance

            await service.apply_tuning_updates(
                product_id=PRODUCT_ID,
                proposals=DRIFT_PROPOSALS,
            )

        MockPS.assert_called_once_with(db_manager, TENANT_KEY)


# ============================================================================
# TEST CLASS 7: ProductService Allowlist + Validation Guards (0962a)
# ============================================================================


class TestBuildUpdateKwargsTargetPlatforms:
    """Test that target_platforms string is converted to a list, not stored as-is."""

    def test_target_platforms_string_converts_to_list(self):
        """A comma-separated target_platforms string must be split into a list."""
        from src.giljo_mcp.services.product_tuning_service import ProductTuningService

        service = ProductTuningService.__new__(ProductTuningService)
        proposals = [
            {
                "section": "target_platforms",
                "drift_detected": True,
                "proposed_value": "windows, linux, macos",
            }
        ]
        kwargs, sections = service._build_update_kwargs(proposals)

        assert kwargs["target_platforms"] == ["windows", "linux", "macos"]
        assert "target_platforms" in sections


class TestProductServiceAllowlist:
    """Test that update_product silently ignores fields not in the allowlist."""

    def test_allowlist_excludes_tenant_key(self):
        """update_product must not write tenant_key even if it is passed as a kwarg."""
        from src.giljo_mcp.services.product_service import _ALLOWED_PRODUCT_FIELDS

        assert "tenant_key" not in _ALLOWED_PRODUCT_FIELDS

    def test_allowlist_excludes_deleted_at(self):
        """update_product must not write deleted_at even if it is passed as a kwarg."""
        from src.giljo_mcp.services.product_service import _ALLOWED_PRODUCT_FIELDS

        assert "deleted_at" not in _ALLOWED_PRODUCT_FIELDS

    def test_allowlist_contains_all_expected_fields(self):
        """Allowlist must contain exactly the intended writable fields.

        quality_standards is intentionally absent — it is written via product_test_configs
        (the canonical location). The products.quality_standards column is legacy and
        deferred for removal in the next baseline squash (Handover 0962d).
        """
        from src.giljo_mcp.services.product_service import _ALLOWED_PRODUCT_FIELDS

        expected = {
            "name",
            "description",
            "project_path",
            "core_features",
            "brand_guidelines",
            "extraction_custom_instructions",
            "target_platforms",
        }
        assert _ALLOWED_PRODUCT_FIELDS == expected


class TestValidateProposals:
    """Test _validate_proposals input validation including proposed_value checks."""

    def test_rejects_integer_proposed_value(self):
        """proposed_value must be str, dict, list, or None — integer is invalid."""
        from src.giljo_mcp.tools.submit_tuning_review import _validate_proposals

        proposals = [
            {
                "section": "description",
                "drift_detected": True,
                "proposed_value": 42,
            }
        ]
        errors = _validate_proposals(proposals)

        assert any("proposed_value" in e for e in errors)
        assert any("int" in e for e in errors)

    def test_rejects_proposed_value_over_10000_chars(self):
        """proposed_value strings longer than 10000 characters must be rejected."""
        from src.giljo_mcp.tools.submit_tuning_review import _validate_proposals

        proposals = [
            {
                "section": "description",
                "drift_detected": True,
                "proposed_value": "x" * 10001,
            }
        ]
        errors = _validate_proposals(proposals)

        assert any("proposed_value" in e for e in errors)
        assert any("10000" in e for e in errors)

    def test_accepts_proposed_value_at_10000_chars(self):
        """proposed_value string of exactly 10000 characters must be accepted."""
        from src.giljo_mcp.tools.submit_tuning_review import _validate_proposals

        proposals = [
            {
                "section": "description",
                "drift_detected": True,
                "proposed_value": "x" * 10000,
            }
        ]
        errors = _validate_proposals(proposals)

        assert not any("proposed_value" in e for e in errors)

    def test_accepts_none_proposed_value(self):
        """proposed_value of None must be accepted."""
        from src.giljo_mcp.tools.submit_tuning_review import _validate_proposals

        proposals = [
            {
                "section": "description",
                "drift_detected": True,
                "proposed_value": None,
            }
        ]
        errors = _validate_proposals(proposals)

        assert not any("proposed_value" in e for e in errors)

    def test_accepts_dict_proposed_value(self):
        """proposed_value of dict type must be accepted."""
        from src.giljo_mcp.tools.submit_tuning_review import _validate_proposals

        proposals = [
            {
                "section": "tech_stack",
                "drift_detected": True,
                "proposed_value": {"programming_languages": "Python"},
            }
        ]
        errors = _validate_proposals(proposals)

        assert not any("proposed_value" in e for e in errors)

    def test_accepts_list_proposed_value_for_target_platforms(self):
        """proposed_value list of strings must be accepted for target_platforms section."""
        from src.giljo_mcp.tools.submit_tuning_review import _validate_proposals

        proposals = [
            {
                "section": "target_platforms",
                "drift_detected": True,
                "proposed_value": ["windows", "linux", "macos"],
            }
        ]
        errors = _validate_proposals(proposals)

        assert not any("proposed_value" in e for e in errors)

    def test_rejects_list_with_non_string_items_for_target_platforms(self):
        """target_platforms proposed_value list must contain only strings."""
        from src.giljo_mcp.tools.submit_tuning_review import _validate_proposals

        proposals = [
            {
                "section": "target_platforms",
                "drift_detected": True,
                "proposed_value": ["windows", 123],
            }
        ]
        errors = _validate_proposals(proposals)

        assert any("proposed_value" in e for e in errors)


class TestRelationSectionStringRejection:
    """Test that relation sections (tech_stack, architecture) reject string proposed_value."""

    def test_relation_section_with_string_value_is_skipped(self):
        """When a relation section has a string value, it must be skipped — not applied."""
        from src.giljo_mcp.services.product_tuning_service import ProductTuningService

        service = ProductTuningService.__new__(ProductTuningService)
        service._logger = Mock()

        proposals = [
            {
                "section": "tech_stack",
                "drift_detected": True,
                "proposed_value": "Python, FastAPI, PostgreSQL",
            }
        ]
        kwargs, sections = service._build_update_kwargs(proposals)

        assert "tech_stack" not in kwargs
        assert "tech_stack" not in sections

    def test_relation_section_with_string_value_logs_warning(self):
        """Skipped relation sections with string values must emit a warning log."""
        from src.giljo_mcp.services.product_tuning_service import ProductTuningService

        service = ProductTuningService.__new__(ProductTuningService)
        service._logger = Mock()

        proposals = [
            {
                "section": "architecture",
                "drift_detected": True,
                "proposed_value": "monolith",
            }
        ]
        service._build_update_kwargs(proposals)

        service._logger.warning.assert_called_once()
        warning_args = service._logger.warning.call_args[0]
        assert "architecture" in warning_args[1]

    def test_relation_section_with_dict_value_is_applied(self):
        """Relation sections with dict values must still be applied normally."""
        from src.giljo_mcp.services.product_tuning_service import ProductTuningService

        service = ProductTuningService.__new__(ProductTuningService)
        service._logger = Mock()

        proposals = [
            {
                "section": "tech_stack",
                "drift_detected": True,
                "proposed_value": {"programming_languages": "Python 3.12"},
            }
        ]
        kwargs, sections = service._build_update_kwargs(proposals)

        assert "tech_stack" in kwargs
        assert kwargs["tech_stack"] == {"programming_languages": "Python 3.12"}
        assert "tech_stack" in sections
