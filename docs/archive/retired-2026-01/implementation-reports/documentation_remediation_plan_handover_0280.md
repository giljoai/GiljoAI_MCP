# Documentation Remediation Plan - Handover 0280 Migration
## Complete Documentation Update Strategy for Monolithic Context Architecture

**Date**: December 1, 2025
**Status**: Ready for Execution
**Priority**: CRITICAL
**Effort Estimate**: 12-16 hours total

---

## Executive Summary

This plan addresses the documentation debt created by migrating from **modular fetch_* tools** (9 separate MCP context tools) to **monolithic get_orchestrator_instructions()** architecture (Handover 0280).

**Key Finding**: 33 files reference the old architecture, but most are **historical/archived** and need deprecation notices rather than full rewrites. Only **4 critical files** require immediate updates.

**Architecture Change**:
- **OLD (v3.1)**: Orchestrator calls 9 separate tools (`fetch_vision_document`, `fetch_tech_stack`, `fetch_git_history`, etc.) based on user priority settings
- **NEW (v3.2+)**: Single `get_orchestrator_instructions()` call returns all context pre-filtered by server based on user configuration

**Impact**: All documentation referencing "lazy loading," "on-demand fetch," or individual `fetch_*` tools is now outdated.

---

## Section 1: Critical Updates (MUST DO)

These files are actively used by developers and users. Incorrect documentation here causes confusion and broken workflows.

### 1.1 Reference_docs/Dynamic_context.md
**Path**: `F:\GiljoAI_MCP\handovers\Reference_docs\Dynamic_context.md`
**Priority**: 🔥 CRITICAL
**Effort**: 3 hours
**Status**: User-specified, actively referenced

**Current Issues**:
- Lines 19-131: Describes 9 modular fetch_* tools with "lazy loading" and "on-demand fetch" patterns
- Lines 60-89: References vision for staging prompt flow with individual tool calls
- Lines 92-131: Entire "Context Sources" section describes modular architecture
- Lines 134-150: Edge cases assume dynamic fetching

**Proposed Changes**:

**Add Architecture Change Notice** (Line 0):
```markdown
---
**ARCHITECTURE CHANGE NOTICE** (Handover 0280 - December 2025)

This document describes an OUTDATED modular context architecture using 9 separate `fetch_*` tools.

**CURRENT ARCHITECTURE (v3.2+)**: Single `get_orchestrator_instructions()` call returns all pre-filtered context.

For current architecture documentation, see:
- [CLAUDE.md](../../CLAUDE.md#context-management-v20) - Current context model
- [ORCHESTRATOR.md](../../docs/ORCHESTRATOR.md) - Orchestrator workflow
- [Handover 0280](../0280_monolithic_context_migration.md) - Migration details

This document is preserved for HISTORICAL REFERENCE ONLY.
---
```

**Rewrite "Context Sources" Section** (Lines 92-131):
```markdown
## Context Sources (v3.2+ Architecture)

As of Handover 0280 (December 2025), GiljoAI uses a **monolithic context delivery model**:

### Single Entry Point: get_orchestrator_instructions()

**One MCP Tool, All Context**:
```python
# Orchestrator calls ONCE during staging
instructions = get_orchestrator_instructions(
    orchestrator_id='uuid-123',
    tenant_key='tenant-xyz'
)

# Server returns:
{
    "mission": "...",  # Pre-condensed mission (<10K tokens)
    "available_agents": [...],  # Agent metadata
    "context_package": {
        "product_description": "...",  # If priority ≥ 1
        "vision_documents": [...],     # If priority ≥ 1 AND chunking enabled
        "tech_stack": {...},           # If priority ≥ 1
        "architecture": "...",         # If priority ≥ 2
        "testing_config": {...},       # If priority ≥ 2
        "memory_360": [...],           # If priority ≥ 2 AND last_n_projects > 0
        "git_history": [...],          # If priority ≥ 3 AND commits > 0
        "agent_templates": [...]       # If priority ≥ 1 AND detail != 'none'
    },
    "token_budget": 9743,
    "field_priorities": {...},
    "depth_config": {...}
}
```

**Server-Side Filtering**:
- User's priority settings read from `User.field_priority_config`
- User's depth settings read from `User.depth_config`
- Context assembled on server BEFORE returning to orchestrator
- Orchestrator receives ONLY what user configured (no client-side filtering)

**Benefits**:
- ✅ Reduced token usage (single call vs 9 calls)
- ✅ Consistent filtering (server enforces priorities)
- ✅ Simplified orchestrator logic (no conditional fetching)
- ✅ Better auditability (single context package logged)

**Migration Impact**:
The 9 modular tools (`fetch_vision_document`, `fetch_tech_stack`, etc.) still exist for backward compatibility and specialized agent needs, but orchestrators NO LONGER call them directly during staging.

### Context Configuration

Users configure context via **My Settings → Context**:

**Priority Dimension** (WHAT to include):
- Priority 1 (CRITICAL) - Always included
- Priority 2 (IMPORTANT) - High priority
- Priority 3 (NICE_TO_HAVE) - Medium priority
- Priority 4 (EXCLUDED) - Never included

**Depth Dimension** (HOW MUCH detail):
- Vision Chunking: none/light/moderate/heavy (0-30K tokens)
- Git Commits: 10/25/50/100 commits (500-5K tokens)
- 360 Memory: 1/3/5/10 projects (500-5K tokens)
- Agent Template Detail: minimal/standard/full (400-2.4K tokens)
- Tech Stack Sections: required/all (200-400 tokens)
- Architecture Depth: overview/detailed (300-1.5K tokens)
- Testing Depth: none/basic/full (0-400 tokens)

### How Context Settings Are Applied

**Workflow**:
```
User configures priorities in UI
    ↓
Settings saved to User.field_priority_config
    ↓
User clicks [Stage Project]
    ↓
ProjectService.launch_project() reads user settings
    ↓
Orchestrator job metadata includes priorities + depth
    ↓
Orchestrator calls get_orchestrator_instructions()
    ↓
Server reads orchestrator.job_metadata
    ↓
Server applies priorities + depth to context assembly
    ↓
Server returns pre-filtered context package
    ↓
