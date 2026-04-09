# Copyright (c) 2024-2026 GiljoAI LLC. All rights reserved.
# Licensed under the GiljoAI Community License v1.1.
# See LICENSE in the project root for terms.
# [CE] Community Edition — source-available, single-user use only.

"""Tests for JSONB validation models and convenience functions.

Validates Pydantic models enforce schema consistency for remaining JSONB columns.
Pure unit tests — no database access required.

Created: Handover 0840
"""

import pytest
from pydantic import ValidationError

from src.giljo_mcp.schemas.jsonb_validators import (
    AgentJobMetadata,
    AgentTemplateMetadata,
    GitCommitEntry,
    MCPSessionData,
    MemoryEntryMetrics,
    OrganizationSettings,
    ProductMemoryConfig,
    ProductTuningState,
    SettingsData,
    SetupValidationEntry,
    validate_git_commits,
    validate_job_metadata,
    validate_memory_metrics,
    validate_product_memory,
    validate_session_data,
    validate_template_metadata,
    validate_tuning_state,
)

# ============================================================================
# AgentJobMetadata
# ============================================================================


class TestAgentJobMetadata:
    """Tests for AgentJobMetadata model."""

    def test_valid_full_data(self):
        data = {
            "field_priorities": {"tech_stack": 1},
            "depth_config": {"memory_last_n_projects": 5},
            "template_name": "architect",
        }
        model = AgentJobMetadata(**data)
        assert model.template_name == "architect"

    def test_empty_data_uses_defaults(self):
        model = AgentJobMetadata()
        assert model.field_priorities is None
        assert model.depth_config is None
        assert model.template_name is None

    def test_extra_keys_allowed(self):
        data = {"custom_runtime_key": "some_value", "another_key": 42}
        model = AgentJobMetadata(**data)
        assert model.custom_runtime_key == "some_value"
        assert model.another_key == 42

    def test_invalid_template_name_type(self):
        with pytest.raises(ValidationError):
            AgentJobMetadata(template_name=["not", "a", "string"])


# ============================================================================
# AgentTemplateMetadata
# ============================================================================


class TestAgentTemplateMetadata:
    """Tests for AgentTemplateMetadata model."""

    def test_valid_full_data(self):
        data = {
            "capabilities": ["code_review", "testing"],
            "expertise": ["python", "rust"],
            "typical_tasks": ["refactor", "optimize"],
            "tools": ["pytest", "ruff"],
        }
        model = AgentTemplateMetadata(**data)
        assert model.capabilities == ["code_review", "testing"]
        assert len(model.tools) == 2

    def test_empty_data_uses_defaults(self):
        model = AgentTemplateMetadata()
        assert model.capabilities == []
        assert model.expertise == []
        assert model.typical_tasks == []
        assert model.tools == []

    def test_extra_keys_allowed(self):
        model = AgentTemplateMetadata(custom_field="hello")
        assert model.custom_field == "hello"

    def test_invalid_capabilities_type(self):
        with pytest.raises(ValidationError):
            AgentTemplateMetadata(capabilities="not_a_list")


# ============================================================================
# GitCommitEntry
# ============================================================================


class TestGitCommitEntry:
    """Tests for GitCommitEntry model."""

    def test_valid_entry(self):
        entry = GitCommitEntry(sha="abc123", message="fix bug")
        assert entry.sha == "abc123"
        assert entry.message == "fix bug"
        assert entry.author is None

    def test_valid_entry_with_author(self):
        entry = GitCommitEntry(sha="abc123", message="fix bug", author="dev@example.com")
        assert entry.author == "dev@example.com"

    def test_missing_sha_raises(self):
        with pytest.raises(ValidationError):
            GitCommitEntry(message="fix bug")

    def test_missing_message_raises(self):
        with pytest.raises(ValidationError):
            GitCommitEntry(sha="abc123")

    def test_both_required_missing(self):
        with pytest.raises(ValidationError):
            GitCommitEntry()


# ============================================================================
# MemoryEntryMetrics
# ============================================================================


