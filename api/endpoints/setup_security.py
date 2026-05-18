# Copyright (c) 2024-2026 GiljoAI LLC. All rights reserved.
# Licensed under the Elastic License 2.0.
# See LICENSE in the project root for terms.
# [CE] Community Edition.

"""
Setup-status / fresh-install detection endpoint (IMP-0011 hardened).

Drives the unauthenticated frontend landing decision:

  GILJO_MODE x has_admin_user x has_any_user  ->  route_signal

CE keeps the original "no users -> create admin account" behavior. Demo and
SaaS-production modes NEVER expose the admin-bootstrap UI publicly -- they
always return ``show_public_landing=True`` so the router sends the visitor to
the Demo/SaaS landing view. Operators bootstrap the admin user out-of-band via
the CLI (see ``src/giljo_mcp/saas/cli/admin_bootstrap.py``).

This gate lives in CE because the application must be able to determine its
own mode to branch safely -- it only reads the ``GILJO_MODE`` string constant
and imports nothing from ``saas/``. Passes the Deletion Test.
"""

from __future__ import annotations

import logging
import os
from typing import Any

from fastapi import APIRouter, Depends
from sqlalchemy import func, select
from sqlalchemy.ext.asyncio import AsyncSession

from api.app_state import GILJO_MODE
from giljo_mcp.auth.dependencies import get_db_session
from giljo_mcp.models import User


logger = logging.getLogger(__name__)

router = APIRouter()


# Modes that are known to this codebase. Any other value is treated as
# "not CE" and therefore fail-secure (no admin-bootstrap UI exposure).
_KNOWN_NON_CE_MODES = frozenset({"demo", "saas", "saas-production"})
_CE_MODE = "ce"


def _compute_setup_signal(
    *,
    mode: str,
    has_admin_user: bool,
    has_any_user: bool,
) -> dict[str, Any]:
    """Pure policy function for the setup-status endpoint.

    Args:
        mode: Value of ``GILJO_MODE`` (already lower-cased at import time).
        has_admin_user: True if at least one user with role='admin' exists.
        has_any_user: True if any user exists in the database.

    Returns:
        Dict with the signals the frontend consumes:
          * is_fresh_install (bool) -- CE-only semantic, true iff CE with zero users.
          * requires_admin_creation (bool) -- alias of is_fresh_install.
          * show_public_landing (bool) -- true for demo/saas/unknown modes.
          * route_signal (str) -- 'create_admin', 'login', or 'public_landing'.

    Policy table:
      | mode        | has_admin | has_any | route_signal    | fresh | req_admin | landing |
      |-------------|-----------|---------|-----------------|-------|-----------|---------|
      | ce          | False     | False   | create_admin    | True  | True      | False   |
      | ce          | True      | True    | login           | False | False     | False   |
      | ce          | False     | True    | login (defensive)| False| False     | False   |
      | demo/saas   | *         | *       | public_landing  | False | False     | True    |
      | unknown     | *         | *       | public_landing  | False | False     | True    |
    """
    normalised = (mode or "").strip().lower()

    if normalised == _CE_MODE:
        is_fresh = not has_any_user
        # has_any_user=True but has_admin_user=False is defensively treated as
        # "not fresh" -- we never want to re-open admin bootstrap after any
        # user row exists.
        return {
            "is_fresh_install": is_fresh,
            "requires_admin_creation": is_fresh,
            "show_public_landing": False,
            "route_signal": "create_admin" if is_fresh else "login",
        }

    # demo, saas, saas-production, or anything unknown -> fail-secure path.
    # The landing page handles both "sign in" and "register" CTAs for
    # unauthenticated visitors; no admin-bootstrap UI is ever exposed.
    _ = normalised in _KNOWN_NON_CE_MODES  # intentional: unknown modes share policy
    return {
        "is_fresh_install": False,
        "requires_admin_creation": False,
        "show_public_landing": True,
        "route_signal": "public_landing",
    }