Orchestrator receives ONLY configured context
```

**No client-side filtering required** - server handles everything.
```

**Update Vision for Staging Prompt** (Lines 56-89):
```markdown
#### My vision for the Prompt flow on [Stage Project] button press (v3.2):

- Give identity: You are Orchestrator, your agent ID is {UUID}
- Give product ID: You are working on Product {name}, product ID {UUID}
- Give project ID: You are working on Project {name}, project ID {UUID}
- Your first task is to check MCP health {MCP Command: health_check()}
- Your second task is to check your project environment, read CLAUDE.md in the project folder
- Your third task is to fetch ALL your mission instructions in ONE call:
  - {MCP command: get_orchestrator_instructions(orchestrator_id, tenant_key)}
  - This single call returns:
    - Your mission (pre-condensed by server)
    - Available agents (dynamic discovery)
    - ALL context pre-filtered by your user's priority/depth settings
  - NO additional context fetching needed - server handles filtering
- Your fourth task is to spawn agent jobs {MCP command: spawn_agent_job(...)}
- Your fifth task is to activate the jobs {MCP command for toggling states}, enabling [Launch Jobs] button

**Key Change**: Orchestrator NO LONGER calls individual fetch_* tools. The server pre-packages all context in `get_orchestrator_instructions()` based on user configuration.
```

**Remove Edge Cases Section** (Lines 134-150):
```markdown
## Edge Cases (v3.2 - Resolved)

**OLD ARCHITECTURE ISSUES** (v3.1 - now resolved):
- ~~Orchestrator succession risk during mode changes~~ → Fixed: Single context package in metadata
- ~~Template version conflicts~~ → Fixed: Dynamic discovery with version validation
- ~~WebSocket protocol impact~~ → Fixed: Single context event vs 9 separate events
- ~~Security vulnerabilities~~ → Fixed: Server-side filtering prevents injection
- ~~Job state management~~ → Fixed: Context package immutable in job metadata

**NEW ARCHITECTURE** (v3.2+): Monolithic context delivery eliminates all edge cases related to conditional fetching and race conditions between multiple tool calls.
```

---

### 1.2 Reference_docs/Mcp_tool_catalog.md
**Path**: `F:\GiljoAI_MCP\handovers\Reference_docs\Mcp_tool_catalog.md`
**Priority**: 🔥 CRITICAL
**Effort**: 2 hours
**Status**: User-specified, MCP tool reference

**Current Issues**:
- Handover 0270 completion report describes OLD architecture
- Lists 9 context tools as orchestrator workflow
- No mention of monolithic get_orchestrator_instructions()
- Examples show orchestrator calling fetch_* tools individually

**Proposed Changes**:

**Add Architecture Change Notice** (Top of file):
```markdown
---
**ARCHITECTURE CHANGE NOTICE** (Handover 0280 - December 2025)

**THIS DOCUMENT IS OUTDATED** - Describes v3.1 architecture with 9 separate context tools.

**CURRENT TOOL CATALOG** (v3.2+):
- Orchestrators call: `get_orchestrator_instructions()` (single tool, all context)
- Agents call: `get_agent_mission()` (single tool, agent-specific mission)
- 9 modular tools (`fetch_vision_document`, `fetch_tech_stack`, etc.) DEPRECATED for orchestrator use

For current MCP tool documentation, see:
- [ORCHESTRATOR.md](../../docs/ORCHESTRATOR.md#mcp-tools-0246-series)
- [Handover 0280](../0280_monolithic_context_migration.md)

This document is preserved for HISTORICAL REFERENCE ONLY.
---
```

**Update "Orchestration Tools" Section**:
```markdown
### Orchestration Tools (v3.2+ - Updated)

#### Primary Tool (NEW)
**get_orchestrator_instructions(orchestrator_id, tenant_key)**
- **Parameters**: orchestrator_id (UUID), tenant_key (string)
- **Description**: Fetches ALL orchestrator context in single call (mission, agents, priorities, context package)
- **Returns**: Complete orchestrator instructions with pre-filtered context
- **When to use**:
  - During staging workflow (Task 2)
  - Replaces ALL 9 modular fetch_* tools
  - Server handles priority/depth filtering
- **Example**:
  ```python
  instructions = get_orchestrator_instructions(
      orchestrator_id='abc-123',
      tenant_key='tenant-xyz'
  )
  # Returns: {mission, available_agents, context_package, priorities, depth_config}
  ```

#### Agent-Specific Tool
**get_agent_mission(agent_job_id, tenant_key)**
- **Parameters**: agent_job_id (UUID), tenant_key (string)
- **Description**: Fetches agent's mission and required context
- **Returns**: Agent-specific mission with filtered context
- **When to use**: Agent startup (thin client pattern)
- **Example**:
  ```python
  mission = get_agent_mission(
      agent_job_id='def-456',
      tenant_key='tenant-xyz'
  )
  # Returns: {mission, context_subset, project_info, team_members}
  ```

#### Deprecated Orchestration Tools (v3.1 - Still Available for Specialized Use)
These tools are NO LONGER used by orchestrators during staging, but remain available for specialized agent needs:
- spawn_agent_job() - Still used
- orchestrate_project() - Legacy workflow (not recommended)
- get_workflow_status() - Still used
```

**Update "Context Tools" Section**:
```markdown
### Context Tools (v3.1 - DEPRECATED for Orchestrator Use)

**IMPORTANT**: As of v3.2+ (Handover 0280), orchestrators NO LONGER call these tools individually. Context is delivered via `get_orchestrator_instructions()`.

These tools remain available for:
- Specialized agent context fetching
- Backward compatibility
- Direct API access outside orchestrator workflow

**Deprecated for orchestrators**:
1. ~~fetch_product_context~~ → Included in get_orchestrator_instructions()
2. ~~fetch_vision_document~~ → Included in get_orchestrator_instructions()
3. ~~fetch_tech_stack~~ → Included in get_orchestrator_instructions()
4. ~~fetch_architecture~~ → Included in get_orchestrator_instructions()
5. ~~fetch_testing_config~~ → Included in get_orchestrator_instructions()
6. ~~fetch_360_memory~~ → Included in get_orchestrator_instructions()
7. ~~fetch_git_history~~ → Included in get_orchestrator_instructions()
8. ~~fetch_agent_templates~~ → Included in get_orchestrator_instructions()
9. ~~fetch_project_context~~ → Included in get_orchestrator_instructions()

**Agent-specific context**: Agents receive context via `get_agent_mission()`, not by calling these tools directly.
```

