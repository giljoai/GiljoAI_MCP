"""
Integration test fixtures for Handover 0316
"""

import random
from datetime import datetime, timezone
from unittest.mock import AsyncMock, MagicMock
from uuid import uuid4

import pytest
import pytest_asyncio
from httpx import ASGITransport, AsyncClient
from sqlalchemy.ext.asyncio import AsyncSession

from src.giljo_mcp.database import DatabaseManager
from src.giljo_mcp.models import Product, Project, User
from src.giljo_mcp.models.agent_identity import AgentExecution
from src.giljo_mcp.models.tasks import Message
from src.giljo_mcp.tenant import TenantManager


@pytest.fixture
def mock_db_manager():
    """Mock database manager for integration tests."""
    from contextlib import asynccontextmanager

    db_manager = MagicMock()
    # Add get_product and get_project as AsyncMock methods
    db_manager.get_product = AsyncMock()
    db_manager.get_project = AsyncMock()
    # Session support - create proper async context manager
    session = AsyncMock()
    session.__aenter__ = AsyncMock(return_value=session)
    session.__aexit__ = AsyncMock(return_value=False)
    session.get = AsyncMock()
    session.commit = AsyncMock()
    session.refresh = AsyncMock()

    @asynccontextmanager
    async def mock_get_session_async():
        yield session

    db_manager.get_session_async = mock_get_session_async
    # Legacy sync session support (deprecated but kept for backward compatibility)
    db_manager.get_session = MagicMock(return_value=session)
    return db_manager


@pytest_asyncio.fixture
async def test_user(db_session: AsyncSession):
    """Create test user with tenant"""
    from src.giljo_mcp.models.organizations import Organization

    unique_suffix = uuid4().hex[:8]
    tenant_key = TenantManager.generate_tenant_key()  # 0424m: Generate before org creation

    # Create org first (0424m: org_id is NOT NULL, tenant_key required)
    org = Organization(
        name=f"Test User Org {unique_suffix}",
        slug=f"test-user-org-{unique_suffix}",
        tenant_key=tenant_key,  # 0424m: Required NOT NULL
        is_active=True,
    )
    db_session.add(org)
    await db_session.flush()

    user = User(
        username=f"testuser_{unique_suffix}",
        email=f"test_{uuid4().hex[:8]}@example.com",
        tenant_key=tenant_key,  # 0424m: Use same tenant_key
        role="developer",
        password_hash="hashed_password",
        org_id=org.id,  # Required after 0424j
    )
    db_session.add(user)
    await db_session.commit()
    await db_session.refresh(user)
    return user


@pytest.fixture(autouse=True)
def set_tenant_context(test_user: User):
    """Ensure TenantManager is set to the primary test user's tenant."""
    TenantManager.set_current_tenant(test_user.tenant_key)
    return test_user.tenant_key


@pytest_asyncio.fixture
async def test_user_2(db_session: AsyncSession):
    """Create second test user (different tenant for isolation tests)"""
    from src.giljo_mcp.models.organizations import Organization

    unique_suffix = uuid4().hex[:8]
    tenant_key = TenantManager.generate_tenant_key()  # 0424m: Generate before org creation

    # Create org first (0424m: org_id is NOT NULL, tenant_key required)
    org = Organization(
        name=f"Test User 2 Org {unique_suffix}",
        slug=f"test-user-2-org-{unique_suffix}",
        tenant_key=tenant_key,  # 0424m: Required NOT NULL
        is_active=True,
    )
    db_session.add(org)
    await db_session.flush()

    user = User(
        username=f"testuser2_{unique_suffix}",
        email=f"test2_{uuid4().hex[:8]}@example.com",
        tenant_key=tenant_key,  # 0424m: Use same tenant_key as org
        role="developer",
        password_hash="hashed_password",
        org_id=org.id,  # Required after 0424j
    )
    db_session.add(user)
    await db_session.commit()
    await db_session.refresh(user)
    return user


@pytest_asyncio.fixture
async def auth_headers(test_user: User) -> dict:
    """Generate authentication headers for primary test user."""
    from src.giljo_mcp.auth.jwt_manager import JWTManager

    token = JWTManager.create_access_token(
        user_id=test_user.id, username=test_user.username, role=test_user.role, tenant_key=test_user.tenant_key
    )

    return {"Authorization": f"Bearer {token}"}


