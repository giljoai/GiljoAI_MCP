# Handover 0700: Cleanup Index Creation

## Series Context

You are executing handover 0700 in the 0700 Code Cleanup Series.
- Series progress: 1/12 complete
- Previous handover: 0700a - Remove Light Mode Theme Support
- Next handover: 0701 - Dependency Visualization

**Your Position**: This is the FOUNDATIONAL handover for the entire cleanup series. All subsequent handovers (0701-0373) will reference the cleanup index you create.

---

## Your Mission

Create a comprehensive automated tracking system for code cleanup by scanning the entire codebase and cataloging technical debt. You will produce a structured JSON index that enables subsequent handovers to work efficiently.

### Primary Deliverable

Create `handovers/0700_series/cleanup_index.json` containing:

1. **DEPRECATED markers** (46 expected from baseline)
   - File path, line number, context
   - Associated symbol/component
   - Removal target version (if specified)

2. **TODO/FIXME markers** (43 expected from baseline)
   - File path, line number, context
   - Priority inference (CRITICAL/HIGH/MEDIUM/LOW)
   - Category (bug/feature/refactor/docs)

3. **Skipped tests** (168 expected from baseline)
   - Test file path, test name
   - Skip reason (from decorator/comment)
   - Category (unit/integration/e2e)

4. **Dead code candidates** (~5000 lines expected)
   - Unused imports
   - Unreachable code
   - Conditional branches that are always true/false
   - Functions/methods with no callers

### Categorization Requirements

Each entry must be categorized by:

| Dimension | Values | Description |
|-----------|--------|-------------|
| **Type** | deprecated, todo, skipped_test, dead_code | Primary classification |
| **Urgency** | critical, high, medium, low | Determines cleanup priority |
| **Component** | models, services, api, mcp_tools, frontend, tests, utils, config | Affects dependency chain |
| **Risk** | high, medium, low | Potential impact of removal |

---

## Technical Debt Baseline

Current state (from orchestrator_state.json):
- DEPRECATED markers: 46
- TODO markers: 43
- Skipped tests: 168
- Dead code lines: ~5000 (estimate)

**Your scan should validate these numbers and provide exact counts.**

---

## Context from Previous Agents

### From 0700a (Light Mode Removal)

```
Subject: Light mode removal complete
Type: info
From: 0700a
To: 0700, 0701, 0702, 0703

Message: Removed light mode theme support. isDarkTheme now always returns true.
toggleTheme() function removed from settings store. If any code checks isDarkTheme
for conditional logic beyond theming, that logic is now dead code (always takes
dark branch).

Files affected: 18 frontend files
Lines removed: 145
Assets deleted: 4 SVG files
```

**Action for you**: When scanning for dead code, look for:
- References to `isDarkTheme` that check the value (should always be true now)
- Conditional branches that depend on theme state
- Dead branches in theme-related code

---

## Grep Patterns for Scanning

Use these patterns to find cleanup targets:

### DEPRECATED Markers
```bash
# Python files
grep -rn "DEPRECATED" src/ api/ --include="*.py"

# Frontend files
grep -rn "DEPRECATED" frontend/src/ --include="*.js" --include="*.vue"

# Comments with deprecation info
grep -rn "@deprecated" src/ api/ frontend/ --include="*.py" --include="*.js" --include="*.vue"
```

### TODO/FIXME Markers
```bash
# All TODO markers
grep -rn "TODO" src/ api/ frontend/ --include="*.py" --include="*.js" --include="*.vue"

# FIXME markers
grep -rn "FIXME" src/ api/ frontend/ --include="*.py" --include="*.js" --include="*.vue"

# XXX markers
grep -rn "XXX" src/ api/ frontend/ --include="*.py" --include="*.js" --include="*.vue"
```

### Skipped Tests
```bash
# Python tests
grep -rn "@pytest.mark.skip" tests/ --include="*.py"
grep -rn "pytest.skip" tests/ --include="*.py"

# Frontend tests
grep -rn "xit(" frontend/tests/ --include="*.js" --include="*.spec.js"
grep -rn "xdescribe(" frontend/tests/ --include="*.js" --include="*.spec.js"
grep -rn ".skip" frontend/tests/ --include="*.js" --include="*.spec.js"
```

