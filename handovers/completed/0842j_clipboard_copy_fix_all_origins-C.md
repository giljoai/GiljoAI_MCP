# Handover 0842j: Clipboard Copy Fix — All Origins + Dialog Compatibility

**Series:** 0842 Vision Document Analysis
**Status:** COMPLETE
**Branch:** `feature/0842-vision-doc-analysis`
**Edition Scope:** CE

---

## Problem Statement

The "Stage Analysis" button in the product setup wizard (handover 0842i) showed "Prompt Copied!" but nothing was actually copied to the clipboard. This affected users accessing the app via LAN/WAN IP addresses (non-secure HTTP contexts). Additional bugs included the create wizard breaking mid-flow and ghost product cards after DB deletion.

## Root Cause

**The real bug was in `useClipboard.js` — the `execCommand('copy')` fallback appended a hidden textarea to `document.body`, but Vuetify dialogs with `retain-focus` immediately steal focus from elements outside the dialog.** The textarea lost focus before `execCommand('copy')` could execute, so the copy silently failed while returning `true`.

This only affected clipboard copy inside Vuetify dialogs on non-secure HTTP contexts (LAN IP, WAN IP, DNS over HTTP). On secure contexts (localhost, HTTPS), `navigator.clipboard.writeText` was used instead, bypassing the issue entirely.

## Investigation Path

The debugging process went through several incorrect hypotheses before finding the real cause:

1. **Hypothesis: `async` function breaks user gesture** — Tested whether `await` before `copyToClipboard()` caused the browser to lose the user gesture context. Disproved: Stage Project uses the same async pattern and works fine on `10.1.0.237`.

2. **Hypothesis: `@click.stop` prevents clipboard** — Removed `.stop` modifier from the button. Button click handler fired, but copy still failed. `.stop` was not the cause.

3. **Hypothesis: Button nested in `v-radio-group` swallows clicks** — Moved button outside the radio group. Click handler fired, but copy still failed. Nesting was not the cause.

4. **Hypothesis: `navigator.clipboard` unavailable on non-secure context** — Confirmed `isSecureContext=false` on IP access, but the `execCommand` fallback should have handled this. Stage Project proved the fallback works on the same IP.

5. **Root cause found: Vuetify `retain-focus` trap** — The key difference between Stage Project (works) and Stage Analysis (fails) was that Stage Analysis runs inside a `v-dialog` with `retain-focus`. The composable's `fallbackCopy` appended a textarea to `document.body` (outside the dialog), and Vuetify's focus trap immediately redirected focus back into the dialog, preventing `execCommand('copy')` from working.

## Fix

**`useClipboard.js`** — Changed `fallbackCopy` to append the hidden textarea inside the active Vuetify overlay (if one exists) instead of `document.body`:

```js
// Before
document.body.appendChild(textarea)

// After
const container = document.querySelector('.v-overlay--active .v-overlay__content') || document.body
container.appendChild(textarea)
```

This ensures focus stays within the dialog's focus trap, and `execCommand('copy')` works correctly. Falls back to `document.body` when no dialog is active (preserving existing behavior for all non-dialog clipboard copies).

## All Files Changed

| File | Changes |
|------|---------|
| `frontend/src/composables/useClipboard.js` | Append textarea inside active overlay; improved `readonly` attr and opacity |
| `frontend/src/components/products/ProductForm.vue` | Check `copyToClipboard` return value; show inline fallback textarea on failure; product watcher skips `loadProductData()` during create mode |
| `frontend/src/views/ProductsView.vue` | `isEdit` prop uses `&& !autoSavedForAnalysis` to preserve wizard flow; 404-safe delete in `confirmDeleteProduct`, `confirmDelete`, `closeDialog` |
| `frontend/src/components/AgentExport.vue` | Replaced inline clipboard implementation with shared `useClipboard` composable |

## Clipboard Compatibility Matrix

| Access Mode | Secure Context | Method | Inside Dialog | Works |
|---|---|---|---|---|
| localhost (HTTP) | Yes | `navigator.clipboard.writeText` | Yes | Yes |
| LAN IP (HTTP) | No | `execCommand` (overlay-aware) | Yes | Yes |
| WAN IP (HTTP) | No | `execCommand` (overlay-aware) | Yes | Yes |
| DNS (HTTPS/SaaS) | Yes | `navigator.clipboard.writeText` | Yes | Yes |
| Any (no dialog) | Any | Same as above, falls back to `document.body` | N/A | Yes |

## Secondary Fixes (same commit)

1. **Wizard flow preserved during create** — When file upload silently creates a product, `isEdit` no longer flips to `true`. The "Next" button and tabbed wizard flow remain intact.

2. **Ghost product 404 handling** — If a product exists in the frontend but not in the DB, delete operations handle 404 gracefully (clean up UI card, show informational toast).

3. **AgentExport.vue** — Consolidated duplicate clipboard implementation to use the shared composable.

## Testing Notes

- Verified on `localhost:7274` and `10.1.0.237:7274`
- Stage Analysis button copies prompt with correct product UUID
- Stage Project button still works (regression check)
- Build passes (`vite build`)
- No backend changes required
