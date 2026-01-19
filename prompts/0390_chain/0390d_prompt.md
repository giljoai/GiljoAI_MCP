# Terminal Session: 0390d - Deprecate JSONB Column (FINAL)

## Mission
Execute Handover 0390d (Part 4/4 360 Memory JSONB Normalization) - **FINAL HANDOVER**.

## Handover Document
**READ THIS FIRST**: `F:\GiljoAI_MCP\handovers\0390d_deprecate_jsonb_column.md`

## CRITICAL: Use Task Tool Subagents
**YOU MUST use the Task tool to spawn subagents for this work. Do NOT do the work directly.**

Example:
```
Task(subagent_type="documentation-manager", prompt="Update CLAUDE.md and 360_MEMORY_MANAGEMENT.md per handover 0390d Phase 3...")
Task(subagent_type="backend-tester", prompt="Run full regression test suite per handover 0390d Phase 4...")
```

Recommended subagents for this handover:
- `documentation-manager` - For doc updates
- `backend-tester` - For final verification

## Prerequisite Check
Verify 0390c complete (all writes to table):
```bash
grep -rn "flag_modified.*product_memory" src/giljo_mcp/tools/
# Should show ONLY git_integration related
pytest tests/ -v --tb=short
```

## Execute
1. Read the handover document above completely
2. **Use Task tool subagents** to complete phases
3. Add deprecation comments
4. Remove dead code
5. Update documentation
6. Run final verification
7. Merge to master

## Success Criteria
- [ ] JSONB field marked deprecated in code
- [ ] No sequential_history reads/writes
- [ ] All tests pass (100% green)
- [ ] CLAUDE.md updated
- [ ] docs/360_MEMORY_MANAGEMENT.md updated
- [ ] Handover catalogue updated
- [ ] Branch merged to master
- [ ] Handovers archived to completed/

## CHAIN COMPLETE

This is the **FINAL** terminal in the 0390 chain.

When all success criteria are met:
1. Commit all changes
2. Merge to master
3. Archive handovers
4. Update catalogue

**DO NOT spawn another terminal. The chain is complete.**

## Final Commit Template
```bash
git add .
git commit -m "feat(0390): Complete 360 Memory JSONB to Table Migration

Migrates Product.product_memory.sequential_history JSONB array to
normalized product_memory_entries table.

- 0390a: Created table, model, repository, backfill migration
- 0390b: Switched all reads to table
- 0390c: Switched all writes to table
- 0390d: Deprecated JSONB field, updated docs

BREAKING: sequential_history JSONB is deprecated.
Use ProductMemoryRepository for all 360 memory operations.

Co-Authored-By: Claude Opus 4.5 <noreply@anthropic.com>"

git checkout master
git merge 0390-360-memory-normalization
git push origin master
```
