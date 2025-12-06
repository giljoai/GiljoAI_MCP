"""
Test utilities and helpers for tools testing
"""

import asyncio
import uuid
from datetime import datetime, timezone
from pathlib import Path
from typing import Any, Optional
from unittest.mock import MagicMock

from sqlalchemy.ext.asyncio import AsyncSession

from src.giljo_mcp.models import Configuration, ContextIndex, MCPAgentJob, Message, Project, Task, Vision
from src.giljo_mcp.tenant import TenantManager


class ToolsTestHelper:
    """Helper class for tools testing"""

    @staticmethod
    async def create_test_project(session: AsyncSession, name: str = "Test Project") -> Project:
        """Create a test project in the database"""
        project = Project(
            id=str(uuid.uuid4()),
            name=name,
            description="Test project description for tools testing",
            mission="Test mission for tools testing",
            status="active",
            tenant_key=TenantManager.generate_tenant_key(name),
            context_budget=100000,
            context_used=0,
            created_at=datetime.now(timezone.utc),
        )
        session.add(project)
        await session.commit()
        await session.refresh(project)
        return project

    @staticmethod
    async def create_test_agent(session: AsyncSession, project_id: str, name: str = "test_agent") -> MCPAgentJob:
        """Create a test agent job in the database"""
        agent_job = MCPAgentJob(
            job_id=str(uuid.uuid4()),
            agent_name=name,
            agent_type="worker",
            status="active",
            project_id=project_id,
            tenant_key=TenantManager.generate_tenant_key(name),
            created_at=datetime.now(timezone.utc),
        )
        session.add(agent_job)
        await session.commit()
        await session.refresh(agent_job)
        return agent_job

    @staticmethod
    async def create_test_message(
        session: AsyncSession,
        project_id: str,
        from_agent: str = "orchestrator",
        to_agent: str = "test_agent",
        content: str = "Test message",
    ) -> Message:
        """Create a test message in the database"""
        message = Message(
            id=str(uuid.uuid4()),
            from_agent=from_agent,
            to_agent=to_agent,
            content=content,
            type="direct",
            priority="normal",
            status="waiting",
            project_id=project_id,
            tenant_key=TenantManager.generate_tenant_key(),
            created_at=datetime.now(timezone.utc),
        )
        session.add(message)
        await session.commit()
        await session.refresh(message)
        return message

    @staticmethod
    async def create_test_task(
        session: AsyncSession, project_id: str, title: str = "Test Task", status: str = "pending"
    ) -> Task:
        """Create a test task in the database"""
        task = Task(
            id=str(uuid.uuid4()),
            title=title,
            description="Test task description",
            status=status,
            priority="medium",
            project_id=project_id,
            tenant_key=TenantManager.generate_tenant_key(),
            created_at=datetime.now(timezone.utc),
        )
        session.add(task)
        await session.commit()
        await session.refresh(task)
        return task

    @staticmethod
    async def create_test_vision(
        session: AsyncSession,
        project_id: str,
        tenant_key: str,
        document_name: str = "test.md",
        content: str = "Test vision content",
    ) -> Vision:
        """Create a test vision document in the database"""
        vision = Vision(
            id=str(uuid.uuid4()),
            tenant_key=tenant_key,
            project_id=project_id,
            document_name=document_name,
            chunk_number=1,
            total_chunks=1,
            content=content,
            tokens=100,
            char_start=0,
            char_end=len(content),
            boundary_type="document",
            keywords=["test"],
            headers=["# Test"],
            created_at=datetime.now(timezone.utc),
        )
        session.add(vision)
        await session.commit()
        await session.refresh(vision)
        return vision

    @staticmethod
    async def create_test_context_index(
        session: AsyncSession, project_id: str, tenant_key: str, document_name: str = "test.md"
    ) -> ContextIndex:
        """Create a test context index in the database"""
        index = ContextIndex(
            id=str(uuid.uuid4()),
            tenant_key=tenant_key,
            project_id=project_id,
            index_type="vision",
            document_name=document_name,
            chunk_numbers=[1],
            summary="Test document summary",
            token_count=100,
            keywords=["test"],
            full_path=f"docs/Vision/{document_name}",
            content_hash="abc123",
            created_at=datetime.now(timezone.utc),
        )
        session.add(index)
        await session.commit()
        await session.refresh(index)
        return index

    @staticmethod
    async def create_test_configuration(
        session: AsyncSession, project_id: str, tenant_key: str, key: str = "test_config", value: str = "test_value"
    ) -> Configuration:
        """Create a test configuration in the database"""
        config = Configuration(
            id=str(uuid.uuid4()),
            tenant_key=tenant_key,
            project_id=project_id,
            key=key,
            value=value,
            category="test",
            created_at=datetime.now(timezone.utc),
        )
        session.add(config)
        await session.commit()
        await session.refresh(config)
        return config


