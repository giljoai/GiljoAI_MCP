"""
Test suite for VisionDocumentSummarizer - TDD Handover 0345b

This test suite covers Sumy LSA integration for vision document summarization:
- Compression ratio (70-80% target)
- Extractive integrity (no hallucination)
- Performance benchmarks (<5 seconds for 100K tokens)
- Integration with ProductService upload flow
- Setting-based conditional execution

Coverage Target: >90%
"""

import pytest
import time
from unittest.mock import MagicMock, AsyncMock, patch

from src.giljo_mcp.services.vision_summarizer import VisionDocumentSummarizer


# ============================================================================
# FIXTURES
# ============================================================================

@pytest.fixture
def summarizer():
    """Create VisionDocumentSummarizer instance for testing"""
    return VisionDocumentSummarizer(language="english")


def generate_test_document(tokens: int = 1000) -> str:
    """
    Generate a test document with approximately the specified token count.

    Uses repetitive technical content to simulate vision documents.
    Assumes ~4 chars per token for estimation.
    """
    # Sample technical paragraph (~100 tokens, ~400 chars)
    base_paragraph = (
        "The GiljoAI system architecture leverages a multi-agent orchestration "
        "framework built on FastAPI and PostgreSQL. Each agent operates independently "
        "with specialized capabilities including code generation, testing, and "
        "deployment automation. The system employs context prioritization to manage "
        "token budgets efficiently across distributed agent workflows. Vision documents "
        "provide high-level architectural guidance to orchestrators during project "
        "initialization and execution phases."
    )

    # Calculate how many paragraphs needed
    chars_per_paragraph = len(base_paragraph)
    tokens_per_paragraph = chars_per_paragraph // 4
    paragraphs_needed = max(1, tokens // tokens_per_paragraph)

    # Generate document with variation
    paragraphs = []
    for i in range(paragraphs_needed):
        # Add variation to avoid exact duplicates
        variant = base_paragraph.replace("GiljoAI", f"GiljoAI-{i % 10}")
        paragraphs.append(variant)

    return "\n\n".join(paragraphs)


# ============================================================================
# UNIT TESTS - VisionDocumentSummarizer
# ============================================================================

def test_summarizer_achieves_70_percent_compression(summarizer):
    """
    LSA should compress 100K tokens to ~25-30K (70%+ compression).

    CRITICAL: This validates the core value proposition - reducing
    large vision documents to fit within orchestrator context budgets.
    """
    large_text = generate_test_document(tokens=100000)

    result = summarizer.summarize(large_text, target_tokens=25000)

    # Verify result structure
    assert "summary" in result
    assert "original_tokens" in result
    assert "summary_tokens" in result
    assert "compression_ratio" in result
    assert "processing_time_ms" in result

    # Verify compression achieved
    assert result["original_tokens"] >= 95000, "Original token count should be ~100K"
    assert result["summary_tokens"] <= 30000, "Summary should be under 30K tokens"
    assert result["compression_ratio"] >= 0.70, "Should achieve 70%+ compression"

    # Verify summary is not empty
    assert len(result["summary"]) > 0, "Summary should not be empty"


def test_summarizer_preserves_key_sentences(summarizer):
    """
    Extractive summarization must preserve original sentences exactly.

    CRITICAL: This ensures zero hallucination - all sentences in the
    summary come directly from the original document without modification.
    """
    text = (
        "Sentence one provides context. "
        "Sentence two describes architecture. "
        "Sentence three explains implementation. "
        "KEY INSIGHT: This is the most important sentence. "
        "Sentence five adds details. "
        "Sentence six concludes."
    )

    result = summarizer.summarize(text, target_tokens=100)

    # Extract sentences from summary
    summary_sentences = [
        s.strip() + "."
        for s in result["summary"].split(".")
        if s.strip()
    ]

    # Verify every summary sentence exists in original
    for sentence in summary_sentences:
        assert sentence in text or sentence.replace(".", "") in text, (
            f"Summary sentence '{sentence}' not found in original text. "
            "This indicates hallucination - CRITICAL FAILURE."
        )


def test_summarizer_handles_empty_input(summarizer):
    """
    Empty or very short documents should pass through unchanged.

    Edge case: Ensure graceful handling when no summarization is needed.
    """
    # Test empty string
    result = summarizer.summarize("", target_tokens=1000)
    assert result["summary"] == ""
    assert result["original_tokens"] == 0
    assert result["summary_tokens"] == 0
    assert result["compression_ratio"] == 0.0

    # Test very short string
    short_text = "Short sentence."
    result = summarizer.summarize(short_text, target_tokens=1000)
    assert result["summary"] == short_text
    assert result["compression_ratio"] == 0.0  # No compression needed


def test_summarizer_handles_small_documents(summarizer):
    """
    Documents smaller than target_tokens should not be summarized.

    This saves processing time and preserves full context when possible.
    """
    small_text = generate_test_document(tokens=5000)

    result = summarizer.summarize(small_text, target_tokens=25000)

    # Should return original unchanged
    assert result["summary"] == small_text
    assert result["original_tokens"] == result["summary_tokens"]
    assert result["compression_ratio"] == 0.0


def test_processing_time_under_5_seconds(summarizer):
    """
    100K token document should summarize in <5 seconds.

    CRITICAL: Performance requirement ensures real-time upload UX.
    """
    large_text = generate_test_document(tokens=100000)

    start = time.time()
    result = summarizer.summarize(large_text, target_tokens=25000)
    elapsed = time.time() - start

    assert elapsed < 5.0, (
        f"Summarization took {elapsed:.2f}s, exceeds 5s requirement. "
        f"Document: {result['original_tokens']} tokens."
    )

    # Verify processing time is tracked
    assert result["processing_time_ms"] > 0
    assert result["processing_time_ms"] < 5000


def test_token_estimation_accuracy(summarizer):
    """
    Token estimation should be reasonably accurate (within 20%).

    Uses 1 token ≈ 4 chars heuristic.
    """
    text = "a" * 4000  # Exactly 4000 chars = ~1000 tokens

    estimated = summarizer.estimate_tokens(text)

    # Should be close to 1000 tokens (within 20%)
    assert 800 <= estimated <= 1200, f"Estimated {estimated} tokens, expected ~1000"


# ============================================================================
# INTEGRATION TESTS - ProductService Integration
# ============================================================================

@pytest.mark.asyncio
async def test_upload_stores_both_original_and_summary():
    """
    Upload should store both original chunks AND summary text.

    CRITICAL: Auditability requirement - both versions must be retained.

    NOTE: This is a placeholder until ProductService integration is complete.
    Will be fleshed out in Phase 2 after VisionDocumentSummarizer is implemented.
    """
    # TODO: After VisionDocumentSummarizer implementation:
    # 1. Mock settings: vision_summarization_enabled=True
    # 2. Create test product and session
    # 3. Upload 50K token document via ProductService
    # 4. Verify vision_doc.summary_text is populated
    # 5. Verify vision_doc.chunks still contains original
    # 6. Verify vision_doc.is_summarized == True
    # 7. Verify vision_doc.compression_ratio > 0

    pytest.skip("Integration test - implement after VisionDocumentSummarizer is complete")


@pytest.mark.asyncio
async def test_summarization_only_when_enabled():
    """
    Summarization should NOT run if admin setting disabled.

    CRITICAL: Default behavior preserved - feature is opt-in.

    NOTE: This is a placeholder until ProductService integration is complete.
    """
    # TODO: After ProductService integration:
    # 1. Mock settings: vision_summarization_enabled=False
    # 2. Upload 100K token document
    # 3. Verify vision_doc.is_summarized == False
    # 4. Verify vision_doc.summary_text is None
    # 5. Verify original chunks stored normally

    pytest.skip("Integration test - implement after ProductService integration")


@pytest.mark.asyncio
async def test_summarization_only_above_threshold():
    """
    Documents under 30K tokens should skip summarization.

    Preserves full context for smaller documents.

    NOTE: This is a placeholder until ProductService integration is complete.
    """
    # TODO: After ProductService integration:
    # 1. Mock settings: vision_summarization_enabled=True
    # 2. Upload 20K token document (below 30K threshold)
    # 3. Verify vision_doc.is_summarized == False
    # 4. Verify no summarization occurred

    pytest.skip("Integration test - implement after ProductService integration")
