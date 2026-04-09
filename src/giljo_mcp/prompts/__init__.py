# Copyright (c) 2024-2026 GiljoAI LLC. All rights reserved.
# Licensed under the GiljoAI Community License v1.1.
# See LICENSE in the project root for terms.
# [CE] Community Edition — source-available, single-user use only.

"""Prompt builders subpackage for GiljoAI MCP.

Extracted from ThinClientPromptGenerator (Handover 0950g).
Four platform-specific builders + one dispatcher.
Re-exports ThinClientPromptGenerator for backward compatibility.
"""

from giljo_mcp.prompts.claude_prompt_builder import ClaudePromptBuilder
from giljo_mcp.prompts.codex_prompt_builder import CodexPromptBuilder
from giljo_mcp.prompts.gemini_prompt_builder import GeminiPromptBuilder
from giljo_mcp.prompts.multi_terminal_prompt_builder import MultiTerminalPromptBuilder
from giljo_mcp.prompts.staging_prompt_builder import StagingPromptBuilder
from giljo_mcp.thin_prompt_generator import ThinClientPromptGenerator

__all__ = [
    "ClaudePromptBuilder",
    "CodexPromptBuilder",
    "GeminiPromptBuilder",
    "MultiTerminalPromptBuilder",
    "StagingPromptBuilder",
    "ThinClientPromptGenerator",
]
