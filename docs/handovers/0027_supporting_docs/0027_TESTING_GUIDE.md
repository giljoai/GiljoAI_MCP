# Testing Guide - Integrations Tab Redesign
## Handover 0027 - Quality Assurance Protocol

**Version**: 1.0
**Date**: 2025-10-20
**Component**: Admin Settings → Integrations Tab
**Test Coverage**: Functional, Visual, Accessibility, Responsive

---

## Test Environment Setup

### Prerequisites
1. GiljoAI MCP Server running (localhost:7272)
2. Frontend dev server running (localhost:7274)
3. Admin user account created
4. Modern browser (Chrome, Firefox, Safari, or Edge)

### Test Data Required
- None (read-only interface, no data input)

### Browser DevTools Setup
1. Open Browser DevTools (F12)
2. Enable Console for logging verification
3. Enable Network tab for asset loading verification
4. Enable Lighthouse for accessibility scanning

---

## Functional Testing

### Test Suite 1: Tab Navigation

#### Test 1.1: Access Integrations Tab
**Steps**:
1. Log in as admin user
2. Navigate to Admin Settings
3. Click "Integrations" tab

**Expected Result**:
- ✓ Tab activates and displays content
- ✓ URL updates to include tab parameter
- ✓ Content loads without errors
- ✓ All logos/assets display correctly

**Status**: _____ (Pass/Fail)

---

### Test Suite 2: Agent Coding Tools Section

#### Test 2.1: Claude Code CLI Display
**Steps**:
1. Navigate to Integrations tab
2. Scroll to "Agent Coding Tools" section
3. Locate Claude Code CLI card

**Expected Result**:
- ✓ Claude logo displays (Claude_AI_symbol.svg)
- ✓ Heading reads "Claude Code CLI"
- ✓ Subtitle reads "AI-powered development with MCP integration"
- ✓ Yellow alert box displays with alpha testing message
- ✓ Description text is readable and accurate
- ✓ "How to Configure Claude Code" button is visible and enabled

**Status**: _____ (Pass/Fail)

#### Test 2.2: Claude Configuration Modal - Marketplace Tab
**Steps**:
1. Click "How to Configure Claude Code" button
2. Verify modal opens
3. Ensure "Marketplace Configuration" tab is active by default
4. Read through instructions

**Expected Result**:
- ✓ Modal opens with animation
- ✓ Modal title displays with robot icon
- ✓ Info alert shows at top with API key generation reminder
- ✓ Marketplace Configuration tab is active
- ✓ Step-by-step instructions are clear and numbered
- ✓ Instructions reference correct server IP and port
- ✓ Instructions are professionally written

**Status**: _____ (Pass/Fail)

#### Test 2.3: Claude Configuration Modal - Manual Tab
**Steps**:
1. In Claude modal, click "Manual Configuration" tab
2. Review configuration snippet
3. Click "Copy Configuration" button
4. Verify clipboard contents

**Expected Result**:
- ✓ Tab switches successfully
- ✓ Configuration file location guidance displays (OS-specific)
- ✓ Documentation link is present and clickable
- ✓ Configuration code block displays properly formatted JSON
- ✓ Code uses proper syntax highlighting (if available)
- ✓ Placeholder format is `{your-api-key-here}`
- ✓ Copy button copies exact configuration to clipboard
- ✓ Console logs copy action

**Configuration to Verify**:
```json
{
  "servers": {
    "giljo-mcp": {
      "command": "mcp-client",
      "args": [
        "--server-url", "http://your-server-ip:7272",
        "--api-key", "{your-api-key-here}"
      ],
      "description": "GiljoAI Agent Orchestration MCP Server"
    }
  }
}
```

**Status**: _____ (Pass/Fail)

#### Test 2.4: Claude Configuration Modal - Download Tab
**Steps**:
1. In Claude modal, click "Download Instructions" tab
2. Click "Download Claude Code Setup Guide" button
3. Open downloaded file

**Expected Result**:
- ✓ Tab switches successfully
- ✓ Description explains what will be downloaded
- ✓ Download button is properly styled
- ✓ File downloads as `claude-code-giljo-mcp-setup.txt`
- ✓ File contains comprehensive setup instructions
- ✓ File includes both marketplace and manual methods
- ✓ File has verification steps
- ✓ File formatting is clean and readable

