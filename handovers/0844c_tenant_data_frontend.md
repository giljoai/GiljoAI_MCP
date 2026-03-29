# Handover 0844c: Tenant Data Export/Import Frontend

**Date:** 2026-03-29
**From Agent:** Planning Session
**To Agent:** Next Session
**Priority:** Medium
**Estimated Complexity:** 1 session
**Status:** Not Started
**Edition Scope:** CE
**Series:** 0844c of 0844a/b/c — read `0844_tenant_data_export_import.md` first for shared context
**Depends On:** 0844a + 0844b must be complete and manually verified

---

## 1. Task Summary

Build the Vue frontend component that integrates export and import into Admin Settings > Database tab. The component provides export-with-progress, file upload, compatibility report dialog with stale backup warning, and import-with-progress. This is the simplest phase — the patterns already exist in the codebase (WebSocket progress, file upload, dialogs).

---

## 2. Context and Background

See `0844_tenant_data_export_import.md` for full context and API endpoint definitions.

**Pre-conditions:**
- 0844a export endpoint is working: `POST /api/v1/settings/export`
- 0844b import endpoints are working: `POST /api/v1/settings/import/analyze` + `POST /api/v1/settings/import/execute`
- Both have been manually verified with round-trip testing

**Existing patterns to reference:**
- WebSocket progress: search existing components for WebSocket event listeners
- File upload: `ProductForm.vue:160` has `v-file-input` with accept filtering
- Multi-step dialogs: existing `v-dialog` patterns throughout the app
- Admin settings tabs: `SystemSettings.vue` — the parent view
- API client: `frontend/src/services/api.js` — `settings` section

---

## 3. Technical Details

### Files to Create

| File | Purpose |
|------|---------|
| `frontend/src/components/settings/TenantDataManager.vue` | Export/Import UI component |

### Files to Modify

| File | Change |
|------|--------|
| `frontend/src/views/SystemSettings.vue` (line 60-78) | Add `<TenantDataManager />` below `<DatabaseConnection>` in database `v-window-item` |
| `frontend/src/services/api.js` | Add 3 API client methods to `settings` section |

### API Client Methods

Add to `frontend/src/services/api.js` inside the `settings` object:

```javascript
// Tenant data export/import (Handover 0844)
exportTenantData: () => apiClient.post('/api/v1/settings/export'),
analyzeImport: (formData) => apiClient.post('/api/v1/settings/import/analyze', formData, {
  headers: { 'Content-Type': 'multipart/form-data' },
  timeout: 120000,
}),
executeImport: (analysisToken) => apiClient.post('/api/v1/settings/import/execute', {
  analysis_token: analysisToken,
}),
```

### SystemSettings.vue Integration

Inside the database `v-window-item` (currently lines 60-78), add below `</DatabaseConnection>`:

```vue
<!-- Tenant Data Export/Import - Handover 0844c -->
<v-divider class="my-6" />
<TenantDataManager />
```

---

## 4. TenantDataManager.vue Component Design

### Layout

Two sections inside a `v-card`:

**Section 1 — Export**
- Header: "Data Backup" with `mdi-database-export` icon
- Subtitle: "Download all your data as a portable backup file"
- "Export My Data" button (`v-btn`, `smooth-border` class, primary color)
- On click: shows `v-progress-linear` fed by WebSocket `tenant:export_progress` events
- On complete: triggers browser download via the returned URL
- Shows brief model count summary after completion

**Section 2 — Import**
- Header: "Restore Data" with `mdi-database-import` icon
- Subtitle: "Upload a previously exported backup"
- `v-file-input` accepting `.zip` only (`accept=".zip"`)
- Multi-step flow (managed by reactive state, not separate routes):

### Import Flow Steps

**Step 1 — Upload & Analyze**
User selects ZIP → auto-upload to `/import/analyze` → show loading spinner

**Step 2 — Compatibility Report Dialog (`v-dialog`)**
Shows the `SchemaCompatibilityReport` returned by the analyze endpoint:

- **Version banner** at top:
  - Same version: green `v-alert` — "This backup matches your current database version."
  - Different version: amber `v-alert` — "This backup was created on version {export_revision}. Your current version is {current_revision}."
- **Stale backup warning** (always shown):
  - `v-alert type="warning"` — _"This backup was created on {exported_at formatted as readable date}. Records modified after this date will be reverted to their {date} state."_
  - This is the key UX addition from the PM review. The `exported_at` timestamp is already in the SchemaCompatibilityReport.
- **Model list** — `v-list` with one item per model:
  - Green `mdi-check-circle` — model present, no column issues
  - Amber `mdi-alert` — model has dropped or new columns (expandable detail showing which columns)
  - Record count chip per model
- **Bottom actions:**
  - "Cancel" button (outlined)
  - "Proceed with Import" button (primary, `smooth-border`)

**Step 3 — Import Progress**
After user confirms, call `/import/execute` with the analysis token. Show `v-progress-linear` fed by WebSocket `tenant:import_progress` events. Display current model being imported.

**Step 4 — Result Summary**
On completion, show a summary `v-dialog`:
- Per-model: inserted / updated / skipped counts
- Vision files: extracted / skipped counts
- TSVECTOR: regenerated count
- Any warnings
- "Done" button to close

### WebSocket Integration

Listen for events on the existing WebSocket connection:

```javascript
// In setup() or onMounted()
const ws = useWebSocket()  // or however the app's WS composable works

ws.on('tenant:export_progress', (data) => {
  exportProgress.value = { model: data.model, current: data.current, total: data.total }
})

ws.on('tenant:import_progress', (data) => {
  importProgress.value = { model: data.model, current: data.current, total: data.total, phase: data.phase }
})
```

Check existing components for the WebSocket pattern — don't reinvent it.

### Error Handling

- Upload failure: show `v-alert type="error"` with message
- Checksum failure (from analyze or execute): show specific error — "Backup file appears corrupted or tampered"
- Import failure: show error with rollback confirmation — "Import failed and was rolled back. No data was changed."
- Network timeout on large uploads: the `timeout: 120000` in the API client gives 2 minutes

---

## 5. Implementation Plan

### Step 1: API Client Methods
Add the 3 methods to `api.js`. Quick, testable.

### Step 2: TenantDataManager.vue — Export Section
Build the export button, progress bar, and download trigger. Use existing WebSocket pattern from the codebase.

### Step 3: TenantDataManager.vue — Import Section
Build the file input, upload-to-analyze flow, and the compatibility report dialog.

### Step 4: Stale Backup Warning
Wire `exported_at` from the report to the warning banner. Format the date for readability.

### Step 5: Import Execution + Result
Build the progress view and result summary dialog.

### Step 6: Integration into SystemSettings.vue
Add the component below DatabaseConnection. Import and register it.

### Step 7: Polish
- `smooth-border` class on all rounded buttons/cards
- Vuetify theme variables for colors (no hardcoded hex)
- Keyboard navigability on all interactive elements
- Loading states on buttons (disable during operations)

---

## 6. Testing Requirements

### Component Tests
- `test_export_button_triggers_api_call`
- `test_export_progress_bar_updates_from_websocket`
- `test_import_file_input_accepts_only_zip`
- `test_compatibility_dialog_shows_model_list`
- `test_stale_backup_warning_shows_exported_at_date`
- `test_version_mismatch_shows_amber_alert`
- `test_same_version_shows_green_alert`
- `test_import_progress_bar_updates_from_websocket`
- `test_result_summary_shows_per_model_counts`
- `test_error_states_display_correctly`

### Manual Testing
1. Full end-to-end: export button → download ZIP → import button → select ZIP → analyze → review report → confirm → import → result
2. Verify stale backup warning shows the correct date from the manifest
3. Verify version mismatch banner when importing an older export
4. Try uploading a non-ZIP file → verify rejection
5. Try uploading a corrupt ZIP → verify error message
6. Verify 403 if non-admin user accesses the Database tab (should already be gated by SystemSettings)