class TestMemoryEntryMetrics:
    """Tests for MemoryEntryMetrics model."""

    def test_valid_data(self):
        metrics = MemoryEntryMetrics(test_coverage=85.5, lines_added=100, lines_deleted=30)
        assert metrics.test_coverage == 85.5
        assert metrics.lines_added == 100
        assert metrics.lines_deleted == 30

    def test_empty_data(self):
        metrics = MemoryEntryMetrics()
        assert metrics.test_coverage is None
        assert metrics.lines_added is None
        assert metrics.lines_deleted is None

    def test_extra_keys_allowed(self):
        metrics = MemoryEntryMetrics(files_changed=15)
        assert metrics.files_changed == 15

    def test_accepts_integer_coverage(self):
        metrics = MemoryEntryMetrics(test_coverage=90)
        assert metrics.test_coverage == 90.0

    def test_invalid_lines_type(self):
        with pytest.raises(ValidationError):
            MemoryEntryMetrics(lines_added="not_a_number")


# ============================================================================
# SetupValidationEntry
# ============================================================================


class TestSetupValidationEntry:
    """Tests for SetupValidationEntry model."""

    def test_valid_entry(self):
        entry = SetupValidationEntry(message="Database not configured")
        assert entry.message == "Database not configured"
        assert entry.timestamp is None

    def test_with_timestamp(self):
        entry = SetupValidationEntry(message="error", timestamp="2026-03-25T12:00:00Z")
        assert entry.timestamp == "2026-03-25T12:00:00Z"

    def test_missing_message_raises(self):
        with pytest.raises(ValidationError):
            SetupValidationEntry()


# ============================================================================
# SettingsData & OrganizationSettings (flexible containers)
# ============================================================================


class TestSettingsData:
    """Tests for SettingsData model."""

    def test_accepts_any_keys(self):
        data = {"general": {"theme": "dark"}, "network": {"port": 8080}}
        model = SettingsData(**data)
        assert model.general == {"theme": "dark"}

    def test_empty_is_valid(self):
        model = SettingsData()
        assert model.model_dump() == {}


class TestOrganizationSettings:
    """Tests for OrganizationSettings model."""

    def test_accepts_any_keys(self):
        model = OrganizationSettings(max_users=50, plan="enterprise")
        assert model.max_users == 50

    def test_empty_is_valid(self):
        model = OrganizationSettings()
        assert model.model_dump() == {}


# ============================================================================
# MCPSessionData
# ============================================================================


class TestMCPSessionData:
    """Tests for MCPSessionData model."""

    def test_valid_data(self):
        data = {
            "client_info": {"name": "claude-code", "version": "1.0"},
            "capabilities": {"tools": True},
            "tool_call_history": [{"tool": "read_file", "ts": "2026-03-25"}],
        }
        model = MCPSessionData(**data)
        assert model.client_info["name"] == "claude-code"
        assert model.capabilities["tools"] is True

    def test_empty_data(self):
        model = MCPSessionData()
        assert model.client_info is None
        assert model.capabilities is None
        assert model.tool_call_history is None

    def test_extra_keys_allowed(self):
        model = MCPSessionData(custom="value")
        assert model.custom == "value"


# ============================================================================
# ProductMemoryConfig
# ============================================================================


class TestProductMemoryConfig:
    """Tests for ProductMemoryConfig model."""

    def test_valid_data(self):
        data = {
            "github": {"enabled": True, "commit_limit": 25},
            "context": {"last_updated": "2026-03-25"},
        }
        model = ProductMemoryConfig(**data)
        assert model.github["enabled"] is True

    def test_empty_data(self):
        model = ProductMemoryConfig()
        assert model.github is None
        assert model.context is None

    def test_extra_keys_allowed(self):
        model = ProductMemoryConfig(github={}, context={})
        assert model.github == {}


# ============================================================================
# ProductTuningState
# ============================================================================


