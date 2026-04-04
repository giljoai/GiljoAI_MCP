# Handover: Remote Client Certificate Trust Modal

**Date:** 2026-04-03
**From Agent:** User + Claude session
**To Agent:** Next Session
**Priority:** High
**Estimated Complexity:** 4-6 hours
**Status:** Not Started
**Edition Scope:** CE

## Task Summary

When a user installs GiljoAI with HTTPS on a server and connects from a remote machine, the MCP setup fails silently because the client doesn't trust the self-signed certificate. The install.py terminal instructions scroll past unread. This handover adds a certificate trust modal that intercepts remote HTTPS users before the setup wizard, plus a rootCA download endpoint and a matching section in Admin Settings > Network.

**Origin:** Handover 0843 (HTTPS Conditional Install) specced a `GET /api/setup/root-ca` endpoint and a "Connect Another Machine" UI section but only delivered the install.py side. This completes the missing pieces with a smarter UX.

## Context and Background

**The problem flow (today):**
1. User runs `install.py` on server, enables HTTPS, terminal shows cert instructions — user doesn't read them
2. User connects from laptop via HTTPS, gets browser warning, clicks "proceed anyway"
3. Browser page loads but background API calls (port 7272) fail silently due to untrusted cert
4. User creates admin account, enters setup wizard
5. Step 2 (Connect) gives MCP config — user copies it
6. MCP connection fails because Node.js/CLI doesn't trust the cert
7. User is stuck with no clear guidance

**The fix:** After admin account creation, before the setup wizard, detect remote+HTTPS and show a cert trust modal with download link and OS-specific instructions.

**Why 0834b:** Extends 0834 (Dynamic Protocol Resolution) which made all URL generation respect `ssl_enabled`. This completes the HTTPS story for remote clients.

## Technical Details

### Phase 1: Backend — rootCA Download Endpoint

**File:** `api/endpoints/downloads.py` (or `api/endpoints/configuration.py`)

New authenticated endpoint:
```
GET /api/config/root-ca
```
- Requires `get_current_active_user` auth
- Runs `mkcert -CAROOT` to find the CA directory
- Returns `rootCA.pem` as a file download (`application/x-pem-file`)
- Returns 404 if HTTPS is disabled or rootCA.pem doesn't exist

**File:** `api/endpoints/configuration.py`

Add `is_remote_client` to the frontend config response:
- Compare `request.client.host` against `127.0.0.1`, `::1`, and the configured `external_host`
- If none match, the client is remote
- Add field: `"is_remote_client": true/false` to the config response

Reuse existing `_get_client_ip` pattern from `api/middleware/rate_limiter.py` (handles X-Forwarded-For).

### Phase 2: Frontend — Certificate Trust Modal

**New file:** `frontend/src/components/setup/CertTrustModal.vue`

A modal dialog (Teleport to body, same pattern as `SetupWizardOverlay.vue`) shown when:
- `ssl_enabled === true` AND `is_remote_client === true`
- Shown AFTER admin account creation, BEFORE setup wizard opens
- Only shown once per session (dismissed state stored in sessionStorage or a ref)

**Content:**
1. Header: "Install Certificate for Trusted HTTPS"
2. Explanation: "You're connecting from another machine. Your browser accepted the connection, but AI coding tools (Claude Code, Codex CLI, Gemini CLI) need the server's root certificate installed on this machine."
3. Download button: calls `GET /api/config/root-ca` to download `rootCA.pem`
4. OS-specific install instructions (detect via `navigator.platform` or `navigator.userAgentData`):
   - **Windows:** `certutil -addstore -f "ROOT" %USERPROFILE%\Downloads\rootCA.pem`
   - **macOS:** `sudo security add-trusted-cert -d -r trustRoot -k /Library/Keychains/System.keychain ~/Downloads/rootCA.pem`
   - **Linux:** `sudo cp ~/Downloads/rootCA.pem /usr/local/share/ca-certificates/giljoai.crt && sudo update-ca-certificates`
5. NODE_OPTIONS step: `export NODE_OPTIONS="--use-system-ca"` (OS-appropriate variant)
6. "Continue to Setup" button → dismisses modal, opens setup wizard

**Styling:** Follow `.dlg-header` / `.dlg-footer` conventions from `main.scss`. Use `.dlg-header--warning` (amber band) since this is a prerequisite action.

### Phase 3: Integration Point

**File:** Parent component that manages setup wizard display (find where `SetupWizardOverlay` is opened after admin account creation)

Logic:
```
if (ssl_enabled && is_remote_client && !certModalDismissed) {
  show CertTrustModal
  on dismiss → show SetupWizardOverlay
} else {
  show SetupWizardOverlay directly
}
```

### Phase 4: Admin Settings > Network — "Connect Another Machine" Section

**File:** `frontend/src/components/settings/tabs/NetworkSettingsTab.vue`

Add a section (visible only when HTTPS is enabled) with:
- "Connect Another Machine" heading
- Download button for rootCA.pem
- Same OS-specific instructions as the modal
- This fulfills the `install.py` promise: "You can also download it later from Admin Settings > Network."

## Testing Requirements

**Backend tests:**
- `GET /api/config/root-ca` returns PEM file when HTTPS enabled and rootCA exists
- `GET /api/config/root-ca` returns 404 when HTTPS disabled
- `GET /api/config/root-ca` requires authentication
- Frontend config response includes `is_remote_client` field
- `is_remote_client` is `false` for `127.0.0.1` and server's own IP
- `is_remote_client` is `true` for a different IP

**Frontend tests:**
- CertTrustModal renders when `ssl_enabled && is_remote_client`
- CertTrustModal does NOT render when `ssl_enabled && !is_remote_client`
- CertTrustModal does NOT render when `!ssl_enabled`
- Download button triggers file download
- "Continue to Setup" dismisses modal and opens setup wizard
- Modal only shows once per session
- NetworkSettingsTab shows cert download section when HTTPS enabled

**Manual testing:**
1. Fresh install with HTTPS on server machine → no cert modal (local client)
2. Connect from different machine → cert modal appears after admin setup
3. Download rootCA.pem, install it, verify MCP connection works
4. Admin Settings > Network shows download section

## Dependencies and Blockers

**Dependencies:** None — all prerequisite work exists (ssl_enabled config, mkcert integration, setup wizard infrastructure).

**Existing code to reuse:**
- `_get_client_ip` pattern in `api/middleware/rate_limiter.py`
- SSL status endpoint in `api/endpoints/configuration.py`
- `SetupWizardOverlay.vue` patterns for modal structure
- Dialog conventions from `main.scss` (`.dlg-header`, `.dlg-footer`)

## Success Criteria

- Remote HTTPS user sees cert trust modal before setup wizard
- Local HTTPS user (same machine) skips the modal entirely
- rootCA.pem downloads correctly via the UI
- Admin Settings > Network has "Connect Another Machine" with download
- MCP connection succeeds after following the modal instructions
- All tests pass

## Rollback Plan

All changes are additive (new endpoint, new component, new UI section). Revert the commit to restore previous behavior. No database changes, no migration needed.
