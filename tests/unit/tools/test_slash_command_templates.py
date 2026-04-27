# Copyright (c) 2024-2026 GiljoAI LLC. All rights reserved.
# Licensed under the GiljoAI Community License v1.1.
# See LICENSE in the project root for terms.
# [CE] Community Edition — source-available, single-user use only.

"""
Unit tests asserting Read-mode keywords appear in /gil_add slash command templates.

Read mode was added so that pasting project UUIDs (or saying
"read project X") routes through `list_projects` + a `project_id`-keyed jq
filter. The gotcha — the field is `project_id`, NOT `id` — must surface in
every platform-specific template (Claude Code, Gemini CLI, Codex CLI).

These tests guard against regressions where one of the three constants drifts
out of sync and silently loses the Read-mode guidance.
"""

import pytest

from giljo_mcp.tools.slash_command_templates import (
    GIL_ADD_CODEX_SKILL_MD,
    GIL_ADD_GEMINI_TOML,
    GIL_ADD_MD,
    SKILLS_VERSION,
)


# (constant_name, constant_value) tuples for parametrization.
GIL_ADD_TEMPLATES = [
    ("GIL_ADD_MD", GIL_ADD_MD),
    ("GIL_ADD_GEMINI_TOML", GIL_ADD_GEMINI_TOML),
    ("GIL_ADD_CODEX_SKILL_MD", GIL_ADD_CODEX_SKILL_MD),
]

# Required lowercase substrings that must appear in every /gil_add template.
# These prove the Read-mode section landed: trigger phrasing, MCP tool name,
# and the project_id field name (the gotcha).
REQUIRED_READ_MODE_KEYWORDS = ("read project", "list_projects", "project_id")


@pytest.mark.parametrize(("constant_name", "template"), GIL_ADD_TEMPLATES)
@pytest.mark.parametrize("keyword", REQUIRED_READ_MODE_KEYWORDS)
def test_gil_add_template_contains_read_mode_keyword(constant_name: str, template: str, keyword: str) -> None:
    """Every /gil_add template must reference the Read-mode keyword (case-insensitive)."""
    assert keyword in template.lower(), (
        f"{constant_name} is missing Read-mode keyword '{keyword}'. "
        f"All three /gil_add templates must document the Read flow consistently."
    )


def test_skills_version_bumped_for_read_mode() -> None:
    """SKILLS_VERSION must be 1.1.9 once Read mode lands in /gil_add templates."""
    assert SKILLS_VERSION == "1.1.9", f"SKILLS_VERSION is {SKILLS_VERSION!r}; expected '1.1.9' after adding Read mode."
