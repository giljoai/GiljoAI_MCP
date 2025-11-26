"""
Integration test fixtures for Handover 0316
"""

import pytest
import pytest_asyncio
from unittest.mock import AsyncMock, MagicMock
from uuid import uuid4
from sqlalchemy.ext.asyncio import AsyncSession

from src.giljo_mcp.models import User, Product, Project
from src.giljo_mcp.database import DatabaseManager


@pytest.fixture
def mock_db_manager():
    """Mock database manager for integration tests."""
    db_manager = MagicMock()
    # Add get_product and get_project as AsyncMock methods
    db_manager.get_product = AsyncMock()
    db_manager.get_project = AsyncMock()
    # Session support
    session = AsyncMock()
    session.__aenter__ = AsyncMock(return_value=session)
    session.__aexit__ = AsyncMock(return_value=False)
    session.get = AsyncMock()
    session.commit = AsyncMock()
    session.refresh = AsyncMock()
    db_manager.get_session = MagicMock(return_value=session)
    db_manager.session = session
    return db_manager


@pytest_asyncio.fixture
async def test_user(db_session: AsyncSession):
    """Create test user with tenant"""
    user = User(
        username=f"testuser_{uuid4().hex[:8]}",
        email=f"test_{uuid4().hex[:8]}@example.com",
        tenant_key=f"tenant_{uuid4().hex[:8]}",
        role="developer",
        password_hash="hashed_password",
    )
    db_session.add(user)
    await db_session.commit()
    await db_session.refresh(user)
    return user


@pytest_asyncio.fixture
async def test_user_2(db_session: AsyncSession):
    """Create second test user (different tenant for isolation tests)"""
    user = User(
        username=f"testuser2_{uuid4().hex[:8]}",
        email=f"test2_{uuid4().hex[:8]}@example.com",
        tenant_key=f"tenant2_{uuid4().hex[:8]}",
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
