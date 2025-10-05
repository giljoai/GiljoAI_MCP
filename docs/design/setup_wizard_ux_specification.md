# GiljoAI MCP Setup Wizard - UX Specification

**Version**: 1.0
**Date**: 2025-10-05
**Designer**: UX Designer Agent
**Status**: Draft for Review

---

## 1. Overview

### 1.1 Purpose
The Setup Wizard guides users through post-installation configuration of GiljoAI MCP, ensuring proper database connectivity, deployment mode selection, and AI tool integration.

### 1.2 Design Goals
- **Simplicity**: Clear, linear flow with minimal cognitive load
- **Guidance**: Contextual help and validation at every step
- **Flexibility**: Conditional steps based on deployment mode
- **Confidence**: Clear success indicators and error recovery paths
- **Accessibility**: WCAG 2.1 AA compliance throughout

### 1.3 User Journey
```
Entry Point: http://localhost:7274/setup
Exit Point: http://localhost:7274/ (dashboard)
Duration: 5-10 minutes (typical)
```

---

## 2. Wizard Flow Architecture

### 2.1 Step Sequence

**Linear Steps (all users):**
1. Welcome
2. Database Connection
3. Deployment Mode Selection
5. AI Tool Integration
7. Complete

**Conditional Steps:**
- Step 4: Admin Account (only if LAN mode selected)
- Step 6: LAN Configuration (only if LAN mode selected)

### 2.2 Progress Indicator Design

**Vuetify Stepper Component:**
- Display step numbers and titles
- Show completed steps with checkmarks
- Highlight current step
- Dim future steps
- Hide conditional steps until triggered

**Visual States:**
```
○ Not Started (gray, dimmed)
◉ Current Step (yellow primary, bold)
✓ Completed (green, checkmark)
⊗ Error (red, error icon)
```

### 2.3 Navigation Rules

**Forward Navigation:**
- Enabled only when current step is valid
- Continue button at bottom-right
- Keyboard shortcut: Enter (when form valid)

**Backward Navigation:**
- Always available (except on Welcome screen)
- Back button at bottom-left
- Keyboard shortcut: Escape
- Warning if unsaved changes exist

**Skip Navigation:**
- Not permitted (ensures complete setup)
- Exception: AI Tool Integration can be skipped with warning

---

## 3. Step-by-Step Specifications

### Step 1: Welcome

#### 3.1.1 Layout
```
┌─────────────────────────────────────────────────────────┐
│  [GiljoAI Logo - Yellow/White]                          │
│                                                         │
│  Welcome to GiljoAI MCP                                 │
│  Multi-Agent Coding Orchestrator                        │
│                                                         │
│  ┌───────────────────────────────────────────────┐    │
│  │  This wizard will help you:                    │    │
│  │                                                │    │
│  │  ✓ Verify database connection                 │    │
│  │  ✓ Choose deployment mode                     │    │
│  │  ✓ Configure AI tool integration              │    │
│  │  ✓ Complete initial setup                     │    │
│  │                                                │    │
│  │  Estimated time: 5-10 minutes                 │    │
│  └───────────────────────────────────────────────┘    │
│                                                         │
│  ┌─────────────────────────────────────────────┐      │
│  │ Progress: Step 1 of 7                        │      │
│  │ ▓▓▓░░░░░░░░░░░ 14%                           │      │
│  └─────────────────────────────────────────────┘      │
│                                                         │
│                                   [Get Started →]      │
└─────────────────────────────────────────────────────────┘
```

#### 3.1.2 Content
- **Title**: "Welcome to GiljoAI MCP"
- **Subtitle**: "Multi-Agent Coding Orchestrator"
- **Checklist**:
  - Verify database connection
  - Choose deployment mode
  - Configure AI tool integration
  - Complete initial setup
- **Time estimate**: "5-10 minutes"

#### 3.1.3 Actions
- Primary: "Get Started" (navigates to Step 2)
- Secondary: None (first step)

#### 3.1.4 Accessibility
- Focus on "Get Started" button on load
- Keyboard navigation: Tab, Enter
- Screen reader: Announce step count and progress

---

### Step 2: Database Connection

