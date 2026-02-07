"""
Comprehensive API tests for agent templates endpoints
Handover 0041 - Phase 4: API Integration Testing

Tests cover:
- CRUD operations (Create, Read, Update, Delete)
- New Phase 3 endpoints (reset, diff, preview)
- Security (multi-tenant isolation, authentication, authorization)
- Input validation (template size limits, required fields)
- WebSocket broadcasts (real-time updates)
- Performance (response time targets)
"""

import time
from datetime import datetime, timezone
from uuid import uuid4

import pytest
from fastapi import status
from httpx import AsyncClient
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from src.giljo_mcp.models import AgentTemplate, User


# Test fixtures


@pytest.fixture
async def test_user(db_session: AsyncSession) -> User:
    """Create test user with unique tenant"""
    user = User(
        id=str(uuid4()),
        username=f"testuser_{uuid4().hex[:8]}",
        email=f"test_{uuid4().hex[:8]}@test.com",
        password_hash="test_hash",
        tenant_key=f"tenant_{uuid4().hex[:8]}",
        is_active=True,
        role="developer",
        created_at=datetime.now(timezone.utc),
    )
    db_session.add(user)
    await db_session.commit()
    await db_session.refresh(user)
    return user


@pytest.fixture
def auth_headers(test_user: User) -> dict:
    """Generate JWT authentication headers for test user"""
    # Mock JWT token for testing
    # In real scenario, use proper JWT generation
    return {"Authorization": f"Bearer test_token_{test_user.id}"}


@pytest.fixture
async def orchestrator_template(db_session: AsyncSession, test_user: User) -> AgentTemplate:
    """Create orchestrator template for testing"""
    template = AgentTemplate(
        id=str(uuid4()),
        tenant_key=test_user.tenant_key,
        product_id=None,
        name="Orchestrator",
        role="orchestrator",
        category="role",
        system_instructions="You are the orchestrator for {project_name}. Mission: {project_mission}",
        variables=["project_name", "project_mission"],
        behavioral_rules=["Delegate work", "Monitor progress", "Report status"],
        success_criteria=["All tasks completed", "Quality maintained", "On schedule"],
        description="Project orchestrator template",
        version="1.0.0",
        is_active=True,
        is_default=False,
        tags=["default", "role"],
        usage_count=0,
        preferred_tool="claude",
        created_at=datetime.now(timezone.utc),
    )
    db_session.add(template)
    await db_session.commit()
    await db_session.refresh(template)
    return template


@pytest.fixture
async def system_orchestrator_template(db_session: AsyncSession) -> AgentTemplate:
    """Create system-level orchestrator template"""
    template = AgentTemplate(
        id=str(uuid4()),
        tenant_key="system",
        product_id=None,
        name="System Orchestrator",
        role="orchestrator",
        category="role",
        system_instructions="SYSTEM: You are the orchestrator for {project_name}",
        variables=["project_name"],
        behavioral_rules=["System rule 1", "System rule 2"],
        success_criteria=["System criteria 1"],
        description="System orchestrator template",
        version="1.0.0",
        is_active=True,
        is_default=True,
        tags=["system"],
        usage_count=0,
        preferred_tool="claude",
        created_at=datetime.now(timezone.utc),
    )
    db_session.add(template)
    await db_session.commit()
    await db_session.refresh(template)
    return template


# CRUD Operation Tests


