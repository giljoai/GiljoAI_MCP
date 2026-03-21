# Handover 0832: SSL/HTTPS Admin UI Toggle

**Date:** 2026-03-21
**Priority:** Medium
**Status:** Complete
**Edition Scope:** CE

## Task Summary

Added an interactive SSL/HTTPS toggle to the Admin Settings > Network tab, replacing the previous display-only status indicator. Admins can now enable/disable HTTPS directly from the UI without manual CLI commands or config file editing.

## What Was Built

**Backend** (`api/endpoints/configuration.py`):
- `GET /api/v1/config/ssl` — returns SSL status, cert existence, and file paths (admin-only)
- `POST /api/v1/config/ssl` — toggles SSL on/off in `config.yaml`, auto-generates self-signed certs via OpenSSL when enabling with no existing certificates (admin-only)
- Pydantic models: `SSLToggleRequest`, `SSLStatusResponse`
- Uses existing `_config_io.read_config` / `write_config` for atomic config persistence

**Frontend** (`frontend/src/components/settings/tabs/NetworkSettingsTab.vue`):
- Replaced static HTTPS status display with interactive `v-switch` toggle
- Shows certificate path when certs exist on disk
- "Server restart required" warning banner after toggling
- Error banner with dismissal if cert generation fails
- Self-signed certificate advisory note when SSL is enabled
- Loads live status from `/api/v1/config/ssl` on mount and refresh

## Key Design Decisions

- **No restart from UI**: SSL toggle writes to `config.yaml` but requires manual server restart — changing SSL at runtime would drop active connections
- **Auto-cert generation**: When enabling SSL with no existing certs, the endpoint generates self-signed certs using OpenSSL (same logic as `scripts/generate_ssl_cert.py`)
- **Existing patterns reused**: `_config_io` for config persistence, `require_admin` for auth, `getApiBaseURL()` + CSRF for frontend API calls

## Files Modified

- `api/endpoints/configuration.py` — 2 new endpoints + 2 Pydantic models (~100 lines added)
- `frontend/src/components/settings/tabs/NetworkSettingsTab.vue` — template + script rewritten for interactive SSL management

## Quality Checks

- Both endpoints use `require_admin` (admin-only access)
- Exception-based error handling (HTTPException, no dict returns)
- `Path.cwd()` for cross-platform file paths
- No dead code, no commented-out code
- Functions under 200 lines
- Frontend type-checks clean (`vue-tsc --noEmit`)
- Backend imports clean (verified with Python import)
