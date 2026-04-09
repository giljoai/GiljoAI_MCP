# Copyright (c) 2024-2026 GiljoAI LLC. All rights reserved.
# Licensed under the GiljoAI Community License v1.1.
# See LICENSE in the project root for terms.
# [CE] Community Edition — source-available, single-user use only.

"""
MCP Tools for Agent Coordination (Handover 0045).

Provides universal coordination layer for Claude Code, Codex, and Gemini AI coding agents.
All tools enforce multi-tenant isolation and integrate with AgentJobManager.

Production-grade features:
- Multi-tenant isolation enforcement
- Exception-based error handling (post-0480)
- Audit logging for all operations
- Type validation and safety checks
- Delegation to AgentJobManager service layer (Handover 0769a)
"""

import logging
from typing import Any, Optional

from src.giljo_mcp.database import DatabaseManager
from src.giljo_mcp.exceptions import ValidationError

logger = logging.getLogger(__name__)


# Module-level state holder
class _AgentCoordinationState:
    """State holder to avoid global statement."""

    db_manager_instance: Optional[DatabaseManager] = None
    test_session = None


def _get_db_manager() -> DatabaseManager:
    """Get or create database manager instance."""
    if _AgentCoordinationState.db_manager_instance is None:
        _AgentCoordinationState.db_manager_instance = DatabaseManager()
    return _AgentCoordinationState.db_manager_instance


def set_db_manager(db_manager: DatabaseManager) -> None:
    """
    Set the database manager for module-level functions.

    This allows tests to inject a specific database manager instance.
    """
    _AgentCoordinationState.db_manager_instance = db_manager


def init_for_testing(db_manager: DatabaseManager, db_session) -> None:
    """
    Initialize module for testing with shared session (Handover 0366c).

    This allows spawn_agent() to use the same
    database session as test fixtures, preventing session isolation issues.

    Args:
        db_manager: DatabaseManager instance for tests
        db_session: Shared AsyncSession for test transaction isolation

    Usage (in conftest.py):
        @pytest_asyncio.fixture(scope="function", autouse=True)
        async def setup_agent_coordination(db_manager, db_session):
            from src.giljo_mcp.tools import agent_coordination
            agent_coordination.init_for_testing(db_manager, db_session)
            yield
    """
    _AgentCoordinationState.db_manager_instance = db_manager
    _AgentCoordinationState.test_session = db_session


def _create_job_manager():
    """Create AgentJobManager with current state."""
    from src.giljo_mcp.services.agent_job_manager import AgentJobManager
    from src.giljo_mcp.tenant import TenantManager

    db_manager = _get_db_manager()
    tenant_manager = TenantManager()
    return AgentJobManager(
        db_manager=db_manager,
        tenant_manager=tenant_manager,
        test_session=_AgentCoordinationState.test_session,
    )


# Module-level functions for direct import (Handover 0366c)
async def spawn_agent(
    job_id: str,
    agent_display_name: str,
    tenant_key: str,
    spawned_by_agent_id: str = None,
) -> dict[str, Any]:
    """
    Spawn NEW executor for EXISTING job (Handover 0366c).

    Creates a NEW AgentExecution (executor instance) that references
    an EXISTING AgentJob (work order). Enables agent succession while
    preserving job continuity.

    Delegates to AgentJobManager.spawn_execution() (Handover 0769a).

    Args:
        job_id: AgentJob UUID to spawn execution for (must exist)
        agent_display_name: Agent display name for this executor
        tenant_key: Tenant key for multi-tenant isolation
        spawned_by_agent_id: Parent executor's agent_id (for succession tracking)

    Returns:
        dict with success, job_id, agent_id

    Raises:
        ValidationError: Empty required parameters
        ResourceNotFoundError: Job not found for tenant
    """
    if not job_id or not job_id.strip():
        raise ValidationError(message="job_id cannot be empty")

    if not agent_display_name or not agent_display_name.strip():
        raise ValidationError(message="agent_display_name cannot be empty")

    if not tenant_key or not tenant_key.strip():
        raise ValidationError(message="tenant_key cannot be empty")

    job_manager = _create_job_manager()
    job_id, new_agent_id = await job_manager.spawn_execution(
        job_id=job_id,
        agent_display_name=agent_display_name,
        tenant_key=tenant_key,
        spawned_by=spawned_by_agent_id,
    )

    logger.info(f"[spawn_agent] Spawned agent_id={new_agent_id} for job_id={job_id}, tenant={tenant_key}")

    return {
        "success": True,
        "job_id": job_id,
        "agent_id": new_agent_id,
    }


async def get_team_agents(
    job_id: str,
    tenant_key: str,
    include_inactive: bool = False,
) -> dict[str, Any]:
    """
    List agent executions (teammates) associated with this job.

    Handover 0360 Feature 2: Team Discovery Tool.
    Delegates to AgentJobManager.list_team_agents().

    Args:
        job_id: Job ID to get teammates for
        tenant_key: Tenant key for multi-tenant isolation
        include_inactive: If True, include completed/decommissioned executions

    Returns:
        dict with success flag and team member list

    Raises:
        ValidationError: Empty required parameters
    """
    if not job_id or not job_id.strip():
        raise ValidationError(message="job_id cannot be empty")

    if not tenant_key or not tenant_key.strip():
        raise ValidationError(message="tenant_key cannot be empty")

    job_manager = _create_job_manager()
    team_members = await job_manager.list_team_agents(
        job_id=job_id,
        tenant_key=tenant_key,
        include_inactive=include_inactive,
    )

    logger.info(
        f"[get_team_agents] Retrieved {len(team_members)} teammates for job {job_id}, "
        f"include_inactive={include_inactive}, tenant={tenant_key}"
    )

    return {
        "success": True,
        "team": team_members,
    }
