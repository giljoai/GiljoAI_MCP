"""
Tests for CH2 protocol injection and depth defaults consolidation (Handover 0823).

Verifies:
1. DEFAULT_DEPTHS in fetch_context.py matches DEFAULT_DEPTH_CONFIG from defaults.py
2. CH2 protocol generates inline fetch_context() calls for enabled categories
3. Disabled categories are excluded from CH2
4. depth_config values appear correctly in generated fetch calls
5. Framing text reflects depth (e.g. "Last 3" for memory_360=3)
"""


from src.giljo_mcp.config.defaults import DEFAULT_DEPTH_CONFIG as RAW_DEPTH_CONFIG


class TestDepthDefaultsConsolidation:
    """Phase 1: Verify single source of truth for depth defaults."""

    def test_fetch_context_defaults_match_canonical_defaults(self):
        """DEFAULT_DEPTHS in fetch_context.py must derive from DEFAULT_DEPTH_CONFIG in defaults.py."""
        from src.giljo_mcp.tools.context_tools.fetch_context import DEFAULT_DEPTHS

        canonical = RAW_DEPTH_CONFIG["depths"]

        # memory_360: canonical says 3
        assert DEFAULT_DEPTHS["memory_360"] == canonical["memory_360"], (
            f"memory_360 mismatch: fetch_context={DEFAULT_DEPTHS['memory_360']}, "
            f"defaults.py={canonical['memory_360']}"
        )

        # git_history: canonical says 25 (per handover decision)
        assert DEFAULT_DEPTHS["git_history"] == canonical["git_history"], (
            f"git_history mismatch: fetch_context={DEFAULT_DEPTHS['git_history']}, "
            f"defaults.py={canonical['git_history']}"
        )

        # vision_documents
        assert DEFAULT_DEPTHS["vision_documents"] == canonical["vision_documents"]

        # agent_templates
        assert DEFAULT_DEPTHS["agent_templates"] == canonical["agent_templates"]

    def test_canonical_defaults_have_expected_values(self):
        """Verify canonical defaults match handover 0823 decision."""
        canonical = RAW_DEPTH_CONFIG["depths"]
        assert canonical["memory_360"] == 3
        assert canonical["git_history"] == 25
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

    def test_ch2_depth_config_in_memory_360_call(self):
        """memory_360 fetch call must include depth_config with user's value."""
        toggles = {"memory_360": True}
        depth = {"memory_360": 7}
        ch2 = self._build_ch2(field_toggles=toggles, depth_config=depth)

        assert '"memory_360": 7' in ch2 or "'memory_360': 7" in ch2

    def test_ch2_depth_config_in_git_history_call(self):
        """git_history fetch call must include depth_config with user's value."""
        toggles = {"git_history": True}
        depth = {"git_history": 50}
        ch2 = self._build_ch2(field_toggles=toggles, depth_config=depth)

        assert '"git_history": 50' in ch2 or "'git_history': 50" in ch2

    def test_ch2_depth_config_in_vision_call(self):
        """vision_documents fetch call must include depth_config."""
        toggles = {"vision_documents": True}
        depth = {"vision_documents": "full"}
        ch2 = self._build_ch2(field_toggles=toggles, depth_config=depth)

        assert '"vision_documents": "full"' in ch2 or "'vision_documents': 'full'" in ch2

    def test_ch2_framing_reflects_memory_depth(self):
        """Framing text should say 'Last N' matching depth."""
        toggles = {"memory_360": True}
        depth = {"memory_360": 3}
        ch2 = self._build_ch2(field_toggles=toggles, depth_config=depth)
        assert "Last 3" in ch2

    def test_ch2_framing_reflects_git_depth(self):
        """Framing text should say 'Last N' matching git commits depth."""
        toggles = {"git_history": True}
        depth = {"git_history": 50}
        ch2 = self._build_ch2(field_toggles=toggles, depth_config=depth)
        assert "Last 50" in ch2

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
