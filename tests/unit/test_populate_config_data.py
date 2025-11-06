"""
Unit tests for scripts/populate_config_data.py

Tests configuration extraction and population logic.
"""

import json
import sys
from pathlib import Path
from unittest.mock import MagicMock, patch


# Add project root to path
sys.path.insert(0, str(Path(__file__).parent.parent.parent))

from scripts.populate_config_data import (
    check_serena_mcp_available,
    detect_backend_framework,
    detect_codebase_structure,
    detect_frontend_framework,
    extract_architecture_from_claude_md,
    extract_project_config_data,
    extract_tech_stack_from_claude_md,
    extract_test_commands_from_claude_md,
)


class TestExtractArchitecture:
    """Test architecture extraction from CLAUDE.md"""

    def test_extract_architecture_explicit_section(self, tmp_path):
        """Test extraction from explicit Architecture section"""
        claude_md = tmp_path / "CLAUDE.md"
        claude_md.write_text("""
# Project

## Architecture Overview

FastAPI + PostgreSQL + Vue.js multi-tenant system

## Other Section
""")

        result = extract_architecture_from_claude_md(claude_md)
        assert result == "FastAPI + PostgreSQL + Vue.js multi-tenant system"

    def test_extract_architecture_alternative_header(self, tmp_path):
        """Test extraction from alternative header format"""
        claude_md = tmp_path / "CLAUDE.md"
        claude_md.write_text("""
### Architecture

Django + MySQL REST API

### Components
""")

        result = extract_architecture_from_claude_md(claude_md)
        assert result == "Django + MySQL REST API"

    def test_extract_architecture_inline(self, tmp_path):
        """Test extraction from inline Architecture: pattern"""
        claude_md = tmp_path / "CLAUDE.md"
        claude_md.write_text("""
Architecture: Flask + SQLite + React
""")

        result = extract_architecture_from_claude_md(claude_md)
        assert result == "Flask + SQLite + React"

    def test_extract_architecture_fallback_inference(self, tmp_path):
        """Test fallback inference from content"""
        claude_md = tmp_path / "CLAUDE.md"
        claude_md.write_text("""
This project uses FastAPI for the backend with PostgreSQL database.
The frontend is built with Vue 3.
""")

        result = extract_architecture_from_claude_md(claude_md)
        assert result == "FastAPI + PostgreSQL + Vue.js"

    def test_extract_architecture_missing_file(self, tmp_path):
        """Test handling of missing CLAUDE.md"""
        claude_md = tmp_path / "CLAUDE.md"

        result = extract_architecture_from_claude_md(claude_md)
        assert result is None

    def test_extract_architecture_no_match(self, tmp_path):
        """Test when no architecture can be determined"""
        claude_md = tmp_path / "CLAUDE.md"
        claude_md.write_text("""
# Some Project
Just a README file.
""")

        result = extract_architecture_from_claude_md(claude_md)
        assert result is None


class TestExtractTechStack:
    """Test tech stack extraction from CLAUDE.md"""

    def test_extract_tech_stack_comprehensive(self, tmp_path):
        """Test extraction of comprehensive tech stack"""
        claude_md = tmp_path / "CLAUDE.md"
        claude_md.write_text("""
**Tech Stack**:
- Python 3.11
- PostgreSQL 18
- FastAPI
- Vue 3
- Docker
- SQLAlchemy
- Alembic
""")

        result = extract_tech_stack_from_claude_md(claude_md)

        assert "Python 3.11" in result
        assert "PostgreSQL 18" in result
        assert "FastAPI" in result
        assert "Vue 3" in result
        assert "Docker" in result
        assert "SQLAlchemy" in result
        assert "Alembic" in result

    def test_extract_tech_stack_inline_versions(self, tmp_path):
        """Test extraction with inline version numbers"""
        claude_md = tmp_path / "CLAUDE.md"
        claude_md.write_text("""
Built with Python 3.13 and PostgreSQL 18.
""")

        result = extract_tech_stack_from_claude_md(claude_md)

        assert "Python 3.13" in result
        assert "PostgreSQL 18" in result

    def test_extract_tech_stack_frameworks_only(self, tmp_path):
        """Test extraction of frameworks without versions"""
        claude_md = tmp_path / "CLAUDE.md"
        claude_md.write_text("""
Frontend: React with TypeScript
Backend: Django REST Framework
""")

        result = extract_tech_stack_from_claude_md(claude_md)

        assert "React" in result
        assert "Django" in result

    def test_extract_tech_stack_missing_file(self, tmp_path):
        """Test handling of missing CLAUDE.md"""
        claude_md = tmp_path / "CLAUDE.md"

        result = extract_tech_stack_from_claude_md(claude_md)
        assert result == []


