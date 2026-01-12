"""
Unit tests for Handover 0017 agent models.

Tests MCPContextIndex, MCPContextSummary, and MCPAgentJob models
with focus on tenant isolation and data integrity.
"""

from datetime import datetime

import pytest
from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker

from src.giljo_mcp.models import Base, MCPContextIndex, MCPContextSummary, Product
from src.giljo_mcp.models.agent_identity import AgentJob, AgentExecution


class TestMCPContextIndex:
    """Test MCPContextIndex model functionality."""

    @pytest.fixture
    def db_session(self):
        """Create in-memory SQLite database for testing."""
        engine = create_engine("sqlite:///:memory:")
        Base.metadata.create_all(engine)
        Session = sessionmaker(bind=engine)
        session = Session()
        yield session
        session.close()

    @pytest.fixture
    def sample_product(self, db_session):
        """Create a sample product for testing."""
        product = Product(
            id="test-product-id",
            tenant_key="test-tenant",
            name="Test Product",
            description="Test product for context indexing",
        )
        db_session.add(product)
        db_session.commit()
        return product

    def test_mcp_context_index_creation(self, db_session, sample_product):
        """Test creating context index with all fields."""
        context_index = MCPContextIndex(
            tenant_key="test-tenant",
            product_id=sample_product.id,
            content="This is test content for the vision document.",
            keywords=["test", "vision", "document"],
            token_count=150,
            chunk_order=1,
        )

        db_session.add(context_index)
        db_session.commit()

        # Verify creation
        assert context_index.id is not None
        assert context_index.chunk_id is not None
        assert context_index.tenant_key == "test-tenant"
        assert context_index.product_id == sample_product.id
        assert context_index.content == "This is test content for the vision document."
        assert context_index.keywords == ["test", "vision", "document"]
        assert context_index.token_count == 150
        assert context_index.chunk_order == 1
        assert context_index.summary is None  # Default for Phase 1
        assert context_index.created_at is not None

    def test_mcp_context_index_with_summary(self, db_session, sample_product):
        """Test creating context index with LLM summary."""
        context_index = MCPContextIndex(
            tenant_key="test-tenant",
            product_id=sample_product.id,
            content="Detailed technical specifications for the system architecture.",
            keywords=["architecture", "technical", "specifications"],
            token_count=200,
            chunk_order=2,
            summary="Technical specs for system architecture",
        )

        db_session.add(context_index)
        db_session.commit()

        assert context_index.summary == "Technical specs for system architecture"
        assert context_index.chunk_order == 2

    def test_mcp_context_index_tenant_isolation(self, db_session, sample_product):
        """Test tenant isolation in context index."""
        # Create context for tenant A
        context_a = MCPContextIndex(
            tenant_key="tenant-a",
            product_id=sample_product.id,
            content="Content for tenant A",
            keywords=["tenant-a"],
            token_count=100,
            chunk_order=1,
        )

        # Create context for tenant B
        context_b = MCPContextIndex(
            tenant_key="tenant-b",
            product_id=sample_product.id,
            content="Content for tenant B",
            keywords=["tenant-b"],
            token_count=120,
            chunk_order=1,
        )

        db_session.add_all([context_a, context_b])
        db_session.commit()

        # Query for tenant A only
        tenant_a_contexts = db_session.query(MCPContextIndex).filter(MCPContextIndex.tenant_key == "tenant-a").all()

        assert len(tenant_a_contexts) == 1
        assert tenant_a_contexts[0].content == "Content for tenant A"

        # Query for tenant B only
        tenant_b_contexts = db_session.query(MCPContextIndex).filter(MCPContextIndex.tenant_key == "tenant-b").all()

        assert len(tenant_b_contexts) == 1
        assert tenant_b_contexts[0].content == "Content for tenant B"

    def test_mcp_context_index_product_relationship(self, db_session, sample_product):
        """Test relationship with Product model."""
        context_index = MCPContextIndex(
            tenant_key="test-tenant",
            product_id=sample_product.id,
            content="Test content",
            keywords=["test"],
            token_count=50,
            chunk_order=1,
        )

        db_session.add(context_index)
        db_session.commit()

        # Test relationship
        assert context_index.product == sample_product
        assert context_index in sample_product.context_chunks