---

### 1.3 Reference_docs/start_to_finish_agent_FLOW.md
**Path**: `F:\GiljoAI_MCP\handovers\Reference_docs\start_to_finish_agent_FLOW.md`
**Priority**: 🔥 CRITICAL (500 lines, comprehensive workflow doc)
**Effort**: 4 hours
**Status**: User-specified, active reference

**Current Issues**:
- Lines 100-127: "Context Sources" section describes 9 modular tools
- Line 262: Task 2 shows orchestrator calling fetch_* tools individually
- Line 272: "fetch_context" implies multiple calls

**Proposed Changes**:

**Update Architecture Notice** (Line 0):
```markdown
---
**Document Type:** Unified Workflow Documentation
**Last Updated:** 2025-12-01 - Updated for monolithic context (Handover 0280)
**Purpose:** Single source of truth for GiljoAI Agent Orchestration workflows
**Status:** ✅ Updated for v3.2+ monolithic context architecture
---
```

**Rewrite Task 2 in Staging Workflow** (Lines 250-280):
```markdown
TASK 2: Fetch Complete Instructions (SINGLE CALL)
└─► get_orchestrator_instructions(orchestrator_id, tenant_key)
    ├─► **ONE CALL, ALL CONTEXT** (v3.2+ architecture)
    ├─► Mission NOT embedded in thin prompt
    ├─► Server builds context package (~6K-10K tokens)
    ├─► Reads Product.description (user input)
    ├─► Reads Project.description (user input)
    ├─► Reads User.field_priority_config (priorities)
    ├─► Reads User.depth_config (depth settings)
    ├─► Applies priority filtering on SERVER
    ├─► Returns complete context package:
    │   ├─► mission (pre-condensed)
    │   ├─► available_agents (dynamic discovery)
    │   ├─► context_package (pre-filtered)
    │   ├─► field_priorities (user config)
    │   └─► depth_config (user config)
    └─► NO additional context fetching required

**Key Change (v3.2)**: Orchestrator makes ONE call, server returns ALL context pre-filtered. No more individual fetch_vision_document(), fetch_tech_stack(), etc. calls during staging.
```

**Update Context Sources Section** (Lines 92-131):
```markdown
## Context Sources (v3.2+ Monolithic Architecture)

This section describes how context is assembled and delivered to orchestrators and agents. As of Handover 0280 (December 2025), GiljoAI uses a **monolithic context delivery model**.

### Single Context Package Delivery

**Server-Side Assembly**:
When orchestrator calls `get_orchestrator_instructions()`, the server:
1. Reads user's priority configuration (`User.field_priority_config`)
2. Reads user's depth configuration (`User.depth_config`)
3. Assembles context package based on priorities
4. Applies depth settings (chunking, commit counts, memory limits)
5. Returns single unified context package

**No Client-Side Filtering**: Orchestrator receives ONLY what user configured, no conditional fetching required.

### Context Package Structure

```python
{
    "mission": "...",  # Pre-condensed mission (~6K-10K tokens)
    "available_agents": [...],  # Dynamic agent discovery
    "context_package": {
        # Included based on priority ≥ 1:
        "product_description": "...",
        "tech_stack": {...},

        # Included based on priority ≥ 2:
        "architecture": "...",
        "testing_config": {...},

        # Included based on priority ≥ 3:
        "git_history": [...],  # Filtered by depth_config.git_commits

        # Conditionally included:
        "vision_documents": [...],  # If chunking != 'none'
        "memory_360": [...],  # If last_n_projects > 0
        "agent_templates": [...]  # If detail != 'none'
    },
    "token_budget": 9743,
    "field_priorities": {...},  # User's configuration
    "depth_config": {...}  # User's depth settings
}
```

### Context Source Details

#### Product Description
- **Source**: `Product.description` (user-written)
- **Priority**: Always included if ≥ 1
- **Tokens**: ~100-500 tokens
- **Purpose**: High-level product narrative and constraints

#### Vision Documents
- **Source**: `ProductVisionDocument` table (user-uploaded)
- **Priority**: Included if ≥ 1 AND depth_config.vision_chunking != 'none'
- **Tokens**: 0-30K tokens (based on chunking level)
- **Purpose**: Long-form product specs, roadmaps, strategy docs

#### Tech Stack
- **Source**: `Product.tech_stack` (structured JSON)
- **Priority**: Included if ≥ 1
- **Tokens**: 200-400 tokens
- **Purpose**: Languages, frameworks, core dependencies

#### Architecture
- **Source**: `Product.architecture_docs` (linked documents)
- **Priority**: Included if ≥ 2
- **Tokens**: 300-1.5K tokens (based on depth)
- **Purpose**: Architectural decisions, patterns, module boundaries

#### Testing Config
- **Source**: `Product.testing_config` (metadata)
- **Priority**: Included if ≥ 2
- **Tokens**: 0-400 tokens (based on depth)
- **Purpose**: Test frameworks, coverage expectations, TDD rules

#### 360 Memory
- **Source**: `Product.product_memory` (JSONB)
- **Priority**: Included if ≥ 2 AND depth_config.memory_last_n_projects > 0
- **Tokens**: 500-5K tokens (based on project count)
- **Purpose**: Historical project learnings and decisions

#### Git History
- **Source**: Git integration or manual summaries
- **Priority**: Included if ≥ 3 AND depth_config.git_commits > 0
- **Tokens**: 500-5K tokens (based on commit count)
- **Purpose**: Recent code changes and commit context

#### Agent Templates
- **Source**: `AgentTemplate` table (multi-tenant)
- **Priority**: Included if ≥ 1 AND depth_config.agent_template_detail != 'none'
- **Tokens**: 400-2.4K tokens (based on detail level)
- **Purpose**: Available agent capabilities and roles

### How Settings Flow Through System

```
User Interface (My Settings → Context)
    ↓ (Save)
