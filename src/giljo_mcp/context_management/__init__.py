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
