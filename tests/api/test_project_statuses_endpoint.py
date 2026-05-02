# Copyright (c) 2024-2026 GiljoAI LLC. All rights reserved.
# Licensed under the GiljoAI Community License v1.1.
# See LICENSE in the project root for terms.
# [CE] Community Edition -- source-available, single-user use only.

"""Integration tests for ``GET /api/v1/project-statuses/`` (BE-5039 Phase 2b).

Asserts the endpoint returns the canonical six metadata objects with the
documented shape, and that auth is required.
"""

from __future__ import annotations

import pytest
from httpx import AsyncClient

from giljo_mcp.domain.project_status import PROJECT_STATUS_META, ProjectStatus


_EXPECTED_VALUES = [s.value for s in ProjectStatus]


@pytest.mark.asyncio
async def test_list_project_statuses_returns_six_canonical_members(api_client: AsyncClient, auth_headers: dict) -> None:
    """Endpoint must return exactly six rows in declaration order."""

    resp = await api_client.get("/api/v1/project-statuses/", headers=auth_headers)
    assert resp.status_code == 200, resp.text

    body = resp.json()
    assert isinstance(body, list)
    assert [item["value"] for item in body] == _EXPECTED_VALUES


@pytest.mark.asyncio
async def test_list_project_statuses_payload_shape(api_client: AsyncClient, auth_headers: dict) -> None:
    """Each row carries the documented metadata fields with correct types."""

    resp = await api_client.get("/api/v1/project-statuses/", headers=auth_headers)
    assert resp.status_code == 200

    for item in resp.json():
        assert set(item.keys()) == {
            "value",
            "label",
            "color_token",
            "is_lifecycle_finished",
            "is_immutable",
            "is_user_mutable_via_mcp",
        }
        assert isinstance(item["value"], str)
        assert isinstance(item["label"], str)
        assert isinstance(item["color_token"], str)
        assert isinstance(item["is_lifecycle_finished"], bool)
        assert isinstance(item["is_immutable"], bool)
        assert isinstance(item["is_user_mutable_via_mcp"], bool)
        # Color tokens MUST be SCSS variable names, never hex literals.
        assert not item["color_token"].startswith("#")


@pytest.mark.asyncio
async def test_list_project_statuses_metadata_matches_domain(api_client: AsyncClient, auth_headers: dict) -> None:
    """Per-row payload equals the in-memory PROJECT_STATUS_META entry."""

    resp = await api_client.get("/api/v1/project-statuses/", headers=auth_headers)
    assert resp.status_code == 200

    by_value = {item["value"]: item for item in resp.json()}
    for member, meta in PROJECT_STATUS_META.items():
        item = by_value[member.value]
        assert item["label"] == meta.label
        assert item["color_token"] == meta.color_token
        assert item["is_lifecycle_finished"] is meta.is_lifecycle_finished
        assert item["is_immutable"] is meta.is_immutable
        assert item["is_user_mutable_via_mcp"] is meta.is_user_mutable_via_mcp


@pytest.mark.asyncio
async def test_list_project_statuses_requires_auth(api_client: AsyncClient) -> None:
    """Unauthenticated callers must be rejected."""

    resp = await api_client.get("/api/v1/project-statuses/")
    # Auth dependency rejects without a JWT cookie -- 401 Unauthorized.
    assert resp.status_code == 401, resp.text
