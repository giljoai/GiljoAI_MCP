"""
TDD tests for close_project_and_update_memory with table-based writes (Handover 0390c Phase 5).

Purpose:
Test that close_project_and_update_memory creates entries in product_memory_entries table
instead of mutating the JSONB sequential_history array.

Tool Signature:
    close_project_and_update_memory(
        project_id: str,
        summary: str,
        key_outcomes: List[str],
        decisions_made: List[str],
        tenant_key: str,
        db_manager: Optional[DatabaseManager] = None,
        session: Optional[AsyncSession] = None,
    ) -> Dict[str, Any]

Test Coverage:
1. Creates entry with type="project_closeout"
2. All fields are populated (including computed fields)
3. Does NOT mutate JSONB sequential_history
4. Sequence numbers are atomic
5. Returns entry_id from table
6. Respects tenant isolation
7. Handles GitHub commits if configured
"""

from datetime import datetime, timezone
from uuid import uuid4

import pytest
import pytest_asyncio
from sqlalchemy import select

from src.giljo_mcp.models.product_memory_entry import ProductMemoryEntry
from src.giljo_mcp.models.products import Product
from src.giljo_mcp.models.projects import Project
from src.giljo_mcp.tools.project_closeout import close_project_and_update_memory


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
        name="Test Product 0390c Closeout",
        description="Test product for project closeout",
        is_active=True,
        product_memory={},  # Empty JSONB - should stay empty
    )
    db_session.add(product)
    await db_session.commit()
    await db_session.refresh(product)
    return product


@pytest_asyncio.fixture
async def test_product_with_git(db_session, tenant_key):
    """Create test product with GitHub integration enabled."""
    product = Product(
        id=str(uuid4()),
        tenant_key=tenant_key,
        name="Test Product with Git",
        description="Test product with GitHub integration",
        is_active=True,
        product_memory={
            "git_integration": {
                "enabled": True,
                "repo_name": "test-repo",
                "repo_owner": "test-owner",
                "access_token": None,  # No token = will fail gracefully
            }
        },
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
        name="Test Project Closeout",
        description="Test project for closeout",
        product_id=test_product.id,
        mission="Test mission",
        status="active",
        created_at=datetime.now(timezone.utc),
        meta_data={"test_coverage": 85.5},  # For metrics testing
    )
    db_session.add(project)
    await db_session.commit()
    await db_session.refresh(project)
    return project


@pytest_asyncio.fixture
async def test_project_with_git(db_session, tenant_key, test_product_with_git):
    """Create test project with GitHub-enabled product."""
    project = Project(
        id=str(uuid4()),
        tenant_key=tenant_key,
        name="Test Project with Git",
        description="Test project with git integration",
        product_id=test_product_with_git.id,
        mission="Test mission",
        status="active",
        created_at=datetime.now(timezone.utc),
    )
    db_session.add(project)
    await db_session.commit()
    await db_session.refresh(project)
    return project


# ========================================================================
# Test Cases - Project Closeout Entry Creation
# ========================================================================


