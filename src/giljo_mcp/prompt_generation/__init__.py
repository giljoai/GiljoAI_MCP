"""
Prompt generation module - Generate structured prompts for agents and orchestrators.

Exports:
- generate_serena_instructions: Generate simplified Serena MCP notice (~50 tokens)
"""

from .serena_instructions import generate_serena_instructions


__all__ = ["generate_serena_instructions"]