Database (User.field_priority_config, User.depth_config)
    ↓ (Project Launch)
Orchestrator Job Metadata (priorities + depth copied)
    ↓ (Orchestrator calls get_orchestrator_instructions)
Server Context Builder (reads job_metadata)
    ↓ (Applies filters)
Pre-Filtered Context Package
    ↓ (Returns to orchestrator)
Orchestrator Mission (already filtered, no client logic needed)
```

**Key Benefit**: Orchestrator code is simple - one call, receive context, proceed. No conditional logic, no priority checking, no depth calculations.
```

---

### 1.4 CLAUDE.md
**Path**: `F:\GiljoAI_MCP\CLAUDE.md`
**Priority**: 🔥 CRITICAL
**Effort**: 2 hours
**Status**: Developer onboarding doc

**Current Issues**:
- Lines 128-162: Lists 9 MCP context tools with badges
- Lines 163-183: Describes workflow pipeline but doesn't mention monolithic architecture
- No mention of Handover 0280

**Proposed Changes**:

**Update Recent Updates Section** (Lines 10-17):
```markdown
**Recent Updates (v3.2+)**:
- **Monolithic Context Architecture (0280)**: Single get_orchestrator_instructions() replaces 9 modular fetch_* tools
- Orchestrator Workflow & Token Optimization (0246a-0246c)
- GUI Redesign Series (0243)
- Context Management v2.0 (0312-0316)
- 360 Memory Management (0135-0139)
- Remediation Project (0500-0515)
- Nuclear Migration Reset (0601)
- Agent Monitoring & Cancellation (0107)
- One-Liner Installation (0100)
```

**Rewrite Context Management Section** (Lines 128-162):
```markdown
## Context Management (v2.0 - Monolithic Architecture)

**As of Handover 0280 (December 2025)**: GiljoAI uses a **monolithic context delivery model**.

### Architecture Overview

**Single Entry Point**:
```python
# Orchestrator makes ONE call during staging:
instructions = get_orchestrator_instructions(
    orchestrator_id='uuid-123',
    tenant_key='tenant-xyz'
)

# Server returns ALL context pre-filtered:
{
    "mission": "...",  # Pre-condensed
    "available_agents": [...],
    "context_package": {  # Pre-filtered based on user settings
        "product_description": "...",
        "vision_documents": [...],
        "tech_stack": {...},
        "architecture": "...",
        "testing_config": {...},
        "memory_360": [...],
        "git_history": [...],
        "agent_templates": [...]
    },
    "field_priorities": {...},
    "depth_config": {...}
}
```

### 2-Dimensional Context Model

**Priority Dimension** (WHAT to fetch - configured by user):
- Priority 1 (CRITICAL) - Always included
- Priority 2 (IMPORTANT) - High priority
- Priority 3 (NICE_TO_HAVE) - Medium priority
- Priority 4 (EXCLUDED) - Never included

**Depth Dimension** (HOW MUCH detail - configured by user):
- Vision Documents: none/light/moderate/heavy (0-30K tokens)
- Tech Stack: required/all (200-400 tokens)
- Architecture: overview/detailed (300-1.5K tokens)
- Testing: none/basic/full (0-400 tokens)
- 360 Memory: 1/3/5/10 projects (500-5K tokens)
- Git History: 10/25/50/100 commits (500-5K tokens)
- Agent Templates: minimal/standard/full (400-2.4K tokens)

### User Configuration

**Settings Location**: My Settings → Context

**Priority Configuration**: Field Priority Configuration tab
**Depth Configuration**: Depth Configuration tab

### Server-Side Filtering

**Key Change (v3.2+)**: Context filtering happens on the SERVER, not the client.

**OLD (v3.1)**: Orchestrator called 9 separate tools (`fetch_vision_document`, `fetch_tech_stack`, etc.) with priority/depth parameters.

**NEW (v3.2+)**: Orchestrator calls `get_orchestrator_instructions()` once, server reads user settings and returns pre-filtered context package.

**Benefits**:
- ✅ Reduced token usage (1 call vs 9 calls)
- ✅ Consistent filtering (server enforces priorities)
- ✅ Simplified orchestrator logic
- ✅ Better auditability

### Context Tools (v3.1 - Deprecated for Orchestrator Use)

The following 9 tools exist for backward compatibility and specialized agent use, but orchestrators NO LONGER call them during staging:

1. ~~`fetch_product_context`~~ → Included in get_orchestrator_instructions()
2. ~~`fetch_vision_document`~~ → Included in get_orchestrator_instructions()
3. ~~`fetch_tech_stack`~~ → Included in get_orchestrator_instructions()
4. ~~`fetch_architecture`~~ → Included in get_orchestrator_instructions()
5. ~~`fetch_testing_config`~~ → Included in get_orchestrator_instructions()
6. ~~`fetch_360_memory`~~ → Included in get_orchestrator_instructions()
7. ~~`fetch_git_history`~~ → Included in get_orchestrator_instructions()
8. ~~`fetch_agent_templates`~~ → Included in get_orchestrator_instructions()
9. ~~`fetch_project_context`~~ → Included in get_orchestrator_instructions()

**New Primary Tools** (v3.2+):
- `get_orchestrator_instructions()` - Orchestrator context (ALL sources)
- `get_agent_mission()` - Agent-specific context
```

