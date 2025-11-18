# Handover 0312: Context Architecture v2.0 Design

**Status**: Design Complete
**Tool**: Claude Code (CLI) - Architecture design and documentation
**Created**: 2025-11-17
**Updated**: 2025-11-17
**Dependencies**: 0301-0311 (v1.0 Context Management), 013A (Architecture Status)
**Next**: 0313 (Priority System), 0314 (Depth Controls), 0315 (MCP Thin Client)

## Executive Summary

Design the v2.0 architecture for Context Management System with 2-dimensional model (Priority × Depth). This handover addresses the architectural mismatch discovered in v1.0 where priority conflated "importance emphasis" with "token trimming".

**CRITICAL CORRECTION - Product Vision**:
GiljoAI is NOT a token reduction tool. It is a **context management and orchestration center** for terminal-based coding agents. v2.0 focuses on:
- **Context Management**: Prioritize, organize, and deliver context intelligently
- **Developer Control**: Fine-grained tuning of WHAT gets fetched and HOW MUCH detail
- **Message Hub**: Agent status reporting and progress tracking
- **360 Memory**: Cumulative product knowledge across projects
- **Technical Debt Management**: Decision tracking and architecture evolution

Token reduction is a side effect, NOT the driving force.

**Root Cause**: v1.0 treated priority as context prioritization level (Priority 1 = full detail, Priority 3 = abbreviated). Users actually need priority to signal importance, with separate depth controls for token management.

**Solution**: Decouple concerns into 2-dimensional model:
- **Priority** (4 levels): CRITICAL / IMPORTANT / NICE TO HAVE / EXCLUDE (fetch order/mandatory flag)
- **Depth** (per-source): Context-specific chunking/limiting strategies (developer-tunable granularity)

## Problem Statement

### Current v1.0 System (Completed in 0301-0311)

**Priority = Token Reduction**:
- Priority 1 → 100% context (0% reduction)
- Priority 2 → 75% context (25% reduction)
- Priority 3 → 50% context (50% reduction)
- Exclude → 0% context (100% reduction)

**Issues**:
1. User wants to say "Architecture is CRITICAL" but gets 100% of tokens (wasteful)
2. User can't say "Include all 9 sources but trim each appropriately"
3. No per-source trimming strategies (360 memory ≠ vision document ≠ git history)
4. Thin client MCP architecture not fully realized (still fat prompts)

### Desired v2.0 System

**Priority = Importance Emphasis**:
- Level 1 (CRITICAL): "Must understand thoroughly - don't miss this"
- Level 2 (IMPORTANT): "Pay close attention"
- Level 3 (NICE TO HAVE): "Consider if relevant"
- Level 4 (EXCLUDE): "Not relevant - skip entirely"

**Depth = Per-Source Chunking** (separate from priority):
- Vision Document: [None | Light | Moderate | Heavy] chunking
- 360 Memory: [Last 1 | 3 | 5 | 10] projects
- Git History: [Last 1 | 3 | 5 | 10] commits
- Agent Templates: [Title Only | Full Description]
- Tech Stack: [Summary | Full]
- Architecture: [Summary | Full] + optional Serena codebase

## Architecture Design Tasks

### Task 1: Define 2-Dimensional Data Model

**User.field_priority_config** (existing - repurpose):
```json
{
  "version": "2.0",
  "priorities": {
    "vision_document": 1,      // CRITICAL
    "architecture": 1,          // CRITICAL
    "tech_stack": 2,            // IMPORTANT
    "agent_templates": 2,       // IMPORTANT
    "360_memory": 3,            // NICE TO HAVE
    "testing": 3,               // NICE TO HAVE
    "git_integration": 4        // EXCLUDE
  }
}
```

**User.depth_config** (NEW - add to models.py):
```json
{
  "version": "1.0",
  "depth": {
    "vision_chunking": "moderate",        // none | light | moderate | heavy
    "memory_projects": 3,                  // 1 | 3 | 5 | 10
    "git_commits": 5,                      // 1 | 3 | 5 | 10
    "agent_detail": "title",               // title | full
    "tech_stack_detail": "summary",        // summary | full
    "architecture_detail": "full",         // summary | full
    "include_serena_codebase": true        // boolean (when Serena enabled)
  }
}
```

### Task 2: Design MCP Tool Contracts

Define 6 new MCP tools for on-demand context fetching:

