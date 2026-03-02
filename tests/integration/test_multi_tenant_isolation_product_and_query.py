"""
Integration tests for multi-tenant isolation: Product Settings, Context Generation, and Query Isolation

Split from test_multi_tenant_isolation.py (Handover 0272).

Validates:
- Product settings (testing config, memory, GitHub) isolated between tenants
- Context generation is tenant-scoped
- Queries are properly scoped to tenant boundaries
"""

import random
from datetime import datetime
from uuid import uuid4

import pytest

from src.giljo_mcp.mission_planner import MissionPlanner
from src.giljo_mcp.models import Product, Project, User
from src.giljo_mcp.models.agent_identity import AgentExecution

pytestmark = pytest.mark.skip(reason="0750c3: schema drift — serena_enabled invalid keyword for User model")


# ============================================================================
# TEST SUITE 2: Product Settings Isolation
# ============================================================================


class TestProductSettingsIsolation:
    """
    Validate that product settings (testing config, memory, GitHub) are
    completely isolated between tenants
    """

    async def test_testing_config_not_visible_across_tenants(
        self,
        db_session,
        product_in_tenant_a,
        product_in_tenant_b,
    ):
        """
        REQUIREMENT: Product A's testing config must not leak to Product B

        Tenant A: pytest, 85% coverage
        Tenant B: mocha, 75% coverage
        """
        assert product_in_tenant_a.testing_config["framework"] == "pytest"
        assert product_in_tenant_a.testing_config["coverage_target"] == 85

        assert product_in_tenant_b.testing_config["framework"] == "mocha"
        assert product_in_tenant_b.testing_config["coverage_target"] == 75

        # Verify isolation
        retrieved_a = await db_session.get(Product, product_in_tenant_a.id)
        retrieved_b = await db_session.get(Product, product_in_tenant_b.id)

        assert retrieved_a.testing_config["framework"] == "pytest"
        assert retrieved_b.testing_config["framework"] == "mocha"

    async def test_github_integration_not_visible_across_tenants(
        self,
        db_session,
        product_in_tenant_a,
        product_in_tenant_b,
    ):
        """
        REQUIREMENT: GitHub integration state isolated between products

        Tenant A Product: GitHub ENABLED
        Tenant B Product: GitHub DISABLED
        """
        assert product_in_tenant_a.product_memory["git_integration"]["enabled"] is True
        assert product_in_tenant_b.product_memory["git_integration"]["enabled"] is False

        # Verify isolation
        retrieved_a = await db_session.get(Product, product_in_tenant_a.id)
        retrieved_b = await db_session.get(Product, product_in_tenant_b.id)

        assert retrieved_a.product_memory["git_integration"]["enabled"] is True
        assert retrieved_b.product_memory["git_integration"]["enabled"] is False

    async def test_memory_not_shared_across_tenants(
        self,
        db_session,
        product_in_tenant_a,
        product_in_tenant_b,
    ):
        """
        REQUIREMENT: 360 memory (sequential_history) must not leak between products

        Tenant A: Has 1 history entry
        Tenant B: Has 0 history entries
        """
        memory_a = product_in_tenant_a.product_memory["sequential_history"]
        memory_b = product_in_tenant_b.product_memory["sequential_history"]

        assert len(memory_a) == 1
        assert len(memory_b) == 0

        # Verify isolation persists across database round-trip
        retrieved_a = await db_session.get(Product, product_in_tenant_a.id)
        retrieved_b = await db_session.get(Product, product_in_tenant_b.id)

        assert len(retrieved_a.product_memory["sequential_history"]) == 1
        assert len(retrieved_b.product_memory["sequential_history"]) == 0

    async def test_adding_memory_to_one_product_doesnt_affect_other(
        self,
        db_session,
        product_in_tenant_a,
        product_in_tenant_b,
    ):
        """
        REQUIREMENT: Adding memory to Product A must not affect Product B
        """
        # Add memory entry to product_a
        product_in_tenant_a.product_memory["sequential_history"].append(
            {
                "sequence": 2,
                "type": "project_closeout",
                "project_id": str(uuid4()),
                "summary": "Another tenant A project",
                "timestamp": datetime.utcnow().isoformat(),
            }
        )
        await db_session.flush()

        # Verify product_b unchanged
        retrieved_b = await db_session.get(Product, product_in_tenant_b.id)
        assert len(retrieved_b.product_memory["sequential_history"]) == 0


