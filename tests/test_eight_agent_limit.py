"""
Test suite for Eight-Agent Active Limit Enforcement (Handover 0075)

Tests validate:
- 8-agent active limit enforcement
- Active count endpoint accuracy
- Multi-tenant isolation
- Validation logic for activate/deactivate
- Edge cases (8th activation succeeds, 9th blocked)
"""

import pytest
from sqlalchemy.ext.asyncio import AsyncSession

from src.giljo_mcp.database import DatabaseManager
from src.giljo_mcp.models import AgentTemplate, User
from src.giljo_mcp.services.template_service import TemplateService
from src.giljo_mcp.tenant import TenantManager


# Test Fixtures
@pytest.fixture
async def test_user(db_session: AsyncSession) -> User:
    """Create test user for authentication"""
    user = User(
        id="user-test-001",
        username="test_user",
        email="test@example.com",
        tenant_key="tenant-test-001",
        is_active=True,
        password_hash="test_hash",
    )
    db_session.add(user)
    await db_session.commit()
    await db_session.refresh(user)
    return user


@pytest.fixture
async def create_template(db_session: AsyncSession):
    """Factory fixture to create agent templates"""

    async def _create(tenant_key: str, name: str, is_active: bool = True, role: str = "implementor") -> AgentTemplate:
        template = AgentTemplate(
            id=f"tpl-{name}-{hash(name) % 1000:03d}",
            tenant_key=tenant_key,
            name=name,
            category="role",
            role=role,
            system_instructions=f"Template for {name}",
            variables=[],
            behavioral_rules=[],
            success_criteria=[],
            is_active=is_active,
            is_default=False,
            tool="claude",
        )
        db_session.add(template)
        await db_session.commit()
        await db_session.refresh(template)
        return template

    return _create


