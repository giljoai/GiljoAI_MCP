---
Handover 0066: Codex MCP Integration
Date: 2025-10-27
Status: Ready for Implementation
Priority: MEDIUM
Complexity: HIGH
Duration: 12-16 hours
---

# Executive Summary

The GiljoAI MCP Server currently integrates with Claude Code as the primary external agent tool. This handover adds full integration with OpenAI Codex CLI, enabling Codex to be used as an alternative agent tool with access to the same agent coordination infrastructure (Handover 0060).

**Key Principle**: Multiple external agent tools should be supported with equal feature parity, allowing users to leverage the strengths of different AI coding assistants.

The system will implement Codex CLI wrapper, MCP server adapter, authentication bridge, and bidirectional communication with the GiljoAI orchestrator.

---

# Problem Statement

## Current State

Only Claude Code is integrated:
- Claude Code has full MCP access to agent coordination tools
- Codex CLI exists but has no GiljoAI integration
- Users can't assign Codex to agents (Handover 0063 enables UI, but backend missing)
- No Codex authentication with GiljoAI server
- No bidirectional communication between Codex and orchestrator

## Gaps Without This Implementation

1. **No Codex Support**: Can't use Codex as agent tool
2. **Limited Tool Options**: Users restricted to Claude Code only
3. **Feature Parity Gap**: Codex can't access agent coordination infrastructure
4. **No Authentication**: Codex can't authenticate with GiljoAI server
5. **Manual Coordination**: Must manually coordinate Codex work

---

# Implementation Plan

## Overview

This implementation creates a Codex MCP adapter that wraps the Codex CLI, implements authentication bridge, exposes agent coordination tools, and integrates with orchestrator workflow. Complex integration requiring both Python and Codex API work.

**Total Estimated Lines of Code**: ~800 lines across 8 files

## Phase 1: Codex CLI Wrapper (3-4 hours)

**File**: `src/giljo_mcp/integrations/codex/codex_client.py` (NEW)