#### 3.2.1 Layout
```
┌─────────────────────────────────────────────────────────┐
│  Database Connection                                     │
│  ──────────────────────────────────────────────────────  │
│                                                          │
│  ┌─────────────────────────────────────────────────┐   │
│  │ ℹ Database settings are configured during       │   │
│  │   installation. This step verifies connectivity.│   │
│  └─────────────────────────────────────────────────┘   │
│                                                          │
│  Connection Details (read-only)                         │
│  ┌──────────────┬──────────────┐                       │
│  │ Host         │ Port         │                       │
│  │ localhost 🔒 │ 5432     🔒 │                       │
│  └──────────────┴──────────────┘                       │
│  ┌──────────────┬──────────────┐                       │
│  │ Database     │ Username     │                       │
│  │ giljo_mcp 🔒│ postgres 🔒 │                       │
│  └──────────────┴──────────────┘                       │
│                                                          │
│  [Test Connection]                                      │
│                                                          │
│  ┌─────────────────────────────────────────────────┐   │
│  │ ✓ Connected to PostgreSQL database 'giljo_mcp' │   │
│  │   on localhost:5432                             │   │
│  └─────────────────────────────────────────────────┘   │
│                                                          │
│  Need help? See troubleshooting guide                   │
│                                                          │
│  [← Back]                             [Continue →]     │
└─────────────────────────────────────────────────────────┘
```

#### 3.2.2 Component Reuse
- Extracts DatabaseConnection.vue from SettingsView.vue
- Props:
  - `readonly: true` (settings are locked)
  - `showTestButton: true`
  - `autoTest: true` (test on mount)

#### 3.2.3 States
1. **Loading**: "Testing connection..." (spinner)
2. **Success**: Green alert with connection details
3. **Error**: Red alert with error message + troubleshooting link

#### 3.2.4 Error Handling
- Connection timeout: "Could not connect to database. Check if PostgreSQL is running."
- Authentication failure: "Database authentication failed. Verify credentials."
- Network error: "Network error. Ensure PostgreSQL is accessible on localhost:5432."
- Link to troubleshooting guide (to be created)

#### 3.2.5 Actions
- Primary: "Continue" (enabled only when connection successful)
- Secondary: "Back" (returns to Welcome)
- Tertiary: "Test Connection" (re-runs test)

#### 3.2.6 Accessibility
- Focus on "Test Connection" button on load
- Screen reader announces test result
- Error messages have role="alert"
- Keyboard shortcuts: Enter (continue), Escape (back)

---

### Step 3: Deployment Mode Selection

#### 3.3.1 Layout
```
┌─────────────────────────────────────────────────────────┐
│  Choose Deployment Mode                                  │
│  ──────────────────────────────────────────────────────  │
│                                                          │
│  How will you use GiljoAI MCP?                          │
│                                                          │
│  ○  Localhost                                           │
│     Single user on this computer only                   │
│     • No network access required                        │
│     • No authentication needed                          │
│     • Fastest performance                               │
│     • Recommended for personal use                      │
│                                                          │
│  ○  LAN (Local Area Network)                            │
│     Team access on your local network                   │
│     • Multiple users can connect                        │
│     • Requires admin account setup                      │
│     • Firewall configuration needed                     │
│     • Recommended for teams (2-10 users)                │
│                                                          │
│  ⊘  WAN (Wide Area Network)                             │
│     Internet access for remote teams                    │
│     • Coming in Phase 1                                 │
│     • Requires SSL/TLS certificates                     │
│     • Advanced security features                        │
│                                                          │
│  ┌─────────────────────────────────────────────────┐   │
│  │ ℹ You can change this later in Settings         │   │
│  └─────────────────────────────────────────────────┘   │
│                                                          │
│  [← Back]                             [Continue →]     │
└─────────────────────────────────────────────────────────┘
```

#### 3.3.2 Radio Options

**Localhost (default):**
- Title: "Localhost"
- Subtitle: "Single user on this computer only"
- Benefits:
  - No network access required
  - No authentication needed
  - Fastest performance
  - Recommended for personal use
- Icon: mdi-laptop

**LAN:**
- Title: "LAN (Local Area Network)"
- Subtitle: "Team access on your local network"
- Benefits:
  - Multiple users can connect
  - Requires admin account setup
  - Firewall configuration needed
  - Recommended for teams (2-10 users)
- Icon: mdi-network

**WAN (disabled):**
- Title: "WAN (Wide Area Network)"
- Subtitle: "Internet access for remote teams"
- Status: "Coming in Phase 1"
- Benefits (grayed):
  - Requires SSL/TLS certificates
  - Advanced security features
