# 1005 – Diagrams and PowerPoint Exports

Objective
- Provide “PowerPoint-style” visualizations for architecture views, installation flow, API/MCP catalogs, and DB schema – viewable in the panel and exportable as `.pptx`.

Diagram Views
- Architecture: High-level containers, components, data flows.
- Agent Orchestration: From `handovers/start_to_finish_agent_FLOW.md` into a sequence/flow diagram.
- WebSocket Events: From `handovers/0106d_websocket_event_catalog.md`.
- API Topology: Group endpoints by domain and relationships.
- DB Schema: ER diagram from SQLAlchemy models.
- Installation Flow: From `docs/INSTALLATION_FLOW_PROCESS.md`.

Deliverables
- Frontend renderers using a graph lib (e.g., Mermaid/Graphviz via WASM, or Cytoscape) for live view inside the panel.
- Export pipeline using `python-pptx` to generate `.pptx` slides under `uploads/devpanel/exports/`.
- Download endpoints: `GET /api/v1/developer/exports/{name}.pptx`.

Acceptance Criteria
- Each diagram view renders reliably with >60 FPS for typical graph sizes (≤ 300 nodes).
- PPTX export opens in PowerPoint with clear titles, legends, and readable fonts.

Primary Data Sources
- `handovers/start_to_finish_agent_FLOW.md`
- `docs/INSTALLATION_FLOW_PROCESS.md`
- `docs/SERVER_ARCHITECTURE_TECH_STACK.md`
- `api/endpoints/*` (for API grouping), `src/giljo_mcp/models.py` (DB ER)

Implementation Notes
- Normalize all diagrams to an intermediate JSON schema to allow multiple renderers and PPT export from one source of truth.
- Consider server-side PNG/SVG generation for print quality; embed images into PPT.

Estimate / Owner
- 1.5–2 days; Full-stack.
