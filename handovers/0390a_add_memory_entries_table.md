# Handover 0390a: Add Product Memory Entries Table

**Part 1 of 4** in the 360 Memory JSONB Normalization series (0390)
**Date**: 2026-01-18
**Status**: Ready for Implementation
**Complexity**: Medium-High
**Estimated Duration**: 6-8 hours
**Branch**: `0390-360-memory-normalization`

---

## 1. EXECUTIVE SUMMARY

### Mission
Create the `product_memory_entries` table with SQLAlchemy model, repository with CRUD operations, and Alembic migration that backfills existing JSONB data.

### Context
Currently, 360 memory is stored in `Product.product_memory.sequential_history[]` as a JSONB array. This handover creates the foundation for normalizing this data into a proper relational table with:
- Foreign key constraints (CASCADE/SET NULL)
- Proper indexes for query performance
- Multi-tenant isolation via tenant_key column

### Why This Matters
- **Foundation**: All subsequent handovers (0390b-d) depend on this table
- **Data Integrity**: FK constraints prevent orphaned records
- **Performance**: Indexed table queries vs JSONB array iteration
- **Production-Grade**: Proper schema for commercialization

### Success Criteria
- [ ] Table `product_memory_entries` exists in database
- [ ] SQLAlchemy model properly mapped
- [ ] Repository CRUD operations work
- [ ] Migration backfills all existing JSONB entries
- [ ] COUNT(table entries) == COUNT(JSONB entries per product)
- [ ] All TDD tests pass (10+ tests)
- [ ] Existing tests still pass

---

## 2. TECHNICAL CONTEXT

### Current JSONB Structure (to migrate FROM)

```python
# Product.product_memory structure
{
    "sequential_history": [
        {
            "sequence": 1,
            "project_id": "uuid-string",
            "project_name": "Feature X",
            "type": "project_closeout",  # or "project_completion", "handover_closeout"
            "source": "closeout_v1",      # or "write_360_memory_v1"
            "timestamp": "2025-11-16T10:00:00Z",
            "summary": "Completed feature...",
            "key_outcomes": ["outcome1", "outcome2"],
            "decisions_made": ["decision1", "decision2"],
            "git_commits": [
                {"sha": "abc123", "message": "...", "author": "..."}
            ],
            # Extended fields (project_closeout only)
            "deliverables": ["file1.py", "file2.py"],
            "metrics": {"test_coverage": 85},
            "priority": 3,
            "significance_score": 0.7,
            "token_estimate": 500,
            "tags": ["feature", "api"],
            # Author fields (write_360_memory only)
            "author_job_id": "uuid-string",
            "author_name": "orchestrator-1",
            "author_type": "orchestrator",
            # Soft-delete fields (set when project deleted)
            "deleted_by_user": true,
            "user_deleted_at": "2025-11-17T15:00:00Z"
        }
    ],
    "git_integration": {
        "enabled": true,
        "repo_name": "GiljoAI-MCP",
        "repo_owner": "patrik-giljoai",
        "access_token": "ghp_xxx"
    }
}
```

### Target Table Schema

```sql
CREATE TABLE product_memory_entries (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    tenant_key VARCHAR(36) NOT NULL,
    product_id UUID NOT NULL REFERENCES products(id) ON DELETE CASCADE,
    project_id UUID REFERENCES projects(id) ON DELETE SET NULL,

    -- Core fields
    sequence INTEGER NOT NULL,
    entry_type VARCHAR(50) NOT NULL,
    source VARCHAR(50) NOT NULL,
    timestamp TIMESTAMP WITH TIME ZONE NOT NULL,

    -- Content
    project_name VARCHAR(255),
    summary TEXT,
    key_outcomes JSONB DEFAULT '[]',
    decisions_made JSONB DEFAULT '[]',
    git_commits JSONB DEFAULT '[]',

    -- Extended metadata
    deliverables JSONB DEFAULT '[]',
    metrics JSONB DEFAULT '{}',
    priority INTEGER DEFAULT 3,
    significance_score FLOAT DEFAULT 0.5,
    token_estimate INTEGER,
    tags JSONB DEFAULT '[]',

    -- Author tracking
    author_job_id UUID,
    author_name VARCHAR(255),
    author_type VARCHAR(50),

    -- Soft-delete tracking
    deleted_by_user BOOLEAN DEFAULT FALSE,
    user_deleted_at TIMESTAMP WITH TIME ZONE,

    -- Timestamps
    created_at TIMESTAMP WITH TIME ZONE DEFAULT NOW(),
    updated_at TIMESTAMP WITH TIME ZONE DEFAULT NOW(),

    UNIQUE (product_id, sequence)
);

-- Indexes
CREATE INDEX idx_pme_tenant_product ON product_memory_entries(tenant_key, product_id);
CREATE INDEX idx_pme_project ON product_memory_entries(project_id) WHERE project_id IS NOT NULL;
CREATE INDEX idx_pme_sequence ON product_memory_entries(product_id, sequence DESC);
CREATE INDEX idx_pme_type ON product_memory_entries(entry_type);
CREATE INDEX idx_pme_deleted ON product_memory_entries(deleted_by_user) WHERE deleted_by_user = TRUE;
```

