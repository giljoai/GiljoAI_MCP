# Copyright (c) 2024-2026 GiljoAI LLC. All rights reserved.
# Licensed under the GiljoAI Community License v1.1.
# See LICENSE in the project root for terms.
# [CE] Community Edition — source-available, single-user use only.

"""
Tests for CE-OPT-002: Verification Agent Deferral protocol text.

Verifies:
1. CH1 output contains VERIFICATION AGENT DEFERRAL guidance
2. CH3 output contains verification deferral section with correct text
3. Phase 2 orchestrator protocol contains spawn verification agent action
4. Backward compatibility: existing protocol structure is preserved
"""

from src.giljo_mcp.services.protocol_sections.agent_lifecycle import _generate_orchestrator_protocol
from src.giljo_mcp.services.protocol_sections.chapters_reference import _build_ch3_spawning_rules
from src.giljo_mcp.services.protocol_sections.chapters_startup import _build_ch1_mission


class TestCH1VerificationDeferral:
    """CH1 must include verification agent deferral guidance."""

    def test_ch1_contains_verification_deferral_heading(self):
        """CH1 output must contain the VERIFICATION AGENT DEFERRAL heading."""
        result = _build_ch1_mission()
        assert "VERIFICATION AGENT DEFERRAL" in result

    def test_ch1_deferral_mentions_deliverable_agents(self):
        """CH1 deferral text must name deliverable agent types."""
        result = _build_ch1_mission()
        assert "implementer" in result
        assert "analyzer" in result
        assert "documenter" in result

    def test_ch1_deferral_mentions_verification_agents(self):
        """CH1 deferral text must name verification agent types."""
        result = _build_ch1_mission()
        assert "tester" in result
        assert "reviewer" in result

    def test_ch1_deferral_present_for_all_tools(self):
        """Deferral text must appear regardless of tool platform."""
        for tool in ("claude-code", "codex", "gemini", "multi_terminal"):
            result = _build_ch1_mission(tool=tool)
            assert "VERIFICATION AGENT DEFERRAL" in result, f"Missing for tool={tool}"

    def test_ch1_preserves_existing_structure(self):
        """Existing CH1 sections must still be present."""
        result = _build_ch1_mission()
        assert "CH1: YOUR MISSION" in result
        assert "YOUR ROLE: PROJECT STAGING" in result
        assert "PHASE AWARENESS" in result
        assert "CRITICAL DISTINCTION" in result


class TestCH3VerificationDeferral:
    """CH3 must include verification agent deferral section."""

    def test_ch3_contains_verification_deferral_heading(self):
        """CH3 output must contain the VERIFICATION AGENT DEFERRAL heading."""
        result = _build_ch3_spawning_rules()
        assert "VERIFICATION AGENT DEFERRAL" in result

    def test_ch3_contains_staging_prohibition(self):
        """CH3 must state verification agents are NOT spawned during staging."""
        result = _build_ch3_spawning_rules()
        assert "Verification agents (tester, reviewer) are NOT spawned during staging" in result

    def test_ch3_contains_implementation_phase_instructions(self):
        """CH3 must describe the implementation phase spawning sequence."""
        result = _build_ch3_spawning_rules()
        assert "get_agent_result" in result
        assert "spawn_agent_job()" in result

    def test_ch3_deferral_present_for_all_tools(self):
        """Deferral text must appear regardless of tool platform."""
        for tool in ("claude-code", "codex", "gemini", "multi_terminal"):
            result = _build_ch3_spawning_rules(tool=tool)
            assert "VERIFICATION AGENT DEFERRAL" in result, f"Missing for tool={tool}"

    def test_ch3_preserves_existing_structure(self):
        """Existing CH3 sections must still be present."""
        result = _build_ch3_spawning_rules()
        assert "CH3: AGENT SPAWNING RULES" in result
        assert "PARAMETER REQUIREMENTS" in result
        assert "SPAWNING LIMITS" in result
        assert "VALIDATION BEFORE SPAWNING" in result


class TestPhase2VerificationSpawnAction:
    """Orchestrator Phase 2 protocol must include verification agent spawn action."""

    def _build_protocol(self, **kwargs):
        defaults = {
            "job_id": "test-job-123",
            "tenant_key": "tk_test",
            "executor_id": "exec-456",
            "execution_mode": "claude-code",
        }
        defaults.update(kwargs)
        return _generate_orchestrator_protocol(**defaults)

    def test_phase2_contains_spawn_verification_action(self):
        """Phase 2 must contain the spawn verification agent action."""
        result = self._build_protocol()
        assert "Spawn verification agent" in result

    def test_phase2_contains_get_agent_result_call(self):
        """Phase 2 verification action must reference get_agent_result."""
        result = self._build_protocol()
        assert "get_agent_result" in result

    def test_phase2_verification_present_for_all_modes(self):
        """Verification spawn action must appear for all execution modes."""
        for mode in ("claude-code", "codex", "gemini", "multi_terminal"):
            result = self._build_protocol(execution_mode=mode)
            assert "Spawn verification agent" in result, f"Missing for mode={mode}"

    def test_phase2_preserves_existing_actions(self):
        """Existing coordination actions must still be present."""
        result = self._build_protocol()
        assert "Unblock an agent" in result
        assert "Spawn a replacement agent" in result
        assert "Broadcast to team" in result
        assert "PROGRESS REPORTING" in result
