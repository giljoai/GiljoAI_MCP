# Handover 0900: WebSocket Debug Panel → Connection Health Panel

**Date:** 2026-04-02
**Edition Scope:** CE
**Priority:** Medium
**Estimated Complexity:** 1 session (~1 hour)
**Status:** COMPLETE

## Task Summary

Simplify the WebSocket Debug Panel from a developer-oriented debug tool into a user-friendly "Connection Health" panel. Remove internal diagnostics (subscriptions, message counters, test harness) and keep only what helps a user answer: "Why isn't my stuff updating?"

## Context and Background

The current `ConnectionDebugDialog.vue` exposes 5 accordion sections and 4 action buttons designed for developer debugging. For a shipped CE product, most of this is confusing noise for end users. The panel should surface connection health at a glance, recent events for troubleshooting, and a single reconnect action.

**Current state (what exists):**

| Section | Content | Verdict |
|---|---|---|
| Connection Status | State, client ID, WS URL, timestamps | **KEEP** — core troubleshooting info |
| Statistics | Messages sent/received, queued, connection attempts (4 tonal cards) | **TRIM** — only queued messages count is useful |
| Active Subscriptions | Raw event channel names | **REMOVE** — internal dev detail |
| Recent Events | Last 10 WS events with icons | **KEEP** — simplify labels |
| Last Error | Error alert (conditional) | **KEEP** — directly actionable |

| Button | Purpose | Verdict |
|---|---|---|
| Force Reconnect | Disconnect + reconnect | **KEEP** — the one user action |
| Simulate Drop | Kill connection deliberately | **REMOVE** — dev testing only |
| Send Test | Send test message over WS | **REMOVE** — dev testing only |
| Clear Queue | Clear queued messages | **REMOVE** — queue drains on reconnect |
| Debug Mode toggle | Enable verbose console logging | **REMOVE** — dev-only, floods console |

## Technical Details

### Files to Modify

**1. `frontend/src/components/navigation/ConnectionDebugDialog.vue`** (sole file)

This is a self-contained component. No backend changes. No database changes. No cascading impact.

### No Database Changes
Pure frontend component refactor — no migration needed.

### No Backend Changes
The WebSocket store (`stores/websocket.js`) retains all methods; we simply stop calling the dev-only ones from the UI.

## Implementation Plan

### Phase 1: Rename and Restructure Dialog

1. Rename dialog title from "WebSocket Debug Panel" to "Connection Health"
2. Replace `mdi-bug` icon with `mdi-wifi` or connection-appropriate icon
3. Use proper `dlg-header` / `dlg-footer` classes per dialog anatomy convention

### Phase 2: Simplify Sections

**Connection Status section** — Keep as-is (state, client ID, WS URL, timestamps). This is the primary info panel.

**Statistics section** — Remove the 4-card grid. Add a single "Queued Messages" line item into the Connection Status list (only show if queue > 0).

**Subscriptions section** — Remove entirely.

**Recent Events section** — Keep, but review event labels. If event messages are already human-readable, no change needed. If they show raw channel names, map to friendly labels.

**Last Error section** — Keep as-is (conditional, only shows on error).

### Phase 3: Simplify Actions

Replace the 5-button action bar with:
- **Force Reconnect** button (keep, primary action)
- **Close** button (text variant)

Remove: Simulate Drop, Send Test, Clear Queue buttons, Debug Mode toggle.

### Phase 4: Polish

- Ensure the dialog follows the `dlg-header` / `dlg-footer` pattern from `main.scss`
- Use `smooth-border` class on the card
- Dialog should be narrower since content is simpler — consider reducing `max-width` from 800 to 560

## Quality Gates

- [ ] Dialog opens from connection status indicator in nav
- [ ] Shows current connection state (connected/disconnected/reconnecting)
- [ ] Shows WS URL and timestamps
- [ ] Shows queued message count when > 0
- [ ] Shows recent events
- [ ] Shows last error when present
- [ ] Force Reconnect button works
- [ ] No references to removed features (Simulate Drop, Send Test, etc.)
- [ ] Dialog follows `dlg-header` / `dlg-footer` anatomy
- [ ] `smooth-border` on card
- [ ] WebSocket store unchanged (no method removal — other consumers may use them)

## Risk Assessment

**Low risk.** Single frontend component, no backend changes, no store API changes. The websocket store methods (`setDebugMode`, `send` for test messages) remain available for future dev tooling or browser console use — we just remove them from the UI.
