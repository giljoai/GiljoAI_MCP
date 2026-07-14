# Architecture Decision Records

This directory contains Architecture Decision Records (ADRs) for GiljoAI MCP.

ADRs document significant technical decisions, the context that drove them,
and the consequences of the choice. They are the institutional memory for
"why does the code work this way?"

## Format

Records follow the Michael Nygard / MADR-lite structure:
Status, Context, Decision, Consequences, Exceptions, References.
Each record targets ~100 lines. Lead with the rule, not the history.

## Records

| ID | Title | Status | Date |
|----|-------|--------|------|
| [ADR-001](ADR-001-frontend-url-resolution.md) | Frontend URL Resolution | Accepted | 2026-04-28 |
| [ADR-002](ADR-002-setup-driven-mode-source-of-truth.md) | Setup-Driven Mode Source of Truth | Accepted | 2026-04-28 |

## Edition Scope

`docs/adr/` is exported to the CE repo. Records here apply to all editions
(CE and SaaS) unless a record explicitly states otherwise. Never reference
SaaS-only internals, handover paths, or private repo paths in this directory.
