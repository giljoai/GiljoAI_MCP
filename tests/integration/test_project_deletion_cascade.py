"""
TDD Tests for Project Deletion Cascade (Handover 0329).

Tests verify that _purge_project_records() deletes ALL related data:
- MCPAgentJob (currently works)
- Task (currently works)
- Message (currently works)
- ContextIndex (MISSING - this test should FAIL initially)
- LargeDocumentIndex (MISSING - this test should FAIL initially)
- Vision (MISSING - this test should FAIL initially)

NOTE: Session/ProjectSession removed (Handover 0423 - dead code cleanup)

TDD Phase: RED - These tests should FAIL until _purge_project_records() is fixed.
"""

from contextlib import asynccontextmanager
from datetime import datetime, timedelta, timezone
from unittest.mock import MagicMock

import pytest
from sqlalchemy import select

from src.giljo_mcp.models import Message, Product, Project, Task
from src.giljo_mcp.models.agent_identity import AgentJob, AgentExecution
from src.giljo_mcp.models.context import ContextIndex, LargeDocumentIndex
from src.giljo_mcp.models.products import Vision
from src.giljo_mcp.services.project_service import ProjectService
from src.giljo_mcp.tenant import TenantManager


@pytest.fixture
def cascade_test_tenant_key():
    """Provide a unique test tenant key for cascade tests."""
    return TenantManager.generate_tenant_key()


@pytest.fixture
async def cascade_test_product(db_session, cascade_test_tenant_key):
    """Create a test product for cascade tests."""
    product = Product(name="Cascade Test Product", tenant_key=cascade_test_tenant_key)
    db_session.add(product)
    await db_session.commit()
    await db_session.refresh(product)
    return product


@pytest.fixture
async def project_with_all_relations(db_session, cascade_test_tenant_key, cascade_test_product):
    """
    Create a project with ALL 6 related record types that should be cascade deleted.

    This fixture creates:
    1. MCPAgentJob - Agent job with embedded messages
    2. Task - A task record
    3. Message - A standalone message
    4. ContextIndex - Context index record
    5. LargeDocumentIndex - Document index record
    6. Vision - A vision document

    NOTE: ProjectSession removed (Handover 0423 - Session model deleted)
    """
    # Create expired soft-deleted project
    project = Project(
        name="Project With All Relations",
        mission="Test cascade deletion",
        description="Project with all child record types for cascade testing",
        tenant_key=cascade_test_tenant_key,
        product_id=cascade_test_product.id,
        status="deleted",
        deleted_at=datetime.now(timezone.utc) - timedelta(days=11),
    )
    db_session.add(project)
    await db_session.commit()
    await db_session.refresh(project)

    # 1. Create MCPAgentJob
    agent_job = AgentExecution(
        tenant_key=cascade_test_tenant_key,
        project_id=project.id,
        agent_display_name="implementer",
        mission="Test agent mission",
        messages=[{"content": "Embedded message", "status": "pending"}],
    )
    db_session.add(agent_job)

    # 2. Create Task
    task = Task(
        title="Cascade Test Task",
        tenant_key=cascade_test_tenant_key,
        product_id=cascade_test_product.id,
        project_id=project.id,
    )
    db_session.add(task)

    # 3. Create Message
    message = Message(
        content="Cascade test message",
        tenant_key=cascade_test_tenant_key,
        project_id=project.id,
    )
    db_session.add(message)

    # 4. Create ContextIndex
    context_index = ContextIndex(
        project_id=project.id,
        tenant_key=cascade_test_tenant_key,
        index_type="test",
        document_name="test_document.md",
        section_name="test_section",
    )
    db_session.add(context_index)

    # 5. Create LargeDocumentIndex
    doc_index = LargeDocumentIndex(
        project_id=project.id,
        tenant_key=cascade_test_tenant_key,
        document_path="/test/document.md",
        document_type="markdown",
    )
    db_session.add(doc_index)

    # NOTE: ProjectSession removed (Handover 0423 - Session model deleted)

    # 6. Create Vision
    vision = Vision(
        project_id=project.id,
        tenant_key=cascade_test_tenant_key,
        document_name="test_vision.md",
        chunk_number=1,
        content="Test vision content",
    )
    db_session.add(vision)

    await db_session.commit()

    # Refresh to get IDs
    await db_session.refresh(agent_job)
    await db_session.refresh(task)
    await db_session.refresh(message)
    await db_session.refresh(context_index)
    await db_session.refresh(doc_index)
    await db_session.refresh(vision)

    return {
        "project": project,
        "agent_job": agent_job,
        "task": task,
        "message": message,
        "context_index": context_index,
        "doc_index": doc_index,
        "vision": vision,
    }


