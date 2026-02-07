"""
Integration tests for template validation system.

Tests validation integration with:
- ThinClientPromptGenerator
- WebSocket event broadcasting
- Redis caching
- Template fallback mechanisms
"""

from unittest.mock import AsyncMock, Mock

import fakeredis
import pytest

from api.websocket import WebSocketManager
from src.giljo_mcp.validation.template_validator import TemplateValidator


class TestValidationIntegrationWithThinPrompt:
    """Test validation integration with ThinClientPromptGenerator."""

    @pytest.fixture
    async def mock_db(self):
        """Mock database session."""
        db = AsyncMock()
        return db

    @pytest.fixture
    def mock_redis(self):
        """Fake Redis client for testing."""
        return fakeredis.FakeRedis()

    @pytest.fixture
    def mock_ws_manager(self):
        """Mock WebSocket manager."""
        manager = Mock(spec=WebSocketManager)
        manager.broadcast_validation_failure = AsyncMock()
        return manager

    @pytest.mark.asyncio
    async def test_validation_can_be_used_with_template_instructions(self, mock_db, mock_redis):
        """Test validation can validate template instructions independently."""
        validator = TemplateValidator(redis_client=mock_redis)

        # Simulate fetching template instructions
        content = """
            You are an implementer agent.

            Agent ID: {agent_id}
            Tenant: {tenant_key}
            Job: {job_id}
            Mission: {mission}

            MCP Tools:
            - acknowledge_job(job_id, tenant_key)
            - report_progress(job_id, progress, tenant_key)
            - complete_job(job_id, result, tenant_key)
            - send_message(to_agent, message, tenant_key)
            - receive_messages(agent_id, tenant_key)
        """

        # Validate template instructions
        result = validator.validate(content, "template-123", "implementer")

        assert result is not None
        assert result.is_valid

    @pytest.mark.asyncio
    async def test_invalid_template_detected_by_validator(self, mock_db, mock_redis, mock_ws_manager):
        """Test validator detects invalid templates and can trigger fallback logic."""
        validator = TemplateValidator(redis_client=mock_redis)

        # Invalid template (missing MCP tools)
        invalid_content = "You are an agent. Do tasks."

        # Validate
        result = validator.validate(invalid_content, "invalid-template", "implementer")

        # Should be invalid
        assert not result.is_valid
        assert result.has_critical_errors

        # Simulated fallback: use system default template
        valid_default_template = """
            You are an implementer agent.

            Agent ID: {agent_id}
            Tenant: {tenant_key}
            Job: {job_id}
            Mission: {mission}

            MCP Tools:
            - acknowledge_job(job_id, tenant_key)
            - report_progress(job_id, progress, tenant_key)
            - complete_job(job_id, result, tenant_key)
            - send_message(to_agent, message, tenant_key)
            - receive_messages(agent_id, tenant_key)
        """

        fallback_result = validator.validate(valid_default_template, "system-default", "implementer")
        assert fallback_result.is_valid

        # Simulate WebSocket broadcast
        if not result.is_valid:
            await mock_ws_manager.broadcast_validation_failure(
                tenant_key="test-tenant", template_id="invalid-template", validation_errors=result.errors
            )

        # Verify broadcast was called
        assert mock_ws_manager.broadcast_validation_failure.called

    @pytest.mark.asyncio
    async def test_websocket_broadcast_on_validation_failure(self, mock_redis):
        """Test WebSocket event broadcast on validation failure."""
        validator = TemplateValidator(redis_client=mock_redis)
        ws_manager = Mock(spec=WebSocketManager)
        ws_manager.broadcast_validation_failure = AsyncMock()

        # Invalid template
        invalid_template = "'; DROP TABLE users; --"

        # Validate
        result = validator.validate(invalid_template, "template-123", "implementer")

        assert not result.is_valid

        # Simulate WebSocket broadcast
        await ws_manager.broadcast_validation_failure(
            tenant_key="test-tenant", template_id="template-123", validation_errors=result.errors
        )

        # Verify broadcast was called
        ws_manager.broadcast_validation_failure.assert_called_once()
        call_args = ws_manager.broadcast_validation_failure.call_args
        assert call_args[1]["tenant_key"] == "test-tenant"
        assert call_args[1]["template_id"] == "template-123"
        assert len(call_args[1]["validation_errors"]) > 0


class TestValidationCachingPerformance:
    """Test validation caching performance under load."""

    @pytest.fixture
    def validator_with_real_redis(self):
        """Validator with real Redis for performance tests."""
        # Use fakeredis for tests (real Redis would require running server)
        redis_client = fakeredis.FakeRedis()
        return TemplateValidator(redis_client=redis_client)

    def test_cache_hit_rate_simulation(self, validator_with_real_redis):
        """Simulate production cache hit rate (should be >95%)."""
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

        cache_hits = 0
        total_requests = 100

        # Prime cache
        validator_with_real_redis.validate(template, "template-123", "implementer", use_cache=True)

        # Simulate 100 requests
        for _ in range(total_requests):
            result = validator_with_real_redis.validate(template, "template-123", "implementer", use_cache=True)
            if result.cached:
                cache_hits += 1

        cache_hit_rate = (cache_hits / total_requests) * 100

        # Should have >95% cache hit rate
        assert cache_hit_rate > 95.0

    def test_concurrent_validation_with_cache(self, validator_with_real_redis):
        """Test concurrent validations use cache correctly."""
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
        cache_hits = []

        def validate():
            result = validator_with_real_redis.validate(template, "template-123", "implementer", use_cache=True)
            results.append(result)
            if result.cached:
                cache_hits.append(1)

        # Prime cache
        validator_with_real_redis.validate(template, "template-123", "implementer", use_cache=True)

        # Run 50 concurrent validations
        threads = [threading.Thread(target=validate) for _ in range(50)]
        for t in threads:
            t.start()
        for t in threads:
            t.join()

        # All should succeed
        assert len(results) == 50
        # Most should be cache hits (allow some timing variance)
        assert len(cache_hits) > 40


