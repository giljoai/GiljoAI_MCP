# Session: 0700b Kickoff Prompt Creation

**Date**: 2026-02-04
**Agent**: Documentation Manager
**Context**: Creating kickoff prompt for Handover 0700b (Database Schema Purge) leveraging 0701 visualization findings

---

## Objective

Create a comprehensive kickoff prompt for 0700b that incorporates critical dependency insights from 0701's visualization analysis, ensuring worker understands the high-risk nature of modifying agent_identity.py with its 32 dependents.

---

## Deliverable

**File**: `handovers/0700_series/kickoff_prompts/0700b_kickoff.md`

**Structure**:
1. Mission overview and strategic context
2. **CRITICAL SECTION**: Dependency awareness from 0701 findings
   - High-risk files list (8 files with 20+ dependents)
   - Focus on agent_identity.py's 32 dependent files
   - Explicit warning about models/__init__.py (105 dependents)
3. Scope breakdown (4 tables, 9 deprecated columns)
4. 4-phase execution plan with verification steps
5. Risk mitigation and rollback procedures
6. Communication requirements (comms_log.json format)
7. Recommended subagents (database-expert primary, tdd-implementor secondary)
8. Documentation update checklist
9. Commit format template
10. Success criteria checklist

---

## Key Design Decisions

### 1. High-Risk Awareness Prominently Featured

Placed dependency insights from 0701 at the TOP of the kickoff prompt (immediately after mission overview) because:
- Worker needs to understand risk BEFORE starting work
- 32 dependents on agent_identity.py makes this HIGH-RISK
- Visual emphasis with ⚠️ warnings draws attention

### 2. Execution Order: Least-to-Most Risky

Phase 2 execution plan orders removals by risk level:
1. `download_tokens` (safest - utility columns)
2. `templates` (medium - seeder dependency)
3. `projects` (medium - migration to AgentExecution needed)
4. `agent_identity.py` (highest risk - 32 dependents)

Rationale: If something breaks, better it breaks early with low-risk changes. Build confidence before tackling the high-risk file.

### 3. Grep-Before-Remove Pattern

Required verification step BEFORE removing each column:
```bash
grep -r "column_name" src/ api/ --exclude-dir=migrations
```

Rationale: 0701 identified 32 files that import agent_identity.py - we don't know which ones access these specific columns. Grepping ensures we catch any usage before breaking it.

### 4. Stop-After-Each-Table Testing

After each table's columns are removed:
- Run relevant test files
- Check for import errors
- Verify no runtime breaks

Rationale: Incremental verification prevents cascade failures. If tests break, we know exactly which change caused it.

### 5. Three-Handover Communication Chain

Comms log entries should notify:
- **0700c** - JSONB cleanup needs to know about schema changes
- **0700d** - Legacy succession cleanup needs confirmation succession columns gone
- **0700e** - Template system cleanup needs confirmation template_content gone

Rationale: These three handovers have direct dependencies on 0700b's work. Other handovers (0700f, 0700g, 0700h) are further downstream and don't need immediate notification.

---

## Technical Details

### Incorporated 0701 Findings

From `dependency_analysis.json`:
- 8 high-risk files with 20+ dependents
- agent_identity.py specifically has 32 dependents
- Orphan modules count (271) - indicates safe removal candidates
- Circular dependencies detected (49 cycles)

### Cross-Referenced Files Read

