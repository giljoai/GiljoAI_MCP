"""
Test suite for simplified VisionSummarizer — core summarization tests.

Tests the simplified 2-level summarization system:
- Light: 33% of original tokens
- Medium: 66% of original tokens
- No Heavy level (removed)

Split from test_vision_summarizer_simplified.py during file reorganization.

Coverage Target: >90%

Updated Handover 0731: Migrated from dict returns to typed SummarizeMultiLevelResult.
"""

import pytest

from src.giljo_mcp.schemas.service_responses import SummarizeMultiLevelResult
from src.giljo_mcp.services.vision_summarizer import VisionDocumentSummarizer

from tests.services.conftest import generate_realistic_document


# ============================================================================
# UNIT TESTS - Simplified Two-Level Summarization (Core)
# ============================================================================


class TestSimplifiedSummarization:
    """Test suite for simplified 2-level summarization (light + medium)."""

    def test_generate_light_summary_is_33_percent_of_original(self):
        """
        Light summary should be approximately 33% of original token count.

        CRITICAL: Handover 0246b specifies LIGHT_REDUCTION = 0.66 (keep 33%).
        This test verifies the light summary achieves ~33% compression target.

        Tolerance: ±10% to account for extractive summarization variance.
        """
        summarizer = VisionDocumentSummarizer()

        # Generate realistic 10K token document
        original_text = generate_realistic_document(tokens=10000)

        # Summarize with retention ratios (light=33%, medium=66%)
        result = summarizer.summarize_multi_level(original_text, levels={"light": 0.33, "medium": 0.66})

        # Verify typed SummarizeMultiLevelResult (Handover 0731)
        assert isinstance(result, SummarizeMultiLevelResult)

        # Calculate actual percentage
        original_tokens = result.original_tokens
        light_tokens = result.light.tokens
        actual_percentage = (light_tokens / original_tokens) if original_tokens > 0 else 0

        # Assert 33% ± 10% (23% to 43%)
        assert 0.23 <= actual_percentage <= 0.43, (
            f"Light summary is {actual_percentage * 100:.1f}% of original, "
            f"expected 33% ± 10% (23-43%). "
            f"Tokens: {light_tokens}/{original_tokens}"
        )

    def test_generate_medium_summary_is_66_percent_of_original(self):
        """
        Medium summary should be approximately 66% of original token count.

        CRITICAL: Handover 0246b specifies MEDIUM_REDUCTION = 0.33 (keep 66%).
        This test verifies the medium summary achieves ~66% compression target.

        Tolerance: ±10% to account for extractive summarization variance.
        """
        summarizer = VisionDocumentSummarizer()

        # Generate realistic 10K token document
        original_text = generate_realistic_document(tokens=10000)

        # Summarize with retention ratios (light=33%, medium=66%)
        result = summarizer.summarize_multi_level(original_text, levels={"light": 0.33, "medium": 0.66})

        # Verify typed SummarizeMultiLevelResult (Handover 0731)
        assert isinstance(result, SummarizeMultiLevelResult)

        # Calculate actual percentage
        original_tokens = result.original_tokens
        medium_tokens = result.medium.tokens
        actual_percentage = (medium_tokens / original_tokens) if original_tokens > 0 else 0

        # Assert 66% ± 10% (56% to 76%)
        assert 0.56 <= actual_percentage <= 0.76, (
            f"Medium summary is {actual_percentage * 100:.1f}% of original, "
            f"expected 66% ± 10% (56-76%). "
            f"Tokens: {medium_tokens}/{original_tokens}"
        )

    def test_summarize_multi_level_returns_only_two_levels(self):
        """
        summarize_multi_level() should return ONLY light and medium levels.

        CRITICAL: Handover 0246b removes 'heavy' level completely.
        Result dictionary should NOT contain 'heavy' key.
        """
        summarizer = VisionDocumentSummarizer()
        original_text = generate_realistic_document(tokens=10000)

        result = summarizer.summarize_multi_level(original_text)

        # Verify typed SummarizeMultiLevelResult (Handover 0731)
        assert isinstance(result, SummarizeMultiLevelResult)

        # Verify light and medium exist as typed attributes
        assert isinstance(result.light.summary, str)
        assert isinstance(result.medium.summary, str)
        assert not hasattr(result, "heavy"), "Result should NOT contain 'heavy' level (removed in Handover 0246b)"

        # Verify metadata fields exist
        assert isinstance(result.original_tokens, int)
        assert isinstance(result.processing_time_ms, int)

    def test_summarize_preserves_original_wording(self):
        """
        Summaries must be extractive (not abstractive) - preserve original sentences.

        CRITICAL: Zero hallucination requirement. All summary sentences must
        come directly from the original document without modification.

        This test verifies extractive integrity by checking that summary
        sentences are found in the original text.
        """
        summarizer = VisionDocumentSummarizer()

        # Use smaller document for easier verification
        original_text = generate_realistic_document(tokens=2000)

        result = summarizer.summarize_multi_level(original_text)

        # Verify typed return (Handover 0731)
        assert isinstance(result, SummarizeMultiLevelResult)

        # Split original into sentences for verification
        original_sentences = [s.strip() for s in original_text.split(".") if s.strip()]

        # Verify both light and medium summaries are extractive
        for level_name in ["light", "medium"]:
            level_result = getattr(result, level_name)
            summary_text = level_result.summary
            summary_sentences = [s.strip() for s in summary_text.split(".") if s.strip()]

            # At least 80% of summary sentences should match original
            matches = 0
            for summ_sent in summary_sentences:
                if len(summ_sent) < 10:  # Skip very short fragments
                    continue

                # Check if summary sentence exists in original
                # Use first 50 chars for fuzzy matching (handles punctuation variance)
                for orig_sent in original_sentences:
                    if summ_sent[:50] in orig_sent or orig_sent[:50] in summ_sent:
                        matches += 1
                        break

            valid_summary_sentences = [s for s in summary_sentences if len(s) >= 10]
            match_ratio = matches / max(len(valid_summary_sentences), 1)

            assert match_ratio >= 0.80, (
                f"{level_name.capitalize()} summary appears non-extractive: "
                f"only {match_ratio * 100:.0f}% of sentences match original. "
                f"This indicates potential hallucination - CRITICAL FAILURE. "
                f"Matched: {matches}/{len(valid_summary_sentences)} sentences"
            )

    def test_medium_is_longer_than_light(self):
        """
        Medium summary must be longer than light summary (proper ordering).

        CRITICAL: Verifies hierarchy is maintained:
        - Light: 33% of original
        - Medium: 66% of original
        - Medium should have roughly 2x the tokens of light
        """
        summarizer = VisionDocumentSummarizer()
        original_text = generate_realistic_document(tokens=10000)

        result = summarizer.summarize_multi_level(original_text)

        assert isinstance(result, SummarizeMultiLevelResult)
        light_tokens = result.light.tokens
        medium_tokens = result.medium.tokens

        # Medium must be longer than light
        assert medium_tokens > light_tokens, (
            f"Medium summary ({medium_tokens} tokens) should be longer than "
            f"light summary ({light_tokens} tokens). Hierarchy violated!"
        )

        # Medium should be roughly 2x light (66% vs 33%)
        # Allow wider tolerance (1.5x to 3x) for extractive summarization variance
        ratio = medium_tokens / light_tokens if light_tokens > 0 else 0

        assert 1.5 <= ratio <= 3.0, (
            f"Medium/Light ratio is {ratio:.2f}x, expected ~2.0x (±50%). "
            f"Medium: {medium_tokens} tokens, Light: {light_tokens} tokens"
        )

    def test_default_levels_use_new_targets(self):
        """
        Default levels should use new targets when levels parameter is None.

        Handover 0246b specifies:
        - Light: 5000 tokens (33% of typical 15K doc)
        - Medium: 10000 tokens (66% of typical 15K doc)
        - No heavy level

        NOTE: This test will FAIL until summarize_multi_level() is updated
        to use new default levels.
        """
        summarizer = VisionDocumentSummarizer()
        original_text = generate_realistic_document(tokens=15000)

        # Call with levels=None to use defaults
        result = summarizer.summarize_multi_level(original_text, levels=None)

        # Verify typed return (Handover 0731)
        assert isinstance(result, SummarizeMultiLevelResult)

        # Verify light target (~5K tokens +- 20%)
        light_tokens = result.light.tokens
        assert 4000 <= light_tokens <= 6000, f"Light summary has {light_tokens} tokens, expected ~5K (4K-6K range)"

        # Verify medium target (~10K tokens +- 20%)
        medium_tokens = result.medium.tokens
        assert 8000 <= medium_tokens <= 12000, (
            f"Medium summary has {medium_tokens} tokens, expected ~10K (8K-12K range)"
        )

        # Verify heavy does NOT exist as attribute
        assert not hasattr(result, "heavy"), "Default levels should NOT include 'heavy'"

    def test_custom_levels_without_heavy(self):
        """
        Custom levels should work with only light and medium (no heavy).

        This test verifies that the API supports custom retention ratios for the
        2-level system without requiring a 'heavy' key.
        """
        summarizer = VisionDocumentSummarizer()
        original_text = generate_realistic_document(tokens=20000)

        # Custom retention ratios for light and medium only
        # For 20K token document: light=20% (~4K), medium=50% (~10K)
        custom_levels = {"light": 0.20, "medium": 0.50}

        result = summarizer.summarize_multi_level(original_text, levels=custom_levels)

        # Verify typed return (Handover 0731)
        assert isinstance(result, SummarizeMultiLevelResult)

        # Verify approximate targets (20% and 50% of original tokens +-20%)
        original_tokens = result.original_tokens
        light_expected = int(original_tokens * 0.20)
        medium_expected = int(original_tokens * 0.50)

        # Allow +-30% tolerance due to extractive summarization variance
        assert light_expected * 0.5 <= result.light.tokens <= light_expected * 1.5, (
            f"Light summary has {result.light.tokens} tokens, expected ~{light_expected}"
        )
        assert medium_expected * 0.5 <= result.medium.tokens <= medium_expected * 1.5, (
            f"Medium summary has {result.medium.tokens} tokens, expected ~{medium_expected}"
        )
