"""
AI Tools Configuration Generator API Endpoints

Provides elegant copy-paste configuration system for connecting AI tools
(Claude Code, CODEX, Gemini) to GiljoAI MCP server.
"""

import json
import logging
from pathlib import Path
from typing import List, Optional

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
    instructions: List[str] = Field(..., description="Step-by-step setup instructions")
    download_filename: str = Field(..., description="Filename for markdown guide download")


class SupportedToolsResponse(BaseModel):
    """Response listing all supported AI tools."""
    tools: List[AIToolInfo]


# Configuration Templates

def get_claude_code_config(server_url: str, tenant_key: str) -> dict:
    """
    Generate Claude Code MCP configuration.

    Args:
        server_url: GiljoAI server URL
        tenant_key: User's tenant key

    Returns:
        Configuration dictionary
    """
    return {
        "mcpServers": {
            "giljo-mcp": {
                "command": "python",
                "args": ["-m", "giljo_mcp.mcp_server"],
                "env": {
                    "GILJO_SERVER_URL": server_url,
                    "GILJO_TENANT_KEY": tenant_key
                }
            }
        }
    }


def get_codex_config(server_url: str, tenant_key: str) -> dict:
    """
    Generate CODEX configuration.

    Args:
        server_url: GiljoAI server URL
        tenant_key: User's tenant key

    Returns:
        Configuration dictionary
    """
    # CODEX uses similar MCP server configuration
    return {
        "mcp": {
            "servers": {
                "giljo-mcp": {
                    "command": "python",
                    "args": ["-m", "giljo_mcp.mcp_server"],
                    "environment": {
                        "GILJO_SERVER_URL": server_url,
                        "GILJO_TENANT_KEY": tenant_key
                    }
                }
            }
        }
    }


def get_gemini_config(server_url: str, tenant_key: str) -> dict:
    """
    Generate Gemini configuration.

    Args:
        server_url: GiljoAI server URL
        tenant_key: User's tenant key

    Returns:
        Configuration dictionary
    """
    # Gemini uses JSON configuration
    return {
        "tools": {
            "giljo-mcp": {
                "type": "mcp_server",
                "command": "python",
                "args": ["-m", "giljo_mcp.mcp_server"],
                "env": {
                    "GILJO_SERVER_URL": server_url,
                    "GILJO_TENANT_KEY": tenant_key
                }
            }
        }
    }


def get_tool_instructions(tool_id: str, file_location: str) -> List[str]:
    """
    Get setup instructions for a specific tool.

    Args:
        tool_id: Tool identifier
        file_location: Config file location

    Returns:
        List of instruction steps
    """
    common_restart = {
        "claude": "Restart Claude Code CLI",
        "codex": "Restart CODEX",
        "gemini": "Restart Gemini CLI"
    }

    return [
        f"1. Open or create the file: {file_location}",
        "2. Copy the configuration below",
        f"3. Paste it into {file_location} (merge with existing config if needed)",
        "4. Save the file",
        f"5. {common_restart.get(tool_id, 'Restart your AI tool')}",
        "6. Test the connection by asking your AI tool to use GiljoAI MCP"
    ]


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
            config_format="json",
            file_location="~/.claude.json",
            supported=True
        ),
        AIToolInfo(
            id="codex",
            name="OpenAI CODEX",
            config_format="json",
            file_location="~/.codex/config.json",
            supported=True
        ),
        AIToolInfo(
            id="gemini",
            name="Google Gemini",
            config_format="json",
            file_location="~/.gemini/config.json",
            supported=True
        )
    ]

    return SupportedToolsResponse(tools=tools)


@router.get("/config-generator/{tool_name}", response_model=AIToolConfigResponse, tags=["ai-tools"])
async def generate_ai_tool_config(
    tool_name: str,
    current_user: Optional[User] = Depends(get_current_active_user),
    db: AsyncSession = Depends(get_db_session)
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
    host = getattr(config.services, 'external_host', None) or config.services.api.host
    port = config.services.api.port

    # Use http (wss for production with SSL)
    protocol = "https" if getattr(config.features, 'ssl_enabled', False) else "http"
    server_url = f"{protocol}://{host}:{port}"

    logger.info(f"Generating config for tool '{tool_id}' with server URL: {server_url}")

    # Get tenant key (use default if no user authenticated)
    tenant_key = current_user.tenant_key if current_user else "default"

    # Generate configuration based on tool
    config_generators = {
        "claude": {
            "generator": get_claude_code_config,
            "format": "json",
            "file_location": "~/.claude.json",
            "filename": "giljo-claude-setup.md"
        },
        "codex": {
            "generator": get_codex_config,
            "format": "json",
            "file_location": "~/.codex/config.json",
            "filename": "giljo-codex-setup.md"
        },
        "gemini": {
            "generator": get_gemini_config,
            "format": "json",
            "file_location": "~/.gemini/config.json",
            "filename": "giljo-gemini-setup.md"
        }
    }

    if tool_id not in config_generators:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"Tool '{tool_name}' is not supported. Supported tools: {', '.join(config_generators.keys())}"
        )

    tool_config = config_generators[tool_id]

    # Generate configuration
    config_dict = tool_config["generator"](server_url, tenant_key)

    # Convert to formatted string
    if tool_config["format"] == "json":
        config_content = json.dumps(config_dict, indent=2, ensure_ascii=False)
    else:
        # YAML format (future enhancement)
        import yaml
        config_content = yaml.dump(config_dict, default_flow_style=False)

    # Get instructions
    instructions = get_tool_instructions(tool_id, tool_config["file_location"])

    logger.info(f"Successfully generated config for {tool_id} (tenant: {tenant_key})")

    return AIToolConfigResponse(
        tool=tool_id,
        config_format=tool_config["format"],
        config_content=config_content,
        file_location=tool_config["file_location"],
        instructions=instructions,
        download_filename=tool_config["filename"]
    )


@router.get("/config-generator/{tool_name}/markdown", tags=["ai-tools"])
async def download_setup_guide(
    tool_name: str,
    current_user: Optional[User] = Depends(get_current_active_user),
    db: AsyncSession = Depends(get_db_session)
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
    tool_display_name = {
        "claude": "Claude Code",
        "codex": "OpenAI CODEX",
        "gemini": "Google Gemini"
    }.get(config_response.tool, config_response.tool.title())

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

    markdown += instructions_text + """


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

    return PlainTextResponse(
        content=markdown,
        media_type="text/markdown",
        headers={
            "Content-Disposition": f"attachment; filename={config_response.download_filename}"
        }
    )
