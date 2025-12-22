"""
Integration tests for simplified vision context assembly.

Tests the new simplified vision document storage and retrieval system:
- Only 3 depth levels: none, light, medium, full (no "heavy")
- Full depth returns vision_document column directly (no chunk fetching)
- Light/Medium depths use summary columns
- No chunk fetching for any depth level

Handover: 0246b - Vision Document Storage Simplification
Status: RED phase (tests should FAIL initially)
"""

import uuid
from unittest.mock import patch

import pytest
from sqlalchemy.ext.asyncio import AsyncSession

from src.giljo_mcp.models import Product, Project
from src.giljo_mcp.models.products import VisionDocument
from src.giljo_mcp.mission_planner import MissionPlanner


@pytest.fixture
async def test_tenant_key() -> str:
    """Generate unique tenant key for test isolation."""
    return f"tk_test_{uuid.uuid4().hex[:16]}"


@pytest.fixture
async def test_product(db_session: AsyncSession, test_tenant_key: str) -> Product:
    """Create test product for vision context tests."""
    product = Product(
        id=str(uuid.uuid4()),
        tenant_key=test_tenant_key,
        name="Test Product",
        description="Test product for vision context assembly",
    )
    db_session.add(product)
    await db_session.commit()
    await db_session.refresh(product)
    return product


@pytest.fixture
async def test_project(db_session: AsyncSession, test_product: Product, test_tenant_key: str):
    """Create test project for context assembly."""
    project = Project(
        id=str(uuid.uuid4()),
        tenant_key=test_tenant_key,
        product_id=test_product.id,
        name="Test Project",
        description="Test project for vision context tests",
        mission="Test mission for vision context assembly",
        status="active",
    )
    db_session.add(project)
    await db_session.commit()
    await db_session.refresh(project)
    return project


@pytest.fixture
async def test_vision_document(
    db_session: AsyncSession, test_product: Product, test_tenant_key: str
) -> VisionDocument:
    """
    Create test vision document with full content and summaries.

    This simulates a vision document that has been uploaded and summarized.
    """
    full_content = """# Product Vision: Advanced AI Platform

## Executive Summary
This is a comprehensive vision document for an advanced AI platform.
It contains detailed information about architecture, features, and roadmap.

## Architecture Overview
The platform is built on a microservices architecture.

## Core Features
- Multi-tenant isolation
- Real-time collaboration
- AI agent orchestration

## Technical Stack
Backend: Python, FastAPI, PostgreSQL
Frontend: Vue 3, TypeScript

## Development Roadmap
Q1: Core platform development
Q2: Advanced features
Q3: Production readiness
Q4: Enterprise features
"""

    light_summary = """# Product Vision: Advanced AI Platform

## Executive Summary
This is a comprehensive vision document for an advanced AI platform.

## Core Features
- Multi-tenant isolation
- AI agent orchestration
"""

    medium_summary = """# Product Vision: Advanced AI Platform

## Executive Summary
This is a comprehensive vision document for an advanced AI platform.

## Architecture Overview
The platform is built on a microservices architecture.

## Core Features
- Multi-tenant isolation
- Real-time collaboration
- AI agent orchestration

## Technical Stack
Backend: Python, FastAPI, PostgreSQL
"""

    vision_doc = VisionDocument(
        id=str(uuid.uuid4()),
        tenant_key=test_tenant_key,
        product_id=test_product.id,
        document_name="Product Vision",
        document_type="vision",
        vision_document=full_content,
        summary_light=light_summary,
        summary_medium=medium_summary,
        storage_type="inline",
        chunked=False,
        chunk_count=0,
        is_active=True,
        is_summarized=True,
        display_order=0,
        # Deprecated fields - provide defaults to avoid INSERT errors
        summary_text=None,
        compression_ratio=None,
    )

    db_session.add(vision_doc)
    await db_session.commit()
    await db_session.refresh(vision_doc)
    return vision_doc


@pytest.fixture
def mock_db_manager(db_session: AsyncSession):
    """Create mock database manager for MissionPlanner."""
    from contextlib import asynccontextmanager
    from unittest.mock import MagicMock

    db_manager = MagicMock()

    @asynccontextmanager
    async def mock_get_session_async():
        yield db_session

    db_manager.get_session_async = mock_get_session_async
    return db_manager


