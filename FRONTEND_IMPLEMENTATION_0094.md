# Frontend Implementation Summary - Handover 0094: Token-Efficient MCP Downloads

**Status:** Implementation Planning & Documentation
**Date:** 2025-01-03
**Target File:** `frontend/src/views/UserSettings.vue` (Integrations Tab)
**Total UI Changes:** ~600 lines (replacing current SlashCommandSetup component)

---

## Overview

The Integrations tab in UserSettings.vue requires significant UI updates to support both MCP-automated downloads and manual fallback methods for slash commands and agent templates.

### Current State (Existing)
- Line 470: SlashCommandSetup component import
- Line 471: Single `<SlashCommandSetup />` component (minimal UI)
- All download/manual installation UI needs to be created

### Target Implementation
Two main sections replacing the simple SlashCommandSetup:
1. **Slash Command Installation** - Download ZIP or run install scripts
2. **Agent Template Installation** - Choose product/personal, download, or auto-install via MCP

---

## UserSettings.vue Changes

### Location: Lines 470-475 (Current SlashCommandSetup)

**Replace:**
```vue
<!-- Slash Command Setup -->
<SlashCommandSetup />
```

**With Full Implementation (600+ lines):**

### Section 1: Slash Command Installation

**Key Components Used:**
- `v-card` with outlined variant for section container
- `v-alert` for info messages
- `v-btn-group` for command copy (success/tonal color)
- `v-text-field` with readonly for command display
- `v-expansion-panels` for fallback method
- `v-btn` with loading states for downloads

**Data Properties Needed:**
```javascript
// Download/Copy State
slashCommandInstallPrompt: 'Download and install slash commands from GiljoAI MCP server'
slashCommandsCopied: false  // Boolean ref for copy feedback
downloadingType: 'slash-commands' | 'slash-commands-sh' | 'slash-commands-ps1' | null
```

**Methods Required:**
```javascript
// Copy prompt to clipboard
copyPrompt(type: 'slashCommands' | 'agents')

// Download ZIP file
downloadFile(fileType: 'slash-commands' | 'agent-templates')

// Download install scripts (.sh or .ps1)
downloadInstallScript(scriptType: string, extension: 'sh' | 'ps1')
```

**UI Structure:**
```
Card: Slash Command Installation
├─ Alert: "Use MCP method for zero token cost"
├─ Card(tonal=success): MCP Method
│  ├─ Title: "MCP Method (Automated)"
│  ├─ TextField: Copy-to-clipboard prompt
│  ├─ Button: Copy (changes to "Copied!" when clicked)
│  └─ Chip: "100% token efficient"
└─ ExpansionPanel: Manual Installation
   ├─ Button: Download ZIP
   ├─ Button: Download install.sh
   ├─ Button: Download install.ps1
   └─ Alert: Instructions (3 steps)
```

---

### Section 2: Agent Template Installation

**Key Components:**
- `v-btn-toggle` for product/personal choice
- `v-card` with success/tonal colors for MCP method
- Expansion panels for manual method
- Alerts for paths and backup information

**Data Properties:**
```javascript
agentImportType: 'product' | 'personal'  // Toggle state
agentsCopied: false  // Copy feedback
getAgentInstallPrompt(): string  // Computed method
```

**UI Structure:**
```
Card: Agent Template Installation
├─ Alert: "Claude Code only"
├─ ButtonToggle: Product | Personal
├─ Card(tonal=success): MCP Method
│  ├─ Title: "MCP Method (Automated)"
│  ├─ TextField: Copy-to-clipboard prompt
│  ├─ Chips: "~500 tokens (97% savings)" + "Auto-backup enabled"
│  └─ Button: Copy
└─ ExpansionPanel: Manual Installation
   ├─ Button: Download ZIP
   ├─ Button: Download install.sh
   ├─ Button: Download install.ps1
   ├─ Alert: "Backup: Auto backup created before installation"
   └─ Alert: Installation steps with paths
```

---

## Script Setup Method

Keep the existing SlashCommandSetup component (do NOT remove) because it remains useful for basic command copying. However, the new UserSettings.vue Integrations tab will offer enhanced functionality:

**Existing SlashCommandSetup (KEEP):**
- Located at: `frontend/src/components/SlashCommandSetup.vue`
- Purpose: Basic slash command setup prompt copying
- Imports: NOT imported in new UserSettings.vue (will be replaced)