**Status**: _____ (Pass/Fail)

#### Test 2.5: Claude Modal - Close Functionality
**Steps**:
1. Open Claude configuration modal
2. Test closing methods:
   - a) Click "Close" button
   - b) Press Escape key
   - c) Click outside modal (backdrop)

**Expected Result**:
- ✓ All three methods close the modal
- ✓ Modal closes with animation
- ✓ Focus returns to "How to Configure Claude Code" button
- ✓ Page remains stable (no scrolling issues)

**Status**: _____ (Pass/Fail)

---

#### Test 2.6: Codex CLI Display
**Steps**:
1. Navigate to Integrations tab
2. Scroll to Codex CLI card

**Expected Result**:
- ✓ Codex logo displays (codex_logo.svg)
- ✓ Heading reads "Codex CLI"
- ✓ Subtitle reads "Advanced code generation and analysis"
- ✓ Description text mentions sub-agent architecture
- ✓ "How to Configure Codex" button is visible and enabled
- ✓ No yellow alert (only Claude has this)

**Status**: _____ (Pass/Fail)

#### Test 2.7: Codex Configuration Modal - Manual Tab
**Steps**:
1. Click "How to Configure Codex" button
2. Verify modal opens on Manual Configuration tab
3. Review configuration snippet
4. Click "Copy Configuration" button

**Expected Result**:
- ✓ Modal opens successfully
- ✓ Manual Configuration tab is active (no Marketplace tab for Codex)
- ✓ Configuration file location guidance displays
- ✓ Documentation links are present (MCP and CLI docs)
- ✓ Configuration code block displays TOML format
- ✓ Agent coordination settings are included
- ✓ Copy button works correctly
- ✓ Placeholder format is `{your-api-key-here}`

**Configuration to Verify**:
```toml
[giljo-mcp]
endpoint = "http://your-server-ip:7272"
api_key = "{your-api-key-here}"
description = "GiljoAI Agent Orchestration MCP Server"

[agents]
orchestrator_enabled = true
subagent_coordination = true
context_sharing = true
```

**Status**: _____ (Pass/Fail)

#### Test 2.8: Codex Configuration Modal - Download Tab
**Steps**:
1. In Codex modal, click "Download Instructions" tab
2. Click download button
3. Open downloaded file

**Expected Result**:
- ✓ Tab switches successfully
- ✓ File downloads as `codex-cli-giljo-mcp-setup.txt`
- ✓ File contains complete setup instructions
- ✓ File includes sub-agent workflow explanation
- ✓ File has verification steps
- ✓ File references both documentation links

**Status**: _____ (Pass/Fail)

---

#### Test 2.9: Gemini CLI Display
**Steps**:
1. Navigate to Integrations tab
2. Scroll to Gemini CLI card

**Expected Result**:
- ✓ Gemini logo displays (gemini-icon.svg)
- ✓ Heading reads "Gemini CLI"
- ✓ Subtitle reads "Google's advanced AI development platform"
- ✓ Description mentions multi-modal capabilities
- ✓ "How to Configure Gemini CLI" button is visible and enabled

**Status**: _____ (Pass/Fail)

#### Test 2.10: Gemini Configuration Modal - Manual Tab
**Steps**:
1. Click "How to Configure Gemini CLI" button
2. Verify modal opens
3. Review configuration snippet
4. Click "Copy Configuration" button

**Expected Result**:
- ✓ Modal opens successfully
- ✓ Manual Configuration tab is active
- ✓ Settings.json file location displays
- ✓ GitHub repository link is present
- ✓ Configuration code block displays JSON format
- ✓ Capabilities array is included
- ✓ Copy button works correctly

**Configuration to Verify**:
```json
{
  "mcpServers": {
    "giljo-mcp": {
      "url": "http://your-server-ip:7272",
      "apiKey": "{your-api-key-here}",
      "description": "GiljoAI Agent Orchestration MCP Server",
      "capabilities": [
        "agent_coordination",
        "context_sharing",
        "memory_persistence"
      ]
    }
  }
}
```

**Status**: _____ (Pass/Fail)

#### Test 2.11: Gemini Configuration Modal - Download Tab
**Steps**:
1. In Gemini modal, click "Download Instructions" tab
2. Click download button
3. Open downloaded file