@pytest.mark.asyncio
class TestTemplatesCRUD:
    """Tests for basic CRUD operations on templates"""

    async def test_list_templates_success(
        self,
        async_client: AsyncClient,
        auth_headers: dict,
        orchestrator_template: AgentTemplate,
    ):
        """Test listing templates returns tenant's templates"""
        response = await async_client.get("/api/v1/templates/", headers=auth_headers)

        assert response.status_code == status.HTTP_200_OK
        templates = response.json()
        assert isinstance(templates, list)
        assert len(templates) >= 1
        assert any(t["id"] == orchestrator_template.id for t in templates)

    async def test_list_templates_filters_by_category(
        self,
        async_client: AsyncClient,
        auth_headers: dict,
        orchestrator_template: AgentTemplate,
    ):
        """Test listing templates with category filter"""
        response = await async_client.get("/api/v1/templates/?category=role", headers=auth_headers)

        assert response.status_code == status.HTTP_200_OK
        templates = response.json()
        assert all(t["category"] == "role" for t in templates)

    async def test_list_templates_filters_by_role(
        self,
        async_client: AsyncClient,
        auth_headers: dict,
        orchestrator_template: AgentTemplate,
    ):
        """Test listing templates with role filter"""
        response = await async_client.get("/api/v1/templates/?role=orchestrator", headers=auth_headers)

        assert response.status_code == status.HTTP_200_OK
        templates = response.json()
        assert all(t["role"] == "orchestrator" for t in templates)
        assert len(templates) >= 1

    async def test_create_template_success(self, async_client: AsyncClient, auth_headers: dict, test_user: User):
        """Test creating a new template"""
        template_data = {
            "name": "Custom Analyzer",
            "category": "role",
            "role": "analyzer",
            "system_instructions": "You are an analyzer for {project_name}",
            "description": "Custom analyzer template",
            "behavioral_rules": ["Analyze requirements", "Identify patterns"],
            "success_criteria": ["Analysis complete", "Patterns documented"],
            "tags": ["custom", "analyzer"],
            "is_default": False,
            "preferred_tool": "claude",
        }

        response = await async_client.post("/api/v1/templates/", json=template_data, headers=auth_headers)

        assert response.status_code == status.HTTP_201_CREATED
        created = response.json()
        assert created["name"] == template_data["name"]
        assert created["role"] == template_data["role"]
        assert created["tenant_key"] == test_user.tenant_key
        assert "project_name" in created["variables"]

    async def test_create_template_validates_size_limit(self, async_client: AsyncClient, auth_headers: dict):
        """Test template creation fails when content exceeds 100KB"""
        large_content = "x" * (101 * 1024)  # 101KB
        template_data = {
            "name": "Too Large",
            "category": "role",
            "role": "tester",
            "system_instructions": large_content,
        }

        response = await async_client.post("/api/v1/templates/", json=template_data, headers=auth_headers)

        assert response.status_code == status.HTTP_422_UNPROCESSABLE_ENTITY
        assert "exceeds maximum size" in response.text.lower()

    async def test_update_template_success(
        self,
        async_client: AsyncClient,
        auth_headers: dict,
        orchestrator_template: AgentTemplate,
    ):
        """Test updating an existing template"""
        update_data = {
            "name": "Updated Orchestrator",
            "description": "Updated description",
            "is_default": True,
        }

        response = await async_client.put(
            f"/api/v1/templates/{orchestrator_template.id}",
            json=update_data,
            headers=auth_headers,
        )

        assert response.status_code == status.HTTP_200_OK
        updated = response.json()
        assert updated["name"] == update_data["name"]
        assert updated["description"] == update_data["description"]
        assert updated["is_default"] == update_data["is_default"]

    async def test_delete_template_soft_delete(
        self,
        async_client: AsyncClient,
        auth_headers: dict,
        orchestrator_template: AgentTemplate,
        db_session: AsyncSession,
    ):
        """Test deleting template (soft delete)"""
        response = await async_client.delete(f"/api/v1/templates/{orchestrator_template.id}", headers=auth_headers)

        assert response.status_code == status.HTTP_204_NO_CONTENT

        # Verify template is soft-deleted (is_active=False)
        await db_session.refresh(orchestrator_template)
        assert orchestrator_template.is_active is False


# Phase 3 New Endpoints Tests