class TestMCPContextSummary:
    """Test MCPContextSummary model functionality."""

    @pytest.fixture
    def db_session(self):
        """Create in-memory SQLite database for testing."""
        engine = create_engine("sqlite:///:memory:")
        Base.metadata.create_all(engine)
        Session = sessionmaker(bind=engine)
        session = Session()
        yield session
        session.close()

    @pytest.fixture
    def sample_product(self, db_session):
        """Create a sample product for testing."""
        product = Product(
            id="test-product-id",
            tenant_key="test-tenant",
            name="Test Product",
            description="Test product for context summarization",
        )
        db_session.add(product)
        db_session.commit()
        return product

    def test_mcp_context_summary_creation(self, db_session, sample_product):
        """Test creating context summary with all fields."""
        context_summary = MCPContextSummary(
            tenant_key="test-tenant",
            product_id=sample_product.id,
            full_content="This is the complete original content that needs summarization for context prioritization.",
            condensed_mission="Create summarized version of content",
            full_token_count=1000,
            condensed_token_count=300,
            reduction_percent=70.0,
        )

        db_session.add(context_summary)
        db_session.commit()

        # Verify creation
        assert context_summary.id is not None
        assert context_summary.context_id is not None
        assert context_summary.tenant_key == "test-tenant"
        assert context_summary.product_id == sample_product.id
        assert context_summary.full_content.startswith("This is the complete")
        assert context_summary.condensed_mission == "Create summarized version of content"
        assert context_summary.full_token_count == 1000
        assert context_summary.condensed_token_count == 300
        assert context_summary.reduction_percent == 70.0
        assert context_summary.created_at is not None

    def test_mcp_context_summary_reduction_calculation(self, db_session, sample_product):
        """Test context prioritization percentage calculation."""
        # Test various reduction scenarios
        test_cases = [
            (1000, 300, 70.0),  # 70% reduction
            (500, 250, 50.0),  # 50% reduction
            (800, 200, 75.0),  # 75% reduction
            (1000, 1000, 0.0),  # No reduction
        ]

        for full_tokens, condensed_tokens, expected_percent in test_cases:
            reduction_percent = ((full_tokens - condensed_tokens) / full_tokens) * 100 if full_tokens > 0 else 0.0

            context_summary = MCPContextSummary(
                tenant_key="test-tenant",
                product_id=sample_product.id,
                full_content=f"Content with {full_tokens} tokens",
                condensed_mission=f"Condensed to {condensed_tokens} tokens",
                full_token_count=full_tokens,
                condensed_token_count=condensed_tokens,
                reduction_percent=reduction_percent,
            )

            assert context_summary.reduction_percent == expected_percent

    def test_mcp_context_summary_tenant_isolation(self, db_session, sample_product):
        """Test tenant isolation in context summary."""
        # Create summary for tenant A
        summary_a = MCPContextSummary(
            tenant_key="tenant-a",
            product_id=sample_product.id,
            full_content="Full content for tenant A",
            condensed_mission="Mission for tenant A",
            full_token_count=500,
            condensed_token_count=150,
            reduction_percent=70.0,
        )

        # Create summary for tenant B
        summary_b = MCPContextSummary(
            tenant_key="tenant-b",
            product_id=sample_product.id,
            full_content="Full content for tenant B",
            condensed_mission="Mission for tenant B",
            full_token_count=600,
            condensed_token_count=180,
            reduction_percent=70.0,
        )

        db_session.add_all([summary_a, summary_b])
        db_session.commit()

        # Query for tenant A only
        tenant_a_summaries = (
            db_session.query(MCPContextSummary).filter(MCPContextSummary.tenant_key == "tenant-a").all()
        )

        assert len(tenant_a_summaries) == 1
        assert tenant_a_summaries[0].condensed_mission == "Mission for tenant A"

        # Query for tenant B only
        tenant_b_summaries = (
            db_session.query(MCPContextSummary).filter(MCPContextSummary.tenant_key == "tenant-b").all()
        )

        assert len(tenant_b_summaries) == 1
        assert tenant_b_summaries[0].condensed_mission == "Mission for tenant B"


