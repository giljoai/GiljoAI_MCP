"""
Shared fixtures for tests/services/ test modules.

Extracted during test file reorganization to support split test files
while keeping fixture definitions DRY.
"""

import random
from datetime import datetime, timezone
from unittest.mock import AsyncMock, MagicMock
from uuid import uuid4

from sqlalchemy.ext.asyncio import AsyncSession

import pytest_asyncio
from passlib.hash import bcrypt

from src.giljo_mcp.models.auth import User
from src.giljo_mcp.models import AgentTemplate, Message
from src.giljo_mcp.models.organizations import Organization
from src.giljo_mcp.database import DatabaseManager
from src.giljo_mcp.models.agent_identity import AgentExecution, AgentJob
from src.giljo_mcp.models.products import Product, VisionDocument
from src.giljo_mcp.models.projects import Project
from src.giljo_mcp.models.tasks import Task
from src.giljo_mcp.services.message_service import MessageService
from src.giljo_mcp.services.task_service import TaskService
from src.giljo_mcp.tenant import TenantManager


@pytest_asyncio.fixture
async def user_service(db_manager, db_session, test_tenant_key):
    """Create UserService instance for testing with shared session (Handover 0324)"""
    from src.giljo_mcp.services.user_service import UserService

    return UserService(
        db_manager=db_manager,
        tenant_key=test_tenant_key,
        websocket_manager=None,  # No WebSocket in tests
        session=db_session,  # SHARED SESSION for test transaction isolation
    )


@pytest_asyncio.fixture
async def test_user(db_session, test_tenant_key):
    """Create test user in database"""
    user = User(
        id=str(uuid4()),
        username=f"testuser_{uuid4().hex[:6]}",
        email=f"test_{uuid4().hex[:6]}@example.com",
        password_hash=bcrypt.hash("TestPassword123"),
        full_name="Test User",
        role="developer",
        tenant_key=test_tenant_key,
        is_active=True,
        created_at=datetime.now(timezone.utc),
    )
    db_session.add(user)
    await db_session.commit()
    await db_session.refresh(user)
    return user


@pytest_asyncio.fixture
async def admin_user(db_session, test_tenant_key):
    """Create admin user in database"""
    admin = User(
        id=str(uuid4()),
        username=f"admin_{uuid4().hex[:6]}",
        email=f"admin_{uuid4().hex[:6]}@example.com",
        password_hash=bcrypt.hash("AdminPassword123"),
        full_name="Admin User",
        role="admin",
        tenant_key=test_tenant_key,
        is_active=True,
        created_at=datetime.now(timezone.utc),
    )
    db_session.add(admin)
    await db_session.commit()
    await db_session.refresh(admin)
    return admin


@pytest_asyncio.fixture
async def other_tenant_key():
    """Generate another tenant key for cross-tenant testing"""
    return TenantManager.generate_tenant_key()


@pytest_asyncio.fixture
async def test_product(db_session, test_tenant_key):
    """Create test product in database"""
    product = Product(
        id=str(uuid4()),
        name=f"Test Product {uuid4().hex[:6]}",
        description="Test product for task service tests",
        tenant_key=test_tenant_key,
        is_active=True,
        created_at=datetime.now(timezone.utc),
    )
    db_session.add(product)
    await db_session.commit()
    await db_session.refresh(product)
    return product


@pytest_asyncio.fixture
async def other_tenant_user(db_session, other_tenant_key):
    """Create user in different tenant"""
    user = User(
        id=str(uuid4()),
        username=f"otheruser_{uuid4().hex[:6]}",
        email=f"other_{uuid4().hex[:6]}@example.com",
        password_hash=bcrypt.hash("OtherPassword123"),
        full_name="Other Tenant User",
        role="developer",
        tenant_key=other_tenant_key,
        is_active=True,
        created_at=datetime.now(timezone.utc),
    )
    db_session.add(user)
    await db_session.commit()
    await db_session.refresh(user)
    return user


@pytest_asyncio.fixture
async def other_tenant_product(db_session, other_tenant_key):
    """Create product for other tenant"""
    product = Product(
        id=str(uuid4()),
        name=f"Other Product {uuid4().hex[:6]}",
        description="Product for other tenant",
        tenant_key=other_tenant_key,
        is_active=True,
        created_at=datetime.now(timezone.utc),
    )
    db_session.add(product)
    await db_session.commit()
    await db_session.refresh(product)
    return product


