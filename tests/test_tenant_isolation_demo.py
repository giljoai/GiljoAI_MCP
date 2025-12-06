"""
Simple demonstration of multi-tenant isolation working correctly.
"""

# Add src to path
import sys
import time
from concurrent.futures import ThreadPoolExecutor, as_completed
from pathlib import Path


sys.path.insert(0, str(Path(__file__).parent.parent))

from src.giljo_mcp.database import DatabaseManager
from src.giljo_mcp.models import MCPAgentJob, Message, Project
from src.giljo_mcp.tenant import TenantManager
from tests.helpers.test_db_helper import PostgreSQLTestHelper


def test_multi_tenant_isolation_demo():
    """Demonstrate complete isolation between 10 tenants."""

    # Create database
    db_manager = DatabaseManager(PostgreSQLTestHelper.get_test_db_url(async_driver=False))
    db_manager.create_tables()

    # Create 10 tenants
    num_tenants = 10
    tenant_data = {}

    for i in range(num_tenants):
        tenant_key = TenantManager.generate_tenant_key()

        with db_manager.get_tenant_session(tenant_key) as session:
            # Create project
            project = Project(
                name=f"Tenant {i} Project", mission=f"Secret mission for tenant {i}", tenant_key=tenant_key
            )
            session.add(project)
            session.commit()

            # Create agents
            for j in range(3):
                agent = Agent(
                    name=f"agent_{i}_{j}",
                    role=["analyzer", "implementer", "tester"][j],
                    tenant_key=tenant_key,
                    project_id=project.id,
                    status="active",
                    context_used=0,
                )
                session.add(agent)

            session.commit()

            tenant_data[tenant_key] = {"id": i, "project_id": project.id, "project_name": project.name}

    # Test isolation - each tenant can only see their own data

    for tenant_key, data in tenant_data.items():
        with db_manager.get_tenant_session(tenant_key) as session:
            # Count all projects this tenant can see
            projects = db_manager.query_with_tenant(session, Project, tenant_key).all()

            agents = db_manager.query_with_tenant(session, Agent, tenant_key).all()

            # Should only see their own data
            assert len(projects) == 1, f"Tenant {data['id']} sees {len(projects)} projects!"
            assert projects[0].name == data["project_name"]
            assert len(agents) == 3, f"Tenant {data['id']} sees {len(agents)} agents!"

    # Test concurrent operations

    def create_messages(tenant_key, tenant_id):
        """Create messages for a tenant."""
        with db_manager.get_tenant_session(tenant_key) as session:
            project = db_manager.query_with_tenant(session, Project, tenant_key).first()

            for i in range(5):
                message = Message(
                    tenant_key=tenant_key,
                    project_id=project.id,
                    to_agents=[f"agent_{tenant_id}_0"],
                    content=f"Concurrent message {i} for tenant {tenant_id}",
                    message_type="direct",
                    status="waiting",
                )
                session.add(message)
            session.commit()
        return tenant_id

    # Run concurrent message creation
    with ThreadPoolExecutor(max_workers=num_tenants) as executor:
        futures = []
        for tenant_key, data in tenant_data.items():
            future = executor.submit(create_messages, tenant_key, data["id"])
            futures.append(future)

        for future in as_completed(futures):
            future.result()

    # Verify message isolation
    for tenant_key, data in tenant_data.items():
        with db_manager.get_tenant_session(tenant_key) as session:
            messages = db_manager.query_with_tenant(session, Message, tenant_key).all()
            assert len(messages) == 5
            for msg in messages:
                assert str(data["id"]) in msg.content

    # Performance test

    start_time = time.perf_counter()

    # Quick performance test - 100 queries across all tenants
    for _ in range(10):
        for tenant_key in tenant_data:
            with db_manager.get_tenant_session(tenant_key) as session:
                projects = db_manager.query_with_tenant(session, Project, tenant_key).all()

    elapsed = time.perf_counter() - start_time
    100 / elapsed

    # Test TenantManager thread safety

    def test_tenant_manager_ops(thread_id):
        """Test TenantManager operations."""
        results = []
        for _i in range(10):
            key = TenantManager.generate_tenant_key()
            valid = TenantManager.validate_tenant_key(key)
            results.append((key, valid))
        return thread_id, results

    with ThreadPoolExecutor(max_workers=5) as executor:
        futures = []
        for i in range(5):
            future = executor.submit(test_tenant_manager_ops, i)
            futures.append(future)

        all_keys = []
        for future in as_completed(futures):
            _thread_id, results = future.result()
            all_keys.extend([k for k, _ in results])

    # Verify all keys are unique
    assert len(all_keys) == len(set(all_keys)), "Duplicate keys generated!"

    # Summary

    db_manager.close()


if __name__ == "__main__":
    test_multi_tenant_isolation_demo()
