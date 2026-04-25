# Copyright (c) 2024-2026 GiljoAI LLC. All rights reserved.
# Licensed under the GiljoAI Community License v1.1.
# See LICENSE in the project root for terms.
# [CE] Community Edition — source-available, single-user use only.

"""
Public-URL resolution for FastAPI request contexts (INF-5012).

Single source of truth for "what URL do my users see?". Delegates to
request.base_url, which FastAPI/Starlette populates from X-Forwarded-*
headers when Uvicorn is run with proxy_headers=True. This works for
every deployment edition (CE localhost, CE LAN mkcert, CE customer
nginx, Demo Cloudflare Tunnel, SaaS production) without any mode
branching.
"""

from fastapi import Request


def get_public_base_url(request: Request) -> str:
    """
    Return the public base URL for the current request, without trailing slash.

    Honors X-Forwarded-Host / X-Forwarded-Proto via FastAPI + Uvicorn
    proxy_headers. Do NOT read from config — config values are the
    server's bind address, not its public address.

    Args:
        request: The incoming FastAPI Request.

    Returns:
        Base URL string like "https://demo.giljo.ai" or "http://localhost:7272".
    """
    return str(request.base_url).rstrip("/")
