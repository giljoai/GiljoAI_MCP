# Frontend Testing Checklist - Handover 0094: Token-Efficient MCP Downloads

**Target Files:**
- `F:\GiljoAI_MCP\frontend\src\views\UserSettings.vue` (Main implementation)
- `F:\GiljoAI_MCP\frontend\src\services\api.js` (API methods)

**Testing Scope:** Frontend UI/UX for downloads and clipboard operations
**Date:** Implementation Phase (Post-Backend)

---

## Manual Testing Checklist

### Browser Testing

#### Google Chrome (Windows/macOS/Linux)
- [ ] Navigate to Settings → Integrations tab
- [ ] Verify Slash Command Installation section displays
- [ ] Verify Agent Template Installation section displays
- [ ] Copy slash command prompt (should show "Copied!" feedback)
- [ ] Wait 2 seconds, verify button resets to "Copy"
- [ ] Download slash-commands.zip (should trigger file download)
- [ ] Download install.sh (should trigger file download)
- [ ] Download install.ps1 (should trigger file download)
- [ ] Toggle product/personal agents
- [ ] Copy agent install prompt (should show "Copied!" feedback)
- [ ] Download agent-templates.zip

#### Mozilla Firefox (Windows/macOS/Linux)
- [ ] Repeat all tests from Chrome checklist
- [ ] Test clipboard fallback method (if Clipboard API unavailable)
- [ ] Verify copy button shows success feedback

#### Apple Safari (macOS/iOS)
- [ ] Repeat all tests from Chrome checklist
- [ ] Test on both desktop Safari and mobile Safari
- [ ] Verify clipboard works on iOS (may require different handling)

#### Microsoft Edge (Windows)
- [ ] Repeat all tests from Chrome checklist
- [ ] Verify downloads work correctly

---

### UI/UX Testing

#### Slash Command Installation Section
- [ ] Section title displays "Slash Command Installation"
- [ ] Subtitle displays correct text
- [ ] Info alert shows with lightbulb icon
- [ ] "MCP Method (Automated)" card shows with success color
- [ ] Command text field displays `/setup_slash_commands`
- [ ] Copy button shows "mdi-content-copy" icon initially
- [ ] Copy button shows "mdi-check" icon after click
- [ ] Copy button text changes to "Copied!" after click
- [ ] Chip shows "100% token efficient"
- [ ] Manual Installation expansion panel opens/closes smoothly
- [ ] Download slash-commands.zip button visible
- [ ] Download install.sh button visible
- [ ] Download install.ps1 button visible
- [ ] Instructions alert shows with 3 numbered steps
- [ ] All buttons have proper styling and hover states
- [ ] Loading spinners appear during downloads

#### Agent Template Installation Section
- [ ] Section title displays "Agent Template Installation"
- [ ] Subtitle displays correct text
- [ ] Info alert about Claude Code only support
- [ ] Product/Personal toggle displays correctly
- [ ] Product button selected by default
- [ ] Toggle shows "Product Agents" and "Personal Agents" labels
- [ ] Location info alert shows installation paths
- [ ] MCP Method card displays with success color
- [ ] Command text field displays `/gil_import_productagents` initially
- [ ] Command text changes to `/gil_import_personalagents` when Personal selected
- [ ] Copy button works for both product and personal commands
- [ ] Chips show "~500 tokens (97% savings)" and "Auto-backup enabled"
- [ ] Manual Installation expansion panel works correctly
- [ ] Download buttons show for product agents
- [ ] Download buttons show for personal agents
- [ ] Warning alert about automatic backup
- [ ] Instructions show correct script parameters
- [ ] Mobile layout stacks buttons vertically

---

### Copy-to-Clipboard Testing

#### Clipboard API Path (Modern Browsers)
- [ ] Copy button triggers Clipboard API
- [ ] Console logs indicate Clipboard API usage
- [ ] Copied state shows for exactly 2 seconds
- [ ] Button text reverts to "Copy" after 2 seconds
- [ ] Multiple rapid clicks handled correctly
- [ ] Special characters copied correctly (if any)

#### Fallback Copy Path (Older Browsers)
- [ ] Disable Clipboard API in DevTools
- [ ] Copy button still works via document.execCommand
- [ ] Copied state shows for exactly 2 seconds
- [ ] Console logs indicate fallback usage
- [ ] iOS compatibility code executes if on iOS

#### Error Handling
- [ ] If copy fails, button shows appropriate error state
- [ ] Console logs show any copy errors
- [ ] No exceptions thrown in DevTools console

