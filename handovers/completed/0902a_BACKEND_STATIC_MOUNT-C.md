# Handover 0902a: Backend Static Mount + Middleware Exemptions

**Date:** 2026-04-03
**Priority:** High (CE release blocker)
**Edition Scope:** CE
**Status:** Not Started
**Parent:** 0902 Single-Port Frontend Serving
**Dependencies:** None
**Estimated Complexity:** 2 hours

---

## Task Summary

Add FastAPI static file serving from `frontend/dist/` and exempt static file paths from auth, CSRF, rate limiting, metrics, and logging middleware. This is the backend foundation for single-port serving.

---

## Implementation

### 1. Static file mount + SPA fallback (`api/app.py`)

At the END of `create_app()`, after all `include_router()` calls, add conditional static serving:

```python
from starlette.staticfiles import StaticFiles
from starlette.responses import FileResponse
from pathlib import Path

# Production frontend serving (single-port mode)
dist_dir = Path(state.config.get_nested("paths.static", "frontend/dist"))
if dist_dir.exists() and (dist_dir / "index.html").exists():
    # Wrap the existing root endpoint conditionally
    # (it returns JSON — conflicts with index.html serving)

    # SPA fallback: non-API 404s serve index.html for Vue Router
    original_exception_handlers = dict(app.exception_handlers)

    @app.exception_handler(404)
    async def spa_fallback(request, exc):
        path = request.url.path
        if not path.startswith(("/api", "/ws", "/mcp", "/health", "/docs", "/redoc", "/openapi.json")):
            return FileResponse(str(dist_dir / "index.html"))
        # Re-raise for API routes
        from fastapi.responses import JSONResponse
        return JSONResponse(status_code=404, content={"detail": "Not Found"})

    app.mount("/", StaticFiles(directory=str(dist_dir), html=False), name="static")
```

**CRITICAL:** The `app.mount("/", ...)` must be the LAST mount. FastAPI checks routes top-down; API routes registered via `include_router()` take priority over mounts.

### 2. Conditional root endpoint (`api/app.py`)

The existing `GET /` (around line 524) returns JSON. Wrap it so it only registers when NOT in production mode:

```python
dist_dir = Path(state.config.get_nested("paths.static", "frontend/dist"))
if not (dist_dir.exists() and (dist_dir / "index.html").exists()):
    @app.get("/")
    async def root():
        # ... existing JSON response ...
```

### 3. Auth middleware exemption (`api/middleware/auth.py`)

In `_is_public_endpoint()` (around line 142), add static paths:

```python
# Static file paths (production frontend serving)
if path == "/" or path == "/index.html" or path.startswith("/assets/") or path == "/favicon.ico":
    return True
```

### 4. CSRF middleware exemption (`api/app.py`)

In the `CSRFProtectionMiddleware` configuration (around line 390), add to `exempt_prefixes`:

```python
"/assets",
```

### 5. Rate limiter exclusion (`api/middleware/rate_limiter.py`)

Add early return at the top of `dispatch()`:

```python
# Skip rate limiting for static file requests (production frontend serving)
path = request.url.path
if path == "/" or path == "/index.html" or path.startswith("/assets/") or path == "/favicon.ico":
    return await call_next(request)
```

### 6. Metrics exclusion (`api/middleware/metrics.py`)

Add early return before counter increment:

```python
# Skip metrics for static file requests
path = request.url.path
if path == "/" or path.startswith("/assets/") or path == "/favicon.ico":
    response = await call_next(request)
    return response
```

### 7. Logging exclusion (`api/run_api.py`)

Add to `exclude_patterns` list (around line 204):

```python
"GET /assets/",
"GET /index.html",
"GET /favicon.ico",
```

---

## Files to Modify

| File | Change |
|------|--------|
| `api/app.py` | Static mount, SPA fallback, conditional root endpoint, CSRF exempt |
| `api/middleware/auth.py` | Public endpoint list |
| `api/middleware/rate_limiter.py` | Static path early return |
| `api/middleware/metrics.py` | Static path early return |
| `api/run_api.py` | Log exclusion patterns |

## Testing

```bash
# Build frontend first
cd frontend && npm run build && cd ..

# Start API only
python -m uvicorn api.app:app --host 127.0.0.1 --port 7272

# Test in browser
# http://localhost:7272 should serve the Vue app
# http://localhost:7272/api/health should return JSON
# http://localhost:7272/projects/123 should serve index.html (SPA fallback)
# http://localhost:7272/assets/index-xxx.js should serve JS file
```

## Success Criteria

- [ ] `GET /` serves `index.html` when `frontend/dist/` exists
- [ ] `GET /` returns JSON when `frontend/dist/` does NOT exist
- [ ] `GET /api/health` returns JSON (not index.html)
- [ ] `GET /projects/123` returns index.html (SPA fallback)
- [ ] `GET /assets/*` serves static files without auth
- [ ] Static requests don't count against rate limit
- [ ] Static requests don't inflate API metrics
- [ ] Static requests don't spam logs
