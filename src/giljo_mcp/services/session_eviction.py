# Copyright (c) 2024-2026 GiljoAI LLC. All rights reserved.
# Licensed under the Elastic License 2.0.
# See LICENSE in the project root for terms.
# [CE] Community Edition.

"""Shared session-eviction helpers (SEC-9047 / TSK-9006).

Bump-epoch + revoke-refresh and live-WebSocket close, factored out of the large
``UserService`` so its deactivation and credential-change paths share one
implementation without growing that file past its shrink-only size budget.

Edition Scope: Both — depends only on CE modules (oauth_refresh_service,
api.app_state). No saas imports.
"""

from __future__ import annotations

import logging
from typing import TYPE_CHECKING

from sqlalchemy import select

from giljo_mcp.models.auth import User
from giljo_mcp.services.oauth_refresh_service import revoke_all_for_user


if TYPE_CHECKING:
    from sqlalchemy.ext.asyncio import AsyncSession


async def evict_user_tokens(session: AsyncSession, user: User) -> int:
    """Bump the revocation epoch + revoke the user's refresh tokens (in-txn).

    Shared by the credential-change (SEC-9047/9071) and deactivation (TSK-9006)
    paths. Bumping ``token_revocation_epoch`` invalidates every outstanding access
    token via the ``rev`` claim check in principal.py; revoking refresh tokens
    stops them minting fresh ones. Because the epoch persists on the row, a later
    reactivation cannot resurrect the pre-deactivation tokens. Returns the
    refresh-token rows revoked.

    SEC-9217b: takes a user-first ``SELECT ... FOR UPDATE`` on the owning User
    row BEFORE mutating, so a concurrent OAuth ``/refresh`` grant (which locks the
    same row in the same order) cannot interleave with this eviction and mint a
    surviving access+refresh pair. See ``oauth_refresh_service._refresh_grant_after_lookup``.
    """
    await session.execute(
        select(User.id).where(User.id == str(user.id), User.tenant_key == user.tenant_key).with_for_update()
    )
    user.token_revocation_epoch = (user.token_revocation_epoch or 0) + 1
    return await revoke_all_for_user(session, user_id=str(user.id), tenant_key=user.tenant_key)


async def close_live_user_sockets(tenant_key: str, logger: logging.Logger) -> None:
    """Best-effort force-close of the account's live WebSocket sockets (TSK-9006).

    Deactivation must bite live sockets, which only re-check is_active at the WS
    handshake. Reaches the running WebSocketManager via app_state and calls
    ``disconnect_tenant``, which closes local sockets and fans a cross-worker close
    over the existing giljo_ws_events broker. Post-commit and best-effort: a
    WebSocket failure must never fail the committed deactivation — the persisted
    epoch bump is the durable backstop that still evicts REST/MCP and blocks
    reconnects.
    """
    try:
        from api.app_state import state

        ws_manager = getattr(state, "websocket_manager", None)
        if ws_manager is not None:
            await ws_manager.disconnect_tenant(tenant_key, reason="account deactivated")
    except Exception:  # noqa: BLE001 - fire-and-forget; never fail the deactivation
        logger.warning("Failed to close live WebSocket sockets on deactivation", exc_info=True)
