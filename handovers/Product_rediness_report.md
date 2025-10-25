# Product Readiness Report — Product → Project → Orchestrator + Agent Cards → MCP Comms

## User Described The Following
- Create a product, then create a project under that product.
- Write a description for the project and activate it.
- Generate the initial “agent card” with a copyable prompt to kick off the orchestrator.
- Orchestrator should read the product specs and context, read the project, create the mission, assign agents, and produce agent cards with prompt instructions.
- All agents should communicate via the MCP server (so external CLIs like Codex/Gemini/Claude can participate).

## What Was Found (TL;DR)
- The backend has full support for Product, Project, Agent models and a server‑led orchestration flow that reads a product’s vision/config, generates missions, selects/coordinates agents, and returns results.
- The MCP HTTP endpoint is implemented and exposes project/agent/messaging/context tools for external MCP clients (Claude, Codex, Gemini) to communicate through your server.
- The UI has the pieces to display templates and copy configuration commands for MCP, plus agent monitoring. A dedicated “Agent Card with copyable prompt” view is not prebuilt, but all building blocks exist.
- A small gap: the “agent job” lifecycle (acknowledge/report/complete) exists as REST endpoints but is not currently exposed as MCP tools; CLIs can still use the REST endpoints or you can wrap them as MCP tools.

---

## Detailed Findings

### Data Models & Context
- Product model with rich context and vision storage
  - Holds  (JSONB) for tech stack, features, architecture; supports inline or file‑based vision.
  - Source:  (class Product)
- Project model with alias/status and tenant isolation
  - Links to Product via , tracks status/budget/usage.
  - Source:  (class Project)
- Agent model with role/mission/status and per‑project scoping
  - Source:  (class Agent)

### Product Creation + Vision
- Create product (with optional file upload) via Products API.
  - Source: , POST 
- Upload inline vision and chunk for orchestration via Agent Management API.
  - Source:  (upload_vision_document)
  - Marks  and  ()

### Project Creation (under Product) + Activation
- Create project via Projects API (supports  in request model; ToolAccessor persists it).
  - Source:  (ProjectCreate),  (create_project)
- Orchestrator’s lifecycle expects PLANNING → ACTIVE for activation.
  - Project creation (orchestrator path) sets PLANNING (), activation allowed from PLANNING/PAUSED ()
- UI Projects page can update status to active; API  updates  (frontend triggers the update; backend persists).
  - Source: , 

### Server‑Led Orchestration (one‑call workflow)
- Entry point:  creates a PLANNING project, chunks vision (if needed), analyzes requirements, selects agents, generates missions, coordinates, and returns mission plan + metrics.
  - Source:  (process_vision)
- Orchestrator class
  - Creates/activates projects, spawns agents with template‑backed missions, coordinates workflow.
  - Sources:  (class),  (create_project),  (activate_project),  (spawn_agent),  (coordinate_agent_workflow),  (generate_mission_plan)
- Mission planning
  - Reads  and  (or chunks) to generate role‑specific missions with token budget focus.
  - Sources:  (class),  (analyze_requirements),  (_filter_vision_for_role)
- Templates
  - Unified template manager provides orchestrator + role prompts; used when spawning agents.
  - Sources:  (class UnifiedTemplateManager),  (get_template)

### “Agent Card” With Copyable Prompt (Hybrid CLI Flow)
- Building blocks available now:
  - Missions/prompts for roles (via templates) to render in a card.
  - Job model + API so the card can include a Job ID and status (pullable by CLIs).
    - Sources:  (create_agent_job),  (get_active_agent_jobs),  (update_agent_job_status),  (acknowledge_job_message)
  - MCP connection wizard that generates a copyable command (Claude/Gemini; Codex entry present as placeholder).
    - Source: 
