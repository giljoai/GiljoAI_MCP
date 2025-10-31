# 0075 Completion Summary: Eight‑Agent Active Limit Enforcement

Status: Retired/Archived (Specification Consolidated)
Date: 2025-10-31
Owner: Project 0075

---

## Executive Summary

Project 0075 defined a policy and validation flow to cap active Agent Templates to eight, protecting Claude Code context budget and improving performance/predictability. This closeout consolidates the specification and intended implementation details. The feature can be scheduled for implementation in a future iteration or superseded by higher‑level orchestration policies.

---

## Scope (Original Intent)

- Enforce a maximum of 8 active agent templates per tenant.
- Keep default seeded agents to a recommended 6; orchestrator selects only from the active set.
- Detect constellation changes that require re‑export of `.claude/agents/` and warn users.
- Auto‑backup `.claude/agents/` before export to prevent data loss.

Reference: handovers/0075_eight_agent_active_limit_enforcement-C.md

---

## Proposed Implementation (Consolidated)

Backend
- Validation helper `validate_active_agent_limit(db, tenant_key, template_id, new_is_active)` in `api/endpoints/templates.py`.
- Apply validation in PATCH `/api/templates/{template_id}` when toggling `is_active` to True.
- Use existing `AgentTemplate.is_active` (no schema change required).

Frontend
- UI feedback on toggle: toast + inline error if exceeding limit.
- Badge/notice to re‑export agents when the active constellation changes.
- Optional: export action performs pre‑export zip backup of `.claude/agents/`.

Operational
- Document rationale (context budget clamping) and recommended defaults (6–8 agents).

---

## Notes

- 0075 depends on Agent Template management (0041) and MCP integration (0069) but does not require DB migrations.
- The cap is enforced at toggle time; bulk enable flows should iterate with validation.
- Orchestrator should read only active templates by design (no code change if this is already the case).

---

## Archived Documents

- handovers/completed/0075_eight_agent_active_limit_enforcement-C.md

---

## Status

Project 0075 is retired as a consolidated specification. If prioritization shifts, this summary serves as the single source to implement the limit in a focused PR.

