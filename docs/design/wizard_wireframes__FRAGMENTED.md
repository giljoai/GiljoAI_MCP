# GiljoAI MCP Setup Wizard - Detailed Wireframes

**Version**: 1.0
**Date**: 2025-10-05
**Designer**: UX Designer Agent

---

## Wireframe Notation

```
┌─┐  Borders and containers
│ │
└─┘

[Button]  Clickable button
○         Radio button (unselected)
●         Radio button (selected)
□         Checkbox (unchecked)
☑         Checkbox (checked)
✓         Success indicator
⊗         Error indicator
⚠         Warning indicator
ℹ         Information indicator
🔒        Locked/Read-only indicator
👁         Show/hide toggle
▓░░░      Progress bar (40% filled)
```

---

## Step 1: Welcome Screen

### Desktop View (> 960px)

```
┌─────────────────────────────────────────────────────────────────────────┐
│                                                                         │
│                            ┌─────────────────┐                         │
│                            │                 │                         │
│                            │  [GiljoAI Logo] │  (Yellow/White)         │
│                            │                 │                         │
│                            └─────────────────┘                         │
│                                                                         │
│                    Welcome to GiljoAI MCP                              │
│              Multi-Agent Coding Orchestrator                           │
│                                                                         │
│     ┌───────────────────────────────────────────────────────────┐     │
│     │                                                             │     │
│     │   This setup wizard will help you:                         │     │
│     │                                                             │     │
│     │   ✓  Verify PostgreSQL database connection                │     │
│     │   ✓  Choose your deployment mode                          │     │
│     │   ✓  Configure AI tool integration                        │     │
│     │   ✓  Complete initial system setup                        │     │
│     │                                                             │     │
│     │   Estimated time: 5-10 minutes                             │     │
│     │                                                             │     │
│     └───────────────────────────────────────────────────────────┘     │
│                                                                         │
│     ┌───────────────────────────────────────────────────────────┐     │
│     │  Progress: Step 1 of 7                                     │     │
│     │  ▓▓░░░░░░░░░░░░░░░░░░ 14%                                 │     │
│     └───────────────────────────────────────────────────────────┘     │
│                                                                         │
│                                                                         │
│                                                                         │
│                                                                         │
│                                             [Get Started →]            │
│                                                                         │
└─────────────────────────────────────────────────────────────────────────┘
```

### Tablet View (600px - 960px)

```
┌──────────────────────────────────────────────┐
│                                              │
│         ┌─────────────┐                     │
│         │ [GiljoAI]   │                     │
│         └─────────────┘                     │
│                                              │
│      Welcome to GiljoAI MCP                 │
│   Multi-Agent Coding Orchestrator           │
│                                              │
│  ┌────────────────────────────────────┐    │
│  │ This wizard will help you:          │    │
│  │                                     │    │
│  │ ✓ Verify database connection       │    │
│  │ ✓ Choose deployment mode            │    │
│  │ ✓ Configure AI tools                │    │
│  │ ✓ Complete setup                    │    │
│  │                                     │    │
│  │ Estimated time: 5-10 minutes        │    │
│  └────────────────────────────────────┘    │
│                                              │
│  ┌────────────────────────────────────┐    │
│  │ Step 1 of 7                         │    │
│  │ ▓▓░░░░░░░░░░░░░ 14%                │    │
│  └────────────────────────────────────┘    │
│                                              │
│                                              │
│                   [Get Started →]           │
│                                              │
└──────────────────────────────────────────────┘
```

### Mobile View (< 600px)

```
┌─────────────────────────────┐
│                             │
│      [GiljoAI Logo]         │
│                             │
│  Welcome to GiljoAI MCP     │
│  Multi-Agent Coding         │
│  Orchestrator               │
│                             │
│ ┌─────────────────────────┐ │
│ │ This wizard will help:  │ │
│ │                         │ │
│ │ ✓ Verify database       │ │
│ │ ✓ Choose mode           │ │
│ │ ✓ Configure AI tools    │ │
│ │ ✓ Complete setup        │ │
│ │                         │ │
│ │ Time: 5-10 minutes      │ │
│ └─────────────────────────┘ │
│                             │
│ ┌─────────────────────────┐ │
│ │ Step 1 of 7             │ │
│ │ ▓▓░░░░░░░░ 14%          │ │
│ └─────────────────────────┘ │
│                             │
│                             │
│    [Get Started →]         │
│                             │
└─────────────────────────────┘
```

### Interactive States

**Default State:**
```
[Get Started →]  ← Primary yellow button, dark text
```

**Hover State:**
```
[Get Started →]  ← Slightly lighter yellow, shadow
```

**Focus State:**
```
╔════════════════╗
║ Get Started →  ║  ← 2px yellow outline
╚════════════════╝
```

---

## Step 2: Database Connection

### Desktop View - Initial State