```python
"""
OpenAI Codex CLI Integration

Wrapper for Codex CLI with GiljoAI MCP Server integration.
"""

import asyncio
import json
from typing import Dict, Any, Optional, List
from pathlib import Path
import aiohttp


class CodexClient:
    """Client for interacting with OpenAI Codex CLI."""

    def __init__(
        self,
        api_key: str,
        model: str = "gpt-4",
        mcp_server_url: str = "http://localhost:7272"
    ):
        self.api_key = api_key
        self.model = model
        self.mcp_server_url = mcp_server_url
        self.session = None

    async def _get_session(self) -> aiohttp.ClientSession:
        """Get or create aiohttp session."""
        if not self.session:
            self.session = aiohttp.ClientSession(
                headers={
                    "Authorization": f"Bearer {self.api_key}",
                    "Content-Type": "application/json"
                }
            )
        return self.session

    async def execute_task(
        self,
        instruction: str,
        context: Dict[str, Any] = None,
        tools: List[str] = None
    ) -> Dict[str, Any]:
        """
        Execute a task using Codex with optional tool access.

        Args:
            instruction: Task instruction/prompt
            context: Additional context (project info, product vision, etc.)
            tools: List of MCP tools to make available

        Returns:
            {
                "success": True,
                "result": "...",
                "artifacts": [...],
                "tool_calls": [...]
            }
        """
        session = await self._get_session()

        # Build prompt with context
        prompt = self._build_prompt(instruction, context)

        # Build tool schemas if tools specified
        tool_schemas = []
        if tools:
            tool_schemas = await self._get_tool_schemas(tools)

        # Call Codex API
        payload = {
            "model": self.model,
            "messages": [
                {"role": "system", "content": "You are a coding assistant integrated with GiljoAI MCP Server."},
                {"role": "user", "content": prompt}
            ],
            "tools": tool_schemas,
            "temperature": 0.7,
            "max_tokens": 4000
        }

        async with session.post(
            "https://api.openai.com/v1/chat/completions",
            json=payload
        ) as response:
            if response.status != 200:
                error_data = await response.json()
                raise Exception(f"Codex API error: {error_data}")

            result = await response.json()

        # Process response
        return self._process_response(result)

    def _build_prompt(self, instruction: str, context: Dict[str, Any] = None) -> str:
        """Build prompt with instruction and context."""
        prompt_parts = [instruction]

        if context:
            if context.get("product_name"):
                prompt_parts.append(f"\nProduct: {context['product_name']}")

            if context.get("project_name"):
                prompt_parts.append(f"Project: {context['project_name']}")

            if context.get("field_priority"):
                prompt_parts.append(f"\nField Priority:\n{json.dumps(context['field_priority'], indent=2)}")

            if context.get("vision_summary"):
                prompt_parts.append(f"\nProduct Vision:\n{context['vision_summary']}")

        return "\n".join(prompt_parts)

    async def _get_tool_schemas(self, tools: List[str]) -> List[Dict[str, Any]]:
        """
        Fetch MCP tool schemas from GiljoAI server.

        Converts MCP tool schemas to OpenAI function calling format.
        """
        # Fetch tool schemas from MCP server
        async with aiohttp.ClientSession() as session:
            async with session.get(f"{self.mcp_server_url}/mcp/tools") as response:
                if response.status != 200:
                    return []

                all_tools = await response.json()

        # Filter requested tools and convert to OpenAI format
        tool_schemas = []
        for tool_name in tools:
            mcp_tool = next((t for t in all_tools if t["name"] == tool_name), None)
            if mcp_tool:
                tool_schemas.append(self._convert_mcp_to_openai_tool(mcp_tool))

        return tool_schemas

    def _convert_mcp_to_openai_tool(self, mcp_tool: Dict) -> Dict:
        """Convert MCP tool schema to OpenAI function calling format."""
        return {
            "type": "function",
            "function": {
                "name": mcp_tool["name"],
                "description": mcp_tool["description"],
                "parameters": mcp_tool.get("parameters", {})
            }
        }

    def _process_response(self, result: Dict) -> Dict[str, Any]:
        """Process Codex API response."""
        choice = result["choices"][0]
        message = choice["message"]

        response = {
            "success": True,
            "result": message.get("content", ""),
            "tool_calls": [],
            "artifacts": []
        }

        # Process tool calls if any
        if message.get("tool_calls"):
            for tool_call in message["tool_calls"]:
                response["tool_calls"].append({
                    "tool": tool_call["function"]["name"],
                    "arguments": json.loads(tool_call["function"]["arguments"]),
                    "result": None  # Will be filled by execute_tool_call
                })

        return response

    async def execute_tool_call(
        self,
        tool_name: str,
        arguments: Dict[str, Any],
        auth_token: str
    ) -> Any:
        """
        Execute an MCP tool call via GiljoAI server.

        Args:
            tool_name: Name of MCP tool
            arguments: Tool arguments
            auth_token: GiljoAI JWT token for authentication

        Returns:
            Tool execution result
        """
        async with aiohttp.ClientSession() as session:
            headers = {
                "Authorization": f"Bearer {auth_token}",
                "Content-Type": "application/json"
            }

            async with session.post(
                f"{self.mcp_server_url}/mcp/tools/{tool_name}",
                json=arguments,
                headers=headers
            ) as response:
                if response.status >= 400:
                    error_data = await response.json()
                    raise Exception(f"Tool execution error: {error_data}")

                return await response.json()

    async def close(self):
        """Close aiohttp session."""
        if self.session:
            await self.session.close()
```

## Phase 2: Codex MCP Adapter (3-4 hours)

**File**: `src/giljo_mcp/integrations/codex/mcp_adapter.py` (NEW)