@pytest_asyncio.fixture
async def other_tenant_task(db_session, other_tenant_key, other_tenant_product, other_tenant_user):
    """Create task in different tenant with required product_id (0433)"""
    task = Task(
        id=str(uuid4()),
        tenant_key=other_tenant_key,
        product_id=other_tenant_product.id,  # Required per handover 0433
        title="Other Tenant Task",
        description="Task in different tenant",
        status="waiting",
        priority="medium",
        created_by_user_id=other_tenant_user.id,
        created_at=datetime.now(timezone.utc),
    )
    db_session.add(task)
    await db_session.commit()
    await db_session.refresh(task)
    return task


@pytest_asyncio.fixture
async def task_service(db_manager, db_session, test_tenant_key):
    """Create TaskService instance with TenantManager and shared session"""
    # Create a mock TenantManager that returns our test tenant key
    mock_tenant_manager = MagicMock()
    mock_tenant_manager.get_current_tenant.return_value = test_tenant_key

    return TaskService(
        db_manager=db_manager,
        tenant_manager=mock_tenant_manager,
        session=db_session,  # ADD THIS - Shared Session Pattern (Handover 0324)
    )


# ============================================================================
# Phase Labels fixtures (extracted from test_orchestration_service_phase_labels.py)
# ============================================================================


@pytest_asyncio.fixture
async def test_agent_templates(db_session, test_tenant_key):
    """Create agent templates matching agent_name values used in phase label tests."""
    template_names = ["analyzer-1", "impl-1", "tester-1"]
    for name in template_names:
        template = AgentTemplate(
            tenant_key=test_tenant_key,
            name=name,
            role=name,
            description=f"Test template for {name}",
            system_instructions=f"# {name}\nTest agent instructions.",
            is_active=True,
        )
        db_session.add(template)
    await db_session.commit()


@pytest_asyncio.fixture
async def test_project(db_session, test_tenant_key, test_agent_templates) -> Project:
    """Create test project for agent jobs (depends on test_agent_templates)."""
    project = Project(
        id=str(uuid4()),
        name="Phase Labels Test Project",
        description="Test project for phase labels",
        mission="Test mission for phase labels",
        status="active",
        tenant_key=test_tenant_key,
        implementation_launched_at=datetime.now(timezone.utc),
        series_number=random.randint(1, 999999),
    )
    db_session.add(project)
    await db_session.commit()
    await db_session.refresh(project)
    return project


@pytest_asyncio.fixture
async def test_project_multi_terminal(db_session, test_tenant_key, test_agent_templates) -> Project:
    """Create test project with multi_terminal execution_mode."""
    project = Project(
        id=str(uuid4()),
        name="Multi Terminal Phase Test",
        description="Test project for multi-terminal phase labels",
        mission="Test mission for multi-terminal",
        status="active",
        tenant_key=test_tenant_key,
        execution_mode="multi_terminal",
        implementation_launched_at=datetime.now(timezone.utc),
        series_number=random.randint(1, 999999),
    )
    db_session.add(project)
    await db_session.commit()
    await db_session.refresh(project)
    return project


@pytest_asyncio.fixture
async def test_project_cli_mode(db_session, test_tenant_key, test_agent_templates) -> Project:
    """Create test project with claude_code_cli execution_mode."""
    project = Project(
        id=str(uuid4()),
        name="CLI Mode Phase Test",
        description="Test project for CLI mode",
        mission="Test mission for CLI mode",
        status="active",
        tenant_key=test_tenant_key,
        execution_mode="claude_code_cli",
        implementation_launched_at=datetime.now(timezone.utc),
        series_number=random.randint(1, 999999),
    )
    db_session.add(project)
    await db_session.commit()
    await db_session.refresh(project)
    return project


# ============================================================================
# Message tenant isolation fixtures
# (extracted from test_message_tenant_isolation_regression.py during split)
# ============================================================================