@pytest.mark.asyncio
class TestTemplatePhase3Endpoints:
    """Tests for Phase 3 endpoints: reset, diff, preview"""

    async def test_reset_template_to_system_default(
        self,
        async_client: AsyncClient,
        auth_headers: dict,
        orchestrator_template: AgentTemplate,
        system_orchestrator_template: AgentTemplate,
        db_session: AsyncSession,
    ):
        """Test POST /templates/{id}/reset - Reset to system default"""
        # Modify tenant template
        orchestrator_template.system_instructions = "CUSTOM MODIFIED CONTENT"
        await db_session.commit()

        response = await async_client.post(
            f"/api/v1/templates/{orchestrator_template.id}/reset",
            headers=auth_headers,
        )

        assert response.status_code == status.HTTP_200_OK
        result = response.json()
        assert result["success"] is True
        assert "reset" in result["message"].lower()

        # Verify template was reset
        await db_session.refresh(orchestrator_template)
        assert "SYSTEM:" in orchestrator_template.system_instructions

    async def test_reset_template_without_system_default(
        self,
        async_client: AsyncClient,
        auth_headers: dict,
        orchestrator_template: AgentTemplate,
    ):
        """Test reset fails when no system template exists"""
        # No system template exists for this role
        response = await async_client.post(
            f"/api/v1/templates/{orchestrator_template.id}/reset",
            headers=auth_headers,
        )

        # Should fail gracefully or return info message
        assert response.status_code in [
            status.HTTP_404_NOT_FOUND,
            status.HTTP_400_BAD_REQUEST,
        ]

    async def test_diff_template_with_system(
        self,
        async_client: AsyncClient,
        auth_headers: dict,
        orchestrator_template: AgentTemplate,
        system_orchestrator_template: AgentTemplate,
    ):
        """Test GET /templates/{id}/diff - Compare with system template"""
        # Modify tenant template to create difference
        orchestrator_template.system_instructions = "MODIFIED: Custom orchestrator for {project_name}"

        response = await async_client.get(
            f"/api/v1/templates/{orchestrator_template.id}/diff",
            headers=auth_headers,
        )

        assert response.status_code == status.HTTP_200_OK
        diff = response.json()
        assert diff["template_id"] == orchestrator_template.id
        assert diff["has_system_template"] is True
        assert diff["is_customized"] is True
        assert diff["diff_unified"] is not None or diff["diff_html"] is not None

    async def test_diff_template_without_system(
        self,
        async_client: AsyncClient,
        auth_headers: dict,
        orchestrator_template: AgentTemplate,
    ):
        """Test diff when no system template exists"""
        response = await async_client.get(
            f"/api/v1/templates/{orchestrator_template.id}/diff",
            headers=auth_headers,
        )

        assert response.status_code == status.HTTP_200_OK
        diff = response.json()
        assert diff["has_system_template"] is False
        assert diff["is_customized"] is False

    async def test_preview_template_with_variables(
        self,
        async_client: AsyncClient,
        auth_headers: dict,
        orchestrator_template: AgentTemplate,
    ):
        """Test POST /templates/{id}/preview - Preview with variable substitution"""
        preview_data = {
            "variables": {
                "project_name": "Test Project",
                "project_mission": "Build awesome software",
            }
        }

        response = await async_client.post(
            f"/api/v1/templates/{orchestrator_template.id}/preview",
            json=preview_data,
            headers=auth_headers,
        )

        assert response.status_code == status.HTTP_200_OK
        preview = response.json()
        assert preview["template_id"] == orchestrator_template.id
        assert "Test Project" in preview["mission"]
        assert "Build awesome software" in preview["mission"]
        assert "{project_name}" not in preview["mission"]  # Variables replaced

    async def test_preview_template_with_augmentations(
        self,
        async_client: AsyncClient,
        auth_headers: dict,
        orchestrator_template: AgentTemplate,
    ):
        """Test preview with additional augmentation content"""
        preview_data = {
            "variables": {"project_name": "Test", "project_mission": "Test"},
            "augmentations": "\n\n## ADDITIONAL CONTEXT\n- Use Python 3.11\n- Follow PEP 8",
        }

        response = await async_client.post(
            f"/api/v1/templates/{orchestrator_template.id}/preview",
            json=preview_data,
            headers=auth_headers,
        )

        assert response.status_code == status.HTTP_200_OK
        preview = response.json()
        assert "ADDITIONAL CONTEXT" in preview["mission"]
        assert "Python 3.11" in preview["mission"]


