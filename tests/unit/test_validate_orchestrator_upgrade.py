"""
Unit tests for scripts/validate_orchestrator_upgrade.py

Tests validation checks for orchestrator upgrade components.
"""

import sys
from pathlib import Path
from unittest.mock import MagicMock, Mock, patch


# Add project root to path
sys.path.insert(0, str(Path(__file__).parent.parent.parent))

from scripts.validate_orchestrator_upgrade import validate_filtering, validate_migration, validate_orchestrator_template


class TestValidateMigration:
    """Test database migration validation"""

    @patch("scripts.validate_orchestrator_upgrade.get_db_manager")
    def test_validate_migration_success(self, mock_get_db):
        """Test successful migration validation"""
        # Mock database inspector
        mock_inspector = Mock()
        mock_inspector.get_columns.return_value = [
            {"name": "id"},
            {"name": "name"},
            {"name": "config_data"},
            {"name": "created_at"},
        ]
        mock_inspector.get_indexes.return_value = [{"name": "idx_product_config_data_gin"}]

        # Mock database manager
        mock_db = Mock()
        mock_db.engine = Mock()
        mock_get_db.return_value = mock_db

        with patch("scripts.validate_orchestrator_upgrade.inspect", return_value=mock_inspector):
            result = validate_migration()

        assert result is True

    @patch("scripts.validate_orchestrator_upgrade.get_db_manager")
    def test_validate_migration_missing_column(self, mock_get_db):
        """Test validation fails when column missing"""
        # Mock database inspector without config_data column
        mock_inspector = Mock()
        mock_inspector.get_columns.return_value = [{"name": "id"}, {"name": "name"}, {"name": "created_at"}]

        # Mock database manager
        mock_db = Mock()
        mock_db.engine = Mock()
        mock_get_db.return_value = mock_db

        with patch("scripts.validate_orchestrator_upgrade.inspect", return_value=mock_inspector):
            result = validate_migration()

        assert result is False

    @patch("scripts.validate_orchestrator_upgrade.get_db_manager")
    def test_validate_migration_without_gin_index(self, mock_get_db, capsys):
        """Test validation succeeds without GIN index (partial indexing)"""
        # Mock database inspector
        mock_inspector = Mock()
        mock_inspector.get_columns.return_value = [{"name": "id"}, {"name": "config_data"}]
        mock_inspector.get_indexes.return_value = []

        # Mock database manager
        mock_db = Mock()
        mock_db.engine = Mock()
        mock_get_db.return_value = mock_db

        with patch("scripts.validate_orchestrator_upgrade.inspect", return_value=mock_inspector):
            result = validate_migration()

        # Should still pass (GIN index is optional)
        assert result is True

        # Check warning message
        captured = capsys.readouterr()
        assert "may be normal if using partial indexing" in captured.out


