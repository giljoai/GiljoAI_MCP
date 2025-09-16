"""
Test suite for chunking system naming patterns.
Verifies consistency in chunk_number, total_chunks, and part naming.
"""
import sys
from pathlib import Path
import json

# Add src to path
sys.path.insert(0, str(Path(__file__).parent.parent / "src"))

from giljo_mcp.tools.chunking import EnhancedChunker


def test_single_document_naming():
    """Test naming patterns for single document chunking"""
    print("Testing single document naming patterns:")
    print("-" * 50)
    
    chunker = EnhancedChunker(max_tokens=100)
    
    # Create test content that will require multiple chunks
    content = "Test content. " * 200  # ~2800 chars, ~560 tokens
    
    chunks = chunker.chunk_content(content, "test_doc")
    
    # Verify naming patterns
    tests_passed = True
    
    # Check chunk_number sequence
    for i, chunk in enumerate(chunks, 1):
        if chunk['chunk_number'] != i:
            print(f"[FAIL] Chunk {i} has chunk_number={chunk['chunk_number']}")
            tests_passed = False
        else:
            print(f"[PASS] Chunk {i} has correct chunk_number")
    
    # Check total_chunks consistency
    total = chunks[0]['total_chunks'] if chunks else 0
    for chunk in chunks:
        if chunk['total_chunks'] != total:
            print(f"[FAIL] Inconsistent total_chunks: {chunk['total_chunks']} != {total}")
            tests_passed = False
    
    if tests_passed and chunks:
        print(f"[PASS] All chunks have consistent total_chunks={total}")
    
    # Check document_name
    for chunk in chunks:
        if chunk['document_name'] != "test_doc":
            print(f"[FAIL] Wrong document_name: {chunk['document_name']}")
            tests_passed = False
    
    if tests_passed:
        print("[PASS] All chunks have correct document_name")
    
    return tests_passed


def test_multiple_documents_naming():
    """Test naming patterns for multiple document chunking"""
    print("\nTesting multiple documents naming patterns:")
    print("-" * 50)
    
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
        if chunk['chunk_number'] != i:
            print(f"[FAIL] Chunk has wrong number: {chunk['chunk_number']} != {i}")
            tests_passed = False
    
    if tests_passed:
        print(f"[PASS] All {len(chunks)} chunks numbered sequentially")
    
    # Check total_chunks consistency
    if chunks:
        total = len(chunks)
        for chunk in chunks:
            if chunk['total_chunks'] != total:
                print(f"[FAIL] Wrong total_chunks: {chunk['total_chunks']} != {total}")
                tests_passed = False
                break
        else:
            print(f"[PASS] All chunks have total_chunks={total}")
    
    # Check document_name patterns
    doc_names = set(chunk['document_name'] for chunk in chunks)
    print(f"[INFO] Document names in chunks: {doc_names}")
    
    # Should have "combined" for small docs and "doc3.md" for large doc
    expected_names = {"combined", "doc3.md"}
    if not doc_names.issubset({"combined", "doc1.md", "doc2.md", "doc3.md"}):
        print(f"[FAIL] Unexpected document names: {doc_names}")
        tests_passed = False
    else:
        print("[PASS] Document names follow expected pattern")
    
    return tests_passed


def test_naming_fields_presence():
    """Test that all required naming fields are present"""
    print("\nTesting required naming fields:")
    print("-" * 50)
    
    chunker = EnhancedChunker(max_tokens=100)
    content = "Test content. " * 100
    
    chunks = chunker.chunk_content(content, "test")
    
    required_fields = [
        'chunk_number',
        'total_chunks',
        'document_name',
        'content',
        'tokens',
        'char_start',
        'char_end',
        'boundary_type',
        'keywords',
        'headers'
    ]
    
    tests_passed = True
    
    if not chunks:
        print("[FAIL] No chunks generated")
        return False
    
    for field in required_fields:
        if field in chunks[0]:
            print(f"[PASS] Field '{field}' present")
        else:
            print(f"[FAIL] Field '{field}' missing")
            tests_passed = False
    
    return tests_passed


