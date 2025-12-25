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

    def test_protocol_distinct_identifiers(self):
        """Verify protocol shows different values for job_id and agent_id (Bug 2)."""
        # When agent_id is provided, it should differ from job_id
        protocol = _generate_agent_protocol(
            job_id="job-123",
            tenant_key="tenant-abc",
            agent_name="test-agent",
            agent_id="executor-456"
        )

        # Extract the "Your Identifiers" section
        assert "**Your Identifiers:**" in protocol
        identifiers_start = protocol.index("**Your Identifiers:**")
        identifiers_end = protocol.index("**When to Check Messages:**")
        identifiers_section = protocol[identifiers_start:identifiers_end]

        # Verify job_id and agent_id show different values
        assert "job-123" in identifiers_section, "job_id should be job-123"
        assert "executor-456" in identifiers_section, "agent_id should be executor-456"
        # They should NOT both show the same value
        assert identifiers_section.count("job-123") >= 1
        assert identifiers_section.count("executor-456") >= 1

    def test_protocol_receive_messages_includes_tenant_key(self):
        """Verify all receive_messages examples include tenant_key parameter (Bug 3)."""
        protocol = _generate_agent_protocol(
            job_id="job-abc",
            tenant_key="tenant-xyz",
            agent_name="test-agent",
            agent_id="executor-def"
        )

        # Find all receive_messages calls in the protocol
        # There should be examples in Phase 1, 2, 3, and 4
        import re
        receive_messages_calls = re.findall(
            r'receive_messages\([^)]+\)',
            protocol
        )

        # Verify we found multiple examples
        assert len(receive_messages_calls) >= 4, \
            f"Expected at least 4 receive_messages examples, found {len(receive_messages_calls)}"

        # Verify NONE of them are missing tenant_key
        # The old broken format would be: receive_messages(agent_id="...")
        # The correct format is: receive_messages(agent_id="...", tenant_key="...")
        for call in receive_messages_calls:
            # Skip short-form examples that just show the tool name
            if 'agent_id=' not in call:
                continue

            # Full-form examples MUST include tenant_key
            assert 'tenant_key=' in call, \
                f"receive_messages call missing tenant_key: {call}"

    def test_protocol_includes_todowrite_sync_instructions(self):
        """Verify protocol includes instructions to sync TodoWrite with report_progress (Bug 4)."""
        protocol = _generate_agent_protocol(
            job_id="job-123",
            tenant_key="tenant-abc",
            agent_name="test-agent"
        )

        # Verify protocol mentions syncing TodoWrite with progress reporting
        assert "TodoWrite" in protocol, "Protocol should mention TodoWrite tool"
        assert "report_progress" in protocol, "Protocol should mention report_progress tool"

        # Look for explicit sync instructions (should be near each other)
        # Check for keywords that indicate the sync relationship
        protocol_lower = protocol.lower()
        assert "sync" in protocol_lower or "immediately" in protocol_lower or "every time" in protocol_lower, \
            "Protocol should include instructions to sync TodoWrite status with progress reporting"

        # Verify the sync section mentions both tools together
        # Find sections that mention both TodoWrite and report_progress
        lines = protocol.split('\n')
        todowrite_section_found = False
        for i, line in enumerate(lines):
            if 'todowrite' in line.lower() and 'sync' in line.lower():
                # Look in surrounding lines for report_progress mention
                context = '\n'.join(lines[max(0, i-5):min(len(lines), i+15)])
                if 'report_progress' in context.lower():
                    todowrite_section_found = True
                    break

        assert todowrite_section_found, \
            "Protocol should have a section explaining TodoWrite sync with report_progress"