**Expected Result**:
- ✓ Tab switches successfully
- ✓ File downloads as `gemini-cli-giljo-mcp-setup.txt`
- ✓ File contains installation instructions (npm, homebrew)
- ✓ File includes multi-modal features explanation
- ✓ File has verification steps

**Status**: _____ (Pass/Fail)

---

### Test Suite 3: Native Integrations Section

#### Test 3.1: Serena Integration Display
**Steps**:
1. Navigate to Integrations tab
2. Scroll to "Native Integrations" section
3. Locate Serena MCP card

**Expected Result**:
- ✓ Section heading "Native Integrations" displays
- ✓ Serena logo displays (Serena.png)
- ✓ Heading reads "Serena MCP"
- ✓ Subtitle reads "Intelligent codebase understanding and navigation"
- ✓ Description paragraph is clear and accurate
- ✓ GitHub button displays with icon
- ✓ Credit text shows "Credit: Oraios"
- ✓ Info alert displays with user configuration note

**Status**: _____ (Pass/Fail)

#### Test 3.2: Serena GitHub Link
**Steps**:
1. Click "GitHub Repository" button
2. Verify link behavior

**Expected Result**:
- ✓ Link opens in new tab/window (target="_blank")
- ✓ Link navigates to https://github.com/oraios/serena
- ✓ Original page remains open

**Status**: _____ (Pass/Fail)

#### Test 3.3: More Coming Soon Card
**Steps**:
1. Scroll to bottom of Native Integrations section
2. Locate "More Coming Soon" card

**Expected Result**:
- ✓ Card displays with surface-variant styling
- ✓ Plus circle icon displays (size 48)
- ✓ Heading "More Integrations Coming Soon"
- ✓ Description text is centered
- ✓ Card has appropriate padding

**Status**: _____ (Pass/Fail)

---

## Visual Testing

### Test Suite 4: Layout and Styling

#### Test 4.1: Overall Layout
**Steps**:
1. View entire Integrations tab at desktop resolution (1920x1080)

**Expected Result**:
- ✓ Consistent spacing between sections
- ✓ Cards have proper elevation/shadow
- ✓ All text is readable with good contrast
- ✓ Section divider is visible between Agent Tools and Native Integrations
- ✓ No overlapping elements
- ✓ Professional, clean appearance

**Status**: _____ (Pass/Fail)

#### Test 4.2: Logo Quality
**Steps**:
1. Inspect all four logos (Claude, Codex, Gemini, Serena)

**Expected Result**:
- ✓ All logos display at 48px size
- ✓ Logos are crisp and clear (no pixelation)
- ✓ Logo colors match brand guidelines
- ✓ Proper spacing around logos (mr-4)

**Status**: _____ (Pass/Fail)

#### Test 4.3: Typography
**Steps**:
1. Review all text elements on the page

**Expected Result**:
- ✓ Headings use proper hierarchy (h1 → h2 → h3)
- ✓ Body text is readable (text-body-2)
- ✓ Consistent font family throughout
- ✓ Proper line height for readability
- ✓ No text overflow or truncation

**Status**: _____ (Pass/Fail)

#### Test 4.4: Color Scheme
**Steps**:
1. Review color usage across the tab

**Expected Result**:
- ✓ Yellow alert uses warning color consistently
- ✓ Info alerts use info color consistently
- ✓ Buttons use primary/secondary colors appropriately
- ✓ Text colors have sufficient contrast
- ✓ Hover states are visually distinct

**Status**: _____ (Pass/Fail)

---

## Responsive Testing

### Test Suite 5: Mobile Layout (320px - 599px)

#### Test 5.1: Mobile - Overall Layout
**Steps**:
1. Open DevTools and set viewport to 375x667 (iPhone SE)
2. Navigate to Integrations tab
3. Scroll through entire page

**Expected Result**:
- ✓ No horizontal scrolling required
- ✓ Cards stack vertically
- ✓ All content visible and readable
- ✓ Touch targets ≥ 44x44px
- ✓ Buttons remain accessible
- ✓ Images/logos scale appropriately

**Status**: _____ (Pass/Fail)

#### Test 5.2: Mobile - Modal Behavior
**Steps**:
1. Open Claude configuration modal on mobile
2. Test modal interaction