```python
# src/giljo_mcp/tools/get_vision_document.py
@mcp_tool
async def get_vision_document(
    product_id: str,
    tenant_key: str,
    chunking: str = "moderate"  # none | light | moderate | heavy
) -> str:
    """
    Fetch vision document with specified chunking level.

    Returns: Markdown-formatted vision content
    Token estimate: 500-5000 tokens (depends on chunking)
    """

# src/giljo_mcp/tools/get_360_memory.py
@mcp_tool
async def get_360_memory(
    product_id: str,
    tenant_key: str,
    last_n_projects: int = 3  # 1 | 3 | 5 | 10
) -> str:
    """
    Fetch 360 Memory historical learnings.

    Returns: Markdown-formatted project summaries
    Token estimate: 150-1500 tokens (150 per project)
    """

# src/giljo_mcp/tools/get_git_history.py
@mcp_tool
async def get_git_history(
    product_id: str,
    tenant_key: str,
    last_n_commits: int = 5  # 1 | 3 | 5 | 10
) -> str:
    """
    Fetch recent Git commit history.

    Returns: Markdown-formatted commit log
    Token estimate: 50-500 tokens (50 per commit)
    """

# src/giljo_mcp/tools/get_agent_templates.py
@mcp_tool
async def get_agent_templates(
    tenant_key: str,
    detail: str = "title"  # title | full
) -> str:
    """
    Fetch available agent templates.

    Returns: Markdown-formatted agent roster
    Token estimate: 150-2400 tokens
    """

# src/giljo_mcp/tools/get_tech_stack.py
@mcp_tool
async def get_tech_stack(
    product_id: str,
    tenant_key: str,
    detail: str = "summary"  # summary | full
) -> str:
    """
    Fetch technology stack configuration.

    Returns: Markdown-formatted tech stack
    Token estimate: 100-400 tokens
    """

# src/giljo_mcp/tools/get_architecture.py
@mcp_tool
async def get_architecture(
    product_id: str,
    tenant_key: str,
    detail: str = "full",              # summary | full
    include_codebase: bool = False     # requires Serena MCP
) -> str:
    """
    Fetch architecture patterns and optional codebase structure.

    Returns: Markdown-formatted architecture + optional codebase
    Token estimate: 200-1500 tokens (500+ if codebase included)
    """
```

### Task 3: Design Thin Client Prompt Template

**New orchestrator prompt structure** (~500 tokens):

```markdown
## Project Mission
[project.description]

## Context Priorities

### 🔴 CRITICAL (Level 1) - Must understand thoroughly
- Vision Document
- Architecture

**INSTRUCTION**: For CRITICAL items, fetch FULL context before planning.

### 🟡 IMPORTANT (Level 2) - Pay close attention
- Tech Stack
- Agent Templates

**INSTRUCTION**: Fetch summaries, drill down via MCP if needed.

### 🟢 NICE TO HAVE (Level 3) - Consider if relevant
- 360 Memory
- Testing Strategy

**INSTRUCTION**: Only fetch if directly relevant to mission.

### ❌ EXCLUDED (Level 4)
- Git History (user disabled)

## MCP Tools for Context Retrieval

Use these tools to fetch context on-demand:

\`\`\`python
get_vision_document(chunking="moderate")      # ~1200 tokens
get_architecture(detail="full", include_codebase=True)  # ~1500 tokens
get_tech_stack(detail="summary")              # ~100 tokens
get_agent_templates(detail="title")           # ~150 tokens
get_360_memory(last_n_projects=3)             # ~450 tokens
\`\`\`

**Token Budget**: Use judgment. Prioritize CRITICAL context over abstract token-efficiency metrics.
```

### Task 4: Design Frontend UI Mockups

**UserSettings.vue - New 2-Tab Design**:

**Tab 1: Context Priorities** (drag-and-drop cards):
```
┌─────────────────────────────────────┐
│  Context Priorities                 │
│                                     │
│  Drag to reorder by importance:    │
│                                     │
│  🔴 CRITICAL (Always include)      │
│  ┌──────────────────────────────┐  │
│  │ 📄 Vision Document           │  │
│  │ 🏗️ Architecture              │  │
│  └──────────────────────────────┘  │
│                                     │
│  🟡 IMPORTANT (High priority)      │
│  ┌──────────────────────────────┐  │
│  │ 💻 Tech Stack                │  │
│  │ 🤖 Agent Templates           │  │
│  └──────────────────────────────┘  │
│                                     │
│  🟢 NICE TO HAVE (If relevant)     │
│  ┌──────────────────────────────┐  │
│  │ 📚 360 Memory                │  │
│  │ 🧪 Testing Strategy          │  │
│  └──────────────────────────────┘  │
│                                     │
│  ❌ EXCLUDED                        │
│  ┌──────────────────────────────┐  │
│  │ (empty - drag here)          │  │
│  └──────────────────────────────┘  │
└─────────────────────────────────────┘
```