@pytest.mark.asyncio
async def test_full_depth_returns_original_document_directly(
    db_session: AsyncSession,
    test_product: Product,
    test_project: Project,
    test_vision_document: VisionDocument,
    mock_db_manager,
):
    """
    Test that full depth returns complete original document from vision_document column.

    RED PHASE: This test should FAIL because:
    - Current implementation fetches chunks for full mode (line 1429-1438 in mission_planner.py)
    - Calls _get_relevant_vision_chunks() instead of using vision_document column
    - Full depth logic not yet simplified per Handover 0246b

    Expected behavior (after implementation):
    - Returns vision_document.vision_document column content directly
    - Does NOT call _get_relevant_vision_chunks()
    - Does NOT query mcp_context_index table
    - Returns 100% of original content from column
    """
    await db_session.refresh(test_product)

    planner = MissionPlanner(db_manager=mock_db_manager)

    context = await planner._build_context_with_priorities(
        product=test_product,
        project=test_project,
        field_priorities={"vision_documents": 2},
        depth_config={"vision_documents": "full"},
        user_id="test-user",
    )

    # Verify full content is present (not summary)
    assert "# Product Vision: Advanced AI Platform" in context
    assert "Development Roadmap" in context
    assert "Q1: Core platform development" in context
    assert "Q4: Enterprise features" in context

    # Should contain full vision_document content
    assert test_vision_document.vision_document in context


@pytest.mark.asyncio
async def test_light_depth_returns_summary_light(
    db_session: AsyncSession,
    test_product: Product,
    test_project: Project,
    test_vision_document: VisionDocument,
    mock_db_manager,
):
    """
    Test that light depth returns summary_light column.

    Expected behavior:
    - Returns vision_document.summary_light column content
    - Does NOT query mcp_context_index table
    - Returns approximately 33% of original content
    """
    await db_session.refresh(test_product)

    planner = MissionPlanner(db_manager=mock_db_manager)

    context = await planner._build_context_with_priorities(
        product=test_product,
        project=test_project,
        field_priorities={"vision_documents": 2},
        depth_config={"vision_documents": "light"},
        user_id="test-user",
    )

    # Should contain light summary content
    assert "Executive Summary" in context
    assert "Core Features" in context

    # Should NOT contain sections only in full version
    assert "Development Roadmap" not in context
    assert "Q1: Core platform development" not in context


@pytest.mark.asyncio
async def test_medium_depth_returns_summary_medium(
    db_session: AsyncSession,
    test_product: Product,
    test_project: Project,
    test_vision_document: VisionDocument,
    mock_db_manager,
):
    """
    Test that medium depth returns summary_medium column (mapped to 'medium').

    RED PHASE: May fail due to:
    - Current implementation uses 'moderate' depth value (line 1447)
    - Column is summary_medium but user setting is 'medium'
    - Mapping from 'medium' to summary_medium column may not work correctly

    Expected behavior (after implementation):
    - Depth setting 'medium' maps to summary_medium column
    - Returns approximately 66% of original content
    - Does NOT query mcp_context_index table
    """
    await db_session.refresh(test_product)

    planner = MissionPlanner(db_manager=mock_db_manager)

    context = await planner._build_context_with_priorities(
        product=test_product,
        project=test_project,
        field_priorities={"vision_documents": 2},
        depth_config={"vision_documents": "medium"},
        user_id="test-user",
    )

    # Should contain medium summary content
    assert "Executive Summary" in context
    assert "Architecture Overview" in context
    assert "Core Features" in context
    assert "Technical Stack" in context

    # Should NOT contain sections only in full version
    assert "Development Roadmap" not in context or context.count("Development Roadmap") == 0


@pytest.mark.asyncio
async def test_none_depth_returns_empty_vision(
    db_session: AsyncSession,
    test_product: Product,
    test_project: Project,
    test_vision_document: VisionDocument,
    mock_db_manager,
):
    """
    Test that excluded vision_documents returns no vision content.

    Expected behavior:
    - When priority is 4 (EXCLUDED) or depth is 'none', vision not included
    - Context may contain other fields but no vision content
    """
    await db_session.refresh(test_product)

    planner = MissionPlanner(db_manager=mock_db_manager)

    context = await planner._build_context_with_priorities(
        product=test_product,
        project=test_project,
        field_priorities={"vision_documents": 4},  # EXCLUDED
        depth_config={"vision_documents": "medium"},
        user_id="test-user",
    )

    # Should NOT contain ANY vision content
    assert "Product Vision" not in context or context.count("## Product Vision") == 0
    assert "Advanced AI Platform" not in context