**Expected Result**:
- ✓ Modal occupies most of viewport
- ✓ Modal content scrolls within dialog
- ✓ Tabs are accessible (may scroll horizontally)
- ✓ Code blocks scroll horizontally when needed
- ✓ Copy/download buttons remain accessible
- ✓ Close button easily tappable

**Status**: _____ (Pass/Fail)

---

### Test Suite 6: Tablet Layout (600px - 959px)

#### Test 6.1: Tablet - Portrait Orientation
**Steps**:
1. Set viewport to 768x1024 (iPad portrait)
2. Navigate through Integrations tab

**Expected Result**:
- ✓ Layout adapts smoothly
- ✓ Cards have appropriate width
- ✓ Spacing is balanced
- ✓ No wasted space
- ✓ Touch-friendly interface

**Status**: _____ (Pass/Fail)

#### Test 6.2: Tablet - Landscape Orientation
**Steps**:
1. Set viewport to 1024x768 (iPad landscape)
2. Navigate through Integrations tab

**Expected Result**:
- ✓ Layout utilizes horizontal space well
- ✓ Cards remain readable
- ✓ No excessive whitespace
- ✓ Modal dialogs sized appropriately

**Status**: _____ (Pass/Fail)

---

### Test Suite 7: Desktop Layout (960px+)

#### Test 7.1: Desktop - Standard Resolution
**Steps**:
1. Set viewport to 1920x1080
2. Review entire tab layout

**Expected Result**:
- ✓ Optimal use of screen real estate
- ✓ Cards have max-width constraints (readable)
- ✓ Proper padding and margins
- ✓ Hover effects on buttons/links
- ✓ Modal dialogs centered and sized well

**Status**: _____ (Pass/Fail)

#### Test 7.2: Desktop - Ultrawide (2560px+)
**Steps**:
1. Set viewport to 2560x1440
2. Review layout at ultrawide resolution

**Expected Result**:
- ✓ Content doesn't stretch uncomfortably wide
- ✓ Cards maintain readable width
- ✓ Spacing remains professional
- ✓ No layout breaking

**Status**: _____ (Pass/Fail)

---

## Accessibility Testing

### Test Suite 8: Keyboard Navigation

#### Test 8.1: Tab Navigation
**Steps**:
1. Click in address bar to reset focus
2. Press Tab repeatedly to navigate through page
3. Navigate to each configuration button
4. Press Enter to open modal

**Expected Result**:
- ✓ Focus indicator clearly visible on all elements
- ✓ Tab order is logical (top to bottom)
- ✓ All interactive elements reachable
- ✓ No keyboard traps
- ✓ Enter key activates buttons
- ✓ Modals open on Enter/Space

**Status**: _____ (Pass/Fail)

#### Test 8.2: Modal Keyboard Navigation
**Steps**:
1. Open any configuration modal with keyboard (Enter)
2. Press Tab to navigate within modal
3. Use arrow keys on tabs (if applicable)
4. Press Escape to close

**Expected Result**:
- ✓ Focus trapped within modal
- ✓ Tab cycles through modal controls
- ✓ Arrow keys switch tabs (if implemented)
- ✓ Escape key closes modal
- ✓ Focus returns to trigger button on close
- ✓ Close button reachable via Tab

**Status**: _____ (Pass/Fail)

#### Test 8.3: Skip Navigation
**Steps**:
1. Navigate to Integrations tab
2. Use Tab to move through sections

**Expected Result**:
- ✓ Can skip to main content areas
- ✓ Tab structure allows bypassing repetitive elements
- ✓ Navigation is efficient

**Status**: _____ (Pass/Fail)

---

### Test Suite 9: Screen Reader Compatibility

#### Test 9.1: Heading Structure
**Steps**:
1. Enable screen reader heading navigation (H key in NVDA/JAWS)
2. Navigate through headings

**Expected Result**:
- ✓ "Admin Settings" announced as h1
- ✓ "Agent Coding Tools" announced as h2
- ✓ "Native Integrations" announced as h2
- ✓ Tool names announced as h3
- ✓ No skipped heading levels
- ✓ Logical hierarchy

**Status**: _____ (Pass/Fail)

