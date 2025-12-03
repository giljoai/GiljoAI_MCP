# Manual Testing Guide: Button Relocation

## Overview
This guide validates the relocation of Stage Project and Launch Jobs buttons from LaunchTab to ProjectTabs header.

## Test Environment Setup

```bash
cd frontend
npm run dev
```

Navigate to a project's detail view.

## Visual Verification Checklist

### 1. Layout Structure
- [ ] Tab headers ("Launch" and "Implement") are visible at the top
- [ ] Action buttons (Stage Project, Waiting:, Launch Jobs) appear on the same horizontal line as tab headers
- [ ] Action buttons are aligned to the right side of the container
- [ ] No action buttons appear within the Launch tab content area
- [ ] Main container starts immediately below the tab header (no extra space)

### 2. Button Positioning
- [ ] Stage Project button is on the far left of the action button group
- [ ] "Waiting:" status text is centered between the buttons
- [ ] Launch Jobs button is on the far right of the action button group
- [ ] Buttons maintain consistent vertical alignment with tab labels

### 3. Button Styling

#### Stage Project Button
- [ ] Has yellow outline (yellow-darken-2 color)
- [ ] Has transparent background (outlined variant)
- [ ] Has rounded corners
- [ ] Text displays "Stage project" (no caps)
- [ ] Shows loading spinner when clicked

#### Waiting Status Text
- [ ] Displays "Waiting:" in yellow/gold color (#ffd700)
- [ ] Text is italic
- [ ] Font size is readable (16px)

#### Launch Jobs Button
- [ ] Has grey color when disabled (no mission/agents)
- [ ] Has yellow color (yellow-darken-2) when enabled
- [ ] Has rounded corners
- [ ] Text displays "Launch jobs" (no caps)
- [ ] Is disabled when not ready to launch

### 4. Functional Testing

#### Stage Project Button
1. **Click Stage Project**
   - [ ] Button shows loading state
   - [ ] Orchestrator prompt is copied to clipboard
   - [ ] Console shows "[ProjectTabs] Orchestrator prompt copied to clipboard"
   - [ ] No errors in console

2. **After Staging (simulate orchestrator running)**
   - [ ] Mission appears in Orchestrator Mission panel (within Launch tab content)
   - [ ] Agent cards appear in Default Agent panel (within Launch tab content)
   - [ ] Launch Jobs button becomes enabled (changes from grey to yellow)

#### Launch Jobs Button
1. **When Disabled (no mission/agents)**
   - [ ] Button appears grey
   - [ ] Button has disabled attribute
   - [ ] Clicking does nothing

2. **When Enabled (mission + agents exist)**
   - [ ] Button appears yellow
   - [ ] Button is clickable

3. **Click Launch Jobs**
   - [ ] Jobs are launched successfully
   - [ ] Tab automatically switches to "Implement" tab
   - [ ] Agent status board appears in Implement tab
   - [ ] No errors in console

### 5. Responsive Design

#### Desktop (> 1024px)
- [ ] All buttons visible on one line
- [ ] Proper spacing between elements
- [ ] No wrapping or overlap

#### Tablet (768px - 1024px)
- [ ] Buttons remain visible
- [ ] Layout adapts gracefully
- [ ] Text remains readable

#### Mobile (< 768px)
- [ ] Action buttons wrap to second line if needed
- [ ] Buttons remain accessible
- [ ] Touch targets are adequate (minimum 44x44px)

### 6. Accessibility

#### Keyboard Navigation
- [ ] Tab key focuses Stage Project button
- [ ] Tab key focuses Launch Jobs button
- [ ] Enter key activates focused button
- [ ] Focus indicators are visible

#### Screen Reader
- [ ] Stage Project button has proper role
- [ ] Launch Jobs button indicates disabled state (aria-disabled="true")
- [ ] Status text is announced properly

### 7. Launch Tab Content Area

#### Panel Layout
- [ ] Three panels are visible: Project Description, Orchestrator Mission, Default Agent
- [ ] Panels are equal width (1fr 1fr 1fr grid)
- [ ] No extra spacing at top (where buttons used to be)
- [ ] Main container border and padding are correct

#### Functionality Preserved
- [ ] Edit description icon works in Project Description panel
- [ ] Orchestrator info icon works in Default Agent panel
- [ ] Agent info icons work in Agent Team section
- [ ] WebSocket updates still populate mission and agent data

### 8. Error Handling

#### Stage Project Fails
- [ ] Error snackbar appears at top of screen
- [ ] Error message is descriptive
- [ ] Loading state clears
- [ ] Button returns to clickable state

#### Launch Jobs Fails
- [ ] Error snackbar appears at top of screen
- [ ] Error message is descriptive
- [ ] Tab does not switch
- [ ] Button returns to clickable state

### 9. State Persistence

#### Page Reload
- [ ] If mission exists, Launch button remains enabled after reload
- [ ] If agents exist, they appear in Agent Team section after reload
- [ ] Tab selection persists in URL (?tab=launch or ?tab=jobs)

#### Navigation
- [ ] Switching between projects maintains correct state
- [ ] Buttons reflect project-specific state

## Console Checks

### Expected Logs (Success Path)
```
[ProjectTabs] Orchestrator prompt copied to clipboard
[LaunchTab] Received project:mission_updated event
[LaunchTab] Mission panel updated successfully
[LaunchTab] Received agent:created event
[LaunchTab] Agent card added to UI. Total agents: X
```

### No Errors Should Appear
- [ ] No "Cannot read properties of undefined" errors
- [ ] No "Failed to stage project" errors (unless API actually fails)
- [ ] No "Failed to launch jobs" errors (unless API actually fails)

## Browser Compatibility

Test in:
- [ ] Chrome/Edge (Chromium)
- [ ] Firefox
- [ ] Safari (if available)

## Test Results

**Date:** _______________
**Tester:** _______________
**Browser:** _______________
**Result:** Pass / Fail

**Notes:**
_______________________________________________________________________________
_______________________________________________________________________________
_______________________________________________________________________________

## Regression Checks

Verify these existing features still work:
- [ ] Tab switching between Launch and Implement
- [ ] Unread message badge on Implement tab
- [ ] Agent status updates in Implement tab
- [ ] Edit description modal
- [ ] Agent details modal
- [ ] WebSocket real-time updates
- [ ] Message center
- [ ] Agent action buttons (in Implement tab)
