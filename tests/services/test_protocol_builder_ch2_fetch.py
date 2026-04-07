"""
Tests for CH2 protocol injection and depth defaults consolidation (Handover 0823, 0823b).

Verifies:
1. DEFAULT_DEPTHS in fetch_context.py matches DEFAULT_DEPTH_CONFIG from defaults.py
2. CH2 protocol generates inline fetch_context() calls for enabled categories
3. Disabled categories are excluded from CH2
4. depth_config values are NOT snapshotted into fetch calls (Handover 0823b)
5. Framing text is generic, not depth-specific (Handover 0823b)
6. fetch_context reads user depth_config from DB when not provided (Handover 0823b)
"""


from src.giljo_mcp.config.defaults import DEFAULT_DEPTH_CONFIG as RAW_DEPTH_CONFIG


class TestDepthDefaultsConsolidation:
    """Phase 1: Verify single source of truth for depth defaults."""

    def test_fetch_context_defaults_match_canonical_defaults(self):
        """DEFAULT_DEPTHS in fetch_context.py must derive from DEFAULT_DEPTH_CONFIG in defaults.py."""
        from src.giljo_mcp.tools.context_tools.fetch_context import DEFAULT_DEPTHS

        # Handover 0840d: DEFAULT_DEPTH_CONFIG is now a flat dict with column-style keys
        canonical = RAW_DEPTH_CONFIG

        # memory_360 in DEFAULT_DEPTHS maps to memory_last_n_projects in canonical
        assert DEFAULT_DEPTHS["memory_360"] == canonical["memory_last_n_projects"], (
            f"memory_360 mismatch: fetch_context={DEFAULT_DEPTHS['memory_360']}, "
            f"defaults.py={canonical['memory_last_n_projects']}"
        )

        # git_history in DEFAULT_DEPTHS maps to git_commits in canonical
        assert DEFAULT_DEPTHS["git_history"] == canonical["git_commits"], (
            f"git_history mismatch: fetch_context={DEFAULT_DEPTHS['git_history']}, "
            f"defaults.py={canonical['git_commits']}"
        )

        # vision_documents - same key
        assert DEFAULT_DEPTHS["vision_documents"] == canonical["vision_documents"]

        # agent_templates - same key
        assert DEFAULT_DEPTHS["agent_templates"] == canonical["agent_templates"]

    def test_canonical_defaults_have_expected_values(self):
        """Verify canonical defaults match handover 0823 decision."""
        canonical = RAW_DEPTH_CONFIG
        assert canonical["memory_last_n_projects"] == 3
        assert canonical["git_commits"] == 25
        assert canonical["vision_documents"] == "medium"
        assert canonical["agent_templates"] == "type_only"


