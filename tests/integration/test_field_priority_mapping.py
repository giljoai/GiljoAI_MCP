"""
Integration tests for Priority System v2.0 - Category-Based Fetch Order

Tests verify the refactored priority system (Handover 0313) that migrates from:
- v1.0: 13 individual fields with 10/7/4 token reduction priorities
- v2.0: 6 context categories with 1/2/3/4 fetch order priorities

Priority Semantics (v2.0):
    Priority 1 (CRITICAL): Always fetch first, highest priority
    Priority 2 (IMPORTANT): Fetch if token budget allows
    Priority 3 (NICE_TO_HAVE): Fetch if budget remaining after 1 & 2
    Priority 4 (EXCLUDED): Never fetch by default

Categories (v2.0):
    - product_core: Product description + tech stack (languages, backend, frontend, database, infrastructure)
    - agent_templates: Active agent behavior configurations
    - vision_documents: Chunked vision document uploads
    - project_description: Project description, user notes, architecture notes
    - memory_360: Cumulative project history (learnings, decisions, sequential closeouts)
    - git_history: Recent commits from git integration

Handover: 0313 (Phase 6: Integration test update)
"""

from src.giljo_mcp.config.defaults import (
    DEFAULT_FIELD_PRIORITY,
    get_categories_by_priority,
    get_priority_for_category,
    validate_priority_config,
)


class TestPrioritySystemV2Defaults:
    """
    Test suite for Priority System v2.0 default configuration.

    Verifies that default priorities are correctly structured and
    follow category-based fetch order semantics.
    """

    def test_default_config_has_version_2_0(self):
        """Verify default configuration is v2.0"""
        assert DEFAULT_FIELD_PRIORITY["version"] == "2.0"

    def test_default_config_has_all_six_categories(self):
        """Verify all 6 categories are present in defaults"""
        expected_categories = {
            "product_core",
            "agent_templates",
            "vision_documents",
            "project_description",
            "memory_360",
            "git_history",
        }
        actual_categories = set(DEFAULT_FIELD_PRIORITY["priorities"].keys())
        assert actual_categories == expected_categories, f"Expected {expected_categories}, got {actual_categories}"

    def test_default_priorities_are_valid_range(self):
        """Verify all default priorities are in valid range (1-4)"""
        for category, priority in DEFAULT_FIELD_PRIORITY["priorities"].items():
            assert 1 <= priority <= 4, f"Priority {priority} for '{category}' out of valid range (1-4)"

    def test_default_has_at_least_one_critical_category(self):
        """Verify at least one category has Priority 1 (CRITICAL)"""
        critical_categories = [cat for cat, pri in DEFAULT_FIELD_PRIORITY["priorities"].items() if pri == 1]
        assert len(critical_categories) >= 1, "At least one category must have Priority 1 (CRITICAL)"

    def test_default_critical_categories(self):
        """Verify product_core and agent_templates are CRITICAL (Priority 1)"""
        assert DEFAULT_FIELD_PRIORITY["priorities"]["product_core"] == 1
        assert DEFAULT_FIELD_PRIORITY["priorities"]["agent_templates"] == 1

    def test_default_important_categories(self):
        """Verify vision_documents and project_description are IMPORTANT (Priority 2)"""
        assert DEFAULT_FIELD_PRIORITY["priorities"]["vision_documents"] == 2
        assert DEFAULT_FIELD_PRIORITY["priorities"]["project_description"] == 2

    def test_default_nice_to_have_categories(self):
        """Verify memory_360 is NICE_TO_HAVE (Priority 3)"""
        assert DEFAULT_FIELD_PRIORITY["priorities"]["memory_360"] == 3

    def test_default_excluded_categories(self):
        """Verify git_history is EXCLUDED (Priority 4)"""
        assert DEFAULT_FIELD_PRIORITY["priorities"]["git_history"] == 4


