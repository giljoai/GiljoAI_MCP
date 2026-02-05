"""
Comprehensive tests for multi-tenant isolation in GiljoAI MCP.

These tests verify that tenant data is completely isolated and that
no cross-tenant data leakage is possible.
"""

import asyncio

# Add src to path
import sys
from concurrent.futures import ThreadPoolExecutor, as_completed
from pathlib import Path

import pytest
from sqlalchemy import select


sys.path.insert(0, str(Path(__file__).parent.parent))

from src.giljo_mcp.database import DatabaseManager
from src.giljo_mcp.models import Message, Project
from src.giljo_mcp.models.agent_identity import AgentJob, AgentExecution
from src.giljo_mcp.tenant import TenantManager
from tests.helpers.test_db_helper import PostgreSQLTestHelper


class TestTenantManager:
    """Test TenantManager functionality."""

    def test_tenant_key_generation(self):
        """Test tenant key generation is unique and valid."""
        keys = set()
        for _ in range(100):
            key = TenantManager.generate_tenant_key()
            assert key.startswith("tk_")
            assert len(key) == 35  # tk_ + 32 chars
            assert key not in keys
            keys.add(key)
            assert TenantManager.validate_tenant_key(key)

    def test_tenant_key_validation(self):
        """Test tenant key validation."""
        # Valid keys
        valid_key = TenantManager.generate_tenant_key()
        assert TenantManager.validate_tenant_key(valid_key)

        # Invalid keys
        assert not TenantManager.validate_tenant_key(None)
        assert not TenantManager.validate_tenant_key("")
        assert not TenantManager.validate_tenant_key("invalid")
        assert not TenantManager.validate_tenant_key("tk_")
        assert not TenantManager.validate_tenant_key("tk_short")
        assert not TenantManager.validate_tenant_key("wrong_prefix_" + "a" * 32)

    def test_tenant_context_management(self):
        """Test tenant context setting and retrieval."""
        key1 = TenantManager.generate_tenant_key()
        key2 = TenantManager.generate_tenant_key()

        # Initially no tenant
        assert TenantManager.get_current_tenant() is None

        # Set tenant 1
        TenantManager.set_current_tenant(key1)
        assert TenantManager.get_current_tenant() == key1

        # Switch to tenant 2
        TenantManager.set_current_tenant(key2)
        assert TenantManager.get_current_tenant() == key2

        # Clear tenant
        TenantManager.clear_current_tenant()
        assert TenantManager.get_current_tenant() is None

    def test_tenant_context_manager(self):
        """Test with_tenant context manager."""
        key1 = TenantManager.generate_tenant_key()
        key2 = TenantManager.generate_tenant_key()

        # Set initial tenant
        TenantManager.set_current_tenant(key1)
        assert TenantManager.get_current_tenant() == key1

        # Use context manager
        with TenantManager.with_tenant(key2):
            assert TenantManager.get_current_tenant() == key2

        # Should restore previous tenant
        assert TenantManager.get_current_tenant() == key1

        # Clear and test with no previous tenant
        TenantManager.clear_current_tenant()
        with TenantManager.with_tenant(key2):
            assert TenantManager.get_current_tenant() == key2
        assert TenantManager.get_current_tenant() is None

    def test_require_tenant(self):
        """Test require_tenant error handling."""
        TenantManager.clear_current_tenant()

        # Should raise when no tenant set
        with pytest.raises(RuntimeError, match="No tenant context"):
            TenantManager.require_tenant()

        # Should work when tenant is set
        key = TenantManager.generate_tenant_key()
        TenantManager.set_current_tenant(key)
        assert TenantManager.require_tenant() == key

    def test_tenant_key_hashing(self):
        """Test tenant key hashing for logging."""
        key = TenantManager.generate_tenant_key()
        hash1 = TenantManager.hash_tenant_key(key)
        hash2 = TenantManager.hash_tenant_key(key)

        # Should be consistent
        assert hash1 == hash2
        assert len(hash1) == 8

        # Different keys should have different hashes
        key2 = TenantManager.generate_tenant_key()
        hash3 = TenantManager.hash_tenant_key(key2)
        assert hash3 != hash1

    def test_batch_validation(self):
        """Test batch tenant key validation."""
        valid_keys = [TenantManager.generate_tenant_key() for _ in range(5)]
        invalid_keys = ["invalid1", "tk_", None, "", "wrong_prefix"]

        all_keys = valid_keys + invalid_keys
        results = TenantManager.batch_validate_keys(all_keys)

        for key in valid_keys:
            assert results[key] is True

        for key in invalid_keys:
            assert results[key] is False


