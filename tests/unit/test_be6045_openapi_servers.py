# Copyright (c) 2024-2026 GiljoAI LLC. All rights reserved.
# Licensed under the Elastic License 2.0.
# See LICENSE in the project root for terms.

"""BE-6045 regression: OpenAPI ``servers`` list is root-relative.

The former implementation hardcoded ``http(s)://localhost:7272`` and
``http(s)://0.0.0.0:7272``. ``0.0.0.0`` is a bind address (not a routable
client target) and the localhost entry pinned the docs dropdown to the loopback
on LAN and SaaS-prod installs. A single root-relative entry resolves against
whatever origin ``/docs`` was loaded from, so it is correct for every
deployment without reading config. Edition Scope: CE/Both.
"""

from __future__ import annotations

from api.wiring.openapi import build_openapi_servers


def test_servers_is_single_root_relative_entry():
    assert build_openapi_servers() == [{"url": "/", "description": "This server"}]


def test_never_advertises_bind_address_or_hardcoded_host():
    blob = repr(build_openapi_servers())
    # The exact regression being guarded: no bind address, no pinned loopback,
    # no hardcoded port leaking into the published API docs.
    assert "0.0.0.0" not in blob
    assert "localhost" not in blob
    assert "127.0.0.1" not in blob
    assert "7272" not in blob


def test_every_entry_has_fastapi_required_shape():
    servers = build_openapi_servers()
    assert servers, "servers list must be non-empty"
    for entry in servers:
        assert set(entry) >= {"url", "description"}
        # Relative URLs only -- correct under any host/scheme/proxy prefix.
        assert entry["url"].startswith("/")
