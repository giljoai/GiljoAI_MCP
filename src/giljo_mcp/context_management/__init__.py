"""
Context Management System for GiljoAI MCP.

Handover 0018: Agentic Vision Document Chunking and Dynamic Context Loading.

This module provides production-grade context management with:
- VisionDocumentChunker: Tiktoken-based accurate token counting and semantic chunking
- ContextIndexer: Database storage and retrieval using PostgreSQL full-text search
- DynamicContextLoader: Role-based chunk selection and relevance scoring
- ContextSummarizer: Token reduction tracking and optimization
- ContextManagementSystem: Main orchestration interface

All operations enforce multi-tenant isolation via tenant_key.
"""

from .chunker import VisionDocumentChunker
from .indexer import ContextIndexer
from .loader import DynamicContextLoader
from .summarizer import ContextSummarizer
from .manager import ContextManagementSystem

__all__ = [
    "VisionDocumentChunker",
    "ContextIndexer",
    "DynamicContextLoader",
    "ContextSummarizer",
    "ContextManagementSystem",
]
