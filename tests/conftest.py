"""
Pytest configuration for test suite
Provides test fixtures and database setup
"""

import asyncio
import os
import sys
import tempfile
from collections.abc import AsyncGenerator
from pathlib import Path

import pytest
import pytest_asyncio


# Add src to path
sys.path.insert(0, str(Path(__file__).parent.parent))

import builtins
import contextlib

from sqlalchemy.ext.asyncio import AsyncSession

from src.giljo_mcp.config_manager import get_config
from src.giljo_mcp.database import DatabaseManager
from src.giljo_mcp.tenant import TenantManager
from tests.helpers.async_helpers import AsyncMockManager, DatabaseTestHelper, TimeoutHelper
from tests.helpers.mock_servers import ExternalServiceMocks

# Import test helpers
from tests.helpers.test_factories import AgentFactory, MessageFactory, ProjectFactory


@pytest.fixture(scope="session")
def event_loop():
    """Create event loop for async tests"""
    loop = asyncio.get_event_loop_policy().new_event_loop()
    yield loop
    loop.close()


@pytest_asyncio.fixture(scope="function")
async def test_db():
    """Create a test database for each test"""
    # Create temporary database file
    temp_db = tempfile.NamedTemporaryFile(suffix=".db", delete=False)
    temp_db.close()

    # Create database manager with test database
    connection_string = f"sqlite+aiosqlite:///{temp_db.name}"
    db_manager = DatabaseManager(connection_string, is_async=True)

    # Initialize database
    await db_manager.create_tables_async()

    yield db_manager

    # Cleanup
    await db_manager.close_async()
    with contextlib.suppress(builtins.BaseException):
        os.unlink(temp_db.name)


@pytest_asyncio.fixture(scope="function")
async def db_session(test_db) -> AsyncGenerator[AsyncSession, None]:
    """Get database session for testing"""
    async with test_db.get_session_async() as session:
        yield session


@pytest_asyncio.fixture(scope="function")
async def tenant_manager() -> TenantManager:
    """Create tenant manager for testing"""
    return TenantManager()


@pytest.fixture
def test_config():
    """Get test configuration"""
    config = get_config()
    # Override with test settings
    config.database.database_url = "sqlite+aiosqlite:///:memory:"
    config.api.port = 7000  # Use different port for tests
    config.websocket.port = 7001
    return config


@pytest_asyncio.fixture(scope="function")
async def test_project_id(db_session):
    """Create a test project and return its ID"""
    import uuid

    from src.giljo_mcp.models import Project

    project = Project(
        id=str(uuid.uuid4()),
        name="Test Project",
        mission="Test mission for integration testing",
        status="active",
        tenant_key=str(uuid.uuid4()),
    )

    db_session.add(project)
    await db_session.commit()

    return project.id


@pytest_asyncio.fixture(scope="function")
async def test_agent(db_session, test_project_id):
    """Create a test agent"""
    import uuid
    from datetime import datetime, timezone

    from src.giljo_mcp.models import Agent

    agent = Agent(
        id=str(uuid.uuid4()),
        name="test_agent",
        type="worker",
        status="active",
        project_id=test_project_id,
        created_at=datetime.now(timezone.utc),
    )

    db_session.add(agent)
    await db_session.commit()

    return agent


# Performance benchmarking fixtures
@pytest.fixture
def benchmark_timer():
    """Simple timer for performance benchmarking"""
    import time

    class Timer:
        def __init__(self):
            self.times = []

        def start(self):
            self.start_time = time.perf_counter()

        def stop(self):
            elapsed = (time.perf_counter() - self.start_time) * 1000  # Convert to ms
            self.times.append(elapsed)
            return elapsed

        def average(self):
            return sum(self.times) / len(self.times) if self.times else 0

        def max(self):
            return max(self.times) if self.times else 0

        def min(self):
            return min(self.times) if self.times else 0

    return Timer()


# Additional test fixtures using new helpers
@pytest.fixture
def project_factory():
    """Factory for creating test projects"""
    return ProjectFactory


@pytest.fixture
def agent_factory():
    """Factory for creating test agents"""
    return AgentFactory


@pytest.fixture
def message_factory():
    """Factory for creating test messages"""
    return MessageFactory


@pytest.fixture
def timeout_helper():
    """Helper for testing timeouts and conditions"""
    return TimeoutHelper


@pytest.fixture
def db_helper():
    """Helper for database testing operations"""
    return DatabaseTestHelper


@pytest.fixture
def external_mocks():
    """Collection of external service mocks"""
    return ExternalServiceMocks


@pytest_asyncio.fixture(scope="function")
async def async_mock_manager():
    """Manager for async mocks with automatic cleanup"""
    manager = AsyncMockManager()
    yield manager
    manager.cleanup()


@pytest.fixture
def sample_project_data():
    """Sample project data for testing"""
    return {"name": "Test Project", "mission": "Test mission for unit testing", "status": "active"}


@pytest.fixture
def sample_agent_data():
    """Sample agent data for testing"""
    return {"name": "test_agent", "type": "worker", "status": "active"}


@pytest.fixture
def sample_message_data():
    """Sample message data for testing"""
    return {"from_agent": "orchestrator", "content": "Test message content", "type": "direct", "priority": "normal"}


