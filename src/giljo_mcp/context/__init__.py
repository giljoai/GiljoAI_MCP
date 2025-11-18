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
    estimate_tokens_for_selection,
    migrate_depth_config_v2_to_v3,
    is_v3_schema,
    get_field_selections,
)

__all__ = [
    "FIELD_METADATA",
    "get_field_metadata",
    "get_default_field_selection",
    "get_fields_for_category",
    "migrate_v2_to_v3_fields",
    "estimate_tokens_for_selection",
    "migrate_depth_config_v2_to_v3",
    "is_v3_schema",
    "get_field_selections",
]
