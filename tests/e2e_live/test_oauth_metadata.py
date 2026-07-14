# Copyright (c) 2024-2026 GiljoAI LLC. All rights reserved.
# Licensed under the Elastic License 2.0.
# See LICENSE in the project root for terms.
# [CE] Community Edition.

"""(c) OAuth 2.0 Protected Resource metadata (RFC 9728) is served + well-formed.

Spec-aware MCP clients (claude.ai connector, MCP Inspector) probe
``/.well-known/oauth-protected-resource`` at the host root. This must return the
JSON document (not the SPA's index.html via the 404 fallback) with the RFC 9728
fields the server advertises. Validating it over the live edge catches the exact
class of routing/proxy regression where the catch-all swallows the well-known
path.
"""

from __future__ import annotations

import pytest


@pytest.mark.network
def test_oauth_protected_resource_metadata_shape(http_client):
    resp = http_client.get("/.well-known/oauth-protected-resource")
    assert resp.status_code == 200, resp.text
    assert resp.headers.get("content-type", "").startswith("application/json"), resp.headers.get("content-type")

    body = resp.json()
    # Fields per ProtectedResourceMetadataResponse in api/endpoints/oauth.py.
    assert isinstance(body.get("resource"), str) and body["resource"], body
    assert isinstance(body.get("authorization_servers"), list) and body["authorization_servers"], body
    assert isinstance(body.get("scopes_supported"), list), body
    assert isinstance(body.get("bearer_methods_supported"), list), body
    # RFC 8707: this server advertises resource-indicator support.
    assert body.get("resource_indicators_supported") is True, body