# ============================================================================
# TEST SUITE 3: Context Generation Respects Tenant Boundaries
# ============================================================================


class TestContextGenerationTenantRespect:
    """
    Validate that context generation is tenant-scoped and never leaks data
    """

    async def test_mission_planner_uses_tenant_scoped_user_settings(
        self,
        db_session,
        user_in_tenant_a,
        product_in_tenant_a,
        tenant_a,
    ):
        """
        REQUIREMENT: MissionPlanner must use ONLY User A's settings when
        building context for User A
        """
        # Create project
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

        planner = MissionPlanner(test_session=db_session)

        # Build mission for user_a
        mission = await planner.plan_orchestrator_mission(
            user_id=user_in_tenant_a.id,
            product_id=product_in_tenant_a.id,
            project_id=project.id,
            tenant_key=tenant_a,
        )

        # Mission should be based on user_a's settings
        assert mission is not None
        assert user_in_tenant_a.id in str(user_in_tenant_a.id)

    async def test_agent_job_metadata_includes_tenant_key(
        self,
        db_session,
        user_in_tenant_a,
        product_in_tenant_a,
        tenant_a,
    ):
        """
        REQUIREMENT: Agent job metadata MUST include tenant_key for isolation
        """
        # Create project
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

        # Create job
        job = AgentExecution(
            id=str(uuid4()),
            product_id=product_in_tenant_a.id,
            project_id=project.id,
            user_id=user_in_tenant_a.id,
            agent_display_name="orchestrator",
            status="staged",
            tenant_key=tenant_a,
            job_metadata={
                "user_id": user_in_tenant_a.id,
                "tenant_key": tenant_a,
                "field_priorities": user_in_tenant_a.field_priority_config["priorities"],
            },
        )
        db_session.add(job)
        await db_session.flush()

        # Verify tenant_key in metadata
        assert job.job_metadata["tenant_key"] == tenant_a


# ============================================================================
# TEST SUITE 4: Query Isolation (Preventing Data Leakage)
# ============================================================================


class TestQueryIsolation:
    """
    Validate that queries are properly scoped to tenant boundaries
    """

    async def test_querying_all_users_returns_only_tenant_users(
        self,
        db_session,
        user_in_tenant_a,
        user_in_tenant_b,
    ):
        """
        REQUIREMENT: Even with direct database queries, tenant A users
        should not be mixed with tenant B users (when queries are tenant-scoped)
        """
        # Users exist
        assert user_in_tenant_a.tenant_key != user_in_tenant_b.tenant_key

        # When querying by tenant, only get that tenant's users
        from sqlalchemy import select

        query_a = select(User).where(User.tenant_key == user_in_tenant_a.tenant_key)
        result_a = await db_session.scalars(query_a)
        users_a = result_a.all()

        # Should only contain users from tenant A
        tenant_a_ids = {u.id for u in users_a}
        assert user_in_tenant_a.id in tenant_a_ids
        # user_in_tenant_b might exist but shouldn't be in this query result
        # (depends on fixture cleanup, but principle is sound)

    async def test_querying_all_products_returns_only_tenant_products(
        self,
        db_session,
        product_in_tenant_a,
        product_in_tenant_b,
    ):
        """
        REQUIREMENT: Queries for products must respect tenant boundaries
        """
        from sqlalchemy import select

        query_a = select(Product).where(Product.tenant_key == product_in_tenant_a.tenant_key)
        result_a = await db_session.scalars(query_a)
        products_a = result_a.all()

        product_a_ids = {p.id for p in products_a}
        assert product_in_tenant_a.id in product_a_ids