class TestPriorityHelperFunctions:
    """Test suite for priority configuration helper functions"""

    def test_get_categories_by_priority_critical(self):
        """Test retrieving all CRITICAL (Priority 1) categories"""
        critical_categories = get_categories_by_priority(1)
        assert "product_core" in critical_categories
        assert "agent_templates" in critical_categories
        assert len(critical_categories) == 2

    def test_get_categories_by_priority_important(self):
        """Test retrieving all IMPORTANT (Priority 2) categories"""
        important_categories = get_categories_by_priority(2)
        assert "vision_documents" in important_categories
        assert "project_description" in important_categories
        assert len(important_categories) == 2

    def test_get_categories_by_priority_nice_to_have(self):
        """Test retrieving all NICE_TO_HAVE (Priority 3) categories"""
        nice_to_have_categories = get_categories_by_priority(3)
        assert "memory_360" in nice_to_have_categories
        assert len(nice_to_have_categories) == 1

    def test_get_categories_by_priority_excluded(self):
        """Test retrieving all EXCLUDED (Priority 4) categories"""
        excluded_categories = get_categories_by_priority(4)
        assert "git_history" in excluded_categories
        assert len(excluded_categories) == 1

    def test_get_priority_for_category_valid(self):
        """Test retrieving priority for valid category"""
        assert get_priority_for_category("product_core") == 1
        assert get_priority_for_category("vision_documents") == 2
        assert get_priority_for_category("memory_360") == 3
        assert get_priority_for_category("git_history") == 4

    def test_get_priority_for_category_invalid(self):
        """Test retrieving priority for invalid category returns None"""
        assert get_priority_for_category("invalid_category") is None
        assert get_priority_for_category("tech_stack_languages") is None  # v1.0 field

    def test_validate_priority_config_passes(self):
        """Test that default configuration passes validation"""
        assert validate_priority_config() is True


class TestBackwardCompatibility:
    """
    Test suite for backward compatibility with v1.0 priority system.

    Ensures graceful handling of legacy v1.0 configurations if they exist.
    """

    def test_v1_priority_values_not_in_v2_defaults(self):
        """
        Verify v1.0 priority values (10, 7, 4) are not used in v2.0 defaults.

        v1.0 used: 10 (full), 7 (moderate), 4 (abbreviated), 0 (exclude)
        v2.0 uses: 1 (CRITICAL), 2 (IMPORTANT), 3 (NICE_TO_HAVE), 4 (EXCLUDED)
        """
        v1_priorities = {10, 7, 0}  # v1.0 specific values (4 is reused in v2.0)
        v2_priorities = set(DEFAULT_FIELD_PRIORITY["priorities"].values())

        # Verify no overlap with v1.0 priorities (except 4, which is reused)
        assert not v1_priorities.intersection(v2_priorities), (
            "v2.0 defaults should not contain v1.0 priority values (10, 7, 0)"
        )

    def test_v1_field_names_not_in_v2_categories(self):
        """
        Verify v1.0 individual field names are not used in v2.0 categories.

        v1.0 fields: tech_stack_languages, tech_stack_backend, etc. (13 total)
        v2.0 categories: product_core, vision_documents, etc. (6 total)
        """
        v1_field_names = {
            "tech_stack_languages",
            "tech_stack_backend",
            "tech_stack_frontend",
            "tech_stack_database",
            "tech_stack_infrastructure",
            "architecture_notes",
            "user_notes",
            "agent_templates",  # This one exists in both (renamed in v2.0)
            "recent_commits",
            "vision_docs",
        }
        v2_category_names = set(DEFAULT_FIELD_PRIORITY["priorities"].keys())

        # Only "agent_templates" should overlap (renamed but semantically same)
        overlap = v1_field_names.intersection(v2_category_names)
        assert overlap == {"agent_templates"}, f"Unexpected overlap between v1.0 fields and v2.0 categories: {overlap}"