@pytest_asyncio.fixture(scope="function")
async def two_tenant_messages(db_session, db_manager):
    """
    Create messages in two separate tenants for isolation testing.

    Tenant A: product_a, project_a, message_a (orchestrator -> agent, pending)
    Tenant B: product_b, project_b, message_b (orchestrator -> agent, pending)
    """
    tenant_a = TenantManager.generate_tenant_key()
    tenant_b = TenantManager.generate_tenant_key()

    # Create products (required FK for projects)
    product_a = Product(
        id=str(uuid4()),
        name="Tenant A Product",
        description="Product for tenant A",
        tenant_key=tenant_a,
        is_active=True,
    )
    product_b = Product(
        id=str(uuid4()),
        name="Tenant B Product",
        description="Product for tenant B",
        tenant_key=tenant_b,
        is_active=True,
    )
    db_session.add(product_a)
    db_session.add(product_b)
    await db_session.commit()

    # Create projects (required FK for messages)
    project_a = Project(
        id=str(uuid4()),
        name="Tenant A Project",
        description="Project for tenant A",
        mission="Tenant A mission",
        tenant_key=tenant_a,
        product_id=product_a.id,
        status="active",
        series_number=random.randint(1, 999999),
    )
    project_b = Project(
        id=str(uuid4()),
        name="Tenant B Project",
        description="Project for tenant B",
        mission="Tenant B mission",
        tenant_key=tenant_b,
        product_id=product_b.id,
        status="active",
        series_number=random.randint(1, 999999),
    )
    db_session.add(project_a)
    db_session.add(project_b)
    await db_session.commit()

    # Create agent jobs (needed for broadcast to find agents)
    job_a = AgentJob(
        job_id=str(uuid4()),
        tenant_key=tenant_a,
        project_id=project_a.id,
        job_type="worker-a",
        mission="Worker agent for tenant A",
        status="active",
        created_at=datetime.now(timezone.utc),
        job_metadata={},
    )
    job_b = AgentJob(
        job_id=str(uuid4()),
        tenant_key=tenant_b,
        project_id=project_b.id,
        job_type="worker-b",
        mission="Worker agent for tenant B",
        status="active",
        created_at=datetime.now(timezone.utc),
        job_metadata={},
    )
    db_session.add(job_a)
    db_session.add(job_b)
    await db_session.commit()

    # Create messages
    message_a = Message(
        id=str(uuid4()),
        project_id=project_a.id,
        tenant_key=tenant_a,
        to_agents=["worker-a"],
        content="Message for tenant A agent",
        message_type="direct",
        priority="normal",
        status="pending",
        meta_data={"_from_agent": "orchestrator"},
    )
    message_b = Message(
        id=str(uuid4()),
        project_id=project_b.id,
        tenant_key=tenant_b,
        to_agents=["worker-b"],
        content="Message for tenant B agent",
        message_type="direct",
        priority="normal",
        status="pending",
        meta_data={"_from_agent": "orchestrator"},
    )
    db_session.add(message_a)
    db_session.add(message_b)
    await db_session.commit()

    for obj in [message_a, message_b]:
        await db_session.refresh(obj)

    # Create MessageService using test session
    tenant_manager = TenantManager()
    service = MessageService(
        db_manager=db_manager,
        tenant_manager=tenant_manager,
        test_session=db_session,
    )

    return {
        "tenant_a": tenant_a,
        "tenant_b": tenant_b,
        "product_a": product_a,
        "product_b": product_b,
        "project_a": project_a,
        "project_b": project_b,
        "job_a": job_a,
        "job_b": job_b,
        "message_a": message_a,
        "message_b": message_b,
        "service": service,
        "tenant_manager": tenant_manager,
    }


# ============================================================================
# Thin client prompt generator helpers
# (extracted from test_thin_client_prompt_generator_agent_templates.py during split)
# ============================================================================


async def create_test_org(session: AsyncSession, tenant_key: str, unique_suffix: str) -> Organization:
    """Helper to create an organization for test users (0424j: User.org_id NOT NULL)."""
    org = Organization(
        tenant_key=tenant_key,
        name=f"Test Org {unique_suffix}",
        slug=f"test-org-{unique_suffix}",
        is_active=True,
    )
    session.add(org)
    await session.flush()
    return org