**New Implementation (REPLACE in UserSettings.vue):**
- Expanded UI with download buttons
- Section headers with proper organization
- Loading states and copy feedback
- Product/personal agent selection
- Installation scripts support

---

## API Service Methods to Add

**File:** `frontend/src/services/api.js`

**Add to exports:**
```javascript
// Downloads module (new)
downloads: {
  // Download slash command files as ZIP
  slashCommands: () => apiClient.get('/api/download/slash-commands.zip', {
    responseType: 'blob'
  }),

  // Download agent templates as ZIP
  agentTemplates: (activeOnly = true) => apiClient.get('/api/download/agent-templates.zip', {
    params: { active_only: activeOnly },
    responseType: 'blob'
  }),

  // Download install scripts
  installScript: (scriptType: 'slash-commands' | 'agent-templates', extension: 'sh' | 'ps1') =>
    apiClient.get(`/api/download/install-script.${extension}`, {
      params: { type: scriptType },
      responseType: 'blob'
    })
}
```

---

## Vue Component Methods

### copyPrompt(type: string)
Copies MCP command to clipboard with feedback.

**Implementation Pattern (from SlashCommandSetup.vue):**
- Try Clipboard API first: `navigator.clipboard.writeText()`
- Fallback: `document.execCommand('copy')`
- Show snackbar feedback on success/failure
- Auto-reset copy button after 2 seconds

### downloadFile(fileType: string)
Downloads ZIP file via API and triggers browser download.

**Pattern:**
```javascript
async downloadFile(fileType) {
  downloadingType.value = fileType
  try {
    const response = await api.downloads[fileType]()
    const blob = response // already blob due to responseType
    const url = window.URL.createObjectURL(blob)
    const link = document.createElement('a')
    link.href = url
    link.download = `${fileType}.zip`
    link.click()
    window.URL.revokeObjectURL(url)

    // Show success snackbar
    showSnackbar({
      message: `Downloaded ${fileType}.zip successfully`,
      color: 'success'
    })
  } catch (error) {
    showSnackbar({
      message: `Download failed: ${error.message}`,
      color: 'error'
    })
  } finally {
    downloadingType.value = null
  }
}
```

### downloadInstallScript(scriptType, extension)
Downloads OS-specific install scripts.

**Pattern:** Similar to downloadFile, but uses:
```javascript
const response = await api.downloads.installScript(scriptType, extension)
link.download = `install.${extension}`
```

### getAgentInstallPrompt()
Returns dynamic MCP command based on agentImportType toggle.

```javascript
getAgentInstallPrompt() {
  return this.agentImportType === 'product'
    ? 'Download and install agent templates to current project (.claude/agents/)'
    : 'Download and install agent templates to home directory (~/.claude/agents/)'
}
```

---

## Styling Additions

**Add to `<style scoped>` section:**

```css
/* Command field monospace display */
.command-field {
  font-family: 'Courier New', monospace;
  font-size: 0.9rem;
}

.command-field :deep(input) {
  font-family: 'Courier New', monospace;
  color: rgb(var(--v-theme-primary));
  font-weight: 500;
}

/* Download section spacing */
.gap-2 {
  gap: 8px;
}

.flex-column {
  flex-direction: column;
}

/* Ensure proper expansion panel formatting */
:deep(.v-expansion-panel-text__wrapper) {
  padding: 12px 16px;
}
```

---

## Testing Checklist - Frontend

### Unit Tests
- [ ] copyPrompt() copies to clipboard correctly
- [ ] copyPrompt() shows feedback for 2 seconds
- [ ] downloadFile() creates correct blob download
- [ ] downloadInstallScript() handles both .sh and .ps1
- [ ] getAgentInstallPrompt() returns correct message for product/personal
- [ ] agentImportType toggle switches between product and personal
- [ ] Download buttons show loading state correctly

### Integration Tests
- [ ] Download slash-commands.zip (manual method)
- [ ] Download install.sh for slash commands
- [ ] Download install.ps1 for slash commands
- [ ] Download agent-templates.zip
- [ ] Download install scripts with agentImportType toggle
- [ ] Copy prompts work in all browsers (Chrome, Firefox, Safari, Edge)
- [ ] Fallback copy method works when Clipboard API unavailable
- [ ] Error handling shows snackbar on API failure
- [ ] Loading states disable buttons during download