class TestDatabaseTenantIsolation:
    """Test database-level tenant isolation."""

    @pytest.fixture
    def db_manager(self):
        """Create an in-memory database manager for testing."""
        manager = DatabaseManager(PostgreSQLTestHelper.get_test_db_url(async_driver=False))
        manager.create_tables()
        yield manager
        manager.close()

    def test_tenant_session_isolation(self, db_manager):
        """Test that tenant sessions are properly isolated."""
        tenant1 = TenantManager.generate_tenant_key()
        tenant2 = TenantManager.generate_tenant_key()

        # Create projects in different tenant contexts
        with db_manager.get_tenant_session(tenant1) as session:
            project1 = Project(name="Tenant 1 Project", mission="Mission 1", tenant_key=tenant1)
            session.add(project1)
            session.commit()

        with db_manager.get_tenant_session(tenant2) as session:
            project2 = Project(name="Tenant 2 Project", mission="Mission 2", tenant_key=tenant2)
            session.add(project2)
            session.commit()

        # Verify isolation with tenant queries
        with db_manager.get_tenant_session(tenant1) as session:
            projects = session.execute(select(Project).where(Project.tenant_key == tenant1)).scalars().all()
            assert len(projects) == 1
            assert projects[0].name == "Tenant 1 Project"

        with db_manager.get_tenant_session(tenant2) as session:
            projects = session.execute(select(Project).where(Project.tenant_key == tenant2)).scalars().all()
            assert len(projects) == 1
            assert projects[0].name == "Tenant 2 Project"

    def test_cross_tenant_access_prevention(self, db_manager):
        """Test that cross-tenant access is prevented."""
        tenant1 = TenantManager.generate_tenant_key()
        tenant2 = TenantManager.generate_tenant_key()

        # Create entities for tenant1
        with db_manager.get_tenant_session(tenant1) as session:
            project = Project(name="Private Project", mission="Secret mission", tenant_key=tenant1)
            session.add(project)
            session.commit()
            project_id = project.id

        # Try to access from tenant2 context
        with db_manager.get_tenant_session(tenant2) as session:
            # Direct query should not find it
            found = session.execute(select(Project).where(Project.tenant_key == tenant2, Project.id == project_id)).scalars().first()
            assert found is None

            # Even without filter, ensure_tenant_isolation should catch it
            all_projects = session.query(Project).filter_by(id=project_id).first()
            if all_projects:
                with pytest.raises(PermissionError, match="Access denied"):
                    db_manager.ensure_tenant_isolation(all_projects, tenant2)

    def test_tenant_inheritance(self, db_manager):
        """Test tenant key inheritance for child entities."""
        tenant_key = TenantManager.generate_tenant_key()

        with db_manager.get_tenant_session(tenant_key) as session:
            # Create project
            project = Project(name="Parent Project", mission="Test inheritance", tenant_key=tenant_key)
            session.add(project)
            session.commit()

            # Create agent inheriting tenant from project
            inherited_key = TenantManager.inherit_tenant_key(project)
            assert inherited_key == tenant_key

            agent = Agent(name="child_agent", role="worker", tenant_key=inherited_key, project_id=project.id)
            session.add(agent)
            session.commit()

            # Verify inheritance worked
            assert agent.tenant_key == project.tenant_key

    def test_concurrent_tenant_operations(self, db_manager):
        """Test concurrent operations from different tenants."""
        num_tenants = 5
        operations_per_tenant = 10

        def tenant_operations(tenant_key, tenant_id):
            """Perform operations for a single tenant."""
            results = []

            for i in range(operations_per_tenant):
                with db_manager.get_tenant_session(tenant_key) as session:
                    # Create project
                    project = Project(
                        name=f"Tenant{tenant_id}_Project{i}", mission=f"Mission {i}", tenant_key=tenant_key
                    )
                    session.add(project)
                    session.commit()
                    results.append(project.id)

            # Verify all projects are accessible
            with db_manager.get_tenant_session(tenant_key) as session:
                projects = session.execute(select(Project).where(Project.tenant_key == tenant_key)).scalars().all()
                assert len(projects) == operations_per_tenant

            return tenant_key, results

        # Create tenant keys
        tenant_keys = [TenantManager.generate_tenant_key() for _ in range(num_tenants)]

        # Run concurrent operations
        with ThreadPoolExecutor(max_workers=num_tenants) as executor:
            futures = []
            for i, key in enumerate(tenant_keys):
                future = executor.submit(tenant_operations, key, i)
                futures.append(future)

            # Collect results
            results = {}
            for future in as_completed(futures):
                tenant_key, project_ids = future.result()
                results[tenant_key] = project_ids

        # Verify complete isolation
        for tenant_key in tenant_keys:
            with db_manager.get_tenant_session(tenant_key) as session:
                # Should only see own projects
                projects = session.execute(select(Project).where(Project.tenant_key == tenant_key)).scalars().all()
                assert len(projects) == operations_per_tenant

                # All projects should belong to this tenant
                for project in projects:
                    assert project.tenant_key == tenant_key

    def test_message_isolation(self, db_manager):
        """Test message isolation between tenants."""
        tenant1 = TenantManager.generate_tenant_key()
        tenant2 = TenantManager.generate_tenant_key()

        # Create projects and messages for each tenant
        with db_manager.get_tenant_session(tenant1) as session:
            project1 = Project(name="Tenant 1 Project", mission="Mission 1", tenant_key=tenant1)
            session.add(project1)
            session.commit()

            message1 = Message(
                tenant_key=tenant1,
                project_id=project1.id,
                content="Secret message for tenant 1",
                to_agents=["agent1"],
                from_agent="orchestrator",
            )
            session.add(message1)
            session.commit()

        with db_manager.get_tenant_session(tenant2) as session:
            project2 = Project(name="Tenant 2 Project", mission="Mission 2", tenant_key=tenant2)
            session.add(project2)
            session.commit()

            message2 = Message(
                tenant_key=tenant2,
                project_id=project2.id,
                content="Secret message for tenant 2",
                to_agents=["agent2"],
                from_agent="orchestrator",
            )
            session.add(message2)
            session.commit()

        # Verify message isolation
        with db_manager.get_tenant_session(tenant1) as session:
            messages = session.execute(select(Message).where(Message.tenant_key == tenant1)).scalars().all()
            assert len(messages) == 1
            assert messages[0].content == "Secret message for tenant 1"

        with db_manager.get_tenant_session(tenant2) as session:
            messages = session.execute(select(Message).where(Message.tenant_key == tenant2)).scalars().all()
            assert len(messages) == 1
            assert messages[0].content == "Secret message for tenant 2"

    def test_cascade_deletion_respects_tenants(self, db_manager):
        """Test that cascade deletion only affects the correct tenant."""
        tenant1 = TenantManager.generate_tenant_key()
        tenant2 = TenantManager.generate_tenant_key()

        # Create projects with agents for both tenants
        with db_manager.get_tenant_session(tenant1) as session:
            project1 = Project(name="Tenant 1 Project", mission="Mission 1", tenant_key=tenant1)
            session.add(project1)
            session.commit()

            agent1 = Agent(name="tenant1_agent", role="worker", tenant_key=tenant1, project_id=project1.id)
            session.add(agent1)
            session.commit()
            project1_id = project1.id

        with db_manager.get_tenant_session(tenant2) as session:
            project2 = Project(name="Tenant 2 Project", mission="Mission 2", tenant_key=tenant2)
            session.add(project2)
            session.commit()

            agent2 = Agent(name="tenant2_agent", role="worker", tenant_key=tenant2, project_id=project2.id)
            session.add(agent2)
            session.commit()

        # Delete tenant1's project
        with db_manager.get_tenant_session(tenant1) as session:
            project = session.query(Project).filter_by(id=project1_id, tenant_key=tenant1).first()
            session.delete(project)
            session.commit()

        # Verify tenant1's data is gone
        with db_manager.get_tenant_session(tenant1) as session:
            projects = session.execute(select(Project).where(Project.tenant_key == tenant1)).scalars().all()
            agents = session.execute(select(Agent).where(Agent.tenant_key == tenant1)).scalars().all()
            assert len(projects) == 0
            assert len(agents) == 0

        # Verify tenant2's data is intact
        with db_manager.get_tenant_session(tenant2) as session:
            projects = session.execute(select(Project).where(Project.tenant_key == tenant2)).scalars().all()
            agents = session.execute(select(Agent).where(Agent.tenant_key == tenant2)).scalars().all()
            assert len(projects) == 1
            assert len(agents) == 1
            assert projects[0].name == "Tenant 2 Project"
            assert agents[0].name == "tenant2_agent"


