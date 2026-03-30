# Phase E: User Settings

**Suite:** UI Functional Test Suite (0769-UI)
**Prerequisite:** User logged in
**Creates data:** No — read-only navigation and verification

---

## Steps

### E1. Navigate to Settings
1. Click user menu or navigate to `/settings`
2. **Verify:** Settings page loads with tabs
3. **Verify:** Tabs visible: Startup, Notifications, Agents, Context, API Keys, Integrations
4. **Verify:** Zero console errors

### E2. Startup Tab
1. Click "Startup" tab (should be default)
2. **Verify:** Setup wizard button visible ("Open Setup Wizard")
3. **Verify:** "What is GiljoAI MCP?" tips button works (opens dialog)
4. Close any dialogs
5. **Verify:** Zero console errors

### E3. Notifications Tab
1. Click "Notifications" tab
2. **Verify:** Notification preferences load
3. **Verify:** Toggle switches render correctly
4. **Verify:** Zero console errors

### E4. Agents Tab
1. Click "Agents" tab
2. **Verify:** Agent template list or configuration loads
3. **Verify:** Zero console errors

### E5. Context Tab
1. Click "Context" tab
2. **Verify:** Context depth settings load
3. **Verify:** Zero console errors

### E6. API Keys Tab
1. Click "API Keys" tab
2. **Verify:** API key management interface loads
3. **Verify:** "Create API Key" button visible
4. **Verify:** Existing keys listed (if any)
5. **Verify:** Date formatting on key creation dates
6. **Verify:** Zero console errors

### E7. Integrations Tab
1. Click "Integrations" tab
2. **Verify:** Integration cards render:
   - Git + GiljoAI 360 Memory (not "Git + 360 Memory" — 0769b fix)
   - MCP integration card
   - Serena integration card
3. **Verify:** Card descriptions match current text
4. **Verify:** Zero console errors

---

## Pass Criteria
- [ ] All 6 settings tabs load without errors
- [ ] Integration card text matches 0769b updates
- [ ] API key management renders with correct date formatting
- [ ] Zero console errors across all tabs
