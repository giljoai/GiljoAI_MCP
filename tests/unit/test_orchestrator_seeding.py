"""
Test suite for orchestrator template seeding script.
Tests ensure the seeding script properly populates the database
with the enhanced orchestrator template.
"""

from unittest.mock import MagicMock, Mock

import pytest

from src.giljo_mcp.models import AgentTemplate


class TestOrchestratorSeeding:
    """Test orchestrator template database seeding."""

    @pytest.fixture
    def mock_db_manager(self):
        """Create mock database manager."""
        return MagicMock()

    @pytest.fixture
    def mock_session(self):
        """Create mock database session."""
        session = MagicMock()
        session.__enter__ = Mock(return_value=session)
        session.__exit__ = Mock(return_value=False)
        return session

    def test_seed_creates_orchestrator_template(self, mock_db_manager, mock_session):
        """Test that seeding creates orchestrator template in database."""
        # Mock session and query results
        mock_db_manager.get_session.return_value = mock_session
        mock_session.query.return_value.filter.return_value.first.return_value = None

        # Import after setting up mocks
        from scripts.seed_orchestrator_template import seed_orchestrator_template

        # Run seeding
        seed_orchestrator_template(mock_db_manager, "test-tenant")

        # Verify template was added to session
        mock_session.add.assert_called_once()
        added_template = mock_session.add.call_args[0][0]

        # Verify it's an AgentTemplate
        assert isinstance(added_template, AgentTemplate)

    def test_seed_sets_template_properties(self, mock_db_manager, mock_session):
        """Test that seeding sets correct template properties."""
        mock_db_manager.get_session.return_value = mock_session
        mock_session.query.return_value.filter.return_value.first.return_value = None

        from scripts.seed_orchestrator_template import seed_orchestrator_template

        seed_orchestrator_template(mock_db_manager, "test-tenant")

        added_template = mock_session.add.call_args[0][0]

        # Check basic properties
        assert added_template.tenant_key == "test-tenant"
        assert added_template.name == "orchestrator"
        assert added_template.category == "role"
        assert added_template.role == "orchestrator"
        assert added_template.is_default is True
        assert added_template.is_active is True

    def test_seed_includes_enhanced_content(self, mock_db_manager, mock_session):
        """Test that seeded template includes enhanced content."""
        mock_db_manager.get_session.return_value = mock_session
        mock_session.query.return_value.filter.return_value.first.return_value = None

        from scripts.seed_orchestrator_template import seed_orchestrator_template

        seed_orchestrator_template(mock_db_manager, "test-tenant")

        added_template = mock_session.add.call_args[0][0]

        # Template content should have key features
        content = added_template.template_content
        assert "30-80-10 PRINCIPLE" in content
        assert "3-TOOL RULE" in content
        assert "PROJECT CLOSURE" in content
        assert "Serena MCP First" in content

    def test_seed_includes_behavioral_rules(self, mock_db_manager, mock_session):
        """Test that seeded template includes behavioral rules."""
        mock_db_manager.get_session.return_value = mock_session
        mock_session.query.return_value.filter.return_value.first.return_value = None

        from scripts.seed_orchestrator_template import seed_orchestrator_template

        seed_orchestrator_template(mock_db_manager, "test-tenant")

        added_template = mock_session.add.call_args[0][0]

        # Check behavioral rules
        rules = added_template.behavioral_rules
        assert isinstance(rules, list)
        assert len(rules) > 0

        # Check for key rules
        rule_text = " ".join(rules).lower()
        assert "3-tool" in rule_text
        assert "specific mission" in rule_text or "discoveries" in rule_text
        assert "documentation" in rule_text and "artifact" in rule_text

    def test_seed_includes_success_criteria(self, mock_db_manager, mock_session):
        """Test that seeded template includes success criteria."""
        mock_db_manager.get_session.return_value = mock_session
        mock_session.query.return_value.filter.return_value.first.return_value = None

        from scripts.seed_orchestrator_template import seed_orchestrator_template

        seed_orchestrator_template(mock_db_manager, "test-tenant")

        added_template = mock_session.add.call_args[0][0]

        # Check success criteria
        criteria = added_template.success_criteria
        assert isinstance(criteria, list)
        assert len(criteria) > 0

        # Check for key criteria
        criteria_text = " ".join(criteria).lower()
        assert "vision" in criteria_text
        assert "config_data" in criteria_text or "config" in criteria_text
        assert "serena" in criteria_text
        assert "documentation" in criteria_text

    def test_seed_includes_required_variables(self, mock_db_manager, mock_session):
        """Test that seeded template includes required variables."""
        mock_db_manager.get_session.return_value = mock_session
        mock_session.query.return_value.filter.return_value.first.return_value = None

        from scripts.seed_orchestrator_template import seed_orchestrator_template

        seed_orchestrator_template(mock_db_manager, "test-tenant")

        added_template = mock_session.add.call_args[0][0]

        # Check variables
        variables = added_template.variables
        assert isinstance(variables, list)
        assert "project_name" in variables
        assert "project_mission" in variables
        assert "product_name" in variables

    def test_seed_sets_version(self, mock_db_manager, mock_session):
        """Test that seeded template has version 2.0.0."""
        mock_db_manager.get_session.return_value = mock_session
        mock_session.query.return_value.filter.return_value.first.return_value = None

        from scripts.seed_orchestrator_template import seed_orchestrator_template

        seed_orchestrator_template(mock_db_manager, "test-tenant")

        added_template = mock_session.add.call_args[0][0]

        # Check version
        assert added_template.version == "2.0.0"

    def test_seed_sets_description(self, mock_db_manager, mock_session):
        """Test that seeded template has descriptive text."""
        mock_db_manager.get_session.return_value = mock_session
        mock_session.query.return_value.filter.return_value.first.return_value = None

        from scripts.seed_orchestrator_template import seed_orchestrator_template

        seed_orchestrator_template(mock_db_manager, "test-tenant")

        added_template = mock_session.add.call_args[0][0]

        # Check description
        assert added_template.description is not None
        assert len(added_template.description) > 0
        assert "discovery" in added_template.description.lower()
        assert "delegation" in added_template.description.lower()

    def test_seed_sets_tags(self, mock_db_manager, mock_session):
        """Test that seeded template includes appropriate tags."""
        mock_db_manager.get_session.return_value = mock_session
        mock_session.query.return_value.filter.return_value.first.return_value = None

        from scripts.seed_orchestrator_template import seed_orchestrator_template

        seed_orchestrator_template(mock_db_manager, "test-tenant")

        added_template = mock_session.add.call_args[0][0]

        # Check tags
        tags = added_template.tags
        assert isinstance(tags, list)
        assert "orchestrator" in tags
        assert "discovery" in tags
        assert "delegation" in tags
        assert "default" in tags

    def test_seed_skips_if_exists(self, mock_db_manager, mock_session):
        """Test that seeding skips if template already exists."""
        # Mock existing template
        existing_template = AgentTemplate(
            tenant_key="test-tenant",
            name="orchestrator",
            template_content="existing content",
            is_default=True,
            is_active=True,
        )

        mock_db_manager.get_session.return_value = mock_session
        mock_session.query.return_value.filter.return_value.first.return_value = existing_template

        from scripts.seed_orchestrator_template import seed_orchestrator_template

        seed_orchestrator_template(mock_db_manager, "test-tenant")

        # Should not add new template
        mock_session.add.assert_not_called()

    def test_seed_commits_transaction(self, mock_db_manager, mock_session):
        """Test that seeding commits the transaction."""
        mock_db_manager.get_session.return_value = mock_session
        mock_session.query.return_value.filter.return_value.first.return_value = None

        from scripts.seed_orchestrator_template import seed_orchestrator_template

        seed_orchestrator_template(mock_db_manager, "test-tenant")

        # Verify commit was called
        mock_session.commit.assert_called_once()

    def test_seed_handles_errors_gracefully(self, mock_db_manager, mock_session):
        """Test that seeding handles errors gracefully."""
        mock_db_manager.get_session.return_value = mock_session
        mock_session.query.side_effect = Exception("Database error")

        from scripts.seed_orchestrator_template import seed_orchestrator_template

        # Should raise exception (caller handles it)
        with pytest.raises(Exception):
            seed_orchestrator_template(mock_db_manager, "test-tenant")

    def test_seed_uses_template_manager_content(self, mock_db_manager, mock_session):
        """Test that seeding uses UnifiedTemplateManager for content."""
        mock_db_manager.get_session.return_value = mock_session
        mock_session.query.return_value.filter.return_value.first.return_value = None

        from scripts.seed_orchestrator_template import seed_orchestrator_template
        from src.giljo_mcp.template_manager import UnifiedTemplateManager

        # Create template manager to compare
        template_mgr = UnifiedTemplateManager()
        expected_content = template_mgr._legacy_templates["orchestrator"]

        seed_orchestrator_template(mock_db_manager, "test-tenant")

        added_template = mock_session.add.call_args[0][0]

        # Content should match template manager
        assert added_template.template_content == expected_content