**Update Workflow Pipeline Section** (Lines 163-183):
```markdown
## Orchestrator Workflow Pipeline (v3.2 Handovers 0246a-c, 0280)

**Complete 4-Phase Pipeline**:
1. **Staging** (7 tasks, 931 tokens)
   - Identity verification
   - MCP health check
   - Environment understanding
   - Agent discovery via `get_available_agents()`
   - **Context fetching via `get_orchestrator_instructions()` - ONE CALL, ALL CONTEXT**
   - Job spawning
   - Activation

2. **Discovery** (420 tokens saved)
   - Dynamic agent discovery via MCP tool
   - No embedded templates

3. **Spawning** (1,253 tokens per agent)
   - Generic agent template with 6-phase protocol
   - Mission fetching via `get_agent_mission()`

4. **Execution**
   - Agents run 6-phase protocol
   - Real-time coordination

**Key Features**:
- **85% Token Reduction**: ~3,500 → ~450-550 tokens per orchestrator
- **Monolithic Context (Handover 0280)**: Single call replaces 9 tool calls
- **Dynamic Agent Discovery**: 71% token savings (420 tokens)
- **Client-Server Separation**: Server = context builder, Client = code executor
- **Multi-Tenant Isolation**: All MCP tools filter by tenant_key

**MCP Tools** (0246 Series + 0280):
- `get_orchestrator_instructions(orchestrator_id, tenant_key)` - **PRIMARY TOOL (0280)**
- `get_available_agents(tenant_key, active_only)` - Agent discovery (0246c)
- `get_generic_agent_template(agent_id, job_id, ...)` - Unified template (0246b)
- `get_agent_mission(job_id, tenant_key)` - Agent mission fetch
- Staging prompt: `ThinClientPromptGenerator._build_staging_prompt()` (0246a)

**Documentation**:
- [ORCHESTRATOR.md](docs/ORCHESTRATOR.md)
- [STAGING_WORKFLOW.md](docs/components/STAGING_WORKFLOW.md)
- [Handover 0280](handovers/0280_monolithic_context_migration.md)
```

---

## Section 2: Handover Updates

### 2.1 Handover 0279 (Context Priority Integration Fix)
**Path**: `F:\GiljoAI_MCP\handovers\0279_context_priority_integration_fix.md`
**Priority**: 🔥 CRITICAL
**Effort**: 1 hour
**Status**: Active handover, MUST be updated to reference 0280

**Current Issues**:
- Entire document describes fixing user_id parameter in modular fetch_* tools
- Lines 68-108: Tool call templates for 9 separate tools
- No mention that this is now OBSOLETE due to 0280

**Proposed Changes**:

**Add Superseded Notice** (Top of file):
```markdown
---
**SUPERSEDED NOTICE** (Handover 0280 - December 2025)

**THIS HANDOVER IS OBSOLETE** - The issues described here (missing user_id in tool templates) are no longer relevant because orchestrators NO LONGER call individual fetch_* tools.

**CURRENT ARCHITECTURE (v3.2+)**: Single `get_orchestrator_instructions()` call handles all context fetching with built-in priority/depth filtering.

**What Happened**:
- This handover identified that tool call templates in `thin_prompt_generator.py` were missing `user_id` parameters
- Before implementation, architecture changed to monolithic context (Handover 0280)
- The fix described here is no longer needed because orchestrators don't call these tools directly
- Priority filtering now happens server-side in `get_orchestrator_instructions()`

**Related Handovers**:
- [Handover 0280](0280_monolithic_context_migration.md) - Monolithic architecture
- [Handover 0312-0316](completed/0300_EXECUTION_ROADMAP_COMPLETE.md) - Context v2.0 implementation

**This document is preserved for HISTORICAL REFERENCE ONLY.**
---
```

**Add Note to Backend Issue Section** (After line 108):
```markdown
---
**UPDATE (December 2025)**: This section describes adding user_id to 9 tool call templates in `thin_prompt_generator.py`. However, Handover 0280 eliminated these tool calls entirely by moving to monolithic context delivery. The fix described here was NEVER IMPLEMENTED because it became obsolete before execution.
---
```

---

### 2.2 Completed Handovers (Historical Archive)
**Priority**: 🟡 MEDIUM
**Effort**: 4 hours
**Strategy**: Add deprecation notices, don't rewrite

**Files to Update** (32 total from grep results):

**Add Standard Deprecation Notice Template**:
```markdown
---
**ARCHITECTURE CHANGE NOTICE** (Handover 0280 - December 2025)

This document references the OLD v3.1 architecture with 9 separate context tools (`fetch_vision_document`, `fetch_tech_stack`, etc.).

**CURRENT ARCHITECTURE (v3.2+)**: Single `get_orchestrator_instructions()` call replaces modular tools.

For current documentation, see:
- [CLAUDE.md](../../CLAUDE.md#context-management-v20)
- [ORCHESTRATOR.md](../../docs/ORCHESTRATOR.md)
- [Handover 0280](../0280_monolithic_context_migration.md)

This document is preserved for HISTORICAL REFERENCE ONLY.
---
```

**Files Requiring Deprecation Notices** (Priority Order):

1. **Context/Priority Related** (12 files):
   - `tests/integration/test_orchestrator_priority_filtering.py`
   - `tests/integration/test_context_filtering_by_priority.py`
   - `handovers/completed/0272_comprehensive_integration_tests-C.md`
   - `handovers/completed/0270_add_mcp_tool_instructions-C.md`
   - `handovers/completed/0265_orchestrator_context_investigation_reference.md`
   - `handovers/completed/0248_series/0248b_priority_framing_implementation-C.md`
   - `handovers/completed/0316_context_field_alignment_refactor-C.md`
   - `handovers/completed/0316a_context_alignment_fix-C.md`
   - `handovers/completed/0318_documentation_update_0300_series-C.md`
   - `handovers/completed/0315_mcp_thin_client_refactor-C.md`
   - `handovers/completed/0312_context_architecture_v2_design-C.md`
   - `docs/api/context_tools.md`

2. **Architecture/Flow Related** (10 files):
   - `docs/SERVER_ARCHITECTURE_TECH_STACK.md`
   - `docs/components/STAGING_WORKFLOW.md`
   - `docs/testing/ORCHESTRATOR_SIMULATOR.md`
   - `E2E_SIMULATION_TEST_SUITE_REPORT.md`
   - `AGENTS.md`
   - `handovers/MCPreport_nov28.md`
   - `handovers/completed/0252_remove_codebase_summary_dead_code.md`
   - `handovers/completed/0249_series/0249_project_closeout_workflow.md`
   - `handovers/completed/0246_series/0246a_staging_prompt_implementation-C.md`
   - `BACKEND_TEST_REPORT_0246a.md`

