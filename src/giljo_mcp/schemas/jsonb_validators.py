# Copyright (c) 2024-2026 GiljoAI LLC. All rights reserved.
# Licensed under the GiljoAI Community License v1.1.
# See LICENSE in the project root for terms.
# [CE] Community Edition — source-available, single-user use only.

"""Pydantic validation models for remaining JSONB columns.

These models enforce schema consistency at write time for JSONB columns
that intentionally remain as flexible storage.

Created: Handover 0840f
Updated: Handover 0962c — added AgentExecutionResult, template
    validators; fixed ProductMemoryConfig field names; removed stale todo_steps from
    AgentJobMetadata.
Updated: Sprint 002d — removed 6 dead validators + CloseoutChecklistItem.
"""

from __future__ import annotations

from pydantic import BaseModel, ConfigDict, Field, field_validator


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


# --- Settings category-specific validators (config.yaml -> DB migration) ---


class GitIntegrationSettings(BaseModel):
    """Validates git_integration block within integrations settings."""

    enabled: bool = False
    use_in_prompts: bool = False
    include_commit_history: bool = True
    max_commits: int = Field(default=50, ge=1, le=1000)
    branch_strategy: str = Field(default="main", max_length=100)


class SerenaMcpSettings(BaseModel):
    """Validates serena_mcp block within integrations settings."""

    use_in_prompts: bool = False


class IntegrationsSettingsData(BaseModel):
    """Validates settings.settings_data for category='integrations'."""

    git_integration: GitIntegrationSettings = Field(default_factory=GitIntegrationSettings)
    serena_mcp: SerenaMcpSettings = Field(default_factory=SerenaMcpSettings)


class RateLimitingSettings(BaseModel):
    """Validates rate_limiting block within security settings."""

    enabled: bool = False
    requests_per_minute: int = Field(default=60, ge=1, le=10000)


class SecuritySettingsData(BaseModel):
    """Validates settings.settings_data for category='security'."""

    ssl_enabled: bool = False
    ssl_cert_path: str | None = None
    ssl_key_path: str | None = None
    cookie_domain_whitelist: list[str] = Field(default_factory=list)
    rate_limiting: RateLimitingSettings = Field(default_factory=RateLimitingSettings)


class AgentRuntimeSettings(BaseModel):
    """Validates agent block within runtime settings."""

    max_agents: int = Field(default=10, ge=1, le=100)
    default_context_budget: int = Field(default=200000, ge=1000)
    context_warning_threshold: float = Field(default=0.8, ge=0.0, le=1.0)


class SessionRuntimeSettings(BaseModel):
    """Validates session block within runtime settings."""

    timeout_seconds: int = Field(default=3600, ge=60)
    max_concurrent: int = Field(default=5, ge=1, le=100)
    cleanup_interval: int = Field(default=300, ge=60)


class RuntimeSettingsData(BaseModel):
    """Validates settings.settings_data for category='runtime'."""

    agent: AgentRuntimeSettings = Field(default_factory=AgentRuntimeSettings)
    session: SessionRuntimeSettings = Field(default_factory=SessionRuntimeSettings)


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


# --- User.setup_selected_tools ---


class SetupSelectedTools(BaseModel):
    """Validates users.setup_selected_tools JSONB.

    List of AI coding tool names selected during setup wizard.
    Known values: claude, codex, gemini, etc.
    """

    items: list[str] = Field(default_factory=list, max_length=50)

    @field_validator("items")
    @classmethod
    def validate_items(cls, v: list[str]) -> list[str]:
        for item in v:
            if len(item) > 200:
                raise ValueError(f"Tool name exceeds 200 characters: {item[:20]}...")
        return v


# --- User.notification_preferences ---


class NotificationPreferences(BaseModel):
    """Validates users.notification_preferences JSONB.

    Known schema with two fields. No extra fields allowed —
    the schema is fully defined by DEFAULT_NOTIFICATION_PREFERENCES.
    """

    model_config = ConfigDict(extra="forbid")

    context_tuning_reminder: bool = True
    tuning_reminder_threshold: int = Field(default=10, ge=3, le=1000)


# --- APIKey.permissions ---


