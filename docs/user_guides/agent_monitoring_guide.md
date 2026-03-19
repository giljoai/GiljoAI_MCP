# Agent Monitoring & Graceful Cancellation - User Guide

**Version**: 3.1.1
**Date**: 2025-11-06
**Last Updated**: 2025-01-05 (Harmonized)
**Handover**: 0107
**Harmonization Status**: ✅ Aligned with codebase

---

## Quick Links to Harmonized Documents

- **[Simple_Vision.md](../../handovers/Simple_Vision.md)** - Complete user journey with agent coordination
- **[start_to_finish_agent_FLOW.md](../../handovers/start_to_finish_agent_FLOW.md)** - Technical agent flow

**Supported AI Tools**:
- Claude Code, Codex CLI, Gemini CLI (all with native MCP support)

---

GiljoAI MCP provides comprehensive agent monitoring and graceful cancellation capabilities for agents running in external terminals (Claude Code, Codex CLI, Gemini CLI). This guide explains how to monitor agent health, interpret status indicators, and gracefully cancel agents when needed.

## Key Features

- **Passive Health Monitoring**: Automatic detection of unresponsive agents
- **Graceful Cancellation**: Request agents stop work cleanly
- **Real-Time Status**: Live updates on agent activity and progress
- **Force Stop**: Manual intervention when agents become unresponsive

---

## Understanding Agent IDs vs Job IDs

GiljoAI MCP uses a **dual-model architecture** that separates persistent work orders from individual agent execution instances. This enables **orchestrator succession**, where one agent can hand off work to another while preserving context and mission continuity.

### Key Concepts

| **Concept** | **What It Represents** | **Persistence** | **Example** |
|------------|------------------------|-----------------|-------------|
| **Agent Job** | Logical unit of work with defined mission and objectives | Persists across agent succession | "Refactor Backend" (job_12345) |
| **Agent Execution** | Single agent instance working on a job | Created fresh for each agent | Agent A (agent_a1b2c3d4) → Agent B (agent_e5f6g7h8) |

### Agent Job (The WHAT)

An **Agent Job** represents the **work order** that needs to be done. It contains:

- **Mission**: The instructions and objectives for the work
- **Job Type**: orchestrator, implementer, tester, etc.
- **Status**: active, completed, cancelled
- **Project**: Which project this job belongs to

**Key Point**: The job persists even when agents change. If Agent A hands over to Agent B, the same job continues with a new executor.

### Agent Execution (The WHO)

An **Agent Execution** represents a **specific agent instance** working on a job. It contains:

- **Agent ID**: Unique identifier for this executor (agent_a1b2c3d4)
- **Status**: waiting, working, blocked, complete, failed, cancelled
- **Succession Chain**: Links to previous/next agents (spawned_by, succeeded_by)

**Key Point**: Each time an agent hands over work, a new execution is created while the job remains the same.

### When Do Agents Succeed Each Other?

Orchestrator agents trigger succession via user action in these scenarios:

1. **High Context Usage**: When an orchestrator's context window is high (e.g., 135K/150K tokens or 90%), the user can trigger succession manually to prevent context issues.

2. **Manual Handover**: User triggers succession via:
   - `/gil_handover` slash command in CLI
   - "Hand Over" button in dashboard UI

3. **Phase Transition**: Users may choose to hand off when transitioning between major phases (e.g., planning → implementation).

**Typical Timeline**: Succession takes 2-5 minutes (handover summary generation, new agent spawn, context transfer).

### Viewing Succession Timeline

The dashboard displays the full succession history for each job, showing how work progressed through different agent instances:

```
Job: "Refactor Backend Services" (job_12345abc)
├─ Agent A (agent_a1b2c3d4) - Instance #1 - Complete
│  Agent Type: orchestrator
│  Context: 135K/150K used (90% - triggered succession)
│  Reason: "Approaching context limit"
│  Duration: 90 minutes
│  Started: 2025-12-20 10:00 AM
│  Completed: 2025-12-20 11:30 AM
│
└─ Agent B (agent_e5f6g7h8) - Instance #2 - Active
   Agent Type: orchestrator
   Context: 35K/150K used (23%)
   Started: 2025-12-20 11:32 AM
   Duration: 30 minutes (ongoing)
```

**Navigation**: Go to Projects → Jobs Tab → Click job row → View "Execution History" panel

---

## Understanding Agent Health Indicators

### Health Status Colors

Agents display health indicators based on their recent activity:

| **Status** | **Color** | **Meaning** | **Action Needed** |
|-----------|----------|-------------|-------------------|
| **Active** | Green | Agent checking in regularly (<10 min) | None - agent is healthy |
| **Stale** | Orange/Warning | No check-in for 10+ minutes | Monitor - agent may be stuck |
| **Cancelling** | Yellow | Cancel request sent | Wait for agent to stop (usually <5 min) |
| **Inactive** | Grey | Agent not currently working | None - normal state |