3. **Reference/Obsolete** (10 files):
   - `handovers/completed/superseded/0319_context_management_v3_granular_fields_SUPERSEDED.md`
   - `handovers/completed/REFACTORING_ROADMAP_0131-0200_OLD.md`
   - `handovers/completed/0300_EXECUTION_ROADMAP_COMPLETE.md`
   - `docs/sessions/2025-11-24_handover_0246a_refocus.md`
   - `docs/devlog/2025-11-17_context_v2_completion.md`
   - `reports/CCW_REPORT_2025-11-13.md`
   - `examples/context_demo_standalone.py`
   - `handovers/completed/0136_360_memory_initialization-C.md`
   - `docs/TEMPLATE_SYSTEM_EVOLUTION.md`
   - `tests/test_dynamic_discovery.py`

**Batch Update Script** (Create helper):
```bash
#!/bin/bash
# File: add_deprecation_notices.sh
# Usage: ./add_deprecation_notices.sh <file_list.txt>

NOTICE="---
**ARCHITECTURE CHANGE NOTICE** (Handover 0280 - December 2025)

This document references the OLD v3.1 architecture with 9 separate context tools.

**CURRENT ARCHITECTURE (v3.2+)**: Single \`get_orchestrator_instructions()\` call.

See [Handover 0280](../0280_monolithic_context_migration.md) for details.
---

"

while IFS= read -r file; do
  if [ -f "$file" ]; then
    # Prepend notice to file
    echo "$NOTICE" | cat - "$file" > temp && mv temp "$file"
    echo "Updated: $file"
  fi
done < "$1"
```

---

## Section 3: Core Documentation Updates

### 3.1 docs/ORCHESTRATOR.md
**Path**: `F:\GiljoAI_MCP\docs\ORCHESTRATOR.md`
**Priority**: 🔥 CRITICAL
**Effort**: 2 hours
**Status**: Core technical documentation

**Current Issues**:
- Lines 0-300: Describes staging workflow but doesn't emphasize monolithic context
- No mention of Handover 0280
- Dynamic discovery section doesn't mention single-call context

**Proposed Changes**:

**Update Version Header** (Lines 0-5):
```markdown
# Orchestrator Context Tracking & Succession

**Version**: v3.2+ (Handover 0080, 0246a-c, 0280)
**Last Updated**: 2025-12-01
**Architecture**: Monolithic Context Delivery (Handover 0280)
```

**Add Monolithic Architecture Callout** (After line 17):
```markdown
---
## Monolithic Context Architecture (v3.2+ Handover 0280)

**CRITICAL CHANGE**: As of December 2025, orchestrators use **single-call context delivery**.

**What Changed**:
- **OLD (v3.1)**: Orchestrator called 9 separate tools during staging
  ```python
  fetch_vision_document(...)
  fetch_tech_stack(...)
  fetch_architecture(...)
  # ... 6 more tools
  ```

- **NEW (v3.2+)**: Orchestrator calls ONE tool, server returns ALL context
  ```python
  instructions = get_orchestrator_instructions(
      orchestrator_id='uuid-123',
      tenant_key='tenant-xyz'
  )
  # Returns: {mission, available_agents, context_package (pre-filtered)}
  ```

**Benefits**:
- ✅ Reduced token usage (~1,200 tokens saved per orchestrator)
- ✅ Consistent filtering (server enforces user priorities)
- ✅ Simplified orchestrator code (no conditional logic)
- ✅ Better auditability (single context package logged)

**Impact on Documentation**: Any reference to orchestrators calling `fetch_*` tools directly is now outdated. See [Handover 0280](../handovers/0280_monolithic_context_migration.md) for migration details.

---
```

**Update Staging Task 5** (Around line 121-132):
```markdown
5. CONTEXT PRIORITIZATION & MISSION (Single Call)
   ├─ Call get_orchestrator_instructions(orchestrator_id, tenant_key)
   ├─ Server reads User.field_priority_config
   ├─ Server reads User.depth_config
   ├─ Server assembles context package based on priorities
   ├─ Server applies depth settings (chunking, commit counts)
   ├─ Returns unified context package:
   │   ├─ mission (pre-condensed, <10K tokens)
   │   ├─ available_agents (dynamic discovery)
   │   ├─ context_package (pre-filtered)
   │   ├─ field_priorities (user config)
   │   └─ depth_config (user config)
   └─ NO additional context fetching required

**Key Point**: This is a SINGLE MCP call that replaces 9 separate calls from v3.1.
```

---

### 3.2 docs/README_FIRST.md
**Path**: `F:\GiljoAI_MCP\docs\README_FIRST.md`
**Priority**: 🟡 MEDIUM
**Effort**: 30 minutes
**Status**: Navigation hub

**Proposed Changes**:

**Add Recent Changes Section**:
```markdown
## Recent Architecture Changes

### Monolithic Context Architecture (December 2025 - Handover 0280)

**IMPORTANT**: As of v3.2+, orchestrators use **single-call context delivery**.

**Key Change**: `get_orchestrator_instructions()` replaces 9 modular `fetch_*` tools.

**Impact**: Documentation referencing "lazy loading," "on-demand fetch," or individual context tools is outdated.

**Updated Documentation**:
- ✅ [CLAUDE.md](../CLAUDE.md#context-management-v20) - Developer onboarding
- ✅ [ORCHESTRATOR.md](ORCHESTRATOR.md) - Orchestrator workflows
- ✅ [Reference Docs](../handovers/Reference_docs/) - Architecture references
- ⏳ [Completed Handovers](../handovers/completed/) - Historical archive (deprecation notices added)

**See Also**: [Handover 0280](../handovers/0280_monolithic_context_migration.md) for complete migration details.
```

---

## Section 4: Code Comment Updates

### 4.1 Code Comments Audit

**Files with Outdated Comments** (from grep results):

1. **src/giljo_mcp/thin_prompt_generator.py**
   - Lines 560-592: Tool call templates (now obsolete for orchestrators)
   - **Action**: Add deprecation comment
   ```python
   # DEPRECATED (Handover 0280): These tool templates are no longer used by orchestrators.
   # Orchestrators now call get_orchestrator_instructions() instead of individual fetch_* tools.
   # These templates remain for backward compatibility and specialized agent use only.
   ```