- What’s not prebuilt:
  - A dedicated “Agent Card” UI component that bundles mission text + job ID + copyable MCP/REST commands as one card. The codebase has Agents monitoring (cards table/grid) and Template Manager with preview/copy controls, so composing a card is straightforward with existing components.
  - The job lifecycle (ack/report/complete) is currently REST only; not exposed in  tool list. CLIs can call REST, or you can add wrapper MCP tools.

### MCP Communications (External CLIs)
- The MCP HTTP endpoint implements JSON‑RPC 2.0 and exposes project/agent/message/context tools.
  - Sources:  (handle_initialize),  (handle_tools_list),  (handle_tools_call)
  - Tools map to  for create/list/switch/close project, spawn/list/update/retire agents, and send/receive/ack messages; also context/template helpers.
  - REST mirror exists in  (for HTTP‑only clients).
- UI wizard provides copyable MCP add command for external CLIs (Claude today; Gemini supported; Codex shown as “coming soon” text in backend).
  - Sources: ,  (Codex/Gemini placeholders)

### UI Surface
- Projects management (create, edit, activate/close) and agents monitoring (cards/table), mission dashboard, and config wizards exist.
  - Sources: , , , 
- Copy‑to‑clipboard patterns are widely used for setup/config text, so adding copyable agent prompts is consistent with existing UX.

---

## Gaps, Risks, Clarifications
- Project association in UI: Project creation UI doesn’t expose . The API supports it today.
- “Agent Card” is not a single out‑of‑the‑box component; you’d compose it from existing Template Manager preview + copy patterns and agent/job state.
- Agent Job lifecycle is REST‑only; if you require MCP‑only operation, add MCP tool wrappers for job endpoints.
- Codex CLI “mcp add” in your backend copy helpers is marked placeholder, but Codex supports configuring  in  per upstream docs.

---

## Recommended Flows

### 1) Server‑Led (one call)
1) Create product and upload inline/file vision.
2) Call  with , , .
3) Orchestrator generates the project + mission plan, selects agents, coordinates, and returns results. No CLI required.

### 2) Hybrid CLI Agent Cards
1) Create product → upload vision (inline), ensuring .
2) Create project under product (API supports ).
3) Create an agent job for the Orchestrator role (store Job ID).
4) Render an Agent Card showing:
   - Orchestrator mission (from ).
   - Job ID / status.
   - Copyable command to add MCP server (from AiToolConfigWizard) + a short instruction on how the CLI should poll/ack/report job via REST (or future MCP wrappers).
5) External CLIs connect to your MCP server and communicate via  tools.

---

## Validation Checklist (What’s Ready)
- Product: create/update; inline vision upload + chunking is implemented (ready).
- Project: create/update/activate/close; server‑led orchestration path exists and returns mission plan (ready).
- Missions/Prompts: role templates and generator in place; Serena optimizer integrated (ready).
- MCP: HTTP endpoint with project/agent/messaging/context tools (ready). UI wizard emits copyable MCP commands (ready).
- Agent Cards: building blocks exist (templates preview/copy, job API, copyable MCP commands). Needs a composed UI card to match the exact UX (near‑ready).
- Agent jobs via MCP: requires MCP tool wrappers if you want to avoid REST (enhancement).

---

## File Pointers
- Orchestration API and flow
  - , , 
  - , , , , , 
  - , , 
  - , 
- Product/Project/Agent models
  - , , 
- MCP server and tools
  - , , 
  - 
- Agent jobs (for Agent Cards)
  - , , , 
- UI building blocks
  - 
  - 
  - 
  - 
  - 

---

## Next Steps (Minimal To Hit Exact Ask)
- Add MCP tool wrappers for agent‑job endpoints (ack/report/complete) so CLIs can remain MCP‑only if desired.
- Compose a lightweight “Agent Card” view that reads a role’s mission + current job + emits a copyable prompt (mission body + MCP connect command + job ack/report instructions). Reuse Template Manager preview/copy and wizard copy logic.
- (Optional) Expose  in the Projects UI or provide a quick picker; API support already exists.

