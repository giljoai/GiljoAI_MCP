# Handover: Single-Port Frontend Serving for CE Production Release

**Date:** 2026-04-03
**From Agent:** Research session (deep feasibility analysis)
**To Agent:** Next Session
**Priority:** High (CE release blocker — release target: week of 2026-04-07)
**Edition Scope:** CE
**Estimated Complexity:** 8 hours (1 session)
**Status:** Not Started

---

## Task Summary

Merge frontend static file serving into the FastAPI backend so CE production runs on a single port (7272). Currently the product requires two ports (7272 API + 7274 Vite dev server), which is unsuitable for a production release. Development mode (two-port Vite HMR) must remain fully functional.

**Why it matters:** CE ships in ~1 week. Users expect `python install.py` → `python startup.py` → one URL, one port. Two-port architecture leaks dev infrastructure into the user experience.

---

## Context and Background

### Current Architecture

```
Browser → :7274 (Vite dev server) → proxies /api, /mcp, /ws → :7272 (FastAPI)
```

Both `startup.py` and `startup_prod.py` launch separate frontend processes. The Vite dev server or a simple Python HTTP server runs on 7274. There is no FastAPI static file mount.

### Target Architecture (Production)

```
Browser → :7272 (FastAPI) → serves static files at /
                           → serves API at /api/*
                           → serves WebSocket at /ws/*
                           → serves MCP at /mcp/*
```

### Target Architecture (Development — unchanged)

```
Browser → :7274 (Vite HMR) → proxies /api, /mcp, /ws → :7272 (FastAPI)
```

### Feasibility Research (Completed)

Three independent deep-dive agents analyzed frontend, backend, and database layers. Key findings:

- **Database layer: CLEAR** — No ports stored in DB, JWT cookies are port-agnostic, CSRF tokens not port-scoped, WebSocket broker has zero port dependencies.
- **Backend: 3 blockers + 3 optimizations** — Root endpoint conflict, auth/CSRF middleware blocking static files, rate limiter/metrics/logging inflation from static requests.
- **Frontend: 13 hardcoded port references** — All follow the same fix pattern: `window.location.port || '7272'`.
- **Config already anticipates this:** `config.yaml` has `unified_port: true` and `paths.static: frontend/dist`.

---

## Technical Details

### Phase 1: Backend — FastAPI Static Mount + Middleware Exemptions

#### 1A. Static file serving in `api/app.py`

Add conditional static file mount at the END of `create_app()` (after all routers). Must be last so API routes take priority.

```python
# In create_app(), after all include_router() calls:
from starlette.staticfiles import StaticFiles
from starlette.responses import FileResponse
from pathlib import Path

dist_dir = Path(state.config.get_nested("paths.static", "frontend/dist"))
if dist_dir.exists() and (dist_dir / "index.html").exists():
    # SPA fallback: serve index.html for any path not matched by API routes
    @app.exception_handler(404)
    async def spa_fallback(request: Request, exc):
        # Only fallback for non-API, non-WS, non-MCP requests
        if not request.url.path.startswith(("/api", "/ws", "/mcp", "/health", "/docs", "/redoc")):
            return FileResponse(str(dist_dir / "index.html"))
        raise exc

    app.mount("/", StaticFiles(directory=str(dist_dir), html=False), name="static")
```

**Note:** Using `html=False` because we handle the SPA fallback via the 404 handler. If `html=True`, StaticFiles would serve `index.html` for directories but not handle Vue Router paths like `/projects/123`.

#### 1B. Remove root endpoint conflict (`api/app.py:524`)

The existing `GET /` returns JSON. In production mode (dist/ exists), this conflicts with serving `index.html`. Wrap it conditionally:

```python
dist_dir = Path(state.config.get_nested("paths.static", "frontend/dist"))
if not (dist_dir.exists() and (dist_dir / "index.html").exists()):
    @app.get("/")
    async def root():
        return {"name": "GiljoAI MCP", ...}
```

#### 1C. Auth middleware — exempt static paths (`api/middleware/auth.py:142-166`)

Add to `_is_public_endpoint()`:

```python
# Static file paths (production frontend serving)
if path == "/" or path == "/index.html" or path.startswith("/assets/"):
    return True
```

