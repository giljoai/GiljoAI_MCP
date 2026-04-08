# Copyright (c) 2024-2026 GiljoAI LLC. All rights reserved.
# Licensed under the GiljoAI Community License v1.1.
# See LICENSE in the project root for terms.
# [CE] Community Edition — source-available, single-user use only.

"""
GiljoAI MCP API Package
FastAPI-based REST and WebSocket API for orchestration system
"""

from .app import create_app


__all__ = ["create_app"]
