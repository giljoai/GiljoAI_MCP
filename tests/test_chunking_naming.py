"""
Test suite for chunking system naming patterns.
Verifies consistency in chunk_number, total_chunks, and part naming.
"""

import sys
from pathlib import Path


# Add src to path
sys.path.insert(0, str(Path(__file__).parent.parent))

from src.giljo_mcp.tools.chunking import EnhancedChunker


def test_single_document_naming():
    """Test naming patterns for single document chunking"""

    chunker = EnhancedChunker(max_tokens=100)

    # Create test content that will require multiple chunks
    content = "Test content. " * 200  # ~2800 chars, ~560 tokens

    chunks = chunker.chunk_content(content, "test_doc")

    # Verify naming patterns
    tests_passed = True

    # Check chunk_number sequence
    for i, chunk in enumerate(chunks, 1):
        if chunk["chunk_number"] != i:
            tests_passed = False
        else:
            pass

    # Check total_chunks consistency
    total = chunks[0]["total_chunks"] if chunks else 0
    for chunk in chunks:
        if chunk["total_chunks"] != total:
            tests_passed = False

    if tests_passed and chunks:
        pass

    # Check document_name
    for chunk in chunks:
        if chunk["document_name"] != "test_doc":
            tests_passed = False

    if tests_passed:
        pass

    return tests_passed


def test_multiple_documents_naming():
    """Test naming patterns for multiple document chunking"""

    chunker = EnhancedChunker(max_tokens=100)

    # Create test documents
    documents = [
        {"name": "doc1.md", "content": "Content 1. " * 50},
        {"name": "doc2.md", "content": "Content 2. " * 50},
        {"name": "doc3.md", "content": "Content 3. " * 200},  # Large doc
    ]

    chunks = chunker.chunk_multiple_documents(documents)

    tests_passed = True

    # Check sequential numbering after renumbering
    for i, chunk in enumerate(chunks, 1):
        if chunk["chunk_number"] != i:
            tests_passed = False

    if tests_passed:
        pass

    # Check total_chunks consistency
    if chunks:
        total = len(chunks)
        for chunk in chunks:
            if chunk["total_chunks"] != total:
                tests_passed = False
                break
        else:
            pass

    # Check document_name patterns
    doc_names = {chunk["document_name"] for chunk in chunks}

    # Should have "combined" for small docs and "doc3.md" for large doc
    if not doc_names.issubset({"combined", "doc1.md", "doc2.md", "doc3.md"}):
        tests_passed = False
    else:
        pass

    return tests_passed


def test_naming_fields_presence():
    """Test that all required naming fields are present"""

    chunker = EnhancedChunker(max_tokens=100)
    content = "Test content. " * 100

    chunks = chunker.chunk_content(content, "test")

    required_fields = [
        "chunk_number",
        "total_chunks",
        "document_name",
        "content",
        "tokens",
        "char_start",
        "char_end",
        "boundary_type",
        "keywords",
        "headers",
    ]

    tests_passed = True

    if not chunks:
        return False

    for field in required_fields:
        if field in chunks[0]:
            pass
        else:
            tests_passed = False

    return tests_passed


def test_part_vs_chunk_naming():
    """Verify consistent use of 'chunk' vs 'part' terminology"""

    chunker = EnhancedChunker()
    content = "Test. " * 500
    chunks = chunker.chunk_content(content)

    # Check that we use 'chunk' not 'part' in field names
    if chunks:
        chunk = chunks[0]

        # Should use 'chunk_number' not 'part_number'
        has_chunk_number = "chunk_number" in chunk
        has_part_number = "part_number" in chunk

        if has_chunk_number and not has_part_number:
            pass
        elif has_part_number:
            return False
        else:
            return False

        # Should use 'total_chunks' not 'total_parts'
        has_total_chunks = "total_chunks" in chunk
        has_total_parts = "total_parts" in chunk

        if has_total_chunks and not has_total_parts:
            pass
        elif has_total_parts:
            return False
        else:
            return False

        return True

    return False


def test_metadata_consistency():
    """Test metadata field naming consistency"""

    chunker = EnhancedChunker(max_tokens=50)

    # Test with different content sizes
    test_cases = [
        ("small", "Small content."),
        ("medium", "Medium content. " * 50),
        ("large", "Large content. " * 200),
    ]

    all_field_sets = []

    for name, content in test_cases:
        chunks = chunker.chunk_content(content, name)
        if chunks:
            fields = set(chunks[0].keys())
            all_field_sets.append(fields)

    # All chunks should have same field structure
    if all_field_sets:
        first_set = all_field_sets[0]
        all_same = all(fields == first_set for fields in all_field_sets)

        if all_same:
            return True
        for _i, fields in enumerate(all_field_sets):
            diff = fields.symmetric_difference(first_set)
            if diff:
                pass
        return False

    return False


def run_all_tests():
    """Run all chunking naming tests"""

    results = []

    # Run tests
    results.append(("Single document naming", test_single_document_naming()))
    results.append(("Multiple documents naming", test_multiple_documents_naming()))
    results.append(("Required fields presence", test_naming_fields_presence()))
    results.append(("Chunk vs Part terminology", test_part_vs_chunk_naming()))
    results.append(("Metadata consistency", test_metadata_consistency()))

    # Summary

    passed = 0
    failed = 0

    for _name, result in results:
        if result:
            passed += 1
        else:
            failed += 1

    return failed == 0


if __name__ == "__main__":
    success = run_all_tests()
    # sys.exit(0 if success else 1)  # Commented for pytest
