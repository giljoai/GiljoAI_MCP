"""
MCP Tool Endpoints for API Server
Provides HTTP endpoints that mirror MCP tool functionality
Allows MCP clients to access tools via HTTP instead of stdio
"""

import logging
from datetime import datetime, timezone
from typing import Any, Optional

from fastapi import APIRouter, HTTPException
from pydantic import BaseModel, Field


logger = logging.getLogger(__name__)

router = APIRouter()


class MCPToolRequest(BaseModel):
    """Generic MCP tool request format"""

    tool: str = Field(..., description="Tool name to execute")
    arguments: dict[str, Any] = Field(default_factory=dict, description="Tool arguments")
    tenant_key: Optional[str] = Field(None, description="Tenant key for multi-tenant isolation")
    project_id: Optional[str] = Field(None, description="Project ID for context")


class MCPToolResponse(BaseModel):
    """Generic MCP tool response format"""

    success: bool
    result: Optional[dict[str, Any]] = None
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
            "list_projects": state.tool_accessor.list_projects,
            "get_project": state.tool_accessor.get_project,
            "close_project": state.tool_accessor.close_project,
            "close_project_and_update_memory": state.tool_accessor.close_project_and_update_memory,
            "update_project_mission": state.tool_accessor.update_project_mission,
            # Message tools
            "send_message": state.tool_accessor.send_message,
            "receive_messages": state.tool_accessor.receive_messages,
            "list_messages": state.tool_accessor.list_messages,
            # Task tools (MCP tools retired Dec 2025 - only create_task kept)
            "create_task": state.tool_accessor.create_task,
            # Template tools
            "list_templates": state.tool_accessor.list_templates,
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

        return MCPToolResponse(success=True, result=result, timestamp=datetime.now(timezone.utc))

    except HTTPException:
        raise
    except Exception as e:
        logger.exception(f"Error executing MCP tool '{request.tool}'")
        return MCPToolResponse(success=False, error=str(e), timestamp=datetime.now(timezone.utc))


