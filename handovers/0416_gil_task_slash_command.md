# Handover: /gil_task Slash Command Implementation

**Date:** 2026-01-16
**From Agent:** Claude Opus 4.5 (Research Session)
**To Agent:** Next Session / tdd-implementor
**Priority:** Medium
**Estimated Complexity:** 8-12 hours
**Status:** Ready for Implementation
**Branch:** `task_update`

---

## Task Summary

Implement a `/gil_task` slash command that allows users to "punt" technical debt and scope creep items from their CLI conversation directly to the GiljoAI MCP server's Tasks dashboard.

**Why it matters:** Users working on Feature X often realize they need to do Y (scope creep). Instead of derailing, they run `/gil_task`, Claude summarizes the concept, asks clarifying questions, and stores it as a task for later review/conversion to a project.

---

## Context and Background

### Hierarchy Clarification
```
User (remote terminal with CLI)
├── Products (software products)
│   └── Projects (work orders -> orchestrated by agents)
│       └── Agent Jobs (MCP orchestration)
│
└── Tasks (SIDE FEATURE - separate from orchestration)
    ├── Ideas, concepts, todos, technical debt
    ├── Dashboard for organizing/sorting
    └── Can be CONVERTED -> Project (then executed)
```

**Key Insight:** Tasks are a "parking lot" / backlog feature, NOT part of the agent orchestration pipeline.

### Existing Infrastructure

| Component | Location | Status |
|-----------|----------|--------|
| `create_task` MCP tool | `ToolAccessor.create_task()` -> `TaskService.create_task()` | Exists |
| Task Model | `src/giljo_mcp/models/tasks.py` | Rich schema |
| Slash Command Pattern | `src/giljo_mcp/slash_commands/` | Pattern established |
| Web UI Task Modal | Frontend `TasksView.vue` | Fields: title, description, status, priority, category, due_date |

### Task Model Fields (Relevant)
```python
title           # Required - task name
description     # Detailed description
category        # "frontend", "backend", "database", "infra", "docs", "general"
priority        # low, medium, high, critical
status          # pending (default for punt)
product_id      # Optional - links to product for filtering
project_id      # Optional - links to project
meta_data       # JSONB for extensible metadata
```

---

## Technical Details

### Two Modes of Operation

| Mode | Trigger | Behavior |
|------|---------|----------|
| **Direct** | `/gil_task --name "X" --priority high --category backend` | Immediate DB insert via MCP tool |
| **Interactive** | `/gil_task` (no args) | Claude summarizes conversation -> asks questions -> creates task |

### Implementation Approach: Claude Code Skill (Recommended)

**Why Skill over Server-Side Handler:**
- Interactive mode needs conversation context (summarization)
- Server-side handlers (`src/giljo_mcp/slash_commands/`) don't have access to conversation
- Skill runs client-side in Claude Code, has full context

**File to Create:** `.claude/commands/gil_task.md`

### Skill Flow (Interactive Mode)

```
User: /gil_task

Claude (via skill):
1. Summarizes last concept discussed in conversation
2. Shows: "This is what I'll punt to the server:"
   - Title: [generated from summary]
   - Description: [generated from summary]

3. Asks user:
   a) Scope: "Where should this task live?"
      - Active product: "ABC Product" (if exists)
      - All Tasks (unscoped) - no product association

   b) Category: frontend | backend | database | infra | docs | general

   c) Priority: low | medium (default) | high | critical

4. Calls MCP tool: mcp__giljo-mcp__create_task(...)

5. Confirms: "Task created: [title]"
```

### Direct Mode (With Flags)

```bash
/gil_task --name "Refactor auth service" --priority high --category backend
```

Skill parses flags and directly calls MCP tool without Q&A.

---

## Files to Modify/Create

### 1. Create Skill File
**File:** `.claude/commands/gil_task.md`
**Purpose:** Claude Code skill definition with prompt instructions

### 2. Verify MCP Tool Exposure
**File:** `src/giljo_mcp/tools/tool_accessor.py` (line 431-437)
**Purpose:** Confirm `create_task` is properly exposed and accepts all needed params