- Icon: mdi-earth (grayed)

#### 3.3.3 Visual Design
- Radio buttons with large clickable areas
- Hover state: Subtle background highlight
- Selected state: Yellow border + primary color accent
- Disabled state: 40% opacity + "Coming Soon" badge

#### 3.3.4 Actions
- Primary: "Continue" (enabled when selection made)
- Secondary: "Back"

#### 3.3.5 Conditional Logic
- If "Localhost" selected → Skip to Step 5 (AI Tools)
- If "LAN" selected → Go to Step 4 (Admin Account)
- Update progress indicator dynamically

#### 3.3.6 Accessibility
- Radio group with proper ARIA labels
- Keyboard navigation: Arrow keys to select, Tab to navigate buttons
- Screen reader announces selected option and benefits
- Focus visible on all interactive elements

---

### Step 4: Admin Account (Conditional - LAN only)

#### 3.4.1 Layout
```
┌─────────────────────────────────────────────────────────┐
│  Create Admin Account                                    │
│  ──────────────────────────────────────────────────────  │
│                                                          │
│  ┌─────────────────────────────────────────────────┐   │
│  │ ℹ This account will manage user access and      │   │
│  │   system settings for your LAN deployment.      │   │
│  └─────────────────────────────────────────────────┘   │
│                                                          │
│  Username                                               │
│  ┌─────────────────────────────────────────────────┐   │
│  │ admin                                            │   │
│  └─────────────────────────────────────────────────┘   │
│  ✓ Available                                            │
│                                                          │
│  Email (optional)                                       │
│  ┌─────────────────────────────────────────────────┐   │
│  │ admin@example.com                                │   │
│  └─────────────────────────────────────────────────┘   │
│                                                          │
│  Password                                               │
│  ┌─────────────────────────────────────────────────┐   │
│  │ ••••••••••••                          👁         │   │
│  └─────────────────────────────────────────────────┘   │
│  Password strength: ▓▓▓▓▓▓▓▓░░ Strong                  │
│                                                          │
│  Confirm Password                                       │
│  ┌─────────────────────────────────────────────────┐   │
│  │ ••••••••••••                          👁         │   │
│  └─────────────────────────────────────────────────┘   │
│  ✓ Passwords match                                      │
│                                                          │
│  Password Requirements:                                 │
│  ✓ At least 8 characters                               │
│  ✓ Contains uppercase letter                           │
│  ✓ Contains lowercase letter                           │
│  ✓ Contains number                                     │
│  ○ Contains special character (recommended)            │
│                                                          │
│  [← Back]                             [Continue →]     │
└─────────────────────────────────────────────────────────┘
```

#### 3.4.2 Form Fields

**Username:**
- Required
- Min length: 3 characters
- Pattern: alphanumeric + underscore/hyphen
- Validation: Real-time availability check
- Default: "admin"

**Email:**
- Optional
- Pattern: valid email format
- Validation: Real-time format check

**Password:**
- Required
- Min length: 8 characters
- Requirements:
  - Uppercase letter (required)
  - Lowercase letter (required)
  - Number (required)
  - Special character (recommended)
- Show/hide toggle
- Real-time strength indicator

**Confirm Password:**
- Required
- Validation: Must match password
- Real-time match indicator

#### 3.4.3 Password Strength Indicator
```
Weak:     ▓▓▓░░░░░░░ (red)     - < 8 chars or missing requirements
Fair:     ▓▓▓▓▓░░░░░ (orange)  - 8+ chars, 2 requirement types
Good:     ▓▓▓▓▓▓▓░░░ (yellow)  - 8+ chars, 3 requirement types
Strong:   ▓▓▓▓▓▓▓▓░░ (green)   - 10+ chars, all requirements
Excellent: ▓▓▓▓▓▓▓▓▓▓ (green)   - 12+ chars, all requirements + special
```

#### 3.4.4 Validation Rules
- Show validation messages only after field is touched
- Success: Green checkmark + "Available" / "Passwords match"
- Error: Red X + specific error message
- Real-time validation for username availability

#### 3.4.5 Actions
- Primary: "Continue" (enabled when form valid)
- Secondary: "Back" (navigates to deployment mode)

#### 3.4.6 Accessibility
- Labels properly associated with inputs
- Error messages announced by screen readers
- Password visibility toggle with ARIA labels
- Keyboard navigation through all fields
- Form validation prevents submission of invalid data