@router.get("/list", response_model=dict[str, Any])
async def list_mcp_tools():
    """
    List all available MCP tools with enhanced metadata (Handover 0090 Phase 3)

    Returns rich metadata for all 25 MCP tools including:
    - Enhanced argument descriptions with types and REQUIRED/OPTIONAL markers
    - Usage examples showing 2-3 common patterns
    - Clear array notation in examples
    - Realistic UUID formats
    """
    tools = {
        "project_management": [
            {
                "name": "list_projects",
                "description": "List all projects with optional status filter",
                "arguments": {
                    "status": "string OPTIONAL - Filter by status: 'active', 'completed', 'archived', 'deleted'",
                },
                "examples": [
                    {
                        "description": "List all active projects",
                        "payload": {"status": "active"},
                    },
                    {
                        "description": "List all projects (no filter)",
                        "payload": {},
                    },
                ],
            },
            {
                "name": "get_project",
                "description": "Get detailed information about a specific project",
                "arguments": {
                    "project_id": "string (UUID) REQUIRED - Project ID to retrieve",
                },
                "examples": [
                    {
                        "description": "Get project details",
                        "payload": {"project_id": "proj-abc123-def456"},
                    },
                ],
            },
            {
                "name": "close_project",
                "description": "Close/archive a project and deactivate associated agents",
                "arguments": {
                    "project_id": "string (UUID) REQUIRED - Project ID to close",
                },
                "examples": [
                    {
                        "description": "Close completed project",
                        "payload": {"project_id": "proj-abc123-def456"},
                    },
                ],
            },
            {
                "name": "update_project_mission",
                "description": "Update project's AI-generated mission plan (orchestrator use only)",
                "arguments": {
                    "project_id": "string (UUID) REQUIRED - Project ID to update",
                    "mission": "string REQUIRED - Orchestrator-generated condensed mission plan",
                },
                "examples": [
                    {
                        "description": "Orchestrator updates project mission after analysis",
                        "payload": {
                            "project_id": "proj-abc123-def456",
                            "mission": "Implement JWT auth with RS256, protect 8 endpoints, add rate limiting...",
                        },
                    },
                ],
            },
        ],
        "message_queue": [
            {
                "name": "send_message",
                "description": "Send message to one or more agents (supports broadcast)",
                "arguments": {
                    "to_agents": "array[string] REQUIRED - Recipient agent names: ['orchestrator'] or ['broadcast']",
                    "content": "string REQUIRED - Message content",
                    "project_id": "string (UUID) REQUIRED - Project ID for context",
                    "from_agent": "string OPTIONAL - Sender agent name (defaults to 'orchestrator')",
                    "message_type": "string OPTIONAL - 'direct' or 'broadcast' (default: 'direct')",
                    "priority": "string OPTIONAL - 'normal', 'high', 'critical' (default: 'normal')",
                },
                "examples": [
                    {
                        "description": "Broadcast message to all agents",
                        "payload": {
                            "to_agents": ["broadcast"],
                            "content": "Team update: Feature implementation complete, begin testing phase",
                            "project_id": "proj-abc123-def456",
                            "message_type": "broadcast",
                        },
                    },
                    {
                        "description": "Direct message to orchestrator",
                        "payload": {
                            "to_agents": ["orchestrator"],
                            "content": "Implementation blocked: Need architecture decision on caching strategy",
                            "project_id": "proj-abc123-def456",
                            "from_agent": "backend-implementer",
                            "priority": "high",
                        },
                    },
                    {
                        "description": "Message to multiple specific agents",
                        "payload": {
                            "to_agents": ["backend-tester", "frontend-tester"],
                            "content": "API endpoints ready for integration testing",
                            "project_id": "proj-abc123-def456",
                            "from_agent": "backend-implementer",
                        },
                    },
                ],
            },
            {
                "name": "receive_messages",
                "description": "Retrieve pending messages for an agent",
                "arguments": {
                    "agent_name": "string REQUIRED - Name of agent to get messages for",
                    "project_id": "string (UUID) OPTIONAL - Filter by project (uses current if not specified)",
                },
                "examples": [
                    {
                        "description": "Get messages for specific agent",
                        "payload": {
                            "agent_name": "backend-implementer",
                            "project_id": "proj-abc123-def456",
                        },
                    },
                ],
            },
            {
                "name": "list_messages",
                "description": "List messages with optional filtering",
                "arguments": {
                    "agent_id": "string (UUID) OPTIONAL - Filter by specific agent",
                    "status": "string OPTIONAL - Filter by status: 'pending', 'acknowledged', 'completed'",
                    "limit": "integer OPTIONAL - Maximum messages to retrieve (default: 50)",
                },
                "examples": [
                    {
                        "description": "List all pending messages for agent",
                        "payload": {
                            "agent_id": "agent-abc123-def456",
                            "status": "pending",
                        },
                    },
                    {
                        "description": "List recent messages (all statuses)",
                        "payload": {"limit": 20},
                    },
                ],
            },
        ],
        "task_management": [
            {
                "name": "create_task",
                "description": "Create a new task with product isolation",
                "arguments": {
                    "title": "string REQUIRED - Task title",
                    "description": "string OPTIONAL - Detailed task description",
                    "category": "string OPTIONAL - Task category for organization",
                    "priority": "string OPTIONAL - 'low', 'medium', 'high', 'critical' (default: 'medium')",
                    "tenant_key": "string (UUID) OPTIONAL - Tenant key (uses current if not provided)",
                    "product_id": "string (UUID) OPTIONAL - Product ID for isolation",
                    "project_id": "string (UUID) OPTIONAL - Associate with specific project",
                },
                "examples": [
                    {
                        "description": "Create simple task",
                        "payload": {
                            "title": "Research Redis caching strategies",
                            "priority": "medium",
                        },
                    },
                    {
                        "description": "Create detailed task with project association",
                        "payload": {
                            "title": "Implement user authentication",
                            "description": "Add JWT-based authentication with refresh tokens",
                            "category": "backend",
                            "priority": "high",
                            "project_id": "proj-abc123-def456",
                        },
                    },
                ],
            },
            # list_tasks and update_task removed - Task MCP tools retired Dec 2025
        ],
        "template_management": [
            {
                "name": "list_templates",
                "description": "List available agent templates",
                "arguments": {},
                "examples": [
                    {
                        "description": "List all templates",
                        "payload": {},
                    },
                ],
            },
        ],
        "orchestration": [
            {
                "name": "health_check",
                "description": "Check MCP server health and connectivity",
                "arguments": {},
                "examples": [
                    {
                        "description": "Verify MCP connection",
                        "payload": {},
                    },
                ],
            },
            {
                "name": "get_orchestrator_instructions",
                "description": "Fetch orchestrator mission with context prioritization and orchestration (thin client architecture)",
                "arguments": {
                    "job_id": "string (UUID) REQUIRED - Orchestrator job UUID",
                    "tenant_key": "string (UUID) REQUIRED - Tenant isolation key",
                },
                "examples": [
                    {
                        "description": "Orchestrator fetches condensed mission on startup",
                        "payload": {
                            "job_id": "orch-abc123-def456",
                            "tenant_key": "tk-tenant123-456",
                        },
                    },
                ],
            },
            {
                "name": "spawn_agent_job",
                "description": "Create agent job for multi-agent coordination (orchestrator use)",
                "arguments": {
                    "agent_display_name": "string REQUIRED - Agent role: 'implementer', 'tester', 'reviewer', 'documenter', etc.",
                    "agent_name": "string REQUIRED - User-readable agent name",
                    "mission": "string REQUIRED - Agent-specific mission/tasks",
                    "project_id": "string (UUID) REQUIRED - Project ID",
                    "tenant_key": "string (UUID) REQUIRED - Tenant isolation key",
                },
                "examples": [
                    {
                        "description": "Spawn backend implementer agent",
                        "payload": {
                            "agent_display_name": "implementer",
                            "agent_name": "backend-implementer",
                            "mission": "Implement JWT authentication endpoints with RS256 signing",
                            "project_id": "proj-abc123-def456",
                            "tenant_key": "tk-tenant123-456",
                        },
                    },
                    {
                        "description": "Spawn tester agent",
                        "payload": {
                            "agent_display_name": "tester",
                            "agent_name": "backend-tester",
                            "mission": "Write comprehensive tests for authentication system",
                            "project_id": "proj-abc123-def456",
                            "tenant_key": "tk-tenant123-456",
                        },
                    },
                ],
            },
            {
                "name": "get_agent_mission",
                "description": "Fetch agent-specific mission from storage (thin client architecture)",
                "arguments": {
                    "job_id": "string (UUID) REQUIRED - Agent job UUID (Handover 0381: renamed from agent_job_id)",
                    "tenant_key": "string (UUID) REQUIRED - Tenant isolation key",
                },
                "examples": [
                    {
                        "description": "Agent retrieves its mission on startup",
                        "payload": {
                            "job_id": "job-abc123-def456",
                            "tenant_key": "tk-tenant123-456",
                        },
                    },
                ],
            },
            {
                "name": "orchestrate_project",
                "description": "Execute complete project orchestration workflow (context prioritization and orchestration)",
                "arguments": {
                    "project_id": "string (UUID) REQUIRED - Project UUID",
                    "tenant_key": "string (UUID) REQUIRED - Tenant isolation key",
                },
                "examples": [
                    {
                        "description": "Start full orchestration for project",
                        "payload": {
                            "project_id": "proj-abc123-def456",
                            "tenant_key": "tk-tenant123-456",
                        },
                    },
                ],
            },
            {
                "name": "get_workflow_status",
                "description": "Get status of all agents in project workflow",
                "arguments": {
                    "project_id": "string (UUID) REQUIRED - Project UUID",
                    "tenant_key": "string (UUID) REQUIRED - Tenant isolation key",
                },
                "examples": [
                    {
                        "description": "Check project workflow status",
                        "payload": {
                            "project_id": "proj-abc123-def456",
                            "tenant_key": "tk-tenant123-456",
                        },
                    },
                ],
            },
        ],
        "agent_coordination": [
            {
                "name": "get_pending_jobs",
                "description": "Get jobs waiting for agent of this type (agent polling)",
                "arguments": {
                    "agent_display_name": "string REQUIRED - Agent type/role to query for",
                    "tenant_key": "string (UUID) REQUIRED - Tenant isolation key",
                },
                "examples": [
                    {
                        "description": "Backend implementer checks for pending jobs",
                        "payload": {
                            "agent_display_name": "implementer",
                            "tenant_key": "tk-tenant123-456",
                        },
                    },
                    {
                        "description": "Tester checks for pending work",
                        "payload": {
                            "agent_display_name": "tester",
                            "tenant_key": "tk-tenant123-456",
                        },
                    },
                ],
            },
            {
                "name": "acknowledge_job",
                "description": "Claim job and transition to active status (pending -> active)",
                "arguments": {
                    "job_id": "string (UUID) REQUIRED - Job UUID to acknowledge",
                    "agent_id": "string REQUIRED - Agent identifier claiming the job",
                },
                "examples": [
                    {
                        "description": "Agent claims pending job",
                        "payload": {
                            "job_id": "job-abc123-def456",
                            "agent_id": "backend-implementer",
                        },
                    },
                ],
            },
            {
                "name": "report_progress",
                "description": "Report incremental progress on active job",
                "arguments": {
                    "job_id": "string (UUID) REQUIRED - Job UUID being worked on",
                    "progress": "object REQUIRED - Progress details with percentage and status updates",
                },
                "examples": [
                    {
                        "description": "Report 50% completion",
                        "payload": {
                            "job_id": "job-abc123-def456",
                            "progress": {
                                "percentage": 50,
                                "status": "Completed authentication endpoints, starting tests",
                                "files_modified": 8,
                            },
                        },
                    },
                    {
                        "description": "Report task milestone completion",
                        "payload": {
                            "job_id": "job-abc123-def456",
                            "progress": {
                                "percentage": 75,
                                "status": "Tests passing, documentation in progress",
                                "tests_passed": 45,
                                "tests_total": 50,
                            },
                        },
                    },
                ],
            },
            {
                "name": "complete_job",
                "description": "Mark job as completed with results",
                "arguments": {
                    "job_id": "string (UUID) REQUIRED - Job UUID to complete",
                    "result": "object REQUIRED - Completion result with deliverables and summary",
                },
                "examples": [
                    {
                        "description": "Complete implementation job",
                        "payload": {
                            "job_id": "job-abc123-def456",
                            "result": {
                                "status": "completed",
                                "summary": "JWT authentication implemented with 100% test coverage",
                                "files_created": 12,
                                "files_modified": 3,
                                "tests_added": 45,
                            },
                        },
                    },
                ],
            },
            {
                "name": "report_error",
                "description": "Report job error and pause for orchestrator review",
                "arguments": {
                    "job_id": "string (UUID) REQUIRED - Job UUID encountering error",
                    "error": "string REQUIRED - Error message and context",
                },
                "examples": [
                    {
                        "description": "Report blocking error",
                        "payload": {
                            "job_id": "job-abc123-def456",
                            "error": "Missing dependency: crypto library not installed. Need orchestrator decision on version.",
                        },
                    },
                    {
                        "description": "Report architectural blocker",
                        "payload": {
                            "job_id": "job-abc123-def456",
                            "error": "Test failures: 15/45 tests failing. Root cause: database schema mismatch requires migration.",
                        },
                    },
                ],
            },
        ],
    }

    return {
        "tools": tools,
        "total_count": sum(len(category) for category in tools.values()),
        "categories": list(tools.keys()),
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
        "tool_accessor": "ready" if state.tool_accessor else "not initialized",
    }
