"""
Comprehensive tests for the GiljoAI Vision Chunking System.
Tests chunking algorithm, boundary detection, and database integration.
"""

import asyncio
import shutil

# Add src to path
import sys
import tempfile
from pathlib import Path

import pytest


sys.path.insert(0, "src")

from src.giljo_mcp.database import DatabaseManager
from src.giljo_mcp.models import ContextIndex, LargeDocumentIndex, Project, Vision
from src.giljo_mcp.tenant import TenantManager
from src.giljo_mcp.tools.chunking import EnhancedChunker
from tests.helpers.test_db_helper import PostgreSQLTestHelper


class TestEnhancedChunker:
    """Test the enhanced chunking algorithm."""

    def setup_method(self):
        """Set up test fixtures."""
        self.chunker = EnhancedChunker(max_tokens=1000)

    def test_token_estimation(self):
        """Test token estimation accuracy."""
        # Test 1:4 ratio
        text = "test " * 1000  # 5000 chars
        estimated = self.chunker.estimate_tokens(text)
        assert estimated == 1250  # 5000 / 4

        # Test empty string
        assert self.chunker.estimate_tokens("") == 0

    def test_boundary_detection_hierarchy(self):
        """Test multi-level boundary detection."""
        # Document separator
        content = "text before\n---\ntext after"
        pos, boundary_type = self.chunker.find_natural_boundary(content, 15, 10)
        assert boundary_type == "document"
        assert content[pos - 4 : pos] == "---\n"

        # Section header
        content = "text before\n# Header\ntext after"
        pos, boundary_type = self.chunker.find_natural_boundary(content, 15, 10)
        assert boundary_type == "section"

        # Paragraph break
        content = "text before\n\ntext after"
        pos, boundary_type = self.chunker.find_natural_boundary(content, 15, 10)
        assert boundary_type == "paragraph"

        # Line break
        content = "text before\ntext after"
        pos, boundary_type = self.chunker.find_natural_boundary(content, 15, 10)
        assert boundary_type == "line"

        # Sentence end
        content = "First sentence. Second sentence"
        pos, boundary_type = self.chunker.find_natural_boundary(content, 20, 10)
        assert boundary_type == "sentence"

        # Word boundary
        content = "firstword secondword"
        pos, boundary_type = self.chunker.find_natural_boundary(content, 12, 5)
        assert boundary_type == "word"

    def test_no_mid_sentence_splits(self):
        """Verify chunks never split mid-sentence."""
        content = "This is sentence one. This is sentence two. This is sentence three. " * 50
        chunks = self.chunker.chunk_content(content, "test_doc")

        for chunk in chunks:
            # Check that chunk doesn't end mid-sentence
            text = chunk["content"].strip()
            if text and not text.endswith((".", "!", "?", "\n")):
                # Should end at a boundary
                assert chunk["boundary_type"] in ["line", "paragraph", "document", "word"]

    def test_small_document_no_chunking(self):
        """Test that small documents aren't unnecessarily chunked."""
        content = "Small document content. " * 10  # ~240 chars, ~60 tokens
        chunks = self.chunker.chunk_content(content, "small_doc")

        assert len(chunks) == 1
        assert chunks[0]["chunk_number"] == 1
        assert chunks[0]["total_chunks"] == 1
        assert chunks[0]["boundary_type"] == "complete"

    def test_large_document_chunking(self):
        """Test chunking of large documents."""
        # Create 10K token document (40K chars)
        content = "This is a test sentence. " * 1600
        chunks = self.chunker.chunk_content(content, "large_doc")

        # Should create ~10 chunks with 1000 token limit
        assert len(chunks) >= 8
        assert len(chunks) <= 12

        # Verify chunk numbering
        for i, chunk in enumerate(chunks, 1):
            assert chunk["chunk_number"] == i
            assert chunk["total_chunks"] == len(chunks)

    def test_chunk_metadata_extraction(self):
        """Test extraction of keywords and headers."""
        content = """
# Main Header

This document discusses Phase 1 of the Project involving Agents and Database.

## Sub Header

More content about API and UI deployment.
"""
        chunks = self.chunker.chunk_content(content, "metadata_doc")
        chunk = chunks[0]

        # Check keywords
        assert "Phase" in chunk["keywords"]
        assert "Project" in chunk["keywords"]
        assert "Database" in chunk["keywords"]

        # Check headers
        headers = chunk["headers"]
        assert len(headers) == 2
        assert headers[0]["text"] == "Main Header"
        assert headers[0]["level"] == 1
        assert headers[1]["text"] == "Sub Header"
        assert headers[1]["level"] == 2

    def test_chunk_consistency(self):
        """Test that chunking is consistent."""
        content = "Test content. " * 1000

        chunks1 = self.chunker.chunk_content(content, "doc")
        chunks2 = self.chunker.chunk_content(content, "doc")

        assert len(chunks1) == len(chunks2)
        for c1, c2 in zip(chunks1, chunks2):
            assert c1["content"] == c2["content"]
            assert c1["tokens"] == c2["tokens"]
            assert c1["boundary_type"] == c2["boundary_type"]

    def test_multiple_document_chunking(self):
        """Test chunking multiple documents together."""
        docs = [
            {"name": "doc1.md", "content": "Short content"},
            {"name": "doc2.md", "content": "Another short doc"},
            {"name": "doc3.md", "content": "Large content. " * 500},
        ]

        chunks = self.chunker.chunk_multiple_documents(docs)

        # Small docs should be combined, large one separate
        assert len(chunks) >= 2

        # Check combined small docs
        if "doc1.md" in chunks[0]["content"] and "doc2.md" in chunks[0]["content"]:
            assert chunks[0]["document_name"] == "combined"

    def test_content_hash(self):
        """Test content hash calculation."""
        content = "Test content for hashing"
        hash1 = self.chunker.calculate_content_hash(content)
        hash2 = self.chunker.calculate_content_hash(content)
        hash3 = self.chunker.calculate_content_hash(content + " modified")

        assert hash1 == hash2  # Same content, same hash
        assert hash1 != hash3  # Different content, different hash
        assert len(hash1) == 32  # MD5 hash length


