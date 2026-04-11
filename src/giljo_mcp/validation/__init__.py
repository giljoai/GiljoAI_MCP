# Copyright (c) 2024-2026 GiljoAI LLC. All rights reserved.
# Licensed under the GiljoAI Community License v1.1.
# See LICENSE in the project root for terms.
# [CE] Community Edition — source-available, single-user use only.

"""
Template validation system for GiljoAI MCP.

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

from src.giljo_mcp.validation.rules import (
    InjectionDetectionRule,
    MCPToolsPresenceRule,
    PlaceholderVerificationRule,
    ToolUsageBestPracticesRule,
    ValidationRule,
)
from src.giljo_mcp.validation.template_validator import TemplateValidationResult, TemplateValidator, ValidationError


__all__ = [
    "InjectionDetectionRule",
    "MCPToolsPresenceRule",
    "PlaceholderVerificationRule",
    "TemplateValidationResult",
    "TemplateValidator",
    "ToolUsageBestPracticesRule",
    "ValidationError",
    "ValidationRule",
]