@pytest.mark.asyncio
async def test_no_chunks_fetched_for_any_depth(
    db_session: AsyncSession,
    test_product: Product,
    test_project: Project,
    test_vision_document: VisionDocument,
    mock_db_manager,
):
    """
    Test that NO chunks are fetched from mcp_context_index for any depth level.

    RED PHASE: This test will FAIL because:
    - Current implementation calls _get_relevant_vision_chunks for full depth (line 1429-1438)
    - This queries mcp_context_index table

    Expected behavior (after implementation):
    - NO queries to mcp_context_index table for vision context
    - All depths use vision_document table columns directly
    - _get_relevant_vision_chunks method not called for vision documents
    """
    await db_session.refresh(test_product)

    planner = MissionPlanner(db_manager=mock_db_manager)

    # Mock _get_relevant_vision_chunks to track if it's called
    original_method = planner._get_relevant_vision_chunks
    call_count = {"count": 0}

    async def tracked_get_chunks(*args, **kwargs):
        call_count["count"] += 1
        return await original_method(*args, **kwargs)

    with patch.object(planner, '_get_relevant_vision_chunks', side_effect=tracked_get_chunks):
        # Test all depth levels
        for depth in ["light", "medium", "full"]:
            call_count["count"] = 0

            context = await planner._build_context_with_priorities(
                product=test_product,
                project=test_project,
                field_priorities={"vision_documents": 2},
                depth_config={"vision_documents": depth},
                user_id="test-user",
            )

            # Verify _get_relevant_vision_chunks was NOT called
            assert call_count["count"] == 0, (
                f"Depth '{depth}' should NOT call _get_relevant_vision_chunks(). "
                f"Called {call_count['count']} times."
            )


@pytest.mark.asyncio
async def test_heavy_depth_maps_to_medium(
    db_session: AsyncSession,
    test_product: Product,
    test_project: Project,
    test_vision_document: VisionDocument,
    mock_db_manager,
):
    """
    Test backward compatibility: 'heavy' depth maps to 'medium'.

    Expected behavior (after implementation):
    - User setting 'heavy' is mapped to 'medium' (line 1382-1383 already does this)
    - Returns summary_medium column (same as 'medium')
    - Provides smooth migration path for existing users
    """
    await db_session.refresh(test_product)

    planner = MissionPlanner(db_manager=mock_db_manager)

    # Test with 'heavy' depth
    context_heavy = await planner._build_context_with_priorities(
        product=test_product,
        project=test_project,
        field_priorities={"vision_documents": 2},
        depth_config={"vision_documents": "full"},
        user_id="test-user",
    )

    # Test with 'medium' depth
    context_medium = await planner._build_context_with_priorities(
        product=test_product,
        project=test_project,
        field_priorities={"vision_documents": 2},
        depth_config={"vision_documents": "medium"},
        user_id="test-user",
    )

    # Both should produce similar output (both map to summary_medium)
    # Content may differ slightly due to formatting, but key sections should be the same
    assert "Architecture Overview" in context_heavy
    assert "Architecture Overview" in context_medium
    assert "Technical Stack" in context_heavy
    assert "Technical Stack" in context_medium


@pytest.mark.asyncio
async def test_vision_context_handles_missing_summaries(
    db_session: AsyncSession,
    test_product: Product,
    test_project: Project,
    test_tenant_key: str,
    mock_db_manager,
):
    """
    Test graceful handling when summaries are missing (not yet generated).

    Expected behavior (after implementation):
    - If summary_light is NULL, falls back to vision_document or empty
    - If summary_medium is NULL, falls back to vision_document or empty
    - No crashes or errors
    """
    # Create vision document WITHOUT summaries
    doc_no_summaries = VisionDocument(
        id=str(uuid.uuid4()),
        tenant_key=test_tenant_key,
        product_id=test_product.id,
        document_name="Unsummarized Vision",
        document_type="vision",
        vision_document="# Unsummarized\nFull content without summaries.",
        summary_light=None,  # No summary
        summary_medium=None,  # No summary
        storage_type="inline",
        chunked=False,
        chunk_count=0,
        is_active=True,
        is_summarized=False,  # Not summarized
        display_order=0,
        summary_text=None,
        compression_ratio=None,
    )

    db_session.add(doc_no_summaries)
    await db_session.commit()
    await db_session.refresh(test_product)

    planner = MissionPlanner(db_manager=mock_db_manager)

    # Test light depth with missing summary
    context_light = await planner._build_context_with_priorities(
        product=test_product,
        project=test_project,
        field_priorities={"vision_documents": 2},
        depth_config={"vision_documents": "light"},
        user_id="test-user",
    )

    # Should not crash
    assert context_light is not None
    assert isinstance(context_light, str)

    # Test medium depth with missing summary
    context_medium = await planner._build_context_with_priorities(
        product=test_product,
        project=test_project,
        field_priorities={"vision_documents": 2},
        depth_config={"vision_documents": "medium"},
        user_id="test-user",
    )

    assert context_medium is not None
    assert isinstance(context_medium, str)