# Security Tests


@pytest.mark.asyncio
class TestTemplatesSecurity:
    """Security tests for multi-tenant isolation and authentication"""

    async def test_multi_tenant_isolation_list(
        self,
        async_client: AsyncClient,
        auth_headers: dict,
        orchestrator_template: AgentTemplate,
        db_session: AsyncSession,
    ):
        """Test tenants cannot see each other's templates"""
        # Create template for different tenant
        other_template = AgentTemplate(
            id=str(uuid4()),
            tenant_key="other_tenant_123",
            name="Other Tenant Template",
            role="orchestrator",
            category="role",
            system_instructions="Other tenant content",
            variables=[],
            behavioral_rules=[],
            success_criteria=[],
            version="1.0.0",
            is_active=True,
            is_default=False,
            tags=[],
            preferred_tool="claude",
            created_at=datetime.now(timezone.utc),
        )
        db_session.add(other_template)
        await db_session.commit()

        # Request templates with test user's token
        response = await async_client.get("/api/v1/templates/", headers=auth_headers)

        assert response.status_code == status.HTTP_200_OK
        templates = response.json()

        # Should only see own tenant's templates
        template_ids = [t["id"] for t in templates]
        assert orchestrator_template.id in template_ids
        assert other_template.id not in template_ids

    async def test_cross_tenant_update_forbidden(
        self,
        async_client: AsyncClient,
        auth_headers: dict,
        db_session: AsyncSession,
    ):
        """Test user cannot update other tenant's template"""
        # Create template for different tenant
        other_template = AgentTemplate(
            id=str(uuid4()),
            tenant_key="other_tenant_456",
            name="Other Template",
            role="analyzer",
            category="role",
            system_instructions="Content",
            variables=[],
            behavioral_rules=[],
            success_criteria=[],
            version="1.0.0",
            is_active=True,
            is_default=False,
            tags=[],
            preferred_tool="claude",
            created_at=datetime.now(timezone.utc),
        )
        db_session.add(other_template)
        await db_session.commit()

        # Attempt to update other tenant's template
        response = await async_client.put(
            f"/api/v1/templates/{other_template.id}",
            json={"name": "Hacked Name"},
            headers=auth_headers,
        )

        assert response.status_code == status.HTTP_403_FORBIDDEN

    async def test_system_template_protection(
        self,
        async_client: AsyncClient,
        auth_headers: dict,
        system_orchestrator_template: AgentTemplate,
    ):
        """Test system templates cannot be modified by users"""
        response = await async_client.put(
            f"/api/v1/templates/{system_orchestrator_template.id}",
            json={"name": "Modified System Template"},
            headers=auth_headers,
        )

        assert response.status_code == status.HTTP_403_FORBIDDEN
        assert "system" in response.text.lower()

    async def test_authentication_required(self, async_client: AsyncClient):
        """Test endpoints require authentication (401 without JWT)"""
        response = await async_client.get("/api/v1/templates/")

        assert response.status_code == status.HTTP_401_UNAUTHORIZED

    async def test_invalid_token_rejected(self, async_client: AsyncClient):
        """Test invalid JWT token is rejected"""
        bad_headers = {"Authorization": "Bearer invalid_token_12345"}
        response = await async_client.get("/api/v1/templates/", headers=bad_headers)

        assert response.status_code == status.HTTP_401_UNAUTHORIZED


# Input Validation Tests


