> **SUPERSEDED (2026-03-08):** This document has been replaced by `docs/EDITION_ISOLATION_GUIDE.md` as the authoritative reference for edition strategy and code isolation. The guide below is retained for historical context only. If any guidance below conflicts with the Edition Isolation Guide, the Guide takes precedence.

---

# GiljoAI MCP — Edition Strategy & Architecture Brief

**Date:** 2026-03-07
**Purpose:** Context document for any agent working on the GiljoAI MCP codebase. Explains the two-edition product strategy and how it affects all architecture, code, and documentation decisions.

---

## The Core Idea

GiljoAI MCP Coding Orchestrator is a single product developed in a single repository today. Before public release, it will split into two editions shipped from two repos:

1. **Community Edition** (public repo) — Free for single-user use under the GiljoAI Community License v1.0
2. **SaaS Edition** (private repo) — Multi-user, subscription-based, commercial license

The private SaaS repo will import the public Community repo as a dependency and layer SaaS-only features on top. This means the Community Edition codebase must be clean, self-contained, and architecturally complete on its own — it is the foundation that SaaS builds upon, not a stripped-down version of SaaS.

---

## What This Is NOT

- **Not open source.** The GiljoAI Community License v1.0 is not OSI-approved. Do not use terms like "MIT," "open source," or "open core" anywhere in code, docs, or UI.
- **Not a freemium SaaS.** Community Edition is a locally installed, self-hosted product. SaaS Edition is a separately deployed, separately licensed product.
- **Not two codebases doing the same thing differently.** SaaS extends Community. It never forks or replaces it.

---

## What Stays in Community Edition (Public Repo)

| Component | Description |
|-----------|-------------|
| Core orchestration engine | Mission planning, agent coordination, context management |
| Agent management | Templates, spawning, communication, job lifecycle |
| Single-user auth | Login/password, JWT, single admin user |
| Tenant isolation infrastructure | All tenant_key filtering stays in place — hidden in single-user mode but fully functional. This was already hardened across 35+ code paths with 53 regression tests. It is the foundation SaaS builds on. |
| WebSocket & MCP protocol | Real-time communication, MCP tool integration |
| Frontend dashboard | Full UI for projects, agents, messages, settings |
| CE branding + licensing check | Edition badge, 30-day licensing reminder |

## What Goes to SaaS Edition (Private Repo)

| Component | Description |
|-----------|-------------|
| OAuth / MFA / SSO | Enterprise auth providers, multi-factor |
| Billing & subscription | Stripe integration, plan enforcement, usage tracking |
| Organization & team management | Multi-org, roles, team structure |
| Multi-user admin tools | User management, org-level settings |
| Usage analytics & metering | API call tracking, agent hours, storage |
| SaaS onboarding flows | Trial/freemium, org setup wizard |
| SaaS deployment configs | Docker/K8s, horizontal scaling, Redis state |

---

## Why Tenant Isolation Matters Now

The Community Edition runs as a single-user local install with one tenant. But the tenant isolation layer (tenant_key filtering on every database query) is kept fully intact because:

1. **SaaS depends on it.** When SaaS Edition imports Community as a dependency, multi-tenant isolation must already work. Retrofitting tenant isolation into a running SaaS product is one of the most expensive things you can do in software.
2. **It's already done.** A full security audit remediated all CRITICAL (5), HIGH (20), and MEDIUM (10) isolation findings across 5 commits with 53+ regression tests. Every `session.get()` bypass has been replaced with tenant-scoped queries.
3. **It costs nothing to keep.** The infrastructure is invisible to a single-user — it just works. Removing it would create technical debt that SaaS would have to repay.

**Data hierarchy:** org → tenants (admins/users) → products → projects → jobs. Each level is tenant-scoped. Child entities are isolated both by their parent chain and by explicit tenant_key WHERE clauses (defense in depth).

---

## How This Affects Your Work

### If you're writing code:
- Every database query must filter by `tenant_key`. No exceptions, even for Community Edition.
- Design interfaces so they can be extended by SaaS without changing callers (e.g., `read_config()` returns a dict today, but should be replaceable with env-var or per-tenant config later).
- Never hardcode single-user assumptions. Use the existing tenant infrastructure even when there's only one tenant.

### If you're writing documentation or diagrams:
- Label system-wide architecture diagrams as "Community Edition" scope.
- If a diagram shows multi-user features (multiple Developer PCs, multi-org), annotate it as "SaaS Edition" or "SaaS Edition only (not in Community)."
- If a diagram shows deployment topology, note: "Community Edition: single-user local install. SaaS Edition: Docker/K8s multi-tenant deployment."
- Never reference MIT, open source, or open core.

### If you're working on the installer or setup flow:
- Community Edition installs locally, single admin user created via setup wizard.
- No default credentials — user creates everything during first run.
- The setup flow is for one user. Multi-user onboarding is SaaS Edition scope.

### If you're working on the frontend:
- The UI should display "Community Edition" branding (edition badge).
- Features that only exist in SaaS (billing, org management, team roles) should never appear in Community Edition UI.
- Tenant isolation is transparent — the frontend passes the JWT, the backend handles scoping.

---

## Branding Reference

| Field | Value |
|-------|-------|
| Product name | GiljoAI MCP Coding Orchestrator |
| Tagline | "Break through AI context limits. Orchestrate teams of specialized AI agents." |
| Community Edition label | Community Edition |
| License | GiljoAI Community License v1.0 |
| License short form | "GiljoAI Community License v1.0 — Free for single-user use" |
| Website | giljoai.com |
| Terms to never use | "MIT," "open source," "open core" |

---

## Summary for Quick Reference

**One product, two editions, two repos.** Community is the public foundation — complete, functional, single-user. SaaS is the private extension — multi-user, subscription, enterprise. SaaS imports Community as a dependency. Tenant isolation stays in both. Never call it open source.