```python
"""
Codex MCP Adapter

Adapts Codex CLI to work with GiljoAI MCP Server infrastructure.
Handles authentication, tool exposure, and bidirectional communication.
"""

from typing import Dict, Any, Optional
import asyncio
from .codex_client import CodexClient
from ...auth import create_mcp_auth_token
from ...tools.agent_coordination import agent_coordination


class CodexMCPAdapter:
    """Adapter for integrating Codex with GiljoAI MCP Server."""

    def __init__(
        self,
        codex_api_key: str,
        giljoai_tenant_key: str,
        giljoai_user_id: str,
        mcp_server_url: str = "http://localhost:7272",
        model: str = "gpt-4"
    ):
        self.codex_client = CodexClient(
            api_key=codex_api_key,
            model=model,
            mcp_server_url=mcp_server_url
        )
        self.tenant_key = giljoai_tenant_key
        self.user_id = giljoai_user_id
        self.mcp_server_url = mcp_server_url
        self.auth_token = None

    async def authenticate(self) -> str:
        """
        Authenticate with GiljoAI MCP Server.

        Returns JWT token for MCP tool access.
        """
        self.auth_token = await create_mcp_auth_token(
            tenant_key=self.tenant_key,
            user_id=self.user_id
        )
        return self.auth_token

    async def execute_agent_job(
        self,
        job_id: str,
        agent_id: str
    ) -> Dict[str, Any]:
        """
        Execute an agent job assigned to Codex.

        Flow:
        1. Acknowledge job
        2. Get job details
        3. Execute with Codex
        4. Report progress
        5. Complete or fail job

        Returns:
            {
                "success": True,
                "job_id": "...",
                "result": {...}
            }
        """
        if not self.auth_token:
            await self.authenticate()

        try:
            # Step 1: Acknowledge job
            await agent_coordination.acknowledge_agent_job(
                job_id=job_id,
                agent_id=agent_id,
                acknowledgment_message="Codex has started work on this job"
            )

            # Step 2: Get job details
            job = await agent_coordination.get_agent_job_status(job_id)

            # Step 3: Build context from product/project
            context = await self._build_job_context(job)

            # Step 4: Execute with Codex
            # Available tools for this job
            available_tools = [
                "send_agent_message",
                "get_agent_job_status",
                "list_active_agent_jobs"
            ]

            result = await self.codex_client.execute_task(
                instruction=job["mission"],
                context=context,
                tools=available_tools
            )

            # Step 5: Execute any tool calls
            for tool_call in result["tool_calls"]:
                tool_result = await self.codex_client.execute_tool_call(
                    tool_name=tool_call["tool"],
                    arguments=tool_call["arguments"],
                    auth_token=self.auth_token
                )
                tool_call["result"] = tool_result

            # Step 6: Complete job
            await agent_coordination.complete_agent_job(
                job_id=job_id,
                agent_id=agent_id,
                result_data=result,
                artifacts=result.get("artifacts", [])
            )

            return {
                "success": True,
                "job_id": job_id,
                "result": result
            }

        except Exception as e:
            # Fail job on error
            await agent_coordination.fail_agent_job(
                job_id=job_id,
                agent_id=agent_id,
                error_message=str(e),
                error_details={"exception": type(e).__name__}
            )

            return {
                "success": False,
                "job_id": job_id,
                "error": str(e)
            }

    async def _build_job_context(self, job: Dict) -> Dict[str, Any]:
        """Build execution context from job details."""
        # Fetch product and project info from GiljoAI
        import aiohttp

        async with aiohttp.ClientSession() as session:
            headers = {"Authorization": f"Bearer {self.auth_token}"}

            # Get product info
            async with session.get(
                f"{self.mcp_server_url}/api/v1/products/{job['product_id']}",
                headers=headers
            ) as response:
                product = await response.json() if response.status == 200 else {}

            # Get project info if available
            project = {}
            if job.get("project_id"):
                async with session.get(
                    f"{self.mcp_server_url}/api/v1/projects/{job['project_id']}",
                    headers=headers
                ) as response:
                    project = await response.json() if response.status == 200 else {}

        return {
            "product_name": product.get("name"),
            "product_id": job["product_id"],
            "project_name": project.get("name"),
            "project_id": job.get("project_id"),
            "field_priority": product.get("config_data", {}).get("field_priority"),
            "vision_summary": product.get("vision_summary")
        }

    async def close(self):
        """Cleanup resources."""
        await self.codex_client.close()
```

## Phase 3: Configuration & Settings (2 hours)

**File**: `api/endpoints/integrations.py` (MODIFY EXISTING)

**Add Codex Settings**:

```python
class CodexSettings(BaseModel):
    """Codex integration settings."""
    enabled: bool = False
    api_key: Optional[str] = None
    model: str = "gpt-4"
    mcp_enabled: bool = True


class IntegrationsSettings(BaseModel):
    """Existing fields..."""
    claude_code: Optional[ClaudeCodeSettings] = None
    codex: Optional[CodexSettings] = None  # NEW
    gemini_cli: Optional[GeminiSettings] = None
    serena: Optional[SerenaSettings] = None
```

**File**: `frontend/src/views/settings/IntegrationsTab.vue` (MODIFY)

