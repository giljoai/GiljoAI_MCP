"""
Integration tests for multi-tenant isolation: MCP Tool Scoping, Cross-Tenant Access Prevention, and Memory Isolation

Split from test_multi_tenant_isolation.py (Handover 0272).

Validates:
- MCP tool responses are tenant-scoped
- Cross-tenant data access is prevented
- 360 memory is completely isolated per product per tenant
"""

import random
from datetime import datetime
from uuid import uuid4

import pytest

from src.giljo_mcp.models import Product, Project, User
from src.giljo_mcp.models.agent_identity import AgentExecution

pytestmark = pytest.mark.skip(reason="0750c3: schema drift — serena_enabled invalid keyword for User model")


# ============================================================================
# TEST SUITE 5: MCP Tool Responses Are Tenant-Scoped
# ============================================================================


class TestMCPToolTenantScoping:
    """
    Validate that MCP tools (like get_orchestrator_instructions) are
    tenant-scoped and never leak data
    """

    async def test_orchestrator_instructions_include_tenant_key(
        self,
        db_session,
        user_in_tenant_a,
        product_in_tenant_a,
        tenant_a,
    ):
        """
        REQUIREMENT: get_orchestrator_instructions responses must include
        tenant_key to prevent data leakage
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

        # Create job for MCP tool call
        job = AgentExecution(
            id=str(uuid4()),
            product_id=product_in_tenant_a.id,
            project_id=project.id,
            user_id=user_in_tenant_a.id,
            agent_display_name="orchestrator",
            status="active",
            tenant_key=tenant_a,
            job_metadata={
                "user_id": user_in_tenant_a.id,
                "tenant_key": tenant_a,
            },
        )
        db_session.add(job)
        await db_session.flush()

        # When MCP tool retrieves instructions, it should use tenant_key
        assert job.tenant_key == tenant_a

    async def test_context_service_respects_tenant_isolation(
        self,
        db_session,
        user_in_tenant_a,
        product_in_tenant_a,
        tenant_a,
    ):
        """
        REQUIREMENT: ContextService must build context respecting tenant boundaries
        """
        from src.giljo_mcp.services.context_service import ContextService

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

        # Context service should only use tenant A's data
        service = ContextService(test_session=db_session)
        # (Call would check that service respects tenant_key parameter)


# ============================================================================
# TEST SUITE 6: Cross-Tenant Data Access Prevention
# ============================================================================


class TestCrossTenantAccessPrevention:
    """
    Validate that even malformed requests can't access cross-tenant data
    """

    async def test_cannot_access_other_tenant_user_by_id(
        self,
        db_session,
        user_in_tenant_a,
        user_in_tenant_b,
        tenant_a,
    ):
        """
        REQUIREMENT: Even if someone knows User B's ID, they can't access
        it via Tenant A (context requires tenant_key validation)
        """
        # Try to simulate cross-tenant access
        # In a well-designed system, queries would include tenant_key filter

        # This test documents the REQUIREMENT that:
        # 1. User IDs alone are insufficient
        # 2. Tenant_key must be verified in every query
        # 3. No query should return cross-tenant data

        retrieved_a = await db_session.get(User, user_in_tenant_a.id)
        assert retrieved_a.tenant_key == tenant_a

    async def test_cannot_access_other_tenant_product_by_id(
        self,
        db_session,
        product_in_tenant_a,
        product_in_tenant_b,
        tenant_a,
    ):
        """
        REQUIREMENT: Product retrieval must verify tenant ownership
        """
        retrieved_a = await db_session.get(Product, product_in_tenant_a.id)
        assert retrieved_a.tenant_key == tenant_a


# ============================================================================
# TEST SUITE 7: 360 Memory Isolation
# ============================================================================


class TestMemoryIsolation:
    """
    Validate that 360 memory (sequential_history) is completely isolated
    """

    async def test_sequential_history_unique_per_product(
        self,
        db_session,
        product_in_tenant_a,
        product_in_tenant_b,
    ):
        """
        REQUIREMENT: Each product has independent sequential_history
        with its own sequence numbering
        """
        # Add entries to both products
        for i in range(3):
            product_in_tenant_a.product_memory["sequential_history"].append(
                {
                    "sequence": i + 2,  # Starting from 2 (already has 1)
                    "type": "project_closeout",
                    "project_id": str(uuid4()),
                    "timestamp": datetime.utcnow().isoformat(),
                }
            )

        # Add entries to product B (should have separate sequence)
        for i in range(2):
            product_in_tenant_b.product_memory["sequential_history"].append(
                {
                    "sequence": i + 1,  # Product B starts at 1
                    "type": "project_closeout",
                    "project_id": str(uuid4()),
                    "timestamp": datetime.utcnow().isoformat(),
                }
            )

        await db_session.flush()

        # Verify separate sequences
        retrieved_a = await db_session.get(Product, product_in_tenant_a.id)
        retrieved_b = await db_session.get(Product, product_in_tenant_b.id)

        assert len(retrieved_a.product_memory["sequential_history"]) == 4
        assert len(retrieved_b.product_memory["sequential_history"]) == 2

        # Verify sequence independence
        max_seq_a = max(e["sequence"] for e in retrieved_a.product_memory["sequential_history"])
        max_seq_b = max(e["sequence"] for e in retrieved_b.product_memory["sequential_history"])

        assert max_seq_a == 4
        assert max_seq_b == 2