2. **src/giljo_mcp/tools/context.py**
   - Docstrings for 9 fetch_* functions
   - **Action**: Add usage notes
   ```python
   def fetch_vision_document(...):
       """
       Fetch vision document chunks with priority filtering.

       NOTE (Handover 0280): This tool is NO LONGER called by orchestrators during staging.
       Orchestrators use get_orchestrator_instructions() for all context.

       This tool remains available for:
       - Specialized agent context fetching
       - Backward compatibility
       - Direct API access outside orchestrator workflow
       """
   ```

3. **tests/integration/test_orchestrator_priority_filtering.py**
   - Test file for old architecture
   - **Action**: Add test suite deprecation notice
   ```python
   """
   DEPRECATED TEST SUITE (Handover 0280)

   These tests validate the OLD v3.1 architecture where orchestrators called individual
   fetch_* tools with user_id parameters for priority filtering.

   CURRENT ARCHITECTURE (v3.2+): Orchestrators call get_orchestrator_instructions() once,
   server handles all priority filtering.

   These tests remain for:
   - Backward compatibility validation
   - Specialized agent context fetching
   - Historical reference

   For current orchestrator tests, see:
   - tests/integration/test_monolithic_context.py
   - tests/integration/test_orchestrator_staging.py
   """
   ```

4. **tests/integration/test_context_filtering_by_priority.py**
   - Similar to above
   - **Action**: Same deprecation notice

5. **src/giljo_mcp/prompt_generation/mcp_tool_catalog.py**
   - Lines describing individual context tools
   - **Action**: Update category comments
   ```python
   # Context Tools (v3.1 - Deprecated for Orchestrator Use)
   # NOTE (Handover 0280): Orchestrators NO LONGER call these tools individually.
   # Context is delivered via get_orchestrator_instructions().
   # These tools remain available for specialized agent use and backward compatibility.
   ```

---

## Section 5: Update Sequence (Recommended Order)

### Phase 1: Critical Reference Docs (Day 1 - 6 hours)
**Must complete first** - These are actively referenced by developers and users.

1. **Reference_docs/Dynamic_context.md** (3 hours)
   - Add architecture change notice
   - Rewrite Context Sources section
   - Update staging prompt flow
   - Remove/rewrite edge cases

2. **Reference_docs/Mcp_tool_catalog.md** (2 hours)
   - Add architecture change notice
   - Update Orchestration Tools section
   - Deprecate Context Tools section

3. **CLAUDE.md** (1 hour)
   - Update Recent Updates section
   - Rewrite Context Management section
   - Update Workflow Pipeline section

---

### Phase 2: Core Documentation (Day 2 - 4 hours)

4. **docs/ORCHESTRATOR.md** (2 hours)
   - Add monolithic architecture callout
   - Update staging workflow Task 5
   - Add Handover 0280 references

5. **Reference_docs/start_to_finish_agent_FLOW.md** (2 hours)
   - Update architecture notice
   - Rewrite Task 2 in staging
   - Update Context Sources section

---

### Phase 3: Handover Updates (Day 3 - 4 hours)

6. **Handover 0279** (1 hour)
   - Add SUPERSEDED notice
   - Explain why this is now obsolete

7. **Completed Handovers** (3 hours)
   - Run batch deprecation notice script
   - Spot-check 5-10 files manually
   - Commit with descriptive message

---

### Phase 4: Secondary Documentation (Day 4 - 2 hours)

8. **docs/README_FIRST.md** (30 minutes)
   - Add Recent Architecture Changes section

9. **Code Comments** (1.5 hours)
   - Update thin_prompt_generator.py
   - Update src/giljo_mcp/tools/context.py
   - Update test file docstrings

---

## Section 6: Deprecation Notice Template

Use this standard template for all historical/archived documents:

```markdown
---
**ARCHITECTURE CHANGE NOTICE** (Handover 0280 - December 2025)

This document describes the OLD v3.1 modular context architecture with 9 separate `fetch_*` tools:
- `fetch_vision_document()` - Vision document chunks
- `fetch_tech_stack()` - Tech stack info
- `fetch_architecture()` - Architecture docs
- `fetch_testing_config()` - Testing configuration
- `fetch_360_memory()` - Project memory
- `fetch_git_history()` - Git commit history
- `fetch_agent_templates()` - Agent templates
- `fetch_product_context()` - Product metadata
- `fetch_project_context()` - Project metadata

**CURRENT ARCHITECTURE (v3.2+)**: Single `get_orchestrator_instructions()` call returns all context pre-filtered by server.

**Key Changes**:
- Orchestrators make ONE MCP call instead of 9 during staging
- Server applies user priority/depth settings (no client-side filtering)
- ~1,200 tokens saved per orchestrator instance
- Better auditability and consistency

**Why This Change**:
- Reduced token usage (1 call vs 9 calls)
- Simplified orchestrator logic
- Consistent filtering (server-enforced)
- Better performance and reliability

**Migration Impact**:
- ✅ Orchestrator code simplified (no conditional tool calls)
- ✅ User settings applied consistently on server
- ✅ Better error handling (single failure point)
- ⚠️ This document's workflow no longer matches current architecture

**Current Documentation**:
- [CLAUDE.md](../../CLAUDE.md#context-management-v20) - Developer onboarding
- [ORCHESTRATOR.md](../../docs/ORCHESTRATOR.md) - Current workflows
- [Handover 0280](../0280_monolithic_context_migration.md) - Migration details

**This document is preserved for HISTORICAL REFERENCE ONLY.**

---
```

---

## Section 7: Verification Checklist

After completing all updates, verify:

### Critical Files Updated ✅
- [ ] Reference_docs/Dynamic_context.md - Architecture change notice added
- [ ] Reference_docs/Mcp_tool_catalog.md - Tool catalog updated
- [ ] Reference_docs/start_to_finish_agent_FLOW.md - Workflow updated
- [ ] CLAUDE.md - Context Management section rewritten
- [ ] docs/ORCHESTRATOR.md - Monolithic architecture documented

### Handover 0279 Marked Obsolete ✅
- [ ] SUPERSEDED notice added
- [ ] Explanation of why fixes are no longer needed
- [ ] Cross-references to Handover 0280