---

## 3. SCOPE

### In Scope

1. **SQLAlchemy Model**
   - Create `ProductMemoryEntry` model class
   - Define all columns with types
   - Set up relationships to Product and Project

2. **Repository Class**
   - `create_entry()` - Insert new entry
   - `get_entries_by_product()` - List with pagination
   - `get_entry_by_id()` - Single entry lookup
   - `get_next_sequence()` - Atomic sequence generation
   - `mark_entries_deleted()` - Soft-delete by project_id
   - `update_entry()` - Modify existing entry

3. **Alembic Migration**
   - Create table with all columns
   - Create indexes
   - Backfill from JSONB data

4. **TDD Tests**
   - Write tests FIRST (RED phase)
   - Implement to pass tests (GREEN phase)
   - 10+ comprehensive tests

### Out of Scope (Future Handovers)
- Switching reads to table (0390b)
- Stopping JSONB writes (0390c)
- Deprecating JSONB column (0390d)

### Dependencies
- PostgreSQL database running
- Alembic configured
- `Product` and `Project` models exist

---

## 4. IMPLEMENTATION PLAN

### Phase 0: Safety Net (15 minutes)

**Goal**: Create branch and backup before ANY changes.

```bash
# 1. Create feature branch
git checkout -b 0390-360-memory-normalization

# 2. Push branch
git push -u origin 0390-360-memory-normalization

# 3. Database backup
PGPASSWORD=$DB_PASSWORD /f/PostgreSQL/bin/pg_dump.exe -U postgres giljo_mcp > backup_pre_0390.sql

# 4. Document baseline
pytest tests/ --tb=no -q | grep -E "passed|failed"
# Record count in closeout notes
```

**Validation**:
- [ ] Branch exists
- [ ] Backup file non-zero size
- [ ] Baseline test count recorded

---

### Phase 1: RED - Write Failing Tests (1 hour)

**Goal**: Define expected behavior through tests before implementation.

**Test File**: `tests/repositories/test_product_memory_repository.py`

