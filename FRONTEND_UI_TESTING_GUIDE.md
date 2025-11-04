# MCP Configuration UI Testing Guide - Handover 0094

## Overview
This guide documents how to test the updated MCP Configuration UI components with natural language download instructions.

## Test Environment Setup

### Prerequisites
- Running GiljoAI MCP server on localhost:7272
- Authenticated user with valid API key
- Frontend dev server or production build
- Modern browser (Chrome, Firefox, Safari, Edge)

### Starting the Frontend Dev Server
```bash
cd F:\GiljoAI_MCP\frontend
npm run dev
```

Access at: http://localhost:7273

## Test Cases

### Section 1: Slash Commands Download (McpConfigComponent)

#### Test 1.1: Copy Command Button - Token Generation
**Steps**:
1. Navigate to Settings → Manual AI Tool Configuration
2. Click "Copy Command" button in "Slash Commands Quick Setup" section
3. Observe loading spinner
4. Wait for API response (1-2 seconds)

**Expected Results**:
- Loading spinner visible during API call
- Button disabled while loading
- No console errors
- API call to POST /api/download/generate-token with content_type=slash_commands

**Verification**:
```javascript
// Check browser console for:
[McpConfig] Failed to copy slash commands instructions: // should not appear
// Network tab should show successful token generation
```

#### Test 1.2: Copy Command Button - Instruction Generation
**Steps**:
1. Copy Command button click (from Test 1.1)
2. Verify instructions are copied to clipboard

**Expected Results**:
- Instructions copied to clipboard successfully
- Button changes to "Copied!" state
- Button returns to "Copy Command" after 2 seconds
- Instructions format:
  ```
  Download the slash commands from: {downloadUrl}

  Once downloaded:
  1. Extract the ZIP file...
  ```

**Verification**:
- Paste clipboard content to verify format
- Check that download URL is valid and contains token

#### Test 1.3: Copy Command Button - Toast Notification
**Steps**:
1. Complete Test 1.1 and 1.2
2. Observe toast notification

**Expected Results**:
- Success toast appears: "Instructions copied! Paste in your AI coding tool."
- Toast appears in bottom-right corner
- Toast disappears after 3 seconds
- Green success color

#### Test 1.4: Manual Download Button - File Download
**Steps**:
1. Click "Manual Download" button
2. Check browser downloads folder

**Expected Results**:
- File downloads: slash-commands.zip
- Loading spinner visible during download
- Button disabled during download
- Download completes in 1-5 seconds (depends on network)
- ZIP file size: ~5-50 KB

**Verification**:
```bash
# Check file size and contents
unzip -l ~/Downloads/slash-commands.zip
# Should contain:
# - gill_handover.md
# - gill_import_personalagents.md
# - gill_import_productagents.md
# - install.sh
# - install.ps1
```

#### Test 1.5: Manual Download Button - Toast Notification
**Steps**:
1. Complete Test 1.4
2. Observe toast notification

**Expected Results**:
- Success toast appears: "Download started. Extract to ~/.claude/commands/"
- Helpful extraction instructions in toast
- Toast appears in bottom-right corner

#### Test 1.6: Error Handling - Network Failure
**Steps**:
1. Open browser DevTools
2. Go to Network tab
3. Simulate offline: DevTools → Network → Offline
4. Click "Copy Command" or "Manual Download"

**Expected Results**:
- Error toast appears: "Failed to generate download link..."
- Error message in console
- No unhandled exceptions
- Application remains functional after error

### Section 2: Agent Templates Export (TemplateManager)

#### Test 2.1: Personal Agents - Copy Command Button
**Steps**:
1. Navigate to Settings → Agent Template Manager
2. Scroll to "Export Agent Templates" section
3. Click "Personal Agents" button

**Expected Results**:
- Loading spinner visible
- API call to POST /api/download/generate-token with content_type=agent_templates
- Instructions generated with:
  - Download URL included
  - ~/.claude/agents/ path (macOS/Linux)
  - %USERPROFILE%\.claude\agents\ path (Windows)
  - Install script instructions

**Verification**:
- Paste instructions and verify format
- Check that paths are cross-platform
- Verify token is one-time use

#### Test 2.2: Personal Agents - Button State Change
**Steps**:
1. Complete Test 2.1
2. Observe button state

**Expected Results**:
- Button changes to "Copied!" with checkmark icon
- Button returns to "Personal Agents" after 2 seconds
- Icon changes from copy to check to copy again

#### Test 2.3: Product Agents - Copy Command Button
**Steps**:
1. In "Export Agent Templates" section
2. Click "Product Agents" button
3. Paste clipboard content

**Expected Results**:
- Instructions generated with:
  - Download URL included
  - .claude/agents/ path (project-specific, relative)
  - Emphasizes "project root" location
  - Install script instructions
- Different from personal agents instructions

#### Test 2.4: Manual Download Button - Agent Templates ZIP
**Steps**:
1. Click "Manual Download" button in "Export Agent Templates"
2. Check browser downloads folder