@pytest_asyncio.fixture
async def auth_headers_user_2(test_user_2: User) -> dict:
    """Generate authentication headers for secondary test user."""
    from src.giljo_mcp.auth.jwt_manager import JWTManager

    token = JWTManager.create_access_token(
        user_id=test_user_2.id, username=test_user_2.username, role=test_user_2.role, tenant_key=test_user_2.tenant_key
    )

    return {"Authorization": f"Bearer {token}"}


@pytest_asyncio.fixture
async def authed_client(db_manager: DatabaseManager, db_session: AsyncSession, test_user: User):
    """Create AsyncClient with authenticated user and tenant context."""
    from api.app import app, state
    from src.giljo_mcp.auth.dependencies import get_current_active_user, get_db_session

    async def mock_get_current_user():
        return test_user

    async def mock_get_db_session():
        yield db_session

    class DummyAuth:
        async def authenticate_request(self, request):
            TenantManager.set_current_tenant(test_user.tenant_key)
            return {
                "authenticated": True,
                "user_id": str(test_user.id),
                "user": test_user.username,
                "user_obj": test_user,
                "tenant_key": test_user.tenant_key,
            }

    state.db_manager = db_manager
    state.tenant_manager = state.tenant_manager or TenantManager()
    state.auth = DummyAuth()
    app.state.db_manager = db_manager
    app.state.tenant_manager = state.tenant_manager
    app.state.auth = state.auth

    app.dependency_overrides[get_current_active_user] = mock_get_current_user
    app.dependency_overrides[get_db_session] = mock_get_db_session

    transport = ASGITransport(app=app)
    async with AsyncClient(transport=transport, base_url="http://testserver") as client:
        yield client

    app.dependency_overrides.clear()


@pytest_asyncio.fixture
async def authed_client_user_2(db_manager: DatabaseManager, db_session: AsyncSession, test_user_2: User):
    """Authenticated client for secondary test user (tenant isolation checks)."""
    from api.app import app, state
    from src.giljo_mcp.auth.dependencies import get_current_active_user, get_db_session

    async def mock_get_current_user():
        return test_user_2

    async def mock_get_db_session():
        yield db_session

    class DummyAuth:
        async def authenticate_request(self, request):
            TenantManager.set_current_tenant(test_user_2.tenant_key)
            return {
                "authenticated": True,
                "user_id": str(test_user_2.id),
                "user": test_user_2.username,
                "user_obj": test_user_2,
                "tenant_key": test_user_2.tenant_key,
            }

    state.db_manager = db_manager
    state.tenant_manager = state.tenant_manager or TenantManager()
    state.auth = DummyAuth()
    app.state.db_manager = db_manager
    app.state.tenant_manager = state.tenant_manager
    app.state.auth = state.auth

    app.dependency_overrides[get_current_active_user] = mock_get_current_user
    app.dependency_overrides[get_db_session] = mock_get_db_session

    transport = ASGITransport(app=app)
    async with AsyncClient(transport=transport, base_url="http://testserver") as client:
        yield client

    app.dependency_overrides.clear()


@pytest_asyncio.fixture
async def async_client(authed_client: AsyncClient):
    """Alias authed_client for backward compatibility in integration tests."""
    yield authed_client


@pytest_asyncio.fixture
async def test_product(db_session: AsyncSession, test_user: User):
    """Create test product with VisionDocument (Handover 0128e migration)"""
    from src.giljo_mcp.models import VisionDocument

    product = Product(
        name=f"Test Product {uuid4().hex[:8]}",
        tenant_key=test_user.tenant_key,
        is_active=False,  # Product uses is_active (boolean) not status (string)
        config_data={
            "architecture": "Microservices architecture with event-driven design.",
            "tech_stack": "Python, FastAPI, PostgreSQL, Vue 3",
        },
    )
    db_session.add(product)
    await db_session.commit()
    await db_session.refresh(product)

    # Create VisionDocument for the product (replaces deprecated vision_document field)
    vision_doc = VisionDocument(
        product_id=product.id,
        tenant_key=test_user.tenant_key,
        document_name="Product Vision",
        document_type="vision",
        vision_document="# Product Vision\n\nComprehensive product vision document with all details.",
        storage_type="inline",
        is_active=True,
        display_order=0,
    )
    db_session.add(vision_doc)
    await db_session.commit()
    await db_session.refresh(product)  # Refresh to load relationship

    return product