### Last Activity Timestamp

Each agent card shows "last update" time:
- **"2m ago"**: Agent is actively working
- **"15m ago"**: Agent may be stuck on a long task or unresponsive

---

## How Agents Report Progress

Agents follow a **contextual check-in protocol**:

### When Agents Check In

✅ After completing a todo item
✅ After finishing a major phase/operation
✅ Before starting a long-running task (>5 minutes)
✅ When waiting for user input

❌ **NOT** on a fixed timer (every 2 minutes)

### Why Contextual Check-Ins?

- More natural workflow breaks
- More responsive (agents may check in <2 min)
- Aligns with how agents actually work
- Most tasks complete in <5 minutes

---

## Cancelling Agents Gracefully

### When to Cancel an Agent

- Agent is working on the wrong task
- You need to stop the project temporarily
- Agent is taking too long on a task
- You want to reassign work to a different agent

### How to Cancel an Agent

1. **Locate the agent card** in the dashboard
2. **Click "Cancel Job" button** (yellow warning button)
3. **Confirm cancellation** in the dialog
4. **Wait for graceful stop** (usually <5 minutes)

### What Happens During Cancellation

1. **Status changes to "cancelling"** (yellow indicator)
2. **Cancel message queued** for the agent
3. **Agent receives message** on next check-in
4. **Agent stops work cleanly** (saves progress, cleans up)
5. **Job marked as complete** with "cancelled" status

**Typical Timeline**: 30 seconds to 5 minutes (depends on task completion)

---

## When to Use Force Stop

### Normal Cancellation First

Always try graceful cancellation first. It allows the agent to:
- Save current progress
- Clean up temporary files
- Report partial results
- Close connections properly

### Force Stop Scenarios

Use force stop **ONLY** when:
- Agent hasn't responded to cancel request for 5+ minutes
- Agent appears completely unresponsive
- Cancel status shows for 10+ minutes with no change

### How to Force Stop

1. **Wait for "Force Stop" button** to appear (after 5+ min in cancelling state)
2. **Click "Force Stop" button** (red error button)
3. **Confirm force stop** in the warning dialog
4. **Job immediately marked as failed**

**Warning**: Force stop does NOT actually terminate the external terminal. You must manually close the Claude Code/Codex/Gemini terminal window.

---

## Interpreting Stale Warnings

### What is a Stale Agent?

An agent that hasn't checked in for **10+ minutes**.

### Stale Warning Appearance

```
⚠️ No update for 15m - Agent may be stuck
```

- Orange alert banner on agent card
- "15m ago" timestamp
- Warning icon

### Why Agents Go Stale

**Legitimate Reasons**:
- Working on a long-running task (database migration, large test suite)
- Performing deep analysis (reviewing 100+ files)
- Waiting for external process (build, deployment)

**Problem Scenarios**:
- Agent crashed or terminal closed
- Agent encountered an error and stopped
- Network connectivity issue
- Agent stuck in infinite loop

### How to Respond to Stale Warnings

1. **Check agent terminal** (if accessible) - is it still running?
2. **Wait 5 more minutes** - task may complete soon
3. **Request cancellation** if agent appears stuck
4. **Force stop** if no response after 5+ minutes

---

## Best Practices

### Monitoring Active Projects

- **Check dashboard regularly** during active work
- **Watch for stale warnings** on long-running tasks
- **Verify check-in frequency** matches expected task duration

### Cancelling Work

- **Use graceful cancel first** - always preferred
- **Allow 5 minutes** for agent to respond
- **Force stop only as last resort**
- **Close terminal manually** after force stop

### Avoiding Stale Agents

- **Break down large tasks** into smaller milestones
- **Monitor long-running operations** proactively
- **Test agent templates** before production use
- **Ensure stable network connection** for agents

---

## Frequently Asked Questions

### Q: What's the difference between agent_id and job_id?

**A**:
- **job_id**: Identifies the **work order** (the mission, objectives, and scope). This persists across agent succession.
- **agent_id**: Identifies a **specific agent instance** working on that job. Changes when agents succeed each other.

**Example**: Job "Refactor Backend" (job_12345) may have Agent A (agent_a1b2) complete 90% of work, then hand over to Agent B (agent_e5f6) who finishes the remaining 10%. Same job, different agents.

### Q: Can I see which agent is currently working on a job?

**A**: Yes. In the dashboard Jobs Tab:
1. Look at the **Agent ID** column - shows the current executor
2. Click the job row to see the **Execution History** panel
3. The most recent execution with status "working" is the current agent
4. Previous executions show the succession chain (who worked before, why they handed over)

