"""
Integration tests for Handover 0017 agent workflows.

Tests complete workflows including vision upload → chunking → storage,
agent job lifecycle, and multi-tenant isolation.
"""

import pytest

from src.giljo_mcp.database import DatabaseManager
from src.giljo_mcp.models import Product
from src.giljo_mcp.repositories.agent_job_repository import AgentJobRepository
from src.giljo_mcp.repositories.context_repository import ContextRepository
from src.giljo_mcp.tools.chunking import EnhancedChunker


class TestVisionUploadToChunks:
    """Test vision document upload and chunking workflow."""

    @pytest.fixture
    async def async_db_manager(self):
        """Create async database manager for testing."""
        from tests.helpers.test_db_helper import PostgreSQLTestHelper

        db_url = PostgreSQLTestHelper.get_test_db_url()
        db_manager = DatabaseManager(db_url, is_async=True)

        # Create tables
        await db_manager.create_tables_async()

        yield db_manager

        # Cleanup
        await db_manager.close_async()

    @pytest.fixture
    async def sample_product(self, async_db_manager):
        """Create a sample product for testing."""
        async with async_db_manager.get_session_async() as session:
            product = Product(
                id="test-product-id",
                tenant_key="test-tenant",
                name="Test Product",
                description="Product for vision chunking tests",
                vision_type="none",
                chunked=False,
            )
            session.add(product)
            await session.commit()
            await session.refresh(product)
            return product

    @pytest.mark.asyncio
    async def test_vision_upload_to_chunks(self, async_db_manager, sample_product):
        """Test uploading vision → chunking → storage."""
        context_repo = ContextRepository(async_db_manager)
        chunker = EnhancedChunker(max_tokens=20000)

        # Sample vision content
        vision_content = """
        # Product Vision: AI Development Platform

        ## Overview
        We are building an advanced AI development platform that enables developers
        to create, deploy, and manage AI agents with ease. The platform provides
        comprehensive tooling for agent orchestration and coordination.

        ## Core Features
        - Multi-agent orchestration system
        - Real-time agent communication
        - Comprehensive project management
        - Advanced context management
        - Token-efficient operations

        ## Technical Architecture
        The system uses FastAPI for the backend, Vue.js for the frontend,
        and PostgreSQL for data persistence. All operations are designed
        with multi-tenant isolation in mind.

        ## Implementation Strategy
        Phase 1: Core infrastructure and database schema
        Phase 2: Agent coordination and messaging
        Phase 3: Advanced context management
        Phase 4: UI and user experience enhancements
        Phase 5: Performance optimization and scaling
        """

        async with async_db_manager.get_session_async() as session:
            # 1. Chunk the vision content
            chunks = chunker.chunk_content(vision_content, sample_product.name)
            assert len(chunks) > 0

            total_tokens = 0
            chunks_created = 0

            # 2. Store chunks in mcp_context_index
            for chunk in chunks:
                context_chunk = context_repo.create_chunk(
                    session,
                    "test-tenant",
                    sample_product.id,
                    content=chunk["content"],
                    keywords=chunk["keywords"],
                    token_count=chunk["tokens"],
                    chunk_order=chunk["chunk_number"],
                    summary=None,  # Phase 1 - no LLM summary
                )
                chunks_created += 1
                total_tokens += chunk["tokens"]

            # 3. Update Product model
            product = await session.get(Product, sample_product.id)
            product.vision_document = vision_content
            product.vision_type = "inline"
            product.chunked = True

            await session.commit()

            # 4. Verify chunks were created correctly
            created_chunks = context_repo.get_chunks_by_product(session, "test-tenant", sample_product.id)

            assert len(created_chunks) == chunks_created
            assert all(chunk.tenant_key == "test-tenant" for chunk in created_chunks)
            assert all(chunk.product_id == sample_product.id for chunk in created_chunks)

            # Verify chunks are ordered correctly
            chunk_orders = [chunk.chunk_order for chunk in created_chunks]
            assert chunk_orders == sorted(chunk_orders)

            # 5. Verify Product.chunked = True
            updated_product = await session.get(Product, sample_product.id)
            assert updated_product.chunked is True
            assert updated_product.vision_type == "inline"
            assert updated_product.vision_document == vision_content

            # 6. Test search functionality
            search_results = context_repo.search_chunks(session, "test-tenant", sample_product.id, "orchestration")
            assert len(search_results) > 0

            # Verify search results contain the keyword
            found_orchestration = False
            for result in search_results:
                if "orchestration" in result.content.lower():
                    found_orchestration = True
                    break
            assert found_orchestration

    @pytest.mark.asyncio
    async def test_vision_chunking_with_different_sizes(self, async_db_manager, sample_product):
        """Test chunking with different content sizes."""
        context_repo = ContextRepository(async_db_manager)

        # Test small content (single chunk)
        small_content = "This is a small vision document that should fit in one chunk."
        chunker_small = EnhancedChunker(max_tokens=1000)
        small_chunks = chunker_small.chunk_content(small_content, "Small Doc")

        assert len(small_chunks) == 1
        assert small_chunks[0]["chunk_number"] == 1
        assert small_chunks[0]["total_chunks"] == 1

        # Test large content (multiple chunks)
        large_content = "\n\n".join(
            [f"Section {i}: " + "This is a detailed section with lots of content. " * 50 for i in range(1, 11)]
        )

        chunker_large = EnhancedChunker(max_tokens=500)  # Small chunks to force splitting
        large_chunks = chunker_large.chunk_content(large_content, "Large Doc")

        assert len(large_chunks) > 1

        # Verify chunk continuity
        for i, chunk in enumerate(large_chunks, 1):
            assert chunk["chunk_number"] == i
            assert chunk["total_chunks"] == len(large_chunks)

        # Store large content chunks
        async with async_db_manager.get_session_async() as session:
            for chunk in large_chunks:
                context_repo.create_chunk(
                    session,
                    "test-tenant",
                    sample_product.id,
                    content=chunk["content"],
                    keywords=chunk["keywords"],
                    token_count=chunk["tokens"],
                    chunk_order=chunk["chunk_number"],
                )

            await session.commit()

            # Verify all chunks stored correctly
            stored_chunks = context_repo.get_chunks_by_product(session, "test-tenant", sample_product.id)
            assert len(stored_chunks) == len(large_chunks)