class TestExtractTestCommands:
    """Test test command extraction from CLAUDE.md"""

    def test_extract_pytest_command(self, tmp_path):
        """Test extraction of pytest command"""
        claude_md = tmp_path / "CLAUDE.md"
        claude_md.write_text("""
## Testing

Run tests with:
pytest tests/ --cov=src
""")

        result = extract_test_commands_from_claude_md(claude_md)

        assert "pytest tests/ --cov=src" in result

    def test_extract_npm_test_command(self, tmp_path):
        """Test extraction of npm test command"""
        claude_md = tmp_path / "CLAUDE.md"
        claude_md.write_text("""
Frontend tests:
npm run test:unit
""")

        result = extract_test_commands_from_claude_md(claude_md)

        assert "npm run test:unit" in result

    def test_extract_multiple_test_commands(self, tmp_path):
        """Test extraction of multiple test commands"""
        claude_md = tmp_path / "CLAUDE.md"
        claude_md.write_text("""
Testing:
- Backend: pytest tests/
- Frontend: npm run test
""")

        result = extract_test_commands_from_claude_md(claude_md)

        assert "pytest tests/" in result
        assert "npm run test" in result

    def test_extract_test_commands_fallback(self, tmp_path):
        """Test fallback defaults when commands mentioned but not explicit"""
        claude_md = tmp_path / "CLAUDE.md"
        claude_md.write_text("""
We use pytest and npm for testing.
""")

        result = extract_test_commands_from_claude_md(claude_md)

        # Should get fallback defaults when tools mentioned in test context
        assert "pytest tests/" in result or "npm run test" in result

    def test_extract_test_commands_missing_file(self, tmp_path):
        """Test handling of missing CLAUDE.md"""
        claude_md = tmp_path / "CLAUDE.md"

        result = extract_test_commands_from_claude_md(claude_md)
        assert result == []


class TestDetectFrontendFramework:
    """Test frontend framework detection"""

    def test_detect_vue3_root_package_json(self, tmp_path):
        """Test Vue 3 detection from root package.json"""
        package_json = tmp_path / "package.json"
        package_json.write_text(json.dumps({"dependencies": {"vue": "^3.4.0"}}))

        result = detect_frontend_framework(tmp_path)
        assert result == "Vue 3"

    def test_detect_vue_legacy(self, tmp_path):
        """Test Vue.js detection (legacy version)"""
        package_json = tmp_path / "package.json"
        package_json.write_text(json.dumps({"dependencies": {"vue": "^2.7.0"}}))

        result = detect_frontend_framework(tmp_path)
        assert result == "Vue.js"

    def test_detect_react(self, tmp_path):
        """Test React detection"""
        package_json = tmp_path / "package.json"
        package_json.write_text(json.dumps({"dependencies": {"react": "^18.0.0"}}))

        result = detect_frontend_framework(tmp_path)
        assert result == "React"

    def test_detect_angular(self, tmp_path):
        """Test Angular detection"""
        package_json = tmp_path / "package.json"
        package_json.write_text(json.dumps({"dependencies": {"@angular/core": "^17.0.0"}}))

        result = detect_frontend_framework(tmp_path)
        assert result == "Angular"

    def test_detect_svelte(self, tmp_path):
        """Test Svelte detection"""
        package_json = tmp_path / "package.json"
        package_json.write_text(json.dumps({"dependencies": {"svelte": "^4.0.0"}}))

        result = detect_frontend_framework(tmp_path)
        assert result == "Svelte"

    def test_detect_from_frontend_subdirectory(self, tmp_path):
        """Test detection from frontend/ subdirectory"""
        frontend_dir = tmp_path / "frontend"
        frontend_dir.mkdir()

        package_json = frontend_dir / "package.json"
        package_json.write_text(json.dumps({"dependencies": {"vue": "3.4.0"}}))

        result = detect_frontend_framework(tmp_path)
        assert result == "Vue 3"

    def test_detect_no_package_json(self, tmp_path):
        """Test when no package.json exists"""
        result = detect_frontend_framework(tmp_path)
        assert result is None

    def test_detect_invalid_json(self, tmp_path):
        """Test handling of invalid JSON"""
        package_json = tmp_path / "package.json"
        package_json.write_text("{ invalid json }")

        result = detect_frontend_framework(tmp_path)
        assert result is None