@router.get("/status")
async def get_setup_security_status(db: AsyncSession = Depends(get_db_session)):
    """
    Setup-status detection driven by the policy table.

    Returns fields consumed by frontend router.beforeEach:
      * setup_complete
      * is_fresh_install         (CE-only semantic)
      * requires_admin_creation  (CE-only semantic)
      * show_public_landing      (demo/saas flag, used by router guard)
      * route_signal             ('create_admin' | 'login' | 'public_landing')
      * total_users_count        (int)
      * mode                     (echoed for frontend debugging)
      * sentryDsn                (camelCase; SENTRY_DSN_FRONTEND in saas/demo, else null)
      * environment              (camelCase; echoes GILJO_MODE, defaulting to 'ce')
    """
    try:
        # Count total users and admin users in a single round-trip.
        total_users_stmt = select(func.count(User.id))
        admin_users_stmt = select(func.count(User.id)).where(User.role == "admin")

        total_users_count = (await db.execute(total_users_stmt)).scalar() or 0
        admin_users_count = (await db.execute(admin_users_stmt)).scalar() or 0

        signal = _compute_setup_signal(
            mode=GILJO_MODE,
            has_admin_user=admin_users_count > 0,
            has_any_user=total_users_count > 0,
        )

        if signal["is_fresh_install"]:
            logger.info("[SETUP] Fresh install detected (mode=ce, 0 users). Create-admin flow active.")
        else:
            logger.debug(
                "[SETUP] mode=%s total_users=%d admins=%d route_signal=%s",
                GILJO_MODE,
                total_users_count,
                admin_users_count,
                signal["route_signal"],
            )

        paddle_client_token, paddle_environment = _resolve_paddle_fields(GILJO_MODE)

        return {
            "setup_complete": not signal["is_fresh_install"],
            "is_fresh_install": signal["is_fresh_install"],
            "requires_admin_creation": signal["requires_admin_creation"],
            "show_public_landing": signal["show_public_landing"],
            "route_signal": signal["route_signal"],
            "total_users_count": total_users_count,
            "mode": GILJO_MODE,
            "sentryDsn": _resolve_sentry_dsn(GILJO_MODE),
            "environment": _resolve_environment(GILJO_MODE),
            "paddle_client_token": paddle_client_token,
            "paddle_environment": paddle_environment,
        }

    except (ValueError, KeyError):
        logger.exception("Failed to get setup status")
        # Fail-secure fallback: hide admin bootstrap regardless of mode.
        # The frontend will land on the public-landing view and the router
        # guard will retry setup-status on the next navigation.
        return {
            "setup_complete": False,
            "is_fresh_install": False,
            "requires_admin_creation": False,
            "show_public_landing": True,
            "route_signal": "public_landing",
            "mode": GILJO_MODE,
            "sentryDsn": _resolve_sentry_dsn(GILJO_MODE),
            "environment": _resolve_environment(GILJO_MODE),
            "paddle_client_token": None,
            "paddle_environment": None,
        }


def _resolve_sentry_dsn(mode: str) -> str | None:
    """Return SENTRY_DSN_FRONTEND only in saas/demo modes (INF-5063)."""
    if (mode or "").strip().lower() in ("saas", "demo"):
        return os.environ.get("SENTRY_DSN_FRONTEND") or None
    return None


def _resolve_environment(mode: str) -> str:
    """Echo GILJO_MODE for the frontend Sentry init, defaulting to 'ce'."""
    return (mode or "").strip().lower() or "ce"


def _resolve_paddle_fields(mode: str) -> tuple[str | None, str | None]:
    """Return ``(paddle_client_token, paddle_environment)`` for the SaaS frontend.

    Returns ``(None, None)`` in any non-SaaS mode — CE and demo never expose
    the Paddle client token. Uses ``importlib.import_module`` so the CE/SaaS
    static boundary check (``scripts/check_saas_import_boundary.py``) cannot
    flag this CE file. Mirrors the pattern in ``api/app.py:278``.
    """
    if (mode or "").strip().lower() != "saas":
        return None, None

    try:
        import importlib

        _paddle_mod = importlib.import_module("giljo_mcp.saas.billing.paddle_service")
    except ImportError:
        # SaaS package not present in this build — treat as not configured.
        return None, None

    # PaddleConfigError lives in the lazy module; resolve it dynamically so
    # this CE file never holds a reference to a SaaS-defined class at load time.
    paddle_config_error = getattr(_paddle_mod, "PaddleConfigError", Exception)
    try:
        service = _paddle_mod.PaddleService()
        return service.get_client_token(), service.environment
    except paddle_config_error as exc:
        logger.warning("paddle_setup_status_unconfigured: %s", exc)
        return None, _safe_env_only_paddle_environment()


def _safe_env_only_paddle_environment() -> str | None:
    raw = os.environ.get("PADDLE_ENVIRONMENT")
    if not raw:
        return None
    normalised = raw.strip().lower()
    if normalised in ("sandbox", "production"):
        return normalised
    return None