---

### Step 5: AI Tool Integration

#### 3.5.1 Layout
```
┌─────────────────────────────────────────────────────────┐
│  Configure AI Tool Integration                           │
│  ──────────────────────────────────────────────────────  │
│                                                          │
│  Detecting installed AI coding tools...                 │
│                                                          │
│  ┌─────────────────────────────────────────────────┐   │
│  │ ✓  Claude Code                                   │   │
│  │    Version: 1.2.3                                │   │
│  │    Path: C:\Users\...\AppData\Roaming\...       │   │
│  │                              [Configure] [Test]  │   │
│  └─────────────────────────────────────────────────┘   │
│                                                          │
│  ┌─────────────────────────────────────────────────┐   │
│  │ ✓  Cline                                         │   │
│  │    Version: 2.1.0                                │   │
│  │    Path: C:\Users\...\AppData\Roaming\...       │   │
│  │                              [Configure] [Test]  │   │
│  └─────────────────────────────────────────────────┘   │
│                                                          │
│  ┌─────────────────────────────────────────────────┐   │
│  │ ⊗  Cursor                                        │   │
│  │    Not detected                                  │   │
│  │    Install Cursor or configure manually          │   │
│  │                         [Manual Setup] [Skip]    │   │
│  └─────────────────────────────────────────────────┘   │
│                                                          │
│  ┌─────────────────────────────────────────────────┐   │
│  │ ℹ You can configure additional tools later in   │   │
│  │   Settings > AI Tools                            │   │
│  └─────────────────────────────────────────────────┘   │
│                                                          │
│  [← Back]  [Skip This Step]          [Continue →]     │
└─────────────────────────────────────────────────────────┘
```

#### 3.5.2 Tool Detection States

**Detected (Claude Code, Cline):**
- Green checkmark icon
- Tool name (bold)
- Version number
- Installation path (truncated)
- Actions: [Configure] [Test]

**Not Detected (Cursor):**
- Red X icon
- Tool name (grayed)
- Message: "Not detected"
- Suggestion: "Install Cursor or configure manually"
- Actions: [Manual Setup] [Skip]

**Configuring:**
- Loading spinner
- Message: "Generating configuration..."
- Disable all other actions

**Configured:**
- Green checkmark + blue badge "Configured"
- Actions: [Reconfigure] [Test]

**Testing:**
- Loading spinner on test button
- Message: "Testing connection..."

**Test Success:**
- Green alert: "Connection successful! Tool is ready to use."

**Test Failure:**
- Red alert: "Connection failed. [View Details] [Retry]"

#### 3.5.3 Configuration Dialog
```
┌─────────────────────────────────────────────────────────┐
│  Configuration Preview: Claude Code             [X]     │
│  ──────────────────────────────────────────────────────  │
│                                                          │
│  ┌─────────────────────────────────────────────────┐   │
│  │ ℹ This configuration will be written to:        │   │
│  │                                                  │   │
│  │   C:\Users\...\AppData\Roaming\Code\User\      │   │
│  │   globalStorage\saoudrizwan.claude-dev\         │   │
│  │   settings\cline_mcp_settings.json              │   │
│  └─────────────────────────────────────────────────┘   │
│                                                          │
│  ┌──────────────────────────────────────────────────┐  │
│  │ {                                                 │  │
│  │   "mcpServers": {                                 │  │
│  │     "giljo-mcp": {                                │  │
│  │       "command": "node",                          │  │
│  │       "args": [                                   │  │
│  │         "C:/Projects/GiljoAI_MCP/..."            │  │
│  │       ],                                          │  │
│  │       "env": {                                    │  │
│  │         "DATABASE_URL": "postgresql://..."       │  │
│  │       }                                           │  │
│  │     }                                             │  │
│  │   }                                               │  │
│  │ }                                                 │  │
│  └──────────────────────────────────────────────────┘  │
│                                                          │
│  ⚠ Warning: This will modify your tool configuration   │
│                                                          │
│  [Cancel]                      [Apply Configuration]   │
└─────────────────────────────────────────────────────────┘
```

#### 3.5.4 User Actions

**Configure:**
1. Click [Configure] → Show configuration preview dialog
2. Review JSON configuration
3. Click [Apply Configuration] → Write config file
4. Auto-run connection test
5. Show success/failure message

