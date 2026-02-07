"""
Prompt generation module - Generate structured prompts for agents and orchestrators.

Exports:
- generate_serena_instructions: Generate simplified Serena MCP notice (~50 tokens)
- MCPToolCatalogGenerator: Generate comprehensive MCP tool catalog for orchestrators and agents
"""

from .mcp_tool_catalog import MCPToolCatalogGenerator
from .serena_instructions import generate_serena_instructions


__all__ = ["MCPToolCatalogGenerator", "generate_serena_instructions"]
