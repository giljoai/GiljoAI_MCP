## Execute
Execute Handover 0511a (NOT 0511) following production-grade standards.

**Handover Document**: F:\GiljoAI_MCP\handovers\0511a_smoke_tests_critical_workflows.md
**Master Plan**: F:\GiljoAI_MCP\handovers\Projectplan_500.md
**Architecture**: F:\GiljoAI_MCP\CLAUDE.md
**Completion Format**: F:\GiljoAI_MCP\handovers\HANDOVER_INSTRUCTIONS.md

---

## PHASE 2 COMPLETION SUMMARY

**Status:** ✅ COMPLETE
**Completed:** 2025-11-13
**Actual Effort:** 7 hours (estimated 7-8 hours, on target)

### Deliverables
✅ **Frontend Fixes Complete**:
- API Client URL alignment: All endpoints match backend exactly
- Vision upload error handling: Zero silent failures, comprehensive user feedback
- Succession UI: Timeline component + Launch Dialog with thin-client prompts

✅ **Production-Grade Code**:
- 1,900+ lines of frontend code (Vue components + API client updates)
- 646 lines of comprehensive tests (32 test suites across 3 spec files)
- Token-efficient documentation throughout

### Git Commits (All 3 Handovers)
- **0507**: API Client fixes (API client URL alignment)
- **0508**: Vision error handling (comprehensive user feedback)
- **0509**: Succession UI components (Timeline + Launch Dialog)

### Handovers Completed
- ✅ 0507: API Client URL Fixes - ARCHIVED
- ✅ 0508: Vision Upload Error Handling - ARCHIVED
- ✅ 0509: Succession UI Components - ARCHIVED

### Next Steps
**Phase 3 (Integration Testing)** - READY for sequential execution in CLI:
- 0510 (Fix Broken Test Suite) ← YOU ARE HERE
- 0511 (E2E Integration Tests)

**Unblocked:** Phase 3 can now begin ✅

---

# Project 0500 Series Execution Prompt Template

## Copy-Paste Prompt for Agentic Coding Tools
 Notes for Future Handovers

  - Serena MCP saved significant time - Used get_symbols_overview and find_symbol instead of reading full files
  - Production-grade code only - No TODO comments, no placeholders, no bandaids
  - Token-efficient documentation - Inline comments optimized for AI agent consumption
  - Existing patterns followed - Used VisionDocumentRepository and VisionDocumentChunker as designed

Execute Handover 0507 following production-grade standards.

## Project Context

**Handover Document**: F:\GiljoAI_MCP\handovers\0506_settings_endpoints.md
**Master Plan**: F:\GiljoAI_MCP\handovers\Projectplan_500.md
**Architecture**: F:\GiljoAI_MCP\CLAUDE.md
**Completion Format**: F:\GiljoAI_MCP\handovers\HANDOVER_INSTRUCTIONS.md

## Quality Standards

**Production-Grade Code Only**:
- ✅ Commercial-quality implementation
- ✅ Follow existing patterns in codebase
- ✅ >80% test coverage
- ❌ NO bandaids or temporary solutions
- ❌ NO shortcuts or "TODO: fix later" comments
- ❌ NO placeholder implementations

## Tools Available
***CRITICAL*** YOU MUST USE CLAUDE CODE SUBAGENTS

**Serena MCP** (REQUIRED for code navigation):
- Use `mcp__serena__get_symbols_overview` before reading files
- Use `mcp__serena__find_symbol` for precise navigation
- Use `mcp__serena__replace_symbol_body` for edits
- Read Serena Instructions: `mcp__serena__initial_instructions`

**Integrated Subagents/Skills**:
- Use Task tool with appropriate subagent_type when beneficial
- backend-tester for API testing
- database-expert for schema work
- tdd-implementor for test-first development
- Use skills for specialized operations (pdf, xlsx, etc.)

**Memory System**:
- Read relevant memories: `mcp__serena__list_memories` then `mcp__serena__read_memory`
- Write discoveries: `mcp__serena__write_memory`

