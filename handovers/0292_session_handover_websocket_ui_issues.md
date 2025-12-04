# Handover 0292: WebSocket UI Issues - Session Memory

**Date**: 2025-12-03
**Status**: NEEDS DIAGNOSIS AND FIX
**Priority**: HIGH - Multiple regressions introduced

---

## Current Problems (Confirmed by User)

### Problem 1: Orchestrator Not Spawning
**Symptom**: After clicking "Stage Project", orchestrator is not appearing in the Jobs tab
**URL**: `http://10.1.0.164:7274/projects/{project_id}?via=jobs&tab=jobs`
**Suspected Cause**: Changes to `thin_prompt_generator.py` may have broken orchestrator spawning
**Note**: User mentioned "mix use of `_build_thin_prompt()` appears to be deprecated"

### Problem 2: Launch Jobs Button Not Enabling
**Symptom**: Even when messages are sent, the "Launch Jobs" button doesn't enable automatically
**Expected**: Button should enable when orchestrator sends `STAGING_COMPLETE` broadcast

### Problem 3: Message Counts Not Updating in Dashboard
**Symptom**: "Messages Sent" and "Messages Waiting" columns in JobsTab dashboard show 0 even when messages exist
**Expected**: Real-time count updates via WebSocket events

---

## Files Modified in This Session

### 1. `api/endpoints/mcp_http.py` (Lines 195-225)
**Change**: Fixed MCP schema for `send_message` tool
**Before**: `to_agent` (string), `message`, `priority`
**After**: `to_agents` (array), `content`, `project_id`, `message_type`, `priority`, `from_agent`

```python
# Current schema (lines 195-225):
{
    "name": "send_message",
    "description": "Send a message to one or more agents. Use to_agents=['all'] for broadcast.",
    "inputSchema": {
        "type": "object",
        "properties": {
            "to_agents": {
                "type": "array",
                "items": {"type": "string"},
                "description": "List of target agent IDs/types. Use ['all'] for broadcast to all agents.",
            },
            "content": {"type": "string", "description": "Message content"},
            "project_id": {"type": "string", "description": "Project ID for the message"},
            "message_type": {
                "type": "string",
                "enum": ["direct", "broadcast", "system"],
                "description": "Message type (default: direct)",
                "default": "direct",
            },
            "priority": {
                "type": "string",
                "enum": ["low", "normal", "high"],
                "description": "Message priority (default: normal)",
                "default": "normal",
            },
            "from_agent": {
                "type": "string",
                "description": "Sender agent ID (default: orchestrator)",
            },
        },
        "required": ["to_agents", "content", "project_id"],
    },
},
```

### 2. `src/giljo_mcp/thin_prompt_generator.py`

**CRITICAL WARNING**: This file has TWO prompt generation methods:
- `_build_thin_prompt()` - Appears to be DEPRECATED/OLD
- `_generate_thin_prompt()` - ACTIVE method that generates clipboard prompt

**Change Made**: Added Step 6 to `_generate_thin_prompt()` (line 619):
```python
6. Signal complete: mcp__giljo-mcp__send_message(to_agents=['all'], content='STAGING_COMPLETE: Mission created, N agents spawned: [list names]', project_id='{project_id}', message_type='broadcast')
   → This broadcast enables the Launch Jobs button in UI (REQUIRED)
```

**DIAGNOSIS NEEDED**:
1. Which method is actually called when "Stage Project" is clicked?
2. Is `_build_thin_prompt()` still used anywhere?
3. Did changes break the orchestrator job creation?

### 3. `frontend/src/components/projects/ProjectTabs.vue` (Lines 301-322, 349, 366)

**Change**: Added handler for `message:sent` WebSocket event

```javascript
// Lines 301-322
const handleStagingCompleteMessage = (data) => {
  // Project isolation check
  const projectId = props.project?.id || props.project?.project_id
  if (data.job_id !== projectId && data.project_id !== projectId) {
    return
  }

  // Only process orchestrator broadcasts with STAGING_COMPLETE marker
  const isFromOrchestrator = data.from_agent === 'orchestrator'
  const isBroadcast = data.message_type === 'broadcast'
  const hasStagingMarker = (data.content_preview || data.content || '').includes('STAGING_COMPLETE')

  if ((isFromOrchestrator || isBroadcast) && hasStagingMarker) {
    console.log('[ProjectTabs] STAGING_COMPLETE broadcast received - enabling Launch Jobs')
    store.setStagingComplete(true)
  }
}

// Line 349 (onMounted)
on('message:sent', handleStagingCompleteMessage)

// Line 366 (onBeforeUnmount)
off('message:sent', handleStagingCompleteMessage)
```