class TestDetectBackendFramework:
    """Test backend framework detection"""

    def test_detect_fastapi_from_requirements(self, tmp_path):
        """Test FastAPI detection from requirements.txt"""
        requirements = tmp_path / "requirements.txt"
        requirements.write_text("""
sqlalchemy==2.0.0
fastapi==0.110.0
uvicorn==0.27.0
""")

        result = detect_backend_framework(tmp_path)
        assert result == "FastAPI"

    def test_detect_django_from_requirements(self, tmp_path):
        """Test Django detection from requirements.txt"""
        requirements = tmp_path / "requirements.txt"
        requirements.write_text("""
Django==5.0.0
djangorestframework==3.14.0
""")

        result = detect_backend_framework(tmp_path)
        assert result == "Django"

    def test_detect_flask_from_requirements(self, tmp_path):
        """Test Flask detection from requirements.txt"""
        requirements = tmp_path / "requirements.txt"
        requirements.write_text("""
Flask==3.0.0
flask-sqlalchemy==3.1.0
""")

        result = detect_backend_framework(tmp_path)
        assert result == "Flask"

    def test_detect_fastapi_from_pyproject_toml(self, tmp_path):
        """Test FastAPI detection from pyproject.toml"""
        pyproject = tmp_path / "pyproject.toml"
        pyproject.write_text("""
[tool.poetry.dependencies]
python = "^3.11"
fastapi = "^0.110.0"
""")

        result = detect_backend_framework(tmp_path)
        assert result == "FastAPI"

    def test_detect_no_framework_files(self, tmp_path):
        """Test when no framework files exist"""
        result = detect_backend_framework(tmp_path)
        assert result is None


class TestDetectCodebaseStructure:
    """Test codebase structure detection"""

    def test_detect_common_directories(self, tmp_path):
        """Test detection of common project directories"""
        # Create common directories
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

    def test_detect_src_package(self, tmp_path):
        """Test detection of main package in src/"""
        src_dir = tmp_path / "src"
        src_dir.mkdir()
        (src_dir / "giljo_mcp").mkdir()

        result = detect_codebase_structure(tmp_path)

        assert "src/giljo_mcp" in result
        assert "Giljo Mcp package" in result["src/giljo_mcp"]

    def test_detect_empty_project(self, tmp_path):
        """Test detection with no directories"""
        result = detect_codebase_structure(tmp_path)

        assert result == {}


class TestCheckSerenaMCP:
    """Test Serena MCP availability check"""

    @patch("importlib.util.find_spec")
    def test_serena_mcp_available(self, mock_find_spec):
        """Test when Serena MCP is available"""
        mock_find_spec.return_value = MagicMock()

        result = check_serena_mcp_available()
        assert result is True

    @patch("importlib.util.find_spec")
    def test_serena_mcp_not_available(self, mock_find_spec):
        """Test when Serena MCP is not available"""
        mock_find_spec.return_value = None

        result = check_serena_mcp_available()
        assert result is False

    @patch("importlib.util.find_spec")
    def test_serena_mcp_import_error(self, mock_find_spec):
        """Test when import check raises exception"""
        mock_find_spec.side_effect = Exception("Import error")

        result = check_serena_mcp_available()
        assert result is False


class TestExtractProjectConfigData:
    """Test comprehensive config data extraction"""

    def test_extract_full_config_data(self, tmp_path):
        """Test extraction of comprehensive config data"""
        # Create CLAUDE.md
        claude_md = tmp_path / "CLAUDE.md"
        claude_md.write_text("""
## Architecture Overview

FastAPI + PostgreSQL 18 + Vue 3 multi-tenant orchestration system

## Tech Stack

- Python 3.13
- PostgreSQL 18
- FastAPI
- Vue 3
- Docker

## Testing

Run tests:
pytest tests/ --cov=src
npm run test
""")

        # Create package.json
        (tmp_path / "frontend").mkdir()
        package_json = tmp_path / "frontend" / "package.json"
        package_json.write_text(json.dumps({"dependencies": {"vue": "^3.4.0"}}))

        # Create requirements.txt
        requirements = tmp_path / "requirements.txt"
        requirements.write_text("fastapi==0.110.0")

        # Create directories
        (tmp_path / "api").mkdir()
        (tmp_path / "docs").mkdir()

        with patch("scripts.populate_config_data.check_serena_mcp_available", return_value=True):
            result = extract_project_config_data(tmp_path)

        assert result["architecture"] == "FastAPI + PostgreSQL 18 + Vue 3 multi-tenant orchestration system"
        assert "Python 3.13" in result["tech_stack"]
        assert "PostgreSQL 18" in result["tech_stack"]
        assert "pytest tests/ --cov=src" in result["test_commands"]
        assert "npm run test" in result["test_commands"]
        assert result["frontend_framework"] == "Vue 3"
        assert result["backend_framework"] == "FastAPI"
        assert result["serena_mcp_enabled"] is True
        assert result["database_type"] == "postgresql"

    def test_extract_minimal_config_data(self, tmp_path):
        """Test extraction with minimal project structure"""
        result = extract_project_config_data(tmp_path)

        # Should have defaults
        assert "architecture" in result
        assert result["architecture"] == "Unknown (populate manually)"
        assert result["serena_mcp_enabled"] is False

    def test_extract_with_alembic(self, tmp_path):
        """Test database type detection with Alembic"""
        (tmp_path / "alembic").mkdir()

        result = extract_project_config_data(tmp_path)

        assert result["database_type"] == "postgresql"