class TestMCPAgentJob:
    """Test MCPAgentJob model functionality."""

    @pytest.fixture
    def db_session(self):
        """Create in-memory SQLite database for testing."""
        engine = create_engine("sqlite:///:memory:")
        Base.metadata.create_all(engine)
        Session = sessionmaker(bind=engine)
        session = Session()
        yield session
        session.close()

    def test_mcp_agent_job_creation(self, db_session):
        """Test creating agent job with all fields."""
        agent_job = AgentExecution(
            tenant_key="test-tenant",
            agent_display_name="orchestrator",
            mission="Coordinate development project tasks",
            status="waiting",
            spawned_by="parent-agent-id",
            context_chunks=["chunk-1", "chunk-2", "chunk-3"],
            messages=[
                {"type": "info", "content": "Job created", "timestamp": "2025-01-01T00:00:00Z"},
                {"type": "update", "content": "Job assigned", "timestamp": "2025-01-01T00:01:00Z"},
            ],
        )

        db_session.add(agent_job)
        db_session.commit()

        # Verify creation
        assert agent_job.id is not None
        assert agent_job.job_id is not None
        assert agent_job.tenant_key == "test-tenant"
        assert agent_job.agent_display_name == "orchestrator"
        assert agent_job.mission == "Coordinate development project tasks"
        assert agent_job.status == "pending"
        assert agent_job.spawned_by == "parent-agent-id"
        assert agent_job.context_chunks == ["chunk-1", "chunk-2", "chunk-3"]
        assert len(agent_job.messages) == 2
        assert agent_job.messages[0]["type"] == "info"
        assert agent_job.acknowledged is False  # Default value
        assert agent_job.created_at is not None

    def test_mcp_agent_job_status_workflow(self, db_session):
        """Test job status transitions."""
        agent_job = AgentExecution(
            tenant_key="test-tenant", agent_display_name="analyzer", mission="Analyze codebase structure", status="waiting"
        )

        db_session.add(agent_job)
        db_session.commit()

        # Test status transitions
        assert agent_job.status == "pending"
        assert agent_job.started_at is None
        assert agent_job.completed_at is None

        # Move to active
        agent_job.status = "active"
        agent_job.started_at = datetime.utcnow()
        db_session.commit()

        assert agent_job.status == "active"
        assert agent_job.started_at is not None
        assert agent_job.completed_at is None

        # Move to completed
        agent_job.status = "completed"
        agent_job.completed_at = datetime.utcnow()
        db_session.commit()

        assert agent_job.status == "completed"
        assert agent_job.started_at is not None
        assert agent_job.completed_at is not None

    def test_mcp_agent_job_tenant_isolation(self, db_session):
        """Test tenant isolation in agent jobs."""
        # Create job for tenant A
        job_a = AgentExecution(
            tenant_key="tenant-a", agent_display_name="implementer", mission="Implement feature for tenant A", status="waiting"
        )

        # Create job for tenant B
        job_b = AgentExecution(
            tenant_key="tenant-b", agent_display_name="tester", mission="Test feature for tenant B", status="active"
        )

        db_session.add_all([job_a, job_b])
        db_session.commit()

        # Query for tenant A only
        tenant_a_jobs = db_session.query(AgentExecution).filter(AgentExecution.tenant_key == "tenant-a").all()

        assert len(tenant_a_jobs) == 1
        assert tenant_a_jobs[0].agent_display_name == "implementer"
        assert tenant_a_jobs[0].mission.endswith("tenant A")

        # Query for tenant B only
        tenant_b_jobs = db_session.query(AgentExecution).filter(AgentExecution.tenant_key == "tenant-b").all()

        assert len(tenant_b_jobs) == 1
        assert tenant_b_jobs[0].agent_display_name == "tester"
        assert tenant_b_jobs[0].mission.endswith("tenant B")

    def test_mcp_agent_job_message_array(self, db_session):
        """Test agent job message array functionality."""
        agent_job = AgentExecution(
            tenant_key="test-tenant", agent_display_name="orchestrator", mission="Test message handling", status="active"
        )

        db_session.add(agent_job)
        db_session.commit()

        # Start with empty messages
        assert agent_job.messages == []

        # Add messages
        messages = [
            {"type": "start", "content": "Job started", "timestamp": "2025-01-01T00:00:00Z"},
            {"type": "progress", "content": "50% complete", "timestamp": "2025-01-01T00:30:00Z"},
            {"type": "complete", "content": "Job finished", "timestamp": "2025-01-01T01:00:00Z"},
        ]

        agent_job.messages = messages
        db_session.commit()

        # Verify messages are stored correctly
        assert len(agent_job.messages) == 3
        assert agent_job.messages[0]["type"] == "start"
        assert agent_job.messages[1]["content"] == "50% complete"
        assert agent_job.messages[2]["type"] == "complete"

    def test_mcp_agent_job_context_chunks_array(self, db_session):
        """Test agent job context chunks array functionality."""
        agent_job = AgentExecution(
            tenant_key="test-tenant", agent_display_name="analyzer", mission="Analyze with context", status="waiting"
        )

        db_session.add(agent_job)
        db_session.commit()

        # Start with empty context chunks
        assert agent_job.context_chunks == []

        # Add context chunks
        chunks = ["chunk-uuid-1", "chunk-uuid-2", "chunk-uuid-3", "chunk-uuid-4"]
        agent_job.context_chunks = chunks
        db_session.commit()

        # Verify chunks are stored correctly
        assert len(agent_job.context_chunks) == 4
        assert agent_job.context_chunks[0] == "chunk-uuid-1"
        assert agent_job.context_chunks[-1] == "chunk-uuid-4"


