"""
Integration tests for Download API endpoints (Handover 0094)
Tests complete backend-to-frontend flow with real database and ZIP generation.

Integration Test Coverage:
1. Download endpoints return valid ZIP files
2. ZIP contents match expected file structure
3. API key/JWT authentication works correctly
4. Install script rendering ({{SERVER_URL}} substitution)
5. Error responses with fallback instructions
6. Multi-tenant isolation (different users get different templates)
7. File integrity and extraction
8. Security validation
"""

import io
import zipfile

import pytest
from httpx import AsyncClient
from sqlalchemy.ext.asyncio import AsyncSession

from src.giljo_mcp.models import AgentTemplate, User


# ========================================
# Integration Test: Slash Commands Download
# ========================================


class TestSlashCommandsDownloadIntegration:
    """Integration tests for /api/download/slash-commands.zip"""

    @pytest.mark.asyncio
    async def test_download_slash_commands_complete_flow(self, authed_client: AsyncClient, auth_headers: dict):
        """Test complete slash commands download flow"""
        response = await authed_client.get("/api/download/slash-commands.zip", headers=auth_headers)

        # Verify response
        assert response.status_code == 200
        assert response.headers["content-type"] == "application/zip"
        assert "attachment" in response.headers.get("content-disposition", "")
        assert "slash-commands.zip" in response.headers.get("content-disposition", "")

        # Verify ZIP is valid
        zip_bytes = response.content
        assert len(zip_bytes) > 0

        with zipfile.ZipFile(io.BytesIO(zip_bytes), "r") as zipf:
            # Verify ZIP integrity
            bad_file = zipf.testzip()
            assert bad_file is None, f"ZIP integrity check failed: {bad_file}"

            # Verify expected files
            namelist = zipf.namelist()
            assert "gil_get_claude_agents.md" in namelist
            assert "gil_activate.md" in namelist
            assert "gil_launch.md" in namelist
            assert "gil_handover.md" in namelist
            # Install scripts are optional (only included if templates exist)
            assert "install.sh" in namelist or "install.ps1" in namelist

            # Verify content structure
            for filename in namelist:
                content = zipf.read(filename).decode("utf-8")

                if filename.endswith(".md"):
                    # Verify YAML frontmatter
                    assert content.startswith("---\n"), f"{filename} missing YAML frontmatter"
                    assert "name:" in content
                    assert "description:" in content
                else:
                    # install.sh / install.ps1 should have server_url rendered
                    assert "{{SERVER_URL}}" not in content, f"{filename} still contains placeholder"

                # Verify content is not empty
                assert len(content) > 100, f"{filename} content too short"

    @pytest.mark.asyncio
    async def test_slash_commands_content_verification(self, authed_client: AsyncClient, auth_headers: dict):
        """Verify slash commands contain correct content"""
        response = await authed_client.get("/api/download/slash-commands.zip", headers=auth_headers)

        zip_bytes = response.content
        with zipfile.ZipFile(io.BytesIO(zip_bytes), "r") as zipf:
            # Test gil_get_claude_agents.md
            content = zipf.read("gil_get_claude_agents.md").decode("utf-8")
            assert "name: gil_get_claude_agents" in content
            assert "mcp__giljo-mcp__get_agent_download_url" in content

            # Test gil_handover.md
            content = zipf.read("gil_handover.md").decode("utf-8")
            assert "name: gil_handover" in content
            assert "handover" in content.lower() or "succession" in content.lower()

    @pytest.mark.asyncio
    async def test_slash_commands_unauthenticated(self, authed_client: AsyncClient):
        """Test slash commands download without authentication (public)"""
        response = await authed_client.get("/api/download/slash-commands.zip")
        assert response.status_code == 200


# ========================================
# Integration Test: Agent Templates Download
# ========================================


