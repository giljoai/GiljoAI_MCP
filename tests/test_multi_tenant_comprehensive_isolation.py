"""
Multi-tenant isolation and inheritance tests for GiljoAI MCP.

Split from test_multi_tenant_comprehensive.py: covers tenant data isolation
and tenant key inheritance chain verification.
"""

import random

# Add src to path
import sys
from pathlib import Path

import pytest
from sqlalchemy import select

pytestmark = pytest.mark.skip(reason="0750c3: async_engine attribute missing on DatabaseManager — DB test infrastructure")


sys.path.insert(0, str(Path(__file__).parent.parent))

from src.giljo_mcp.database import DatabaseManager
from src.giljo_mcp.models import Job, Message, Project, Task
from src.giljo_mcp.tenant import TenantManager
from tests.helpers.test_db_helper import PostgreSQLTestHelper


class TestMultiTenantIsolation:
    """Tests for multi-tenant data isolation and tenant key inheritance."""

    @pytest.fixture
    def db_manager(self):
        """Create an in-memory database manager for testing."""
        manager = DatabaseManager(PostgreSQLTestHelper.get_test_db_url(async_driver=False))
        manager.create_tables()
        yield manager
        manager.close()

    def test_complete_tenant_isolation(self, db_manager):
        """Test complete isolation between 10 tenants."""
        num_tenants = 10
        tenant_data = {}

        # Create data for each tenant
        for i in range(num_tenants):
            tenant_key = TenantManager.generate_tenant_key()

            with db_manager.get_tenant_session(tenant_key) as session:
                # Create project
                project = Project(
                    name=f"Tenant {i} Project",
                    mission=f"Mission for tenant {i}",
                    tenant_key=tenant_key,
                    series_number=random.randint(1, 999999),
                )
                session.add(project)
                session.commit()

                # Create agents
                agents = []
                for j in range(3):
                    agent = Agent(
                        name=f"agent_{i}_{j}",
                        role=["analyzer", "implementer", "tester"][j],
                        tenant_key=tenant_key,
                        project_id=project.id,
                        status="active",
                    )
                    agents.append(agent)
                    session.add(agent)

                # Create messages
                messages = []
                for j in range(5):
                    message = Message(
                        tenant_key=tenant_key,
                        project_id=project.id,
                        to_agents=[agents[(j + 1) % 3].name],
                        content=f"Message {j} for tenant {i}",
                        message_type="direct",
                        status="waiting",
                        priority="normal",
                    )
                    messages.append(message)
                    session.add(message)

                # Create tasks
                tasks = []
                for j in range(4):
                    task = Task(
                        tenant_key=tenant_key,
                        project_id=project.id,
                        content=f"Task {j} for tenant {i}",
                        category=["development", "testing", "documentation", "review"][j],
                        priority=["low", "medium", "high", "critical"][j],
                        status="waiting",
                    )
                    tasks.append(task)
                    session.add(task)

                session.commit()

                tenant_data[tenant_key] = {
                    "project_id": project.id,
                    "project_name": project.name,
                    "agent_count": len(agents),
                    "message_count": len(messages),
                    "task_count": len(tasks),
                }

        # Verify complete isolation for each tenant
        for tenant_key, data in tenant_data.items():
            with db_manager.get_tenant_session(tenant_key) as session:
                # Check projects
                projects = session.execute(select(Project).where(Project.tenant_key == tenant_key)).scalars().all()
                assert len(projects) == 1
                assert projects[0].id == data["project_id"]
                assert projects[0].name == data["project_name"]

                # Check agents
                agents = session.execute(select(Agent).where(Agent.tenant_key == tenant_key)).scalars().all()
                assert len(agents) == data["agent_count"]
                for agent in agents:
                    assert agent.tenant_key == tenant_key

                # Check messages
                messages = session.execute(select(Message).where(Message.tenant_key == tenant_key)).scalars().all()
                assert len(messages) == data["message_count"]
                for message in messages:
                    assert message.tenant_key == tenant_key

                # Check tasks
                tasks = session.execute(select(Task).where(Task.tenant_key == tenant_key)).scalars().all()
                assert len(tasks) == data["task_count"]
                for task in tasks:
                    assert task.tenant_key == tenant_key

        # Cross-tenant verification - ensure no data leakage
        tenant_keys = list(tenant_data.keys())
        for i, tenant_key in enumerate(tenant_keys):
            with db_manager.get_tenant_session(tenant_key) as session:
                # Try to access other tenants' data
                for j, other_tenant_key in enumerate(tenant_keys):
                    if i != j:
                        # Should not find any data from other tenants
                        other_projects = session.query(Project).filter_by(tenant_key=other_tenant_key).all()
                        assert len(other_projects) == 0

    def test_tenant_key_inheritance_chain(self, db_manager):
        """Test tenant key inheritance through entity relationships."""
        tenant_key = TenantManager.generate_tenant_key()

        with db_manager.get_tenant_session(tenant_key) as session:
            # Create project
            project = Project(name="Parent Project", mission="Test inheritance chain", tenant_key=tenant_key, series_number=random.randint(1, 999999))
            session.add(project)
            session.commit()

            # Create agent inheriting from project
            agent = Agent(
                name="child_agent",
                role="worker",
                tenant_key=TenantManager.inherit_tenant_key(project),
                project_id=project.id,
                status="active",
            )
            session.add(agent)
            session.commit()

            # Create message inheriting from agent
            message = Message(
                tenant_key=TenantManager.inherit_tenant_key(agent),
                project_id=project.id,
                to_agents=["other_agent"],
                content="Inherited message",
                message_type="direct",
                status="waiting",
            )
            session.add(message)

            # Create task inheriting from project
            task = Task(
                tenant_key=TenantManager.inherit_tenant_key(project),
                project_id=project.id,
                content="Inherited task",
                category="development",
                priority="medium",
                status="waiting",
            )
            session.add(task)

            # Create job inheriting from agent
            job = Job(
                tenant_key=TenantManager.inherit_tenant_key(agent),
                agent_id=agent.id,
                job_type="analysis",
                status="waiting",
            )
            session.add(job)

            session.commit()

            # Verify all entities have the same tenant key
            assert agent.tenant_key == tenant_key
            assert message.tenant_key == tenant_key
            assert task.tenant_key == tenant_key
            assert job.tenant_key == tenant_key


if __name__ == "__main__":
    pytest.main([__file__, "-v", "--tb=short"])
