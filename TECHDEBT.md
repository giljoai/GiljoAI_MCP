# Technical Debt and Future Enhancements

## Current Architecture Limitations

### Multi-Agent CLI Tool Support

**Current State (v1.0):**
- **Claude Code Only**: Full support with native subagent orchestration
- Built exclusively for Claude Code's subagent spawning capability
- Direct, synchronous agent coordination through Claude's reasoning engine

**Why Claude Code Only?**

Claude Code provides native subagent spawning that enables:
- Synchronous control and coordination
- Direct handoffs between specialized agents
- No polling or message checking required
- Built-in reasoning for task prioritization
- Zero additional infrastructure needed

**Technical Limitation:**

Other AI coding tools (Cursor, Windsurf, Gemini, Codeium) do NOT have equivalent subagent capabilities. They operate as single-agent systems, which breaks our multi-agent orchestration model.

**Problem Example:**
```
Agent A (Cursor terminal) → sends message to queue
Agent B (Cursor terminal) → ❌ Cannot auto-check messages
                           ❌ No subagent API
                           ❌ Requires manual user prompts
```

---

## Expansion Proposal: Multi-Agent Support for Non-Claude Tools

### Phase 1: Current Implementation (Completed)
- ✅ Claude Code native subagent orchestration
- ✅ PostgreSQL message queue
- ✅ Multi-tenant project management
- ✅ WebSocket dashboard for real-time monitoring

### Phase 2: Hybrid Priority Orchestrator (Future)

**Goal:** Enable Cursor, Windsurf, Gemini, and other CLI tools to participate in multi-agent workflows.

**Architecture:**

```
┌──────────────────────────────────────────────────┐
│  GiljoAI Server                                  │
│  ┌────────────────────────────────────────────┐  │
│  │  Hybrid Priority Manager                   │  │
│  │  ┌──────────────┐  ┌───────────────────┐  │  │
│  │  │ Rules Engine │  │ Claude Haiku API  │  │  │
│  │  │ (Free/Fast)  │  │ (Smart/Cheap)     │  │  │
│  │  │              │  │ $0.75/month       │  │  │
│  │  └──────────────┘  └───────────────────┘  │  │
│  └────────────────────────────────────────────┘  │
│                                                   │
│  Background Services:                             │
│  - Message polling (every 30 seconds)             │
│  - Priority evaluation                            │
│  - Dashboard notifications via WebSocket          │
└──────────────────────────────────────────────────┘
```

**Components:**

1. **Rules Engine (Free, Instant)**
   - Handles 80% of priority decisions
   - Simple, fast heuristics:
     - Security issues interrupt everything
     - FIFO for non-urgent tasks
     - Single-agent-with-messages = immediate priority

2. **LLM Fallback (Claude Haiku API)**
   - Handles complex priority decisions
   - Multi-agent conflict resolution
   - Dynamic task re-ordering
   - Cost: ~$0.75/month for typical usage

3. **Message Polling Service**
   ```python
   async def poll_and_notify():
       """Runs every 30 seconds"""
       while True:
           agents_with_messages = await get_agents_with_unread()

           for agent in agents_with_messages:
               priority = await decide_priority(agent, context)

               await broadcast_to_dashboard({
                   "type": "agent_needs_attention",
                   "agent": agent.name,
                   "message_count": len(agent.messages),
                   "priority": priority,
                   "suggested_prompt": generate_prompt(agent)
               })

           await asyncio.sleep(30)
   ```

4. **Dashboard Integration**
   - Real-time priority queue visualization
   - "Prompt Agent" buttons with pre-filled prompts
   - Copy-to-clipboard for easy agent prompting
   - Visual indicators for urgent tasks

**User Experience:**

```
Dashboard shows:
┌─────────────────────────────────────────────┐
│ 🎯 Priority Queue                           │
├─────────────────────────────────────────────┤
│ 1. Implementation Agent (URGENT)            │
│    💬 3 messages: Security vulnerability    │
│    [Copy Prompt] [View Messages]            │
├─────────────────────────────────────────────┤
│ 2. Test Agent                               │
│    💬 1 message: Ready for integration test │
│    [Copy Prompt] [View Messages]            │
└─────────────────────────────────────────────┘

User clicks "Copy Prompt" →
Clipboard: "Check your pending messages using check_messages tool and address the security vulnerability in JWT validation."

User switches to Implementation Agent terminal →
Pastes prompt →
Agent processes messages and acts
```

### Phase 3: Advanced Automation (Optional)

**Investigation needed:** Can we programmatically send prompts to:
- Cursor API (if available)
- Windsurf API (if available)
- Gemini API (if available)

If APIs exist, we could achieve near-Claude Code level automation for other tools.

---

## Implementation Estimates

### Phase 2: Hybrid Orchestrator
- **Time:** 2-3 weeks
- **Complexity:** Medium
- **Dependencies:**
  - Claude API key (for Haiku)
  - Background task infrastructure (already have with FastAPI)
  - Dashboard enhancements (Vue components)

### Phase 3: API Integrations
- **Time:** 1 week per tool (if APIs exist)
- **Complexity:** Low-Medium
- **Dependencies:** Tool vendor API documentation

---

## Cost Analysis

### Claude Code (Current)
- **Cost:** $0 (uses user's Claude subscription)
- **Infrastructure:** None
- **Maintenance:** Low

### Hybrid Orchestrator (Future)
- **Cost:** ~$0.75/month (Claude Haiku API)
- **Infrastructure:** Background polling service (already have)
- **Maintenance:** Medium
- **Benefit:** Support for all CLI tools

---

## Risks and Mitigation

### Risk 1: Other tools may never support native subagents
**Mitigation:** Hybrid orchestrator provides acceptable UX through dashboard notifications + copy-prompt workflow

### Risk 2: Priority decisions via small LLM may be lower quality
**Mitigation:** Use hybrid approach (rules + Claude API) for best quality at low cost

### Risk 3: User fatigue from manual prompting
**Mitigation:**
- Make prompts as easy as possible (one-click copy)
- Investigate tool APIs for automation
- Provide excellent priority visibility in dashboard

---

## Decision: Start with Claude Code Only

**Rationale:**
1. Native subagent support provides best UX
2. Zero additional infrastructure/cost
3. Get to market faster
4. Validate multi-agent orchestration concept
5. Expand to other tools based on user demand

**Migration Path:**
- Keep architecture designed for multi-tool support
- Comment out non-Claude integrations (keep code for future)
- Document expansion plan for future phases
- Re-enable other tools when orchestrator is ready

---

## Related Documentation
- See `docs/PROJECT_ORCHESTRATION_PLAN.md` for subagent integration details
- See `README.md` for current tool support status
- See `CLAUDE.md` for Claude Code-specific features

---

**Last Updated:** 2025-09-30
**Status:** Claude Code v1.0 Released, Phase 2 Planned for Q2 2025
