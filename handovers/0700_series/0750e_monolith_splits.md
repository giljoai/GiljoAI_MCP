# 0750e: Monolith Splits — Research Phase

**Series:** 0750 (Code Quality Cleanup Sprint)
**Phase:** 5 of 7 (Session 1 — RESEARCH ONLY)
**Branch:** `0750-cleanup-sprint`
**Priority:** MEDIUM — architecture improvement

### Reference Documents
- **Roadmap:** `handovers/CLEANUP_ROADMAP_2026_02_28.md` (Phase 5 section)
- **Audit report:** `handovers/CODE_QUALITY_AUDIT_REPORT_2026_02_28.md` (finding H-16: 4 oversized functions >250 lines)
- **Mid-point audit:** `prompts/0750_chain/midpoint_audit.json` (score 7.1/10, new findings)
- **Dependency graph:** `docs/cleanup/dependency_graph.json` (refresh FIRST before using)
- **Previous phase notes:** Read `prompts/0750_chain/chain_log.json` session 0750d `notes_for_next`

### Tracking Files (update these when done)
- **Chain log:** `prompts/0750_chain/chain_log.json`
- **Progress tracker:** `handovers/0700_series/0750_cleanup_progress.json`

---

## Context

The mid-point re-audit (7.1/10) passed the gate. The codebase has two major monoliths that need splitting:

1. **`src/giljo_mcp/services/orchestration_service.py`** — 3,427 lines, 162 TODOs, 32 dependents. This is the largest single file in the codebase. It handles agent spawning, retirement, status tracking, heartbeats, event handling, and more — all in one class.

2. **`src/giljo_mcp/tools/tool_accessor.py`** — 1,072 lines, 28 dependents. Functions cover multiple domains (agent tools, project tools, context tools) that should be separated.

This session is **RESEARCH ONLY**. You will map the monoliths, identify split boundaries, and write a detailed split plan. No code changes.

---

## Scope

### Step 0: Refresh the dependency graph

```bash
python scripts/update_dependency_graph_full.py
```

This ensures the graph reflects all Phase 3/4 changes. Wait for it to complete before proceeding.

### Step 1: Map OrchestrationService (3,427 lines)

Read `src/giljo_mcp/services/orchestration_service.py` and identify natural split boundaries.

**Tasks:**
- [ ] Read the file using `get_symbols_overview` with `depth=1` to get all methods
- [ ] Group methods by domain:
  - **Spawn management**: methods that create/launch agents
  - **Retirement management**: methods that retire/decommission agents
  - **Status/heartbeat**: methods that track agent status and health
  - **Event handling**: methods that process events and notifications
  - **Job management**: methods that handle agent jobs/executions
  - **Other**: anything that doesn't fit the above
- [ ] For each proposed module, use the dependency graph to list which current dependents would import it
- [ ] Count lines per group to verify the split produces balanced modules
- [ ] Identify shared state (instance variables, DB sessions) that all split modules need access to — this determines if you use inheritance, composition, or standalone functions

### Step 2: Map tool_accessor.py (1,072 lines)

Read `src/giljo_mcp/tools/tool_accessor.py` and group functions by domain.

**Tasks:**
- [ ] Read the file using `get_symbols_overview` with `depth=1`
- [ ] Group functions by domain (agent tools, project tools, context tools, product tools, etc.)
- [ ] For each group, list its callers using `find_referencing_symbols` or the dependency graph
- [ ] Determine if splitting makes sense — if most callers use functions from multiple groups, splitting creates more import complexity without benefit

### Step 3: Find other monolith candidates

```bash
# Find large files in src/
wc -l src/giljo_mcp/**/*.py src/giljo_mcp/**/**/*.py 2>/dev/null | sort -rn | head -20
```

**Tasks:**
- [ ] List any file >500 lines in `src/giljo_mcp/`
- [ ] For each, check dependent count in the dependency graph
- [ ] Determine if it's a genuine monolith (one class doing too many things) or just a large but focused file (acceptable)

### Step 4: Find oversized functions (H-16)

```bash
# This requires reading the file and checking method lengths
```

**Tasks:**
- [ ] Find the 4 functions >250 lines referenced in H-16
- [ ] For each, determine if it can be extracted into smaller functions
- [ ] Document proposed extractions in the split plan

### Step 5: Write the split plan

Create `handovers/MONOLITH_SPLIT_PLAN.md` with this structure:

```markdown
# Monolith Split Plan

## OrchestrationService Split

### Current State
- File: src/giljo_mcp/services/orchestration_service.py
- Lines: 3,427
- Dependents: [list from graph]
- TODOs: 162

### Proposed Split
| New Module | Methods | Lines | Dependents Affected |
|---|---|---|---|
| spawn_manager.py | [list] | ~X | [list] |
| retirement_manager.py | [list] | ~X | [list] |
| status_tracker.py | [list] | ~X | [list] |
| event_handler.py | [list] | ~X | [list] |

### Shared Infrastructure
- [What's shared between modules: DB session, tenant context, etc.]
- [Proposed pattern: base class, mixin, dependency injection, etc.]

### Migration Strategy
- [How to maintain backward compatibility during transition]
- [Re-export pattern from original file if needed]

## tool_accessor.py Split
[Same structure]

## Other Splits
[If any]

## Oversized Functions
| Function | File | Lines | Proposed Action |
|---|---|---|---|
| [name] | [file] | [lines] | [extract into X and Y] |

## Estimated Effort
- OrchestrationService: X sessions
- tool_accessor.py: X sessions
- Other: X sessions
```

---

## What NOT To Do

- Do NOT write any production code — this is research only
- Do NOT modify any source files
- Do NOT delete any files
- Do NOT split files without the plan being reviewed first
- Do NOT treat the dependency graph as the sole source of truth — verify with `find_referencing_symbols`
- Do NOT propose splits that increase import complexity without clear benefit
- Do NOT split `models/__init__.py` (it's a registry, not a monolith)

---

## Acceptance Criteria

- [ ] Dependency graph refreshed with post-Phase-4 data
- [ ] `handovers/MONOLITH_SPLIT_PLAN.md` exists with detailed split proposals
- [ ] OrchestrationService methods grouped by domain with line counts
- [ ] tool_accessor.py functions grouped by domain with caller lists
- [ ] All files >500 lines identified and assessed
- [ ] All functions >250 lines identified with extraction proposals
- [ ] No production code modified

---

## Completion Steps

### Step 1: Verify branch
```bash
git branch --show-current
# Must show: 0750-cleanup-sprint
```

### Step 2: Commit
```bash
git add handovers/MONOLITH_SPLIT_PLAN.md docs/cleanup/dependency_graph.json
git commit -m "research(0750e): Map monolith splits — OrchestrationService, tool_accessor, oversized functions"
```

### Step 3: Record commit hash
```bash
git rev-parse --short HEAD
```

### Step 4: Update chain log
Read `prompts/0750_chain/chain_log.json`, update session `0750e`:
- Set `"status": "complete"`
- Set `"started_at"` and `"completed_at"` to timestamps
- Fill in `"tasks_completed"` — list what you mapped
- Fill in `"notes_for_next"`: key findings, recommended split order, any surprises
- Fill in `"summary"`: 2-3 sentences

### Step 5: Update progress tracker
Read `handovers/0700_series/0750_cleanup_progress.json`, update `phases[4]`:
- Set `"status": "complete"`
- Set `"commits": ["<hash>"]`
- Set `"notes"`: brief summary

### Step 6: Done
Do NOT spawn the next terminal.
Print "0750e COMPLETE" as your final message.
