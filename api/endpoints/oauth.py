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
from urllib.parse import urlencode

from fastapi import APIRouter, Depends, Form, HTTPException, Request, status
from pydantic import BaseModel, Field

from src.giljo_mcp.auth.dependencies import get_current_active_user, get_db_session
from src.giljo_mcp.models import User
from src.giljo_mcp.services.oauth_service import OAuthService


logger = logging.getLogger(__name__)
router = APIRouter()


class AuthorizeRequest(BaseModel):
    """Request body for the OAuth authorize (consent) endpoint."""

    client_id: str = Field(..., description="OAuth client identifier")
    redirect_uri: str = Field(..., description="URI to redirect after authorization")
    code_challenge: str = Field(..., description="PKCE S256 code challenge")
    code_challenge_method: str = Field(default="S256", description="PKCE challenge method (must be S256)")
    scope: str = Field(default="mcp", description="Requested OAuth scope")
    state: str = Field(default="", description="Opaque state value for CSRF protection")
    response_type: str = Field(default="code", description="OAuth response type (must be code)")


class TokenResponse(BaseModel):
    """Response body for the OAuth token endpoint."""

    access_token: str
    token_type: str = "bearer"
    expires_in: int = 86400


class OAuthMetadataResponse(BaseModel):
    """OAuth 2.1 authorization server metadata (RFC 8414)."""

    issuer: str
    authorization_endpoint: str
    token_endpoint: str
    response_types_supported: list[str]
    code_challenge_methods_supported: list[str]
    grant_types_supported: list[str]


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
        oauth_service.validate_authorize_request(
            client_id=body.client_id,
            redirect_uri=body.redirect_uri,
            code_challenge=body.code_challenge,
            code_challenge_method=body.code_challenge_method,
            response_type=body.response_type,
            scope=body.scope,
        )
    except ValueError as exc:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=str(exc),
        ) from exc

    code = await oauth_service.generate_authorization_code(
        user_id=str(current_user.id),
        tenant_key=current_user.tenant_key,
        client_id=body.client_id,
        redirect_uri=body.redirect_uri,
        code_challenge=body.code_challenge,
        scope=body.scope,
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
    grant_type: str = Form(...),
    code: str = Form(...),
    client_id: str = Form(...),
    code_verifier: str = Form(...),
    redirect_uri: str = Form(...),
    db=Depends(get_db_session),
):
    """Exchange an authorization code for a JWT access token.

    This is a public endpoint (no authentication required). Accepts
    application/x-www-form-urlencoded per the OAuth 2.1 specification.

    Args:
        grant_type: Must be "authorization_code".
        code: The authorization code from the authorize step.
        client_id: OAuth client identifier.
        code_verifier: PKCE code verifier to prove possession.
        redirect_uri: Must match the URI used during authorization.
        db: Database session.

    Returns:
        TokenResponse with access_token, token_type, and expires_in.

    Raises:
        HTTPException 400: If grant_type is invalid, code exchange fails,
            or PKCE verification fails.
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
        )
    except ValueError as exc:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=str(exc),
        ) from exc

    return TokenResponse(
        access_token=result["access_token"],
        token_type=result["token_type"],
        expires_in=result["expires_in"],
    )


@router.get(
    "/.well-known/oauth-authorization-server",
    response_model=OAuthMetadataResponse,
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
    base_url = str(request.base_url).rstrip("/")

    return OAuthMetadataResponse(
        issuer=base_url,
        authorization_endpoint="/oauth/authorize",
        token_endpoint="/api/oauth/token",
        response_types_supported=["code"],
        code_challenge_methods_supported=["S256"],
        grant_types_supported=["authorization_code"],
    )