class TestAsyncTenantIsolation:
    """Test tenant isolation with async database operations."""

    @pytest.fixture
    async def async_db_manager(self):
        """Create an async in-memory database manager."""
        manager = DatabaseManager(PostgreSQLTestHelper.get_test_db_url(), is_async=True)
        await manager.create_tables_async()
        yield manager
        await manager.close_async()

    @pytest.mark.asyncio
    async def test_async_tenant_operations(self, async_db_manager):
        """Test async operations with tenant isolation."""
        tenant1 = TenantManager.generate_tenant_key()
        tenant2 = TenantManager.generate_tenant_key()

        # Create projects asynchronously
        async with async_db_manager.get_tenant_session_async(tenant1) as session:
            project1 = Project(name="Async Tenant 1", mission="Async mission 1", tenant_key=tenant1)
            session.add(project1)
            await session.commit()

        async with async_db_manager.get_tenant_session_async(tenant2) as session:
            project2 = Project(name="Async Tenant 2", mission="Async mission 2", tenant_key=tenant2)
            session.add(project2)
            await session.commit()

        # Verify isolation
        async with async_db_manager.get_tenant_session_async(tenant1) as session:
            result = await session.execute(
                async_db_manager.apply_tenant_filter(session.query(Project), Project, tenant1)
            )
            projects = result.scalars().all()
            assert len(projects) == 1
            assert projects[0].name == "Async Tenant 1"

    @pytest.mark.asyncio
    async def test_concurrent_async_tenants(self, async_db_manager):
        """Test concurrent async operations from multiple tenants."""
        num_tenants = 3

        async def create_tenant_data(tenant_key, tenant_id):
            """Create data for a tenant asynchronously."""
            async with async_db_manager.get_tenant_session_async(tenant_key) as session:
                project = Project(
                    name=f"Async Project {tenant_id}", mission=f"Async Mission {tenant_id}", tenant_key=tenant_key
                )
                session.add(project)
                await session.commit()

                # Create multiple agents
                for i in range(3):
                    agent = Agent(
                        name=f"agent_{tenant_id}_{i}", role="async_worker", tenant_key=tenant_key, project_id=project.id
                    )
                    session.add(agent)
                await session.commit()

            return tenant_key

        # Create tenant keys
        tenant_keys = [TenantManager.generate_tenant_key() for _ in range(num_tenants)]

        # Run concurrent async operations
        tasks = []
        for i, key in enumerate(tenant_keys):
            task = create_tenant_data(key, i)
            tasks.append(task)

        await asyncio.gather(*tasks)

        # Verify isolation for each tenant
        for i, tenant_key in enumerate(tenant_keys):
            async with async_db_manager.get_tenant_session_async(tenant_key) as session:
                # Check projects
                result = await session.execute(
                    async_db_manager.apply_tenant_filter(session.query(Project), Project, tenant_key)
                )
                projects = result.scalars().all()
                assert len(projects) == 1
                assert projects[0].name == f"Async Project {i}"

                # Check agents
                result = await session.execute(
                    async_db_manager.apply_tenant_filter(session.query(Agent), Agent, tenant_key)
                )
                agents = result.scalars().all()
                assert len(agents) == 3
                for agent in agents:
                    assert agent.tenant_key == tenant_key