class TestProductHybridVisionStorage:
    """Test Product model hybrid vision storage enhancement."""

    @pytest.fixture
    def db_session(self):
        """Create in-memory SQLite database for testing."""
        engine = create_engine("sqlite:///:memory:")
        Base.metadata.create_all(engine)
        Session = sessionmaker(bind=engine)
        session = Session()
        yield session
        session.close()

    def test_product_hybrid_vision_storage(self, db_session):
        """Test both file and inline vision storage."""
        # Test file-based vision storage
        product_file = Product(
            id="product-file",
            tenant_key="test-tenant",
            name="Product with File Vision",
            description="Test file-based vision",
            vision_path="/path/to/vision.md",
            vision_type="file",
            chunked=False,
        )

        # Test inline vision storage
        product_inline = Product(
            id="product-inline",
            tenant_key="test-tenant",
            name="Product with Inline Vision",
            description="Test inline vision",
            vision_document="This is inline vision content",
            vision_type="inline",
            chunked=True,
        )

        # Test no vision
        product_none = Product(
            id="product-none",
            tenant_key="test-tenant",
            name="Product without Vision",
            description="Test no vision",
            vision_type="none",
            chunked=False,
        )

        db_session.add_all([product_file, product_inline, product_none])
        db_session.commit()

        # Verify file-based storage
        assert product_file.vision_path == "/path/to/vision.md"
        assert product_file.vision_document is None
        assert product_file.vision_type == "file"
        assert product_file.chunked is False

        # Verify inline storage
        assert product_inline.vision_path is None
        assert product_inline.vision_document == "This is inline vision content"
        assert product_inline.vision_type == "inline"
        assert product_inline.chunked is True

        # Verify no vision
        assert product_none.vision_path is None
        assert product_none.vision_document is None
        assert product_none.vision_type == "none"
        assert product_none.chunked is False

    def test_product_vision_type_constraint(self, db_session):
        """Test vision_type check constraint."""
        # Valid vision types should work
        valid_types = ["file", "inline", "none"]

        for vision_type in valid_types:
            product = Product(
                id=f"product-{vision_type}",
                tenant_key="test-tenant",
                name=f"Product {vision_type}",
                vision_type=vision_type,
            )
            db_session.add(product)

        db_session.commit()

        # Verify all products were created
        products = db_session.query(Product).all()
        assert len(products) == 3

        # Get vision types
        vision_types = [p.vision_type for p in products]
        assert "file" in vision_types
        assert "inline" in vision_types
        assert "none" in vision_types


if __name__ == "__main__":
    pytest.main([__file__, "-v"])
