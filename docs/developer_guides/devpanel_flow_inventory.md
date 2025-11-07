# Developer Panel Flow Inventory

Curated list of user-facing workflows to visualize in the Developer Panel. Each entry includes a short description and primary references (docs, handovers, code, or tests) that capture the current behavior.

## 1. Installation & Bootstrap

- **Fresh Installation Flow** – Full zero-to-ready sequence, including environment checks, database provisioning, and first admin creation.  
  _Sources_: docs/INSTALLATION_FLOW_PROCESS.md, tests/installer/test_fresh_install_flow.py, tests/installer/integration/test_installation_flow.py
- **Slash Command Deployment** – Copy command and manual download flows for CLI setup.  
  _Sources_: handovers/Simple_Vision.md#L416-L432, docs/user_guides/0104_USER_TESTING_GUIDE.md, handovers/completed/0084b_agent_import_slash_commands-C.md
- **Agent Package Export (Zip + Instructions)** – Exporting personal/project agents and regeneration triggers.  
  _Sources_: handovers/Simple_Vision.md, handovers/start_to_finish_agent_FLOW.md#L740-L920
- **Dev Tools Installer (Optional Panel)** – Provisioning isolated developer utilities.  
  _Sources_: dev_tools/devpanel/scripts/devpanel_install.py, dev_tools/devpanel/docs/user_manual.md

## 2. Project Lifecycle

- **Project Creation & Mission Definition** – Creating projects, assigning vision/context, configuring context budgets.  
  _Sources_: tests/integration/test_e2e_workflows.py, docs/user_guides/orchestrator_project_launch.md, API endpoints (api/endpoints/projects.py)
- **Project Staging to Activation** – Staging flows, approval checkpoints, activating staged projects.  
  _Sources_: tests/integration/test_stage_project_workflow.py, handovers/0105_orchestrator_mission_workflow.md
- **Launch & Execution Flow** – Orchestrator run, agent handoffs, completion criteria.  
  _Sources_: handovers/start_to_finish_agent_FLOW.md, tests/integration/test_orchestration_workflow.py, tests/test_orchestrator_workflow.py
- **Succession & Handover Flow** – Manual `/gil_handover` command, automatic 90% context succession.  
  _Sources_: docs/user_guides/orchestrator_succession_guide.md, handovers/README.md (0080a), tests/integration/test_succession_workflow.py
- **Implementation & QA Flow** – Staging to implementation to QA handoff and sign-off.  
  _Sources_: docs/Vision/AGENTIC_PROJECT_MANAGEMENT_VISION.md, handovers/0106_agent_template_hardcoded_rules.md, tests/integration/test_agent_workflow.py

## 3. Agent & Template Management

- **Agent Template Creation & Editing** – Creating templates, editing instructions, toggling activation.  
  _Sources_: docs/AGENT_TEMPLATES_REFERENCE.md, src/giljo_mcp/template_manager.py, tests covering template CRUD
- **Agent Messaging Flow** – Queue interactions, websocket delivery, job status updates.  
  _Sources_: docs/AGENT_JOBS_API_REFERENCE.md, api/websocket.py, tests/integration/test_agent_workflow.py
- **External Agent Coordination Flow** – HTTP MCP workflows, external tool orchestration.  
  _Sources_: handovers/0106d_websocket_event_catalog.md, src/giljo_mcp/tools/agent_coordination_external.py
- **Agent Export/Import Flow** – Copy command, tokenized downloads, CLI integration.  
  _Sources_: handovers/Simple_Vision.md, docs/frontend sections (copy command buttons)

## 4. Task & Context Management

- **Task Creation → Assignment → Completion** – Task state transitions, notifications, reporting.  
  _Sources_: docs/AGENT_JOBS_API_REFERENCE.md, tests/integration/test_task_workflow.py (if present), src/giljo_mcp/tools/task.py
- **Context Prioritization & Chunking** – Adjusting context priorities, chunking pipelines, token budgeting.  
  _Sources_: src/giljo_mcp/context_management/chunker.py, docs/CONTEXT_MANAGEMENT_SYSTEM.md, tests covering chunking
- **Vision Document Lifecycle** – Upload, staging, chunking, activation.  
  _Sources_: docs/INSTALLATION_FLOW_PROCESS.md (Phase 2), src/giljo_mcp/context_management

## 5. Settings & Administration

- **Admin Settings Flow** – Configuring tenants, feature flags, slash command toggles, security setup.  
  _Sources_: docs/user_guides/admin_settings.md (if available), api/endpoints/configuration.py, tests/integration/test_user_management_flow.py
- **User Settings Flow** – Adjusting context priorities, notification preferences, personal agent exports.  
  _Sources_: docs/ACCESSIBILITY_VISUAL_SUMMARY.md (notifications), docs/user_guides/user_settings.md, API endpoints (api/endpoints/user_settings.py)
- **Authentication & Password Reset Flow** – Fresh installs, PIN recovery, password reset experiences.  
  _Sources_: handovers/completed/harmonized/HANDOVER_0013_SETUP_FLOW_AUTHENTICATION_REDESIGN-C.md, docs/devlog/2025-10-21_password_reset_implementation.md, tests/manual/test_auth_flows.md

## 6. Notifications & Bell Menu

- **Real-Time Notifications Flow** – WebSocket events, toast notifications, bell interactions.  
  _Sources_: docs/technical/WEBSOCKET_DEPENDENCY_INJECTION.md, docs/ACCESSIBILITY_VISUAL_SUMMARY.md (notification button), src/giljo_mcp/websocket.py
- **Job/Event Notifications** – Job completed/failed flows, orchestrator alerts, agent escalation.  
  _Sources_: docs/references/0045/USER_GUIDE.md, docs/MASTER_ORCHESTRATOR_PROMPT.md (notification copy), handovers/MCP_Tools_needs.md (message notifications)

## 7. Miscellaneous / Supporting Flows

- **Workflow Engine / Automation** – Underlying state transitions available via `workflow_engine`.  
  _Sources_: src/giljo_mcp/workflow_engine.py, tests/unit/test_workflow_engine.py
- **Download & Token Security Flow** – Tokenized download flow for agents/slash commands.  
  _Sources_: handovers/start_to_finish_agent_FLOW.md (Phase 2), docs/DOWNLOAD_TOKEN_TEST_SUMMARY.md
- **WebSocket Flow (Serena, Live Updates)** – Serena enablement and messaging.  
  _Sources_: tests/integration/test_serena_enabled_flow.py, handovers/0106d_websocket_event_catalog.md

## Next Steps for Visualization

1. **Group flows into navigation categories** (Install, Lifecycle, Templates, Settings, Notifications).  
2. **Design expandable canvases** depicting step-by-step states (tree/branch diagrams).  
3. **Link diagrams to contextual docs/tests** (hover-to-source references, badges).  
4. **Add status indicators** (implemented, in-progress, planned) based on handover state.

This inventory should guide which flows appear in the Developer Panel and how we structure expandable tree visuals and dependency maps.