# Tools testing fixtures
@pytest_asyncio.fixture(scope="function")
async def mock_mcp_server():
    """Mock FastMCP server for tools testing"""
    from unittest.mock import MagicMock

    mock_server = MagicMock()
    mock_server.tool = MagicMock()

    # Create a decorator that stores the function for testing
    def tool_decorator():
        def decorator(func):
            # Store the function for later testing
            if not hasattr(mock_server, "_registered_tools"):
                mock_server._registered_tools = {}
            mock_server._registered_tools[func.__name__] = func
            return func

        return decorator

    mock_server.tool.return_value = tool_decorator()
    return mock_server


@pytest_asyncio.fixture(scope="function")
async def mock_discovery_manager():
    """Mock DiscoveryManager for tools testing"""
    from pathlib import Path
    from unittest.mock import AsyncMock, MagicMock

    mock_discovery = MagicMock()

    # Mock discovery methods
    mock_discovery.discover_context = AsyncMock(
        return_value={
            "priority": {"vision": [], "sessions": [], "devlog": []},
            "context_budget": 100000,
            "agent_role": "default",
        }
    )

    mock_discovery.get_discovery_paths = AsyncMock(
        return_value={
            "vision": Path("docs/vision"),
            "sessions": Path("docs/sessions"),
            "devlog": Path("docs/devlog"),
            "claude": Path("CLAUDE.md"),
        }
    )

    mock_discovery.detect_changes = AsyncMock(return_value={})
    mock_discovery.PRIORITY_ORDER = ["vision", "sessions", "devlog", "claude"]

    return mock_discovery


@pytest_asyncio.fixture(scope="function")
async def mock_path_resolver():
    """Mock PathResolver for tools testing"""
    from pathlib import Path
    from unittest.mock import AsyncMock, MagicMock

    mock_resolver = MagicMock()

    # Mock path resolution
    mock_resolver.resolve_path = AsyncMock(return_value=Path("tests/temp"))
    mock_resolver.get_all_paths = AsyncMock(
        return_value={"vision": Path("docs/vision"), "sessions": Path("docs/sessions"), "devlog": Path("docs/devlog")}
    )

    mock_resolver.DEFAULT_PATHS = {"vision": "docs/vision", "sessions": "docs/sessions", "devlog": "docs/devlog"}

    return mock_resolver


@pytest_asyncio.fixture(scope="function")
async def mock_chunker():
    """Mock EnhancedChunker for tools testing"""
    from unittest.mock import MagicMock

    mock_chunker = MagicMock()

    # Mock chunking methods
    mock_chunker.chunk_multiple_documents.return_value = [
        {
            "document_name": "test.md",
            "chunk_number": 1,
            "total_chunks": 1,
            "content": "Test content",
            "tokens": 100,
            "char_start": 0,
            "char_end": 100,
            "boundary_type": "document",
            "keywords": ["test"],
            "headers": ["# Test"],
        }
    ]

    mock_chunker.chunk_content.return_value = [
        {
            "chunk_number": 1,
            "total_chunks": 1,
            "content": "Test content",
            "tokens": 100,
            "char_start": 0,
            "char_end": 100,
            "boundary_type": "document",
            "keywords": ["test"],
            "headers": ["# Test"],
        }
    ]

    mock_chunker.estimate_tokens.return_value = 100
    mock_chunker.extract_keywords.return_value = ["test", "content"]
    mock_chunker.calculate_content_hash.return_value = "abc123"

    return mock_chunker


@pytest_asyncio.fixture(scope="function")
async def tools_test_setup(
    test_db, tenant_manager, mock_mcp_server, mock_discovery_manager, mock_path_resolver, mock_chunker
):
    """Complete tools testing setup with all mocks"""
    from unittest.mock import patch

    # Patch the imports in tools modules
    patches = [
        patch("src.giljo_mcp.tools.context.DiscoveryManager", return_value=mock_discovery_manager),
        patch("src.giljo_mcp.tools.context.PathResolver", return_value=mock_path_resolver),
        patch("src.giljo_mcp.tools.context.EnhancedChunker", return_value=mock_chunker),
    ]

    for p in patches:
        p.start()

    yield {
        "db_manager": test_db,
        "tenant_manager": tenant_manager,
        "mcp_server": mock_mcp_server,
        "discovery_manager": mock_discovery_manager,
        "path_resolver": mock_path_resolver,
    }

    # Stop all patches
    for p in patches:
        p.stop()


@pytest.fixture
def vision_test_files(tmp_path):
    """Create temporary vision files for testing"""
    vision_dir = tmp_path / "docs" / "Vision"
    vision_dir.mkdir(parents=True)

    # Create test vision files
    (vision_dir / "overview.md").write_text(
        """
# Project Overview
This is a test vision document with multiple sections.

## Architecture
The system follows a modular design.

## Goals
- Achieve 95% test coverage
- Maintain code quality
"""
    )

    (vision_dir / "technical_spec.md").write_text(
        """
# Technical Specification
Detailed technical requirements.

## Database Design
Using SQLAlchemy with async support.

## API Design
REST API with FastAPI framework.
"""
    )

    return vision_dir


@pytest.fixture
def mock_message_queue():
    """Mock message queue for testing"""
    from unittest.mock import AsyncMock, MagicMock

    mock_queue = MagicMock()
    mock_queue.send_message = AsyncMock(return_value={"success": True, "message_id": "test-msg-123"})
    mock_queue.get_messages = AsyncMock(return_value={"success": True, "messages": []})
    mock_queue.acknowledge_message = AsyncMock(return_value={"success": True})
    mock_queue.complete_message = AsyncMock(return_value={"success": True})

    return mock_queue
