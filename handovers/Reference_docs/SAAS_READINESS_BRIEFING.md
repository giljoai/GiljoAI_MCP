# GiljoAI MCP -- SaaS Readiness Briefing

**Compiled:** 2026-03-08
**Version:** 1.0.2
**Purpose:** Complete application state assessment and SaaS implementation planning context

---

## 1. What Is GiljoAI MCP?

A multi-tenant AI agent orchestration platform that coordinates teams of specialized AI coding agents (via Claude Code, Codex CLI, Gemini CLI) through a central dashboard. Agents receive missions, report progress, exchange messages, and deliver results -- all orchestrated through MCP (Model Context Protocol) tools and real-time WebSocket events.

---

## 2. Current Tech Stack

### Backend
| Component | Technology | Version |
|-----------|-----------|---------|
| Language | Python | >=3.10 (3.14.2 in dev) |
| Web Framework | FastAPI | >=0.100.0 |
| ORM | SQLAlchemy 2.0+ | Async mode (asyncpg) |
| Database | PostgreSQL | 18 |
| Migrations | Alembic | 11 version files + baseline |
| Auth | PyJWT + passlib[bcrypt] | Dual: JWT cookies + API keys |
| Logging | structlog | JSON (prod) / colored (dev) |
| Summarization | sumy + nltk | CPU-only (no GPU) |

### Frontend
| Component | Technology | Version |
|-----------|-----------|---------|
| Framework | Vue 3 | ^3.4.0 (Composition API, `<script setup>`) |
| UI Library | Vuetify 3 | ^3.4.0 (Material Design 3) |
| Build Tool | Vite | ^7.1.8 |
| State | Pinia | ^3.0.3 (15 stores) |
| HTTP Client | Axios | ^1.6.0 (interceptors, tenant headers) |
| Testing | Vitest + Playwright | Unit + E2E |

### Infrastructure
| Component | Status |
|-----------|--------|
| CI/CD | 4 GitHub Actions workflows (lint, test, security scan, release) |
| Pre-commit | 12+ hooks (ruff, bandit, gitleaks, pip-audit, prettier) |
| Docker | **NOT YET IMPLEMENTED** |
| Monitoring | Basic in-memory metrics only (no Prometheus/Sentry) |

---

## 3. Application Scale

| Metric | Count |
|--------|-------|
| Database tables (SQLAlchemy models) | 33 |
| REST API endpoints | 209 |
| MCP tools (JSON-RPC) | 22 |
| Service classes | 17 |
| API endpoint files | 45 |
| Middleware layers | 7 (CORS, CSRF, metrics, input validation, security headers, rate limiting, auth) |
| Vue components | 90 |
| Pinia stores | 15 |
| Composables | 10 |
| Views/pages | 19 |
| Test files | 141 |
| Alembic migrations | 11 |

---

## 4. Architecture Overview

### Request Flow
```
Browser -> Vite/Static (port 7274) -> Axios -> FastAPI (port 7272)
                                                  |
                                          7 Middleware layers
                                                  |
                                          45 Endpoint files
                                                  |
                                          17 Service classes
                                                  |
                                          SQLAlchemy 2.0 (async)
                                                  |
                                          PostgreSQL 18
```

### Agent Orchestration Flow (Thin Client)
```
1. User creates Project via REST API
2. OrchestrationService.spawn_agent_job() creates:
   - AgentJob (Work Order -- the WHAT)
   - AgentExecution (Executor -- the WHO)
3. Thin prompt generated (~10 lines, ~50 tokens)
4. Agent spawns in terminal, calls get_agent_mission() MCP tool
5. Server returns full mission + protocol (~2000 tokens)
6. Agent works: report_progress(), send_message(), create_task()
7. Agent completes: complete_job() -> WebSocket broadcast -> dashboard update
```

### Real-Time Layer
```
WebSocket /ws/{client_id}
   -> WebSocketManager (28 methods, tenant-scoped broadcasts)
   -> WebSocketEventBroker (pluggable):
      - InMemoryBroker (default, single-process)
      - PostgresNotifyBroker (available, enables multi-instance)
   -> WebSocketEventRouter (frontend, 25+ event types -> Pinia stores)
```

---

## 5. What Already Works Well

### Security (Production-Grade)
- OWASP-compliant security headers (HSTS, CSP with SHA-256 hashes, X-Frame-Options DENY)
- CSRF double-submit cookie pattern
- Input validation middleware (SQL injection, XSS, path traversal)
- Rate limiting (configurable, per-IP sliding window, auth-specific limits)
- Structured logging with 42 error codes across 5 categories
- Secret scanning in CI (gitleaks, bandit, Trivy)
- API key security: bcrypt hashing, IP logging, per-user limits, 90-day expiry

