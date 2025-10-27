---
Handover 0067: Gemini MCP Integration
Date: 2025-10-27
Status: Ready for Implementation
Priority: MEDIUM
Complexity: VERY HIGH
Duration: 16-20 hours
---

# Executive Summary

The GiljoAI MCP Server supports Claude Code and (via Handover 0066) Codex as external agent tools. This handover adds Google Gemini 2.0 Flash Experimental integration, requiring a Node.js MCP wrapper due to Gemini's JavaScript-based SDK. This is the most complex integration due to the language bridge requirement.

**Key Principle**: Multiple external agent tools should be supported with equal feature parity, even when requiring cross-language bridges.

The system will implement Node.js MCP wrapper, Python-Node.js communication bridge, Gemini CLI adapter, authentication bridge, and bidirectional communication with the GiljoAI orchestrator.

---

# Problem Statement

## Current State

No Gemini integration exists:
- Claude Code (native Python MCP)
- Codex (Python wrapper, direct API)
- Gemini has no integration (JavaScript SDK only)
- Users can't assign Gemini to agents
- No Gemini authentication with GiljoAI server
- No way to leverage Gemini's multimodal capabilities

## Gaps Without This Implementation

1. **No Gemini Support**: Can't use Gemini as agent tool
2. **No Multimodal**: Can't leverage Gemini's vision/audio capabilities
3. **Limited Tool Options**: Missing competitive alternative to Claude/Codex
4. **No JavaScript Bridge**: No infrastructure for JS-based tool integrations
5. **Manual Coordination**: Must manually coordinate Gemini work

---

# Technical Challenges

1. **Language Bridge**: Gemini SDK is JavaScript-only, GiljoAI is Python
2. **MCP Protocol**: Need Node.js MCP server that talks to Python backend
3. **Authentication**: JWT tokens must cross language boundary
4. **WebSocket Communication**: Bidirectional real-time updates
5. **Process Management**: Node.js process lifecycle from Python
6. **Error Handling**: Cross-language error propagation

---

# Implementation Plan

## Overview

This implementation creates a Node.js MCP wrapper server that exposes Gemini to the Python GiljoAI backend via HTTP/WebSocket bridge. Complex multi-language integration requiring coordination between Python and Node.js processes.

**Total Estimated Lines of Code**: ~1100 lines across 12 files (Python + Node.js)

## Phase 1: Node.js MCP Wrapper Server (5-6 hours)

**File**: `src/giljo_mcp/integrations/gemini/node_mcp_wrapper/package.json` (NEW)

```json
{
  "name": "giljoai-gemini-mcp-wrapper",
  "version": "1.0.0",
  "description": "Node.js MCP wrapper for Google Gemini integration with GiljoAI",
  "main": "index.js",
  "type": "module",
  "scripts": {
    "start": "node index.js",
    "dev": "nodemon index.js"
  },
  "dependencies": {
    "@google/generative-ai": "^0.1.3",
    "express": "^4.18.2",
    "ws": "^8.14.2",
    "axios": "^1.6.0",
    "dotenv": "^16.3.1"
  },
  "devDependencies": {
    "nodemon": "^3.0.1"
  }
}
```

**File**: `src/giljo_mcp/integrations/gemini/node_mcp_wrapper/index.js` (NEW)

