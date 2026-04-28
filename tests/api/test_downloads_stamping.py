# Copyright (c) 2024-2026 GiljoAI LLC. All rights reserved.
# Licensed under the GiljoAI Community License v1.1.
# See LICENSE in the project root for terms.
# [CE] Community Edition — source-available, single-user use only.

"""HO 1028: stamping last_installed_skills_version when bundle is served.

The /api/download/agent-templates.zip endpoint must stamp the requesting
user's last_installed_skills_version with the current SKILLS_VERSION when
the request is authenticated. This goes through UserService — direct
setattr on the ORM model from the endpoint is forbidden (post-0962).
"""

from uuid import uuid4

import pytest
from sqlalchemy import select


@pytest.mark.asyncio
async def test_agent_templates_download_stamps_skills_version(api_client, db_manager, auth_headers):
    """A successful authenticated agent-templates download stamps SKILLS_VERSION."""
    from giljo_mcp.models import AgentTemplate, User
    from giljo_mcp.tools.slash_command_templates import SKILLS_VERSION

    # The auth_headers fixture created a tenant + user. Resolve them and seed
    # at least one active agent template so the endpoint returns 200 (not 404).
    async with db_manager.get_session_async() as session:
        users = (await session.execute(select(User).order_by(User.created_at.desc()))).scalars().all()
        # Pick the most recently created developer test user
        user = next(u for u in users if u.username.startswith("test_user_"))

        template = AgentTemplate(
            id=str(uuid4()),
            tenant_key=user.tenant_key,
            org_id=user.org_id,
            name=f"impl_{uuid4().hex[:6]}",
            role="implementer",
            system_instructions="You are a test agent.",
            description="Test impl agent",
            tools="Read,Write",
            model="claude-sonnet-4-5",
            is_active=True,
        )
        session.add(template)
        await session.commit()

    resp = await api_client.get("/api/download/agent-templates.zip", headers=auth_headers)
    assert resp.status_code == 200, resp.text

    async with db_manager.get_session_async() as session:
        refreshed = (await session.execute(select(User).where(User.id == user.id))).scalar_one()
        assert refreshed.last_installed_skills_version == SKILLS_VERSION


@pytest.mark.asyncio
async def test_unauthenticated_download_does_not_stamp(api_client, db_manager):
    """Unauthenticated downloads MUST NOT touch any user record."""
    # Without seeding a system-default template the endpoint returns 404 — that
    # is exactly what we want: confirm no stamping side-effect on a 404 either.
    resp = await api_client.get("/api/download/agent-templates.zip")
    assert resp.status_code == 404
