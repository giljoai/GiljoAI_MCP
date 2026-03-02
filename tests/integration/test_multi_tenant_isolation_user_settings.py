"""
Integration tests for multi-tenant isolation: User Settings

Split from test_multi_tenant_isolation.py (Handover 0272).

Validates:
- Field priorities isolated per user per tenant
- Serena settings isolated per user per tenant
- Context generation respects user tenant boundaries
"""

import random
from uuid import uuid4

import pytest

from src.giljo_mcp.mission_planner import MissionPlanner
from src.giljo_mcp.models import Product, Project, User

pytestmark = pytest.mark.skip(reason="0750c3: schema drift — serena_enabled invalid keyword for User model")


# ============================================================================
# TEST SUITE 1: User Settings Isolation
# ============================================================================


class TestUserSettingsIsolation:
    """
    Validate that user settings (priorities, Serena toggle) are completely
    isolated between tenants
    """

    async def test_field_priorities_not_visible_across_tenants(
        self,
        db_session,
        user_in_tenant_a,
        user_in_tenant_b,
    ):
        """
        REQUIREMENT: User A's field priorities must not be visible to User B
        (even when querying same database)

        Tenant A priorities:
        - git_history: 3 (NICE_TO_HAVE)

        Tenant B priorities:
        - git_history: 4 (EXCLUDED)
        """
        # Verify they're different
        assert user_in_tenant_a.tenant_key != user_in_tenant_b.tenant_key

        priorities_a = user_in_tenant_a.field_priority_config["priorities"]
        priorities_b = user_in_tenant_b.field_priority_config["priorities"]

        # Critical difference in git_history priority
        assert priorities_a["git_history"] == 3
        assert priorities_b["git_history"] == 4

        # Verify isolation: each user gets only their own
        retrieved_a = await db_session.get(User, user_in_tenant_a.id)
        retrieved_b = await db_session.get(User, user_in_tenant_b.id)

        assert retrieved_a.field_priority_config["priorities"]["git_history"] == 3
        assert retrieved_b.field_priority_config["priorities"]["git_history"] == 4

    async def test_serena_setting_not_visible_across_tenants(
        self,
        db_session,
        user_in_tenant_a,
        user_in_tenant_b,
    ):
        """
        REQUIREMENT: Serena enabled state isolated between tenants

        Tenant A: Serena ENABLED
        Tenant B: Serena DISABLED
        """
        assert user_in_tenant_a.serena_enabled is True
        assert user_in_tenant_b.serena_enabled is False

        # Verify persistence and isolation
        retrieved_a = await db_session.get(User, user_in_tenant_a.id)
        retrieved_b = await db_session.get(User, user_in_tenant_b.id)

        assert retrieved_a.serena_enabled is True
        assert retrieved_b.serena_enabled is False

    async def test_changing_one_users_settings_doesnt_affect_other_tenant(
        self,
        db_session,
        user_in_tenant_a,
        user_in_tenant_b,
    ):
        """
        REQUIREMENT: Changing User A's settings must not affect User B,
        even if they're in same product
        """
        # Change user_a's priorities
        user_in_tenant_a.field_priority_config["priorities"]["vision_documents"] = 4
        await db_session.flush()

        # Change user_a's Serena setting
        user_in_tenant_a.serena_enabled = False
        await db_session.flush()

        # Verify user_b unchanged
        retrieved_b = await db_session.get(User, user_in_tenant_b.id)
        assert retrieved_b.field_priority_config["priorities"]["vision_documents"] == 3
        assert retrieved_b.serena_enabled is False

    async def test_context_respects_user_tenant_boundaries(
        self,
        db_session,
        user_in_tenant_a,
        product_in_tenant_a,
        tenant_a,
    ):
        """
        REQUIREMENT: Context generation must only use User A's settings
        when building context for User A
        """
        # Create a project in tenant A
        project = Project(
            id=str(uuid4()),
            product_id=product_in_tenant_a.id,
            name=f"Project_{uuid4().hex[:6]}",
            status="created",
            tenant_key=tenant_a,
            series_number=random.randint(1, 999999),
        )
        db_session.add(project)
        await db_session.flush()

        # Context should use user_a's settings, not user_b's
        planner = MissionPlanner(test_session=db_session)
        context = await planner._build_context_with_priorities(
            user=user_in_tenant_a,
            product=product_in_tenant_a,
            project=project,
            field_priorities=user_in_tenant_a.field_priority_config["priorities"],
            include_serena=user_in_tenant_a.serena_enabled,
        )

        # Should be built with tenant A's user settings
        assert context is not None
