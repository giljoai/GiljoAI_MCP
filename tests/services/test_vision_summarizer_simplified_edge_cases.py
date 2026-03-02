"""
Test suite for simplified VisionSummarizer — edge cases, integration, and validation.

Tests cover:
- Small and large document handling
- Required field validation
- Empty input handling
- Database integration placeholders
- Unicode and boundary edge cases

Split from test_vision_summarizer_simplified.py during file reorganization.

Coverage Target: >90%

Updated Handover 0731: Migrated from dict returns to typed SummarizeMultiLevelResult.
"""

import pytest

from src.giljo_mcp.schemas.service_responses import SummarizeMultiLevelResult
from src.giljo_mcp.services.vision_summarizer import VisionDocumentSummarizer

from tests.services.conftest import generate_realistic_document


# ============================================================================
# UNIT TESTS - Document Handling and Validation
# ============================================================================


class TestSimplifiedSummarizationValidation:
    """Tests for document handling, field validation, and input edge cases."""

    def test_small_document_handling(self):
        """
        Small documents (<3K tokens) should be handled gracefully.

        Even for small documents:
        - Light should be shortest
        - Medium should be longer than light
        - No errors should occur
        """
        summarizer = VisionDocumentSummarizer()
        small_text = generate_realistic_document(tokens=2000)

        result = summarizer.summarize_multi_level(small_text)
        assert isinstance(result, SummarizeMultiLevelResult)

        # Verify hierarchy maintained even for small docs
        assert result.light.tokens <= result.medium.tokens, (
            "Light should not be longer than medium, even for small documents"
        )

        # Verify summaries don't exceed original
        assert result.light.tokens <= result.original_tokens
        assert result.medium.tokens <= result.original_tokens

    def test_large_document_performance(self):
        """
        Large documents (50K tokens) should process in reasonable time.

        Performance requirement: <15 seconds for 2-level summarization
        of 50K token document.
        """
        import time

        summarizer = VisionDocumentSummarizer()
        large_text = generate_realistic_document(tokens=50000)

        start = time.time()
        result = summarizer.summarize_multi_level(large_text)
        elapsed = time.time() - start

        assert isinstance(result, SummarizeMultiLevelResult)
        # Should complete in <15 seconds
        assert elapsed < 15.0, f"Summarization took {elapsed:.2f}s, exceeds 15s requirement for 50K tokens"

        # Verify processing time is tracked
        assert result.processing_time_ms > 0
        assert result.processing_time_ms < 15000

    def test_each_level_has_required_fields(self):
        """
        Each summary level must have summary, tokens, and sentences fields.

        This verifies the data structure returned by summarize_multi_level()
        matches the expected format.
        """
        summarizer = VisionDocumentSummarizer()
        text = generate_realistic_document(tokens=10000)

        result = summarizer.summarize_multi_level(text)

        assert isinstance(result, SummarizeMultiLevelResult)

        # Check both levels have required typed fields
        for level_name in ["light", "medium"]:
            level_result = getattr(result, level_name)

            # Verify field types
            assert isinstance(level_result.summary, str), f"{level_name} summary should be string"
            assert isinstance(level_result.tokens, int), f"{level_name} tokens should be int"
            assert isinstance(level_result.sentences, int), f"{level_name} sentences should be int"

            # Verify non-empty
            assert len(level_result.summary) > 0, f"{level_name} summary should not be empty"
            assert level_result.tokens > 0, f"{level_name} tokens should be > 0"
            assert level_result.sentences > 0, f"{level_name} sentences should be > 0"

    def test_empty_input_handling(self):
        """
        Empty or whitespace-only input should be handled gracefully.

        Should return empty summaries without errors.
        """
        summarizer = VisionDocumentSummarizer()

        # Test empty string
        result = summarizer.summarize_multi_level("")
        assert isinstance(result, SummarizeMultiLevelResult)

        assert result.original_tokens == 0

        # Summaries should be empty or minimal
        assert result.light.tokens == 0 or result.light.summary == ""
        assert result.medium.tokens == 0 or result.medium.summary == ""


# ============================================================================
# INTEGRATION TESTS - Database Storage
# ============================================================================


# ============================================================================
# EDGE CASES
# ============================================================================


class TestEdgeCases:
    """Edge case testing for robustness."""

    def test_single_sentence_document(self):
        """Single sentence should be handled without errors."""
        summarizer = VisionDocumentSummarizer()
        single_sentence = "This is a single sentence document for testing purposes."

        result = summarizer.summarize_multi_level(single_sentence)
        assert isinstance(result, SummarizeMultiLevelResult)

        # Both summaries should contain something (even if same as original)
        assert len(result.light.summary) > 0
        assert len(result.medium.summary) > 0

    def test_no_periods_in_text(self):
        """Text without sentence boundaries should be handled gracefully."""
        summarizer = VisionDocumentSummarizer()

        # Long text without periods
        no_periods = " ".join(["word"] * 1000)

        result = summarizer.summarize_multi_level(no_periods)
        assert isinstance(result, SummarizeMultiLevelResult)

    def test_unicode_content(self):
        """Unicode characters should be handled correctly."""
        summarizer = VisionDocumentSummarizer()

        unicode_text = (
            """
        The system supports internationalization with Unicode characters.
        测试中文字符处理能力。
        Тестирование кириллических символов.
        Testing emoji support: 🚀 💻 📊
        """
            * 100
        )  # Repeat to get reasonable token count

        result = summarizer.summarize_multi_level(unicode_text)
        assert isinstance(result, SummarizeMultiLevelResult)

        # Should handle Unicode without errors
        assert result.original_tokens > 0
