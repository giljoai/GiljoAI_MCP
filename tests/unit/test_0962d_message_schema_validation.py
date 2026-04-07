"""
Unit tests for Handover 0962d: MessageSend and MessageSendRequest enum validation.

Tests that Literal type constraints reject invalid message_type and priority values.
"""

import pytest
from pydantic import ValidationError

from api.endpoints.messages import BroadcastMessage, MessageSend, MessageSendRequest


class TestMessageSendEnums:
    """Enum validation for MessageSend schema."""

    def test_invalid_message_type_rejected(self):
        """MessageSend must reject unknown message_type values (0962d)."""
        with pytest.raises(ValidationError) as exc_info:
            MessageSend(
                to_agents=["agent1"],
                content="hello",
                project_id="proj-1",
                message_type="multicast",
            )

        errors = exc_info.value.errors()
        assert any(error["loc"] == ("message_type",) for error in errors)

    def test_invalid_priority_rejected(self):
        """MessageSend must reject unknown priority values (0962d)."""
        with pytest.raises(ValidationError) as exc_info:
            MessageSend(
                to_agents=["agent1"],
                content="hello",
                project_id="proj-1",
                priority="urgent",
            )

        errors = exc_info.value.errors()
        assert any(error["loc"] == ("priority",) for error in errors)

    def test_valid_message_types(self):
        """MessageSend accepts all valid message_type values."""
        for msg_type in ["direct", "broadcast"]:
            msg = MessageSend(
                to_agents=["agent1"],
                content="hello",
                project_id="proj-1",
                message_type=msg_type,
            )
            assert msg.message_type == msg_type

    def test_valid_priority_values(self):
        """MessageSend accepts all valid priority values."""
        for priority in ["low", "normal", "high"]:
            msg = MessageSend(
                to_agents=["agent1"],
                content="hello",
                project_id="proj-1",
                priority=priority,
            )
            assert msg.priority == priority

    def test_defaults_are_valid(self):
        """MessageSend default values satisfy their own Literal constraints."""
        msg = MessageSend(to_agents=["agent1"], content="hello", project_id="proj-1")
        assert msg.message_type == "direct"
        assert msg.priority == "normal"


class TestMessageSendRequestEnums:
    """Enum validation for MessageSendRequest schema."""

    def test_invalid_message_type_rejected(self):
        """MessageSendRequest must reject unknown message_type values (0962d)."""
        with pytest.raises(ValidationError) as exc_info:
            MessageSendRequest(
                project_id="proj-1",
                to_agents=["agent1"],
                content="hello",
                message_type="unknown",
            )

        errors = exc_info.value.errors()
        assert any(error["loc"] == ("message_type",) for error in errors)

    def test_invalid_priority_rejected(self):
        """MessageSendRequest must reject unknown priority values (0962d)."""
        with pytest.raises(ValidationError) as exc_info:
            MessageSendRequest(
                project_id="proj-1",
                to_agents=["agent1"],
                content="hello",
                priority="critical",
            )

        errors = exc_info.value.errors()
        assert any(error["loc"] == ("priority",) for error in errors)


class TestBroadcastMessageEnums:
    """Enum validation for BroadcastMessage schema."""

    def test_invalid_priority_rejected(self):
        """BroadcastMessage must reject unknown priority values (0962d)."""
        with pytest.raises(ValidationError) as exc_info:
            BroadcastMessage(project_id="proj-1", content="hello", priority="urgent")

        errors = exc_info.value.errors()
        assert any(error["loc"] == ("priority",) for error in errors)

    def test_valid_priority_values(self):
        """BroadcastMessage accepts all valid priority values."""
        for priority in ["low", "normal", "high"]:
            msg = BroadcastMessage(project_id="proj-1", content="hello", priority=priority)
            assert msg.priority == priority
