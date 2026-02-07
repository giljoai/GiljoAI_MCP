# Handover 0700a: Remove Light Mode Theme Support

## Series Context

You are executing **handover 0700a** in the **0700 Code Cleanup Series**.

| Status | Value |
|--------|-------|
| Series progress | 0/12 complete |
| Previous handover | None (this is the first) |
| Next handover | 0700 - Cleanup Index Creation |
| Priority | MEDIUM |
| Estimated effort | 2-3 hours |

---

## Your Mission

**Simplify the GiljoAI MCP frontend by removing light mode theme support, going dark-mode only.**

### Why This Matters
- Developer tools conventionally use dark mode (VS Code, Chrome DevTools)
- Light mode has contrast issues with the yellow brand color (#ffc300)
- Removes ~500+ lines of theme-switching code across 15+ files
- Eliminates maintenance burden of two parallel theme systems

### Scope Summary
1. **Core Theme System** - Remove `lightTheme` export from `theme.js`, simplify `main.js` and `settings.js`
2. **UI Component Cleanup** - Remove theme toggle button and theme selector UI
3. **Icon Simplification** - Always use dark theme icon variants (remove conditionals)
4. **CSS Cleanup** - Delete all `.v-theme--light` and `[data-theme="light"]` blocks
5. **Test Updates** - Remove theme toggle tests
6. **Asset Deletion** - Delete unused light mode SVG assets (after verification)

---

## Key Files to Modify

### Phase 1: Core Theme System
| File | Action |
|------|--------|
| `frontend/src/config/theme.js` | DELETE `lightTheme` export (~35 lines) |
| `frontend/src/main.js` | Remove lightTheme import, simplify theme init |
| `frontend/src/stores/settings.js` | DELETE `toggleTheme()`, make `isDarkTheme` always true |

### Phase 2: UI Components
| File | Action |
|------|--------|
| `frontend/src/components/navigation/NavigationDrawer.vue` | DELETE "Toggle Theme" button |
| `frontend/src/views/UserSettings.vue` | DELETE theme selector radio buttons |

### Phase 3: Icon Components (12 files)
Remove conditional icon path logic from:
- `NavigationDrawer.vue`, `GiljoFaceIcon.vue`, `AppBar.vue`
- `Login.vue`, `FirstLogin.vue`, `UserSettings.vue`
- `AgentDetailsModal.vue`, `JobsTab.vue`, `GilMascot.vue`
- `McpIntegrationCard.vue`, `AdminIntegrationsTab.vue`, `WelcomeView.vue`

### Phase 4: CSS Files
| File | Lines | Description |
|------|-------|-------------|
| `frontend/src/styles/main.scss` | 24-33 | Light theme CSS variables |
| `frontend/src/App.vue` | ~47-49 | Light mode background |
| `frontend/src/views/Login.vue` | ~348-351 | Light mode card styling |
| `frontend/src/views/FirstLogin.vue` | ~382-385 | Light mode card styling |
| `frontend/src/components/TemplateManager.vue` | ~1745-1752 | Light mode input styling |
| `frontend/src/components/projects/MessageInput.vue` | ~388-399 | Light mode input border |

### Phase 5: Tests
- `frontend/tests/unit/views/UserSettings.spec.js` - Remove theme toggle tests
- `frontend/tests/unit/components/settings/integrations/McpIntegrationCard.spec.js` - Remove light mode icon tests

### Phase 6: Asset Deletion (LAST - after verification)
```
frontend/public/Giljo_BY.svg
frontend/public/icons/Giljo_BY_Face.svg
frontend/public/icons/Giljo_Inactive_Light.svg
frontend/public/icons/Giljo_Dark_Face.svg
frontend/public/mascot/Giljo_*_Blue_*.svg
```

---

## Context from Previous Agents

**No previous agents** - This is the first handover in the 0700 series.

---

## Documentation to Review/Update

From `doc_impacts.json`:

| Document | Sections | Priority |
|----------|----------|----------|
| `frontend/README.md` | Theme Configuration, Vuetify Setup | HIGH |
| `docs/TESTING.md` | Coverage Targets | LOW (if test changes affect coverage) |

**Note**: If User Settings screenshots exist in documentation showing theme toggle, they need updating.

---

## Execution Protocol

### Required Reads First
1. Full handover spec: `handovers/0700a_remove_light_mode_theme.md`
2. Worker protocol: `handovers/0700_series/WORKER_PROTOCOL.md`
3. Current theme config: `frontend/src/config/theme.js`

### Recommended Subagents
| Agent | Purpose |
|-------|---------|
| `ux-designer` | PRIMARY - UI component cleanup, CSS removal |
| `frontend-tester` | SECONDARY - Verify tests pass, update test files |

### Test Commands
```bash
cd frontend
npm run test:unit          # Run all unit tests
npm run dev                 # Start dev server for manual verification
```

### Verification Checklist (Before Completing)
- [ ] `lightTheme` removed from `theme.js`
- [ ] No theme toggle button in NavigationDrawer
- [ ] No theme selector in UserSettings
- [ ] All icon paths use dark variants only (no conditionals)
- [ ] No `.v-theme--light` or `[data-theme="light"]` CSS exists
- [ ] All tests pass (`npm run test:unit`)
- [ ] No console errors when loading app
- [ ] App loads in dark mode by default
- [ ] Light mode assets deleted (after verification)

---

## Communication Requirements

Before completing, **write to `comms_log.json`** with:

### Required Entry
```json
{
  "id": "<generate-uuid>",
  "timestamp": "<ISO-timestamp>",
  "from_handover": "0700a",
  "to_handovers": ["0700", "0701", "0702", "0703"],
  "type": "info",
  "subject": "Light mode removal complete",
  "message": "Removed light mode theme support. isDarkTheme now always returns true. If any code checks this value for conditional logic beyond theming, that logic is now dead code.",
  "files_affected": ["<list all modified files>"],
  "action_required": false,
  "context": {
    "lines_removed": "<approximate count>",
    "assets_deleted": ["<list deleted files>"]
  }
}
```

### If You Find Issues
Write additional entries for:
- Any code that surprisingly depended on light mode
- Files you couldn't modify due to blockers
- Patterns you noticed that 0700 (cleanup index) should track

---

## State Updates Required

When complete, update `orchestrator_state.json`:

```json
{
  "id": "0700a",
  "status": "complete",
  "started_at": "<when you started>",
  "completed_at": "<ISO timestamp>",
  "worker_session_id": null,
  "docs_updated": ["frontend/README.md"]
}
```

Also update `doc_impacts.json` for any docs you reviewed/updated.

---

## Commit Format

```bash
git add -A
git commit -m "cleanup(0700a): Remove light mode theme support

Simplify frontend by removing light mode, going dark-mode only.
~500 lines of conditional theming code removed.

Changes:
- DELETE lightTheme export from theme.js
- DELETE theme toggle button from NavigationDrawer
- DELETE theme selector from UserSettings
- Simplify all icon paths to dark variants only
- DELETE .v-theme--light CSS blocks
- DELETE unused light mode SVG assets

Docs Updated:
- frontend/README.md (if applicable)

Co-Authored-By: Claude Opus 4.5 <noreply@anthropic.com>"
```

---

## Rollback Plan

If issues occur:
```bash
git checkout frontend/src/config/theme.js
git checkout frontend/src/main.js
git checkout frontend/src/stores/settings.js
# ... restore other files as needed
git checkout frontend/public/  # Restore deleted assets
npm run test:unit  # Verify rollback
```

---

## Begin Execution

1. Read the full handover spec at `handovers/0700a_remove_light_mode_theme.md`
2. Follow the 6-phase Worker Protocol in `WORKER_PROTOCOL.md`
3. Use subagents `ux-designer` and `frontend-tester` for execution
4. Update state files when complete
5. Report completion summary to orchestrator

**Good luck! This is a straightforward cleanup that will make the codebase simpler.**