class APIKeyPermissions(BaseModel):
    """Validates api_keys.permissions JSONB.

    List of permission strings (e.g., ["*"], ["read", "write"]).
    """

    items: list[str] = Field(default_factory=list, max_length=50)

    @field_validator("items")
    @classmethod
    def validate_items(cls, v: list[str]) -> list[str]:
        for item in v:
            if len(item) > 200:
                raise ValueError(f"Permission string exceeds 200 characters: {item[:20]}...")
        return v


# --- MCPContextIndex.keywords ---


class ContextIndexKeywords(BaseModel):
    """Validates mcp_context_index.keywords JSONB.

    Array of keyword strings extracted via regex or LLM.
    """

    items: list[str] = Field(default_factory=list, max_length=200)

    @field_validator("items")
    @classmethod
    def validate_items(cls, v: list[str]) -> list[str]:
        for item in v:
            if len(item) > 500:
                raise ValueError(f"Keyword exceeds 500 characters: {item[:20]}...")
        return v


# --- Convenience validators ---


def validate_job_metadata(data: dict | None) -> dict | None:
    """Validate and return job_metadata dict, or None."""
    if data is None:
        return None
    return AgentJobMetadata(**data).model_dump(exclude_none=False)


def validate_git_commits(data: list | None) -> list | None:
    """Validate git_commits array."""
    if data is None:
        return None
    return [GitCommitEntry(**entry).model_dump() for entry in data]


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


# --- Category-specific settings validators ---

# Map of category name -> validator model for SettingsService to use at write boundary
SETTINGS_CATEGORY_VALIDATORS: dict[str, type[BaseModel]] = {
    "integrations": IntegrationsSettingsData,
    "security": SecuritySettingsData,
    "runtime": RuntimeSettingsData,
}


def validate_settings_by_category(category: str, data: dict) -> dict:
    """Validate settings_data dict against category-specific Pydantic model.

    For categories without a specific validator (general, network, database),
    returns data as-is (validated by the generic SettingsData model).

    Args:
        category: Settings category name
        data: Raw settings data dict

    Returns:
        Validated and normalized dict

    Raises:
        pydantic.ValidationError: if data fails schema validation
    """
    validator_cls = SETTINGS_CATEGORY_VALIDATORS.get(category)
    if validator_cls is None:
        return SettingsData(**data).model_dump(exclude_none=False)
    return validator_cls(**data).model_dump(exclude_none=False)


# --- New convenience validators (sprint 002) ---


def validate_setup_selected_tools(data: list | None) -> list | None:
    """Validate User.setup_selected_tools — list of tool name strings."""
    if data is None:
        return None
    return SetupSelectedTools(items=data).items


def validate_notification_preferences(data: dict | None) -> dict | None:
    """Validate User.notification_preferences dict."""
    if data is None:
        return None
    return NotificationPreferences(**data).model_dump()


def validate_api_key_permissions(data: list | None) -> list | None:
    """Validate APIKey.permissions — list of permission strings."""
    if data is None:
        return None
    return APIKeyPermissions(items=data).items


def validate_context_keywords(data: list | None) -> list | None:
    """Validate MCPContextIndex.keywords — list of keyword strings."""
    if data is None:
        return None
    return ContextIndexKeywords(items=data).items


def validate_string_list(
    data: list | None,
    field_name: str,
    max_items: int = 1000,
    max_length: int = 5000,
) -> list | None:
    """Generic validator for JSONB columns storing list[str].

    Used for ProductMemoryEntry list columns: key_outcomes, decisions_made,
    deliverables, tags.

    Args:
        data: List to validate, or None.
        field_name: Column name for error messages.
        max_items: Maximum number of items allowed.
        max_length: Maximum character length per item.

    Returns:
        Validated list or None.

    Raises:
        TypeError: If any item is not a string.
        ValueError: If list exceeds max_items or item exceeds max_length.
    """
    if data is None:
        return None
    if len(data) > max_items:
        raise ValueError(f"{field_name} exceeds maximum of {max_items} items (got {len(data)})")
    validated = []
    for item in data:
        if not isinstance(item, str):
            raise TypeError(f"{field_name} items must be strings, got {type(item).__name__}")
        if len(item) > max_length:
            raise ValueError(f"{field_name} item exceeds {max_length} characters")
        validated.append(item)
    return validated