class TestProductTuningState:
    """Tests for ProductTuningState model."""

    def test_valid_data(self):
        data = {
            "last_tuned_at": "2026-03-20T10:00:00Z",
            "last_tuned_at_sequence": 5,
        }
        model = ProductTuningState(**data)
        assert model.last_tuned_at_sequence == 5

    def test_empty_data(self):
        model = ProductTuningState()
        assert model.last_tuned_at is None
        assert model.last_tuned_at_sequence is None

    def test_extra_keys_allowed(self):
        model = ProductTuningState(custom_flag=True)
        assert model.custom_flag is True


# ============================================================================
# Convenience validator functions
# ============================================================================


class TestValidateJobMetadata:
    """Tests for validate_job_metadata convenience function."""

    def test_none_returns_none(self):
        assert validate_job_metadata(None) is None

    def test_valid_data_returns_dict(self):
        result = validate_job_metadata({"template_name": "architect"})
        assert isinstance(result, dict)
        assert result["template_name"] == "architect"

    def test_extra_keys_preserved(self):
        result = validate_job_metadata({"custom": "value", "template_name": "test"})
        assert result["custom"] == "value"
        assert result["template_name"] == "test"

    def test_invalid_data_raises(self):
        with pytest.raises(ValidationError):
            validate_job_metadata({"template_name": ["invalid"]})


class TestValidateTemplateMetadata:
    """Tests for validate_template_metadata convenience function."""

    def test_none_returns_none(self):
        assert validate_template_metadata(None) is None

    def test_valid_data_returns_dict(self):
        result = validate_template_metadata({"capabilities": ["review"]})
        assert result["capabilities"] == ["review"]

    def test_defaults_populated(self):
        result = validate_template_metadata({})
        assert result["capabilities"] == []
        assert result["expertise"] == []
        assert result["typical_tasks"] == []
        assert result["tools"] == []


class TestValidateGitCommits:
    """Tests for validate_git_commits convenience function."""

    def test_none_returns_none(self):
        assert validate_git_commits(None) is None

    def test_valid_list(self):
        commits = [
            {"sha": "abc123", "message": "fix bug"},
            {"sha": "def456", "message": "add feature", "author": "dev"},
        ]
        result = validate_git_commits(commits)
        assert len(result) == 2
        assert result[0]["sha"] == "abc123"
        assert result[1]["author"] == "dev"

    def test_missing_required_field_raises(self):
        with pytest.raises(ValidationError):
            validate_git_commits([{"sha": "abc123"}])

    def test_empty_list(self):
        result = validate_git_commits([])
        assert result == []


class TestValidateMemoryMetrics:
    """Tests for validate_memory_metrics convenience function."""

    def test_none_returns_none(self):
        assert validate_memory_metrics(None) is None

    def test_valid_data(self):
        result = validate_memory_metrics({"test_coverage": 92.5, "lines_added": 50})
        assert result["test_coverage"] == 92.5
        assert result["lines_added"] == 50

    def test_extra_keys_preserved(self):
        result = validate_memory_metrics({"custom_metric": 42})
        assert result["custom_metric"] == 42


class TestValidateSessionData:
    """Tests for validate_session_data convenience function."""

    def test_none_returns_none(self):
        assert validate_session_data(None) is None

    def test_valid_data(self):
        result = validate_session_data({"client_info": {"name": "test"}})
        assert result["client_info"]["name"] == "test"


class TestValidateProductMemory:
    """Tests for validate_product_memory convenience function."""

    def test_none_returns_none(self):
        assert validate_product_memory(None) is None

    def test_valid_data(self):
        result = validate_product_memory({"git_integration": {"enabled": True}})
        assert result["git_integration"]["enabled"] is True

    def test_extra_keys_preserved(self):
        result = validate_product_memory({"github": {}, "context": {}})
        assert "github" in result


class TestValidateTuningState:
    """Tests for validate_tuning_state convenience function."""

    def test_none_returns_none(self):
        assert validate_tuning_state(None) is None

    def test_valid_data(self):
        result = validate_tuning_state({"last_tuned_at": "2026-03-25T00:00:00Z"})
        assert result["last_tuned_at"] == "2026-03-25T00:00:00Z"

    def test_empty_dict(self):
        result = validate_tuning_state({})
        assert result["last_tuned_at"] is None
        assert result["last_tuned_at_sequence"] is None
