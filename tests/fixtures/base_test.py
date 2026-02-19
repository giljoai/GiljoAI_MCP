"""
Base test class with common functionality for all test classes.
"""

import asyncio
from pathlib import Path
from typing import Any
from unittest.mock import AsyncMock, Mock, patch
from uuid import uuid4


class BaseTest:
    """Base class for all test classes"""

    @classmethod
    def setup_class(cls):
        """Setup test class"""
        cls.test_data_dir = Path(__file__).parent.parent / "test_data"
        cls.test_data_dir.mkdir(exist_ok=True)

    @classmethod
    def teardown_class(cls):
        """Teardown test class"""

    def setup_method(self, method):
        """Setup each test method"""
        self.mocks = {}
        self.patches = []

    def teardown_method(self, method):
        """Teardown each test method"""
        # Stop all patches
        for patch_obj in self.patches:
            patch_obj.stop()
        self.patches.clear()
        self.mocks.clear()

    def create_mock(self, name: str, **kwargs) -> Mock:
        """Create and store a mock object"""
        mock = Mock(**kwargs)
        self.mocks[name] = mock
        return mock

    def create_async_mock(self, name: str, **kwargs) -> AsyncMock:
        """Create and store an async mock object"""
        mock = AsyncMock(**kwargs)
        self.mocks[name] = mock
        return mock

    def patch_object(self, target: Any, attribute: str, **kwargs) -> Mock:
        """Patch an object attribute and store the patch"""
        patch_obj = patch.object(target, attribute, **kwargs)
        mock = patch_obj.start()
        self.patches.append(patch_obj)
        return mock

    def patch_module(self, name: str, **kwargs) -> Mock:
        """Patch a module and store the patch"""
        patch_obj = patch(name, **kwargs)
        mock = patch_obj.start()
        self.patches.append(patch_obj)
        return mock

    @staticmethod
    def assert_dict_contains(actual: dict, expected: dict):
        """Assert that actual dict contains all expected key-value pairs"""
        for key, value in expected.items():
            assert key in actual, f"Key '{key}' not found in actual dict"
            assert actual[key] == value, f"Value mismatch for key '{key}': {actual[key]} != {value}"

    @staticmethod
    def assert_list_contains(actual: list, expected: Any):
        """Assert that actual list contains expected item"""
        assert expected in actual, f"Item {expected} not found in list"


class BaseAsyncTest(BaseTest):
    """Base class for async test classes"""

    def run_async(self, coro):
        """Run an async coroutine in the test"""
        return asyncio.run(coro)

    async def wait_for(self, coro, timeout: float = 5.0):
        """Wait for an async operation with timeout"""
        return await asyncio.wait_for(coro, timeout=timeout)

    async def gather_exceptions(self, *coros):
        """Gather async operations and return results even if some fail"""
        results = await asyncio.gather(*coros, return_exceptions=True)
        exceptions = [r for r in results if isinstance(r, Exception)]
        if exceptions:
            raise exceptions[0]
        return results

    def create_context_manager(self, mock_session):
        """Create an async context manager for database sessions"""

        class MockContextManager:
            def __init__(self, session):
                self.session = session

            async def __aenter__(self):
                return self.session

            async def __aexit__(self, exc_type, exc_val, exc_tb):
                pass

        return MockContextManager(mock_session)


class BaseIntegrationTest(BaseAsyncTest):
    """Base class for integration tests"""

    async def create_test_environment(self, db_session):
        """Create a complete test environment with projects, agent jobs, etc."""
        from src.giljo_mcp.models import Project
        from src.giljo_mcp.models.agent_identity import AgentExecution, AgentJob
        from tests.fixtures.base_fixtures import TestData

        # Create tenant key
        tenant_key = TestData.generate_tenant_key()

        # Create project
        project_data = TestData.generate_project_data(tenant_key)
        project = Project(**project_data)
        db_session.add(project)

        # Create agent jobs with executions (AgentJob -> AgentExecution)
        agent_jobs = []
        for agent_display_name in ["orchestrator", "analyzer", "implementer"]:
            # Create AgentJob (holds project_id, mission)
            job_data = TestData.generate_agent_job_data(project.id, tenant_key, agent_display_name)
            job = AgentJob(**job_data)
            db_session.add(job)

            # Create AgentExecution (FK to AgentJob)
            execution_data = TestData.generate_agent_execution_data(
                job.job_id, tenant_key, agent_display_name
            )
            execution = AgentExecution(**execution_data)
            db_session.add(execution)
            agent_jobs.append(execution)

        await db_session.commit()

        return {"tenant_key": tenant_key, "project": project, "agent_jobs": agent_jobs}

    async def cleanup_test_environment(self, db_session, environment: dict):
        """Clean up test environment"""
        from sqlalchemy import select

        from src.giljo_mcp.models import Message, Project, Task
        from src.giljo_mcp.models.agent_identity import AgentExecution, AgentJob

        project_id = environment["project"].id

        # Delete in order to respect foreign keys:
        # Messages and Tasks reference project directly
        # AgentExecution references AgentJob, AgentJob references Project

        # 1. Delete messages
        stmt = select(Message).where(Message.project_id == project_id)
        result = await db_session.execute(stmt)
        for msg in result.scalars().all():
            await db_session.delete(msg)

        # 2. Delete tasks
        stmt = select(Task).where(Task.project_id == project_id)
        result = await db_session.execute(stmt)
        for task in result.scalars().all():
            await db_session.delete(task)

        # 3. Delete agent executions (FK child of agent_jobs)
        stmt = select(AgentJob).where(AgentJob.project_id == project_id)
        result = await db_session.execute(stmt)
        jobs = result.scalars().all()
        for job in jobs:
            exec_stmt = select(AgentExecution).where(AgentExecution.job_id == job.job_id)
            exec_result = await db_session.execute(exec_stmt)
            for execution in exec_result.scalars().all():
                await db_session.delete(execution)

        # 4. Delete agent jobs (FK child of projects)
        for job in jobs:
            await db_session.delete(job)

        # 5. Delete project
        stmt = select(Project).where(Project.id == project_id)
        result = await db_session.execute(stmt)
        project = result.scalar_one_or_none()
        if project:
            await db_session.delete(project)

        await db_session.commit()
