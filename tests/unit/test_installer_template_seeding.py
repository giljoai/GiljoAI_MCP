"""
Test suite for installer template seeding functionality
Phase 3: Orchestrator Upgrade - Installer Integration
"""

from unittest.mock import MagicMock, Mock, patch

import pytest

from installer.core.config import seed_default_orchestrator_template


class TestOrchestratorTemplateSeeding:
    """Test orchestrator template seeding in installer"""

    def test_seed_function_exists(self):
        """Test that seed function is importable"""
        assert callable(seed_default_orchestrator_template), "Seed function should be callable"

    @patch("src.giljo_mcp.template_manager.UnifiedTemplateManager")
    def test_seed_creates_template(self, mock_template_manager):
        """Test that seed function creates template in database"""
        # Setup mocks
        mock_db_manager = MagicMock()
        mock_session = MagicMock()
        mock_db_manager.get_session.return_value.__enter__.return_value = mock_session

        # Mock existing template query (none exists)
        mock_session.query.return_value.filter.return_value.first.return_value = None

        # Mock template manager
        mock_mgr_instance = Mock()
        mock_mgr_instance._legacy_templates = {"orchestrator": "Test orchestrator template content"}
        mock_template_manager.return_value = mock_mgr_instance

        # Call seed function
        result = seed_default_orchestrator_template(mock_db_manager, "test_tenant")

        # Verify success
        assert result["success"] is True, "Seeding should succeed"
        assert "message" in result, "Result should contain message"

        # Verify template was added
        assert mock_session.add.called, "Should add template to session"
        assert mock_session.commit.called, "Should commit changes"

    @patch("src.giljo_mcp.template_manager.UnifiedTemplateManager")
    def test_seed_skips_if_exists(self, mock_template_manager):
        """Test that seed function skips if template already exists"""
        # Setup mocks
        mock_db_manager = MagicMock()
        mock_session = MagicMock()
        mock_db_manager.get_session.return_value.__enter__.return_value = mock_session

        # Mock existing template query (template exists)
        existing_template = Mock()
        mock_session.query.return_value.filter.return_value.first.return_value = existing_template

        # Mock template manager
        mock_mgr_instance = Mock()
        mock_mgr_instance._legacy_templates = {"orchestrator": "Test orchestrator template content"}
        mock_template_manager.return_value = mock_mgr_instance

        # Call seed function
        result = seed_default_orchestrator_template(mock_db_manager, "test_tenant")

        # Verify success but no changes
        assert result["success"] is True, "Should succeed when template exists"
        assert "already exists" in result.get("message", "").lower(), "Should indicate template exists"

        # Verify no add/commit
        assert not mock_session.add.called, "Should not add if template exists"
        assert not mock_session.commit.called, "Should not commit if template exists"

    @patch("src.giljo_mcp.template_manager.UnifiedTemplateManager")
    def test_seed_handles_errors(self, mock_template_manager):
        """Test that seed function handles errors gracefully"""
        # Setup mocks to raise exception
        mock_db_manager = Mock()
        mock_db_manager.get_session.side_effect = Exception("Database connection failed")

        # Call seed function
        result = seed_default_orchestrator_template(mock_db_manager, "test_tenant")

        # Verify error handling
        assert result["success"] is False, "Should indicate failure"
        assert "errors" in result, "Should contain error list"
        assert len(result["errors"]) > 0, "Should have at least one error"

    @patch("src.giljo_mcp.template_manager.UnifiedTemplateManager")
    def test_seed_template_metadata(self, mock_template_manager):
        """Test that seeded template has correct metadata"""
        from src.giljo_mcp.models import AgentTemplate

        # Setup mocks
        mock_db_manager = MagicMock()
        mock_session = MagicMock()
        mock_db_manager.get_session.return_value.__enter__.return_value = mock_session

        # Mock existing template query (none exists)
        mock_session.query.return_value.filter.return_value.first.return_value = None

        # Mock template manager with realistic content
        mock_mgr_instance = Mock()
        mock_mgr_instance._legacy_templates = {
            "orchestrator": "Orchestrator template with 30-80-10 principle and 3-tool rule"
        }
        mock_template_manager.return_value = mock_mgr_instance

        # Call seed function
        result = seed_default_orchestrator_template(mock_db_manager, "test_tenant")

        # Verify template was created with correct metadata
        assert mock_session.add.called, "Should add template"

        # Get the template that was added
        call_args = mock_session.add.call_args
        added_template = call_args[0][0]

        # Verify it's an AgentTemplate
        assert isinstance(added_template, AgentTemplate), "Should add AgentTemplate instance"

        # Verify key fields
        assert added_template.tenant_key == "test_tenant", "Should have correct tenant key"
        assert added_template.role == "orchestrator", "Should have orchestrator role"
        assert added_template.is_default is True, "Should be marked as default"
        assert added_template.is_active is True, "Should be marked as active"
        assert added_template.version == "2.0.0", "Should have correct version"

        # Verify behavioral rules
        assert len(added_template.behavioral_rules) > 0, "Should have behavioral rules"
        assert any("3-tool" in rule.lower() for rule in added_template.behavioral_rules), "Should mention 3-tool rule"
        assert any("delegation" in rule.lower() for rule in added_template.behavioral_rules), (
            "Should mention delegation"
        )

        # Verify success criteria
        assert len(added_template.success_criteria) > 0, "Should have success criteria"
        assert any("vision" in crit.lower() for crit in added_template.success_criteria), "Should mention vision"
        assert any("documentation" in crit.lower() for crit in added_template.success_criteria), (
            "Should mention documentation"
        )

        # Verify template content
        assert (
            "30-80-10" in added_template.system_instructions
            or "principle" in added_template.system_instructions.lower()
        ), "Should contain principle reference"


if __name__ == "__main__":
    pytest.main([__file__, "-v"])
