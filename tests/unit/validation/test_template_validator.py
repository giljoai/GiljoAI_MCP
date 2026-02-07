"""
Unit tests for template validation system.

Following TDD: These tests are written BEFORE implementation.
They define the expected behavior of the validation system.
"""

from datetime import datetime, timezone

import fakeredis
import pytest

from src.giljo_mcp.validation.rules import (
    InjectionDetectionRule,
    MCPToolsPresenceRule,
    PlaceholderVerificationRule,
    ToolUsageBestPracticesRule,
)
from src.giljo_mcp.validation.template_validator import TemplateValidationResult, TemplateValidator, ValidationError


class TestValidationError:
    """Test ValidationError dataclass."""

    def test_validation_error_creation(self):
        """Test creating ValidationError with all fields."""
        error = ValidationError(
            rule_id="TEST_001", severity="critical", message="Test error message", remediation="Fix by doing X"
        )

        assert error.rule_id == "TEST_001"
        assert error.severity == "critical"
        assert error.message == "Test error message"
        assert error.remediation == "Fix by doing X"

    def test_validation_error_to_dict(self):
        """Test ValidationError serialization to dict."""
        error = ValidationError(
            rule_id="TEST_001", severity="warning", message="Test warning", remediation="Optional fix"
        )

        result = error.to_dict()

        assert result["rule_id"] == "TEST_001"
        assert result["severity"] == "warning"
        assert result["message"] == "Test warning"
        assert result["remediation"] == "Optional fix"

    def test_validation_error_without_remediation(self):
        """Test ValidationError without remediation field."""
        error = ValidationError(rule_id="TEST_002", severity="info", message="Informational message")

        assert error.remediation is None
        result = error.to_dict()
        assert result["remediation"] is None


class TestTemplateValidationResult:
    """Test TemplateValidationResult dataclass."""

    def test_validation_result_creation(self):
        """Test creating validation result."""
        errors = [ValidationError("ERR_001", "critical", "Critical error")]
        warnings = [ValidationError("WARN_001", "warning", "Warning message")]

        result = TemplateValidationResult(
            is_valid=False,
            errors=errors,
            warnings=warnings,
            template_id="template-123",
            validated_at=datetime.now(timezone.utc),
            validation_duration_ms=5.2,
        )

        assert not result.is_valid
        assert len(result.errors) == 1
        assert len(result.warnings) == 1
        assert result.template_id == "template-123"
        assert result.validation_duration_ms == 5.2
        assert not result.cached

    def test_has_critical_errors_property(self):
        """Test has_critical_errors property detection."""
        # No critical errors
        result1 = TemplateValidationResult(
            is_valid=True,
            errors=[],
            warnings=[ValidationError("W1", "warning", "msg")],
            template_id="t1",
            validated_at=datetime.now(timezone.utc),
            validation_duration_ms=1.0,
        )
        assert not result1.has_critical_errors

        # Has critical errors
        result2 = TemplateValidationResult(
            is_valid=False,
            errors=[ValidationError("E1", "critical", "msg"), ValidationError("E2", "warning", "msg")],
            warnings=[],
            template_id="t2",
            validated_at=datetime.now(timezone.utc),
            validation_duration_ms=1.0,
        )
        assert result2.has_critical_errors


