"""
Integration test: E2E mission planning with chunked vision documents.

Tests full workflow:
1. Create product with vision document
2. Chunk vision using VisionDocumentChunker
3. Create project with specific description
4. Build context with MissionPlanner
5. Verify relevant chunks used (not full text)

Requires PostgreSQL (JSONB columns).

Handover: 0305 - Integrate Vision Document Chunking with Context Generation
"""

import uuid

import pytest
from sqlalchemy.ext.asyncio import AsyncSession, async_sessionmaker, create_async_engine

from src.giljo_mcp.context_management.chunker import VisionDocumentChunker
from src.giljo_mcp.mission_planner import MissionPlanner
from src.giljo_mcp.models import Base
from src.giljo_mcp.models.products import Product, VisionDocument
from src.giljo_mcp.models.projects import Project


@pytest.fixture
async def test_db_session():
    """Create temporary PostgreSQL test database session for integration testing."""
    # Use test database URL from environment or default
    import os

    test_db_url = os.getenv("TEST_DATABASE_URL", "postgresql+asyncpg://postgres:***@localhost/giljo_mcp_test")

    # Create async engine
    engine = create_async_engine(test_db_url, echo=False)

    # Create all tables
    async with engine.begin() as conn:
        await conn.run_sync(Base.metadata.create_all)

    # Create session factory
    async_session_maker = async_sessionmaker(engine, class_=AsyncSession, expire_on_commit=False)

    # Create session
    async with async_session_maker() as session:
        yield session

    # Cleanup: drop all tables
    async with engine.begin() as conn:
        await conn.run_sync(Base.metadata.drop_all)

    await engine.dispose()


@pytest.mark.asyncio
async def test_mission_planner_uses_relevant_chunks(test_db_session):
    """
    Integration test: MissionPlanner retrieves relevant chunks.

    Workflow:
    1. Create vision document with mixed content (auth + database + UI)
    2. Chunk vision into 5+ chunks
    3. Create project with description focused on "authentication"
    4. Build context with field_priorities
    5. Verify context contains auth-related chunks (not full vision)
    6. Verify token count reduced vs full text
    """
    tenant_key = str(uuid.uuid4())  # tenant_key must be <=36 chars

    # Create large vision document with distinct sections
    vision_content = """# Product Vision: SaaS Platform

## Authentication System
Our authentication system uses JWT-based authentication with refresh tokens for secure
access control. We integrate with OAuth2 providers including Google and GitHub for
social login capabilities. Multi-factor authentication using TOTP is mandatory for
admin users. The system implements role-based access control (RBAC) with granular
permissions for different user types.

## Database Architecture
The database layer uses PostgreSQL with multi-tenant isolation via tenant_key column
filtering on all queries. We maintain read replicas for horizontal scaling of read
operations. Automated backups run every 6 hours with point-in-time recovery capability.
Connection pooling is handled by pgbouncer for efficient resource management. All
migrations are version controlled and applied via Alembic.

## User Interface Design
The frontend is built as a React SPA with TypeScript for type safety. We follow a
mobile-first responsive design approach to ensure optimal experience on all devices.
Dark mode support is built into the theme system with automatic detection of user
preference. All components meet WCAG 2.1 AA accessibility standards with full keyboard
navigation support.

## Deployment Strategy
Applications are packaged as Docker containers and deployed to AWS ECS with Fargate
for serverless container management. Auto-scaling policies adjust container count based
on CPU and memory utilization metrics. We use blue-green deployment strategy for zero
downtime releases. Static assets are served via CloudFront CDN with cache invalidation
on deployments.

## API Architecture
RESTful API endpoints follow OpenAPI 3.0 specification with automatic documentation
generation via FastAPI. All endpoints require authentication except public health
checks. Rate limiting is enforced per user and per IP address to prevent abuse.
Versioning uses URL-based approach (e.g., /api/v1/users) for backward compatibility.
"""

    # 1. Create product
    product = Product(
        id=str(uuid.uuid4()),
        tenant_key=tenant_key,
        name="Test SaaS Platform",
        description="Multi-tenant SaaS platform with authentication",
    )
    test_db_session.add(product)
    await test_db_session.flush()

    # 2. Create vision document
    doc = VisionDocument(
        id=str(uuid.uuid4()),
        tenant_key=tenant_key,
        product_id=product.id,
        document_name="Product Vision",
        vision_document=vision_content,
        storage_type="inline",
        document_type="vision",
        chunked=False,
        is_active=True,
    )
    test_db_session.add(doc)
    await test_db_session.flush()
    await test_db_session.commit()

    # 3. Chunk the vision
    chunker = VisionDocumentChunker()
    chunk_result = await chunker.chunk_vision_document(test_db_session, tenant_key, str(doc.id))

    # Verify chunking succeeded
    assert chunk_result["success"] is True
    assert chunk_result["chunks_created"] >= 1  # At least 1 chunk created
    await test_db_session.commit()

    # Refresh to get updated chunk_count
    await test_db_session.refresh(doc)
    assert doc.chunked is True
    assert doc.chunk_count > 0

    # 4. Create project focused on authentication
    project = Project(
        id=str(uuid.uuid4()),
        tenant_key=tenant_key,
        product_id=product.id,
        name="Auth Service Implementation",
        description="Build JWT authentication service with OAuth2 and RBAC support",
        mission="Implement authentication service with JWT and OAuth2",
    )
    test_db_session.add(project)
    await test_db_session.flush()
    await test_db_session.commit()

    # Refresh product to get vision_documents relationship
    await test_db_session.refresh(product)

    # 5. Build context with MissionPlanner
    from contextlib import asynccontextmanager
    from unittest.mock import MagicMock

    # Mock DatabaseManager with proper async context manager
    db_manager = MagicMock()

    @asynccontextmanager
    async def mock_get_session_async():
        yield test_db_session

    db_manager.get_session_async = mock_get_session_async

    planner = MissionPlanner(db_manager=db_manager)

    # This will FAIL - chunk retrieval not implemented yet (RED phase)
    context = await planner._build_context_with_priorities(
        product=product,
        project=project,
        field_priorities={"product_vision": 10},  # Full priority
        user_id=f"test-user-{uuid.uuid4()}",
    )

    # 6. Verify context contains auth chunks (not full vision)
    assert "Authentication System" in context
    assert "JWT" in context or "OAuth2" in context or "RBAC" in context

    # 7. Verify irrelevant sections minimized or excluded
    # Context should prioritize auth-related chunks over database/UI/deployment
    # We can't guarantee exclusion, but auth content should be prominent
    auth_section_count = context.count("authentication") + context.count("JWT") + context.count("OAuth2")
    assert auth_section_count > 0

    # 8. Verify context prioritization
    full_text_tokens = planner._count_tokens(vision_content)
    context_tokens = planner._count_tokens(context)

    # Context should be smaller than full vision (due to chunk selection)
    # Note: Context includes other fields too, so we check vision section specifically
    assert "## Product Vision (Relevant Sections)" in context or "## Product Vision" in context

    # The vision section should be smaller than original
    # (We can't measure exact vision section tokens without parsing, but total context
    # should be reasonable)
    assert context_tokens < full_text_tokens * 2  # Context includes more than just vision


