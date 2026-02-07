"""
Integration tests for write_360_memory tool (Handover 0412)

Tests the complete workflow:
1. MCP tool registration
2. Tool execution via ToolAccessor
3. Database persistence
4. Multi-tenant isolation
"""

from uuid import uuid4

import pytest

from src.giljo_mcp.database import DatabaseManager
from src.giljo_mcp.models import Product, Project
from src.giljo_mcp.models.agent_identity import AgentJob
from src.giljo_mcp.tools.write_360_memory import write_360_memory


@pytest.fixture
async def setup_test_data(db_manager: DatabaseManager, tenant_key: str):
    """Create test product, project, and agent job."""
    async with db_manager.get_session_async() as session:
        # Create product
        product = Product(
            id=str(uuid4()),
            name="Test Product",
            tenant_key=tenant_key,
            product_memory={"sequential_history": []},
            is_active=True,
        )
        session.add(product)

        # Create project
        project = Project(
            id=str(uuid4()),
            name="Test Project",
            description="Test project for write_360_memory",
            product_id=product.id,
            tenant_key=tenant_key,
            status="active",
        )
        session.add(project)

        # Create agent job
        agent_job = AgentJob(
            job_id=str(uuid4()),
            agent_name="Test Agent",
            job_type="implementer",
            project_id=project.id,
            tenant_key=tenant_key,
            status="active",
        )
        session.add(agent_job)

        await session.commit()

        yield {
            "product_id": product.id,
            "project_id": project.id,
            "agent_job_id": agent_job.job_id,
        }


@pytest.mark.asyncio
async def test_write_360_memory_basic(db_manager: DatabaseManager, tenant_key: str, setup_test_data):
    """Test basic write_360_memory functionality."""
    data = setup_test_data

    result = await write_360_memory(
        project_id=data["project_id"],
        tenant_key=tenant_key,
        summary="Implemented user authentication with JWT tokens",
        key_outcomes=[
            "JWT authentication working",
            "Password hashing implemented",
            "Token refresh mechanism added",
        ],
        decisions_made=[
            "Chose bcrypt for password hashing",
            "15-minute access token expiry",
            "7-day refresh token expiry",
        ],
        entry_type="project_completion",
        author_job_id=data["agent_job_id"],
        db_manager=db_manager,
    )

    assert result["success"] is True
    assert result["sequence_number"] == 1
    assert result["entry_type"] == "project_completion"
    assert "message" in result


@pytest.mark.asyncio
async def test_write_360_memory_handover_type(db_manager: DatabaseManager, tenant_key: str, setup_test_data):
    """Test write_360_memory with handover_closeout type."""
    data = setup_test_data

    result = await write_360_memory(
        project_id=data["project_id"],
        tenant_key=tenant_key,
        summary="Completed backend API implementation before handover",
        key_outcomes=[
            "REST API endpoints created",
            "Database schema migrated",
        ],
        decisions_made=[
            "Used FastAPI for performance",
            "PostgreSQL for persistence",
        ],
        entry_type="handover_closeout",
        author_job_id=data["agent_job_id"],
        db_manager=db_manager,
    )

    assert result["success"] is True
    assert result["entry_type"] == "handover_closeout"


@pytest.mark.asyncio
async def test_write_360_memory_sequential_entries(db_manager: DatabaseManager, tenant_key: str, setup_test_data):
    """Test multiple sequential memory entries."""
    data = setup_test_data

    # First entry
    result1 = await write_360_memory(
        project_id=data["project_id"],
        tenant_key=tenant_key,
        summary="Phase 1: Backend setup",
        key_outcomes=["Database configured"],
        decisions_made=["Chose PostgreSQL"],
        db_manager=db_manager,
    )

    # Second entry
    result2 = await write_360_memory(
        project_id=data["project_id"],
        tenant_key=tenant_key,
        summary="Phase 2: API implementation",
        key_outcomes=["REST API complete"],
        decisions_made=["Used FastAPI"],
        db_manager=db_manager,
    )

    assert result1["sequence_number"] == 1
    assert result2["sequence_number"] == 2


@pytest.mark.asyncio
async def test_write_360_memory_tenant_isolation(db_manager: DatabaseManager, setup_test_data):
    """Test multi-tenant isolation."""
    data = setup_test_data
    wrong_tenant = "wrong-tenant-key"

    result = await write_360_memory(
        project_id=data["project_id"],
        tenant_key=wrong_tenant,
        summary="Unauthorized access attempt",
        key_outcomes=["Should fail"],
        decisions_made=["Should fail"],
        db_manager=db_manager,
    )

    assert result["success"] is False
    assert "not found" in result["error"].lower() or "unauthorized" in result["error"].lower()


@pytest.mark.asyncio
async def test_write_360_memory_invalid_entry_type(db_manager: DatabaseManager, tenant_key: str, setup_test_data):
    """Test validation of entry_type."""
    data = setup_test_data

    result = await write_360_memory(
        project_id=data["project_id"],
        tenant_key=tenant_key,
        summary="Test invalid entry type",
        key_outcomes=["Test"],
        decisions_made=["Test"],
        entry_type="invalid_type",
        db_manager=db_manager,
    )

    assert result["success"] is False
    assert "Invalid entry_type" in result["error"]


@pytest.mark.asyncio
async def test_write_360_memory_author_info(db_manager: DatabaseManager, tenant_key: str, setup_test_data):
    """Test author information is captured when job_id provided."""
    data = setup_test_data

    result = await write_360_memory(
        project_id=data["project_id"],
        tenant_key=tenant_key,
        summary="Test with author",
        key_outcomes=["Captured author info"],
        decisions_made=["Used job_id"],
        author_job_id=data["agent_job_id"],
        db_manager=db_manager,
    )

    assert result["success"] is True

    # Verify author info was stored in product_memory
    async with db_manager.get_session_async() as session:
        from sqlalchemy import select

        product_stmt = select(Product).where(Product.id == data["product_id"])
        product_result = await session.execute(product_stmt)
        product = product_result.scalar_one()

        history = product.product_memory["sequential_history"]
        assert len(history) == 1
        assert history[0]["author_job_id"] == data["agent_job_id"]
        assert "author_name" in history[0]
        assert "author_type" in history[0]