### 4. `handovers/0291_staging_complete_broadcast_signal.md`
**Change**: Created handover documentation for the broadcast signal approach

---

## Key Files to Investigate

### Backend - Orchestrator Creation Flow
1. `src/giljo_mcp/thin_prompt_generator.py` - Which method is active?
2. `src/giljo_mcp/tools/tool_accessor.py` - `send_message()` implementation (lines 137-147)
3. `api/endpoints/mcp_http.py` - MCP tool schema definitions
4. `src/giljo_mcp/services/orchestration.py` - Orchestrator spawning logic

### Frontend - WebSocket Event Handling
1. `frontend/src/components/projects/ProjectTabs.vue` - Event handlers
2. `frontend/src/components/projects/JobsTab.vue` - Message count display
3. `frontend/src/stores/websocket.js` - WebSocket event routing
4. `frontend/src/stores/projectTabs.js` - `stagingComplete` state

---

## Diagnostic Steps for Next Agent

### Step 1: Verify Orchestrator Spawning
```bash
# Check if orchestrator job is created in database after "Stage Project"
PGPASSWORD=$DB_PASSWORD /f/PostgreSQL/bin/psql.exe -U postgres -d giljo_mcp -c "SELECT id, agent_type, status, created_at FROM mcp_agent_jobs ORDER BY created_at DESC LIMIT 5;"
```

### Step 2: Trace the Prompt Generation
```bash
# Find which method is called
grep -rn "_build_thin_prompt\|_generate_thin_prompt" src/giljo_mcp/
grep -rn "_build_thin_prompt\|_generate_thin_prompt" api/
```

### Step 3: Check WebSocket Events
- Open browser console
- Click "Stage Project"
- Look for:
  - `orchestrator:instructions_fetched` event
  - `message:sent` event with `STAGING_COMPLETE`
  - Any error messages

### Step 4: Verify Message Counts
```bash
# Check if messages exist in database
PGPASSWORD=$DB_PASSWORD /f/PostgreSQL/bin/psql.exe -U postgres -d giljo_mcp -c "SELECT id, from_agent, to_agents, content, message_type, created_at FROM messages ORDER BY created_at DESC LIMIT 10;"
```

---

## Git Status (Current)

```
On branch master
Your branch is ahead of 'origin/master' by 4 commits.

Changes not staged for commit:
  modified:   api/endpoints/mcp_http.py
  modified:   frontend/src/components/projects/ProjectTabs.vue
  modified:   handovers/dashboard.jpg
  modified:   src/giljo_mcp/thin_prompt_generator.py

Untracked files:
  handovers/0291_staging_complete_broadcast_signal.md
  handovers/no_launch_button.jpg
```

---

## Original User Request

User wanted a simplified approach where:
1. Orchestrator sends `STAGING_COMPLETE` broadcast message when staging finishes
2. This message appears in JobsTab dashboard as "Messages Sent" from orchestrator
3. Frontend listens for this message and enables "Launch Jobs" button
4. Message counts should update in real-time in the dashboard

---

## Related Handovers

- **0290**: WebSocket payload normalization (nested vs flat payloads)
- **0289**: Message routing architecture fix
- **0287**: Staging complete detection

---

## Recommended Fix Approach

1. **FIRST**: Diagnose why orchestrator is not spawning (this is blocking everything else)
2. **SECOND**: Verify the prompt generation method being used
3. **THIRD**: Test message sending with correct MCP schema
4. **FOURTH**: Verify WebSocket events reach frontend handlers
5. **FIFTH**: Fix message count updates in JobsTab

---

## Commands for Testing

```bash
# Restart backend
cd /f/GiljoAI_MCP && python startup.py

# Watch backend logs for errors
# (in separate terminal)

# Frontend dev server (already running)
cd /f/GiljoAI_MCP/frontend && npm run dev

# Database queries
PGPASSWORD=$DB_PASSWORD /f/PostgreSQL/bin/psql.exe -U postgres -d giljo_mcp -c "\dt"
```

---

## Contact/Context

This handover was created due to context window limits. The previous agent made changes attempting to fix WebSocket UI updates but introduced regressions. The next agent should:

1. Start with diagnosis before making any fixes
2. Understand the full flow before modifying code
3. Test each fix incrementally
4. Be careful with `thin_prompt_generator.py` - understand which method is active
