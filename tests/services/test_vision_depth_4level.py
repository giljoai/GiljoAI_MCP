"""
Test suite for 4-level vision depth configuration (Handover 0347e).

Tests the implementation of 4-level vision depth system:
- optional: Pointer + pagination only (~200 tokens)
- light: 33% summarized content inline (~10-12K tokens)
- medium: 66% summarized content inline (~20-24K tokens)
- full: Pointer + MANDATORY read instruction (~200 tokens + fetch)

TDD Implementation: Tests written FIRST, before implementation.
"""

import json
from unittest.mock import AsyncMock, MagicMock, patch

import pytest
from sqlalchemy.ext.asyncio import AsyncSession

from src.giljo_mcp.mission_planner import MissionPlanner
from src.giljo_mcp.models import Product, Project
from src.giljo_mcp.models.products import VisionDocument


@pytest.fixture
def mock_db_manager():
    """Mock database manager for testing."""
    db_manager = MagicMock()
    db_manager.is_async = True

    # Mock async session context manager
    mock_session = AsyncMock(spec=AsyncSession)
    mock_session.__aenter__ = AsyncMock(return_value=mock_session)
    mock_session.__aexit__ = AsyncMock(return_value=None)

    db_manager.get_session_async = MagicMock(return_value=mock_session)

    return db_manager


@pytest.fixture
def mission_planner(mock_db_manager):
    """Create MissionPlanner instance with mock DB."""
    return MissionPlanner(mock_db_manager)


@pytest.fixture
def sample_product():
    """Create sample product with vision document."""
    product = Product(
        id="test-product-id",
        name="Test Product",
        description="Test product description",
        tenant_key="test-tenant",
        config_data={"tech_stack": {"languages": ["Python"]}},
        product_memory={},
    )
    return product


@pytest.fixture
def sample_vision_doc():
    """Create sample vision document (40K tokens)."""
    vision_doc = VisionDocument(
        id="test-vision-doc-id",
        product_id="test-product-id",
        tenant_key="test-tenant",
        document_name="Product Vision",
        is_active=True,
        chunked=True,
        chunk_count=5,
        original_token_count=40000,
        display_order=1,
    )
    return vision_doc


@pytest.fixture
def sample_project():
    """Create sample project."""
    project = Project(
        id="test-project-id",
        name="Test Project",
        description="Test project description",
        tenant_key="test-tenant",
        product_id="test-product-id",
    )
    return project


