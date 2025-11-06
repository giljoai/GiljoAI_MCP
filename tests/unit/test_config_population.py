"""
Unit tests for config_data population functions.

Tests the automatic population of Product.config_data from project files.
"""

import json
from pathlib import Path
from unittest.mock import Mock, patch

import pytest

from src.giljo_mcp.config_manager import (
    check_serena_mcp_available,
    detect_backend_framework,
    detect_codebase_structure,
    detect_frontend_framework,
    extract_architecture_from_claude_md,
    extract_tech_stack_from_claude_md,
    extract_test_commands_from_claude_md,
    populate_config_data,
)


@pytest.fixture
def sample_claude_md_content():
    """Sample CLAUDE.md content for testing"""
    return """
# CLAUDE.md

## Project Overview

GiljoAI MCP is a multi-agent orchestration system.

## Architecture Overview

FastAPI + PostgreSQL + Vue.js multi-tenant architecture

### Core Components

1. **Orchestrator** - Central coordination
2. **Database Layer** - PostgreSQL 18 backend
3. **Frontend** - Vue 3 + Vuetify dashboard

## Technology Stack

- Python 3.13+
- PostgreSQL 18
- Vue 3
- FastAPI
- Docker
- Alembic
- SQLAlchemy

## Development Commands

### Testing

```bash
pytest tests/                    # Run all tests
pytest tests/unit/               # Run unit tests only
npm run test                     # Run frontend tests
```

### Installation

```bash
python installer/cli/install.py
```
"""


@pytest.fixture
def sample_package_json():
    """Sample package.json for testing"""
    return {
        "name": "test-frontend",
        "version": "1.0.0",
        "dependencies": {"vue": "^3.3.4", "vuetify": "^3.3.0"},
        "devDependencies": {"vite": "^5.0.0"},
    }


@pytest.fixture
def sample_requirements_txt():
    """Sample requirements.txt content"""
    return """
fastapi==0.104.1
sqlalchemy==2.0.23
alembic==1.12.1
pytest==7.4.3
"""


class TestExtractArchitectureFromClaudeMd:
    """Tests for extract_architecture_from_claude_md"""

    def test_extract_architecture_from_section(self, tmp_path, sample_claude_md_content):
        """Test extracting architecture from Architecture Overview section"""
        claude_md = tmp_path / "CLAUDE.md"
        claude_md.write_text(sample_claude_md_content, encoding="utf-8")

        result = extract_architecture_from_claude_md(claude_md)
        assert result == "FastAPI + PostgreSQL + Vue.js multi-tenant architecture"

    def test_extract_architecture_missing_file(self, tmp_path):
        """Test with missing CLAUDE.md file"""
        claude_md = tmp_path / "CLAUDE.md"
        result = extract_architecture_from_claude_md(claude_md)
        assert result is None

    def test_extract_architecture_infers_from_content(self, tmp_path):
        """Test inferring architecture when no explicit section"""
        content = "This project uses FastAPI with PostgreSQL and Vue for the UI"
        claude_md = tmp_path / "CLAUDE.md"
        claude_md.write_text(content, encoding="utf-8")

        result = extract_architecture_from_claude_md(claude_md)
        assert result == "FastAPI + PostgreSQL + Vue.js"

    def test_extract_architecture_react_variant(self, tmp_path):
        """Test inferring React-based architecture"""
        content = "Built with FastAPI backend and PostgreSQL database, React frontend"
        claude_md = tmp_path / "CLAUDE.md"
        claude_md.write_text(content, encoding="utf-8")

        result = extract_architecture_from_claude_md(claude_md)
        assert result == "FastAPI + PostgreSQL + React"

    def test_extract_architecture_no_vue_or_react(self, tmp_path):
        """Test inferring architecture without frontend framework"""
        content = "API built with FastAPI and PostgreSQL database"
        claude_md = tmp_path / "CLAUDE.md"
        claude_md.write_text(content, encoding="utf-8")

        result = extract_architecture_from_claude_md(claude_md)
        assert result == "FastAPI + PostgreSQL"


class TestExtractTechStackFromClaudeMd:
    """Tests for extract_tech_stack_from_claude_md"""

    def test_extract_complete_tech_stack(self, tmp_path, sample_claude_md_content):
        """Test extracting complete tech stack"""
        claude_md = tmp_path / "CLAUDE.md"
        claude_md.write_text(sample_claude_md_content, encoding="utf-8")

        result = extract_tech_stack_from_claude_md(claude_md)

        assert "Python 3.13" in result
        assert "PostgreSQL 18" in result
        assert "Vue 3" in result
        assert "FastAPI" in result
        assert "Docker" in result
        assert "Alembic" in result
        assert "SQLAlchemy" in result

    def test_extract_tech_stack_missing_file(self, tmp_path):
        """Test with missing file"""
        result = extract_tech_stack_from_claude_md(tmp_path / "CLAUDE.md")
        assert result == []

    def test_extract_tech_stack_partial(self, tmp_path):
        """Test extracting partial tech stack"""
        content = "Using Python 3.11 and Flask"
        claude_md = tmp_path / "CLAUDE.md"
        claude_md.write_text(content, encoding="utf-8")

        result = extract_tech_stack_from_claude_md(claude_md)

        assert "Python 3.11" in result
        assert "Flask" in result
        assert len(result) == 2


