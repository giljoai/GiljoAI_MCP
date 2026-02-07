"""
Integration Tests for Context Building with 360 Memory

Tests the complete context generation workflow including 360 Memory learnings
and Git integration.

TDD Approach:
- Written FIRST (RED phase) before integration implementation
- Validates end-to-end context building with all priority levels
- Ensures token budget tracking includes 360 Memory

Related Handovers:
- 0135-0139: 360 Memory Management backend
- 013B: Git integration refactor
- 0311: Context integration (this handover)
"""

from unittest.mock import AsyncMock, MagicMock

import pytest

from src.giljo_mcp.mission_planner import MissionPlanner
from src.giljo_mcp.models.products import Product
from src.giljo_mcp.models.projects import Project


# ==================== Fixtures ====================


@pytest.fixture
def sample_product():
    """Create sample product with 360 Memory data."""

    def _create_learning(seq: int) -> dict:
        return {
            "sequence": seq,
            "type": "project_closeout",
            "project_id": f"proj-{seq}",
            "project_name": f"Alpha v{seq}.0",
            "timestamp": f"2025-11-{seq:02d}T10:00:00Z",
            "summary": f"Completed major milestone {seq} with significant architectural improvements.",
            "key_outcomes": [f"Implemented feature set {seq}", f"Achieved performance target {seq}"],
            "decisions_made": [f"Chose architecture pattern {seq}", f"Selected technology stack {seq}"],
        }

    product = Product(
        id="test-product-123",
        tenant_key="test-tenant",
        name="Integration Test Product",
        description="Product for testing 360 Memory integration",
        product_memory={
            "learnings": [_create_learning(i) for i in range(1, 6)],  # 5 learnings
            "git_integration": {
                "enabled": False,  # Default off
                "commit_limit": 20,
                "default_branch": "main",
            },
            "context": {},
        },
    )
    return product


@pytest.fixture
def sample_project():
    """Create sample project for context building."""
    return Project(
        id="test-project-456",
        product_id="test-product-123",
        tenant_key="test-tenant",
        name="Integration Test Project",
        description="Testing 360 Memory context integration",
    )


