"""
TDD tests for write_360_memory tool with table-based writes (Handover 0390c Phase 5).

Purpose:
Test that write_360_memory creates entries in product_memory_entries table
instead of mutating the JSONB sequential_history array.

Tool Signature:
    write_360_memory(
        project_id: str,
        tenant_key: str,
        summary: str,
        key_outcomes: List[str],
        decisions_made: List[str],
        entry_type: str = "project_completion",
        author_job_id: Optional[str] = None,
        db_manager: Optional[DatabaseManager] = None,
        session: Optional[AsyncSession] = None,
    ) -> Dict[str, Any]

Test Coverage:
1. Creates entry in product_memory_entries table
2. Does NOT mutate JSONB sequential_history
3. Sequence numbers are atomic and sequential
4. Returns entry_id from table
5. All required fields are populated
6. Respects tenant isolation
7. Validates entry_type (project_completion, handover_closeout)
8. Handles missing/invalid inputs gracefully
"""

from datetime import datetime, timezone
from uuid import uuid4

import pytest
import pytest_asyncio
from sqlalchemy import select

from src.giljo_mcp.models.agent_identity import AgentExecution, AgentJob
from src.giljo_mcp.models.products import Product
from src.giljo_mcp.models.projects import Project
from src.giljo_mcp.models.product_memory_entry import ProductMemoryEntry
from src.giljo_mcp.tools.write_360_memory import write_360_memory


# ========================================================================
# Test Fixtures
# ========================================================================


@pytest_asyncio.fixture
async def tenant_key():
    """Generate test tenant key."""
    return f"tk_test_{uuid4().hex[:16]}"


@pytest_asyncio.fixture
async def other_tenant_key():
    """Generate separate tenant key for isolation tests."""
    return f"tk_other_{uuid4().hex[:16]}"


@pytest_asyncio.fixture
async def test_product(db_session, tenant_key):
    """Create test product with empty JSONB product_memory."""
    product = Product(
        id=str(uuid4()),
        tenant_key=tenant_key,
        name="Test Product 0390c",
        description="Test product for 360 memory table writes",
        is_active=True,
        product_memory={},  # Empty JSONB - should stay empty
    )
    db_session.add(product)
    await db_session.commit()
    await db_session.refresh(product)
    return product


@pytest_asyncio.fixture
async def test_project(db_session, tenant_key, test_product):
    """Create test project linked to product."""
    project = Project(
        id=str(uuid4()),
        tenant_key=tenant_key,
        name="Test Project 0390c",
        description="Test project for 360 memory",
        product_id=test_product.id,
        mission="Test mission",
        status="active",
        created_at=datetime.now(timezone.utc),
    )
    db_session.add(project)
    await db_session.commit()
    await db_session.refresh(project)
    return project


@pytest_asyncio.fixture
async def test_agent_job(db_session, tenant_key, test_project):
    """Create test agent job for author tracking."""
    job = AgentJob(
        job_id=str(uuid4()),
        tenant_key=tenant_key,
        project_id=test_project.id,
        job_type="orchestrator",
        mission="Test orchestrator mission",
        status="active",
        created_at=datetime.now(timezone.utc),
        job_metadata={},
    )
    db_session.add(job)
    await db_session.commit()
    await db_session.refresh(job)
    return job


@pytest_asyncio.fixture
async def test_agent_execution(db_session, tenant_key, test_agent_job):
    """Create test agent execution for author tracking."""
    execution = AgentExecution(
        agent_id=str(uuid4()),
        job_id=test_agent_job.job_id,
        tenant_key=tenant_key,
        agent_display_name="orchestrator",
        agent_name="Test Orchestrator",        status="working",
        progress=50,
        messages_sent_count=0,
        messages_waiting_count=0,
        messages_read_count=0,
        health_status="healthy",
        tool_type="universal",
        context_used=5000,
        context_budget=150000,
    )
    db_session.add(execution)
    await db_session.commit()
    await db_session.refresh(execution)
    return execution


# ========================================================================
# Test Cases - Table Entry Creation
# ========================================================================


