# Copyright (c) 2024-2026 GiljoAI LLC. All rights reserved.
# Licensed under the GiljoAI Community License v1.1.
# See LICENSE in the project root for terms.
# [CE] Community Edition -- source-available, single-user use only.

"""IMP-0023: contract test for GET /api/notifications/check-skills-version.

Response shape: {current, announced, drift_detected, message}. The older
fields installed and never_installed are gone.
"""

from unittest.mock import patch

import pytest
from sqlalchemy import delete

from giljo_mcp.models.system_setting import SystemSetting


ENDPOINT = "/api/notifications/check-skills-version"
ANNOUNCED_KEY = "skills_version_announced"


async def _set_announced(db_manager, value):
    async with db_manager.get_session_async() as session:
        await session.execute(delete(SystemSetting).where(SystemSetting.key == ANNOUNCED_KEY))
        if value is not None:
            session.add(SystemSetting(key=ANNOUNCED_KEY, value=value))
        await session.commit()


@pytest.mark.asyncio
async def test_requires_auth(api_client):
    resp = await api_client.get(ENDPOINT)
    assert resp.status_code == 401


@pytest.mark.asyncio
async def test_drift_detected_when_announced_older(api_client, auth_headers, db_manager):
    await _set_announced(db_manager, "1.0.0")
    with patch("api.endpoints.notifications.SKILLS_VERSION", "1.1.11"):
        resp = await api_client.get(ENDPOINT, headers=auth_headers)

    assert resp.status_code == 200
    data = resp.json()
    assert set(data.keys()) == {"current", "announced", "drift_detected", "message"}
    assert data["current"] == "1.1.11"
    assert data["announced"] == "1.0.0"
    assert data["drift_detected"] is True
    assert data["message"]


@pytest.mark.asyncio
async def test_no_drift_when_versions_match(api_client, auth_headers, db_manager):
    await _set_announced(db_manager, "1.1.11")
    with patch("api.endpoints.notifications.SKILLS_VERSION", "1.1.11"):
        resp = await api_client.get(ENDPOINT, headers=auth_headers)

    assert resp.status_code == 200
    data = resp.json()
    assert set(data.keys()) == {"current", "announced", "drift_detected", "message"}
    assert data["current"] == "1.1.11"
    assert data["announced"] == "1.1.11"
    assert data["drift_detected"] is False
    assert data["message"] is None


@pytest.mark.asyncio
async def test_drift_when_announced_row_missing(api_client, auth_headers, db_manager):
    await _set_announced(db_manager, None)
    with patch("api.endpoints.notifications.SKILLS_VERSION", "1.1.11"):
        resp = await api_client.get(ENDPOINT, headers=auth_headers)

    assert resp.status_code == 200
    data = resp.json()
    assert set(data.keys()) == {"current", "announced", "drift_detected", "message"}
    assert data["current"] == "1.1.11"
    assert data["announced"] is None
    assert data["drift_detected"] is True
    assert data["message"]
