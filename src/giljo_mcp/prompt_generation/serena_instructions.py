"""
Simplified Serena MCP Instructions (Handover 0277)

Generates simple 50-token notice about Serena MCP availability.
Removed 6,000 token comprehensive guide for 99% token reduction.
"""

import logging

logger = logging.getLogger(__name__)


def generate_serena_instructions(enabled: bool = True) -> str:
    """
    Generate simplified Serena MCP instructions.

    Args:
        enabled: Whether Serena MCP is enabled

    Returns:
        Simple notice (~50 tokens) if enabled, empty string if disabled
    """
    if not enabled:
        return ""

    return """
## Serena MCP Available

Serena MCP symbolic code navigation is enabled for token-efficient codebase exploration.
Key tools: find_symbol, get_symbols_overview, search_for_pattern, replace_symbol_body.
Serena provides 80-90% token savings vs full file reads.
""".strip()