**Test:**
1. Click [Test] → Send test request to MCP server
2. Show loading state
3. Display test result
4. Update tool card with result

**Manual Setup:**
1. Click [Manual Setup] → Show manual config dialog
2. User provides config path
3. System validates path
4. Generate and write config
5. Run connection test

**Skip:**
1. Click [Skip This Step] → Show confirmation dialog
2. Warning: "You can configure tools later in Settings"
3. Confirm → Continue to next step

#### 3.5.5 Actions
- Primary: "Continue" (enabled when at least 1 tool configured, or user confirms skip)
- Secondary: "Skip This Step" (shows confirmation dialog)
- Tertiary: "Back"

#### 3.5.6 Accessibility
- Tool list with proper ARIA labels
- Configuration dialog announced as modal
- Test results announced by screen readers
- Keyboard navigation: Tab through tools, Enter to configure/test
- Focus management: Return focus to trigger button after dialog closes

---

### Step 6: LAN Configuration (Conditional - LAN only)

#### 3.6.1 Layout
```
┌─────────────────────────────────────────────────────────┐
│  LAN Network Configuration                               │
│  ──────────────────────────────────────────────────────  │
│                                                          │
│  Your GiljoAI MCP server is now running on:             │
│  ┌─────────────────────────────────────────────────┐   │
│  │  http://192.168.1.100:7274                       │   │
│  │                                      [Copy URL]  │   │
│  └─────────────────────────────────────────────────┘   │
│                                                          │
│  Firewall Configuration                                 │
│  ──────────────────────────────────────────────────────  │
│                                                          │
│  Platform detected: Windows 11                          │
│                                                          │
│  ┌─────────────────────────────────────────────────┐   │
│  │ ⚠ Port 7274 must be open for network access    │   │
│  └─────────────────────────────────────────────────┘   │
│                                                          │
│  Run this command as Administrator:                     │
│  ┌─────────────────────────────────────────────────┐   │
│  │ netsh advfirewall firewall add rule ^           │   │
│  │   name="GiljoAI MCP" dir=in action=allow ^      │   │
│  │   protocol=TCP localport=7274                   │   │
│  │                                          [Copy]  │   │
│  └─────────────────────────────────────────────────┘   │
│                                                          │
│  1. Open PowerShell as Administrator                    │
│  2. Paste and run the command above                     │
│  3. Click "Test Port Access" below                      │
│                                                          │
│  [Test Port Access]                                     │
│                                                          │
│  ┌─────────────────────────────────────────────────┐   │
│  │ ✓ Port 7274 is accessible on your network       │   │
│  │   Team members can now connect to:              │   │
│  │   http://192.168.1.100:7274                      │   │
│  └─────────────────────────────────────────────────┘   │
│                                                          │
│  [← Back]                             [Continue →]     │
└─────────────────────────────────────────────────────────┘
```

#### 3.6.2 Platform-Specific Instructions

**Windows:**
```powershell
netsh advfirewall firewall add rule ^
  name="GiljoAI MCP" dir=in action=allow ^
  protocol=TCP localport=7274
```

**Linux (ufw):**
```bash
sudo ufw allow 7274/tcp
sudo ufw reload
```

**Linux (iptables):**
```bash
sudo iptables -A INPUT -p tcp --dport 7274 -j ACCEPT
sudo iptables-save | sudo tee /etc/iptables/rules.v4
```

**macOS:**
```
1. Open System Preferences > Security & Privacy
2. Click Firewall > Firewall Options
3. Click + to add an application
4. Select "GiljoAI MCP" or add port 7274
5. Click OK
```

#### 3.6.3 Network Detection
- Auto-detect platform: Windows, Linux, macOS
- Auto-detect local IP address(es)
- If multiple IPs, show dropdown to select
- Display full server URL with IP and port

#### 3.6.4 Port Testing
1. Click [Test Port Access]
2. Backend attempts to bind to port
3. Tests accessibility from localhost
4. Shows result:
   - Success: Green alert + team connection URL
   - Blocked: Red alert + "Port appears blocked. Verify firewall settings."
   - Error: Orange alert + "Could not test port. Continue anyway?"

#### 3.6.5 Actions
- Primary: "Continue" (enabled after successful port test, or user acknowledges warning)
- Secondary: "Back"
- Tertiary: "Test Port Access", "Copy URL", "Copy Command"