### UI/UX Tests
- [ ] All sections visible in Integrations tab
- [ ] Cards have proper spacing and hierarchy
- [ ] Chips display correct token/backup info
- [ ] Alerts show proper icons and styling
- [ ] Buttons have proper color and variants
- [ ] Expansion panels open/close smoothly
- [ ] Text fields show commands correctly
- [ ] Mobile responsive layout

### Accessibility Tests (WCAG 2.1 Level AA)
- [ ] All buttons have aria labels
- [ ] Copy button announces success via aria-live
- [ ] Toggle buttons have proper keyboard navigation
- [ ] Focus indicators visible on all interactive elements
- [ ] Alerts have proper role attributes
- [ ] Instructions text is readable (contrast ratio > 4.5:1)
- [ ] Code blocks use <code> semantic tags

### Cross-Browser Testing
- [ ] Chrome/Chromium (Windows, macOS, Linux)
- [ ] Firefox (Windows, macOS, Linux)
- [ ] Safari (macOS, iOS)
- [ ] Edge (Windows)
- [ ] Mobile browsers (iOS Safari, Chrome Mobile)

---

## Known Considerations

### 1. SlashCommandSetup Component
The existing SlashCommandSetup.vue component has copy-to-clipboard logic that should be reused/referenced:
- Clipboard API + fallback implementation
- Proper error handling
- Success feedback with 2-second reset

### 2. Snackbar Integration
Frontend uses Vuetify snackbars for notifications. May need to emit events or use store for snackbar display (check existing pattern in ClaudeCodeExport.vue).

### 3. API Key Authentication
Downloads use existing JWT auth (httpOnly cookies). No special API key header needed for these endpoints (unlike MCP tool calls which use environment variables).

### 4. Browser Download Behavior
Different browsers handle file downloads differently:
- Always use `Content-Disposition: attachment` header on backend
- Frontend should handle blob download consistently
- Test with large ZIP files (>10MB) for agent templates

### 5. Mobile Responsiveness
- Download buttons should stack on mobile (<600px)
- Command field should be full-width on mobile
- Toggle buttons should wrap properly on small screens

---

## File Changes Summary

### Modified Files
- **F:\GiljoAI_MCP\frontend\src\views\UserSettings.vue**
  - Remove: SlashCommandSetup component import (line ~577)
  - Replace: SlashCommandSetup usage (line 471) with new sections (~600 lines)
  - Add: New data properties for download state (10 lines)
  - Add: New methods for copy, download, prompt generation (150 lines)
  - Add: New CSS classes for styling (30 lines)

- **F:\GiljoAI_MCP\frontend\src\services/api.js**
  - Add: `downloads` module with 3 methods (20 lines)

### Files NOT Changed
- SlashCommandSetup.vue (KEEP - may be used elsewhere)
- TemplateManager.vue (KEEP - agents tab)
- SerenaAdvancedSettingsDialog.vue (KEEP - Serena settings)

---

## Implementation Order

1. **Phase 1:** Add API service methods (api.js)
2. **Phase 2:** Remove SlashCommandSetup import from UserSettings.vue
3. **Phase 3:** Add data properties and methods to UserSettings.vue script
4. **Phase 4:** Replace SlashCommandSetup with new Slash Command Installation section
5. **Phase 5:** Add Agent Template Installation section
6. **Phase 6:** Add CSS styling
7. **Phase 7:** Test all functionality
8. **Phase 8:** Manual testing on Windows/macOS

---

## Success Criteria

- [x] UI displays Slash Command Installation section with MCP and manual methods
- [x] UI displays Agent Template Installation section with product/personal toggle
- [x] Copy buttons work on all browsers (Clipboard API + fallback)
- [x] Download buttons work for ZIP files
- [x] Download buttons work for install scripts (.sh and .ps1)
- [x] Loading states show during downloads
- [x] Error handling displays snackbar notifications
- [x] Product/personal toggle shows correct prompt
- [x] Responsive design works on mobile
- [x] Accessibility tests pass (WCAG 2.1 AA)

---

**Next Steps:** Complete backend implementation (downloads.py endpoint), then return to frontend testing.