## Execution Pattern

***CRITICAL*** YOU MUST USE CLAUDE CODE SUBAGENTS

### Phase 1: PLAN
1. Read handover document thoroughly
2. Use Serena to explore affected files (`get_symbols_overview`, `find_symbol`)
3. Read relevant memories for context
4. Create execution plan with TodoWrite tool
5. Identify dependencies and risks
6. Only engage developer with questions if you need significant decisions related to vision, direction or significant cascading consequences.

***CRITICAL*** YOU MUST USE CLAUDE CODE SUBAGENTS

### Phase 2: IMPLEMENT
1. Follow handover implementation tasks sequentially
2. Use Serena for precise code navigation and editing
3. Write production-grade code following existing patterns
4. Add comprehensive inline documentation (for AI agents, token-efficient)
5. Mark todos as completed as you finish each task

***CRITICAL*** YOU MUST USE CLAUDE CODE SUBAGENTS

### Phase 3: TEST
1. Write unit tests (>80% coverage target)
2. Write integration tests if specified
3. Run test suite: `pytest tests/ -v`
4. Fix any failures immediately
5. Validate against handover success criteria

***CRITICAL*** YOU MUST USE CLAUDE CODE SUBAGENTS

### Phase 4: COMMIT
1. Review all changes: `git status`, `git diff`
2. Stage changes: `git add [files]`
3. Commit with descriptive message following this format:

  CRITICAL RULE: Before creating a PR, ALWAYS run:
```bash
git fetch origin
git rebase origin/master

git commit -m "$(cat <<'EOF'
[handover_id]: [brief_summary]

[Detailed description of changes - bullet points]

Success Criteria Met:
- [List criteria from handover]

Files Changed:
- [List modified files]

Tests Added:
- [List new test files/functions]
Have a great day!
EOF
)"
```
***CRITICAL*** YOU MUST USE CLAUDE CODE SUBAGENTS
### Phase 5: REITERATE
1. Re-read handover success criteria
2. Validate each criterion is met
3. If any criterion fails:
   - Identify gap
   - Implement fix
   - Test again
   - Commit fix
4. Repeat until all criteria pass
***CRITICAL*** YOU MUST USE CLAUDE CODE SUBAGENTS
### Phase 6: VALIDATE
1. Run full test suite: `pytest tests/ -v --cov`
2. Check test coverage: Should be >80%
3. Manual testing per handover testing strategy
4. Database validation queries (if applicable)
5. Verify no regressions: All existing tests still pass
***CRITICAL*** YOU MUST USE CLAUDE CODE SUBAGENTS
### Phase 7: DOCUMENT
1. Update handover document with "COMPLETE" status
2. Add completion summary:
   - Actual effort vs estimated
   - Challenges encountered
   - Deviations from plan
   - Lessons learned
3. Write to Serena memory if useful for future handovers
4. Update any affected documentation (CLAUDE.md, etc.)

### Phase 8: CLOSE OUT
1. Follow instructions in `F:\GiljoAI_MCP\handovers\HANDOVER_INSTRUCTIONS.md`
2. Move handover to completed: `handovers/completed/[ID]_[name]-COMPLETE.md`
3. Update Projectplan_500.md status table
4. Archive format per HANDOVER_INSTRUCTIONS.md:
   - Add completion timestamp
   - Add final metrics (effort, files changed, tests added)
   - Add successor references (what handover unlocks next)
5. Clean up todos: Mark all as completed, remove stale items

## Documentation Style for AI Agents

**Token-Efficient Documentation**:
```python
# ProductService.upload_vision() - Chunks docs to <25K tokens using EnhancedChunker
# Args: product_id, file_content, filename, auto_chunk=True, max_tokens=25000
# Returns: {success, document_id, chunk_count, total_tokens}
# Raises: ValueError if product not found or user lacks access
```