class TestCH2InlineFetchCalls:
    """Phase 2: Verify CH2 generates inline fetch_context() calls."""

    def _build_ch2(self, field_toggles=None, depth_config=None,
                   product_id="prod-123", tenant_key="tk_test"):
        """Helper to build CH2 with test parameters."""
        from src.giljo_mcp.services.protocol_builder import _build_ch2_startup

        if field_toggles is None:
            field_toggles = {
                "product_core": True,
                "tech_stack": True,
                "memory_360": True,
                "vision_documents": True,
                "git_history": True,
                "architecture": True,
                "testing": True,
                "agent_templates": True,
                "project_description": True,
            }
        if depth_config is None:
            depth_config = {
                "memory_360": 3,
                "git_history": 25,
                "vision_documents": "medium",
                "agent_templates": "type_only",
            }
        return _build_ch2_startup(
            orchestrator_id="orch-001",
            project_id="proj-001",
            field_toggles=field_toggles,
            depth_config=depth_config,
            product_id=product_id,
            tenant_key=tenant_key,
        )

    def test_ch2_contains_fetch_context_calls(self):
        """CH2 Step 2 must contain explicit fetch_context() calls."""
        ch2 = self._build_ch2()
        assert "fetch_context(" in ch2, "CH2 must contain fetch_context() calls"

    def test_ch2_contains_mandatory_framing(self):
        """CH2 Step 2 must tell agent calls are NOT optional."""
        ch2 = self._build_ch2()
        assert "MUST" in ch2 or "NOT optional" in ch2 or "Do NOT skip" in ch2

    def test_ch2_includes_product_id_and_tenant_key(self):
        """Each fetch call must include product_id and tenant_key."""
        ch2 = self._build_ch2(product_id="prod-abc", tenant_key="tk_xyz")
        assert "prod-abc" in ch2
        assert "tk_xyz" in ch2

    def test_ch2_enabled_categories_appear(self):
        """All enabled categories should have fetch calls in CH2."""
        toggles = {
            "product_core": True,
            "tech_stack": True,
            "memory_360": True,
            "project_description": True,  # inlined, should NOT appear as fetch
        }
        depth = {"memory_360": 3}
        ch2 = self._build_ch2(field_toggles=toggles, depth_config=depth)

        assert "product_core" in ch2
        assert "tech_stack" in ch2
        assert "memory_360" in ch2

    def test_ch2_disabled_categories_excluded(self):
        """Disabled categories must NOT appear as fetch calls."""
        toggles = {
            "product_core": True,
            "tech_stack": False,
            "memory_360": False,
            "vision_documents": False,
            "git_history": False,
            "architecture": False,
            "testing": False,
            "agent_templates": False,
            "project_description": True,
        }
        ch2 = self._build_ch2(field_toggles=toggles, depth_config={})

        # tech_stack is disabled, should not appear as a fetch call
        # We check that fetch_context(...tech_stack...) is NOT present
        assert 'categories=["tech_stack"]' not in ch2
        assert 'categories=["memory_360"]' not in ch2
        assert 'categories=["git_history"]' not in ch2

        # product_core IS enabled
        assert 'categories=["product_core"]' in ch2

    def test_ch2_inlined_fields_not_fetched(self):
        """project_description is inlined, should not appear as fetch call."""
        toggles = {"project_description": True, "product_core": True}
        ch2 = self._build_ch2(field_toggles=toggles, depth_config={})
        assert 'categories=["project_description"]' not in ch2

    def test_ch2_depth_config_not_in_memory_360_call(self):
        """memory_360 fetch call must NOT include depth_config (Handover 0823b)."""
        from src.giljo_mcp.services.protocol_sections.chapters_startup import _build_ch2_fetch_calls

        result = _build_ch2_fetch_calls(
            field_toggles={"memory_360": True},
            depth_config={"memory_360": 7},
            product_id="prod-123",
            tenant_key="tk_test",
        )
        # depth_config should NOT appear anywhere in the generated fetch calls
        assert "depth_config" not in result, (
            "memory_360 fetch call should not contain depth_config (0823b)"
        )

    def test_ch2_depth_config_not_in_git_history_call(self):
        """git_history fetch call must NOT include depth_config (Handover 0823b)."""
        from src.giljo_mcp.services.protocol_sections.chapters_startup import _build_ch2_fetch_calls

        result = _build_ch2_fetch_calls(
            field_toggles={"git_history": True},
            depth_config={"git_history": 50},
            product_id="prod-123",
            tenant_key="tk_test",
        )
        assert "depth_config" not in result, (
            "git_history fetch call should not contain depth_config (0823b)"
        )

    def test_ch2_depth_config_not_in_vision_call(self):
        """vision_documents fetch call must NOT include depth_config (Handover 0823b)."""
        from src.giljo_mcp.services.protocol_sections.chapters_startup import _build_ch2_fetch_calls

        result = _build_ch2_fetch_calls(
            field_toggles={"vision_documents": True},
            depth_config={"vision_documents": "full"},
            product_id="prod-123",
            tenant_key="tk_test",
        )
        assert "depth_config" not in result, (
            "vision_documents fetch call should not contain depth_config (0823b)"
        )

    def test_ch2_framing_memory_360_generic(self):
        """Framing text for memory_360 should be generic, not depth-specific (0823b)."""
        toggles = {"memory_360": True}
        depth = {"memory_360": 3}
        ch2 = self._build_ch2(field_toggles=toggles, depth_config=depth)
        assert "Recent product project closeouts" in ch2
        assert "Last 3" not in ch2

    def test_ch2_framing_git_history_generic(self):
        """Framing text for git_history should be generic, not depth-specific (0823b)."""
        toggles = {"git_history": True}
        depth = {"git_history": 50}
        ch2 = self._build_ch2(field_toggles=toggles, depth_config=depth)
        assert "Recent git commits" in ch2
        assert "Last 50" not in ch2

    def test_ch2_non_depth_categories_omit_depth_config(self):
        """Categories without depth (product_core, tech_stack) should not have depth_config."""
        toggles = {"product_core": True, "tech_stack": True}
        ch2 = self._build_ch2(field_toggles=toggles, depth_config={})

        # Find product_core fetch call - it should NOT have depth_config
        lines = ch2.split("\n")
        for line in lines:
            if 'categories=["product_core"]' in line:
                assert "depth_config" not in line

    def test_ch2_count_matches_enabled_toggles(self):
        """Number of fetch calls should match number of enabled non-inlined categories."""
        toggles = {
            "product_core": True,
            "tech_stack": True,
            "memory_360": True,
            "vision_documents": False,
            "git_history": False,
            "architecture": False,
            "testing": False,
            "agent_templates": False,
            "project_description": True,  # inlined
        }
        depth = {"memory_360": 3}
        ch2 = self._build_ch2(field_toggles=toggles, depth_config=depth)

        # Should have 3 fetch calls: product_core, tech_stack, memory_360
        count = ch2.count("fetch_context(categories=")
        assert count == 3, f"Expected 3 fetch calls, got {count}"

    def test_ch2_preserves_context_variables_block(self):
        """CH2 must keep the CONTEXT VARIABLES block."""
        ch2 = self._build_ch2()
        assert "CONTEXT VARIABLES" in ch2

    def test_ch2_preserves_other_steps(self):
        """CH2 must preserve steps 0, 1, 1b, 3-7."""
        ch2 = self._build_ch2()
        assert "STEP 0" in ch2
        assert "STEP 1:" in ch2
        assert "STEP 1b" in ch2
        assert "STEP 3" in ch2
        assert "STEP 4" in ch2

    def test_ch2_agent_templates_type_only_skipped(self):
        """agent_templates with type_only depth should not generate fetch call."""
        toggles = {"agent_templates": True}
        depth = {"agent_templates": "type_only"}
        ch2 = self._build_ch2(field_toggles=toggles, depth_config=depth)
        assert 'categories=["agent_templates"]' not in ch2

    def test_ch2_agent_templates_full_generates_fetch(self):
        """agent_templates with 'full' depth should generate fetch call."""
        toggles = {"agent_templates": True}
        depth = {"agent_templates": "full"}
        ch2 = self._build_ch2(field_toggles=toggles, depth_config=depth)
        assert 'categories=["agent_templates"]' in ch2