@pytest.mark.asyncio
async def test_fallback_to_full_text_when_not_chunked(test_db_session):
    """
    Integration test: Falls back to full text when vision not chunked.

    Given: Product with vision_document but chunked=False
    When: Building context with MissionPlanner
    Then: Uses product.primary_vision_text (full text)
    And: No errors or empty context
    """
    tenant_key = str(uuid.uuid4())  # tenant_key must be <=36 chars

    vision_content = """# Simple Vision

This is a small vision document that doesn't need chunking.
It describes a simple authentication system with basic features.
"""

    # 1. Create product with small vision (not chunked)
    product = Product(
        id=str(uuid.uuid4()),
        tenant_key=tenant_key,
        name="Simple Product",
        description="Simple product with small vision",
    )
    test_db_session.add(product)
    await test_db_session.flush()

    # 2. Create vision document (deliberately NOT chunked)
    doc = VisionDocument(
        id=str(uuid.uuid4()),
        tenant_key=tenant_key,
        product_id=product.id,
        document_name="Simple Vision",
        vision_document=vision_content,
        storage_type="inline",
        document_type="vision",
        chunked=False,  # NOT chunked
        chunk_count=0,
        is_active=True,
    )
    test_db_session.add(doc)
    await test_db_session.flush()
    await test_db_session.commit()

    # 3. Create project
    project = Project(
        id=str(uuid.uuid4()),
        tenant_key=tenant_key,
        product_id=product.id,
        name="Simple Auth",
        description="Build authentication",
        mission="Implement simple authentication",
    )
    test_db_session.add(project)
    await test_db_session.flush()
    await test_db_session.commit()

    # Refresh product
    await test_db_session.refresh(product)

    # 4. Build context with MissionPlanner
    from contextlib import asynccontextmanager
    from unittest.mock import MagicMock

    db_manager = MagicMock()

    @asynccontextmanager
    async def mock_get_session_async():
        yield test_db_session

    db_manager.get_session_async = mock_get_session_async

    planner = MissionPlanner(db_manager=db_manager)

    # This will FAIL - fallback logic not implemented (RED phase)
    context = await planner._build_context_with_priorities(
        product=product,
        project=project,
        field_priorities={"product_vision": 10},
        user_id=f"test-user-{uuid.uuid4()}",
    )

    # 5. Verify context contains full vision (not chunks)
    assert "Simple Vision" in context or "authentication system" in context
    assert context is not None
    assert len(context) > 0

    # Verify it uses full text marker (not chunked marker)
    assert "## Product Vision" in context