#### Test 9.2: Button and Link Announcements
**Steps**:
1. Navigate to configuration buttons with screen reader
2. Listen to announcements

**Expected Result**:
- ✓ Button role announced
- ✓ Button text read clearly
- ✓ Interactive state announced
- ✓ GitHub link announced as link with "opens in new window"

**Status**: _____ (Pass/Fail)

#### Test 9.3: Alert Announcements
**Steps**:
1. Navigate to yellow alert in Claude section
2. Navigate to info alerts

**Expected Result**:
- ✓ Alert role announced
- ✓ Alert type announced (warning, info)
- ✓ Alert content read fully
- ✓ Icon meaning conveyed

**Status**: _____ (Pass/Fail)

---

### Test Suite 10: Color Contrast

#### Test 10.1: Automated Contrast Check
**Steps**:
1. Open Chrome DevTools
2. Run Lighthouse accessibility audit
3. Review contrast issues

**Expected Result**:
- ✓ No contrast issues reported
- ✓ All text passes AA standards (4.5:1 minimum)
- ✓ Large text passes AA standards (3:1 minimum)
- ✓ Interactive elements have sufficient contrast

**Status**: _____ (Pass/Fail)

#### Test 10.2: Manual Contrast Verification
**Steps**:
1. Use browser extension or online tool to check specific elements
2. Test: Body text, headings, button text, alert text

**Expected Result**:
- ✓ Body text: ≥ 4.5:1 contrast ratio
- ✓ Headings: ≥ 4.5:1 contrast ratio
- ✓ Button text: ≥ 4.5:1 contrast ratio
- ✓ Alert text: ≥ 4.5:1 contrast ratio
- ✓ Link text: ≥ 4.5:1 contrast ratio

**Status**: _____ (Pass/Fail)

---

## Performance Testing

### Test Suite 11: Load Performance

#### Test 11.1: Asset Loading
**Steps**:
1. Open Network tab in DevTools
2. Refresh page
3. Navigate to Integrations tab
4. Review asset loading

**Expected Result**:
- ✓ All logos load successfully (4 images)
- ✓ No 404 errors
- ✓ Assets load in < 500ms (local)
- ✓ No unnecessary requests

**Assets to Verify**:
- Claude_AI_symbol.svg
- codex_logo.svg
- gemini-icon.svg
- Serena.png

**Status**: _____ (Pass/Fail)

#### Test 11.2: Modal Performance
**Steps**:
1. Open each configuration modal
2. Monitor performance in DevTools

**Expected Result**:
- ✓ Modals open smoothly (< 100ms)
- ✓ No jank or stuttering
- ✓ Animations run at 60fps
- ✓ Tab switching is instant

**Status**: _____ (Pass/Fail)

---

## Browser Compatibility Testing

### Test Suite 12: Cross-Browser

#### Test 12.1: Chrome
**Version**: _____ (current stable)

**Test Results**:
- Layout: _____ (Pass/Fail)
- Functionality: _____ (Pass/Fail)
- Modals: _____ (Pass/Fail)
- Copy/Download: _____ (Pass/Fail)

#### Test 12.2: Firefox
**Version**: _____ (current stable)

**Test Results**:
- Layout: _____ (Pass/Fail)
- Functionality: _____ (Pass/Fail)
- Modals: _____ (Pass/Fail)
- Copy/Download: _____ (Pass/Fail)

#### Test 12.3: Safari
**Version**: _____ (current stable)

**Test Results**:
- Layout: _____ (Pass/Fail)
- Functionality: _____ (Pass/Fail)
- Modals: _____ (Pass/Fail)
- Copy/Download: _____ (Pass/Fail)

#### Test 12.4: Edge
**Version**: _____ (current stable)

**Test Results**:
- Layout: _____ (Pass/Fail)
- Functionality: _____ (Pass/Fail)
- Modals: _____ (Pass/Fail)
- Copy/Download: _____ (Pass/Fail)

---

## Regression Testing

### Test Suite 13: Other Tabs Not Affected

#### Test 13.1: Network Tab
**Steps**:
1. Navigate to Network tab
2. Verify all functionality works

**Expected Result**:
- ✓ Network settings display correctly
- ✓ No visual regressions
- ✓ Functionality intact

**Status**: _____ (Pass/Fail)