### Dead Code Patterns
```bash
# Unused imports (Python)
# Use pylint or manual inspection for "imported but unused" warnings

# Unreachable code after return/raise
grep -rn "return" src/ api/ -A 5 --include="*.py" | grep -v "^--$"

# Always-true conditions (from 0700a context)
grep -rn "if.*isDarkTheme" frontend/src/ --include="*.vue" --include="*.js"
```

---

## Output Format Specification

### JSON Structure

```json
{
  "generated_at": "ISO 8601 timestamp",
  "generated_by": "handover 0700",
  "baseline_comparison": {
    "deprecated_markers": { "expected": 46, "found": X },
    "todo_markers": { "expected": 43, "found": X },
    "skipped_tests": { "expected": 168, "found": X },
    "dead_code_lines": { "expected": 5000, "found": X }
  },
  "entries": [
    {
      "id": "uuid",
      "type": "deprecated|todo|skipped_test|dead_code",
      "urgency": "critical|high|medium|low",
      "component": "models|services|api|mcp_tools|frontend|tests|utils|config",
      "risk": "high|medium|low",
      "file_path": "relative/path/from/project/root",
      "line_number": 123,
      "symbol": "ClassName.method_name or variable_name",
      "context": "3-5 lines of code showing the item",
      "reason": "Why this is marked (from comments or analysis)",
      "removal_target": "v4.0 or null",
      "notes": "Additional context for cleanup agent",
      "related_to": ["list of related entry IDs if applicable"]
    }
  ],
  "summary": {
    "total_entries": 257,
    "by_type": {
      "deprecated": 46,
      "todo": 43,
      "skipped_test": 168,
      "dead_code": X
    },
    "by_urgency": {
      "critical": X,
      "high": X,
      "medium": X,
      "low": X
    },
    "by_component": {
      "models": X,
      "services": X,
      "api": X,
      "mcp_tools": X,
      "frontend": X,
      "tests": X,
      "utils": X,
      "config": X
    }
  }
}
```

### Example Entry

```json
{
  "id": "dep-001",
  "type": "deprecated",
  "urgency": "high",
  "component": "models",
  "risk": "medium",
  "file_path": "src/giljo_mcp/models/agent_identity.py",
  "line_number": 145,
  "symbol": "AgentExecution.messages",
  "context": "# DEPRECATED: Remove in v4.0 (Handover 0387i)\n# Use messages_sent_count, messages_waiting_count, messages_read_count\nmessages: Mapped[Optional[dict]] = mapped_column(JSON, nullable=True)",
  "reason": "Replaced by counter-based message system (0387i)",
  "removal_target": "v4.0",
  "notes": "Must ensure all readers/writers migrated before removal",
  "related_to": ["dep-002", "dead-003"]
}
```

---

## Documentation to Review/Update

No documentation updates required for this handover. You are creating source data that future handovers will reference.

However, you should add a reference in `docs/architecture/technical_debt.md` (if it exists) or note that this file should be created in a future handover.

---

## Execution Protocol

### Phase 1: Context Acquisition (5 min)
1. ✅ Read orchestrator_state.json (already provided above)
2. ✅ Read comms_log.json (provided above)
3. ✅ Read doc_impacts.json
4. Read this kickoff prompt fully

### Phase 2: Scope Investigation (30-45 min)
1. Run all grep patterns provided above
2. Use Serena MCP tools for symbol analysis where needed:
   - `mcp__serena__find_symbol()` for tracking deprecated symbols
   - `mcp__serena__find_referencing_symbols()` for dead code detection
   - `mcp__serena__search_for_pattern()` for complex patterns
3. Cross-reference findings with baseline numbers
4. Identify discrepancies (if baseline says 46 DEPRECATED but you find 52, investigate why)

### Phase 3: Execution (60-90 min)
1. Use `deep-researcher` subagent as primary investigator
2. For each finding:
   - Extract context (3-5 lines of code)
   - Analyze severity (urgency + risk)
   - Categorize by component
   - Generate unique ID
   - Add notes for cleanup agents
3. Build the cleanup_index.json structure incrementally
4. Validate JSON syntax as you build
5. Generate summary statistics

### Phase 4: Documentation (10 min)
1. Add comment to cleanup_index.json explaining purpose and usage
2. Update doc_impacts.json to note that cleanup_index.json is a new artifact
3. No other docs need updates

