"""
ProductMemoryEntry Model (Handover 0390a)

Normalized table for 360 memory entries.

REPLACES: Product.product_memory.sequential_history JSONB array (DEPRECATED in 0390).

This table is the SINGLE SOURCE OF TRUTH for 360 memory entries as of v3.3.
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

from .base import Base


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
        String(36),
        ForeignKey("products.id", ondelete="CASCADE"),
        nullable=False,
        comment="Parent product (CASCADE on delete)",
    )
    project_id = Column(
        String(36),
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
        comment="Entry type: project_closeout, project_completion, handover_closeout, session_handover",
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
        String(36),
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
