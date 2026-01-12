"""
Template validation system for GiljoAI MCP Server.

Provides runtime validation of agent templates with Redis caching
for sub-millisecond performance on cache hits.

Components:
- TemplateValidator: Main validation engine
- ValidationRule: Base class for validation rules
- ValidationError: Error/warning representation
- TemplateValidationResult: Validation result container

Usage:
    from src.giljo_mcp.validation import TemplateValidator

    validator = TemplateValidator(redis_client=redis)
    result = validator.validate(template, template_id, agent_display_name)

    if not result.is_valid:
        for error in result.errors:
            print(f"{error.severity}: {error.message}")
"""

from src.giljo_mcp.validation.template_validator import (
    TemplateValidator,
    ValidationError,
    TemplateValidationResult
)
from src.giljo_mcp.validation.rules import (
    ValidationRule,
    MCPToolsPresenceRule,
    PlaceholderVerificationRule,
    InjectionDetectionRule,
    ToolUsageBestPracticesRule
)

__all__ = [
    "TemplateValidator",
    "ValidationError",
    "TemplateValidationResult",
    "ValidationRule",
    "MCPToolsPresenceRule",
    "PlaceholderVerificationRule",
    "InjectionDetectionRule",
    "ToolUsageBestPracticesRule"
]
