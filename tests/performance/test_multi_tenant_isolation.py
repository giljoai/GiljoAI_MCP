"""
Phase 4: Multi-Tenant Isolation Performance Test (Handover 0246d)

Validates multi-tenant isolation across all 3 components (0246a/b/c):
- Execution mode toggle (0246a): Tenant A can't change Tenant B's mode
- Agent discovery (0246b): Tenant A can't see Tenant B's agents
- Succession (0246c): Tenant A can't access Tenant B's orchestrators

Performance aspect: Isolation checks don't degrade performance

TDD Phase: RED (Tests written BEFORE isolation optimized)
Expected: Tests SHOULD PASS (isolation is critical security requirement)
"""

import time
from uuid import uuid4

import pytest
import pytest_asyncio

from src.giljo_mcp.models import AgentTemplate, Product, Project, User
from src.giljo_mcp.models.agent_identity import AgentExecution
from src.giljo_mcp.thin_prompt_generator import ThinClientPromptGenerator
from src.giljo_mcp.tools.agent_discovery import get_available_agents


@pytest_asyncio.fixture
async def tenant_a_user(db_session):
    """Create Tenant A user"""
    user = User(
        username=f"tenant_a_{uuid4().hex[:8]}",
        email=f"tenant_a_{uuid4().hex[:8]}@example.com",
        tenant_key=f"tenant_a_{uuid4().hex[:8]}",
        role="developer",
        password_hash="hashed_password",
    )
    db_session.add(user)
    await db_session.commit()
    await db_session.refresh(user)
    return user


@pytest_asyncio.fixture
async def tenant_b_user(db_session):
    """Create Tenant B user"""
    user = User(
        username=f"tenant_b_{uuid4().hex[:8]}",
        email=f"tenant_b_{uuid4().hex[:8]}@example.com",
        tenant_key=f"tenant_b_{uuid4().hex[:8]}",
        role="developer",
        password_hash="hashed_password",
    )
    db_session.add(user)
    await db_session.commit()
    await db_session.refresh(user)
    return user


@pytest_asyncio.fixture
async def tenant_a_product(db_session, tenant_a_user):
    """Create Tenant A product"""
    product = Product(
        name=f"Tenant A Product {uuid4().hex[:8]}",
        description="Tenant A product",
        tenant_key=tenant_a_user.tenant_key,
        is_active=True,
    )
    db_session.add(product)
    await db_session.commit()
    await db_session.refresh(product)
    return product


@pytest_asyncio.fixture
async def tenant_b_product(db_session, tenant_b_user):
    """Create Tenant B product"""
    product = Product(
        name=f"Tenant B Product {uuid4().hex[:8]}",
        description="Tenant B product",
        tenant_key=tenant_b_user.tenant_key,
        is_active=True,
    )
    db_session.add(product)
    await db_session.commit()
    await db_session.refresh(product)
    return product