**Add Codex Configuration Section**:

```vue
<!-- Codex Section -->
<v-card class="mb-4">
  <v-card-title>
    <v-icon class="mr-2">mdi-code-braces</v-icon>
    OpenAI Codex
  </v-card-title>

  <v-card-text>
    <v-switch
      v-model="integrationsData.codex.enabled"
      label="Enable Codex Integration"
      color="primary"
      class="mb-4"
    />

    <v-text-field
      v-if="integrationsData.codex.enabled"
      v-model="integrationsData.codex.api_key"
      label="OpenAI API Key"
      type="password"
      prepend-icon="mdi-key"
      hint="Your OpenAI API key for Codex access"
      persistent-hint
      class="mb-4"
    />

    <v-select
      v-if="integrationsData.codex.enabled"
      v-model="integrationsData.codex.model"
      :items="codexModels"
      label="Model"
      prepend-icon="mdi-robot"
      class="mb-4"
    />

    <v-switch
      v-if="integrationsData.codex.enabled"
      v-model="integrationsData.codex.mcp_enabled"
      label="Enable MCP Tool Access"
      color="primary"
      hint="Allow Codex to access agent coordination tools"
      persistent-hint
    />
  </v-card-text>
</v-card>
```

```javascript
const codexModels = [
  { title: 'GPT-4', value: 'gpt-4' },
  { title: 'GPT-4 Turbo', value: 'gpt-4-turbo' },
  { title: 'GPT-3.5 Turbo', value: 'gpt-3.5-turbo' }
]
```

## Phase 4: Codex Agent Runner (2-3 hours)

**File**: `scripts/run_codex_agent.py` (NEW)

```python
"""
Codex Agent Runner

Standalone script to run Codex as an agent, polling for jobs and executing them.
"""

import asyncio
import argparse
import sys
from pathlib import Path

# Add src to path
sys.path.insert(0, str(Path(__file__).parent.parent))

from src.giljo_mcp.integrations.codex.mcp_adapter import CodexMCPAdapter
from src.giljo_mcp.config import config_manager


async def poll_for_jobs(
    adapter: CodexMCPAdapter,
    agent_id: str,
    interval: int = 10
):
    """
    Poll for agent jobs and execute them.

    Args:
        adapter: CodexMCPAdapter instance
        agent_id: UUID of Codex agent
        interval: Polling interval in seconds
    """
    print(f"[CODEX] Starting job polling for agent {agent_id}")

    while True:
        try:
            # Get pending jobs for this agent
            from src.giljo_mcp.tools.agent_coordination import agent_coordination

            jobs = await agent_coordination.list_active_agent_jobs(
                agent_id=agent_id
            )

            # Filter for pending/acknowledged jobs
            pending_jobs = [
                j for j in jobs
                if j["status"] in ["pending", "acknowledged"]
            ]

            if pending_jobs:
                print(f"[CODEX] Found {len(pending_jobs)} pending job(s)")

                for job in pending_jobs:
                    print(f"[CODEX] Executing job {job['job_id']}: {job['mission'][:60]}...")

                    result = await adapter.execute_agent_job(
                        job_id=job["job_id"],
                        agent_id=agent_id
                    )

                    if result["success"]:
                        print(f"[CODEX] Job {job['job_id']} completed successfully")
                    else:
                        print(f"[CODEX] Job {job['job_id']} failed: {result.get('error')}")

            await asyncio.sleep(interval)

        except KeyboardInterrupt:
            print("\n[CODEX] Stopping agent...")
            break
        except Exception as e:
            print(f"[CODEX] Error in polling loop: {e}")
            await asyncio.sleep(interval)


async def main():
    parser = argparse.ArgumentParser(description="Run Codex as GiljoAI agent")
    parser.add_argument("--agent-id", required=True, help="UUID of Codex agent")
    parser.add_argument("--tenant-key", required=True, help="Tenant key")
    parser.add_argument("--user-id", required=True, help="User ID")
    parser.add_argument("--interval", type=int, default=10, help="Polling interval (seconds)")

    args = parser.parse_args()

    # Load Codex settings from config
    config = config_manager.get_all()
    integrations = config.get("integrations", {})
    codex_settings = integrations.get("codex", {})

    if not codex_settings.get("enabled"):
        print("[CODEX] Error: Codex integration not enabled in settings")
        return

    api_key = codex_settings.get("api_key")
    if not api_key:
        print("[CODEX] Error: Codex API key not configured")
        return

    # Initialize adapter
    adapter = CodexMCPAdapter(
        codex_api_key=api_key,
        giljoai_tenant_key=args.tenant_key,
        giljoai_user_id=args.user_id,
        model=codex_settings.get("model", "gpt-4")
    )

    # Authenticate
    print("[CODEX] Authenticating with GiljoAI...")
    await adapter.authenticate()
    print("[CODEX] Authentication successful")

    # Start polling
    try:
        await poll_for_jobs(adapter, args.agent_id, args.interval)
    finally:
        await adapter.close()


if __name__ == "__main__":
    asyncio.run(main())
```