#### 3.6.6 Accessibility
- Code blocks with proper ARIA labels "Firewall command"
- Copy buttons announce "Copied!" on activation
- Port test result announced by screen readers
- Keyboard navigation through all interactive elements

---

### Step 7: Complete

#### 3.7.1 Layout
```
┌─────────────────────────────────────────────────────────┐
│  ✓  Setup Complete!                                     │
│  ──────────────────────────────────────────────────────  │
│                                                          │
│  ┌─────────────────────────────────────────────────┐   │
│  │  🎉 GiljoAI MCP is ready to use!                │   │
│  │                                                  │   │
│  │  Your configuration summary:                     │   │
│  └─────────────────────────────────────────────────┘   │
│                                                          │
│  System Status                                          │
│  ┌─────────────────────────────────────────────────┐   │
│  │  ✓  Database: Connected                          │   │
│  │      PostgreSQL on localhost:5432                │   │
│  └─────────────────────────────────────────────────┘   │
│                                                          │
│  ┌─────────────────────────────────────────────────┐   │
│  │  ✓  Deployment: Localhost                        │   │
│  │      Single-user mode                            │   │
│  └─────────────────────────────────────────────────┘   │
│                                                          │
│  ┌─────────────────────────────────────────────────┐   │
│  │  ✓  AI Tools: 2 configured                       │   │
│  │      • Claude Code (connected)                   │   │
│  │      • Cline (connected)                         │   │
│  └─────────────────────────────────────────────────┘   │
│                                                          │
│  ┌─────────────────────────────────────────────────┐   │
│  │  ✓  WebSocket: Active                            │   │
│  │      Real-time updates enabled                   │   │
│  └─────────────────────────────────────────────────┘   │
│                                                          │
│  Next Steps                                             │
│  • Create your first project                           │
│  • Explore agent templates                             │
│  • Review documentation                                │
│                                                          │
│                                   [Go to Dashboard →]   │
└─────────────────────────────────────────────────────────┘
```

#### 3.7.2 Configuration Summary

**Display:**
- Green checkmarks for all completed steps
- Summarize key configuration choices
- Show connection status for each component
- Provide "Next Steps" suggestions

**Data Displayed:**
- Database connection (host:port)
- Deployment mode (localhost/LAN)
- If LAN: Admin account created, network URL
- AI tools configured (count + list)
- WebSocket status

#### 3.7.3 Celebration Moment
- Success icon/animation (subtle)
- Positive messaging: "GiljoAI MCP is ready to use!"
- Confidence-building summary

#### 3.7.4 Next Steps
- Contextual suggestions based on configuration:
  - "Create your first project"
  - "Explore agent templates"
  - "Review documentation"
  - If LAN: "Share access URL with team members"

#### 3.7.5 Actions
- Primary: "Go to Dashboard" (navigates to `/`)
- Secondary: None (setup complete)
- Save setup completion flag to prevent re-showing wizard

#### 3.7.6 Accessibility
- Success message announced by screen readers
- Keyboard focus on "Go to Dashboard" button
- Summary list properly structured with headings

---

## 4. Visual Design System

### 4.1 Color Palette

**Dark Theme (default):**
- Background: `#0e1c2d` (darkest blue)
- Surface: `#182739` (dark blue)
- Surface Variant: `#1e3147` (lighter dark blue)
- Primary: `#ffc300` (yellow - GiljoAI brand)
- Success: `#67bd6d` (green)
- Error: `#c6298c` (pink-red)
- Warning: `#ffc300` (yellow)
- Info: `#8f97b7` (light blue)
- Text: `#e1e1e1` (light gray)

**Light Theme:**
- Background: `#ffffff`
- Surface: `#f5f5f5`
- Primary: `#ffc300` (yellow)
- Text: `#363636` (dark gray)

### 4.2 Typography

**Headings:**
- H1 (Step titles): 2rem, font-weight: 500, color: primary
- H2 (Sections): 1.5rem, font-weight: 500
- H3 (Subsections): 1.25rem, font-weight: 500

**Body:**
- Default: 1rem, font-weight: 400, line-height: 1.5
- Small: 0.875rem (form hints, captions)

**Code:**
- Font: 'Courier New', monospace
- Background: surface-variant
- Padding: 1rem
- Border-radius: 8px

### 4.3 Spacing

**Layout:**
- Container padding: 24px
- Card padding: 24px
- Section spacing: 32px
- Element spacing: 16px