**Expected Results**:
- File downloads: agent-templates.zip
- Loading spinner visible
- Download completes
- ZIP file contains active agent templates
- File size: 10-100 KB (depends on number of templates)

**Verification**:
```bash
# List ZIP contents
unzip -l ~/Downloads/agent-templates.zip
# Should contain:
# - {agent-name}.md files (orchestrator.md, implementer.md, etc.)
# - install.sh
# - install.ps1
```

#### Test 2.5: Multiple Exports - State Management
**Steps**:
1. Click "Personal Agents" button
2. Wait for "Copied!" state
3. While "Copied!" is showing, click "Product Agents" button
4. Observe both buttons

**Expected Results**:
- Personal Agents button shows "Copied!"
- Product Agents button shows "Copied!"
- Both have independent 2-second timers
- No conflicts between button states

### Section 3: Cross-Platform Compatibility

#### Test 3.1: Windows Path Handling
**Steps**:
1. On Windows machine (or check instructions text)
2. Copy Command for both slash commands and personal agents
3. Verify paths in instructions

**Expected Results**:
- Windows paths use backslashes: %USERPROFILE%\.claude\agents\
- PowerShell script reference: install.ps1
- No forward slashes in Windows path examples
- Mixed case preservation

#### Test 3.2: macOS/Linux Path Handling
**Steps**:
1. On macOS or Linux machine (or check instructions text)
2. Copy Command for both slash commands and personal agents
3. Verify paths in instructions

**Expected Results**:
- Unix paths use forward slashes: ~/.claude/agents/
- Bash script reference: install.sh
- Tilde expansion: ~/
- Lowercase paths

#### Test 3.3: Instruction Clarity for AI Tools
**Steps**:
1. Copy instructions from "Copy Command" button
2. Paste into ChatGPT or Claude Code conversation
3. Ask AI tool to execute the instructions

**Expected Results**:
- Natural language is clear and unambiguous
- AI tool understands extraction step
- AI tool understands path selection (personal vs product)
- Installation script reference is helpful

### Section 4: Clipboard Handling

#### Test 4.1: Clipboard API (Modern Browsers)
**Steps**:
1. Click "Copy Command" button
2. Open DevTools → Console
3. Paste with Ctrl+V or Cmd+V

**Expected Results**:
- No console errors related to clipboard
- Content pastes successfully
- Format preserved (line breaks intact)

#### Test 4.2: Clipboard Fallback (Older Browsers)
**Steps**:
1. Use IE11 or old Safari (if available)
2. Click "Copy Command" button
3. Paste content

**Expected Results**:
- Content copies successfully via fallback method
- No errors in console
- Format preserved

#### Test 4.3: iOS Clipboard (Safari on iPad/iPhone)
**Steps**:
1. On iPad or iPhone with Safari
2. Navigate to MCP Configuration page
3. Click "Copy Command" button
4. Paste elsewhere (Notes app, etc.)

**Expected Results**:
- Content copies successfully
- Full instructions preserved
- Selection range handled correctly
- Works on iOS 13+

### Section 5: API Integration

#### Test 5.1: Token Generation and Validation
**Steps**:
1. Click "Copy Command" button
2. Check Network tab for API call
3. Verify response structure

**Expected Results**:
- Endpoint: POST /api/download/generate-token
- Query params: content_type=slash_commands or agent_templates
- Response contains:
  ```json
  {
    "download_url": "http://localhost:7272/api/download/temp/{token}/...",
    "expires_at": "2025-11-04T...",
    "content_type": "slash_commands",
    "one_time_use": true
  }
  ```

#### Test 5.2: Direct Download Endpoint
**Steps**:
1. Click "Manual Download" button
2. Check Network tab

**Expected Results**:
- Endpoint: GET /api/download/slash-commands.zip or agent-templates.zip
- Status: 200 OK
- Content-Type: application/zip
- Content-Disposition: attachment; filename=...
- No authentication required (public endpoint)

#### Test 5.3: One-Time Token Usage
**Steps**:
1. Generate token and get download URL
2. Use URL to download file once
3. Try to download again with same URL

**Expected Results**:
- First download: Success (200 OK)
- Second download: Failure (410 Gone - already used)
- Error message: "Download already completed"

### Section 6: UI/UX Validation

#### Test 6.1: Loading States
**Steps**:
1. Click any button (Copy or Download)
2. Observe UI during loading

**Expected Results**:
- Button shows loading spinner (mdi-circle-outline)
- Button text changes to loading state
- Button is disabled while loading
- Cannot click button multiple times
- UI remains responsive

#### Test 6.2: Success Feedback
**Steps**:
1. Complete any successful operation
2. Observe feedback

**Expected Results**:
- Toast notification appears
- Button state changes (for copy buttons)
- Icons update appropriately
- Feedback clears/resets after timeout
- User knows operation succeeded

#### Test 6.3: Info Alert Text
**Steps**:
1. View "How it works" alert in both sections
2. Read instructions

**Expected Results**:
- Alert clearly explains Copy Command approach
- Alert clearly explains Manual Download approach
- Text is actionable and specific
- Icons align with described actions

