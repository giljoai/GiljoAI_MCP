# Edition Isolation Guide

**Date:** 2026-03-08
**Status:** Authoritative Reference
**Scope:** All agents working on CE or SaaS features
**Version:** 1.0

This is the authoritative reference for Community Edition (CE) and SaaS Edition code isolation. If any other document conflicts with this guide, this guide takes precedence.

---

## A. Edition Model

GiljoAI MCP ships as **two editions** from a single repository with two long-lived branches.

| Edition | Branch | Visibility | Users | Install Method |
|---------|--------|-----------|-------|---------------|
| Community (CE) | `main` | Public repo | Single user | `git clone` + `python install.py` |
| SaaS | `saas` | Private repo | Multi-user, multi-org | Docker/K8s |

Enterprise is a deployment mode of SaaS (self-hosted by corporate IT), not a separate edition or codebase. There is no Enterprise branch or Enterprise directory.

The Community Edition is licensed under the **GiljoAI Community License v1.1** (single-user free, multi-user requires commercial license). This is NOT an OSI-approved license. Never reference MIT, open source, or open core in code, documentation, or UI.

---

## B. Directory Structure

The following layout shows the full project structure with SaaS-only directories clearly marked. CE directories contain all existing production code. SaaS directories are scaffolding for future SaaS-only features.

```
src/giljo_mcp/
├── mission_planner.py           # CE -- core orchestration
├── context_manager.py           # CE -- core context management
├── database.py                  # CE -- database layer
├── tenant.py                    # CE -- kept, hidden in single-user mode
├── template_seeder.py           # CE -- agent template management
├── template_manager.py          # CE -- template operations
├── auth_manager.py              # CE -- authentication management
├── config_manager.py            # CE -- configuration
├── auth/                        # CE -- single-user auth
│   ├── manager.py
│   ├── jwt_handler.py
│   └── password.py
├── services/                    # CE -- business logic services
│   ├── orchestration_service.py
│   ├── agent_job_manager.py
│   ├── message_service.py
│   ├── project_service.py
│   ├── product_service.py
│   ├── org_service.py
│   ├── user_service.py
│   ├── task_service.py
│   └── (other service modules)
├── models/                      # CE -- database models (includes org model)
├── tools/                       # CE -- MCP tools
├── repositories/                # CE -- data access layer
├── schemas/                     # CE -- validation schemas
├── config/                      # CE -- configuration modules
├── utils/                       # CE -- shared utilities
├── validation/                  # CE -- input validation
│
├── saas/                        # *** SaaS-ONLY -- never imported by CE code ***
│   ├── __init__.py              # Empty or feature registry (conditional loading)
│   ├── auth/                    # OAuth, SSO, LDAP, MFA
│   ├── billing/                 # Stripe, plan enforcement, usage metering
│   ├── org/                     # Multi-org management, team features
│   ├── notifications/           # Twilio, email services, push notifications
│   ├── analytics/               # Usage analytics, metering dashboards
│   └── models.py                # SaaS-only database tables

api/
├── endpoints/                   # CE -- existing endpoints (auth, projects, agents, etc.)
├── middleware/                   # CE -- existing middleware stack
├── broker/                      # CE -- WebSocket broker (PostgresNotify)
├── dependencies/                # CE -- FastAPI dependency injection
├── events/                      # CE -- event handling
├── schemas/                     # CE -- API schemas
├── startup/                     # CE -- application startup
│
├── saas_endpoints/              # *** SaaS-ONLY API routes ***
│   └── __init__.py
├── saas_middleware/              # *** SaaS-ONLY middleware ***
│   └── __init__.py

frontend/src/
├── views/                       # CE -- existing views
├── components/                  # CE -- existing components
├── stores/                      # CE -- existing Pinia stores
├── router/                      # CE -- Vue Router configuration
├── composables/                 # CE -- Vue composables
├── services/                    # CE -- frontend service layer
├── layouts/                     # CE -- layout components
├── config/                      # CE -- frontend configuration
├── types/                       # CE -- TypeScript types
├── utils/                       # CE -- frontend utilities
│
├── saas/                        # *** SaaS-ONLY frontend ***
│   ├── views/
│   ├── components/
│   ├── stores/
│   └── routes.js                # SaaS-only route definitions

tests/
├── api/                         # CE tests -- API endpoint tests
├── services/                    # CE tests -- service layer tests
├── unit/                        # CE tests -- unit tests
├── integration/                 # CE tests -- integration tests
├── repositories/                # CE tests -- repository tests
├── schemas/                     # CE tests -- schema tests
├── fixtures/                    # CE tests -- test fixtures
├── helpers/                     # CE tests -- test helpers
│
├── saas/                        # *** SaaS-ONLY tests ***
│   └── __init__.py

migrations/
├── versions/                    # CE migration chain (existing migrations)
│
├── saas_versions/               # *** SaaS-ONLY migration chain ***
│   └── __init__.py
```

