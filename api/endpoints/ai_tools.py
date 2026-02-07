"""
AI Tools Configuration Generator API Endpoints

Provides elegant copy-paste configuration system for connecting AI tools
(Claude Code, CODEX, Gemini) to GiljoAI MCP server.
"""

import logging

from fastapi import APIRouter, Depends, HTTPException, status
from pydantic import BaseModel, Field
from sqlalchemy.ext.asyncio import AsyncSession

from src.giljo_mcp.auth.dependencies import get_current_active_user, get_db_session
from src.giljo_mcp.config_manager import get_config
from src.giljo_mcp.models import User

logger = logging.getLogger(__name__)
router = APIRouter()

# Pydantic Models

class AIToolInfo(BaseModel):
    """Information about a supported AI tool."""

    id: str = Field(..., description="Tool identifier (e.g., 'claude', 'codex')")
    name: str = Field(..., description="Display name")
    config_format: str = Field(..., description="Configuration format (json/yaml)")
    file_location: str = Field(..., description="Default config file location")
    supported: bool = Field(default=True, description="Whether tool is currently supported")

class AIToolConfigResponse(BaseModel):
    """Response containing AI tool configuration."""

    tool: str = Field(..., description="Tool identifier")
    config_format: str = Field(..., description="Configuration format (json/yaml)")
    config_content: str = Field(..., description="Configuration content as string")
    file_location: str = Field(..., description="Where to save the config file")
    instructions: list[str] = Field(..., description="Step-by-step setup instructions")
    download_filename: str = Field(..., description="Filename for markdown guide download")

class SupportedToolsResponse(BaseModel):
    """Response listing all supported AI tools."""

    tools: list[AIToolInfo]

# Configuration Templates

def get_claude_code_config(server_url: str, api_key: str) -> str:
    """
    Generate Claude Code MCP HTTP transport command.

    Args:
        server_url: GiljoAI server URL
        api_key: User's API key

    Returns:
        Command string for HTTP transport
    """
    return f"""claude mcp add --transport http giljo-mcp {server_url}/mcp \\
  --header "X-API-Key: {api_key}" """

def get_codex_config(server_url: str, api_key: str) -> str:
    """
    Generate Codex CLI MCP HTTP transport command.

    Uses bearer token env var, because Codex URL transport does not
    support arbitrary headers like X-API-Key.

    Args:
        server_url: GiljoAI server URL
        api_key: User's API key

    Returns:
        Command string(s) for HTTP transport (export + add)
    """
    return (
        f'export GILJO_API_KEY="{api_key}"\n'
        f"codex mcp add --url {server_url}/mcp --bearer-token-env-var GILJO_API_KEY giljo-mcp"
    )

def get_gemini_config(server_url: str, api_key: str) -> str:
    """
    Generate Gemini CLI MCP HTTP transport command.

    Gemini CLI supports custom headers directly; pass X-API-Key and set
    transport to HTTP. Order is: <name> <url>.

    Args:
        server_url: GiljoAI server URL
        api_key: User's API key

    Returns:
        Command string for HTTP transport (single line)
    """
    return f'gemini mcp add -t http -H "X-API-Key: {api_key}" giljo-mcp {server_url}/mcp'

def get_http_tool_instructions(tool_id: str) -> list[str]:
    """
    Get HTTP transport setup instructions for a specific tool.

    Args:
        tool_id: Tool identifier

    Returns:
        List of instruction steps
    """
    if tool_id == "claude":
        return [
            "Open your terminal or command prompt",
            "Copy the command shown above",
            "Paste and run the command to configure Claude Code",
            "Verify connection with: claude mcp list",
            "Start using GiljoAI tools in Claude Code conversations",
        ]
    if tool_id == "codex":
        return [
            "Open your terminal or command prompt",
            "Export your API key as GILJO_API_KEY (see command above)",
            "Run the codex mcp add command shown above",
            "Verify connection with: codex mcp list",
            "Start using GiljoAI tools in Codex sessions",
        ]
    if tool_id == "gemini":
        return [
            "Open your terminal or command prompt",
            "Run the gemini mcp add command shown above (note: order is <name> <url>)",
            "Verify connection with: gemini mcp list",
            "Start using GiljoAI tools in Gemini sessions",
        ]
    return ["Copy the command above", "Run it in your terminal", "Verify the connection", "Start using GiljoAI tools"]

# API Endpoints

@router.get("/supported", response_model=SupportedToolsResponse, tags=["ai-tools"])
async def list_supported_tools():
    """
    List all supported AI tools with their configuration details.

    Returns information about each AI tool that can connect to GiljoAI MCP,
    including configuration format and file locations.
    """
    tools = [
        AIToolInfo(
            id="claude",
            name="Claude Code",
            config_format="command",
            file_location="Terminal/PowerShell",
            supported=True,
        ),
        AIToolInfo(
            id="codex", name="Codex CLI", config_format="command", file_location="Terminal/PowerShell", supported=True
        ),
        AIToolInfo(
            id="gemini", name="Gemini CLI", config_format="command", file_location="Terminal/PowerShell", supported=True
        ),
    ]

    return SupportedToolsResponse(tools=tools)