class TestExtractTestCommandsFromClaudeMd:
    """Tests for extract_test_commands_from_claude_md"""

    def test_extract_test_commands(self, tmp_path, sample_claude_md_content):
        """Test extracting test commands"""
        claude_md = tmp_path / "CLAUDE.md"
        claude_md.write_text(sample_claude_md_content, encoding="utf-8")

        result = extract_test_commands_from_claude_md(claude_md)

        # Check if pytest command is in the results (may include comments)
        assert any("pytest tests/" in cmd for cmd in result)
        assert any("npm run test" in cmd for cmd in result)

    def test_extract_test_commands_missing_file(self, tmp_path):
        """Test with missing file"""
        result = extract_test_commands_from_claude_md(tmp_path / "CLAUDE.md")
        assert result == []

    def test_extract_test_commands_fallback(self, tmp_path):
        """Test fallback when no commands but keywords present"""
        content = "We use pytest and npm"
        claude_md = tmp_path / "CLAUDE.md"
        claude_md.write_text(content, encoding="utf-8")

        result = extract_test_commands_from_claude_md(claude_md)

        # Should extract something when keywords present
        assert len(result) > 0
        # Verify keywords are found in results
        combined = " ".join(result)
        assert "pytest" in combined.lower()
        assert "npm" in combined.lower()


class TestDetectFrontendFramework:
    """Tests for detect_frontend_framework"""

    def test_detect_vue3(self, tmp_path, sample_package_json):
        """Test detecting Vue 3"""
        package_json = tmp_path / "package.json"
        package_json.write_text(json.dumps(sample_package_json), encoding="utf-8")

        result = detect_frontend_framework(tmp_path)
        assert result == "Vue 3"

    def test_detect_vue3_in_frontend_subdir(self, tmp_path, sample_package_json):
        """Test detecting Vue 3 in frontend/ subdirectory"""
        frontend_dir = tmp_path / "frontend"
        frontend_dir.mkdir()
        package_json = frontend_dir / "package.json"
        package_json.write_text(json.dumps(sample_package_json), encoding="utf-8")

        result = detect_frontend_framework(tmp_path)
        assert result == "Vue 3"

    def test_detect_react(self, tmp_path):
        """Test detecting React"""
        package_json_data = {"dependencies": {"react": "^18.2.0"}}
        package_json = tmp_path / "package.json"
        package_json.write_text(json.dumps(package_json_data), encoding="utf-8")

        result = detect_frontend_framework(tmp_path)
        assert result == "React"

    def test_detect_angular(self, tmp_path):
        """Test detecting Angular"""
        package_json_data = {"dependencies": {"@angular/core": "^16.0.0"}}
        package_json = tmp_path / "package.json"
        package_json.write_text(json.dumps(package_json_data), encoding="utf-8")

        result = detect_frontend_framework(tmp_path)
        assert result == "Angular"

    def test_no_package_json(self, tmp_path):
        """Test when no package.json exists"""
        result = detect_frontend_framework(tmp_path)
        assert result is None


class TestDetectBackendFramework:
    """Tests for detect_backend_framework"""

    def test_detect_fastapi(self, tmp_path, sample_requirements_txt):
        """Test detecting FastAPI"""
        requirements = tmp_path / "requirements.txt"
        requirements.write_text(sample_requirements_txt, encoding="utf-8")

        result = detect_backend_framework(tmp_path)
        assert result == "FastAPI"

    def test_detect_django(self, tmp_path):
        """Test detecting Django"""
        requirements = tmp_path / "requirements.txt"
        requirements.write_text("django==4.2.0\n", encoding="utf-8")

        result = detect_backend_framework(tmp_path)
        assert result == "Django"

    def test_detect_flask(self, tmp_path):
        """Test detecting Flask"""
        requirements = tmp_path / "requirements.txt"
        requirements.write_text("flask==2.3.0\n", encoding="utf-8")

        result = detect_backend_framework(tmp_path)
        assert result == "Flask"

    def test_detect_from_pyproject_toml(self, tmp_path):
        """Test detecting from pyproject.toml"""
        pyproject = tmp_path / "pyproject.toml"
        pyproject.write_text('[tool.poetry.dependencies]\nfastapi = "^0.104.0"\n', encoding="utf-8")

        result = detect_backend_framework(tmp_path)
        assert result == "FastAPI"

    def test_no_requirements(self, tmp_path):
        """Test when no requirements file exists"""
        result = detect_backend_framework(tmp_path)
        assert result is None


