"""
Comprehensive test suite for Vision Document Chunking System
Tests the actual implementation with real documents and performance metrics
"""

import asyncio
import sys
import tempfile
from pathlib import Path

import pytest


# Add src to path
sys.path.insert(0, str(Path(__file__).parent.parent / "src"))
sys.path.insert(0, str(Path(__file__).parent.parent))

# Import the actual implementation
from test_vision_chunking import PerformanceTracker, TestDocumentGenerator, TestFixtures

from src.giljo_mcp.tools.chunking import EnhancedChunker


class TestActualChunking:
    """Test the actual chunking implementation"""

    def setup_method(self):
        """Set up test environment"""
        self.chunker = EnhancedChunker(max_tokens=25000)
        self.generator = TestDocumentGenerator()
        self.tracker = PerformanceTracker()
        self.fixtures = TestFixtures()

    def test_token_estimation(self):
        """Test token estimation accuracy"""
        test_cases = [
            ("Hello World", 3),  # ~11 chars / 4 = ~3 tokens
            ("A" * 400, 100),  # 400 chars / 4 = 100 tokens
            ("This is a longer test sentence with multiple words.", 13),
        ]

        for text, expected_tokens in test_cases:
            estimated = self.chunker.estimate_tokens(text)
            # Allow for ±30% variance (or at least 1 token difference)
            tolerance = max(expected_tokens * 0.3, 1)
            assert abs(estimated - expected_tokens) <= tolerance, (
                f"Token estimation off for '{text[:20]}...': got {estimated}, expected ~{expected_tokens}"
            )

    def test_chunk_50k_document(self):
        """Test chunking of 50K token document"""

        # Generate 50K token document
        doc = self.generator.generate_markdown_document(50000)

        # Chunk the document
        with self.tracker.measure("chunk_50k"):
            chunks = self.chunker.chunk_content(doc)

        # Verify chunking
        assert len(chunks) > 1, "50K document should produce multiple chunks"

        # Verify no content loss
        reconstructed = ""
        for chunk in chunks:
            reconstructed += chunk["content"]
        assert len(reconstructed) == len(doc), "Content was lost during chunking"

        # Verify chunk metadata
        for i, chunk in enumerate(chunks):
            assert chunk["chunk_number"] == i + 1
            assert chunk["total_chunks"] == len(chunks)
            assert "boundary_type" in chunk
            assert "tokens" in chunk
            assert chunk["tokens"] <= 25000

        self.tracker.get_stats("chunk_50k")

        return chunks

    def test_chunk_75k_document(self):
        """Test chunking of 75K token document"""

        doc = self.generator.generate_markdown_document(75000)

        with self.tracker.measure("chunk_75k"):
            chunks = self.chunker.chunk_content(doc)

        assert len(chunks) >= 3, "75K document should produce at least 3 chunks"

        # Verify boundaries
        for chunk in chunks:
            content = chunk["content"]
            # Should not end mid-word (unless forced)
            if chunk["boundary_type"] != "forced":
                assert not content or content[-1] in " \n\t.!?;:,)]}>\"'" or content.endswith("```"), (
                    f"Chunk ends mid-word: ...{content[-20:]}"
                )

        self.tracker.get_stats("chunk_75k")

        return chunks

    def test_chunk_100k_document(self):
        """Test chunking of 100K+ token document"""

        doc = self.generator.generate_mixed_format_document(100000)

        with self.tracker.measure("chunk_100k"):
            chunks = self.chunker.chunk_content(doc)

        assert len(chunks) >= 5, "100K document should produce at least 5 chunks"

        # Verify memory efficiency (chunks should not duplicate content)
        total_chunk_size = sum(len(chunk["content"]) for chunk in chunks)
        assert total_chunk_size == len(doc), "Chunks contain duplicated or missing content"

        stats = self.tracker.get_stats("chunk_100k")
        assert stats["average"] < 2.0, "100K document should chunk in under 2 seconds"

        return chunks

    def test_natural_boundary_preservation(self):
        """Test that chunks break at natural boundaries"""

        # Create document with clear boundaries
        doc = """# Section One

This is the first paragraph of section one. It contains multiple sentences.
Each sentence should stay together when possible.

This is the second paragraph. It also has multiple sentences.

## Subsection 1.1

Here is a subsection with its own content.

# Section Two

This is section two. It has different content.

## Subsection 2.1

More content here in the subsection.
"""

        # Use small chunk size to force splitting
        small_chunker = EnhancedChunker(max_tokens=50)  # ~200 chars
        chunks = small_chunker.chunk_content(doc)

        # Verify no mid-sentence splits
        for chunk in chunks:
            content = chunk["content"].strip()
            if content and not content.endswith((".", "!", "?", ":", "\n", "#")):
                # Check if it's a header or complete paragraph
                lines = content.split("\n")
                last_line = lines[-1].strip()
                assert last_line.endswith((".", "!", "?", ":")) or last_line.startswith("#"), (
                    f"Chunk doesn't end at sentence boundary: ...{content[-50:]}"
                )

        for _i, chunk in enumerate(chunks):
            pass

    def test_metadata_extraction(self):
        """Test metadata extraction from chunks"""

        doc = """# Main Title

Keywords: testing, chunking, performance

## Introduction

This document tests metadata extraction.

### Details

- Point 1: Important detail
- Point 2: Another detail

## Conclusion

Final thoughts here.
"""

        chunks = self.chunker.chunk_content(doc)

        for chunk in chunks:
            assert "keywords" in chunk
            assert "headers" in chunk
            assert isinstance(chunk["keywords"], list)
            assert isinstance(chunk["headers"], list)

            # First chunk should contain main headers
            if chunk["chunk_number"] == 1:
                header_texts = [h["text"] if isinstance(h, dict) else h for h in chunk["headers"]]
                assert any("Main Title" in text for text in header_texts)

        for chunk in chunks:
            pass

    def test_edge_cases(self):
        """Test edge cases in chunking"""

        edge_docs = self.fixtures.create_edge_case_documents()

        # Test empty document
        chunks = self.chunker.chunk_content(edge_docs["empty"])
        assert len(chunks) == 0 or (len(chunks) == 1 and chunks[0]["content"] == "")

        # Test single line
        chunks = self.chunker.chunk_content(edge_docs["single_line"])
        assert len(chunks) == 1
        assert chunks[0]["content"] == edge_docs["single_line"]

        # Test very long lines
        chunks = self.chunker.chunk_content(edge_docs["long_lines"])
        assert all(chunk["tokens"] <= 20000 for chunk in chunks)

        # Test special characters
        chunks = self.chunker.chunk_content(edge_docs["special_chars"])
        reconstructed = "".join(chunk["content"] for chunk in chunks)
        assert reconstructed == edge_docs["special_chars"]

    def test_performance_metrics(self):
        """Test performance with various document sizes"""

        sizes = [10000, 25000, 50000, 75000, 100000]
        results = []

        for size in sizes:
            doc = self.generator.generate_markdown_document(size)

            with self.tracker.measure(f"perf_{size}"):
                chunks = self.chunker.chunk_content(doc)

            stats = self.tracker.get_stats(f"perf_{size}")
            results.append(
                {
                    "size": size,
                    "chunks": len(chunks),
                    "time": stats["average"],
                    "tokens_per_second": size / stats["average"],
                }
            )

        # Verify performance scales linearly
        # Time should not increase exponentially with size
        time_ratio = results[-1]["time"] / results[0]["time"]
        size_ratio = results[-1]["size"] / results[0]["size"]
        assert time_ratio < size_ratio * 1.5, "Performance doesn't scale linearly"

    def test_chunk_consistency(self):
        """Test that chunking is consistent across runs"""

        doc = self.generator.generate_markdown_document(30000)

        # Chunk the same document multiple times
        results = []
        for i in range(3):
            chunks = self.chunker.chunk_content(doc)
            results.append(chunks)

        # Verify all runs produce identical chunks
        for i in range(1, len(results)):
            assert len(results[i]) == len(results[0]), "Different number of chunks on repeated runs"
            for j, (chunk1, chunk2) in enumerate(zip(results[0], results[i])):
                assert chunk1["content"] == chunk2["content"], f"Chunk {j} differs between runs"
                assert chunk1["boundary_type"] == chunk2["boundary_type"], f"Boundary type differs for chunk {j}"

    def test_combined_small_documents(self):
        """Test combining small documents into single chunks"""

        # Create several small documents
        small_docs = ["# Doc 1\nShort content.", "# Doc 2\nAnother short piece.", "# Doc 3\nThird small document."]

        # Combine and chunk
        combined = "\n\n---\n\n".join(small_docs)
        chunks = self.chunker.chunk_content(combined)

        # Should produce single chunk for small combined size
        assert len(chunks) == 1, "Small documents should combine into single chunk"
        assert chunks[0]["content"] == combined


