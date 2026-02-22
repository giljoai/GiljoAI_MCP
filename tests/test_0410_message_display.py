"""
Tests for Handover 0410: Message Display UX Fix.

Validates that:
1. Response builder includes `to` and `to_agent_id` fields for recipient resolution
2. Fan-out broadcasts preserve message_type="broadcast"
3. Frontend formatRecipient() uses resolved `to` field
4. Sender resolution still works
5. Empty to_agents handled gracefully
"""

import inspect
import pytest


class TestResponseBuilderRecipientFields:
    """Verify get_job_messages response builder includes recipient fields."""

    def test_response_builder_includes_to_field(self):
        """Response builder dict must include 'to' key for resolved recipient name."""
        from api.endpoints.agent_jobs.messages import get_job_messages
        source = inspect.getsource(get_job_messages)
        assert '"to":' in source or "'to':" in source, (
            "Response builder must include 'to' field for resolved recipient name"
        )

    def test_response_builder_includes_to_agent_id_field(self):
        """Response builder dict must include 'to_agent_id' key."""
        from api.endpoints.agent_jobs.messages import get_job_messages
        source = inspect.getsource(get_job_messages)
        assert '"to_agent_id":' in source or "'to_agent_id':" in source, (
            "Response builder must include 'to_agent_id' field"
        )

    def test_broadcast_resolves_to_all_agents(self):
        """Broadcast messages must resolve to 'All Agents' display name."""
        from api.endpoints.agent_jobs.messages import get_job_messages
        source = inspect.getsource(get_job_messages)
        assert "All Agents" in source, (
            "Broadcast messages must resolve 'to' as 'All Agents'"
        )

    def test_empty_to_agents_handled_gracefully(self):
        """Empty to_agents array must not cause errors - should resolve to Unknown."""
        from api.endpoints.agent_jobs.messages import get_job_messages
        source = inspect.getsource(get_job_messages)
        # Verify there's a check for empty/None to_agents
        assert "to_agents[0]" in source, (
            "Response builder must access to_agents[0] for single recipient"
        )
        # Verify there's a fallback for missing/empty to_agents
        assert "Unknown" in source, (
            "Response builder must handle missing recipient with 'Unknown' fallback"
        )


class TestBroadcastFanoutPreservation:
    """Verify fan-out preserves broadcast signal in message_type."""

    def test_fanout_overrides_message_type_for_broadcast(self):
        """When to_agents contains 'all', fan-out must set message_type='broadcast'."""
        from src.giljo_mcp.services.message_service import MessageService
        source = inspect.getsource(MessageService.send_message)
        # The fan-out should detect "all" in to_agents and override message_type
        assert "is_broadcast_fanout" in source or (
            '"broadcast"' in source and '"all"' in source and "message_type" in source
        ), (
            "Fan-out must override message_type to 'broadcast' when to_agents contains 'all'"
        )


class TestSenderResolution:
    """Verify sender resolution still works after changes."""

    def test_resolve_sender_display_name_exists(self):
        """_resolve_sender_display_name function must exist and handle known cases."""
        from api.endpoints.agent_jobs.messages import _resolve_sender_display_name
        # Test known cases
        assert _resolve_sender_display_name("user", {}) == "User"
        assert _resolve_sender_display_name("system", {}) == "System"
        assert _resolve_sender_display_name("", {}) == "Unknown"
        assert _resolve_sender_display_name(None, {}) == "Unknown"

    def test_resolve_sender_with_agent_lookup(self):
        """_resolve_sender_display_name must resolve agent_id via lookup."""
        from api.endpoints.agent_jobs.messages import _resolve_sender_display_name
        lookup = {"agent-uuid-123": "Orchestrator"}
        assert _resolve_sender_display_name("agent-uuid-123", lookup) == "Orchestrator"

    def test_resolve_sender_known_roles(self):
        """Known role names must be capitalized."""
        from api.endpoints.agent_jobs.messages import _resolve_sender_display_name
        assert _resolve_sender_display_name("orchestrator", {}) == "Orchestrator"
        assert _resolve_sender_display_name("implementer", {}) == "Implementer"


class TestFrontendFormatRecipient:
    """Verify frontend formatRecipient uses resolved 'to' field."""

    def test_format_recipient_uses_message_to(self):
        """formatRecipient must use message.to (resolved name from backend)."""
        import re
        with open("frontend/src/components/projects/MessageAuditModal.vue", "r") as f:
            source = f.read()
        # Extract formatRecipient function body
        match = re.search(r'function formatRecipient\(message\)\s*\{([^}]+)\}', source)
        assert match, "formatRecipient function must exist"
        body = match.group(1)
        assert "message.to" in body, (
            "formatRecipient must use message.to (resolved recipient name from backend)"
        )

    def test_dead_format_message_meta_removed(self):
        """formatMessageMeta dead code must be deleted."""
        with open("frontend/src/components/projects/MessageAuditModal.vue", "r") as f:
            source = f.read()
        assert "formatMessageMeta" not in source, (
            "Dead formatMessageMeta function must be removed"
        )

    def test_stale_developer_filter_removed(self):
        """Stale m.from === 'developer' filter must be removed."""
        with open("frontend/src/components/projects/MessageAuditModal.vue", "r") as f:
            source = f.read()
        assert "developer" not in source, (
            "Stale 'developer' filter must be removed from sentMessages computed"
        )


class TestMessageDetailView:
    """Verify MessageDetailView shows resolved To name + UUID."""

    def test_detail_view_shows_to_field(self):
        """MessageDetailView must show message.to (resolved name)."""
        with open("frontend/src/components/projects/MessageDetailView.vue", "r") as f:
            source = f.read()
        assert "message.to" in source, (
            "MessageDetailView must display message.to for resolved recipient name"
        )

    def test_detail_view_shows_to_agent_id(self):
        """MessageDetailView must show message.to_agent_id."""
        with open("frontend/src/components/projects/MessageDetailView.vue", "r") as f:
            source = f.read()
        assert "message.to_agent_id" in source, (
            "MessageDetailView must display message.to_agent_id for UUID"
        )