---

### File Download Testing

#### Slash Commands ZIP Download
- [ ] Download button shows loading spinner
- [ ] File downloads as "slash-commands.zip"
- [ ] ZIP file contains expected content (verify locally)
- [ ] Button loading state clears after download completes
- [ ] File size is reasonable (~50KB estimated)
- [ ] Works with resume/retry if connection interrupted

#### Agent Templates ZIP Download
- [ ] Download button shows loading spinner
- [ ] File downloads as "agent-templates.zip"
- [ ] ZIP file contains multiple .md template files
- [ ] Button loading state clears after download completes
- [ ] File size is reasonable (~200KB estimated)
- [ ] Product vs Personal selection doesn't affect download currently

#### Install Scripts Download
- [ ] install.sh downloads correctly
- [ ] install.ps1 downloads correctly
- [ ] Files are executable (sh files have proper format)
- [ ] Files contain expected content
- [ ] File permissions are correct (644 or 755)

#### Download Error Handling
- [ ] Simulate network failure
- [ ] Error should be caught and logged
- [ ] Button state should reset (not stuck in loading)
- [ ] No exception appears in console (graceful failure)

---

### Responsive Design Testing

#### Desktop (1920x1080)
- [ ] All sections display side-by-side where applicable
- [ ] Buttons display horizontally in download section
- [ ] Text fields are full width
- [ ] Cards have proper spacing

#### Tablet (768x1024)
- [ ] Sections stack appropriately
- [ ] Buttons may wrap but remain clickable
- [ ] Touch targets are at least 44x44px
- [ ] Text fields adjust width

#### Mobile (375x667)
- [ ] Buttons stack vertically
- [ ] Text fields are 100% width
- [ ] Copy buttons don't overlap command text field
- [ ] Expansion panels work with touch
- [ ] All content scrolls without horizontal scroll

---

### Accessibility Testing (WCAG 2.1 Level AA)

#### Keyboard Navigation
- [ ] Tab through all interactive elements (buttons, toggles, expansions)
- [ ] Focus order is logical (top-to-bottom, left-to-right)
- [ ] Focus indicators visible (outline or highlight)
- [ ] Can activate buttons with Enter/Space
- [ ] Can toggle product/personal with arrow keys
- [ ] Can expand/collapse panels with Enter
- [ ] No keyboard traps

#### Screen Reader (NVDA/JAWS/VoiceOver)
- [ ] Section headings announced as h2/h3
- [ ] Alert announcements read correctly
- [ ] Button purposes announced clearly
- [ ] Copy button announces "Copy" or "Copied"
- [ ] Download buttons announce filename being downloaded
- [ ] Toggle buttons announce selected state
- [ ] Form labels associated with text fields

#### Color Contrast
- [ ] Text on colored backgrounds meets 4.5:1 ratio for normal text
- [ ] Text on colored backgrounds meets 3:1 ratio for large text
- [ ] Icons have sufficient contrast
- [ ] Hover/focus states have sufficient contrast
- [ ] Don't rely solely on color to convey meaning

#### Form Elements
- [ ] All buttons have text labels (not just icons)
- [ ] Text fields have associated labels or are read-only clearly
- [ ] Toggle buttons have clear labels
- [ ] Required information (if any) is clearly marked

---

### State Management Testing

