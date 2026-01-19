"""
Simple tests for ProjectOrchestrator that don't require database.

Handover 0422: Cleaned up tests for removed dead token budget code.
Removed tests for: get_context_status(), _get_handoff_reason()
"""

import pytest

from src.giljo_mcp.enums import ProjectStatus, ContextStatus
from src.giljo_mcp.orchestrator import AgentRole, ProjectOrchestrator


# Handover 0422: Entire TestContextStatusIndicators class removed - tests removed method:
# - get_context_status() - method removed


class TestAgentMissionTemplates:
    """Test agent mission templates."""

    def test_orchestrator_mission(self):
        """Test orchestrator role has correct mission template."""
        orch = ProjectOrchestrator()
        mission = orch.AGENT_MISSIONS[AgentRole.ORCHESTRATOR]

        assert "orchestrator responsible for" in mission
        assert "Breaking down the project mission" in mission
        assert "Coordinating agent activities" in mission

    def test_analyzer_mission(self):
        """Test analyzer role has correct mission template."""
        orch = ProjectOrchestrator()
        mission = orch.AGENT_MISSIONS[AgentRole.ANALYZER]

        assert "analyzer responsible for" in mission
        assert "Understanding requirements" in mission
        assert "architectural designs" in mission

    def test_implementer_mission(self):
        """Test implementer role has correct mission template."""
        orch = ProjectOrchestrator()
        mission = orch.AGENT_MISSIONS[AgentRole.IMPLEMENTER]

        assert "implementer responsible for" in mission
        assert "Writing clean, maintainable code" in mission
        assert "Following architectural specifications" in mission

    def test_tester_mission(self):
        """Test tester role has correct mission template."""
        orch = ProjectOrchestrator()
        mission = orch.AGENT_MISSIONS[AgentRole.TESTER]

        assert "tester responsible for" in mission
        assert "comprehensive test suites" in mission
        assert "code coverage" in mission

    def test_reviewer_mission(self):
        """Test reviewer role has correct mission template."""
        orch = ProjectOrchestrator()
        mission = orch.AGENT_MISSIONS[AgentRole.REVIEWER]

        assert "reviewer responsible for" in mission
        assert "code for quality" in mission
        assert "security best practices" in mission


class TestProjectStatuss:
    """Test project state transitions logic."""

    def test_state_enum_values(self):
        """Test state enum has correct values."""
        # Verify all expected statuses exist (Handover 0071)
        assert ProjectStatus.ACTIVE.value == "active"
        assert ProjectStatus.INACTIVE.value == "inactive"
        assert ProjectStatus.COMPLETED.value == "completed"
        assert ProjectStatus.CANCELLED.value == "cancelled"
        assert ProjectStatus.DELETED.value == "deleted"

        # Verify old statuses don't exist
        assert not hasattr(ProjectStatus, "DRAFT")
        assert not hasattr(ProjectStatus, "PAUSED")
        assert not hasattr(ProjectStatus, "ARCHIVED")
        assert not hasattr(ProjectStatus, "PLANNING")


# Handover 0422: Entire TestHandoffLogic class removed - tests removed method:
# - _get_handoff_reason() - method removed


if __name__ == "__main__":
    pytest.main([__file__, "-v"])
