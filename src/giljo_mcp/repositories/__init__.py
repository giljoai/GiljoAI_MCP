# Copyright (c) 2024-2026 GiljoAI LLC. All rights reserved.
# Licensed under the GiljoAI Community License v1.1.
# See LICENSE in the project root for terms.
# [CE] Community Edition — source-available, single-user use only.

"""
Repository layer for GiljoAI MCP database operations.

Handover 0017: Provides clean abstractions for new agentic models with tenant filtering.
Handover 0043 Phase 2: Added VisionDocumentRepository for multi-vision document support.
Handover 1011 Phase 3: Added ConfigurationRepository and StatisticsRepository for migration from endpoints.

All repositories enforce multi-tenant isolation at the database level.
"""

from .agent_completion_repository import AgentCompletionRepository
from .agent_job_repository import AgentJobRepository
from .agent_operations_repository import AgentOperationsRepository
from .auth_repository import AuthRepository
from .base import BaseRepository
from .configuration_repository import ConfigurationRepository
from .context_repository import ContextRepository
from .job_statistics_repository import JobStatisticsRepository
from .mission_repository import MissionRepository
from .org_repository import OrgRepository
from .product_memory_repository import ProductMemoryRepository
from .product_repository import ProductRepository
from .product_statistics_repository import ProductStatisticsRepository
from .progress_repository import ProgressRepository
from .project_lifecycle_repository import ProjectLifecycleRepository
from .project_repository import ProjectRepository
from .project_type_repository import ProjectTypeRepository
from .settings_repository import SettingsRepository
from .statistics_repository import StatisticsRepository
from .task_repository import TaskRepository
from .template_repository import TemplateRepository
from .user_repository import UserRepository
from .vision_document_repository import VisionDocumentRepository


__all__ = [
    "AgentCompletionRepository",
    "AgentJobRepository",
    "AgentOperationsRepository",
    "AuthRepository",
    "BaseRepository",
    "ConfigurationRepository",
    "ContextRepository",
    "JobStatisticsRepository",
    "MissionRepository",
    "OrgRepository",
    "ProductMemoryRepository",
    "ProductRepository",
    "ProductStatisticsRepository",
    "ProgressRepository",
    "ProjectLifecycleRepository",
    "ProjectRepository",
    "ProjectTypeRepository",
    "SettingsRepository",
    "StatisticsRepository",
    "TaskRepository",
    "TemplateRepository",
    "UserRepository",
    "VisionDocumentRepository",
]
