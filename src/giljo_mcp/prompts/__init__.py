"""Prompt builders subpackage for GiljoAI MCP.

Extracted from ThinClientPromptGenerator (Handover 0950g).
Re-exports ThinClientPromptGenerator for backward compatibility.
"""

from giljo_mcp.prompts.claude_prompt_builder import ClaudePromptBuilder
from giljo_mcp.prompts.codex_prompt_builder import CodexPromptBuilder
from giljo_mcp.prompts.staging_prompt_builder import StagingPromptBuilder
from giljo_mcp.thin_prompt_generator import ThinClientPromptGenerator


__all__ = [
    "ClaudePromptBuilder",
    "CodexPromptBuilder",
    "StagingPromptBuilder",
    "ThinClientPromptGenerator",
]
