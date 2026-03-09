# Reference_docs Resource Index

**Created**: 2026-03-09
**Purpose**: Catalog every file in handovers/Reference_docs/ with category, description, and retention recommendation.

---

## Category Legend

| Category | Meaning |
|----------|---------|
| **VISION** | Product vision, intent, or philosophy |
| **PROTOCOL** | Agent protocols, workflows, or operational procedures |
| **REFERENCE** | Technical reference (schema maps, tool catalogs, etc.) |
| **LOG/SCRATCH** | Test runs, logs, scratch notes, temporary work |
| **BINARY** | Images, PDFs, presentations, archives |
| **STALE** | Outdated content superseded by later work |

## Recommendation Legend

| Recommendation | Meaning |
|----------------|---------|
| **KEEP** | Still-relevant vision docs, active protocols, useful references |
| **ARCHIVE** | Historically interesting but superseded -- could move to completed/reference/ |
| **DELETE** | Logs, scratch notes, duplicates, stale content with no ongoing value |

---

## File Index

| File | Category | Description | Recommendation |
|------|----------|-------------|----------------|
| AGENT_FLOW_SUMMARY.md | **REFERENCE** | Compact quick-reference for the entire agent flow: architecture diagram, key terminology, 5-task staging workflow, MCP tools table, execution modes, WebSocket events, and slide-by-slide descriptions of the workflow presentation (39 slides). Last verified 2026-02-28. | **KEEP** |
| agent_behaviouir.txt | **LOG/SCRATCH** | Raw developer notes (unedited, with typos) capturing early thinking about agent_id vs job_id hierarchy, orchestrator self-job writing, prompt injection concerns, and Claude Code CLI vs multi-terminal modes. | **ARCHIVE** |
| agent_seeding.md | **STALE** | Pasted transcript of an investigation session about the three-layer instruction architecture (Handover 0254), agent template seeding, and the ZIP export system. Findings incorporated into later handovers. | **DELETE** |
| claude-prompt-3e257447.md | **REFERENCE** | Detailed implementation plan for fixing alpha test failures: message counter bugs, UUID normalization, TodoWrite prompt strengthening, and a reactive feedback system. References Handovers 0401b, 0405, 0406. | **ARCHIVE** |
| code_revew_nov24.md | **REFERENCE** | Codebase health scorecard from November 24, 2025. Tracks improvements and regressions across frontend, services, orchestration, and integrations. Contains actionable recommendations. | **ARCHIVE** |
| Dynamic_context.md | **VISION** | Extensive design document on dynamic agent discovery. Covers Claude Code CLI mode vs multi-terminal mode, context sources, and the prompt flow vision. Contains many inline questions from the product owner. | **ARCHIVE** |
| filing_tests.md | **REFERENCE** | Registry of 17 pre-existing failing tests after orchestration tools-to-service consolidation. Categorized into D, E, and G groups. Includes pytest commands. Created 2026-02-16. | **ARCHIVE** |
| gemini_vs_claude_agent_templates.md | **REFERENCE** | Side-by-side comparison of Gemini CLI vs Claude Code CLI agent template formats: file structures, configuration fields, command syntax, subagent approaches, and a unified schema proposal. | **KEEP** |
| giljoai workflow.pdf | **BINARY** | PDF export of the 39-slide workflow presentation (~373 KB). Duplicate of the PPTX source and the JPG slide exports. | **DELETE** |
| giljoai workflow.pptx | **BINARY** | PowerPoint source file for the 39-slide workflow presentation (~180 KB). Slide content is transcribed in AGENT_FLOW_SUMMARY.md and exported as JPGs in the subfolder. | **ARCHIVE** |
| HARMONIZED_WORKFLOW.md | **PROTOCOL** | Harmonized staging-to-implementation workflow. Button-to-endpoint mapping (Stage Project = /activate), field naming conventions (description=human, mission=AI), status translation (pending to waiting), and complete Phase 1/Phase 2 flows with ASCII UI wireframes. | **KEEP** |
| IMPLEMENTATION_CONTEXT.md | **REFERENCE** | Deep companion to the Master Implementation Plan (~922 lines). Covers 4 frontend API pattern fixes with exact file:line references, 0377 vision consolidation bug, 0353 team awareness details, database schema status, and message counter architecture. | **ARCHIVE** |
| launch jobs.zip | **BINARY** | Opaque ZIP archive (~1.3 MB). No accompanying documentation or manifest. Contents unknown. | **DELETE** |
| log_backend.md | **LOG/SCRATCH** | Raw server startup log from 2026-01-02. Shows FastAPI v2.0 binding to 0.0.0.0:7272, CORS origins, rate limiting at 300 req/min, and security middleware initialization. No analytical content. | **DELETE** |
| MASTER_IMPLEMENTATION_PLAN_VALIDATED.md | **REFERENCE** | Validated roadmap from 2026-01-28. Verification table corrects false claims (0377 vision columns do NOT exist, 0700 series NOT STARTED). Technical debt inventory: 46 DEPRECATED markers, 43 TODO markers, 168 skipped tests. Estimated 115-177 hours remaining. | **ARCHIVE** |
| Mcp_tool_catalog.md | **REFERENCE** | Handover 0270 documentation for MCPToolCatalogGenerator. Catalogs 20+ MCP tools across 5 categories (Orchestration, Context, Communication, Tasks, Project). Defines agent-type-specific subsets (orchestrator gets 13 tools, documenter gets 8). | **ARCHIVE** |
| MULTI_TERMINAL_CHAIN_STRATEGY.md | **PROTOCOL** | Strategy document for chained multi-terminal execution. PowerShell spawn syntax with color-coded tabs, chain log JSON pattern for inter-session context forwarding. Includes lessons learned from 0387 Phase 4 (5 terminals, 75 files, 8321 insertions). | **KEEP** |
| no_launch_button.jpg | **BINARY** | Screenshot (~225 KB) of the Launch tab UI showing Project Description, Orchestrator Generated Mission, Agent Team panel (OR ORCHESTRATOR, IM IMPLEMENTER x2, DO DOCUMENTER), and the Launch Jobs button. | **ARCHIVE** |
| PHASE_1_User_Copies_STAGING_Prompt.txt | **PROTOCOL** | Canonical two-phase prompt example. Phase 1: staging prompt with identity block, MCP connection, 6-step startup sequence, agent_type lifecycle table, forbidden patterns. Phase 2: implementation prompt with Task tool spawning syntax, monitoring via get_workflow_status, completion flow. | **KEEP** |
| QUICK_LAUNCH.txt | **PROTOCOL** | Comprehensive handover execution guide (~2048 lines, 12 sections). Covers TDD discipline, architectural discipline, code quality standards, execution workflow, GiljoAI-specific patterns, deliverables, critical checks, command reference, troubleshooting, scope management anti-patterns, and refactor instructions (4-phase pattern with cascade analysis). | **KEEP** |
| serena.jpg | **BINARY** | Screenshot (~70 KB) of the Serena MCP Advanced Settings dialog showing toggles for Use in prompts, Tailor by mission, Dynamic tool catalog, and Prefer range reads. | **ARCHIVE** |
| Simple_Vision.md | **VISION** | Product vision and user journey (~475 lines). Covers product purpose, tenancy hierarchy, agent template system (6 defaults, 3-layer caching), context prioritization, products/projects/tasks/jobs workflows, 360 memory, MCP integration, installation, and end-to-end user journey. Updated 2026-03-07 with SaaS timeline note. | **KEEP** |
| start_to_finish_agent_FLOW.md | **PROTOCOL** | Unified workflow documentation with dual-status architecture (7 canonical DB states plus API aliases), two spawning types (Type 1 MCP server vs Type 2 CLI native), and terminology alignment. Last updated 2025-11-29. | **KEEP** |
| start_to_finish_agent_FLOW.md.old | **STALE** | Earlier version of start_to_finish_agent_FLOW.md dated 2025-11-06. Fully superseded by the current version. | **DELETE** |
| testrun_Jan_2nd.md | **LOG/SCRATCH** | Raw alpha test transcript from January 2, 2026. Shows orchestrator testing the implementation phase with 3 agents on TinyContacts project. Contains unedited AI thinking traces and debug output. | **DELETE** |
| thing_to_test_again.txt | **LOG/SCRATCH** | 8-line scratch note: fixed the job id vs agent id bug for orchestrator, Launch Successor Orchestrator Instance 2, learn more here. No context or detail. | **DELETE** |
| Worflow.jpg | **BINARY** | Architecture diagram (~278 KB) showing GiljoAI MCP Server (management features, server core, orchestration features) connected to Client PC (Browser, Terminal Agents, Project Files/Repo). | **ARCHIVE** |
| Workflow architecture.pdf | **BINARY** | PDF of architecture diagram (~80 KB). Likely a duplicate or alternate export of Worflow.jpg content. | **ARCHIVE** |