```
┌─────────────────────────────────────────────────────────────────────────┐
│  ← Stepper: [1✓] [2●] [3○] [4○] [5○] [6○] [7○]                        │
│                                                                         │
│  Database Connection                                                   │
│  ─────────────────────────────────────────────────────────────────────  │
│                                                                         │
│  ┌───────────────────────────────────────────────────────────────┐    │
│  │ ℹ Database settings were configured during installation.      │    │
│  │   This step verifies that the connection is working properly. │    │
│  └───────────────────────────────────────────────────────────────┘    │
│                                                                         │
│  Connection Details (read-only)                                        │
│  ┌───────────────────────────┬──────────────────────────────────┐    │
│  │  Host                     │  Port                            │    │
│  │  ┌─────────────────────┐  │  ┌─────────────────────────┐    │    │
│  │  │ localhost        🔒 │  │  │ 5432                 🔒 │    │    │
│  │  └─────────────────────┘  │  └─────────────────────────┘    │    │
│  └───────────────────────────┴──────────────────────────────────┘    │
│                                                                         │
│  ┌───────────────────────────┬──────────────────────────────────┐    │
│  │  Database Name            │  Username                        │    │
│  │  ┌─────────────────────┐  │  ┌─────────────────────────┐    │    │
│  │  │ giljo_mcp        🔒 │  │  │ postgres             🔒 │    │    │
│  │  └─────────────────────┘  │  └─────────────────────────┘    │    │
│  └───────────────────────────┴──────────────────────────────────┘    │
│                                                                         │
│  ┌─────────────────────────────────────────────────────────────┐     │
│  │  Password                                                     │     │
│  │  ┌─────────────────────────────────────────────────────────┐ │     │
│  │  │ ••••••••••••                                          🔒 │ │     │
│  │  └─────────────────────────────────────────────────────────┘ │     │
│  └─────────────────────────────────────────────────────────────┘     │
│                                                                         │
│  ─────────────────────────────────────────────────────────────────────  │
│                                                                         │
│  [Test Connection]                                                     │
│                                                                         │
│                                                                         │
│  Need help with database issues? View troubleshooting guide           │
│                                                                         │
│  ┌───────────────────────────────────────────────────────────────┐    │
│  │  Progress: Step 2 of 7                                         │    │
│  │  ▓▓▓▓░░░░░░░░░░░░░░░░ 29%                                     │    │
│  └───────────────────────────────────────────────────────────────┘    │
│                                                                         │
│  [← Back]                                          [Continue →]       │
│  (disabled until test succeeds)                                        │
└─────────────────────────────────────────────────────────────────────────┘
```

### Testing State

```
┌─────────────────────────────────────────────────────────────────────────┐
│  Database Connection                                                   │
│  ─────────────────────────────────────────────────────────────────────  │
│                                                                         │
│  (... connection details fields ...)                                   │
│                                                                         │
│  [ ⟳  Testing Connection...]  ← Button shows spinner                  │
│                                                                         │
│  ┌───────────────────────────────────────────────────────────────┐    │
│  │ ⟳  Testing connection to PostgreSQL database...               │    │
│  │    This may take a few seconds.                                │    │
│  └───────────────────────────────────────────────────────────────┘    │
│                                                                         │
│  [← Back]                                          [Continue →]       │
│                                                    (disabled)           │
└─────────────────────────────────────────────────────────────────────────┘
```

### Success State

```
┌─────────────────────────────────────────────────────────────────────────┐
│  Database Connection                                                   │
│  ─────────────────────────────────────────────────────────────────────  │
│                                                                         │
│  (... connection details fields ...)                                   │
│                                                                         │
│  [Test Connection]                                                     │
│                                                                         │
│  ┌───────────────────────────────────────────────────────────────┐    │
│  │ ✓ Connection successful!                                       │    │
│  │   Connected to PostgreSQL database 'giljo_mcp' on              │    │
│  │   localhost:5432                                               │    │
│  └───────────────────────────────────────────────────────────────┘    │
│                          ↑ Green background                             │
│                                                                         │
│  [← Back]                                          [Continue →]       │
│                                                    (enabled)            │
└─────────────────────────────────────────────────────────────────────────┘
```

### Error State

```
┌─────────────────────────────────────────────────────────────────────────┐
│  Database Connection                                                   │
│  ─────────────────────────────────────────────────────────────────────  │
│                                                                         │
│  (... connection details fields ...)                                   │
│                                                                         │
│  [Test Connection]                                                     │
│                                                                         │
│  ┌───────────────────────────────────────────────────────────────┐    │
│  │ ⊗ Connection failed                                            │    │
│  │   Could not connect to PostgreSQL database.                    │    │
│  │                                                                 │    │
│  │   Error: ECONNREFUSED - Connection refused                     │    │
│  │                                                                 │    │
│  │   Possible causes:                                             │    │
│  │   • PostgreSQL service is not running                          │    │
│  │   • Incorrect host or port                                     │    │
│  │   • Firewall blocking connection                               │    │
│  │                                                                 │    │
│  │   [View Troubleshooting Guide]                                 │    │
│  └───────────────────────────────────────────────────────────────┘    │
│                          ↑ Red background                               │
│                                                                         │
│  [← Back]                                          [Continue →]       │
│                                                    (disabled)           │
└─────────────────────────────────────────────────────────────────────────┘
```

---

## Step 3: Deployment Mode Selection

### Desktop View