NOT this (too verbose for agents):
```python
"""
This method uploads a vision document for the specified product.
It will automatically chunk large documents to ensure each chunk
is under the maximum token limit. The chunking uses semantic
boundaries to preserve meaning across chunk borders.

Parameters:
    product_id (str): The UUID of the product to upload the vision for
    file_content (bytes): The raw file bytes to upload
    ...
"""
```

## Git Workflow

**Branch Naming**:
- CLI handovers: Work on current branch (master or feature branch)
- CCW handovers: Already on feature branch (CCW creates it)

**Commit Checkpoints**:
- After each major task completion
- After tests pass
- Before moving to next phase
- Never commit broken code

**Commit Message Format**:
- First line: `[handover_id]: [summary]` (max 72 chars)
- Body: Detailed bullet points
- Footer: Success criteria, files changed, tests added, attribution

## Success Criteria Validation
***CRITICAL*** YOU MUST USE CLAUDE CODE SUBAGENTS
Before closing out, verify EVERY criterion from handover document:
- [ ] All implementation tasks completed
- [ ] All tests pass (unit + integration)
- [ ] Test coverage >80%
- [ ] No HTTP 501/404 errors (if applicable)
- [ ] Manual testing completed per handover
- [ ] Database validation queries pass (if applicable)
- [ ] No regressions (existing functionality works)
- [ ] Documentation updated
- [ ] Handover-specific criteria met

## Common Pitfalls to Avoid

❌ **DON'T**:
- Skip reading the full handover document
- Implement without exploring existing code patterns
- Write tests after implementation (do TDD when possible)
- Commit without running tests
- Close out without validating ALL success criteria
- Leave TODO comments in production code
- Use placeholder implementations
- Skip documentation updates

✅ **DO**:
***CRITICAL*** YOU MUST USE CLAUDE CODE SUBAGENTS
- Use Serena MCP for efficient code navigation
- Follow existing patterns in codebase
- Write token-efficient documentation for AI agents
- Commit frequently at logical checkpoints
- Validate rigorously before close out
- Use integrated subagents when beneficial
- Read memories for context
- Write memories for discoveries

## Example Execution

```
Execute Handover 0500 following production-grade standards.

[Copy paste the template above, replacing [PROJECT_NUMBER] with 0500]

Starting Phase 1: PLAN...
Reading handover document: F:\GiljoAI_MCP\handovers\0500_productservice_enhancement.md
Using Serena to explore ProductService...
[continues through all 8 phases]
...
Phase 8: CLOSE OUT complete.

Handover 0500 successfully completed.
- Estimated effort: 4 hours
- Actual effort: 5.5 hours
- Files changed: 3
- Tests added: 8 (100% passing)
- Success criteria: 5/5 met

Next handover: 0501 (blocked until 0500 merged)
```

---

**Status**: Template ready for use
**Usage**: Copy the prompt section, replace [PROJECT_NUMBER], execute
**Archive**: Keep this template for all 0500 series handovers


---

## Usage Instructions
***CRITICAL*** YOU MUST USE CLAUDE CODE SUBAGENTS
1. Copy the prompt from "Execute Handover..." to the end
2. Replace `[PROJECT_NUMBER]` with actual handover (e.g., 0500, 0501, etc.)
3. Replace `[name]` with handover name (e.g., productservice_enhancement)
4. Paste into Claude Code CLI or CCW
5. Agent will follow the 8-phase pattern automatically

## Example for Handover 0500


Execute Handover 0500 following production-grade standards.
***CRITICAL*** YOU MUST USE CLAUDE CODE SUBAGENTS
## Project Context

**Handover Document**: F:\GiljoAI_MCP\handovers\0500_productservice_enhancement.md
**Master Plan**: F:\GiljoAI_MCP\handovers\Projectplan_500.md
**Architecture**: F:\GiljoAI_MCP\CLAUDE.md
**Completion Format**: F:\GiljoAI_MCP\handovers\HANDOVER_INSTRUCTIONS.md

[... rest of template ...]
```
