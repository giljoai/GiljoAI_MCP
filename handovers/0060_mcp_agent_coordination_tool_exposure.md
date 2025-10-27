---
Handover 0060: MCP Agent Coordination Tool Exposure
Date: 2025-10-27
Status: Ready for Implementation
Priority: CRITICAL
Complexity: LOW
Duration: 4-6 hours
---

# Executive Summary

The GiljoAI MCP Server's existing agent coordination infrastructure (AgentJobManager, AgentCommunicationQueue, JobCoordinator) is currently only accessible via internal Python APIs. This handover exposes 7 core coordination functions as MCP tools through a new HTTP endpoint, enabling Claude Code, Codex, and Gemini CLI to directly interact with the agent orchestration system.

**Key Principle**: External AI agents (Claude Code, Codex, Gemini) must be able to coordinate work, assign tasks, and communicate through the same infrastructure used by internal agents.

The system will expose tools for creating jobs, sending messages, checking status, acknowledging work, and completing/failing jobs - all with proper tenant isolation and authentication.

---

# Problem Statement

## Current State

The agent coordination infrastructure exists but is Python-only:
- `src/giljo_mcp/agent_job_manager.py` - Job lifecycle management
- `src/giljo_mcp/agent_communication_queue.py` - Inter-agent messaging
- `src/giljo_mcp/job_coordinator.py` - Multi-agent orchestration
- 13 REST API endpoints in `api/endpoints/agent_jobs.py`
- WebSocket events for real-time updates

## Gaps Without This Implementation

1. **No MCP Integration**: External agents can't use the agent coordination system
2. **Manual Coordination**: Users must manually assign work to external agents
3. **Broken Workflows**: Multi-agent workflows can't include external tools
4. **Context Loss**: External agents don't know what other agents are working on
5. **Duplicate Work**: No way to check if another agent is already handling a task

---

# Implementation Plan

## Overview

This implementation adds a single new MCP tools module that wraps existing API endpoints. No changes to core coordination logic - pure exposure layer.

**Total Estimated Lines of Code**: ~250 lines (1 new file)

## Phase 1: Create MCP Tools Module (2-3 hours)

**File**: `src/giljo_mcp/tools/agent_coordination.py` (NEW)

**Tools to Expose**:

1. **create_agent_job**
   - Parameters: agent_id, mission, product_id, priority, metadata
   - Returns: job_id, status, created_at
   - Wraps: POST /api/v1/agent-jobs

2. **send_agent_message**
   - Parameters: from_agent_id, to_agent_id, message_type, content
   - Returns: message_id, timestamp
   - Wraps: POST /api/v1/agent-jobs/messages

3. **get_agent_job_status**
   - Parameters: job_id
   - Returns: status, progress, current_step, metadata
   - Wraps: GET /api/v1/agent-jobs/{job_id}

4. **acknowledge_agent_job**
   - Parameters: job_id, agent_id, acknowledgment_message
   - Returns: success, acknowledged_at
   - Wraps: POST /api/v1/agent-jobs/{job_id}/acknowledge

5. **complete_agent_job**
   - Parameters: job_id, agent_id, result_data, artifacts
   - Returns: success, completed_at, result_summary
   - Wraps: POST /api/v1/agent-jobs/{job_id}/complete

6. **fail_agent_job**
   - Parameters: job_id, agent_id, error_message, error_details
   - Returns: success, failed_at
   - Wraps: POST /api/v1/agent-jobs/{job_id}/fail

7. **list_active_agent_jobs**
   - Parameters: product_id (optional), agent_id (optional)
   - Returns: jobs array with status, progress, assigned agents
   - Wraps: GET /api/v1/agent-jobs

**Implementation Template**:

```python
"""
Agent Coordination MCP Tools

Exposes agent job management and coordination capabilities to external MCP clients
(Claude Code, Codex, Gemini CLI). Wraps existing REST API endpoints with MCP tool interface.
"""

from typing import Any, Dict, List, Optional
from datetime import datetime
import aiohttp
from ..config import config_manager
from ..auth import get_mcp_auth_token


class AgentCoordinationTools:
    """MCP tools for agent job coordination and communication."""

    def __init__(self, base_url: str = None):
        self.base_url = base_url or config_manager.get('api', {}).get('base_url', 'http://localhost:7272')
        self.session = None

    async def _get_session(self) -> aiohttp.ClientSession:
        """Get or create aiohttp session."""
        if not self.session:
            self.session = aiohttp.ClientSession()
        return self.session

    async def _api_request(
        self,
        method: str,
        endpoint: str,
        data: Dict = None,
        params: Dict = None
    ) -> Dict:
        """Make authenticated API request."""
        session = await self._get_session()
        headers = {
            'Authorization': f'Bearer {await get_mcp_auth_token()}',
            'Content-Type': 'application/json'
        }

        url = f"{self.base_url}/api/v1{endpoint}"

        async with session.request(method, url, json=data, params=params, headers=headers) as response:
            if response.status >= 400:
                error_data = await response.json()
                raise Exception(f"API Error {response.status}: {error_data.get('detail', 'Unknown error')}")
            return await response.json()

    async def create_agent_job(
        self,
        agent_id: str,
        mission: str,
        product_id: str,
        priority: int = 5,
        metadata: Dict = None
    ) -> Dict[str, Any]:
        """
        Create a new agent job.

        Args:
            agent_id: UUID of the agent to assign the job to
            mission: Mission description/instructions
            product_id: UUID of the product this job belongs to
            priority: Job priority (1-10, default 5)
            metadata: Optional job metadata

        Returns:
            {
                "job_id": "uuid",
                "status": "pending",
                "created_at": "2025-10-27T10:30:00Z",
                "agent_id": "uuid",
                "mission": "...",
                "priority": 5
            }
        """
        data = {
            "agent_id": agent_id,
            "mission": mission,
            "product_id": product_id,
            "priority": priority,
            "metadata": metadata or {}
        }
        return await self._api_request('POST', '/agent-jobs', data=data)

    async def send_agent_message(
        self,
        from_agent_id: str,
        to_agent_id: str,
        message_type: str,
        content: Dict
    ) -> Dict[str, Any]:
        """
        Send a message from one agent to another.

        Args:
            from_agent_id: UUID of sending agent
            to_agent_id: UUID of receiving agent
            message_type: Type of message (request, response, notification, etc.)
            content: Message content (JSON-serializable dict)

        Returns:
            {
                "message_id": "uuid",
                "timestamp": "2025-10-27T10:30:00Z",
                "status": "sent"
            }
        """
        data = {
            "from_agent_id": from_agent_id,
            "to_agent_id": to_agent_id,
            "message_type": message_type,
            "content": content
        }
        return await self._api_request('POST', '/agent-jobs/messages', data=data)

    async def get_agent_job_status(self, job_id: str) -> Dict[str, Any]:
        """
        Get current status of an agent job.

        Args:
            job_id: UUID of the job

        Returns:
            {
                "job_id": "uuid",
                "status": "in_progress",
                "progress": 45,
                "current_step": "Implementing feature X",
                "agent_id": "uuid",
                "metadata": {...}
            }
        """
        return await self._api_request('GET', f'/agent-jobs/{job_id}')

    async def acknowledge_agent_job(
        self,
        job_id: str,
        agent_id: str,
        acknowledgment_message: str = None
    ) -> Dict[str, Any]:
        """
        Acknowledge receipt and start of work on a job.

        Args:
            job_id: UUID of the job
            agent_id: UUID of the agent acknowledging
            acknowledgment_message: Optional acknowledgment message

        Returns:
            {
                "success": true,
                "acknowledged_at": "2025-10-27T10:30:00Z",
                "status": "acknowledged"
            }
        """
        data = {
            "agent_id": agent_id,
            "message": acknowledgment_message
        }
        return await self._api_request('POST', f'/agent-jobs/{job_id}/acknowledge', data=data)

    async def complete_agent_job(
        self,
        job_id: str,
        agent_id: str,
        result_data: Dict,
        artifacts: List[str] = None
    ) -> Dict[str, Any]:
        """
        Mark an agent job as completed with results.

        Args:
            job_id: UUID of the job
            agent_id: UUID of the completing agent
            result_data: Job results (JSON-serializable dict)
            artifacts: Optional list of artifact paths/URLs

        Returns:
            {
                "success": true,
                "completed_at": "2025-10-27T10:30:00Z",
                "result_summary": "..."
            }
        """
        data = {
            "agent_id": agent_id,
            "result_data": result_data,
            "artifacts": artifacts or []
        }
        return await self._api_request('POST', f'/agent-jobs/{job_id}/complete', data=data)

    async def fail_agent_job(
        self,
        job_id: str,
        agent_id: str,
        error_message: str,
        error_details: Dict = None
    ) -> Dict[str, Any]:
        """
        Mark an agent job as failed with error details.

        Args:
            job_id: UUID of the job
            agent_id: UUID of the failing agent
            error_message: Error description
            error_details: Optional error details (JSON-serializable dict)

        Returns:
            {
                "success": true,
                "failed_at": "2025-10-27T10:30:00Z"
            }
        """
        data = {
            "agent_id": agent_id,
            "error_message": error_message,
            "error_details": error_details or {}
        }
        return await self._api_request('POST', f'/agent-jobs/{job_id}/fail', data=data)

    async def list_active_agent_jobs(
        self,
        product_id: str = None,
        agent_id: str = None
    ) -> List[Dict[str, Any]]:
        """
        List active agent jobs, optionally filtered.

        Args:
            product_id: Optional - filter by product UUID
            agent_id: Optional - filter by agent UUID

        Returns:
            [
                {
                    "job_id": "uuid",
                    "status": "in_progress",
                    "agent_id": "uuid",
                    "mission": "...",
                    "progress": 30,
                    "created_at": "..."
                },
                ...
            ]
        """
        params = {}
        if product_id:
            params['product_id'] = product_id
        if agent_id:
            params['agent_id'] = agent_id

        return await self._api_request('GET', '/agent-jobs', params=params)

    async def close(self):
        """Close aiohttp session."""
        if self.session:
            await self.session.close()


# Export tools instance
agent_coordination = AgentCoordinationTools()
```

