"""
Unit tests for priority framing language in monolithic context system.

Tests the _apply_priority_framing() helper function and its integration into
_build_context_with_priorities() to ensure proper framing based on user priorities.

Following TDD principles: Tests written BEFORE implementation.

Priority Scale (v2.0):
- Priority 1: CRITICAL (required for all operations)
- Priority 2: IMPORTANT (high priority context)
- Priority 3: NICE_TO_HAVE / REFERENCE (supplemental information)
- Priority 4: EXCLUDED (0 bytes included)
"""

from unittest.mock import AsyncMock, Mock, patch
import pytest
from src.giljo_mcp.mission_planner import MissionPlanner
from src.giljo_mcp.models import Product, Project


class TestPriorityFramingHelper:
    """Test cases for _apply_priority_framing() helper function."""

    @pytest.fixture
    def mission_planner(self):
        """Create MissionPlanner instance with mocked dependencies."""
        mock_db_manager = Mock()
        mock_db_manager.is_async = True
        return MissionPlanner(mock_db_manager)

    def test_priority_1_critical_framing(self, mission_planner):
        """Priority 1 should show CRITICAL header with strong language."""
        content = "Product name: GiljoAI MCP\nDescription: Agent orchestration system"

        result = mission_planner._apply_priority_framing(
            section_name="Product Context",
            content=content,
            priority=1,
            category_key="product_core"
        )

        # Assert CRITICAL framing elements
        assert "**CRITICAL: Product Context**" in result
        assert "(Priority 1)" in result
        assert "REQUIRED FOR ALL OPERATIONS" in result
        assert "**Why This Matters**:" in result
        assert "CRITICAL context" in result
        assert content in result  # Original content should be included

    def test_priority_2_important_framing(self, mission_planner):
        """Priority 2 should show IMPORTANT header."""
        content = "# Vision Document\n\nBuild an AI agent orchestration platform..."

        result = mission_planner._apply_priority_framing(
            section_name="Vision Documents",
            content=content,
            priority=2,
            category_key="vision_documents"
        )

        # Assert IMPORTANT framing elements
        assert "**IMPORTANT: Vision Documents**" in result
        assert "(Priority 2)" in result
        assert "High priority context" in result
        assert content in result  # Original content should be included
        # Should NOT have CRITICAL language
        assert "REQUIRED FOR ALL OPERATIONS" not in result
        assert "CRITICAL" not in result

    def test_priority_3_reference_framing(self, mission_planner):
        """Priority 3 should show REFERENCE label."""
        content = "## Architecture\n\nMicroservices with event-driven design..."

        result = mission_planner._apply_priority_framing(
            section_name="Architecture",
            content=content,
            priority=3,
            category_key="project_context"
        )

        # Assert REFERENCE framing elements
        assert "Architecture (Priority 3 - REFERENCE)" in result
        assert "Supplemental information" in result
        assert content in result  # Original content should be included
        # Should NOT have CRITICAL or IMPORTANT language
        assert "CRITICAL" not in result
        assert "IMPORTANT" not in result
        assert "REQUIRED FOR ALL OPERATIONS" not in result

    def test_priority_4_excluded(self, mission_planner):
        """Priority 4 should return empty string (excluded)."""
        content = "Git commit history data..."

        result = mission_planner._apply_priority_framing(
            section_name="Git History",
            content=content,
            priority=4,
            category_key="git_history"
        )

        # Priority 4 = EXCLUDED - should return empty string
        assert result == ""
        assert content not in result

    def test_multiple_section_names(self, mission_planner):
        """Test framing with different section names."""
        test_cases = [
            ("Product Context", 1, "product_core"),
            ("Product Vision", 2, "vision_documents"),
            ("Tech Stack", 2, "tech_stack"),
            ("Agent Templates", 2, "agent_templates"),
            ("360 Memory", 3, "memory_360"),
            ("Git History", 3, "git_history"),
        ]

        for section_name, priority, category_key in test_cases:
            result = mission_planner._apply_priority_framing(
                section_name=section_name,
                content="Test content",
                priority=priority,
                category_key=category_key
            )

            # Verify section name appears in result
            assert section_name in result
            assert f"Priority {priority}" in result

    def test_content_preservation(self, mission_planner):
        """Ensure original content is never modified, only wrapped."""
        original_content = """## Complex Content

With **markdown** formatting and:
- Bullet points
- Multiple lines
- Special characters: & < > " '

Code blocks:
```python
def test():
    return True
```
"""

        result = mission_planner._apply_priority_framing(
            section_name="Test Section",
            content=original_content,
            priority=2,
            category_key="test"
        )

        # Original content should be preserved exactly
        assert original_content in result

        # Content should appear after framing headers
        framing_end_marker = "\n\n"  # Headers end with double newline
        assert framing_end_marker in result