```
┌─────────────────────────────────────────────────────────────────────────┐
│  ← Stepper: [1✓] [2✓] [3●] [4○] [5○] [6○] [7○]                        │
│                                                                         │
│  Choose Deployment Mode                                                │
│  ─────────────────────────────────────────────────────────────────────  │
│                                                                         │
│  How will you use GiljoAI MCP?                                         │
│                                                                         │
│  ┌───────────────────────────────────────────────────────────────┐    │
│  │ ●  Localhost                                                   │    │
│  │    Single user on this computer only                           │    │
│  │                                                                 │    │
│  │    ┌─────────────────────────────────────────────────────┐    │    │
│  │    │  • No network access required                        │    │    │
│  │    │  • No authentication needed                          │    │    │
│  │    │  • Fastest performance                               │    │    │
│  │    │  • Recommended for personal use                      │    │    │
│  │    └─────────────────────────────────────────────────────┘    │    │
│  └───────────────────────────────────────────────────────────────┘    │
│                     ↑ Yellow border when selected                       │
│                                                                         │
│  ┌───────────────────────────────────────────────────────────────┐    │
│  │ ○  LAN (Local Area Network)                                   │    │
│  │    Team access on your local network                          │    │
│  │                                                                 │    │
│  │    ┌─────────────────────────────────────────────────────┐    │    │
│  │    │  • Multiple users can connect                        │    │    │
│  │    │  • Requires admin account setup                      │    │    │
│  │    │  • Firewall configuration needed                     │    │    │
│  │    │  • Recommended for teams (2-10 users)                │    │    │
│  │    └─────────────────────────────────────────────────────┘    │    │
│  └───────────────────────────────────────────────────────────────┘    │
│                                                                         │
│  ┌───────────────────────────────────────────────────────────────┐    │
│  │ ⊘  WAN (Wide Area Network)                                    │    │
│  │    Internet access for remote teams                           │    │
│  │                                                                 │    │
│  │    ┌─────────────────────────────────────────────────────┐    │    │
│  │    │  • Coming in Phase 1                                 │    │    │
│  │    │  • Requires SSL/TLS certificates                     │    │    │
│  │    │  • Advanced security features                        │    │    │
│  │    └─────────────────────────────────────────────────────┘    │    │
│  └───────────────────────────────────────────────────────────────┘    │
│                     ↑ Grayed out, not clickable                         │
│                                                                         │
│  ┌───────────────────────────────────────────────────────────────┐    │
│  │ ℹ You can change this setting later in Settings > General     │    │
│  └───────────────────────────────────────────────────────────────┘    │
│                                                                         │
│  ┌───────────────────────────────────────────────────────────────┐    │
│  │  Progress: Step 3 of 7                                         │    │
│  │  ▓▓▓▓▓▓░░░░░░░░░░░░░░ 43%                                     │    │
│  └───────────────────────────────────────────────────────────────┘    │
│                                                                         │
│  [← Back]                                          [Continue →]       │
└─────────────────────────────────────────────────────────────────────────┘
```

### Mobile View

```
┌─────────────────────────────┐
│ Choose Deployment Mode      │
│ ─────────────────────────── │
│                             │
│ How will you use it?        │
│                             │
│ ┌─────────────────────────┐ │
│ │ ● Localhost             │ │
│ │   Single user           │ │
│ │                         │ │
│ │ • No network needed     │ │
│ │ • No authentication     │ │
│ │ • Fastest performance   │ │
│ │ • Personal use          │ │
│ └─────────────────────────┘ │
│                             │
│ ┌─────────────────────────┐ │
│ │ ○ LAN                   │ │
│ │   Team access           │ │
│ │                         │ │
│ │ • Multi-user            │ │
│ │ • Admin account needed  │ │
│ │ • Firewall config       │ │
│ │ • Teams (2-10 users)    │ │
│ └─────────────────────────┘ │
│                             │
│ ┌─────────────────────────┐ │
│ │ ⊘ WAN (Coming Soon)     │ │
│ │   Internet access       │ │
│ │                         │ │
│ │ • Phase 1 feature       │ │
│ │ • SSL/TLS required      │ │
│ └─────────────────────────┘ │
│                             │
│ ┌─────────────────────────┐ │
│ │ Step 3 of 7             │ │
│ │ ▓▓▓▓▓▓░░░░ 43%          │ │
│ └─────────────────────────┘ │
│                             │
│    [Continue →]            │
│    [← Back]                │
│                             │
└─────────────────────────────┘
```

---

## Step 4: Admin Account (Conditional - LAN Mode Only)

### Desktop View - Empty Form

```
┌─────────────────────────────────────────────────────────────────────────┐
│  ← Stepper: [1✓] [2✓] [3✓] [4●] [5○] [6○] [7○]                        │
│                                                                         │
│  Create Admin Account                                                  │
│  ─────────────────────────────────────────────────────────────────────  │
│                                                                         │
│  ┌───────────────────────────────────────────────────────────────┐    │
│  │ ℹ This account will manage user access and system settings    │    │
│  │   for your LAN deployment.                                     │    │
│  └───────────────────────────────────────────────────────────────┘    │
│                                                                         │
│  Username                                                              │
│  ┌─────────────────────────────────────────────────────────────┐     │
│  │                                                               │     │
│  │                                                               │     │
│  └─────────────────────────────────────────────────────────────┘     │
│  Must be 3-20 characters (letters, numbers, - or _)                   │
│                                                                         │
│  Email (optional)                                                      │
│  ┌─────────────────────────────────────────────────────────────┐     │
│  │                                                               │     │
│  │                                                               │     │
│  └─────────────────────────────────────────────────────────────┘     │
│  For password recovery and notifications                              │
│                                                                         │
│  Password                                                              │
│  ┌─────────────────────────────────────────────────────────────┐     │
│  │                                                            👁 │     │
│  │                                                               │     │
│  └─────────────────────────────────────────────────────────────┘     │
│  Password strength: Not set                                            │
│                                                                         │
│  Confirm Password                                                      │
│  ┌─────────────────────────────────────────────────────────────┐     │
│  │                                                            👁 │     │
│  │                                                               │     │
│  └─────────────────────────────────────────────────────────────┘     │
│                                                                         │
│  Password Requirements:                                                │
│  ○ At least 8 characters                                              │
│  ○ Contains uppercase letter                                          │
│  ○ Contains lowercase letter                                          │
│  ○ Contains number                                                    │
│  ○ Contains special character (recommended)                           │
│                                                                         │
│  ┌───────────────────────────────────────────────────────────────┐    │
│  │  Progress: Step 4 of 7                                         │    │
│  │  ▓▓▓▓▓▓▓▓░░░░░░░░░░░░ 57%                                     │    │
│  └───────────────────────────────────────────────────────────────┘    │
│                                                                         │
│  [← Back]                                          [Continue →]       │
│                                                    (disabled)           │
└─────────────────────────────────────────────────────────────────────────┘
```

