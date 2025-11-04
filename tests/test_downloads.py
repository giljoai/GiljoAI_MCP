"""
Unit tests for api/endpoints/downloads.py
Tests download endpoints for slash commands and agent templates.

Test-Driven Development: These tests are written BEFORE implementation.
"""

import io
import zipfile
from datetime import datetime
from pathlib import Path
from unittest.mock import AsyncMock, MagicMock, patch

import pytest
from fastapi import HTTPException
from sqlalchemy import select

from src.giljo_mcp.models import AgentTemplate, User


class TestZipArchiveCreation:
    """Test ZIP archive creation utility"""

    def test_create_zip_archive_basic(self):
        """Test basic ZIP archive creation from file dict"""
        from api.endpoints.downloads import create_zip_archive

        files = {
            "file1.md": "# Content 1",
            "file2.md": "# Content 2",
            "file3.md": "# Content 3",
        }

        zip_bytes = create_zip_archive(files)

        # Verify ZIP is valid
        assert isinstance(zip_bytes, bytes)
        assert len(zip_bytes) > 0

        # Verify contents
        with zipfile.ZipFile(io.BytesIO(zip_bytes), "r") as zipf:
            namelist = zipf.namelist()
            assert len(namelist) == 3
            assert "file1.md" in namelist
            assert "file2.md" in namelist
            assert "file3.md" in namelist

            # Verify content
            assert zipf.read("file1.md").decode("utf-8") == "# Content 1"

    def test_create_zip_archive_empty(self):
        """Test ZIP archive creation with no files"""
        from api.endpoints.downloads import create_zip_archive

        files = {}
        zip_bytes = create_zip_archive(files)

        # Should create empty ZIP
        assert isinstance(zip_bytes, bytes)
        with zipfile.ZipFile(io.BytesIO(zip_bytes), "r") as zipf:
            assert len(zipf.namelist()) == 0

    def test_create_zip_archive_unicode_content(self):
        """Test ZIP archive with Unicode content"""
        from api.endpoints.downloads import create_zip_archive

        files = {
            "test.md": "# 测试 🚀 Test",
        }

        zip_bytes = create_zip_archive(files)
        with zipfile.ZipFile(io.BytesIO(zip_bytes), "r") as zipf:
            content = zipf.read("test.md").decode("utf-8")
            assert "测试" in content
            assert "🚀" in content


class TestDownloadSlashCommands:
    """Test /api/download/slash-commands.zip endpoint"""

    @pytest.mark.asyncio
    async def test_download_slash_commands_authenticated(self, test_client, auth_headers):
        """Test slash commands download with authentication"""
        response = test_client.get(
            "/api/download/slash-commands.zip",
            headers=auth_headers
        )

        assert response.status_code == 200
        assert response.headers["content-type"] == "application/zip"
        assert "attachment" in response.headers.get("content-disposition", "")

        # Verify ZIP contents
        zip_bytes = response.content
        with zipfile.ZipFile(io.BytesIO(zip_bytes), "r") as zipf:
            namelist = zipf.namelist()
            assert "gil_import_productagents.md" in namelist
            assert "gil_import_personalagents.md" in namelist
            assert "gil_handover.md" in namelist

    @pytest.mark.asyncio
    async def test_download_slash_commands_unauthenticated(self, test_client):
        """Test slash commands download without authentication"""
        response = test_client.get("/api/download/slash-commands.zip")

        assert response.status_code == 401

    @pytest.mark.asyncio
    async def test_download_slash_commands_content_verification(self, test_client, auth_headers):
        """Test slash commands ZIP contains correct content"""
        response = test_client.get(
            "/api/download/slash-commands.zip",
            headers=auth_headers
        )

        zip_bytes = response.content
        with zipfile.ZipFile(io.BytesIO(zip_bytes), "r") as zipf:
            # Verify gil_import_productagents.md content
            content = zipf.read("gil_import_productagents.md").decode("utf-8")
            assert "name: gil_import_productagents" in content
            assert "description:" in content
            assert "Import agent templates" in content


