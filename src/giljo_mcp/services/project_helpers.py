# Copyright (c) 2024-2026 GiljoAI LLC. All rights reserved.
# Licensed under the GiljoAI Community License v1.1.
# See LICENSE in the project root for terms.
# [CE] Community Edition — source-available, single-user use only.

"""
Shared helpers for the project service family.

Extracted from project_service.py (Sprint 002e) to eliminate cross-import
coupling where project_lifecycle_service and project_launch_service
imported ``_build_ws_project_data`` directly from project_service.
"""


def _build_ws_project_data(project) -> dict:
    """Build standardized project data dict for WebSocket broadcasts.

    Single source of truth for project data sent to frontend via
    WebSocket ``broadcast_project_update`` events. All project broadcast
    sites should use this helper to ensure a consistent field structure.

    Args:
        project: Project model instance (SQLAlchemy).

    Returns:
        Dict with the fields extracted by
        ``WebSocketManager.broadcast_project_update``.
    """
    return {
        "name": project.name,
        "description": project.description,
        "status": project.status,
        "mission": project.mission,
    }