### Tenant Isolation (Audited + Remediated)
- TenantManager with `apply_tenant_filter()` on all queries
- Post-fetch validation via `ensure_tenant_isolation()`
- Comprehensive audit completed Feb 2026: 65 findings, all CRITICAL + HIGH remediated
- 61 tenant isolation regression tests passing
- Frontend enforces tenant via X-Tenant-Key header + WebSocket event filtering

### Auth System (Dual-Mode)
- JWT via httpOnly cookies (primary) with silent refresh, proactive refresh
- API keys via header (MCP/machine clients) with bcrypt hashing
- First-run admin creation flow
- Forced password change / recovery PIN setup
- Organization-based user management with roles (owner, admin, member)

### Multi-User UI (Scaffolded)
- User management (CRUD, roles, password reset) -- admin only
- Organization management (CRUD, member invite, role management, ownership transfer)
- Tenant-scoped WebSocket events (drops cross-tenant data)
- AppBar shows workspace name and org role badge

### Testing
- 141 test files across unit, integration, API, schema, repository layers
- pytest with async support (pytest-asyncio)
- 80% coverage threshold enforced
- Test markers: slow, integration, unit, e2e, stress, security, smoke
- Frontend: Vitest + Playwright

### CI/CD
- Full pipeline: Python linting (ruff, bandit, mypy) + frontend linting (ESLint, prettier)
- Matrix testing: Python 3.10, 3.11, 3.12
- Integration tests with PostgreSQL service container
- Security scanning: Trivy (CRITICAL/HIGH blocks build), SARIF upload to GitHub Security
- Auto-release workflow (master -> release branch sync)
- Manual release creation with version validation and git archive

---

## 6. SaaS Blockers -- What Must Change

### CRITICAL: In-Memory State (Prevents Horizontal Scaling)

The application runs as a single-process uvicorn instance. These items are in-memory and would be lost on restart or duplicated across instances:

| In-Memory Item | Current State | SaaS Requirement |
|----------------|--------------|------------------|
| WebSocket connections | `dict[str, WebSocket]` in APIState | Redis pub/sub or use existing PostgresNotifyBroker |
| Event bus | Local subscriber lists | Redis pub/sub or PostgreSQL LISTEN/NOTIFY |
| Rate limiter | Per-process token bucket | Redis-backed distributed rate limiting |
| API/MCP call counters | `dict[str, int]` | DB-backed (ApiMetrics table already exists) |
| Config | File-based `config.yaml` | DB-backed (Configuration + Settings tables exist) |
| Silence detector | Scans all tenants, no coordination | Distributed lock or single-leader election |
| File storage | Local filesystem (uploads, temp, logs) | Object storage (S3/MinIO) |

**Key insight:** The PostgresNotifyBroker for WebSocket events is already implemented and available -- just not the default. Switching `GILJO_WS_BROKER=postgres_notify` enables multi-instance WebSocket coordination without Redis.

### CRITICAL: No Docker Containerization

- No Dockerfile anywhere in the repository
- No docker-compose.yml
- `.env.example` has a `BUILD_TARGET=production` placeholder suggesting Docker was planned
- `.coveragerc` references `/app/src/` container path (also planned)

**Needed:**
- Multi-stage Dockerfile (build frontend, install Python deps, slim runtime)
- docker-compose.yml (api, frontend, postgres, redis)
- Health check directives
- Non-root user
- .dockerignore

### HIGH: No External Monitoring

- No Prometheus /metrics endpoint
- No Sentry or error tracking
- No OpenTelemetry distributed tracing
- No Grafana dashboards
- No log aggregation (ELK, Loki)
- No alerting system

### HIGH: No Secrets Management

- All secrets in environment variables (JWT_SECRET, DB_PASSWORD, etc.)
- No integration with HashiCorp Vault, AWS Secrets Manager, or Azure Key Vault
- No secret rotation support

### MEDIUM: Auth Gaps for SaaS

- No OAuth2/SSO integration (Auth0, Clerk, or Keycloak)
- No MFA
- No self-service registration (admin creates users)
- No invite-by-email (invite-by-user-ID only)
- No org/workspace switcher for multi-org users

### MEDIUM: TLS Certificate Distribution

mkcert generates a local Certificate Authority trusted only on the install machine. Remote users (LAN or internet) get browser warnings, and critically, background API calls from the frontend fail silently — causing the app to show `/welcome` (fresh install wizard) instead of the login page.

**Current workaround:** Export `rootCA.pem` (via `mkcert -CAROOT`) and install on each client machine. Acceptable for a second workstation, not viable for SaaS or public demos.

**Demo approach (decided 2026-04-02):** Cloudflare Tunnel — exposes the server behind real TLS certs with zero client-side setup. See `handovers/Demo_server_prepp.md` section 6 for full setup.