**Key:** Any directory or file marked with `*** SaaS-ONLY ***` exists only on the `saas` branch in production. On the `main` branch, these directories contain only empty `__init__.py` scaffolding files.

---

## C. The Four Rules

These are mandatory rules, not suggestions. Every agent must follow them without exception.

### Rule 1 -- Import Direction

SaaS code may import from CE code (it extends CE). CE code NEVER imports from any `saas/` directory. If you find yourself needing CE to call SaaS code, use the conditional registration pattern (see Section E), never a direct import.

**Verification command:**

```bash
# Run from project root. Expected result: no output.
grep -r "from.*saas" src/giljo_mcp/ api/ frontend/src/ \
  --include="*.py" --include="*.js" --include="*.vue" \
  | grep -v "saas/" | grep -v "__pycache__"
```

If this command produces any output, there is a dependency leak. Fix it before completing the handover.

### Rule 2 -- The Deletion Test

Before marking any SaaS work as complete, confirm: "If all `saas/`, `saas_endpoints/`, `saas_middleware/`, and `frontend/src/saas/` directories were deleted, would CE still start, serve requests, and pass all tests in `tests/` (excluding `tests/saas/`)?" If no, there is a dependency leak. Fix it before completing the handover.

### Rule 3 -- Placement Decision Framework

Use this decision tree for every new feature:

```
Does this feature require infrastructure a solo developer wouldn't have?
(Stripe account, Twilio, SMTP relay, LDAP server, OAuth provider)
    --> YES --> saas/ directory

Does this feature only make sense with multiple users or organizations?
(team management, viewer roles, cross-user product transfer, org analytics)
    --> YES --> saas/ directory

Does this feature improve the core orchestration for ANY user, including solo?
(better mission planning, new MCP tools, UI improvements, performance)
    --> YES --> CE directory (main branch)

Does this code already exist in CE and is needed for CE to function?
(TenantManager, Organization model, multi-user auth infrastructure)
    --> YES --> stays in CE directory, do NOT move to saas/
```

### Rule 4 -- Handover Tagging

Every handover document MUST include in its metadata:

```
**Edition Scope:** CE | SaaS | Both
```

This tells the receiving agent which directories and which branch they should be working in.

---

## D. Existing SaaS-Adjacent Code (Do NOT Move)

The following code is intentionally in CE directories and must NOT be relocated to `saas/`. These components serve dual purposes: they enable CE to function in single-user/single-tenant mode, and they provide the foundation that SaaS extends.

| Component | Location | Why It Stays in CE |
|-----------|----------|-------------------|
| TenantManager | `src/giljo_mcp/tenant.py` | CE uses it in hidden single-tenant mode. Foundation for SaaS. |
| Organization model | `src/giljo_mcp/models/` | CE creates a single implicit org at install. SaaS activates multi-org. |
| Multi-user auth | `src/giljo_mcp/auth/` | CE uses single-user login. SaaS extends it (OAuth, MFA). |
| User management endpoints | `api/endpoints/users.py` | CE manages the single admin user. SaaS adds team features. |
| API key system | Across auth + endpoints | CE uses API keys for MCP tool auth. SaaS adds per-org key management. |
| WebSocket broker (PostgresNotify) | `api/broker/` | CE uses it for single-instance real-time. SaaS uses it for multi-instance. |
| Frontend tenant awareness | `frontend/src/` (X-Tenant-Key headers) | CE sends implicit key. SaaS adds org switcher. |

The principle: if CE needs this code to boot and function in single-user mode, it stays in CE even though SaaS will also use it.

---

## E. Conditional Loading Patterns

When SaaS features need to integrate with the CE application without creating import dependencies, use these conditional loading patterns. The key principle is: CE code checks whether the SaaS directory exists at runtime and loads modules only if present. If the directory is missing (CE-only deployment), the code silently skips SaaS modules.

### Backend (FastAPI app.py) -- Conditional endpoint registration

```python
# CE endpoints -- always loaded
from api.endpoints import auth, projects, agents, orchestrator, messages
app.include_router(auth.router)
app.include_router(projects.router)
# ... etc

# SaaS endpoints -- loaded only if saas_endpoints directory exists
import importlib
import os

_saas_endpoints_dir = os.path.join(os.path.dirname(__file__), "saas_endpoints")
if os.path.isdir(_saas_endpoints_dir):
    try:
        from api.saas_endpoints import oauth, billing, org_management, analytics
        app.include_router(oauth.router, prefix="/api/saas", tags=["SaaS: Auth"])
        app.include_router(billing.router, prefix="/api/saas", tags=["SaaS: Billing"])
        app.include_router(org_management.router, prefix="/api/saas", tags=["SaaS: Org"])
        app.include_router(analytics.router, prefix="/api/saas", tags=["SaaS: Analytics"])
    except ImportError:
        pass  # SaaS modules not available -- CE mode
```