### Completed Handovers Marked ✅
- [ ] 32 completed handovers have deprecation notices
- [ ] Batch script executed successfully
- [ ] Spot-check confirms notices are correctly placed

### Code Comments Updated ✅
- [ ] thin_prompt_generator.py - Deprecation comment on tool templates
- [ ] src/giljo_mcp/tools/context.py - Usage notes on fetch_* functions
- [ ] Test files - Deprecation notices in docstrings

### Cross-References Valid ✅
- [ ] All links to Handover 0280 resolve correctly
- [ ] Links to CLAUDE.md and ORCHESTRATOR.md work
- [ ] No broken relative paths

### Git Commit ✅
- [ ] Descriptive commit message explaining scope
- [ ] All files staged and committed together
- [ ] Commit references Handover 0280

---

## Section 8: Git Commit Strategy

### Commit Message Template

```
docs: Update documentation for monolithic context architecture (Handover 0280)

BREAKING DOCUMENTATION CHANGE: Updated all documentation to reflect migration
from 9 modular fetch_* context tools to single get_orchestrator_instructions() call.

Critical Updates:
- Reference_docs/Dynamic_context.md - Rewritten for monolithic architecture
- Reference_docs/Mcp_tool_catalog.md - Updated tool catalog
- Reference_docs/start_to_finish_agent_FLOW.md - Updated workflow
- CLAUDE.md - Rewritten Context Management section
- docs/ORCHESTRATOR.md - Added monolithic architecture documentation

Handover Updates:
- handovers/0279_context_priority_integration_fix.md - Marked as SUPERSEDED
- 32 completed handovers - Added deprecation notices

Code Comments:
- src/giljo_mcp/thin_prompt_generator.py - Deprecated tool templates
- src/giljo_mcp/tools/context.py - Added usage notes
- Test files - Added deprecation notices

Architecture Change (v3.1 → v3.2+):
OLD: Orchestrator called 9 separate tools (fetch_vision_document, fetch_tech_stack, etc.)
NEW: Orchestrator calls get_orchestrator_instructions() once, server returns all context

Benefits:
- ~1,200 tokens saved per orchestrator
- Server-side priority filtering (consistent)
- Simplified orchestrator code
- Better auditability

Related:
- Handover 0280: Monolithic context migration
- Handover 0246a-c: Orchestrator workflow optimization
- Handover 0312-0316: Context Management v2.0

🤖 Generated with Claude Code
```

---

## Section 9: Success Criteria

### Documentation Accuracy ✅
- [ ] No references to orchestrators calling individual fetch_* tools during staging
- [ ] All workflow descriptions match v3.2+ architecture
- [ ] Monolithic context delivery emphasized in critical docs

### Deprecation Notices ✅
- [ ] All outdated documents have clear deprecation notices
- [ ] Notices explain WHAT changed and WHY
- [ ] Notices link to current documentation

### Developer Experience ✅
- [ ] New developers reading CLAUDE.md understand current architecture
- [ ] Workflow documentation (start_to_finish_agent_FLOW.md) is accurate
- [ ] Historical handovers clearly marked as obsolete where relevant

### Search Discoverability ✅
- [ ] Searching for "fetch_vision_document" returns docs with deprecation notices
- [ ] Searching for "modular context" returns docs with architecture change notices
- [ ] Searching for "get_orchestrator_instructions" returns current docs

---

## Section 10: Effort Summary

| Phase | Task | Files | Effort | Priority |
|-------|------|-------|--------|----------|
| 1 | Critical Reference Docs | 3 | 6h | 🔥 CRITICAL |
| 2 | Core Documentation | 2 | 4h | 🔥 CRITICAL |
| 3 | Handover Updates | 33 | 4h | 🟡 MEDIUM |
| 4 | Secondary Documentation | 2 | 2h | 🟡 MEDIUM |
| **TOTAL** | **All Tasks** | **40** | **16h** | - |

**Recommended Timeline**: 4 days (4 hours/day) or 2 days (8 hours/day)

---

## Section 11: Risk Assessment

### Low Risk Updates
- Adding deprecation notices to completed handovers
- Updating README_FIRST.md
- Code comment updates

**Mitigation**: Review PRs before merge, spot-check 5-10 files

### Medium Risk Updates
- Rewriting Context Management sections
- Updating workflow documentation
- Marking Handover 0279 as obsolete

**Mitigation**: Have second reviewer validate technical accuracy

### High Risk Updates
- None - All changes are documentation-only, no code changes

---

## Section 12: Post-Completion Actions

### Documentation Review ✅
- [ ] Technical review by orchestrator expert
- [ ] User guide review by product owner
- [ ] Cross-reference validation by QA

### Knowledge Sharing ✅
- [ ] Announce documentation update in team channel
- [ ] Update onboarding checklist to reference new docs
- [ ] Create quick reference card for monolithic architecture

### Monitoring ✅
- [ ] Track developer questions about old architecture
- [ ] Monitor search queries for outdated terms
- [ ] Update documentation based on feedback

---

## Conclusion

This remediation plan provides a **complete, structured approach** to updating all documentation affected by the monolithic context migration (Handover 0280).

**Key Principles**:
1. **Prioritize**: Critical reference docs first, archives last
2. **Standardize**: Use consistent deprecation notice template
3. **Cross-reference**: Always link to current documentation
4. **Preserve**: Don't delete historical docs, mark them obsolete
5. **Verify**: Checklist ensures nothing is missed

**Total Effort**: 12-16 hours over 4 days

**Outcome**: Accurate, discoverable documentation that guides developers to current architecture while preserving historical context.

---

**Next Steps**:
1. ✅ Review this plan with product owner
2. ⏳ Execute Phase 1 (critical reference docs)
3. ⏳ Execute Phase 2 (core documentation)
4. ⏳ Execute Phase 3 (handover updates)
5. ⏳ Execute Phase 4 (secondary docs)
6. ⏳ Commit all changes with descriptive message
7. ⏳ Announce completion to team

---

**Document Author**: Documentation Manager Agent
**Date**: December 1, 2025
**Handover Reference**: 0280 (Monolithic Context Migration)
**Status**: Ready for Execution
