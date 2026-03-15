---
**Document Type:** Harmonized Workflow Documentation
**Last Updated:** 2025-11-29
**Purpose:** Single source of truth for GiljoAI Agent Orchestration workflows
**Status:** ✅ Harmonized from PDF and Markdown sources
---

# GiljoAI MCP Server - Harmonized Workflow Documentation

## Critical Terminology Alignment

**IMPORTANT**: This section resolves naming inconsistencies between UI labels and backend implementation.

### Button & Endpoint Mapping

| UI Label | Backend Endpoint | Actual Function | Database Field Updated |
|----------|-----------------|-----------------|------------------------|
| "Stage Project" | `/api/v1/projects/{id}/activate` | Activates project & creates orchestrator job | Creates MCPAgentJob record |
| "Launch Jobs" | Navigation only | Switches from Launch tab to Implementation tab | None |
| "Activate Project" | `/api/v1/projects/{id}/activate` | Same as "Stage Project" | Project.is_active = true |

### Field Naming Convention (User vs AI)

| Field | Type | Description | Filled By |
|-------|------|-------------|-----------|
| `Product.description` | User Input | User-written product description | **Human** (via UI) |
| `Project.description` | User Input | User-written project requirements | **Human** (via UI) |
| `Project.mission` | AI Output | Orchestrator-generated mission plan | **Orchestrator** (during staging) |
| `MCPAgentJob.mission` | AI Output | Individual agent's job assignment | **Orchestrator** (via spawn_agent_job) |

**Key Rule**: User writes = "description", AI generates = "mission"

### Status Value Translation (Backend vs Frontend)

| Backend (Python/DB) | Frontend (UI/Vue) | Display Label | Description |
|-------------------|------------------|--------------|-------------|
| `"pending"` | `"waiting"` | "Waiting" | Job created but not yet started |
| `"active"` | `"active"` | "Active" | Agent has claimed the job |
| `"working"` | `"working"` | "Working" | Agent is executing tasks |
| `"complete"` | `"complete"` | "Complete" | Job finished successfully |
| `"failed"` | `"failed"` | "Failed" | Job encountered fatal error |
| `"blocked"` | `"blocked"` | "Blocked" | Job needs intervention |

**Translation Layer**: The API automatically translates `"pending"` → `"waiting"` when sending data to frontend. This translation occurs in the API response serialization layer before WebSocket events and HTTP responses are sent to clients. This is an intentional design to maintain user-friendly terminology without refactoring legacy backend code.

**Where Translation Happens**:
- HTTP Responses: FastAPI endpoint response models handle translation
- WebSocket Events: Event serialization in `api/websocket.py` translates before emission
- Frontend receives: Always sees `"waiting"` for initial job state
- Backend stores: Always uses `"pending"` in database and internal logic

---

## Project Staging → Implementation Phase (Complete Flow)

### Phase 1: PROJECT ACTIVATION & STAGING

#### Step 1: Navigate to Project
```
User Action: Click [Launch Project] button in project list
         OR: Click "Jobs" in left sidebar
         ↓
System Response: Navigate to custom project URL
         URL Format: http://{host}:port/projects/{project_ID}?via=jobs
         ↓
Landing Page: "Launch" Tab (First tab in two-tab interface)
```

#### Step 2: Launch Tab Interface Elements
```
┌─────────────────────────────────────────────────┐
│  Launch Tab                                     │
├─────────────────────────────────────────────────┤
│  [Stage Project] Button                         │ ← UI Label (misleading)
│                                                  │   Backend: /activate endpoint
│  Project Description (editable)                 │ ← User-written content
│                                                  │
│  Orchestrator Generated Mission (empty)         │ ← Will be populated after staging
│                                                  │
│  Orchestrator Card                              │ ← Shows agent_id
│    - Role: orchestrator                         │
│    - Status: waiting                            │
│    - [Copy Prompt >] (disabled initially)       │
└─────────────────────────────────────────────────┘
```

#### Step 3: Stage Project Button Click
```
User Action: Click [Stage Project] button
         ↓
Backend Process:
  1. POST /api/v1/projects/{id}/activate
  2. Create MCPAgentJob record:
     - agent_type: "orchestrator"
     - status: "pending" (backend) → "waiting" (UI display)
     - mission: "I am ready to create the project mission..."
  3. Generate thin client prompt (450-550 tokens)
  4. Enable orchestrator [Copy Prompt >] button
         ↓
UI Updates:
  - Orchestrator card shows copyable prompt
  - User copies prompt to terminal
```