### Backend -- Conditional middleware registration

```python
_saas_middleware_dir = os.path.join(os.path.dirname(__file__), "saas_middleware")
if os.path.isdir(_saas_middleware_dir):
    try:
        from api.saas_middleware.plan_enforcement import PlanEnforcementMiddleware
        app.add_middleware(PlanEnforcementMiddleware)
    except ImportError:
        pass
```

### Frontend (Vue Router) -- Conditional route loading

```javascript
// router/index.js

// CE routes -- always loaded
import DashboardView from '@/views/DashboardView.vue'
// ... other CE imports

const routes = [
  { path: '/dashboard', component: DashboardView },
  // ... other CE routes
]

// SaaS routes -- loaded only if saas/ directory exists
try {
  const saasRoutes = require('@/saas/routes.js').default
  routes.push(...saasRoutes)
} catch (e) {
  // SaaS routes not available -- CE mode
}
```

### Alembic Migrations -- SaaS-only migration branch

SaaS-only database tables get their own migration directory. The CE migration chain (`migrations/versions/`) remains untouched and self-contained.

In `alembic.ini` or `migrations/env.py`, add conditional branch loading:

```python
# In migrations/env.py
import os

# Always run CE migrations
version_locations = "migrations/versions"

# Add SaaS migrations if directory exists
saas_migrations = os.path.join(os.path.dirname(__file__), "saas_versions")
if os.path.isdir(saas_migrations):
    version_locations += f" {saas_migrations}"

context.configure(
    version_locations=version_locations.split(),
    # ... other config
)
```

### Migration placement rules

- If a SaaS feature needs a **new column on an existing CE table** (not a new table), that migration goes in the CE chain (`migrations/versions/`) because both editions benefit from schema compatibility.
- If a SaaS feature needs an **entirely new table**, it goes in `migrations/saas_versions/`.

---

## F. Git Workflow

### Branch structure

```
main              <-- CE (public). All core features merge here.
|-- feature/*     <-- Feature branches off main for CE work
|-- fix/*         <-- Bug fixes off main
|
saas              <-- SaaS (private). Contains everything in main + saas/ directories.
|-- feature/*     <-- Feature branches off saas for SaaS-only work
|-- test/*        <-- Experimental branches off either main or saas
```

### Merge direction

```
main ------------> saas       ALWAYS OK (saas picks up CE improvements)
saas ------------> main       NEVER (unless deliberately donating a feature to CE)
```

### Remote structure

When CE goes public, two GitHub remotes will exist:

- `origin` -- public remote, receives pushes from `main` branch only (CE code)
- `private` -- private remote, receives pushes from both `main` and `saas` branches

### Daily workflow examples

**Core feature (benefits both editions):**

```bash
git checkout main
git checkout -b feature/improve-mission-planner
# ... work happens, commits ...
git checkout main
git merge feature/improve-mission-planner
git branch -d feature/improve-mission-planner
# Then sync to saas:
git checkout saas
git merge main
```

**SaaS-only feature:**

```bash
git checkout saas
git checkout -b feature/org-management
# ... work happens, commits ...
git checkout saas
git merge feature/org-management
git branch -d feature/org-management
# main is never touched
```

### Merge frequency

Merge `main --> saas` at minimum weekly, ideally after every core feature merge. This keeps merge conflicts small.

---

## G. CI/CD Implications

- The CI pipeline on `main` branch runs CE tests only (`tests/` excluding `tests/saas/`).
- The CI pipeline on `saas` branch runs ALL tests (`tests/` + `tests/saas/`).
- If a test in `tests/saas/` fails on the `saas` branch, it does NOT block CE releases from `main`.
- SaaS tests may import from `saas/` directories. CE tests must NOT.

### Test isolation verification

Add this check to CI on the `main` branch:

```bash
# Verify no CE code imports from saas directories
grep -r "from.*saas" src/giljo_mcp/ api/ frontend/src/ \
  --include="*.py" --include="*.js" --include="*.vue" \
  | grep -v "saas/" | grep -v "__pycache__"
# If this produces output, the build should FAIL.
```

---

## H. Reference Documents

- **This guide** (`docs/EDITION_ISOLATION_GUIDE.md`) -- authoritative for code isolation and directory placement
- `handovers/0770_SAAS_EDITION_PROPOSAL.md` -- architectural decision record for the edition split
- `LICENSING_AND_COMMERCIALIZATION_PHILOSOPHY.md` -- licensing terms and commercial strategy
- `handovers/HANDOVER_INSTRUCTIONS.md` -- agent operating protocol (includes edition scope section)

---

*End of Edition Isolation Guide.*