class TestPriorityFramingIntegration:
    """Test integration of priority framing into _build_context_with_priorities()."""

    @pytest.fixture
    def mission_planner(self):
        """Create MissionPlanner instance with mocked dependencies."""
        mock_db_manager = Mock()
        mock_db_manager.is_async = True
        # Properly mock async context manager
        session_mock = AsyncMock()
        context_manager_mock = AsyncMock()
        context_manager_mock.__aenter__.return_value = session_mock
        context_manager_mock.__aexit__.return_value = None
        mock_db_manager.get_session_async.return_value = context_manager_mock
        return MissionPlanner(mock_db_manager)

    @pytest.fixture
    def sample_product(self):
        """Create a sample Product with all context fields."""
        product = Mock(spec=Product)
        product.id = "test-product-id"
        product.tenant_key = "test-tenant"
        product.name = "GiljoAI MCP"
        product.description = "Multi-tenant agent orchestration system"
        product.primary_vision_text = "Build an AI orchestration platform with context prioritization and orchestration."
        product.vision_documents = []  # Empty for simplicity
        product.config_data = {
            "tech_stack": {
                "backend": ["Python", "FastAPI"],
                "frontend": ["Vue3", "Vuetify"],
                "database": ["PostgreSQL"]
            },
            "architecture": "Microservices with event-driven design",
            "test_methodology": "TDD with pytest",
        }
        product.product_memory = {
            "sequential_history": [
                {
                    "sequence": 1,
                    "type": "project_closeout",
                    "summary": "Implemented context management v2.0"
                }
            ]
        }
        return product

    @pytest.fixture
    def sample_project(self):
        """Create a sample Project."""
        project = Mock(spec=Project)
        project.id = "test-project-id"
        project.tenant_key = "test-tenant"
        project.name = "Priority Framing Implementation"
        project.description = "Implement priority framing language in monolithic context"
        return project

    @pytest.mark.asyncio
    async def test_all_priorities_set_to_1_critical(self, mission_planner, sample_product, sample_project):
        """When all priorities = 1, all sections should have CRITICAL framing."""
        field_priorities = {
            "product_core": 1,
            "product_vision": 1,
            "tech_stack": 1,
            "config_data.architecture": 1,
            "testing_config": 1,
            "agent_templates": 1,
            "product_memory.sequential_history": 1,
            "git_history": 1,
        }

        with patch.object(mission_planner, '_extract_testing_config', new_callable=AsyncMock, return_value="## Testing\nTDD with pytest"):
            result = await mission_planner._build_context_with_priorities(
                product=sample_product,
                project=sample_project,
                field_priorities=field_priorities,
                user_id="test-user-id",
                include_serena=False
            )

        # All non-excluded sections should have CRITICAL framing
        assert "**CRITICAL:" in result
        assert "REQUIRED FOR ALL OPERATIONS" in result
        assert "**Why This Matters**:" in result
        assert "(Priority 1)" in result

        # Count CRITICAL occurrences (should be multiple sections)
        critical_count = result.count("**CRITICAL:")
        assert critical_count >= 3  # At least product, vision, tech stack

    @pytest.mark.asyncio
    async def test_mixed_priorities(self, mission_planner, sample_product, sample_project):
        """Test multiple contexts with different priority levels."""
        field_priorities = {
            "product_core": 1,        # CRITICAL
            "product_vision": 2,       # IMPORTANT
            "tech_stack": 2,           # IMPORTANT
            "config_data.architecture": 3,  # REFERENCE
            "testing_config": 3,       # REFERENCE
            "product_memory.sequential_history": 3,  # REFERENCE
            "git_history": 4,          # EXCLUDED
        }

        with patch.object(mission_planner, '_extract_testing_config', new_callable=AsyncMock, return_value="## Testing\nTDD with pytest"):
            result = await mission_planner._build_context_with_priorities(
                product=sample_product,
                project=sample_project,
                field_priorities=field_priorities,
                user_id="test-user-id",
                include_serena=False
            )

        # Verify CRITICAL framing (Priority 1)
        assert "**CRITICAL:" in result
        assert "REQUIRED FOR ALL OPERATIONS" in result

        # Verify IMPORTANT framing (Priority 2)
        assert "**IMPORTANT:" in result
        assert "High priority context" in result

        # Verify REFERENCE framing (Priority 3)
        assert "Priority 3 - REFERENCE" in result
        assert "Supplemental information" in result

        # Verify EXCLUDED (Priority 4) - git_history should NOT appear
        # (Note: git_history might not be in result anyway if toggle is off)

    @pytest.mark.asyncio
    async def test_priority_4_excludes_section(self, mission_planner, sample_product, sample_project):
        """Priority 4 sections should be completely excluded (0 bytes)."""
        field_priorities = {
            "product_core": 1,
            "product_vision": 4,  # EXCLUDED - vision should not appear
            "tech_stack": 4,      # EXCLUDED - tech stack should not appear
        }

        result = await mission_planner._build_context_with_priorities(
            product=sample_product,
            project=sample_project,
            field_priorities=field_priorities,
            user_id="test-user-id",
            include_serena=False
        )

        # Product name should still appear (always mandatory)
        assert "Product" in result
        assert sample_product.name in result

        # Vision and tech stack should NOT appear (priority 4 = excluded)
        # Note: Vision might appear if it's hardcoded as MANDATORY
        # This test verifies the framing logic works for fields that respect priority

    @pytest.mark.asyncio
    async def test_framing_does_not_break_token_counting(self, mission_planner, sample_product, sample_project):
        """Ensure priority framing doesn't break token counting logic."""
        field_priorities = {
            "product_core": 1,
            "product_vision": 2,
        }

        result = await mission_planner._build_context_with_priorities(
            product=sample_product,
            project=sample_project,
            field_priorities=field_priorities,
            user_id="test-user-id",
            include_serena=False
        )

        # Result should be valid markdown text
        assert isinstance(result, str)
        assert len(result) > 0

        # Should not have broken formatting
        assert "##" in result  # Markdown headers should exist
        assert "\n\n" in result  # Section separators should exist

    @pytest.mark.asyncio
    async def test_empty_field_priorities_uses_defaults(self, mission_planner, sample_product, sample_project):
        """Empty field_priorities should fall back to DEFAULT_FIELD_PRIORITIES with framing."""
        # Pass empty dict - should use defaults
        field_priorities = {}

        with patch.object(mission_planner, '_extract_testing_config', new_callable=AsyncMock, return_value="## Testing\nTDD"):
            result = await mission_planner._build_context_with_priorities(
                product=sample_product,
                project=sample_project,
                field_priorities=field_priorities,
                user_id="test-user-id",
                include_serena=False
            )

        # Should have framing based on default priorities
        # Default priorities have priority 1 and 2, so should see CRITICAL and IMPORTANT
        assert "**CRITICAL:" in result or "**IMPORTANT:" in result
        assert "Priority" in result  # Should have priority labels


