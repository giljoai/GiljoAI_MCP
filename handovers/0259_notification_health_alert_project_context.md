# Handover: Notification Health Alert - Add Project Context

**Date:** 2026-03-09
**From Agent:** Planning Session
**To Agent:** Next Session
**Priority:** Medium
**Estimated Complexity:** 2-4 Hours
**Status:** **COMPLETE** (commit `e149f09d`)
**Edition Scope:** CE

---

## Task Summary

Health alerts on the notification bell do not identify which project or agent caused the alert. The user sees a generic message like "orchestrator - No progress update for 5 minutes" with no way to know which project it refers to or navigate to the affected item. This handover adds project name context to health alert notifications and makes them clickable to navigate to the related project.

---

## Context and Background

The health monitoring system (`AgentHealthMonitor`) scans for stalled/stuck agents and broadcasts alerts via WebSocket (`agent:health_alert`). The frontend `websocketEventRouter.js` receives these alerts and creates notifications in the `NotificationDropdown.vue` bell menu. Currently, the broadcast payload includes `job_id`, `agent_display_name`, `health_state`, and `issue_description` but **omits project name, project ID, and execution ID**.

The backend health monitor already queries `AgentExecution` records which have a relationship chain: `AgentExecution -> AgentJob -> Project`. The project context is available in the query but is simply not included in the broadcast payload.

### User Pain Point

The notification message currently reads:
> "orchestrator - No progress update for 5 minutes"

It should read something like:
> "[MyProjectName] orchestrator - No progress update for 5 minutes"

And clicking the notification should navigate to the project view or the specific job/agent.

---

## Technical Details

### Files to Modify

#### Backend (3 files)

1. **`src/giljo_mcp/monitoring/health_config.py`** - `AgentHealthStatus` dataclass
   - Add `project_id: str` field
   - Add `project_name: str` field
   - Add `execution_id: str` field (already exists but confirm it's populated in broadcast)

2. **`src/giljo_mcp/monitoring/agent_health_monitor.py`** - Health monitor queries
   - When querying `AgentExecution` records, join to `AgentJob -> Project` to fetch `project.name` and `project.id`
   - Populate the new fields in `AgentHealthStatus`

3. **`api/websocket.py`** - `broadcast_health_alert()` method (~line 832-864)
   - Add `project_id`, `project_name`, and `execution_id` to the broadcast data payload

#### Frontend (3 files)

4. **`frontend/src/stores/websocketEventRouter.js`** (~line 138-160)
   - Extract `project_name`, `project_id`, `execution_id` from payload
   - Include them in the notification message and metadata
   - Change message format from `${agent_display_name} - ${issue_description}` to `[${project_name}] ${agent_display_name} - ${issue_description}`

5. **`frontend/src/stores/notifications.js`**
   - No schema changes needed (metadata is already an open object)
   - Verify the `agentHealthNotifications` getter still works correctly

6. **`frontend/src/components/navigation/NotificationDropdown.vue`**
   - Add click handler on health alert notifications to navigate to the project
   - Use `router.push({ name: 'project-detail', params: { id: notification.metadata.project_id } })` or equivalent
   - Optionally show a small "project: X" label in the notification card

---

## Implementation Plan

### Phase 1: Backend - Add Project Context to Health Alert Broadcast

**Actions:**
1. In `health_config.py`, add `project_id`, `project_name` fields to `AgentHealthStatus` dataclass
2. In `agent_health_monitor.py`, update the detection queries to join `AgentExecution -> AgentJob -> Project` and populate project fields
3. In `websocket.py`, add `project_id`, `project_name`, and `execution_id` to the `broadcast_health_alert()` data dict

**Testing criteria:**
- Health alert broadcast includes `project_name` and `project_id`
- Existing alerts still fire correctly (no regression)

**Recommended Sub-Agent:** tdd-implementor

### Phase 2: Frontend - Display Project Name in Notification

**Actions:**
1. In `websocketEventRouter.js`, update the `agent:health_alert` handler to include project fields in notification metadata and update the message format
2. In `NotificationDropdown.vue`, make health alert notifications clickable to navigate to the project
3. Test that the notification bell renders the project name correctly

**Testing criteria:**
- Notification message shows `[ProjectName] agent_type - issue description`
- Clicking a health notification navigates to the correct project page
- Notifications without project context (edge case: orphaned job) degrade gracefully to current behavior

**Recommended Sub-Agent:** ux-designer (for the click-to-navigate UX)

### Phase 3: Test and Verify

**Actions:**
1. Write backend test: health alert broadcast includes project context
2. Write frontend test: notification renders project name
3. Manual test: trigger a health alert and verify the full flow end-to-end

---

## Testing Requirements

### Unit Tests
- `test_health_alert_includes_project_context` - Verify `AgentHealthStatus` populates project fields
- `test_broadcast_health_alert_payload_shape` - Verify WebSocket broadcast includes new fields

### Integration Tests
- `test_health_alert_notification_message_format` - Verify frontend notification message includes project name
- `test_health_alert_click_navigates_to_project` - Verify click-through navigation

### Manual Testing
1. Start the application with health monitoring enabled
2. Create a project with agents
3. Let an agent stall (or simulate by adjusting timeout thresholds)
4. Verify the notification bell shows the health alert with project name
5. Click the notification and verify it navigates to the project

---

## Dependencies and Blockers

**Dependencies:**
- None. All required infrastructure exists (health monitor, WebSocket broadcast, notification store)

**Known Blockers:**
- None

**Edge Cases:**
- Orphaned jobs (job without a project) - should degrade gracefully, show "Unknown project" or omit project name
- Multiple alerts from different projects - each should show its own project name

---

## Success Criteria

**Definition of Done:**
- Health alert notifications display the project name in the message
- Clicking a health alert notification navigates to the related project
- Backend broadcast payload includes `project_id`, `project_name`, `execution_id`
- No regression in existing health monitoring or notification functionality
- Tests written and passing

---

## Rollback Plan

**If Things Go Wrong:**
- Revert the 3 backend files and 2-3 frontend files
- The health monitor and notification system fall back to their current behavior (alerts without project context)
- No database changes are involved, so rollback is trivial

---

## Cascading Impact Analysis

- **Downstream:** No downstream impact. We are adding fields to an existing broadcast payload (additive change)
- **Upstream:** No upstream impact. Health monitor queries already access the correct tables
- **Sibling:** No sibling impact. Other notification types (agent_status, system_alert, connection_lost) are unchanged
- **Installation:** No `install.py` changes needed. No schema migration. No config changes.