```javascript
/**
 * GiljoAI Gemini MCP Wrapper
 *
 * Node.js server that wraps Google Gemini SDK and exposes MCP-compatible
 * interface for Python GiljoAI backend.
 */

import express from 'express'
import { WebSocketServer } from 'ws'
import { GoogleGenerativeAI } from '@google/generative-ai'
import axios from 'axios'
import dotenv from 'dotenv'

dotenv.config()

const app = express()
app.use(express.json())

// Configuration
const PORT = process.env.GEMINI_MCP_PORT || 7273
const GILJOAI_SERVER_URL = process.env.GILJOAI_SERVER_URL || 'http://localhost:7272'
const GEMINI_API_KEY = process.env.GEMINI_API_KEY
const GEMINI_MODEL = process.env.GEMINI_MODEL || 'gemini-2.0-flash-exp'

if (!GEMINI_API_KEY) {
  console.error('[GEMINI MCP] Error: GEMINI_API_KEY not set')
  process.exit(1)
}

// Initialize Gemini
const genAI = new GoogleGenerativeAI(GEMINI_API_KEY)
const model = genAI.getGenerativeModel({ model: GEMINI_MODEL })

// Active sessions
const sessions = new Map()

/**
 * Health check endpoint
 */
app.get('/health', (req, res) => {
  res.json({
    status: 'healthy',
    service: 'gemini-mcp-wrapper',
    model: GEMINI_MODEL,
    giljoai_server: GILJOAI_SERVER_URL
  })
})

/**
 * Execute task with Gemini
 */
app.post('/execute', async (req, res) => {
  try {
    const { instruction, context, tools, auth_token } = req.body

    if (!instruction) {
      return res.status(400).json({ error: 'instruction is required' })
    }

    // Build prompt with context
    const prompt = buildPrompt(instruction, context)

    // Configure tools if provided
    let toolConfig = null
    if (tools && tools.length > 0) {
      toolConfig = await fetchToolSchemas(tools, auth_token)
    }

    // Generate content with Gemini
    const generationConfig = {
      temperature: 0.7,
      topK: 40,
      topP: 0.95,
      maxOutputTokens: 8192,
    }

    const chat = model.startChat({
      generationConfig,
      history: [],
    })

    const result = await chat.sendMessage(prompt)
    const response = result.response
    const text = response.text()

    // Parse tool calls if any (Gemini function calling format)
    const toolCalls = parseToolCalls(response)

    // Execute tool calls if any
    const executedTools = []
    if (toolCalls.length > 0 && auth_token) {
      for (const toolCall of toolCalls) {
        const toolResult = await executeToolCall(
          toolCall.name,
          toolCall.args,
          auth_token
        )
        executedTools.push({
          tool: toolCall.name,
          arguments: toolCall.args,
          result: toolResult
        })
      }
    }

    res.json({
      success: true,
      result: text,
      tool_calls: executedTools,
      artifacts: []
    })

  } catch (error) {
    console.error('[GEMINI MCP] Execution error:', error)
    res.status(500).json({
      success: false,
      error: error.message
    })
  }
})

/**
 * Build prompt with context
 */
function buildPrompt(instruction, context) {
  let prompt = instruction

  if (context) {
    if (context.product_name) {
      prompt += `\n\nProduct: ${context.product_name}`
    }
    if (context.project_name) {
      prompt += `\nProject: ${context.project_name}`
    }
    if (context.field_priority) {
      prompt += `\n\nField Priority:\n${JSON.stringify(context.field_priority, null, 2)}`
    }
    if (context.vision_summary) {
      prompt += `\n\nProduct Vision:\n${context.vision_summary}`
    }
  }

  return prompt
}

/**
 * Fetch MCP tool schemas from GiljoAI server
 */
async function fetchToolSchemas(tools, authToken) {
  try {
    const response = await axios.get(`${GILJOAI_SERVER_URL}/mcp/tools`, {
      headers: { Authorization: `Bearer ${authToken}` }
    })

    const allTools = response.data

    // Filter and convert to Gemini function calling format
    const toolSchemas = tools
      .map(toolName => {
        const mcpTool = allTools.find(t => t.name === toolName)
        if (mcpTool) {
          return convertMcpToGeminiTool(mcpTool)
        }
        return null
      })
      .filter(t => t !== null)

    return toolSchemas

  } catch (error) {
    console.error('[GEMINI MCP] Error fetching tool schemas:', error.message)
    return []
  }
}

/**
 * Convert MCP tool schema to Gemini function calling format
 */
function convertMcpToGeminiTool(mcpTool) {
  return {
    name: mcpTool.name,
    description: mcpTool.description,
    parameters: mcpTool.parameters || {}
  }
}

/**
 * Parse tool calls from Gemini response
 */
function parseToolCalls(response) {
  const toolCalls = []

  // Gemini function calling uses functionCall in response
  const functionCall = response.functionCall
  if (functionCall) {
    toolCalls.push({
      name: functionCall.name,
      args: functionCall.args
    })
  }

  return toolCalls
}

/**
 * Execute MCP tool call via GiljoAI server
 */
async function executeToolCall(toolName, args, authToken) {
  try {
    const response = await axios.post(
      `${GILJOAI_SERVER_URL}/mcp/tools/${toolName}`,
      args,
      {
        headers: {
          Authorization: `Bearer ${authToken}`,
          'Content-Type': 'application/json'
        }
      }
    )

    return response.data

  } catch (error) {
    console.error(`[GEMINI MCP] Tool execution error (${toolName}):`, error.message)
    throw error
  }
}

/**
 * WebSocket server for real-time updates
 */
const wss = new WebSocketServer({ noServer: true })

wss.on('connection', (ws) => {
  console.log('[GEMINI MCP] WebSocket client connected')

  ws.on('message', async (message) => {
    try {
      const data = JSON.parse(message)

      if (data.type === 'execute') {
        // Execute task via WebSocket for streaming
        const result = await executeTaskStreaming(data, ws)
      }
    } catch (error) {
      ws.send(JSON.stringify({ type: 'error', error: error.message }))
    }
  })

  ws.on('close', () => {
    console.log('[GEMINI MCP] WebSocket client disconnected')
  })
})

/**
 * Start server
 */
const server = app.listen(PORT, () => {
  console.log(`[GEMINI MCP] Server listening on port ${PORT}`)
  console.log(`[GEMINI MCP] Model: ${GEMINI_MODEL}`)
  console.log(`[GEMINI MCP] GiljoAI Server: ${GILJOAI_SERVER_URL}`)
})

// Upgrade HTTP to WebSocket
server.on('upgrade', (request, socket, head) => {
  wss.handleUpgrade(request, socket, head, (ws) => {
    wss.emit('connection', ws, request)
  })
})

// Graceful shutdown
process.on('SIGTERM', () => {
  console.log('[GEMINI MCP] Shutting down gracefully...')
  server.close(() => {
    console.log('[GEMINI MCP] Server closed')
    process.exit(0)
  })
})
```

