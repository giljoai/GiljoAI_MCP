# Agent Template Color & Icon Coordination

**Date**: 2025-10-29
**Handover**: 0066
**Status**: Documentation

---

## Summary

This document outlines the color and icon coordination between agent templates and the Kanban UI visualization. Consistency across the system ensures developers can quickly identify agent types by visual cues.

---

## Agent Type Color & Icon Mapping

The following mapping is used consistently across:
- **Frontend**: `AgentMiniCard.vue`, `KanbanJobsView.vue`
- **Backend**: Agent template seeder (metadata)

### Core Agent Types (Handover 0066)

| Agent Type | Color (Vuetify) | Hex Code | Icon (MDI) | Description |
|------------|----------------|----------|------------|-------------|
| `orchestrator` | `purple` | `#7c3aed` | `mdi-brain` | Project orchestration and delegation |
| `analyzer` | `blue` | `#3b82f6` or `#ec4899` (pink) | `mdi-magnify` | Requirements analysis and architecture |
| `implementer` | `green` | `#059669` | `mdi-code-braces` | Code implementation |
| `tester` | `orange` | `#f97316` | `mdi-test-tube` | Testing and QA |
| `ux-designer` | `pink` | `#f472b6` | `mdi-palette` | UX/UI design |
| `backend` | `teal` | `#14b8a6` | `mdi-server` | Backend development |
| `frontend` | `indigo` | `#06b6d4` (cyan) or `#6366f1` (indigo) | `mdi-monitor` | Frontend development |

### Additional Agent Types (AgentMiniCard.vue)

| Agent Type | Color (Vuetify) | Hex Code | Icon (MDI) | Description |
|------------|----------------|----------|------------|-------------|
| `lead` | `blue` | `#3b82f6` | `mdi-account-tie` | Team lead |
| `architect` | `violet` | `#8b5cf6` | `mdi-blueprint` | System architecture |
| `devops` | `indigo` | `#6366f1` | `mdi-server` | DevOps and infrastructure |
| `security` | `red` | `#dc2626` | `mdi-shield-lock` | Security analysis |
| `database` | `teal` | `#14b8a6` | `mdi-database-multiple` | Database specialist |
| `ai_specialist` | `fuchsia` | `#a855f7` | `mdi-robot` | AI/ML specialist |
| `reviewer` | `grey` | Default | `mdi-eye` | Code review |
| `documenter` | `grey` | Default | `mdi-file-document` | Documentation |

---

## Color Discrepancies to Resolve

### 1. Analyzer Color
- **KanbanJobsView.vue**: `blue`
- **AgentMiniCard.vue**: `pink` (`#ec4899`)
- **RECOMMENDATION**: Use `blue` consistently (analysis is typically blue in UI conventions)

### 2. Frontend Color
- **KanbanJobsView.vue**: `indigo`
- **AgentMiniCard.vue**: `cyan` (`#06b6d4`)
- **RECOMMENDATION**: Use `indigo` consistently (matches "frontend" semantics better)

### 3. Backend Icon
- **KanbanJobsView.vue**: `mdi-server`
- **AgentMiniCard.vue**: `mdi-database`
- **RECOMMENDATION**: Use `mdi-server` consistently (backend services are servers)

---

## Implementation Files

### Frontend Components

1. **AgentMiniCard.vue** (`frontend/src/components/project-launch/AgentMiniCard.vue`)
   - Lines 174-213: `agentColor` and `agentIcon` computed properties
   - Used in: Project Launch Panel agent cards

2. **KanbanJobsView.vue** (`frontend/src/components/project-launch/KanbanJobsView.vue`)
   - Line ~276-283: `agentTypeMap` constant
   - Used in: Kanban job cards and job details dialog

### Backend Templates

3. **template_seeder.py** (`src/giljo_mcp/template_seeder.py`)
   - Lines 160-306: `_get_template_metadata()` function
   - Defines behavioral rules and success criteria for each agent role
   - Enhanced with MCP coordination instructions (Handover 0066)

---

## Recommended Standardization

### Update AgentMiniCard.vue

