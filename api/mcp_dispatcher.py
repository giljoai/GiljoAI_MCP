# Copyright (c) 2024-2026 GiljoAI LLC. All rights reserved.
# Licensed under the Elastic License 2.0.
# See LICENSE in the project root for terms.
# [CE] Community Edition.

"""Top-level pure-ASGI dispatcher that splits /mcp off the FastAPI onion (BE-6060c).

Installed ABOVE every FastAPI middleware (see ``api/app.py`` bottom): the dispatcher
is the outermost ASGI callable uvicorn invokes. It routes by ASGI ``scope`` BEFORE the
FastAPI app — and its middleware stack — ever sees the request:

- ``scope["type"] == "lifespan"`` -> the FastAPI app. The FastAPI lifespan owns app
  startup AND starts the MCP ``StreamableHTTPSessionManager`` run-context via
  ``start_mcp_session_manager()`` (api/app.py). That session manager is a module-level
  singleton on the shared FastMCP ``mcp`` instance; the ``mcp_app`` routed to below is
  ``StreamableHTTPASGIApp(mcp._session_manager)`` — a pure-HTTP ASGI callable that
  references the SAME running singleton and has no lifespan of its own. So forwarding
  lifespan to the FastAPI app is sufficient and byte-identical to the lifecycle the
  deleted bridge had: the manager is started exactly once, by the FastAPI lifespan, and
  shared with the mcp_app.
- ``scope["type"] == "websocket"`` -> the FastAPI app (no WS endpoint lives under /mcp).
- ``scope["type"] == "http"`` with path ``/mcp`` or ``/mcp/...`` AND method != OPTIONS ->
  the MCP ASGI app, with ``(scope, receive, send)`` passed straight through — NO
  buffering. This is what restores streaming: the deleted bridge (api/wiring/routers.py)
  buffered every ASGI ``send`` frame into a single ``Response`` and killed SSE. The path
  match is PRECISE (exact ``/mcp`` or the ``/mcp/`` prefix) so ``/mcpfoo`` is NOT captured.
- ``OPTIONS /mcp`` (a CORS preflight) -> the FastAPI app, so its outermost
  ``CORSMiddleware`` answers the preflight (200 + echoed origin + allowed headers). The
  MCP transport's own auth has no preflight exemption and would 401 a credential-less
  OPTIONS, breaking the browser-side claude.ai/claude.com connector handshake. This
  exactly restores the deleted bridge's behavior: its route listed only GET/POST/DELETE,
  so OPTIONS /mcp was always short-circuited by CORSMiddleware. OPTIONS carries no MCP
  payload and never streams, so routing it to FastAPI does not undermine the unbuffered
  split for real MCP traffic (BE-6060c regression fix — was: OPTIONS /mcp -> 401).
- everything else -> the FastAPI app (REST, OAuth ``/.well-known`` + ``/api/oauth``,
  dashboard SPA), unchanged, with its full 11-middleware onion intact.

This is a thin transport split — no new deps, tables, flags, or abstractions. It also
converts today's *accidental* isolation of /mcp from the FastAPI middleware onion (and
the four SaaS middlewares) into a tested, intentional policy.
"""

from __future__ import annotations

from starlette.types import ASGIApp, Receive, Scope, Send


class McpDispatcher:
    """Outermost ASGI app: routes /mcp HTTP traffic to ``mcp_app``, all else to ``fastapi_app``.

    Pure ASGI — passes ``(scope, receive, send)`` through unmodified so the MCP transport
    streams unbuffered. Lifespan and websocket scopes always go to ``fastapi_app`` (the
    FastAPI lifespan starts the shared MCP session manager the ``mcp_app`` relies on).
    """

    def __init__(self, fastapi_app: ASGIApp, mcp_app: ASGIApp) -> None:
        self.fastapi_app = fastapi_app
        self.mcp_app = mcp_app

    def __getattr__(self, name: str):
        """Delegate unknown attribute access to the wrapped FastAPI app.

        ``api.app.app`` used to BE the FastAPI instance; callers reach for
        ``app.state`` / ``app.dependency_overrides`` / ``app.routes`` (the test
        ASGITransport fixture, the websocket broadcaster in agent_jobs). The
        dispatcher is now the export, so it transparently forwards those reads to
        the FastAPI app while remaining the ASGI callable uvicorn invokes. Only
        reached for names NOT defined on the dispatcher itself (``__call__``,
        ``fastapi_app``, ``mcp_app``, ``_is_mcp_path``).
        """
        fastapi_app = self.__dict__.get("fastapi_app")
        if fastapi_app is None:
            raise AttributeError(name)
        return getattr(fastapi_app, name)

    @staticmethod
    def _is_mcp_path(path: str) -> bool:
        """True only for the exact ``/mcp`` path or the ``/mcp/`` prefix.

        A bare ``path.startswith("/mcp")`` would wrongly capture ``/mcpfoo``; the MCP
        transport owns exactly ``/mcp`` and everything under ``/mcp/``.
        """
        return path == "/mcp" or path.startswith("/mcp/")

    async def __call__(self, scope: Scope, receive: Receive, send: Send) -> None:
        # OPTIONS /mcp is a CORS preflight, not MCP traffic: route it to FastAPI so
        # CORSMiddleware answers it (the MCP transport's auth has no preflight exemption
        # and would 401 it, breaking the browser claude.ai/claude.com handshake). GET/
        # POST/DELETE /mcp stream straight to the unbuffered MCP app. See module docstring.
        if scope["type"] == "http" and self._is_mcp_path(scope["path"]) and scope.get("method") != "OPTIONS":
            await self.mcp_app(scope, receive, send)
            return
        await self.fastapi_app(scope, receive, send)