# Test validate_active_agent_limit() function
class TestValidateActiveAgentLimit:
    """Test suite for validate_active_agent_limit() validation function"""

    @pytest.mark.asyncio
    async def test_deactivation_always_allowed(self, db_session: AsyncSession, test_user: User, create_template):
        """Test: Deactivating an agent should always be allowed"""
        # Create 8 active templates
        for i in range(8):
            await create_template(test_user.tenant_key, f"agent-{i}", is_active=True)

        # Create TemplateService
        tenant_manager = TenantManager()
        tenant_manager.set_current_tenant(test_user.tenant_key)
        db_manager = DatabaseManager()  # Will use the session passed to validate method
        template_service = TemplateService(db_manager, tenant_manager)

        # Deactivation should always succeed
        valid, msg = await template_service.validate_active_agent_limit(
            session=db_session, tenant_key=test_user.tenant_key, template_id="tpl-agent-0-0", new_is_active=False
        )

        assert valid is True
        assert msg == ""

    @pytest.mark.asyncio
    async def test_activate_within_limit(self, db_session: AsyncSession, test_user: User, create_template):
        """Test: Activating 7th agent should succeed (within 8-agent limit)"""
        # Create 6 active templates
        for i in range(6):
            await create_template(test_user.tenant_key, f"agent-{i}", is_active=True)

        # Create 1 inactive template
        inactive = await create_template(test_user.tenant_key, "agent-inactive", is_active=False)

        # Create TemplateService
        tenant_manager = TenantManager()
        tenant_manager.set_current_tenant(test_user.tenant_key)
        db_manager = DatabaseManager()
        template_service = TemplateService(db_manager, tenant_manager)

        # Activating 7th agent should succeed (6 + 1 = 7 < 8)
        valid, msg = await template_service.validate_active_agent_limit(
            session=db_session, tenant_key=test_user.tenant_key, template_id=inactive.id, new_is_active=True
        )

        assert valid is True
        assert msg == ""

    @pytest.mark.asyncio
    async def test_activate_exactly_at_limit(self, db_session: AsyncSession, test_user: User, create_template):
        """Test: Activating 8th agent should succeed (exactly at limit)"""
        # Create 7 active templates
        for i in range(7):
            await create_template(test_user.tenant_key, f"agent-{i}", is_active=True)

        # Create 1 inactive template
        inactive = await create_template(test_user.tenant_key, "agent-8th", is_active=False)

        # Create TemplateService
        tenant_manager = TenantManager()
        tenant_manager.set_current_tenant(test_user.tenant_key)
        db_manager = DatabaseManager()
        template_service = TemplateService(db_manager, tenant_manager)

        # Activating 8th agent should succeed (7 + 1 = 8)
        valid, msg = await template_service.validate_active_agent_limit(
            session=db_session, tenant_key=test_user.tenant_key, template_id=inactive.id, new_is_active=True
        )

        assert valid is True
        assert msg == ""

    @pytest.mark.asyncio
    async def test_activate_exceeds_limit(self, db_session: AsyncSession, test_user: User, create_template):
        """Test: Activating 9th agent should fail (exceeds 8-agent limit)"""
        # Create 8 active templates
        for i in range(8):
            await create_template(test_user.tenant_key, f"agent-{i}", is_active=True)

        # Create 1 inactive template
        inactive = await create_template(test_user.tenant_key, "agent-9th", is_active=False)

        # Create TemplateService
        tenant_manager = TenantManager()
        tenant_manager.set_current_tenant(test_user.tenant_key)
        db_manager = DatabaseManager()
        template_service = TemplateService(db_manager, tenant_manager)

        # Activating 9th agent should FAIL
        valid, msg = await template_service.validate_active_agent_limit(
            session=db_session, tenant_key=test_user.tenant_key, template_id=inactive.id, new_is_active=True
        )

        assert valid is False
        assert "Maximum 7 active agent roles allowed" in msg
        assert "currently" in msg

    @pytest.mark.asyncio
    async def test_multi_tenant_isolation(self, db_session: AsyncSession, test_user: User, create_template):
        """Test: Agent limit enforced per tenant (multi-tenant isolation)"""
        # Tenant 1: Create 8 active templates
        for i in range(8):
            await create_template(test_user.tenant_key, f"t1-agent-{i}", is_active=True)

        # Tenant 2: Create 5 active templates (different tenant)
        tenant2_key = "tenant-test-002"
        for i in range(5):
            await create_template(tenant2_key, f"t2-agent-{i}", is_active=True)

        # Create inactive for tenant 2
        inactive_t2 = await create_template(tenant2_key, "t2-agent-inactive", is_active=False)

        # Create TemplateService
        tenant_manager = TenantManager()
        db_manager = DatabaseManager()
        template_service = TemplateService(db_manager, tenant_manager)

        # Tenant 2 should be able to activate (5 + 1 = 6 < 8)
        valid, msg = await template_service.validate_active_agent_limit(
            session=db_session, tenant_key=tenant2_key, template_id=inactive_t2.id, new_is_active=True
        )

        assert valid is True
        assert msg == ""

        # But tenant 1 should still be blocked
        inactive_t1 = await create_template(test_user.tenant_key, "t1-agent-inactive", is_active=False)

        valid_t1, msg_t1 = await template_service.validate_active_agent_limit(
            session=db_session, tenant_key=test_user.tenant_key, template_id=inactive_t1.id, new_is_active=True
        )

        assert valid_t1 is False
        assert "Maximum 8 active agents allowed" in msg_t1

    @pytest.mark.asyncio
    async def test_toggle_same_template_excluded(self, db_session: AsyncSession, test_user: User, create_template):
        """Test: Template being toggled is excluded from count"""
        # Create 7 active templates
        for i in range(7):
            await create_template(test_user.tenant_key, f"agent-{i}", is_active=True)

        # Create 1 active template that we'll toggle
        toggle_template = await create_template(test_user.tenant_key, "agent-toggle", is_active=True)

        # Create TemplateService
        tenant_manager = TenantManager()
        tenant_manager.set_current_tenant(test_user.tenant_key)
        db_manager = DatabaseManager()
        template_service = TemplateService(db_manager, tenant_manager)

        # Toggling existing active template to inactive should succeed
        # (count excludes template being toggled: 7 active others + 1 being toggled = 8 total)
        valid, msg = await template_service.validate_active_agent_limit(
            session=db_session, tenant_key=test_user.tenant_key, template_id=toggle_template.id, new_is_active=False
        )

        assert valid is True
        assert msg == ""