@pytest_asyncio.fixture
async def test_project(db_session: AsyncSession, test_user: User, test_product: Product):
    """Create test project"""
    import random

    project = Project(
        name=f"Test Project {uuid4().hex[:8]}",
        description="Comprehensive project description for testing mission generation.",
        mission="Test mission for integration testing",
        product_id=test_product.id,
        tenant_key=test_user.tenant_key,
        status="active",
        series_number=random.randint(1, 999999),
    )
    db_session.add(project)
    await db_session.commit()
    await db_session.refresh(project)
    return project


@pytest.fixture
def test_tenant_key(test_user: User) -> str:
    """Return test tenant key for message schema tests"""
    return test_user.tenant_key


@pytest.fixture
def mock_websocket_manager():
    """Create mock WebSocket manager to verify event emissions"""
    mock_manager = MagicMock()

    # Mock the broadcast methods with AsyncMock
    mock_manager.broadcast_message_sent = AsyncMock(return_value=None)
    mock_manager.broadcast_job_message = AsyncMock(return_value=None)
    mock_manager.broadcast_message_acknowledged = AsyncMock(return_value=None)

    return mock_manager


@pytest_asyncio.fixture
async def test_api_key(db_session: AsyncSession, test_user: User) -> tuple[str, str]:
    """Create test API key and return (api_key_record, plaintext_key)"""
    from src.giljo_mcp.api_key_utils import generate_api_key, get_key_prefix, hash_api_key
    from src.giljo_mcp.models import APIKey

    plaintext_key = generate_api_key()
    key_hash = hash_api_key(plaintext_key)
    key_prefix = get_key_prefix(plaintext_key)

    api_key = APIKey(
        id=str(uuid4()),
        user_id=test_user.id,
        tenant_key=test_user.tenant_key,
        name="Test API Key",
        key_hash=key_hash,
        key_prefix=key_prefix,
        permissions=["*"],
        is_active=True,
    )

    db_session.add(api_key)
    await db_session.commit()
    await db_session.refresh(api_key)

    return api_key, plaintext_key


@pytest_asyncio.fixture
async def test_client(
    db_manager: DatabaseManager, db_session: AsyncSession, test_user: User, test_api_key, mock_websocket_manager
):
    """Create AsyncClient with authenticated user, tenant context, and WebSocket manager injected."""
    from api.app import app, state
    from src.giljo_mcp.auth.dependencies import get_current_active_user, get_db_session

    api_key_record, plaintext_key = test_api_key

    async def mock_get_current_user():
        return test_user

    async def mock_get_db_session():
        yield db_session

    class DummyAuth:
        async def authenticate_request(self, request):
            TenantManager.set_current_tenant(test_user.tenant_key)
            return {
                "authenticated": True,
                "user_id": str(test_user.id),
                "user": test_user.username,
                "user_obj": test_user,
                "tenant_key": test_user.tenant_key,
            }

    # Inject WebSocket manager into app state
    state.db_manager = db_manager
    state.tenant_manager = state.tenant_manager or TenantManager()
    state.auth = DummyAuth()
    state.websocket_manager = mock_websocket_manager  # Inject mock WebSocket manager
    app.state.db_manager = db_manager
    app.state.tenant_manager = state.tenant_manager
    app.state.auth = state.auth
    app.state.websocket_manager = mock_websocket_manager

    # Recreate ToolAccessor with WebSocket manager injected
    from src.giljo_mcp.tools.tool_accessor import ToolAccessor

    state.tool_accessor = ToolAccessor(state.db_manager, state.tenant_manager, websocket_manager=mock_websocket_manager)

    app.dependency_overrides[get_current_active_user] = mock_get_current_user
    app.dependency_overrides[get_db_session] = mock_get_db_session

    transport = ASGITransport(app=app)
    async with AsyncClient(transport=transport, base_url="http://testserver") as client:
        # Store the API key for tests to use
        client.api_key = plaintext_key
        yield client

    app.dependency_overrides.clear()


# ============================================================================
# Multi-Tenant Isolation Fixtures (shared across split test modules)
# ============================================================================


@pytest_asyncio.fixture
async def tenant_a():
    """First test tenant"""
    return f"tenant_a_{uuid4().hex[:8]}"


