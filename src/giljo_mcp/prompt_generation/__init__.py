# Copyright (c) 2024-2026 GiljoAI LLC. All rights reserved.
# Licensed under the GiljoAI Community License v1.1.
# See LICENSE in the project root for terms.
# [CE] Community Edition — source-available, single-user use only.

"""
Prompt generation module - Generate structured prompts for agents and orchestrators.

Exports:
- generate_serena_instructions: Generate simplified Serena MCP notice (~50 tokens)
"""

from .serena_instructions import generate_serena_instructions

__all__ = ["generate_serena_instructions"]
