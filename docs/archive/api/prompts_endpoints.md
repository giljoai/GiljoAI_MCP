# Prompts API Endpoints

**Document Version**: 1.0
**Status**: Production (Thin Client)
**Last Updated**: 2025-01-05 (Harmonized)
**Related Handovers**: 0088 (Thin Client), 0079 (Legacy Fat Prompt)
**Harmonization Status**: ✅ Aligned with codebase

---

## Quick Links to Harmonized Documents

- **[Simple_Vision.md](../../handovers/Simple_Vision.md)** - User journey with orchestrator startup
- **[start_to_finish_agent_FLOW.md](../../handovers/start_to_finish_agent_FLOW.md)** - Technical flow verification
- **[thin_client_migration_guide.md](../guides/thin_client_migration_guide.md)** - Migration guide

**Important Notes** (harmonized):
- Agent job initial status: **"waiting"** (not "pending")
- Agent templates: orchestrator, implementer, tester, analyzer, reviewer, documenter
- Stage Project UI button calls: `POST /api/v1/projects/{id}/activate`

---

## Overview

The Prompts API generates orchestrator launch prompts. As of Handover 0088, prompts use a thin‑client design: the API returns a short identity prompt plus IDs, and the orchestrator fetches its mission via MCP tools. The legacy fat‑prompt endpoint remains for historical reference only.

Base URL: `http://your-server:7272/api`

Authentication: Bearer token

---

## POST /prompts/orchestrator (Thin Client)

Generate a thin orchestrator prompt (~10 lines) with identity information. The orchestrator then calls MCP tools to fetch its mission.

Endpoint: `POST /api/prompts/orchestrator`

Request (JSON):
```
{
  "project_id": "<uuid>",
  "tool": "claude-code|codex|gemini"
}
```

Response (200):
```
{
  "prompt": "I am Orchestrator #1 for GiljoAI Project...",
  "orchestrator_id": "orch-uuid",
  "project_id": "proj-uuid",
  "project_name": "My Project",
  "estimated_prompt_tokens": 50,
  "mcp_tool_name": "get_orchestrator_instructions",
  "instructions_stored": true
}
```

Notes:
- Emits `orchestrator:prompt_generated` WebSocket event with prompt metadata.
- The orchestrator fetches its mission via MCP tools:
  - `get_orchestrator_instructions(orchestrator_id, tenant_key)`
  - `get_agent_mission(agent_job_id, tenant_key)`

---

## GET /prompts/staging/{project_id} (Legacy)

Legacy fat‑prompt endpoint from Handover 0079. Generates a large, self‑contained prompt embedding mission and context. Deprecated by thin client.

Endpoint: `GET /api/prompts/staging/{project_id}`

Status: Legacy (use POST /prompts/orchestrator instead)

---

## See Also

- `docs/STAGE_PROJECT_FEATURE.md` — 0088 thin‑client changes
- `docs/guides/thin_client_migration_guide.md` — migration details
- `docs/developer_guides/websocket_events_guide.md` — events
