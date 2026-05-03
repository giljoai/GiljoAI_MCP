# Copyright (c) 2024-2026 GiljoAI LLC. All rights reserved.
# Licensed under the GiljoAI Community License v1.1.
# See LICENSE in the project root for terms.
# [CE] Community Edition — source-available, single-user use only.

"""HO 1028 follow-up: server-side ``never_installed`` source of truth.

The dashboard previously gated the skills-drift banner on a localStorage
value, which silently hid drift from real existing users (and showed it to
brand-new users who had never run /giljo_setup). The endpoint now exposes
``never_installed`` as a server-side boolean derived from the authenticated
user's ``users.last_installed_skills_version`` column (migration
``ce_0007_users_skills_version_tracking``).

These tests verify the three meaningful cases:
  (a) NULL column     -> never_installed=True
  (b) older version   -> never_installed=False, drift_detected=True
  (c) current version -> never_installed=False, drift_detected=False
"""

from unittest.mock import patch

import pytest
from sqlalchemy import select


ENDPOINT = "/api/notifications/check-skills-version"


async def _stamp_user_skills_version(db_manager, cookie_header: str, value):
    """Update the test user's ``last_installed_skills_version`` to ``value``.

    Resolves the user from the JWT in the auth_headers Cookie. Keeps the test
    decoupled from the auth_headers fixture's user-creation internals.
    """
    from giljo_mcp.auth.jwt_manager import JWTManager
    from giljo_mcp.models import User

    # Cookie format: "access_token=<jwt>; csrf_token=<csrf>"
    token = cookie_header.split("access_token=", 1)[1].split(";", 1)[0].strip()
    payload = JWTManager.verify_token(token)
    user_id = payload["sub"]  # User.id is String(36), keep as str

    async with db_manager.get_session_async() as session:
        result = await session.execute(select(User).where(User.id == user_id))
        user = result.scalar_one()
        user.last_installed_skills_version = value
        await session.commit()


@pytest.mark.asyncio
async def test_never_installed_true_when_column_null(api_client, auth_headers):
    """User with last_installed_skills_version IS NULL -> never_installed=True.

    Default fixture creates the user without stamping the column, so this is
    the happy-path "brand new user" case.
    """
    with patch("api.endpoints.notifications.SKILLS_VERSION", "1.1.11"):
        resp = await api_client.get(
            ENDPOINT + "?installed_skills_version=1.1.11",
            headers=auth_headers,
        )

    assert resp.status_code == 200
    data = resp.json()
    assert data["never_installed"] is True
    # Query param matches current, so drift is False even though the user has
    # never installed -- the two flags are independent by design.
    assert data["drift_detected"] is False


@pytest.mark.asyncio
async def test_never_installed_false_when_stamped_older(api_client, auth_headers, db_manager):
    """User with installed version < current -> never_installed=False, drift=True."""
    await _stamp_user_skills_version(db_manager, auth_headers["Cookie"], "1.1.0")

    with patch("api.endpoints.notifications.SKILLS_VERSION", "1.1.11"):
        resp = await api_client.get(
            ENDPOINT + "?installed_skills_version=1.1.0",
            headers=auth_headers,
        )

    assert resp.status_code == 200
    data = resp.json()
    assert data["never_installed"] is False
    assert data["drift_detected"] is True


@pytest.mark.asyncio
async def test_never_installed_false_when_stamped_current(api_client, auth_headers, db_manager):
    """User on current version -> never_installed=False, drift=False."""
    await _stamp_user_skills_version(db_manager, auth_headers["Cookie"], "1.1.11")

    with patch("api.endpoints.notifications.SKILLS_VERSION", "1.1.11"):
        resp = await api_client.get(
            ENDPOINT + "?installed_skills_version=1.1.11",
            headers=auth_headers,
        )

    assert resp.status_code == 200
    data = resp.json()
    assert data["never_installed"] is False
    assert data["drift_detected"] is False
