# Copyright (c) 2024-2026 GiljoAI LLC. All rights reserved.
# Licensed under the Elastic License 2.0.
# See LICENSE in the project root for terms.
# [CE] Community Edition.

"""Root-level OAuth/MCP discovery documents (RFC 8414 / RFC 9728).

Split out of ``api/endpoints/oauth.py`` (BE-5088) so that module stays under
the 800-line CI guardrail once BE-6040 added the RFC 6749 §5.2 error envelope.

These documents MUST be reachable from the host root (``<host>/.well-known/…``),
not from a ``/api/oauth`` subtree — Claude.ai / MCP clients probe the root per
spec. The AS-metadata *body* is still owned by ``oauth.py``'s
``oauth_metadata`` handler; the root mirror here simply re-invokes it so there
is a single source of truth. Mounted via ``well_known_router`` in
``api/wiring/routers.py``.

Route function names (``oauth_metadata_root_mirror``,
``oauth_protected_resource_metadata``,
``oauth_protected_resource_metadata_pathsuffix``) are referenced by the CI
auth-enforcement allowlist (``scripts/ci_guardrails.sh`` Guardrail 3) — keep
them stable when editing.
"""

from __future__ import annotations

from fastapi import APIRouter, Request
from fastapi.responses import JSONResponse
from pydantic import BaseModel

from api.endpoints.oauth import (
    MCP_SPEC_VERSIONS_SUPPORTED,
    OAuthMetadataResponse,
    oauth_metadata,
)
from giljo_mcp.http.url_resolver import (
    get_canonical_mcp_resource_uri,
    get_public_base_url,
)
from giljo_mcp.services.oauth_service import OAUTH_GRANTABLE_SCOPES


# Root-level well-known router (no prefix). RFC 8414 + RFC 9728 require these
# documents to be reachable from the host root, not from a /api/oauth subtree —
# Claude.ai / MCP clients probe `<host>/.well-known/...` per spec.
well_known_router = APIRouter()


class ProtectedResourceMetadataResponse(BaseModel):
    """OAuth 2.0 Protected Resource metadata (RFC 9728).

    Per RFC 8707 §3, advertises ``resource_indicators_supported: true`` so
    spec-aware clients (claude.ai connector backend) know they MUST send
    ``resource`` to /authorize and /token. API-0021d Phase 2 enforces that
    binding server-side.
    """

    resource: str
    authorization_servers: list[str]
    scopes_supported: list[str]
    bearer_methods_supported: list[str]
    resource_indicators_supported: bool = True


@well_known_router.get(
    "/.well-known/oauth-authorization-server",
    response_model=OAuthMetadataResponse,
    response_model_exclude_none=True,  # CE omits registration_endpoint cleanly
    tags=["oauth"],
)
async def oauth_metadata_root_mirror(request: Request):
    """RFC 8414 root-path mirror of `/api/oauth/.well-known/oauth-authorization-server`.

    Spec-compliant clients (Claude.ai, MCP CLI tooling) probe the root path
    first. Body is identical to the `/api/oauth/...` route — same handler
    invoked for a single source of truth.
    """
    return await oauth_metadata(request)


@well_known_router.get(
    "/.well-known/oauth-protected-resource",
    response_model=ProtectedResourceMetadataResponse,
    tags=["oauth"],
)
async def oauth_protected_resource_metadata(request: Request):
    """Return OAuth 2.0 Protected Resource metadata for `/mcp` (RFC 9728).

    Tells clients which authorization server issues tokens for this resource
    and how to present them. The `WWW-Authenticate` header on `/mcp` 401s
    points here so a client that just got rejected can self-bootstrap.
    """
    return ProtectedResourceMetadataResponse(
        resource=get_canonical_mcp_resource_uri(request),
        authorization_servers=[get_public_base_url(request)],
        scopes_supported=sorted(OAUTH_GRANTABLE_SCOPES),
        bearer_methods_supported=["header"],
    )


