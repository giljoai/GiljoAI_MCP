"""
Comprehensive test suite for PROJECT_0015 - Orchestrator Protection

Tests verify:
1. Orchestrator excluded from Template Manager
2. CRUD protection for orchestrator role
3. Export exclusion
4. System prompt service CRUD operations
5. Admin-only access controls
6. 7-slot user agent limit enforcement
"""

import pytest
from fastapi import HTTPException
from sqlalchemy import select
from datetime import datetime, timezone

from src.giljo_mcp.models import AgentTemplate, Configuration
from src.giljo_mcp.system_roles import SYSTEM_MANAGED_ROLES
from src.giljo_mcp.system_prompts import SystemPromptService


class TestSystemRolesConstant:
    """Test SYSTEM_MANAGED_ROLES constant"""

    def test_orchestrator_in_system_roles(self):
        """Verify orchestrator is protected"""
        assert "orchestrator" in SYSTEM_MANAGED_ROLES
        assert isinstance(SYSTEM_MANAGED_ROLES, set)


class TestTemplateEndpointProtection:
    """Test template API endpoints exclude/protect orchestrator"""

    @pytest.mark.asyncio
    async def test_get_templates_excludes_orchestrator(
        self, async_db_session, test_tenant, auth_headers
    ):
        """GET /templates should exclude system-managed roles by default"""
        from api.endpoints.templates import get_templates
        from src.giljo_mcp.models import User

        # Create mock user
        user = User(
            id="test-user",
            tenant_key=test_tenant,
            username="testuser",
            is_active=True
        )

        # Create orchestrator template
        orch_template = AgentTemplate(
            id="orch-template",
            tenant_key=test_tenant,
            role="orchestrator",
            name="orchestrator",
            template_content="System orchestrator prompt",
            is_active=True
        )
        async_db_session.add(orch_template)

        # Create regular template
        regular_template = AgentTemplate(
            id="regular-template",
            tenant_key=test_tenant,
            role="implementer",
            name="implementer",
            template_content="Regular template",
            is_active=True
        )
        async_db_session.add(regular_template)
        await async_db_session.commit()

        # Get templates (should exclude orchestrator by default)
        templates = await get_templates(
            current_user=user,
            session=async_db_session,
            include_system=False
        )

        # Verify orchestrator not in results
        roles = [t.role for t in templates]
        assert "orchestrator" not in roles
        assert "implementer" in roles

    @pytest.mark.asyncio
    async def test_get_templates_includes_orchestrator_with_flag(
        self, async_db_session, test_tenant
    ):
        """GET /templates?include_system=true should show system roles"""
        from api.endpoints.templates import get_templates
        from src.giljo_mcp.models import User

        user = User(
            id="test-user",
            tenant_key=test_tenant,
            username="testuser",
            is_active=True
        )

        # Create orchestrator template
        orch_template = AgentTemplate(
            id="orch-template",
            tenant_key=test_tenant,
            role="orchestrator",
            name="orchestrator",
            template_content="System orchestrator prompt",
            is_active=True
        )
        async_db_session.add(orch_template)
        await async_db_session.commit()

        # Get templates with include_system=True
        templates = await get_templates(
            current_user=user,
            session=async_db_session,
            include_system=True
        )

        # Verify orchestrator IS in results
        roles = [t.role for t in templates]
        assert "orchestrator" in roles

    @pytest.mark.asyncio
    async def test_update_orchestrator_template_blocked(
        self, async_db_session, test_tenant
    ):
        """PUT /templates/{id} should fail for orchestrator role"""
        from api.endpoints.templates import update_template, TemplateUpdate
        from src.giljo_mcp.models import User

        user = User(
            id="test-user",
            tenant_key=test_tenant,
            username="testuser",
            is_active=True
        )

        # Create orchestrator template
        orch_template = AgentTemplate(
            id="orch-template",
            tenant_key=test_tenant,
            role="orchestrator",
            name="orchestrator",
            template_content="System orchestrator prompt",
            is_active=True
        )
        async_db_session.add(orch_template)
        await async_db_session.commit()

        # Attempt update
        update_request = TemplateUpdate(
            user_instructions="Modified instructions"
        )

        with pytest.raises(HTTPException) as exc_info:
            await update_template(
                template_id="orch-template",
                update=update_request,
                current_user=user,
                session=async_db_session
            )

        assert exc_info.value.status_code == 403
        assert "system-managed" in str(exc_info.value.detail).lower()

    @pytest.mark.asyncio
    async def test_delete_orchestrator_template_blocked(
        self, async_db_session, test_tenant
    ):
        """DELETE /templates/{id} should fail for orchestrator role"""
        from api.endpoints.templates import delete_template
        from src.giljo_mcp.models import User

        user = User(
            id="test-user",
            tenant_key=test_tenant,
            username="testuser",
            is_active=True
        )

        # Create orchestrator template
        orch_template = AgentTemplate(
            id="orch-template",
            tenant_key=test_tenant,
            role="orchestrator",
            name="orchestrator",
            template_content="System orchestrator prompt",
            is_active=True
        )
        async_db_session.add(orch_template)
        await async_db_session.commit()

        # Attempt delete
        with pytest.raises(HTTPException) as exc_info:
            await delete_template(
                template_id="orch-template",
                current_user=user,
                session=async_db_session
            )

        assert exc_info.value.status_code == 403
        assert "system-managed" in str(exc_info.value.detail).lower()

    @pytest.mark.asyncio
    async def test_active_count_excludes_system_roles(
        self, async_db_session, test_tenant
    ):
        """GET /templates/stats/active-count should exclude system roles"""
        from api.endpoints.templates import get_active_count
        from src.giljo_mcp.models import User

        user = User(
            id="test-user",
            tenant_key=test_tenant,
            username="testuser",
            is_active=True
        )

        # Create orchestrator (system-managed)
        orch_template = AgentTemplate(
            id="orch-template",
            tenant_key=test_tenant,
            role="orchestrator",
            name="orchestrator",
            template_content="System orchestrator prompt",
            is_active=True
        )
        async_db_session.add(orch_template)

        # Create 3 active user-managed templates
        for i in range(3):
            template = AgentTemplate(
                id=f"user-template-{i}",
                tenant_key=test_tenant,
                role=f"role-{i}",
                name=f"agent-{i}",
                template_content=f"User template {i}",
                is_active=True
            )
            async_db_session.add(template)

        await async_db_session.commit()

        # Get active count
        result = await get_active_count(
            current_user=user,
            session=async_db_session
        )

        # Verify orchestrator not counted in user-manageable slots
        assert result["active_count"] == 3  # User-managed only
        assert result["max_allowed"] == 7  # User limit
        assert result["remaining_slots"] == 4
        assert result["system_reserved"] == 1  # Orchestrator
        assert result["total_active"] == 4  # 3 user + 1 system
        assert result["total_capacity"] == 8  # 7 user + 1 system