**Components:**
- Button padding: 12px 24px
- Input padding: 12px 16px
- Alert padding: 16px

### 4.4 Component Styles

**Cards:**
- Elevation: 2
- Border-radius: 12px
- Padding: 24px

**Buttons:**
- Primary: Solid yellow (`#ffc300`), dark text
- Secondary: Outlined, no background
- Tertiary: Text only, no border
- Border-radius: 8px
- Min-width: 100px
- Height: 40px

**Inputs:**
- Variant: outlined
- Border-radius: 8px
- Height: 48px
- Focus: 2px yellow border

**Alerts:**
- Border-radius: 8px
- Padding: 16px
- Icon on left
- Variants: success (green), error (red), info (blue), warning (yellow)

---

## 5. Responsive Design

### 5.1 Breakpoints

**Desktop (> 960px):**
- Wizard width: 800px (centered)
- Two-column layouts where appropriate
- Full-size code blocks

**Tablet (600px - 960px):**
- Wizard width: 90% viewport width
- Single-column layouts
- Readable code blocks

**Mobile (< 600px):**
- Wizard width: 100% viewport width
- Single-column layouts
- Horizontal scrolling for wide code blocks
- Larger touch targets (48px min)
- Stacked buttons

### 5.2 Layout Adjustments

**Desktop:**
```
┌────────────────────────┐
│  [Back]     [Continue] │  ← Buttons at edges
└────────────────────────┘
```

**Mobile:**
```
┌────────────────────────┐
│      [Continue]        │  ← Stacked, full-width
│      [Back]            │
└────────────────────────┘
```

### 5.3 Touch Optimization

**Mobile:**
- Minimum touch target: 48px x 48px
- Increased spacing between interactive elements
- Larger font sizes for readability
- Sticky action buttons at bottom

---

## 6. Interaction Design

### 6.1 Animations

**Transitions:**
- Step changes: 200ms fade
- Alert appearances: 150ms slide-down
- Button states: 100ms ease

**Loading States:**
- Spinner for async operations
- Skeleton screens for tool detection
- Progress bars for multi-step processes

### 6.2 Feedback Mechanisms

**Immediate Feedback:**
- Button press: Visual state change
- Form input: Real-time validation
- Hover: Subtle background highlight

**Delayed Feedback:**
- API calls: Loading spinner
- Connection tests: Progress indicator
- File writes: Success confirmation

### 6.3 Error Recovery

**Inline Errors:**
- Show next to problematic field
- Provide specific, actionable message
- Suggest correction

**Step-Level Errors:**
- Alert at top of step
- List all validation errors
- Disable continue button until resolved

**Critical Errors:**
- Full-page error state
- Contact support information
- Option to restart wizard

---

## 7. Accessibility Standards

### 7.1 WCAG 2.1 AA Compliance

**Perceivable:**
- Color contrast ≥ 4.5:1 for text
- Color contrast ≥ 3:1 for UI components
- Alt text for all icons
- No information conveyed by color alone

**Operable:**
- All functionality keyboard accessible
- Visible focus indicators (2px yellow outline)
- No keyboard traps
- Sufficient time for reading

**Understandable:**
- Clear, consistent navigation
- Input labels and instructions
- Error identification and suggestions
- Predictable behavior

**Robust:**
- Valid HTML5
- ARIA landmarks and labels
- Screen reader compatibility
- Cross-browser support

### 7.2 Keyboard Navigation

**Global:**
- Tab: Next focusable element
- Shift+Tab: Previous focusable element
- Enter: Activate button/link
- Escape: Cancel/close dialog/go back
- Space: Toggle checkbox/radio

**Step-Specific:**
- Arrow keys: Navigate radio options (deployment mode)
- Enter: Submit form (when valid)
- Escape: Return to previous step (with confirmation if unsaved changes)

### 7.3 Screen Reader Support

**Announcements:**
- Step transitions: "Step 2 of 7: Database Connection"
- Validation: "Error: Password must be at least 8 characters"
- Success: "Connection successful"
- Loading: "Testing connection, please wait"

**ARIA Labels:**
- Form fields: aria-label or associated label
- Buttons: Clear action names
- Status messages: role="status" or role="alert"
- Progress: aria-valuenow, aria-valuemin, aria-valuemax

### 7.4 Focus Management

