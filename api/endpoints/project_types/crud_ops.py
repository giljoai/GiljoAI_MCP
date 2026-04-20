# Copyright (c) 2024-2026 GiljoAI LLC. All rights reserved.
# Licensed under the GiljoAI Community License v1.1.
# See LICENSE in the project root for terms.
# [CE] Community Edition — source-available, single-user use only.

"""
CRUD operations for Project Types - Handover 0440a Phase 2

BE-5022a: All DB logic now lives in giljo_mcp.services.project_type_ops.
This module re-exports for backward compatibility with api/ consumers.
Endpoint-layer schemas are unpacked into keyword arguments at the call site.
"""

from giljo_mcp.services.project_type_ops import (
    DEFAULT_PROJECT_TYPES,
    check_series_available,
    create_project_type,
    delete_project_type,
    ensure_default_types_seeded,
    get_available_series_numbers,
    get_next_series_number,
    get_project_count_for_type,
    get_used_subseries,
    list_project_types,
    update_project_type,
)


__all__ = [
    "DEFAULT_PROJECT_TYPES",
    "check_series_available",
    "create_project_type",
    "delete_project_type",
    "ensure_default_types_seeded",
    "get_available_series_numbers",
    "get_next_series_number",
    "get_project_count_for_type",
    "get_used_subseries",
    "list_project_types",
    "update_project_type",
]