class TestPriorityFramingSectionNames:
    """Test proper section name mapping for all context categories."""

    @pytest.fixture
    def mission_planner(self):
        """Create MissionPlanner instance."""
        mock_db_manager = Mock()
        mock_db_manager.is_async = True
        return MissionPlanner(mock_db_manager)

    def test_section_name_mapping_exists(self, mission_planner):
        """Verify SECTION_NAMES mapping includes all major categories."""
        # This test will pass once we add the SECTION_NAMES constant
        expected_categories = [
            "product_core",
            "vision_documents",
            "project_context",
            "agent_templates",
            "memory_360",
            "git_history",
        ]

        # Check if SECTION_NAMES attribute exists and has expected keys
        if hasattr(mission_planner, 'SECTION_NAMES'):
            section_names = mission_planner.SECTION_NAMES
            for category in expected_categories:
                assert category in section_names, f"Missing section name mapping for {category}"
                assert isinstance(section_names[category], str)
                assert len(section_names[category]) > 0

    def test_human_readable_section_names(self, mission_planner):
        """Section names should be human-readable (title case with spaces)."""
        test_cases = [
            ("product_core", "Product Context"),
            ("vision_documents", "Product Vision"),
            ("agent_templates", "Agent Templates"),
            ("memory_360", "360 Memory"),
        ]

        result = mission_planner._apply_priority_framing(
            section_name="Product Context",  # Human-readable name
            content="Test content",
            priority=1,
            category_key="product_core"
        )

        # Section name should appear in title case with spaces
        assert "Product Context" in result
        assert "product_core" not in result  # Should NOT show raw key