class TestTenantPerformance:
    """Performance tests for multi-tenant operations."""

    @pytest.fixture
    def db_manager(self):
        """Create an in-memory database for performance testing."""
        manager = DatabaseManager(PostgreSQLTestHelper.get_test_db_url(async_driver=False))
        manager.create_tables()
        yield manager
        manager.close()

    def test_tenant_key_generation_performance(self):
        """Test performance of tenant key generation."""
        import time

        start = time.time()
        keys = [TenantManager.generate_tenant_key() for _ in range(1000)]
        elapsed = time.time() - start

        # Should generate 1000 keys in under 1 second
        assert elapsed < 1.0
        # All keys should be unique
        assert len(set(keys)) == 1000

    def test_tenant_validation_caching(self):
        """Test that validation caching improves performance."""
        import time

        keys = [TenantManager.generate_tenant_key() for _ in range(100)]

        # First validation (uncached)
        TenantManager.clear_cache()
        start = time.time()
        for key in keys:
            TenantManager.validate_tenant_key(key)
        first_run = time.time() - start

        # Second validation (cached)
        start = time.time()
        for key in keys:
            TenantManager.validate_tenant_key(key)
        cached_run = time.time() - start

        # Cached should be faster
        assert cached_run < first_run

    def test_multi_tenant_query_performance(self, db_manager):
        """Test query performance with tenant filtering."""
        import time

        # Create multiple tenants with data
        tenant_keys = [TenantManager.generate_tenant_key() for _ in range(10)]

        # Populate data
        for tenant_key in tenant_keys:
            with db_manager.get_tenant_session(tenant_key) as session:
                for i in range(50):
                    project = Project(name=f"Project {i}", mission=f"Mission {i}", tenant_key=tenant_key)
                    session.add(project)
                session.commit()

        # Test query performance
        target_tenant = tenant_keys[5]
        start = time.time()

        with db_manager.get_tenant_session(target_tenant) as session:
            projects = session.execute(select(Project).where(Project.tenant_key == target_tenant)).scalars().all()
            assert len(projects) == 50

        elapsed = time.time() - start

        # Should query in under 100ms even with 500 total projects
        assert elapsed < 0.1


if __name__ == "__main__":
    pytest.main([__file__, "-v"])