```javascript
const agentColor = computed(() => {
  const colors = {
    orchestrator: '#7c3aed', // Purple
    analyzer: '#3b82f6',     // Blue (CHANGED from pink)
    implementer: '#059669',  // Green
    tester: '#f97316',       // Orange
    'ux-designer': '#f472b6', // Pink
    backend: '#059669',      // Green (backend services)
    frontend: '#6366f1',     // Indigo (CHANGED from cyan)
    lead: '#3b82f6',         // Blue
    architect: '#8b5cf6',    // Violet
    devops: '#6366f1',       // Indigo
    security: '#dc2626',     // Red
    database: '#14b8a6',     // Teal
    ai_specialist: '#a855f7', // Fuchsia
  }
  return colors[props.agent.type?.toLowerCase().replace(/\s+/g, '_')] || '#6b7280'
})

const agentIcon = computed(() => {
  const icons = {
    orchestrator: 'mdi-brain',
    analyzer: 'mdi-magnify',
    implementer: 'mdi-code-braces',
    tester: 'mdi-test-tube',
    'ux-designer': 'mdi-palette',
    backend: 'mdi-server',        // CHANGED from mdi-database
    frontend: 'mdi-monitor',
    lead: 'mdi-account-tie',
    architect: 'mdi-blueprint',
    devops: 'mdi-server',
    security: 'mdi-shield-lock',
    database: 'mdi-database-multiple',
    ai_specialist: 'mdi-robot',
  }
  return icons[props.agent.type?.toLowerCase().replace(/\s+/g, '_')] || 'mdi-robot'
})
```

---

## Agent Template MCP Instructions (Handover 0066)

All agent templates now include comprehensive MCP status reporting instructions:

### Key Updates to `_get_mcp_coordination_section()`:

1. **Phase 1 Enhancement**: Added explicit status update to 'active' when starting work
   - Moves job card from "Pending" to "Active" column
   - Developer visibility of work commencement

2. **Phase 3 Enhancement**: Added explicit status update to 'completed' before job completion
   - Moves job card to "Completed" column
   - Clear completion signal in Kanban dashboard

3. **Error Handling Enhancement**: Added 'blocked' status for errors/human input needed
   - Moves job card to "BLOCKED" column
   - Notifies developer of assistance needed
   - Includes reason parameter for context

4. **Code Examples**: Provided Python MCP tool call examples
   - Starting work: `update_job_status(job_id, "active")`
   - Blocked state: `update_job_status(job_id, "blocked", reason="...")`
   - Completion: `update_job_status(job_id, "completed")`

5. **Agent Self-Navigation**: Emphasized agent autonomy
   - Agents control their own Kanban position
   - Developer CANNOT drag cards (agent self-navigation only)
   - Real-time visibility through status updates

---

## Database Migration Completion

All database migrations for Handover 0066 have been successfully executed:

### Projects Table
- Added `description` column (TEXT, NOT NULL)
- Backfilled from `mission` column for existing records
- Separates human input (description) from AI-generated mission

### MCPAgentJob Table
- Added `project_id` column (VARCHAR(36), nullable)
- Foreign key constraint to `projects(id)` with CASCADE delete
- Indexes created:
  - `idx_mcp_agent_jobs_project` (single column)
  - `idx_mcp_agent_jobs_tenant_project` (composite for multi-tenant queries)

### Status Constraint
- `ck_mcp_agent_job_status` already includes 'blocked' status
- Valid statuses: 'pending', 'active', 'completed', 'failed', 'blocked'

---

## Testing Recommendations

1. **Visual Consistency Check**
   - Load Project Launch Panel with multiple agent types
   - Load Kanban Jobs View with jobs from different agent types
   - Verify colors and icons match across views

2. **Template Verification**
   - Check database `agent_templates` table for enhanced MCP instructions
   - Verify all templates include status update instructions
   - Confirm placeholders (<AGENT_TYPE>, <TENANT_KEY>) are present

3. **Database Verification**
   - Confirm `projects.description` column exists and is populated
   - Confirm `mcp_agent_jobs.project_id` column exists with foreign key
   - Verify indexes improve query performance

---

## Future Enhancements

1. **Color Palette Expansion**: Add more agent types as system grows
2. **Icon Customization**: Allow tenant-level icon overrides
3. **Theme Support**: Dark mode color variants
4. **Accessibility**: Ensure color contrast meets WCAG AA standards

---

**End of Documentation**