### 3. Optional: Extend TaskService
**File:** `src/giljo_mcp/services/task_service.py`
**Purpose:** May need to add `product_id` parameter support if missing

### 4. Update Skill Registry (if needed)
**File:** Check if `.claude/commands/` is auto-discovered or needs registration

---

## Implementation Plan

### Phase 1: Research & TDD Setup (2-3h)
1. Write failing tests for skill behavior
2. Verify `create_task` MCP tool parameters
3. Check how other skills are structured (if any exist)

### Phase 2: Direct Mode (2-3h)
1. Create skill file with flag parsing
2. Direct MCP tool call for `--name`, `--priority`, `--category` flags
3. Test direct mode end-to-end

### Phase 3: Interactive Mode (3-4h)
1. Add summarization prompt logic
2. Implement multi-question flow (scope, category, priority)
3. Handle product association (optional)
4. Test interactive flow

### Phase 4: Integration & Polish (1-2h)
1. Error handling for MCP failures
2. Success confirmation messages
3. Documentation update

---

## Testing Requirements

### Unit Tests
```python
# tests/slash_commands/test_gil_task.py
def test_direct_mode_creates_task_with_flags():
    """Direct mode with --name --priority --category creates task immediately"""

def test_interactive_mode_asks_for_category():
    """Interactive mode prompts for category selection"""

def test_product_scope_optional():
    """Tasks can be created without product association"""
```

### Integration Tests
```python
# tests/integration/test_gil_task_integration.py
def test_task_appears_in_ui_after_creation():
    """Task created via /gil_task appears in Tasks dashboard"""

def test_task_linked_to_product_when_scoped():
    """Task with product scope has correct product_id"""
```

### Manual Testing
1. Run `/gil_task` in Claude Code terminal
2. Verify summarization of conversation
3. Answer category/priority questions
4. Check task appears in web UI
5. Verify task can be converted to project

---

## Dependencies and Blockers

### Dependencies
- [x] `create_task` MCP tool exists
- [x] Task model has all needed fields
- [ ] Verify `.claude/commands/` skill discovery mechanism
- [ ] Confirm product_id can be passed through MCP tool

### Potential Blockers
- **Product ID retrieval**: May need MCP tool to fetch user's active product
- **Skill format**: Need to verify Claude Code skill file format

---

## Success Criteria

**Definition of Done:**
- [ ] `/gil_task --name "X" --priority high --category backend` creates task directly
- [ ] `/gil_task` (no args) triggers interactive flow
- [ ] Interactive flow summarizes conversation context
- [ ] User can choose scope (product or unscoped)
- [ ] User can choose category and priority
- [ ] Task appears in MCP server UI under Tasks tab
- [ ] All tests passing (>80% coverage for new code)
- [ ] Documentation updated

---

## Rollback Plan

**If Things Go Wrong:**
- Skill file is self-contained in `.claude/commands/`
- Delete skill file to disable feature
- No database schema changes required
- No backend code changes if using existing MCP tool

---

## Additional Resources

### Existing Patterns
- Slash commands: `src/giljo_mcp/slash_commands/handover.py` (server-side pattern)
- MCP tool: `ToolAccessor.create_task()` (tool_accessor.py:431-437)
- Task model: `src/giljo_mcp/models/tasks.py`

### Related Handovers
- 0083: Harmonize Slash Commands (deferred, different scope)

---

## Open Questions

1. **Does Claude Code auto-discover `.claude/commands/*.md`?**
   - Need to verify skill registration mechanism

2. **How to get active product ID in skill context?**
   - May need `get_active_product` MCP tool call first

3. **Category list source?**
   - Hardcode for now: `frontend`, `backend`, `database`, `infra`, `docs`, `general`
   - Or fetch from server config?

---

## Progress Updates

### 2026-01-16 - Research Session (Claude Opus 4.5)
**Status:** Research Complete
**Work Done:**
- Reviewed existing slash command patterns
- Analyzed Task model schema
- Documented two-mode architecture (direct vs interactive)
- Identified skill-based approach (client-side) as recommended
- Created implementation plan with TDD phases

**Next Steps:**
- Verify Claude Code skill file format
- Write failing tests first (TDD Red phase)
- Implement direct mode
- Implement interactive mode