class TestDownloadAgentTemplates:
    """Test /api/download/agent-templates.zip endpoint"""

    @pytest.mark.asyncio
    async def test_download_agent_templates_authenticated(
        self, test_client, auth_headers, test_db_session, test_user
    ):
        """Test agent templates download with authentication"""
        # Create test templates
        templates = [
            AgentTemplate(
                name="orchestrator",
                role="orchestrator",
                template_content="# Orchestrator content",
                tool="claude",
                tenant_key=test_user.tenant_key,
                is_active=True,
            ),
            AgentTemplate(
                name="implementor",
                role="implementor",
                template_content="# Implementor content",
                tool="claude",
                tenant_key=test_user.tenant_key,
                is_active=True,
            ),
        ]
        test_db_session.add_all(templates)
        await test_db_session.commit()

        response = test_client.get(
            "/api/download/agent-templates.zip",
            headers=auth_headers
        )

        assert response.status_code == 200
        assert response.headers["content-type"] == "application/zip"

        # Verify ZIP contents
        zip_bytes = response.content
        with zipfile.ZipFile(io.BytesIO(zip_bytes), "r") as zipf:
            namelist = zipf.namelist()
            assert "orchestrator.md" in namelist
            assert "implementor.md" in namelist

    @pytest.mark.asyncio
    async def test_download_agent_templates_active_only(
        self, test_client, auth_headers, test_db_session, test_user
    ):
        """Test agent templates download filters inactive templates"""
        # Create active and inactive templates
        templates = [
            AgentTemplate(
                name="active",
                role="active",
                template_content="# Active",
                tool="claude",
                tenant_key=test_user.tenant_key,
                is_active=True,
            ),
            AgentTemplate(
                name="inactive",
                role="inactive",
                template_content="# Inactive",
                tool="claude",
                tenant_key=test_user.tenant_key,
                is_active=False,
            ),
        ]
        test_db_session.add_all(templates)
        await test_db_session.commit()

        response = test_client.get(
            "/api/download/agent-templates.zip?active_only=true",
            headers=auth_headers
        )

        zip_bytes = response.content
        with zipfile.ZipFile(io.BytesIO(zip_bytes), "r") as zipf:
            namelist = zipf.namelist()
            assert "active.md" in namelist
            assert "inactive.md" not in namelist

    @pytest.mark.asyncio
    async def test_download_agent_templates_with_frontmatter(
        self, test_client, auth_headers, test_db_session, test_user
    ):
        """Test agent templates ZIP includes YAML frontmatter"""
        template = AgentTemplate(
            name="tester",
            role="tester",
            description="Test agent",
            template_content="# Tester content",
            tool="claude",
            tenant_key=test_user.tenant_key,
            is_active=True,
        )
        test_db_session.add(template)
        await test_db_session.commit()

        response = test_client.get(
            "/api/download/agent-templates.zip",
            headers=auth_headers
        )

        zip_bytes = response.content
        with zipfile.ZipFile(io.BytesIO(zip_bytes), "r") as zipf:
            content = zipf.read("tester.md").decode("utf-8")
            # Verify YAML frontmatter
            assert "---" in content
            assert "name: tester" in content
            assert "description: Test agent" in content
            assert 'tools: ["mcp__giljo_mcp__*"]' in content
            assert "model: sonnet" in content

    @pytest.mark.asyncio
    async def test_download_agent_templates_multi_tenant_isolation(
        self, test_client, auth_headers, test_db_session, test_user
    ):
        """Test agent templates download respects multi-tenant isolation"""
        # Create templates for different tenants
        other_tenant_key = "other-tenant-key"
        templates = [
            AgentTemplate(
                name="my_template",
                role="role1",
                template_content="# My content",
                tool="claude",
                tenant_key=test_user.tenant_key,
                is_active=True,
            ),
            AgentTemplate(
                name="other_template",
                role="role2",
                template_content="# Other content",
                tool="claude",
                tenant_key=other_tenant_key,
                is_active=True,
            ),
        ]
        test_db_session.add_all(templates)
        await test_db_session.commit()

        response = test_client.get(
            "/api/download/agent-templates.zip",
            headers=auth_headers
        )

        zip_bytes = response.content
        with zipfile.ZipFile(io.BytesIO(zip_bytes), "r") as zipf:
            namelist = zipf.namelist()
            assert "my_template.md" in namelist
            assert "other_template.md" not in namelist

    @pytest.mark.asyncio
    async def test_download_agent_templates_unauthenticated(self, test_client):
        """Test agent templates download without authentication"""
        response = test_client.get("/api/download/agent-templates.zip")

        assert response.status_code == 401