class TestMCPToolsPresenceRule:
    """Test MCP Tools Presence validation rule."""

    @pytest.fixture
    def rule(self):
        return MCPToolsPresenceRule()

    def test_valid_template_with_all_tools(self, rule):
        """Test template containing all required MCP tools passes."""
        template = """
        You are an implementer agent.

        Use these MCP tools:
        - acknowledge_job(job_id, tenant_key)
        - report_progress(job_id, progress, tenant_key)
        - complete_job(job_id, result, tenant_key)
        - send_message(to_agent, message, tenant_key)
        - receive_messages(agent_id, tenant_key)

        Follow the workflow.
        """

        result = rule.validate(template, "implementer")

        assert result is None  # No error means validation passed

    def test_missing_single_tool(self, rule):
        """Test template missing one required tool fails."""
        template = """
        You are an implementer agent.

        Use these tools:
        - acknowledge_job(job_id, tenant_key)
        - report_progress(job_id, progress, tenant_key)
        - complete_job(job_id, result, tenant_key)
        - receive_messages(agent_id, tenant_key)

        Note: One tool is not listed above!
        """

        result = rule.validate(template, "implementer")

        assert result is not None
        assert result.severity == "critical"
        assert "send_message" in result.message
        assert result.remediation is not None

    def test_missing_multiple_tools(self, rule):
        """Test template missing multiple required tools."""
        template = """
        You are an implementer agent.

        Use these tools:
        - acknowledge_job(job_id, tenant_key)
        - complete_job(job_id, result, tenant_key)

        Only two tools are listed above.
        """

        result = rule.validate(template, "implementer")

        assert result is not None
        assert result.severity == "critical"
        # Should mention at least one missing tool
        missing_tools = ["report_progress", "send_message", "receive_messages"]
        assert any(tool in result.message for tool in missing_tools)

    def test_empty_template_fails(self, rule):
        """Test empty template fails validation."""
        template = ""

        result = rule.validate(template, "implementer")

        assert result is not None
        assert result.severity == "critical"


class TestPlaceholderVerificationRule:
    """Test placeholder verification rule."""

    @pytest.fixture
    def rule(self):
        return PlaceholderVerificationRule()

    def test_valid_template_with_placeholders(self, rule):
        """Test template with valid placeholders passes."""
        template = """
        Agent ID: {agent_id}
        Tenant: {tenant_key}
        Job: {job_id}
        Mission: {mission}
        Tools: {available_tools}
        """

        result = rule.validate(template, "implementer")

        assert result is None

    def test_missing_required_placeholders(self, rule):
        """Test template missing required placeholders fails."""
        template = """
        You are an agent.
        Your mission is to implement code.

        No placeholders defined in this template.
        """

        result = rule.validate(template, "implementer")

        assert result is not None
        assert result.severity == "critical"
        assert "agent_id" in result.message or "tenant_key" in result.message or "job_id" in result.message

    def test_malformed_placeholders_detected(self, rule):
        """Test detection of malformed placeholder syntax."""
        template = """
        Agent ID: {agent_id}
        Tenant: tenant_key}  # Missing opening brace
        Job: {job_id
        Mission: {{mission}}  # Double braces
        """

        result = rule.validate(template, "implementer")

        # Should detect malformed syntax
        assert result is not None
        assert result.severity in ["critical", "warning"]


class TestInjectionDetectionRule:
    """Test injection detection rule."""

    @pytest.fixture
    def rule(self):
        return InjectionDetectionRule()

    def test_clean_template_passes(self, rule):
        """Test clean template without injection passes."""
        template = """
        You are a helpful agent.
        Use the acknowledge_job tool.
        Follow best practices.
        """

        result = rule.validate(template, "implementer")

        assert result is None

    def test_sql_injection_detected(self, rule):
        """Test SQL injection patterns are detected."""
        template = """
        Valid content here.

        '; DROP TABLE users; --
        """

        result = rule.validate(template, "implementer")

        assert result is not None
        assert result.severity == "critical"
        assert "injection" in result.message.lower()

    def test_command_injection_detected(self, rule):
        """Test command injection patterns are detected."""
        template = """
        Run this: && rm -rf /
        Or this: | cat /etc/passwd
        """

        result = rule.validate(template, "implementer")

        assert result is not None
        assert result.severity == "critical"

    def test_script_injection_detected(self, rule):
        """Test script injection patterns are detected."""
        template = """
        <script>alert('XSS')</script>
        <img src=x onerror=alert(1)>
        """

        result = rule.validate(template, "implementer")

        assert result is not None
        assert result.severity == "critical"

    def test_code_examples_not_flagged(self, rule):
        """Test legitimate code examples don't trigger false positives."""
        template = """
        Example SQL query for documentation:
        ```sql
        SELECT * FROM users WHERE id = ?
        ```

        Use parameterized queries, never concatenate.
        """

        result = rule.validate(template, "implementer")

        # Should not flag code examples in proper context
        # This tests that rule is smart about context
        assert result is None or result.severity != "critical"


