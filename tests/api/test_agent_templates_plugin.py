"""
Plugin Template Endpoint Integration Tests - Handover 0334a (TDD RED Phase)

Tests for the public, unauthenticated plugin template endpoint.
Validates multi-tenant isolation, rate limiting, and response structure.

CRITICAL: These tests MUST FAIL initially (endpoint not implemented yet).
Expected failures: 404 Not Found for all tests.

Endpoint: GET /api/v1/agent-templates/plugin
Authentication: None (public endpoint with rate limiting)
Rate Limit: 100 requests/minute per tenant_key

Test Coverage:
- Valid tenant returns active templates with full_instructions
- Unknown tenant returns empty list (200 OK, prevents enumeration)
- Missing/invalid tenant_key returns 422 validation error
- Rate limiting triggers 429 after 100 requests
- include_inactive flag returns inactive templates
- Multi-tenant isolation (zero cross-tenant leakage)
- Response structure validation (templates, tenant_key, count, cache_ttl)
- System-managed roles excluded (orchestrator, etc.)
- Capabilities field populated from meta_data or generated
"""

import asyncio
import pytest
from httpx import AsyncClient
from sqlalchemy import select
from uuid import uuid4

# Models
from src.giljo_mcp.models import AgentTemplate
from src.giljo_mcp.tenant import TenantManager


# ============================================================================
# FIXTURES
# ============================================================================

@pytest.fixture
async def sample_templates_for_plugin(db_manager):
    """
    Create sample AgentTemplate records for plugin endpoint testing.

    Returns:
        dict: {
            "tenant_key": "tk_...",
            "active_templates": [AgentTemplate, ...],
            "inactive_templates": [AgentTemplate, ...]
        }
    """
    tenant_key = TenantManager.generate_tenant_key()
    active_templates = []
    inactive_templates = []

    async with db_manager.get_session_async() as session:
        # Create 3 active templates (different roles)
        active_roles = [
            {
                "name": "implementor",
                "role": "implementor",
                "category": "role",
                "description": "TDD implementation specialist",
                "system_instructions": "You are a TDD implementor agent.",
                "user_instructions": "Follow test-driven development strictly.",
                "cli_tool": "claude",
                "model": "sonnet",
                "background_color": "#4CAF50",
                "meta_data": {"capabilities": ["testing", "implementation", "tdd"]}
            },
            {
                "name": "architect",
                "role": "architect",
                "category": "role",
                "description": "System architecture specialist",
                "system_instructions": "You are an architect agent.",
                "user_instructions": "Design scalable systems.",
                "cli_tool": "codex",
                "model": "gpt-4",
                "background_color": "#2196F3",
                "meta_data": {"capabilities": ["design", "architecture", "planning"]}
            },
            {
                "name": "tester",
                "role": "tester",
                "category": "role",
                "description": "Quality assurance specialist",
                "system_instructions": "You are a tester agent.",
                "user_instructions": "Write comprehensive tests.",
                "cli_tool": "gemini",
                "model": "gemini-pro",
                "background_color": "#FF9800",
                "meta_data": {}  # No capabilities - should be generated
            }
        ]

        for role_data in active_roles:
            template = AgentTemplate(
                id=str(uuid4()),
                tenant_key=tenant_key,
                product_id=None,
                name=role_data["name"],
                role=role_data["role"],
                category=role_data["category"],
                description=role_data["description"],
                system_instructions=role_data["system_instructions"],
                user_instructions=role_data["user_instructions"],
                template_content=f"{role_data['system_instructions']} {role_data['user_instructions']}",
                cli_tool=role_data["cli_tool"],
                model=role_data["model"],
                background_color=role_data["background_color"],
                meta_data=role_data["meta_data"],
                is_active=True,
                version="1.0.0"
            )
            session.add(template)
            active_templates.append(template)

        # Create 1 inactive template
        inactive_template = AgentTemplate(
            id=str(uuid4()),
            tenant_key=tenant_key,
            product_id=None,
            name="deprecated-agent",
            role="deprecated",
            category="role",
            description="Deprecated agent template",
            system_instructions="Old agent template.",
            user_instructions="Do not use.",
            template_content="Old agent template. Do not use.",
            cli_tool="claude",
            model="haiku",
            background_color="#9E9E9E",
            meta_data={},
            is_active=False,
            version="0.9.0"
        )
        session.add(inactive_template)
        inactive_templates.append(inactive_template)

        # Create 1 orchestrator template (system-managed, should be excluded)
        orchestrator_template = AgentTemplate(
            id=str(uuid4()),
            tenant_key=tenant_key,
            product_id=None,
            name="orchestrator",
            role="orchestrator",
            category="role",
            description="System orchestrator (should be excluded)",
            system_instructions="You are the orchestrator.",
            user_instructions="Coordinate agents.",
            template_content="You are the orchestrator. Coordinate agents.",
            cli_tool="claude",
            model="opus",
            background_color="#9C27B0",
            meta_data={},
            is_active=True,
            version="1.0.0"
        )
        session.add(orchestrator_template)

        await session.commit()

        # Refresh all templates to get database-generated values
        for template in active_templates + inactive_templates + [orchestrator_template]:
            await session.refresh(template)

    return {
        "tenant_key": tenant_key,
        "active_templates": active_templates,
        "inactive_templates": inactive_templates
    }