def test_part_vs_chunk_naming():
    """Verify consistent use of 'chunk' vs 'part' terminology"""
    print("\nTesting chunk vs part terminology:")
    print("-" * 50)
    
    chunker = EnhancedChunker()
    content = "Test. " * 500
    chunks = chunker.chunk_content(content)
    
    # Check that we use 'chunk' not 'part' in field names
    if chunks:
        chunk = chunks[0]
        
        # Should use 'chunk_number' not 'part_number'
        has_chunk_number = 'chunk_number' in chunk
        has_part_number = 'part_number' in chunk
        
        if has_chunk_number and not has_part_number:
            print("[PASS] Using 'chunk_number' (not 'part_number')")
        elif has_part_number:
            print("[FAIL] Found 'part_number' - should be 'chunk_number'")
            return False
        else:
            print("[FAIL] Missing chunk_number field")
            return False
        
        # Should use 'total_chunks' not 'total_parts'
        has_total_chunks = 'total_chunks' in chunk
        has_total_parts = 'total_parts' in chunk
        
        if has_total_chunks and not has_total_parts:
            print("[PASS] Using 'total_chunks' (not 'total_parts')")
        elif has_total_parts:
            print("[FAIL] Found 'total_parts' - should be 'total_chunks'")
            return False
        else:
            print("[FAIL] Missing total_chunks field")
            return False
        
        return True
    
    print("[FAIL] No chunks generated")
    return False


def test_metadata_consistency():
    """Test metadata field naming consistency"""
    print("\nTesting metadata naming consistency:")
    print("-" * 50)
    
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
            print(f"[INFO] {name}: {len(chunks)} chunks, {len(fields)} fields")
    
    # All chunks should have same field structure
    if all_field_sets:
        first_set = all_field_sets[0]
        all_same = all(fields == first_set for fields in all_field_sets)
        
        if all_same:
            print("[PASS] All content sizes produce consistent field structure")
            return True
        else:
            print("[FAIL] Inconsistent field structure across content sizes")
            for i, fields in enumerate(all_field_sets):
                diff = fields.symmetric_difference(first_set)
                if diff:
                    print(f"  Difference in set {i}: {diff}")
            return False
    
    print("[FAIL] No chunks generated")
    return False


def run_all_tests():
    """Run all chunking naming tests"""
    print("=" * 60)
    print("CHUNKING SYSTEM NAMING PATTERN TESTS")
    print("=" * 60)
    
    results = []
    
    # Run tests
    results.append(("Single document naming", test_single_document_naming()))
    results.append(("Multiple documents naming", test_multiple_documents_naming()))
    results.append(("Required fields presence", test_naming_fields_presence()))
    results.append(("Chunk vs Part terminology", test_part_vs_chunk_naming()))
    results.append(("Metadata consistency", test_metadata_consistency()))
    
    # Summary
    print("\n" + "=" * 60)
    print("TEST SUMMARY")
    print("=" * 60)
    
    passed = 0
    failed = 0
    
    for name, result in results:
        status = "[PASS] PASS" if result else "[FAIL] FAIL"
        print(f"{status}: {name}")
        if result:
            passed += 1
        else:
            failed += 1
    
    print("-" * 60)
    print(f"Total: {passed} passed, {failed} failed")
    
    if failed == 0:
        print("\n[SUCCESS] All chunking naming tests passed!")
        print("Naming patterns are consistent:")
        print("  - Using 'chunk_number' and 'total_chunks' (not 'part')")
        print("  - Sequential numbering maintained")
        print("  - Document names properly tracked")
        print("  - All required metadata fields present")
        return True
    else:
        print(f"\n[WARNING] {failed} test(s) failed")
        print("Review chunking.py for naming inconsistencies")
        return False


if __name__ == "__main__":
    success = run_all_tests()
    sys.exit(0 if success else 1)