#### 1D. CSRF middleware — exempt static prefixes (`api/app.py:390-405`)

Add `/assets` to `exempt_prefixes` list. Note: GET requests don't mutate state, but the middleware may still check them.

#### 1E. Rate limiter — exclude static files (`api/middleware/rate_limiter.py`)

Add path check early in the middleware dispatch. Static file requests (50+ per page load) must NOT count against the 300 req/min limit:

```python
if request.url.path.startswith("/assets/") or request.url.path in ("/", "/index.html", "/favicon.ico"):
    return await call_next(request)
```

#### 1F. Metrics middleware — skip static files (`api/middleware/metrics.py:19-34`)

Same pattern as rate limiter — skip counter increment for static paths.

#### 1G. Logging exclusions (`api/run_api.py:204-228`)

Add to `exclude_patterns`:
```python
"GET /assets/",
"GET /index.html",
"GET /favicon.ico",
```

### Phase 2: Frontend — Fix 13 Hardcoded Port References

All fixes follow one pattern: replace `'7272'` fallback with `window.location.port || '7272'`.

**Create a shared utility first** (`frontend/src/utils/portConfig.js`):
```javascript
/** Derive the API port from the current page URL, falling back to 7272 */
export const getApiPort = () =>
  import.meta.env.VITE_API_PORT || window.API_PORT || window.location.port || '7272'
```

Then update each file to use `getApiPort()`:

| # | File | Line | Current | Fix |
|---|------|------|---------|-----|
| 1 | `frontend/index.html` | 82 | `const apiPort = 7272` | `const apiPort = window.location.port \|\| 7272` |
| 2 | `frontend/src/config/api.js` | 7 | `\|\| '7272'` | `\|\| window.location.port \|\| '7272'` |
| 3 | `frontend/src/services/configService.js` | 60 | `\|\| '7272'` | `\|\| window.location.port \|\| '7272'` |
| 4 | `frontend/src/stores/websocket.js` | 129 | `\|\| 7272` | `\|\| parseInt(window.location.port) \|\| 7272` |
| 5 | `frontend/src/components/navigation/ConnectionDebugDialog.vue` | 150 | `:7272` | `:${window.location.port \|\| 7272}` |
| 6 | `frontend/src/components/ConnectionStatus.vue` | 300 | `:7272` | `:${window.location.port \|\| 7272}` |
| 7 | `frontend/src/composables/useMcpConfig.js` | 46 | `\|\| '7272'` | `\|\| window.location.port \|\| '7272'` |
| 8 | `frontend/src/views/DashboardView.vue` | 227 | `ref(7272)` | `ref(parseInt(window.location.port) \|\| 7272)` |
| 9 | `frontend/src/components/AiToolConfigWizard.vue` | 213 | `'7272'` | `window.location.port \|\| '7272'` |
| 10 | `frontend/src/components/setup/SetupStep2Connect.vue` | 273 | `ref('7272')` | `ref(window.location.port \|\| '7272')` |
| 11 | `frontend/src/components/settings/tabs/NetworkSettingsTab.vue` | 33-45 | Hint: `Default: 7274` | Dynamic or remove hint |
| 12 | `frontend/src/views/SystemSettings.vue` | 144 | `7274` fallback | Use config value |
| 13 | `frontend/playwright.config.ts` | 22, 43 | `localhost:7274` | `process.env.PLAYWRIGHT_TEST_BASE_URL \|\| 'http://localhost:7274'` (already has env support — just document) |

**IMPORTANT for `index.html` (item 1):** This script runs before Vue/Vite. It cannot use `import.meta.env`. The fix must be pure JavaScript: `window.location.port || 7272`. When served from 7272 in production, `window.location.port` returns `"7272"`. When served from Vite on 7274, the port still resolves correctly because in dev mode `api.js` uses empty base URL (relative paths via Vite proxy).

### Phase 3: Startup Scripts — Production Mode Toggle

#### 3A. `startup.py` — Skip Vite when dist/ exists

Add a production detection check in `start_frontend_server()`:

```python
def start_frontend_server():
    dist_dir = Path("frontend/dist")
    if dist_dir.exists() and (dist_dir / "index.html").exists():
        log_info("Production frontend build detected (frontend/dist/). Skipping Vite dev server.")
        log_info(f"Frontend will be served by FastAPI on port {api_port}.")
        return None  # No subprocess needed
    # ... existing Vite dev server launch code ...
```

#### 3B. `startup_prod.py` — Simplify or deprecate

With FastAPI serving static files, `startup_prod.py` becomes unnecessary. Either:
- Remove it entirely (preferred — less surface area)
- Or update it to just run `npm run build` + `startup.py`

#### 3C. Build step — Add `npm run build` to install.py for release

In `install.py`, after `npm install`, add an optional build step:

```python
# After npm install succeeds:
if production_mode:  # New flag from install.py prompts
    run_command(["npm", "run", "build"], cwd=frontend_dir)
```

### Phase 4: Install.py & Configuration Updates

#### 4A. Install mode prompt

Add a question to `install.py`:

```
How will you use GiljoAI?
  1. Production (recommended) — Single port, optimized frontend build
  2. Development — Two ports, hot-reload for code changes

Select [1/2] (default: 1):
```

**Production mode (1):**
- Runs `npm run build` to create `frontend/dist/`
- Sets `config.yaml` → `services.frontend.dev_server: false`
- Sets `config.yaml` → `services.frontend.port:` same as API port
- Startup detects `dist/` and skips Vite

**Development mode (2):**
- Does NOT build dist/ (or deletes it if present to avoid confusion)
- Sets `config.yaml` → `services.frontend.dev_server: true`
- Sets `config.yaml` → `services.frontend.port: 7274`
- Startup launches Vite as today

#### 4B. Developer contribution path (CRITICAL UX QUESTION)

**Problem:** A user installs CE in production mode. Later, they want to contribute code. They need Vite HMR. How?

**Solution — NO separate devinstall.py needed.** Add a mode switch to `startup.py`:

```bash
python startup.py --dev    # Force Vite dev mode (ignore dist/, launch Vite on 7274)
python startup.py          # Auto-detect: if dist/ exists → production, else → dev
```

The `--dev` flag:
1. Skips static file detection
2. Launches Vite dev server on 7274
3. Prints: "Development mode: frontend on :7274, API on :7272"

This is cleaner than a separate script because:
- No file duplication
- Same entry point for all users
- `install.py` already installs npm dev dependencies regardless of mode
- Developer just needs to run `startup.py --dev` instead of `startup.py`

#### 4C. Config.yaml updates

Add to `services.frontend`:
```yaml
services:
  frontend:
    port: 7274          # Only used in dev mode
    dev_server: true     # false in production installs
    auto_open: true
```

The `dev_server` flag is what `startup.py` checks (along with dist/ existence).

#### 4D. CORS simplification

In production (single port), CORS is same-origin — no preflight needed. But keep CORS config for dev mode where ports differ. No changes needed — existing dynamic CORS already handles both cases.

### Phase 5: Documentation Updates

| Document | What to update |
|----------|---------------|
| `README.md` | Installation section: mention production vs dev mode |
| `CONTRIBUTING.md` | Add: "Run `python startup.py --dev` for hot-reload development" |
| `docs/SERVER_ARCHITECTURE_TECH_STACK.md` | Update network topology diagram: single-port production, two-port dev |
| `docs/EDITION_ISOLATION_GUIDE.md` | No changes (edition isolation unaffected) |
| `handovers/ROADMAP.md` | Remove "Production Frontend Serving" item (this handover addresses it) |
| `installer/` docs | Update install.py inline help text and prompts |

### Phase 6: Testing

#### Backend tests
```python
# test_static_serving.py
def test_root_serves_index_html_when_dist_exists():
    """GET / returns index.html content, not JSON"""

def test_api_routes_take_priority_over_static():
    """GET /api/health returns JSON, not static file"""

def test_spa_fallback_for_vue_routes():
    """GET /projects/123 returns index.html (SPA fallback)"""

def test_static_assets_served():
    """GET /assets/index-abc123.js returns JS file"""

def test_auth_middleware_skips_static():
    """GET /assets/style.css returns 200 without auth token"""

def test_rate_limiter_skips_static():
    """50 rapid static requests don't trigger rate limit"""

def test_websocket_unaffected():
    """WS /ws/{id} still connects on same port"""
```

