# CLAUDE.md -- Project Instructions for GiljoAI MCP

## Project Overview

GiljoAI MCP is an AI agent orchestration platform (the "Coding Orchestrator"). It ships as two editions from a single repository: **Community Edition (CE)** on the `main` branch (public) and **SaaS Edition** on the `saas` branch (private). Enterprise is a deployment mode of SaaS, NOT a separate edition or branch.

## Edition Isolation (MANDATORY -- read this first)

Before writing ANY code, read `docs/EDITION_ISOLATION_GUIDE.md`.
Before starting ANY handover, read `handovers/HANDOVER_INSTRUCTIONS.md`.
Every handover MUST include: `**Edition Scope:** CE | SaaS | Both`

**Directory rule:** CE code lives in standard directories. SaaS-only code lives in `saas/`, `saas_endpoints/`, `saas_middleware/`, `frontend/src/saas/`. CE code NEVER imports from any `saas/` directory.

**The Deletion Test:** If all `saas/`, `saas_endpoints/`, `saas_middleware/`, and `frontend/src/saas/` directories were deleted, CE must still start, serve requests, and pass all tests. If not, there is a dependency leak -- fix it.

**Placement Decision Tree:**
- Needs Stripe/Twilio/OAuth/LDAP or only makes sense with multiple orgs? --> `saas/` directory
- Improves core orchestration for any user including solo? --> CE directory
- Already exists in CE (TenantManager, Organization model, auth)? --> stays in CE, do NOT move

**SaaS Extension Pattern:** CE provides the foundation. SaaS extends via EventBus subscriptions and conditional router registration. CE never knows about SaaS.

## Tech Stack

- **Backend:** Python 3.12+, FastAPI, SQLAlchemy 2.0, Alembic, PostgreSQL 18
- **Frontend:** Vue 3 (Composition API), Pinia, Vuetify 3, Vite
- **Real-time:** WebSocket via PostgresNotifyBroker
- **Auth:** JWT httpOnly cookies, CSRF double-submit
- **Network:** Server binds 0.0.0.0, OS firewall controls access
- **Dev environment:** Windows

## Code Conventions

- Every database query MUST filter by `tenant_key` -- no exceptions
- No AI signatures in code or commits
- Never use terms "MIT", "open source", or "open core" -- license is GiljoAI Community License v1.1
- Pre-commit hooks: never bypass with `--no-verify` without explicit user approval
- All Python layers raise exceptions on error (post-0480) -- never `return {"success": False, ...}`
- No function exceeds 200 lines, no class exceeds 1000 lines without justification
- No commented-out code -- delete it, git has the history
- Search before you build: use existing services, managers, and repositories
- Handover numbering: check `handovers/handover_catalogue.md` for the catalogue and available gaps
- Database migrations: incremental migrations must include idempotency guards; baseline is squashed periodically (see `handovers/HANDOVER_INSTRUCTIONS.md` Migration Protocol)
- **Smooth borders on rounded elements:** Never use CSS `border` on rounded cards, chips, or pill buttons. Use the global `smooth-border` class from `main.scss` which applies `box-shadow: inset` instead. This renders anti-aliased curves on all zoom levels and Windows display scaling. Variants: `.smooth-border` (1px theme), `.smooth-border-2` (2px theme), `.smooth-border-accent` (2px brand yellow). Custom color: `style="--smooth-border-color: #hex"`.

## Key Documents

- `docs/EDITION_ISOLATION_GUIDE.md` -- where to put code (CE vs SaaS), the authoritative reference
- `handovers/HANDOVER_INSTRUCTIONS.md` -- handover protocol, agent operating rules, quality gates
- `handovers/handover_catalogue.md` -- all handovers with numbers, active and completed
- `docs/README_FIRST.md` -- documentation navigation hub
- `docs/SERVER_ARCHITECTURE_TECH_STACK.md` -- system architecture and network topology
- `LICENSING_AND_COMMERCIALIZATION_PHILOSOPHY.md` -- licensing terms and commercial strategy