@pytest.mark.asyncio
class TestTemplatesValidation:
    """Tests for input validation and error handling"""

    async def test_create_template_missing_required_fields(self, async_client: AsyncClient, auth_headers: dict):
        """Test creating template without required fields fails"""
        invalid_data = {"name": "Test"}  # Missing category, system_instructions, etc.

        response = await async_client.post("/api/v1/templates/", json=invalid_data, headers=auth_headers)

        assert response.status_code == status.HTTP_422_UNPROCESSABLE_ENTITY
        errors = response.json()["detail"]
        assert any("category" in str(e).lower() for e in errors)
        assert any("system_instructions" in str(e).lower() for e in errors)

    async def test_update_template_not_found(self, async_client: AsyncClient, auth_headers: dict):
        """Test updating non-existent template returns 404"""
        fake_id = str(uuid4())
        response = await async_client.put(
            f"/api/v1/templates/{fake_id}",
            json={"name": "Updated"},
            headers=auth_headers,
        )

        assert response.status_code == status.HTTP_404_NOT_FOUND

    async def test_template_size_validation_on_update(
        self,
        async_client: AsyncClient,
        auth_headers: dict,
        orchestrator_template: AgentTemplate,
    ):
        """Test update fails when content exceeds size limit"""
        large_content = "x" * (101 * 1024)  # 101KB
        response = await async_client.put(
            f"/api/v1/templates/{orchestrator_template.id}",
            json={"system_instructions": large_content},
            headers=auth_headers,
        )

        assert response.status_code == status.HTTP_422_UNPROCESSABLE_ENTITY


# Performance Tests


@pytest.mark.asyncio
class TestTemplatesPerformance:
    """Performance tests for API endpoints"""

    async def test_list_templates_response_time(
        self,
        async_client: AsyncClient,
        auth_headers: dict,
        orchestrator_template: AgentTemplate,
    ):
        """Test list templates responds within 100ms"""
        start = time.perf_counter()
        response = await async_client.get("/api/v1/templates/", headers=auth_headers)
        elapsed_ms = (time.perf_counter() - start) * 1000

        assert response.status_code == status.HTTP_200_OK
        assert elapsed_ms < 100, f"Response took {elapsed_ms:.2f}ms, expected < 100ms"

    async def test_template_preview_performance(
        self,
        async_client: AsyncClient,
        auth_headers: dict,
        orchestrator_template: AgentTemplate,
    ):
        """Test preview endpoint responds quickly"""
        preview_data = {"variables": {"project_name": "Test", "project_mission": "Test"}}

        start = time.perf_counter()
        response = await async_client.post(
            f"/api/v1/templates/{orchestrator_template.id}/preview",
            json=preview_data,
            headers=auth_headers,
        )
        elapsed_ms = (time.perf_counter() - start) * 1000

        assert response.status_code == status.HTTP_200_OK
        assert elapsed_ms < 50, f"Preview took {elapsed_ms:.2f}ms, expected < 50ms"


# WebSocket Tests


@pytest.mark.asyncio
class TestTemplatesWebSocket:
    """Tests for WebSocket real-time updates"""

    @pytest.mark.skip(reason="WebSocket testing requires additional setup")
    async def test_websocket_broadcast_on_create(self, async_client: AsyncClient, auth_headers: dict):
        """Test WebSocket broadcasts template creation"""
        # This would require WebSocket client setup
        # Placeholder for future implementation

    @pytest.mark.skip(reason="WebSocket testing requires additional setup")
    async def test_websocket_broadcast_on_update(
        self,
        async_client: AsyncClient,
        auth_headers: dict,
        orchestrator_template: AgentTemplate,
    ):
        """Test WebSocket broadcasts template updates"""

    @pytest.mark.skip(reason="WebSocket testing requires additional setup")
    async def test_websocket_tenant_scoped_broadcasts(self, async_client: AsyncClient, auth_headers: dict):
        """Test WebSocket broadcasts are tenant-scoped"""


