# Copyright (c) 2024-2026 GiljoAI LLC. All rights reserved.
# Licensed under the Elastic License 2.0.
# See LICENSE in the project root for terms.
# [CE] Community Edition.

"""
OAuth 2.1 Authorization Code endpoints with PKCE.

Provides REST API for the OAuth 2.1 authorization code flow:
- POST /authorize: Process user consent and generate authorization code
- POST /token: Exchange authorization code for JWT access token
- GET /.well-known/oauth-authorization-server: OAuth server metadata

The authorize endpoint requires authentication (user must be logged in).
The token and metadata endpoints are public (no authentication required).

Handover 0828 Phase 3.
"""

import logging
import os
from urllib.parse import urlencode

from fastapi import APIRouter, Depends, Form, HTTPException, Request, status
from pydantic import BaseModel, Field

from giljo_mcp.auth.dependencies import get_current_active_user, get_db_session
from giljo_mcp.http.url_resolver import (
    get_canonical_mcp_resource_uri,
    get_public_base_url,
)
from giljo_mcp.models import User
from giljo_mcp.services.oauth_service import (
    DEFAULT_OAUTH_SCOPE,
    OAUTH_GRANTABLE_SCOPES,
    OAuthService,
)


logger = logging.getLogger(__name__)
router = APIRouter()

# Root-level well-known router (no prefix). RFC 8414 + RFC 9728 require these
# documents to be reachable from the host root, not from a /api/oauth subtree —
# Claude.ai / MCP clients probe `<host>/.well-known/...` per spec.
well_known_router = APIRouter()


class AuthorizeRequest(BaseModel):
    """Request body for the OAuth authorize (consent) endpoint."""

    client_id: str = Field(..., description="OAuth client identifier")
    redirect_uri: str = Field(..., description="URI to redirect after authorization")
    code_challenge: str = Field(..., description="PKCE S256 code challenge")
    code_challenge_method: str = Field(default="S256", description="PKCE challenge method (must be S256)")
    scope: str = Field(
        default=DEFAULT_OAUTH_SCOPE,
        description=(
            "Requested OAuth scope. Must be a subset of "
            f"{sorted(OAUTH_GRANTABLE_SCOPES)}. The orchestration scope "
            "(`mcp:agent`) is intentionally non-grantable via /authorize."
        ),
    )
    state: str = Field(default="", description="Opaque state value for CSRF protection")
    response_type: str = Field(default="code", description="OAuth response type (must be code)")
    # RFC 8707 — caps the URI length defensively at the route boundary; the
    # service layer re-validates shape (scheme/host/no-fragment) before any DB
    # write. Optional during the API-0021d transition window so older clients
    # that don't yet forward `resource` still complete /authorize.
    resource: str | None = Field(
        default=None,
        max_length=2048,
        description=(
            "RFC 8707 resource indicator. Identifies the target resource "
            "server (typically the canonical MCP URI). When supplied, it is "
            "persisted onto the auth-code record and re-asserted at /token."
        ),
    )


class TokenResponse(BaseModel):
    """Response body for the OAuth token endpoint."""

    access_token: str
    token_type: str = "bearer"
    expires_in: int = 86400
    refresh_token: str | None = None
    refresh_expires_in: int | None = None


class OAuthMetadataResponse(BaseModel):
    """OAuth 2.1 authorization server metadata (RFC 8414).

    All endpoint URLs are absolute (per RFC 8414 §2). The optional
    ``registration_endpoint`` is advertised only when DCR is available
    (SaaS/demo edition); CE omits the field rather than advertising a
    404 path.
    """

    issuer: str
    authorization_endpoint: str
    token_endpoint: str
    response_types_supported: list[str]
    code_challenge_methods_supported: list[str]
    grant_types_supported: list[str]
    registration_endpoint: str | None = None


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


@router.post("/authorize", tags=["oauth"])
async def authorize(
    request: Request,
    body: AuthorizeRequest,
    current_user: User = Depends(get_current_active_user),
    db=Depends(get_db_session),
):
    """Process OAuth authorization consent and generate an authorization code.

    Requires the user to be authenticated via JWT cookie. Validates the OAuth
    parameters, generates an authorization code bound to the user and PKCE
    challenge, and returns the redirect URI with the code and state.

    Args:
        request: FastAPI request object.
        body: OAuth authorization parameters.
        current_user: Authenticated user from JWT dependency.
        db: Database session.

    Returns:
        JSON with the redirect_uri containing the authorization code and state.

    Raises:
        HTTPException 400: If OAuth parameter validation fails.
    """
    oauth_service = OAuthService(db_session=db)

    try:
        await oauth_service.validate_authorize_request(
            client_id=body.client_id,
            redirect_uri=body.redirect_uri,
            code_challenge=body.code_challenge,
            code_challenge_method=body.code_challenge_method,
            response_type=body.response_type,
            scope=body.scope,
            tenant_key=current_user.tenant_key,
            resource=body.resource,
        )
    except ValueError as exc:
        logger.warning("OAuth authorize validation failed: %s", exc)
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Invalid authorization request parameters.",
        ) from exc

    code = await oauth_service.generate_authorization_code(
        user_id=str(current_user.id),
        tenant_key=current_user.tenant_key,
        client_id=body.client_id,
        redirect_uri=body.redirect_uri,
        code_challenge=body.code_challenge,
        scope=body.scope,
        resource=body.resource,
    )

    params = {"code": code}
    if body.state:
        params["state"] = body.state

    separator = "&" if "?" in body.redirect_uri else "?"
    redirect_target = f"{body.redirect_uri}{separator}{urlencode(params)}"

    logger.info(
        "Authorization code issued for user_id=%s client_id=%s",
        current_user.id,
        body.client_id,
    )

    return {"redirect_uri": redirect_target}