---

## 7. Dependencies and Blockers

**Dependencies:**
- **0844a + 0844b must be complete and manually verified**
- All 3 API endpoints working
- WebSocket events firing from backend

**Known Blockers:** None.

---

## 8. Success Criteria

- TenantDataManager component renders in Admin Settings > Database tab
- Export: button → progress → download works end-to-end
- Import: file select → analyze → report dialog → confirm → progress → result works end-to-end
- Stale backup warning displays `exported_at` date from manifest
- Schema version mismatch shown with amber banner
- Column diffs shown per model with expandable details
- All interactive elements keyboard-navigable
- `smooth-border` class on rounded elements
- Vuetify theme variables for colors
- All component tests pass

---

## 9. Rollback Plan

Delete `TenantDataManager.vue`. Remove `<TenantDataManager />` from `SystemSettings.vue`. Remove 3 methods from `api.js`. Backend endpoints remain functional (usable via curl/API directly).

---

## 10. Additional Resources

- Admin settings view: `frontend/src/views/SystemSettings.vue`
- Database tab component: `frontend/src/components/DatabaseConnection.vue`
- File upload pattern: `frontend/src/components/products/ProductForm.vue:160`
- API client: `frontend/src/services/api.js`
- Existing WebSocket usage: search components for WebSocket composable/event listeners
- Smooth border utility: `frontend/src/styles/main.scss` (`.smooth-border` class)

---

## Chain Execution Instructions (Orchestrator-Gated v3)

You are **session 3 of 3** (final session) in the 0844 chain. You are on branch `feature/0844-tenant-data-export-import`.

### Step 1: Read Chain Log
Read `prompts/0844_chain/chain_log.json`
- Check `orchestrator_directives` — if contains "STOP", halt immediately
- **Read 0844b's `notes_for_next` carefully** — it contains the exact API response schemas (SchemaCompatibilityReport, ImportResult), WebSocket event payloads, and analysis_token flow. Build your UI against what was actually implemented, not just the handover plan.
- Also review 0844a's `notes_for_next` for any export-specific details.

### Step 2: Read Shared Context
Read `handovers/0844_tenant_data_export_import.md` — the series coordinator.

### Step 3: Verify Prerequisites
Confirm both 0844a and 0844b session statuses are `"complete"` in the chain log. If not, STOP and report to orchestrator.

### Step 4: Mark Session Started
Update your session in `prompts/0844_chain/chain_log.json`:
```json
"status": "in_progress", "started_at": "<current ISO timestamp>"
```

### Step 5: Execute Handover Tasks
Implement everything in this document. Use `ux-designer` and `frontend-tester` subagents.

**CRITICAL:** Read the actual API endpoint code (created by 0844a + 0844b) before building the frontend. Your API calls, response handling, and WebSocket listeners must match what was actually built.

### Step 6: Update Chain Log
Update your session in `prompts/0844_chain/chain_log.json` with:
- `tasks_completed`, `deviations`, `blockers_encountered`
- `notes_for_next`: null (this is the final session)
- `cascading_impacts`: none expected
- `summary`: 2-3 sentences including commit hash
- `status`: "complete"
- `completed_at`: ISO timestamp

### Step 7: Commit and STOP
```bash
git add -A && git commit -m "feat(0844c): tenant data export/import frontend — TenantDataManager component, compatibility report dialog, stale backup warning"
```
Update the chain log:
```bash
git add prompts/0844_chain/chain_log.json && git commit -m "docs: 0844c chain log — session complete, chain finished"
```

**Do NOT spawn any further terminals.** The orchestrator will:
1. Review the final chain log
2. Perform end-to-end UI testing (export button → download → import button → analyze → confirm → complete)
3. Set `final_status` to "complete" in the chain log
4. Merge the feature branch to master
