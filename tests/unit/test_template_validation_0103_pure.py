# Copyright (c) 2024-2026 GiljoAI LLC. All rights reserved.
# Licensed under the GiljoAI Community License v1.1.
# See LICENSE in the project root for terms.
# [CE] Community Edition — source-available, single-user use only.

"""Unit tests for pure template validation functions (Handover 0103 Phase 8).

Tests pure validation functions that do not require database access:
- slugify_name()
- validate_system_prompt()
- get_role_color()

Split from test_template_validation_0103.py for maintainability.
"""

from giljo_mcp.template_validation import (
    get_role_color,
    slugify_name,
)


class TestSlugifyName:
    """Test slugify_name function."""

    def test_role_only(self):
        """Test generating name from role only."""
        assert slugify_name("orchestrator") == "orchestrator"

    def test_role_with_suffix(self):
        """Test generating name from role and suffix."""
        assert slugify_name("orchestrator", "AmazingGuy") == "orchestrator-amazingguy"

    def test_spaces_in_suffix(self):
        """Test suffix with spaces converted to hyphens."""
        assert slugify_name("tester", "Fast Runner") == "tester-fast-runner"

    def test_underscores_in_suffix(self):
        """Test suffix with underscores converted to hyphens."""
        assert slugify_name("implementer", "API_Handler") == "implementer-api-handler"

    def test_special_chars_removed(self):
        """Test suffix with special characters removed."""
        assert slugify_name("analyzer", "Code@Guru!") == "analyzer-codeguru"

    def test_empty_suffix(self):
        """Test empty suffix returns role only."""
        assert slugify_name("reviewer", "") == "reviewer"

    def test_none_suffix(self):
        """Test None suffix returns role only."""
        assert slugify_name("documenter", None) == "documenter"

    def test_multiple_spaces_consolidated(self):
        """Test multiple consecutive spaces consolidated into single hyphens."""
        result = slugify_name("tester", "Super  Fast   Runner")
        # slugify_name collapses double hyphens into single hyphens
        assert result == "tester-super-fast-runner"

    def test_mixed_case_suffix(self):
        """Test mixed case suffix converted to lowercase."""
        assert slugify_name("backend", "APIHandlerV2") == "backend-apihandlerv2"

    def test_suffix_with_numbers(self):
        """Test suffix with numbers preserved."""
        assert slugify_name("orchestrator", "Version123") == "orchestrator-version123"


class TestGetRoleColor:
    """Test get_role_color function."""

    def test_orchestrator_color(self):
        """Test orchestrator returns correct color."""
        assert get_role_color("orchestrator") == "#D4A574"

    def test_analyzer_color(self):
        """Test analyzer returns correct color."""
        assert get_role_color("analyzer") == "#E74C3C"

    def test_implementer_color(self):
        """Test implementer returns correct color."""
        assert get_role_color("implementer") == "#3498DB"

    def test_tester_color(self):
        """Test tester returns correct color."""
        assert get_role_color("tester") == "#FFC300"

    def test_reviewer_color(self):
        """Test reviewer returns correct color."""
        assert get_role_color("reviewer") == "#9B59B6"

    def test_documenter_color(self):
        """Test documenter returns correct color."""
        assert get_role_color("documenter") == "#27AE60"

    def test_designer_color(self):
        """Test designer returns correct color."""
        assert get_role_color("designer") == "#9B59B6"

    def test_frontend_color(self):
        """Test frontend returns correct color."""
        assert get_role_color("frontend") == "#3498DB"

    def test_backend_color(self):
        """Test backend returns correct color."""
        assert get_role_color("backend") == "#2ECC71"

    def test_unknown_role_returns_default(self):
        """Test unknown role returns default gray color."""
        assert get_role_color("unknown_role") == "#90A4AE"

    def test_empty_role_returns_default(self):
        """Test empty role returns default gray color."""
        assert get_role_color("") == "#90A4AE"

    def test_case_sensitive(self):
        """Test role colors are case-sensitive."""
        assert get_role_color("Orchestrator") == "#90A4AE"  # Uppercase should return default

    def test_all_documented_roles(self):
        """Test all documented roles have colors defined."""
        documented_roles = [
            "orchestrator",
            "analyzer",
            "designer",
            "frontend",
            "backend",
            "implementer",
            "tester",
            "reviewer",
            "documenter",
        ]

        for role in documented_roles:
            color = get_role_color(role)
            assert color.startswith("#")
            assert len(color) == 7
            assert color != "#90A4AE"  # Should not be default color
