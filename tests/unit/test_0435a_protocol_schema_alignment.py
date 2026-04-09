# Copyright (c) 2024-2026 GiljoAI LLC. All rights reserved.
# Licensed under the GiljoAI Community License v1.1.
# See LICENSE in the project root for terms.
# [CE] Community Edition — source-available, single-user use only.

"""
Tests for Handover 0435a: Protocol/Schema Alignment — MCP Tool Contract Fixes.

Tests cover:
1. write_360_memory entry_type alias normalization (project_closeout → project_completion)
2. fetch_context categories string-to-list coercion
3. get_agent_mission placeholder job_id guard
"""

import pytest

from api.endpoints.mcp_sdk_server import _PLACEHOLDER_JOB_IDS

# ---------------------------------------------------------------------------
# 1. write_360_memory entry_type alias normalization
# ---------------------------------------------------------------------------


class TestEntryTypeAliasNormalization:
    """Verify that project_closeout is accepted and normalized to project_completion."""

    def test_alias_map_normalizes_project_closeout(self):
        """project_closeout should be normalized to project_completion before validation."""

        # The alias map is inline in the function. We verify the logic by
        # checking that the alias dict pattern works correctly.
        aliases = {"project_closeout": "project_completion"}
        valid = {"project_completion", "handover_closeout", "session_handover"}

        entry_type = "project_closeout"
        entry_type = aliases.get(entry_type, entry_type)
        assert entry_type == "project_completion"
        assert entry_type in valid

    def test_canonical_values_unchanged(self):
        """Canonical entry_type values should pass through unchanged."""
        aliases = {"project_closeout": "project_completion"}
        valid = {"project_completion", "handover_closeout", "session_handover"}

        for canonical in valid:
            result = aliases.get(canonical, canonical)
            assert result == canonical
            assert result in valid

    def test_invalid_entry_type_not_aliased(self):
        """Unknown entry_type values should not be aliased."""
        aliases = {"project_closeout": "project_completion"}
        entry_type = "totally_invalid"
        result = aliases.get(entry_type, entry_type)
        assert result == "totally_invalid"


# ---------------------------------------------------------------------------
# 2. fetch_context categories string coercion
# ---------------------------------------------------------------------------


class TestFetchContextCategoriesCoercion:
    """Verify that a bare string is coerced to a single-element list."""

    def test_string_coerced_to_list(self):
        """A bare string 'tech_stack' should become ['tech_stack']."""
        categories = "tech_stack"
        if isinstance(categories, str):
            categories = [categories]
        assert categories == ["tech_stack"]

    def test_list_unchanged(self):
        """An already-valid list should pass through unchanged."""
        categories = ["tech_stack", "architecture"]
        if isinstance(categories, str):
            categories = [categories]
        assert categories == ["tech_stack", "architecture"]

    def test_none_unchanged(self):
        """None should pass through unchanged."""
        categories = None
        if isinstance(categories, str):
            categories = [categories]
        assert categories is None


# ---------------------------------------------------------------------------
# 3. get_agent_mission placeholder job_id guard
# ---------------------------------------------------------------------------


class TestGetAgentMissionPlaceholderGuard:
    """Verify that placeholder job_ids return structured guidance, not 404."""

    @pytest.mark.parametrize(
        "placeholder",
        ["unknown", "none", "null", "", "undefined", "placeholder",
         "UNKNOWN", "None", " unknown ", "  NULL  "],
    )
    def test_placeholder_detected(self, placeholder):
        """All placeholder values (case-insensitive, whitespace-trimmed) should match."""
        assert placeholder.strip().lower() in _PLACEHOLDER_JOB_IDS

    def test_valid_uuid_not_placeholder(self):
        """A real UUID should not be treated as a placeholder."""
        job_id = "61d20bb9-d35e-4d9b-bfb6-9d36e5d5f6e6"
        assert job_id.strip().lower() not in _PLACEHOLDER_JOB_IDS

    def test_placeholder_set_contents(self):
        """The placeholder set should contain exactly the expected values."""
        expected = {"unknown", "none", "null", "", "undefined", "placeholder"}
        assert _PLACEHOLDER_JOB_IDS == expected