```python
"""
TDD tests for ProductMemoryEntry repository (Handover 0390a).

Run with: pytest tests/repositories/test_product_memory_repository.py -v
"""

import pytest
from datetime import datetime
from uuid import uuid4
from sqlalchemy.ext.asyncio import AsyncSession
from src.giljo_mcp.models.product_memory_entry import ProductMemoryEntry
from src.giljo_mcp.repositories.product_memory_repository import ProductMemoryRepository


class TestProductMemoryRepository:
    """Tests for product memory entry CRUD operations."""

    @pytest.mark.asyncio
    async def test_model_exists(self, async_session: AsyncSession):
        """ProductMemoryEntry model should exist with all expected columns."""
        entry = ProductMemoryEntry(
            tenant_key="test_tenant",
            product_id=uuid4(),
            sequence=1,
            entry_type="project_completion",
            source="test_v1",
            timestamp=datetime.utcnow(),
        )
        assert hasattr(entry, 'id')
        assert hasattr(entry, 'tenant_key')
        assert hasattr(entry, 'product_id')
        assert hasattr(entry, 'project_id')
        assert hasattr(entry, 'sequence')
        assert hasattr(entry, 'entry_type')
        assert hasattr(entry, 'source')
        assert hasattr(entry, 'summary')
        assert hasattr(entry, 'key_outcomes')
        assert hasattr(entry, 'decisions_made')
        assert hasattr(entry, 'git_commits')
        assert hasattr(entry, 'deleted_by_user')

    @pytest.mark.asyncio
    async def test_create_entry(self, async_session: AsyncSession, test_product):
        """create_entry should insert a new entry and return it."""
        repo = ProductMemoryRepository()
        entry = await repo.create_entry(
            session=async_session,
            tenant_key="test_tenant",
            product_id=test_product.id,
            sequence=1,
            entry_type="project_completion",
            source="test_v1",
            timestamp=datetime.utcnow(),
            summary="Test summary",
            key_outcomes=["outcome1"],
            decisions_made=["decision1"],
        )
        assert entry.id is not None
        assert entry.sequence == 1
        assert entry.summary == "Test summary"

    @pytest.mark.asyncio
    async def test_get_entries_by_product(self, async_session: AsyncSession, test_product):
        """get_entries_by_product should return paginated entries."""
        repo = ProductMemoryRepository()
        # Create 3 entries
        for i in range(3):
            await repo.create_entry(
                session=async_session,
                tenant_key="test_tenant",
                product_id=test_product.id,
                sequence=i + 1,
                entry_type="project_completion",
                source="test_v1",
                timestamp=datetime.utcnow(),
            )

        entries = await repo.get_entries_by_product(
            session=async_session,
            product_id=test_product.id,
            tenant_key="test_tenant",
            limit=2,
        )
        assert len(entries) == 2

    @pytest.mark.asyncio
    async def test_get_next_sequence(self, async_session: AsyncSession, test_product):
        """get_next_sequence should return max(sequence) + 1."""
        repo = ProductMemoryRepository()
        # Initially should be 1
        seq1 = await repo.get_next_sequence(
            session=async_session,
            product_id=test_product.id,
        )
        assert seq1 == 1

        # After creating entry, should be 2
        await repo.create_entry(
            session=async_session,
            tenant_key="test_tenant",
            product_id=test_product.id,
            sequence=1,
            entry_type="test",
            source="test_v1",
            timestamp=datetime.utcnow(),
        )
        seq2 = await repo.get_next_sequence(
            session=async_session,
            product_id=test_product.id,
        )
        assert seq2 == 2

    @pytest.mark.asyncio
    async def test_mark_entries_deleted_by_project(self, async_session: AsyncSession, test_product, test_project):
        """mark_entries_deleted should soft-delete entries for a project."""
        repo = ProductMemoryRepository()
        entry = await repo.create_entry(
            session=async_session,
            tenant_key="test_tenant",
            product_id=test_product.id,
            project_id=test_project.id,
            sequence=1,
            entry_type="project_completion",
            source="test_v1",
            timestamp=datetime.utcnow(),
        )
        assert entry.deleted_by_user is False

        count = await repo.mark_entries_deleted(
            session=async_session,
            project_id=test_project.id,
            tenant_key="test_tenant",
        )
        assert count == 1

        await async_session.refresh(entry)
        assert entry.deleted_by_user is True
        assert entry.user_deleted_at is not None

    @pytest.mark.asyncio
    async def test_tenant_isolation(self, async_session: AsyncSession, test_product):
        """Queries should only return entries for the same tenant."""
        repo = ProductMemoryRepository()
        # Create entry in tenant_a
        await repo.create_entry(
            session=async_session,
            tenant_key="tenant_a",
            product_id=test_product.id,
            sequence=1,
            entry_type="test",
            source="test_v1",
            timestamp=datetime.utcnow(),
        )

        # Query with tenant_b should return nothing
        entries = await repo.get_entries_by_product(
            session=async_session,
            product_id=test_product.id,
            tenant_key="tenant_b",
        )
        assert len(entries) == 0

    @pytest.mark.asyncio
    async def test_sequence_unique_per_product(self, async_session: AsyncSession, test_product):
        """Duplicate sequence for same product should raise error."""
        repo = ProductMemoryRepository()
        await repo.create_entry(
            session=async_session,
            tenant_key="test_tenant",
            product_id=test_product.id,
            sequence=1,
            entry_type="test",
            source="test_v1",
            timestamp=datetime.utcnow(),
        )

        with pytest.raises(Exception):  # IntegrityError
            await repo.create_entry(
                session=async_session,
                tenant_key="test_tenant",
                product_id=test_product.id,
                sequence=1,  # Duplicate!
                entry_type="test",
                source="test_v1",
                timestamp=datetime.utcnow(),
            )

    @pytest.mark.asyncio
    async def test_cascade_delete_on_product(self, async_session: AsyncSession):
        """Entries should be deleted when product is deleted (CASCADE)."""
        # This test requires creating and deleting a product
        # Implementation depends on test fixtures
        pass

    @pytest.mark.asyncio
    async def test_set_null_on_project_delete(self, async_session: AsyncSession):
        """project_id should become NULL when project is deleted (SET NULL)."""
        # This test requires creating and deleting a project
        # Implementation depends on test fixtures
        pass

    @pytest.mark.asyncio
    async def test_entries_ordered_by_sequence_desc(self, async_session: AsyncSession, test_product):
        """get_entries_by_product should return entries in descending sequence order."""
        repo = ProductMemoryRepository()
        # Create entries out of order
        for seq in [3, 1, 2]:
            await repo.create_entry(
                session=async_session,
                tenant_key="test_tenant",
                product_id=test_product.id,
                sequence=seq,
                entry_type="test",
                source="test_v1",
                timestamp=datetime.utcnow(),
            )

        entries = await repo.get_entries_by_product(
            session=async_session,
            product_id=test_product.id,
            tenant_key="test_tenant",
        )
        sequences = [e.sequence for e in entries]
        assert sequences == [3, 2, 1]  # Descending
```

