# Agent Templates Catalog

These role templates define native coding subagents used by the orchestrator. They are:

- Locked by default (system-provided). Users can:
  - Download the Markdown files
  - Copy/Duplicate in-app to tune
  - Auto-inject into the coding tool (Agents SDK) when supported

Format
- Each template is Markdown with YAML front matter for indexing and platform mapping.
- The app uses front matter to sort and filter (name, role, category, version, capabilities, tools, etc.).

Workflow
1) Orchestrator selects a role template (stable duties/skills/guardrails).
2) Orchestrator composes a mission overlay (project-specific objectives, scope, constraints).
3) Worker subagent is spawned with filtered context + the mission overlay.
4) Outputs and handoffs are validated against success criteria.

See DESIGN.md for details on overlays and platform adapters.

