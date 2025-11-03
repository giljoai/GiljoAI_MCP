"""
MCP Tool Endpoints for API Server
Provides HTTP endpoints that mirror MCP tool functionality
Allows MCP clients to access tools via HTTP instead of stdio
"""

import logging
from typing import Any, Dict, Optional
from datetime import datetime, timezone
from uuid import uuid4

from fastapi import APIRouter, HTTPException, Depends
from pydantic import BaseModel, Field

logger = logging.getLogger(__name__)

router = APIRouter()


class MCPToolRequest(BaseModel):
    """Generic MCP tool request format"""
    tool: str = Field(..., description="Tool name to execute")
    arguments: Dict[str, Any] = Field(default_factory=dict, description="Tool arguments")
    tenant_key: Optional[str] = Field(None, description="Tenant key for multi-tenant isolation")
    project_id: Optional[str] = Field(None, description="Project ID for context")


class MCPToolResponse(BaseModel):
    """Generic MCP tool response format"""
    success: bool
    result: Optional[Dict[str, Any]] = None
    error: Optional[str] = None
    timestamp: datetime = Field(default_factory=lambda: datetime.now(timezone.utc))


@router.post("/execute", response_model=MCPToolResponse)
async def execute_mcp_tool(request: MCPToolRequest):
    """
    Execute an MCP tool via HTTP
    This endpoint routes tool requests to the appropriate handler
    """
    from api.app import state

    if not state.db_manager:
        raise HTTPException(status_code=503, detail="Database not available")

    if not state.tool_accessor:
        raise HTTPException(status_code=503, detail="Tool accessor not initialized")

    try:
        tool_name = request.tool
        args = request.arguments

        # Set tenant context if provided
        if request.tenant_key:
            state.tenant_manager.set_current_tenant(request.tenant_key)

        # Route to appropriate tool function
        tool_map = {
            # Project tools
            "create_project": state.tool_accessor.create_project,
            "list_projects": state.tool_accessor.list_projects,
            "get_project": state.tool_accessor.get_project,
            "switch_project": state.tool_accessor.switch_project,
            "close_project": state.tool_accessor.close_project,

            # Agent tools
            "spawn_agent": state.tool_accessor.spawn_agent,
            "list_agents": state.tool_accessor.list_agents,
            "get_agent_status": state.tool_accessor.get_agent_status,
            "update_agent": state.tool_accessor.update_agent,
            "retire_agent": state.tool_accessor.retire_agent,

            # Message tools
            "send_message": state.tool_accessor.send_message,
            "receive_messages": state.tool_accessor.receive_messages,
            "acknowledge_message": state.tool_accessor.acknowledge_message,
            "list_messages": state.tool_accessor.list_messages,

            # Task tools
            "create_task": state.tool_accessor.create_task,
            "list_tasks": state.tool_accessor.list_tasks,
            "update_task": state.tool_accessor.update_task,
            "assign_task": state.tool_accessor.assign_task,
            "complete_task": state.tool_accessor.complete_task,

            # Template tools
            "list_templates": state.tool_accessor.list_templates,
            "get_template": state.tool_accessor.get_template,
            "create_template": state.tool_accessor.create_template,
            "update_template": state.tool_accessor.update_template,

            # Context tools
            "discover_context": state.tool_accessor.discover_context,
            "get_file_context": state.tool_accessor.get_file_context,
            "search_context": state.tool_accessor.search_context,
            "get_context_summary": state.tool_accessor.get_context_summary,

            # Orchestration tools
            "health_check": state.tool_accessor.health_check,
            "get_orchestrator_instructions": state.tool_accessor.get_orchestrator_instructions,
            "spawn_agent_job": state.tool_accessor.spawn_agent_job,
            "get_agent_mission": state.tool_accessor.get_agent_mission,
            "orchestrate_project": state.tool_accessor.orchestrate_project,
            "get_workflow_status": state.tool_accessor.get_workflow_status,

            # Agent coordination tools
            "get_pending_jobs": state.tool_accessor.get_pending_jobs,
            "acknowledge_job": state.tool_accessor.acknowledge_job,
            "report_progress": state.tool_accessor.report_progress,
            "complete_job": state.tool_accessor.complete_job,
            "report_error": state.tool_accessor.report_error,
        }

        if tool_name not in tool_map:
            raise HTTPException(status_code=404, detail=f"Tool '{tool_name}' not found")

        # Execute the tool
        tool_func = tool_map[tool_name]
        result = await tool_func(**args)

        return MCPToolResponse(
            success=True,
            result=result,
            timestamp=datetime.now(timezone.utc)
        )

    except HTTPException:
        raise
    except Exception as e:
        logger.exception(f"Error executing MCP tool '{request.tool}': {e}")
        return MCPToolResponse(
            success=False,
            error=str(e),
            timestamp=datetime.now(timezone.utc)
        )


