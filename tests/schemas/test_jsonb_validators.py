# Copyright (c) 2024-2026 GiljoAI LLC. All rights reserved.
# Licensed under the GiljoAI Community License v1.1.
# See LICENSE in the project root for terms.
# [CE] Community Edition — source-available, single-user use only.

"""Tests for JSONB validator functions and Pydantic models.

Covers: new validators added in Handover 0962c, fixes to ProductMemoryConfig
field names, and removal of stale todo_steps from AgentJobMetadata.

Created: Handover 0962c
"""

import pytest
from pydantic import ValidationError

from src.giljo_mcp.schemas.jsonb_validators import (
    AgentExecutionResult,
    AgentJobMetadata,
    CloseoutChecklistItem,
    ProductMemoryConfig,
    validate_behavioral_rules,
    validate_closeout_checklist,
    validate_execution_result,
    validate_git_commits,
    validate_success_criteria,
    validate_template_variables,
)

# ---------------------------------------------------------------------------
# AgentJobMetadata — stale todo_steps removed
# ---------------------------------------------------------------------------


class TestAgentJobMetadata:
    def test_valid_without_todo_steps(self):
        meta = AgentJobMetadata(field_priorities={"foo": 1}, depth_config={"level": 2})
        assert meta.field_priorities == {"foo": 1}
        assert meta.depth_config == {"level": 2}

    def test_extra_fields_allowed(self):
        meta = AgentJobMetadata(unknown_key="value")
        assert meta.model_dump()["unknown_key"] == "value"

    def test_todo_steps_not_a_declared_field(self):
        fields = AgentJobMetadata.model_fields
        assert "todo_steps" not in fields, "todo_steps was normalized to agent_todo_items table in 0402"

    def test_todo_steps_passes_via_extra_allow(self):
        meta = AgentJobMetadata(todo_steps=[1, 2, 3])
        dumped = meta.model_dump()
        assert dumped.get("todo_steps") == [1, 2, 3]


# ---------------------------------------------------------------------------
# ProductMemoryConfig — field names corrected to github / context
# ---------------------------------------------------------------------------


class TestProductMemoryConfig:
    def test_canonical_keys_accepted(self):
        cfg = ProductMemoryConfig(github={"enabled": True}, context={"summary": "test"})
        assert cfg.github == {"enabled": True}
        assert cfg.context == {"summary": "test"}

    def test_empty_dict_accepted(self):
        cfg = ProductMemoryConfig(github={}, context={})
        assert cfg.github == {}

    def test_old_keys_git_integration_via_extra(self):
        cfg = ProductMemoryConfig(git_integration={"repo_url": "https://github.com/x/y"})
        dumped = cfg.model_dump()
        assert dumped.get("git_integration") == {"repo_url": "https://github.com/x/y"}

    def test_declared_fields_are_github_and_context(self):
        fields = set(ProductMemoryConfig.model_fields.keys())
        assert "github" in fields
        assert "context" in fields
        assert "git_integration" not in fields
        assert "context_metadata" not in fields


# ---------------------------------------------------------------------------
# AgentExecutionResult — new validator
# ---------------------------------------------------------------------------


class TestAgentExecutionResult:
    def test_valid_full(self):
        result = AgentExecutionResult(
            summary="Done",
            artifacts=["path/to/file.py"],
            commits=["abc123"],
        )
        assert result.summary == "Done"
        assert result.artifacts == ["path/to/file.py"]
        assert result.commits == ["abc123"]

    def test_all_fields_optional(self):
        result = AgentExecutionResult()
        assert result.summary is None
        assert result.artifacts is None
        assert result.commits is None

    def test_extra_fields_allowed(self):
        result = AgentExecutionResult(summary="Done", extra_field="extra_value")
        assert result.model_dump()["extra_field"] == "extra_value"

    def test_validate_execution_result_none(self):
        assert validate_execution_result(None) is None

    def test_validate_execution_result_valid(self):
        data = {"summary": "Implemented feature", "artifacts": ["src/foo.py"], "commits": ["deadbeef"]}
        out = validate_execution_result(data)
        assert out["summary"] == "Implemented feature"
        assert out["artifacts"] == ["src/foo.py"]

    def test_validate_execution_result_rejects_bad_artifacts_type(self):
        with pytest.raises((ValidationError, TypeError, ValueError)):
            validate_execution_result({"artifacts": "not-a-list"})


