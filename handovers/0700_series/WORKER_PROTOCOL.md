# 0700 Series Worker Protocol

**For**: Worker sessions executing individual handovers in the 0700 Code Cleanup Series

---

## Your Workflow (6 Phases)

### Phase 1: Context Acquisition (5 min)

**Required Reads**:
```
1. handovers/0700_series/orchestrator_state.json → Understand series, your handover, dependencies
2. handovers/0700_series/comms_log.json → Read entries where to_handovers includes YOUR handover ID
3. handovers/0700_series/doc_impacts.json → See which docs you may need to update
4. handovers/[your_handover_spec].md → Full specification for your work
```

**Context Questions to Answer**:
- What did previous handovers change that affects me?
- Are there any blockers I need to address first?
- Which documentation files reference code I'll modify?

---

### Phase 2: Scope Investigation (15-30 min)

**Tasks**:
1. **Scan codebase** for items in your scope
   - Use Grep for DEPRECATED markers, TODO markers, etc.
   - Use Serena MCP tools for symbol analysis

2. **Identify all files** you'll modify
   - List them explicitly
   - Note which have tests

3. **Map to documentation**
   - Cross-reference with doc_impacts.json
   - Add any new docs you discover

4. **Create execution plan**
   - Order of operations
   - Test points
   - Rollback points

**Output**: Clear list of changes to make, in order

---

### Phase 3: Execution (Main Work)

**Rules**:
1. **Use appropriate subagents**:
   - `database-expert` for model/migration changes
   - `tdd-implementor` for code changes needing tests
   - `backend-integration-tester` for service layer
   - `deep-researcher` for investigation

2. **Test after each significant change**
   - Run relevant test files
   - Check for import errors
   - Verify no runtime breaks

3. **Track everything**
   - Files modified
   - Tests added/modified
   - Patterns established

4. **Stop if blocked**
   - Don't hack around problems
   - Write blocker to comms_log
   - Report to orchestrator

---

### Phase 4: Documentation (15-30 min)

**Required**:
1. **Review doc_impacts.json** for your handover ID
2. **For each listed doc**:
   - Read the current content
   - Check if your changes made it stale
   - Update code examples, references, descriptions
3. **Update doc_impacts.json**:
   - Set status to "updated" or "reviewed_no_changes"
   - Record yourself as updated_by

**What to Update**:
- Code examples that reference changed functions/classes
- Architecture descriptions that mention removed components
- API references for changed signatures
- "DEPRECATED" mentions that are now removed

---

### Phase 5: Communication (10 min)

**Write to comms_log.json**:

```json
{
  "id": "[generate UUID]",
  "timestamp": "[ISO timestamp]",
  "from_handover": "[your handover ID]",
  "to_handovers": ["[IDs of handovers that should read this]"],
  "type": "[info|warning|blocker|dependency|suggestion]",
  "subject": "[short subject]",
  "message": "[detailed message]",
  "files_affected": ["[list of files you changed]"],
  "action_required": [true|false],
  "context": { "[any structured data]" }
}
```

**When to Write**:
- You changed a function signature → warn downstream
- You established a pattern → suggest others follow it
- You found something concerning → info or warning
- You couldn't complete something → blocker
- Your change creates a dependency → dependency type

**Who to Address**:
- Check the dependency chain in orchestrator_state.json
- Your `to_handovers` should include handovers that come AFTER you
- Be specific: if only 0708 needs to know, don't include 0711

---

### Phase 6: Commit & Report (5 min)

**Update orchestrator_state.json**:
```json
{
  "status": "complete",
  "completed_at": "[ISO timestamp]",
  "worker_session_id": "[your session ID if known]",
  "docs_updated": ["[list of docs you updated]"]
}
```

**Commit**:
```bash
git add -A
git commit -m "cleanup(0XXX): [Title]

[2-3 sentence summary of changes]

Changes:
- [list key changes]

Docs Updated:
- [list docs updated]

Co-Authored-By: Claude Opus 4.5 <noreply@anthropic.com>"
```

**Report**:
Provide a completion summary:
- Tasks completed
- Tests passing
- Docs updated
- Comms log entries written
- Any issues for orchestrator attention

---

## Subagent Recommendations by Handover

| Handover | Primary Agent | Secondary Agents |
|----------|--------------|------------------|
| 0700a | `ux-designer` | `frontend-tester` |
| 0700 | `deep-researcher` | - |
| 0701 | `system-architect` | `deep-researcher` |
| 0702 | `tdd-implementor` | `backend-integration-tester` |
| 0703 | `tdd-implementor` | `backend-integration-tester` |
| 0704 | `database-expert` | `tdd-implementor` |
| 0705 | `database-expert` | `tdd-implementor` |
| 0706 | `database-expert` | `backend-integration-tester` |
| 0707 | `tdd-implementor` | `backend-integration-tester` |
| 0708 | `tdd-implementor` | `backend-integration-tester` |
| 0711 | `system-architect` | `tdd-implementor` |
| 0373 | `tdd-implementor` | - |

---

## Communication Examples

### Good: Specific, Actionable

```json
{
  "from_handover": "0705",
  "to_handovers": ["0706"],
  "type": "dependency",
  "subject": "Product.product_memory.sequential_history marked for removal",
  "message": "I added DEPRECATED comments to Product.product_memory.sequential_history with removal target v4.0. The field is still present but should NOT be written to. 0706 should verify AgentExecution.messages follows the same pattern before removal.",
  "files_affected": ["src/giljo_mcp/models/products.py"],
  "action_required": true
}
```

### Bad: Vague, Unhelpful

```json
{
  "from_handover": "0705",
  "to_handovers": ["0706", "0707", "0708", "0711"],
  "type": "info",
  "subject": "Changed some stuff",
  "message": "Made some model changes, FYI.",
  "files_affected": [],
  "action_required": false
}
```

---

## Error Handling

### Test Failures
1. Diagnose the failure
2. If it's pre-existing (not caused by your changes), note it and continue
3. If caused by your changes, fix before proceeding
4. If unfixable, write blocker to comms_log and stop

### Cascading Breaks
1. Immediately stop making changes
2. Run git status to see what's modified
3. Consider reverting to last good state
4. Write blocker describing the cascade
5. Consult orchestrator

### Unclear Scope
1. Write info entry to comms_log explaining confusion
2. Make conservative choices (less change is safer)
3. Note uncertainty in completion report
4. Let orchestrator decide if re-work needed

---

## Checklist Before Completing

- [ ] All tasks in handover spec completed
- [ ] All tests passing (or pre-existing failures documented)
- [ ] Relevant documentation updated
- [ ] doc_impacts.json updated with your changes
- [ ] comms_log.json has entry for downstream handovers
- [ ] orchestrator_state.json updated (status: complete)
- [ ] Changes committed with proper message
- [ ] Completion summary provided

---

**When in doubt, err on the side of communication. Future agents benefit from your notes!**