### Filled Form with Validation

```
┌─────────────────────────────────────────────────────────────────────────┐
│  Create Admin Account                                                  │
│  ─────────────────────────────────────────────────────────────────────  │
│                                                                         │
│  Username                                                              │
│  ┌─────────────────────────────────────────────────────────────┐     │
│  │ admin_user                                                   │     │
│  └─────────────────────────────────────────────────────────────┘     │
│  ✓ Available                           ← Green checkmark               │
│                                                                         │
│  Email (optional)                                                      │
│  ┌─────────────────────────────────────────────────────────────┐     │
│  │ admin@example.com                                            │     │
│  └─────────────────────────────────────────────────────────────┘     │
│  ✓ Valid email format                  ← Green checkmark               │
│                                                                         │
│  Password                                                              │
│  ┌─────────────────────────────────────────────────────────────┐     │
│  │ ••••••••••••••••                                          👁 │     │
│  └─────────────────────────────────────────────────────────────┘     │
│  Password strength: ▓▓▓▓▓▓▓▓░░ Strong  ← Green bar                    │
│                                                                         │
│  Confirm Password                                                      │
│  ┌─────────────────────────────────────────────────────────────┐     │
│  │ ••••••••••••••••                                          👁 │     │
│  └─────────────────────────────────────────────────────────────┘     │
│  ✓ Passwords match                     ← Green checkmark               │
│                                                                         │
│  Password Requirements:                                                │
│  ✓ At least 8 characters               ← Green checks                 │
│  ✓ Contains uppercase letter                                          │
│  ✓ Contains lowercase letter                                          │
│  ✓ Contains number                                                    │
│  ✓ Contains special character (recommended)                           │
│                                                                         │
│  [← Back]                                          [Continue →]       │
│                                                    (enabled)            │
└─────────────────────────────────────────────────────────────────────────┘
```

### Error States

```
┌─────────────────────────────────────────────────────────────────────────┐
│  Username                                                              │
│  ┌─────────────────────────────────────────────────────────────┐     │
│  │ ab                                                           │     │
│  └─────────────────────────────────────────────────────────────┘     │
│  ⊗ Too short. Username must be at least 3 characters.                │
│                          ↑ Red X and message                            │
│                                                                         │
│  Password                                                              │
│  ┌─────────────────────────────────────────────────────────────┐     │
│  │ ••••••                                                    👁 │     │
│  └─────────────────────────────────────────────────────────────┘     │
│  Password strength: ▓▓░░░░░░░░ Weak    ← Red bar                      │
│                                                                         │
│  Confirm Password                                                      │
│  ┌─────────────────────────────────────────────────────────────┐     │
│  │ ••••••••                                                  👁 │     │
│  └─────────────────────────────────────────────────────────────┘     │
│  ⊗ Passwords do not match              ← Red X and message            │
│                                                                         │
│  Password Requirements:                                                │
│  ✓ At least 8 characters                                              │
│  ⊗ Contains uppercase letter           ← Red X for unmet requirement │
│  ✓ Contains lowercase letter                                          │
│  ⊗ Contains number                                                    │
│  ○ Contains special character (recommended)                           │
└─────────────────────────────────────────────────────────────────────────┘
```

---

## Step 5: AI Tool Integration

### Desktop View - Detecting Tools

```
┌─────────────────────────────────────────────────────────────────────────┐
│  ← Stepper: [1✓] [2✓] [3✓] [4○] [5●] [6○] [7○]                        │
│    (If localhost mode, step 4 is hidden)                                │
│                                                                         │
│  Configure AI Tool Integration                                         │
│  ─────────────────────────────────────────────────────────────────────  │
│                                                                         │
│  ┌───────────────────────────────────────────────────────────────┐    │
│  │ ⟳  Detecting installed AI coding tools...                     │    │
│  │    This may take a few seconds.                                │    │
│  └───────────────────────────────────────────────────────────────┘    │
│                          ↑ Blue info alert with spinner                 │
│                                                                         │
│  ┌───────────────────────────────────────────────────────────────┐    │
│  │  ⟳  Claude Code                                                │    │
│  │     Scanning...                                                │    │
│  │                                                                 │    │
│  └───────────────────────────────────────────────────────────────┘    │
│                                                                         │
│  ┌───────────────────────────────────────────────────────────────┐    │
│  │  ⟳  Cline                                                      │    │
│  │     Scanning...                                                │    │
│  │                                                                 │    │
│  └───────────────────────────────────────────────────────────────┘    │
│                                                                         │
│  ┌───────────────────────────────────────────────────────────────┐    │
│  │  ⟳  Cursor                                                     │    │
│  │     Scanning...                                                │    │
│  │                                                                 │    │
│  └───────────────────────────────────────────────────────────────┘    │
│                                                                         │
│  [← Back]                                          [Continue →]       │
│                                                    (disabled)           │
└─────────────────────────────────────────────────────────────────────────┘
```

### Detection Complete

