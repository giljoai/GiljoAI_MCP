# Copyright (c) 2024-2026 GiljoAI LLC. All rights reserved.
# Licensed under the GiljoAI Community License v1.1.
# See LICENSE in the project root for terms.
# [CE] Community Edition -- source-available, single-user use only.

"""User-facing notification endpoints.

Currently exposes:
- ``GET /api/notifications/check-skills-version`` -- drift check for the
  bundled slash-command/skills bundle vs. the deployment-wide announced
  version.

IMP-0023 (this rewrite): drift state is now system-wide. The server reads
``SKILLS_VERSION`` (the bundled constant the running code ships with) and
the ``system_settings.skills_version_announced`` row (what was seeded the
last time the server announced a bundle), and reports whether they match.
No per-user state is involved.

This router is auth-gated. It performs no DB writes.
"""

import logging

from fastapi import APIRouter, Depends
from pydantic import BaseModel
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from giljo_mcp.auth.dependencies import get_current_active_user, get_db_session
from giljo_mcp.models import User
from giljo_mcp.models.system_setting import SystemSetting
from giljo_mcp.tools.slash_command_templates import SKILLS_VERSION


logger = logging.getLogger(__name__)

router = APIRouter(prefix="/api/notifications", tags=["notifications"])

ANNOUNCED_KEY = "skills_version_announced"


class SkillsVersionDriftResponse(BaseModel):
    """Response schema for the system-wide skills bundle drift check.

    Fields:
      - ``current``: the version the running server's bundled
        ``SKILLS_VERSION`` constant reports.
      - ``announced``: the version stored in
        ``system_settings.skills_version_announced``. ``None`` if the row
        is missing (should not happen after migration ce_0009 has run).
      - ``drift_detected``: True when ``current != announced``.
      - ``message``: human-readable hint, populated only when drift is
        detected.
    """

    current: str
    announced: str | None
    drift_detected: bool
    message: str | None = None


@router.get("/check-skills-version", response_model=SkillsVersionDriftResponse)
async def check_skills_version(
    db: AsyncSession = Depends(get_db_session),
    _current_user: User = Depends(get_current_active_user),
) -> SkillsVersionDriftResponse:
    """Compare the bundled SKILLS_VERSION to the system-announced value.

    Drift is the difference between what the running deployment ships with
    (``SKILLS_VERSION`` constant) and what was last announced by the
    operator (``system_settings.skills_version_announced``). Mismatch
    means the slash-command bundle the server is serving has moved
    forward without an explicit announce -- the dashboard renders a banner
    so the user can re-run /giljo_setup.

    Auth is required so anonymous callers cannot probe deployment state.
    """
    current = SKILLS_VERSION

    result = await db.execute(select(SystemSetting.value).where(SystemSetting.key == ANNOUNCED_KEY))
    announced = result.scalar_one_or_none()

    drift_detected = announced is None or announced != current

    message: str | None = None
    if drift_detected:
        if announced is None:
            message = (
                "Skills bundle version not yet announced on this server. "
                "Re-run /giljo_setup to install the latest bundle."
            )
        else:
            message = f"A newer skills bundle is available ({announced} -> {current}). Re-run /giljo_setup to update."

    return SkillsVersionDriftResponse(
        current=current,
        announced=announced,
        drift_detected=drift_detected,
        message=message,
    )
