"""
Unit tests for agent protocol format validation (Handover 0359).

Verifies that _generate_agent_protocol() produces protocol strings
that match the backend's expected progress format.
"""

import pytest

from src.giljo_mcp.services.orchestration_service import _generate_agent_protocol


class TestAgentProtocolFormat:
    """Test agent protocol string format matches backend expectations."""

    def test_protocol_includes_mode_todo(self):
        """Verify protocol instructs agents to include mode='todo' in progress."""
        # Generate protocol
        protocol = _generate_agent_protocol(
            job_id="test-job-123",
            tenant_key="tenant-abc",
            agent_name="test-agent"
        )

        # Assert protocol contains correct format (mode="todo")
        assert '"mode": "todo"' in protocol, \
            "Protocol must instruct agents to use mode='todo' for todo-based progress"
        assert '"completed_steps":' in protocol or 'completed_steps' in protocol, \
            "Protocol must use 'completed_steps' (not 'steps_completed')"
        assert '"total_steps":' in protocol or 'total_steps' in protocol, \
            "Protocol must use 'total_steps' (not 'steps_total')"

        # Assert protocol does NOT contain old wrong format
        assert '"steps_completed"' not in protocol, \
            "Protocol must NOT use old format 'steps_completed' (use 'completed_steps' instead)"
        assert '"steps_total"' not in protocol, \
            "Protocol must NOT use old format 'steps_total' (use 'total_steps' instead)"

    def test_protocol_includes_current_step(self):
        """Verify protocol includes current_step field for todo description."""
        protocol = _generate_agent_protocol(
            job_id="test-job-456",
            tenant_key="tenant-xyz",
            agent_name="another-agent"
        )

        # current_step is optional but recommended for better tracking
        assert '"current_step"' in protocol or 'current_step' in protocol, \
            "Protocol should include 'current_step' for task description"

    def test_protocol_backward_compatibility(self):
        """Verify protocol supports optional agent_id parameter."""
        # Test with agent_id provided
        protocol_with_id = _generate_agent_protocol(
            job_id="job-123",
            tenant_key="tenant-abc",
            agent_name="agent-1",
            agent_id="executor-456"
        )

        # Test without agent_id (backwards compat)
        protocol_without_id = _generate_agent_protocol(
            job_id="job-123",
            tenant_key="tenant-abc",
            agent_name="agent-1"
        )

        # Both should contain mode="todo" format
        assert '"mode": "todo"' in protocol_with_id
        assert '"mode": "todo"' in protocol_without_id

    def test_protocol_phase_3_order(self):
        """Verify Phase 3 contains correct progress reporting format."""
        protocol = _generate_agent_protocol(
            job_id="test-job-789",
            tenant_key="tenant-def",
            agent_name="test-agent"
        )

        # Find Phase 3 section
        assert "### Phase 3: PROGRESS REPORTING" in protocol

        # Extract Phase 3 content
        phase_3_start = protocol.index("### Phase 3: PROGRESS REPORTING")
        phase_4_start = protocol.index("### Phase 4: COMPLETION")
        phase_3_content = protocol[phase_3_start:phase_4_start]

        # Verify Phase 3 contains report_progress call with mode="todo"
        assert "report_progress" in phase_3_content
        assert '"mode": "todo"' in phase_3_content
        assert '"completed_steps"' in phase_3_content or 'completed_steps' in phase_3_content
        assert '"total_steps"' in phase_3_content or 'total_steps' in phase_3_content