#### Copy Feedback State
- [ ] slashCommandsCopied ref updates correctly
- [ ] agentsCopied ref updates correctly
- [ ] States are independent (copying slash command doesn't affect agent state)
- [ ] States reset after 2 seconds automatically
- [ ] Multiple copy actions reset timer correctly

#### Download State
- [ ] downloadingType ref updates correctly
- [ ] Multiple simultaneous downloads handled correctly
- [ ] downloadingType resets to null after download completes
- [ ] Button :loading prop reflects downloadingType

#### Toggle State
- [ ] agentImportType starts as 'product'
- [ ] Toggling updates command prompt in real-time
- [ ] State persists across tab navigation
- [ ] State doesn't reset unexpectedly

---

### Integration Testing

#### API Integration
- [ ] Download endpoints respond with blob data
- [ ] Authorization headers sent correctly
- [ ] API errors handled gracefully
- [ ] Network timeouts handled

#### Component Integration
- [ ] UserSettings.vue mounts without errors
- [ ] Integrations tab loads successfully
- [ ] No console errors on tab change
- [ ] No memory leaks on unmount

---

### Cross-Platform Install Scripts Testing

#### Windows PowerShell (.ps1 scripts)
- [ ] Script downloads correctly
- [ ] Script opens in default editor
- [ ] Script can be run: `powershell -ExecutionPolicy Bypass -File install.ps1`
- [ ] Script creates correct directories
- [ ] Script shows output messages

#### macOS Bash (.sh scripts)
- [ ] Script downloads correctly
- [ ] Script needs execute permission: `chmod +x install.sh`
- [ ] Script runs: `bash install.sh`
- [ ] Script creates correct directories
- [ ] Script works with both bash and zsh

#### Linux Bash (.sh scripts)
- [ ] Same as macOS testing above
- [ ] Works with different distributions (Ubuntu, Fedora, etc.)

---

## Automated Testing Checklist

### Unit Tests
- [ ] Test `copyPrompt()` with Clipboard API
- [ ] Test `copyPrompt()` with fallback method
- [ ] Test `copyPrompt()` timeout behavior
- [ ] Test `downloadFile()` with slash-commands
- [ ] Test `downloadFile()` with agent-templates
- [ ] Test `downloadInstallScript()` with all combinations
- [ ] Test `getAgentInstallPrompt()` product variant
- [ ] Test `getAgentInstallPrompt()` personal variant
- [ ] Test API service methods return blobs
- [ ] Test error handling in download methods

### Component Tests
- [ ] Render Integrations tab
- [ ] Render Slash Command section
- [ ] Render Agent Template section
- [ ] Render product/personal toggle
- [ ] Render all buttons and their states
- [ ] Test button click handlers
- [ ] Test ref updates
- [ ] Test computed properties
- [ ] Test conditional rendering

### Integration Tests
- [ ] Full download workflow (API → Blob → Download)
- [ ] Copy + Download sequence
- [ ] Toggle agent type + Copy
- [ ] Multiple rapid downloads
- [ ] API error response handling

---

## Performance Testing

- [ ] Page loads without lag
- [ ] Copy operation completes instantly
- [ ] Download button shows feedback immediately
- [ ] No memory leaks on repeated copy/download
- [ ] Large ZIP files don't freeze UI
- [ ] Smooth expansion panel animations

---

## Browser DevTools Testing

- [ ] No JavaScript errors in console
- [ ] No network errors
- [ ] No CSS warnings
- [ ] Network tab shows correct API calls
- [ ] Response headers include Content-Disposition: attachment
- [ ] Response type is application/zip
- [ ] Page load performance is acceptable (< 2s)

---

## Regression Testing

- [ ] Other Settings tabs still work
- [ ] Serena section still functional
- [ ] Claude Code Export section still functional
- [ ] Template Manager (Agents tab) still works
- [ ] API Key Manager (API Keys tab) still works
- [ ] Context Priority (Context tab) still works
- [ ] No CSS conflicts with existing styles

---

## Localization Testing (If Applicable)

- [ ] All user-facing text is hardcoded English (not translated)
- [ ] No placeholder text visible
- [ ] No console warnings about missing translations

---

## Security Testing

- [ ] Downloads use HTTPS (not HTTP)
- [ ] Authorization required for download endpoints
- [ ] No API key exposed in frontend code
- [ ] No credentials in downloads
- [ ] Downloaded files are safe (no malicious content)
- [ ] Blob URLs properly revoked after download

---

## Success Criteria

- [ ] All manual testing items checked
- [ ] All automated tests passing
- [ ] No JavaScript errors in console
- [ ] All browsers tested
- [ ] Mobile responsiveness verified
- [ ] Accessibility compliance verified
- [ ] No performance issues
- [ ] No regressions in other features

---

## Known Issues/Limitations

### Browser Compatibility
- Older IE11: Fallback clipboard method may not work perfectly
- Very old Safari: Clipboard API not available, fallback required
- Firefox mobile: Download handling may differ

### Download Behavior
- Some browsers may save to default download folder
- Download names must match Content-Disposition header
- Very large files (>500MB) may timeout

### Clipboard
- iOS has restrictions on clipboard access
- Fallback method requires user interaction (click)
- Some enterprise browsers block clipboard access

---

**Testing Status:** Ready for implementation

**Estimated Testing Time:** 4-6 hours (manual + automated)

**Recommended Order:**
1. Unit tests (1 hour)
2. Component tests (1 hour)
3. Manual browser testing (2 hours)
4. Mobile/Accessibility testing (1-2 hours)
5. Performance/Security testing (30 minutes)