class TestValidateFiltering:
    """Test role-based config filtering validation"""

    @patch("scripts.validate_orchestrator_upgrade.get_db_manager")
    def test_validate_filtering_success(self, mock_get_db):
        """Test successful filtering validation"""
        # Mock session
        mock_session = MagicMock()
        mock_session.__enter__ = Mock(return_value=mock_session)
        mock_session.__exit__ = Mock(return_value=False)

        # Mock database manager
        mock_db = Mock()
        mock_db.get_session.return_value = mock_session
        mock_get_db.return_value = mock_db

        # Mock config functions
        with patch("scripts.validate_orchestrator_upgrade.get_full_config") as mock_full:
            with patch("scripts.validate_orchestrator_upgrade.get_filtered_config") as mock_filtered:
                # Setup mock returns
                mock_full.return_value = {
                    "architecture": "Test",
                    "tech_stack": ["Python"],
                    "test_commands": ["pytest"],
                    "api_docs": "/docs/api.md",
                    "serena_mcp_enabled": True,
                }

                # Implementer config (no test_commands)
                mock_filtered.side_effect = [
                    {
                        "architecture": "Test",
                        "tech_stack": ["Python"],
                        "api_docs": "/docs/api.md",
                        "serena_mcp_enabled": True,
                    },
                    # Tester config (has test_commands, no api_docs)
                    {"architecture": "Test", "test_commands": ["pytest"], "serena_mcp_enabled": True},
                ]

                result = validate_filtering()

        assert result is True

    @patch("scripts.validate_orchestrator_upgrade.get_db_manager")
    def test_validate_filtering_implementer_leak(self, mock_get_db):
        """Test validation fails when implementer gets test_commands"""
        # Mock session
        mock_session = MagicMock()
        mock_session.__enter__ = Mock(return_value=mock_session)
        mock_session.__exit__ = Mock(return_value=False)

        # Mock database manager
        mock_db = Mock()
        mock_db.get_session.return_value = mock_session
        mock_get_db.return_value = mock_db

        # Mock config functions
        with patch("scripts.validate_orchestrator_upgrade.get_full_config") as mock_full:
            with patch("scripts.validate_orchestrator_upgrade.get_filtered_config") as mock_filtered:
                # Setup mock returns
                mock_full.return_value = {
                    "architecture": "Test",
                    "test_commands": ["pytest"],
                    "serena_mcp_enabled": True,
                }

                # Implementer config INCORRECTLY has test_commands
                mock_filtered.return_value = {
                    "architecture": "Test",
                    "test_commands": ["pytest"],  # Should be filtered out!
                    "serena_mcp_enabled": True,
                }

                result = validate_filtering()

        assert result is False

    @patch("scripts.validate_orchestrator_upgrade.get_db_manager")
    def test_validate_filtering_tester_missing_commands(self, mock_get_db):
        """Test validation fails when tester doesn't get test_commands"""
        # Mock session
        mock_session = MagicMock()
        mock_session.__enter__ = Mock(return_value=mock_session)
        mock_session.__exit__ = Mock(return_value=False)

        # Mock database manager
        mock_db = Mock()
        mock_db.get_session.return_value = mock_session
        mock_get_db.return_value = mock_db

        # Mock config functions
        with patch("scripts.validate_orchestrator_upgrade.get_full_config") as mock_full:
            with patch("scripts.validate_orchestrator_upgrade.get_filtered_config") as mock_filtered:
                # Setup mock returns
                mock_full.return_value = {
                    "architecture": "Test",
                    "test_commands": ["pytest"],
                    "serena_mcp_enabled": True,
                }

                # Implementer config (first call)
                mock_filtered.side_effect = [
                    {"architecture": "Test", "serena_mcp_enabled": True},
                    # Tester config MISSING test_commands (second call)
                    {"architecture": "Test", "serena_mcp_enabled": True},
                ]

                result = validate_filtering()

        assert result is False


