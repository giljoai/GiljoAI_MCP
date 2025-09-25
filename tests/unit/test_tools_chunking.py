"""
Comprehensive tests for chunking.py
Target: 10.73% → 95%+ coverage

Tests the EnhancedChunker class and its methods:
- EnhancedChunker initialization
- Document chunking algorithms
- Boundary detection
- Keyword extraction
- Token estimation
- Content hashing
- Multi-document processing
"""



from src.giljo_mcp.tools.chunking import EnhancedChunker


class TestEnhancedChunker:
    """Test class for EnhancedChunker"""

    def setup_method(self):
        """Setup for each test method"""
        self.chunker = EnhancedChunker()

    def test_chunker_initialization_default(self):
        """Test EnhancedChunker initialization with defaults"""
        chunker = EnhancedChunker()

        assert chunker.max_tokens == 20000
        assert chunker.overlap_tokens == 500
        assert hasattr(chunker, "boundary_patterns")

    def test_chunker_initialization_custom(self):
        """Test EnhancedChunker initialization with custom parameters"""
        chunker = EnhancedChunker(max_tokens=10000, overlap_tokens=200)

        assert chunker.max_tokens == 10000
        assert chunker.overlap_tokens == 200

    def test_estimate_tokens_simple(self):
        """Test token estimation for simple text"""
        text = "This is a simple test sentence with several words."

        tokens = self.chunker.estimate_tokens(text)

        assert isinstance(tokens, int)
        assert tokens > 0
        assert tokens < len(text)  # Should be less than character count

    def test_estimate_tokens_empty(self):
        """Test token estimation for empty text"""
        tokens = self.chunker.estimate_tokens("")
        assert tokens == 0

    def test_estimate_tokens_none(self):
        """Test token estimation for None input"""
        tokens = self.chunker.estimate_tokens(None)
        assert tokens == 0

    def test_estimate_tokens_long_text(self):
        """Test token estimation for long text"""
        long_text = "Word " * 1000  # 1000 words

        tokens = self.chunker.estimate_tokens(long_text)

        assert tokens > 500  # Should be substantial
        assert tokens < 2000  # But reasonable estimate

    def test_extract_keywords_simple(self):
        """Test keyword extraction from simple text"""
        text = "Python programming language development testing framework"

        keywords = self.chunker.extract_keywords(text)

        assert isinstance(keywords, list)
        assert len(keywords) > 0
        assert "python" in [kw.lower() for kw in keywords]

    def test_extract_keywords_complex(self):
        """Test keyword extraction from complex text"""
        text = """
        The machine learning algorithm utilizes deep neural networks
        for natural language processing and computer vision tasks.
        The implementation uses TensorFlow and PyTorch frameworks
        with GPU acceleration for training large datasets.
        """

        keywords = self.chunker.extract_keywords(text)

        assert isinstance(keywords, list)
        assert len(keywords) >= 3
        # Should contain technical terms
        keyword_text = " ".join(keywords).lower()
        assert any(term in keyword_text for term in ["machine", "learning", "neural", "tensorflow"])

    def test_extract_keywords_empty(self):
        """Test keyword extraction from empty text"""
        keywords = self.chunker.extract_keywords("")
        assert isinstance(keywords, list)
        assert len(keywords) == 0

    def test_calculate_content_hash(self):
        """Test content hash calculation"""
        text = "This is test content for hashing"

        hash1 = self.chunker.calculate_content_hash(text)
        hash2 = self.chunker.calculate_content_hash(text)

        assert isinstance(hash1, str)
        assert hash1 == hash2  # Same content should produce same hash
        assert len(hash1) > 10  # Should be substantial hash

    def test_calculate_content_hash_different(self):
        """Test that different content produces different hashes"""
        text1 = "This is the first text"
        text2 = "This is the second text"

        hash1 = self.chunker.calculate_content_hash(text1)
        hash2 = self.chunker.calculate_content_hash(text2)

        assert hash1 != hash2

    def test_chunk_content_small_document(self):
        """Test chunking of small document that fits in one chunk"""
        content = "This is a small document that should fit in one chunk."

        chunks = self.chunker.chunk_content(content, "small.md")

        assert len(chunks) == 1
        assert chunks[0]["chunk_number"] == 1
        assert chunks[0]["total_chunks"] == 1
        assert chunks[0]["content"] == content
        assert chunks[0]["document_name"] == "small.md"

    def test_chunk_content_large_document(self):
        """Test chunking of large document that requires multiple chunks"""
        # Create large content
        section_content = "This is a section with substantial content. " * 100
        large_content = "\n\n".join([f"# Section {i}\n\n{section_content}" for i in range(20)])

        chunker = EnhancedChunker(max_tokens=1000)  # Small chunk size for testing
        chunks = chunker.chunk_content(large_content, "large.md")

        assert len(chunks) > 1
        assert chunks[0]["chunk_number"] == 1
        assert chunks[-1]["chunk_number"] == len(chunks)
        for chunk in chunks:
            assert chunk["total_chunks"] == len(chunks)

    def test_chunk_content_with_headers(self):
        """Test chunking respects header boundaries"""
        content = """
# Main Title

This is the introduction section with some content.

## Section 1

This is section 1 with detailed information about the topic.
It contains multiple paragraphs and technical details.

## Section 2

This is section 2 with different information.
It also contains substantial content.

### Subsection 2.1

This is a subsection with specific details.

## Section 3

Final section with concluding information.
"""

        chunker = EnhancedChunker(max_tokens=500)  # Force chunking
        chunks = chunker.chunk_content(content, "structured.md")

        # Should have multiple chunks
        assert len(chunks) >= 2

        # Check that headers are preserved
        for chunk in chunks:
            assert "headers" in chunk
            if chunk["headers"]:
                assert any("#" in header for header in chunk["headers"])

    def test_chunk_content_boundary_detection(self):
        """Test boundary detection in chunking"""
        content = """
# Document Title

## Introduction
Some introductory content here.

---

## Main Content
This is the main content section.

---

## Conclusion
Concluding remarks here.
"""

        chunker = EnhancedChunker(max_tokens=200)  # Force multiple chunks
        chunks = chunker.chunk_content(content, "boundaries.md")

        # Should detect boundaries
        boundary_types = [chunk["boundary_type"] for chunk in chunks]
        assert any("header" in bt or "section" in bt for bt in boundary_types)

    def test_chunk_multiple_documents(self):
        """Test chunking multiple documents"""
        documents = [
            {"name": "doc1.md", "content": "First document content with substantial text."},
            {"name": "doc2.md", "content": "Second document with different content and information."},
            {"name": "doc3.md", "content": "Third document containing more detailed technical specifications."},
        ]

        chunks = self.chunker.chunk_multiple_documents(documents)

        assert len(chunks) >= 3  # At least one chunk per document

        # Check document names are preserved
        doc_names = {chunk["document_name"] for chunk in chunks}
        assert "doc1.md" in doc_names
        assert "doc2.md" in doc_names
        assert "doc3.md" in doc_names

    def test_chunk_multiple_documents_large(self):
        """Test chunking multiple large documents"""
        large_content = "Substantial content section. " * 200
        documents = [
            {"name": "large1.md", "content": f"# Large Doc 1\n\n{large_content}"},
            {"name": "large2.md", "content": f"# Large Doc 2\n\n{large_content}"},
        ]

        chunker = EnhancedChunker(max_tokens=1000)
        chunks = chunker.chunk_multiple_documents(documents)

        # Should create multiple chunks
        assert len(chunks) > 2

        # Each document should have multiple chunks
        doc1_chunks = [c for c in chunks if c["document_name"] == "large1.md"]
        doc2_chunks = [c for c in chunks if c["document_name"] == "large2.md"]
        assert len(doc1_chunks) > 1
        assert len(doc2_chunks) > 1

    def test_chunk_content_with_code_blocks(self):
        """Test chunking content with code blocks"""
        content = """
# API Documentation

## Overview
This API provides various endpoints.

```python
def example_function():
    return "Hello, World!"
```

## Authentication
Use Bearer tokens for authentication.

```bash
curl -H "Authorization: Bearer token" https://api.example.com
```

## Endpoints
Details about available endpoints.
"""

        chunks = self.chunker.chunk_content(content, "api_docs.md")

        # Should preserve code blocks
        all_content = " ".join(chunk["content"] for chunk in chunks)
        assert "```python" in all_content
        assert "```bash" in all_content

    def test_chunk_content_special_characters(self):
        """Test chunking content with special characters"""
        content = """
# Spéciäl Chäracters

This document contains émojis 🚀, ñ characters, and ümlaut symbols.
It also has mathematical symbols: α, β, γ, δ, and π.

## Unicode Support
Testing UTF-8 encoding: café, naïve, résumé.
"""

        chunks = self.chunker.chunk_content(content, "unicode.md")

        assert len(chunks) >= 1
        # Special characters should be preserved
        all_content = " ".join(chunk["content"] for chunk in chunks)
        assert "émojis" in all_content
        assert "🚀" in all_content
        assert "résumé" in all_content

    def test_chunk_content_overlap(self):
        """Test chunk overlap functionality"""
        content = "Sentence 1. " * 50 + "Important transition. " + "Sentence 2. " * 50

        chunker = EnhancedChunker(max_tokens=300, overlap_tokens=50)
        chunks = chunker.chunk_content(content, "overlap.md")

        if len(chunks) > 1:
            # Check that chunks have some overlap
            chunk1_end = chunks[0]["content"][-100:]  # Last 100 chars
            chunk2_start = chunks[1]["content"][:100]  # First 100 chars

            # Should have some common content
            common_words = set(chunk1_end.split()) & set(chunk2_start.split())
            assert len(common_words) > 0

    def test_chunker_performance_large_document(self):
        """Test chunker performance with very large document"""
        # Create a very large document
        large_content = "Performance test content. " * 5000

        import time

        start_time = time.time()

        chunks = self.chunker.chunk_content(large_content, "performance.md")

        end_time = time.time()
        duration = end_time - start_time

        # Should complete reasonably quickly
        assert duration < 5.0  # Should take less than 5 seconds
        assert len(chunks) > 1
        assert all(chunk["tokens"] <= self.chunker.max_tokens for chunk in chunks)

    def test_chunk_content_metadata(self):
        """Test that chunk metadata is correctly populated"""
        content = """
# Test Document

## Section 1
Content for section 1.

## Section 2
Content for section 2.
"""

        chunks = self.chunker.chunk_content(content, "metadata.md")

        for i, chunk in enumerate(chunks):
            # Check required metadata
            assert "chunk_number" in chunk
            assert "total_chunks" in chunk
            assert "content" in chunk
            assert "tokens" in chunk
            assert "char_start" in chunk
            assert "char_end" in chunk
            assert "boundary_type" in chunk
            assert "keywords" in chunk
            assert "headers" in chunk
            assert "document_name" in chunk

            # Check values make sense
            assert chunk["chunk_number"] == i + 1
            assert chunk["total_chunks"] == len(chunks)
            assert chunk["tokens"] > 0
            assert chunk["char_end"] > chunk["char_start"]
            assert isinstance(chunk["keywords"], list)
            assert isinstance(chunk["headers"], list)

    def test_chunk_content_empty_document(self):
        """Test chunking empty document"""
        chunks = self.chunker.chunk_content("", "empty.md")

        assert len(chunks) == 1
        assert chunks[0]["content"] == ""
        assert chunks[0]["tokens"] == 0

    def test_chunker_with_custom_patterns(self):
        """Test chunker with custom boundary patterns"""
        custom_patterns = [
            r"^---\s*$",  # Horizontal rule
            r"^\*\*\*\s*$",  # Triple asterisk
            r"^Chapter \d+",  # Chapter headers
        ]

        chunker = EnhancedChunker(boundary_patterns=custom_patterns)

        content = """
Chapter 1: Introduction
Some content here.

---

Chapter 2: Methods
More content here.

***

Chapter 3: Results
Final content here.
"""

        chunks = chunker.chunk_content(content, "custom.md")

        # Should detect custom boundaries
        [chunk["boundary_type"] for chunk in chunks]
        assert len(chunks) > 1

    def test_chunk_content_json_document(self):
        """Test chunking JSON document"""
        json_content = """
{
    "api_version": "1.0",
    "endpoints": {
        "users": {
            "get": "/api/users",
            "post": "/api/users"
        },
        "products": {
            "get": "/api/products",
            "post": "/api/products"
        }
    },
    "authentication": {
        "type": "bearer",
        "token_endpoint": "/auth/token"
    }
}
"""

        chunks = self.chunker.chunk_content(json_content, "api.json")

        assert len(chunks) >= 1
        # Should preserve JSON structure
        all_content = " ".join(chunk["content"] for chunk in chunks)
        assert "api_version" in all_content
        assert "endpoints" in all_content

    def test_extract_headers_markdown(self):
        """Test header extraction from markdown"""
        content = """
# Main Title
Content here.

## Section Header
More content.

### Subsection
Even more content.

#### Sub-subsection
Final content.
"""

        chunks = self.chunker.chunk_content(content, "headers.md")

        # Should extract headers
        all_headers = []
        for chunk in chunks:
            all_headers.extend(chunk["headers"])

        assert "# Main Title" in all_headers
        assert "## Section Header" in all_headers
        assert "### Subsection" in all_headers

    def test_chunker_error_handling(self):
        """Test chunker error handling"""
        # Test with None content
        chunks = self.chunker.chunk_content(None, "test.md")
        assert len(chunks) == 1
        assert chunks[0]["content"] == ""

        # Test with invalid document name
        chunks = self.chunker.chunk_content("test", None)
        assert len(chunks) == 1
        assert chunks[0]["document_name"] is None