### Phase 5: Communication (15 min)
1. Write to comms_log.json for ALL subsequent handovers (0701-0373)
2. Include:
   - Total entries found vs baseline
   - Any critical findings that affect execution order
   - Recommendations for prioritization
   - Notes about dead code from 0700a (isDarkTheme checks)

### Phase 6: Commit (5 min)
1. Update orchestrator_state.json (mark 0700 complete)
2. Stage all changes
3. Commit with format below

---

## Communication Requirements

Before completing, write to comms_log.json with entries for:

### To 0701 (Dependency Visualization)
- Type: `dependency`
- Subject: "Cleanup index ready for visualization"
- Message: Location of cleanup_index.json, entry count, recommended visualization targets

### To 0702-0711 (All Cleanup Workers)
- Type: `info`
- Subject: "Cleanup index baseline established"
- Message: Summary statistics, any critical/high urgency items in their component, notes about risk levels

### To 0373 (Template Adapter Removal)
- Type: `dependency`
- Subject: "Template adapter findings"
- Message: Specific entries related to template_adapter.py, deprecated imports, dead references

### Special Note for 0706 (Models Agents)
- Type: `warning`
- Subject: "AgentExecution.messages deprecation details"
- Message: Exact location, usage count, migration requirements from your scan

---

## Verification Checklist

Before marking complete, verify:

- [ ] cleanup_index.json exists and is valid JSON
- [ ] Entry count matches or explains discrepancies with baseline
- [ ] All entries have required fields (id, type, urgency, component, risk, file_path, line_number)
- [ ] Summary statistics are accurate
- [ ] Context snippets are 3-5 lines (not too verbose)
- [ ] Symbol names are fully qualified (ClassName.method_name)
- [ ] Risk assessment is present for all entries
- [ ] Related entries are cross-referenced where applicable
- [ ] comms_log entries written for 0701-0373
- [ ] orchestrator_state.json updated
- [ ] Changes committed with proper message

---

## Commit Format

```bash
git add handovers/0700_series/cleanup_index.json
git add handovers/0700_series/comms_log.json
git add handovers/0700_series/orchestrator_state.json
git add handovers/0700_series/doc_impacts.json

git commit -m "cleanup(0700): Create cleanup index with technical debt baseline

Scanned entire codebase for DEPRECATED markers, TODO/FIXME comments, skipped tests,
and dead code patterns. Generated comprehensive cleanup_index.json with 257 entries
categorized by type, urgency, component, and risk.

Changes:
- Created cleanup_index.json with full technical debt catalog
- Validated baseline: 46 DEPRECATED, 43 TODO, 168 skipped tests found
- Identified ~5000 lines of dead code (including isDarkTheme branches from 0700a)
- Added comms_log entries for all downstream handovers (0701-0373)

Deliverables:
- cleanup_index.json: 257 entries across 8 components
- Summary statistics by type/urgency/component
- Cross-references for related entries
- Risk assessment for each item

Next: 0701 will use this index to create dependency visualization graphs.

Co-Authored-By: Claude Opus 4.5 <noreply@anthropic.com>"
```

---

## Subagent Recommendations

**Primary**: `deep-researcher`
- Comprehensive codebase scanning
- Pattern analysis across multiple languages
- Symbol tracking and relationship mapping

**Secondary**: None required (this is primarily a data gathering task)

---

## Expected Timeline

- Phase 1 (Context): 5 min
- Phase 2 (Investigation): 30-45 min
- Phase 3 (Execution): 60-90 min
- Phase 4 (Documentation): 10 min
- Phase 5 (Communication): 15 min
- Phase 6 (Commit): 5 min

**Total**: 2-3 hours

---

## Success Criteria

1. cleanup_index.json exists and is valid
2. All baseline numbers validated (or discrepancies explained)
3. Entries are actionable (clear file paths, line numbers, context)
4. Categorization is complete and consistent
5. Cross-references link related entries
6. Risk assessment helps prioritize cleanup
7. Summary statistics match entry counts
8. Comms log entries guide downstream handovers
9. All changes committed with clear message
10. Orchestrator can proceed to 0701 without blockers

---

**You are the foundation for the entire 0700 cleanup series. The quality and completeness of your index will determine the success of all subsequent handovers. Be thorough, be accurate, and communicate clearly!**
