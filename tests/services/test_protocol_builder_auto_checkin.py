# Copyright (c) 2024-2026 GiljoAI LLC. All rights reserved.
# Licensed under the GiljoAI Community License v1.1.
# See LICENSE in the project root for terms.
# [CE] Community Edition — source-available, single-user use only.

"""
Tests for orchestrator auto check-in protocol (Handover 0904, updated 0960).

Verifies:
1. CH6 is included when auto_checkin_enabled=True and multi-terminal mode
2. CH6 is excluded when auto_checkin_enabled=False
3. CH6 is excluded in CLI subagent modes even when enabled
4. Interval value (minutes) is correctly substituted in protocol text
"""

from src.giljo_mcp.services.protocol_builder import (
    _build_ch6_auto_checkin,
    _build_orchestrator_protocol,
)


class TestCh6AutoCheckin:
    """CH6 auto check-in protocol generation."""

    def test_ch6_contains_interval_and_seconds(self):
        ch6 = _build_ch6_auto_checkin(interval=5)
        assert "sleeping for 5 minutes" in ch6
        assert "sleep 300" in ch6
        assert "Start-Sleep -Seconds 300" in ch6

    def test_ch6_contains_interval_10(self):
        ch6 = _build_ch6_auto_checkin(interval=10)
        assert "sleeping for 10 minutes" in ch6
        assert "sleep 600" in ch6

    def test_ch6_contains_interval_60(self):
        ch6 = _build_ch6_auto_checkin(interval=60)
        assert "sleeping for 60 minutes" in ch6
        assert "sleep 3600" in ch6

    def test_ch6_contains_key_instructions(self):
        ch6 = _build_ch6_auto_checkin(interval=10)
        assert "AUTO CHECK-IN PROTOCOL" in ch6
        assert "receive_messages()" in ch6
        assert "get_workflow_status()" in ch6
        assert "report_progress()" in ch6

    def test_ch6_warns_about_token_consumption(self):
        ch6 = _build_ch6_auto_checkin(interval=10)
        assert "token consumption" in ch6.lower()

    def test_ch6_uses_imperative_mandatory_language(self):
        ch6 = _build_ch6_auto_checkin(interval=10)
        assert "MANDATORY EXECUTION" in ch6
        assert "Do NOT ask the user for confirmation" in ch6
        assert 'set_agent_status(status="sleeping"' in ch6
        assert "NEVER ask" in ch6


class TestProtocolCh6Integration:
    """CH6 integration with _build_orchestrator_protocol."""

    def test_protocol_includes_ch6_when_enabled_multi_terminal(self):
        protocol = _build_orchestrator_protocol(
            cli_mode=False,
            project_id="test-proj",
            orchestrator_id="test-orch",
            tenant_key="test-tenant",
            auto_checkin_enabled=True,
            auto_checkin_interval=10,
        )
        assert protocol["ch6_auto_checkin"] != ""
        assert "AUTO CHECK-IN" in protocol["ch6_auto_checkin"]

    def test_protocol_excludes_ch6_when_disabled(self):
        protocol = _build_orchestrator_protocol(
            cli_mode=False,
            project_id="test-proj",
            orchestrator_id="test-orch",
            tenant_key="test-tenant",
            auto_checkin_enabled=False,
            auto_checkin_interval=10,
        )
        assert protocol["ch6_auto_checkin"] == ""

    def test_protocol_excludes_ch6_in_cli_mode_even_when_enabled(self):
        protocol = _build_orchestrator_protocol(
            cli_mode=True,
            project_id="test-proj",
            orchestrator_id="test-orch",
            tenant_key="test-tenant",
            auto_checkin_enabled=True,
            auto_checkin_interval=10,
        )
        assert protocol["ch6_auto_checkin"] == ""

    def test_protocol_ch6_has_correct_interval(self):
        protocol = _build_orchestrator_protocol(
            cli_mode=False,
            project_id="test-proj",
            orchestrator_id="test-orch",
            tenant_key="test-tenant",
            auto_checkin_enabled=True,
            auto_checkin_interval=30,
        )
        assert "sleeping for 30 minutes" in protocol["ch6_auto_checkin"]

    def test_protocol_defaults_ch6_disabled(self):
        """When auto_checkin params omitted, CH6 is empty (defaults to disabled)."""
        protocol = _build_orchestrator_protocol(
            cli_mode=False,
            project_id="test-proj",
            orchestrator_id="test-orch",
            tenant_key="test-tenant",
        )
        assert protocol["ch6_auto_checkin"] == ""

    def test_protocol_always_has_ch6_key(self):
        """CH6 key always exists in protocol dict, even when empty."""
        protocol = _build_orchestrator_protocol(
            cli_mode=False,
            project_id="test-proj",
            orchestrator_id="test-orch",
            tenant_key="test-tenant",
            auto_checkin_enabled=False,
        )
        assert "ch6_auto_checkin" in protocol
