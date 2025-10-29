---
Handover 0067: Specification Comparison Matrix Template
Date: 2025-10-29
Status: TEMPLATE
---

# Specification Comparison Matrix

## Project Launch Panel (0062)

| Feature | Handwritten Spec | Formal Handover | Implementation | Status | Notes |
|---------|------------------|-----------------|----------------|--------|-------|
| **Top Panel** | | | | | |
| Project Name Display | "Project Name: xxxxxx" | Project.name | ProjectLaunchView.vue:65 | ? | |
| Project ID Display | "Project ID: xxxxxxxxx" | Project.id | ProjectLaunchView.vue:65 | ? | |
| Product Name Display | "PProduct: product name" | Product.name | ProjectLaunchView.vue:65 | ? | |
| | | | | | |
| **Orchestrator Card** | | | | | |
| Card Position | Left side | Left panel | LaunchPanelView.vue:? | ? | |
| Card Info Display | "info" section | Orchestrator details | LaunchPanelView.vue:? | ? | |
| Copy Prompt Button | "Prompt copy" | Copy to clipboard | LaunchPanelView.vue:? | ? | |
| | | | | | |
| **User Description** | | | | | |
| Description Field | "USers project description" | Project.description | LaunchPanelView.vue:? | ? | |
| Edit Button | "Edit button to fine tune" | Edit functionality | LaunchPanelView.vue:? | ? | |
| Save Button | "[Save button if changed]" | Save description | LaunchPanelView.vue:? | ? | |
| | | | | | |
| **Mission Window** | | | | | |
| Mission Display | Center panel | Mission text area | LaunchPanelView.vue:? | ? | |
| Orchestrator Populated | "Mission the orchestrator creates" | Generated mission | LaunchPanelView.vue:? | ? | |
| Scrollable | Implied | Scroll support | LaunchPanelView.vue:? | ? | |
| | | | | | |
| **Agent Cards** | | | | | |
| Grid Layout | 2x3 grid shown | Grid of 6 | AgentMiniCard.vue:? | ? | |
| Agent Name | "Agent Name" | Agent.name | AgentMiniCard.vue:? | ? | |
| Agent Type | "Type of Agent" | Agent.type | AgentMiniCard.vue:? | ? | |
| Agent Info | "Agent info" | Agent details | AgentMiniCard.vue:? | ? | |
| Max Cards | 6 shown | Up to 6 | AgentMiniCard.vue:? | ? | |
| | | | | | |
| **Accept Mission** | | | | | |
| Button Position | Bottom center | Bottom of panel | LaunchPanelView.vue:? | ? | |
| Button Action | Transitions to Kanban | Navigate to Jobs | LaunchPanelView.vue:? | ? | |

---

## Agent Kanban Dashboard (0066)