#### Step 4: Orchestrator Execution - Mission Creation
```
Terminal Process:
  1. User pastes thin prompt into CLI tool
  2. Orchestrator MCP sequence:
     a. health_check() - Verify MCP connection
     b. get_orchestrator_instructions() - Fetch mission context
        - Reads Product.description (user input)
        - Reads Project.description (user input)
        - Reads vision documents (chunked)
        - Reads all context based on toggle/depth settings
     c. Create mission based on context
     d. update_project_mission() - PERSIST to database
        - Saves to Project.mission field
        - WebSocket: project:mission_updated event
     e. spawn_agent_job() - Create agent jobs
        - Creates MCPAgentJob records for each agent
        - Each gets portion of mission
         ↓
UI Live Updates:
  - "Orchestrator Generated Mission" window populates
  - Agent cards appear in "Agent Team" section
  - [Launch Jobs] button appears
```

---

### Phase 2: JOB IMPLEMENTATION & EXECUTION

#### Step 5: Navigate to Implementation
```
User Action: Click [Launch Jobs] button
         ↓
Navigation: Switch to "Implementation" Tab (same URL)
```

#### Step 6: Implementation Tab Interface
```
┌─────────────────────────────────────────────────┐
│  Implementation Tab                             │
├─────────────────────────────────────────────────┤
│  Claude Code CLI Mode: [Toggle Switch]          │ ← Critical toggle
│  Hint: (dynamic based on toggle state)          │
│                                                  │
│  Orchestrator Card                              │
│    - Status: waiting → active → working         │
│    - [Copy Prompt >] (always enabled)           │
│                                                  │
│  Agent Cards (spawned by orchestrator)          │
│    - Implementer_1 [Copy Prompt >]              │ ← Enabled/disabled
│    - Tester_1 [Copy Prompt >]                   │   based on toggle
│    - Documenter_1 [Copy Prompt >]               │
│    - [Additional agents...]                     │
│                                                  │
│  Message Center [Tab indicator with count]      │
└─────────────────────────────────────────────────┘
```

#### Step 7A: Claude Code CLI Mode (Toggle ON)
```
Toggle State: ON
         ↓
UI Behavior:
  - Only orchestrator [Copy Prompt >] button active
  - All agent prompt buttons grayed out
  - Hint: "Claude Code subagent mode - Orchestrator spawns agents"
         ↓
Execution Flow:
  1. User copies orchestrator prompt
  2. Paste in single terminal window
  3. Orchestrator reads special Claude mode instructions
  4. Uses native Claude subagent feature
  5. Spawns agents using {agent_role}.md templates
  6. Passes agent_id, job_id to each subagent
  7. Subagents fetch missions via get_agent_mission()
         ↓
Single Terminal Execution with native subagents
```

#### Step 7B: Multi-Terminal Mode (Toggle OFF - Default)
```
Toggle State: OFF (default)
         ↓
UI Behavior:
  - ALL [Copy Prompt >] buttons active
  - Each agent gets unique prompt
  - Hint: "Multi-terminal mode - Launch agents in separate windows"
         ↓
Execution Flow:
  1. User copies each agent prompt
  2. Paste in separate terminal windows
  3. Each agent reads its unique instructions:
     - Includes agent_id, job_id, project_id
     - Fetches role from MCP server
     - Gets mission via get_agent_mission()
  4. Orchestrator sends coordination broadcast
  5. Agents acknowledge and begin work
         ↓
Multiple Terminal Windows (one per agent)
```

---

## Job Action Phase Details (Implementation)

### Agent Status Progression
```
Status Flow: pending/waiting → active → working → complete/failed/blocked
             (backend/UI)        ↓         ↓              ↓
UI Updates:     Badge         Badge    Progress %    Final state
WebSocket:   agent:acknowledged  agent:progress  agent:complete

Note: Backend stores "pending", UI displays "waiting" via API translation
```

### MCP Communication During Execution