class TestAgentTemplatesDownloadIntegration:
    """Integration tests for /api/download/agent-templates.zip"""

    @pytest.mark.asyncio
    async def test_download_agent_templates_complete_flow(
        self,
        authed_client: AsyncClient,
        auth_headers: dict,
        db_session: AsyncSession,
        test_user: User,
    ):
        """Test complete agent templates download flow"""
        # Create test templates
        templates = [
            AgentTemplate(
                name="orchestrator",
                role="orchestrator",
                description="Orchestrates the development workflow",
                template_content="You are the orchestrator agent responsible for coordinating development.",
                tool="claude",
                tenant_key=test_user.tenant_key,
                is_active=True,
                behavioral_rules=["Always prioritize quality", "Communicate clearly"],
                success_criteria=["All agents coordinated", "Deliverables complete"],
            ),
            AgentTemplate(
                name="implementor",
                role="implementor",
                description="Implements features",
                template_content="You are the implementor agent responsible for writing code.",
                tool="claude",
                tenant_key=test_user.tenant_key,
                is_active=True,
            ),
            AgentTemplate(
                name="tester",
                role="tester",
                description="Tests implementations",
                template_content="You are the tester agent responsible for verifying code.",
                tool="claude",
                tenant_key=test_user.tenant_key,
                is_active=True,
            ),
        ]
        db_session.add_all(templates)
        await db_session.commit()

        # Download templates
        response = await authed_client.get("/api/download/agent-templates.zip?active_only=true", headers=auth_headers)

        # Verify response
        assert response.status_code == 200
        assert response.headers["content-type"] == "application/zip"
        assert "attachment" in response.headers.get("content-disposition", "")

        # Verify ZIP
        zip_bytes = response.content
        with zipfile.ZipFile(io.BytesIO(zip_bytes), "r") as zipf:
            # Verify ZIP integrity
            assert zipf.testzip() is None

            # Verify files
            namelist = zipf.namelist()
            assert "orchestrator.md" in namelist
            assert "implementor.md" in namelist
            assert "tester.md" in namelist

            # Verify YAML frontmatter
            orchestrator_content = zipf.read("orchestrator.md").decode("utf-8")
            assert orchestrator_content.startswith("---\n")
            assert "name: orchestrator" in orchestrator_content
            assert "description: Orchestrates the development workflow" in orchestrator_content
            # 0102a: omit tools field to inherit all
            assert "tools:" not in orchestrator_content
            assert "model: sonnet" in orchestrator_content

            # Verify behavioral rules included
            assert "## Behavioral Rules" in orchestrator_content
            assert "Always prioritize quality" in orchestrator_content

            # Verify success criteria included
            assert "## Success Criteria" in orchestrator_content
            assert "All agents coordinated" in orchestrator_content

    @pytest.mark.asyncio
    async def test_agent_templates_active_only_filter(
        self,
        authed_client: AsyncClient,
        auth_headers: dict,
        db_session: AsyncSession,
        test_user: User,
    ):
        """Test active_only filter works correctly"""
        # Create active and inactive templates
        templates = [
            AgentTemplate(
                name="active_agent",
                role="active",
                template_content="Active template",
                tool="claude",
                tenant_key=test_user.tenant_key,
                is_active=True,
            ),
            AgentTemplate(
                name="inactive_agent",
                role="inactive",
                template_content="Inactive template",
                tool="claude",
                tenant_key=test_user.tenant_key,
                is_active=False,
            ),
        ]
        db_session.add_all(templates)
        await db_session.commit()

        # Test active_only=true (default)
        response = await authed_client.get("/api/download/agent-templates.zip?active_only=true", headers=auth_headers)
        assert response.status_code == 200

        zip_bytes = response.content
        with zipfile.ZipFile(io.BytesIO(zip_bytes), "r") as zipf:
            namelist = zipf.namelist()
            assert "active_agent.md" in namelist
            assert "inactive_agent.md" not in namelist

        # Test active_only=false
        response = await authed_client.get("/api/download/agent-templates.zip?active_only=false", headers=auth_headers)
        assert response.status_code == 200

        zip_bytes = response.content
        with zipfile.ZipFile(io.BytesIO(zip_bytes), "r") as zipf:
            namelist = zipf.namelist()
            assert "active_agent.md" in namelist
            assert "inactive_agent.md" in namelist

    @pytest.mark.asyncio
    async def test_agent_templates_multi_tenant_isolation(
        self,
        authed_client: AsyncClient,
        auth_headers: dict,
        db_session: AsyncSession,
        test_user: User,
    ):
        """Test multi-tenant isolation - CRITICAL security test"""
        # Create templates for test user's tenant
        my_templates = [
            AgentTemplate(
                name="my_template_1",
                role="role1",
                template_content="My content 1",
                tool="claude",
                tenant_key=test_user.tenant_key,
                is_active=True,
            ),
            AgentTemplate(
                name="my_template_2",
                role="role2",
                template_content="My content 2",
                tool="claude",
                tenant_key=test_user.tenant_key,
                is_active=True,
            ),
        ]

        # Create templates for different tenant (security test)
        other_tenant_key = "other-tenant-key-12345"
        other_templates = [
            AgentTemplate(
                name="other_template_1",
                role="role3",
                template_content="Other content 1",
                tool="claude",
                tenant_key=other_tenant_key,
                is_active=True,
            ),
            AgentTemplate(
                name="other_template_2",
                role="role4",
                template_content="Other content 2",
                tool="claude",
                tenant_key=other_tenant_key,
                is_active=True,
            ),
        ]

        db_session.add_all(my_templates + other_templates)
        await db_session.commit()

        # Download templates for test user
        response = await authed_client.get("/api/download/agent-templates.zip", headers=auth_headers)
        assert response.status_code == 200

        # Verify ONLY user's templates returned
        zip_bytes = response.content
        with zipfile.ZipFile(io.BytesIO(zip_bytes), "r") as zipf:
            namelist = zipf.namelist()

            # User's templates present
            assert "my_template_1.md" in namelist
            assert "my_template_2.md" in namelist

            # Other tenant's templates NOT present (security requirement)
            assert "other_template_1.md" not in namelist
            assert "other_template_2.md" not in namelist

            # Verify no data leakage in content
            for filename in namelist:
                content = zipf.read(filename).decode("utf-8")
                assert other_tenant_key not in content
                assert "Other content" not in content

    @pytest.mark.asyncio
    async def test_agent_templates_no_templates_found(
        self,
        authed_client: AsyncClient,
        auth_headers: dict,
        db_session: AsyncSession,
        test_user: User,
    ):
        """Test 404 response when no templates exist for tenant"""
        # Ensure no templates for this tenant
        # (fresh test database should have no templates)

        response = await authed_client.get("/api/download/agent-templates.zip", headers=auth_headers)
        assert response.status_code == 404
        assert "No agent templates found" in response.json()["detail"]


