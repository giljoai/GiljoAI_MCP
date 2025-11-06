"""
Database Operation Reliability Tests

Measures success rates of core database operations to establish baseline reliability metrics.
These tests run operations 100 times and calculate actual reliability percentages.

Target: >=95% reliability for database operations
"""

from datetime import datetime, timezone

import pytest
from sqlalchemy import select

from src.giljo_mcp.database import DatabaseManager
from src.giljo_mcp.models import Agent, AgentInteraction, Product, Project


class TestDatabaseReliability:
    """Test reliability of database operations under normal conditions"""

    @pytest.fixture
    async def db_manager(self):
        """Create database manager for tests"""
        return DatabaseManager()

    @pytest.fixture
    async def test_product(self, db_manager):
        """Create test product for agent creation"""
        async with db_manager.get_session_async() as session:
            product = Product(
                tenant_key="reliability-test-tenant",
                name="Reliability Test Product",
                description="Product for reliability testing",
            )
            session.add(product)
            await session.commit()
            await session.refresh(product)
            return product

    @pytest.fixture
    async def test_project(self, db_manager, test_product):
        """Create test project for agent creation"""
        async with db_manager.get_session_async() as session:
            project = Project(
                tenant_key="reliability-test-tenant",
                product_id=test_product.id,
                name="Reliability Test Project",
                mission="Test database reliability",
            )
            session.add(project)
            await session.commit()
            await session.refresh(project)
            return project

    @pytest.mark.asyncio
    async def test_agent_creation_reliability(self, db_manager, test_project):
        """Test reliability of agent creation over 100 iterations"""
        success_count = 0
        failure_count = 0
        errors = []

        for i in range(100):
            try:
                async with db_manager.get_session_async() as session:
                    agent = Agent(
                        project_id=test_project.id,
                        tenant_key=test_project.tenant_key,
                        name=f"reliability-agent-{i}",
                        role="tester",
                        status="active",
                        created_at=datetime.now(timezone.utc),
                    )
                    session.add(agent)
                    await session.commit()
                    success_count += 1
            except Exception as e:
                failure_count += 1
                errors.append({"iteration": i, "error": str(e)})

        reliability = (success_count / 100) * 100

        print("\n=== Agent Creation Reliability Test ===")
        print(f"Successes: {success_count}/100")
        print(f"Failures: {failure_count}/100")
        print(f"Reliability: {reliability}%")

        if errors:
            print(f"Errors encountered: {len(errors)}")
            for error in errors[:5]:  # Show first 5 errors
                print(f"  - Iteration {error['iteration']}: {error['error']}")

        # Assert >=95% reliability
        assert reliability >= 95.0, (
            f"Agent creation reliability {reliability}% is below target 95%. "
            f"Failures: {failure_count}, First error: {errors[0] if errors else 'None'}"
        )

    @pytest.mark.asyncio
    async def test_interaction_logging_reliability(self, db_manager, test_project):
        """Test reliability of AgentInteraction logging over 100 iterations"""
        success_count = 0
        failure_count = 0
        errors = []

        # Create parent agent first
        async with db_manager.get_session_async() as session:
            parent = Agent(
                project_id=test_project.id,
                tenant_key=test_project.tenant_key,
                name="orchestrator",
                role="orchestrator",
                status="active",
            )
            session.add(parent)
            await session.commit()
            await session.refresh(parent)
            parent_id = parent.id

        # Test 100 interaction logging operations
        for i in range(100):
            try:
                async with db_manager.get_session_async() as session:
                    interaction = AgentInteraction(
                        tenant_key=test_project.tenant_key,
                        project_id=test_project.id,
                        parent_agent_id=parent_id,
                        sub_agent_name=f"worker-{i}",
                        interaction_type="SPAWN",
                        mission="Test mission",
                        start_time=datetime.now(timezone.utc),
                    )
                    session.add(interaction)
                    await session.commit()
                    success_count += 1
            except Exception as e:
                failure_count += 1
                errors.append({"iteration": i, "error": str(e)})

        reliability = (success_count / 100) * 100

        print("\n=== Interaction Logging Reliability Test ===")
        print(f"Successes: {success_count}/100")
        print(f"Failures: {failure_count}/100")
        print(f"Reliability: {reliability}%")

        if errors:
            print(f"Errors encountered: {len(errors)}")
            for error in errors[:5]:
                print(f"  - Iteration {error['iteration']}: {error['error']}")

        assert reliability >= 95.0, (
            f"Interaction logging reliability {reliability}% is below target 95%. Failures: {failure_count}"
        )

    @pytest.mark.asyncio
    async def test_transaction_commit_reliability(self, db_manager, test_project):
        """Test reliability of transaction commits under normal conditions"""
        success_count = 0
        failure_count = 0
        errors = []

        for i in range(100):
            try:
                async with db_manager.get_session_async() as session:
                    # Create agent
                    agent = Agent(
                        project_id=test_project.id,
                        tenant_key=test_project.tenant_key,
                        name=f"transaction-test-{i}",
                        role="tester",
                        status="active",
                    )
                    session.add(agent)

                    # Commit transaction
                    await session.commit()
                    success_count += 1
            except Exception as e:
                failure_count += 1
                errors.append({"iteration": i, "error": str(e)})

        reliability = (success_count / 100) * 100

        print("\n=== Transaction Commit Reliability Test ===")
        print(f"Successes: {success_count}/100")
        print(f"Failures: {failure_count}/100")
        print(f"Reliability: {reliability}%")

        assert reliability >= 95.0, f"Transaction commit reliability {reliability}% is below target 95%"

    @pytest.mark.asyncio
    async def test_query_execution_reliability(self, db_manager, test_project):
        """Test reliability of database queries over 100 iterations"""
        success_count = 0
        failure_count = 0
        errors = []

        # Create some test agents first
        async with db_manager.get_session_async() as session:
            for i in range(10):
                agent = Agent(
                    project_id=test_project.id,
                    tenant_key=test_project.tenant_key,
                    name=f"query-test-agent-{i}",
                    role="tester",
                    status="active",
                )
                session.add(agent)
            await session.commit()

        # Test 100 query operations
        for i in range(100):
            try:
                async with db_manager.get_session_async() as session:
                    query = select(Agent).where(Agent.project_id == test_project.id)
                    result = await session.execute(query)
                    agents = result.scalars().all()

                    assert len(agents) >= 10, "Expected at least 10 agents"
                    success_count += 1
            except Exception as e:
                failure_count += 1
                errors.append({"iteration": i, "error": str(e)})

        reliability = (success_count / 100) * 100

        print("\n=== Query Execution Reliability Test ===")
        print(f"Successes: {success_count}/100")
        print(f"Failures: {failure_count}/100")
        print(f"Reliability: {reliability}%")

        assert reliability >= 95.0, f"Query execution reliability {reliability}% is below target 95%"


