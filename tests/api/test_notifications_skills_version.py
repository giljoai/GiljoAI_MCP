# Copyright (c) 2024-2026 GiljoAI LLC. All rights reserved.
# Licensed under the GiljoAI Community License v1.1.
# See LICENSE in the project root for terms.
# [CE] Community Edition — source-available, single-user use only.

"""API tests for GET /api/notifications/check-skills-version endpoint.

Skills version drift detection. The server's authoritative version is the
SKILLS_VERSION constant in slash_command_templates.py. The endpoint reports
whether the caller's installed bundle is older than the server's current
version (semver comparison via the existing version_service helper).
"""

from unittest.mock import patch

import pytest


ENDPOINT = "/api/notifications/check-skills-version"


@pytest.mark.asyncio
async def test_requires_auth(api_client):
    """No cookie / no API key -> 401."""
    resp = await api_client.get(ENDPOINT)
    assert resp.status_code == 401


@pytest.mark.asyncio
async def test_drift_when_installed_older(api_client, auth_headers):
    """Older installed -> drift_detected True with both versions reported."""
    with patch(
        "api.endpoints.notifications.SKILLS_VERSION",
        "1.1.11",
    ):
        resp = await api_client.get(
            ENDPOINT + "?installed_skills_version=1.1.0",
            headers=auth_headers,
        )

    assert resp.status_code == 200
    data = resp.json()
    assert data["installed"] == "1.1.0"
    assert data["current"] == "1.1.11"
    assert data["drift_detected"] is True
    assert data["message"]


@pytest.mark.asyncio
async def test_no_drift_when_versions_match(api_client, auth_headers):
    with patch(
        "api.endpoints.notifications.SKILLS_VERSION",
        "1.1.11",
    ):
        resp = await api_client.get(
            ENDPOINT + "?installed_skills_version=1.1.11",
            headers=auth_headers,
        )

    assert resp.status_code == 200
    data = resp.json()
    assert data["installed"] == "1.1.11"
    assert data["current"] == "1.1.11"
    assert data["drift_detected"] is False
    assert data["message"] is None


@pytest.mark.asyncio
async def test_drift_when_installed_null(api_client, auth_headers):
    """Missing installed version -> always drift (forces re-install of bundle)."""
    with patch(
        "api.endpoints.notifications.SKILLS_VERSION",
        "1.1.11",
    ):
        resp = await api_client.get(ENDPOINT, headers=auth_headers)

    assert resp.status_code == 200
    data = resp.json()
    assert data["installed"] is None
    assert data["current"] == "1.1.11"
    assert data["drift_detected"] is True
    assert data["message"]


@pytest.mark.asyncio
async def test_no_drift_when_installed_newer(api_client, auth_headers):
    """Caller is on a newer version -> no drift (server is older than client)."""
    with patch(
        "api.endpoints.notifications.SKILLS_VERSION",
        "1.1.11",
    ):
        resp = await api_client.get(
            ENDPOINT + "?installed_skills_version=2.0.0",
            headers=auth_headers,
        )

    assert resp.status_code == 200
    data = resp.json()
    assert data["drift_detected"] is False


@pytest.mark.asyncio
async def test_rejects_oversized_input(api_client, auth_headers):
    """Length cap enforced -> 422 (FastAPI validation)."""
    huge = "1." * 200
    resp = await api_client.get(
        ENDPOINT + f"?installed_skills_version={huge}",
        headers=auth_headers,
    )
    assert resp.status_code == 422


@pytest.mark.asyncio
async def test_rejects_unparseable_input(api_client, auth_headers):
    """Non-semver garbage -> 422 (regex pattern)."""
    resp = await api_client.get(
        ENDPOINT + "?installed_skills_version=not-a-version",
        headers=auth_headers,
    )
    assert resp.status_code == 422