# ========================================
# Integration Test: Install Scripts
# ========================================


class TestInstallScriptsIntegration:
    """Integration tests for install script downloads"""

    @pytest.mark.asyncio
    async def test_download_install_script_sh(self, authed_client: AsyncClient, auth_headers: dict):
        """Test Unix/macOS install script download"""
        response = await authed_client.get(
            "/api/download/install-script.sh?script_type=slash-commands",
            headers=auth_headers,
        )

        assert response.status_code == 200
        assert response.headers["content-type"] == "application/x-sh"

        script_content = response.text

        # Verify bash script structure
        assert script_content.startswith("#!/bin/bash")
        assert "$GILJO_API_KEY" in script_content
        assert "/api/download/slash-commands.zip" in script_content
        assert "curl" in script_content
        assert "unzip" in script_content

        # Verify server URL was templated
        assert "{{SERVER_URL}}" not in script_content
        assert "http://" in script_content or "https://" in script_content

    @pytest.mark.asyncio
    async def test_download_install_script_ps1(self, authed_client: AsyncClient, auth_headers: dict):
        """Test Windows PowerShell install script download"""
        response = await authed_client.get(
            "/api/download/install-script.ps1?script_type=agent-templates",
            headers=auth_headers,
        )

        assert response.status_code == 200
        assert response.headers["content-type"] == "application/x-powershell"

        script_content = response.text

        # Verify PowerShell script structure
        assert "$env:GILJO_API_KEY" in script_content
        assert "/api/download/agent-templates.zip" in script_content
        assert "Invoke-WebRequest" in script_content
        assert "Expand-Archive" in script_content

        # Verify server URL was templated
        assert "{{SERVER_URL}}" not in script_content
        assert "http://" in script_content or "https://" in script_content

    @pytest.mark.asyncio
    async def test_install_script_invalid_extension(self, authed_client: AsyncClient, auth_headers: dict):
        """Test error handling for invalid script extension"""
        response = await authed_client.get(
            "/api/download/install-script.bat?script_type=slash-commands",
            headers=auth_headers,
        )
        assert response.status_code == 400
        assert "Invalid extension" in response.json()["detail"]

    @pytest.mark.asyncio
    async def test_install_script_invalid_type(self, authed_client: AsyncClient, auth_headers: dict):
        """Test error handling for invalid script type"""
        response = await authed_client.get(
            "/api/download/install-script.sh?script_type=invalid-type",
            headers=auth_headers,
        )
        assert response.status_code == 400
        assert "Invalid type" in response.json()["detail"]


# ========================================
# Integration Test: Security & Authentication
# ========================================