**Validation**:
- [ ] Run tests: `pytest tests/repositories/test_product_memory_repository.py -v`
- [ ] All tests should FAIL (model/repo don't exist yet)

---

### Phase 2: GREEN - Create Model (45 minutes)

**Goal**: Create SQLAlchemy model.

**File**: `src/giljo_mcp/models/product_memory_entry.py`

```python
"""
ProductMemoryEntry Model (Handover 0390a)

Normalized table for 360 memory entries, replacing Product.product_memory.sequential_history JSONB.
"""

from datetime import datetime
from typing import Optional, List, Dict, Any
from uuid import uuid4

from sqlalchemy import (
    Column,
    String,
    Text,
    Integer,
    Float,
    Boolean,
    DateTime,
    ForeignKey,
    UniqueConstraint,
    Index,
)
from sqlalchemy.dialects.postgresql import UUID, JSONB
from sqlalchemy.orm import relationship

from src.giljo_mcp.database import Base


class ProductMemoryEntry(Base):
    """
    360 Memory Entry - normalized from Product.product_memory.sequential_history.

    Each entry represents a project completion, closeout, or handover milestone
    that contributes to the product's cumulative memory.
    """

    __tablename__ = "product_memory_entries"

    # Primary key
    id = Column(
        UUID(as_uuid=True),
        primary_key=True,
        default=uuid4,
        comment="Unique entry identifier",
    )

    # Tenant isolation
    tenant_key = Column(
        String(36),
        nullable=False,
        index=True,
        comment="Tenant isolation key",
    )

    # Foreign keys
    product_id = Column(
        UUID(as_uuid=True),
        ForeignKey("products.id", ondelete="CASCADE"),
        nullable=False,
        comment="Parent product (CASCADE on delete)",
    )
    project_id = Column(
        UUID(as_uuid=True),
        ForeignKey("projects.id", ondelete="SET NULL"),
        nullable=True,
        comment="Source project (SET NULL on delete - preserves history)",
    )

    # Core fields
    sequence = Column(
        Integer,
        nullable=False,
        comment="Sequence number within product (1-based)",
    )
    entry_type = Column(
        String(50),
        nullable=False,
        comment="Entry type: project_closeout, project_completion, handover_closeout",
    )
    source = Column(
        String(50),
        nullable=False,
        comment="Source tool: closeout_v1, write_360_memory_v1, migration_backfill",
    )
    timestamp = Column(
        DateTime(timezone=True),
        nullable=False,
        comment="When the entry was created",
    )

    # Content fields
    project_name = Column(
        String(255),
        nullable=True,
        comment="Project name at time of entry",
    )
    summary = Column(
        Text,
        nullable=True,
        comment="2-3 paragraph summary of work accomplished",
    )
    key_outcomes = Column(
        JSONB,
        default=list,
        server_default="[]",
        comment="List of key achievements",
    )
    decisions_made = Column(
        JSONB,
        default=list,
        server_default="[]",
        comment="List of architectural/design decisions",
    )
    git_commits = Column(
        JSONB,
        default=list,
        server_default="[]",
        comment="List of git commit objects with sha, message, author",
    )

    # Extended metadata (project_closeout specific)
    deliverables = Column(
        JSONB,
        default=list,
        server_default="[]",
        comment="List of files/artifacts delivered",
    )
    metrics = Column(
        JSONB,
        default=dict,
        server_default="{}",
        comment="Metrics dict (test_coverage, etc.)",
    )
    priority = Column(
        Integer,
        default=3,
        server_default="3",
        comment="Priority level 1-5",
    )
    significance_score = Column(
        Float,
        default=0.5,
        server_default="0.5",
        comment="Significance score 0.0-1.0",
    )
    token_estimate = Column(
        Integer,
        nullable=True,
        comment="Estimated tokens for this entry",
    )
    tags = Column(
        JSONB,
        default=list,
        server_default="[]",
        comment="List of tags for categorization",
    )

    # Author tracking (write_360_memory specific)
    author_job_id = Column(
        UUID(as_uuid=True),
        nullable=True,
        comment="Job ID of agent that wrote this entry",
    )
    author_name = Column(
        String(255),
        nullable=True,
        comment="Name of agent that wrote this entry",
    )
    author_type = Column(
        String(50),
        nullable=True,
        comment="Type of agent (orchestrator, implementer, etc.)",
    )

    # Soft-delete tracking
    deleted_by_user = Column(
        Boolean,
        default=False,
        server_default="false",
        comment="True if source project was deleted by user",
    )
    user_deleted_at = Column(
        DateTime(timezone=True),
        nullable=True,
        comment="When the source project was deleted",
    )

    # Timestamps
    created_at = Column(
        DateTime(timezone=True),
        default=datetime.utcnow,
        nullable=False,
        comment="When this row was created",
    )
    updated_at = Column(
        DateTime(timezone=True),
        default=datetime.utcnow,
        onupdate=datetime.utcnow,
        nullable=False,
        comment="When this row was last updated",
    )

    # Relationships
    product = relationship("Product", back_populates="memory_entries")
    project = relationship("Project", back_populates="memory_entries")

    # Constraints
    __table_args__ = (
        UniqueConstraint("product_id", "sequence", name="uq_product_sequence"),
        Index("idx_pme_tenant_product", "tenant_key", "product_id"),
        Index("idx_pme_project", "project_id", postgresql_where="project_id IS NOT NULL"),
        Index("idx_pme_sequence", "product_id", "sequence"),
        Index("idx_pme_type", "entry_type"),
        Index("idx_pme_deleted", "deleted_by_user", postgresql_where="deleted_by_user = true"),
    )

    def __repr__(self) -> str:
        return f"<ProductMemoryEntry(id={self.id}, product_id={self.product_id}, sequence={self.sequence}, type={self.entry_type})>"

    def to_dict(self) -> Dict[str, Any]:
        """Convert to dictionary (matching JSONB entry format for compatibility)."""
        return {
            "id": str(self.id),
            "sequence": self.sequence,
            "project_id": str(self.project_id) if self.project_id else None,
            "project_name": self.project_name,
            "type": self.entry_type,
            "source": self.source,
            "timestamp": self.timestamp.isoformat() if self.timestamp else None,
            "summary": self.summary,
            "key_outcomes": self.key_outcomes or [],
            "decisions_made": self.decisions_made or [],
            "git_commits": self.git_commits or [],
            "deliverables": self.deliverables or [],
            "metrics": self.metrics or {},
            "priority": self.priority,
            "significance_score": self.significance_score,
            "token_estimate": self.token_estimate,
            "tags": self.tags or [],
            "author_job_id": str(self.author_job_id) if self.author_job_id else None,
            "author_name": self.author_name,
            "author_type": self.author_type,
            "deleted_by_user": self.deleted_by_user,
            "user_deleted_at": self.user_deleted_at.isoformat() if self.user_deleted_at else None,
        }
```

**Update**: `src/giljo_mcp/models/__init__.py`
```python
from src.giljo_mcp.models.product_memory_entry import ProductMemoryEntry
```

**Update**: `src/giljo_mcp/models/products.py` (add relationship)
```python
# Add to Product class
memory_entries = relationship("ProductMemoryEntry", back_populates="product", cascade="all, delete-orphan")
```

**Update**: `src/giljo_mcp/models/projects.py` (add relationship)
```python
# Add to Project class
memory_entries = relationship("ProductMemoryEntry", back_populates="project")
```

**Validation**:
- [ ] No import errors
- [ ] `test_model_exists` passes

---

### Phase 3: GREEN - Create Repository (1.5 hours)

**Goal**: Implement repository with all CRUD operations.

**File**: `src/giljo_mcp/repositories/product_memory_repository.py`

```python
"""
ProductMemoryEntry Repository (Handover 0390a)

CRUD operations for 360 memory entries with tenant isolation.
"""

import logging
from datetime import datetime
from typing import List, Optional, Dict, Any
from uuid import UUID

from sqlalchemy import select, update, func, and_
from sqlalchemy.ext.asyncio import AsyncSession

from src.giljo_mcp.models.product_memory_entry import ProductMemoryEntry


logger = logging.getLogger(__name__)


class ProductMemoryRepository:
    """Repository for ProductMemoryEntry CRUD operations."""

    async def create_entry(
        self,
        session: AsyncSession,
        tenant_key: str,
        product_id: UUID,
        sequence: int,
        entry_type: str,
        source: str,
        timestamp: datetime,
        project_id: Optional[UUID] = None,
        project_name: Optional[str] = None,
        summary: Optional[str] = None,
        key_outcomes: Optional[List[str]] = None,
        decisions_made: Optional[List[str]] = None,
        git_commits: Optional[List[Dict[str, Any]]] = None,
        deliverables: Optional[List[str]] = None,
        metrics: Optional[Dict[str, Any]] = None,
        priority: int = 3,
        significance_score: float = 0.5,
        token_estimate: Optional[int] = None,
        tags: Optional[List[str]] = None,
        author_job_id: Optional[UUID] = None,
        author_name: Optional[str] = None,
        author_type: Optional[str] = None,
    ) -> ProductMemoryEntry:
        """
        Create a new 360 memory entry.

        Args:
            session: Database session
            tenant_key: Tenant isolation key
            product_id: Parent product ID
            sequence: Sequence number (must be unique per product)
            entry_type: Entry type (project_closeout, project_completion, handover_closeout)
            source: Source tool identifier
            timestamp: When the entry was created
            project_id: Source project ID (optional)
            ... (other fields)

        Returns:
            Created ProductMemoryEntry instance

        Raises:
            IntegrityError: If sequence is duplicate for product
        """
        entry = ProductMemoryEntry(
            tenant_key=tenant_key,
            product_id=product_id,
            project_id=project_id,
            sequence=sequence,
            entry_type=entry_type,
            source=source,
            timestamp=timestamp,
            project_name=project_name,
            summary=summary,
            key_outcomes=key_outcomes or [],
            decisions_made=decisions_made or [],
            git_commits=git_commits or [],
            deliverables=deliverables or [],
            metrics=metrics or {},
            priority=priority,
            significance_score=significance_score,
            token_estimate=token_estimate,
            tags=tags or [],
            author_job_id=author_job_id,
            author_name=author_name,
            author_type=author_type,
        )
        session.add(entry)
        await session.flush()
        await session.refresh(entry)

        logger.info(
            f"Created memory entry {entry.id} for product {product_id} (seq={sequence})",
            extra={"tenant_key": tenant_key, "entry_type": entry_type},
        )
        return entry

    async def get_entries_by_product(
        self,
        session: AsyncSession,
        product_id: UUID,
        tenant_key: str,
        limit: Optional[int] = None,
        offset: int = 0,
        include_deleted: bool = False,
    ) -> List[ProductMemoryEntry]:
        """
        Get 360 memory entries for a product with pagination.

        Args:
            session: Database session
            product_id: Product ID to query
            tenant_key: Tenant isolation key
            limit: Maximum entries to return (None = all)
            offset: Number of entries to skip
            include_deleted: Include soft-deleted entries

        Returns:
            List of ProductMemoryEntry in descending sequence order
        """
        stmt = (
            select(ProductMemoryEntry)
            .where(
                ProductMemoryEntry.product_id == product_id,
                ProductMemoryEntry.tenant_key == tenant_key,
            )
            .order_by(ProductMemoryEntry.sequence.desc())
            .offset(offset)
        )

        if not include_deleted:
            stmt = stmt.where(ProductMemoryEntry.deleted_by_user == False)

        if limit:
            stmt = stmt.limit(limit)

        result = await session.execute(stmt)
        return list(result.scalars().all())

    async def get_entry_by_id(
        self,
        session: AsyncSession,
        entry_id: UUID,
        tenant_key: str,
    ) -> Optional[ProductMemoryEntry]:
        """
        Get a single entry by ID with tenant isolation.

        Args:
            session: Database session
            entry_id: Entry UUID
            tenant_key: Tenant isolation key

        Returns:
            ProductMemoryEntry or None if not found
        """
        stmt = select(ProductMemoryEntry).where(
            ProductMemoryEntry.id == entry_id,
            ProductMemoryEntry.tenant_key == tenant_key,
        )
        result = await session.execute(stmt)
        return result.scalar_one_or_none()

    async def get_next_sequence(
        self,
        session: AsyncSession,
        product_id: UUID,
    ) -> int:
        """
        Get the next available sequence number for a product.

        Uses SELECT MAX(sequence) + 1, returns 1 if no entries exist.

        Args:
            session: Database session
            product_id: Product ID

        Returns:
            Next sequence number (1-based)
        """
        stmt = select(func.max(ProductMemoryEntry.sequence)).where(
            ProductMemoryEntry.product_id == product_id,
        )
        result = await session.execute(stmt)
        max_seq = result.scalar_one_or_none()
        return (max_seq or 0) + 1

    async def mark_entries_deleted(
        self,
        session: AsyncSession,
        project_id: UUID,
        tenant_key: str,
    ) -> int:
        """
        Soft-delete all entries associated with a project.

        Called when a project is deleted - marks entries as deleted
        but preserves them for historical reference.

        Args:
            session: Database session
            project_id: Project ID to mark entries for
            tenant_key: Tenant isolation key

        Returns:
            Number of entries marked as deleted
        """
        stmt = (
            update(ProductMemoryEntry)
            .where(
                ProductMemoryEntry.project_id == project_id,
                ProductMemoryEntry.tenant_key == tenant_key,
            )
            .values(
                deleted_by_user=True,
                user_deleted_at=datetime.utcnow(),
                updated_at=datetime.utcnow(),
            )
        )
        result = await session.execute(stmt)
        await session.flush()

        count = result.rowcount
        if count > 0:
            logger.info(
                f"Marked {count} memory entries as deleted for project {project_id}",
                extra={"tenant_key": tenant_key},
            )
        return count

    async def update_entry(
        self,
        session: AsyncSession,
        entry_id: UUID,
        tenant_key: str,
        **kwargs,
    ) -> Optional[ProductMemoryEntry]:
        """
        Update an existing entry.

        Args:
            session: Database session
            entry_id: Entry UUID
            tenant_key: Tenant isolation key
            **kwargs: Fields to update

        Returns:
            Updated entry or None if not found
        """
        entry = await self.get_entry_by_id(session, entry_id, tenant_key)
        if not entry:
            return None

        for key, value in kwargs.items():
            if hasattr(entry, key):
                setattr(entry, key, value)

        entry.updated_at = datetime.utcnow()
        await session.flush()
        await session.refresh(entry)
        return entry

    async def get_entries_for_context(
        self,
        session: AsyncSession,
        product_id: UUID,
        tenant_key: str,
        limit: int = 5,
    ) -> List[Dict[str, Any]]:
        """
        Get entries formatted for context (mission planning).

        Returns lightweight dicts suitable for agent context injection.

        Args:
            session: Database session
            product_id: Product ID
            tenant_key: Tenant isolation key
            limit: Max entries to return

        Returns:
            List of entry dicts
        """
        entries = await self.get_entries_by_product(
            session=session,
            product_id=product_id,
            tenant_key=tenant_key,
            limit=limit,
            include_deleted=False,
        )
        return [entry.to_dict() for entry in entries]

    async def get_git_history(
        self,
        session: AsyncSession,
        product_id: UUID,
        tenant_key: str,
        limit: int = 50,
    ) -> List[Dict[str, Any]]:
        """
        Get aggregated git commits from all entries.

        Args:
            session: Database session
            product_id: Product ID
            tenant_key: Tenant isolation key
            limit: Max commits to return

        Returns:
            List of git commit dicts
        """
        entries = await self.get_entries_by_product(
            session=session,
            product_id=product_id,
            tenant_key=tenant_key,
            include_deleted=False,
        )

        all_commits = []
        for entry in entries:
            if entry.git_commits:
                all_commits.extend(entry.git_commits)

        # Sort by date descending, limit
        all_commits.sort(key=lambda c: c.get("date", ""), reverse=True)
        return all_commits[:limit]
```

**Validation**:
- [ ] Run tests: `pytest tests/repositories/test_product_memory_repository.py -v`
- [ ] More tests should pass (7-8 out of 10)

---

### Phase 4: Create Migration (1 hour)

**Goal**: Create Alembic migration with backfill logic.

**File**: `alembic/versions/0390a_add_product_memory_entries.py`

```python
"""Add product_memory_entries table (Handover 0390a)

Revision ID: 0390a_memory_entries
Revises: [REPLACE_WITH_ACTUAL_PREVIOUS_REVISION]
Create Date: 2026-01-18
"""

from alembic import op
import sqlalchemy as sa
from sqlalchemy.dialects import postgresql

# revision identifiers
revision = '0390a_memory_entries'
down_revision = None  # UPDATE THIS!
branch_labels = None
depends_on = None


def upgrade():
    # Create table
    op.create_table(
        'product_memory_entries',
        sa.Column('id', postgresql.UUID(as_uuid=True), primary_key=True, server_default=sa.text('gen_random_uuid()')),
        sa.Column('tenant_key', sa.String(36), nullable=False),
        sa.Column('product_id', postgresql.UUID(as_uuid=True), sa.ForeignKey('products.id', ondelete='CASCADE'), nullable=False),
        sa.Column('project_id', postgresql.UUID(as_uuid=True), sa.ForeignKey('projects.id', ondelete='SET NULL'), nullable=True),

        sa.Column('sequence', sa.Integer(), nullable=False),
        sa.Column('entry_type', sa.String(50), nullable=False),
        sa.Column('source', sa.String(50), nullable=False),
        sa.Column('timestamp', sa.DateTime(timezone=True), nullable=False),

        sa.Column('project_name', sa.String(255), nullable=True),
        sa.Column('summary', sa.Text(), nullable=True),
        sa.Column('key_outcomes', postgresql.JSONB(), server_default='[]'),
        sa.Column('decisions_made', postgresql.JSONB(), server_default='[]'),
        sa.Column('git_commits', postgresql.JSONB(), server_default='[]'),

        sa.Column('deliverables', postgresql.JSONB(), server_default='[]'),
        sa.Column('metrics', postgresql.JSONB(), server_default='{}'),
        sa.Column('priority', sa.Integer(), server_default='3'),
        sa.Column('significance_score', sa.Float(), server_default='0.5'),
        sa.Column('token_estimate', sa.Integer(), nullable=True),
        sa.Column('tags', postgresql.JSONB(), server_default='[]'),

        sa.Column('author_job_id', postgresql.UUID(as_uuid=True), nullable=True),
        sa.Column('author_name', sa.String(255), nullable=True),
        sa.Column('author_type', sa.String(50), nullable=True),

        sa.Column('deleted_by_user', sa.Boolean(), server_default='false'),
        sa.Column('user_deleted_at', sa.DateTime(timezone=True), nullable=True),

        sa.Column('created_at', sa.DateTime(timezone=True), server_default=sa.text('NOW()')),
        sa.Column('updated_at', sa.DateTime(timezone=True), server_default=sa.text('NOW()')),

        sa.UniqueConstraint('product_id', 'sequence', name='uq_product_sequence'),
    )

    # Create indexes
    op.create_index('idx_pme_tenant_product', 'product_memory_entries', ['tenant_key', 'product_id'])
    op.create_index('idx_pme_project', 'product_memory_entries', ['project_id'], postgresql_where=sa.text('project_id IS NOT NULL'))
    op.create_index('idx_pme_sequence', 'product_memory_entries', ['product_id', 'sequence'])
    op.create_index('idx_pme_type', 'product_memory_entries', ['entry_type'])
    op.create_index('idx_pme_deleted', 'product_memory_entries', ['deleted_by_user'], postgresql_where=sa.text('deleted_by_user = true'))

    # Backfill from JSONB
    op.execute("""
        INSERT INTO product_memory_entries (
            tenant_key, product_id, project_id, sequence, entry_type, source, timestamp,
            project_name, summary, key_outcomes, decisions_made, git_commits,
            deliverables, metrics, priority, significance_score, token_estimate, tags,
            author_job_id, author_name, author_type,
            deleted_by_user, user_deleted_at, created_at, updated_at
        )
        SELECT
            p.tenant_key,
            p.id AS product_id,
            CASE
                WHEN entry->>'project_id' IS NOT NULL AND entry->>'project_id' != 'null'
                THEN (entry->>'project_id')::uuid
                ELSE NULL
            END AS project_id,
            (entry->>'sequence')::integer AS sequence,
            COALESCE(entry->>'type', 'project_completion') AS entry_type,
            COALESCE(entry->>'source', 'migration_backfill') AS source,
            COALESCE(
                (entry->>'timestamp')::timestamp with time zone,
                NOW()
            ) AS timestamp,
            entry->>'project_name' AS project_name,
            entry->>'summary' AS summary,
            COALESCE(entry->'key_outcomes', '[]'::jsonb) AS key_outcomes,
            COALESCE(entry->'decisions_made', '[]'::jsonb) AS decisions_made,
            COALESCE(entry->'git_commits', '[]'::jsonb) AS git_commits,
            COALESCE(entry->'deliverables', '[]'::jsonb) AS deliverables,
            COALESCE(entry->'metrics', '{}'::jsonb) AS metrics,
            COALESCE((entry->>'priority')::integer, 3) AS priority,
            COALESCE((entry->>'significance_score')::float, 0.5) AS significance_score,
            (entry->>'token_estimate')::integer AS token_estimate,
            COALESCE(entry->'tags', '[]'::jsonb) AS tags,
            CASE
                WHEN entry->>'author_job_id' IS NOT NULL AND entry->>'author_job_id' != 'null'
                THEN (entry->>'author_job_id')::uuid
                ELSE NULL
            END AS author_job_id,
            entry->>'author_name' AS author_name,
            entry->>'author_type' AS author_type,
            COALESCE((entry->>'deleted_by_user')::boolean, false) AS deleted_by_user,
            (entry->>'user_deleted_at')::timestamp with time zone AS user_deleted_at,
            NOW() AS created_at,
            NOW() AS updated_at
        FROM products p,
        LATERAL jsonb_array_elements(
            COALESCE(p.product_memory->'sequential_history', '[]'::jsonb)
        ) AS entry
        WHERE p.product_memory IS NOT NULL
          AND jsonb_array_length(COALESCE(p.product_memory->'sequential_history', '[]'::jsonb)) > 0
    """)


def downgrade():
    op.drop_table('product_memory_entries')
```

**Run Migration**:
```bash
# Get current head revision
alembic heads

# Update down_revision in migration file

# Run migration
alembic upgrade head
```

**Validation**:
- [ ] Migration runs without errors
- [ ] Table exists: `\d product_memory_entries`
- [ ] Backfill populated: `SELECT COUNT(*) FROM product_memory_entries;`

---

### Phase 5: Regression Testing (30 minutes)

**Goal**: Ensure no existing functionality broken.

```bash
# Full test suite
pytest tests/ -v --tb=short

# Coverage
pytest tests/ --cov=src/giljo_mcp --cov-report=term
```

---

## 5. TESTING REQUIREMENTS

### Unit Tests (Required)
- `tests/repositories/test_product_memory_repository.py` (10+ tests)

### Integration Tests (Optional)
- Backfill accuracy verification
- Cascade behavior tests

### Coverage Target
- >90% for new code

---

## 6. ROLLBACK PLAN

### Rollback Triggers
- Migration fails
- More than 10 existing tests break
- Data corruption detected

### Rollback Steps
```bash
# Downgrade migration
alembic downgrade -1

# Revert code
git checkout master -- src/giljo_mcp/models/product_memory_entry.py
git checkout master -- src/giljo_mcp/repositories/product_memory_repository.py
```

---

## 7. FILES INDEX

### Files to CREATE
| File | Purpose |
|------|---------|
| `src/giljo_mcp/models/product_memory_entry.py` | SQLAlchemy model |
| `src/giljo_mcp/repositories/product_memory_repository.py` | CRUD repository |
| `alembic/versions/0390a_add_product_memory_entries.py` | Migration |
| `tests/repositories/test_product_memory_repository.py` | TDD tests |

### Files to MODIFY
| File | Changes |
|------|---------|
| `src/giljo_mcp/models/__init__.py` | Export new model |
| `src/giljo_mcp/models/products.py` | Add relationship |
| `src/giljo_mcp/models/projects.py` | Add relationship |

---

## 8. SUCCESS CRITERIA

### Functional
- [ ] Table exists with correct schema
- [ ] All columns match specification
- [ ] Indexes created properly
- [ ] Backfill migrates all JSONB entries
- [ ] Repository CRUD works correctly

### Quality
- [ ] All 10+ TDD tests pass
- [ ] No existing test regressions
- [ ] No linting errors

### Documentation
- [ ] Closeout notes completed
- [ ] Ready for 0390b handover

---

## CLOSEOUT NOTES

**Status**: [NOT STARTED]

*To be filled upon completion*

---

**Document Version**: 1.0
**Last Updated**: 2026-01-18
