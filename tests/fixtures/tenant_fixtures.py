"""
Test fixtures for multi-tenant testing scenarios.

These fixtures provide utilities for creating, managing, and cleaning up
test tenants and their associated data.
"""

import asyncio
import random
import uuid
from contextlib import contextmanager
from datetime import datetime
from typing import Any, Optional

from src.giljo_mcp.database import get_db_manager
from src.giljo_mcp.models import Message, Project, Task
from src.giljo_mcp.models.agent_identity import AgentExecution


class TenantFixture:
    """Manages test tenant lifecycle and data generation."""

    def __init__(self):
        self.db_manager = get_db_manager()
        self.created_tenants: list[str] = []
        self.tenant_data: dict[str, dict[str, Any]] = {}

    def generate_tenant_key(self, prefix: str = "test") -> str:
        """
        Generate a unique tenant key for testing.

        Args:
            prefix: Prefix for the tenant key

        Returns:
            Unique tenant key string
        """
        unique_id = uuid.uuid4().hex[:8]
        timestamp = datetime.now().strftime("%Y%m%d%H%M%S")
        return f"{prefix}_{timestamp}_{unique_id}"

    def create_test_tenant(
        self,
        tenant_key: Optional[str] = None,
        project_name: Optional[str] = None,
        with_agents: int = 0,
        with_messages: int = 0,
        with_tasks: int = 0,
    ) -> dict[str, Any]:
        """
        Create a test tenant with optional related data.

        Args:
            tenant_key: Specific tenant key to use (auto-generated if None)
            project_name: Name for the test project
            with_agents: Number of agents to create
            with_messages: Number of messages to create
            with_tasks: Number of tasks to create

        Returns:
            Dictionary containing created tenant data
        """
        if tenant_key is None:
            tenant_key = self.generate_tenant_key()

        if project_name is None:
            project_name = f"Test Project {tenant_key[:8]}"

        with self.db_manager.get_session() as session:
            # Create project
            project = Project(
                id=str(uuid.uuid4()),
                tenant_key=tenant_key,
                name=project_name,
                description=f"Test project for tenant {tenant_key}",
                mission=f"Test mission for tenant {tenant_key}",
                status="active",
                context_budget=150000,
                context_used=0,
            )
            session.add(project)

            # Create agent jobs if requested
            agent_jobs = []
            for i in range(with_agents):
                job = AgentExecution(
                    job_id=str(uuid.uuid4()),
                    tenant_key=tenant_key,
                    project_id=project.id,
                    agent_display_name=random.choice(["analyzer", "implementer", "tester", "reviewer"]),
                    mission=f"Test mission for agent {i}",
                    status="waiting",
                )
                agent_jobs.append(job)
                session.add(job)

            # Create messages if requested
            messages = []
            for i in range(with_messages):
                # Select random sender and receiver from agents
                if agents:
                    sender = random.choice([*agents, None])
                    receiver = random.choice(agents)

                    message = Message(
                        id=str(uuid.uuid4()),
                        tenant_key=tenant_key,
                        project_id=project.id,
                        from_agent=sender.name if sender else "orchestrator",
                        to_agents=[receiver.name],
                        content=f"Test message {i} for tenant {tenant_key}",
                        message_type="direct",
                        status="waiting",
                        priority="normal",
                    )
                    messages.append(message)
                    session.add(message)

            # Create tasks if requested
            tasks = []
            for i in range(with_tasks):
                task = Task(
                    id=str(uuid.uuid4()),
                    tenant_key=tenant_key,
                    project_id=project.id,
                    content=f"Test task {i} for tenant {tenant_key}",
                    category=random.choice(["development", "testing", "documentation"]),
                    priority=random.choice(["low", "medium", "high"]),
                    status="waiting",
                )
                tasks.append(task)
                session.add(task)

            session.commit()

            # Store tenant data for cleanup
            self.created_tenants.append(tenant_key)
            self.tenant_data[tenant_key] = {"project": project, "agents": agents, "messages": messages, "tasks": tasks}

            return self.tenant_data[tenant_key]

    def create_multiple_tenants(self, count: int, **kwargs) -> list[dict[str, Any]]:
        """
        Create multiple test tenants with specified configuration.

        Args:
            count: Number of tenants to create
            **kwargs: Additional arguments passed to create_test_tenant

        Returns:
            List of tenant data dictionaries
        """
        tenants = []
        for i in range(count):
            tenant_data = self.create_test_tenant(project_name=f"Test Project {i}", **kwargs)
            tenants.append(tenant_data)
        return tenants

    async def create_test_tenant_async(
        self,
        tenant_key: Optional[str] = None,
        project_name: Optional[str] = None,
        with_agents: int = 0,
        with_messages: int = 0,
        with_tasks: int = 0,
    ) -> dict[str, Any]:
        """
        Async version of create_test_tenant for concurrent testing.
        """
        if tenant_key is None:
            tenant_key = self.generate_tenant_key()

        if project_name is None:
            project_name = f"Test Project {tenant_key[:8]}"

        async with self.db_manager.get_session_async() as session:
            # Create project
            project = Project(
                id=str(uuid.uuid4()),
                tenant_key=tenant_key,
                name=project_name,
                description=f"Test project for tenant {tenant_key}",
                mission=f"Test mission for tenant {tenant_key}",
                status="active",
                context_budget=150000,
                context_used=0,
            )
            session.add(project)

            # Similar logic for agents, messages, tasks...
            await session.commit()

            # Store tenant data
            self.created_tenants.append(tenant_key)
            tenant_data = {"project": project, "agents": [], "messages": [], "tasks": []}
            self.tenant_data[tenant_key] = tenant_data

            return tenant_data

    async def create_concurrent_tenants(self, count: int, **kwargs) -> list[dict[str, Any]]:
        """
        Create multiple tenants concurrently for stress testing.

        Args:
            count: Number of tenants to create concurrently
            **kwargs: Additional arguments for tenant creation

        Returns:
            List of created tenant data
        """
        tasks = []
        for i in range(count):
            task = self.create_test_tenant_async(project_name=f"Concurrent Project {i}", **kwargs)
            tasks.append(task)

        return await asyncio.gather(*tasks)

    def cleanup_tenant(self, tenant_key: str) -> None:
        """
        Clean up all data for a specific tenant.

        Args:
            tenant_key: The tenant key to clean up
        """
        with self.db_manager.get_session() as session:
            # Delete in reverse order of dependencies
            session.query(Task).filter_by(tenant_key=tenant_key).delete()
            session.query(Message).filter_by(tenant_key=tenant_key).delete()
            session.query(AgentExecution).filter_by(tenant_key=tenant_key).delete()
            # NOTE: Session model deleted (Handover 0423 - dead code cleanup)
            session.query(Project).filter_by(tenant_key=tenant_key).delete()
            session.commit()

        # Remove from tracking
        if tenant_key in self.created_tenants:
            self.created_tenants.remove(tenant_key)
        if tenant_key in self.tenant_data:
            del self.tenant_data[tenant_key]

    def cleanup_all_tenants(self) -> None:
        """Clean up all created test tenants."""
        for tenant_key in list(self.created_tenants):
            self.cleanup_tenant(tenant_key)

    @contextmanager
    def tenant_context(self, tenant_key: str):
        """
        Context manager for tenant-scoped operations.

        Args:
            tenant_key: The tenant key to use for operations

        Yields:
            Tenant key for use in with block
        """
        # Store current context (if any)
        previous_context = getattr(self, "_current_tenant", None)

        try:
            # Set new context
            self._current_tenant = tenant_key
            yield tenant_key
        finally:
            # Restore previous context
            self._current_tenant = previous_context

    def switch_tenant_context(self, tenant_key: str) -> str:
        """
        Switch the current tenant context.

        Args:
            tenant_key: The tenant key to switch to

        Returns:
            The new tenant key
        """
        self._current_tenant = tenant_key
        return tenant_key

    def get_current_tenant(self) -> Optional[str]:
        """
        Get the current tenant context.

        Returns:
            Current tenant key or None
        """
        return getattr(self, "_current_tenant", None)

    def generate_random_data(self, tenant_key: str, entity_type: str, count: int) -> list[Any]:
        """
        Generate random test data for a specific entity type.

        Args:
            tenant_key: Tenant key for the data
            entity_type: Type of entity to generate
            count: Number of entities to create

        Returns:
            List of created entities
        """
        entities = []

        with self.db_manager.get_session() as session:
            project = session.query(Project).filter_by(tenant_key=tenant_key).first()

            if not project:
                raise ValueError(f"No project found for tenant {tenant_key}")

            for i in range(count):
                if entity_type == "agent":
                    entity = AgentExecution(
                        job_id=str(uuid.uuid4()),
                        tenant_key=tenant_key,
                        project_id=project.id,
                        agent_display_name=random.choice(["analyzer", "implementer", "tester"]),
                        mission=f"Random mission for agent {i}",
                        status="waiting",
                    )
                elif entity_type == "message":
                    entity = Message(
                        id=str(uuid.uuid4()),
                        tenant_key=tenant_key,
                        project_id=project.id,
                        from_agent=f"agent_{random.randint(0, 10)}",
                        to_agents=[f"agent_{random.randint(0, 10)}"],
                        content=f"Random message {i}",
                        message_type="direct",
                        status="waiting",
                        priority=random.choice(["low", "normal", "high"]),
                    )
                elif entity_type == "task":
                    entity = Task(
                        id=str(uuid.uuid4()),
                        tenant_key=tenant_key,
                        project_id=project.id,
                        content=f"Random task {i}",
                        category=random.choice(["dev", "test", "docs"]),
                        priority=random.choice(["low", "medium", "high"]),
                        status="waiting",
                    )
                else:
                    raise ValueError(f"Unknown entity type: {entity_type}")

                entities.append(entity)
                session.add(entity)

            session.commit()

        return entities


# Global fixture instance
fixture = TenantFixture()


# Convenience functions
def create_test_tenant(**kwargs) -> dict[str, Any]:
    """Create a single test tenant."""
    return fixture.create_test_tenant(**kwargs)


def create_multiple_tenants(count: int, **kwargs) -> list[dict[str, Any]]:
    """Create multiple test tenants."""
    return fixture.create_multiple_tenants(count, **kwargs)


def cleanup_tenant(tenant_key: str) -> None:
    """Clean up a specific tenant."""
    fixture.cleanup_tenant(tenant_key)


def cleanup_all_tenants() -> None:
    """Clean up all test tenants."""
    fixture.cleanup_all_tenants()


def switch_tenant_context(tenant_key: str) -> str:
    """Switch tenant context."""
    return fixture.switch_tenant_context(tenant_key)


@contextmanager
def tenant_context(tenant_key: str):
    """Context manager for tenant operations."""
    with fixture.tenant_context(tenant_key) as ctx:
        yield ctx
