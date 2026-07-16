# Copyright (c) 2024-2026 GiljoAI LLC. All rights reserved.
# Licensed under the Elastic License 2.0.
# See LICENSE in the project root for terms.
# [CE] Community Edition.

"""
Public-URL resolution for FastAPI request contexts (INF-5012).

Single source of truth for "what URL do my users see?". Delegates to
request.base_url, which FastAPI/Starlette populates from X-Forwarded-*
headers when Uvicorn is run with proxy_headers=True. This works for
every deployment edition (CE localhost, CE LAN mkcert, CE customer
nginx, Demo Cloudflare Tunnel, SaaS production) without any mode
branching.
"""

import os

from fastapi import Request
from starlette.requests import Request as StarletteRequest
from starlette.types import Scope


MCP_RESOURCE_PATH = "/mcp"


def _saas_pinned_base_url() -> str | None:
    """SEC-9171 (#30): SaaS-only origin pin for public-URL resolution.

    In SaaS mode the canonical public host is a single known value, while
    ``request.base_url`` honors X-Forwarded-Host — an attacker-influenceable
    header when the edge passes it through (uvicorn runs with
    ``proxy_headers=True``). Emailed lifecycle links (password reset, email
    verify, account deletion) built from it would then point at an attacker
    domain. Pinning is gated on BOTH ``GILJO_MODE=saas`` AND
    ``GILJO_PUBLIC_BASE_URL`` being set, so CE/LAN self-host deployments
    (nginx, mkcert LAN, tunnel) keep the request-derived flexibility.
    """
    if os.environ.get("GILJO_MODE", "").strip().lower() != "saas":
        return None
    pinned = os.environ.get("GILJO_PUBLIC_BASE_URL", "").strip().rstrip("/")
    return pinned or None


def get_public_base_url(request: Request) -> str:
    """
    Return the public base URL for the current request, without trailing slash.

    Honors X-Forwarded-Host / X-Forwarded-Proto via FastAPI + Uvicorn
    proxy_headers. Do NOT read the bind address from config — config values
    are the server's bind address, not its public address. The one exception
    is the SaaS origin pin (``GILJO_PUBLIC_BASE_URL``): the hosted edition's
    public address IS fixed config, and deriving it from the request would
    trust a spoofable header (SEC-9171 #30).

    Args:
        request: The incoming FastAPI Request.

    Returns:
        Base URL string like "https://mcp.example.com" or "http://localhost:7272".
    """
    pinned = _saas_pinned_base_url()
    if pinned:
        return pinned
    return str(request.base_url).rstrip("/")


def get_canonical_mcp_resource_uri(request: Request) -> str:
    """
    Return the canonical MCP resource URI for the current request (RFC 9728).

    This is the absolute, public-facing URL of the MCP transport endpoint
    (`/mcp`). Used as:
    - the `aud` claim baked into JWTs minted for MCP Bearer auth
    - the `resource` field in `/.well-known/oauth-protected-resource`
    - the audience the MCP middleware checks tokens against

    Single source of truth for "what URL identifies this MCP server" so the
    issuer and the validator can never drift.
    """
    return f"{get_public_base_url(request)}{MCP_RESOURCE_PATH}"


def get_canonical_mcp_resource_uri_from_scope(scope: Scope) -> str:
    """ASGI-scope variant of :func:`get_canonical_mcp_resource_uri`.

    The MCP Bearer middleware runs at the ASGI layer with no FastAPI Request
    object yet constructed. Wrapping the scope in a Starlette Request lets us
    reuse the same X-Forwarded-Host / X-Forwarded-Proto resolution that
    :func:`get_public_base_url` relies on — including the SaaS origin pin
    (SEC-9171 #30), so the token audience can never drift from the URL the
    issuer advertised.
    """
    pinned = _saas_pinned_base_url()
    if pinned:
        return f"{pinned}{MCP_RESOURCE_PATH}"
    request = StarletteRequest(scope)
    return f"{str(request.base_url).rstrip('/')}{MCP_RESOURCE_PATH}"
