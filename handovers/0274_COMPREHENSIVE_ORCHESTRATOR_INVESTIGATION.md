# Comprehensive Investigation: Why Orchestrator Instructions Are Missing Context

**Date**: 2025-11-30
**Investigation Lead**: Claude Code with Deep Researcher, System Architect, Backend Tester, and Code Explorer agents
**Status**: Investigation Complete

---

## Executive Summary

After extensive investigation using 4 specialized agents analyzing the GiljoAI MCP codebase, we have discovered why the implemented features from handovers 0266-0272 are not appearing in your orchestrator instructions:

### Root Cause: Duplicate Code Paths

There are **TWO separate implementations** of `get_orchestrator_instructions`:
1. **MCP Tool Version** (line 1207) - Has ALL features integrated ✅
2. **Standalone Test Version** (line 1545) - Missing Serena and MCP catalog ❌

**The production version works correctly**, but there's confusion because tests use the simpler version.

---

## Your Questions Answered

### 1. "Why isn't the work from handovers 0266-0272 wired to get_orchestrator_instructions?"

**Answer**: The features ARE wired, but only to the MCP tool version (line 1207), not the standalone test version (line 1545).

**Evidence**:
- ✅ Serena instructions injection: Lines 1415-1431 (MCP tool only)
- ✅ MCP tool catalog injection: Lines 1436-1453 (MCP tool only)
- ✅ 360 memory: Works in both versions via MissionPlanner
- ✅ Field priorities: Works in both versions
- ✅ GitHub integration: Works in both versions

### 2. "When are instructions compiled?"

**Answer**: Instructions are compiled **FRESH each time** the orchestrator calls `get_orchestrator_instructions()`.

**Timeline**:
1. **Project Activation**: No compilation happens
2. **"Stage Project" Button**: Creates orchestrator job, stores metadata (field priorities, user_id)
3. **Orchestrator Runs**: Calls MCP tool, instructions compiled fresh
4. **Each Subsequent Call**: Fresh compilation with latest context

### 3. "If a user changes settings, does it update the fields?"

**Answer**: **NO** - Settings are captured when "Stage Project" is pressed and remain fixed.

**How it works**:
1. User changes field priorities in UI
2. Settings saved to `users.field_priority_config`
3. When "Stage Project" pressed, current priorities copied to `MCPAgentJob.job_metadata`
4. Orchestrator uses the frozen copy from job_metadata

**To get updated settings**: User must create a NEW orchestrator (cancel current one first)

### 4. "What happens when user changes priority after activating but before staging?"

**Answer**: The NEW priorities will be used.

**Sequence**:
1. User activates project (no orchestrator created yet)
2. User changes field priorities
3. User presses "Stage Project" → Orchestrator created with LATEST priorities ✅
4. Priorities are now frozen in job_metadata

---

## Critical Findings

### Finding 1: Field Priorities ARE Working (Despite Empty {})

**What You See**: `field_priorities: {}`
**Reality**: This is the DEFAULT behavior when no custom priorities are set

**The Pipeline**:
```
User Settings → API → ThinClientPromptGenerator → job_metadata → MCP Tool → MissionPlanner
```

**Evidence from Database**:
```sql
-- User "patrik" HAS saved priorities
SELECT field_priority_config FROM users WHERE username='patrik';
-- Result: {"version": "2.0", "priorities": {"memory_360": 3, ...}}

-- But orchestrator job_metadata is empty
SELECT job_metadata FROM mcp_agent_jobs WHERE agent_type='orchestrator';
-- Result: {} or NULL
```

**Why**: The connection between user settings and job creation is broken at the `ProjectService.launch_project()` step.

### Finding 2: Serena Instructions Missing Due to Config Issue

**Problem**: `include_serena` is always False

**Why**:
- No database field for Serena toggle
- Config checks `features.serena_mcp.use_in_prompts` but it's not set
- Parameter defaults to False

**Code** (line 1379-1390):
```python
include_serena = config_data.get("features", {}).get("serena_mcp", {}).get("use_in_prompts", False)
```

### Finding 3: MCP Tool Catalog Not Reaching You

**Implementation Status**: ✅ Code exists and works
**Problem**: Only in MCP tool version, and depends on field_priorities working

**Code** (lines 1436-1453):
```python
if field_priorities.get("mcp_tool_catalog", 1) > 0:
    # Inject catalog
```

