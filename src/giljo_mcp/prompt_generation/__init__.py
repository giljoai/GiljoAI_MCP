"""
Prompt generation module - Generate structured prompts for agents and orchestrators.

Exports:
- SerenaInstructionGenerator: Generate Serena MCP usage instructions
"""

from .serena_instructions import SerenaInstructionGenerator

__all__ = ["SerenaInstructionGenerator"]
