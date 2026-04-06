# Dashboard User Guide

Complete guide to using the GiljoAI Dashboard status board table and agent management features.

---

## Overview

The GiljoAI Dashboard provides agent orchestration and monitoring capabilities through a modern status board interface. This guide covers the status board table components and agent interaction workflows.

**Key Features**:
- Real-time agent status monitoring with health indicators
- Interactive action buttons for agent control
- Message tracking and communication
- Mission read/acknowledged indicators
- Staleness detection for inactive agents

---

## Status Board Table

The status board table displays all agents for the current project with real-time updates via WebSocket.

### Table Columns

1. **Agent Type**
   - Colored avatar with agent initials
   - Agent role name (Orchestrator, Implementer, Tester, etc.)

2. **Agent ID**
   - 8-character UUID identifier (truncated)
   - Monospace font for readability
   - Full ID available on hover

3. **Status**
   - Status chip with icon and label
   - Health indicator overlay (warning/critical with pulse animation)
   - Staleness warning icon (clock-alert) if no activity >10 minutes
   - Tooltip shows health status and last activity time

4. **Job Read**
   - Green checkmark if orchestrator has read the job
   - Grey dash if not yet read
   - Tooltip shows timestamp

5. **Job Acknowledged**
   - Green checkmark if agent has acknowledged the job
   - Grey dash if not yet acknowledged
   - Tooltip shows timestamp

6. **Messages Sent**
   - Total messages sent by agent
   - Numeric count

7. **Messages Waiting**
   - Messages waiting for user response
   - Yellow text if > 0

8. **Messages Read**
   - Messages read by user
   - Numeric count

9. **Actions**
   - Action buttons for agent interactions
   - See "Interacting with Agents" section below

---

## Agent Status Indicators

### Status Types

The status chip displays the current agent state:

- **Waiting** (🕒 grey) - Agent waiting to start
- **Working** (⚙️ blue) - Agent actively processing
- **Blocked** (⚠️ orange) - Agent blocked waiting for input
- **Complete** (✅ yellow) - Agent completed successfully
- **Failed** (❌ purple) - Agent encountered an error
- **Cancelled** (⛔ warning) - Agent was cancelled by user
- **Decommissioned** (📦 grey) - Agent has been decommissioned

### Health Indicators

Small dot overlay on status chip indicates agent health:

- **No indicator** - Healthy (green dot not shown)
- **Yellow dot** - Warning (health check failures)
- **Red dot (pulsing)** - Critical (multiple health check failures)
- **Grey dot** - Timeout

Hover over the status chip to see:
- Health status label
- Last activity timestamp
- Minutes since last progress (if stale)

### Staleness Detection

Agents show a clock-alert icon if:
- No activity for >10 minutes
- Agent not in terminal state (complete/failed/cancelled)

Hover over the icon to see last activity time.

---

## Interacting with Agents

### Available Actions

The Actions column provides up to 5 action buttons:

#### 1. Launch (▶️)
- **When available**: Agent in "waiting" status
- **Claude Code CLI mode**: Only orchestrator shows launch button
- **Action**: Launches the agent to begin work
- **Icon**: Rocket launch (blue)

#### 2. Copy Prompt (📋)
- **When available**: All agents except decommissioned
- **Action**: Copies agent prompt to clipboard
- **Icon**: Content copy (grey)
- **Feedback**: Green snackbar "Prompt copied to clipboard!"

#### 3. View Messages (💬)
- **When available**: All agents
- **Badge**: Red badge shows unread message count
- **Action**: Opens message history modal
- **Icon**: Message text (blue)

#### 4. Cancel (✖️)
- **When available**: Agent in working/waiting/blocked status
- **Action**: Cancels the running agent
- **Confirmation**: Requires confirmation dialog
- **Icon**: Cancel (red)

#### 5. Hand Over (🖐️)
- **When available**: Orchestrator only, at 90% context usage
- **Action**: Triggers orchestrator succession and context handover
- **Confirmation**: Requires confirmation dialog
- **Icon**: Hand left (warning/yellow)

### Action Workflows