class TestWrite360MemoryTable:
    """Tests for write_360_memory tool with table-based writes."""

    @pytest.mark.asyncio
    async def test_creates_table_entry(
        self, db_session, db_manager, tenant_key, test_project, test_product
    ):
        """Entry should be created in product_memory_entries table."""
        result = await write_360_memory(
            project_id=test_project.id,
            tenant_key=tenant_key,
            summary="Completed authentication system with OAuth2 support",
            key_outcomes=["OAuth2 integration", "User management API", "JWT tokens"],
            decisions_made=["Used bcrypt for password hashing", "Redis for session storage"],
            entry_type="project_completion",
            db_manager=db_manager,
            session=db_session,
        )

        # Verify success response
        assert result["success"] is True
        assert "entry_id" in result
        assert result["sequence_number"] == 1
        assert result["entry_type"] == "project_completion"

        # Verify entry exists in database
        stmt = select(ProductMemoryEntry).where(
            ProductMemoryEntry.id == result["entry_id"],
            ProductMemoryEntry.tenant_key == tenant_key,
        )
        db_result = await db_session.execute(stmt)
        entry = db_result.scalar_one_or_none()

        assert entry is not None
        assert entry.product_id == test_product.id
        assert entry.project_id == test_project.id
        assert entry.sequence == 1
        assert entry.entry_type == "project_completion"
        assert entry.summary == "Completed authentication system with OAuth2 support"
        assert entry.key_outcomes == ["OAuth2 integration", "User management API", "JWT tokens"]
        assert entry.decisions_made == ["Used bcrypt for password hashing", "Redis for session storage"]

    @pytest.mark.asyncio
    async def test_no_jsonb_mutation(
        self, db_session, db_manager, tenant_key, test_project, test_product
    ):
        """JSONB product_memory should NOT be mutated."""
        # Verify JSONB is empty before
        assert test_product.product_memory == {}

        await write_360_memory(
            project_id=test_project.id,
            tenant_key=tenant_key,
            summary="Test summary",
            key_outcomes=["Test outcome"],
            decisions_made=["Test decision"],
            entry_type="project_completion",
            db_manager=db_manager,
            session=db_session,
        )

        # Refresh product and verify JSONB is still empty
        await db_session.refresh(test_product)
        assert test_product.product_memory == {}
        assert "sequential_history" not in test_product.product_memory

    @pytest.mark.asyncio
    async def test_atomic_sequence_generation(
        self, db_session, db_manager, tenant_key, test_project, test_product
    ):
        """Sequence numbers should be atomic and sequential."""
        # Create 3 entries
        results = []
        for i in range(3):
            result = await write_360_memory(
                project_id=test_project.id,
                tenant_key=tenant_key,
                summary=f"Summary {i+1}",
                key_outcomes=[f"Outcome {i+1}"],
                decisions_made=[f"Decision {i+1}"],
                entry_type="project_completion",
                db_manager=db_manager,
                session=db_session,
            )
            results.append(result)

        # Verify sequences are 1, 2, 3
        assert results[0]["sequence_number"] == 1
        assert results[1]["sequence_number"] == 2
        assert results[2]["sequence_number"] == 3

        # Verify in database
        stmt = select(ProductMemoryEntry).where(
            ProductMemoryEntry.product_id == test_product.id,
            ProductMemoryEntry.tenant_key == tenant_key,
        ).order_by(ProductMemoryEntry.sequence)
        db_result = await db_session.execute(stmt)
        entries = db_result.scalars().all()

        assert len(entries) == 3
        assert entries[0].sequence == 1
        assert entries[1].sequence == 2
        assert entries[2].sequence == 3

    @pytest.mark.asyncio
    async def test_returns_entry_id(
        self, db_session, db_manager, tenant_key, test_project
    ):
        """Return should include entry_id from table."""
        result = await write_360_memory(
            project_id=test_project.id,
            tenant_key=tenant_key,
            summary="Test summary",
            key_outcomes=["Test outcome"],
            decisions_made=["Test decision"],
            entry_type="project_completion",
            db_manager=db_manager,
            session=db_session,
        )

        assert result["success"] is True
        assert "entry_id" in result
        assert result["entry_id"] is not None

        # Verify entry_id is a valid UUID
        from uuid import UUID
        try:
            UUID(result["entry_id"])
        except ValueError:
            pytest.fail(f"entry_id is not a valid UUID: {result['entry_id']}")

    @pytest.mark.asyncio
    async def test_all_fields_populated(
        self, db_session, db_manager, tenant_key, test_project, test_product, test_agent_execution
    ):
        """All required fields should be populated in the entry."""
        result = await write_360_memory(
            project_id=test_project.id,
            tenant_key=tenant_key,
            summary="Comprehensive test summary",
            key_outcomes=["Outcome 1", "Outcome 2"],
            decisions_made=["Decision 1", "Decision 2"],
            entry_type="handover_closeout",
            author_job_id=test_agent_execution.job_id,
            db_manager=db_manager,
            session=db_session,
        )

        # Verify entry in database
        stmt = select(ProductMemoryEntry).where(
            ProductMemoryEntry.id == result["entry_id"]
        )
        db_result = await db_session.execute(stmt)
        entry = db_result.scalar_one()

        # Required fields
        assert entry.tenant_key == tenant_key
        assert entry.product_id == test_product.id
        assert entry.project_id == test_project.id
        assert entry.sequence == 1
        assert entry.entry_type == "handover_closeout"
        assert entry.source == "write_360_memory_v1"
        assert entry.timestamp is not None
        assert entry.project_name == test_project.name

        # Content fields
        assert entry.summary == "Comprehensive test summary"
        assert entry.key_outcomes == ["Outcome 1", "Outcome 2"]
        assert entry.decisions_made == ["Decision 1", "Decision 2"]

        # Author fields
        assert entry.author_job_id == test_agent_execution.job_id
        assert entry.author_name == "Test Orchestrator"
        assert entry.author_type == "orchestrator"

        # Optional fields
        assert entry.git_commits == []  # No git config
        assert entry.deleted_by_user is False