@pytest_asyncio.fixture
async def tenant_b():
    """Second test tenant"""
    return f"tenant_b_{uuid4().hex[:8]}"


@pytest_asyncio.fixture
async def user_in_tenant_a(db_session, tenant_a):
    """User in tenant A"""
    user = User(
        id=str(uuid4()),
        username=f"user_a_{uuid4().hex[:6]}",
        email=f"user_a_{uuid4().hex[:6]}@example.com",
        tenant_key=tenant_a,
        role="developer",
        password_hash="hash",
        field_priority_config={
            "version": "2.0",
            "priorities": {
                "product_core": 1,
                "vision_documents": 2,
                "git_history": 3,
            },
        },
        serena_enabled=True,
    )
    db_session.add(user)
    await db_session.flush()
    return user


@pytest_asyncio.fixture
async def user_in_tenant_b(db_session, tenant_b):
    """User in tenant B (different tenant)"""
    user = User(
        id=str(uuid4()),
        username=f"user_b_{uuid4().hex[:6]}",
        email=f"user_b_{uuid4().hex[:6]}@example.com",
        tenant_key=tenant_b,
        role="developer",
        password_hash="hash",
        field_priority_config={
            "version": "2.0",
            "priorities": {
                "product_core": 1,
                "vision_documents": 3,  # Different priority than user_a
                "git_history": 4,
            },
        },
        serena_enabled=False,
    )
    db_session.add(user)
    await db_session.flush()
    return user


@pytest_asyncio.fixture
async def product_in_tenant_a(db_session, tenant_a):
    """Product in tenant A"""
    product = Product(
        id=str(uuid4()),
        name=f"ProductA_{uuid4().hex[:6]}",
        tenant_key=tenant_a,
        testing_config={
            "framework": "pytest",
            "coverage_target": 85,
        },
        product_memory={
            "git_integration": {"enabled": True},
            "sequential_history": [
                {
                    "sequence": 1,
                    "type": "project_closeout",
                    "project_id": str(uuid4()),
                    "summary": "Tenant A project history",
                    "timestamp": datetime.utcnow().isoformat(),
                }
            ],
        },
    )
    db_session.add(product)
    await db_session.flush()
    return product


@pytest_asyncio.fixture
async def product_in_tenant_b(db_session, tenant_b):
    """Product in tenant B (different tenant)"""
    product = Product(
        id=str(uuid4()),
        name=f"ProductB_{uuid4().hex[:6]}",
        tenant_key=tenant_b,
        testing_config={
            "framework": "mocha",
            "coverage_target": 75,
        },
        product_memory={"git_integration": {"enabled": False}, "sequential_history": []},
    )
    db_session.add(product)
    await db_session.flush()
    return product


# ============================================================================
# Auth Endpoint Fixtures (split from test_auth_endpoints.py)
# Prefixed with auth_ep_ to avoid collisions with conftest fixtures above.
# These fixtures create their own isolated DB and dependency overrides.
# ============================================================================


@pytest_asyncio.fixture
async def auth_ep_test_client():
    """Create async HTTP client for testing auth endpoints with proper database dependency override."""
    from typing import Optional

    from fastapi import Cookie, Depends, Header, Request
    from httpx import ASGITransport, AsyncClient
    from sqlalchemy import text
    from sqlalchemy.ext.asyncio import AsyncSession

    from api.app import app
    from src.giljo_mcp.auth.dependencies import get_db_session
    from src.giljo_mcp.database import DatabaseManager
    from tests.helpers.test_db_helper import PostgreSQLTestHelper

    # Ensure test database exists
    await PostgreSQLTestHelper.ensure_test_database_exists()

    # Create test database manager
    db_url = PostgreSQLTestHelper.get_test_db_url()
    test_db_manager = DatabaseManager(db_url, is_async=True)

    # Create tables
    await PostgreSQLTestHelper.create_test_tables(test_db_manager)

    # Clean all test data before each test
    async with test_db_manager.get_session_async() as session:
        await session.execute(text("TRUNCATE TABLE api_keys, users RESTART IDENTITY CASCADE"))
        await session.commit()

    # Override get_db_session dependency to use test database
    async def override_get_db_session():
        """Override database session to use test database"""
        async with test_db_manager.get_session_async() as session:
            yield session

    app.dependency_overrides[get_db_session] = override_get_db_session

    # Monkey-patch the localhost check in get_current_user
    import src.giljo_mcp.auth.dependencies

    original_code = src.giljo_mcp.auth.dependencies.get_current_user

    async def patched_get_current_user(
        request: Request,
        access_token: Optional[str] = Cookie(None),
        x_api_key: Optional[str] = Header(None),
        db: AsyncSession = Depends(override_get_db_session),
    ):
        # Mock the client to appear as non-localhost
        if request.client:

            class MockClient:
                def __init__(self, original_client):
                    self.host = "192.168.1.100"
                    self.port = original_client.port if original_client else 12345

            original_client = request.client
            request._client = MockClient(original_client)
            try:
                return await original_code(request, access_token, x_api_key, db)
            finally:
                request._client = original_client
        else:
            return await original_code(request, access_token, x_api_key, db)

    app.dependency_overrides[src.giljo_mcp.auth.dependencies.get_current_user] = patched_get_current_user

    transport = ASGITransport(app=app)
    async with AsyncClient(transport=transport, base_url="http://testserver:8000") as ac:
        yield ac

    # Cleanup: clear overrides and close test database
    app.dependency_overrides.clear()
    await test_db_manager.close_async()