class TestSecurityIntegration:
    """Security and authentication integration tests"""

    @pytest.mark.asyncio
    async def test_public_endpoints_access(self, authed_client: AsyncClient):
        """Slash commands and install scripts are public; agent templates optional-auth."""
        public_endpoints = [
            "/api/download/slash-commands.zip",
            "/api/download/install-script.sh?script_type=slash-commands",
            "/api/download/install-script.ps1?script_type=agent-templates",
        ]

        for endpoint in public_endpoints:
            response = await authed_client.get(endpoint)
            assert response.status_code == 200, f"{endpoint} should be public"

        # Agent templates: optional-auth
        response = await authed_client.get("/api/download/agent-templates.zip")
        assert response.status_code in [200, 404]

    @pytest.mark.asyncio
    async def test_bearer_token_authentication(self, authed_client: AsyncClient, auth_headers: dict):
        """Test Bearer token authentication works"""
        response = await authed_client.get("/api/download/slash-commands.zip", headers=auth_headers)
        assert response.status_code == 200

    @pytest.mark.asyncio
    async def test_api_key_authentication(self, authed_client: AsyncClient, test_user: User):
        """Slash commands endpoint is public (auth header ignored)."""
        api_key_headers = {"X-API-Key": "gk_test_key_12345"}

        response = await authed_client.get("/api/download/slash-commands.zip", headers=api_key_headers)

        assert response.status_code == 200


# ========================================
# Integration Test: Performance & File Integrity
# ========================================


class TestPerformanceAndIntegrity:
    """Performance and file integrity tests"""

    @pytest.mark.asyncio
    async def test_zip_file_integrity(
        self,
        authed_client: AsyncClient,
        auth_headers: dict,
        db_session: AsyncSession,
        test_user: User,
    ):
        """Test ZIP files can be extracted and are not corrupted"""
        # Create templates
        template = AgentTemplate(
            name="test_agent",
            role="tester",
            template_content="Test content " * 1000,  # Large content
            tool="claude",
            tenant_key=test_user.tenant_key,
            is_active=True,
        )
        db_session.add(template)
        await db_session.commit()

        # Download ZIP
        response = await authed_client.get("/api/download/agent-templates.zip", headers=auth_headers)
        assert response.status_code == 200

        zip_bytes = response.content

        # Test ZIP integrity
        with zipfile.ZipFile(io.BytesIO(zip_bytes), "r") as zipf:
            # testzip() returns None if no errors
            bad_file = zipf.testzip()
            assert bad_file is None, f"ZIP file corrupted: {bad_file}"

            # Extract and verify content
            content = zipf.read("test_agent.md").decode("utf-8")
            assert len(content) > 5000  # Should be large
            assert "Test content" in content

    @pytest.mark.asyncio
    async def test_unicode_content_handling(
        self,
        authed_client: AsyncClient,
        auth_headers: dict,
        db_session: AsyncSession,
        test_user: User,
    ):
        """Test Unicode content is preserved in ZIP files"""
        template = AgentTemplate(
            name="unicode_agent",
            role="unicode_tester",
            template_content="Unicode test: 测试 🚀 العربية Ελληνικά",
            tool="claude",
            tenant_key=test_user.tenant_key,
            is_active=True,
        )
        db_session.add(template)
        await db_session.commit()

        response = await authed_client.get("/api/download/agent-templates.zip", headers=auth_headers)
        assert response.status_code == 200

        zip_bytes = response.content
        with zipfile.ZipFile(io.BytesIO(zip_bytes), "r") as zipf:
            content = zipf.read("unicode_agent.md").decode("utf-8")
            assert "测试" in content
            assert "🚀" in content
            assert "العربية" in content
            assert "Ελληνικά" in content

    @pytest.mark.asyncio
    async def test_download_performance(
        self,
        authed_client: AsyncClient,
        auth_headers: dict,
        db_session: AsyncSession,
        test_user: User,
    ):
        """Test download performance with many templates"""
        # Create 20 templates
        templates = [
            AgentTemplate(
                name=f"agent_{i}",
                role=f"role_{i}",
                template_content=f"Content for agent {i}" * 100,
                tool="claude",
                tenant_key=test_user.tenant_key,
                is_active=True,
            )
            for i in range(20)
        ]
        db_session.add_all(templates)
        await db_session.commit()

        import time

        start_time = time.time()
        response = await authed_client.get("/api/download/agent-templates.zip", headers=auth_headers)
        end_time = time.time()

        assert response.status_code == 200

        # Should complete in under 5 seconds
        elapsed = end_time - start_time
        assert elapsed < 5.0, f"Download took {elapsed:.2f}s (expected <5s)"

        # Verify all templates included
        zip_bytes = response.content
        with zipfile.ZipFile(io.BytesIO(zip_bytes), "r") as zipf:
            namelist = zipf.namelist()
            # 0102a: Cap packaging to 8 distinct roles
            md_files = [name for name in namelist if name.endswith(".md")]
            assert len(md_files) == 8
            expected = {f"agent_{i}.md" for i in range(20)}
            assert set(md_files).issubset(expected)