## Phase 2: Python Bridge to Node.js MCP (4-5 hours)

**File**: `src/giljo_mcp/integrations/gemini/gemini_client.py` (NEW)

```python
"""
Gemini Client - Python Bridge to Node.js MCP Wrapper

Communicates with Node.js Gemini MCP wrapper via HTTP/WebSocket.
"""

import asyncio
import aiohttp
from typing import Dict, Any, Optional, List


class GeminiClient:
    """Client for communicating with Gemini via Node.js MCP wrapper."""

    def __init__(
        self,
        wrapper_url: str = "http://localhost:7273",
        giljoai_server_url: str = "http://localhost:7272"
    ):
        self.wrapper_url = wrapper_url
        self.giljoai_server_url = giljoai_server_url
        self.session = None

    async def _get_session(self) -> aiohttp.ClientSession:
        """Get or create aiohttp session."""
        if not self.session:
            self.session = aiohttp.ClientSession()
        return self.session

    async def health_check(self) -> Dict[str, Any]:
        """Check if Node.js wrapper is healthy."""
        session = await self._get_session()

        try:
            async with session.get(f"{self.wrapper_url}/health", timeout=5) as response:
                if response.status == 200:
                    return await response.json()
                else:
                    raise Exception(f"Wrapper unhealthy: {response.status}")
        except aiohttp.ClientError as e:
            raise Exception(f"Cannot connect to Gemini wrapper: {e}")

    async def execute_task(
        self,
        instruction: str,
        context: Dict[str, Any] = None,
        tools: List[str] = None,
        auth_token: str = None
    ) -> Dict[str, Any]:
        """
        Execute a task using Gemini.

        Args:
            instruction: Task instruction/prompt
            context: Additional context (project info, product vision, etc.)
            tools: List of MCP tools to make available
            auth_token: GiljoAI JWT token for tool access

        Returns:
            {
                "success": True,
                "result": "...",
                "artifacts": [...],
                "tool_calls": [...]
            }
        """
        session = await self._get_session()

        payload = {
            "instruction": instruction,
            "context": context or {},
            "tools": tools or [],
            "auth_token": auth_token
        }

        async with session.post(
            f"{self.wrapper_url}/execute",
            json=payload,
            timeout=aiohttp.ClientTimeout(total=120)
        ) as response:
            if response.status >= 400:
                error_data = await response.json()
                raise Exception(f"Gemini execution error: {error_data.get('error')}")

            return await response.json()

    async def close(self):
        """Close aiohttp session."""
        if self.session:
            await self.session.close()
```

**File**: `src/giljo_mcp/integrations/gemini/mcp_adapter.py` (NEW)

