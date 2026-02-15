"""
Unit tests for Handover 0017 agent models.

Tests MCPContextIndex, MCPContextSummary, and AgentExecution models
with focus on tenant isolation and data integrity.

NOTE: These tests use existing giljo_mcp database (not a separate test database)
because models use JSONB columns which are PostgreSQL-specific. SQLite doesn't support JSONB.
Tests clean up after themselves by rolling back transactions.
"""

from datetime import datetime, timezone

import pytest
from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker

from src.giljo_mcp.models import MCPContextIndex, MCPContextSummary, Product
from src.giljo_mcp.models.agent_identity import AgentExecution, AgentJob


# Use giljo_mcp_test database (tests will rollback changes)
TEST_DB_URL = "postgresql://postgres:***@localhost:5432/giljo_mcp_test"


class TestMCPContextIndex:
    """Test MCPContextIndex model functionality."""

    @pytest.fixture
    def db_session(self):
        """Create PostgreSQL test database session with transaction rollback."""
        engine = create_engine(TEST_DB_URL)
        connection = engine.connect()
        transaction = connection.begin()
        Session = sessionmaker(bind=connection)
        session = Session()

        yield session

        # Cleanup: rollback transaction (undoes all test changes)
        session.close()
        transaction.rollback()
        connection.close()

    @pytest.fixture
    def sample_product(self, db_session):
        """Create a sample product for testing."""
        import uuid

        product = Product(
            id=str(uuid.uuid4()),
            tenant_key="test-tenant",
            name=f"Test Product {uuid.uuid4()}",
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
        """Create PostgreSQL test database session with transaction rollback."""
        engine = create_engine(TEST_DB_URL)
        connection = engine.connect()
        transaction = connection.begin()
        Session = sessionmaker(bind=connection)
        session = Session()

        yield session

        # Cleanup: rollback transaction (undoes all test changes)
        session.close()
        transaction.rollback()
        connection.close()

    @pytest.fixture
    def sample_product(self, db_session):
        """Create a sample product for testing."""
        import uuid

        product = Product(
            id=str(uuid.uuid4()),
            tenant_key="test-tenant",
            name=f"Test Product {uuid.uuid4()}",
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


class TestAgentExecution:
    """Test AgentExecution model functionality."""

    @pytest.fixture
    def db_session(self):
        """Create PostgreSQL test database session with transaction rollback."""
        engine = create_engine(TEST_DB_URL)
        connection = engine.connect()
        transaction = connection.begin()
        Session = sessionmaker(bind=connection)
        session = Session()

        yield session

        # Cleanup: rollback transaction (undoes all test changes)
        session.close()
        transaction.rollback()
        connection.close()

    def test_agent_execution_creation(self, db_session):
        """Test creating agent execution with all fields."""
        # First create an AgentJob (work order)
        agent_job = AgentJob(
            tenant_key="test-tenant",
            job_type="orchestrator",
            mission="Coordinate development project tasks",
            status="active",
        )
        db_session.add(agent_job)
        db_session.commit()

        # Then create an AgentExecution (executor)
        agent_execution = AgentExecution(
            tenant_key="test-tenant",
            job_id=agent_job.job_id,
            agent_display_name="orchestrator",
            status="waiting",
            spawned_by="parent-agent-id",
        )

        db_session.add(agent_execution)
        db_session.commit()

        # Verify creation
        assert agent_execution.id is not None
        assert agent_execution.agent_id is not None
        assert agent_execution.job_id == agent_job.job_id
        assert agent_execution.tenant_key == "test-tenant"
        assert agent_execution.agent_display_name == "orchestrator"
        assert agent_execution.status == "waiting"
        assert agent_execution.spawned_by == "parent-agent-id"
        # Message counters (Handover 0387e)
        assert agent_execution.messages_sent_count == 0
        assert agent_execution.messages_waiting_count == 0
        assert agent_execution.messages_read_count == 0
        # Verify relationship to job
        assert agent_execution.job == agent_job
        assert agent_execution.job.mission == "Coordinate development project tasks"

    def test_agent_execution_status_workflow(self, db_session):
        """Test execution status transitions."""
        # Create job first
        job = AgentJob(
            tenant_key="test-tenant",
            job_type="analyzer",
            mission="Analyze codebase structure",
            status="active",
        )
        db_session.add(job)
        db_session.commit()

        # Create execution
        agent_execution = AgentExecution(
            tenant_key="test-tenant", job_id=job.job_id, agent_display_name="analyzer", status="waiting"
        )

        db_session.add(agent_execution)
        db_session.commit()

        # Test status transitions
        assert agent_execution.status == "waiting"
        assert agent_execution.started_at is None
        assert agent_execution.completed_at is None

        # Move to working
        agent_execution.status = "working"
        agent_execution.started_at = datetime.now(timezone.utc)
        db_session.commit()

        assert agent_execution.status == "working"
        assert agent_execution.started_at is not None
        assert agent_execution.completed_at is None

        # Move to complete
        agent_execution.status = "complete"
        agent_execution.completed_at = datetime.now(timezone.utc)
        db_session.commit()

        assert agent_execution.status == "complete"
        assert agent_execution.started_at is not None
        assert agent_execution.completed_at is not None

    def test_agent_execution_tenant_isolation(self, db_session):
        """Test tenant isolation in agent executions."""
        # Create jobs first
        job_a = AgentJob(
            tenant_key="tenant-a", job_type="implementer", mission="Implement feature for tenant A", status="active"
        )
        job_b = AgentJob(tenant_key="tenant-b", job_type="tester", mission="Test feature for tenant B", status="active")
        db_session.add_all([job_a, job_b])
        db_session.commit()

        # Create executions
        execution_a = AgentExecution(
            tenant_key="tenant-a", job_id=job_a.job_id, agent_display_name="implementer", status="waiting"
        )
        execution_b = AgentExecution(
            tenant_key="tenant-b", job_id=job_b.job_id, agent_display_name="tester", status="working"
        )

        db_session.add_all([execution_a, execution_b])
        db_session.commit()

        # Query for tenant A only
        tenant_a_executions = db_session.query(AgentExecution).filter(AgentExecution.tenant_key == "tenant-a").all()

        assert len(tenant_a_executions) == 1
        assert tenant_a_executions[0].agent_display_name == "implementer"
        assert tenant_a_executions[0].job.mission.endswith("tenant A")

        # Query for tenant B only
        tenant_b_executions = db_session.query(AgentExecution).filter(AgentExecution.tenant_key == "tenant-b").all()

        assert len(tenant_b_executions) == 1
        assert tenant_b_executions[0].agent_display_name == "tester"
        assert tenant_b_executions[0].job.mission.endswith("tenant B")

    def test_agent_execution_message_counters(self, db_session):
        """Test agent execution message counter functionality (Handover 0387e)."""
        # Create job first
        job = AgentJob(
            tenant_key="test-tenant", job_type="orchestrator", mission="Test message handling", status="active"
        )
        db_session.add(job)
        db_session.commit()

        # Create execution
        agent_execution = AgentExecution(
            tenant_key="test-tenant", job_id=job.job_id, agent_display_name="orchestrator", status="working"
        )

        db_session.add(agent_execution)
        db_session.commit()

        # Start with zero message counts
        assert agent_execution.messages_sent_count == 0
        assert agent_execution.messages_waiting_count == 0
        assert agent_execution.messages_read_count == 0

        # Simulate sending messages
        agent_execution.messages_sent_count = 3
        db_session.commit()
        assert agent_execution.messages_sent_count == 3

        # Simulate receiving messages
        agent_execution.messages_waiting_count = 2
        db_session.commit()
        assert agent_execution.messages_waiting_count == 2

        # Simulate reading messages
        agent_execution.messages_read_count = 2
        agent_execution.messages_waiting_count = 0
        db_session.commit()
        assert agent_execution.messages_read_count == 2
        assert agent_execution.messages_waiting_count == 0

class TestProductVisionDocumentRelationship:
    """Test Product model VisionDocument relationship (Handover 0128e)."""

    @pytest.fixture
    def db_session(self):
        """Create PostgreSQL test database session with transaction rollback."""
        engine = create_engine(TEST_DB_URL)
        connection = engine.connect()
        transaction = connection.begin()
        Session = sessionmaker(bind=connection)
        session = Session()

        yield session

        # Cleanup: rollback transaction (undoes all test changes)
        session.close()
        transaction.rollback()
        connection.close()

    def test_product_with_vision_documents(self, db_session):
        """Test Product with VisionDocument relationship."""
        import uuid

        from src.giljo_mcp.models.products import VisionDocument

        # Create product
        product = Product(
            id=str(uuid.uuid4()),
            tenant_key="test-tenant",
            name=f"Product with Vision Documents {uuid.uuid4()}",
            description="Test VisionDocument relationship",
        )
        db_session.add(product)
        db_session.commit()

        # Add vision document with file storage
        vision_file = VisionDocument(
            tenant_key="test-tenant",
            product_id=product.id,
            document_name="Architecture",
            document_type="architecture",
            vision_path="/path/to/architecture.md",
            storage_type="file",
            chunked=False,
            is_active=True,
        )
        db_session.add(vision_file)
        db_session.commit()

        # Add vision document with inline storage
        vision_inline = VisionDocument(
            tenant_key="test-tenant",
            product_id=product.id,
            document_name="API Docs",
            document_type="api",
            vision_document="This is inline API documentation",
            storage_type="inline",
            chunked=True,
            chunk_count=1,  # Must be > 0 when chunked=True
            is_active=True,
        )
        db_session.add(vision_inline)
        db_session.commit()

        # Refresh product to load relationships
        db_session.refresh(product)

        # Verify relationships
        assert len(product.vision_documents) == 2
        assert product.has_vision_documents is True

        # Check file-based document
        file_doc = [d for d in product.vision_documents if d.storage_type == "file"][0]
        assert file_doc.vision_path == "/path/to/architecture.md"
        assert file_doc.vision_document is None

        # Check inline document
        inline_doc = [d for d in product.vision_documents if d.storage_type == "inline"][0]
        assert inline_doc.vision_document == "This is inline API documentation"
        assert inline_doc.vision_path is None

    def test_product_without_vision(self, db_session):
        """Test Product without any vision documents."""
        # Create product without vision documents
        product_none = Product(
            id="product-none",
            tenant_key="test-tenant",
            name="Product without Vision",
            description="Test no vision",
        )
        db_session.add(product_none)
        db_session.commit()

        # Verify no vision documents
        assert len(product_none.vision_documents) == 0
        assert product_none.has_vision_documents is False
        assert product_none.has_vision is False


if __name__ == "__main__":
    pytest.main([__file__, "-v"])