@router.post("/token", response_model=TokenResponse, tags=["oauth"])
async def token(
    request: Request,
    grant_type: str = Form(...),
    code: str = Form(...),
    client_id: str = Form(...),
    redirect_uri: str = Form(...),
    code_verifier: str | None = Form(default=None, max_length=512),
    resource: str | None = Form(default=None, max_length=2048),
    client_secret: str | None = Form(default=None, max_length=512),
    db=Depends(get_db_session),
):
    """Exchange an authorization code for a JWT access token.

    This is a public endpoint (no authentication required). Accepts
    application/x-www-form-urlencoded per the OAuth 2.1 specification.

    Args:
        grant_type: Must be "authorization_code".
        code: The authorization code from the authorize step.
        client_id: OAuth client identifier.
        redirect_uri: Must match the URI used during authorization.
        code_verifier: PKCE code verifier (RFC 7636). Required for public
            clients (no ``client_secret_hash`` on the resolved record),
            optional for confidential clients that authenticate via
            ``client_secret`` (RFC 6749 §6 treats client authentication and
            PKCE as alternative proof-of-possession mechanisms). When a
            confidential client DOES include a verifier, it must match the
            stored challenge (defense-in-depth). API-0021e Phase 1.1.
        resource: RFC 8707 resource indicator. Required when the auth-code
            record carries one (i.e. /authorize was called with `resource`);
            in that case the value here MUST equal the bound value or the
            request is rejected as ``invalid_grant`` (401). Optional only for
            pre-API-0021d in-flight codes that have no bound resource.
        client_secret: Plaintext client secret for confidential clients
            registered via RFC 7591 DCR (token_endpoint_auth_method =
            ``client_secret_post``). Required when the resolved client carries
            a ``client_secret_hash``; rejected as ``invalid_client`` (401)
            when missing or wrong. Public PKCE-only clients (built-in CE)
            MUST omit this field — sending it on a public client is also
            ``invalid_request`` (400). API-0021e Phase 1.
        db: Database session.

    Returns:
        TokenResponse with access_token, token_type, and expires_in.

    Raises:
        HTTPException 400: If grant_type is invalid or token exchange fails
            for non-resource reasons (PKCE, expiry, code reuse, …).
        HTTPException 401: If the resource indicator does not match the
            value bound to the auth-code record (``invalid_grant``), or the
            confidential client failed secret verification (``invalid_client``).
    """
    if grant_type != "authorization_code":
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=f"Unsupported grant_type: expected 'authorization_code', got '{grant_type}'",
        )

    oauth_service = OAuthService(db_session=db)

    try:
        result = await oauth_service.exchange_code_for_token(
            code=code,
            client_id=client_id,
            code_verifier=code_verifier,
            redirect_uri=redirect_uri,
            audience=get_canonical_mcp_resource_uri(request),
            resource=resource,
            client_secret=client_secret,
            tenant_key_hint=None,
        )
    except ValueError as exc:
        message = str(exc)
        # RFC 6749 §5.2: failed client authentication is invalid_client (401).
        # RFC 8707 §2.2: a resource mismatch at /token is invalid_grant (401).
        # All other validation failures (PKCE, code reuse, expired, missing
        # resource when required) stay invalid_request (400).
        if "invalid_client" in message:
            logger.warning("OAuth token client authentication failed: %s", exc)
            raise HTTPException(
                status_code=status.HTTP_401_UNAUTHORIZED,
                detail="invalid_client",
            ) from exc
        if "resource does not match" in message:
            logger.warning("OAuth token resource mismatch: %s", exc)
            raise HTTPException(
                status_code=status.HTTP_401_UNAUTHORIZED,
                detail="invalid_grant",
            ) from exc
        logger.warning("OAuth token exchange failed: %s", exc)
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="invalid_request",
        ) from exc

    return TokenResponse(
        access_token=result["access_token"],
        token_type=result["token_type"],
        expires_in=result["expires_in"],
        refresh_token=result.get("refresh_token"),
        refresh_expires_in=result.get("refresh_expires_in"),
    )