# ========================================================================
# Test Cases - Validation & Error Handling
# ========================================================================


class TestWrite360MemoryValidation:
    """Tests for input validation and error handling."""

    @pytest.mark.asyncio
    async def test_requires_project_id(self, db_manager, tenant_key):
        """Should return error if project_id is missing."""
        result = await write_360_memory(
            project_id="",
            tenant_key=tenant_key,
            summary="Test summary",
            key_outcomes=["Test outcome"],
            decisions_made=["Test decision"],
            db_manager=db_manager,
        )

        assert result["success"] is False
        assert "project_id is required" in result["error"]

    @pytest.mark.asyncio
    async def test_requires_summary(
        self, db_manager, tenant_key, test_project
    ):
        """Should return error if summary is missing."""
        result = await write_360_memory(
            project_id=test_project.id,
            tenant_key=tenant_key,
            summary="",
            key_outcomes=["Test outcome"],
            decisions_made=["Test decision"],
            db_manager=db_manager,
        )

        assert result["success"] is False
        assert "summary is required" in result["error"]

    @pytest.mark.asyncio
    async def test_validates_entry_type(
        self, db_session, db_manager, tenant_key, test_project
    ):
        """Should return error if entry_type is invalid."""
        result = await write_360_memory(
            project_id=test_project.id,
            tenant_key=tenant_key,
            summary="Test summary",
            key_outcomes=["Test outcome"],
            decisions_made=["Test decision"],
            entry_type="invalid_type",
            db_manager=db_manager,
            session=db_session,
        )

        assert result["success"] is False
        assert "Invalid entry_type" in result["error"]

    @pytest.mark.asyncio
    async def test_validates_summary_length(
        self, db_session, db_manager, tenant_key, test_project
    ):
        """Should return error if summary exceeds max length."""
        long_summary = "x" * 10001  # MAX_SUMMARY_LENGTH is 10000

        result = await write_360_memory(
            project_id=test_project.id,
            tenant_key=tenant_key,
            summary=long_summary,
            key_outcomes=["Test outcome"],
            decisions_made=["Test decision"],
            db_manager=db_manager,
            session=db_session,
        )

        assert result["success"] is False
        assert "Summary too long" in result["error"]

    @pytest.mark.asyncio
    async def test_project_not_found(
        self, db_session, db_manager, tenant_key
    ):
        """Should return error if project does not exist."""
        fake_project_id = str(uuid4())

        result = await write_360_memory(
            project_id=fake_project_id,
            tenant_key=tenant_key,
            summary="Test summary",
            key_outcomes=["Test outcome"],
            decisions_made=["Test decision"],
            db_manager=db_manager,
            session=db_session,
        )

        assert result["success"] is False
        assert "Project not found" in result["error"]


# ========================================================================
# Test Cases - Tenant Isolation
# ========================================================================


class TestWrite360MemoryTenantIsolation:
    """Tests for multi-tenant isolation."""

    @pytest.mark.asyncio
    async def test_tenant_isolation(
        self, db_session, db_manager, tenant_key, other_tenant_key, test_project
    ):
        """Should not allow writing to another tenant's project."""
        result = await write_360_memory(
            project_id=test_project.id,
            tenant_key=other_tenant_key,  # Wrong tenant
            summary="Test summary",
            key_outcomes=["Test outcome"],
            decisions_made=["Test decision"],
            db_manager=db_manager,
            session=db_session,
        )

        assert result["success"] is False
        assert "not found or unauthorized" in result["error"]

    @pytest.mark.asyncio
    async def test_entries_isolated_by_tenant(
        self, db_session, db_manager, tenant_key, test_project, test_product
    ):
        """Entries should only be visible to the correct tenant."""
        # Create entry
        result = await write_360_memory(
            project_id=test_project.id,
            tenant_key=tenant_key,
            summary="Test summary",
            key_outcomes=["Test outcome"],
            decisions_made=["Test decision"],
            db_manager=db_manager,
            session=db_session,
        )

        # Query with correct tenant - should find entry
        stmt = select(ProductMemoryEntry).where(
            ProductMemoryEntry.product_id == test_product.id,
            ProductMemoryEntry.tenant_key == tenant_key,
        )
        db_result = await db_session.execute(stmt)
        entries = db_result.scalars().all()
        assert len(entries) == 1

        # Query with wrong tenant - should find nothing
        other_tenant = f"tk_other_{uuid4().hex[:16]}"
        stmt = select(ProductMemoryEntry).where(
            ProductMemoryEntry.product_id == test_product.id,
            ProductMemoryEntry.tenant_key == other_tenant,
        )
        db_result = await db_session.execute(stmt)
        entries = db_result.scalars().all()
        assert len(entries) == 0