@pytest.fixture
async def other_tenant_templates(db_manager):
    """
    Create templates for a different tenant (multi-tenant isolation testing).

    Returns:
        dict: {
            "tenant_key": "tk_...",
            "templates": [AgentTemplate, ...]
        }
    """
    tenant_key = TenantManager.generate_tenant_key()
    templates = []

    async with db_manager.get_session_async() as session:
        template = AgentTemplate(
            id=str(uuid4()),
            tenant_key=tenant_key,
            product_id=None,
            name="other-tenant-agent",
            role="developer",
            category="role",
            description="Template for different tenant",
            system_instructions="Other tenant agent.",
            user_instructions="Private to other tenant.",
            template_content="Other tenant agent. Private to other tenant.",
            cli_tool="claude",
            model="sonnet",
            background_color="#E91E63",
            meta_data={},
            is_active=True,
            version="1.0.0"
        )
        session.add(template)
        templates.append(template)

        await session.commit()
        await session.refresh(template)

    return {
        "tenant_key": tenant_key,
        "templates": templates
    }


# ============================================================================
# BASIC ENDPOINT TESTS
# ============================================================================

class TestPluginEndpointBasics:
    """Test basic endpoint behavior - valid requests, missing params, invalid formats"""

    @pytest.mark.asyncio
    async def test_valid_tenant_returns_templates(
        self, api_client: AsyncClient, sample_templates_for_plugin: dict
    ):
        """Test valid tenant_key returns active templates with full_instructions."""
        tenant_key = sample_templates_for_plugin["tenant_key"]

        response = await api_client.get(
            f"/api/v1/agent-templates/plugin?tenant_key={tenant_key}"
        )

        assert response.status_code == 200
        data = response.json()

        # Validate response structure
        assert "templates" in data
        assert "tenant_key" in data
        assert "count" in data
        assert "cache_ttl" in data

        # Validate response values
        assert data["tenant_key"] == tenant_key
        assert data["count"] >= 2  # At least 2 active templates (excluding orchestrator)
        assert data["cache_ttl"] == 300  # 5 minutes

        # Validate template structure
        templates = data["templates"]
        assert len(templates) >= 2

        for template in templates:
            assert "id" in template
            assert "name" in template
            assert "role" in template
            assert "category" in template
            assert "description" in template
            assert "full_instructions" in template
            assert "capabilities" in template
            assert "version" in template
            assert "background_color" in template
            assert "cli_tool" in template
            assert "model" in template

            # full_instructions should be system_instructions + user_instructions combined
            assert len(template["full_instructions"]) > 0
            assert isinstance(template["capabilities"], list)

            # System-managed roles should be excluded
            assert template["role"] != "orchestrator"

    @pytest.mark.asyncio
    async def test_unknown_tenant_returns_empty_list(
        self, api_client: AsyncClient
    ):
        """Test unknown tenant_key returns empty list (200 OK, prevents enumeration)."""
        # Generate valid format tenant_key that doesn't exist in database
        unknown_tenant_key = TenantManager.generate_tenant_key()

        response = await api_client.get(
            f"/api/v1/agent-templates/plugin?tenant_key={unknown_tenant_key}"
        )

        # Should return 200 OK (not 404) to prevent tenant enumeration
        assert response.status_code == 200
        data = response.json()

        assert data["templates"] == []
        assert data["tenant_key"] == unknown_tenant_key
        assert data["count"] == 0
        assert data["cache_ttl"] == 300

    @pytest.mark.asyncio
    async def test_missing_tenant_key_returns_422(
        self, api_client: AsyncClient
    ):
        """Test missing tenant_key parameter returns 422 validation error."""
        response = await api_client.get("/api/v1/agent-templates/plugin")

        assert response.status_code == 422
        data = response.json()

        # FastAPI validation error response
        assert "detail" in data

    @pytest.mark.asyncio
    async def test_invalid_tenant_key_format_returns_422(
        self, api_client: AsyncClient
    ):
        """Test invalid tenant_key formats return 422 validation error."""
        invalid_keys = [
            "invalid-key",  # Missing tk_ prefix
            "tk_short",  # Too short (not 32 chars after prefix)
            "wrong_prefix_12345678901234567890123456",  # Wrong prefix
            "tk_",  # Prefix only, no value
            "",  # Empty string
            "tk_invalid!@#$%^&*()",  # Invalid characters
        ]

        for invalid_key in invalid_keys:
            response = await api_client.get(
                f"/api/v1/agent-templates/plugin?tenant_key={invalid_key}"
            )

            assert response.status_code == 422, f"Failed for invalid_key: {invalid_key}"


