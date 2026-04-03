"""
Tests for orchestrator auto check-in protocol (Handover 0904).

Verifies:
1. CH6 is included when auto_checkin_enabled=True and multi-terminal mode
2. CH6 is excluded when auto_checkin_enabled=False
3. CH6 is excluded in CLI subagent modes even when enabled
4. Interval value is correctly substituted in protocol text
"""

import pytest

from src.giljo_mcp.services.protocol_builder import (
    _build_ch6_auto_checkin,
    _build_orchestrator_protocol,
)


class TestCh6AutoCheckin:
    """CH6 auto check-in protocol generation."""

    def test_ch6_contains_interval_value(self):
        ch6 = _build_ch6_auto_checkin(interval=30)
        assert "interval: 30s" in ch6
        assert "Wait 30 seconds" in ch6

    def test_ch6_contains_interval_60(self):
        ch6 = _build_ch6_auto_checkin(interval=60)
        assert "interval: 60s" in ch6
        assert "Wait 60 seconds" in ch6

    def test_ch6_contains_interval_90(self):
        ch6 = _build_ch6_auto_checkin(interval=90)
        assert "interval: 90s" in ch6
        assert "Wait 90 seconds" in ch6

    def test_ch6_contains_key_instructions(self):
        ch6 = _build_ch6_auto_checkin(interval=60)
        assert "AUTO CHECK-IN PROTOCOL" in ch6
        assert "receive_messages()" in ch6
        assert "set_agent_status" in ch6
        assert "sleeping" in ch6

    def test_ch6_warns_about_token_consumption(self):
        ch6 = _build_ch6_auto_checkin(interval=60)
        assert "token" in ch6.lower()


class TestProtocolCh6Integration:
    """CH6 integration with _build_orchestrator_protocol."""

    def test_protocol_includes_ch6_when_enabled_multi_terminal(self):
        protocol = _build_orchestrator_protocol(
            cli_mode=False,
            project_id="test-proj",
            orchestrator_id="test-orch",
            tenant_key="test-tenant",
            auto_checkin_enabled=True,
            auto_checkin_interval=60,
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
            auto_checkin_interval=60,
        )
        assert protocol["ch6_auto_checkin"] == ""

    def test_protocol_excludes_ch6_in_cli_mode_even_when_enabled(self):
        protocol = _build_orchestrator_protocol(
            cli_mode=True,
            project_id="test-proj",
            orchestrator_id="test-orch",
            tenant_key="test-tenant",
            auto_checkin_enabled=True,
            auto_checkin_interval=60,
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
        assert "interval: 30s" in protocol["ch6_auto_checkin"]

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
