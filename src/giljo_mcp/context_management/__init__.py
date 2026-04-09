# Copyright (c) 2024-2026 GiljoAI LLC. All rights reserved.
# Licensed under the GiljoAI Community License v1.1.
# See LICENSE in the project root for terms.
# [CE] Community Edition — source-available, single-user use only.

"""
Context Management for GiljoAI MCP.

Provides vision document chunking with tiktoken-based token counting
and semantic chunking. All operations enforce multi-tenant isolation
via tenant_key.
"""

from .chunker import VisionDocumentChunker

__all__ = [
    "VisionDocumentChunker",
]
