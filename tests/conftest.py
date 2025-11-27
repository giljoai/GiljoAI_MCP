"""
Pytest configuration for test suite
Provides test fixtures and database setup
"""

import asyncio
import os
import sys
from pathlib import Path

import pytest
import pytest_asyncio


# Add src to path
sys.path.insert(0, str(Path(__file__).parent.parent))

# Ensure config validation passes without real secrets
os.environ.setdefault("DB_PASSWORD", "test-password")


from src.giljo_mcp.config_manager import get_config
from src.giljo_mcp.services.orchestration_service import OrchestrationService
from src.giljo_mcp.services.product_service import ProductService
from src.giljo_mcp.services.project_service import ProjectService
from src.giljo_mcp.tenant import TenantManager

# Import PostgreSQL test fixtures from base_fixtures
from tests.fixtures.base_fixtures import (
    db_manager,
    db_session,
    e2e_closeout_fixtures,
    test_agent_jobs,
    test_messages,
    test_project,
)
from tests.helpers.async_helpers import AsyncMockManager, DatabaseTestHelper, TimeoutHelper
from tests.helpers.mock_servers import ExternalServiceMocks

# Import test helpers
from tests.helpers.test_factories import AgentFactory, MessageFactory, ProjectFactory


# Import pytest plugin for PostgreSQL database management
pytest_plugins = ["tests.pytest_postgresql_plugin"]

# Re-export fixtures so they're available to all tests
__all__ = [
    "db_manager",
    "db_session",
    "e2e_closeout_fixtures",
    "test_agent_jobs",
    "test_messages",
    "test_project",
]


@pytest.fixture(scope="session")
def event_loop():
    """Create event loop for async tests"""
    loop = asyncio.get_event_loop_policy().new_event_loop()
    yield loop
    loop.close()


@pytest_asyncio.fixture(scope="function")
async def test_db(db_manager):
    """
    Create a test database for each test.

    Note: This now returns the function-scoped PostgreSQL database manager.
    Test isolation is achieved through transaction rollback in db_session fixture.
    """
    yield db_manager


# Note: db_session fixture is imported from base_fixtures.py
# and provides transaction-based test isolation


@pytest_asyncio.fixture(scope="function")
async def tenant_manager() -> TenantManager:
    """Create tenant manager for testing"""
    return TenantManager()


@pytest_asyncio.fixture(scope="function")
async def orchestration_service_with_session(db_session, db_manager, tenant_manager):
    """OrchestrationService using shared test session for E2E/integration tests."""
    return OrchestrationService(
        db_manager=db_manager,
        tenant_manager=tenant_manager,
        test_session=db_session,
    )


@pytest_asyncio.fixture(scope="function")
async def project_service_with_session(db_session, db_manager, tenant_manager):
    """ProjectService using shared test session for E2E/integration tests."""
    return ProjectService(
        db_manager=db_manager,
        tenant_manager=tenant_manager,
        test_session=db_session,
    )


@pytest_asyncio.fixture(scope="function")
async def product_service_with_session(db_session, db_manager, test_project):
    """ProductService using shared test session for E2E/integration tests."""
    return ProductService(
        db_manager=db_manager,
        tenant_key=test_project.tenant_key,
        test_session=db_session,
    )


@pytest.fixture
def test_config():
    """Get test configuration"""
    from tests.helpers.test_db_helper import PostgreSQLTestHelper

    config = get_config()
    # Override with test settings - use PostgreSQL test database
    config.database.database_url = PostgreSQLTestHelper.get_test_db_url()
    # Note: config object may not have api/websocket attributes in newer versions
    # Only set if they exist
    if hasattr(config, 'api'):
        config.api.port = 7000  # Use different port for tests
    if hasattr(config, 'websocket'):
        config.websocket.port = 7001
    return config


# Note: db_manager fixture is imported from base_fixtures.py above

# Serena MCP test fixtures
@pytest.fixture
def temp_config_path(tmp_path):
    """Create temporary config.yaml for Serena tests."""
    import yaml

    config_path = tmp_path / "config.yaml"
    config_data = {
        "features": {"serena_mcp": {"enabled": False, "installed": False, "registered": False}},
        "services": {"api": {"port": 7272}},
    }
    config_path.write_text(yaml.dump(config_data))
    return config_path


@pytest.fixture
def temp_claude_json(tmp_path):
    """Create temporary .claude.json for Serena tests."""
    import json

    claude_path = tmp_path / ".claude.json"
    claude_path.write_text(
        json.dumps({"mcpServers": {"giljo-mcp": {"command": "python", "args": ["-m", "giljo_mcp"]}}})
    )
    return claude_path