@router.get("/list", response_model=Dict[str, Any])
async def list_mcp_tools():
    """List all available MCP tools with their descriptions"""
    tools = {
        "project_management": [
            {
                "name": "create_project",
                "description": "Create a new project with mission and optional agent sequence",
                "arguments": {
                    "name": "Project name",
                    "mission": "Project mission statement",
                    "agents": "Optional list of agent names to initialize"
                }
            },
            {
                "name": "list_projects",
                "description": "List all projects with optional status filter",
                "arguments": {
                    "status": "Optional status filter (active, completed, archived)"
                }
            },
            {
                "name": "switch_project",
                "description": "Switch to a different project context",
                "arguments": {
                    "project_id": "Project ID to switch to"
                }
            },
            {
                "name": "close_project",
                "description": "Close/archive a project",
                "arguments": {
                    "project_id": "Project ID to close"
                }
            }
        ],
        "agent_orchestration": [
            {
                "name": "spawn_agent",
                "description": "Spawn a new agent in the current project",
                "arguments": {
                    "name": "Agent name",
                    "role": "Agent role/specialty",
                    "mission": "Agent-specific mission"
                }
            },
            {
                "name": "list_agents",
                "description": "List all agents in the current project",
                "arguments": {
                    "status": "Optional status filter"
                }
            },
            {
                "name": "retire_agent",
                "description": "Retire an agent from the project",
                "arguments": {
                    "agent_id": "Agent ID to retire"
                }
            }
        ],
        "message_queue": [
            {
                "name": "send_message",
                "description": "Send a message through the message queue",
                "arguments": {
                    "from_agent": "Sender agent ID",
                    "to_agent": "Recipient agent ID (optional)",
                    "content": "Message content",
                    "message_type": "Type of message"
                }
            },
            {
                "name": "receive_messages",
                "description": "Receive pending messages for an agent",
                "arguments": {
                    "agent_id": "Agent ID to receive messages for",
                    "limit": "Maximum number of messages to receive"
                }
            }
        ],
        "task_management": [
            {
                "name": "create_task",
                "description": "Create a new task",
                "arguments": {
                    "title": "Task title",
                    "description": "Task description",
                    "priority": "Task priority (low, medium, high)",
                    "assigned_to": "Optional agent ID to assign to"
                }
            },
            {
                "name": "list_tasks",
                "description": "List tasks with filters",
                "arguments": {
                    "status": "Optional status filter",
                    "assigned_to": "Optional agent ID filter"
                }
            }
        ],
        "context_discovery": [
            {
                "name": "discover_context",
                "description": "Discover project context and structure",
                "arguments": {
                    "path": "Optional path to analyze"
                }
            },
            {
                "name": "search_context",
                "description": "Search project context",
                "arguments": {
                    "query": "Search query",
                    "file_types": "Optional list of file extensions to search"
                }
            }
        ],
        "template_management": [
            {
                "name": "list_templates",
                "description": "List available templates",
                "arguments": {}
            },
            {
                "name": "get_template",
                "description": "Get a specific template",
                "arguments": {
                    "template_name": "Name of the template"
                }
            }
        ]
    }

    return {
        "tools": tools,
        "total_count": sum(len(category) for category in tools.values()),
        "categories": list(tools.keys())
    }


@router.get("/health")
async def mcp_health_check():
    """MCP-specific health check endpoint"""
    from api.app import state

    return {
        "status": "healthy",
        "server": "GiljoAI MCP API",
        "version": "2.0.0",
        "mode": "HTTP",
        "database": "connected" if state.db_manager else "disconnected",
        "tool_accessor": "ready" if state.tool_accessor else "not initialized"
    }