**WebSocket Events**: Real-time updates via `execution:created` and `execution:status_changed` events keep the UI synchronized.

### Q: Why doesn't force stop actually kill the agent process?

**A**: Agents run in external terminals (Claude Code, Codex, Gemini) outside GiljoAI MCP's control. Force stop updates the database status but cannot terminate the external process. You must manually close the terminal.

### Q: What if an agent never checks in?

**A**: Agent may have failed to acknowledge the job. Check:
1. Agent terminal is running
2. MCP connection is active (health check)
3. Agent credentials are correct
4. No errors in agent terminal

### Q: Can I cancel multiple agents at once?

**A**: No, cancellation is per-agent. Each agent must receive its own cancel message and respond individually.

### Q: What happens to partial work when cancelled?

**A**: Depends on agent implementation. Well-designed agents report partial results in the cancellation response, including files modified and work completed before stopping.

### Q: How do I know if a cancel request was successful?

**A**: Agent status changes to "completed" (or "failed" if force stopped). The agent card moves to the appropriate column in the Kanban view.

---

## Troubleshooting

### Agent Stuck in "Cancelling" State

**Symptoms**: Status shows "cancelling" for 10+ minutes

**Solutions**:
1. Check agent terminal - is it frozen?
2. Use force stop button
3. Manually close terminal
4. Verify database status updated

### Stale Warnings Don't Appear

**Symptoms**: Agent unresponsive but no warning

**Possible Causes**:
- Background monitor not running
- Agent never checked in (no baseline timestamp)
- Less than 10 minutes since last check-in

**Solutions**:
- Check system logs for monitor task
- Verify agent acknowledged job successfully
- Wait for 10-minute threshold

### Agent Continues Working After Cancel

**Symptoms**: Agent terminal shows activity after cancellation

**Explanation**: Agent hasn't checked for messages yet. Wait for next check-in (usually <5 min).

**If Persistent**:
- Agent may have a bug in message checking
- Manually close terminal
- Report issue to agent template developer

---

## Technical Details

### Background Monitoring

- **Runs every 5 minutes** in background task
- **Checks `last_progress_at` timestamps**
- **Broadcasts stale warnings** via WebSocket
- **Does NOT auto-fail agents** (user decides)

### Database Fields

#### AgentJob Table (Persistent Work Orders)

- **`job_id`**: Unique identifier for the work order (e.g., "job_12345abc")
- **`mission`**: Agent mission/instructions (stored once, shared by all executions)
- **`job_type`**: Job type (orchestrator, implementer, tester, etc.)
- **`status`**: Job status (active, completed, cancelled)
- **`project_id`**: Project this job belongs to
- **`template_id`**: Template used to create this job (optional)
- **`created_at`**: When job was created
- **`completed_at`**: When job finished (all executions complete)

#### AgentExecution Table (Individual Agent Instances)

- **`agent_id`**: Unique identifier for this agent instance (e.g., "agent_a1b2c3d4")
- **`job_id`**: Foreign key to parent AgentJob
- **`agent_type`**: Agent type for this executor
- **`status`**: Execution status (waiting, working, blocked, complete, failed, cancelled, decommissioned)
- **`spawned_by`**: Agent ID of parent executor (succession chain)
- **`succeeded_by`**: Agent ID of successor executor (succession chain)
- **`progress`**: Execution completion progress (0-100%)
- **`current_task`**: Description of current task
- **`succession_reason`**: Why succession occurred (context_limit, manual, phase_transition)
- **`handover_summary`**: Compressed state transfer for successor
- **`last_progress_at`**: Timestamp of most recent progress report
- **`last_message_check_at`**: Timestamp of most recent message check
- **`mission_acknowledged_at`**: When agent first fetched mission
- **`started_at`**: When this execution started
- **`completed_at`**: When this execution finished
- **`decommissioned_at`**: When this execution was retired (after succession)

### WebSocket Events

- **`job:progress_update`**: Agent reported progress
- **`job:stale_warning`**: Agent detected as stale (10+ min)
- **`job:status_changed`**: Status changed (including to "cancelling")
- **`job:completed`**: Job finished (including cancelled jobs)

---

## Related Documentation

- **Developer Guide**: [docs/developer_guides/agent_monitoring_developer_guide.md](../developer_guides/agent_monitoring_developer_guide.md)
- **Handover Document**: [handovers/completed/0107_agent_monitoring_and_graceful_cancellation-C.md](../../handovers/completed/0107_agent_monitoring_and_graceful_cancellation-C.md)
- **Agent Template System**: [docs/guides/agent_template_management.md](../guides/agent_template_management.md)

---

## Support

For issues or questions:
1. Check agent terminal logs for errors
2. Review system logs in `logs/` directory
3. Consult developer guide for implementation details
4. Report persistent issues with agent template details