@pytest.mark.asyncio
class TestPurgeProjectRecordsCascade:
    """
    Test suite for _purge_project_records() cascade deletion.

    TDD RED PHASE: These tests should FAIL until implementation is fixed.
    """

    async def test_purge_deletes_context_index(
        self, db_session, cascade_test_tenant_key, project_with_all_relations
    ):
        """
        Test that _purge_project_records() deletes ContextIndex records.

        Expected: FAIL (RED) - ContextIndex is NOT currently deleted by _purge_project_records().
        """
        project = project_with_all_relations["project"]
        context_index = project_with_all_relations["context_index"]

        # Verify context_index exists before purge
        stmt = select(ContextIndex).where(ContextIndex.id == context_index.id)
        result = await db_session.execute(stmt)
        assert result.scalar_one_or_none() is not None, "Context index should exist before purge"

        # Create ProjectService and run purge
        @asynccontextmanager
        async def mock_get_session():
            yield db_session

        db_manager = MagicMock()
        db_manager.get_session_async = mock_get_session

        tenant_manager = TenantManager()
        tenant_manager.set_current_tenant(cascade_test_tenant_key)
        project_service = ProjectService(db_manager, tenant_manager)

        result = await project_service.purge_deleted_project(project.id)
        assert result["success"] is True

        # BEHAVIOR: ContextIndex should be deleted
        stmt = select(ContextIndex).where(ContextIndex.id == context_index.id)
        result = await db_session.execute(stmt)
        assert result.scalar_one_or_none() is None, "ContextIndex should be deleted by purge"

    async def test_purge_deletes_large_document_index(
        self, db_session, cascade_test_tenant_key, project_with_all_relations
    ):
        """
        Test that _purge_project_records() deletes LargeDocumentIndex records.

        Expected: FAIL (RED) - LargeDocumentIndex is NOT currently deleted.
        """
        project = project_with_all_relations["project"]
        doc_index = project_with_all_relations["doc_index"]

        # Verify doc_index exists before purge
        stmt = select(LargeDocumentIndex).where(LargeDocumentIndex.id == doc_index.id)
        result = await db_session.execute(stmt)
        assert result.scalar_one_or_none() is not None, "Document index should exist before purge"

        # Create ProjectService and run purge
        @asynccontextmanager
        async def mock_get_session():
            yield db_session

        db_manager = MagicMock()
        db_manager.get_session_async = mock_get_session

        tenant_manager = TenantManager()
        tenant_manager.set_current_tenant(cascade_test_tenant_key)
        project_service = ProjectService(db_manager, tenant_manager)

        result = await project_service.purge_deleted_project(project.id)
        assert result["success"] is True

        # BEHAVIOR: LargeDocumentIndex should be deleted
        stmt = select(LargeDocumentIndex).where(LargeDocumentIndex.id == doc_index.id)
        result = await db_session.execute(stmt)
        assert result.scalar_one_or_none() is None, "LargeDocumentIndex should be deleted by purge"

    # NOTE: test_purge_deletes_project_session removed (Handover 0423 - Session model deleted)

    async def test_purge_deletes_vision(
        self, db_session, cascade_test_tenant_key, project_with_all_relations
    ):
        """
        Test that _purge_project_records() deletes Vision records.

        Expected: FAIL (RED) - Vision is NOT currently deleted.
        """
        project = project_with_all_relations["project"]
        vision = project_with_all_relations["vision"]

        # Verify vision exists before purge
        stmt = select(Vision).where(Vision.id == vision.id)
        result = await db_session.execute(stmt)
        assert result.scalar_one_or_none() is not None, "Vision should exist before purge"

        # Create ProjectService and run purge
        @asynccontextmanager
        async def mock_get_session():
            yield db_session

        db_manager = MagicMock()
        db_manager.get_session_async = mock_get_session

        tenant_manager = TenantManager()
        tenant_manager.set_current_tenant(cascade_test_tenant_key)
        project_service = ProjectService(db_manager, tenant_manager)

        result = await project_service.purge_deleted_project(project.id)
        assert result["success"] is True

        # BEHAVIOR: Vision should be deleted
        stmt = select(Vision).where(Vision.id == vision.id)
        result = await db_session.execute(stmt)
        assert result.scalar_one_or_none() is None, "Vision should be deleted by purge"

    async def test_purge_deletes_all_related_records(
        self, db_session, cascade_test_tenant_key, project_with_all_relations
    ):
        """
        Comprehensive test that ALL 7 related record types are deleted.

        This is the key test for Handover 0329.
        Expected: FAIL (RED) until _purge_project_records() is fixed.
        """
        data = project_with_all_relations
        project = data["project"]

        # Verify all records exist before purge
        records_before = {
            "project": (await db_session.execute(
                select(Project).where(Project.id == project.id)
            )).scalar_one_or_none(),
            "agent_job": (await db_session.execute(
                select(AgentExecution).where(AgentExecution.agent_id == data["agent_job"].agent_id)
            )).scalar_one_or_none(),
            "task": (await db_session.execute(
                select(Task).where(Task.id == data["task"].id)
            )).scalar_one_or_none(),
            "message": (await db_session.execute(
                select(Message).where(Message.id == data["message"].id)
            )).scalar_one_or_none(),
            "context_index": (await db_session.execute(
                select(ContextIndex).where(ContextIndex.id == data["context_index"].id)
            )).scalar_one_or_none(),
            "doc_index": (await db_session.execute(
                select(LargeDocumentIndex).where(LargeDocumentIndex.id == data["doc_index"].id)
            )).scalar_one_or_none(),
            # NOTE: "session" removed (Handover 0423 - Session model deleted)
            "vision": (await db_session.execute(
                select(Vision).where(Vision.id == data["vision"].id)
            )).scalar_one_or_none(),
        }

        # Assert all exist before purge
        for name, record in records_before.items():
            assert record is not None, f"{name} should exist before purge"

        # Create ProjectService and run purge
        @asynccontextmanager
        async def mock_get_session():
            yield db_session

        db_manager = MagicMock()
        db_manager.get_session_async = mock_get_session

        tenant_manager = TenantManager()
        tenant_manager.set_current_tenant(cascade_test_tenant_key)
        project_service = ProjectService(db_manager, tenant_manager)

        result = await project_service.purge_deleted_project(project.id)
        assert result["success"] is True, f"Purge should succeed: {result.get('error', 'unknown error')}"

        # BEHAVIOR: ALL records should be deleted after purge
        records_after = {
            "project": (await db_session.execute(
                select(Project).where(Project.id == project.id)
            )).scalar_one_or_none(),
            "agent_job": (await db_session.execute(
                select(AgentExecution).where(AgentExecution.agent_id == data["agent_job"].agent_id)
            )).scalar_one_or_none(),
            "task": (await db_session.execute(
                select(Task).where(Task.id == data["task"].id)
            )).scalar_one_or_none(),
            "message": (await db_session.execute(
                select(Message).where(Message.id == data["message"].id)
            )).scalar_one_or_none(),
            "context_index": (await db_session.execute(
                select(ContextIndex).where(ContextIndex.id == data["context_index"].id)
            )).scalar_one_or_none(),
            "doc_index": (await db_session.execute(
                select(LargeDocumentIndex).where(LargeDocumentIndex.id == data["doc_index"].id)
            )).scalar_one_or_none(),
            # NOTE: "session" removed (Handover 0423 - Session model deleted)
            "vision": (await db_session.execute(
                select(Vision).where(Vision.id == data["vision"].id)
            )).scalar_one_or_none(),
        }

        # Assert all deleted after purge
        for name, record in records_after.items():
            assert record is None, f"{name} should be deleted after purge"