@pytest.fixture
def mock_serena_detected(monkeypatch):
    """Mock Serena as detected."""
    import subprocess
    from unittest.mock import MagicMock

    def mock_run(cmd, *args, **kwargs):
        if "uvx" in cmd and "--version" in cmd:
            return MagicMock(returncode=0, stdout="uvx 0.1.0")
        if "uvx" in cmd and "serena" in cmd:
            return MagicMock(returncode=0, stdout="Serena MCP v1.2.3")
        return MagicMock(returncode=1)

    monkeypatch.setattr(subprocess, "run", mock_run)


@pytest.fixture
def mock_serena_not_detected(monkeypatch):
    """Mock Serena as not detected."""
    import subprocess

    def mock_run(*args, **kwargs):
        raise FileNotFoundError("uvx not found")

    monkeypatch.setattr(subprocess, "run", mock_run)


@pytest.fixture
def api_client():
    """Create FastAPI test client for API endpoint tests."""
    from fastapi.testclient import TestClient

    # Import the FastAPI app
    try:
        from api.app import app

        return TestClient(app)
    except ImportError:
        pytest.skip("API app not available")


@pytest_asyncio.fixture(scope="function")
async def test_project_id(db_session):
    """Create a test project and return its ID"""
    import uuid

    from src.giljo_mcp.models import Project

    project = Project(
        id=str(uuid.uuid4()),
        name="Test Project",
        description="Test project description for integration testing",
        mission="Test mission for integration testing",
        status="active",
        tenant_key=str(uuid.uuid4()),
    )

    db_session.add(project)
    await db_session.commit()

    return project.id


@pytest_asyncio.fixture(scope="function")
async def test_agent_job(db_session, test_project_id, test_tenant_key):
    """Create a test agent job"""
    import uuid
    from datetime import datetime, timezone

    from src.giljo_mcp.models import MCPAgentJob

    job = MCPAgentJob(
        job_id=str(uuid.uuid4()),
        tenant_key=test_tenant_key,
        project_id=test_project_id,
        agent_type="worker",
        mission="Test mission for worker agent",
        status="waiting",
        created_at=datetime.now(timezone.utc),
    )

    db_session.add(job)
    await db_session.commit()

    return job


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


@pytest_asyncio.fixture(scope="function")
async def async_client(db_manager):
    """
    Create AsyncClient for API testing with proper mocking of authentication.

    Note: This is a simplified fixture. For full API tests, authentication
    should be properly mocked using the dependency override pattern.
    """

    from httpx import AsyncClient as HTTPXAsyncClient

    # Mock the FastAPI app import (placeholder - real tests need full API setup)
    try:
        from api.app import app

        # Mock authentication dependencies
        from src.giljo_mcp.auth.dependencies import get_current_active_user, get_db_session

        async def mock_get_current_user():
            from datetime import datetime, timezone
            from uuid import uuid4

            from src.giljo_mcp.models import User

            # Return mock authenticated user
            return User(
                id=str(uuid4()),
                username="test_user",
                email="test@example.com",
                tenant_key="test_tenant",
                is_active=True,
                role="developer",
                created_at=datetime.now(timezone.utc),
                password_hash="hashed",
            )

        async def mock_get_db_session():
            async with db_manager.get_session_async() as session:
                yield session

        # Override dependencies
        app.dependency_overrides[get_current_active_user] = mock_get_current_user
        app.dependency_overrides[get_db_session] = mock_get_db_session

        from httpx import ASGITransport
        async with HTTPXAsyncClient(transport=ASGITransport(app=app), base_url="http://test") as client:
            yield client

        # Clear overrides
        app.dependency_overrides.clear()

    except ImportError:
        # If API not available, skip tests that need it
        pytest.skip("API application not available for testing")


def pytest_configure(config):
    """
    Pytest hook to configure test session.

    Disables coverage threshold enforcement for smoke tests, since they are
    integration workflow validators (not unit coverage targets).
    """
    # Check if we're only running smoke tests
    selected_tests = config.getoption("file_or_dir", default=[])
    markers = config.getoption("-m", default="")

    # If running smoke tests specifically, disable fail_under threshold
    if "smoke" in markers or any("smoke" in str(test) for test in selected_tests):
        # Store original fail_under value
        if hasattr(config, "_coverage_config"):
            # Access coverage plugin configuration
            try:
                cov_plugin = config.pluginmanager.get_plugin("_cov")
                if cov_plugin and hasattr(cov_plugin, "cov_controller"):
                    # Disable fail_under for smoke tests
                    cov_config = cov_plugin.cov_controller.cov.config
                    if hasattr(cov_config, "fail_under"):
                        cov_config.fail_under = None
            except (AttributeError, KeyError):
                # Coverage plugin not loaded or configured differently
                pass