class TestDatabaseConstraintReliability:
    """Test that database constraints prevent invalid data reliably"""

    @pytest.mark.asyncio
    async def test_constraint_enforcement_reliability(self, db_manager, test_project):
        """Test that constraints consistently prevent invalid data"""
        constraint_violations = 0
        successful_rejections = 0

        for i in range(50):
            try:
                async with db_manager.get_session_async() as session:
                    # Try to create interaction with invalid type
                    interaction = AgentInteraction(
                        tenant_key=test_project.tenant_key,
                        project_id=test_project.id,
                        parent_agent_id=None,
                        sub_agent_name="test",
                        interaction_type="INVALID_TYPE",  # Should violate constraint
                        mission="Test",
                        start_time=datetime.now(timezone.utc),
                    )
                    session.add(interaction)
                    await session.commit()

                    # If we get here, constraint didn't fire
                    constraint_violations += 1
            except Exception as e:
                # Constraint should reject this
                if "ck_interaction_type" in str(e) or "constraint" in str(e).lower():
                    successful_rejections += 1
                else:
                    # Unexpected error
                    print(f"Unexpected error: {e}")

        enforcement_rate = (successful_rejections / 50) * 100

        print("\n=== Constraint Enforcement Reliability Test ===")
        print(f"Successful rejections: {successful_rejections}/50")
        print(f"Constraint violations: {constraint_violations}/50")
        print(f"Enforcement rate: {enforcement_rate}%")

        assert enforcement_rate == 100.0, (
            f"Constraints should reject invalid data 100% of the time, but enforcement rate is {enforcement_rate}%"
        )


if __name__ == "__main__":
    pytest.main([__file__, "-v", "-s"])