# Test GET /api/templates/stats/active-count endpoint
class TestActiveCountEndpoint:
    """Test suite for GET /api/templates/stats/active-count endpoint"""

    @pytest.mark.asyncio
    async def test_active_count_zero(self, client, test_user: User, auth_headers):
        """Test: Returns 0 active count when no templates exist"""
        response = await client.get("/api/templates/stats/active-count", headers=auth_headers)

        assert response.status_code == 200
        data = response.json()
        assert data["active_count"] == 0
        assert data["max_allowed"] == 8
        assert data["remaining_slots"] == 8

    @pytest.mark.asyncio
    async def test_active_count_six(self, client, test_user: User, auth_headers, create_template):
        """Test: Returns 6 active count for default seeded agents"""
        # Create 6 active templates (default configuration)
        for i in range(6):
            await create_template(test_user.tenant_key, f"agent-{i}", is_active=True)

        response = await client.get("/api/templates/stats/active-count", headers=auth_headers)

        assert response.status_code == 200
        data = response.json()
        assert data["active_count"] == 6
        assert data["max_allowed"] == 8
        assert data["remaining_slots"] == 2

    @pytest.mark.asyncio
    async def test_active_count_at_limit(self, client, test_user: User, auth_headers, create_template):
        """Test: Returns 8 active count when at limit"""
        # Create 8 active templates
        for i in range(8):
            await create_template(test_user.tenant_key, f"agent-{i}", is_active=True)

        response = await client.get("/api/templates/stats/active-count", headers=auth_headers)

        assert response.status_code == 200
        data = response.json()
        assert data["active_count"] == 8
        assert data["max_allowed"] == 8
        assert data["remaining_slots"] == 0

    @pytest.mark.asyncio
    async def test_active_count_mixed_active_inactive(self, client, test_user: User, auth_headers, create_template):
        """Test: Only counts is_active=True templates"""
        # Create 5 active, 3 inactive
        for i in range(5):
            await create_template(test_user.tenant_key, f"active-{i}", is_active=True)

        for i in range(3):
            await create_template(test_user.tenant_key, f"inactive-{i}", is_active=False)

        response = await client.get("/api/templates/stats/active-count", headers=auth_headers)

        assert response.status_code == 200
        data = response.json()
        assert data["active_count"] == 5
        assert data["remaining_slots"] == 3

    @pytest.mark.asyncio
    async def test_active_count_tenant_isolation(
        self, client, test_user: User, auth_headers, create_template, db_session: AsyncSession
    ):
        """Test: Active count respects multi-tenant isolation"""
        # Tenant 1: 6 active templates
        for i in range(6):
            await create_template(test_user.tenant_key, f"t1-agent-{i}", is_active=True)

        # Tenant 2: 8 active templates (different tenant)
        tenant2_key = "tenant-test-002"
        for i in range(8):
            await create_template(tenant2_key, f"t2-agent-{i}", is_active=True)

        # Should only see tenant 1's count
        response = await client.get("/api/templates/stats/active-count", headers=auth_headers)

        assert response.status_code == 200
        data = response.json()
        assert data["active_count"] == 6  # Only tenant 1's templates
        assert data["remaining_slots"] == 2