**Launching an Agent**:
1. Find agent with "waiting" status in table
2. Click launch button (▶️)
3. Agent status changes to "working"
4. Monitor progress via status chip

**Copying Agent Prompt**:
1. Click copy button (📋) on any agent row
2. Wait for green success snackbar
3. Paste into Claude Code CLI or CCW

**Cancelling an Agent**:
1. Click cancel button (✖️) on working/waiting/blocked agent
2. Confirmation dialog appears with warning
3. Click "Confirm" to cancel agent
4. Agent status changes to "cancelled"

**Triggering Orchestrator Handover**:
1. Wait until orchestrator reaches 90% context usage
2. Hand over button (🖐️) appears
3. Click button and confirm in dialog
4. New orchestrator instance created with context transfer

---

## Mission Tracking

### Job Read Indicator

Shows when the orchestrator first fetches the agent's mission:

- **Green checkmark** - Mission has been read (shows timestamp on hover)
- **Grey dash** - Mission not yet read

Set automatically when `get_orchestrator_instructions()` MCP tool is called.

### Job Acknowledged Indicator

Shows when the agent acknowledges the mission and begins work:

- **Green checkmark** - Agent has acknowledged (shows timestamp on hover)
- **Grey dash** - Not yet acknowledged

Set automatically when agent status transitions to "working" for the first time.

---

## Real-Time Updates

The status board table uses WebSocket connections for real-time updates:

**What Updates in Real-Time**:
- Agent status changes (waiting → working → complete)
- Health status changes (healthy → warning → critical)
- Message counts (sent/waiting/read)
- Mission read/acknowledged timestamps
- Context usage for orchestrator

**No Page Refresh Needed** - All updates appear automatically.

---

## Claude Code CLI Mode

Toggle switch above the table controls agent launch behavior:

**Enabled** (Claude Code Subagents):
- Only orchestrator can be launched manually
- Other agents launched automatically by orchestrator
- Launch buttons hidden for non-orchestrator agents
- Copy prompt buttons remain available for all agents

**Disabled** (General CLI mode):
- All agents can be launched manually
- Launch buttons visible for all waiting agents
- User has full control over agent execution

---

## Keyboard Shortcuts

- **Ctrl+Enter** - Send message (when message composer focused)
- **Escape** - Close modal dialogs

---

## Tips & Tricks

### Status Board Best Practices

- **Watch health indicators** - Yellow/red dots indicate agent issues
- **Check staleness warnings** - Clock icon means agent may be stuck
- **Use copy prompt** - Easier than manually typing agent prompts
- **Monitor context usage** - Hand over button appears at 90% for orchestrator

### Performance Tips

- **WebSocket connection** - Ensure browser DevTools shows active WS connection
- **Real-time updates** - If table isn't updating, check Network → WS tab in DevTools
- **Table sorting** - Click column headers to sort by status, agent type, etc.

---

## Troubleshooting

### Status Board Issues

**Problem**: Status board table not appearing
- **Solution**: Verify project has agents, check backend logs for errors

**Problem**: Real-time updates not working
- **Solution**: Check WebSocket connection in DevTools → Network → WS tab
- **Solution**: Verify backend server running at http://10.1.0.164:7274

**Problem**: Action buttons disabled
- **Solution**: Check agent status (launch only works for waiting agents)
- **Solution**: Cancel only works for working/waiting/blocked agents
- **Solution**: Hand over only appears for orchestrator at 90% context

### Health Indicator Issues

**Problem**: Agent shows critical health (red pulsing dot)
- **Solution**: Check agent logs for errors
- **Solution**: Consider cancelling and relaunching agent
- **Solution**: Verify backend health check endpoints responding

**Problem**: Staleness warning won't go away
- **Solution**: Agent may be genuinely stuck - check logs
- **Solution**: Cancel agent and relaunch if needed
- **Solution**: Staleness clears automatically when agent resumes activity

---

## Related Documentation

- [Architecture Overview](../SERVER_ARCHITECTURE_TECH_STACK.md)
- [StatusBoard Component API](../components/status_board_components.md)
- [Agent Jobs API Reference](../AGENT_JOBS_API_REFERENCE.md)
- [WebSocket Events Documentation](../api/websocket_events.md)