1. `handovers/0700_series/0700b_database_schema_purge.md` - Full specification
2. `handovers/0700_series/dependency_analysis.json` - High-risk files (couldn't read full file due to size, used grep)
3. `handovers/0700_series/comms_log.json` - Context from 0700a, 0700, 0701
4. `handovers/0700_series/WORKER_PROTOCOL.md` - Execution protocol
5. `handovers/0700_series/orchestrator_state.json` - Series context

### Verification Strategy

Three-stage verification approach:
1. **Pre-removal**: Grep for usage patterns
2. **During removal**: Test after each table
3. **Post-removal**: Fresh install + schema inspection + zero grep hits

This catches issues at three checkpoints, reducing risk of shipping broken code.

---

## Handover Integration

### Series Context Provided

Kickoff prompt opens with:
> **Series**: 0700 Code Cleanup Series (4/12 complete: 0700a, 0700, 0701, [YOU ARE HERE])

This orients the worker in the broader series context.

### Dependency Chain Documented

Clear notation of:
- **Depends on**: 0701 (complete - findings available)
- **Blocks**: 0700c, 0700d, 0700e (waiting for schema cleanup)

Worker understands their place in the execution sequence.

### Communication Format Specified

Provided JSON template for comms_log.json entries with:
- Required fields (id, timestamp, from_handover, to_handovers, type, subject, message)
- Optional context field for structured data
- Example showing proper usage
- List of handovers to notify (0700c, 0700d, 0700e)

---

## Risk Emphasis

Multiple layers of risk communication:
1. **Top-level badge**: "Risk Level: ⚠️ HIGH"
2. **Critical section header**: "⚠️ CRITICAL: Dependency Awareness from 0701 Visualization"
3. **Per-table risk indicators**: ⚠️ emoji next to agent_executions
4. **Critical reminders section** at bottom with three ⚠️ warnings
5. **Rollback plan** prominently featured
6. **Stop-if-blocked** instructions repeated twice

Rationale: This is a HIGH-RISK handover. Over-communication of risk is better than under-communication.

---

## Recommended Subagents

**Primary**: `database-expert`
- Schema expertise
- Migration knowledge
- Database verification skills

**Secondary**: `tdd-implementor`
- Test verification
- Regression detection
- Quality assurance

Rationale: This is primarily a database task (schema changes + migrations) with strong testing requirements. Database-expert makes the changes, tdd-implementor verifies nothing broke.

---

## Success Criteria

10-point checklist provided:
1. All 9 columns removed
2. Migration updated
3. Fresh install works
4. Tests pass (100%)
5. Zero grep hits
6. Schema verification
7. Comms log entry written
8. Docs updated
9. Orchestrator state updated
10. Changes committed

Worker can't miss any critical step - they're all listed explicitly.

---

## Lessons Learned

### What Worked Well

1. **Leveraging 0701 findings**: The visualization analysis provided critical context that made the kickoff prompt much more actionable. Knowing about the 32 dependents on agent_identity.py shaped the entire execution strategy.

2. **Risk-first design**: Putting dependency awareness at the TOP of the prompt (not buried in the middle) ensures worker sees the risk before diving into execution.

3. **Incremental verification**: Stop-after-each-table testing prevents cascade failures and makes debugging easier.

### What Could Be Improved

1. **Dependency file list**: Could have parsed dependency_analysis.json more thoroughly to list ALL 32 dependent files explicitly. Currently only shows categories (services, API endpoints, tools, tests) with counts.

2. **Grep commands**: Could provide more sophisticated grep patterns that exclude false positives (e.g., comments, docstrings).

3. **Visualization reference**: Could have embedded a screenshot or ASCII diagram showing the dependency graph around agent_identity.py for visual learners.

---

## Related Documentation

- **Handover Spec**: `handovers/0700_series/0700b_database_schema_purge.md`
- **Dependency Analysis**: `handovers/0700_series/dependency_analysis.json`
- **Visualization**: `docs/cleanup/dependency_graph.html`
- **Worker Protocol**: `handovers/0700_series/WORKER_PROTOCOL.md`
- **Series State**: `handovers/0700_series/orchestrator_state.json`
- **Comms Log**: `handovers/0700_series/comms_log.json`

---

## Next Steps

1. Worker executes 0700b using this kickoff prompt
2. Worker writes findings to comms_log.json for 0700c/0700d/0700e
3. Documentation manager (me) updates docs per doc_impacts.json after execution
4. Orchestrator reviews completion and schedules next handover

---

**Mission accomplished. Kickoff prompt is ready for worker session. Clear risk communication, actionable execution plan, comprehensive verification strategy.** ✅