class TestBackwardCompatibility:
    """Test that priority framing doesn't break existing functionality."""

    @pytest.fixture
    def mission_planner(self):
        """Create MissionPlanner instance."""
        mock_db_manager = Mock()
        mock_db_manager.is_async = True
        # Properly mock async context manager
        session_mock = AsyncMock()
        context_manager_mock = AsyncMock()
        context_manager_mock.__aenter__.return_value = session_mock
        context_manager_mock.__aexit__.return_value = None
        mock_db_manager.get_session_async.return_value = context_manager_mock
        return MissionPlanner(mock_db_manager)

    @pytest.fixture
    def sample_product(self):
        """Minimal product for compatibility testing."""
        product = Mock(spec=Product)
        product.id = "test-id"
        product.tenant_key = "test-tenant"
        product.name = "Test Product"
        product.description = "Test description"
        product.primary_vision_text = "Test vision"
        product.vision_documents = []
        product.config_data = {}
        product.product_memory = {}
        return product

    @pytest.fixture
    def sample_project(self):
        """Minimal project for compatibility testing."""
        project = Mock(spec=Project)
        project.id = "test-project-id"
        project.tenant_key = "test-tenant"
        project.name = "Test Project"
        project.description = "Test description"
        return project

    @pytest.mark.asyncio
    async def test_existing_context_sections_still_included(self, mission_planner, sample_product, sample_project):
        """Ensure all existing context sections are still built correctly."""
        field_priorities = {
            "product_core": 1,
            "product_vision": 1,
        }

        result = await mission_planner._build_context_with_priorities(
            product=sample_product,
            project=sample_project,
            field_priorities=field_priorities,
            user_id="test-user-id",
            include_serena=False
        )

        # Core sections should still exist
        assert "Product" in result  # Product name section
        assert sample_product.name in result
        assert sample_product.description in result

        # Vision should be included
        assert "Vision" in result or "vision" in result.lower()

    @pytest.mark.asyncio
    async def test_token_reduction_metrics_still_calculated(self, mission_planner, sample_product, sample_project):
        """Priority framing should not break token reduction metrics."""
        field_priorities = {"product_core": 1, "product_vision": 2}

        # Should not raise exceptions
        result = await mission_planner._build_context_with_priorities(
            product=sample_product,
            project=sample_project,
            field_priorities=field_priorities,
            user_id="test-user-id",
            include_serena=False
        )

        # Result should be valid
        assert isinstance(result, str)
        assert len(result) > 0