**Rules:**
- Focus on first interactive element when step loads
- Return focus to trigger after dialog closes
- Focus on first error field when validation fails
- Maintain focus visibility at all times

---

## 8. Error Handling & Validation

### 8.1 Validation Strategy

**Client-Side:**
- Real-time validation on blur
- Prevent invalid form submission
- Clear, specific error messages

**Server-Side:**
- Validate all inputs on backend
- Return structured error responses
- Display errors contextually

### 8.2 Error Message Patterns

**Format:**
```
[Icon] [Field/Context]: [Specific problem]. [Suggested action].
```

**Examples:**
- "⊗ Username: Already taken. Please choose a different username."
- "⊗ Password: Too short. Password must be at least 8 characters."
- "⊗ Database: Connection failed. Check if PostgreSQL is running."

### 8.3 Troubleshooting Links

**When to Show:**
- Database connection fails
- Port test fails
- AI tool configuration fails

**Link Format:**
```
Need help? [View troubleshooting guide]
```

**Destination:**
- Internal docs: `/docs/troubleshooting/[topic]`
- External docs: Opens in new tab with rel="noopener"

---

## 9. Performance Considerations

### 9.1 Loading States

**Tool Detection:**
- Show skeleton UI while detecting
- Timeout after 10 seconds
- Fallback: Manual configuration option

**Connection Tests:**
- Show spinner on button
- Timeout after 30 seconds
- Provide retry option

### 9.2 Optimization

**Lazy Loading:**
- Load step components on demand
- Preload next step when current step valid

**Caching:**
- Cache tool detection results
- Store wizard progress in localStorage
- Resume wizard if user navigates away

### 9.3 Network Resilience

**Offline Detection:**
- Detect network loss
- Show warning: "Network connection lost"
- Retry requests automatically

**Request Timeouts:**
- Database test: 30s
- Tool detection: 10s
- Config write: 5s
- Port test: 10s

---

## 10. Testing Requirements

### 10.1 Browser Compatibility

**Supported:**
- Chrome 120+
- Firefox 120+
- Safari 17+
- Edge 120+

**Testing:**
- Test all steps in each browser
- Verify responsive layouts
- Test keyboard navigation
- Verify screen reader compatibility

### 10.2 Platform Testing

**Operating Systems:**
- Windows 10/11
- macOS Ventura+
- Linux (Ubuntu 22.04+)

**Platform-Specific:**
- Verify firewall instructions display correctly
- Test path detection for each platform
- Validate platform-specific commands

### 10.3 Accessibility Testing

**Tools:**
- WAVE browser extension
- axe DevTools
- Lighthouse accessibility audit
- Manual screen reader testing (NVDA, JAWS, VoiceOver)

**Checklist:**
- All images have alt text
- Color contrast passes WCAG AA
- Keyboard navigation works
- Focus indicators visible
- Screen reader announces correctly
- No keyboard traps

---

## 11. Success Metrics

### 11.1 Completion Rate

**Target**: 95% of users complete setup without abandoning

**Tracking:**
- Log step entry/exit
- Measure time per step
- Identify drop-off points

### 11.2 Error Rate

**Target**: < 5% of users encounter errors

**Tracking:**
- Log all errors by type
- Track error recovery attempts
- Measure time to resolution

### 11.3 User Satisfaction

**Target**: 4.5/5 average satisfaction score

**Feedback:**
- Post-setup survey (optional)
- "Was this helpful?" on each step
- Contact support option

---

## 12. Future Enhancements (Phase 1+)

### 12.1 WAN Mode Support
- SSL/TLS certificate configuration
- Domain name setup
- Advanced security settings
- Port forwarding guidance

### 12.2 Advanced Features
- Import existing configuration
- Export configuration for team sharing
- Setup profiles (save and reuse)
- Video tutorials embedded in wizard

### 12.3 Improved Detection
- Auto-detect more AI tools
- Suggest optimal configuration based on system
- Pre-fill common settings

---

## Appendix A: Component Props & Events

See `component_hierarchy.md` for detailed specifications.

## Appendix B: API Endpoints

See backend Phase 0 specifications for API contract.

## Appendix C: Wireframes

See `wizard_wireframes.md` for detailed ASCII wireframes.

---

**Document Status**: Ready for Review
**Next Steps**:
1. Review with Orchestrator
2. Create wireframes document
3. Define component hierarchy
4. Plan database component extraction
