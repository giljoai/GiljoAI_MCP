"""
Prompt generation module - Generate structured prompts for agents and orchestrators.

Exports:
- generate_serena_instructions: Generate simplified Serena MCP notice (~50 tokens)
- MCPToolCatalogGenerator: Generate comprehensive MCP tool catalog for orchestrators and agents
"""

from .serena_instructions import generate_serena_instructions
from .mcp_tool_catalog import MCPToolCatalogGenerator

__all__ = ["generate_serena_instructions", "MCPToolCatalogGenerator"]