@pytest.mark.asyncio
class TestPurgeExpiredProjectsCascade:
    """
    Test suite for purge_expired_deleted_projects() cascade deletion.

    Similar to _purge_project_records() but for the automated 10-day expiry purge.
    """

    async def test_expired_purge_deletes_all_related_records(
        self, db_session, cascade_test_tenant_key, project_with_all_relations
    ):
        """
        Test that purge_expired_deleted_projects() deletes ALL related record types.

        Expected: FAIL (RED) - relies on _purge_project_records() which is incomplete.
        """
        data = project_with_all_relations
        project = data["project"]

        # Create ProjectService and run expired purge
        @asynccontextmanager
        async def mock_get_session():
            yield db_session

        db_manager = MagicMock()
        db_manager.get_session_async = mock_get_session

        tenant_manager = TenantManager()
        tenant_manager.set_current_tenant(cascade_test_tenant_key)
        project_service = ProjectService(db_manager, tenant_manager)

        # Run expired purge (project is 11 days old, should be purged)
        result = await project_service.purge_expired_deleted_projects()
        assert result["success"] is True
        assert result["purged_count"] >= 1, "At least one project should be purged"

        # BEHAVIOR: ALL records should be deleted
        records_after = {
            "project": (await db_session.execute(
                select(Project).where(Project.id == project.id)
            )).scalar_one_or_none(),
            "context_index": (await db_session.execute(
                select(ContextIndex).where(ContextIndex.id == data["context_index"].id)
            )).scalar_one_or_none(),
            "doc_index": (await db_session.execute(
                select(LargeDocumentIndex).where(LargeDocumentIndex.id == data["doc_index"].id)
            )).scalar_one_or_none(),
            # NOTE: "session" removed (Handover 0423 - Session model deleted)
            "vision": (await db_session.execute(
                select(Vision).where(Vision.id == data["vision"].id)
            )).scalar_one_or_none(),
        }

        for name, record in records_after.items():
            assert record is None, f"{name} should be deleted after expired purge"