```
┌─────────────────────────────────────────────────────────────────────────┐
│  Configure AI Tool Integration                                         │
│  ─────────────────────────────────────────────────────────────────────  │
│                                                                         │
│  ┌───────────────────────────────────────────────────────────────┐    │
│  │  ✓  Claude Code                                                │    │
│  │     Version: 1.2.3                                             │    │
│  │     Path: C:\Users\...\AppData\Roaming\Code\...               │    │
│  │                                                                 │    │
│  │                              [Configure]  [Test]               │    │
│  └───────────────────────────────────────────────────────────────┘    │
│                     ↑ Green checkmark, white background                 │
│                                                                         │
│  ┌───────────────────────────────────────────────────────────────┐    │
│  │  ✓  Cline                                                      │    │
│  │     Version: 2.1.0                                             │    │
│  │     Path: C:\Users\...\AppData\Roaming\Code\...               │    │
│  │                                                                 │    │
│  │                              [Configure]  [Test]               │    │
│  └───────────────────────────────────────────────────────────────┘    │
│                                                                         │
│  ┌───────────────────────────────────────────────────────────────┐    │
│  │  ⊗  Cursor                                                     │    │
│  │     Not detected                                               │    │
│  │     Install Cursor or configure manually                       │    │
│  │                                                                 │    │
│  │                         [Manual Setup]  [Skip]                 │    │
│  └───────────────────────────────────────────────────────────────┘    │
│                     ↑ Red X, grayed background                          │
│                                                                         │
│  ┌───────────────────────────────────────────────────────────────┐    │
│  │ ℹ You can configure additional tools later in                  │    │
│  │   Settings > AI Tools                                          │    │
│  └───────────────────────────────────────────────────────────────┘    │
│                                                                         │
│  ┌───────────────────────────────────────────────────────────────┐    │
│  │  Progress: Step 5 of 7                                         │    │
│  │  ▓▓▓▓▓▓▓▓▓▓▓▓░░░░░░░░ 71%                                     │    │
│  └───────────────────────────────────────────────────────────────┘    │
│                                                                         │
│  [← Back]  [Skip This Step]                       [Continue →]       │
│                                                    (disabled initially) │
└─────────────────────────────────────────────────────────────────────────┘
```

### Configuration Dialog

```
┌─────────────────────────────────────────────────────────────────────────┐
│  Configuration Preview: Claude Code                            [X]     │
│  ─────────────────────────────────────────────────────────────────────  │
│                                                                         │
│  ┌───────────────────────────────────────────────────────────────┐    │
│  │ ℹ This configuration will be written to:                      │    │
│  │                                                                 │    │
│  │   C:\Users\YourName\AppData\Roaming\Code\User\                │    │
│  │   globalStorage\saoudrizwan.claude-dev\settings\               │    │
│  │   cline_mcp_settings.json                                      │    │
│  └───────────────────────────────────────────────────────────────┘    │
│                                                                         │
│  ┌───────────────────────────────────────────────────────────────┐    │
│  │ {                                                               │    │
│  │   "mcpServers": {                                               │    │
│  │     "giljo-mcp": {                                              │    │
│  │       "command": "node",                                        │    │
│  │       "args": [                                                 │    │
│  │         "C:/Projects/GiljoAI_MCP/backend/mcp_server.js"        │    │
│  │       ],                                                        │    │
│  │       "env": {                                                  │    │
│  │         "DATABASE_URL": "postgresql://postgres:***@..."        │    │
│  │       }                                                         │    │
│  │     }                                                           │    │
│  │   }                                                             │    │
│  │ }                                                               │    │
│  │                                                                 │    │
│  │                                                                 │    │
│  │                                                                 │    │
│  │                                                                 │    │
│  └───────────────────────────────────────────────────────────────┘    │
│                        ↑ Monospace font, scrollable                     │
│                                                                         │
│  ┌───────────────────────────────────────────────────────────────┐    │
│  │ ⚠ Warning: This will modify your Claude Code configuration    │    │
│  │   file. A backup will be created automatically.                │    │
│  └───────────────────────────────────────────────────────────────┘    │
│                                                                         │
│  [Cancel]                                  [Apply Configuration]      │
└─────────────────────────────────────────────────────────────────────────┘
```

### Configuration Applied Successfully

```
┌─────────────────────────────────────────────────────────────────────────┐
│  Configure AI Tool Integration                                         │
│  ─────────────────────────────────────────────────────────────────────  │
│                                                                         │
│  ┌───────────────────────────────────────────────────────────────┐    │
│  │  ✓  Claude Code                                 [Configured]  │    │
│  │     Version: 1.2.3                                             │    │
│  │     Path: C:\Users\...\AppData\Roaming\Code\...               │    │
│  │                                                                 │    │
│  │                            [Reconfigure]  [Test]               │    │
│  └───────────────────────────────────────────────────────────────┘    │
│                    ↑ Blue "Configured" badge                            │
│                                                                         │
│  ┌───────────────────────────────────────────────────────────────┐    │
│  │ ✓ Configuration applied successfully!                          │    │
│  │   Testing connection to giljo-mcp...                           │    │
│  └───────────────────────────────────────────────────────────────┘    │
│                        ↑ Green success alert                            │
│                                                                         │
│  (... other tools ...)                                                 │
│                                                                         │
│  [← Back]  [Skip This Step]                       [Continue →]       │
│                                                    (enabled)            │
└─────────────────────────────────────────────────────────────────────────┘
```

### Test Connection Success

