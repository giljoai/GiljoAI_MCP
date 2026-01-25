"""
Slash command HTTP endpoints
Allows MCP adapter to route slash commands via HTTP (Handover 0080a)
"""

import logging
from typing import Any, Optional

from fastapi import APIRouter, HTTPException
from pydantic import BaseModel

from src.giljo_mcp.slash_commands import get_slash_command


logger = logging.getLogger(__name__)

router = APIRouter(prefix="/slash", tags=["slash-commands"])


class SlashCommandRequest(BaseModel):
    """Request model for slash command execution"""

    command: str  # e.g., "gil_handover"
    tenant_key: str
    project_id: Optional[str] = None
    arguments: dict[str, Any] = {}


class SlashCommandResponse(BaseModel):
    """Response model for slash command execution"""

    success: bool
    message: str
    launch_prompt: Optional[str] = None  # Continuation prompt for simple handover
    memory_entry_id: Optional[str] = None  # 360 Memory entry ID (simple handover)
    context_reset: Optional[bool] = None  # Whether context was reset (simple handover)
    error: Optional[str] = None
    details: Optional[str] = None


@router.post("/execute", response_model=SlashCommandResponse)
async def execute_slash_command(request: SlashCommandRequest):
    """
    Execute a slash command via HTTP

    Args:
        request: SlashCommandRequest containing command name, tenant, and arguments

    Returns:
        SlashCommandResponse with success status and result data

    Raises:
        HTTPException: 404 if command not found, 500 if execution fails
    """
    handler = get_slash_command(request.command)

    if not handler:
        raise HTTPException(status_code=404, detail=f"Slash command /{request.command} not found")

    try:
        # Import here to avoid circular dependency
        from api.app import state

        # Execute handler with async database session
        async with state.db_manager.get_session_async() as session:
            result = await handler(
                db_session=session,
                tenant_key=request.tenant_key,
                project_id=request.project_id,
                **request.arguments,
            )

        return SlashCommandResponse(**result)

    except Exception as e:
        logger.error(f"Failed to execute slash command /{request.command}: {e}", exc_info=True)
        raise HTTPException(
            status_code=500,
            detail=f"Failed to execute slash command: {e!s}",
        )