# ---------------------------------------------------------------------------
# CloseoutChecklistItem — new validator
# ---------------------------------------------------------------------------


class TestCloseoutChecklistItem:
    def test_valid_item(self):
        item = CloseoutChecklistItem(task="Close all open PRs", completed=True)
        assert item.task == "Close all open PRs"
        assert item.completed is True

    def test_completed_defaults_to_false(self):
        item = CloseoutChecklistItem(task="Review documentation")
        assert item.completed is False

    def test_task_required(self):
        with pytest.raises(ValidationError):
            CloseoutChecklistItem()

    def test_validate_closeout_checklist_none(self):
        assert validate_closeout_checklist(None) is None

    def test_validate_closeout_checklist_valid_list(self):
        data = [
            {"task": "Deploy to staging", "completed": True},
            {"task": "Send release notes", "completed": False},
        ]
        out = validate_closeout_checklist(data)
        assert len(out) == 2
        assert out[0]["task"] == "Deploy to staging"
        assert out[0]["completed"] is True
        assert out[1]["completed"] is False

    def test_validate_closeout_checklist_rejects_missing_task(self):
        with pytest.raises(ValidationError):
            validate_closeout_checklist([{"completed": False}])


# ---------------------------------------------------------------------------
# validate_behavioral_rules
# ---------------------------------------------------------------------------


class TestValidateBehavioralRules:
    def test_none_returns_none(self):
        assert validate_behavioral_rules(None) is None

    def test_empty_list(self):
        assert validate_behavioral_rules([]) == []

    def test_valid_string_list(self):
        rules = ["Always respond in JSON", "Never hardcode credentials"]
        assert validate_behavioral_rules(rules) == rules

    def test_rejects_non_string_item(self):
        with pytest.raises(TypeError, match="behavioral_rules items must be strings"):
            validate_behavioral_rules(["valid rule", 42])

    def test_rejects_dict_item(self):
        with pytest.raises(TypeError, match="behavioral_rules items must be strings"):
            validate_behavioral_rules([{"rule": "something"}])


# ---------------------------------------------------------------------------
# validate_success_criteria
# ---------------------------------------------------------------------------


class TestValidateSuccessCriteria:
    def test_none_returns_none(self):
        assert validate_success_criteria(None) is None

    def test_empty_list(self):
        assert validate_success_criteria([]) == []

    def test_valid_string_list(self):
        criteria = ["All tests pass", "Code review approved"]
        assert validate_success_criteria(criteria) == criteria

    def test_rejects_non_string_item(self):
        with pytest.raises(TypeError, match="success_criteria items must be strings"):
            validate_success_criteria(["valid", None])

    def test_rejects_int_item(self):
        with pytest.raises(TypeError, match="success_criteria items must be strings"):
            validate_success_criteria([100])


# ---------------------------------------------------------------------------
# validate_template_variables
# ---------------------------------------------------------------------------


class TestValidateTemplateVariables:
    def test_none_returns_none(self):
        assert validate_template_variables(None) is None

    def test_empty_list(self):
        assert validate_template_variables([]) == []

    def test_valid_string_list(self):
        variables = ["project_name", "tenant_key"]
        assert validate_template_variables(variables) == variables

    def test_rejects_non_string_item(self):
        with pytest.raises(TypeError, match="template variables items must be strings"):
            validate_template_variables([{"name": "project_name"}])


# ---------------------------------------------------------------------------
# validate_git_commits — wired-up validator (existing; verify still works)
# ---------------------------------------------------------------------------


class TestValidateGitCommits:
    def test_none_returns_none(self):
        assert validate_git_commits(None) is None

    def test_valid_commits(self):
        commits = [{"sha": "abc123", "message": "Initial commit", "author": "Alice"}]
        out = validate_git_commits(commits)
        assert out[0]["sha"] == "abc123"

    def test_rejects_missing_sha(self):
        with pytest.raises(ValidationError):
            validate_git_commits([{"message": "no sha"}])

    def test_rejects_missing_message(self):
        with pytest.raises(ValidationError):
            validate_git_commits([{"sha": "abc123"}])