```python
"""
Gemini MCP Adapter

Adapts Gemini (via Node.js wrapper) to work with GiljoAI MCP Server infrastructure.
Similar to Codex adapter but bridges through Node.js process.
"""

from typing import Dict, Any, Optional
import asyncio
import subprocess
import time
from pathlib import Path
from .gemini_client import GeminiClient
from ...auth import create_mcp_auth_token
from ...tools.agent_coordination import agent_coordination


class GeminiMCPAdapter:
    """Adapter for integrating Gemini with GiljoAI MCP Server."""

    def __init__(
        self,
        gemini_api_key: str,
        giljoai_tenant_key: str,
        giljoai_user_id: str,
        mcp_server_url: str = "http://localhost:7272",
        wrapper_port: int = 7273
    ):
        self.gemini_api_key = gemini_api_key
        self.tenant_key = giljoai_tenant_key
        self.user_id = giljoai_user_id
        self.mcp_server_url = mcp_server_url
        self.wrapper_port = wrapper_port
        self.wrapper_url = f"http://localhost:{wrapper_port}"

        self.gemini_client = GeminiClient(
            wrapper_url=self.wrapper_url,
            giljoai_server_url=mcp_server_url
        )

        self.auth_token = None
        self.wrapper_process = None

    async def start_wrapper(self):
        """Start Node.js MCP wrapper process."""
        wrapper_dir = Path(__file__).parent / "node_mcp_wrapper"

        # Set environment variables
        env = {
            "GEMINI_API_KEY": self.gemini_api_key,
            "GEMINI_MCP_PORT": str(self.wrapper_port),
            "GILJOAI_SERVER_URL": self.mcp_server_url,
            "PATH": subprocess.os.environ.get("PATH", "")
        }

        # Start Node.js process
        self.wrapper_process = subprocess.Popen(
            ["node", "index.js"],
            cwd=str(wrapper_dir),
            env=env,
            stdout=subprocess.PIPE,
            stderr=subprocess.PIPE
        )

        # Wait for wrapper to be ready
        for _ in range(30):  # 30 seconds timeout
            try:
                await self.gemini_client.health_check()
                print("[GEMINI] Wrapper started successfully")
                return
            except Exception:
                await asyncio.sleep(1)

        raise Exception("Gemini wrapper failed to start")

    async def stop_wrapper(self):
        """Stop Node.js MCP wrapper process."""
        if self.wrapper_process:
            self.wrapper_process.terminate()
            self.wrapper_process.wait(timeout=10)
            self.wrapper_process = None
            print("[GEMINI] Wrapper stopped")

    async def authenticate(self) -> str:
        """Authenticate with GiljoAI MCP Server."""
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
        Execute an agent job assigned to Gemini.

        Flow matches Codex adapter but uses Gemini client.
        """
        if not self.auth_token:
            await self.authenticate()

        try:
            # Acknowledge job
            await agent_coordination.acknowledge_agent_job(
                job_id=job_id,
                agent_id=agent_id,
                acknowledgment_message="Gemini has started work on this job"
            )

            # Get job details
            job = await agent_coordination.get_agent_job_status(job_id)

            # Build context
            context = await self._build_job_context(job)

            # Execute with Gemini
            available_tools = [
                "send_agent_message",
                "get_agent_job_status",
                "list_active_agent_jobs"
            ]

            result = await self.gemini_client.execute_task(
                instruction=job["mission"],
                context=context,
                tools=available_tools,
                auth_token=self.auth_token
            )

            # Complete job
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
        """Build execution context from job details (same as Codex)."""
        # ... (same implementation as Codex adapter)
        pass

    async def close(self):
        """Cleanup resources."""
        await self.gemini_client.close()
        await self.stop_wrapper()
```

## Phase 3: Configuration & Agent Runner (3-4 hours)

**File**: `api/endpoints/integrations.py` (MODIFY)

```python
class GeminiSettings(BaseModel):
    """Gemini integration settings."""
    enabled: bool = False
    api_key: Optional[str] = None
    model: str = "gemini-2.0-flash-exp"
    wrapper_port: int = 7273
    mcp_enabled: bool = True
```

**File**: `scripts/run_gemini_agent.py` (NEW) - Similar to run_codex_agent.py but starts Node.js wrapper first

**File**: `frontend/src/views/settings/IntegrationsTab.vue` (MODIFY) - Add Gemini section similar to Codex

## Phase 4: Process Management & Lifecycle (2-3 hours)

**File**: `src/giljo_mcp/integrations/gemini/process_manager.py` (NEW)