```
┌─────────────────────────────────────────────────────────────────────────┐
│  ┌───────────────────────────────────────────────────────────────┐    │
│  │  ✓  Claude Code                                 [Configured]  │    │
│  │     Version: 1.2.3                                             │    │
│  │     Path: C:\Users\...\AppData\Roaming\Code\...               │    │
│  │                                                                 │    │
│  │     ┌─────────────────────────────────────────────────────┐   │    │
│  │     │ ✓ Connection successful!                            │   │    │
│  │     │   giljo-mcp is responding correctly.                │   │    │
│  │     │   Claude Code is ready to use.                      │   │    │
│  │     └─────────────────────────────────────────────────────┘   │    │
│  │                            [Reconfigure]  [Test]               │    │
│  └───────────────────────────────────────────────────────────────┘    │
└─────────────────────────────────────────────────────────────────────────┘
```

### Test Connection Failure

```
┌─────────────────────────────────────────────────────────────────────────┐
│  ┌───────────────────────────────────────────────────────────────┐    │
│  │  ✓  Claude Code                                 [Configured]  │    │
│  │     Version: 1.2.3                                             │    │
│  │                                                                 │    │
│  │     ┌─────────────────────────────────────────────────────┐   │    │
│  │     │ ⊗ Connection failed                                  │   │    │
│  │     │   Could not establish connection to giljo-mcp.       │   │    │
│  │     │                                                       │   │    │
│  │     │   Error: Server is not responding                    │   │    │
│  │     │                                                       │   │    │
│  │     │   [View Details]  [Retry]                           │   │    │
│  │     └─────────────────────────────────────────────────────┘   │    │
│  │                            [Reconfigure]  [Test]               │    │
│  └───────────────────────────────────────────────────────────────┘    │
└─────────────────────────────────────────────────────────────────────────┘
```

---

## Step 6: LAN Configuration (Conditional - LAN Mode Only)

### Desktop View

```
┌─────────────────────────────────────────────────────────────────────────┐
│  ← Stepper: [1✓] [2✓] [3✓] [4✓] [5✓] [6●] [7○]                        │
│                                                                         │
│  LAN Network Configuration                                             │
│  ─────────────────────────────────────────────────────────────────────  │
│                                                                         │
│  Your GiljoAI MCP server is now running on:                            │
│  ┌───────────────────────────────────────────────────────────────┐    │
│  │  http://192.168.1.100:7274                                     │    │
│  │                                                                 │    │
│  │                                              [Copy URL]        │    │
│  └───────────────────────────────────────────────────────────────┘    │
│                                                                         │
│  Firewall Configuration                                                │
│  ─────────────────────────────────────────────────────────────────────  │
│                                                                         │
│  Platform detected: Windows 11                                         │
│                                                                         │
│  ┌───────────────────────────────────────────────────────────────┐    │
│  │ ⚠ Port 7274 must be open for team members to access the       │    │
│  │   server over your local network.                              │    │
│  └───────────────────────────────────────────────────────────────┘    │
│                                                                         │
│  Run this command as Administrator:                                    │
│  ┌───────────────────────────────────────────────────────────────┐    │
│  │  netsh advfirewall firewall add rule ^                         │    │
│  │    name="GiljoAI MCP" dir=in action=allow ^                    │    │
│  │    protocol=TCP localport=7274                                 │    │
│  │                                                                 │    │
│  │                                                      [Copy]    │    │
│  └───────────────────────────────────────────────────────────────┘    │
│                         ↑ Monospace font, code block                    │
│                                                                         │
│  Instructions:                                                         │
│  1. Right-click Start menu > Terminal (Admin)                         │
│  2. Paste and run the command above                                   │
│  3. Click "Test Port Access" below to verify                          │
│                                                                         │
│  [Test Port Access]                                                    │
│                                                                         │
│                                                                         │
│  ┌───────────────────────────────────────────────────────────────┐    │
│  │  Progress: Step 6 of 7                                         │    │
│  │  ▓▓▓▓▓▓▓▓▓▓▓▓▓▓▓░░░░░ 86%                                     │    │
│  └───────────────────────────────────────────────────────────────┘    │
│                                                                         │
│  [← Back]                                          [Continue →]       │
│                                                    (disabled)           │
└─────────────────────────────────────────────────────────────────────────┘
```

### Port Test - Testing

```
┌─────────────────────────────────────────────────────────────────────────┐
│  LAN Network Configuration                                             │
│  ─────────────────────────────────────────────────────────────────────  │
│                                                                         │
│  (... server URL and firewall command ...)                             │
│                                                                         │
│  [ ⟳  Testing Port Access...]                                          │
│                                                                         │
│  ┌───────────────────────────────────────────────────────────────┐    │
│  │ ⟳  Testing port 7274 accessibility...                         │    │
│  │    This may take a few seconds.                                │    │
│  └───────────────────────────────────────────────────────────────┘    │
│                                                                         │
│  [← Back]                                          [Continue →]       │
│                                                    (disabled)           │
└─────────────────────────────────────────────────────────────────────────┘
```

### Port Test - Success

```
┌─────────────────────────────────────────────────────────────────────────┐
│  LAN Network Configuration                                             │
│  ─────────────────────────────────────────────────────────────────────  │
│                                                                         │
│  (... server URL and firewall command ...)                             │
│                                                                         │
│  [Test Port Access]                                                    │
│                                                                         │
│  ┌───────────────────────────────────────────────────────────────┐    │
│  │ ✓ Port 7274 is accessible on your network!                    │    │
│  │                                                                 │    │
│  │   Team members can now connect to:                             │    │
│  │   http://192.168.1.100:7274                                    │    │
│  │                                                                 │    │
│  │   Share this URL with your team.                [Copy URL]    │    │
│  └───────────────────────────────────────────────────────────────┘    │
│                          ↑ Green success alert                          │
│                                                                         │
│  [← Back]                                          [Continue →]       │
│                                                    (enabled)            │
└─────────────────────────────────────────────────────────────────────────┘
```