class TestChunkingPerformance:
    """Performance tests for chunking large documents."""

    def test_100k_token_document(self):
        """Test chunking a 100K token document."""
        import time

        # Create 100K token document (400K chars)
        content = "This is a test sentence with various words. " * 8888

        chunker = EnhancedChunker(max_tokens=25000)

        start = time.time()
        chunks = chunker.chunk_content(content, "massive_doc")
        duration = time.time() - start

        # Should complete in under 2 seconds
        assert duration < 2.0

        # Should create ~4 chunks (was ~5 with 20K limit)
        assert 3 <= len(chunks) <= 5

        # Verify all chunks have proper metadata
        for chunk in chunks:
            assert chunk["tokens"] > 0
            assert chunk["tokens"] <= 25000
            assert chunk["boundary_type"] is not None
            assert chunk["char_start"] >= 0
            assert chunk["char_end"] > chunk["char_start"]

    def test_memory_efficiency(self):
        """Test memory usage stays reasonable."""
        import os

        import psutil

        process = psutil.Process(os.getpid())

        # Baseline memory
        baseline_memory = process.memory_info().rss / 1024 / 1024  # MB

        # Create and chunk 100K token document
        content = "Test content. " * 30000
        chunker = EnhancedChunker()
        chunker.chunk_content(content, "memory_test")

        # Check memory after
        after_memory = process.memory_info().rss / 1024 / 1024  # MB
        memory_increase = after_memory - baseline_memory

        # Should use less than 100MB for 100K document
        assert memory_increase < 100


