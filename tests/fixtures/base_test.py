"""
Base test class with common functionality for all test classes.
"""

import asyncio
from pathlib import Path
from typing import Any
from unittest.mock import AsyncMock, Mock, patch


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
        from src.giljo_mcp.models.agent_identity import AgentJob, AgentExecution
        from tests.fixtures.base_fixtures import TestData

        # Create tenant key
        tenant_key = TestData.generate_tenant_key()

        # Create project
        project_data = TestData.generate_project_data(tenant_key)
        project = Project(**project_data)
        db_session.add(project)

        # Create agent jobs
        agent_jobs = []
        for agent_type in ["orchestrator", "analyzer", "implementer"]:
            job_data = TestData.generate_agent_job_data(project.id, tenant_key, agent_type)
            job = AgentExecution(**job_data)
            db_session.add(job)
            agent_jobs.append(job)

        await db_session.commit()

        return {"tenant_key": tenant_key, "project": project, "agent_jobs": agent_jobs}

    async def cleanup_test_environment(self, db_session, environment: dict):
        """Clean up test environment"""
        from src.giljo_mcp.models import Message, Project, Task
        from src.giljo_mcp.models.agent_identity import AgentJob, AgentExecution

        # Delete in order to respect foreign keys
        await db_session.query(Message).filter_by(project_id=environment["project"].id).delete()
        await db_session.query(Task).filter_by(project_id=environment["project"].id).delete()
        await db_session.query(AgentExecution).filter_by(project_id=environment["project"].id).delete()
        await db_session.query(Project).filter_by(id=environment["project"].id).delete()
        await db_session.commit()
