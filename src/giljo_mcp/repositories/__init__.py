"""
Repository layer for GiljoAI MCP database operations.

Handover 0017: Provides clean abstractions for new agentic models with tenant filtering.
Handover 0043 Phase 2: Added VisionDocumentRepository for multi-vision document support.
Handover 1011 Phase 3: Added ConfigurationRepository and StatisticsRepository for migration from endpoints.

All repositories enforce multi-tenant isolation at the database level.
"""

from .agent_job_repository import AgentJobRepository
from .base import BaseRepository
from .configuration_repository import ConfigurationRepository
from .context_repository import ContextRepository
from .job_statistics_repository import JobStatisticsRepository
from .product_memory_repository import ProductMemoryRepository
from .product_statistics_repository import ProductStatisticsRepository
from .statistics_repository import StatisticsRepository
from .vision_document_repository import VisionDocumentRepository


__all__ = [
    "AgentJobRepository",
    "BaseRepository",
    "ConfigurationRepository",
    "ContextRepository",
    "JobStatisticsRepository",
    "ProductMemoryRepository",
    "ProductStatisticsRepository",
    "StatisticsRepository",
    "VisionDocumentRepository",
]
