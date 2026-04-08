# Copyright (c) 2024-2026 GiljoAI LLC. All rights reserved.
# Licensed under the GiljoAI Community License v1.1.
# See LICENSE in the project root for terms.
# [CE] Community Edition — source-available, single-user use only.

"""
GiljoAI MCP - Multi-Agent Coding Orchestrator
"""

try:
    from importlib.metadata import PackageNotFoundError
    from importlib.metadata import version as _get_version

    __version__ = _get_version("giljo-mcp")
except (PackageNotFoundError, ImportError):
    __version__ = "1.0.0"