class TestAgentJobLifecycle:
    """Test complete agent job workflow."""

    @pytest.fixture
    async def async_db_manager(self):
        """Create async database manager for testing."""
        from tests.helpers.test_db_helper import PostgreSQLTestHelper

        db_url = PostgreSQLTestHelper.get_test_db_url()
        db_manager = DatabaseManager(db_url, is_async=True)
        await db_manager.create_tables_async()
        yield db_manager
        await db_manager.close_async()

    @pytest.mark.asyncio
    async def test_agent_job_lifecycle(self, async_db_manager):
        """Test complete agent job workflow."""
        job_repo = AgentJobRepository(async_db_manager)

        async with async_db_manager.get_session_async() as session:
            # 1. Create job (pending)
            job = job_repo.create_job(
                session,
                "test-tenant",
                agent_display_name="orchestrator",
                mission="Coordinate development tasks for new feature",
                spawned_by="parent-orchestrator",
                context_chunks=["chunk-1", "chunk-2", "chunk-3"],
            )

            await session.commit()

            assert job.status == "pending"
            assert job.agent_display_name == "orchestrator"
            assert job.spawned_by == "parent-orchestrator"
            assert job.context_chunks == ["chunk-1", "chunk-2", "chunk-3"]
            assert job.acknowledged is False
            assert job.started_at is None
            assert job.completed_at is None

            job_id = job.job_id

            # 2. Update status to active
            success = job_repo.update_status(session, "test-tenant", job_id, "active")
            await session.commit()

            assert success is True

            # Verify status update
            updated_job = job_repo.get_job_by_job_id(session, "test-tenant", job_id)
            assert updated_job.status == "active"
            assert updated_job.started_at is not None

            # 3. Add messages during execution
            messages = [
                {"type": "start", "content": "Job started", "agent": "orchestrator"},
                {"type": "progress", "content": "Analyzing requirements", "progress": 25},
                {"type": "progress", "content": "Creating task breakdown", "progress": 50},
                {"type": "progress", "content": "Assigning sub-agents", "progress": 75},
            ]

            for message in messages:
                job_repo.add_message(session, "test-tenant", job_id, message)

            await session.commit()

            # Verify messages were added
            job_with_messages = job_repo.get_job_by_job_id(session, "test-tenant", job_id)
            assert len(job_with_messages.messages) == len(messages)
            assert job_with_messages.messages[0]["type"] == "start"
            assert job_with_messages.messages[-1]["progress"] == 75

            # 4. Acknowledge job
            ack_success = job_repo.acknowledge_job(session, "test-tenant", job_id)
            await session.commit()

            assert ack_success is True

            acknowledged_job = job_repo.get_job_by_job_id(session, "test-tenant", job_id)
            assert acknowledged_job.acknowledged is True

            # 5. Add context chunks dynamically
            additional_chunks = ["chunk-4", "chunk-5"]
            for chunk_id in additional_chunks:
                job_repo.add_context_chunk(session, "test-tenant", job_id, chunk_id)

            await session.commit()

            # Verify chunks were added
            final_job = job_repo.get_job_by_job_id(session, "test-tenant", job_id)
            assert len(final_job.context_chunks) == 5  # Original 3 + 2 new
            assert "chunk-4" in final_job.context_chunks
            assert "chunk-5" in final_job.context_chunks

            # 6. Complete job
            completion_success = job_repo.update_status(session, "test-tenant", job_id, "completed")
            await session.commit()

            assert completion_success is True

            completed_job = job_repo.get_job_by_job_id(session, "test-tenant", job_id)
            assert completed_job.status == "completed"
            assert completed_job.completed_at is not None
            assert completed_job.started_at is not None

            # Verify time progression
            assert completed_job.completed_at > completed_job.started_at

    @pytest.mark.asyncio
    async def test_agent_job_spawning_hierarchy(self, async_db_manager):
        """Test agent job spawning and hierarchy."""
        job_repo = AgentJobRepository(async_db_manager)

        async with async_db_manager.get_session_async() as session:
            # Create parent orchestrator job
            parent_job = job_repo.create_job(
                session,
                "test-tenant",
                agent_display_name="orchestrator",
                mission="Main project coordination",
                spawned_by=None,  # Top-level job
            )

            await session.commit()
            parent_job_id = parent_job.job_id

            # Spawn child jobs
            child_jobs = []
            agent_display_names = ["analyzer", "implementer", "tester"]

            for agent_display_name in agent_display_names:
                child_job = job_repo.create_job(
                    session,
                    "test-tenant",
                    agent_display_name=agent_display_name,
                    mission=f"Execute {agent_display_name} tasks",
                    spawned_by=parent_job_id,
                    context_chunks=[f"{agent_display_name}-context-1", f"{agent_display_name}-context-2"],
                )
                child_jobs.append(child_job)

            await session.commit()

            # Verify hierarchy
            spawned_jobs = job_repo.get_jobs_by_spawner(session, "test-tenant", parent_job_id)
            assert len(spawned_jobs) == 3

            spawned_agent_display_names = [job.agent_display_name for job in spawned_jobs]
            assert "analyzer" in spawned_agent_display_names
            assert "implementer" in spawned_agent_display_names
            assert "tester" in spawned_agent_display_names

            # Verify all children reference parent
            for job in spawned_jobs:
                assert job.spawned_by == parent_job_id

            # Test job statistics
            stats = job_repo.get_job_statistics(session, "test-tenant")
            assert stats["total_jobs"] == 4  # 1 parent + 3 children
            assert stats["by_status"]["pending"] == 4  # All pending initially
            assert stats["by_agent_display_name"]["orchestrator"] == 1
            assert stats["by_agent_display_name"]["analyzer"] == 1
            assert stats["by_agent_display_name"]["implementer"] == 1
            assert stats["by_agent_display_name"]["tester"] == 1