#### Frontend tests
```javascript
// Test that port detection uses window.location.port
describe('portConfig', () => {
  it('uses window.location.port when available', () => { ... })
  it('falls back to 7272 when port is empty', () => { ... })
})
```

#### Manual testing checklist
- [ ] Fresh install with production mode → single port works
- [ ] Fresh install with dev mode → two ports work, HMR works
- [ ] Existing install → `startup.py` auto-detects dist/ correctly
- [ ] `startup.py --dev` forces Vite even when dist/ exists
- [ ] All Vue routes work via SPA fallback (e.g., `/projects/123`, `/settings`)
- [ ] WebSocket connects and maintains connection on single port
- [ ] MCP endpoints work on single port
- [ ] OAuth flow works (redirect URI correct)
- [ ] SSL/HTTPS mode works on single port
- [ ] LAN access works (non-localhost IP)
- [ ] Rate limiter doesn't throttle page loads
- [ ] API metrics don't count static files

---

## Dependencies and Blockers

**Dependencies:** None — all work is within CE codebase.

**Blockers:** None identified. All changes are additive (production mode) or mechanical (port fixes).

**Risk:** The rate limiter is the sneakiest issue. If missed, the app works in light testing but breaks under real usage when static file requests eat the 300 req/min budget. Test with browser DevTools Network tab open.

---

## Success Criteria

1. `python install.py` (production mode) → `python startup.py` → browser opens `http://localhost:7272` → full app works on single port
2. `python install.py` (dev mode) → `python startup.py` → Vite on 7274, API on 7272 → HMR works
3. Production user switches to dev: `python startup.py --dev` → two-port mode works
4. All existing tests pass
5. New tests cover static serving, middleware exemptions, port detection
6. Documentation updated

---

## Rollback Plan

1. Delete `frontend/dist/` directory → startup.py falls back to Vite dev server
2. Revert `api/app.py` static mount (the conditional check means it's already no-op without dist/)
3. Frontend port fixes are backward-compatible (`window.location.port || '7272'` returns `'7272'` in all existing scenarios)

---

## Files to Modify (Complete List)

**Backend (7 files):**
- `api/app.py` — Static mount, root endpoint conditional, CSRF exemptions
- `api/middleware/auth.py` — Public endpoint list
- `api/middleware/rate_limiter.py` — Static path exclusion
- `api/middleware/metrics.py` — Static path exclusion
- `api/run_api.py` — Log exclusion patterns

**Frontend (13 files):**
- `frontend/index.html`
- `frontend/src/config/api.js`
- `frontend/src/services/configService.js`
- `frontend/src/stores/websocket.js`
- `frontend/src/components/navigation/ConnectionDebugDialog.vue`
- `frontend/src/components/ConnectionStatus.vue`
- `frontend/src/composables/useMcpConfig.js`
- `frontend/src/views/DashboardView.vue`
- `frontend/src/components/AiToolConfigWizard.vue`
- `frontend/src/components/setup/SetupStep2Connect.vue`
- `frontend/src/components/settings/tabs/NetworkSettingsTab.vue`
- `frontend/src/views/SystemSettings.vue`
- `frontend/src/utils/portConfig.js` (NEW — shared utility)

**Startup & Install (3 files):**
- `startup.py` — Production detection, `--dev` flag
- `startup_prod.py` — Deprecate or remove
- `install.py` — Production/dev mode prompt, optional `npm run build`

**Documentation (4+ files):**
- `README.md`
- `CONTRIBUTING.md`
- `docs/SERVER_ARCHITECTURE_TECH_STACK.md`
- `handovers/ROADMAP.md`

**Tests (2 new files):**
- `tests/test_static_serving.py` (NEW)
- `frontend/tests/utils/portConfig.spec.js` (NEW)

**Pre-release cleanup (DONE):**
- `pyproject.toml` -- Removed dead entry point `giljo-setup = "setup_gui:main"` (module never existed). Cleaned up mypy references to `setup_gui`. Would break `pip install .` from repo.
