# 0700 Series Continuation - Orchestrator Kickoff

## Context

You are continuing orchestration of the **0700 Code Cleanup Series** for GiljoAI MCP v1.0 release. A previous orchestrator completed 0720 (delinting) and 0725 (code health audit). You need to review findings and create/execute follow-up handovers.

---

## CRITICAL: Read These Files First

### 1. Session Memory (Start Here)
```
F:\GiljoAI_MCP\handovers\0700_series\SESSION_MEMORY_0700_CLEANUP_ORCHESTRATION.md
```
This contains the complete history of what was done across 6-7 compacted conversations.

### 2. Orchestrator State (Read in Chunks - Large File)
```
F:\GiljoAI_MCP\handovers\0700_series\orchestrator_state.json
```
Contains status of all handovers in the series. Use:
```bash
cat handovers/0700_series/orchestrator_state.json | jq '.handovers[] | {id, status, title}' | head -80
```

### 3. 0725 Audit Report & Findings
```
F:\GiljoAI_MCP\handovers\0725_AUDIT_REPORT.md           # Main report
F:\GiljoAI_MCP\handovers\0725_findings_orphans.md       # Orphan code
F:\GiljoAI_MCP\handovers\0725_findings_naming.md        # Naming issues
F:\GiljoAI_MCP\handovers\0725_findings_coverage.md      # Test coverage
F:\GiljoAI_MCP\handovers\0725_findings_architecture.md  # Architecture
F:\GiljoAI_MCP\handovers\0725_findings_deprecation.md   # Deprecation
```

### 4. Serena Memories
```bash
# Use mcp__serena__read_memory for:
- 0720_delinting_project_status
- 0700_orchestrator_session_state
- project_overview
```

---

## Current State

### Completed
- **0700a-0709**: Deprecated code removal, lint, types, security
- **0720**: Zero lint errors achieved
- **0725**: Code health audit complete with findings

### Pending
- Review 0725 findings
- Create follow-up handovers (0726-0729 reserved)
- Execute follow-up work
- Final v1.0 readiness assessment

### Git Status
```bash
cd F:/GiljoAI_MCP
git status  # Check for uncommitted 0725 files
git log --oneline -10
```

---

## Your Mission

### Step 1: Understand State
1. Read session memory completely
2. Read orchestrator_state.json (note: large file, read in chunks)
3. Read Serena memories
4. Check git status

### Step 2: Review 0725 Findings
1. Read the audit report
2. Read each findings file
3. Categorize issues:
   - **Critical (v1.0 blocker)**: Must fix before release
   - **Important**: Should fix, can delay briefly
   - **Minor (post-v1.0)**: Nice to have

### Step 3: Create Follow-up Handovers
Based on 0725 findings, create handover specs:
- **0726**: [Based on findings]
- **0727**: [Based on findings]
- **0728**: [Based on findings]
- **0729**: [Based on findings]

### Step 4: Update Orchestrator State
Add new handovers to `orchestrator_state.json`

### Step 5: Execute or Delegate
Either execute handovers yourself or provide kickoff prompts for agents.

---

## Key Policies

### Pre-commit Hooks
**DO NOT use `--no-verify` without user approval.**
See `.pre-commit-config.yaml` and `CLAUDE.md` for policy.

### Validation-First
Launch research agents to validate scope BEFORE executing handovers.

### Communication
Update `orchestrator_state.json` after each handover completes.

---

## Commands Reference

```bash
# Environment setup
cd F:/GiljoAI_MCP
source venv/Scripts/activate

# Verify lint status
ruff check src/ api/

# Read large JSON in chunks
cat handovers/0700_series/orchestrator_state.json | jq '.handovers | length'
cat handovers/0700_series/orchestrator_state.json | jq '.handovers[0:10]'
cat handovers/0700_series/orchestrator_state.json | jq '.handovers[10:20]'

# Check 0725 findings
ls -la handovers/0725_*.md
wc -l handovers/0725_*.md

# Git operations
git status
git log --oneline -15
git diff --stat
```

---

## Success Criteria

- [ ] Session memory read and understood
- [ ] Orchestrator state reviewed
- [ ] 0725 findings categorized by priority
- [ ] Follow-up handovers created (0726-0729)
- [ ] Critical issues identified for v1.0
- [ ] Orchestrator state updated
- [ ] Ready to execute or delegate follow-up work
