# 1011 – Interactive Flow Editor Integration

## Objective
- Add an in-panel “Flow Editor” that lets product managers visually arrange workflow steps (drag-and-drop) and stores them as structured JSON for validation against code.
- Reuse parsed steps from handovers (e.g., start_to_finish_agent_FLOW.md) as initial nodes so users can refine flows interactively.

## In Scope
- Embed a graph editor (React Flow or equivalent) under `frontend/flow-editor/` with controls for nodes, edges, labels, and metadata.
- Autosave diagrams as JSON under `dev_tools/devpanel/flows/`.
- Add navigation entries/links from the main panel to the editor.
- Provide basic palette: create/delete nodes, connect edges, annotate with references (API handler, file path, etc.).

## Out of Scope
- Executing flows (no workflow runtime).
- Collaborative editing/version history.
- Automatic validation UI (Phase 2 will consume the JSON for comparisons).

## Milestones
1. **Editor Infrastructure (~2 days)**
   - Create a React/Vite micro-app served by the static server.
   - Integrate React Flow with dark-theme styling consistent with DevPanel.
2. **Seed + Save/Load (~1.5 days)**
   - Extend the `build_flow_data.py` script (or new script) to produce seed JSON per handover.
   - Implement save/load controls so users can export/import JSON.
3. **Metadata & Export (~1 day)**
   - Add editable fields on nodes/edges (description, code reference, status).
   - Expose exported JSON for downstream use (flows.html, validators).
4. **Docs + Navigation (~0.5 day)**
   - Update README/user manual.
   - Add “Flow Editor” links from Architecture & Flows.

## Dependencies
- React Flow (MIT licensed) – feature-rich canvas similar to n8n.
- Vite + static server pipeline already in DevPanel.

## Notes
- Future phases: analyzer to compare user-drawn flows with actual code, highlight missing or outdated steps.