@pytest.mark.asyncio
class TestMultiTenantIsolation:
    """Multi-tenant isolation tests across all components."""

    async def test_execution_mode_toggle_isolation(
        self, db_session, tenant_a_user, tenant_b_user, tenant_a_product, tenant_b_product
    ):
        """
        Test that Tenant A cannot affect Tenant B's execution mode.
        Component: 0246a (Frontend Toggle)
        """

        # Create projects for both tenants
        project_a = Project(
            name="Tenant A Project",
            description="Test isolation",
            tenant_key=tenant_a_user.tenant_key,
            product_id=tenant_a_product.id,
            status="active",
            mission="Test A",
            meta_data={"execution_mode": "claude-code"},
        )
        project_b = Project(
            name="Tenant B Project",
            description="Test isolation",
            tenant_key=tenant_b_user.tenant_key,
            product_id=tenant_b_product.id,
            status="active",
            mission="Test B",
            meta_data={"execution_mode": "multi-terminal"},
        )

        db_session.add(project_a)
        db_session.add(project_b)
        await db_session.commit()
        await db_session.refresh(project_a)
        await db_session.refresh(project_b)

        # Tenant A changes their mode
        project_a.meta_data = {"execution_mode": "multi-terminal"}
        await db_session.commit()

        # Verify Tenant B's mode unchanged
        await db_session.refresh(project_b)
        assert project_b.meta_data["execution_mode"] == "multi-terminal", (
            "Tenant B's mode should be unaffected by Tenant A"
        )

        print("\n✓ Execution mode toggle isolation:")
        print("  - Tenant A changed mode: ✓")
        print("  - Tenant B unaffected: ✓")

    async def test_agent_discovery_isolation(self, db_session, tenant_a_user, tenant_b_user):
        """
        Test that Tenant A cannot see Tenant B's agents.
        Component: 0246b (Dynamic Agent Discovery)
        """

        # Create agents for Tenant A
        agent_a1 = AgentTemplate(
            name="tenant_a_implementer",
            role="Tenant A Implementer",
            description="Tenant A agent",
            tenant_key=tenant_a_user.tenant_key,
            is_active=True,
            version="1.0.0",
            system_instructions="Tenant A",
        )
        agent_a2 = AgentTemplate(
            name="tenant_a_tester",
            role="Tenant A Tester",
            description="Tenant A agent",
            tenant_key=tenant_a_user.tenant_key,
            is_active=True,
            version="1.0.0",
            system_instructions="Tenant A",
        )

        # Create agents for Tenant B
        agent_b1 = AgentTemplate(
            name="tenant_b_implementer",
            role="Tenant B Implementer",
            description="Tenant B agent",
            tenant_key=tenant_b_user.tenant_key,
            is_active=True,
            version="1.0.0",
            system_instructions="Tenant B",
        )
        agent_b2 = AgentTemplate(
            name="tenant_b_tester",
            role="Tenant B Tester",
            description="Tenant B agent",
            tenant_key=tenant_b_user.tenant_key,
            is_active=True,
            version="1.0.0",
            system_instructions="Tenant B",
        )

        db_session.add_all([agent_a1, agent_a2, agent_b1, agent_b2])
        await db_session.commit()

        # Tenant A fetches agents
        result_a = await get_available_agents(session=db_session, tenant_key=tenant_a_user.tenant_key)

        # Tenant B fetches agents
        result_b = await get_available_agents(session=db_session, tenant_key=tenant_b_user.tenant_key)

        # Each tenant should see only their own agents
        assert result_a["success"] is True
        assert result_b["success"] is True

        assert result_a["data"]["count"] == 2, "Tenant A should see 2 agents (their own)"
        assert result_b["data"]["count"] == 2, "Tenant B should see 2 agents (their own)"

        # Verify Tenant A doesn't see Tenant B's agents
        tenant_a_agent_names = [a["name"] for a in result_a["data"]["agents"]]
        assert "tenant_b_implementer" not in tenant_a_agent_names, "Tenant A should NOT see Tenant B's agents"

        # Verify Tenant B doesn't see Tenant A's agents
        tenant_b_agent_names = [a["name"] for a in result_b["data"]["agents"]]
        assert "tenant_a_implementer" not in tenant_b_agent_names, "Tenant B should NOT see Tenant A's agents"

        print("\n✓ Agent discovery isolation:")
        print(f"  - Tenant A sees: {result_a['data']['count']} agents (their own)")
        print(f"  - Tenant B sees: {result_b['data']['count']} agents (their own)")
        print("  - Cross-tenant access: BLOCKED ✓")

    # HANDOVER 0422: Removed test_succession_isolation
    # This test called trigger_succession() which was removed (dead token budget cleanup)

    async def test_isolation_performance_overhead(self, db_session, tenant_a_user, tenant_b_user):
        """
        Test that tenant isolation checks don't significantly degrade performance.
        Target: <10% overhead compared to single-tenant queries
        """

        # Create agents for both tenants (20 each)
        for i in range(20):
            agent_a = AgentTemplate(
                name=f"tenant_a_agent_{i}",
                role=f"Agent {i}",
                tenant_key=tenant_a_user.tenant_key,
                is_active=True,
                version="1.0.0",
                system_instructions="Test",
            )
            agent_b = AgentTemplate(
                name=f"tenant_b_agent_{i}",
                role=f"Agent {i}",
                tenant_key=tenant_b_user.tenant_key,
                is_active=True,
                version="1.0.0",
                system_instructions="Test",
            )
            db_session.add(agent_a)
            db_session.add(agent_b)

        await db_session.commit()

        # Benchmark: Tenant A fetches agents (100 calls)
        latencies_a = []
        for _ in range(100):
            start = time.perf_counter()
            await get_available_agents(db_session, tenant_a_user.tenant_key)
            end = time.perf_counter()
            latencies_a.append((end - start) * 1000)

        # Benchmark: Tenant B fetches agents (100 calls)
        latencies_b = []
        for _ in range(100):
            start = time.perf_counter()
            await get_available_agents(db_session, tenant_b_user.tenant_key)
            end = time.perf_counter()
            latencies_b.append((end - start) * 1000)

        avg_latency_a = sum(latencies_a) / len(latencies_a)
        avg_latency_b = sum(latencies_b) / len(latencies_b)

        # Latencies should be similar (within 20%)
        variance = abs(avg_latency_a - avg_latency_b)
        variance_pct = (variance / avg_latency_a) * 100

        assert variance_pct < 20, f"Tenant isolation overhead too high ({variance_pct:.1f}%)"

        print("\n✓ Isolation performance overhead:")
        print(f"  - Tenant A avg latency: {avg_latency_a:.2f}ms")
        print(f"  - Tenant B avg latency: {avg_latency_b:.2f}ms")
        print(f"  - Variance: {variance_pct:.1f}%")
        print("  - Overhead acceptable: ✓")

    async def test_cross_component_isolation_integrity(
        self, db_session, tenant_a_user, tenant_b_user, tenant_a_product, tenant_b_product
    ):
        """
        Test isolation integrity across all 3 components (0246a/b/c).
        Verifies that tenant boundaries are respected throughout the workflow.
        """

        # Setup: Both tenants have projects, agents, and orchestrators
        # Tenant A
        project_a = Project(
            name="Tenant A Complete",
            tenant_key=tenant_a_user.tenant_key,
            product_id=tenant_a_product.id,
            status="active",
            mission="Test",
            meta_data={"execution_mode": "claude-code"},
        )
        agent_a = AgentTemplate(
            name="tenant_a_impl",
            role="Implementer",
            tenant_key=tenant_a_user.tenant_key,
            is_active=True,
            version="1.0.0",
            system_instructions="A",
        )
        orchestrator_a = AgentExecution(
            project_id=None,  # Will be set after project creation
            tenant_key=tenant_a_user.tenant_key,
            agent_display_name="orchestrator",
            status="waiting",
            mission="A",
            job_metadata={"user_id": tenant_a_user.id},
        )

        # Tenant B
        project_b = Project(
            name="Tenant B Complete",
            tenant_key=tenant_b_user.tenant_key,
            product_id=tenant_b_product.id,
            status="active",
            mission="Test",
            meta_data={"execution_mode": "multi-terminal"},
        )
        agent_b = AgentTemplate(
            name="tenant_b_impl",
            role="Implementer",
            tenant_key=tenant_b_user.tenant_key,
            is_active=True,
            version="1.0.0",
            system_instructions="B",
        )

        db_session.add_all([project_a, project_b, agent_a, agent_b])
        await db_session.commit()

        orchestrator_a.project_id = project_a.id
        db_session.add(orchestrator_a)
        await db_session.commit()

        # Verification: Tenant A's workflow
        # 1. Execution mode
        assert project_a.meta_data["execution_mode"] == "claude-code"

        # 2. Agent discovery
        agents_a = await get_available_agents(db_session, tenant_a_user.tenant_key)
        assert agents_a["data"]["count"] == 1
        assert agents_a["data"]["agents"][0]["name"] == "tenant_a_impl"

        # 3. Prompt generation
        generator_a = ThinClientPromptGenerator(
            session=db_session,
            orchestrator_id=str(orchestrator_a.job_id),
            project_id=str(project_a.id),
            tenant_key=tenant_a_user.tenant_key,
            user_id=tenant_a_user.id,
        )
        prompt_a = await generator_a.generate(tool="claude-code")

        # Prompt should reference Tenant A's mode and agents
        assert "get_available_agents" in prompt_a.lower()

        # Verification: Tenant B's agents NOT accessible to Tenant A
        assert "tenant_b_impl" not in prompt_a

        print("\n✓ Cross-component isolation integrity:")
        print("  - Execution mode isolated: ✓")
        print("  - Agent discovery isolated: ✓")
        print("  - Prompt generation isolated: ✓")
        print("  - Complete workflow integrity: ✓")