class TestMultiTenantIsolation:
    """Test multi-tenant isolation for all new models."""

    @pytest.fixture
    async def async_db_manager(self):
        """Create async database manager for testing."""
        from tests.helpers.test_db_helper import PostgreSQLTestHelper

        db_url = PostgreSQLTestHelper.get_test_db_url()
        db_manager = DatabaseManager(db_url, is_async=True)
        await db_manager.create_tables_async()
        yield db_manager
        await db_manager.close_async()

    @pytest.mark.asyncio
    async def test_multi_tenant_isolation(self, async_db_manager):
        """Verify tenant isolation for all new models."""
        context_repo = ContextRepository(async_db_manager)
        job_repo = AgentJobRepository(async_db_manager)

        async with async_db_manager.get_session_async() as session:
            # Create products for two tenants
            product_a = Product(
                id="product-a", tenant_key="tenant-a", name="Product A", description="Product for tenant A"
            )

            product_b = Product(
                id="product-b", tenant_key="tenant-b", name="Product B", description="Product for tenant B"
            )

            session.add_all([product_a, product_b])
            await session.commit()

            # Create context data for tenant A
            context_a = context_repo.create_chunk(
                session,
                "tenant-a",
                "product-a",
                content="Confidential content for tenant A",
                keywords=["confidential", "tenant-a"],
                token_count=100,
                chunk_order=1,
            )

            summary_a = context_repo.create_summary(
                session,
                "tenant-a",
                "product-a",
                full_content="Full confidential content for tenant A",
                condensed_mission="Condensed mission for tenant A",
                full_tokens=500,
                condensed_tokens=150,
            )

            job_a = job_repo.create_job(
                session,
                "tenant-a",
                agent_display_name="orchestrator",
                mission="Secret mission for tenant A",
                context_chunks=["chunk-a-1", "chunk-a-2"],
            )

            # Create context data for tenant B
            context_b = context_repo.create_chunk(
                session,
                "tenant-b",
                "product-b",
                content="Private content for tenant B",
                keywords=["private", "tenant-b"],
                token_count=120,
                chunk_order=1,
            )

            summary_b = context_repo.create_summary(
                session,
                "tenant-b",
                "product-b",
                full_content="Full private content for tenant B",
                condensed_mission="Condensed mission for tenant B",
                full_tokens=600,
                condensed_tokens=180,
            )

            job_b = job_repo.create_job(
                session,
                "tenant-b",
                agent_display_name="implementer",
                mission="Classified mission for tenant B",
                context_chunks=["chunk-b-1", "chunk-b-2"],
            )

            await session.commit()

            # Test MCPContextIndex isolation
            tenant_a_contexts = context_repo.get_chunks_by_product(session, "tenant-a", "product-a")
            tenant_b_contexts = context_repo.get_chunks_by_product(session, "tenant-b", "product-b")

            assert len(tenant_a_contexts) == 1
            assert len(tenant_b_contexts) == 1
            assert tenant_a_contexts[0].content == "Confidential content for tenant A"
            assert tenant_b_contexts[0].content == "Private content for tenant B"

            # Verify tenant A cannot access tenant B's data
            tenant_a_trying_b = context_repo.get_chunks_by_product(session, "tenant-a", "product-b")
            assert len(tenant_a_trying_b) == 0

            # Test MCPContextSummary isolation
            tenant_a_summaries = context_repo.get_summaries_by_product(session, "tenant-a", "product-a")
            tenant_b_summaries = context_repo.get_summaries_by_product(session, "tenant-b", "product-b")

            assert len(tenant_a_summaries) == 1
            assert len(tenant_b_summaries) == 1
            assert tenant_a_summaries[0].condensed_mission == "Condensed mission for tenant A"
            assert tenant_b_summaries[0].condensed_mission == "Condensed mission for tenant B"

            # Test MCPAgentJob isolation
            tenant_a_jobs = job_repo.get_active_jobs(session, "tenant-a")
            tenant_b_jobs = job_repo.get_active_jobs(session, "tenant-b")

            assert len(tenant_a_jobs) == 1
            assert len(tenant_b_jobs) == 1
            assert tenant_a_jobs[0].mission == "Secret mission for tenant A"
            assert tenant_b_jobs[0].mission == "Classified mission for tenant B"

            # Verify cross-tenant access fails
            tenant_a_job_id = tenant_a_jobs[0].job_id
            cross_tenant_job = job_repo.get_job_by_job_id(session, "tenant-b", tenant_a_job_id)
            assert cross_tenant_job is None

            # Test search isolation
            tenant_a_search = context_repo.search_chunks(session, "tenant-a", "product-a", "content")
            tenant_b_search = context_repo.search_chunks(session, "tenant-b", "product-b", "content")

            assert len(tenant_a_search) == 1
            assert len(tenant_b_search) == 1
            assert "tenant A" in tenant_a_search[0].content
            assert "tenant B" in tenant_b_search[0].content

            # Cross-tenant search should return empty
            cross_search = context_repo.search_chunks(session, "tenant-a", "product-b", "content")
            assert len(cross_search) == 0

            # Test statistics isolation
            stats_a = job_repo.get_job_statistics(session, "tenant-a")
            stats_b = job_repo.get_job_statistics(session, "tenant-b")

            assert stats_a["total_jobs"] == 1
            assert stats_b["total_jobs"] == 1
            assert stats_a["by_agent_display_name"]["orchestrator"] == 1
            assert stats_b["by_agent_display_name"]["implementer"] == 1


if __name__ == "__main__":
    pytest.main([__file__, "-v"])