| Feature | Handwritten Spec | Formal Handover | Implementation | Status | Notes |
|---------|------------------|-----------------|----------------|--------|-------|
| **Board Structure** | | | | | |
| Initial State | "Empty Kanban board" | Empty columns | KanbanJobsView.vue:? | ? | |
| Column Count | Not specified | 5 → 4 (UPDATES) | KanbanJobsView.vue:? | ? | |
| | | | | | |
| **Columns** | | | | | |
| First Column | "WAITING" | "Pending" | KanbanColumn.vue:? | ? | Name mismatch? |
| Second Column | (implied progression) | "Active" | KanbanColumn.vue:? | ? | |
| Third Column | (implied progression) | "Completed" | KanbanColumn.vue:? | ? | |
| Fourth Column | (not mentioned) | "Blocked" | KanbanColumn.vue:? | ? | Added in implementation |
| Fifth Column | (not mentioned) | Removed in UPDATES | N/A | ? | |
| | | | | | |
| **Copy Prompts** | | | | | |
| CODEX Prompt | "COPY PROMPT for CODEX" | Not mentioned | LaunchPanelView.vue:? | ? | MISSING? |
| CODEX Instructions | "AND ALSO GEMINI" | Not mentioned | LaunchPanelView.vue:? | ? | MISSING? |
| GEMINI Prompt | "COPY PROMPT for...GEMINI" | Not mentioned | LaunchPanelView.vue:? | ? | MISSING? |
| Claude Code | "give orchestrator prompt copy" | Implemented | LaunchPanelView.vue:? | ? | |
| Exclusivity | "to Claud Code only" | Claude only | LaunchPanelView.vue:? | ? | |
| | | | | | |
| **Agent Movement** | | | | | |
| Progress Tracking | "Agents move along kanban" | Status updates | KanbanJobsView.vue:? | ? | |
| Self-Navigation | (implied manual) | MCP tool updates | No drag-drop | ? | Different mechanism |
| | | | | | |
| **Message Center** | | | | | |
| Location | "bottom of message center" | Right drawer | MessageThreadPanel.vue:? | ? | LOCATION DIFFERENT? |
| Initial State | "which is empty" | Empty panel | MessageThreadPanel.vue:? | ? | |
| Content | "agent communication" | Message thread | MessageThreadPanel.vue:? | ? | |
| | | | | | |
| **Messaging** | | | | | |
| Broadcast | "broadcast to all agents" | Broadcast feature | agent_jobs.py:? | ? | EXISTS? |
| Specific Agent | "MCP message to agent" | Send to one | MessageThreadPanel.vue:? | ? | |
| User Can Send | "User can send" | Input field | MessageThreadPanel.vue:? | ? | |
| | | | | | |
| **Project Summary** | | | | | |
| Panel Location | "project summary panel bottom" | Unknown | KanbanJobsView.vue:? | ? | WHERE IS IT? |
| Content | "sums up for closeout" | Summary text | Unknown:? | ? | MISSING? |
| Orchestrator Role | "orchestrator...sums up" | Generated summary | Unknown:? | ? | MISSING? |
| | | | | | |
| **Project Closeout** | | | | | |
| Prompt Available | "project Closeout prompt" | Not mentioned | Unknown:? | ? | MISSING? |
| Actions | "commit push document" | Git operations | Unknown:? | ? | MISSING? |
| Mark Complete | "mark complete" | Status update | Unknown:? | ? | MISSING? |
| | | | | | |
| **Completed Agents** | | | | | |
| Tooltip | "have a tootlip" | Not mentioned | JobCard.vue:? | ? | MISSING? |
| Reactivation | "to reactivate" | Not mentioned | JobCard.vue:? | ? | MISSING? |

---

## Severity Legend

| Status | Meaning | Action Required |
|--------|---------|-----------------|
| ✅ MATCH | Specification matches implementation | None |
| ⚠️ PARTIAL | Partially implemented or different approach | Review for adequacy |
| ❌ MISSING | Not found in implementation | Implement or justify |
| 🔄 DIFFERENT | Implemented differently than specified | Validate with user |
| ❓ UNKNOWN | Need to investigate | Deep dive required |

---

## Terminology Discrepancies

| Handwritten Term | Implementation Term | Impact |
|------------------|-------------------|---------|
| WAITING | Pending | User confusion |
| USers | User's | Typo only |
| PProduct | Product | Typo only |
| tootlip | tooltip | Typo only |
| | | |

---

## Critical Gaps Identified

### Priority 0 (Blocking)
1. **Message Center Location**: Spec says bottom, implementation appears to be right drawer
2. **CODEX/GEMINI Support**: No evidence of implementation
3. **Project Closeout**: Entire feature may be missing
4. **Project Summary Panel**: Location unknown or missing

### Priority 1 (Major)
1. **Column Naming**: WAITING vs Pending
2. **Reactivation Tooltips**: Not found
3. **Broadcast Messaging**: Unclear if implemented

### Priority 2 (Minor)
1. **Agent Info Display**: Format may differ
2. **Button Labels**: May use different text

---

## Evidence Notes

```
Example:
Feature: CODEX Prompt Copy
Searched: grep -r "CODEX" frontend/
Result: 0 matches
Searched: grep -r "codex" frontend/
Result: 0 matches
Conclusion: CODEX support not implemented
```

---

## Recommendations

1. **Immediate Actions**:
   - Verify message center location with user
   - Confirm if CODEX/GEMINI support needed
   - Locate or implement project closeout

2. **Clarifications Needed**:
   - Is "WAITING" critical or can "Pending" suffice?
   - Where should project summary panel be?
   - Are reactivation tooltips required?

3. **Quick Fixes**:
   - Update column names if needed
   - Add missing tooltips
   - Implement broadcast if missing

---

*Fill in the '?' marks with actual findings during investigation.*