@router.get("/config-generator/{tool_name}", response_model=AIToolConfigResponse, tags=["ai-tools"])
async def generate_ai_tool_config(
    tool_name: str,
    current_user: User | None = Depends(get_current_active_user),
    db: AsyncSession = Depends(get_db_session),
):
    """
    Generate configuration for a specific AI tool.

    Creates a personalized configuration that includes:
    - Server URL (automatically detected from current deployment)
    - User's tenant key (for multi-tenant isolation)
    - Tool-specific format and settings

    Args:
        tool_name: AI tool identifier (claude, codex, gemini)
        current_user: Authenticated user (optional for public access)
        db: Database session

    Returns:
        Configuration content, instructions, and metadata

    Raises:
        HTTPException: 404 if tool is not supported
    """
    # Normalize tool name
    tool_id = tool_name.lower().strip()

    # Get server configuration
    config = get_config()

    # Build server URL from configuration
    # Use external_host if configured, otherwise use api.host
    host = getattr(config.services, "external_host", None) or config.services.api.host
    port = config.services.api.port

    # Use http (wss for production with SSL)
    protocol = "https" if getattr(config.features, "ssl_enabled", False) else "http"
    server_url = f"{protocol}://{host}:{port}"

    logger.info(f"Generating config for tool '{tool_id}' with server URL: {server_url}")

    # Note: This endpoint should create an API key and use HTTP transport
    # For now, using a placeholder API key - should be integrated with API key creation
    api_key = "placeholder-api-key-please-use-wizard"

    # Generate configuration based on tool
    config_generators = {
        "claude": {
            "generator": get_claude_code_config,
            "format": "command",
            "file_location": "Terminal/PowerShell",
            "filename": "giljo-claude-setup.md",
        },
        "codex": {
            "generator": get_codex_config,
            "format": "command",
            "file_location": "Terminal/PowerShell",
            "filename": "giljo-codex-setup.md",
        },
        "gemini": {
            "generator": get_gemini_config,
            "format": "command",
            "file_location": "Terminal/PowerShell",
            "filename": "giljo-gemini-setup.md",
        },
    }

    if tool_id not in config_generators:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"Tool '{tool_name}' is not supported. Supported tools: {', '.join(config_generators.keys())}",
        )

    tool_config = config_generators[tool_id]

    # Generate configuration command
    config_content = tool_config["generator"](server_url, api_key)

    # Get instructions for HTTP transport
    instructions = get_http_tool_instructions(tool_id)

    logger.info(f"Successfully generated config for {tool_id} (HTTP transport)")

    return AIToolConfigResponse(
        tool=tool_id,
        config_format=tool_config["format"],
        config_content=config_content,
        file_location=tool_config["file_location"],
        instructions=instructions,
        download_filename=tool_config["filename"],
    )

@router.get("/config-generator/{tool_name}/markdown", tags=["ai-tools"])
async def download_setup_guide(
    tool_name: str,
    current_user: User | None = Depends(get_current_active_user),
    db: AsyncSession = Depends(get_db_session),
):
    """
    Download complete setup guide as markdown file.

    Creates a comprehensive markdown guide including:
    - Configuration content
    - Step-by-step instructions
    - Troubleshooting tips
    - Testing instructions

    Args:
        tool_name: AI tool identifier
        current_user: Authenticated user (optional)
        db: Database session

    Returns:
        Markdown content for download
    """
    from fastapi.responses import PlainTextResponse

    # Get configuration
    config_response = await generate_ai_tool_config(tool_name, current_user, db)

    # Build markdown guide
    tool_display_name = {"claude": "Claude Code", "codex": "OpenAI CODEX", "gemini": "Google Gemini"}.get(
        config_response.tool, config_response.tool.title()
    )

    markdown = f"""# GiljoAI MCP Setup Guide for {tool_display_name}

## Overview

This guide will help you connect {tool_display_name} to your GiljoAI MCP server.

## Prerequisites

- {tool_display_name} installed and working
- Access to GiljoAI MCP server
- Python 3.11+ installed

## Configuration

### Step 1: Locate Configuration File

Open or create the following file:

```
{config_response.file_location}
```

### Step 2: Add Configuration

Copy the configuration below and paste it into your config file:

```{config_response.config_format}
{config_response.config_content}
```

**Important Notes:**
- If the file already exists, merge this configuration with your existing config
- For JSON files, ensure proper comma placement between entries
- Preserve existing configurations for other tools

### Step 3: Installation Instructions

"""

    # Build instructions list
    instructions_text = "\n".join(
        f"{i}. {instruction.split('. ', 1)[1] if '. ' in instruction else instruction}"
        for i, instruction in enumerate(config_response.instructions, 1)
    )

    markdown += (
        instructions_text
        + """

## Testing the Connection

After completing setup:

1. Open {tool_display_name}
2. Try asking: "Can you access GiljoAI MCP tools?"
3. Or run: `/mcp list` (if supported by your tool)

You should see GiljoAI MCP tools in the available tools list.

## Troubleshooting

### Connection Failed

If you see connection errors:

1. **Verify Server URL**: Ensure the GiljoAI server is running and accessible
2. **Check Network**: Confirm you can reach the server from your machine
3. **Review Logs**: Check {tool_display_name} logs for specific error messages

### Configuration Not Loading

If configuration doesn't load:

1. **Validate JSON**: Use a JSON validator to check syntax
2. **Check File Location**: Ensure file is in the correct location
3. **File Permissions**: Verify you have read permissions on the config file

### Authentication Issues

If you see authentication errors:

1. **Tenant Key**: Verify your tenant key is correct
2. **Server Access**: Confirm the server is accepting connections
3. **Network Firewall**: Check if firewall rules allow the connection

## Support

For additional help:
- Check GiljoAI MCP documentation
- Visit the project repository
- Contact your system administrator

---

Generated by GiljoAI MCP Configuration Generator
"""
    )

    return PlainTextResponse(
        content=markdown,
        media_type="text/markdown",
        headers={"Content-Disposition": f"attachment; filename={config_response.download_filename}"},
    )