@pytest_asyncio.fixture
async def auth_ep_test_user(auth_ep_test_client):
    """Create a test user for auth endpoint tests."""
    from passlib.hash import bcrypt

    from api.app import app
    from src.giljo_mcp.auth.dependencies import get_db_session

    db_session_gen = app.dependency_overrides[get_db_session]
    async for session in db_session_gen():
        user = User(
            username="testuser",
            password_hash=bcrypt.hash("testpassword123"),
            email="test@example.com",
            role="developer",
            tenant_key="default",
            is_active=True,
        )
        session.add(user)
        await session.commit()
        await session.refresh(user)
        return user


@pytest_asyncio.fixture
async def auth_ep_admin_user(auth_ep_test_client):
    """Create an admin user for testing admin endpoints."""
    from passlib.hash import bcrypt

    from api.app import app
    from src.giljo_mcp.auth.dependencies import get_db_session

    db_session_gen = app.dependency_overrides[get_db_session]
    async for session in db_session_gen():
        user = User(
            username="admin",
            password_hash=bcrypt.hash("adminpass123"),
            email="admin@example.com",
            role="admin",
            tenant_key="default",
            is_active=True,
        )
        session.add(user)
        await session.commit()
        await session.refresh(user)
        return user


@pytest_asyncio.fixture
async def auth_ep_authenticated_headers(auth_ep_test_client: AsyncClient, auth_ep_test_user: User):
    """Get authenticated JWT cookie for testing protected endpoints."""
    response = await auth_ep_test_client.post(
        "/api/auth/login", json={"username": "testuser", "password": "testpassword123"}
    )
    assert response.status_code == 200
    return response.cookies


@pytest_asyncio.fixture
async def auth_ep_admin_headers(auth_ep_test_client: AsyncClient, auth_ep_admin_user: User):
    """Get admin JWT cookie for testing admin endpoints."""
    response = await auth_ep_test_client.post(
        "/api/auth/login", json={"username": "admin", "password": "adminpass123"}
    )
    assert response.status_code == 200
    return response.cookies


@pytest_asyncio.fixture
async def auth_ep_test_api_key(auth_ep_test_client, auth_ep_test_user: User):
    """Create a test API key for auth endpoint tests."""
    from src.giljo_mcp.api_key_utils import generate_api_key, get_key_prefix, hash_api_key
    from src.giljo_mcp.models import APIKey

    from api.app import app
    from src.giljo_mcp.auth.dependencies import get_db_session

    api_key_plaintext = generate_api_key()
    key_hash = hash_api_key(api_key_plaintext)
    key_prefix = get_key_prefix(api_key_plaintext)

    db_session_gen = app.dependency_overrides[get_db_session]
    async for session in db_session_gen():
        api_key = APIKey(
            user_id=auth_ep_test_user.id,
            tenant_key=auth_ep_test_user.tenant_key,
            name="Test Key",
            key_hash=key_hash,
            key_prefix=key_prefix,
            permissions=["*"],
            is_active=True,
        )
        session.add(api_key)
        await session.commit()
        await session.refresh(api_key)
        return api_key


# ============================================================================
# Message Service Receive Test Fixtures (shared across split test modules)
# ============================================================================


