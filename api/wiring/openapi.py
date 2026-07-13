# Copyright (c) 2024-2026 GiljoAI LLC. All rights reserved.
# Licensed under the Elastic License 2.0.
# See LICENSE in the project root for terms.
# [CE] Community Edition.

"""OpenAPI server-list wiring extracted from api/app.py.

``build_openapi_servers`` returns the ``servers`` list passed to
``FastAPI(servers=...)``. It is a single root-relative entry so the API docs
resolve requests against whatever origin the docs page was loaded from.
"""

from __future__ import annotations


def build_openapi_servers() -> list[dict[str, str]]:
    """Return the OpenAPI ``servers`` list as one root-relative entry.

    A relative URL makes Swagger/ReDoc resolve "try it" requests against the
    exact origin the user opened ``/docs`` from -- so it is correct for every
    deployment automatically (localhost, a LAN/HTTPS box, or a hosted
    deployment) without reading any config.

    This replaces the former hardcoded ``localhost`` + ``0.0.0.0`` pair
    (BE-6045): ``0.0.0.0`` is a bind address, not a routable client target, and
    the localhost entry pinned the docs to the loopback even on LAN and
    SaaS-prod installs. The relative form also transparently honors a
    reverse-proxy ``root_path`` prefix, which an absolute URL would not.
    """
    return [{"url": "/", "description": "This server"}]