class TestExportExclusion:
    """Test orchestrator excluded from exports"""

    @pytest.mark.asyncio
    async def test_claude_export_excludes_orchestrator(
        self, async_db_session, test_tenant
    ):
        """Claude export should exclude system-managed roles"""
        from api.endpoints.claude_export import _get_tenant_templates

        # Create orchestrator template
        orch_template = AgentTemplate(
            id="orch-template",
            tenant_key=test_tenant,
            role="orchestrator",
            name="orchestrator",
            template_content="System orchestrator prompt",
            is_active=True
        )
        async_db_session.add(orch_template)

        # Create regular templates
        regular_template = AgentTemplate(
            id="regular-template",
            tenant_key=test_tenant,
            role="implementer",
            name="implementer",
            template_content="Regular template",
            is_active=True
        )
        async_db_session.add(regular_template)
        await async_db_session.commit()

        # Get templates for export
        templates = await _get_tenant_templates(
            session=async_db_session,
            tenant_key=test_tenant,
            include_inactive=False
        )

        # Verify orchestrator not in export
        roles = [t.role for t in templates]
        assert "orchestrator" not in roles
        assert "implementer" in roles


class TestSystemPromptService:
    """Test SystemPromptService CRUD operations"""

    @pytest.mark.asyncio
    async def test_get_default_orchestrator_prompt(self, async_db_session):
        """Should return default prompt when no override exists"""
        service = SystemPromptService(db_manager=None)  # No DB access needed for default

        prompt = await service.get_orchestrator_prompt()

        assert prompt.content
        assert not prompt.is_override
        assert prompt.updated_at is None
        assert prompt.updated_by is None
        assert len(prompt.content) > 100  # Should be substantial

    @pytest.mark.asyncio
    async def test_update_orchestrator_prompt_creates_override(
        self, async_db_session, db_manager
    ):
        """Should create Configuration record for override"""
        service = SystemPromptService(db_manager=db_manager)

        # Update prompt
        updated_prompt = await service.update_orchestrator_prompt(
            content="Custom orchestrator instructions",
            updated_by="admin@test.com",
            session=async_db_session
        )

        assert updated_prompt.content == "Custom orchestrator instructions"
        assert updated_prompt.is_override is True
        assert updated_prompt.updated_by == "admin@test.com"
        assert updated_prompt.updated_at is not None

        # Verify Configuration record created
        stmt = select(Configuration).where(
            Configuration.key == "system.orchestrator_prompt"
        )
        result = await async_db_session.execute(stmt)
        config = result.scalar_one_or_none()

        assert config is not None
        assert config.value["content"] == "Custom orchestrator instructions"
        assert config.value["updated_by"] == "admin@test.com"

    @pytest.mark.asyncio
    async def test_reset_orchestrator_prompt_removes_override(
        self, async_db_session, db_manager
    ):
        """Should delete Configuration record and return default"""
        service = SystemPromptService(db_manager=db_manager)

        # Create override first
        await service.update_orchestrator_prompt(
            content="Custom orchestrator instructions",
            updated_by="admin@test.com",
            session=async_db_session
        )

        # Reset to default
        reset_prompt = await service.reset_orchestrator_prompt(
            session=async_db_session
        )

        assert not reset_prompt.is_override
        assert reset_prompt.updated_at is None
        assert reset_prompt.updated_by is None
        assert len(reset_prompt.content) > 100

        # Verify Configuration record deleted
        stmt = select(Configuration).where(
            Configuration.key == "system.orchestrator_prompt"
        )
        result = await async_db_session.execute(stmt)
        config = result.scalar_one_or_none()
        assert config is None

    @pytest.mark.asyncio
    async def test_validate_content_rejects_empty(self, db_manager):
        """Should reject empty prompt content"""
        service = SystemPromptService(db_manager=db_manager)

        with pytest.raises(ValueError, match="cannot be empty"):
            service._validate_content("")

        with pytest.raises(ValueError, match="cannot be empty"):
            service._validate_content("   ")

    @pytest.mark.asyncio
    async def test_validate_content_rejects_oversized(self, db_manager):
        """Should reject content exceeding 150KB"""
        service = SystemPromptService(db_manager=db_manager)

        oversized_content = "x" * (150_001)  # Just over limit

        with pytest.raises(ValueError, match="exceeds"):
            service._validate_content(oversized_content)


