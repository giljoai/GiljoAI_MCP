# Native Subagent Roles and Mission Overlays

This document captures the design for role templates, mission overlays, and platform adapters.

Goals
- Stable, reusable role templates (duties, skills, guardrails) for native coding subagents.
- Missions as overlays: project-specific objectives/scope layered on top of the role.
- Platform-agnostic content with adapter mappings for OpenAI Agents SDK and Claude Agent SDK.

Assignment Flow
1) Orchestrator chooses a role template (e.g., Implementer, Tester).
2) Orchestrator composes a mission overlay (objective, scope boundary, constraints, success metrics).
3) Subagent spawns with filtered context (`product_config`, relevant vision parts) + overlay.
4) Subagent executes, producing outputs/handoffs per template success criteria.

Context Delivery
- Workers receive filtered `product_config` fields per role (see ROLE_CONFIG_FILTERS in code).
- Vision index and chunk retrieval via MCP tools (`get_vision_index`, `get_vision(part)`).

Platform Adapters
- A thin `SubagentRunner` abstraction can map `role_template_id`, overlay, and context into:
  - OpenAI Agents SDK tool calls + run/step events
  - Anthropic Claude Agent SDK actions + streaming callbacks

File Format
- Markdown with YAML front matter, including platform tool sets:
  - `tools.mcp`: canonical MCP tools used across roles
  - `tools.openai.tools`, `tools.anthropic.tools`: agent action names for platform adapters

Lifecycle
- System-provided templates are locked. Users can clone, tune, and export/inject.
- Version each template; overlays reference the role template ID and version used.

Security & Scopes
- Default to least privilege: read-first, scoped writes, no shell/network unless required.
- Role templates define allowed outputs and write locations.