class TestDetectCodebaseStructure:
    """Tests for detect_codebase_structure"""

    def test_detect_standard_structure(self, tmp_path):
        """Test detecting standard directory structure"""
        # Create standard directories
        (tmp_path / "api").mkdir()
        (tmp_path / "frontend").mkdir()
        (tmp_path / "src").mkdir()
        (tmp_path / "tests").mkdir()
        (tmp_path / "docs").mkdir()

        result = detect_codebase_structure(tmp_path)

        assert result["api"] == "REST API endpoints"
        assert result["frontend"] == "Frontend application"
        assert result["src"] == "Core application code"
        assert result["tests"] == "Test suites"
        assert result["docs"] == "Documentation"

    def test_detect_nested_src_structure(self, tmp_path):
        """Test detecting nested src/ structure"""
        src_dir = tmp_path / "src"
        src_dir.mkdir()
        (src_dir / "giljo_mcp").mkdir()

        result = detect_codebase_structure(tmp_path)

        assert "src" in result
        assert "src/giljo_mcp" in result
        assert "Giljo Mcp package" in result["src/giljo_mcp"]

    def test_detect_partial_structure(self, tmp_path):
        """Test detecting partial directory structure"""
        (tmp_path / "api").mkdir()
        (tmp_path / "docs").mkdir()

        result = detect_codebase_structure(tmp_path)

        assert "api" in result
        assert "docs" in result
        assert "frontend" not in result
        assert "tests" not in result


class TestCheckSerenaMcpAvailable:
    """Tests for check_serena_mcp_available"""

    @patch("importlib.util.find_spec")
    def test_serena_available(self, mock_find_spec):
        """Test when Serena MCP is available"""
        mock_find_spec.return_value = Mock()  # Non-None spec

        result = check_serena_mcp_available()
        assert result is True

    @patch("importlib.util.find_spec")
    def test_serena_not_available(self, mock_find_spec):
        """Test when Serena MCP is not available"""
        mock_find_spec.return_value = None

        result = check_serena_mcp_available()
        assert result is False

    @patch("importlib.util.find_spec")
    def test_serena_check_raises_exception(self, mock_find_spec):
        """Test when check raises an exception"""
        mock_find_spec.side_effect = Exception("Import error")

        result = check_serena_mcp_available()
        assert result is False


class TestPopulateConfigData:
    """Tests for populate_config_data (integration)"""

    def test_populate_config_data_complete(
        self, tmp_path, sample_claude_md_content, sample_package_json, sample_requirements_txt
    ):
        """Test complete config_data population"""
        # Setup project structure
        (tmp_path / "CLAUDE.md").write_text(sample_claude_md_content, encoding="utf-8")
        (tmp_path / "package.json").write_text(json.dumps(sample_package_json), encoding="utf-8")
        (tmp_path / "requirements.txt").write_text(sample_requirements_txt, encoding="utf-8")
        (tmp_path / "docs").mkdir()
        (tmp_path / "alembic").mkdir()
        (tmp_path / "api").mkdir()
        (tmp_path / "frontend").mkdir()
        (tmp_path / "tests").mkdir()

        with patch("src.giljo_mcp.config_manager.check_serena_mcp_available", return_value=True):
            result = populate_config_data("test-product-123", tmp_path)

        # Verify all fields populated
        assert result["architecture"] == "FastAPI + PostgreSQL + Vue.js multi-tenant architecture"
        assert "Python 3.13" in result["tech_stack"]
        assert "PostgreSQL 18" in result["tech_stack"]
        assert any("pytest tests/" in cmd for cmd in result["test_commands"])
        assert result["frontend_framework"] == "Vue 3"
        assert result["backend_framework"] == "FastAPI"
        assert result["serena_mcp_enabled"] is True
        assert result["database_type"] == "postgresql"
        assert "api" in result["codebase_structure"]
        assert result["api_docs"] == "/docs/api_reference.md"

    def test_populate_config_data_minimal(self, tmp_path):
        """Test config_data population with minimal project"""
        # Only CLAUDE.md with minimal content
        (tmp_path / "CLAUDE.md").write_text("# Project\n\nSimple project", encoding="utf-8")

        with patch("src.giljo_mcp.config_manager.check_serena_mcp_available", return_value=False):
            result = populate_config_data("test-product-123", tmp_path)

        # Should have required fields with defaults
        assert result["architecture"] == "Unknown (populate manually)"
        assert result["serena_mcp_enabled"] is False
        # Optional fields should be missing
        assert "tech_stack" not in result
        assert "test_commands" not in result

    def test_populate_config_data_no_claude_md(self, tmp_path):
        """Test config_data population without CLAUDE.md"""
        with patch("src.giljo_mcp.config_manager.check_serena_mcp_available", return_value=False):
            result = populate_config_data("test-product-123", tmp_path)

        # Should have fallback architecture
        assert result["architecture"] == "Unknown (populate manually)"
        assert result["serena_mcp_enabled"] is False

    def test_populate_config_data_uses_cwd_default(self):
        """Test that populate_config_data uses CWD when root_path not provided"""
        with patch("src.giljo_mcp.config_manager.Path.cwd") as mock_cwd:
            mock_cwd.return_value = Path("/fake/path")
            with patch("src.giljo_mcp.config_manager.extract_architecture_from_claude_md", return_value="Test"):
                with patch("src.giljo_mcp.config_manager.check_serena_mcp_available", return_value=False):
                    populate_config_data("test-123")

            # Verify CWD was called
            mock_cwd.assert_called_once()
