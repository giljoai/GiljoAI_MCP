"""
Context management module for GiljoAI MCP Server.

Provides field metadata and configuration for granular context field selection.
"""

from src.giljo_mcp.context.field_metadata import (
    FIELD_METADATA,
    get_field_metadata,
    get_default_field_selection,
    get_fields_for_category,
    migrate_v2_to_v3_fields,
)

__all__ = [
    "FIELD_METADATA",
    "get_field_metadata",
    "get_default_field_selection",
    "get_fields_for_category",
    "migrate_v2_to_v3_fields",
]