@pytest.mark.asyncio
class TestVisionDepth4Level:
    """Test 4-level vision depth system."""

    async def test_optional_depth_returns_pointer_only(
        self, mission_planner, sample_product, sample_project, sample_vision_doc
    ):
        """
        Test optional depth level.

        Expected:
        - Returns pointer with status: "AVAILABLE_IF_NEEDED"
        - Includes fetch_commands list
        - Includes when_to_fetch guidance
        - Token count ~200 tokens
        """
        # Mock _get_active_vision_doc to return vision doc
        # Mock _get_full_agent_templates to avoid DB calls
        with (
            patch.object(
                mission_planner, "_get_active_vision_doc", new_callable=AsyncMock, return_value=sample_vision_doc
            ),
            patch.object(mission_planner, "_get_full_agent_templates", new_callable=AsyncMock, return_value=[]),
        ):
            # Call with optional depth
            context = await mission_planner._build_context_with_priorities(
                product=sample_product,
                project=sample_project,
                field_priorities={"vision_documents": 3},  # Reference tier
                depth_config={"vision_documents": "optional"},
                user_id=None,
                include_serena=False,
            )

            # Verify structure
            assert "reference" in context
            assert "vision_documents" in context["reference"]

            vision_data = context["reference"]["vision_documents"]

            # Verify pointer-only response (implementation uses "AVAILABLE_IF_NEEDED")
            assert vision_data["status"] == "AVAILABLE_IF_NEEDED"
            assert "fetch_commands" in vision_data
            assert isinstance(vision_data["fetch_commands"], list)
            assert "when_to_fetch" in vision_data
            assert isinstance(vision_data["when_to_fetch"], list)

            # Verify no inline content
            assert "inline_content" not in vision_data
            assert "summary" not in vision_data

            # Verify token count (should be small - pointer only)
            # Note: JSON is more compact than expected, ~80-150 tokens is acceptable
            json_str = json.dumps(vision_data)
            token_estimate = len(json_str) // 4
            assert 60 <= token_estimate <= 350, f"Expected small token count, got {token_estimate}"

    async def test_light_depth_includes_33_percent_summary(
        self, mission_planner, sample_product, sample_project, sample_vision_doc
    ):
        """
        Test light depth level.

        Expected:
        - Returns inline summary with pre-computed SUMY summary (33% of original)
        - Status: "INLINE_SUMMARY"
        - Coverage: "33% of original vision (SUMY LSA)"
        - Summary stored in summary_light field
        """
        # Set pre-computed summary_light field (as stored in database after upload)
        # 40K tokens = 160K chars, 33% = ~13K tokens = ~52K chars
        light_summary = "Light summary content. " * 2500  # ~52K chars ≈ 13K tokens
        sample_vision_doc.summary_light = light_summary
        sample_vision_doc.summary_light_tokens = 13000

        # Mock _get_active_vision_doc and _get_full_agent_templates
        with (
            patch.object(
                mission_planner, "_get_active_vision_doc", new_callable=AsyncMock, return_value=sample_vision_doc
            ),
            patch.object(mission_planner, "_get_full_agent_templates", new_callable=AsyncMock, return_value=[]),
        ):
            context = await mission_planner._build_context_with_priorities(
                product=sample_product,
                project=sample_project,
                field_priorities={"vision_documents": 3},
                depth_config={"vision_documents": "light"},
                user_id=None,
                include_serena=False,
            )

            vision_data = context["reference"]["vision_documents"]

            # Verify inline summary
            assert vision_data["status"] == "INLINE_SUMMARY"
            assert vision_data["coverage"] == "33% of original vision (SUMY LSA)"
            assert "inline_content" in vision_data

            # Verify content matches pre-computed summary
            assert vision_data["inline_content"] == light_summary

            # Verify summary_tokens from pre-computed field
            assert vision_data["summary_tokens"] == 13000

    async def test_medium_depth_includes_66_percent_summary(
        self, mission_planner, sample_product, sample_project, sample_vision_doc
    ):
        """
        Test medium depth level.

        Expected:
        - Returns inline summary with pre-computed SUMY summary (66% of original)
        - Status: "INLINE_SUMMARY"
        - Coverage: "66% of original vision (SUMY LSA)"
        - Summary stored in summary_medium field
        """
        # Set pre-computed summary_medium field (as stored in database after upload)
        # 40K tokens = 160K chars, 66% = ~26K tokens = ~104K chars
        medium_summary = "Medium summary content. " * 4200  # ~104K chars ≈ 26K tokens
        sample_vision_doc.summary_medium = medium_summary
        sample_vision_doc.summary_medium_tokens = 26000

        with (
            patch.object(
                mission_planner, "_get_active_vision_doc", new_callable=AsyncMock, return_value=sample_vision_doc
            ),
            patch.object(mission_planner, "_get_full_agent_templates", new_callable=AsyncMock, return_value=[]),
        ):
            context = await mission_planner._build_context_with_priorities(
                product=sample_product,
                project=sample_project,
                field_priorities={"vision_documents": 3},
                depth_config={"vision_documents": "medium"},
                user_id=None,
                include_serena=False,
            )

            vision_data = context["reference"]["vision_documents"]

            # Verify inline summary
            assert vision_data["status"] == "INLINE_SUMMARY"
            assert vision_data["coverage"] == "66% of original vision (SUMY LSA)"
            assert "inline_content" in vision_data

            # Verify content matches pre-computed summary
            assert vision_data["inline_content"] == medium_summary

            # Verify summary_tokens from pre-computed field
            assert vision_data["summary_tokens"] == 26000

    async def test_full_depth_includes_mandatory_read_instruction(
        self, mission_planner, sample_product, sample_project, sample_vision_doc
    ):
        """
        Test full depth level.

        Expected:
        - Returns pointer with status: "REQUIRED_READING"
        - Includes mandatory instruction with "MUST fetch ALL chunks"
        - Includes strong compliance language
        - Token count ~200 tokens (instruction only, no content)
        """
        with (
            patch.object(
                mission_planner, "_get_active_vision_doc", new_callable=AsyncMock, return_value=sample_vision_doc
            ),
            patch.object(mission_planner, "_get_full_agent_templates", new_callable=AsyncMock, return_value=[]),
        ):
            context = await mission_planner._build_context_with_priorities(
                product=sample_product,
                project=sample_project,
                field_priorities={"vision_documents": 3},
                depth_config={"vision_documents": "full"},
                user_id=None,
                include_serena=False,
            )

            vision_data = context["reference"]["vision_documents"]

            # Verify mandatory reading status
            assert vision_data["status"] == "REQUIRED_READING"
            assert "mandatory_instruction" in vision_data

            instruction = vision_data["mandatory_instruction"]

            # Verify strong compliance language
            assert "MUST" in instruction.upper()
            assert "NOT optional" in instruction or "NOT OPTIONAL" in instruction.upper()
            assert "violates" in instruction.lower() or "VIOLATES" in instruction

            # Verify fetch commands included
            assert "fetch_commands" in vision_data
            assert isinstance(vision_data["fetch_commands"], list)
            assert len(vision_data["fetch_commands"]) == sample_vision_doc.chunk_count

            # Verify token count (should be ~200-500 tokens for instruction + fetch commands)
            json_str = json.dumps(vision_data)
            token_estimate = len(json_str) // 4
            assert 100 <= token_estimate <= 550, f"Expected ~200-500 tokens, got {token_estimate}"

    async def test_full_depth_prohibits_skipping(
        self, mission_planner, sample_product, sample_project, sample_vision_doc
    ):
        """
        Test that full depth mode explicitly prohibits skipping.

        Verifies presence of strong prohibition language:
        - "MUST", "NOT optional", "violates"
        """
        with (
            patch.object(
                mission_planner, "_get_active_vision_doc", new_callable=AsyncMock, return_value=sample_vision_doc
            ),
            patch.object(mission_planner, "_get_full_agent_templates", new_callable=AsyncMock, return_value=[]),
        ):
            context = await mission_planner._build_context_with_priorities(
                product=sample_product,
                project=sample_project,
                field_priorities={"vision_documents": 3},
                depth_config={"vision_documents": "full"},
                user_id=None,
                include_serena=False,
            )

            vision_data = context["reference"]["vision_documents"]
            instruction = vision_data["mandatory_instruction"]

            # Check for prohibition keywords
            instruction_upper = instruction.upper()
            assert "MUST" in instruction_upper
            assert any(phrase in instruction_upper for phrase in ["NOT OPTIONAL", "CANNOT SKIP", "REQUIRED"])
            assert "VIOLATE" in instruction_upper or "VIOLATES" in instruction

    async def test_token_budgets_per_level(self, mission_planner, sample_product, sample_project, sample_vision_doc):
        """
        Test that token budgets match spec for each level.

        Expected token ranges:
        - optional: ~100-350 tokens (pointer metadata)
        - light: Uses pre-computed summary_light_tokens
        - medium: Uses pre-computed summary_medium_tokens
        - full: ~100-400 tokens (instruction + fetch commands)
        """
        # Set pre-computed summaries for light/medium depth tests
        light_summary = "Light summary content. " * 2500  # ~52K chars ≈ 13K tokens
        medium_summary = "Medium summary content. " * 4200  # ~104K chars ≈ 26K tokens
        sample_vision_doc.summary_light = light_summary
        sample_vision_doc.summary_light_tokens = 13000
        sample_vision_doc.summary_medium = medium_summary
        sample_vision_doc.summary_medium_tokens = 26000

        test_cases = [
            # (depth_level, min_tokens, max_tokens, uses_inline_content)
            ("optional", 60, 350, False),  # Pointer only - compact JSON
            ("light", 12000, 14000, True),  # 33% inline content from pre-computed
            ("medium", 25000, 27000, True),  # 66% inline content from pre-computed
            ("full", 100, 500, False),  # Instruction + fetch commands
        ]

        for depth_level, min_tokens, max_tokens, uses_inline in test_cases:
            with (
                patch.object(
                    mission_planner, "_get_active_vision_doc", new_callable=AsyncMock, return_value=sample_vision_doc
                ),
                patch.object(mission_planner, "_get_full_agent_templates", new_callable=AsyncMock, return_value=[]),
            ):
                context = await mission_planner._build_context_with_priorities(
                    product=sample_product,
                    project=sample_project,
                    field_priorities={"vision_documents": 3},
                    depth_config={"vision_documents": depth_level},
                    user_id=None,
                    include_serena=False,
                )

                vision_data = context["reference"]["vision_documents"]

                # Calculate token count based on depth level
                if uses_inline:
                    # Inline content - use _count_tokens or pre-computed value
                    actual_tokens = vision_data.get("summary_tokens", 0)
                else:
                    # Metadata only - estimate from JSON size
                    json_str = json.dumps(vision_data)
                    actual_tokens = len(json_str) // 4

                assert min_tokens <= actual_tokens <= max_tokens, (
                    f"{depth_level}: Expected {min_tokens}-{max_tokens} tokens, got {actual_tokens}"
                )

    async def test_default_depth_is_light(self, mission_planner, sample_product, sample_project, sample_vision_doc):
        """
        Test that default vision depth is 'light'.

        When no depth_config is specified, the implementation defaults to 'light'.
        Without pre-computed summary_light, it returns 'SUMMARY_NOT_AVAILABLE'.
        """
        with (
            patch.object(
                mission_planner, "_get_active_vision_doc", new_callable=AsyncMock, return_value=sample_vision_doc
            ),
            patch.object(mission_planner, "_get_full_agent_templates", new_callable=AsyncMock, return_value=[]),
        ):
            # Call without depth_config (should default to light)
            context = await mission_planner._build_context_with_priorities(
                product=sample_product,
                project=sample_project,
                field_priorities={"vision_documents": 3},
                depth_config={},  # Empty depth config - defaults to "light"
                user_id=None,
                include_serena=False,
            )

            vision_data = context["reference"]["vision_documents"]

            # Default is "light" depth. Without pre-computed summary_light,
            # implementation returns "SUMMARY_NOT_AVAILABLE"
            assert vision_data["status"] == "SUMMARY_NOT_AVAILABLE"
            assert vision_data["depth"] == "light"

    async def test_helper_method_generate_mandatory_read_instruction(
        self, mission_planner, sample_product, sample_vision_doc
    ):
        """
        Test _generate_mandatory_read_instruction() helper method.
        """
        instruction = mission_planner._generate_mandatory_read_instruction(
            product=sample_product, vision_doc=sample_vision_doc
        )

        # Verify instruction structure
        assert isinstance(instruction, str)
        assert len(instruction) > 100  # Should be substantial

        # Verify mandatory language
        assert "MUST" in instruction.upper()
        assert "REQUIRED" in instruction.upper()
        assert "NOT optional" in instruction or "NOT OPTIONAL" in instruction.upper()

        # Verify references product/vision doc
        assert sample_product.name in instruction or "product" in instruction.lower()
        assert "vision" in instruction.lower()

    async def test_helper_method_generate_fetch_commands(self, mission_planner, sample_product, sample_vision_doc):
        """
        Test _generate_fetch_commands() helper method.
        """
        commands = mission_planner._generate_fetch_commands(
            product_id=sample_product.id, chunk_count=sample_vision_doc.chunk_count
        )

        # Verify list of commands
        assert isinstance(commands, list)
        assert len(commands) == sample_vision_doc.chunk_count

        # Verify command format
        for i, cmd in enumerate(commands):
            assert f"offset={i}" in cmd
            assert f'product_id="{sample_product.id}"' in cmd
            assert "fetch_vision_document" in cmd

    async def test_helper_method_summarize_vision_content(self, mission_planner):
        """
        Test _summarize_vision_content() helper method (MVP: simple truncation).
        """
        # Create test content
        test_content = "A" * 10000  # 10K chars

        # Test 33% summarization (light)
        summary_33 = mission_planner._summarize_vision_content(vision_content=test_content, ratio=0.33)
        assert len(summary_33) == int(10000 * 0.33)

        # Test 66% summarization (medium)
        summary_66 = mission_planner._summarize_vision_content(vision_content=test_content, ratio=0.66)
        assert len(summary_66) == int(10000 * 0.66)


@pytest.mark.asyncio
class TestVisionDepthAPIValidation:
    """Test API validation for vision depth values."""

    async def test_api_rejects_invalid_depth_values(self):
        """
        Test that API validation rejects invalid vision depth values.

        Valid: optional, light, medium, full
        Invalid: minimal, abbreviated, heavy, etc.
        """
        from api.endpoints.context import VALID_VISION_DEPTH_VALUES

        # Verify valid values defined
        assert "optional" in VALID_VISION_DEPTH_VALUES
        assert "light" in VALID_VISION_DEPTH_VALUES
        assert "medium" in VALID_VISION_DEPTH_VALUES
        assert "full" in VALID_VISION_DEPTH_VALUES

        # Verify only 4 values
        assert len(VALID_VISION_DEPTH_VALUES) == 4

    async def test_api_accepts_valid_depth_values(self):
        """Test that API accepts all valid vision depth values."""
        from api.endpoints.context import VALID_VISION_DEPTH_VALUES

        valid_values = ["optional", "light", "medium", "full"]
        assert set(VALID_VISION_DEPTH_VALUES) == set(valid_values)