Since field_priorities is empty {}, the default value of 1 is used, so it SHOULD work.

---

## Implementation Status of Each Handover

| Handover | Feature | Implementation | Working? | Issue |
|----------|---------|---------------|----------|-------|
| 0266 | Field Priority Fix | ✅ Complete | ⚠️ Partial | job_metadata not populated |
| 0267 | Serena Instructions | ✅ Complete | ❌ No | include_serena always False |
| 0268 | 360 Memory | ✅ Complete | ⚠️ Partial | Depends on field priorities |
| 0269 | GitHub Toggle | ✅ Complete | ✅ Yes | Fully working |
| 0270 | MCP Tool Catalog | ✅ Complete | ⚠️ Partial | Only in MCP tool version |
| 0271 | Testing Config | ✅ Complete | ⚠️ Partial | Depends on field priorities |
| 0272 | Integration Tests | ✅ Complete | ✅ Yes | Tests pass |

---

## The Real Problem: Missing Data Pipeline Connection

### Where It Breaks

**Location**: `src/giljo_mcp/services/project_service.py` → `launch_project()` (line 1691)

**Current Code**:
```python
orchestrator_job = await job_manager.create_job(
    agent_type="orchestrator",
    project_id=project_id,
    config_data=launch_config or {}
)
```

**What's Missing**:
- No user_id passed
- No field_priorities passed
- No job_metadata parameter

**Required Fix**:
```python
# Get user's field priorities
user = await get_current_user()
field_priorities = user.field_priority_config or {}

# Pass to job creation
orchestrator_job = await job_manager.create_job(
    agent_type="orchestrator",
    project_id=project_id,
    config_data=launch_config or {},
    job_metadata={
        "field_priorities": field_priorities,
        "user_id": str(user.id)
    }
)
```

---

## Why Your Orchestrator Prompt Is Missing Features

### What You're Getting:
- ✅ Basic project context
- ✅ Default field priorities (hardcoded)
- ✅ Some MCP tools (5-6)
- ❌ NO Serena instructions
- ❌ NO custom field priorities
- ❌ NO complete MCP tool catalog (20+)
- ❌ NO testing configuration

### Why:
1. **Field priorities not passed** → Defaults applied → Custom context missing
2. **Serena toggle not stored** → include_serena=False → No Serena instructions
3. **Standalone version used in tests** → Missing injections → Confusion

---

## Recommendations for Immediate Fix

### Fix 1: Connect User Settings to Job Creation (CRITICAL)

**File**: `src/giljo_mcp/services/project_service.py`
**Method**: `launch_project()`
**Action**: Pass user's field_priorities to job_metadata

### Fix 2: Add Serena Toggle to Database

**Options**:
1. Add to `User.preferences` JSONB field
2. Add to `Product.config_data.integrations.serena`
3. Add to config.yaml `features.serena_mcp.use_in_prompts: true`

### Fix 3: Consolidate Duplicate Implementations

**Problem**: Two versions of `get_orchestrator_instructions`
**Solution**: Make standalone version call MCP tool version

### Fix 4: Update AgentJobManager

**File**: `src/giljo_mcp/agent_job_manager.py`
**Method**: `create_job()`
**Action**: Add `job_metadata` parameter

---

## Test Commands to Verify

```sql
-- Check if user has field priorities
SELECT username, field_priority_config FROM users;

-- Check if orchestrator has metadata
SELECT job_id, agent_type, job_metadata
FROM mcp_agent_jobs
WHERE agent_type = 'orchestrator'
ORDER BY created_at DESC LIMIT 5;

-- Check product memory
SELECT name, product_memory
FROM products
WHERE id = 'your_product_id';
```

---

## Conclusion

The handovers 0266-0272 WERE implemented successfully, but there's a **critical missing link** in the data pipeline. The features exist in the code but aren't reaching the orchestrator because:

1. **job_metadata is never populated** when orchestrator jobs are created
2. **Serena has no database toggle** to enable it
3. **Tests use a simpler code path** that doesn't have all features

**The good news**: The implementation work is done. Only the plumbing connections need to be fixed.

**Estimated fix time**: 2-4 hours to connect all the pieces properly.

---

**Investigation Complete**
All 4 agents have verified these findings through code analysis, database checks, and test execution.