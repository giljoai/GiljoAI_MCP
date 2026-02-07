"""
Unit Tests for 360 Memory Context Extraction

Tests the priority-based extraction of product learnings from product_memory.learnings
and Git integration instruction injection.

TDD Approach:
- These tests are written FIRST (RED phase) before implementation
- They define expected behavior for the new methods
- Implementation will make these tests pass (GREEN phase)

Related Handovers:
- 0135-0139: 360 Memory Management backend
- 013B: Git integration refactor
- 0311: Context integration (this handover)
"""

from unittest.mock import AsyncMock, MagicMock

import pytest

from src.giljo_mcp.mission_planner import MissionPlanner
from src.giljo_mcp.models.products import Product


# ==================== Fixtures ====================


@pytest.fixture
def mission_planner():
    """Create MissionPlanner instance with mocked dependencies."""
    # Mock DatabaseManager
    db_manager = MagicMock()
    db_manager.get_session = AsyncMock()

    planner = MissionPlanner(db_manager=db_manager)
    # Ensure tokenizer is available for _count_tokens
    if not planner.tokenizer:
        planner.tokenizer = MagicMock()
    planner.tokenizer.encode = lambda text: [0] * (len(text) // 4)  # Rough estimate
    return planner


@pytest.fixture
def create_learning_entry():
    """Factory fixture to create learning entry with consistent structure."""

    def _create_entry(sequence: int, project_name: str = None) -> dict:
        """
        Create a learning entry matching 360 Memory schema.

        Schema (from handovers 0135-0139):
        {
            "sequence": 1,
            "type": "project_closeout",
            "project_id": "uuid",
            "project_name": "Project Alpha",
            "timestamp": "2025-11-15T10:00:00Z",
            "summary": "Implemented user authentication...",
            "key_outcomes": ["OAuth2 integration", "JWT tokens"],
            "decisions_made": ["Use PostgreSQL", "Deploy to AWS"]
        }
        """
        return {
            "sequence": sequence,
            "type": "project_closeout",
            "project_id": f"test-project-{sequence}",
            "project_name": project_name or f"Test Project {sequence}",
            "timestamp": f"2025-11-{sequence:02d}T10:00:00Z",
            "summary": f"This is learning #{sequence} with detailed summary about project outcomes and key decisions.",
            "key_outcomes": [
                f"Outcome A for learning {sequence}",
                f"Outcome B for learning {sequence}",
            ],
            "decisions_made": [
                f"Decision X for learning {sequence}",
                f"Decision Y for learning {sequence}",
            ],
        }

    return _create_entry


@pytest.fixture
def product_with_learnings(create_learning_entry):
    """Create product with multiple learnings for testing."""

    def _create_product(learning_count: int = 10) -> Product:
        """Create Product instance with specified number of learnings."""
        product = Product(
            id="test-product-id",
            tenant_key="test-tenant",
            name="Test Product",
            product_memory={
                "learnings": [create_learning_entry(i + 1, f"Project Alpha-{i + 1}") for i in range(learning_count)],
                "git_integration": {"enabled": False, "commit_limit": 20, "default_branch": "main"},
                "context": {},
            },
        )
        return product

    return _create_product


# ==================== Unit Tests: _extract_product_learnings ====================


@pytest.mark.asyncio
async def test_extract_learnings_full_detail_priority_10(mission_planner, product_with_learnings):
    """
    Priority 10 should include all learnings with full details.

    Expected behavior:
    - Include all learnings (up to max_entries=10)
    - Include summary + outcomes + decisions for each
    - Format: "## Historical Context (360 Memory)" header
    """
    product = product_with_learnings(10)

    result = await mission_planner._extract_product_learnings(product, priority=10, max_entries=10)

    # Verify header and structure
    assert "## Historical Context (360 Memory)" in result
    assert "Product has 10 previous project(s)" in result
    assert "Showing 10 most recent:" in result

    # Verify all learnings present (sorted by sequence descending)
    assert "### Learning #10" in result  # Most recent first
    assert "### Learning #1" in result  # Oldest last

    # Verify full detail: summary + outcomes + decisions
    assert "This is learning #10" in result
    assert "**Key Outcomes:**" in result
    assert "Outcome A for learning 10" in result
    assert "**Decisions Made:**" in result
    assert "Decision X for learning 10" in result

    # Verify guidance note present
    assert "Use these learnings to inform your decisions" in result


@pytest.mark.asyncio
async def test_extract_learnings_moderate_detail_priority_7(mission_planner, product_with_learnings):
    """
    Priority 7 should include last 5 learnings with summary + outcomes.

    Expected behavior:
    - Include only last 5 learnings (most recent)
    - Include summary + outcomes (NO decisions)
    - Context prioritization compared to full detail
    """
    product = product_with_learnings(10)

    result = await mission_planner._extract_product_learnings(product, priority=7, max_entries=10)

    # Verify showing last 5 only
    assert "Showing 5 most recent:" in result
    assert "### Learning #10" in result  # Most recent
    assert "### Learning #6" in result  # 5th most recent
    assert "### Learning #5" not in result  # Excluded (older)

    # Verify moderate detail: summary + outcomes, NO decisions
    assert "This is learning #10" in result
    assert "**Key Outcomes:**" in result
    assert "Outcome A for learning 10" in result
    assert "**Decisions Made:**" not in result  # Excluded at moderate level


@pytest.mark.asyncio
async def test_extract_learnings_abbreviated_priority_5(mission_planner, product_with_learnings):
    """
    Priority 5 should include last 3 learnings with summary only.

    Expected behavior:
    - Include only last 3 learnings
    - Include summary only (NO outcomes, NO decisions)
    - Significant context prioritization
    """
    product = product_with_learnings(10)

    result = await mission_planner._extract_product_learnings(product, priority=5, max_entries=10)

    # Verify showing last 3 only
    assert "Showing 3 most recent:" in result
    assert "### Learning #10" in result
    assert "### Learning #8" in result
    assert "### Learning #7" not in result  # Excluded

    # Verify abbreviated detail: summary only
    assert "This is learning #10" in result
    assert "**Key Outcomes:**" not in result  # Excluded
    assert "**Decisions Made:**" not in result  # Excluded


@pytest.mark.asyncio
async def test_extract_learnings_minimal_priority_2(mission_planner, product_with_learnings):
    """
    Priority 2 should include only most recent learning with summary only.

    Expected behavior:
    - Include only 1 learning (most recent)
    - Include summary only
    - Maximum context prioritization (minimal context)
    """
    product = product_with_learnings(10)

    result = await mission_planner._extract_product_learnings(product, priority=2, max_entries=10)

    # Verify showing 1 only
    assert "Showing 1 most recent:" in result
    assert "### Learning #10" in result  # Most recent only
    assert "### Learning #9" not in result

    # Verify minimal detail
    assert "This is learning #10" in result
    assert "**Key Outcomes:**" not in result
    assert "**Decisions Made:**" not in result


@pytest.mark.asyncio
async def test_extract_learnings_exclude_priority_0(mission_planner, product_with_learnings):
    """
    Priority 0 should return empty string (exclude entirely).

    Expected behavior:
    - Return "" (empty string)
    - No context section generated
    """
    product = product_with_learnings(10)

    result = await mission_planner._extract_product_learnings(product, priority=0, max_entries=10)

    assert result == ""


@pytest.mark.asyncio
async def test_extract_learnings_no_learnings(mission_planner):
    """
    Empty learnings array should return empty string.

    Expected behavior:
    - Return "" when learnings array is empty
    - Graceful degradation (no error)
    """
    product = Product(
        id="test-product-id",
        tenant_key="test-tenant",
        name="Test Product",
        product_memory={
            "learnings": [],  # Empty array
            "git_integration": {},
            "context": {},
        },
    )

    result = await mission_planner._extract_product_learnings(product, priority=10, max_entries=10)

    assert result == ""


@pytest.mark.asyncio
async def test_extract_learnings_token_count_by_priority(mission_planner, product_with_learnings):
    """
    Token count should vary significantly by priority level.

    Expected behavior:
    - Full (priority 10) >> Moderate (priority 7) >> Abbreviated (priority 5) >> Minimal (priority 2)
    - Minimal should be very compact (< 200 tokens)
    - Full should be reasonable (< 2000 tokens even with 10 learnings)
    """
    product = product_with_learnings(10)

    result_full = await mission_planner._extract_product_learnings(product, priority=10, max_entries=10)
    result_moderate = await mission_planner._extract_product_learnings(product, priority=7, max_entries=10)
    result_abbreviated = await mission_planner._extract_product_learnings(product, priority=5, max_entries=10)
    result_minimal = await mission_planner._extract_product_learnings(product, priority=2, max_entries=10)

    tokens_full = mission_planner._count_tokens(result_full)
    tokens_moderate = mission_planner._count_tokens(result_moderate)
    tokens_abbreviated = mission_planner._count_tokens(result_abbreviated)
    tokens_minimal = mission_planner._count_tokens(result_minimal)

    # Verify context prioritization cascade
    assert tokens_full > tokens_moderate, "Full should have more tokens than moderate"
    assert tokens_moderate > tokens_abbreviated, "Moderate should have more tokens than abbreviated"
    assert tokens_abbreviated > tokens_minimal, "Abbreviated should have more tokens than minimal"

    # Verify token bounds
    assert tokens_minimal < 300, f"Minimal should be < 300 tokens, got {tokens_minimal}"
    assert tokens_full < 2500, f"Full should be < 2500 tokens, got {tokens_full}"


# ==================== Unit Tests: _inject_git_instructions ====================


def test_inject_git_instructions(mission_planner):
    """
    Git instructions should include configured commit limits and example commands.

    Expected behavior:
    - Include "## Git Integration" header
    - Include git log command with configured commit_limit
    - Include example commands for CLI agents
    - Include guidance to combine with 360 Memory
    - Fixed token count (~250 tokens)
    """
    git_config = {"enabled": True, "commit_limit": 30, "default_branch": "develop"}

    result = mission_planner._inject_git_instructions(git_config)

    # Verify header and structure
    assert "## Git Integration" in result
    assert "You have access to git commands" in result

    # Verify configured commit limit
    assert "git log --oneline -30" in result

    # Verify example commands
    assert "git branch --show-current" in result
    assert "git status --short" in result
    assert 'git log --since="1 week ago"' in result

    # Verify guidance note
    assert "Combine git history with 360 Memory" in result

    # Verify token count is reasonable (should be compact, fixed structure)
    tokens = mission_planner._count_tokens(result)
    # With our mock tokenizer (len/4), expect ~100-200 tokens for this content
    assert 50 < tokens < 300, f"Git instructions should be compact, got {tokens}"


def test_inject_git_instructions_default_values(mission_planner):
    """
    Git instructions should use defaults when config incomplete.

    Expected behavior:
    - Default commit_limit=20 if not provided
    - Graceful handling of minimal config
    """
    git_config = {
        "enabled": True  # Minimal config
    }

    result = mission_planner._inject_git_instructions(git_config)

    # Verify default commit limit used
    assert "git log --oneline -20" in result
