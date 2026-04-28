# Copyright (c) 2024-2026 GiljoAI LLC. All rights reserved.
# Licensed under the GiljoAI Community License v1.1.
# See LICENSE in the project root for terms.
# [CE] Community Edition — source-available, single-user use only.

"""User-facing notification endpoints.

Currently exposes:
- ``GET /api/notifications/check-skills-version`` — drift check for the
  installed slash-command/skills bundle vs. the server's authoritative
  ``SKILLS_VERSION``.

This router is auth-gated. It performs no DB writes; the stamping and
cadence/throttle sides of the update-notification feature live on the
download/MCP-setup paths and the auth login path
(``UserService.update_user_metadata`` / ``UserService.check_and_emit_skills_update``).
"""

import logging
from typing import Optional

from fastapi import APIRouter, Depends, Query
from pydantic import BaseModel

from giljo_mcp.auth.dependencies import get_current_active_user
from giljo_mcp.models import User
from giljo_mcp.services.version_service import compare_versions
from giljo_mcp.tools.slash_command_templates import SKILLS_VERSION


logger = logging.getLogger(__name__)

router = APIRouter(prefix="/api/notifications", tags=["notifications"])


class SkillsVersionDriftResponse(BaseModel):
    """Response schema for the skills version drift check."""

    installed: Optional[str] = None
    current: str
    drift_detected: bool
    message: Optional[str] = None


@router.get("/check-skills-version", response_model=SkillsVersionDriftResponse)
async def check_skills_version(
    installed_skills_version: Optional[str] = Query(
        default=None,
        max_length=32,
        # Accept dotted numeric versions only — keep the surface small for an
        # untrusted query parameter. Mirrors version_service._parse_version_tuple
        # which only accepts integer-dotted strings.
        pattern=r"^\d+(\.\d+)*$",
        description="Caller's installed SKILLS_VERSION; omit if unknown.",
    ),
    current_user: User = Depends(get_current_active_user),
) -> SkillsVersionDriftResponse:
    """Compare caller's installed skills bundle version to the server's current.

    ``drift_detected`` is True when:
      - ``installed_skills_version`` is omitted/null (the client cannot prove
        it has the current bundle), OR
      - ``installed_skills_version`` is strictly older than ``SKILLS_VERSION``
        per the existing semver helper in ``version_service``.

    A caller running a *newer* version than the server (e.g., dev branch) is
    not flagged as drifted — the server is the older party in that case.
    """
    current = SKILLS_VERSION

    if installed_skills_version is None:
        return SkillsVersionDriftResponse(
            installed=None,
            current=current,
            drift_detected=True,
            message=(
                "No installed skills version reported. Re-run /giljo_setup to install the latest slash-command bundle."
            ),
        )

    if installed_skills_version == current:
        return SkillsVersionDriftResponse(
            installed=installed_skills_version,
            current=current,
            drift_detected=False,
            message=None,
        )

    drift = compare_versions(installed_skills_version, current)

    return SkillsVersionDriftResponse(
        installed=installed_skills_version,
        current=current,
        drift_detected=drift,
        message=(
            f"A newer skills bundle is available ({installed_skills_version} -> {current}). "
            "Re-run /giljo_setup to update."
        )
        if drift
        else None,
    )