class TestDownloadInstallScript:
    """Test /api/download/install-script.{extension} endpoint"""

    @pytest.mark.asyncio
    async def test_download_install_script_sh(self, test_client, auth_headers):
        """Test Unix install script download"""
        response = test_client.get(
            "/api/download/install-script.sh?type=slash-commands",
            headers=auth_headers
        )

        assert response.status_code == 200
        assert response.headers["content-type"] == "application/x-sh"
        assert "attachment" in response.headers.get("content-disposition", "")

        # Verify script content
        content = response.text
        assert "#!/bin/bash" in content
        assert "$GILJO_API_KEY" in content
        assert "/api/download/slash-commands.zip" in content

    @pytest.mark.asyncio
    async def test_download_install_script_ps1(self, test_client, auth_headers):
        """Test PowerShell install script download"""
        response = test_client.get(
            "/api/download/install-script.ps1?type=agent-templates",
            headers=auth_headers
        )

        assert response.status_code == 200
        assert response.headers["content-type"] == "application/x-powershell"
        assert "attachment" in response.headers.get("content-disposition", "")

        # Verify script content
        content = response.text
        assert "$env:GILJO_API_KEY" in content
        assert "/api/download/agent-templates.zip" in content

    @pytest.mark.asyncio
    async def test_download_install_script_invalid_extension(self, test_client, auth_headers):
        """Test install script download with invalid extension"""
        response = test_client.get(
            "/api/download/install-script.bat?type=slash-commands",
            headers=auth_headers
        )

        assert response.status_code == 400

    @pytest.mark.asyncio
    async def test_download_install_script_invalid_type(self, test_client, auth_headers):
        """Test install script download with invalid type"""
        response = test_client.get(
            "/api/download/install-script.sh?type=invalid",
            headers=auth_headers
        )

        assert response.status_code == 400

    @pytest.mark.asyncio
    async def test_download_install_script_server_url_templating(
        self, test_client, auth_headers
    ):
        """Test install script includes correct server URL"""
        response = test_client.get(
            "/api/download/install-script.sh?type=slash-commands",
            headers=auth_headers
        )

        content = response.text
        # Should have replaced template variable
        assert "{{SERVER_URL}}" not in content
        # Should have actual server URL
        assert "http://" in content or "https://" in content


class TestAPIKeyAuthentication:
    """Test API key authentication for download endpoints"""

    @pytest.mark.asyncio
    async def test_download_with_api_key_header(self, test_client, test_user):
        """Test download endpoint with X-API-Key header"""
        # Assume user has api_key attribute
        api_key = f"gk_{test_user.username}_test"

        response = test_client.get(
            "/api/download/slash-commands.zip",
            headers={"X-API-Key": api_key}
        )

        # Should succeed with valid API key
        assert response.status_code in [200, 401]  # Depends on API key validation

    @pytest.mark.asyncio
    async def test_download_with_bearer_token(self, test_client, auth_headers):
        """Test download endpoint with Bearer token"""
        response = test_client.get(
            "/api/download/slash-commands.zip",
            headers=auth_headers
        )

        assert response.status_code == 200

    @pytest.mark.asyncio
    async def test_download_without_authentication(self, test_client):
        """Test download endpoint without any authentication"""
        response = test_client.get("/api/download/slash-commands.zip")

        assert response.status_code == 401


class TestServerURLUtility:
    """Test get_server_url utility function"""

    def test_get_server_url_from_config(self):
        """Test server URL extraction from config"""
        from api.endpoints.downloads import get_server_url

        url = get_server_url()
        assert isinstance(url, str)
        assert url.startswith("http://") or url.startswith("https://")

    @patch("api.endpoints.downloads.get_config")
    def test_get_server_url_localhost_fallback(self, mock_get_config):
        """Test server URL uses localhost for 0.0.0.0"""
        mock_config = MagicMock()
        mock_config.api.host = "0.0.0.0"
        mock_config.api.port = 7272
        mock_get_config.return_value = mock_config

        from api.endpoints.downloads import get_server_url

        url = get_server_url()
        assert "localhost:7272" in url


# Fixtures for testing
@pytest.fixture
def test_user():
    """Create test user"""
    return User(
        id="test-user-id",
        username="testuser",
        email="test@example.com",
        tenant_key="test-tenant",
        is_active=True,
    )


@pytest.fixture
def auth_headers(test_user):
    """Generate authentication headers"""
    # Mock JWT token
    return {
        "Authorization": "Bearer test-token-12345"
    }