### Subfolder: Workflow PPT to JPG/

| Item | Details |
|------|---------|
| **Contents** | 39 JPG files (Slide1.JPG through Slide39.JPG) |
| **Total size** | ~5.8 MB |
| **Description** | Individual slide exports from giljoai workflow.pptx. Each slide covers a specific aspect of the GiljoAI MCP workflow: architecture, agent lifecycle, staging process, implementation modes, WebSocket events, and system components. |
| **Category** | **BINARY** |
| **Recommendation** | **ARCHIVE** -- Slide content is fully transcribed in AGENT_FLOW_SUMMARY.md. The JPGs are useful for visual reference but not essential. |

---

## Summary Statistics

| Recommendation | Count | Files |
|----------------|-------|-------|
| **KEEP** | 8 | AGENT_FLOW_SUMMARY.md, gemini_vs_claude_agent_templates.md, HARMONIZED_WORKFLOW.md, MULTI_TERMINAL_CHAIN_STRATEGY.md, PHASE_1_User_Copies_STAGING_Prompt.txt, QUICK_LAUNCH.txt, Simple_Vision.md, start_to_finish_agent_FLOW.md |
| **ARCHIVE** | 12 | agent_behaviouir.txt, claude-prompt-3e257447.md, code_revew_nov24.md, Dynamic_context.md, filing_tests.md, IMPLEMENTATION_CONTEXT.md, MASTER_IMPLEMENTATION_PLAN_VALIDATED.md, Mcp_tool_catalog.md, giljoai workflow.pptx, no_launch_button.jpg, serena.jpg, Worflow.jpg, Workflow architecture.pdf, Workflow PPT to JPG/ |
| **DELETE** | 8 | agent_seeding.md, giljoai workflow.pdf, launch jobs.zip, log_backend.md, start_to_finish_agent_FLOW.md.old, testrun_Jan_2nd.md, thing_to_test_again.txt, _content.txt, _gen.py |

---

## Retention Rationale

**KEEP (8 files):** These are actively referenced documents that provide current, accurate information about the system architecture, workflows, and vision. They serve as the canonical reference set for onboarding and agent operations.

**ARCHIVE (12 files + subfolder):** Historically valuable documents that have been superseded by later handovers or consolidated references. They contain useful context for understanding design decisions but are not required for day-to-day operations. Recommended destination: a completed/reference/ subfolder.

**DELETE (8+ files):** Raw logs, scratch notes, duplicate binary exports, stale transcripts, and temporary utility files with no ongoing value. The information they contain is either trivially recoverable from git history or has been incorporated into KEEP/ARCHIVE documents.

**Note on temporary files:** _content.txt (test placeholder) and _gen.py (file-writing utility) in this directory appear to be artifacts from a previous session and should be removed.
