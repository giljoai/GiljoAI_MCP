# Copyright (c) 2024-2026 GiljoAI LLC. All rights reserved.
# Licensed under the GiljoAI Community License v1.1.
# See LICENSE in the project root for terms.
# [CE] Community Edition — source-available, single-user use only.

"""Pydantic validation models for remaining JSONB columns.

These models enforce schema consistency at write time for JSONB columns
that intentionally remain as flexible storage.

Created: Handover 0840f
Updated: Handover 0962c — added AgentExecutionResult, CloseoutChecklistItem, template
    validators; fixed ProductMemoryConfig field names; removed stale todo_steps from
    AgentJobMetadata.
"""

from __future__ import annotations

from pydantic import BaseModel, ConfigDict, Field


# --- AgentJob.job_metadata ---


class AgentJobMetadata(BaseModel):
    """Validates agent_jobs.job_metadata JSONB."""

    model_config = ConfigDict(extra="allow")

    field_priorities: dict | None = None
    depth_config: dict | None = None
    template_name: str | None = None


# --- AgentTemplate.meta_data ---


class AgentTemplateMetadata(BaseModel):
    """Validates agent_templates.meta_data JSONB."""

    model_config = ConfigDict(extra="allow")

    capabilities: list[str] = Field(default_factory=list)
    expertise: list[str] = Field(default_factory=list)
    typical_tasks: list[str] = Field(default_factory=list)
    tools: list[str] = Field(default_factory=list)


# --- ProductMemoryEntry arrays ---


class GitCommitEntry(BaseModel):
    """Single git commit in product_memory_entries.git_commits."""

    sha: str
    message: str
    author: str | None = None


class MemoryEntryMetrics(BaseModel):
    """Validates product_memory_entries.metrics JSONB."""

    model_config = ConfigDict(extra="allow")

    test_coverage: float | None = None
    lines_added: int | None = None
    lines_deleted: int | None = None


# --- SetupState / SystemSetup ---


class SetupValidationEntry(BaseModel):
    """Single entry in setup_state.validation_failures / validation_warnings."""

    message: str
    timestamp: str | None = None


# --- Settings.settings_data ---
# This is a per-category dict — categories are dynamic (general, network, database, etc.)
# We validate the wrapper structure, not internal category schemas


class SettingsData(BaseModel):
    """Validates settings.settings_data JSONB. Categories are dynamic."""

    model_config = ConfigDict(extra="allow")


# --- Organization.settings ---


class OrganizationSettings(BaseModel):
    """Validates organizations.settings JSONB.

    The settings blob is intentionally schema-less: keys are dynamic per
    organization and the set of recognized keys grows organically. extra="allow"
    is the correct posture here — there is no fixed schema to enforce.
    """

    model_config = ConfigDict(extra="allow")


# --- MCPSession.session_data ---


class MCPSessionData(BaseModel):
    """Validates mcp_sessions.session_data JSONB."""

    model_config = ConfigDict(extra="allow")

    client_info: dict | None = None
    capabilities: dict | None = None
    tool_call_history: list | None = None


# --- AgentExecution.result ---


class AgentExecutionResult(BaseModel):
    """Validates agent_executions.result JSONB.

    Reflects the structured completion result written by orchestration_service
    when an agent calls complete_job().
    """

    model_config = ConfigDict(extra="allow")

    summary: str | None = None
    artifacts: list[str] | None = None
    commits: list[str] | None = None


# --- Project.closeout_checklist ---


class CloseoutChecklistItem(BaseModel):
    """Single item in projects.closeout_checklist JSONB array."""

    task: str
    completed: bool = False


# --- Product.product_memory ---


class ProductMemoryConfig(BaseModel):
    """Validates products.product_memory JSONB.

    Keys match the server_default: {"github": {}, "context": {}}.
    The legacy key "git_integration" is also written by product_service in one
    code path; extra="allow" tolerates it without validator breakage.
    """

    model_config = ConfigDict(extra="allow")

    github: dict | None = None
    context: dict | None = None


# --- Product.tuning_state ---


class ProductTuningState(BaseModel):
    """Validates products.tuning_state JSONB."""

    model_config = ConfigDict(extra="allow")

    last_tuned_at: str | None = None
    last_tuned_at_sequence: int | None = None


# --- Convenience validators ---


def validate_job_metadata(data: dict | None) -> dict | None:
    """Validate and return job_metadata dict, or None."""
    if data is None:
        return None
    return AgentJobMetadata(**data).model_dump(exclude_none=False)


def validate_template_metadata(data: dict | None) -> dict | None:
    """Validate and return template meta_data dict, or None."""
    if data is None:
        return None
    return AgentTemplateMetadata(**data).model_dump(exclude_none=False)


def validate_git_commits(data: list | None) -> list | None:
    """Validate git_commits array."""
    if data is None:
        return None
    return [GitCommitEntry(**entry).model_dump() for entry in data]


def validate_memory_metrics(data: dict | None) -> dict | None:
    """Validate metrics dict."""
    if data is None:
        return None
    return MemoryEntryMetrics(**data).model_dump(exclude_none=False)


def validate_session_data(data: dict | None) -> dict | None:
    """Validate MCP session data."""
    if data is None:
        return None
    return MCPSessionData(**data).model_dump(exclude_none=False)


def validate_product_memory(data: dict | None) -> dict | None:
    """Validate product_memory dict."""
    if data is None:
        return None
    return ProductMemoryConfig(**data).model_dump(exclude_none=False)


def validate_tuning_state(data: dict | None) -> dict | None:
    """Validate tuning_state dict."""
    if data is None:
        return None
    return ProductTuningState(**data).model_dump(exclude_none=False)


def validate_execution_result(data: dict | None) -> dict | None:
    """Validate agent_executions.result dict."""
    if data is None:
        return None
    return AgentExecutionResult(**data).model_dump(exclude_none=False)


def validate_closeout_checklist(data: list | None) -> list | None:
    """Validate projects.closeout_checklist JSONB array."""
    if data is None:
        return None
    return [CloseoutChecklistItem(**item).model_dump() for item in data]


def validate_behavioral_rules(data: list | None) -> list | None:
    """Validate agent_templates.behavioral_rules — must be a list of strings."""
    if data is None:
        return None
    validated = []
    for item in data:
        if not isinstance(item, str):
            raise TypeError(f"behavioral_rules items must be strings, got {type(item).__name__}")
        validated.append(item)
    return validated


def validate_success_criteria(data: list | None) -> list | None:
    """Validate agent_templates.success_criteria — must be a list of strings."""
    if data is None:
        return None
    validated = []
    for item in data:
        if not isinstance(item, str):
            raise TypeError(f"success_criteria items must be strings, got {type(item).__name__}")
        validated.append(item)
    return validated


def validate_template_variables(data: list | None) -> list | None:
    """Validate agent_templates.variables — must be a list of strings (variable names)."""
    if data is None:
        return None
    validated = []
    for item in data:
        if not isinstance(item, str):
            raise TypeError(f"template variables items must be strings, got {type(item).__name__}")
        validated.append(item)
    return validated