# Test PATCH endpoint with validation integration
class TestUpdateTemplateWithValidation:
    """Test suite for PATCH /api/templates/{id} with 8-agent validation"""

    @pytest.mark.asyncio
    async def test_activate_within_limit_succeeds(self, client, test_user: User, auth_headers, create_template):
        """Test: Activating agent within limit succeeds"""
        # Create 6 active templates
        for i in range(6):
            await create_template(test_user.tenant_key, f"agent-{i}", is_active=True)

        # Create 1 inactive template
        inactive = await create_template(test_user.tenant_key, "agent-inactive", is_active=False)

        # Activate the inactive template (6 + 1 = 7 < 8)
        response = await client.put(f"/api/templates/{inactive.id}", headers=auth_headers, json={"is_active": True})

        assert response.status_code == 200
        data = response.json()
        assert data["is_active"] is True

    @pytest.mark.asyncio
    async def test_activate_8th_agent_succeeds(self, client, test_user: User, auth_headers, create_template):
        """Test: Activating exactly 8th agent succeeds"""
        # Create 7 active templates
        for i in range(7):
            await create_template(test_user.tenant_key, f"agent-{i}", is_active=True)

        # Create 1 inactive template
        inactive = await create_template(test_user.tenant_key, "agent-8th", is_active=False)

        # Activate 8th agent (7 + 1 = 8)
        response = await client.put(f"/api/templates/{inactive.id}", headers=auth_headers, json={"is_active": True})

        assert response.status_code == 200
        data = response.json()
        assert data["is_active"] is True

    @pytest.mark.asyncio
    async def test_activate_9th_agent_blocked(self, client, test_user: User, auth_headers, create_template):
        """Test: Activating 9th agent returns 400 error"""
        # Create 8 active templates
        for i in range(8):
            await create_template(test_user.tenant_key, f"agent-{i}", is_active=True)

        # Create 1 inactive template
        inactive = await create_template(test_user.tenant_key, "agent-9th", is_active=False)

        # Attempt to activate 9th agent
        response = await client.put(f"/api/templates/{inactive.id}", headers=auth_headers, json={"is_active": True})

        assert response.status_code == 400
        error_detail = response.json()["detail"]
        assert "Maximum 8 active agents allowed" in error_detail
        assert "currently 8 active" in error_detail
        assert "Claude Code context budget limit" in error_detail

    @pytest.mark.asyncio
    async def test_deactivate_always_succeeds(self, client, test_user: User, auth_headers, create_template):
        """Test: Deactivating agent always succeeds regardless of count"""
        # Create 8 active templates
        templates = []
        for i in range(8):
            template = await create_template(test_user.tenant_key, f"agent-{i}", is_active=True)
            templates.append(template)

        # Deactivate one agent
        response = await client.put(
            f"/api/templates/{templates[0].id}", headers=auth_headers, json={"is_active": False}
        )

        assert response.status_code == 200
        data = response.json()
        assert data["is_active"] is False

    @pytest.mark.asyncio
    async def test_update_other_fields_no_validation(self, client, test_user: User, auth_headers, create_template):
        """Test: Updating fields other than is_active skips validation"""
        # Create 8 active templates
        for i in range(8):
            await create_template(test_user.tenant_key, f"agent-{i}", is_active=True)

        # Create 1 more active template (shouldn't happen but test edge case)
        template = await create_template(test_user.tenant_key, "agent-update", is_active=True)

        # Update description only (no is_active change)
        response = await client.put(
            f"/api/templates/{template.id}", headers=auth_headers, json={"description": "Updated description"}
        )

        assert response.status_code == 200
        data = response.json()
        assert data["description"] == "Updated description"

    @pytest.mark.asyncio
    async def test_toggle_inactive_to_active_exceeds_limit(
        self, client, test_user: User, auth_headers, create_template
    ):
        """Test: Toggling from inactive to active respects limit"""
        # Create 8 active + 2 inactive
        for i in range(8):
            await create_template(test_user.tenant_key, f"active-{i}", is_active=True)

        inactive1 = await create_template(test_user.tenant_key, "inactive-1", is_active=False)
        inactive2 = await create_template(test_user.tenant_key, "inactive-2", is_active=False)

        # First inactive activation should fail (8 + 1 = 9)
        response1 = await client.put(f"/api/templates/{inactive1.id}", headers=auth_headers, json={"is_active": True})

        assert response1.status_code == 400

        # Second should also fail
        response2 = await client.put(f"/api/templates/{inactive2.id}", headers=auth_headers, json={"is_active": True})

        assert response2.status_code == 400