# ============================================================================
# Message counter test fixtures
# (extracted from test_message_service_counters_0387f.py during split)
# ============================================================================


@pytest_asyncio.fixture
async def mock_websocket_manager():
    """Mock WebSocket manager for testing without real WebSocket connections."""
    mock = MagicMock()
    mock.broadcast_message_sent = AsyncMock()
    mock.broadcast_message_received = AsyncMock()
    mock.broadcast_message_acknowledged = AsyncMock()
    mock.broadcast_job_message = AsyncMock()
    return mock


@pytest_asyncio.fixture
async def test_project_with_agents(
    db_session: AsyncSession,
    test_tenant_key: str,
    test_product: Product,
) -> tuple[Project, list[AgentExecution]]:
    """
    Create a test project with multiple agents.
    Returns tuple of (project, [agent_executions]).
    """
    # Create project
    project = Project(
        id=str(uuid4()),
        tenant_key=test_tenant_key,
        product_id=test_product.id,
        name="Test Project for Counter Tests",
        description="Test project with agents",
        mission="Test mission",
        status="active",
        created_at=datetime.now(timezone.utc),
        series_number=random.randint(1, 999999),
    )
    db_session.add(project)
    await db_session.commit()
    await db_session.refresh(project)

    # Create agent jobs and executions
    agent_display_names = ["orchestrator", "analyzer", "implementer"]
    agents = []
    for agent_display_name in agent_display_names:
        # Create work order (AgentJob)
        job = AgentJob(
            job_id=str(uuid4()),
            tenant_key=test_tenant_key,
            project_id=project.id,
            job_type=agent_display_name,
            mission=f"Test mission for {agent_display_name}",
            status="active",
        )
        db_session.add(job)

        # Create executor instance (AgentExecution) with counter columns initialized
        agent = AgentExecution(
            job_id=job.job_id,
            tenant_key=test_tenant_key,
            agent_display_name=agent_display_name,
            status="waiting",
            messages_sent_count=0,
            messages_waiting_count=0,
            messages_read_count=0,
        )
        db_session.add(agent)
        agents.append(agent)

    await db_session.commit()
    for agent in agents:
        await db_session.refresh(agent)

    return project, agents


@pytest_asyncio.fixture
async def message_service(
    db_manager: DatabaseManager,
    db_session: AsyncSession,
    mock_websocket_manager: MagicMock,
) -> MessageService:
    """Create MessageService instance with mocked WebSocket manager and test session."""
    from contextlib import asynccontextmanager

    tenant_manager = TenantManager()

    # Mock db_manager.get_session_async() to return test session
    @asynccontextmanager
    async def mock_get_session_async():
        yield db_session

    db_manager.get_session_async = mock_get_session_async

    # Pass test_session for transaction-aware testing
    service = MessageService(
        db_manager=db_manager,
        tenant_manager=tenant_manager,
        websocket_manager=mock_websocket_manager,
        test_session=db_session,
    )
    return service


# ============================================================================
# Medium tenant isolation regression fixtures
# (extracted from test_medium_tenant_isolation_regression.py during split)
# ============================================================================


