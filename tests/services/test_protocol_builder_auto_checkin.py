# Copyright (c) 2024-2026 GiljoAI LLC. All rights reserved.
# Licensed under the Elastic License 2.0.
# See LICENSE in the project root for terms.
# [CE] Community Edition.

"""
Tests for orchestrator auto check-in protocol (Handover 0904/0960, rewritten BE-6013).

BE-6013 changed CH6 from a literal-baked sleep number into a live-read loop:
the orchestrator re-reads auto_checkin_enabled / auto_checkin_interval from
get_workflow_status() on EVERY cycle. These tests pin the new contract and
guard against a regression back to the literal-bake pattern.

Verifies:
1. CH6 instructs reading the live interval from get_workflow_status each cycle.
2. CH6 does NOT hardcode a single fixed sleep number as the authoritative cadence.
3. CH6 carries the on/off branch (behaves correctly when disabled).
4. CH6 keeps the Claude Code `sleep 1 N` workaround and PowerShell/bash branch.
5. _build_orchestrator_protocol still includes/omits CH6 per its own gate.
"""

import re

from giljo_mcp.services.protocol_builder import (
    _build_ch6_auto_checkin,
    _build_orchestrator_protocol,
)


class TestCh6LiveReadContract:
    """CH6 must re-read the live interval each cycle (BE-6013)."""

    def test_ch6_instructs_reading_interval_from_get_workflow_status_each_cycle(self):
        ch6 = _build_ch6_auto_checkin(interval=10)
        assert "get_workflow_status" in ch6
        assert "auto_checkin_enabled" in ch6
        assert "auto_checkin_interval" in ch6
        # The loop must restart at the read step, proving a per-cycle re-read.
        assert "go back to STEP 1" in ch6

    def test_ch6_states_last_used_value_is_not_authoritative(self):
        ch6 = _build_ch6_auto_checkin(interval=10)
        lowered = ch6.lower()
        assert "not authoritative" in lowered
        # Must explicitly tell the orchestrator never to reuse a remembered number.
        assert "remember" in lowered or "remembered" in lowered

    def test_ch6_does_not_bake_a_single_authoritative_sleep_number(self):
        """Regression guard: the OLD pattern baked `sleep 600` / `Start-Sleep -Seconds 600`.

        With a live-read loop, the agent computes seconds = interval*60 itself each
        cycle, so the rendered text must NOT contain a concrete baked sleep command
        like `sleep 600` or `Start-Sleep -Seconds 600` that the LLM could latch onto
        as the authoritative cadence.
        """
        for interval in (5, 10, 30, 60):
            ch6 = _build_ch6_auto_checkin(interval=interval)
            baked_seconds = interval * 60
            assert f"sleep {baked_seconds}" not in ch6, (
                f"CH6 must not bake a literal `sleep {baked_seconds}` (interval={interval})"
            )
            assert f"Start-Sleep -Seconds {baked_seconds}" not in ch6, (
                f"CH6 must not bake `Start-Sleep -Seconds {baked_seconds}` (interval={interval})"
            )

    def test_ch6_instructs_computing_seconds_at_the_agent(self):
        ch6 = _build_ch6_auto_checkin(interval=10)
        assert "seconds = M * 60" in ch6

    def test_ch6_carries_on_off_branch(self):
        ch6 = _build_ch6_auto_checkin(interval=10)
        lowered = ch6.lower()
        assert "auto check-in is off" in lowered or "is false" in lowered
        # When disabled the orchestrator must NOT self-sleep.
        assert "do not sleep" in lowered

    def test_ch6_keeps_claude_code_sleep_workaround(self):
        ch6 = _build_ch6_auto_checkin(interval=10)
        assert "sleep 1 N" in ch6 or "sleep 1 <seconds>" in ch6
        assert "CLAUDE CODE NOTE" in ch6

    def test_ch6_keeps_powershell_and_bash_branch(self):
        ch6 = _build_ch6_auto_checkin(interval=10)
        assert "Start-Sleep -Seconds" in ch6
        assert "sleep <seconds>" in ch6 or re.search(r"\bsleep\b", ch6)

    def test_ch6_uses_imperative_mandatory_language(self):
        ch6 = _build_ch6_auto_checkin(interval=10)
        assert "MANDATORY EXECUTION" in ch6
        assert "Do NOT ask the user for confirmation" in ch6
        assert 'set_agent_status(status="sleeping"' in ch6
        assert "NEVER" in ch6

    def test_ch6_warns_about_token_consumption(self):
        ch6 = _build_ch6_auto_checkin(interval=10)
        assert "token consumption" in ch6.lower()

    def test_ch6_interval_is_only_a_seed(self):
        """The interval arg is a first-cycle seed only, not the authoritative cadence."""
        ch6 = _build_ch6_auto_checkin(interval=10)
        assert "seed" in ch6.lower()

    def test_ch6_interval_defaults_when_omitted(self):
        # interval is now optional (first-cycle seed). Must not raise.
        ch6 = _build_ch6_auto_checkin()
        assert "AUTO CHECK-IN PROTOCOL" in ch6


class TestProtocolCh6Integration:
    """CH6 integration with _build_orchestrator_protocol (preview path gate unchanged)."""

    def test_protocol_includes_ch6_when_enabled_multi_terminal(self):
        protocol = _build_orchestrator_protocol(
            cli_mode=False,
            project_id="test-proj",
            orchestrator_id="test-orch",
            tenant_key="test-tenant",
            auto_checkin_enabled=True,
            auto_checkin_interval=10,
        )
        assert "ch6_auto_checkin" in protocol
        assert "AUTO CHECK-IN" in protocol["ch6_auto_checkin"]
        assert "get_workflow_status" in protocol["ch6_auto_checkin"]

    def test_protocol_excludes_ch6_when_disabled(self):
        # CE-0033 Task 7: empty chapters are omitted (not emitted as "").
        protocol = _build_orchestrator_protocol(
            cli_mode=False,
            project_id="test-proj",
            orchestrator_id="test-orch",
            tenant_key="test-tenant",
            auto_checkin_enabled=False,
            auto_checkin_interval=10,
        )
        assert "ch6_auto_checkin" not in protocol

    def test_protocol_excludes_ch6_in_cli_mode_even_when_enabled(self):
        # CE-0033 Task 7: empty chapters are omitted (not emitted as "").
        protocol = _build_orchestrator_protocol(
            cli_mode=True,
            project_id="test-proj",
            orchestrator_id="test-orch",
            tenant_key="test-tenant",
            auto_checkin_enabled=True,
            auto_checkin_interval=10,
        )
        assert "ch6_auto_checkin" not in protocol

    def test_protocol_ch6_live_read_regardless_of_seed_interval(self):
        """The preview-path CH6 is the live-read loop; it must not bake the seed."""
        protocol = _build_orchestrator_protocol(
            cli_mode=False,
            project_id="test-proj",
            orchestrator_id="test-orch",
            tenant_key="test-tenant",
            auto_checkin_enabled=True,
            auto_checkin_interval=30,
        )
        ch6 = protocol["ch6_auto_checkin"]
        assert "get_workflow_status" in ch6
        assert "sleep 1800" not in ch6
        assert "Start-Sleep -Seconds 1800" not in ch6

    def test_protocol_defaults_ch6_disabled(self):
        """When auto_checkin params omitted, CH6 is omitted (CE-0033 Task 7)."""
        protocol = _build_orchestrator_protocol(
            cli_mode=False,
            project_id="test-proj",
            orchestrator_id="test-orch",
            tenant_key="test-tenant",
        )
        assert "ch6_auto_checkin" not in protocol