class TestResponseStructure:
    """Phase 3: Verify response no longer contains context_fetch_instructions."""

    # These tests verify the response from get_orchestrator_instructions
    # but require DB fixtures. They are structural assertions on the protocol.

    def test_orchestrator_protocol_receives_toggles(self):
        """_build_orchestrator_protocol must accept and pass through toggle params."""
        from src.giljo_mcp.services.protocol_builder import _build_orchestrator_protocol

        field_toggles = {"product_core": True, "tech_stack": False}
        depth_config = {"memory_360": 3}

        result = _build_orchestrator_protocol(
            cli_mode=False,
            project_id="proj-123",
            orchestrator_id="orch-456",
            tenant_key="tk_test",
            field_toggles=field_toggles,
            depth_config=depth_config,
            product_id="prod-789",
        )

        # CH2 should contain the fetch calls
        ch2 = result["ch2_startup_sequence"]
        assert 'categories=["product_core"]' in ch2
        assert 'categories=["tech_stack"]' not in ch2


class TestFetchContextDepthFromDB:
    """Phase 4 (Handover 0823b): Verify fetch_context reads depth from DB at runtime."""

    @staticmethod
    def _make_mock_user(**depth_kwargs):
        """Create a mock User object with depth columns (Handover 0840d)."""
        from unittest.mock import MagicMock
        user = MagicMock()
        user.is_active = True
        user.tenant_key = "tk_test"
        # Set depth column defaults
        user.depth_vision_documents = depth_kwargs.get("vision_documents", "medium")
        user.depth_memory_last_n = depth_kwargs.get("memory_last_n_projects", 3)
        user.depth_git_commits = depth_kwargs.get("git_commits", 25)
        user.depth_agent_templates = depth_kwargs.get("agent_templates", "type_only")
        user.depth_tech_stack_sections = depth_kwargs.get("tech_stack_sections", "all")
        user.depth_architecture = depth_kwargs.get("architecture_depth", "overview")
        return user

    def test_load_user_depth_config_normalizes_keys(self):
        """_load_user_depth_config must map DB keys to internal keys."""
        import asyncio
        from unittest.mock import AsyncMock, MagicMock

        from src.giljo_mcp.tools.context_tools.fetch_context import _load_user_depth_config

        mock_user = self._make_mock_user(
            memory_last_n_projects=5,
            git_commits=50,
            vision_documents="full",
            agent_templates="full",
        )

        # Mock the DB session and query
        mock_result = MagicMock()
        mock_result.scalar_one_or_none.return_value = mock_user

        mock_session = AsyncMock()
        mock_session.execute = AsyncMock(return_value=mock_result)
        mock_session.__aenter__ = AsyncMock(return_value=mock_session)
        mock_session.__aexit__ = AsyncMock(return_value=False)

        mock_db = MagicMock()
        mock_db.get_session_async = MagicMock(return_value=mock_session)

        result = asyncio.get_event_loop().run_until_complete(
            _load_user_depth_config("tk_test", mock_db)
        )

        assert result is not None
        assert result["memory_360"] == 5
        assert result["git_history"] == 50
        assert result["vision_documents"] == "full"
        assert result["agent_templates"] == "full"

    def test_load_user_depth_config_returns_none_when_no_user(self):
        """_load_user_depth_config returns None when no user found."""
        import asyncio
        from unittest.mock import AsyncMock, MagicMock

        from src.giljo_mcp.tools.context_tools.fetch_context import _load_user_depth_config

        mock_result = MagicMock()
        mock_result.scalar_one_or_none.return_value = None

        mock_session = AsyncMock()
        mock_session.execute = AsyncMock(return_value=mock_result)
        mock_session.__aenter__ = AsyncMock(return_value=mock_session)
        mock_session.__aexit__ = AsyncMock(return_value=False)

        mock_db = MagicMock()
        mock_db.get_session_async = MagicMock(return_value=mock_session)

        result = asyncio.get_event_loop().run_until_complete(
            _load_user_depth_config("tk_test", mock_db)
        )

        assert result is None

    def test_load_user_depth_config_returns_defaults_when_columns_have_defaults(self):
        """_load_user_depth_config returns column defaults when user has default depth values."""
        import asyncio
        from unittest.mock import AsyncMock, MagicMock

        from src.giljo_mcp.tools.context_tools.fetch_context import _load_user_depth_config

        mock_user = self._make_mock_user()  # Uses column defaults

        mock_result = MagicMock()
        mock_result.scalar_one_or_none.return_value = mock_user

        mock_session = AsyncMock()
        mock_session.execute = AsyncMock(return_value=mock_result)
        mock_session.__aenter__ = AsyncMock(return_value=mock_session)
        mock_session.__aexit__ = AsyncMock(return_value=False)

        mock_db = MagicMock()
        mock_db.get_session_async = MagicMock(return_value=mock_session)

        result = asyncio.get_event_loop().run_until_complete(
            _load_user_depth_config("tk_test", mock_db)
        )

        # Handover 0840d: columns always have defaults, so result is never None when user exists
        assert result is not None
        assert result["memory_360"] == 3  # default
        assert result["vision_documents"] == "medium"  # default

    def test_load_user_depth_config_normalizes_vision_optional(self):
        """_load_user_depth_config maps vision_documents 'optional' to 'light'."""
        import asyncio
        from unittest.mock import AsyncMock, MagicMock

        from src.giljo_mcp.tools.context_tools.fetch_context import _load_user_depth_config

        mock_user = self._make_mock_user(vision_documents="optional")

        mock_result = MagicMock()
        mock_result.scalar_one_or_none.return_value = mock_user

        mock_session = AsyncMock()
        mock_session.execute = AsyncMock(return_value=mock_result)
        mock_session.__aenter__ = AsyncMock(return_value=mock_session)
        mock_session.__aexit__ = AsyncMock(return_value=False)

        mock_db = MagicMock()
        mock_db.get_session_async = MagicMock(return_value=mock_session)

        result = asyncio.get_event_loop().run_until_complete(
            _load_user_depth_config("tk_test", mock_db)
        )

        assert result is not None
        assert result["vision_documents"] == "light"
