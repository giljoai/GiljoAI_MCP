"""
Universal AI Tool Configuration Endpoint
Provides self-configuration instructions for any AI coding tool

This revolutionary endpoint allows ANY AI coding tool (Claude Code, Codex, Gemini, 
Cursor, Continue.dev, etc.) to visit a URL and receive tailored configuration 
instructions for MCP integration.

Usage:
- User tells AI: "Visit http://server/setup/ai-tools and configure yourself"
- AI agent makes request to endpoint
- Server detects AI tool type and returns specific instructions
- AI agent follows instructions to self-configure
"""

import re
from datetime import datetime
from fastapi import APIRouter, Depends, Header, Query, Request
from fastapi.responses import PlainTextResponse
from typing import Optional

from ..dependencies import get_db
from src.giljo_mcp.config_manager import get_config

router = APIRouter(prefix="/setup", tags=["ai-tools-setup"])


@router.get("/ai-tools", response_class=PlainTextResponse)
async def universal_ai_tool_setup(
    request: Request,
    tool: Optional[str] = Query(None, description="AI tool type: claude-code, codex, gemini, cursor, continue"),
    user_agent: str = Header(None)
):
    """
    Universal AI tool configuration endpoint.
    
    Returns tailored configuration instructions based on the requesting AI tool.
    Can auto-detect tool type from User-Agent or use explicit tool parameter.
    
    This is the magic URL that any AI coding tool can visit to receive
    customized setup instructions for MCP integration.
    """
    
    # Detect server URL
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


def detect_ai_tool_from_user_agent(user_agent: str) -> str:
    """Auto-detect AI tool from User-Agent string"""
    ua_lower = user_agent.lower()
    
    if "claude" in ua_lower:
        return "claude-code"
    elif "codex" in ua_lower:
        return "codex"
    elif "gemini" in ua_lower:
        return "gemini"
    elif "cursor" in ua_lower:
        return "cursor"
    elif "continue" in ua_lower:
        return "continue"
    else:
        return "unknown"


def generate_claude_code_instructions(server_url: str) -> str:
    """Generate Claude Code specific configuration instructions"""
    return f"""# MCP Configuration Instructions for Claude Code

I am a GiljoAI MCP server at {server_url}. You are Claude Code and need to configure an MCP connection to me.

## What You Must Do

1. **Ask the user for their API key** from this GiljoAI server
   - Tell them: "I need your API key from {server_url}"
   - Wait for them to provide it

2. **Add this exact configuration** to ~/.claude.json in the mcpServers section:

```json
"giljo-mcp": {{
  "command": "python",
  "args": ["-m", "giljo_mcp"],
  "env": {{
    "GILJO_SERVER_URL": "{server_url}",
    "GILJO_API_KEY": "[REPLACE_WITH_USER_PROVIDED_KEY]"
  }}
}}
```

3. **Replace [REPLACE_WITH_USER_PROVIDED_KEY]** with the actual API key the user provided

4. **Test the connection** by making a request to: {server_url}/api/status

5. **Tell the user**: "Configuration complete! Please restart Claude Code to activate the MCP connection."

## Server Capabilities
- URL: {server_url}
- Tools: 47+ agent coordination tools
- Features: Multi-agent orchestration, context management, task automation, template system

## Troubleshooting
If the user doesn't have an API key, tell them to:
1. Visit {server_url} in their browser
2. Create an account or log in
3. Generate an API key in Settings
4. Come back with the key
"""


def generate_codex_instructions(server_url: str) -> str:
    """Generate Codex specific configuration instructions"""
    return f"""# MCP Configuration Instructions for Codex

I am a GiljoAI MCP server at {server_url}. You are Codex and need to configure an MCP connection to me.

## What You Must Do

1. **Ask the user for their API key** from this GiljoAI server

2. **Configure MCP connection** using your platform's method:
   - Server URL: {server_url}
   - API Key: [USER_PROVIDED]
   - Tool command: python -m giljo_mcp

3. **Test the connection** by making a request to: {server_url}/api/status

4. **Tell the user** to restart Codex to activate the connection

Note: Adapt these instructions to Codex's specific configuration format.
"""


def generate_gemini_instructions(server_url: str) -> str:
    """Generate Gemini Code Assist specific configuration instructions"""
    return f"""# MCP Configuration Instructions for Gemini Code Assist

I am a GiljoAI MCP server at {server_url}. You are Gemini Code Assist and need to configure an MCP connection to me.

## What You Must Do

1. **Ask the user for their API key** from this GiljoAI server

2. **Configure MCP connection** using your platform's configuration method:
   - Server URL: {server_url}
   - API Key: [USER_PROVIDED]
   - Connection type: HTTP MCP

3. **Test the connection** to verify it works

4. **Tell the user** to restart or reload to activate the connection

Note: Adapt these instructions to Gemini's specific configuration requirements.
"""


def generate_cursor_instructions(server_url: str) -> str:
    """Generate Cursor specific configuration instructions"""
    return f"""# MCP Configuration Instructions for Cursor

I am a GiljoAI MCP server at {server_url}. You are Cursor and need to configure an MCP connection to me.

## What You Must Do

1. **Ask the user for their API key** from this GiljoAI server

2. **Add MCP configuration** to Cursor's settings:
   - Server: {server_url}
   - API Key: [USER_PROVIDED]
   - Command: python -m giljo_mcp

3. **Test the connection**

4. **Tell the user** to restart Cursor

Note: Adapt to Cursor's specific MCP configuration format.
"""


def generate_continue_instructions(server_url: str) -> str:
    """Generate Continue.dev specific configuration instructions"""
    return f"""# MCP Configuration Instructions for Continue.dev

I am a GiljoAI MCP server at {server_url}. You are Continue.dev and need to configure an MCP connection to me.

## What You Must Do

1. **Ask the user for their API key** from this GiljoAI server

2. **Add to Continue configuration**:
   - Server: {server_url}
   - API Key: [USER_PROVIDED]

3. **Test and activate the connection**

Note: Adapt to Continue.dev's specific configuration requirements.
"""


def generate_universal_instructions(server_url: str, tool_type: str = "unknown") -> str:
    """Generate universal instructions for unknown AI tools"""
    return f"""# Universal MCP Configuration Instructions

I am a GiljoAI MCP server at {server_url}. You are an AI coding tool ({tool_type}) that needs to configure an MCP connection to me.

## What You Must Do

1. **Ask the user for their API key** from this GiljoAI server
   - Tell them: "I need your API key from {server_url}"

2. **Configure MCP connection** using your platform's method:
   - Server URL: {server_url}
   - API Key: [USER_PROVIDED]
   - Command: python -m giljo_mcp
   - Environment variables:
     - GILJO_SERVER_URL={server_url}
     - GILJO_API_KEY=[USER_PROVIDED_KEY]

3. **Test the connection** by making a request to: {server_url}/api/status

4. **Tell the user** to restart your AI tool to activate the connection

## Server Details
- URL: {server_url}
- Protocol: HTTP-based MCP
- Tools Available: 47+ agent coordination tools
- Capabilities: Multi-agent orchestration, context management, task automation

## If User Needs API Key
Direct them to:
1. Visit {server_url} in browser
2. Create account or log in  
3. Go to Settings → API Keys
4. Generate new API key
5. Return with the key
"""