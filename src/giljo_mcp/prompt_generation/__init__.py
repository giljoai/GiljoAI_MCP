# Copyright (c) 2024-2026 GiljoAI LLC. All rights reserved.
# Licensed under the Elastic License 2.0.
# See LICENSE in the project root for terms.
# [CE] Community Edition.

"""
Prompt generation module - Generate structured prompts for agents and orchestrators.

Exports:
- generate_serena_instructions: Generate simplified Serena MCP notice (~50 tokens)
- for_role: Generate role-specific Serena MCP guidance (INF-6007)
"""

from .serena_instructions import for_role, generate_serena_instructions


__all__ = ["for_role", "generate_serena_instructions"]