class TestValidateOrchestratorTemplate:
    """Test orchestrator template validation"""

    @patch("scripts.validate_orchestrator_upgrade.get_db_manager")
    def test_validate_template_success(self, mock_get_db):
        """Test successful template validation"""
        # Mock template
        mock_template = Mock()
        mock_template.name = "orchestrator"
        mock_template.is_default = True
        mock_template.template_content = """
Enhanced Orchestrator Agent

Key Principles:
- 30-80-10 principle: delegate implementation
- 3-tool rule: after 3 tools, delegate to specialist
- Discovery workflow: use Serena MCP tools first
- Delegation enforcement: never do implementation yourself
- After-action docs: write completion report to devlog
"""

        # Mock session
        mock_session = MagicMock()
        mock_session.__enter__ = Mock(return_value=mock_session)
        mock_session.__exit__ = Mock(return_value=False)
        mock_session.query.return_value.filter.return_value.first.return_value = mock_template

        # Mock database manager
        mock_db = Mock()
        mock_db.get_session.return_value = mock_session
        mock_get_db.return_value = mock_db

        result = validate_orchestrator_template()

        assert result is True

    @patch("scripts.validate_orchestrator_upgrade.get_db_manager")
    def test_validate_template_not_found(self, mock_get_db):
        """Test validation fails when template not found"""
        # Mock session - no template found
        mock_session = MagicMock()
        mock_session.__enter__ = Mock(return_value=mock_session)
        mock_session.__exit__ = Mock(return_value=False)
        mock_session.query.return_value.filter.return_value.first.return_value = None

        # Mock database manager
        mock_db = Mock()
        mock_db.get_session.return_value = mock_session
        mock_get_db.return_value = mock_db

        result = validate_orchestrator_template()

        assert result is False

    @patch("scripts.validate_orchestrator_upgrade.get_db_manager")
    def test_validate_template_missing_30_80_10(self, mock_get_db):
        """Test validation fails when 30-80-10 missing"""
        # Mock template without 30-80-10
        mock_template = Mock()
        mock_template.name = "orchestrator"
        mock_template.is_default = True
        mock_template.template_content = """
Simple orchestrator template.
Uses discovery and delegation.
"""

        # Mock session
        mock_session = MagicMock()
        mock_session.__enter__ = Mock(return_value=mock_session)
        mock_session.__exit__ = Mock(return_value=False)
        mock_session.query.return_value.filter.return_value.first.return_value = mock_template

        # Mock database manager
        mock_db = Mock()
        mock_db.get_session.return_value = mock_session
        mock_get_db.return_value = mock_db

        result = validate_orchestrator_template()

        assert result is False

    @patch("scripts.validate_orchestrator_upgrade.get_db_manager")
    def test_validate_template_missing_3_tool_rule(self, mock_get_db):
        """Test validation fails when 3-tool rule missing"""
        # Mock template without 3-tool rule
        mock_template = Mock()
        mock_template.name = "orchestrator"
        mock_template.is_default = True
        mock_template.template_content = """
30-80-10 principle
Uses discovery and serena
Writes completion reports to devlog
"""

        # Mock session
        mock_session = MagicMock()
        mock_session.__enter__ = Mock(return_value=mock_session)
        mock_session.__exit__ = Mock(return_value=False)
        mock_session.query.return_value.filter.return_value.first.return_value = mock_template

        # Mock database manager
        mock_db = Mock()
        mock_db.get_session.return_value = mock_session
        mock_get_db.return_value = mock_db

        result = validate_orchestrator_template()

        assert result is False

    @patch("scripts.validate_orchestrator_upgrade.get_db_manager")
    def test_validate_template_missing_discovery(self, mock_get_db):
        """Test validation fails when discovery workflow missing"""
        # Mock template without discovery/serena
        mock_template = Mock()
        mock_template.name = "orchestrator"
        mock_template.is_default = True
        mock_template.template_content = """
30-80-10 principle
3-tool rule enforced
Writes to devlog
"""

        # Mock session
        mock_session = MagicMock()
        mock_session.__enter__ = Mock(return_value=mock_session)
        mock_session.__exit__ = Mock(return_value=False)
        mock_session.query.return_value.filter.return_value.first.return_value = mock_template

        # Mock database manager
        mock_db = Mock()
        mock_db.get_session.return_value = mock_session
        mock_get_db.return_value = mock_db

        result = validate_orchestrator_template()

        assert result is False

    @patch("scripts.validate_orchestrator_upgrade.get_db_manager")
    def test_validate_template_missing_delegation(self, mock_get_db):
        """Test validation fails when delegation enforcement missing"""
        # Mock template without delegate keyword
        mock_template = Mock()
        mock_template.name = "orchestrator"
        mock_template.is_default = True
        mock_template.template_content = """
30-80-10 principle
3-tool rule
Uses discovery and serena
Writes completion reports
"""

        # Mock session
        mock_session = MagicMock()
        mock_session.__enter__ = Mock(return_value=mock_session)
        mock_session.__exit__ = Mock(return_value=False)
        mock_session.query.return_value.filter.return_value.first.return_value = mock_template

        # Mock database manager
        mock_db = Mock()
        mock_db.get_session.return_value = mock_session
        mock_get_db.return_value = mock_db

        result = validate_orchestrator_template()

        assert result is False

    @patch("scripts.validate_orchestrator_upgrade.get_db_manager")
    def test_validate_template_missing_devlog(self, mock_get_db):
        """Test validation fails when after-action docs missing"""
        # Mock template without completion report or devlog
        mock_template = Mock()
        mock_template.name = "orchestrator"
        mock_template.is_default = True
        mock_template.template_content = """
30-80-10 principle
3-tool rule
Uses discovery and serena with delegation
"""

        # Mock session
        mock_session = MagicMock()
        mock_session.__enter__ = Mock(return_value=mock_session)
        mock_session.__exit__ = Mock(return_value=False)
        mock_session.query.return_value.filter.return_value.first.return_value = mock_template

        # Mock database manager
        mock_db = Mock()
        mock_db.get_session.return_value = mock_session
        mock_get_db.return_value = mock_db

        result = validate_orchestrator_template()

        assert result is False
