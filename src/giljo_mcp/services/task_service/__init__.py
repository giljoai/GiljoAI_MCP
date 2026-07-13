# Copyright (c) 2024-2026 GiljoAI LLC. All rights reserved.
# Licensed under the Elastic License 2.0.
# See LICENSE in the project root for terms.
# [CE] Community Edition.

"""
TaskService - Dedicated service for task management

This service extracts all task-related operations from ToolAccessor
as part of Phase 2 of the god object refactoring (Handover 0123).
Updated for typed returns (Handover 0731c).

Responsibilities:
- CRUD operations for tasks
- Task assignment to agents
- Task status tracking and lifecycle
- Task prioritization and categorization

Design Principles:
- Single Responsibility: Only task domain logic
- Dependency Injection: Accepts DatabaseManager and TenantManager
- Async/Await: Full SQLAlchemy 2.0 async support
- Error Handling: Consistent exception handling and logging
- Testability: Can be unit tested independently

Return Type Conventions (0731c):
- Simple lookups return the ORM model directly (Task)
- Not-found cases raise ResourceNotFoundError
- Validation failures raise ValidationError
- Authorization failures raise AuthorizationError
- Delete operations return None (already correct)
- Update operations return TaskUpdateResult
- Conversion operations return ConversionResult
- List operations return list[Task]
- Summary operations return dict (complex nested structure)

BE-9073 (item 2): this god-class was mechanically split into domain mixins
under the ``task_service/`` subpackage, mirroring the ``project_service``
package precedent (BE-6042c). The composed ``TaskService`` below preserves
the load-bearing public import ``from giljo_mcp.services.task_service import
TaskService`` (21+ importers across src/tools, api, tests). Shared
construction (``__init__`` + the ``_get_session`` helper) stays here on the
base; the read path lives in ``_query_mixin._TaskQueryMixin``, core CRUD
write methods live in ``_mutation_mixin._TaskMutationMixin``, status-change /
conversion / completion-notes lifecycle methods live in
``_lifecycle_mixin._TaskLifecycleMixin`` (split out of the mutation mixin so
every file in this package stays under the 800-line cap with no
``size_budgets.txt`` entry), and the agent-facing MCP surface lives in
``_mcp_adapter_mixin.McpAdapterMixin`` (unchanged, BE-9060). The
``_ALLOWED_TASK_UPDATE_FIELDS`` allowlist is preserved on this module.
Behavior is unchanged.
"""

import logging
from typing import Any

from sqlalchemy.ext.asyncio import AsyncSession

from giljo_mcp.database import DatabaseManager
from giljo_mcp.repositories.task_repository import TaskRepository
from giljo_mcp.services._session_helpers import optional_tenant_session
from giljo_mcp.services.task_conversion_service import TaskConversionService
from giljo_mcp.services.task_service._lifecycle_mixin import _TaskLifecycleMixin
from giljo_mcp.services.task_service._mcp_adapter_mixin import McpAdapterMixin
from giljo_mcp.services.task_service._mutation_mixin import (
    _ALLOWED_TASK_UPDATE_FIELDS as _ALLOWED_TASK_UPDATE_FIELDS,
)
from giljo_mcp.services.task_service._mutation_mixin import _TaskMutationMixin
from giljo_mcp.services.task_service._query_mixin import _TaskQueryMixin
from giljo_mcp.tenant import TenantManager


logger = logging.getLogger(__name__)


class TaskService(McpAdapterMixin, _TaskMutationMixin, _TaskLifecycleMixin, _TaskQueryMixin):
    """
    Service for managing tasks.

    This service handles all task-related operations including:
    - Creating and logging tasks
    - Listing and filtering tasks
    - Updating task status and properties
    - Task-agent assignment
    - Task completion

    Thread Safety: Each instance is session-scoped. Do not share across requests.
    """

    def __init__(
        self,
        db_manager: DatabaseManager = None,
        tenant_manager: TenantManager = None,
        session: AsyncSession | None = None,
        websocket_manager: Any | None = None,
    ):
        """
        Initialize TaskService with database and tenant management.

        Args:
            db_manager: Database manager for async database operations
            tenant_manager: Tenant manager for multi-tenancy support
            session: Optional AsyncSession for test transaction isolation (Handover 0324)
            websocket_manager: Optional WS manager for task:updated broadcasts (FE-5046)
        """
        self.db_manager = db_manager
        self.tenant_manager = tenant_manager
        self._session = session  # Store for test transaction isolation
        self._websocket_manager = websocket_manager
        self._logger = logging.getLogger(f"{__name__}.{self.__class__.__name__}")
        self._repo = TaskRepository()
        self._conversion = TaskConversionService(db_manager, tenant_manager, session)

    def _get_session(self, tenant_key: str | None = None):
        """Yield a tenant-scoped DB session, honoring an injected test session (shared helper, BE-8000d)."""
        return optional_tenant_session(
            self.db_manager, tenant_key or self.tenant_manager.get_current_tenant(), self._session
        )
