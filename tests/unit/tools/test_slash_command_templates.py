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
# These prove the Read-mode section landed: trigger phrasing, both MCP tools
# (cheap list_projects + cheap fetch_context single-project read), and the
# project_id field name (the gotcha).
REQUIRED_READ_MODE_KEYWORDS = ("read project", "list_projects", "fetch_context", "project_id")


@pytest.mark.parametrize(("constant_name", "template"), GIL_ADD_TEMPLATES)
@pytest.mark.parametrize("keyword", REQUIRED_READ_MODE_KEYWORDS)
def test_gil_add_template_contains_read_mode_keyword(constant_name: str, template: str, keyword: str) -> None:
    """Every /gil_add template must reference the Read-mode keyword (case-insensitive)."""
    assert keyword in template.lower(), (
        f"{constant_name} is missing Read-mode keyword '{keyword}'. "
        f"All three /gil_add templates must document the Read flow consistently."
    )


def test_skills_version_bumped_for_frontmatter_description_sync() -> None:
    """SKILLS_VERSION must be 1.1.11 after the frontmatter description was
    updated to advertise Read mode alongside Add/Update.

    1.1.9 added Read mode (BE-5033). 1.1.10 fixed the cheap-first routing
    inside the body. 1.1.11 syncs the frontmatter description so agents
    discover the Read capability from the available-skills list (without
    that, fresh sessions saw "Add a task or project..." and reasonably
    concluded /gil_add couldn't read).
    """
    assert SKILLS_VERSION == "1.1.11", (
        f"SKILLS_VERSION is {SKILLS_VERSION!r}; expected '1.1.11' after frontmatter description sync."
    )


# Frontmatter descriptions are surfaced to every Claude session as the entry in
# the available-skills list -- the only signal an agent has when deciding
# "should I invoke /gil_add for this request?". Each description must mention
# all three capabilities (add, update, read) so a fresh agent doesn't dismiss
# the skill for read requests just because the description forgot to advertise
# the capability.
@pytest.mark.parametrize(("constant_name", "template"), GIL_ADD_TEMPLATES)
def test_gil_add_frontmatter_description_advertises_all_modes(constant_name: str, template: str) -> None:
    """Frontmatter description must mention add, update, AND read.

    Regression guard for the Apr 2026 incident where Read mode (BE-5033) and
    the routing fix (commit c1d4245c) updated the body of all three /gil_add
    templates but left the frontmatter description saying "Add a task or
    project". Agents reading the available-skills list dismissed the skill
    for read requests because the description didn't mention read.
    """
    # Pull just the first ~300 chars where the frontmatter lives so we don't
    # accidentally match body keywords.
    frontmatter_region = template[:300].lower()
    for required_keyword in ("add", "update", "read"):
        assert required_keyword in frontmatter_region, (
            f"{constant_name} frontmatter description must mention '{required_keyword}' "
            f"so agents discover the capability from the available-skills list."
        )
