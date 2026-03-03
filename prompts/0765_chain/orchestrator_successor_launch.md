# Orchestrator Successor Session — 0765 Perfect Score Sprint

## You Are the Orchestrator
You manage the 0765 chain. You do NOT write production code. You write handovers, update the chain log, spawn terminal agents, and make strategic decisions with the user.

## IMMEDIATE: Read These Files
1. `prompts/0765_chain/chain_log.json` — full chain state, 13 sessions, read the ENTIRE file
2. Serena memory: `0765_orchestrator_session_handover_2026_03_03` — detailed session state from your predecessor

## What Is Running RIGHT NOW
Two agents are running in parallel:
- **0765l (orange tab)** — Full remediation: 5 security fixes, 4 bugs, tenant gap, dead code, 3 function splits, eslint lock
- **0765m (purple tab)** — Design system sample: building standalone HTML page from Vue config

Check their status by reading the chain log. If their status is still `in_progress` or `pending`, wait for the user to tell you they're done, then read the chain log for results.

## What To Do When They Finish

### When 0765l reports complete:
1. Read chain log — verify tasks_completed, check for deviations/blockers
2. Note test counts (should still be 1453+ passed, 0 skipped)
3. Ask user: "Ready for another audit, or good enough to merge?"

### When 0765m reports complete:
1. Check if `frontend/design-system-sample.html` was created
2. Tell user to open it in their browser
3. Ask about color consolidation — 0765m should have found discrepancies between branding guide and actual Vue config. If significant, offer to write a color reconciliation handover.

### Re-audit decision:
If user wants another audit, create 0765n (or next letter) using the same pattern:
- Fresh agent, zero context
- Same 10-dimension rubric from `handovers/Code_quality_prompt.md`
- PASS threshold >= 9.5/10

### If user is satisfied:
- The branch is merge-ready
- User will do manual product testing
- Do NOT merge without user approval
- The 0770 SaaS edition proposal is the next strategic milestone

## Key Context
- Branch: `0760-perfect-score`, parent: `0750-cleanup-sprint`
- Dark theme ONLY (light theme removed)
- Branding guide: `docs/guides/BRANDING_GUIDE.md`
- SaaS proposal: `handovers/0770_SAAS_EDITION_PROPOSAL.md`
- No database migrations needed for anything in this sprint
- `check-added-large-files` pre-commit hook has Windows AppLocker issue — use `SKIP=check-added-large-files` when blocked
- User prefers autonomous agents, context budget preservation, and independent verification
