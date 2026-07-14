# Copyright (c) 2024-2026 GiljoAI LLC. All rights reserved.
# Licensed under the Elastic License 2.0.
# See LICENSE in the project root for terms.
# [CE] Community Edition.

"""INF-6049a -- endpoint content lock for GET /api/download/bootstrap-prompt.

The slash-command fleet (gil_add / gil_get / gil_chain / gil_get_agents)
collapsed to one thin ``/giljo`` command. ``/api/download/bootstrap-prompt`` is a
LIVE agent-facing endpoint: it renders a ready-to-paste onboarding prompt from
the per-platform ``BOOTSTRAP_*`` templates. This drives the real HTTP endpoint
(auth + token + slash-command staging) and asserts each platform's prompt now
advertises the single ``/giljo`` command and NOT the deleted gil_* commands --
leaving the old commands in would tell a fresh agent to run commands that no
longer install (a broken bootstrap).
"""

from __future__ import annotations

import pytest
from httpx import AsyncClient


pytestmark = pytest.mark.asyncio


_PLATFORMS = ["claude_code", "gemini_cli", "codex_cli", "antigravity_cli", "generic"]

# Every deleted command name, in both slash (/gil_) and codex ($gil-) spellings.
_DELETED_COMMANDS = [
    "gil_get_agents",
    "gil-get-agents",
    "gil_add",
    "gil-add",
    "/gil_get",
    "$gil-get",
    "gil_chain",
    "gil-chain",
    "gil_get_reference",
]


@pytest.mark.parametrize("platform", _PLATFORMS)
async def test_bootstrap_prompt_advertises_giljo_not_legacy(api_client: AsyncClient, auth_headers: dict, platform: str):
    resp = await api_client.get(f"/api/download/bootstrap-prompt?platform={platform}", headers=auth_headers)
    assert resp.status_code == 200, f"{platform}: {resp.status_code} {resp.text}"

    prompt = resp.json()["prompt"]
    assert "giljo" in prompt.lower(), f"{platform} bootstrap prompt does not mention giljo"
    for legacy in _DELETED_COMMANDS:
        assert legacy not in prompt, f"{platform} bootstrap still advertises deleted command {legacy!r}"


@pytest.mark.parametrize("platform", ["claude_code", "gemini_cli", "codex_cli", "antigravity_cli"])
async def test_bootstrap_prompt_routes_agent_install_through_giljo_setup(
    api_client: AsyncClient, auth_headers: dict, platform: str
):
    """Agent-template install/refresh now folds into giljo_setup (no gil_get_agents)."""
    resp = await api_client.get(f"/api/download/bootstrap-prompt?platform={platform}", headers=auth_headers)
    assert resp.status_code == 200, f"{platform}: {resp.status_code} {resp.text}"
    assert "giljo_setup" in resp.json()["prompt"], f"{platform} bootstrap must route agents through giljo_setup"