## Phase 5: Testing & Documentation (2 hours)

**Test Coverage**:

1. **Unit Tests** (`tests/integrations/test_codex_client.py`):
   - Test CodexClient API calls
   - Test prompt building
   - Test tool schema conversion
   - Test response processing

2. **Integration Tests** (`tests/integrations/test_codex_mcp_adapter.py`):
   - Test authentication
   - Test job execution flow
   - Test tool call execution
   - Test error handling

3. **End-to-End Test**:
   - Create agent with Codex tool
   - Create job via orchestrator
   - Run Codex agent runner
   - Verify job completion

**Documentation**:
- Update CLAUDE.md with Codex integration
- Create `docs/integrations/CODEX_SETUP.md`
- Update Integrations tab docs

---

# Files to Modify

1. **src/giljo_mcp/integrations/codex/codex_client.py** (~300 lines, NEW)
   - Complete Codex CLI wrapper

2. **src/giljo_mcp/integrations/codex/mcp_adapter.py** (~250 lines, NEW)
   - MCP adapter with authentication and job execution

3. **src/giljo_mcp/integrations/codex/__init__.py** (~10 lines, NEW)
   - Module exports

4. **api/endpoints/integrations.py** (+30 lines)
   - Add CodexSettings model

5. **frontend/src/views/settings/IntegrationsTab.vue** (+60 lines)
   - Add Codex configuration section

6. **scripts/run_codex_agent.py** (~150 lines, NEW)
   - Standalone agent runner

7. **tests/integrations/test_codex_*.py** (~100 lines, NEW)
   - Comprehensive tests

8. **docs/integrations/CODEX_SETUP.md** (~50 lines, NEW)
   - Setup documentation

**Total**: ~950 lines across 8 files (6 new, 2 modified)

---

# Success Criteria

## Functional Requirements
- Codex can authenticate with GiljoAI server
- Codex can access agent coordination MCP tools
- Codex can execute assigned agent jobs
- Codex can send/receive messages to/from other agents
- Codex can report progress and completion
- Tool calls work bidirectionally
- Multi-tenant isolation enforced

## Technical Requirements
- Secure API key storage
- Proper error handling and job failure reporting
- Efficient polling mechanism
- Tool schema conversion accurate
- Authentication token refresh
- Session cleanup

## User Experience Requirements
- Easy configuration via Integrations tab
- Clear status indicators
- Helpful error messages
- Agent runner can be started/stopped easily

---

# Related Handovers

- **Handover 0027**: Integrations Tab (DEPENDS ON)
  - Provides settings UI

- **Handover 0060**: MCP Agent Coordination Tool Exposure (DEPENDS ON)
  - Provides tools for Codex to use

- **Handover 0063**: Per-Agent Tool Selection UI (ENABLES)
  - Allows assigning Codex to agents

---

# Risk Assessment

**Complexity**: HIGH (external API integration, authentication bridge)
**Risk**: MEDIUM (depends on OpenAI API stability)
**Breaking Changes**: None
**Performance Impact**: Moderate (polling adds background load)

---

# Timeline Estimate

**Phase 1**: 3-4 hours (Codex client)
**Phase 2**: 3-4 hours (MCP adapter)
**Phase 3**: 2 hours (Configuration)
**Phase 4**: 2-3 hours (Agent runner)
**Phase 5**: 2 hours (Testing/docs)

**Total**: 12-16 hours for experienced developer

---

**Decision Recorded By**: System Architect
**Date**: 2025-10-27
**Priority**: MEDIUM (enables multi-tool workflows)

---

**End of Handover 0066**