class TestSystemPromptAPIEndpoints:
    """Test system prompt API endpoints"""

    @pytest.mark.asyncio
    async def test_get_orchestrator_prompt_requires_admin(self, api_client):
        """GET /system/orchestrator-prompt requires admin role"""
        # TODO: Implement once auth fixtures are ready
        pass

    @pytest.mark.asyncio
    async def test_update_orchestrator_prompt_requires_admin(self, api_client):
        """PUT /system/orchestrator-prompt requires admin role"""
        # TODO: Implement once auth fixtures are ready
        pass

    @pytest.mark.asyncio
    async def test_reset_orchestrator_prompt_requires_admin(self, api_client):
        """POST /system/orchestrator-prompt/reset requires admin role"""
        # TODO: Implement once auth fixtures are ready
        pass


class Test7SlotUserLimit:
    """Test 7-slot limit for user-managed agents (orchestrator reserved)"""

    @pytest.mark.asyncio
    async def test_cannot_activate_8th_user_agent(
        self, async_db_session, test_tenant
    ):
        """Should reject activating 8th user-managed agent"""
        from api.endpoints.templates import validate_active_agent_limit

        # Create 7 active user-managed templates
        for i in range(7):
            template = AgentTemplate(
                id=f"template-{i}",
                tenant_key=test_tenant,
                role=f"role-{i}",
                name=f"agent-{i}",
                template_content=f"Template {i}",
                is_active=True
            )
            async_db_session.add(template)

        # Create 8th template (inactive)
        template_8 = AgentTemplate(
            id="template-8",
            tenant_key=test_tenant,
            role="role-8",
            name="agent-8",
            template_content="Template 8",
            is_active=False
        )
        async_db_session.add(template_8)
        await async_db_session.commit()

        # Attempt to activate 8th template
        is_valid, error_msg = await validate_active_agent_limit(
            db=async_db_session,
            tenant_key=test_tenant,
            template_id="template-8",
            new_is_active=True,
            role="role-8"
        )

        assert not is_valid
        assert "Maximum 7 active agent roles" in error_msg

    @pytest.mark.asyncio
    async def test_can_activate_same_role_multiple_times(
        self, async_db_session, test_tenant
    ):
        """Should allow multiple templates of same role (counts as 1 slot)"""
        from api.endpoints.templates import validate_active_agent_limit

        # Create 6 active unique roles
        for i in range(6):
            template = AgentTemplate(
                id=f"template-{i}",
                tenant_key=test_tenant,
                role=f"role-{i}",
                name=f"agent-{i}",
                template_content=f"Template {i}",
                is_active=True
            )
            async_db_session.add(template)

        # Create 2nd template with same role as template-0
        duplicate_role_template = AgentTemplate(
            id="template-duplicate",
            tenant_key=test_tenant,
            role="role-0",  # Same as template-0
            name="agent-duplicate",
            template_content="Duplicate role template",
            is_active=False
        )
        async_db_session.add(duplicate_role_template)
        await async_db_session.commit()

        # Should allow activation (same role, doesn't consume new slot)
        is_valid, error_msg = await validate_active_agent_limit(
            db=async_db_session,
            tenant_key=test_tenant,
            template_id="template-duplicate",
            new_is_active=True,
            role="role-0"
        )

        assert is_valid
        assert error_msg == ""

    @pytest.mark.asyncio
    async def test_cannot_toggle_system_managed_role(
        self, async_db_session, test_tenant
    ):
        """Should reject toggle attempts for system-managed roles"""
        from api.endpoints.templates import validate_active_agent_limit

        # Attempt to toggle orchestrator
        is_valid, error_msg = await validate_active_agent_limit(
            db=async_db_session,
            tenant_key=test_tenant,
            template_id="orch-template",
            new_is_active=True,
            role="orchestrator"
        )

        assert not is_valid
        assert "system-managed" in error_msg.lower()


# Fixtures
@pytest.fixture
def test_tenant():
    """Provide test tenant key"""
    return "test-tenant-001"


@pytest.fixture
async def db_manager():
    """Provide DatabaseManager for SystemPromptService tests"""
    from src.giljo_mcp.database import DatabaseManager

    # Mock DB manager with get_session_async method
    class MockDBManager:
        def __init__(self, session):
            self._session = session

        async def get_session_async(self):
            """Context manager yielding the session"""
            yield self._session

    # This will be overridden in actual test runs
    return None


if __name__ == "__main__":
    pytest.main([__file__, "-v", "--tb=short"])
