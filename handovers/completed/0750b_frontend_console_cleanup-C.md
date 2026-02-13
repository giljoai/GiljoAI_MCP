# Handover 0750b: Frontend Console.log + Dependency Cleanup

**Date**: 2026-02-11
**Series**: 0750 Final Scrub (Part 2/3)
**Branch**: `cleanup/post-0745-audit-fixes` (continue existing)
**Predecessor**: 0750a (Backend Except Cleanup)

---

## Context

In the previous cleanup session (commit 7f0cdf33), 75 console.log statements were removed from the top 10 frontend files. Approximately 100 more remain across ~35 files. Additionally, npm vulnerabilities should be patched.

The 41 dead API methods and 2 unused components were already removed in commit 7f0cdf33.

## Task

### Task 1: Remove remaining console.log statements

Search all `.vue` and `.js` files under `frontend/src/` for `console.log` statements and remove them.

**Rules:**
- Remove `console.log(...)` calls completely (the entire statement)
- KEEP `console.warn(...)` and `console.error(...)` - these are intentional
- KEEP any console.log inside a `if (import.meta.env.DEV)` block (dev-only logging)
- If removing a console.log leaves an empty if/else/catch block, remove the block too (or add a comment if the block structure is needed)
- Do NOT remove console.log from test files (`*.spec.js`, `*.test.js`)

**Approach:** Work through files systematically. Use `grep -r "console.log" frontend/src/ --include="*.vue" --include="*.js" -l` to get the file list, then clean each file.

### Task 2: npm audit fix

```bash
cd frontend && npm audit fix
```

If `npm audit fix` suggests breaking changes (`--force`), do NOT apply them. Only apply safe fixes. Report any remaining vulnerabilities in the chain log.

### Task 3: Verify frontend build

```bash
cd frontend && npm run build
```

The build MUST pass. If it fails, fix the issue (likely a missing variable that was only used in a removed console.log).

## Verification

1. `grep -r "console.log" frontend/src/ --include="*.vue" --include="*.js" | wc -l` should be 0 (or near-zero if dev-only blocks kept)
2. `cd frontend && npm run build` passes
3. `npm audit` shows 0 vulnerabilities (or only unfixable ones)

## Success Criteria

- [ ] All non-dev console.log removed from frontend/src/
- [ ] npm audit fix applied (safe fixes only)
- [ ] Frontend build passes
- [ ] Changes committed to branch

---

## Chain Execution Instructions

### Step 1: Read Chain Log
Read `prompts/0750_chain/chain_log.json`
- Review 0750a's `notes_for_next` for any important context
- Verify 0750a status is `complete`
- If 0750a is `blocked` or `failed`, STOP and report: "Previous session failed, cannot continue chain"

### Step 2: Mark Session Started
Update session 0750b in chain_log.json: `"status": "in_progress", "started_at": "<timestamp>"`

### Step 3: Execute Handover Tasks

**CRITICAL: Use Task tool to spawn subagents for this work. Do NOT do all work directly.**

Recommended approach - spawn TWO parallel agents:

Agent 1 - Console.log removal:
```
Task(subagent_type="frontend-tester", prompt="Remove all console.log statements from Vue and JS files under frontend/src/. Search with grep first to get file list. Remove the entire console.log(...) statement. KEEP console.warn and console.error. KEEP console.log inside if(import.meta.env.DEV) blocks. Do NOT touch test files. If removing leaves empty blocks, clean those up too. Work through all files systematically.")
```

Agent 2 - npm audit:
```
Task(subagent_type="version-manager", prompt="Run npm audit fix in the frontend/ directory. Only apply safe fixes (no --force). Then run npm run build to verify the build passes. Report any remaining vulnerabilities.")
```

After agents complete:
1. Verify `grep -r "console.log" frontend/src/ --include="*.vue" --include="*.js"` returns minimal results
2. Verify `cd frontend && npm run build` passes
3. Stage and commit all changes

### Step 4: Update Chain Log
Update `prompts/0750_chain/chain_log.json` for session 0750b:
- `tasks_completed`: What was done
- `deviations`: Any changes from plan
- `notes_for_next`: Remaining issues for final audit
- `summary`: 2-3 sentences
- `status`: "complete"
- `completed_at`: "<timestamp>"

### Step 5: Spawn Next Terminal
**Use Bash tool to EXECUTE this command (Don't Just Print It!):**

```powershell
powershell.exe -Command "Start-Process wt -ArgumentList '--title \"0750c - Final Audit & Archive\" --tabColor \"#F44336\" -d \"F:\GiljoAI_MCP\" cmd /k claude --dangerously-skip-permissions \"Execute handover 0750c. READ F:\GiljoAI_MCP\handovers\0750c_final_audit_archive.md for full instructions. Check chain log at F:\GiljoAI_MCP\prompts\0750_chain\chain_log.json first.\"' -Verb RunAs"
```

**CRITICAL: DO NOT SPAWN DUPLICATE TERMINALS! Only ONE agent should spawn the next terminal. If your subagent already spawned it, DO NOT spawn again.**
