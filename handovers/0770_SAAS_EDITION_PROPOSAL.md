# 0770: SaaS / Community / Enterprise Edition Planning

**Date:** 2026-03-03
**Status:** DECISIONS RECORDED (2026-03-07) — Key strategic decisions resolved
**Priority:** Strategic planning
**Prerequisite:** 0765 series complete (10/10 code quality baseline)
**Decision maker:** Gil

---

## Context

The GiljoAI MCP codebase is approaching 10/10 code quality via the 0765 sprint series. The next strategic decision is how to split the codebase for three deployment models. This document frames the discussion — no code changes until decisions are made.

---

## Three Editions

| Edition | Installed by | Users | Tenancy | Install method |
|---------|-------------|-------|---------|---------------|
| **Community** | End users | Single user, single product | None (stripped) | install.py |
| **Enterprise** | Corporate IT | Multi-user on WAN/LAN | Single org, one tenant key | install.py |
| **SaaS** | Gil only | Multi-org, multi-user | Full multi-tenancy | Docker/K8s, not install.py |

---

## Key Decisions Needed

### D1: Fork Strategy

**Option A: Hard fork (recommended in inception session)**
- Tag `v1.0-saas-baseline` after 0765 completes
- Create `community` branch — strip TenantManager, org models, multi-product routing
- SaaS continues on `main`
- Community gets periodic cherry-picks from SaaS

**Option B: Feature flags in single codebase**
- Single codebase, `EDITION=community|enterprise|saas` env var
- TenantManager becomes a no-op in community mode
- More maintenance burden, less code divergence

**Option C: Monorepo with shared core**
- Shared `core/` package, edition-specific wrappers
- Cleanest architecture, highest upfront cost

**Option D: Single repo now, split before publish (hybrid)**
- Build everything (SaaS, OAuth, billing) in the single repo
- Split into public (Community) + private (SaaS) repos before publishing
- Private repo imports public repo as a dependency, layers SaaS on top
- Avoids merge debt while keeping development velocity

**DECIDED (2026-03-07):** Option D chosen — single repo now, plugin/extension
split before publish. Private repo layers SaaS on top of public Community repo.

**Tradeoffs (historical context):**
- A is fastest to ship community edition but creates merge debt
- B keeps one codebase but adds complexity everywhere
- C is best long-term but requires significant restructuring
- D (chosen) balances development speed with clean separation at publish time

### D2: Tenant Key Provisioning (SaaS + Enterprise)

**Decided (2026-03-03 discussion):**
- No tenant key provided → 401 Reject
- Key generated at first-admin/org creation (not in install.py for SaaS)
- Frontend receives key via login response / JWT claims
- install.py generates key for Enterprise installs

**Still needed:**
- JWT claim schema: what fields? `tenant_key`, `org_id`, `org_name`?
- Multi-org user support: can a user belong to multiple orgs?
- Org switcher UX: how does a multi-org user switch context?

### D3: install.py Divergence

**Community install.py:**
- Strips TenantManager references
- No org creation — single user, auto-provisioned
- Minimal config.yaml (no tenant section)
- SQLite option? (removes PostgreSQL dependency for simple use)

**Enterprise install.py:**
- Full install with org + first admin creation
- Generates tenant key, stores in config.yaml
- PostgreSQL required (multi-user needs it)
- Optional: LDAP/AD integration for corporate auth

**SaaS deployment:**
- NOT install.py — Docker Compose / Kubernetes / Terraform
- Database migrations via alembic
- Secrets via environment variables or vault
- Horizontal scaling requires externalizing in-memory state (APIState, WebSocket connections)

### D4: What Gets Stripped for Community Edition?

| Component | Keep | Strip | Notes |
|-----------|------|-------|-------|
| TenantManager | | X | Replace with no-op or remove entirely |
| Organization model | | X | Single implicit org |
| Multi-user auth | | X | Single user, auto-login or simple password |
| API key management | | X | No need for API keys in single-user |
| RBAC (admin/member) | | X | Single user is always admin |
| Multi-product | ? | ? | Decision needed — single product simpler but limits utility |
| MCP tools | X | | Core functionality |
| Agent orchestration | X | | Core functionality |
| WebSocket real-time | X | | Core functionality |
| Project management | X | | Core functionality |
| Template system | X | | Core functionality |
| CSRF middleware | X | | Security baseline |

### D5: Billing (SaaS only)

**Current state:** Nothing exists (1/10 from SaaS readiness audit)

**Needs:**
- Subscription model decision: flat vs usage-based vs hybrid
- Stripe integration (or alternative)
- Plan enforcement middleware
- Usage tracking (API calls, agent hours, storage)
- Billing UI (subscription management, invoices)

**Estimated effort:** 6-8 developer-weeks (largest single SaaS blocker)

### D6: Auth Provider (SaaS + Enterprise)

**Current state:** Custom JWT + API key auth (5/10 from audit)