#### Test 13.2: Database Tab
**Steps**:
1. Navigate to Database tab
2. Test database connection

**Expected Result**:
- ✓ Database settings display
- ✓ Test connection works
- ✓ No regressions

**Status**: _____ (Pass/Fail)

#### Test 13.3: Users Tab
**Steps**:
1. Navigate to Users tab
2. Verify user management works

**Expected Result**:
- ✓ User list displays
- ✓ All user actions work
- ✓ No regressions

**Status**: _____ (Pass/Fail)

#### Test 13.4: Security Tab
**Steps**:
1. Navigate to Security tab
2. Verify cookie domain management works

**Expected Result**:
- ✓ Cookie domains display
- ✓ Add/remove functionality works
- ✓ No regressions

**Status**: _____ (Pass/Fail)

---

## Edge Case Testing

### Test Suite 14: Edge Cases

#### Test 14.1: Rapid Modal Opening/Closing
**Steps**:
1. Rapidly click configuration buttons
2. Open and close modals quickly
3. Switch tabs rapidly

**Expected Result**:
- ✓ No crashes or errors
- ✓ Modals handle rapid interaction
- ✓ State remains consistent
- ✓ No memory leaks

**Status**: _____ (Pass/Fail)

#### Test 14.2: Multiple Modals (Verify Mutual Exclusivity)
**Steps**:
1. Open Claude modal
2. Attempt to open Codex modal

**Expected Result**:
- ✓ Only one modal open at a time
- ✓ Previous modal closes when new one opens (if applicable)
- ✓ No overlay stacking issues

**Status**: _____ (Pass/Fail)

#### Test 14.3: Slow Network Simulation
**Steps**:
1. Enable network throttling (Slow 3G)
2. Navigate to Integrations tab
3. Test logo loading

**Expected Result**:
- ✓ Page remains usable during loading
- ✓ Loading states visible (if applicable)
- ✓ No broken images
- ✓ Graceful degradation

**Status**: _____ (Pass/Fail)

---

## Security Testing

### Test Suite 15: Security Verification

#### Test 15.1: External Links
**Steps**:
1. Inspect GitHub link
2. Verify security attributes

**Expected Result**:
- ✓ Link has target="_blank"
- ✓ Opens in new tab safely
- ✓ No security warnings in console

**Status**: _____ (Pass/Fail)

#### Test 15.2: Configuration Placeholders
**Steps**:
1. Verify all configuration snippets
2. Check for actual API keys or secrets

**Expected Result**:
- ✓ All placeholders use dummy values
- ✓ No real API keys exposed
- ✓ Server IP shown as "your-server-ip"
- ✓ Clear instructions for replacement

**Status**: _____ (Pass/Fail)

---

## Test Summary Report

### Overall Statistics
- Total Test Suites: 15
- Total Test Cases: 70+
- Tests Passed: _____ / _____
- Tests Failed: _____ / _____
- Pass Rate: _____%

### Critical Issues Found
1. ___________________
2. ___________________

### Major Issues Found
1. ___________________
2. ___________________

### Minor Issues Found
1. ___________________
2. ___________________

### Recommendations
1. ___________________
2. ___________________

---

## Sign-Off

**Tester Name**: _________________
**Date**: _________________
**Overall Assessment**: _____ (Approved/Needs Work/Rejected)

**Comments**:
________________________________________________________________
________________________________________________________________
________________________________________________________________

**Production Readiness**: _____ (Yes/No)

---

## Appendix: Quick Smoke Test (5 Minutes)

For rapid verification, perform these essential tests:

1. ✓ Open Integrations tab - loads correctly
2. ✓ All 4 logos display (Claude, Codex, Gemini, Serena)
3. ✓ Click "How to Configure Claude Code" - modal opens
4. ✓ Switch to Manual tab - configuration displays
5. ✓ Click Copy button - clipboard receives data
6. ✓ Click Download button - file downloads
7. ✓ Press Escape - modal closes
8. ✓ Click GitHub link - opens in new tab
9. ✓ Resize to mobile (375px) - responsive layout works
10. ✓ Tab through page with keyboard - navigation works

**Quick Test Result**: _____ (Pass/Fail)

---

**Document Version**: 1.0
**Last Updated**: 2025-10-20
**Next Review**: After any component changes
