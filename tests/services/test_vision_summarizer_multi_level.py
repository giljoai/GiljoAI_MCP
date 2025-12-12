"""
Test suite for multi-level vision document summarization.

Tests VisionDocumentSummarizer.summarize_multi_level() method that generates
three compression levels (light/moderate/heavy) in a single pass.

Handover 0345e: Sumy Semantic Compression Levels
"""

import pytest
import time
from src.giljo_mcp.services.vision_summarizer import VisionDocumentSummarizer


def generate_test_document(tokens: int) -> str:
    """
    Generate test document with approximately the specified token count.

    Uses repetitive but semantically varied paragraphs to create realistic
    test data for summarization.

    Args:
        tokens: Target token count (~4 chars per token)

    Returns:
        Test document string
    """
    # Base paragraphs with different semantic content
    paragraphs = [
        "The system architecture follows a microservices pattern with independent services. "
        "Each service communicates via REST APIs and message queues for async operations. "
        "This design enables horizontal scaling and independent deployment of components.",

        "Frontend components are built using Vue 3 with TypeScript and Vuetify. "
        "The application uses a reactive state management system with Pinia stores. "
        "Real-time updates are handled through WebSocket connections to the backend.",

        "Database operations use SQLAlchemy ORM with PostgreSQL 18 as the primary store. "
        "Multi-tenant isolation is enforced at the query level using tenant_key filters. "
        "Connection pooling and async operations ensure optimal database performance.",

        "Authentication implements JWT tokens with refresh token rotation for security. "
        "Password hashing uses bcrypt with configurable work factors. "
        "Rate limiting protects against brute force attacks on authentication endpoints.",

        "Testing strategy includes unit tests with pytest and integration tests for APIs. "
        "Frontend uses Vitest for component testing and end-to-end tests with Cypress. "
        "Code coverage targets exceed 80 percent across all critical paths.",
    ]

    # Calculate how many times to repeat to reach target
    chars_needed = tokens * 4  # ~4 chars per token
    full_text = " ".join(paragraphs)
    repetitions = max(1, chars_needed // len(full_text))

    # Build document with varied paragraphs
    result = []
    for i in range(repetitions):
        for j, para in enumerate(paragraphs):
            # Add semantic variety with section numbers
            result.append(f"Section {i+1}.{j+1}: {para}")

    return "\n\n".join(result)


class TestMultiLevelSummarization:
    """Test suite for multi-level semantic compression."""

    def test_summarize_multi_level_returns_three_summaries(self):
        """Should generate light, moderate, and heavy summaries."""
        summarizer = VisionDocumentSummarizer()
        text = generate_test_document(tokens=50000)

        result = summarizer.summarize_multi_level(text)

        assert "light" in result
        assert "moderate" in result
        assert "heavy" in result

        # Each level should have summary, tokens, and sentences
        for level in ["light", "moderate", "heavy"]:
            assert "summary" in result[level]
            assert "tokens" in result[level]
            assert "sentences" in result[level]
            assert isinstance(result[level]["summary"], str)
            assert isinstance(result[level]["tokens"], int)
            assert isinstance(result[level]["sentences"], int)

    def test_light_moderate_heavy_token_targets(self):
        """Token counts should approximately match targets (±20% tolerance)."""
        summarizer = VisionDocumentSummarizer()
        text = generate_test_document(tokens=50000)

        result = summarizer.summarize_multi_level(text)

        # Light: ~5K tokens (allow 4K-6K)
        assert 4000 <= result["light"]["tokens"] <= 6000, \
            f"Light summary has {result['light']['tokens']} tokens, expected 4K-6K"

        # Moderate: ~12.5K tokens (allow 10K-15K)
        assert 10000 <= result["moderate"]["tokens"] <= 15000, \
            f"Moderate summary has {result['moderate']['tokens']} tokens, expected 10K-15K"

        # Heavy: ~25K tokens (allow 20K-30K)
        assert 20000 <= result["heavy"]["tokens"] <= 30000, \
            f"Heavy summary has {result['heavy']['tokens']} tokens, expected 20K-30K"

    def test_light_is_subset_of_moderate_is_subset_of_heavy(self):
        """Cascading summaries should preserve hierarchy (lighter < heavier)."""
        summarizer = VisionDocumentSummarizer()
        text = generate_test_document(tokens=50000)

        result = summarizer.summarize_multi_level(text)

        # Light should be shortest, heavy should be longest
        assert result["light"]["tokens"] < result["moderate"]["tokens"], \
            f"Light ({result['light']['tokens']}) should be < Moderate ({result['moderate']['tokens']})"
        assert result["moderate"]["tokens"] < result["heavy"]["tokens"], \
            f"Moderate ({result['moderate']['tokens']}) should be < Heavy ({result['heavy']['tokens']})"

    def test_multi_level_processing_time_under_15_seconds(self):
        """Generating 3 summaries should take <15 sec for 100K tokens."""
        summarizer = VisionDocumentSummarizer()
        text = generate_test_document(tokens=100000)

        start = time.time()
        result = summarizer.summarize_multi_level(text)
        elapsed = time.time() - start

        assert elapsed < 15.0, f"Processing took {elapsed:.2f}s, expected <15s"
        assert result["processing_time_ms"] < 15000, \
            f"Reported time {result['processing_time_ms']}ms, expected <15000ms"

    def test_multi_level_includes_original_tokens_and_timing(self):
        """Result should include original_tokens and processing_time_ms."""
        summarizer = VisionDocumentSummarizer()
        text = generate_test_document(tokens=50000)

        result = summarizer.summarize_multi_level(text)

        assert "original_tokens" in result
        assert "processing_time_ms" in result
        assert isinstance(result["original_tokens"], int)
        assert isinstance(result["processing_time_ms"], int)
        assert result["original_tokens"] > 0
        assert result["processing_time_ms"] > 0

    def test_custom_level_targets(self):
        """Should accept custom target token counts per level."""
        summarizer = VisionDocumentSummarizer()
        text = generate_test_document(tokens=50000)

        custom_levels = {
            "light": 3000,
            "moderate": 8000,
            "heavy": 15000
        }

        result = summarizer.summarize_multi_level(text, levels=custom_levels)

        # Check custom targets are approximately met (±20% tolerance)
        assert 2400 <= result["light"]["tokens"] <= 3600  # 3K ± 20%
        assert 6400 <= result["moderate"]["tokens"] <= 9600  # 8K ± 20%
        assert 12000 <= result["heavy"]["tokens"] <= 18000  # 15K ± 20%

    def test_small_document_handling(self):
        """Should handle documents smaller than target sizes gracefully."""
        summarizer = VisionDocumentSummarizer()
        text = generate_test_document(tokens=3000)  # Smaller than light target

        result = summarizer.summarize_multi_level(text)

        # Should still generate summaries, even if small
        assert result["light"]["tokens"] <= result["original_tokens"]
        assert result["moderate"]["tokens"] <= result["original_tokens"]
        assert result["heavy"]["tokens"] <= result["original_tokens"]

        # Light should be smallest
        assert result["light"]["tokens"] <= result["moderate"]["tokens"]
        assert result["moderate"]["tokens"] <= result["heavy"]["tokens"]

    def test_summaries_are_extractive_not_abstractive(self):
        """Summaries should only contain sentences from original (no hallucination)."""
        summarizer = VisionDocumentSummarizer()
        text = generate_test_document(tokens=20000)

        result = summarizer.summarize_multi_level(text)

        # Split original into sentences for verification
        original_sentences = [s.strip() for s in text.split('.') if s.strip()]

        # Check that summary sentences come from original
        for level in ["light", "moderate", "heavy"]:
            summary = result[level]["summary"]
            summary_sentences = [s.strip() for s in summary.split('.') if s.strip()]

            # At least some sentences should match original (extractive property)
            # Allow for slight variations in punctuation/whitespace
            matches = 0
            for summ_sent in summary_sentences:
                for orig_sent in original_sentences:
                    # Check if summary sentence is contained in original
                    if summ_sent[:50] in orig_sent or orig_sent[:50] in summ_sent:
                        matches += 1
                        break

            # At least 80% of summary sentences should come from original
            match_ratio = matches / max(len(summary_sentences), 1)
            assert match_ratio >= 0.8, \
                f"{level} summary appears non-extractive (only {match_ratio*100:.0f}% matches)"

    def test_default_levels_when_none_provided(self):
        """Should use default levels (5K/12.5K/25K) when levels parameter is None."""
        summarizer = VisionDocumentSummarizer()
        text = generate_test_document(tokens=50000)

        result = summarizer.summarize_multi_level(text, levels=None)

        # Default targets: light=5K, moderate=12.5K, heavy=25K
        # Allow ±20% tolerance
        assert 4000 <= result["light"]["tokens"] <= 6000
        assert 10000 <= result["moderate"]["tokens"] <= 15000
        assert 20000 <= result["heavy"]["tokens"] <= 30000


@pytest.mark.asyncio
class TestUploadWithMultiLevelSummaries:
    """Test vision document upload with multi-level summarization."""

    async def test_upload_stores_three_summaries(
        self, db_session_async, test_product, test_tenant
    ):
        """Upload should populate all three summary columns."""
        from src.giljo_mcp.services.product_service import ProductService

        service = ProductService(session=db_session_async, tenant_key=test_tenant["key"])

        # Create large document (>30K tokens to trigger summarization)
        large_document = generate_test_document(tokens=50000)

        result = await service.upload_vision_document(
            product_id=test_product["id"],
            content=large_document,
            filename="test_vision.md",
            auto_chunk=False  # Skip chunking for this test
        )

        assert result["success"] is True

        # Verify database record has all three summaries
        from sqlalchemy import select
        from src.giljo_mcp.models.products import VisionDocument

        stmt = select(VisionDocument).where(VisionDocument.id == result["document_id"])
        db_result = await db_session_async.execute(stmt)
        vision_doc = db_result.scalar_one_or_none()

        assert vision_doc is not None
        assert vision_doc.is_summarized is True

        # Check all three summary levels exist
        assert vision_doc.summary_light is not None
        assert vision_doc.summary_moderate is not None
        assert vision_doc.summary_heavy is not None

        # Check token counts are populated
        assert vision_doc.summary_light_tokens is not None
        assert vision_doc.summary_moderate_tokens is not None
        assert vision_doc.summary_heavy_tokens is not None

        # Verify token counts match targets (±20%)
        assert 4000 <= vision_doc.summary_light_tokens <= 6000
        assert 10000 <= vision_doc.summary_moderate_tokens <= 15000
        assert 20000 <= vision_doc.summary_heavy_tokens <= 30000

        # Verify hierarchy (light < moderate < heavy)
        assert vision_doc.summary_light_tokens < vision_doc.summary_moderate_tokens
        assert vision_doc.summary_moderate_tokens < vision_doc.summary_heavy_tokens


@pytest.mark.asyncio
class TestContextRetrievalWithDepth:
    """Test orchestrator context retrieval respects depth configuration."""

    async def test_orchestrator_instructions_respects_depth_config_light(
        self, db_session_async, test_product, test_project, test_tenant
    ):
        """Should return light summary when depth='light'."""
        from src.giljo_mcp.mission_planner import MissionPlanner
        from src.giljo_mcp.services.settings_service import SettingsService

        # Upload vision document with summaries
        from src.giljo_mcp.services.product_service import ProductService
        product_service = ProductService(
            session=db_session_async,
            tenant_key=test_tenant["key"]
        )

        large_document = generate_test_document(tokens=50000)
        await product_service.upload_vision_document(
            product_id=test_product["id"],
            content=large_document,
            filename="test_vision.md",
            auto_chunk=False
        )

        # Set depth config to 'light'
        settings_service = SettingsService(
            session=db_session_async,
            tenant_key=test_tenant["key"]
        )
        await settings_service.save_depth_config({
            "vision_documents": "light"
        })

        # Build context with mission planner
        planner = MissionPlanner(
            db_manager=None,  # Will use session directly
            tenant_key=test_tenant["key"]
        )

        context = await planner._build_context_with_priorities(
            product=test_product,
            project=test_project,
            field_priorities={"vision_documents": 2},  # IMPORTANT priority
            user_id=test_tenant["user_id"]
        )

        # Verify context contains vision content
        assert "vision" in context.lower() or "Vision Documents" in context

        # Estimate token count (rough: 1 token ≈ 4 chars)
        estimated_tokens = len(context) // 4

        # Should be approximately 5K tokens (light level) ± tolerance
        # Allow wider range since context includes other fields
        assert 4000 <= estimated_tokens <= 10000, \
            f"Expected ~5K tokens for light depth, got {estimated_tokens}"

    async def test_full_depth_returns_original_chunks(
        self, db_session_async, test_product, test_project, test_tenant
    ):
        """'Full' depth should bypass summaries and return original chunks."""
        from src.giljo_mcp.mission_planner import MissionPlanner
        from src.giljo_mcp.services.settings_service import SettingsService
        from src.giljo_mcp.services.product_service import ProductService

        # Upload and chunk vision document
        product_service = ProductService(
            session=db_session_async,
            tenant_key=test_tenant["key"]
        )

        large_document = generate_test_document(tokens=50000)
        await product_service.upload_vision_document(
            product_id=test_product["id"],
            content=large_document,
            filename="test_vision.md",
            auto_chunk=True  # Enable chunking for full depth test
        )

        # Set depth config to 'full'
        settings_service = SettingsService(
            session=db_session_async,
            tenant_key=test_tenant["key"]
        )
        await settings_service.save_depth_config({
            "vision_documents": "full"
        })

        # Build context
        planner = MissionPlanner(
            db_manager=None,
            tenant_key=test_tenant["key"]
        )

        context = await planner._build_context_with_priorities(
            product=test_product,
            project=test_project,
            field_priorities={"vision_documents": 2},
            user_id=test_tenant["user_id"]
        )

        # Full depth should include more content than summaries
        estimated_tokens = len(context) // 4

        # Should be close to original 50K tokens (allow 40K-60K range)
        assert 30000 <= estimated_tokens <= 70000, \
            f"Expected ~50K tokens for full depth, got {estimated_tokens}"