# ============================================================================
# RATE LIMITING TESTS
# ============================================================================

class TestRateLimiting:
    """Test rate limiting (100 requests/minute per tenant_key)"""

    @pytest.mark.asyncio
    async def test_rate_limiting_triggers_429(
        self, api_client: AsyncClient, sample_templates_for_plugin: dict
    ):
        """Test 101 requests trigger 429 Too Many Requests (limit: 100/min)."""
        tenant_key = sample_templates_for_plugin["tenant_key"]

        # Make 100 requests (should all succeed)
        for i in range(100):
            response = await api_client.get(
                f"/api/v1/agent-templates/plugin?tenant_key={tenant_key}"
            )
            assert response.status_code == 200, f"Request {i+1} failed with {response.status_code}"

        # 101st request should trigger rate limit
        response = await api_client.get(
            f"/api/v1/agent-templates/plugin?tenant_key={tenant_key}"
        )

        assert response.status_code == 429
        data = response.json()
        assert "detail" in data
        assert "rate limit" in data["detail"].lower()


# ============================================================================
# INCLUDE_INACTIVE FLAG TESTS
# ============================================================================

class TestIncludeInactiveFlag:
    """Test include_inactive query parameter behavior"""

    @pytest.mark.asyncio
    async def test_include_inactive_flag_works(
        self, api_client: AsyncClient, sample_templates_for_plugin: dict
    ):
        """Test include_inactive=true returns inactive templates."""
        tenant_key = sample_templates_for_plugin["tenant_key"]

        response = await api_client.get(
            f"/api/v1/agent-templates/plugin?tenant_key={tenant_key}&include_inactive=true"
        )

        assert response.status_code == 200
        data = response.json()

        # Should include inactive templates
        templates = data["templates"]
        inactive_count = sum(1 for t in templates if not t.get("is_active", True))
        assert inactive_count > 0, "Should include at least one inactive template"

    @pytest.mark.asyncio
    async def test_default_excludes_inactive_templates(
        self, api_client: AsyncClient, sample_templates_for_plugin: dict
    ):
        """Test default behavior excludes inactive templates."""
        tenant_key = sample_templates_for_plugin["tenant_key"]

        # Test without include_inactive parameter
        response = await api_client.get(
            f"/api/v1/agent-templates/plugin?tenant_key={tenant_key}"
        )

        assert response.status_code == 200
        data = response.json()

        # Should only return active templates
        templates = data["templates"]
        for template in templates:
            # is_active might not be in response, but all returned should be active
            # We can verify by checking that inactive templates are not present
            assert template["name"] != "deprecated-agent"


# ============================================================================
# MULTI-TENANT ISOLATION TESTS
# ============================================================================

class TestMultiTenantIsolation:
    """Test multi-tenant isolation - zero cross-tenant leakage"""

    @pytest.mark.asyncio
    async def test_multi_tenant_isolation(
        self, api_client: AsyncClient, sample_templates_for_plugin: dict, other_tenant_templates: dict
    ):
        """Test different tenant_keys return only their own templates."""
        tenant_a_key = sample_templates_for_plugin["tenant_key"]
        tenant_b_key = other_tenant_templates["tenant_key"]

        # Get tenant A templates
        response_a = await api_client.get(
            f"/api/v1/agent-templates/plugin?tenant_key={tenant_a_key}"
        )
        assert response_a.status_code == 200
        data_a = response_a.json()

        # Get tenant B templates
        response_b = await api_client.get(
            f"/api/v1/agent-templates/plugin?tenant_key={tenant_b_key}"
        )
        assert response_b.status_code == 200
        data_b = response_b.json()

        # Extract template IDs
        ids_a = {t["id"] for t in data_a["templates"]}
        ids_b = {t["id"] for t in data_b["templates"]}

        # Zero cross-tenant leakage
        assert len(ids_a & ids_b) == 0, "Templates leaked across tenants!"

        # Verify tenant B has their template
        tenant_b_names = {t["name"] for t in data_b["templates"]}
        assert "other-tenant-agent" in tenant_b_names


