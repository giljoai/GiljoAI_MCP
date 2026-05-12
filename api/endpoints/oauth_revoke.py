# Copyright (c) 2024-2026 GiljoAI LLC. All rights reserved.
# Licensed under the Elastic License 2.0.
# See LICENSE in the project root for terms.
# [CE] Community Edition.

"""RFC 7009 OAuth Token Revocation endpoint (API-0022).

Split out of ``api/endpoints/oauth.py`` so that module stays under the
800-line CI guardrail. Mounted under the same ``/api/oauth`` prefix as
the rest of the OAuth surface (see ``api/app.py`` router registration).

The endpoint is intentionally unauthenticated -- per RFC 7009 §2.1 the
presented token IS the credential. CSRF, network-auth, and the CI
auth-enforcement guardrail allowlist the route name (``revoke``).
"""

from __future__ import annotations

import json

from fastapi import APIRouter, Depends, HTTPException, Request, status
from fastapi.responses import Response

from giljo_mcp.auth.dependencies import get_db_session


router = APIRouter()


# Mirrors the caps in api/endpoints/oauth.py. The /revoke surface
# only consumes ``token`` and ``token_type_hint`` -- everything else
# in the body is ignored per RFC 7009 §2.1.
_REVOKE_FIELD_MAX_LENGTHS = {
    "token": 4096,
    "token_type_hint": 32,
}


async def _parse_revoke_body(request: Request) -> dict:
    """Parse the /revoke body as form (canonical) or JSON.

    Mirrors ``_parse_oauth_body`` in api/endpoints/oauth.py but kept
    local so this module has no implementation dependency on the
    sibling OAuth file (only the get_db_session dependency).
    """
    content_type = request.headers.get("content-type", "").lower()
    if "application/json" in content_type:
        try:
            data = await request.json()
        except (json.JSONDecodeError, ValueError, UnicodeDecodeError) as exc:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="invalid_request: malformed JSON body",
            ) from exc
        if not isinstance(data, dict):
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="invalid_request: body must be a JSON object",
            )
        return data

    form = await request.form()
    return dict(form.items())


def _enforce_caps(**fields: str | None) -> None:
    for name, value in fields.items():
        if value is None:
            continue
        cap = _REVOKE_FIELD_MAX_LENGTHS.get(name)
        if cap is not None and len(value) > cap:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail=f"invalid_request: {name} exceeds maximum length {cap}",
            )


@router.post("/revoke", tags=["oauth"])
async def revoke(
    request: Request,
    db=Depends(get_db_session),
):
    """RFC 7009 OAuth 2.0 Token Revocation (API-0022).

    Body (form or JSON): ``token`` (required), ``token_type_hint`` (optional;
    ``access_token`` or ``refresh_token``). The hint is advisory -- on first-
    type miss the service tries the other type.

    Response is ALWAYS 200 OK with empty body except when ``token`` is
    absent (400 invalid_request). Unknown, malformed, foreign, or already-
    revoked tokens still return 200 (RFC 7009 §2.2 -- no token-validity leak).

    Side effects:
      - Access JWT: persists a row in ``oauth_revoked_tokens`` keyed by the
        JWT's ``jti`` claim. The /mcp Bearer middleware rejects revoked
        tokens on the next request.
      - Refresh token: flips ``revoked=true`` on the entire token family
        (RFC 6749 §10.4 / OAuth 2.1 Security BCP).
    """
    from giljo_mcp.services import oauth_revocation_service as _revoke

    body = await _parse_revoke_body(request)
    token_value = body.get("token")
    token_type_hint = body.get("token_type_hint")

    if not isinstance(token_value, str):
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="invalid_request: token is required",
        )
    if token_type_hint is not None and not isinstance(token_type_hint, str):
        token_type_hint = None

    _enforce_caps(token=token_value, token_type_hint=token_type_hint)

    await _revoke.revoke_token(
        db,
        token=token_value,
        token_type_hint=token_type_hint,
    )

    return Response(status_code=status.HTTP_200_OK)