```python
"""
Gemini Process Manager

Manages lifecycle of Node.js wrapper processes.
Handles startup, health monitoring, restart on failure.
"""

import asyncio
import subprocess
from typing import Dict
from pathlib import Path


class GeminiProcessManager:
    """Manages Node.js wrapper process lifecycle."""

    def __init__(self):
        self.processes: Dict[str, subprocess.Popen] = {}

    async def start_wrapper(
        self,
        agent_id: str,
        api_key: str,
        port: int = 7273
    ) -> bool:
        """Start wrapper process for agent."""
        # ... implementation ...
        pass

    async def stop_wrapper(self, agent_id: str):
        """Stop wrapper process."""
        # ... implementation ...
        pass

    async def health_check(self, agent_id: str) -> bool:
        """Check if wrapper is healthy."""
        # ... implementation ...
        pass

    async def restart_if_unhealthy(self, agent_id: str):
        """Restart wrapper if unhealthy."""
        # ... implementation ...
        pass
```

## Phase 5: Testing & Documentation (2 hours)

Similar test structure to Codex integration but with Node.js wrapper tests added.

---

# Files to Modify

**Node.js Files** (NEW):
1. `src/giljo_mcp/integrations/gemini/node_mcp_wrapper/package.json` (~30 lines)
2. `src/giljo_mcp/integrations/gemini/node_mcp_wrapper/index.js` (~350 lines)
3. `src/giljo_mcp/integrations/gemini/node_mcp_wrapper/.env.example` (~10 lines)

**Python Files**:
4. `src/giljo_mcp/integrations/gemini/gemini_client.py` (~120 lines, NEW)
5. `src/giljo_mcp/integrations/gemini/mcp_adapter.py` (~280 lines, NEW)
6. `src/giljo_mcp/integrations/gemini/process_manager.py` (~150 lines, NEW)
7. `src/giljo_mcp/integrations/gemini/__init__.py` (~10 lines, NEW)

**Configuration**:
8. `api/endpoints/integrations.py` (+30 lines)
9. `frontend/src/views/settings/IntegrationsTab.vue` (+60 lines)

**Scripts**:
10. `scripts/run_gemini_agent.py` (~180 lines, NEW)

**Tests**:
11. `tests/integrations/test_gemini_*.py` (~100 lines, NEW)

**Documentation**:
12. `docs/integrations/GEMINI_SETUP.md` (~70 lines, NEW)

**Total**: ~1390 lines across 12 files (10 new, 2 modified)

---

# Success Criteria

## Functional Requirements
- Node.js wrapper starts and stays healthy
- Gemini can authenticate with GiljoAI server
- Gemini can access agent coordination MCP tools
- Gemini can execute assigned agent jobs
- Tool calls work bidirectionally across language bridge
- Process lifecycle managed properly
- Multi-tenant isolation enforced

## Technical Requirements
- Wrapper process auto-restarts on failure
- Health checks every 30 seconds
- Proper error handling across language boundary
- Efficient HTTP/WebSocket communication
- Authentication token refresh
- Clean shutdown of all processes

## User Experience Requirements
- Easy configuration via Integrations tab
- Clear status indicators
- Helpful error messages
- Wrapper status visible in UI

---

# Related Handovers

- **Handover 0027**: Integrations Tab (DEPENDS ON)
- **Handover 0060**: MCP Agent Coordination Tool Exposure (DEPENDS ON)
- **Handover 0063**: Per-Agent Tool Selection UI (ENABLES)
- **Handover 0066**: Codex MCP Integration (SIMILAR PATTERN)

---

# Risk Assessment

**Complexity**: VERY HIGH (cross-language, process management)
**Risk**: HIGH (Node.js dependency, process lifecycle)
**Breaking Changes**: None
**Performance Impact**: Moderate (additional process, HTTP overhead)

---

# Timeline Estimate

**Phase 1**: 5-6 hours (Node.js wrapper)
**Phase 2**: 4-5 hours (Python bridge)
**Phase 3**: 3-4 hours (Configuration/runner)
**Phase 4**: 2-3 hours (Process management)
**Phase 5**: 2 hours (Testing/docs)

**Total**: 16-20 hours for experienced developer

---

**Decision Recorded By**: System Architect
**Date**: 2025-10-27
**Priority**: MEDIUM (enables multi-tool workflows, multimodal capabilities)

---

**End of Handover 0067**