### Port Test - Blocked

```
┌─────────────────────────────────────────────────────────────────────────┐
│  LAN Network Configuration                                             │
│  ─────────────────────────────────────────────────────────────────────  │
│                                                                         │
│  [Test Port Access]                                                    │
│                                                                         │
│  ┌───────────────────────────────────────────────────────────────┐    │
│  │ ⊗ Port 7274 appears to be blocked                             │    │
│  │                                                                 │    │
│  │   The firewall may still be blocking connections.              │    │
│  │                                                                 │    │
│  │   Troubleshooting steps:                                       │    │
│  │   1. Verify you ran the command as Administrator              │    │
│  │   2. Check Windows Firewall settings                          │    │
│  │   3. Restart the GiljoAI MCP server                           │    │
│  │                                                                 │    │
│  │   [View Troubleshooting Guide]  [Retry Test]                  │    │
│  └───────────────────────────────────────────────────────────────┘    │
│                          ↑ Red error alert                              │
│                                                                         │
│  ┌───────────────────────────────────────────────────────────────┐    │
│  │ ℹ You can continue setup and configure the firewall later.    │    │
│  │   [Continue Anyway]                                            │    │
│  └───────────────────────────────────────────────────────────────┘    │
│                                                                         │
│  [← Back]                                          [Continue →]       │
│                                                    (disabled unless     │
│                                                     user clicks         │
│                                                     "Continue Anyway")  │
└─────────────────────────────────────────────────────────────────────────┘
```

---

## Step 7: Complete

### Desktop View

```
┌─────────────────────────────────────────────────────────────────────────┐
│  ← Stepper: [1✓] [2✓] [3✓] [4✓] [5✓] [6✓] [7✓]                        │
│                                                                         │
│  ✓  Setup Complete!                                                    │
│  ─────────────────────────────────────────────────────────────────────  │
│                                                                         │
│     ┌───────────────────────────────────────────────────────────┐     │
│     │                                                             │     │
│     │     🎉  GiljoAI MCP is ready to use!                       │     │
│     │                                                             │     │
│     │     Your configuration summary:                            │     │
│     │                                                             │     │
│     └───────────────────────────────────────────────────────────┘     │
│                                                                         │
│  System Status                                                         │
│  ─────────────────────────────────────────────────────────────────────  │
│                                                                         │
│  ┌───────────────────────────────────────────────────────────────┐    │
│  │  ✓  Database: Connected                                        │    │
│  │     PostgreSQL on localhost:5432                               │    │
│  │     Database: giljo_mcp                                        │    │
│  └───────────────────────────────────────────────────────────────┘    │
│                                                                         │
│  ┌───────────────────────────────────────────────────────────────┐    │
│  │  ✓  Deployment: Localhost                                      │    │
│  │     Single-user mode                                           │    │
│  │     URL: http://localhost:7274                                 │    │
│  └───────────────────────────────────────────────────────────────┘    │
│                                                                         │
│  ┌───────────────────────────────────────────────────────────────┐    │
│  │  ✓  AI Tools: 2 configured                                     │    │
│  │     • Claude Code (connected ✓)                                │    │
│  │     • Cline (connected ✓)                                      │    │
│  └───────────────────────────────────────────────────────────────┘    │
│                                                                         │
│  ┌───────────────────────────────────────────────────────────────┐    │
│  │  ✓  WebSocket: Active                                          │    │
│  │     Real-time updates enabled                                  │    │
│  └───────────────────────────────────────────────────────────────┘    │
│                                                                         │
│  Next Steps                                                            │
│  ─────────────────────────────────────────────────────────────────────  │
│  • Create your first project                                          │
│  • Explore agent templates                                            │
│  • Review documentation                                               │
│                                                                         │
│  ┌───────────────────────────────────────────────────────────────┐    │
│  │  Progress: Complete!                                           │    │
│  │  ▓▓▓▓▓▓▓▓▓▓▓▓▓▓▓▓▓▓▓▓ 100%                                    │    │
│  └───────────────────────────────────────────────────────────────┘    │
│                                                                         │
│                                            [Go to Dashboard →]        │
└─────────────────────────────────────────────────────────────────────────┘
```

### LAN Mode Complete (Alternative)

```
┌─────────────────────────────────────────────────────────────────────────┐
│  ✓  Setup Complete!                                                    │
│  ─────────────────────────────────────────────────────────────────────  │
│                                                                         │
│     🎉  GiljoAI MCP is ready for your team!                            │
│                                                                         │
│  System Status                                                         │
│  ─────────────────────────────────────────────────────────────────────  │
│                                                                         │
│  ┌───────────────────────────────────────────────────────────────┐    │
│  │  ✓  Database: Connected                                        │    │
│  │     PostgreSQL on localhost:5432                               │    │
│  └───────────────────────────────────────────────────────────────┘    │
│                                                                         │
│  ┌───────────────────────────────────────────────────────────────┐    │
│  │  ✓  Deployment: LAN                                            │    │
│  │     Team access enabled                                        │    │
│  │     Admin: admin_user                                          │    │
│  │     Network URL: http://192.168.1.100:7274                     │    │
│  │                                              [Copy URL]        │    │
│  └───────────────────────────────────────────────────────────────┘    │
│                                                                         │
│  ┌───────────────────────────────────────────────────────────────┐    │
│  │  ✓  AI Tools: 2 configured                                     │    │
│  │     • Claude Code (connected ✓)                                │    │
│  │     • Cline (connected ✓)                                      │    │
│  └───────────────────────────────────────────────────────────────┘    │
│                                                                         │
│  ┌───────────────────────────────────────────────────────────────┐    │
│  │  ✓  Firewall: Configured                                       │    │
│  │     Port 7274 is accessible                                    │    │
│  └───────────────────────────────────────────────────────────────┘    │
│                                                                         │
│  ┌───────────────────────────────────────────────────────────────┐    │
│  │  ✓  WebSocket: Active                                          │    │
│  │     Real-time updates enabled                                  │    │
│  └───────────────────────────────────────────────────────────────┘    │
│                                                                         │
│  Next Steps                                                            │
│  ─────────────────────────────────────────────────────────────────────  │
│  • Share http://192.168.1.100:7274 with team members                  │
│  • Create your first project                                          │
│  • Review documentation                                               │
│                                                                         │
│                                            [Go to Dashboard →]        │
└─────────────────────────────────────────────────────────────────────────┘
```

