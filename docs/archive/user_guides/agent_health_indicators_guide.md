# Agent Health Indicators - User Guide

**Feature**: Real-time agent health monitoring with visual indicators
**Version**: 3.1+ (Handover 0106)
**Status**: Production

---

## What You'll See

Agent health indicators appear on agent cards **only when there's a problem**. When agents are working normally, no health indicator is shown - keeping your UI clean and uncluttered.

---

## Health States

### 🟢 Healthy (No Indicator)

**What it means**: Agent is working normally

**Visual**: No health indicator shown

**Your action**: None needed - everything is good!

---

### 🟡 Warning - Slow Response

**What it means**: Agent hasn't reported progress for 5-7 minutes

**Visual**:
```
┌─────────────────────────────┐
│ Progress: 45% ████████░░░░  │
│                             │
│ 🟡 Slow response (6.2 min) │  ← Yellow chip
│                             │
│ Current: Writing tests...   │
└─────────────────────────────┘
```

**Details** (hover to see):
- Exact minutes since last update
- Issue description: "No activity for 6.2 minutes"

**Your action**:
- Informational only - no action required yet
- Agent may be working on a complex task
- Monitor for a few more minutes

---

### 🔴 Critical - Not Responding

**What it means**: Agent hasn't reported progress for 7-10 minutes

**Visual**:
```
┌─────────────────────────────┐
│ Progress: 45% ████████░░░░  │
│                             │
│ 🔴 Not responding (8.5 min) │  ← Red chip with pulse
│                             │
│ Current: Writing tests...   │
└─────────────────────────────┘
```

**Details** (hover to see):
- Exact minutes since last update
- Issue description: "Agent silent for 8.5 minutes"
- Recommended action: "Check agent logs, may need manual restart"

**Notifications**:
- 🔔 Toast notification appears in top-right corner
- Stays visible for 8 seconds

**Your action**:
1. Check agent details (click "Details" button)
2. Review agent logs for errors
3. Consider manual restart if problem persists
4. Check your IDE/CLI - agent may be waiting for input

---

### ⚫ Timeout - Timed Out

**What it means**: Agent hasn't reported progress for over 10 minutes (auto-failed)

**Visual**:
```
┌─────────────────────────────┐
│ Progress: 45% ████████░░░░  │
│                             │
│ ⚫ Timed out (12.3 min)     │  ← Grey chip
│                             │
│ Current: Writing tests...   │
└─────────────────────────────┘
```

**Details** (hover to see):
- Exact minutes since last update
- Issue description: "No response for 12.3 minutes"
- Recommended action: "May need restart - manual intervention required"

**Notifications**:
- 🔔 Error notification appears in top-right corner
- Stays visible for 10 seconds
- Agent automatically marked as failed by system

**Your action**:
1. Agent has been auto-failed - manual intervention required
2. Review error logs (click "View Error" button)
3. Identify root cause
4. Restart agent or resolve blocking issue
5. May need to check your development environment

---

## Auto-Recovery

**Good news**: When an agent resumes work, the health indicator **automatically disappears**.

**How it works**:
1. Agent reports progress update
2. Health alert is cleared instantly
3. Health indicator vanishes from card
4. No manual action needed

**Example**: If an agent was showing "Critical" (red chip) but then reports 50% progress, the red chip immediately disappears and the card returns to normal.

---

## Accessibility Features

### Keyboard Navigation
- Press **Tab** to navigate to health chip
- Health chip receives visible focus ring
- Tooltip appears on focus (not just hover)

### Screen Readers
- Health state announced when card is focused
- Full description available via ARIA labels
- Tooltip content accessible to assistive technologies

### Colorblind Support
- Information conveyed through **icon + color** combination
- Not relying on color alone
- Distinct icons for each state:
  - Warning: Clock with exclamation (mdi-clock-alert)
  - Critical: Circle with exclamation (mdi-alert-circle)
  - Timeout: Clock with X (mdi-clock-remove)

