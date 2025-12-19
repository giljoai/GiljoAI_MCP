# Alpha Trial Remediation Roadmap

**Session Date**: 2025-12-19
**Session Type**: Alpha Trial Analysis & Remediation Planning
**Status**: PLANNING COMPLETE - Ready for Implementation

---

## Executive Summary

This document captures the outcomes of the Alpha Trial Remediation Session, where we analyzed feedback from the TinyContacts project alpha trial and created 7 remediation handovers (0355-0361).

**Trial Project**: TinyContacts (F:\TinyContacts)
**Agents Used**: Analyzer, Documenter
**Orchestrator**: Successfully staged and coordinated 2 agents
**Outcome**: Both agents completed successfully with detailed feedback

---

## How We Got Here

### 1. Alpha Trial Execution

The TinyContacts project was used to test the GiljoAI MCP orchestration pipeline:
- **Staging Phase**: Orchestrator received instructions, discovered agents, spawned 2 jobs
- **Execution Phase**: Analyzer created architecture analysis, Documenter created scaffolding
- **Completion Phase**: Both agents wrote feedback files documenting their experience

### 2. Feedback Collection

Two primary feedback sources:
- **F:\TinyContacts\analyzer_feedback.md** (458 lines) - Comprehensive MCP protocol analysis
- **F:\TinyContacts\documenter_feedback.md** (276 lines) - Workflow and handoff analysis

Plus real-time observations during the session:
- WebSocket/UI state regressions
- Duplicate orchestrator spawning on page refresh
- Steps column showing 0/0
- Closeout button disappearing

### 3. Issue Classification

We identified **15 issues** across 4 categories:

| Priority | Count | Categories |
|----------|-------|------------|
| HIGH | 8 | Protocol, MCP Tools, Frontend |
| MEDIUM | 4 | MCP Tools, Integration |
| LOW | 3 | Documentation |

### 4. Remediation Planning

Created 7 handover documents with estimated **28-38 hours** total effort.

---

## The 7 Remediation Projects

| Handover | Title | Priority | Hours | Key Fix |
|----------|-------|----------|-------|---------|
| 0355 | Protocol Message Handling Fix | HIGH | 4-6h | Agents must read all messages |
| 0356 | MCP Tool Parameter Consistency | HIGH | 3-4h | tenant_key, agent_id standardization |
| 0357 | Agent Template Context Loading | HIGH | 2-3h | User "full" setting not working |
| 0358 | WebSocket & UI State Overhaul | HIGH | 10-14h | Stale data, duplicate orchestrators |
| 0359 | Steps/Progress Tracking Fix | HIGH | 3-4h | Steps column shows 0/0 |
| 0360 | Medium Priority Tool Enhancements | MEDIUM | 4-5h | Message filtering, get_team_agents |
| 0361 | Documentation Updates | LOW | 2h | fetch_context syntax, protocol guide |

---

## Recommended Execution Order

Based on dependencies and impact:

1. **0355** (Protocol Message Handling) - Foundation for agent coordination
2. **0356** (Tool Parameter Consistency) - Removes immediate agent friction
3. **0359** (Steps/Progress Tracking) - Quick visible win (single-line fix)
4. **0357** (Agent Template Context) - User settings should work
5. **0358** (WebSocket & UI Overhaul) - Largest scope, comprehensive fix
6. **0360** (Tool Enhancements) - Nice-to-haves for next trial
7. **0361** (Documentation) - Can be done anytime

---

## Key Findings from Agent Feedback

### What Worked Well (PRESERVE)

1. **Thin-client architecture** - Spawn message ~10 lines, mission fetched on-demand
2. **Auto-acknowledging messages** - `receive_messages()` marks as read automatically
3. **TodoWrite integration** - Forces planning, improves output quality
4. **Full protocol in mission response** - Agents don't need to remember lifecycle
5. **Feedback requirement injection** - Captured valuable agent experience
6. **Sequential spawning** - Worked well for dependent tasks (analyzer → documenter)