class TestIntegrationWithContext:
    """Test integration with context.py tools"""

    @pytest.mark.asyncio
    async def test_vision_document_workflow(self):
        """Test complete vision document workflow"""

        # Create a temporary vision directory
        with tempfile.TemporaryDirectory() as tmpdir:
            vision_dir = Path(tmpdir) / "Vision"
            vision_dir.mkdir()

            # Create test vision documents
            generator = TestDocumentGenerator()

            # Create multiple vision files
            files = {
                "VISION_OVERVIEW.md": generator.generate_markdown_document(15000),
                "TECHNICAL_SPEC.md": generator.generate_markdown_document(25000),
                "ROADMAP.md": generator.generate_markdown_document(20000),
            }

            for filename, content in files.items():
                (vision_dir / filename).write_text(content)

            # Test would normally call get_vision() here
            # But we're testing the chunking directly
            chunker = EnhancedChunker()

            # Combine all files as context.py would
            full_content = "\n\n---\n\n".join([f"# {filename}\n\n{content}" for filename, content in files.items()])

            chunks = chunker.chunk_content(full_content)

            # Verify chunking
            assert len(chunks) >= 3, "Combined vision documents should produce multiple chunks"

            # Verify metadata
            for chunk in chunks:
                assert chunk["chunk_number"] <= chunk["total_chunks"]
                assert chunk["tokens"] <= 25000

            # Verify chunk retrieval (simulating get_vision(part=N))
            for i in range(1, len(chunks) + 1):
                chunk = chunks[i - 1]
                assert chunk["chunk_number"] == i


def run_all_tests():
    """Run all tests and generate report"""

    # Run tests
    test_actual = TestActualChunking()
    test_actual.setup_method()

    try:
        # Basic functionality tests
        test_actual.test_token_estimation()

        # Document size tests
        test_actual.test_chunk_50k_document()
        test_actual.test_chunk_75k_document()
        test_actual.test_chunk_100k_document()

        # Quality tests
        test_actual.test_natural_boundary_preservation()
        test_actual.test_metadata_extraction()
        test_actual.test_edge_cases()

        # Performance tests
        test_actual.test_performance_metrics()
        test_actual.test_chunk_consistency()
        test_actual.test_combined_small_documents()

        # Integration test (async)
        test_integration = TestIntegrationWithContext()
        asyncio.run(test_integration.test_vision_document_workflow())

        # Generate summary

        return True

    except AssertionError:
        return False
    except Exception:
        import traceback

        traceback.print_exc()
        return False


if __name__ == "__main__":
    success = run_all_tests()
    # sys.exit(0 if success else 1)  # Commented for pytest