**SaaS approach:** Let's Encrypt via certbot (automated renewal) or Cloudflare proxy with real domain. Should be part of Phase 3 (SaaS Infrastructure).

### MEDIUM: No Billing Infrastructure

- No subscription model
- No Stripe integration
- No plan enforcement middleware
- No usage tracking/metering
- No billing UI

---

## 7. Remaining TODO Items

### Community Edition Launch Path (24-35 hours)

These must complete before publishing the Community Edition:

| # | ID | Task | Effort | Status |
|---|-----|------|--------|--------|
| 1 | 0732 | **Release Packaging** -- Dockerfile, docker-compose.yml, GitHub issue/PR templates, README screenshots, CHANGELOG.md, fix 12 pre-existing test failures | 3-5 hrs | Ready |
| 2 | 0409 | **Quick Setup Buttons** -- Copy-paste install prompts for Claude Code (Codex/Gemini later). Backend endpoint + frontend dialog in ProductIntroTour | 4-6 hrs | Not Started |
| 3 | 0731 | **Legacy Code Removal** -- Fresh scan needed (line refs stale after 0765 sprint). ~89 legacy patterns: agent message queue compat, deprecated model fields, Ollama refs, commented code, stale type-ignores | 8-12 hrs | Needs re-scan |
| ~~4~~ | ~~9999~~ | ~~One-Liner Install Scripts~~ | -- | DELETED (2026-03-09). Website directs to GitHub. |

### SaaS Implementation Phases (25-35 weeks after CE)

Per the 0770 roadmap (decisions made 2026-03-07):

| Phase | Scope | Effort | Depends On |
|-------|-------|--------|------------|
| 0 | Code Quality Baseline | **COMPLETE** (0765 sprint, score 8.35/10) | -- |
| 1 | Community/SaaS Repo Split | 2-3 weeks | CE published |
| 2 | Enterprise Foundation (tenant key provisioning, JWT claims, enterprise install.py) | 3-4 weeks | Phase 1 |
| 3 | SaaS Infrastructure (Docker, Redis state externalization, alembic-only migrations, 12-factor config, health probes) | 4 weeks | Phase 2 |
| 4 | SaaS Identity (OAuth2/SSO, multi-org, org switcher, granular RBAC, MFA) | 4 weeks | Phase 3 + D6 decision |
| 5 | Billing (Stripe, plan enforcement, usage tracking, billing UI, trial/freemium) | 6-8 weeks | Phase 4 + D5 decision |
| 6 | Production Hardening (API versioning, pagination, K8s, monitoring, alerting) | 4 weeks | Phase 5 |

### Deferred / Nice-to-Have

| ID | Task | Effort | Blocks |
|----|------|--------|--------|
| TODO_vision | Vision Summarizer LLM Upgrade (Qwen2.5-0.5B or Claude Haiku) | 16-24 hrs | Nothing (Sumy works) |
| 0284 | get_available_agents Enhancement (exposure + docs) | 2-4 hrs | Nothing |
| 1014 | Security Event Auditing (AuditLog table, compliance trail) | 8 hrs | Enterprise compliance only |
| 0250 | HTTPS Enablement | **DONE** -- needs archiving | Nothing |

---

## 8. Strategic Decisions (Resolved)

| Decision | Resolution | Date |
|----------|-----------|------|
| Licensing | GiljoAI Community License v1.0 (free single-user, commercial for multi-user) | 2026-03-07 |
| Release priority | Community Edition ships first | 2026-03-07 |
| Fork strategy | Option D: Single repo now, split before publish. Private repo layers SaaS on top of public CE repo | 2026-03-07 |
| Edition split | Public repo = core orchestration + single-user auth + dashboard. Private repo = OAuth, billing, org management, analytics, SaaS deployment | 2026-03-07 |
| D3: Multi-product in CE | Keep multi-product in CE. Single-active-product constraint (Handover 0050) already prevents confusion. No code change. | 2026-03-08 |
| D7: CE ship date | April 5, 2026. SaaS MVP target: CE + 20 weeks. | 2026-03-08 |
| Code isolation architecture | SaaS-only code in dedicated `saas/` directories. CE never imports from `saas/`. Two branches: `main` (CE) and `saas` (private). See `docs/EDITION_ISOLATION_GUIDE.md`. | 2026-03-08 |
| Edition model | Two editions (CE + SaaS), not three. Enterprise is a deployment mode of SaaS. | 2026-03-08 |

---

## 9. Open Decisions (Blocking SaaS Phases)