> "A comprehensive analyzer output made my job 10x easier. Invest in making analyzer thorough, and downstream agents benefit immensely." - Documenter Agent

### What Needs Fixing

1. **Message handling gaps** - Agents not reading all messages, orchestrator not polling
2. **Parameter inconsistencies** - tenant_key, agent_id/job_id confusion
3. **User settings ignored** - "full" template depth not applied
4. **UI state regressions** - Dashboard shows stale data, duplicate spawns
5. **Progress tracking broken** - Steps column always 0/0

---

## Agent Feedback Files

For detailed review with developers, refer to:

### Analyzer Feedback (F:\TinyContacts\analyzer_feedback.md)
- **Lines 17-52**: Mission Clarity & Ambiguities
- **Lines 54-95**: Missing Context Analysis
- **Lines 97-168**: MCP Protocol Experience (CRITICAL)
- **Lines 175-217**: Agent Prompt Quality
- **Lines 222-260**: MCP Server Improvement Suggestions
- **Lines 264-316**: Documentation Suggestions
- **Lines 427-439**: Questions for Developer

### Documenter Feedback (F:\TinyContacts\documenter_feedback.md)
- **Lines 9-35**: Mission Clarity Assessment
- **Lines 37-56**: Missing Context Issues
- **Lines 58-79**: Analyzer → Documenter Handoff Quality
- **Lines 84-115**: MCP Protocol Experience
- **Lines 119-138**: Workflow Friction Points
- **Lines 142-168**: Agent Prompt Improvement Suggestions
- **Lines 200-209**: What Worked Well (Preserve These)

---

## Developer Discussion Points

Each handover now includes a **⚠️ DEVELOPER DISCUSSION REQUIRED** section with:
- Options to review (typically 3-4 alternatives)
- Trade-offs for each option
- Questions requiring developer input
- Links to relevant agent feedback

**Before implementing any handover**, review these sections with the developer to:
1. Confirm the proposed approach
2. Make decisions on open questions
3. Adjust scope if needed

---

## Research Findings

Code investigation confirmed:
- `full_protocol` generated in `orchestration_service.py:153-211`
- `launch_project()` does NOT check for existing orchestrators (CONFIRMED BUG)
- WebSocket events are NOT re-emitted on page load (by design)
- `report_progress` expects `mode: "todo"` format (protocol mismatch)

---

## Next Steps

1. **Review this roadmap** with developer
2. **Read agent feedback files** for detailed context
3. **Start with Handover 0355** (message handling) as foundation
4. **Run another alpha trial** after implementing 0355-0357 to validate fixes

---

## Session Artifacts

| Artifact | Location |
|----------|----------|
| Plan File | `C:\Users\giljo\.claude\plans\expressive-herding-aurora.md` |
| Analyzer Feedback | `F:\TinyContacts\analyzer_feedback.md` |
| Documenter Feedback | `F:\TinyContacts\documenter_feedback.md` |
| Handover 0355 | `handovers/0355_protocol_message_handling_fix.md` |
| Handover 0356 | `handovers/0356_mcp_tool_parameter_consistency.md` |
| Handover 0357 | `handovers/0357_agent_template_context_loading.md` |
| Handover 0358 | `handovers/0358_websocket_ui_state_overhaul.md` |
| Handover 0359 | `handovers/0359_steps_progress_tracking_fix.md` |
| Handover 0360 | `handovers/0360_medium_priority_tool_enhancements.md` |
| Handover 0361 | `handovers/0361_documentation_updates.md` |

---

## Commit History

```
bdb09648 docs(0355-0361): alpha trial remediation handovers (7 files, 5095 lines)
```

---

**Document prepared by**: Orchestrator Coordinator
**Session duration**: ~2 hours
**Handovers created**: 7
**Total estimated remediation effort**: 28-38 hours