@pytest_asyncio.fixture(scope="function")
async def two_tenant_products(db_session, db_manager):
    """
    Create products with child entities in two separate tenants.

    Tenant A: product_a with projects, tasks, vision documents
    Tenant B: product_b with projects, tasks, vision documents
    """
    tenant_a = TenantManager.generate_tenant_key()
    tenant_b = TenantManager.generate_tenant_key()

    # Create products
    product_a = Product(
        id=str(uuid4()),
        name="Tenant A Product",
        description="Product for tenant A",
        tenant_key=tenant_a,
        is_active=True,
        quality_standards="TDD required",
    )
    product_b = Product(
        id=str(uuid4()),
        name="Tenant B Product",
        description="Product for tenant B",
        tenant_key=tenant_b,
        is_active=True,
        quality_standards="Code review required",
    )
    db_session.add(product_a)
    db_session.add(product_b)
    await db_session.commit()

    # Create projects
    project_a = Project(
        id=str(uuid4()),
        name="Tenant A Project",
        description="Project for tenant A",
        mission="Tenant A mission",
        tenant_key=tenant_a,
        product_id=product_a.id,
        status="active",
        series_number=random.randint(1, 999999),
    )
    project_b = Project(
        id=str(uuid4()),
        name="Tenant B Project",
        description="Project for tenant B",
        mission="Tenant B mission",
        tenant_key=tenant_b,
        product_id=product_b.id,
        status="active",
        series_number=random.randint(1, 999999),
    )
    db_session.add_all([project_a, project_b])
    await db_session.commit()

    # Create tasks
    task_a = Task(
        id=str(uuid4()),
        title="Tenant A Task",
        description="Task for tenant A",
        tenant_key=tenant_a,
        product_id=product_a.id,
        project_id=project_a.id,
        status="pending",
    )
    task_b = Task(
        id=str(uuid4()),
        title="Tenant B Task",
        description="Task for tenant B",
        tenant_key=tenant_b,
        product_id=product_b.id,
        project_id=project_b.id,
        status="pending",
    )
    db_session.add_all([task_a, task_b])

    # Create vision documents (VisionDocument uses document_name + vision_document fields)
    vision_a = VisionDocument(
        id=str(uuid4()),
        product_id=product_a.id,
        tenant_key=tenant_a,
        document_name="Tenant A Vision",
        document_type="vision",
        vision_document="Vision content for tenant A",
        storage_type="inline",
    )
    vision_b = VisionDocument(
        id=str(uuid4()),
        product_id=product_b.id,
        tenant_key=tenant_b,
        document_name="Tenant B Vision",
        document_type="vision",
        vision_document="Vision content for tenant B",
        storage_type="inline",
    )
    db_session.add_all([vision_a, vision_b])

    # Create agent jobs and executions
    job_a = AgentJob(
        job_id=str(uuid4()),
        job_type="implementer",
        tenant_key=tenant_a,
        project_id=project_a.id,
        mission="Implement feature for tenant A",
        status="active",
        created_at=datetime.now(timezone.utc),
    )
    job_b = AgentJob(
        job_id=str(uuid4()),
        job_type="tester",
        tenant_key=tenant_b,
        project_id=project_b.id,
        mission="Test feature for tenant B",
        status="active",
        created_at=datetime.now(timezone.utc),
    )
    db_session.add_all([job_a, job_b])
    await db_session.commit()

    execution_a = AgentExecution(
        agent_id=str(uuid4()),
        job_id=job_a.job_id,
        tenant_key=tenant_a,
        agent_display_name="implementer",
        agent_name="implementer-a",
        status="working",
        started_at=datetime.now(timezone.utc),
    )
    execution_b = AgentExecution(
        agent_id=str(uuid4()),
        job_id=job_b.job_id,
        tenant_key=tenant_b,
        agent_display_name="tester",
        agent_name="tester-b",
        status="working",
        started_at=datetime.now(timezone.utc),
    )
    db_session.add_all([execution_a, execution_b])

    # Create messages
    message_a = Message(
        id=str(uuid4()),
        content="Message for tenant A",
        tenant_key=tenant_a,
        project_id=project_a.id,
        created_at=datetime.now(timezone.utc),
    )
    message_b = Message(
        id=str(uuid4()),
        content="Message for tenant B",
        tenant_key=tenant_b,
        project_id=project_b.id,
        created_at=datetime.now(timezone.utc),
    )
    db_session.add_all([message_a, message_b])
    await db_session.commit()

    # Refresh all objects
    for obj in [
        product_a, product_b, project_a, project_b, task_a, task_b,
        vision_a, vision_b, job_a, job_b, execution_a, execution_b,
        message_a, message_b,
    ]:
        await db_session.refresh(obj)

    return {
        "tenant_a": tenant_a,
        "tenant_b": tenant_b,
        "product_a": product_a,
        "product_b": product_b,
        "project_a": project_a,
        "project_b": project_b,
        "task_a": task_a,
        "task_b": task_b,
        "vision_a": vision_a,
        "vision_b": vision_b,
        "job_a": job_a,
        "job_b": job_b,
        "execution_a": execution_a,
        "execution_b": execution_b,
        "message_a": message_a,
        "message_b": message_b,
        "db_session": db_session,
        "db_manager": db_manager,
    }