### Mobile View

```
┌─────────────────────────────┐
│ ✓ Setup Complete!           │
│ ─────────────────────────── │
│                             │
│ 🎉 GiljoAI MCP is ready!    │
│                             │
│ System Status               │
│ ─────────────────────────── │
│                             │
│ ┌─────────────────────────┐ │
│ │ ✓ Database              │ │
│ │   PostgreSQL connected  │ │
│ └─────────────────────────┘ │
│                             │
│ ┌─────────────────────────┐ │
│ │ ✓ Deployment            │ │
│ │   Localhost mode        │ │
│ └─────────────────────────┘ │
│                             │
│ ┌─────────────────────────┐ │
│ │ ✓ AI Tools: 2           │ │
│ │   • Claude Code ✓       │ │
│ │   • Cline ✓             │ │
│ └─────────────────────────┘ │
│                             │
│ ┌─────────────────────────┐ │
│ │ ✓ WebSocket Active      │ │
│ └─────────────────────────┘ │
│                             │
│ Next Steps                  │
│ • Create first project      │
│ • Explore templates         │
│ • Review docs               │
│                             │
│ ┌─────────────────────────┐ │
│ │ Complete! 100%          │ │
│ │ ▓▓▓▓▓▓▓▓▓▓▓▓▓▓▓▓▓▓▓▓   │ │
│ └─────────────────────────┘ │
│                             │
│   [Go to Dashboard →]      │
│                             │
└─────────────────────────────┘
```

---

## Vuetify Stepper Component

### Desktop Stepper (Horizontal)

```
┌─────────────────────────────────────────────────────────────────────────┐
│                                                                         │
│  [1✓]───[2✓]───[3●]───[4○]───[5○]───[6○]───[7○]                       │
│   │      │      │      │      │      │      │                          │
│ Welcome DB   Mode  Admin  Tools  LAN  Done                             │
│         Connection                                                      │
│                                                                         │
│  ✓ = Completed (green)                                                 │
│  ● = Current (yellow, bold)                                            │
│  ○ = Not started (gray)                                                │
│                                                                         │
└─────────────────────────────────────────────────────────────────────────┘
```

### Conditional Steps Display

**Localhost Mode (Steps 4 & 6 hidden):**
```
[1✓]───[2✓]───[3✓]───[5●]───[7○]
  │      │      │      │      │
Welcome  DB   Mode  Tools  Done
```

**LAN Mode (All steps shown):**
```
[1✓]───[2✓]───[3✓]───[4●]───[5○]───[6○]───[7○]
  │      │      │      │      │      │      │
Welcome  DB   Mode  Admin Tools  LAN  Done
```

### Mobile Stepper (Vertical)

```
┌─────────────────────────┐
│                         │
│  1✓ Welcome             │
│  │                      │
│  2✓ Database            │
│  │                      │
│  3● Deployment Mode     │
│  │                      │
│  4○ AI Tools            │
│  │                      │
│  5○ Complete            │
│                         │
└─────────────────────────┘
```

---

## Progress Bar States

### Step 1 (14%)
```
▓▓░░░░░░░░░░░░░░░░░░░░░░░░░░ 14%
```

### Step 2 (29%)
```
▓▓▓▓▓▓▓░░░░░░░░░░░░░░░░░░░░░ 29%
```

### Step 3 (43%)
```
▓▓▓▓▓▓▓▓▓▓▓░░░░░░░░░░░░░░░░░ 43%
```

### Step 4 (57%)
```
▓▓▓▓▓▓▓▓▓▓▓▓▓▓▓░░░░░░░░░░░░░ 57%
```

### Step 5 (71%)
```
▓▓▓▓▓▓▓▓▓▓▓▓▓▓▓▓▓▓░░░░░░░░░░ 71%
```

### Step 6 (86%)
```
▓▓▓▓▓▓▓▓▓▓▓▓▓▓▓▓▓▓▓▓▓▓░░░░░░ 86%
```

### Step 7 (100%)
```
▓▓▓▓▓▓▓▓▓▓▓▓▓▓▓▓▓▓▓▓▓▓▓▓▓▓▓▓ 100%
```

---

## Footer Navigation Pattern

### Desktop
```
┌─────────────────────────────────────────────────────────────────────────┐
│                                                                         │
│  [← Back]                                          [Continue →]       │
│  (secondary btn)                                   (primary btn)        │
│                                                                         │
└─────────────────────────────────────────────────────────────────────────┘
```

### Mobile (Stacked)
```
┌─────────────────────────────┐
│                             │
│    [Continue →]            │
│    (primary, full-width)    │
│                             │
│    [← Back]                │
│    (secondary, full-width)  │
│                             │
└─────────────────────────────┘
```

---

**Document Status**: Complete
**Next Document**: `component_hierarchy.md`
