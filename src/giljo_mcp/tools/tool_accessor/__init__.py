# Copyright (c) 2024-2026 GiljoAI LLC. All rights reserved.
# Licensed under the Elastic License 2.0.
# See LICENSE in the project root for terms.
# [CE] Community Edition.

"""
Tool Accessor for API Integration
Provides direct access to MCP tool functions for API endpoints

BE-6042a: This god-class was mechanically split into domain mixins under the
``tool_accessor/`` subpackage. The composed ``ToolAccessor`` below preserves the
load-bearing public import ``from giljo_mcp.tools.tool_accessor import ToolAccessor``
(used by api/startup/core_services.py + the boundary test fixtures). Construction
logic (``__init__`` + ``get_session_async``) stays here on the base; each tool
domain lives in its own mixin module.

BE-6118: after BE-3010b, ``_call_tool`` dispatches the ~30 PURE MCP tools straight
to their terminal service bound method via ``TOOL_DISPATCH`` (no longer through the
ToolAccessor mixin). The pure pass-through mixin methods were therefore deleted;
only the genuine ADAPTER methods (reshape results / build envelopes / inject deps
into standalone tool-functions / map params — resolved through ``_call_tool``'s
``getattr`` fallback) remain. The all-pure TaskToolsMixin + RoadmapToolsMixin were
removed entirely; the Project/Message/Comm/Job mixins keep only their adapters.
"""

from __future__ import annotations

import logging
from typing import TYPE_CHECKING, Any


if TYPE_CHECKING:
    from sqlalchemy.ext.asyncio import AsyncSession


from giljo_mcp.database import DatabaseManager
from giljo_mcp.services.comm_thread_service import CommThreadService
from giljo_mcp.services.message_routing_service import MessageRoutingService
from giljo_mcp.services.orchestration_service import OrchestrationService
from giljo_mcp.services.project_service import ProjectService
from giljo_mcp.services.roadmap_service import RoadmapService
from giljo_mcp.services.task_service import TaskService
from giljo_mcp.services.user_approval_service import UserApprovalService
from giljo_mcp.tenant import TenantManager
from giljo_mcp.tools.tool_accessor._chain_tools import ChainToolsMixin
from giljo_mcp.tools.tool_accessor._comm_tools import CommToolsMixin
from giljo_mcp.tools.tool_accessor._context_tools import ContextToolsMixin
from giljo_mcp.tools.tool_accessor._job_tools import JobLifecycleMixin
from giljo_mcp.tools.tool_accessor._memory_tools import MemoryToolsMixin
from giljo_mcp.tools.tool_accessor._message_tools import MessageToolsMixin
from giljo_mcp.tools.tool_accessor._project_tools import ProjectToolsMixin
from giljo_mcp.tools.tool_accessor._setup_tools import SetupMiscMixin


logger = logging.getLogger(__name__)


class ToolAccessor(
    ProjectToolsMixin,
    MessageToolsMixin,
    CommToolsMixin,
    ChainToolsMixin,
    JobLifecycleMixin,
    MemoryToolsMixin,
    ContextToolsMixin,
    SetupMiscMixin,
):
    """Provides direct access to MCP tool functionality for API"""

    def __init__(
        self,
        db_manager: DatabaseManager,
        tenant_manager: TenantManager,
        websocket_manager: Any | None = None,
        test_session: AsyncSession | None = None,
    ):
        self.db_manager = db_manager
        self.tenant_manager = tenant_manager
        self._websocket_manager = websocket_manager
        self._test_session = test_session

        self._product_service = None  # Lazy initialization per-request
        self._project_service = ProjectService(
            db_manager,
            tenant_manager,
            test_session=test_session,
            websocket_manager=websocket_manager,  # Fix: Pass WebSocket manager for mission updates
        )
        self._task_service = TaskService(
            db_manager,
            tenant_manager,
            websocket_manager=websocket_manager,
        )
        # FE-6022a: Roadmapping Pane writes
        self._roadmap_service = RoadmapService(
            db_manager,
            tenant_manager,
            session=test_session,
            websocket_manager=websocket_manager,
        )
        # BE-9012d: the bus send/broadcast methods were hard-removed; only the
        # relocated Hub reactivation coupling (auto_block_for_thread_post) remains.
        self._message_routing_service = MessageRoutingService(
            db_manager,
            tenant_manager,
            websocket_manager=websocket_manager,
        )
        # BE-6054b: Agent Message Hub thread/tool surface
        self._comm_thread_service = CommThreadService(
            db_manager,
            tenant_manager,
            session=test_session,
        )
        # BE-9012d: websocket_manager is now passed directly (previously smuggled
        # through the deleted MessageService's _websocket_manager fallback — see
        # OrchestrationService.__init__'s ``websocket_manager or getattr(message_service,
        # "_websocket_manager", None)``). Passing it explicitly here is required or the
        # sub-services (JobLifecycleService, MissionService, ProgressService,
        # OrchestrationAgentStateService) silently lose real-time WS emission.
        self._orchestration_service = OrchestrationService(
            db_manager,
            tenant_manager,
            test_session=test_session,
            websocket_manager=websocket_manager,
        )

        # BE-5029: User approval primitive. BE-9012d: comm_thread_service replaces
        # message_routing_service for the decide-notify Hub post (see
        # UserApprovalService._notify_orchestrator_of_decision).
        self._user_approval_service = UserApprovalService(
            db_manager,
            tenant_manager,
            websocket_manager=websocket_manager,
            test_session=test_session,
            comm_thread_service=self._comm_thread_service,
        )

        # Sprint 002f: Direct sub-service references for collapsed pass-throughs
        self._mission_service = self._orchestration_service._mission
        self._progress_service = self._orchestration_service._progress
        self._agent_state_service = self._orchestration_service._agent_state
        self._workflow_status_service = self._orchestration_service._workflow_status
        self._job_completion_service = self._orchestration_service._job_completion

    def get_session_async(self):
        """
        Get async session context manager.

        Uses test_session when available for transaction sharing in tests (Handover 0358c).
        """
        if self._test_session is not None:
            # Return async context manager that yields test session
            import contextlib

            @contextlib.asynccontextmanager
            async def _test_session_wrapper():
                yield self._test_session

            return _test_session_wrapper()
        return self.db_manager.get_session_async()