---

## Common Questions

### Q: Why don't I see health indicators on all my agents?
**A**: Health indicators only appear when there's a problem. If all your agents are healthy, you won't see any indicators - that's by design to keep your UI clean.

### Q: What triggers a health alert?
**A**: The system monitors agent progress updates. If an agent doesn't report progress within the configured thresholds (5/7/10 minutes), health alerts are triggered automatically.

### Q: Can I customize the timeout thresholds?
**A**: Currently, thresholds are system-wide configuration. Future versions may support per-agent or per-project customization.

### Q: Will I lose work if an agent times out?
**A**: No - agent work is preserved. The timeout only marks the agent as failed. You can review the error, address the issue, and restart the agent.

### Q: Why did my agent show "Critical" but then recover on its own?
**A**: The agent may have been working on a complex task that took longer than usual. Once it completed that task and reported progress, it automatically recovered.

### Q: Do health alerts appear in the notification bell?
**A**: Yes - Critical and Timeout alerts are sent to the notification bell. Warning states are not (to avoid notification fatigue).

---

## Tips for Using Health Indicators

### 1. Don't Panic on Warning
Yellow "Slow response" warnings are informational. Agents often take 5-7 minutes on complex tasks. Wait a few more minutes before taking action.

### 2. Investigate Critical States
Red "Not responding" alerts deserve attention. Check:
- Agent logs in the details panel
- Your IDE/CLI for prompts or errors
- System resources (CPU, memory)

### 3. Restart Timed Out Agents
Grey "Timed out" states indicate auto-failure. These require manual restart:
1. Review error details
2. Fix underlying issue
3. Restart the agent

### 4. Watch for Patterns
If specific agent types consistently hit health alerts:
- May indicate resource constraints
- Could signal code complexity issues
- Might need different agent configuration

### 5. Use Tooltips
Hover (or focus) on health chips to see:
- Exact minutes since last update
- Detailed issue description
- Recommended next action

---

## Technical Details

### Health Check Intervals
- System scans agent health every **30 seconds** (default)
- Configurable in backend settings

### Thresholds
- **Warning**: 5-7 minutes without progress
- **Critical**: 7-10 minutes without progress
- **Timeout**: >10 minutes without progress (auto-fail)

### What Counts as "Progress"
- Status updates (e.g., "waiting" → "working")
- Progress percentage changes
- Task updates
- Message sending
- Any interaction with the orchestrator

### What Doesn't Count
- Page refreshes
- UI navigation
- Viewing agent details
- These are frontend actions - agents report progress from backend

---

## Troubleshooting

### Health indicator stuck on screen
**Symptom**: Health chip shows even though agent is working
**Fix**: Refresh the page - this resyncs WebSocket connection

### No health indicators when agent is clearly stalled
**Symptom**: Agent not working but no health indicator
**Fix**:
1. Check WebSocket connection (should show "connected" in footer)
2. Verify health monitoring is enabled in backend
3. Check system logs for monitoring errors

### Health indicators appear then disappear quickly
**Symptom**: Flashing health chips
**Fix**: This is normal if agents are intermittently slow. If persistent:
1. Check agent resource usage
2. Review agent logs for warnings
3. Consider allocating more resources

---

## Related Features

- **Agent Jobs Tab**: View all active agents with health status
- **Agent Details Panel**: Deep dive into specific agent behavior
- **Notification Bell**: Receive critical health alerts
- **Orchestrator Succession**: Manage context limits for long-running projects

---

## Need Help?

- **Documentation**: See `handovers/0106_health_monitoring_ui_integration.md`
- **Backend Configuration**: See `handovers/0107_agent_monitoring_and_graceful_cancellation.md`
- **Support**: Check logs in `logs/` directory for health monitoring events

---

**Last Updated**: 2025-11-06
**Related Handovers**: 0106, 0107
**Feature Stability**: Production (v3.1+)