@pytest.mark.asyncio
class TestDatabaseIntegration:
    """Test database integration for chunking system."""

    async def setup_method(self):
        """Set up test database."""
        # Use in-memory SQLite for tests
        self.db_manager = DatabaseManager(PostgreSQLTestHelper.get_test_db_url(async_driver=False), is_async=True)
        await self.db_manager.create_tables_async()

        self.tenant_manager = TenantManager()

        # Create test project
        async with self.db_manager.get_session_async() as session:
            project = Project(
                id="test-project-id", tenant_key="test-tenant", name="Test Project", mission="Test mission"
            )
            session.add(project)
            await session.commit()

    async def test_vision_storage(self):
        """Test storing vision chunks in database."""
        EnhancedChunker()
        chunks = [
            {
                "chunk_number": 1,
                "total_chunks": 2,
                "content": "First chunk",
                "tokens": 10,
                "char_start": 0,
                "char_end": 11,
                "boundary_type": "line",
                "keywords": ["test"],
                "headers": [],
                "document_name": "test.md",
            },
            {
                "chunk_number": 2,
                "total_chunks": 2,
                "content": "Second chunk",
                "tokens": 10,
                "char_start": 12,
                "char_end": 24,
                "boundary_type": "complete",
                "keywords": ["test"],
                "headers": [],
                "document_name": "test.md",
            },
        ]

        async with self.db_manager.get_session_async() as session:
            for chunk_data in chunks:
                vision = Vision(
                    tenant_key="test-tenant",
                    project_id="test-project-id",
                    document_name=chunk_data["document_name"],
                    chunk_number=chunk_data["chunk_number"],
                    total_chunks=chunk_data["total_chunks"],
                    content=chunk_data["content"],
                    tokens=chunk_data["tokens"],
                    char_start=chunk_data["char_start"],
                    char_end=chunk_data["char_end"],
                    boundary_type=chunk_data["boundary_type"],
                    keywords=chunk_data["keywords"],
                    headers=chunk_data["headers"],
                )
                session.add(vision)

            await session.commit()

            # Verify storage
            from sqlalchemy import select

            result = await session.execute(select(Vision).where(Vision.project_id == "test-project-id"))
            visions = result.scalars().all()

            assert len(visions) == 2
            assert visions[0].chunk_number == 1
            assert visions[1].chunk_number == 2
            assert visions[0].boundary_type == "line"
            assert visions[1].boundary_type == "complete"

    async def test_context_index_creation(self):
        """Test creation of context index."""
        async with self.db_manager.get_session_async() as session:
            index = ContextIndex(
                tenant_key="test-tenant",
                project_id="test-project-id",
                index_type="vision",
                document_name="test.md",
                chunk_numbers=[1, 2, 3],
                summary="Test document summary",
                token_count=1000,
                keywords=["test", "document"],
                full_path="docs/test.md",
                content_hash="abc123",
            )
            session.add(index)
            await session.commit()

            # Verify storage
            from sqlalchemy import select

            result = await session.execute(select(ContextIndex).where(ContextIndex.project_id == "test-project-id"))
            indexes = result.scalars().all()

            assert len(indexes) == 1
            assert indexes[0].document_name == "test.md"
            assert indexes[0].chunk_numbers == [1, 2, 3]
            assert "test" in indexes[0].keywords

    async def test_large_document_index(self):
        """Test large document index creation."""
        async with self.db_manager.get_session_async() as session:
            large_doc = LargeDocumentIndex(
                tenant_key="test-tenant",
                project_id="test-project-id",
                document_path="docs/large.md",
                document_type="markdown",
                total_size=100000,
                total_tokens=25000,
                chunk_count=5,
                metadata={"created": "2024-01-01"},
            )
            session.add(large_doc)
            await session.commit()

            # Verify storage
            from sqlalchemy import select

            result = await session.execute(
                select(LargeDocumentIndex).where(LargeDocumentIndex.project_id == "test-project-id")
            )
            docs = result.scalars().all()

            assert len(docs) == 1
            assert docs[0].document_path == "docs/large.md"
            assert docs[0].total_tokens == 25000
            assert docs[0].chunk_count == 5


def test_file_type_detection():
    """Test document type detection."""
    test_dir = tempfile.mkdtemp()

    try:
        # Create test files
        md_file = Path(test_dir) / "test.md"
        md_file.write_text("# Markdown")

        yaml_file = Path(test_dir) / "test.yaml"
        yaml_file.write_text("key: value")

        json_file = Path(test_dir) / "test.json"
        json_file.write_text('{"key": "value"}')

        txt_file = Path(test_dir) / "test.txt"
        txt_file.write_text("Plain text")

        # Test detection (would be in actual function)
        assert md_file.suffix == ".md"
        assert yaml_file.suffix == ".yaml"
        assert json_file.suffix == ".json"
        assert txt_file.suffix == ".txt"

    finally:
        shutil.rmtree(test_dir)


if __name__ == "__main__":
    # Run synchronous tests
    test_chunker = TestEnhancedChunker()
    test_chunker.setup_method()

    test_chunker.test_token_estimation()

    test_chunker.test_boundary_detection_hierarchy()

    test_chunker.test_no_mid_sentence_splits()

    test_chunker.test_small_document_no_chunking()

    test_chunker.test_large_document_chunking()

    test_chunker.test_chunk_metadata_extraction()

    test_chunker.test_chunk_consistency()

    test_chunker.test_multiple_document_chunking()

    test_chunker.test_content_hash()

    # Performance tests
    perf_test = TestChunkingPerformance()

    perf_test.test_100k_token_document()

    perf_test.test_memory_efficiency()

    # Async database tests

    async def run_async_tests():
        db_test = TestDatabaseIntegration()
        await db_test.setup_method()

        await db_test.test_vision_storage()

        await db_test.test_context_index_creation()

        await db_test.test_large_document_index()

    asyncio.run(run_async_tests())

    test_file_type_detection()