#### Test 6.4: Button Accessibility
**Steps**:
1. Use keyboard Tab to navigate buttons
2. Press Enter to activate button
3. Check ARIA labels in DevTools

**Expected Results**:
- All buttons are keyboard accessible
- Tab order logical
- Enter key activates buttons
- ARIA labels present and descriptive
- Focus indicators visible

### Section 7: Error Scenarios

#### Test 7.1: No Active Templates (Agent Export)
**Steps**:
1. Deactivate all agent templates
2. Click "Personal Agents" or "Product Agents"
3. Observe response

**Expected Results**:
- Either: Error toast with appropriate message
- Or: Empty templates handled gracefully
- No unhandled exceptions
- User understands what went wrong

#### Test 7.2: Authentication Failure
**Steps**:
1. Clear authentication cookies (log out)
2. Try to copy slash commands or agent templates
3. Observe response

**Expected Results**:
- Error: "Authentication required..."
- User redirected to login
- No sensitive data exposed
- Clear error message

#### Test 7.3: API Timeout
**Steps**:
1. Open Network tab
2. Set network throttle to "Offline"
3. Click button
4. Wait 10+ seconds

**Expected Results**:
- Loading spinner continues briefly
- Eventually shows timeout error
- Button becomes clickable again
- User can retry

## Manual Testing Checklist

### McpConfigComponent
- [ ] Copy Command button generates token
- [ ] Copy Command button copies to clipboard
- [ ] Copy Command shows "Copied!" state
- [ ] Copy Command toast appears
- [ ] Manual Download downloads ZIP file
- [ ] Manual Download toast appears
- [ ] Loading spinners visible during operations
- [ ] Error handling works (offline/network failure)
- [ ] Cross-platform paths in instructions
- [ ] Keyboard navigation works
- [ ] Info alert visible and helpful

### TemplateManager
- [ ] Personal Agents copy button works
- [ ] Product Agents copy button works
- [ ] Manual Download downloads templates ZIP
- [ ] Multiple buttons have independent states
- [ ] Export section visible and accessible
- [ ] Loading states during operations
- [ ] Toast notifications display correctly
- [ ] Error handling for no templates
- [ ] Cross-platform path instructions
- [ ] Button state indicators (icons/text)
- [ ] Info alert explains personal vs product

## Performance Testing

### Test P.1: API Response Time
- Token generation: < 500ms
- Direct download: < 5s
- Expected and acceptable for user experience

### Test P.2: Network Monitor
- Check Network tab in DevTools
- No double requests
- Proper Content-Type headers
- Efficient payload size

### Test P.3: Browser Compatibility
- Chrome 90+: ✓
- Firefox 88+: ✓
- Safari 14+: ✓
- Edge 90+: ✓
- Mobile browsers: ✓

## Edge Cases

### Edge Case 1: Rapid Button Clicks
**Steps**: Click button multiple times quickly

**Expected**:
- Only one request per button
- Loading prevents duplicate clicks
- State doesn't get corrupted

### Edge Case 2: Copy While Downloading
**Steps**:
1. Click download button
2. While loading, click copy button

**Expected**:
- Independent state management
- Both operations work correctly
- No conflicts

### Edge Case 3: Copy Again Immediately
**Steps**:
1. Copy Command → "Copied!" shows
2. Click again immediately (before 2s reset)

**Expected**:
- New copy operation starts
- Previous timer canceled
- Fresh instruction set copied
- New 2s "Copied!" timer starts

## Sign-Off

### Functional Testing
- [ ] All button clicks work as expected
- [ ] All API calls made correctly
- [ ] All responses handled properly
- [ ] Error cases handled gracefully

### UI/UX Testing
- [ ] Loading states visible and clear
- [ ] Success feedback provided
- [ ] Error feedback provided
- [ ] Instructions are clear and actionable

### Cross-Platform Testing
- [ ] Windows paths and scripts correct
- [ ] macOS/Linux paths and scripts correct
- [ ] Mobile responsive (optional)

### Browser Compatibility
- [ ] Chrome/Edge
- [ ] Firefox
- [ ] Safari

### Accessibility
- [ ] Keyboard navigation works
- [ ] ARIA labels present
- [ ] Focus indicators visible

---

## Debugging Tips

### Check API Calls
1. Open DevTools → Network tab
2. Filter for "XHR" requests
3. Look for /api/download/generate-token calls
4. Verify request headers and response

### Check Console for Errors
1. Open DevTools → Console
2. Look for any red error messages
3. Search for "[McpConfig]" or "[TemplateManager]" logs
4. Check for network errors

### Test Clipboard Fallback
1. Temporarily disable Clipboard API in browser
2. DevTools → Settings → Disable JavaScript
3. Reload page with JavaScript enabled selectively
4. Test copy functionality

### Simulate Network Issues
1. DevTools → Network tab
2. Set throttle to "Slow 3G"
3. Click buttons and observe behavior
4. Check error handling

---

**Date**: 2025-11-04
**Version**: 1.0
**Status**: Ready for Testing
