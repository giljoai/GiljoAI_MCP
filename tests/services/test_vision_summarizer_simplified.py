"""
Test suite for simplified VisionSummarizer (Handover 0246b).

Tests the simplified 2-level summarization system:
- Light: 33% of original tokens
- Medium: 66% of original tokens
- No Heavy level (removed)

These tests follow TDD Red phase - they will FAIL until implementation is complete.

Coverage Target: >90%
"""

import pytest
from src.giljo_mcp.services.vision_summarizer import VisionDocumentSummarizer


def generate_realistic_document(tokens: int) -> str:
    """
    Generate realistic technical document with approximately the specified token count.

    Uses varied technical content to simulate vision documents with proper
    sentence structure for extractive summarization.

    Args:
        tokens: Target token count (~4 chars per token)

    Returns:
        Test document string with realistic content
    """
    # Technical paragraphs with diverse semantic content
    base_paragraphs = [
        (
            "The GiljoAI Agent Orchestration system provides a sophisticated multi-agent "
            "framework for complex software development tasks. The orchestrator coordinates "
            "specialized agents including implementors, testers, analyzers, and deployment "
            "specialists. Each agent operates with context awareness and token budget management "
            "to ensure efficient use of available language model capacity."
        ),
        (
            "Vision documents serve as high-level architectural guidance for orchestrators "
            "during project initialization and execution phases. These documents describe "
            "the overall system goals, technical constraints, implementation strategies, "
            "and design patterns that guide agent decision-making throughout the development "
            "lifecycle. Proper vision documentation ensures consistency across project phases."
        ),
        (
            "The system architecture leverages FastAPI for backend services with PostgreSQL "
            "for persistent storage and multi-tenant isolation. Frontend components are built "
            "using Vue 3 with Vuetify for material design components. Real-time updates are "
            "handled through WebSocket connections that provide live status updates to the "
            "dashboard interface for monitoring agent execution progress."
        ),
        (
            "Context management is critical for efficient token usage in large language models. "
            "The system employs a two-dimensional prioritization model combining field priority "
            "with depth configuration. This enables agents to access essential information while "
            "staying within context budget limits. Priority levels range from critical to excluded, "
            "while depth levels control the amount of detail included for each context field."
        ),
        (
            "Multi-tenant isolation ensures secure separation of data across different users "
            "and organizations. Each tenant operates in a completely isolated environment with "
            "dedicated database partitions enforced through tenant_key filtering. Access controls "
            "prevent cross-tenant data leakage. This architecture supports enterprise deployments "
            "while maintaining strict data security and privacy requirements."
        ),
        (
            "Agent job management provides lifecycle control for spawned agents including "
            "creation, execution monitoring, cancellation, and handover coordination. The system "
            "tracks context usage and automatically triggers succession when approaching token "
            "budget limits. Job status updates are broadcast through WebSocket events to enable "
            "real-time UI updates and orchestrator coordination across distributed agents."
        ),
        (
            "Testing strategy encompasses unit tests with pytest for service layer validation, "
            "integration tests for API endpoints and database operations, and end-to-end tests "
            "for complete workflow verification. Code coverage targets exceed 80 percent across "
            "all critical paths. Frontend testing uses Vitest for component tests and Cypress "
            "for browser-based integration testing of user workflows."
        ),
        (
            "Authentication implements JWT tokens with refresh token rotation for enhanced security. "
            "Password hashing uses bcrypt with configurable work factors. Rate limiting protects "
            "against brute force attacks on authentication endpoints. Recovery mechanisms include "
            "PIN-based password reset with expiration and rate limiting to prevent abuse while "
            "maintaining user accessibility for account recovery scenarios."
        ),
    ]

    # Calculate how many paragraphs needed to reach target
    avg_chars = sum(len(p) for p in base_paragraphs) // len(base_paragraphs)
    tokens_per_paragraph = avg_chars // 4
    paragraphs_needed = max(1, tokens // tokens_per_paragraph)

    # Generate document with varied content
    paragraphs = []
    for i in range(paragraphs_needed):
        # Cycle through diverse paragraphs
        para = base_paragraphs[i % len(base_paragraphs)]
        # Add variation to prevent exact duplicates
        variant = para.replace("system", f"system-v{i % 10}")
        paragraphs.append(variant)

    return "\n\n".join(paragraphs)


# ============================================================================
# UNIT TESTS - Simplified Two-Level Summarization
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

        # Summarize with light level (should target ~3,300 tokens)
        result = summarizer.summarize_multi_level(
            original_text,
            levels={"light": 3300, "medium": 6600}
        )

        # Verify light summary exists
        assert "light" in result, "Result should contain 'light' key"
        assert "tokens" in result["light"], "Light summary should have token count"

        # Calculate actual percentage
        original_tokens = result["original_tokens"]
        light_tokens = result["light"]["tokens"]
        actual_percentage = (light_tokens / original_tokens) if original_tokens > 0 else 0

        # Assert 33% ± 10% (23% to 43%)
        assert 0.23 <= actual_percentage <= 0.43, (
            f"Light summary is {actual_percentage*100:.1f}% of original, "
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

        # Summarize with medium level (should target ~6,600 tokens)
        result = summarizer.summarize_multi_level(
            original_text,
            levels={"light": 3300, "medium": 6600}
        )

        # Verify medium summary exists
        assert "medium" in result, "Result should contain 'medium' key"
        assert "tokens" in result["medium"], "Medium summary should have token count"

        # Calculate actual percentage
        original_tokens = result["original_tokens"]
        medium_tokens = result["medium"]["tokens"]
        actual_percentage = (medium_tokens / original_tokens) if original_tokens > 0 else 0

        # Assert 66% ± 10% (56% to 76%)
        assert 0.56 <= actual_percentage <= 0.76, (
            f"Medium summary is {actual_percentage*100:.1f}% of original, "
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

        # Verify exactly 2 summary levels present
        summary_levels = [k for k in result.keys() if k not in ["original_tokens", "processing_time_ms"]]

        assert len(summary_levels) == 2, (
            f"Expected exactly 2 summary levels (light, medium), got {len(summary_levels)}: {summary_levels}"
        )

        # Verify light and medium exist
        assert "light" in result, "Result must contain 'light' level"
        assert "medium" in result, "Result must contain 'medium' level"

        # Verify heavy does NOT exist
        assert "heavy" not in result, (
            "Result should NOT contain 'heavy' level (removed in Handover 0246b)"
        )

        # Verify metadata fields exist
        assert "original_tokens" in result, "Result should include original_tokens"
        assert "processing_time_ms" in result, "Result should include processing_time_ms"

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

        # Split original into sentences for verification
        original_sentences = [s.strip() for s in original_text.split('.') if s.strip()]

        # Verify both light and medium summaries are extractive
        for level in ["light", "medium"]:
            summary_text = result[level]["summary"]
            summary_sentences = [s.strip() for s in summary_text.split('.') if s.strip()]

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
                f"{level.capitalize()} summary appears non-extractive: "
                f"only {match_ratio*100:.0f}% of sentences match original. "
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

        light_tokens = result["light"]["tokens"]
        medium_tokens = result["medium"]["tokens"]

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

        # Verify only 2 levels returned
        summary_levels = [k for k in result.keys() if k not in ["original_tokens", "processing_time_ms"]]
        assert len(summary_levels) == 2, f"Expected 2 levels, got {len(summary_levels)}"

        # Verify light target (~5K tokens ± 20%)
        light_tokens = result["light"]["tokens"]
        assert 4000 <= light_tokens <= 6000, (
            f"Light summary has {light_tokens} tokens, expected ~5K (4K-6K range)"
        )

        # Verify medium target (~10K tokens ± 20%)
        medium_tokens = result["medium"]["tokens"]
        assert 8000 <= medium_tokens <= 12000, (
            f"Medium summary has {medium_tokens} tokens, expected ~10K (8K-12K range)"
        )

        # Verify heavy does NOT exist in defaults
        assert "heavy" not in result, "Default levels should NOT include 'heavy'"

    def test_custom_levels_without_heavy(self):
        """
        Custom levels should work with only light and medium (no heavy).

        This test verifies that the API supports custom targets for the
        2-level system without requiring a 'heavy' key.
        """
        summarizer = VisionDocumentSummarizer()
        original_text = generate_realistic_document(tokens=20000)

        # Custom targets for light and medium only
        custom_levels = {
            "light": 4000,
            "medium": 10000
        }

        result = summarizer.summarize_multi_level(original_text, levels=custom_levels)

        # Verify only requested levels returned
        assert "light" in result
        assert "medium" in result
        assert "heavy" not in result

        # Verify approximate targets (±20%)
        assert 3200 <= result["light"]["tokens"] <= 4800, (
            f"Light summary has {result['light']['tokens']} tokens, expected ~4K"
        )
        assert 8000 <= result["medium"]["tokens"] <= 12000, (
            f"Medium summary has {result['medium']['tokens']} tokens, expected ~10K"
        )

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

        # Verify both levels exist
        assert "light" in result
        assert "medium" in result

        # Verify hierarchy maintained even for small docs
        assert result["light"]["tokens"] <= result["medium"]["tokens"], (
            "Light should not be longer than medium, even for small documents"
        )

        # Verify summaries don't exceed original
        assert result["light"]["tokens"] <= result["original_tokens"]
        assert result["medium"]["tokens"] <= result["original_tokens"]

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

        # Should complete in <15 seconds
        assert elapsed < 15.0, (
            f"Summarization took {elapsed:.2f}s, exceeds 15s requirement for 50K tokens"
        )

        # Verify processing time is tracked
        assert result["processing_time_ms"] > 0
        assert result["processing_time_ms"] < 15000

    def test_each_level_has_required_fields(self):
        """
        Each summary level must have summary, tokens, and sentences fields.

        This verifies the data structure returned by summarize_multi_level()
        matches the expected format.
        """
        summarizer = VisionDocumentSummarizer()
        text = generate_realistic_document(tokens=10000)

        result = summarizer.summarize_multi_level(text)

        # Check both levels have required fields
        for level in ["light", "medium"]:
            assert level in result, f"Missing {level} level"

            assert "summary" in result[level], f"{level} missing 'summary' field"
            assert "tokens" in result[level], f"{level} missing 'tokens' field"
            assert "sentences" in result[level], f"{level} missing 'sentences' field"

            # Verify field types
            assert isinstance(result[level]["summary"], str), f"{level} summary should be string"
            assert isinstance(result[level]["tokens"], int), f"{level} tokens should be int"
            assert isinstance(result[level]["sentences"], int), f"{level} sentences should be int"

            # Verify non-empty
            assert len(result[level]["summary"]) > 0, f"{level} summary should not be empty"
            assert result[level]["tokens"] > 0, f"{level} tokens should be > 0"
            assert result[level]["sentences"] > 0, f"{level} sentences should be > 0"

    def test_empty_input_handling(self):
        """
        Empty or whitespace-only input should be handled gracefully.

        Should return empty summaries without errors.
        """
        summarizer = VisionDocumentSummarizer()

        # Test empty string
        result = summarizer.summarize_multi_level("")

        assert result["original_tokens"] == 0
        assert "light" in result
        assert "medium" in result

        # Summaries should be empty or minimal
        assert result["light"]["tokens"] == 0 or result["light"]["summary"] == ""
        assert result["medium"]["tokens"] == 0 or result["medium"]["summary"] == ""


# ============================================================================
# INTEGRATION TESTS - Database Storage
# ============================================================================


@pytest.mark.asyncio
class TestDatabaseIntegration:
    """
    Integration tests for vision document storage with 2-level summaries.

    NOTE: These tests require database fixtures and will be implemented
    in Phase 2 after the VisionSummarizer changes are complete.
    """

    async def test_upload_stores_light_and_medium_only(self):
        """
        Upload should populate only light and medium summary columns.

        CRITICAL: Deprecated summary fields (summary_moderate, summary_heavy) removed in Handover 0374.

        NOTE: This test is a placeholder and will FAIL until database
        integration is implemented.
        """
        pytest.skip("Integration test - implement after VisionSummarizer changes")

    async def test_vision_document_column_populated(self):
        """
        Upload should populate vision_document column with full content.

        Handover 0246b: Store complete original in vision_document column,
        no chunking.

        NOTE: This test is a placeholder.
        """
        pytest.skip("Integration test - implement after database schema changes")

    async def test_no_chunks_created_for_vision_docs(self):
        """
        Vision document upload should NOT create entries in mcp_context_index.

        Handover 0246b: Remove chunking logic for vision documents.

        NOTE: This test is a placeholder.
        """
        pytest.skip("Integration test - implement after upload flow changes")


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

        # Should not crash
        assert "light" in result
        assert "medium" in result

        # Both summaries should contain something (even if same as original)
        assert len(result["light"]["summary"]) > 0
        assert len(result["medium"]["summary"]) > 0

    def test_no_periods_in_text(self):
        """Text without sentence boundaries should be handled gracefully."""
        summarizer = VisionDocumentSummarizer()

        # Long text without periods
        no_periods = " ".join(["word"] * 1000)

        result = summarizer.summarize_multi_level(no_periods)

        # Should not crash (though summarization may be less effective)
        assert "light" in result
        assert "medium" in result

    def test_unicode_content(self):
        """Unicode characters should be handled correctly."""
        summarizer = VisionDocumentSummarizer()

        unicode_text = """
        The system supports internationalization with Unicode characters.
        测试中文字符处理能力。
        Тестирование кириллических символов.
        Testing emoji support: 🚀 💻 📊
        """ * 100  # Repeat to get reasonable token count

        result = summarizer.summarize_multi_level(unicode_text)

        # Should handle Unicode without errors
        assert "light" in result
        assert "medium" in result
        assert result["original_tokens"] > 0
