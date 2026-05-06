# Copyright (c) 2024-2026 GiljoAI LLC. All rights reserved.
# Licensed under the GiljoAI Community License v1.1.
# See LICENSE in the project root for terms.
# [CE] Community Edition — source-available, single-user use only.

"""Tests for taxonomy-alias prefixing on orchestrator kickoff title.

Covers `StagingPromptBuilder.build_staging_prompt` and
`MultiTerminalPromptBuilder.build_execution_prompt`. When a project carries
structured taxonomy fields (`project_type_id` and/or `series_number`), the
opening title line must read `"<alias> <name>"`. When neither is set, the
title must render the project name alone — never the random 6-char fallback
alias from `Project.taxonomy_alias`.
"""

from types import SimpleNamespace
from uuid import uuid4

from giljo_mcp.prompts.multi_terminal_prompt_builder import MultiTerminalPromptBuilder
from giljo_mcp.prompts.staging_prompt_builder import StagingPromptBuilder


def _project(*, name: str, alias: str, project_type_id, series_number) -> SimpleNamespace:
    return SimpleNamespace(
        id=uuid4(),
        name=name,
        taxonomy_alias=alias,
        project_type_id=project_type_id,
        series_number=series_number,
    )


def test_build_staging_prompt_prefixes_taxonomy_alias_when_set():
    builder = StagingPromptBuilder()
    project = _project(
        name="Token Prefix Feature",
        alias="BE-0042",
        project_type_id=uuid4(),
        series_number=42,
    )

    rendered = builder.build_staging_prompt(
        project=project,
        product=SimpleNamespace(),
        orchestrator_id="job-123",
        project_id="proj-123",
        agent_id="agent-123",
        mcp_url="http://localhost:7272",
    )

    assert 'You are the ORCHESTRATOR for project "BE-0042 Token Prefix Feature"' in rendered


def test_build_staging_prompt_omits_prefix_when_no_taxonomy():
    builder = StagingPromptBuilder()
    project = _project(
        name="Untaxonomied Project",
        alias="abc123",
        project_type_id=None,
        series_number=None,
    )

    rendered = builder.build_staging_prompt(
        project=project,
        product=SimpleNamespace(),
        orchestrator_id="job-123",
        project_id="proj-123",
        agent_id="agent-123",
        mcp_url="http://localhost:7272",
    )

    assert 'You are the ORCHESTRATOR for project "Untaxonomied Project"' in rendered
    assert "abc123" not in rendered


def test_multi_terminal_prompt_prefixes_taxonomy_alias_when_set():
    builder = MultiTerminalPromptBuilder()
    project = _project(
        name="Token Prefix Feature",
        alias="BE-0042",
        project_type_id=uuid4(),
        series_number=42,
    )

    rendered = builder.build_execution_prompt(
        orchestrator_id="job-123",
        project=project,
        agent_jobs=[],
    )

    assert "You are the ORCHESTRATOR for project 'BE-0042 Token Prefix Feature'." in rendered


def test_multi_terminal_prompt_omits_prefix_when_no_taxonomy():
    builder = MultiTerminalPromptBuilder()
    project = _project(
        name="Untaxonomied Project",
        alias="abc123",
        project_type_id=None,
        series_number=None,
    )

    rendered = builder.build_execution_prompt(
        orchestrator_id="job-123",
        project=project,
        agent_jobs=[],
    )

    assert "You are the ORCHESTRATOR for project 'Untaxonomied Project'." in rendered
    assert "abc123" not in rendered