**Tab 2: Context Depth** (per-source configuration):
```
┌───────────────────────────────────────────────────┐
│  Context Depth Configuration                      │
│                                                   │
│  ┌──────────┬────────────────────┬─────────────┐ │
│  │ Source   │ Depth Control      │ Est. Tokens │ │
│  ├──────────┼────────────────────┼─────────────┤ │
│  │ Vision   │ [None|Light|       │   1,200     │ │
│  │          │  Moderate|Heavy] ▼ │             │ │
│  ├──────────┼────────────────────┼─────────────┤ │
│  │ 360      │ Last [1|3|5|10] ▼  │     450     │ │
│  │ Memory   │ projects           │             │ │
│  ├──────────┼────────────────────┼─────────────┤ │
│  │ Git      │ Last [1|3|5|10] ▼  │     250     │ │
│  │ History  │ commits            │             │ │
│  ├──────────┼────────────────────┼─────────────┤ │
│  │ Agents   │ [Title Only|       │     150     │ │
│  │          │  Full Desc] ▼      │             │ │
│  ├──────────┼────────────────────┼─────────────┤ │
│  │ Tech     │ [Summary|Full] ▼   │     100     │ │
│  │ Stack    │                    │             │ │
│  ├──────────┼────────────────────┼─────────────┤ │
│  │ Arch.    │ [Summary|Full] ▼   │     800     │ │
│  │          │ ☑ Include codebase │             │ │
│  └──────────┴────────────────────┴─────────────┘ │
│                                                   │
│  📊 Estimated Total: 2,950 tokens                │
│     (Fetched via MCP on-demand)                  │
└───────────────────────────────────────────────────┘
```

## Workflow Integration

### Launch Tab (Project Staging)
1. User creates project, triggers orchestrator staging
2. Orchestrator receives **thin prompt** (<600 tokens):
   - Tenant key, product ID, project ID
   - References to 6 MCP tools for context fetching
   - Token budget (default 2000, user-configurable)
3. Orchestrator fetches context via MCP tools **based on Priority**:
   - Priority 1 (CRITICAL): Always fetch (e.g., tech stack, agent templates)
   - Priority 2 (IMPORTANT): Fetch if budget allows (e.g., vision, 360 memory)
   - Priority 3 (NICE_TO_HAVE): Fetch if budget remaining (e.g., git history)
   - Priority 4 (EXCLUDED): Never fetch
4. Orchestrator creates mission, selects agents, spawns jobs
5. UI displays "Launch" button when staging complete

### Implementation Tab (Agent Execution)
1. User clicks "Launch" → tab switches to Implementation view
2. **Claude Code Mode**: Orchestrator spawns agents as subprocesses, agents fetch jobs via MCP
3. **Legacy CLI Mode**: Each agent card displays thin prompt, user pastes in separate terminal
4. Agents communicate via MCP message center, report progress via WebSocket
5. Orchestrator monitors context usage, triggers succession at 90% capacity

## Deliverables

1. **Architecture Specification Document** (this handover updated with design details) ✅
2. **Data Model Schema** (User.depth_config JSONB structure) ✅
3. **MCP Tool Contracts** (6 tool signatures with token estimates) ✅
4. **Thin Client Prompt Template** (~500 tokens with MCP instructions) ✅
5. **UI Mockups** (ASCII diagrams for Priority/Depth configuration) ✅
6. **Migration Strategy** (v1.0 → v2.0 hard cutover plan) ✅

## Success Criteria

- [x] 2-dimensional model clearly defined (Priority × Depth)
- [x] Per-source depth controls specified for all 6 sources
- [x] MCP tool contracts documented with token estimates
- [x] Thin client prompt template validated (<600 tokens)
- [x] UI mockups reviewed and approved (ASCII diagrams)
- [x] Migration strategy addresses backward compatibility (hard cutover, no prod users)
- [x] Product vision corrected (context management, NOT token reduction)
- [x] Workflow integration documented (Launch/Implementation tabs)
- [x] References to dependencies (0301-0311, 013A) documented

## Dependencies

**Blocked by**: None (design phase)

**Blocks**:
- Handover 0313 (Implement Priority System)
- Handover 0314 (Implement Depth Controls)
- Handover 0315 (Refactor MCP Thin Client)

## Notes

**Code Reuse from v1.0**:
- ✅ Keep: `_format_tech_stack()`, `_extract_config_field()`, `_extract_product_learnings()`, `_get_relevant_vision_chunks()`
- 🔄 Refactor: Change semantics, not logic (60-80% reuse)
- ❌ Remove: Token budget enforcement, uniform trimming strategies

**v1.0 Work Not Wasted**:
All extraction methods from 0301-0311 will be reused in MCP tools. Only the architectural approach changes (priority semantics, thin client).