@pytest.fixture
async def setup_test_data(db_manager: DatabaseManager, test_tenant_key: str):
    """Create test project, agents, and messages with unique IDs."""
    tenant_key = test_tenant_key

    # Generate unique IDs for this test run
    project_id = f"proj-test-{uuid4().hex[:8]}"
    agent1_id = f"agent-{uuid4().hex[:8]}"
    agent2_id = f"agent-{uuid4().hex[:8]}"
    agent3_id = f"agent-{uuid4().hex[:8]}"
    msg1_id = f"msg-{uuid4().hex[:8]}"
    msg2_id = f"msg-{uuid4().hex[:8]}"
    msg3_id = f"msg-{uuid4().hex[:8]}"
    msg4_id = f"msg-{uuid4().hex[:8]}"
    msg5_id = f"msg-{uuid4().hex[:8]}"

    async with db_manager.get_session_async() as session:
        # Create test project
        project = Project(
            id=project_id,
            tenant_key=tenant_key,
            name="Test Project",
            description="Test project for message service",
            mission="Test mission for message service integration tests",
            status="active",
            series_number=random.randint(1, 999999),
        )
        session.add(project)

        # Create test agents (status must be one of: waiting, working, blocked, complete, failed, cancelled, decommissioned)
        agent1 = AgentExecution(
            job_id=agent1_id,
            tenant_key=tenant_key,
            project_id=project.id,
            agent_display_name="implementer",
            agent_name="Implementer Agent",
            mission="Implement features",
            status="working",
        )
        agent2 = AgentExecution(
            job_id=agent2_id,
            tenant_key=tenant_key,
            project_id=project.id,
            agent_display_name="tester",
            agent_name="Tester Agent",
            mission="Run tests",
            status="working",
        )
        agent3 = AgentExecution(
            job_id=agent3_id,
            tenant_key=tenant_key,
            project_id=project.id,
            agent_display_name="analyzer",
            agent_name="Analyzer Agent",
            mission="Analyze code",
            status="working",
        )
        session.add_all([agent1, agent2, agent3])

        # Create test messages
        messages = [
            # Direct message to agent-1
            Message(
                id=msg1_id,
                tenant_key=tenant_key,
                project_id=project.id,
                to_agents=[agent1_id],
                message_type="direct",
                content="Direct message to agent 1",
                priority="normal",
                status="pending",
                meta_data={"_from_agent": "orchestrator"},
            ),
            # Broadcast message to all
            Message(
                id=msg2_id,
                tenant_key=tenant_key,
                project_id=project.id,
                to_agents=["all"],
                message_type="broadcast",
                content="Broadcast to all agents",
                priority="high",
                status="pending",
                meta_data={"_from_agent": "orchestrator"},
            ),
            # Direct message to agent-2
            Message(
                id=msg3_id,
                tenant_key=tenant_key,
                project_id=project.id,
                to_agents=[agent2_id],
                message_type="direct",
                content="Direct message to agent 2",
                priority="normal",
                status="pending",
                meta_data={"_from_agent": agent1_id},
            ),
            # Acknowledged message to agent-1
            Message(
                id=msg4_id,
                tenant_key=tenant_key,
                project_id=project.id,
                to_agents=[agent1_id],
                message_type="direct",
                content="Acknowledged message",
                priority="normal",
                status="acknowledged",
                acknowledged_by=[agent1_id],
                acknowledged_at=datetime.now(timezone.utc),
                meta_data={"_from_agent": "orchestrator"},
            ),
            # Multiple recipients (not broadcast)
            Message(
                id=msg5_id,
                tenant_key=tenant_key,
                project_id=project.id,
                to_agents=[agent1_id, agent2_id],
                message_type="direct",
                content="Message to multiple agents",
                priority="high",
                status="pending",
                meta_data={"_from_agent": "orchestrator"},
            ),
        ]
        session.add_all(messages)

        await session.commit()

        # Store IDs for test assertions
        test_data = {
            "project": project,
            "agents": [agent1, agent2, agent3],
            "messages": messages,
            "agent1_id": agent1_id,
            "agent2_id": agent2_id,
            "agent3_id": agent3_id,
            "msg1_id": msg1_id,
            "msg2_id": msg2_id,
            "msg3_id": msg3_id,
            "msg4_id": msg4_id,
            "msg5_id": msg5_id,
        }

        yield test_data

        # Cleanup: Rollback any uncommitted changes
        await session.rollback()