@router.post("/refresh", response_model=TokenResponse, response_model_exclude_none=True, tags=["oauth"])
async def refresh(
    grant_type: str = Form(...),
    refresh_token: str = Form(..., max_length=512),
    client_id: str = Form(...),
    client_secret: str | None = Form(default=None, max_length=512),
    db=Depends(get_db_session),
):
    """Exchange a refresh token for a new access+refresh pair (API-0021e Phase 2).

    Public endpoint; ``client_secret_post`` confidential clients only. Public
    PKCE clients never receive a refresh token at /token, so /refresh
    intentionally rejects them as ``invalid_client``.

    Args:
        grant_type: Must be ``"refresh_token"`` (RFC 6749 §6).
        refresh_token: Plaintext refresh token from the prior /token or
            /refresh response.
        client_id: Client identifier (DCR-registered).
        client_secret: Confidential client secret (required + verified).
        db: Database session.

    Returns:
        TokenResponse with new ``access_token`` + rotated ``refresh_token``.
        The previous refresh token is marked revoked; reuse triggers
        family-wide revocation per RFC 6749 §10.4.

    Raises:
        HTTPException 400: ``invalid_request`` (grant_type wrong, missing field).
        HTTPException 401: ``invalid_client`` (auth failed) or
            ``invalid_grant`` (token unknown / revoked / expired).
    """
    if grant_type != "refresh_token":
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=f"Unsupported grant_type: expected 'refresh_token', got '{grant_type}'",
        )

    oauth_service = OAuthService(db_session=db)
    try:
        result = await oauth_service.refresh_token_grant(
            refresh_token=refresh_token,
            client_id=client_id,
            client_secret=client_secret,
        )
    except ValueError as exc:
        message = str(exc)
        if message.startswith("invalid_client"):
            logger.warning("OAuth refresh client authentication failed: %s", exc)
            raise HTTPException(
                status_code=status.HTTP_401_UNAUTHORIZED,
                detail="invalid_client",
            ) from exc
        if message.startswith("invalid_grant"):
            logger.warning("OAuth refresh invalid_grant: %s", exc)
            raise HTTPException(
                status_code=status.HTTP_401_UNAUTHORIZED,
                detail="invalid_grant",
            ) from exc
        logger.warning("OAuth refresh request invalid: %s", exc)
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="invalid_request",
        ) from exc

    return TokenResponse(
        access_token=result["access_token"],
        token_type=result["token_type"],
        expires_in=result["expires_in"],
        refresh_token=result.get("refresh_token"),
        refresh_expires_in=result.get("refresh_expires_in"),
    )


@router.get(
    "/.well-known/oauth-authorization-server",
    response_model=OAuthMetadataResponse,
    response_model_exclude_none=True,  # CE omits registration_endpoint cleanly
    tags=["oauth"],
)
async def oauth_metadata(request: Request):
    """Return OAuth 2.1 authorization server metadata (RFC 8414).

    This is a public endpoint. Returns the server's OAuth configuration
    so clients can discover endpoints and supported features.

    Args:
        request: FastAPI request object (for building issuer URL).

    Returns:
        OAuthMetadataResponse with server metadata.
    """
    base_url = get_public_base_url(request)

    # RFC 8414 §2 — absolute endpoint URLs. Pre-fix returned bare paths
    # ("/oauth/authorize"); some clients (claude.ai) coped via issuer-resolution
    # but others fail or skip optional endpoints when paths aren't absolute.
    authorization_endpoint = f"{base_url}/oauth/authorize"
    token_endpoint = f"{base_url}/api/oauth/token"

    # RFC 7591 dynamic client registration endpoint — advertised ONLY when the
    # SaaS/demo edition is active. The DCR endpoint lives under saas_endpoints/
    # which is stripped on CE export, so CE omits this field. claude.ai and
    # other DCR-using clients pick up `registration_endpoint` here; without it
    # they fall back to the conventional `<issuer>/register` (which 404s here)
    # and the connector setup fails before consent.
    giljo_mode = os.environ.get("GILJO_MODE", "").lower()
    registration_endpoint: str | None = None
    if giljo_mode in ("demo", "saas"):
        registration_endpoint = f"{base_url}/api/saas/oauth/register"

    return OAuthMetadataResponse(
        issuer=base_url,
        authorization_endpoint=authorization_endpoint,
        token_endpoint=token_endpoint,
        response_types_supported=["code"],
        code_challenge_methods_supported=["S256"],
        # API-0021e Phase 3: advertise the refresh_token grant. Confidential
        # DCR clients receive a refresh_token at /token and rotate it via
        # /api/oauth/refresh. Public PKCE-only clients can still only use
        # authorization_code (the refresh path rejects them server-side).
        grant_types_supported=["authorization_code", "refresh_token"],
        registration_endpoint=registration_endpoint,
    )


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
