# Orchestrator Succession - User Guide

> **ARCHIVED (Handover 0461e)**: This documentation describes the old complex
> succession system which has been replaced by simple 360 Memory-based handover.
> See [ORCHESTRATOR.md](../ORCHESTRATOR.md) for current documentation.

**Last Updated**: 2025-11-02
**Version**: v3.0+
**Applies To**: GiljoAI MCP Coding Orchestrator with Handover 0080

## Table of Contents

1. [What is Orchestrator Succession?](#what-is-orchestrator-succession)
2. [Why Does It Matter?](#why-does-it-matter)
3. [How to Recognize Succession Events](#how-to-recognize-succession-events)
4. [Launching a Successor Orchestrator](#launching-a-successor-orchestrator)
5. [Viewing Succession History](#viewing-succession-history)
6. [Troubleshooting](#troubleshooting)
7. [FAQ](#faq)

---

## What is Orchestrator Succession?

Orchestrator succession is an automatic handover system that allows your AI projects to continue indefinitely without interruption.

Think of it like a relay race: when one orchestrator agent approaches the limit of what it can remember (its "context window"), it automatically creates a successor orchestrator and hands off the project with a comprehensive summary.

**Key Concept**: AI agents have a limited "memory" or "context window" (typically 150,000 tokens, roughly 100,000 words). In large projects, this limit could be reached, causing the orchestrator to fail. Succession solves this by creating a fresh orchestrator before that happens.

## Why Does It Matter?

### Benefits for Your Projects

1. **Unlimited Project Duration**
   - Projects can continue indefinitely without context limitations
   - No more "orchestrator ran out of memory" failures
   - Long-running projects (months, years) are now possible

2. **Graceful Context Management**
   - Manual handover when context is high (user-triggered via UI or slash command)
   - Compressed handover summaries (under 10,000 tokens)
   - No loss of project state or continuity

3. **Full Transparency**
   - See the complete succession chain in the dashboard
   - Review handover summaries between instances
   - Track which orchestrator instance is handling your project

4. **Cost Efficiency**
   - Fresh context windows reduce token waste
   - context prioritization and orchestration compared to replaying full context
   - Intelligent compression keeps only critical state

## How to Recognize Succession Events

### Visual Indicators in the Dashboard

When you open your project's Jobs tab, you'll see orchestrator cards with several succession indicators:

#### 1. Instance Number Badges

Each orchestrator card shows its instance number:
- **#1** - First orchestrator (original)
- **#2** - Second orchestrator (first successor)
- **#3** - Third orchestrator (second successor)
- And so on...

#### 2. Context Usage Progress Bars

Color-coded bars show how much of the context window is used:
- **Green (0-75%)** - Healthy, plenty of context remaining
- **Yellow (75-90%)** - Approaching threshold, succession may be planned
- **Red (90-100%)** - Succession threshold reached, handover imminent

#### 3. Status Badges

- **NEW** - Green badge on successor orchestrators waiting to be launched
- **Handed Over** - Grey badge on completed orchestrators that transferred control
- **Working** - Blue badge on the currently active orchestrator

#### 4. Visual Linkage

Arrows or connecting lines show the succession chain:
```
[Orchestrator #1: Complete] → [Orchestrator #2: Working] → [Orchestrator #3: Waiting]
```

## Launching a Successor Orchestrator

When succession occurs, the new orchestrator is created but **NOT automatically launched**. You have full control over when to start it.

### Step-by-Step Launch Process

#### Step 1: Recognize the Succession Event

You'll see two orchestrator cards in the Jobs tab:
- **Instance 1** - Status: "Complete" or "Handed Over"
- **Instance 2** - Status: "Waiting" with a **NEW** badge

#### Step 2: Click the Launch Button

On the successor card (Instance 2), click the **"Launch Successor"** button.

This opens the Launch Successor Dialog.

#### Step 3: Review the Handover Summary

The dialog shows:
- **Project Status**: Overall progress (e.g., "60% complete")
- **Active Agents**: List of sub-agents currently working
- **Completed Phases**: What's been finished
- **Pending Decisions**: Open questions requiring attention
- **Next Steps**: Recommended actions for the successor

Take a moment to review this summary to understand where the project stands.

#### Step 4: Copy the Launch Prompt

The dialog displays an auto-generated command prompt:

```bash
export GILJO_MCP_SERVER_URL=http://10.1.0.164:7272
export GILJO_AGENT_JOB_ID=orch-a1b2c3d4-5e6f-7890-1234-567890abcdef
export GILJO_PROJECT_ID=6adbec5c-9e11-46b4-ad8b-060c69a8d124

# Handover Summary:
# Project Status: 60% complete
# Active Agents: frontend-dev (working), backend-api (waiting)
# Pending Decisions: API endpoint naming, Auth method
# Next Steps: Implement API endpoints, then frontend integration

# Start Claude Code with MCP connection:
codex mcp add giljo-orchestrator
```

Click **"Copy to Clipboard"** to copy this entire prompt.

#### Step 5: Open a Terminal

Open a new terminal window or command prompt on your computer.

#### Step 6: Paste and Execute

Paste the copied prompt into the terminal and press Enter.

The successor orchestrator will start with:
- Fresh context window (0% usage)
- Full handover summary loaded
- All project state preserved
- Connection to the MCP server

#### Step 7: Verify Launch

Back in the dashboard, the successor card status should change:
- **Status**: "Waiting" → "Working"
- **Context Usage**: 0% → ~3% (handover summary loaded)
- **NEW Badge**: Disappears

The successor is now actively orchestrating your project.

### Alternative: Triggering Succession via Slash Command

**New in Handover 0080a**: You can manually trigger orchestrator succession from within Claude Code or Codex CLI using the `/gil_handover` slash command.

#### When to Use This

Use the slash command when you want to hand over from within your AI coding agent:
- After 40-50 messages in a long conversation
- Before major phase transitions in your project
- When the conversation feels "long" or context-heavy
- To proactively manage context before approaching limits

#### How to Use

**Step 1: Type the Command**

In your Claude Code or Codex CLI conversation with the orchestrator:

```
/gil_handover
```

**Step 2: Review the Output**

The command will display:
- ✅ Success message confirming successor creation (Instance 2)
- 📋 Handover summary showing:
  - Project status and completion percentage
  - Active agents and their current work
  - Pending decisions
  - Next steps
- 🚀 Launch prompt ready to copy

**Step 3: Copy the Launch Prompt**

The output includes an auto-generated launch prompt:

```bash
export GILJO_MCP_SERVER_URL=http://10.1.0.164:7272
export GILJO_AGENT_JOB_ID=orch-a1b2c3d4-5e6f-7890-1234-567890abcdef
export GILJO_PROJECT_ID=6adbec5c-9e11-46b4-ad8b-060c69a8d124

codex mcp add giljo-orchestrator
```

**Step 4: Launch in New Terminal**

Open a new terminal window and paste the command to start Instance 2.

#### UI Alternative: "Hand Over" Button

You can also trigger succession from the web dashboard:

1. Navigate to your project's **Jobs** tab
2. Find the orchestrator card (showing instance number)
3. Click the **"Hand Over"** button (only visible for working orchestrators)
4. Copy the generated launch prompt from the dialog
5. Paste and run in a new terminal

Both methods produce the same result - a clean handover to a successor orchestrator with fresh context.

## Viewing Succession History

### Timeline View

To see the complete succession chain for your project:

1. Open your project in the dashboard
2. Navigate to the **Jobs** tab
3. Click **"View Timeline"** button (top-right of orchestrators section)

The Succession Timeline shows:
- **Chronological list** of all orchestrator instances
- **Instance numbers** and status
- **Handover summaries** (expandable)
- **Context usage** at handover time
- **Timestamps** for creation and completion

### Expanding Handover Summaries

Click on any instance in the timeline to expand its handover summary:
- Project status at handover
- Active agents at that time
- Completed phases
- Pending decisions
- Context usage percentage
- Reason for succession (context_limit, manual, phase_transition)

This historical view is valuable for:
- Understanding project evolution
- Reviewing past decisions
- Debugging issues
- Forensic analysis

## Troubleshooting

### Problem: Successor Not Showing Up

**Symptoms**: Orchestrator #1 shows "Complete" but no successor card appears.

**Possible Causes**:
- Succession failed due to database error
- Network interruption during handover
- Orchestrator reached 100% context before succession could complete

**Solution**:
1. Refresh the dashboard (Ctrl+R or Cmd+R)
2. Check the browser console for errors (F12 → Console tab)
3. Verify the database is running (`psql -U postgres -l`)
4. Contact administrator if issue persists

### Problem: Launch Prompt Doesn't Work

**Symptoms**: Pasting the launch prompt in terminal produces errors.

**Possible Causes**:
- MCP server URL incorrect or server not running
- Environment variables not exported correctly
- Terminal doesn't support multi-line paste

**Solution**:
1. Verify MCP server is running: `python startup.py`
2. Check server URL in My Settings → MCP Configuration
3. Copy and paste each line individually if terminal doesn't support multi-line paste
4. Ensure you're in the correct directory for your AI coding agent (Claude Code, Codex CLI, etc.)

### Problem: Context Usage Shows Red Before Succession

**Symptoms**: Orchestrator context bar is red (90%+) but no successor created.

**Possible Causes**:
- Orchestrator hasn't checked context usage recently
- Succession disabled for this project (rare)
- Orchestrator encountered an error before triggering succession

**Solution**:
1. Wait 5-10 minutes for automatic succession trigger
2. Manually trigger succession via **"Trigger Succession"** button (if available)
3. Check orchestrator logs for errors
4. Contact administrator if succession doesn't occur within 30 minutes

### Problem: Multiple Successors Created Simultaneously

**Symptoms**: Instance 2 and Instance 3 both show "Waiting" status.

**Possible Causes**:
- Rapid context growth triggered multiple successions
- Race condition during succession (rare)
- Database synchronization issue

**Solution**:
1. Launch the LOWEST numbered successor first (Instance 2)
2. Wait for Instance 2 to reach working status
3. If Instance 3 is still "Waiting", it can be safely ignored or launched later if needed
4. Report to administrator for investigation

### Problem: Handover Summary Missing Information

**Symptoms**: Successor starts but handover summary is incomplete or empty.

**Possible Causes**:
- Orchestrator had minimal context to transfer
- Compression algorithm filtered out non-critical state
- Database truncation during handover

**Solution**:
1. Review Instance 1's message history (available in timeline)
2. Cross-reference with project vision documents
3. Successor can re-read project vision if needed
4. Report to administrator if critical state is missing

## FAQ

### Q1: How often does succession occur?

**A**: Succession is triggered manually by the user when an orchestrator's context usage is high (e.g., approaching 90% of its budget, typically 135,000 out of 150,000 tokens). The frequency depends on project complexity and user monitoring:
- Simple projects: May never need succession
- Medium projects: 1-2 manual successions over several weeks
- Complex projects: 3-5 manual successions over months

### Q2: Can I manually trigger succession at any time?

**A**: Yes, you can manually trigger succession via:
- **Slash command**: Type `/gil_handover` in your AI coding agent (Claude Code, Codex, Gemini)
- **UI Button**: Click the **"Hand Over"** button on the orchestrator card in the dashboard

This is useful for:
- When context usage is high (e.g., 80-90%)
- Phase transitions (e.g., switching from planning to implementation)
- Starting fresh after major project changes
- Proactive context management

### Q3: Will I lose any project data during succession?

**A**: No. Succession preserves:
- All message history (stored in database)
- Project vision and mission documents
- Agent job records and status
- Context references and critical state
- User decisions and approvals

The only thing that changes is the orchestrator instance number and its context window resets to fresh.

### Q4: Can I go back to a previous orchestrator instance?

**A**: No, orchestrator instances are linear and forward-only. Once Instance 1 hands over to Instance 2:
- Instance 1 is marked "Complete" and cannot be restarted
- Instance 2 becomes the active orchestrator

However, you can:
- View Instance 1's full message history in the timeline
- Review handover summaries
- Access all stored context and decisions

### Q5: What happens if I don't launch the successor?

**A**: The successor remains in "Waiting" status indefinitely. The project is effectively paused until you launch it. This gives you full control over:
- When to continue the project
- Whether to review handover summary first
- Timing of context transitions

There's no time limit - you can launch the successor hours, days, or weeks later.

### Q6: Can multiple orchestrators work on the same project simultaneously?

**A**: No. Only ONE orchestrator can be "Working" on a project at a time. The succession system ensures:
- Instance 1 completes before Instance 2 starts
- Clear handover boundaries
- No conflicting commands or decisions

This prevents race conditions and maintains project coherence.

### Q7: How do I know which orchestrator instance is currently active?

**A**: Look for the orchestrator card with:
- **Status**: "Working" (blue badge)
- **Highest instance number** among all "Working" status cards
- **Context usage** actively increasing

The timeline view also highlights the active instance.

### Q8: What if succession fails during handover?

**A**: The system has multiple safeguards:
1. **Atomic transactions**: Database changes are rolled back if handover fails
2. **Graceful degradation**: Instance 1 remains active if succession fails
3. **User notification**: Alert shown in dashboard with error details

You can manually retry succession via the UI or slash command, or contact administrator for assistance.

### Q9: Does succession cost extra?

**A**: Succession is cost-efficient:
- **Handover summary**: ~10,000 tokens (compressed state)
- **Fresh context**: Successor starts at 0 tokens
- **Net savings**: 70% reduction vs replaying full 150,000 token context

Succession actually REDUCES costs by avoiding context bloat.

### Q10: How do I know when to trigger succession?

**A**: Monitor the context usage bar on the orchestrator card in the dashboard. When it approaches 80-90% (yellow or red), it's a good time to consider triggering succession manually. You can also trigger succession at any time during phase transitions or after major project milestones.

---

## Need Help?

If you encounter issues not covered in this guide:

1. **Check the Dashboard Alerts**: Look for error messages or notifications
2. **Review the Timeline**: Historical view often reveals patterns
3. **Contact Administrator**: Provide:
   - Project ID
   - Orchestrator instance numbers involved
   - Screenshots of the issue
   - Error messages from browser console (F12)

For general questions about orchestrator succession, refer to the [Developer Guide](../developer_guides/orchestrator_succession_developer_guide.md) for technical details.

---

**Happy Orchestrating!** Remember: Succession is your ally for unlimited project duration. Embrace it as a natural part of large-scale AI development.