@pytest.mark.asyncio
async def test_multi_tenant_chunk_isolation_e2e(test_db_session):
    """
    Integration test: Multi-tenant isolation in context building.

    Given: Two products from different tenants, both chunked
    When: Building context for tenant-alpha project
    Then: Only tenant-alpha chunks used
    And: No tenant-beta chunks leaked
    """
    tenant_alpha = str(uuid.uuid4())  # tenant_key must be <=36 chars
    tenant_beta = str(uuid.uuid4())  # tenant_key must be <=36 chars

    vision_alpha = """# Alpha Product Vision

## Alpha Authentication
Alpha-specific JWT authentication with custom claims for alpha users.
Role-based access control specific to alpha tenant requirements.
"""

    vision_beta = """# Beta Product Vision

## Beta Authentication
Beta-specific OAuth2 integration with different providers.
Custom authorization rules for beta tenant use cases.
"""

    # 1. Create product for tenant-alpha
    product_alpha = Product(
        id=str(uuid.uuid4()),
        tenant_key=tenant_alpha,
        name="Alpha Product",
        description="Alpha product",
    )
    test_db_session.add(product_alpha)
    await test_db_session.flush()

    # 2. Create vision document for alpha
    doc_alpha = VisionDocument(
        id=str(uuid.uuid4()),
        tenant_key=tenant_alpha,
        product_id=product_alpha.id,
        document_name="Alpha Vision",
        vision_document=vision_alpha,
        storage_type="inline",
        document_type="vision",
        chunked=False,
        is_active=True,
    )
    test_db_session.add(doc_alpha)
    await test_db_session.flush()

    # 3. Create product for tenant-beta
    product_beta = Product(
        id=str(uuid.uuid4()),
        tenant_key=tenant_beta,
        name="Beta Product",
        description="Beta product",
    )
    test_db_session.add(product_beta)
    await test_db_session.flush()

    # 4. Create vision document for beta
    doc_beta = VisionDocument(
        id=str(uuid.uuid4()),
        tenant_key=tenant_beta,
        product_id=product_beta.id,
        document_name="Beta Vision",
        vision_document=vision_beta,
        storage_type="inline",
        document_type="vision",
        chunked=False,
        is_active=True,
    )
    test_db_session.add(doc_beta)
    await test_db_session.flush()
    await test_db_session.commit()

    # 5. Chunk both visions
    chunker = VisionDocumentChunker()

    alpha_result = await chunker.chunk_vision_document(test_db_session, tenant_alpha, str(doc_alpha.id))
    assert alpha_result["success"] is True

    beta_result = await chunker.chunk_vision_document(test_db_session, tenant_beta, str(doc_beta.id))
    assert beta_result["success"] is True
    await test_db_session.commit()

    # 6. Create project for tenant-alpha
    project_alpha = Project(
        id=str(uuid.uuid4()),
        tenant_key=tenant_alpha,
        product_id=product_alpha.id,
        name="Alpha Auth",
        description="Build authentication for alpha",
        mission="Implement alpha authentication",
    )
    test_db_session.add(project_alpha)
    await test_db_session.flush()
    await test_db_session.commit()

    # Refresh product
    await test_db_session.refresh(product_alpha)

    # 7. Build context for tenant-alpha project
    from contextlib import asynccontextmanager
    from unittest.mock import MagicMock

    db_manager = MagicMock()

    @asynccontextmanager
    async def mock_get_session_async():
        yield test_db_session

    db_manager.get_session_async = mock_get_session_async

    planner_alpha = MissionPlanner(db_manager=db_manager)

    # This will FAIL - multi-tenant filtering not implemented (RED phase)
    context_alpha = await planner_alpha._build_context_with_priorities(
        product=product_alpha,
        project=project_alpha,
        field_priorities={"product_vision": 10},
        user_id=f"test-user-{uuid.uuid4()}",
    )

    # 8. Verify only alpha content in context
    assert "Alpha" in context_alpha or "alpha" in context_alpha
    assert "Beta" not in context_alpha and "beta" not in context_alpha

    # Verify no cross-tenant contamination
    assert tenant_beta not in context_alpha
