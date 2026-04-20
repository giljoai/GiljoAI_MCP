# Copyright (c) 2024-2026 GiljoAI LLC. All rights reserved.
# Licensed under the GiljoAI Community License v1.1.
# See LICENSE in the project root for terms.
# [CE] Community Edition — source-available, single-user use only.

"""Tests for project_helpers module (Sprint 002e extraction)."""

from unittest.mock import MagicMock

from giljo_mcp.services.project_helpers import _build_ws_project_data


def test_build_ws_project_data_returns_expected_fields():
    """_build_ws_project_data returns name, description, status, mission."""
    project = MagicMock()
    project.name = "Test"
    project.description = "Desc"
    project.status = "active"
    project.mission = "Mission text"

    result = _build_ws_project_data(project)

    assert result == {
        "name": "Test",
        "description": "Desc",
        "status": "active",
        "mission": "Mission text",
    }


def test_build_ws_project_data_handles_none_fields():
    """_build_ws_project_data handles None values gracefully."""
    project = MagicMock()
    project.name = "P"
    project.description = None
    project.status = "inactive"
    project.mission = None

    result = _build_ws_project_data(project)

    assert result["description"] is None
    assert result["mission"] is None
