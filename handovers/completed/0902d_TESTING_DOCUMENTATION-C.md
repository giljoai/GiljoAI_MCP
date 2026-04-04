# Handover 0902d: Testing + Documentation

**Date:** 2026-04-03
**Priority:** High (CE release blocker)
**Edition Scope:** CE
**Status:** COMPLETE
**Parent:** 0902 Single-Port Frontend Serving
**Dependencies:** 0902a + 0902b + 0902c
**Estimated Complexity:** 1.5 hours

---

## Task Summary

Write backend and frontend tests for single-port serving. Update all documentation to reflect production (single port) vs development (two port) architecture.

---

## Implementation

### 1. Backend tests — `tests/test_static_serving.py` (NEW)

```python
"""Tests for production single-port frontend serving."""
import pytest
from pathlib import Path
from unittest.mock import patch
from fastapi.testclient import TestClient


class TestStaticServing:
    """Test static file serving when frontend/dist/ exists."""

    def test_root_serves_index_html_when_dist_exists(self, client_with_dist):
        """GET / returns index.html content, not JSON."""
        response = client_with_dist.get("/")
        assert response.status_code == 200
        assert "text/html" in response.headers["content-type"]

    def test_api_routes_take_priority(self, client_with_dist):
        """GET /api/health returns JSON, not index.html."""
        response = client_with_dist.get("/health")
        assert response.status_code == 200
        assert response.json()["api"] == "healthy"

    def test_spa_fallback_for_vue_routes(self, client_with_dist):
        """GET /projects/123 returns index.html (SPA fallback)."""
        response = client_with_dist.get("/projects/123")
        assert response.status_code == 200
        assert "text/html" in response.headers["content-type"]

    def test_static_assets_served(self, client_with_dist):
        """GET /assets/test.js returns the JS file."""
        response = client_with_dist.get("/assets/test.js")
        assert response.status_code == 200

    def test_auth_skips_static_files(self, client_with_dist):
        """Static files served without authentication."""
        response = client_with_dist.get("/assets/test.css")
        assert response.status_code == 200  # Not 401

    def test_api_404_returns_json(self, client_with_dist):
        """GET /api/nonexistent returns JSON 404, not index.html."""
        response = client_with_dist.get("/api/nonexistent")
        assert response.status_code == 404
        assert "application/json" in response.headers["content-type"]


class TestWithoutDist:
    """Test behavior when frontend/dist/ does NOT exist."""

    def test_root_returns_json_without_dist(self, client_without_dist):
        """GET / returns API info JSON when no dist/ directory."""
        response = client_without_dist.get("/")
        assert response.status_code == 200
        assert "GiljoAI" in response.json().get("name", "")
```

**Note:** The implementing agent must create appropriate pytest fixtures (`client_with_dist`, `client_without_dist`) that mock the dist/ directory presence. Use `tmp_path` to create a fake dist/ with index.html and assets/.

### 2. Frontend tests — `frontend/tests/utils/portConfig.spec.js` (NEW)

```javascript
import { describe, it, expect, vi, beforeEach, afterEach } from 'vitest'

describe('portConfig', () => {
  const originalLocation = window.location

  beforeEach(() => {
    // Reset env vars
    vi.stubEnv('VITE_API_PORT', '')
  })

  afterEach(() => {
    vi.unstubAllEnvs()
  })

  it('uses window.location.port when available', () => {
    // Test with port 7272 in location
    // ... implementation depends on how vitest handles window.location
  })

  it('falls back to 7272 when port is empty string', () => {
    // window.location.port returns "" for default ports (80/443)
  })

  it('prefers VITE_API_PORT env var over location.port', () => {
    vi.stubEnv('VITE_API_PORT', '9999')
    // ...
  })
})
```

### 3. Documentation updates

| Document | What to update |
|----------|---------------|
| `CONTRIBUTING.md` | Add "Development Setup" section: `python startup.py --dev` for hot-reload |
| `docs/SERVER_ARCHITECTURE_TECH_STACK.md` | Update network topology: single-port production, two-port dev. Remove references to 7274 as the main user-facing port. |
| `handovers/ROADMAP.md` | Mark "Production Frontend Serving (0902)" as IN PROGRESS or COMPLETE |
| `handovers/handover_catalogue.md` | Update 0902 status and add 0902a-d entries |

### 4. Run full test suites

```bash
# Backend
pytest tests/ -x -v

# Frontend
cd frontend && npm run test:run
```

---

## Files to Modify/Create

| File | Type |
|------|------|
| `tests/test_static_serving.py` | NEW |
| `frontend/tests/utils/portConfig.spec.js` | NEW |
| `CONTRIBUTING.md` | Edit |
| `docs/SERVER_ARCHITECTURE_TECH_STACK.md` | Edit |
| `handovers/ROADMAP.md` | Edit |
| `handovers/handover_catalogue.md` | Edit |

## Success Criteria

- [ ] Backend static serving tests pass
- [ ] Frontend portConfig tests pass
- [ ] All existing backend tests still pass
- [ ] All existing frontend tests still pass
- [ ] Documentation reflects single-port production architecture
- [ ] ROADMAP and catalogue updated
