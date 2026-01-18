"""
Slash command handlers for project actions.

NOTE (Handover 0388): /gil_activate and /gil_launch removed.
Users perform these actions via web UI:
- Activate: POST /api/v1/projects/{id}/activate
- Launch: POST /api/v1/projects/{id}/launch

This file is kept for backwards compatibility reference.
The ToolAccessor methods still exist for REST API use.
"""
