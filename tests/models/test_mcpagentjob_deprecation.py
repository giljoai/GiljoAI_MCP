"""
Tests for MCPAgentJob deprecation (Handover 0358d).

RED Phase (TDD): These tests are written FIRST and will FAIL until deprecation warnings are implemented.

MCPAgentJob is being deprecated in favor of AgentJob + AgentExecution:
- Instantiation should emit DeprecationWarning
- Import should emit DeprecationWarning
- Warnings should mention AgentJob, AgentExecution, and v4.0 removal
"""

import pytest
import warnings
from sqlalchemy.ext.asyncio import AsyncSession


class TestMCPAgentJobDeprecation:
    """Test that MCPAgentJob emits deprecation warnings."""

    def test_mcpagentjob_instantiation_raises_deprecation_warning(self):
        """MCPAgentJob instantiation should emit DeprecationWarning."""
        with warnings.catch_warnings(record=True) as w:
            warnings.simplefilter("always")

            # Import and instantiate MCPAgentJob
            from src.giljo_mcp.models.agents import MCPAgentJob
            job = MCPAgentJob(
                job_id="test-job-001",
                tenant_key="tenant-abc",
                agent_type="orchestrator",
                mission="Test mission"
            )

            # Assert deprecation warning was raised
            assert len(w) >= 1, "Expected at least one warning"

            # Find the DeprecationWarning in the warnings list
            deprecation_warnings = [warning for warning in w if issubclass(warning.category, DeprecationWarning)]
            assert len(deprecation_warnings) >= 1, "Expected at least one DeprecationWarning"

            # Check warning message content
            warning_msg = str(deprecation_warnings[0].message)
            assert "MCPAgentJob" in warning_msg, "Warning should mention MCPAgentJob"
            assert "AgentJob" in warning_msg, "Warning should mention AgentJob"
            assert "AgentExecution" in warning_msg, "Warning should mention AgentExecution"
            assert "v4.0" in warning_msg or "4.0" in warning_msg, "Warning should mention v4.0 removal"

    def test_mcpagentjob_import_raises_deprecation_warning(self):
        """Importing MCPAgentJob from models package should emit DeprecationWarning."""
        with warnings.catch_warnings(record=True) as w:
            warnings.simplefilter("always")

            # Test import-time warning via models.__init__.__getattr__
            # This simulates: from src.giljo_mcp.models import MCPAgentJob
            import src.giljo_mcp.models as models

            # Trigger __getattr__ by accessing MCPAgentJob
            _ = models.MCPAgentJob

            # Assert deprecation warning was raised
            deprecation_warnings = [warning for warning in w if issubclass(warning.category, DeprecationWarning)]
            assert len(deprecation_warnings) >= 1, "Expected DeprecationWarning on import"

            # Check warning message content
            warning_msg = str(deprecation_warnings[0].message)
            assert "MCPAgentJob" in warning_msg, "Warning should mention MCPAgentJob"
            assert "AgentJob" in warning_msg or "AgentExecution" in warning_msg, "Warning should mention replacement models"

    def test_deprecation_warning_message_format(self):
        """Deprecation warning should have clear, actionable message."""
        with warnings.catch_warnings(record=True) as w:
            warnings.simplefilter("always")

            from src.giljo_mcp.models.agents import MCPAgentJob
            job = MCPAgentJob(
                job_id="test-job-002",
                tenant_key="tenant-xyz",
                agent_type="implementor",
                mission="Test mission"
            )

            # Find the DeprecationWarning
            deprecation_warnings = [warning for warning in w if issubclass(warning.category, DeprecationWarning)]
            assert len(deprecation_warnings) >= 1

            warning_msg = str(deprecation_warnings[0].message)

            # Should be clear and actionable
            assert "deprecated" in warning_msg.lower(), "Warning should say 'deprecated'"
            assert "will be removed" in warning_msg.lower() or "removed in" in warning_msg.lower(), \
                "Warning should mention removal timeline"

    def test_mcpagentjob_still_functional_despite_deprecation(self):
        """MCPAgentJob should still work (just with warnings) until v4.0."""
        with warnings.catch_warnings(record=True) as w:
            warnings.simplefilter("always")

            from src.giljo_mcp.models.agents import MCPAgentJob
            job = MCPAgentJob(
                job_id="test-job-003",
                tenant_key="tenant-test",
                agent_type="tester",
                mission="Test mission for backward compatibility"
            )

            # Should still create successfully
            assert job.job_id == "test-job-003"
            assert job.agent_type == "tester"
            assert job.mission == "Test mission for backward compatibility"

            # But should have warned
            deprecation_warnings = [warning for warning in w if issubclass(warning.category, DeprecationWarning)]
            assert len(deprecation_warnings) >= 1, "Should warn even though still functional"


class TestDeprecationWarningContent:
    """Test specific content of deprecation warning messages."""

    def test_warning_mentions_migration_path(self):
        """Warning should explain how to migrate to new models."""
        with warnings.catch_warnings(record=True) as w:
            warnings.simplefilter("always")

            from src.giljo_mcp.models.agents import MCPAgentJob
            job = MCPAgentJob(
                job_id="test-migration",
                tenant_key="tenant-migrate",
                agent_type="orchestrator",
                mission="Migration test"
            )

            deprecation_warnings = [warning for warning in w if issubclass(warning.category, DeprecationWarning)]
            assert len(deprecation_warnings) >= 1

            warning_msg = str(deprecation_warnings[0].message).lower()

            # Should mention both new models
            assert "agentjob" in warning_msg, "Should mention AgentJob"
            assert "agentexecution" in warning_msg, "Should mention AgentExecution"

    def test_warning_mentions_handover_reference(self):
        """Warning should reference handover documentation."""
        with warnings.catch_warnings(record=True) as w:
            warnings.simplefilter("always")

            from src.giljo_mcp.models.agents import MCPAgentJob
            job = MCPAgentJob(
                job_id="test-handover-ref",
                tenant_key="tenant-ref",
                agent_type="database-expert",
                mission="Handover reference test"
            )

            deprecation_warnings = [warning for warning in w if issubclass(warning.category, DeprecationWarning)]
            assert len(deprecation_warnings) >= 1

            warning_msg = str(deprecation_warnings[0].message).lower()

            # Should reference handover or documentation
            assert "0358" in warning_msg or "handover" in warning_msg or "migration" in warning_msg, \
                "Should reference handover 0358 or migration guide"