## Phase 2: Register MCP Tools (1 hour)

**File**: `src/giljo_mcp/tools/__init__.py`

**Add Import and Registration**:

```python
from .agent_coordination import agent_coordination

# Register all agent coordination tools
MCP_TOOLS.extend([
    {
        "name": "create_agent_job",
        "description": "Create a new agent job with mission instructions",
        "function": agent_coordination.create_agent_job
    },
    {
        "name": "send_agent_message",
        "description": "Send a message from one agent to another",
        "function": agent_coordination.send_agent_message
    },
    {
        "name": "get_agent_job_status",
        "description": "Get current status and progress of an agent job",
        "function": agent_coordination.get_agent_job_status
    },
    {
        "name": "acknowledge_agent_job",
        "description": "Acknowledge receipt and start of work on a job",
        "function": agent_coordination.acknowledge_agent_job
    },
    {
        "name": "complete_agent_job",
        "description": "Mark an agent job as completed with results",
        "function": agent_coordination.complete_agent_job
    },
    {
        "name": "fail_agent_job",
        "description": "Mark an agent job as failed with error details",
        "function": agent_coordination.fail_agent_job
    },
    {
        "name": "list_active_agent_jobs",
        "description": "List active agent jobs, optionally filtered by product or agent",
        "function": agent_coordination.list_active_agent_jobs
    }
])
```

## Phase 3: Testing (1-2 hours)

**Test File**: `tests/mcp/test_agent_coordination_tools.py`

Coverage:
- Create job via MCP tool
- Send message between agents via MCP
- Check job status via MCP
- Acknowledge, complete, fail jobs via MCP
- List jobs with filtering
- Authentication validation
- Multi-tenant isolation
- Error handling (invalid job_id, unauthorized access)

---

# Files to Modify

1. **src/giljo_mcp/tools/agent_coordination.py** (~250 lines, NEW FILE)
   - Complete MCP tools wrapper class
   - 7 async tool methods
   - HTTP client setup with auth
   - Error handling

2. **src/giljo_mcp/tools/__init__.py** (+40 lines)
   - Import agent_coordination module
   - Register 7 tools in MCP_TOOLS list

3. **tests/mcp/test_agent_coordination_tools.py** (~200 lines, NEW FILE)
   - Comprehensive test coverage
   - Multi-tenant isolation tests
   - Error handling tests

**Total**: ~490 lines across 3 files (2 new, 1 modified)

---

# API Dependencies

This handover relies on existing REST API endpoints (already implemented in v3.0+):

- POST /api/v1/agent-jobs
- GET /api/v1/agent-jobs
- GET /api/v1/agent-jobs/{job_id}
- POST /api/v1/agent-jobs/{job_id}/acknowledge
- POST /api/v1/agent-jobs/{job_id}/complete
- POST /api/v1/agent-jobs/{job_id}/fail
- POST /api/v1/agent-jobs/messages

No API changes required - pure wrapper implementation.

---

# Success Criteria

## Functional Requirements
- All 7 MCP tools callable via HTTP MCP endpoint
- Tools properly authenticated with JWT tokens
- Multi-tenant isolation enforced
- Error responses properly formatted for MCP clients
- Real-time WebSocket events still fire correctly
- Tools accessible from Claude Code, Codex, Gemini CLI

## Technical Requirements
- No changes to core coordination logic
- Consistent error handling across all tools
- Proper async/await usage throughout
- aiohttp session management (single session, proper cleanup)
- API request timeouts configured
- Comprehensive test coverage (80%+)

---

# Related Handovers

- **Handover 0019**: Agent Job Management (COMPLETE)
  - Provides the infrastructure this handover exposes

- **Handover 0020**: Orchestrator Enhancement (COMPLETE)
  - Mission planner uses job coordination system

- **Handover 0061**: Orchestrator Launch UI Workflow (NEXT)
  - Will use these MCP tools to launch orchestrator missions

- **Handover 0066**: Codex MCP Integration (DEPENDS ON THIS)
  - Codex agents will use these coordination tools

- **Handover 0067**: Gemini MCP Integration (DEPENDS ON THIS)
  - Gemini agents will use these coordination tools

---

# Risk Assessment

**Complexity**: LOW (pure wrapper implementation)
**Risk**: LOW (no core logic changes)
**Breaking Changes**: None
**Performance Impact**: Minimal (+10-20ms per MCP call vs direct API)

---

# Timeline Estimate

**Phase 1**: 2-3 hours (MCP tools module)
**Phase 2**: 1 hour (registration)
**Phase 3**: 1-2 hours (testing)

**Total**: 4-6 hours for experienced developer

---

**Decision Recorded By**: System Architect
**Date**: 2025-10-27
**Priority**: CRITICAL (blocks Handover 0061, 0066, 0067)

---

**End of Handover 0060**