# ============================================================================
# RESPONSE STRUCTURE TESTS
# ============================================================================

class TestResponseStructure:
    """Test response structure and field validation"""

    @pytest.mark.asyncio
    async def test_full_instructions_field_populated(
        self, api_client: AsyncClient, sample_templates_for_plugin: dict
    ):
        """Test full_instructions field is populated (system + user combined)."""
        tenant_key = sample_templates_for_plugin["tenant_key"]

        response = await api_client.get(
            f"/api/v1/agent-templates/plugin?tenant_key={tenant_key}"
        )

        assert response.status_code == 200
        data = response.json()

        templates = data["templates"]
        assert len(templates) > 0

        for template in templates:
            assert "full_instructions" in template
            full_instructions = template["full_instructions"]

            # Should be non-empty string
            assert isinstance(full_instructions, str)
            assert len(full_instructions) > 0

            # Should contain both system and user instructions
            # (combined from system_instructions + user_instructions fields)
            # We know implementor has "TDD implementor agent" in system and
            # "Follow test-driven development" in user
            if template["name"] == "implementor":
                assert "TDD implementor agent" in full_instructions
                assert "Follow test-driven development" in full_instructions

    @pytest.mark.asyncio
    async def test_capabilities_field_present(
        self, api_client: AsyncClient, sample_templates_for_plugin: dict
    ):
        """Test capabilities field is present (from meta_data or generated)."""
        tenant_key = sample_templates_for_plugin["tenant_key"]

        response = await api_client.get(
            f"/api/v1/agent-templates/plugin?tenant_key={tenant_key}"
        )

        assert response.status_code == 200
        data = response.json()

        templates = data["templates"]
        assert len(templates) > 0

        for template in templates:
            assert "capabilities" in template
            capabilities = template["capabilities"]

            # Should be array
            assert isinstance(capabilities, list)

            # Templates with meta_data.capabilities should use those
            if template["name"] == "implementor":
                assert set(capabilities) == {"testing", "implementation", "tdd"}
            elif template["name"] == "architect":
                assert set(capabilities) == {"design", "architecture", "planning"}
            # Templates without meta_data.capabilities should have generated ones
            elif template["name"] == "tester":
                assert len(capabilities) > 0  # Should be generated

    @pytest.mark.asyncio
    async def test_system_managed_roles_excluded(
        self, api_client: AsyncClient, sample_templates_for_plugin: dict
    ):
        """Test orchestrator and other system roles are excluded."""
        tenant_key = sample_templates_for_plugin["tenant_key"]

        response = await api_client.get(
            f"/api/v1/agent-templates/plugin?tenant_key={tenant_key}"
        )

        assert response.status_code == 200
        data = response.json()

        templates = data["templates"]
        template_roles = {t["role"] for t in templates}

        # System-managed roles that should be excluded
        system_roles = {"orchestrator", "system", "admin"}

        # None of these should appear in results
        assert len(template_roles & system_roles) == 0

    @pytest.mark.asyncio
    async def test_response_structure(
        self, api_client: AsyncClient, sample_templates_for_plugin: dict
    ):
        """Test response has all required top-level fields."""
        tenant_key = sample_templates_for_plugin["tenant_key"]

        response = await api_client.get(
            f"/api/v1/agent-templates/plugin?tenant_key={tenant_key}"
        )

        assert response.status_code == 200
        data = response.json()

        # Required top-level fields
        required_fields = {"templates", "tenant_key", "count", "cache_ttl"}
        assert set(data.keys()) == required_fields

        # Validate types
        assert isinstance(data["templates"], list)
        assert isinstance(data["tenant_key"], str)
        assert isinstance(data["count"], int)
        assert isinstance(data["cache_ttl"], int)

        # Validate values
        assert data["tenant_key"] == tenant_key
        assert data["count"] == len(data["templates"])
        assert data["cache_ttl"] == 300  # 5 minutes

        # Validate template structure
        if len(data["templates"]) > 0:
            template = data["templates"][0]
            required_template_fields = {
                "id", "name", "role", "category", "description",
                "full_instructions", "capabilities", "version",
                "background_color", "cli_tool", "model", "is_active"
            }
            assert set(template.keys()) == required_template_fields
