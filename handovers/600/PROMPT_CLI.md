# CLI Agent Launch Prompt (Local Execution)

**Use this prompt when running agents locally (Claude Code CLI) with database access.**

---

## Copy-Paste Prompt Template

```
You are working on Project 600 (Complete System Restoration & Validation) for the GiljoAI MCP codebase.

**Your Handover**: handovers/600/[HANDOVER_NUMBER]_[HANDOVER_NAME].md

**Project Root**: F:\GiljoAI_MCP

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

**Required Reading** (in this order):
1. handovers/600/AGENT_REFERENCE_GUIDE.md - Read this FIRST for universal project context
2. Your specific handover file - Contains all objectives, tasks, success criteria, validation steps

**Execution Mode**: CLI (Local)
- Database access: PostgreSQL localhost:5432 (password: 4010)
- Database name: giljo_mcp
- Local file system: Full read/write access
- Git: Commit directly to master branch after validation
- Testing: Run real pytest with database fixtures

**Your Tasks**:
1. Read AGENT_REFERENCE_GUIDE.md to understand the project
2. Read your handover file completely
3. Execute all tasks in sequence as specified
4. Create all deliverables (code, tests, docs)
5. Run all validation steps
6. Verify all success criteria are met
7. Commit to master with message format specified in handover
## Phase 4: COMMIT
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

**Quality Standards**:
- Follow all patterns from AGENT_REFERENCE_GUIDE.md
- No placeholders or TODOs
- All tests must pass
- Production-grade code only
- Comprehensive error handling

Execute the handover specification. Do not ask for permission - the handover file contains complete instructions. use subagents
```

---

## Usage Instructions

1. **Copy the prompt above**
2. **Replace placeholders**:
   - `[HANDOVER_NUMBER]` → e.g., `0600`, `0601`, `0602`, etc.
   - `[HANDOVER_NAME]` → e.g., `comprehensive_system_audit`, `fix_migration_order`, etc.
3. **Paste into Claude Code CLI**
4. **Agent will execute directly on master branch**

---

## Examples

### Example 1: Handover 0600 (System Audit)
```
You are working on Project 600 (Complete System Restoration & Validation) for the GiljoAI MCP codebase.

**Your Handover**: handovers/600/0600_comprehensive_system_audit.md

**Project Root**: F:\GiljoAI_MCP

[... rest of template ...]

Execute the handover specification. Do not ask for permission - the handover file contains complete instructions. use subagents
```

### Example 2: Handover 0601 (Fix Migration Order)
```
You are working on Project 600 (Complete System Restoration & Validation) for the GiljoAI MCP codebase.

**Your Handover**: handovers/600/0601_fix_migration_order.md

**Project Root**: F:\GiljoAI_MCP

[... rest of template ...]

Execute the handover specification. Do not ask for permission - the handover file contains complete instructions. use subagents
```

---

## CLI Handovers List

**Phase 0** (Sequential):
- 0600_comprehensive_system_audit.md
- 0601_fix_migration_order.md
- 0602_establish_test_baseline.md

**Phase 3** (Sequential):
- 0619_core_workflows_e2e.md
- 0620_orchestration_workflows_e2e.md
- 0621_advanced_workflows_e2e.md

**Phase 4** (Sequential):
- 0622_self_healing_decorators.md
- 0623_schema_consolidation.md

**Phase 5** (Sequential):
- 0624_unit_test_suite_completion.md
- 0625_integration_test_suite_completion.md
- 0626_e2e_performance_benchmarks.md

---

**Document Control**:
- **File**: PROMPT_CLI.md
- **Purpose**: Standard prompt template for local CLI agent execution
- **Usage**: Copy-paste for each CLI handover, replace placeholders
- **Created**: 2025-11-14