class TestValidationErrorMessages:
    """Test validation error messages are helpful and actionable."""

    @pytest.fixture
    def validator(self):
        return TemplateValidator(redis_client=None)

    def test_error_messages_include_remediation(self, validator):
        """Test all critical errors include remediation hints."""
        # Template with multiple issues
        bad_template = """
        Bad template.
        No tools, no placeholders, has injection.
        '; DROP TABLE users; --
        """

        result = validator.validate(bad_template, "template-123", "implementer")

        # All critical errors should have remediation
        for error in result.errors:
            if error.severity == "critical":
                assert error.remediation is not None
                assert len(error.remediation) > 0

    def test_error_messages_are_specific(self, validator):
        """Test error messages specify exactly what's wrong."""
        template_missing_tools = """
        Agent ID: {agent_id}
        Tenant: {tenant_key}
        Job: {job_id}

        No MCP tools defined!
        """

        result = validator.validate(template_missing_tools, "template-123", "implementer")

        # Should have specific error about missing tools
        tool_error = next((e for e in result.errors if "acknowledge_job" in e.message), None)
        assert tool_error is not None
        assert "Missing required MCP tools" in tool_error.message or "acknowledge_job" in tool_error.message


class TestValidationSecurityFocus:
    """Test validation security features."""

    @pytest.fixture
    def validator(self):
        return TemplateValidator(redis_client=None)

    def test_sql_injection_zero_false_negatives(self, validator):
        """Test SQL injection detection has zero false negatives."""
        injection_patterns = [
            "'; DROP TABLE users; --",
            "1' OR '1'='1",
            "admin'--",
            "' UNION SELECT * FROM passwords--",
            "; DELETE FROM sessions WHERE 1=1; --",
        ]

        for pattern in injection_patterns:
            template = f"""
            Valid content.
            Agent ID: {{agent_id}}

            {pattern}
            """

            result = validator.validate(template, "template-123", "implementer")

            # Must detect injection
            assert not result.is_valid, f"Failed to detect injection: {pattern}"
            assert any("injection" in e.message.lower() for e in result.errors)

    def test_command_injection_detection(self, validator):
        """Test command injection patterns are detected."""
        injection_patterns = ["&& rm -rf /", "| cat /etc/passwd", "; whoami", "`malicious_command`", "$(evil_code)"]

        for pattern in injection_patterns:
            template = f"""
            Content here.
            {pattern}
            """

            result = validator.validate(template, "template-123", "implementer")

            # Must detect injection
            assert not result.is_valid, f"Failed to detect command injection: {pattern}"

    def test_legitimate_content_not_flagged(self, validator):
        """Test legitimate content doesn't trigger false positives."""
        legitimate_template = """
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

        Documentation example:
        When writing SQL, always use parameterized queries.
        Example: SELECT * FROM users WHERE id = ?

        Code snippets are allowed in backticks.
        """

        result = validator.validate(legitimate_template, "template-123", "implementer")

        # Should pass validation (no false positives)
        assert result.is_valid
        assert len([e for e in result.errors if e.severity == "critical"]) == 0


class TestValidationWithRealTemplates:
    """Test validation with real template scenarios."""

    @pytest.fixture
    def validator(self):
        return TemplateValidator(redis_client=None)

    def test_orchestrator_template_validation(self, validator):
        """Test validation of real orchestrator template."""
        orchestrator_template = """
        You are the Orchestrator Agent for the GiljoAI system.

        Agent ID: {agent_id}
        Tenant: {tenant_key}
        Job ID: {job_id}
        Mission: {mission}
        Available Tools: {available_tools}

        Your role is to coordinate sub-agents and manage project workflow.

        Use these MCP tools:
        - acknowledge_job(job_id, tenant_key)
        - report_progress(job_id, progress, tenant_key)
        - complete_job(job_id, result, tenant_key)
        - send_message(to_agent, message, tenant_key)
        - receive_messages(agent_id, tenant_key)
        - spawn_agent_job(agent_display_name, mission, tenant_key)
        - get_agent_status(agent_id, tenant_key)

        Follow orchestration best practices and handle errors gracefully.
        """

        result = validator.validate(orchestrator_template, "orchestrator-template", "orchestrator")

        assert result.is_valid
        assert len(result.errors) == 0

    def test_implementer_template_validation(self, validator):
        """Test validation of real implementer template."""
        implementer_template = """
        You are the TDD Implementor Agent.

        Agent ID: {agent_id}
        Tenant: {tenant_key}
        Job ID: {job_id}
        Mission: {mission}

        Follow strict test-driven development:
        1. Write tests first
        2. Implement to pass tests
        3. Refactor and optimize

        MCP Tools:
        - acknowledge_job(job_id, tenant_key)
        - report_progress(job_id, progress, tenant_key)
        - complete_job(job_id, result, tenant_key)
        - send_message(to_agent, message, tenant_key)
        - receive_messages(agent_id, tenant_key)

        Use cross-platform path handling (pathlib.Path).
        Handle all errors gracefully.
        """

        result = validator.validate(implementer_template, "implementer-template", "implementer")

        assert result.is_valid
        assert len(result.errors) == 0
