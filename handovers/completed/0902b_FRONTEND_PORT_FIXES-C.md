# Handover 0902b: Frontend Hardcoded Port Fixes

**Date:** 2026-04-03
**Priority:** High (CE release blocker)
**Edition Scope:** CE
**Status:** Complete
**Parent:** 0902 Single-Port Frontend Serving
**Dependencies:** None (parallel with 0902a)
**Estimated Complexity:** 1.5 hours

---

## Task Summary

Fix 13 hardcoded port `7272` references across the frontend so the app auto-detects its serving port via `window.location.port`. This enables single-port serving without breaking two-port dev mode.

---

## Implementation

### Step 1: Create shared utility

Create `frontend/src/utils/portConfig.js`:

```javascript
/**
 * Derive the API port from the current page URL.
 * In production (single-port), window.location.port returns the serving port.
 * In dev mode (Vite on 7274), the empty base URL + proxy handles routing.
 * Falls back to 7272 for edge cases (file:// protocol, tests).
 */
export const getApiPort = () =>
  import.meta.env.VITE_API_PORT || window.API_PORT || window.location.port || '7272'

export const getApiPortInt = () => parseInt(getApiPort(), 10)
```

### Step 2: Fix each file

**IMPORTANT:** Read each file first. Verify the exact line and surrounding code before editing. Line numbers below are from the research phase and may have shifted.

| # | File | What to find | What to change |
|---|------|-------------|----------------|
| 1 | `frontend/index.html` | `const apiPort = 7272;` | `const apiPort = window.location.port \|\| 7272;` |
| 2 | `frontend/src/config/api.js` | `\|\| '7272'` on API_PORT line | `\|\| window.location.port \|\| '7272'` |
| 3 | `frontend/src/services/configService.js` | `\|\| '7272'` in production path | `\|\| window.location.port \|\| '7272'` |
| 4 | `frontend/src/stores/websocket.js` | `\|\| 7272` on wsPort line | `\|\| parseInt(window.location.port) \|\| 7272` |
| 5 | `frontend/src/components/navigation/ConnectionDebugDialog.vue` | `:7272` in wsUrl computed | `:${window.location.port \|\| 7272}` |
| 6 | `frontend/src/components/ConnectionStatus.vue` | `:7272` in wsUrl computed | `:${window.location.port \|\| 7272}` |
| 7 | `frontend/src/composables/useMcpConfig.js` | `\|\| '7272'` in buildServerUrl | `\|\| window.location.port \|\| '7272'` |
| 8 | `frontend/src/views/DashboardView.vue` | `ref(7272)` for serverPort | `ref(parseInt(window.location.port) \|\| 7272)` |
| 9 | `frontend/src/components/AiToolConfigWizard.vue` | `const port = '7272'` in detectServerInfo | `const port = window.location.port \|\| '7272'` |
| 10 | `frontend/src/components/setup/SetupStep2Connect.vue` | `ref('7272')` for serverPort | `ref(window.location.port \|\| '7272')` |
| 11 | `frontend/src/components/settings/tabs/NetworkSettingsTab.vue` | `hint="Default: 7274"` and `hint="Default: 7272"` | Remove hardcoded hints or make dynamic |
| 12 | `frontend/src/views/SystemSettings.vue` | `7274` and `7272` fallbacks | Use config values from backend |
| 13 | `frontend/playwright.config.ts` | `localhost:7274` | Already has env var support — just verify |

### Notes

- **Item 1 (`index.html`)**: This runs BEFORE Vue/Vite loads. Cannot use `import.meta.env`. Must be pure JS: `window.location.port || 7272`.
- **Items 2-3**: These are the critical config files. The `import.meta.env.DEV` check in `api.js` returns empty string for base URL in dev mode (Vite proxy handles it). In production, it constructs `protocol://host:port`. The port fix ensures production uses the correct serving port.
- **Items 5-6**: Template literal change. Make sure backticks are used.
- **Item 13**: Playwright tests already support `PLAYWRIGHT_TEST_BASE_URL` env var. No code change needed, just document.

---

## Files to Modify

| File | Type |
|------|------|
| `frontend/src/utils/portConfig.js` | NEW |
| `frontend/index.html` | Edit |
| `frontend/src/config/api.js` | Edit |
| `frontend/src/services/configService.js` | Edit |
| `frontend/src/stores/websocket.js` | Edit |
| `frontend/src/components/navigation/ConnectionDebugDialog.vue` | Edit |
| `frontend/src/components/ConnectionStatus.vue` | Edit |
| `frontend/src/composables/useMcpConfig.js` | Edit |
| `frontend/src/views/DashboardView.vue` | Edit |
| `frontend/src/components/AiToolConfigWizard.vue` | Edit |
| `frontend/src/components/setup/SetupStep2Connect.vue` | Edit |
| `frontend/src/components/settings/tabs/NetworkSettingsTab.vue` | Edit |
| `frontend/src/views/SystemSettings.vue` | Edit |

## Testing

```bash
cd frontend
npm run test:run  # Existing tests should still pass

# Manual: run in dev mode (npm run dev), verify everything still works on :7274
# Manual: run production build, serve from :7272, verify port auto-detection
```

## Success Criteria

- [ ] All 13 files updated
- [ ] `portConfig.js` utility created
- [ ] Existing frontend tests pass (`npm run test:run`)
- [ ] Dev mode (Vite on :7274) still works correctly
- [ ] No hardcoded `7272` port fallbacks remain without `window.location.port` check
