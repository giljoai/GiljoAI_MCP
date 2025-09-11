"""
Simple tests for ProjectOrchestrator that don't require database.
"""

import pytest
from src.giljo_mcp.orchestrator import (
    ProjectOrchestrator,
    ProjectState,
    AgentRole,
    ContextStatus
)


class TestContextStatusIndicators:
    """Test context status color indicators without database."""
    
    def test_context_status_green(self):
        """Test GREEN status (< 50%)."""
        orch = ProjectOrchestrator()
        
        # Test various percentages under 50%
        assert orch.get_context_status(0, 10000) == ContextStatus.GREEN
        assert orch.get_context_status(2500, 10000) == ContextStatus.GREEN  # 25%
        assert orch.get_context_status(4999, 10000) == ContextStatus.GREEN  # 49.99%
        
    def test_context_status_yellow(self):
        """Test YELLOW status (50-80%)."""
        orch = ProjectOrchestrator()
        
        # Test various percentages between 50% and 80%
        assert orch.get_context_status(5000, 10000) == ContextStatus.YELLOW  # 50%
        assert orch.get_context_status(6500, 10000) == ContextStatus.YELLOW  # 65%
        assert orch.get_context_status(7999, 10000) == ContextStatus.YELLOW  # 79.99%
        
    def test_context_status_red(self):
        """Test RED status (>= 80%)."""
        orch = ProjectOrchestrator()
        
        # Test various percentages at or above 80%
        assert orch.get_context_status(8000, 10000) == ContextStatus.RED  # 80%
        assert orch.get_context_status(9000, 10000) == ContextStatus.RED  # 90%
        assert orch.get_context_status(10000, 10000) == ContextStatus.RED  # 100%
        

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
        

class TestProjectStates:
    """Test project state transitions logic."""
    
    def test_state_enum_values(self):
        """Test state enum has correct values."""
        assert ProjectState.DRAFT.value == "draft"
        assert ProjectState.ACTIVE.value == "active"
        assert ProjectState.PAUSED.value == "paused"
        assert ProjectState.COMPLETED.value == "completed"
        assert ProjectState.ARCHIVED.value == "archived"
        

class TestHandoffLogic:
    """Test handoff detection logic."""
    
    def test_handoff_reason_generation(self):
        """Test generation of handoff reasons."""
        from unittest.mock import MagicMock
        
        orch = ProjectOrchestrator()
        
        # Mock agent with high context usage
        agent = MagicMock()
        agent.context_used = 8500
        agent.context_budget = 10000
        agent.status = "active"
        
        reason = orch._get_handoff_reason(agent)
        assert "Context usage at 85%" in reason
        
        # Mock agent with error status
        agent.context_used = 5000
        agent.status = "error"
        
        reason = orch._get_handoff_reason(agent)
        assert "encountered error" in reason
        
        # Mock agent with normal usage
        agent.context_used = 5000
        agent.status = "active"
        
        reason = orch._get_handoff_reason(agent)
        assert "Manual handoff" in reason


if __name__ == "__main__":
    pytest.main([__file__, "-v"])