| ID | Question | Blocks | Options |
|----|----------|--------|---------|
| ~~D3~~ | ~~Should Community Edition support multi-product or single product only?~~ **CLOSED (2026-03-08):** Keep multi-product. Single-active constraint already prevents confusion. | ~~CE launch scope~~ | N/A |
| D5 | Billing model? | Phase 5 (6-8 weeks) | Flat subscription / per-seat / usage-based / hybrid |
| D6 | Auth provider? | Phase 4 (4 weeks) | Build in-house (4-6 extra weeks for LDAP/SAML) / Auth0 or Clerk (saves time, adds cost) / Keycloak (self-hosted, complex) |
| ~~D7~~ | ~~Target timeline?~~ **CLOSED (2026-03-08):** CE ships April 5, 2026. SaaS MVP: CE + 20 weeks. | ~~All phases~~ | N/A |
| D8 | CE → SaaS data migration strategy? | Phase 2 (Enterprise Foundation) | Auto-detect existing CE database and import, or SaaS starts fresh? Design during Phase 2 before schema migrations. |

---

## 10. What's Already SaaS-Adjacent (Existing Infrastructure)

These components are **already built** and reduce SaaS implementation effort:

1. **PostgresNotifyBroker** -- Multi-instance WebSocket event coordination (just needs to be made default)
2. **TenantManager** -- Full tenant isolation framework with audit + 61 regression tests
3. **Organization model** -- Org CRUD, membership, roles, ownership transfer
4. **User management** -- Multi-user auth, roles (admin/developer/viewer), password management
5. **API key system** -- Bcrypt hashing, IP logging, per-user limits, 90-day expiry
6. **Configuration/Settings tables** -- DB-backed config (could replace file-based config.yaml)
7. **ApiMetrics table** -- DB-backed usage tracking (could replace in-memory counters)
8. **Structured logging** -- 42 error codes, JSON output in production mode
9. **Security middleware stack** -- CORS, CSRF, rate limiting, input validation, security headers
10. **Alembic migrations** -- Database schema versioning ready for multi-environment deployment
11. **CI/CD pipeline** -- Full GitHub Actions with security scanning, matrix testing, auto-release
12. **Frontend tenant awareness** -- X-Tenant-Key on every request, WebSocket event filtering, org UI

---

## 11. Effort Summary

| Category | Items | Effort |
|----------|-------|--------|
| CE Launch Blockers | 0732 + 0409 + 0731 | 16-23 hours (~1 dev-week) |
| SaaS Phases 1-6 | Full SaaS implementation | 25-35 weeks |
| Nice-to-haves | Vision upgrade + agent enhancement | 18-29 hours |
| Housekeeping | Archive 0250, update catalogue, move reference docs | 1-2 hours |

---

## 12. Community / SaaS Edition Component Split

| Layer | Community Edition (Public Repo) | SaaS Edition (Private Repo) |
|-------|--------------------------------|----------------------------|
| Orchestration | Core engine, mission planning, agent coordination | -- |
| Agents | Templates, spawning, communication, job lifecycle | -- |
| Auth | Single-user login/password, JWT | OAuth2, MFA, SSO, LDAP/SAML |
| Tenancy | Infrastructure kept but hidden in single-user mode | Org & team management, multi-org |
| Real-time | WebSocket, MCP transport | -- |
| Frontend | Full dashboard (CE branding) | Multi-user admin tools, billing UI |
| Billing | -- | Stripe, subscriptions, usage metering |
| Analytics | -- | Usage analytics, metering dashboards |
| TLS | mkcert (local CA, single-machine trust) | Cloudflare Tunnel or Let's Encrypt (zero-friction for remote users) |
| Deployment | install.py + Docker (single-machine) | Docker/K8s, horizontal scaling, Redis |

> **Implementation architecture (2026-03-08):** The edition split is implemented via physical directory isolation. SaaS-only code lives in `saas/` directories (`src/giljo_mcp/saas/`, `api/saas_endpoints/`, `api/saas_middleware/`, `frontend/src/saas/`, `tests/saas/`, `migrations/saas_versions/`). CE code never imports from these directories. Full specification: `docs/EDITION_ISOLATION_GUIDE.md`.

---

## SaaS Security Hardening Backlog

| Item | Current State | SaaS Target | Priority | Notes |
|------|--------------|-------------|----------|-------|
| CSP style-src | `'unsafe-inline'` (required by Vuetify runtime styles) | Nonce-based CSP: server generates per-request nonce, Vuetify uses it | Medium | Every Vue/Vuetify app ships with unsafe-inline for styles. Nonce-based requires SSR integration. Not a launch blocker but should be addressed for enterprise customers. |
| CSP script-src | Hash-locked (production grade) | Keep as-is | N/A | Already locked down. |

---

*This document was compiled from automated codebase analysis of 33 database models, 209 API endpoints, 90 Vue components, 141 test files, and 10 handover documents.*
