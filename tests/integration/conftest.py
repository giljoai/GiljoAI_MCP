"""
Integration test fixtures for Handover 0316
"""

import pytest
import pytest_asyncio
from unittest.mock import AsyncMock, MagicMock
from uuid import uuid4
from sqlalchemy.ext.asyncio import AsyncSession

from httpx import ASGITransport, AsyncClient
from src.giljo_mcp.models import User, Product, Project
from src.giljo_mcp.database import DatabaseManager
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
    user = User(
        username=f"testuser_{uuid4().hex[:8]}",
        email=f"test_{uuid4().hex[:8]}@example.com",
        tenant_key=TenantManager.generate_tenant_key(),
        role="developer",
        password_hash="hashed_password",
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
    user = User(
        username=f"testuser2_{uuid4().hex[:8]}",
        email=f"test2_{uuid4().hex[:8]}@example.com",
        tenant_key=TenantManager.generate_tenant_key(),
        role="developer",
        password_hash="hashed_password",
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
        user_id=test_user.id,
        username=test_user.username,
        role=test_user.role,
        tenant_key=test_user.tenant_key
    )

    return {"Authorization": f"Bearer {token}"}


@pytest_asyncio.fixture
async def auth_headers_user_2(test_user_2: User) -> dict:
    """Generate authentication headers for secondary test user."""
    from src.giljo_mcp.auth.jwt_manager import JWTManager

    token = JWTManager.create_access_token(
        user_id=test_user_2.id,
        username=test_user_2.username,
        role=test_user_2.role,
        tenant_key=test_user_2.tenant_key
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
    project = Project(
        name=f"Test Project {uuid4().hex[:8]}",
        description="Comprehensive project description for testing mission generation.",
        mission="Test mission for integration testing",
        product_id=test_product.id,
        tenant_key=test_user.tenant_key,
        status="active",
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
    from src.giljo_mcp.api_key_utils import generate_api_key, hash_api_key, get_key_prefix
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
async def test_client(db_manager: DatabaseManager, db_session: AsyncSession, test_user: User, test_api_key, mock_websocket_manager):
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
    state.tool_accessor = ToolAccessor(
        state.db_manager,
        state.tenant_manager,
        websocket_manager=mock_websocket_manager
    )

    app.dependency_overrides[get_current_active_user] = mock_get_current_user
    app.dependency_overrides[get_db_session] = mock_get_db_session

    transport = ASGITransport(app=app)
    async with AsyncClient(transport=transport, base_url="http://testserver") as client:
        # Store the API key for tests to use
        client.api_key = plaintext_key
        yield client

    app.dependency_overrides.clear()


@pytest_asyncio.fixture
async def test_project_with_orchestrator(db_session: AsyncSession, test_user: User, test_product: Product):
    """Create test project with orchestrator job"""
    from src.giljo_mcp.models.agent_identity import AgentJob, AgentExecution

    project = Project(
        name=f"Test Project with Orchestrator {uuid4().hex[:8]}",
        description="Test project for orchestrator integration testing",
        mission="Test mission for orchestrator workflow testing",
        product_id=test_product.id,
        tenant_key=test_user.tenant_key,
        status="active",
    )
    db_session.add(project)
    await db_session.commit()
    await db_session.refresh(project)

    # Create orchestrator job for the project
    orchestrator_job = AgentExecution(
        job_id=str(uuid4()),
        project_id=project.id,
        tenant_key=test_user.tenant_key,
        agent_display_name="orchestrator",
        agent_name="Orchestrator",
        mission="Orchestrate project execution",
        status="working",  # Valid status: waiting, working, blocked, complete, failed, cancelled, decommissioned
        spawned_by=None,  # Top-level orchestrator
    )
    db_session.add(orchestrator_job)
    await db_session.commit()
    await db_session.refresh(project)

    return project