**Options:**
- **Build in-house:** Full control, more maintenance (current path)
- **Auth0 / Clerk:** Saves 4-6 weeks, adds dependency and cost
- **Keycloak (self-hosted):** Open source, Enterprise-friendly, complex setup

**Enterprise consideration:** Corporate customers may require LDAP/SAML/OIDC integration. Auth0/Clerk handle this out of the box. Building it in-house is 4-6 additional weeks.

---

## Proposed Phasing

### Phase 0: Code Quality Baseline (IN PROGRESS — 0765 series)
- Reach 10/10 code quality score
- Tag `v1.0-saas-baseline`

### Phase 1: Community Edition Fork (~2-3 weeks)
- Hard fork from baseline tag
- Strip TenantManager, org models, multi-user auth
- Simplify install.py for single-user
- Verify all core functionality works without tenancy
- Release as open source

### Phase 2: Enterprise Foundation (~3-4 weeks)
- Tenant key provisioning at org creation
- JWT claims with tenant_key
- Login response delivers tenant context
- install.py enterprise mode with org setup wizard
- CORS, CSRF, tenant isolation fully enforced

### Phase 3: SaaS Infrastructure (~4 weeks)
- Dockerize (Dockerfile + docker-compose)
- Externalize in-memory state (Redis for APIState, WebSocket)
- Database migrations via alembic (not install.py)
- Environment-based config (12-factor)
- Health checks, readiness probes

### Phase 4: SaaS Identity (~4 weeks)
- OAuth2/SSO integration (or Auth0)
- Org-level tenancy (Tenant = Org, not User)
- Multi-org user support + org switcher
- Granular RBAC beyond admin/member
- MFA

### Phase 5: Billing (~6-8 weeks)
- Subscription model + Stripe integration
- Plan enforcement middleware
- Usage tracking
- Billing UI
- Trial/freemium flow

### Phase 6: Production Hardening (~4 weeks)
- API versioning + pagination
- Rate limiting
- Audit logging
- Kubernetes deployment
- Monitoring + alerting

**Total: ~25-35 weeks from baseline tag to production SaaS**

---

## Immediate Next Steps (After 0765 Completes)

1. **Tag baseline:** `git tag v1.0-saas-baseline` on the 0760-perfect-score branch after merge
2. **Decide D1:** Fork strategy — hard fork vs feature flags vs monorepo
3. **Decide D5:** Billing model — needed before any billing code
4. **Decide D6:** Auth provider — build vs buy, needed before Phase 4
5. **Create 0770 handover series** for Phase 1 (community fork) once decisions are made

---

## Resolved Decisions (2026-03-07)

The following strategic decisions were made on 2026-03-07.

### Licensing

**GiljoAI Community License v1.0** adopted (commit `9dd6e9e8`). Single-user
free, multi-user requires a commercial license. This replaces the prior MIT
default and the open questions around MIT/Apache/AGPL.

Reference: `LICENSING_AND_COMMERCIALIZATION_PHILOSOPHY.md`

### Release Priority

**Community Edition ships first.** SaaS infrastructure follows after the
Community Edition is published.

### Fork Strategy

**One repo for now, split before publish.** All development (SaaS, OAuth,
billing, etc.) continues in the single repo. Before publishing the Community
Edition, the repo splits into:

- **Public repo (Community Edition)** -- published under GiljoAI Community
  License v1.0
- **Private repo (SaaS Edition)** -- imports the public repo as a dependency
  and layers SaaS features on top

### Community / SaaS Split

| Layer | Public Repo (Community) | Private Repo (SaaS) |
|-------|-------------------------|----------------------|
| Orchestration | Core orchestration engine | -- |
| Agents | Agent management | -- |
| Auth | Single-user auth | OAuth, MFA, SSO |
| Tenancy | Tenant isolation (hidden) | Org & team management |
| Realtime | WebSocket, MCP transport | -- |
| Frontend | Dashboard (CE branding) | Multi-user admin tools |
| Licensing | CE branding + license check | -- |
| Billing | -- | Billing, subscriptions |
| Analytics | -- | Usage analytics, metering |
| Onboarding | -- | SaaS onboarding flows |
| Deployment | -- | SaaS deployment configs |

### Reference

- Commit: `9dd6e9e8` (license adoption + edition branding)
- Doc: `LICENSING_AND_COMMERCIALIZATION_PHILOSOPHY.md`

---

## Open Questions for Gil

1. ~~Is community edition the first priority, or SaaS infrastructure?~~ **RESOLVED: Community Edition first.**
2. Should community support multi-product or be locked to single product?
3. Auth provider preference: build in-house, Auth0, Clerk, or Keycloak?
4. Billing model preference: flat subscription, per-seat, usage-based, or hybrid?
5. Target timeline: when do you want community edition shipped? SaaS MVP?
6. ~~Licensing: what license for community edition? (MIT, Apache 2.0, AGPL?)~~ **RESOLVED: GiljoAI Community License v1.0 (adopted 2026-03-07, commit `9dd6e9e8`).**
