# 0075 — Eight-Agent Active Limit (Archived Spec)

Status: Archived (specification only)
Date: 2025-10-30
Source: handovers/completed/0075_eight_agent_active_limit_enforcement-C.md

---

## Summary

Proposed enforcing a hard limit of 8 active agent templates to protect context budget in Claude Code sessions, add validation in template endpoints, and improve UX with notifications and backups before export.

This was not shipped; use as reference only. The current orchestration UI (0073) provides performance guidance and status visibility without enforcing a hard active-template limit.

### Key Ideas (Reference)
- Validate active template toggles (max 8) at API
- Orchestrator selects from active set only
- Export change detection and copy/backup safeguards

For full details, see: `handovers/completed/0075_eight_agent_active_limit_enforcement-C.md`.