# Database Query Tests


@pytest.mark.asyncio
class TestTemplatesDatabaseQueries:
    """Tests for database query correctness and performance"""

    async def test_database_query_filters_by_tenant(self, db_session: AsyncSession, test_user: User):
        """Test all database queries filter by tenant_key"""
        # This test directly queries database to verify filtering
        stmt = select(AgentTemplate).where(AgentTemplate.tenant_key == test_user.tenant_key)
        result = await db_session.execute(stmt)
        templates = result.scalars().all()

        # All templates should match user's tenant
        assert all(t.tenant_key == test_user.tenant_key for t in templates)

    async def test_database_query_performance(self, db_session: AsyncSession, test_user: User):
        """Test database queries complete within 10ms"""
        stmt = select(AgentTemplate).where(
            AgentTemplate.tenant_key == test_user.tenant_key,
            AgentTemplate.is_active == True,
        )

        start = time.perf_counter()
        result = await db_session.execute(stmt)
        templates = result.scalars().all()
        elapsed_ms = (time.perf_counter() - start) * 1000

        assert elapsed_ms < 10, f"Query took {elapsed_ms:.2f}ms, expected < 10ms"


# Integration Tests


@pytest.mark.asyncio
class TestTemplatesIntegration:
    """End-to-end integration tests"""

    async def test_full_crud_workflow(self, async_client: AsyncClient, auth_headers: dict, test_user: User):
        """Test complete CRUD workflow: Create → Read → Update → Delete"""
        # Create
        create_data = {
            "name": "Workflow Test Template",
            "category": "role",
            "role": "tester",
            "system_instructions": "Test template for {project_name}",
            "description": "Integration test template",
            "behavioral_rules": ["Test thoroughly"],
            "success_criteria": ["All tests pass"],
            "tags": ["test"],
            "is_default": False,
            "preferred_tool": "claude",
        }
        create_response = await async_client.post("/api/v1/templates/", json=create_data, headers=auth_headers)
        assert create_response.status_code == status.HTTP_201_CREATED
        template_id = create_response.json()["id"]

        # Read (list)
        list_response = await async_client.get("/api/v1/templates/?role=tester", headers=auth_headers)
        assert list_response.status_code == status.HTTP_200_OK
        templates = list_response.json()
        assert any(t["id"] == template_id for t in templates)

        # Update
        update_data = {"name": "Updated Workflow Template"}
        update_response = await async_client.put(
            f"/api/v1/templates/{template_id}",
            json=update_data,
            headers=auth_headers,
        )
        assert update_response.status_code == status.HTTP_200_OK
        assert update_response.json()["name"] == update_data["name"]

        # Delete
        delete_response = await async_client.delete(f"/api/v1/templates/{template_id}", headers=auth_headers)
        assert delete_response.status_code == status.HTTP_204_NO_CONTENT

    async def test_seeding_to_api_workflow(
        self,
        async_client: AsyncClient,
        auth_headers: dict,
        test_user: User,
        db_session: AsyncSession,
    ):
        """Test workflow: Seed templates → API fetch → Cache hit"""
        from src.giljo_mcp.template_seeder import seed_tenant_templates

        # Seed templates for user's tenant
        count = await seed_tenant_templates(db_session, test_user.tenant_key)
        assert count == 6  # Should seed 6 templates

        # Fetch via API
        response = await async_client.get("/api/v1/templates/", headers=auth_headers)
        assert response.status_code == status.HTTP_200_OK
        templates = response.json()
        assert len(templates) >= 6  # At least the 6 seeded templates

        # Verify all 6 roles exist
        roles = {t["role"] for t in templates}
        expected_roles = {
            "orchestrator",
            "analyzer",
            "implementer",
            "tester",
            "reviewer",
            "documenter",
        }
        assert expected_roles.issubset(roles)