# ============================================================================
# Field Priority Tenant Isolation Fixtures
# (shared across test_field_priority_tenant_isolation_*.py split modules)
# ============================================================================


@pytest_asyncio.fixture
async def tenant_a_key():
    """Tenant A isolation key"""
    return f"tenant_a_{uuid4().hex[:8]}"


@pytest_asyncio.fixture
async def tenant_b_key():
    """Tenant B isolation key (different from tenant A)"""
    return f"tenant_b_{uuid4().hex[:8]}"


@pytest_asyncio.fixture
async def user_tenant_a(db_session, tenant_a_key):
    """Create user in Tenant A with specific field priorities"""
    user = User(
        id=str(uuid4()),
        username=f"user_a_{uuid4().hex[:6]}",
        email=f"user_a_{uuid4().hex[:6]}@example.com",
        tenant_key=tenant_a_key,
        role="developer",
        password_hash="hashed_password",
        field_priority_config={
            "version": "2.0",
            "priorities": {
                "product_core": 1,
                "vision_documents": 2,
                "agent_templates": 3,
                "project_description": 1,
                "memory_360": 2,
                "git_history": 4,  # Tenant A excludes git_history
            },
        },
    )
    db_session.add(user)
    await db_session.commit()
    await db_session.refresh(user)
    return user


@pytest_asyncio.fixture
async def user_tenant_b(db_session, tenant_b_key):
    """Create user in Tenant B with DIFFERENT field priorities"""
    user = User(
        id=str(uuid4()),
        username=f"user_b_{uuid4().hex[:6]}",
        email=f"user_b_{uuid4().hex[:6]}@example.com",
        tenant_key=tenant_b_key,
        role="developer",
        password_hash="hashed_password",
        field_priority_config={
            "version": "2.0",
            "priorities": {
                "product_core": 1,
                "vision_documents": 4,  # Tenant B excludes vision_documents
                "agent_templates": 2,
                "project_description": 1,
                "memory_360": 4,  # Tenant B excludes memory_360
                "git_history": 2,  # Tenant B INCLUDES git_history (different from A)
            },
        },
    )
    db_session.add(user)
    await db_session.commit()
    await db_session.refresh(user)
    return user


@pytest_asyncio.fixture
async def product_tenant_a(db_session, tenant_a_key):
    """Create product in Tenant A"""
    product = Product(
        id=str(uuid4()),
        name=f"Product A {uuid4().hex[:8]}",
        description="Product for Tenant A.",
        tenant_key=tenant_a_key,
        is_active=True,
    )
    db_session.add(product)
    await db_session.commit()
    await db_session.refresh(product)
    return product


@pytest_asyncio.fixture
async def product_tenant_b(db_session, tenant_b_key):
    """Create product in Tenant B"""
    product = Product(
        id=str(uuid4()),
        name=f"Product B {uuid4().hex[:8]}",
        description="Product for Tenant B.",
        tenant_key=tenant_b_key,
        is_active=True,
    )
    db_session.add(product)
    await db_session.commit()
    await db_session.refresh(product)
    return product


@pytest_asyncio.fixture
async def project_tenant_a(db_session, product_tenant_a, tenant_a_key):
    """Create project in Tenant A"""
    project = Project(
        id=str(uuid4()),
        name=f"Project A {uuid4().hex[:8]}",
        description="Project for Tenant A.",
        product_id=str(product_tenant_a.id),
        tenant_key=tenant_a_key,
        status="planning",
        mission="Mission for Tenant A.",
        series_number=random.randint(1, 999999),
    )
    db_session.add(project)
    await db_session.commit()
    await db_session.refresh(project)
    return project


@pytest_asyncio.fixture
async def project_tenant_b(db_session, product_tenant_b, tenant_b_key):
    """Create project in Tenant B"""
    project = Project(
        id=str(uuid4()),
        name=f"Project B {uuid4().hex[:8]}",
        description="Project for Tenant B.",
        product_id=str(product_tenant_b.id),
        tenant_key=tenant_b_key,
        status="planning",
        mission="Mission for Tenant B.",
        series_number=random.randint(1, 999999),
    )
    db_session.add(project)
    await db_session.commit()
    await db_session.refresh(project)
    return project