class TestProjectCloseoutTable:
    """Tests for close_project_and_update_memory with table-based writes."""

    @pytest.mark.asyncio
    async def test_creates_closeout_entry(self, db_session, db_manager, tenant_key, test_project, test_product):
        """Entry should be created with type='project_closeout'."""
        result = await close_project_and_update_memory(
            project_id=test_project.id,
            tenant_key=tenant_key,
            summary="Completed authentication system with OAuth2 support",
            key_outcomes=["OAuth2 integration", "User management API", "JWT tokens"],
            decisions_made=["Used bcrypt for password hashing", "Redis for session storage"],
            db_manager=db_manager,
            session=db_session,
        )

        # Verify success response
        assert result["success"] is True
        assert "entry_id" in result
        assert result["sequence_number"] == 1
        assert result["git_commits_count"] == 0  # No git config

        # Verify entry exists in database with correct type
        stmt = select(ProductMemoryEntry).where(
            ProductMemoryEntry.id == result["entry_id"],
            ProductMemoryEntry.tenant_key == tenant_key,
        )
        db_result = await db_session.execute(stmt)
        entry = db_result.scalar_one_or_none()

        assert entry is not None
        assert entry.entry_type == "project_closeout"
        assert entry.source == "closeout_v1"

    @pytest.mark.asyncio
    async def test_all_fields_populated(self, db_session, db_manager, tenant_key, test_project, test_product):
        """All fields should be populated (including computed fields)."""
        result = await close_project_and_update_memory(
            project_id=test_project.id,
            tenant_key=tenant_key,
            summary="Comprehensive closeout summary with multiple achievements",
            key_outcomes=["Feature A complete", "Feature B deployed", "Bug fix C"],
            decisions_made=["Architecture decision 1", "Tech stack choice 2"],
            db_manager=db_manager,
            session=db_session,
        )

        # Verify entry in database
        stmt = select(ProductMemoryEntry).where(ProductMemoryEntry.id == result["entry_id"])
        db_result = await db_session.execute(stmt)
        entry = db_result.scalar_one()

        # Core identity fields
        assert entry.tenant_key == tenant_key
        assert entry.product_id == test_product.id
        assert entry.project_id == test_project.id
        assert entry.sequence == 1
        assert entry.entry_type == "project_closeout"
        assert entry.source == "closeout_v1"
        assert entry.timestamp is not None
        assert entry.project_name == test_project.name

        # Content fields
        assert entry.summary == "Comprehensive closeout summary with multiple achievements"
        assert entry.key_outcomes == ["Feature A complete", "Feature B deployed", "Bug fix C"]
        assert entry.decisions_made == ["Architecture decision 1", "Tech stack choice 2"]

        # Computed fields (from helper functions)
        assert entry.deliverables is not None
        assert isinstance(entry.deliverables, list)
        assert entry.metrics is not None
        assert isinstance(entry.metrics, dict)
        assert entry.metrics["test_coverage"] == 85.5  # From project.meta_data
        assert entry.priority is not None
        assert isinstance(entry.priority, int)
        assert 1 <= entry.priority <= 3  # Priority range
        assert entry.significance_score is not None
        assert isinstance(entry.significance_score, float)
        assert 0.0 <= entry.significance_score <= 1.0
        assert entry.token_estimate is not None
        assert isinstance(entry.token_estimate, int)
        assert entry.token_estimate > 0
        assert entry.tags is not None
        assert isinstance(entry.tags, list)

        # Optional fields
        assert entry.git_commits == []  # No git config
        assert entry.deleted_by_user is False

    @pytest.mark.asyncio
    async def test_no_jsonb_mutation(self, db_session, db_manager, tenant_key, test_project, test_product):
        """JSONB product_memory should NOT be mutated."""
        # Verify JSONB is empty before
        assert test_product.product_memory == {}

        await close_project_and_update_memory(
            project_id=test_project.id,
            tenant_key=tenant_key,
            summary="Test summary",
            key_outcomes=["Test outcome"],
            decisions_made=["Test decision"],
            db_manager=db_manager,
            session=db_session,
        )

        # Refresh product and verify JSONB is still empty
        await db_session.refresh(test_product)
        assert test_product.product_memory == {}
        assert "sequential_history" not in test_product.product_memory

    @pytest.mark.asyncio
    async def test_atomic_sequence_generation(self, db_session, db_manager, tenant_key, test_product):
        """Sequence numbers should be atomic and sequential."""
        # Create 3 projects and close them
        # Note: Only one active project allowed per product, so we set status="completed"
        # for previous projects after closing them
        results = []
        for i in range(3):
            project = Project(
                id=str(uuid4()),
                tenant_key=tenant_key,
                name=f"Project {i + 1}",
                description=f"Project {i + 1}",
                product_id=test_product.id,
                mission="Test mission",
                status="active",
                created_at=datetime.now(timezone.utc),
            )
            db_session.add(project)
            await db_session.commit()
            await db_session.refresh(project)

            result = await close_project_and_update_memory(
                project_id=project.id,
                tenant_key=tenant_key,
                summary=f"Summary {i + 1}",
                key_outcomes=[f"Outcome {i + 1}"],
                decisions_made=[f"Decision {i + 1}"],
                db_manager=db_manager,
                session=db_session,
            )
            results.append(result)

            # Mark project as completed to allow next active project
            project.status = "completed"
            await db_session.commit()

        # Verify sequences are 1, 2, 3
        assert results[0]["sequence_number"] == 1
        assert results[1]["sequence_number"] == 2
        assert results[2]["sequence_number"] == 3

        # Verify in database
        stmt = (
            select(ProductMemoryEntry)
            .where(
                ProductMemoryEntry.product_id == test_product.id,
                ProductMemoryEntry.tenant_key == tenant_key,
            )
            .order_by(ProductMemoryEntry.sequence)
        )
        db_result = await db_session.execute(stmt)
        entries = db_result.scalars().all()

        assert len(entries) == 3
        assert entries[0].sequence == 1
        assert entries[1].sequence == 2
        assert entries[2].sequence == 3

    @pytest.mark.asyncio
    async def test_returns_entry_id(self, db_session, db_manager, tenant_key, test_project):
        """Return should include entry_id from table."""
        result = await close_project_and_update_memory(
            project_id=test_project.id,
            tenant_key=tenant_key,
            summary="Test summary",
            key_outcomes=["Test outcome"],
            decisions_made=["Test decision"],
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


# ========================================================================
# Test Cases - Computed Fields
# ========================================================================


class TestProjectCloseoutComputedFields:
    """Tests for computed fields (deliverables, metrics, priority, etc.)."""

    @pytest.mark.asyncio
    async def test_deliverables_extracted_from_outcomes(self, db_session, db_manager, tenant_key, test_project):
        """Deliverables should be extracted from key_outcomes."""
        result = await close_project_and_update_memory(
            project_id=test_project.id,
            tenant_key=tenant_key,
            summary="Test summary",
            key_outcomes=["Deliverable A", "Deliverable B", "Deliverable A"],  # Duplicate
            decisions_made=["Decision 1"],
            db_manager=db_manager,
            session=db_session,
        )

        stmt = select(ProductMemoryEntry).where(ProductMemoryEntry.id == result["entry_id"])
        db_result = await db_session.execute(stmt)
        entry = db_result.scalar_one()

        # Should deduplicate
        assert entry.deliverables == ["Deliverable A", "Deliverable B"]

    @pytest.mark.asyncio
    async def test_metrics_includes_test_coverage(self, db_session, db_manager, tenant_key, test_project):
        """Metrics should include test_coverage from project.meta_data."""
        result = await close_project_and_update_memory(
            project_id=test_project.id,
            tenant_key=tenant_key,
            summary="Test summary",
            key_outcomes=["Outcome 1"],
            decisions_made=["Decision 1"],
            db_manager=db_manager,
            session=db_session,
        )

        stmt = select(ProductMemoryEntry).where(ProductMemoryEntry.id == result["entry_id"])
        db_result = await db_session.execute(stmt)
        entry = db_result.scalar_one()

        assert entry.metrics["test_coverage"] == 85.5  # From fixture

    @pytest.mark.asyncio
    async def test_priority_derived_from_content(self, db_session, db_manager, tenant_key, test_project):
        """Priority should be derived from summary/outcomes."""
        # Critical priority (contains "incident")
        result = await close_project_and_update_memory(
            project_id=test_project.id,
            tenant_key=tenant_key,
            summary="Emergency incident response and rollback",
            key_outcomes=["Incident resolved"],
            decisions_made=["Decision 1"],
            db_manager=db_manager,
            session=db_session,
        )

        stmt = select(ProductMemoryEntry).where(ProductMemoryEntry.id == result["entry_id"])
        db_result = await db_session.execute(stmt)
        entry = db_result.scalar_one()

        assert entry.priority == 1  # CRITICAL

    @pytest.mark.asyncio
    async def test_significance_score_calculated(self, db_session, db_manager, tenant_key, test_project):
        """Significance score should be calculated based on outcomes/commits."""
        result = await close_project_and_update_memory(
            project_id=test_project.id,
            tenant_key=tenant_key,
            summary="Test summary",
            key_outcomes=["Outcome 1", "Outcome 2", "Outcome 3"],
            decisions_made=["Decision 1"],
            db_manager=db_manager,
            session=db_session,
        )

        stmt = select(ProductMemoryEntry).where(ProductMemoryEntry.id == result["entry_id"])
        db_result = await db_session.execute(stmt)
        entry = db_result.scalar_one()

        assert 0.0 <= entry.significance_score <= 1.0
        assert entry.significance_score > 0.0  # Should have some significance

    @pytest.mark.asyncio
    async def test_token_estimate_calculated(self, db_session, db_manager, tenant_key, test_project):
        """Token estimate should be calculated from content length."""
        result = await close_project_and_update_memory(
            project_id=test_project.id,
            tenant_key=tenant_key,
            summary="This is a longer summary with more content to estimate tokens",
            key_outcomes=["Long outcome 1", "Long outcome 2"],
            decisions_made=["Long decision 1"],
            db_manager=db_manager,
            session=db_session,
        )

        stmt = select(ProductMemoryEntry).where(ProductMemoryEntry.id == result["entry_id"])
        db_result = await db_session.execute(stmt)
        entry = db_result.scalar_one()

        assert entry.token_estimate > 0

    @pytest.mark.asyncio
    async def test_tags_extracted(self, db_session, db_manager, tenant_key, test_project):
        """Tags should be extracted from summary/outcomes/decisions."""
        result = await close_project_and_update_memory(
            project_id=test_project.id,
            tenant_key=tenant_key,
            summary="Authentication system with OAuth2 integration",
            key_outcomes=["OAuth2 complete", "User management API"],
            decisions_made=["Redis for sessions"],
            db_manager=db_manager,
            session=db_session,
        )

        stmt = select(ProductMemoryEntry).where(ProductMemoryEntry.id == result["entry_id"])
        db_result = await db_session.execute(stmt)
        entry = db_result.scalar_one()

        assert isinstance(entry.tags, list)
        assert len(entry.tags) > 0


# ========================================================================
# Test Cases - GitHub Integration
# ========================================================================


class TestProjectCloseoutGitHub:
    """Tests for GitHub commit fetching during closeout."""

    @pytest.mark.asyncio
    async def test_attempts_github_fetch_when_configured(
        self, db_session, db_manager, tenant_key, test_project_with_git, test_product_with_git
    ):
        """Should attempt to fetch GitHub commits when integration is enabled."""
        result = await close_project_and_update_memory(
            project_id=test_project_with_git.id,
            tenant_key=tenant_key,
            summary="Test summary",
            key_outcomes=["Outcome 1"],
            decisions_made=["Decision 1"],
            db_manager=db_manager,
            session=db_session,
        )

        # Should succeed even if GitHub fetch fails (graceful degradation)
        assert result["success"] is True
        assert "git_commits_count" in result
        # Will be 0 because no access token and API will fail
        assert result["git_commits_count"] == 0

    @pytest.mark.asyncio
    async def test_no_github_fetch_when_disabled(self, db_session, db_manager, tenant_key, test_project, test_product):
        """Should not attempt GitHub fetch when integration is disabled."""
        result = await close_project_and_update_memory(
            project_id=test_project.id,
            tenant_key=tenant_key,
            summary="Test summary",
            key_outcomes=["Outcome 1"],
            decisions_made=["Decision 1"],
            db_manager=db_manager,
            session=db_session,
        )

        assert result["success"] is True
        assert result["git_commits_count"] == 0


# ========================================================================
# Test Cases - Validation & Error Handling
# ========================================================================


class TestProjectCloseoutValidation:
    """Tests for input validation and error handling."""

    @pytest.mark.asyncio
    async def test_requires_project_id(self, db_manager, tenant_key):
        """Should return error if project_id is missing."""
        result = await close_project_and_update_memory(
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
    async def test_requires_summary(self, db_manager, tenant_key, test_project):
        """Should return error if summary is missing."""
        result = await close_project_and_update_memory(
            project_id=test_project.id,
            tenant_key=tenant_key,
            summary="",
            key_outcomes=["Test outcome"],
            decisions_made=["Test decision"],
            db_manager=db_manager,
        )

        assert result["success"] is False
        assert "summary is required" in result["error"]


# ========================================================================
# Test Cases - Tenant Isolation
# ========================================================================


class TestProjectCloseoutTenantIsolation:
    """Tests for multi-tenant isolation."""

    @pytest.mark.asyncio
    async def test_tenant_isolation(self, db_session, db_manager, tenant_key, other_tenant_key, test_project):
        """Should not allow closing another tenant's project."""
        result = await close_project_and_update_memory(
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