@pytest.mark.asyncio
class TestNuclearDeleteConsistency:
    """
    Test that nuclear_delete_project() and _purge_project_records()
    delete the same set of tables for consistency.
    """

    async def test_nuclear_delete_and_purge_delete_same_tables(
        self, db_session, cascade_test_tenant_key, cascade_test_product
    ):
        """
        Verify nuclear_delete_project() deletes all 7 record types.

        This test should PASS (nuclear_delete already works correctly).
        Used as reference for what _purge_project_records() should do.
        """
        # Create a project with all relations (not soft-deleted, for nuclear delete)
        project = Project(
            name="Nuclear Delete Test",
            mission="Test nuclear deletion",
            description="Project for nuclear delete testing",
            tenant_key=cascade_test_tenant_key,
            product_id=cascade_test_product.id,
            status="active",
        )
        db_session.add(project)
        await db_session.commit()
        await db_session.refresh(project)

        # Create all related records
        agent_job = AgentExecution(
            tenant_key=cascade_test_tenant_key,
            project_id=project.id,
            agent_display_name="implementer",
            mission="Nuclear test agent",
        )
        task = Task(
            title="Nuclear Test Task",
            tenant_key=cascade_test_tenant_key,
            product_id=cascade_test_product.id,
            project_id=project.id,
        )
        message = Message(
            content="Nuclear test message",
            tenant_key=cascade_test_tenant_key,
            project_id=project.id,
        )
        context_index = ContextIndex(
            project_id=project.id,
            tenant_key=cascade_test_tenant_key,
            index_type="test",
            document_name="nuclear_test.md",
        )
        doc_index = LargeDocumentIndex(
            project_id=project.id,
            tenant_key=cascade_test_tenant_key,
            document_path="/nuclear/test.md",
            document_type="markdown",
        )
        # NOTE: ProjectSession removed (Handover 0423 - Session model deleted)
        vision = Vision(
            project_id=project.id,
            tenant_key=cascade_test_tenant_key,
            document_name="nuclear_vision.md",
            chunk_number=1,
            content="Nuclear test vision",
        )

        db_session.add_all([agent_job, task, message, context_index, doc_index, vision])
        await db_session.commit()

        # Get IDs
        project_id = project.id
        job_id = agent_job.id
        task_id = task.id
        message_id = message.id
        context_index_id = context_index.id
        doc_index_id = doc_index.id
        # NOTE: session_id removed (Handover 0423 - Session model deleted)
        vision_id = vision.id

        # Create ProjectService and run nuclear delete
        @asynccontextmanager
        async def mock_get_session():
            yield db_session

        db_manager = MagicMock()
        db_manager.get_session_async = mock_get_session

        tenant_manager = TenantManager()
        tenant_manager.set_current_tenant(cascade_test_tenant_key)
        project_service = ProjectService(db_manager, tenant_manager)

        result = await project_service.nuclear_delete_project(project_id)
        assert result["success"] is True, f"Nuclear delete should succeed: {result.get('error')}"

        # BEHAVIOR: ALL records should be deleted
        assert (await db_session.execute(
            select(Project).where(Project.id == project_id)
        )).scalar_one_or_none() is None, "Project should be deleted"

        assert (await db_session.execute(
            select(AgentExecution).where(AgentExecution.agent_id == job_id)
        )).scalar_one_or_none() is None, "MCPAgentJob should be deleted"

        assert (await db_session.execute(
            select(Task).where(Task.id == task_id)
        )).scalar_one_or_none() is None, "Task should be deleted"

        assert (await db_session.execute(
            select(Message).where(Message.id == message_id)
        )).scalar_one_or_none() is None, "Message should be deleted"

        assert (await db_session.execute(
            select(ContextIndex).where(ContextIndex.id == context_index_id)
        )).scalar_one_or_none() is None, "ContextIndex should be deleted"

        assert (await db_session.execute(
            select(LargeDocumentIndex).where(LargeDocumentIndex.id == doc_index_id)
        )).scalar_one_or_none() is None, "LargeDocumentIndex should be deleted"

        # NOTE: ProjectSession assertion removed (Handover 0423 - Session model deleted)

        assert (await db_session.execute(
            select(Vision).where(Vision.id == vision_id)
        )).scalar_one_or_none() is None, "Vision should be deleted"