class MockMCPToolRegistrar:
    """Helper to register and test MCP tools"""

    def __init__(self):
        self.registered_tools = {}
        self.mock_server = MagicMock()
        self.mock_server.tool = MagicMock()

    def create_tool_decorator(self):
        """Create a tool decorator that captures registered functions"""

        def tool_decorator():
            def decorator(func):
                self.registered_tools[func.__name__] = func
                return func

            return decorator

        self.mock_server.tool.return_value = tool_decorator()
        return self.mock_server

    def get_registered_tool(self, name: str):
        """Get a registered tool function by name"""
        return self.registered_tools.get(name)

    def get_all_tools(self) -> list[str]:
        """Get names of all registered tools"""
        return list(self.registered_tools.keys())


class AssertionHelpers:
    """Collection of assertion helpers for tools testing"""

    @staticmethod
    def assert_success_response(response: dict[str, Any], expected_keys: Optional[list[str]] = None):
        """Assert that a response indicates success and has expected keys"""
        assert response.get("success") is True, f"Expected success=True, got: {response}"

        if expected_keys:
            for key in expected_keys:
                assert key in response, f"Expected key '{key}' in response: {response}"

    @staticmethod
    def assert_error_response(response: dict[str, Any], expected_error: Optional[str] = None):
        """Assert that a response indicates failure with optional error message check"""
        assert response.get("success") is False, f"Expected success=False, got: {response}"
        assert "error" in response, f"Expected 'error' key in response: {response}"

        if expected_error:
            assert expected_error in response["error"], f"Expected error '{expected_error}' in '{response['error']}'"

    @staticmethod
    def assert_tool_registered(registrar: MockMCPToolRegistrar, tool_name: str):
        """Assert that a tool was registered with the MCP server"""
        assert tool_name in registrar.get_all_tools(), (
            f"Tool '{tool_name}' not registered. Available tools: {registrar.get_all_tools()}"
        )

    @staticmethod
    def assert_database_state(
        session: AsyncSession, model_class, expected_count: int, filters: Optional[dict[str, Any]] = None
    ):
        """Assert the state of the database for a given model"""
        # This would need to be implemented as an async function in actual usage


class PerformanceTestHelpers:
    """Helpers for performance testing of tools"""

    @staticmethod
    async def measure_tool_performance(tool_func, *args, **kwargs) -> float:
        """Measure the execution time of a tool function in milliseconds"""
        import time

        start_time = time.perf_counter()
        await tool_func(*args, **kwargs)
        end_time = time.perf_counter()

        return (end_time - start_time) * 1000  # Convert to milliseconds

    @staticmethod
    async def run_performance_benchmark(tool_func, iterations: int = 10, *args, **kwargs) -> dict[str, float]:
        """Run a performance benchmark for a tool function"""
        times = []

        for _ in range(iterations):
            execution_time = await PerformanceTestHelpers.measure_tool_performance(tool_func, *args, **kwargs)
            times.append(execution_time)

        return {"average": sum(times) / len(times), "min": min(times), "max": max(times), "iterations": iterations}


class FileSystemTestHelpers:
    """Helpers for testing file system operations"""

    @staticmethod
    def create_test_vision_directory(base_path: Path) -> Path:
        """Create a test vision directory with sample files"""
        vision_dir = base_path / "docs" / "Vision"
        vision_dir.mkdir(parents=True, exist_ok=True)

        # Create sample vision files
        files = {
            "overview.md": """# Project Overview
This is a comprehensive overview of the project.

## Mission
The mission is to create a robust system.

## Goals
- Achieve high coverage
- Maintain quality
""",
            "architecture.md": """# Architecture
The system follows a modular design.

## Components
- Database layer
- API layer
- Business logic
""",
            "requirements.md": """# Requirements
Functional and non-functional requirements.

## Functional
- User management
- Project management

## Non-functional
- Performance
- Security
""",
        }

        for filename, content in files.items():
            (vision_dir / filename).write_text(content)

        return vision_dir

    @staticmethod
    def create_large_test_document(path: Path, size_kb: int = 100) -> Path:
        """Create a large test document for chunking tests"""
        content = "# Large Test Document\n\n"

        # Generate content to reach approximately the desired size
        section_content = "This is a test section with enough content to make the document large. " * 50

        sections_needed = (size_kb * 1024) // len(section_content)

        for i in range(sections_needed):
            content += f"## Section {i + 1}\n\n{section_content}\n\n"

        path.write_text(content)
        return path


class AsyncTestHelpers:
    """Helpers for async testing scenarios"""

    @staticmethod
    async def wait_for_condition(condition_func, timeout_seconds: float = 5.0, check_interval: float = 0.1) -> bool:
        """Wait for a condition to become true with timeout"""
        start_time = asyncio.get_event_loop().time()

        while True:
            if await condition_func() if asyncio.iscoroutinefunction(condition_func) else condition_func():
                return True

            if asyncio.get_event_loop().time() - start_time > timeout_seconds:
                return False

            await asyncio.sleep(check_interval)

    @staticmethod
    async def run_with_timeout(coro, timeout_seconds: float = 10.0):
        """Run a coroutine with a timeout"""
        try:
            return await asyncio.wait_for(coro, timeout=timeout_seconds)
        except asyncio.TimeoutError:
            raise AssertionError(f"Operation timed out after {timeout_seconds} seconds")
