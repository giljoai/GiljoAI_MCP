# Orchestrator Succession - Quick Reference

**Version**: v3.0+ (Handover 0080)
**Last Updated**: 2025-11-02

## When Does It Happen?

- **Manual handover** (user-triggered via UI or slash command)
- **High context usage** (user monitors and triggers when approaching 90%)
- **Phase transition** (user-triggered at project milestones)

## UI Indicators

| Indicator | Meaning |
|-----------|---------|
| Red progress bar (90%+ context) | Succession imminent |
| "NEW" badge (green) | Successor waiting to be launched |
| "Handed Over" badge (grey) | Predecessor completed handover |
| Succession chain links (spawned_by) | Succession chain position |

## Launch Successor

1. Click **"Launch Successor"** button on successor card
2. Copy generated prompt from dialog
3. Paste in terminal
4. Successor starts with fresh context

**Example Prompt:**
```bash
export GILJO_MCP_SERVER_URL=http://10.1.0.164:7272
export GILJO_AGENT_JOB_ID=orch-a1b2c3d4-5e6f...
export GILJO_PROJECT_ID=6adbec5c-9e11...

codex mcp add giljo-orchestrator
```

## View History

- Click **"View Timeline"** button
- See all instances chronologically
- Expand handover summaries
- Review project evolution

## Database Queries

### Get Succession Chain

```sql
SELECT job_id, status, handover_to
FROM mcp_agent_jobs
WHERE project_id = 'your-project-id'
  AND agent_type = 'orchestrator'
  AND tenant_key = 'your-tenant-key'
ORDER BY created_at;
```

### Check Context Usage

```sql
SELECT
    job_id,
    context_used,
    context_budget,
    ROUND((context_used::float / context_budget * 100)::numeric, 2) AS usage_percent
FROM mcp_agent_jobs
WHERE job_id = 'orchestrator-job-id';
```

## API Endpoints

### Create Handover (Manual)

```bash
POST /api/agent_jobs/{job_id}/create_simple_handover?reason=manual
Authorization: Bearer <token>
```

**Response:**
```json
{
  "success": true,
  "successor_id": "orch-...",
  "handover_summary": {...}
}
```

### Get Succession Chain

```bash
GET /api/agent_jobs/{job_id}/succession_chain
Authorization: Bearer <token>
```

**Response:**
```json
{
  "project_id": "...",
  "chain": [
    {"job_id": "...", "status": "complete", ...},
    {"job_id": "...", "status": "waiting", ...}
  ]
}
```

## MCP Tools

### create_simple_handover

```python
result = await create_simple_handover(
    current_job_id="orch-6adbec5c-9e11...",
    tenant_key="tenant-abc123",
    reason="context_limit"  # or 'manual', 'phase_transition'
)
# Returns: {success, successor_id, handover_summary}
```

### check_succession_status

```python
status = await check_succession_status(
    job_id="orch-6adbec5c-9e11...",
    tenant_key="tenant-abc123"
)
# Returns: {should_trigger, usage_percentage, recommendation}
```

## WebSocket Events

### job:succession_triggered

```json
{
  "event": "job:succession_triggered",
  "data": {
    "orchestrator_id": "orch-...",
    "reason": "context_limit"
  }
}
```

### job:successor_created

```json
{
  "event": "job:successor_created",
  "data": {
    "successor_id": "orch-...",
    "predecessor_id": "orch-...",
    "handover_summary": {...}
  }
}
```

## Key Files

### Backend
- `src/giljo_mcp/orchestrator_succession.py` - Core logic
- `src/giljo_mcp/tools/succession_tools.py` - MCP tools
- `api/endpoints/agent_jobs.py` - API endpoints

### Frontend
- `frontend/src/components/projects/AgentCardEnhanced.vue` - Instance badges
- `frontend/src/components/projects/SuccessionTimeline.vue` - Timeline view
- `frontend/src/components/projects/LaunchSuccessorDialog.vue` - Launch dialog

### Database
- Table: `mcp_agent_jobs`
- Columns: `handover_to`, `handover_summary`, `succession_reason`, `context_used`, `context_budget`, `handover_context_refs`

## Troubleshooting

### Successor Not Showing Up
- Refresh dashboard (Ctrl+R)
- Check browser console (F12)
- Verify database is running

### Launch Prompt Doesn't Work
- Verify MCP server is running: `python startup.py`
- Check server URL in My Settings → MCP Configuration
- Paste lines individually if multi-line paste fails

### Context Usage Red Before Succession
- Wait 5-10 minutes for automatic trigger
- Manually trigger via "Trigger Succession" button
- Check orchestrator logs for errors

## Success Metrics

- **Succession Success Rate**: >99% target
- **Handover Summary Size**: <10K tokens
- **Succession Latency**: <5 seconds
- **Context Loss**: <1% of critical state

## Documentation Links

- **User Guide**: [docs/user_guides/orchestrator_succession_guide.md](../user_guides/orchestrator_succession_guide.md)
- **Developer Guide**: [docs/developer_guides/orchestrator_succession_developer_guide.md](../developer_guides/orchestrator_succession_developer_guide.md)
- **Main Handover**: [handovers/0080_orchestrator_succession_architecture.md](../../handovers/0080_orchestrator_succession_architecture.md)

---

**Quick Tips:**
- Succession is manual (triggered via UI or slash command)
- Monitor context usage and trigger succession when high
- Successors require manual launch (full user control)
- All project history is preserved in database
- Timeline view shows complete succession chain
- Handover summaries are compressed to <10K tokens
- Zero data loss during succession