@pytest.fixture
def mission_planner_with_db():
    """Create MissionPlanner with mocked database manager."""
    # Mock DatabaseManager
    db_manager = MagicMock()
    db_manager.get_session = AsyncMock()

    planner = MissionPlanner(db_manager=db_manager)

    # Mock tokenizer for token counting
    if not planner.tokenizer:
        planner.tokenizer = MagicMock()
    planner.tokenizer.encode = lambda text: [0] * (len(text) // 4)

    # Mock Serena context fetching (not testing Serena here)
    async def mock_fetch_serena(*args, **kwargs):
        return ""

    planner._fetch_serena_codebase_context = mock_fetch_serena

    return planner


# ==================== Integration Tests ====================


@pytest.mark.asyncio
async def test_full_context_with_360_memory_and_git(mission_planner_with_db, sample_product, sample_project):
    """
    Complete context build with 360 Memory enabled and Git integration active.

    Expected behavior:
    - Include "## Historical Context (360 Memory)" section
    - Include learnings based on priority (moderate = last 5 with outcomes)
    - Include "## Git Integration" section when git enabled
    - Include git command instructions
    - Token count includes both 360 Memory and Git sections
    """
    # Enable Git integration
    sample_product.product_memory["git_integration"]["enabled"] = True

    field_priorities = {
        "product_memory.learnings": 7,  # Moderate detail
        # Other priorities would go here...
    }

    # Execute context building
    context = await mission_planner_with_db._build_context_with_priorities(
        product=sample_product,
        project=sample_project,
        field_priorities=field_priorities,
        user_id="test-user",
        include_serena=False,
    )

    # Verify 360 Memory section present
    assert "## Historical Context (360 Memory)" in context
    assert "Product has 5 previous project(s)" in context
    assert "### Learning #5" in context  # Most recent
    assert "### Learning #1" in context  # 5th most recent
    assert "**Key Outcomes:**" in context  # Moderate includes outcomes

    # Verify Git integration section present
    assert "## Git Integration" in context
    assert "git log --oneline -20" in context
    assert "git branch --show-current" in context

    # Verify guidance notes
    assert "Use these learnings to inform your decisions" in context
    assert "Combine git history with 360 Memory" in context


@pytest.mark.asyncio
async def test_context_without_360_memory(mission_planner_with_db, sample_product, sample_project):
    """
    Context build with 360 Memory priority = 0 (excluded).

    Expected behavior:
    - NO "360 Memory" section in context
    - No learning entries
    - Context still valid (other sections present)
    """
    field_priorities = {
        "product_memory.learnings": 0,  # Excluded
    }

    context = await mission_planner_with_db._build_context_with_priorities(
        product=sample_product,
        project=sample_project,
        field_priorities=field_priorities,
        user_id="test-user",
        include_serena=False,
    )

    # Verify 360 Memory section excluded (check for section header, not just text)
    assert "## Historical Context (360 Memory)" not in context
    assert "Learning #1" not in context
    assert "key_outcomes" not in context.lower()


@pytest.mark.asyncio
async def test_context_git_disabled(mission_planner_with_db, sample_product, sample_project):
    """
    Git integration disabled should not include git instructions.

    Expected behavior:
    - 360 Memory section present (if priority > 0)
    - NO Git integration section
    - No git command examples
    """
    # Ensure Git disabled
    sample_product.product_memory["git_integration"]["enabled"] = False

    field_priorities = {
        "product_memory.learnings": 7,  # Moderate (included)
    }

    context = await mission_planner_with_db._build_context_with_priorities(
        product=sample_product,
        project=sample_project,
        field_priorities=field_priorities,
        user_id="test-user",
        include_serena=False,
    )

    # Verify 360 Memory present
    assert "## Historical Context (360 Memory)" in context

    # Verify Git integration excluded
    assert "## Git Integration" not in context
    assert "git log" not in context
    assert "git branch" not in context


@pytest.mark.asyncio
async def test_token_budget_with_360_memory(mission_planner_with_db, sample_product, sample_project):
    """
    360 Memory content should be counted in token budget.

    Expected behavior:
    - Total token count increases with 360 Memory
    - Token count varies by priority level
    - Full detail (priority 10) > Moderate (priority 7) > Minimal (priority 2)
    """
    # Build context with different priority levels
    context_without = await mission_planner_with_db._build_context_with_priorities(
        product=sample_product,
        project=sample_project,
        field_priorities={"product_memory.learnings": 0},  # Excluded
        user_id="test-user",
        include_serena=False,
    )

    context_minimal = await mission_planner_with_db._build_context_with_priorities(
        product=sample_product,
        project=sample_project,
        field_priorities={"product_memory.learnings": 2},  # Minimal
        user_id="test-user",
        include_serena=False,
    )

    context_moderate = await mission_planner_with_db._build_context_with_priorities(
        product=sample_product,
        project=sample_project,
        field_priorities={"product_memory.learnings": 7},  # Moderate
        user_id="test-user",
        include_serena=False,
    )

    context_full = await mission_planner_with_db._build_context_with_priorities(
        product=sample_product,
        project=sample_project,
        field_priorities={"product_memory.learnings": 10},  # Full
        user_id="test-user",
        include_serena=False,
    )

    # Count tokens
    tokens_without = mission_planner_with_db._count_tokens(context_without)
    tokens_minimal = mission_planner_with_db._count_tokens(context_minimal)
    tokens_moderate = mission_planner_with_db._count_tokens(context_moderate)
    tokens_full = mission_planner_with_db._count_tokens(context_full)

    # Verify token counts increase with priority
    assert tokens_without < tokens_minimal, "Excluded should have fewer tokens than minimal"
    assert tokens_minimal < tokens_moderate, "Minimal should have fewer tokens than moderate"
    assert tokens_moderate < tokens_full, "Moderate should have fewer tokens than full"

    # Verify token counts within reasonable ranges
    token_diff_minimal = tokens_minimal - tokens_without
    token_diff_moderate = tokens_moderate - tokens_without
    token_diff_full = tokens_full - tokens_without

    assert token_diff_minimal > 0, "Minimal should add tokens"
    assert token_diff_moderate > token_diff_minimal, "Moderate should add more tokens than minimal"
    assert token_diff_full > token_diff_moderate, "Full should add more tokens than moderate"


@pytest.mark.asyncio
async def test_context_with_no_learnings(mission_planner_with_db, sample_product, sample_project):
    """
    Product with empty learnings array should degrade gracefully.

    Expected behavior:
    - No 360 Memory section added
    - No error thrown
    - Context still builds successfully
    """
    # Clear learnings
    sample_product.product_memory["learnings"] = []

    field_priorities = {
        "product_memory.learnings": 10,  # Full priority, but no data
    }

    context = await mission_planner_with_db._build_context_with_priorities(
        product=sample_product,
        project=sample_project,
        field_priorities=field_priorities,
        user_id="test-user",
        include_serena=False,
    )

    # Verify graceful degradation (no 360 Memory section added)
    assert "## Historical Context (360 Memory)" not in context
    assert "Learning #" not in context
    # Context should still be valid (has product name, etc.)
    assert "Integration Test Product" in context or "Product:" in context


@pytest.mark.asyncio
async def test_context_priority_detail_levels(mission_planner_with_db, sample_product, sample_project):
    """
    Different priority levels should produce different detail levels.

    Expected behavior:
    - Priority 10: All learnings with outcomes + decisions
    - Priority 7: Last 5 learnings with outcomes (no decisions)
    - Priority 5: Last 3 learnings with summary only
    - Priority 2: Last 1 learning with summary only
    """
    # Test full detail (priority 10)
    context_full = await mission_planner_with_db._build_context_with_priorities(
        product=sample_product,
        project=sample_project,
        field_priorities={"product_memory.learnings": 10},
        user_id="test-user",
        include_serena=False,
    )
    assert "**Decisions Made:**" in context_full, "Full detail should include decisions"
    assert "**Key Outcomes:**" in context_full, "Full detail should include outcomes"

    # Test moderate detail (priority 7)
    context_moderate = await mission_planner_with_db._build_context_with_priorities(
        product=sample_product,
        project=sample_project,
        field_priorities={"product_memory.learnings": 7},
        user_id="test-user",
        include_serena=False,
    )
    assert "**Key Outcomes:**" in context_moderate, "Moderate should include outcomes"
    assert "**Decisions Made:**" not in context_moderate, "Moderate should exclude decisions"

    # Test abbreviated detail (priority 5)
    context_abbreviated = await mission_planner_with_db._build_context_with_priorities(
        product=sample_product,
        project=sample_project,
        field_priorities={"product_memory.learnings": 5},
        user_id="test-user",
        include_serena=False,
    )
    assert "**Key Outcomes:**" not in context_abbreviated, "Abbreviated should exclude outcomes"
    assert "**Decisions Made:**" not in context_abbreviated, "Abbreviated should exclude decisions"
    assert "### Learning #" in context_abbreviated, "Abbreviated should still have learning headers"