# API-0021k — RFC 9728 §3.1 path-suffix discovery variant. Spec-aware clients
# (claude.ai connector backend, MCP Inspector) probe
# `<host>/.well-known/oauth-protected-resource/<resource-path>` to ask "tell me
# about the protected resource at this path". Without this route, the Vue SPA
# catch-all in api/app.py intercepts the 404 and serves index.html (200 HTML),
# misleading clients into parsing an OAuth-irrelevant body. Only `/mcp` is a
# valid resource on this server; everything else is 404. Single source of truth
# preserved by re-invoking the host-only handler — no duplicated response body.
# The unknown-suffix branch returns JSONResponse(status_code=404) directly
# rather than `raise HTTPException(404)` because the SPA fallback in
# api/app.py is registered as `@app.exception_handler(404)` and intercepts
# raised 404s for any path outside its prefix allowlist (which does not
# include `/.well-known/...`). Same pattern as the openid-configuration route.
@well_known_router.get(
    "/.well-known/oauth-protected-resource/{resource_path:path}",
    response_model=ProtectedResourceMetadataResponse,
    include_in_schema=False,
    tags=["oauth"],
)
async def oauth_protected_resource_metadata_pathsuffix(
    resource_path: str,
    request: Request,
):
    """RFC 9728 §3.1 path-suffix variant: `/.well-known/oauth-protected-resource/{path}`.

    Returns identical metadata to the host-only form for `resource_path == "mcp"`;
    404 for any other suffix. `mcp` is the only protected resource this server
    exposes — multi-resource support is out of scope (API-0021k).
    """
    if resource_path.lstrip("/") != "mcp":
        return JSONResponse(
            status_code=404,
            content={"error": "Not Found"},
        )
    return await oauth_protected_resource_metadata(request)


# API-0021i: spec-aware clients (claude.ai, OIDC libraries) probe the OIDC
# discovery document opportunistically when bootstrapping against an unknown
# issuer. We don't implement OIDC, so the correct signal is 404 ("path not
# found"), not 401 ("path exists but you're unauthenticated"). The explicit
# registration is also load-bearing: without it, the SPA-fallback 404 handler
# in api/app.py would intercept this path and return index.html (200 HTML),
# misleading clients into parsing an OAuth-irrelevant body.
@well_known_router.get(
    "/.well-known/openid-configuration",
    include_in_schema=False,
    tags=["oauth"],
)
async def oidc_configuration_not_supported():
    """Return 404 for the OIDC discovery document — OIDC is not implemented."""
    return JSONResponse(
        status_code=404,
        content={"error": "OIDC not supported on this server"},
    )


class McpServerInfoResponse(BaseModel):
    """MCP spec-version + capability discovery document (API-0021h).

    Lightweight companion to OAuth AS-metadata: exposes the declared MCP
    spec-version list, the server identity, and a capability snapshot read
    from the canonical FastMCP tool registry. Surface for conformance
    discovery without forcing the client through `initialize`.
    """

    spec_versions: list[str]
    capabilities: dict
    server_name: str
    server_version: str


@well_known_router.get(
    "/.well-known/mcp-server-info",
    response_model=McpServerInfoResponse,
    tags=["oauth"],
)
async def mcp_server_info():
    """Return MCP spec-version + capability discovery document (API-0021h).

    Public, unauthenticated endpoint. Capability data is read from canonical
    sources — `TOOL_SCOPES` (defined alongside the FastMCP instance) for the
    scope-per-tool map, `giljo_mcp.__version__` for `server_version`. No
    duplicate registries.
    """
    # Local import avoids the api.endpoints.mcp_sdk_server ↔ api.endpoints.oauth
    # cycle at module load. FastMCP setup transitively imports modules that
    # depend on api.app; the lazy import keeps this module importable in any order.
    from api.endpoints.mcp_sdk_server import TOOL_SCOPES, mcp
    from giljo_mcp import __version__ as giljo_version

    capabilities: dict = {
        "tools": {
            "count": len(TOOL_SCOPES),
            "scopes": dict(TOOL_SCOPES),
        }
    }

    return McpServerInfoResponse(
        spec_versions=list(MCP_SPEC_VERSIONS_SUPPORTED),
        capabilities=capabilities,
        server_name=mcp.name,
        server_version=giljo_version,
    )