class TestToolUsageBestPracticesRule:
    """Test tool usage best practices rule."""

    @pytest.fixture
    def rule(self):
        return ToolUsageBestPracticesRule()

    def test_template_with_best_practices(self, rule):
        """Test template following best practices passes."""
        template = """
        Always acknowledge jobs immediately.
        Report progress regularly every 10 seconds.
        Complete jobs with detailed results.
        Handle errors gracefully using report_error.
        """

        result = rule.validate(template, "implementer")

        assert result is None or result.severity == "info"

    def test_missing_error_handling_warning(self, rule):
        """Test template without error handling gets warning."""
        template = """
        Acknowledge job.
        Do the work.
        Complete job.

        No error handling mentioned!
        """

        result = rule.validate(template, "implementer")

        if result is not None:
            assert result.severity in ["warning", "info"]
            assert "error" in result.message.lower() or "report_error" in result.message.lower()


class TestTemplateValidator:
    """Test main TemplateValidator class."""

    @pytest.fixture
    def validator_no_cache(self):
        """Validator without Redis caching."""
        return TemplateValidator(redis_client=None)

    @pytest.fixture
    def validator_with_cache(self):
        """Validator with fake Redis for caching tests."""
        fake_redis = fakeredis.FakeRedis()
        return TemplateValidator(redis_client=fake_redis)

    def test_validator_initialization(self, validator_no_cache):
        """Test validator initializes with rules."""
        assert validator_no_cache.redis is None
        assert len(validator_no_cache.rules) > 0

        # Check all core rules are registered
        rule_ids = [r.rule_id for r in validator_no_cache.rules]
        assert "CRITICAL_001_MCP_TOOLS" in rule_ids
        assert "CRITICAL_002_PLACEHOLDERS" in rule_ids
        assert "CRITICAL_003_INJECTION" in rule_ids

    def test_valid_template_passes_validation(self, validator_no_cache):
        """Test template with all required elements passes validation."""
        template = """
        You are an implementer agent.

        Agent ID: {agent_id}
        Tenant: {tenant_key}
        Job: {job_id}
        Mission: {mission}

        Use these MCP tools:
        - acknowledge_job(job_id, tenant_key)
        - report_progress(job_id, progress, tenant_key)
        - complete_job(job_id, result, tenant_key)
        - send_message(to_agent, message, tenant_key)
        - receive_messages(agent_id, tenant_key)

        Always handle errors gracefully.
        """

        result = validator_no_cache.validate(template, "template-123", "implementer")

        assert result.is_valid
        assert len(result.errors) == 0
        assert result.template_id == "template-123"
        assert result.validation_duration_ms >= 0
        assert not result.cached

    def test_missing_mcp_tools_fails_validation(self, validator_no_cache):
        """Test template missing MCP tools fails validation."""
        template = """
        You are an implementer agent.
        Agent ID: {agent_id}
        Do coding tasks.
        """

        result = validator_no_cache.validate(template, "template-123", "implementer")

        assert not result.is_valid
        assert result.has_critical_errors
        assert any("acknowledge_job" in str(e.message) for e in result.errors)

    def test_injection_detected_fails_validation(self, validator_no_cache):
        """Test SQL injection patterns cause validation failure."""
        template = """
        Valid content here.
        Agent ID: {agent_id}
        acknowledge_job()

        '; DROP TABLE users; --
        """

        result = validator_no_cache.validate(template, "template-123", "implementer")

        assert not result.is_valid
        assert any("injection" in e.message.lower() for e in result.errors)

    def test_multiple_errors_collected(self, validator_no_cache):
        """Test multiple validation errors are all collected."""
        template = """
        Bad template.
        '; DROP TABLE users; --
        """

        result = validator_no_cache.validate(template, "template-123", "implementer")

        assert not result.is_valid
        # Should have errors for missing tools AND injection
        assert len(result.errors) >= 2

    def test_validation_caching_enabled(self, validator_with_cache):
        """Test validation results are cached correctly."""
        template = """
        You are an implementer agent.
        Agent ID: {agent_id}
        Tenant: {tenant_key}
        Job: {job_id}
        Mission: {mission}

        Use these MCP tools:
        - acknowledge_job(job_id, tenant_key)
        - report_progress(job_id, progress, tenant_key)
        - complete_job(job_id, result, tenant_key)
        - send_message(to_agent, message, tenant_key)
        - receive_messages(agent_id, tenant_key)
        """

        # First call - should not be cached
        result1 = validator_with_cache.validate(template, "template-123", "implementer", use_cache=True)
        assert not result1.cached
        first_duration = result1.validation_duration_ms

        # Second call - should be cached
        result2 = validator_with_cache.validate(template, "template-123", "implementer", use_cache=True)
        assert result2.cached
        assert result2.validation_duration_ms < 1.0  # Cache hit is very fast
        assert result2.is_valid == result1.is_valid

    def test_validation_cache_bypass(self, validator_with_cache):
        """Test cache can be bypassed when use_cache=False."""
        template = """
        Agent ID: {agent_id}
        Tenant: {tenant_key}
        Job: {job_id}
        Mission: {mission}
        acknowledge_job()
        report_progress()
        complete_job()
        send_message()
        receive_messages()
        """

        # First call with cache
        result1 = validator_with_cache.validate(template, "template-123", "implementer", use_cache=True)

        # Second call without cache
        result2 = validator_with_cache.validate(template, "template-123", "implementer", use_cache=False)

        assert not result1.cached
        assert not result2.cached  # Cache was bypassed

    def test_cache_invalidation_on_content_change(self, validator_with_cache):
        """Test cache key changes when template content changes."""
        template1 = """
        Original content.
        Agent ID: {agent_id}
        acknowledge_job()
        """

        template2 = """
        Modified content.
        Agent ID: {agent_id}
        acknowledge_job()
        """

        # Cache first template
        result1 = validator_with_cache.validate(template1, "template-123", "implementer", use_cache=True)

        # Different content should not use cache
        result2 = validator_with_cache.validate(template2, "template-123", "implementer", use_cache=True)

        assert not result1.cached
        assert not result2.cached  # Different content = different cache key

    def test_performance_under_10ms_uncached(self, validator_no_cache):
        """Test validation completes in <10ms without cache."""
        template = """
        Agent ID: {agent_id}
        Tenant: {tenant_key}
        Job: {job_id}
        Mission: {mission}
        acknowledge_job()
        report_progress()
        complete_job()
        send_message()
        receive_messages()
        """

        result = validator_no_cache.validate(template, "template-123", "implementer")

        assert result.validation_duration_ms < 10.0

    def test_cache_hit_under_1ms(self, validator_with_cache):
        """Test cached validation completes in <1ms."""
        template = """
        Agent ID: {agent_id}
        Tenant: {tenant_key}
        Job: {job_id}
        Mission: {mission}
        acknowledge_job()
        report_progress()
        complete_job()
        send_message()
        receive_messages()
        """

        # Prime cache
        validator_with_cache.validate(template, "template-123", "implementer", use_cache=True)

        # Measure cache hit
        result = validator_with_cache.validate(template, "template-123", "implementer", use_cache=True)

        assert result.cached
        assert result.validation_duration_ms < 1.0

    def test_thread_safe_validation(self, validator_with_cache):
        """Test validator handles concurrent validation requests."""
        import threading

        template = """
        Agent ID: {agent_id}
        Tenant: {tenant_key}
        Job: {job_id}
        Mission: {mission}
        acknowledge_job()
        report_progress()
        complete_job()
        send_message()
        receive_messages()
        """

        results = []

        def validate_template():
            result = validator_with_cache.validate(template, "template-123", "implementer")
            results.append(result)

        # Run 10 concurrent validations
        threads = [threading.Thread(target=validate_template) for _ in range(10)]
        for t in threads:
            t.start()
        for t in threads:
            t.join()

        # All should complete successfully
        assert len(results) == 10
        assert all(r is not None for r in results)