#### Available MCP Tools for Agents
```
Coordination Tools:
├── get_pending_jobs()      - Find work assigned to agent
├── acknowledge_job()       - Claim job (waiting → active)
├── report_progress()       - Update progress percentage
├── complete_job()          - Mark as done with results
└── report_error()          - Report blocking issues

Messaging Tools (MESSAGES category):
├── send_message()          - Direct or broadcast messages
├── receive_messages()      - Check incoming messages
└── acknowledge_message()   - Mark message as read

See: docs/architecture/messaging_contract.md for full taxonomy
     (Messages vs Signals vs Instructions)

Status Tools:
├── get_workflow_status()   - View all agents in project
└── get_next_instruction()  - Check for orchestrator updates
```

### Real-time UI Updates
```
WebSocket Events → UI Components:
├── job:status_changed      → Agent card badge color
├── job:progress_updated    → Progress bar percentage
├── message:new             → Message center count badge
├── project:mission_updated → Mission window content
└── agent:spawned           → New agent card appears
```

### Agent Execution Patterns

#### Parallel Execution
```
Orchestrator Decision: Independent tasks
         ↓
Example:
  - Implementer_1: Backend authentication
  - Implementer_2: Frontend UI
  - Documenter_1: API documentation
         ↓
All agents work simultaneously
```

#### Sequential Execution
```
Orchestrator Decision: Dependent tasks
         ↓
Example:
  1. Implementer creates feature
  2. Tester validates feature
  3. Documenter updates docs
         ↓
Agents wait for dependencies
```

---

## Critical Implementation Details

### 1. Token Optimization (Handover 0246 Series)
- **Before**: 3,500 token prompts embedded in requests
- **After**: 450-550 token thin client prompts
- **Method**: Mission fetched via MCP tools, not embedded

### 2. Context Configuration
User configurable in: My Settings → Context Configuration
- Enabled (toggle: true): Category included with configured depth
- Disabled (toggle: false): Category excluded entirely

### 3. Agent Template Management
- **Max Active**: 8 agent types at once
- **Unlimited Instances**: Can have multiple of same type (Implementer_1, Implementer_2)
- **Export Required**: Claude Code mode needs templates exported to ~/.claude/agents/

### 4. Orchestrator Succession (Context Limits)
When orchestrator approaches context limit (90%):
1. User clicks [Handover] button
2. Current orchestrator writes 360 memory
3. New orchestrator spawned with condensed context
4. Mission and agent states preserved
5. Execution continues with new orchestrator

---

## Workflow State Diagram

```
┌──────────┐      ┌──────────┐      ┌────────────┐      ┌──────────────┐
│ Project  │ ───► │ Activate │ ───► │   Stage    │ ───► │ Implementation│
│ Created  │      │ Project  │      │  (Launch)  │      │   (Execute)   │
└──────────┘      └──────────┘      └────────────┘      └──────────────┘
     │                  │                   │                    │
     │                  │                   │                    │
     ▼                  ▼                   ▼                    ▼
[Inactive]    [Creates Job Record]  [Mission Created]    [Agents Working]
                [Status: waiting]    [Agents Spawned]     [Status Updates]
                                     [Jobs Assigned]      [Message Flow]
```

---

## Resolved Inconsistencies

1. **"Stage Project" vs "Activate"**: UI shows "Stage Project", backend uses `/activate` endpoint
2. **Tab Navigation**: Two distinct tabs - "Launch" (staging) and "Implementation" (execution)
3. **Claude Toggle Location**: Located at top of Implementation tab, not Launch tab
4. **Mission Persistence**: Mission saved to database via `update_project_mission()` MCP tool
5. **Job Status Translation**: Backend stores "pending", Frontend displays "waiting" (intentional design)
   - API layer handles automatic translation
   - Maintains backward compatibility with existing backend code
   - Provides user-friendly terminology in UI
6. **Agent Prompt Behavior**: Toggle controls which prompt buttons are active

---

## Key Takeaways

1. **UI Labels ≠ Backend Endpoints**: "Stage Project" button actually calls `/activate`
2. **Two-Phase Process**: Launch tab (staging) → Implementation tab (execution)
3. **Mode Toggle Critical**: Determines single vs multi-terminal execution
4. **Mission Persistence**: Orchestrator creates AND persists mission to database
5. **Real-time Updates**: WebSocket events drive all UI updates
6. **Token Efficient**: Thin client architecture reduces prompt size by 85%
7. **Status Translation**: API layer transparently converts backend "pending" to UI "waiting"

---

*This harmonized document represents the authoritative workflow for GiljoAI MCP Server v3.2+*