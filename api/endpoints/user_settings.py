"""
User Settings endpoints for authenticated, per-user operations.

Implements the MCP AI Tools Configurator under the v3 path
`/api/v1/user/ai-tools-configurator`, relocating logic out of the
deprecated setup flow.
"""

import logging
from typing import Optional

from fastapi import APIRouter, Depends, Header, Query, Request
from fastapi.responses import PlainTextResponse

from src.giljo_mcp.auth.dependencies import get_current_active_user
from src.giljo_mcp.models import User

# Reuse detection and generator helpers from users endpoints
from api.endpoints.users import (
    detect_ai_tool_from_user_agent,
    generate_claude_code_instructions,
    generate_codex_instructions,
    generate_gemini_instructions,
    generate_cursor_instructions,
    generate_continue_instructions,
    generate_universal_instructions,
)


logger = logging.getLogger(__name__)
router = APIRouter()


@router.get("/ai-tools-configurator", response_class=PlainTextResponse)
async def ai_tools_configurator_v1(
    request: Request,
    tool: Optional[str] = Query(
        None,
        description="AI tool type: claude-code, codex, gemini, cursor, continue",
    ),
    user_agent: str = Header(None),
    current_user: User = Depends(get_current_active_user),
) -> str:
    """
    AI Tools Configurator (v3) - generates MCP configuration instructions for AI tools.

    Authenticated endpoint intended to be accessed by logged-in users via
    Avatar → My Settings → API and Integrations.
    """
    logger.info(
        "[UserSettings] %s accessing AI tools configurator (tool=%s)",
        current_user.username,
        tool,
    )

    # Detect server URL from request
    server_url = f"{request.url.scheme}://{request.url.netloc}"

    # Auto-detect AI tool if not explicitly specified
    if not tool:
        tool = detect_ai_tool_from_user_agent(user_agent or "")

    # Generate tool-specific instructions
    if tool == "claude-code":
        return generate_claude_code_instructions(server_url)
    elif tool == "codex":
        return generate_codex_instructions(server_url)
    elif tool == "gemini":
        return generate_gemini_instructions(server_url)
    elif tool == "cursor":
        return generate_cursor_instructions(server_url)
    elif tool == "continue":
        return generate_continue_instructions(server_url)
    else:
        return generate_universal_instructions(server_url, tool)

