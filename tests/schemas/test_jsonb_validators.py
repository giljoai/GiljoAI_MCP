# Copyright (c) 2024-2026 GiljoAI LLC. All rights reserved.
# Licensed under the GiljoAI Community License v1.1.
# See LICENSE in the project root for terms.
# [CE] Community Edition — source-available, single-user use only.

"""Tests for JSONB validator functions and Pydantic models.

Covers: new validators added in Handover 0962c, fixes to ProductMemoryConfig
field names, and removal of stale todo_steps from AgentJobMetadata.
Updated: settings category validators added for config.yaml -> DB migration.

Created: Handover 0962c
"""

import pytest
from pydantic import ValidationError

from giljo_mcp.schemas.jsonb_validators import (
    SETTINGS_CATEGORY_VALIDATORS,
    AgentExecutionResult,
    AgentJobMetadata,
    GitIntegrationSettings,
    IntegrationsSettingsData,
    ProductMemoryConfig,
    RateLimitingSettings,
    RuntimeSettingsData,
    SecuritySettingsData,
    SerenaMcpSettings,
    validate_behavioral_rules,
    validate_git_commits,
    validate_settings_by_category,
    validate_success_criteria,
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


# ---------------------------------------------------------------------------
# AgentExecutionResult — model tests (validator function removed, model kept)
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


# ---------------------------------------------------------------------------
# GitIntegrationSettings — config.yaml -> DB migration validator
# ---------------------------------------------------------------------------


class TestGitIntegrationSettings:
    def test_defaults_produce_disabled_git(self):
        s = GitIntegrationSettings()
        assert s.enabled is False
        assert s.use_in_prompts is False
        assert s.include_commit_history is True
        assert s.max_commits == 50
        assert s.branch_strategy == "main"

    def test_valid_full_settings(self):
        s = GitIntegrationSettings(
            enabled=True,
            use_in_prompts=True,
            include_commit_history=False,
            max_commits=100,
            branch_strategy="develop",
        )
        assert s.enabled is True
        assert s.max_commits == 100
        assert s.branch_strategy == "develop"

    def test_string_for_enabled_is_coerced_by_pydantic(self):
        # Pydantic v2 coerces "true"/"false" strings to bool; that is acceptable behavior.
        # The validator still rejects non-boolean-like strings such as arbitrary words.
        with pytest.raises(ValidationError):
            GitIntegrationSettings(enabled="not_a_bool_at_all_xyz")

    def test_rejects_max_commits_below_minimum(self):
        with pytest.raises(ValidationError):
            GitIntegrationSettings(max_commits=0)

    def test_rejects_max_commits_above_maximum(self):
        with pytest.raises(ValidationError):
            GitIntegrationSettings(max_commits=1001)

    def test_rejects_branch_strategy_too_long(self):
        with pytest.raises(ValidationError):
            GitIntegrationSettings(branch_strategy="x" * 101)

    def test_max_commits_boundary_values_accepted(self):
        GitIntegrationSettings(max_commits=1)
        GitIntegrationSettings(max_commits=1000)


# ---------------------------------------------------------------------------
# SerenaMcpSettings
# ---------------------------------------------------------------------------


class TestSerenaMcpSettings:
    def test_defaults_to_disabled(self):
        s = SerenaMcpSettings()
        assert s.use_in_prompts is False

    def test_enabled_state(self):
        s = SerenaMcpSettings(use_in_prompts=True)
        assert s.use_in_prompts is True

    def test_non_bool_string_for_use_in_prompts_raises(self):
        # Pydantic v2 coerces "true"/"false" but rejects arbitrary strings.
        with pytest.raises(ValidationError):
            SerenaMcpSettings(use_in_prompts="not_a_boolean_xyz")


# ---------------------------------------------------------------------------
# IntegrationsSettingsData
# ---------------------------------------------------------------------------


class TestIntegrationsSettingsData:
    def test_defaults_produce_valid_structure(self):
        data = IntegrationsSettingsData()
        assert isinstance(data.git_integration, GitIntegrationSettings)
        assert isinstance(data.serena_mcp, SerenaMcpSettings)
        assert data.git_integration.enabled is False

    def test_accepts_nested_git_settings(self):
        data = IntegrationsSettingsData(
            git_integration={"enabled": True, "max_commits": 25},
            serena_mcp={"use_in_prompts": True},
        )
        assert data.git_integration.enabled is True
        assert data.git_integration.max_commits == 25
        assert data.serena_mcp.use_in_prompts is True

    def test_rejects_invalid_git_integration_type(self):
        with pytest.raises(ValidationError):
            IntegrationsSettingsData(git_integration="not_a_dict")

    def test_rejects_invalid_max_commits_nested(self):
        with pytest.raises(ValidationError):
            IntegrationsSettingsData(git_integration={"max_commits": -5})

    def test_model_dump_produces_serializable_dict(self):
        data = IntegrationsSettingsData()
        dumped = data.model_dump()
        assert "git_integration" in dumped
        assert "serena_mcp" in dumped
        assert isinstance(dumped["git_integration"]["max_commits"], int)


# ---------------------------------------------------------------------------
# RateLimitingSettings
# ---------------------------------------------------------------------------


class TestRateLimitingSettings:
    def test_defaults(self):
        r = RateLimitingSettings()
        assert r.enabled is False
        assert r.requests_per_minute == 60

    def test_rejects_requests_below_minimum(self):
        with pytest.raises(ValidationError):
            RateLimitingSettings(requests_per_minute=0)

    def test_rejects_requests_above_maximum(self):
        with pytest.raises(ValidationError):
            RateLimitingSettings(requests_per_minute=10001)

    def test_boundary_values_accepted(self):
        RateLimitingSettings(requests_per_minute=1)
        RateLimitingSettings(requests_per_minute=10000)


# ---------------------------------------------------------------------------
# SecuritySettingsData
# ---------------------------------------------------------------------------


class TestSecuritySettingsData:
    def test_defaults_produce_valid_structure(self):
        data = SecuritySettingsData()
        assert data.ssl_enabled is False
        assert data.ssl_cert_path is None
        assert data.ssl_key_path is None
        assert data.cookie_domain_whitelist == []
        assert isinstance(data.rate_limiting, RateLimitingSettings)

    def test_accepts_full_settings(self):
        data = SecuritySettingsData(
            ssl_enabled=True,
            ssl_cert_path="/etc/certs/cert.pem",
            ssl_key_path="/etc/certs/key.pem",
            cookie_domain_whitelist=["example.com", "app.example.com"],
            rate_limiting={"enabled": True, "requests_per_minute": 120},
        )
        assert data.ssl_enabled is True
        assert data.ssl_cert_path == "/etc/certs/cert.pem"
        assert len(data.cookie_domain_whitelist) == 2
        assert data.rate_limiting.enabled is True
        assert data.rate_limiting.requests_per_minute == 120

    def test_non_bool_string_for_ssl_enabled_raises(self):
        # Pydantic v2 coerces "true"/"false" but rejects arbitrary strings.
        with pytest.raises(ValidationError):
            SecuritySettingsData(ssl_enabled="not_a_boolean_xyz")

    def test_rejects_invalid_rate_limiting_value(self):
        with pytest.raises(ValidationError):
            SecuritySettingsData(rate_limiting={"requests_per_minute": -1})

    def test_cookie_domain_whitelist_accepts_empty_list(self):
        data = SecuritySettingsData(cookie_domain_whitelist=[])
        assert data.cookie_domain_whitelist == []

    def test_cookie_domain_whitelist_accepts_multiple_domains(self):
        domains = ["a.com", "b.com", "c.com"]
        data = SecuritySettingsData(cookie_domain_whitelist=domains)
        assert data.cookie_domain_whitelist == domains


# ---------------------------------------------------------------------------
# RuntimeSettingsData
# ---------------------------------------------------------------------------


class TestRuntimeSettingsData:
    def test_defaults_produce_valid_structure(self):
        data = RuntimeSettingsData()
        assert data.agent.max_agents == 10
        assert data.agent.default_context_budget == 200000
        assert data.agent.context_warning_threshold == 0.8
        assert data.session.timeout_seconds == 3600
        assert data.session.max_concurrent == 5
        assert data.session.cleanup_interval == 300

    def test_accepts_custom_agent_settings(self):
        data = RuntimeSettingsData(
            agent={"max_agents": 20, "default_context_budget": 100000, "context_warning_threshold": 0.9}
        )
        assert data.agent.max_agents == 20
        assert data.agent.context_warning_threshold == 0.9

    def test_rejects_max_agents_below_minimum(self):
        with pytest.raises(ValidationError):
            RuntimeSettingsData(agent={"max_agents": 0})

    def test_rejects_max_agents_above_maximum(self):
        with pytest.raises(ValidationError):
            RuntimeSettingsData(agent={"max_agents": 101})

    def test_rejects_context_warning_threshold_above_1(self):
        with pytest.raises(ValidationError):
            RuntimeSettingsData(agent={"context_warning_threshold": 1.1})

    def test_rejects_context_warning_threshold_below_0(self):
        with pytest.raises(ValidationError):
            RuntimeSettingsData(agent={"context_warning_threshold": -0.1})

    def test_rejects_session_timeout_below_minimum(self):
        with pytest.raises(ValidationError):
            RuntimeSettingsData(session={"timeout_seconds": 59})

    def test_rejects_session_max_concurrent_above_maximum(self):
        with pytest.raises(ValidationError):
            RuntimeSettingsData(session={"max_concurrent": 101})

    def test_rejects_cleanup_interval_below_minimum(self):
        with pytest.raises(ValidationError):
            RuntimeSettingsData(session={"cleanup_interval": 59})


# ---------------------------------------------------------------------------
# SETTINGS_CATEGORY_VALIDATORS map
# ---------------------------------------------------------------------------


class TestSettingsCategoryValidatorsMap:
    def test_map_contains_all_three_new_categories(self):
        assert "integrations" in SETTINGS_CATEGORY_VALIDATORS
        assert "security" in SETTINGS_CATEGORY_VALIDATORS
        assert "runtime" in SETTINGS_CATEGORY_VALIDATORS

    def test_map_points_to_correct_validators(self):
        assert SETTINGS_CATEGORY_VALIDATORS["integrations"] is IntegrationsSettingsData
        assert SETTINGS_CATEGORY_VALIDATORS["security"] is SecuritySettingsData
        assert SETTINGS_CATEGORY_VALIDATORS["runtime"] is RuntimeSettingsData


# ---------------------------------------------------------------------------
# validate_settings_by_category — routing function
# ---------------------------------------------------------------------------


class TestValidateSettingsByCategory:
    def test_integrations_category_validates_git_structure(self):
        result = validate_settings_by_category(
            "integrations",
            {"git_integration": {"enabled": True, "max_commits": 75}, "serena_mcp": {"use_in_prompts": False}},
        )
        assert result["git_integration"]["enabled"] is True
        assert result["git_integration"]["max_commits"] == 75

    def test_security_category_validates_ssl_fields(self):
        result = validate_settings_by_category(
            "security",
            {"ssl_enabled": True, "ssl_cert_path": "/cert.pem", "cookie_domain_whitelist": ["x.com"]},
        )
        assert result["ssl_enabled"] is True
        assert result["cookie_domain_whitelist"] == ["x.com"]

    def test_runtime_category_validates_agent_session(self):
        result = validate_settings_by_category(
            "runtime",
            {"agent": {"max_agents": 5}, "session": {"timeout_seconds": 7200}},
        )
        assert result["agent"]["max_agents"] == 5
        assert result["session"]["timeout_seconds"] == 7200

    def test_unknown_category_passes_through_as_generic_settings_data(self):
        result = validate_settings_by_category("general", {"any_key": "any_value"})
        assert result["any_key"] == "any_value"

    def test_integrations_rejects_invalid_max_commits(self):
        with pytest.raises(ValidationError):
            validate_settings_by_category(
                "integrations",
                {"git_integration": {"max_commits": 9999}},
            )

    def test_security_rejects_non_bool_string_for_ssl_enabled(self):
        # Pydantic v2 coerces "true"/"false" but rejects arbitrary strings.
        with pytest.raises(ValidationError):
            validate_settings_by_category("security", {"ssl_enabled": "not_a_boolean_xyz"})

    def test_runtime_rejects_agent_max_above_100(self):
        with pytest.raises(ValidationError):
            validate_settings_by_category("runtime", {"agent": {"max_agents": 200}})

    def test_empty_dict_produces_defaults_for_integrations(self):
        result = validate_settings_by_category("integrations", {})
        assert "git_integration" in result
        assert result["git_integration"]["enabled"] is False

    def test_empty_dict_produces_defaults_for_security(self):
        result = validate_settings_by_category("security", {})
        assert result["ssl_enabled"] is False
        assert result["cookie_domain_whitelist"] == []

    def test_empty_dict_produces_defaults_for_runtime(self):
        result = validate_settings_by_category("runtime", {})
        assert result["agent"]["max_agents"] == 10
        assert result["session"]["timeout_seconds"] == 3600
