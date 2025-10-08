# Documentation index — catalog and proposed organization

This file catalogs the top-level documents found in `docs/`, groups them into logical folders, and gives a short overview for each file. I created the destination folders and small READMEs. I did not move the original files yet — please review this index and tell me if you want me to move the files now (I can move them in bulk or iteratively).

Folders created:
- `docs/installer/` — installer & uninstaller guides, checklists, troubleshooting
- `docs/architecture/` — technical architecture, LAN setup, design decisions
- `docs/guides/` — standards, how-tos, operational guides
- `docs/research/` — research notes, proposals, plans
- `docs/projects/` — project cards, orchestration plans, flow visuals
- `docs/security/` — security policy and reports
- `docs/misc/` — miscellaneous small files (colors, assets)
- `docs/agents/` — agent templates, MCP/agent integration docs

Index (source file -> destination folder) with short overview

Installer & Uninstaller
- `Installer_Devlog_Summary.md` -> `docs/installer/`
  Summary of installer development, fixes, UX changes, migration notes and test results (SeptOct 2025).
- `INSTALLER_ERROR_HANDLING_IMPROVEMENTS.md` -> `docs/installer/`
  Focused notes on improving error handling for PostgreSQL and installer recovery flows.
- `installer_implementation_checklist.md` -> `docs/installer/`
  Implementation checklist for installer phases, testing, and docs — useful for release tracking.
- `INSTALLER_MIGRATION_SUMMARY_2025_09_30.md` -> `docs/installer/`
  Summary of migration to PostgreSQL-only installer and related process changes.
- `installer_troubleshooting.md` -> `docs/installer/`
  Troubleshooting commands and steps for CLI installer problems.
- `installer_user_guide.md` -> `docs/installer/`
  CLI quickstart and mode descriptions (developer profile, profiles, service commands).
- `UNINSTALLER_TEST_REPORT.md` -> `docs/installer/`
  Test report for the uninstaller covering all uninstall modes and verification results.
- `RELEASE_QUICK_START.md` -> `docs/installer/`
  Release checklist and quick commands for making a release and smoke-testing it.

Architecture & Deployment
- `TECHNICAL_ARCHITECTURE.md` -> `docs/architecture/`
  System-level architecture, component diagrams, deployment modes (local/LAN/WAN) and data flow.
- `Oct_6_LAN_implementation.md` -> `docs/architecture/`
  LAN enablement implementation plan and gaps identified (CORS, API key, restart flow).
- `LAN_SETUP_GUIDE.md` -> `docs/architecture/`
  Practical LAN/server-mode verification, firewall and authentication guidance.
- `PRODUCTION_READINESS_CERTIFICATION_FINAL.md` -> `docs/architecture/`
  Large production readiness certification and final validation summary.
- `PROVEN_FEATURES_TO_PRESERVE.md` -> `docs/architecture/`
  Inventory of implemented features to be retained during refactors (vision chunking, message queue patterns).
- `Platform_TESTING_MATRIX.md` -> `docs/architecture/`
  Cross-platform testing matrix and verification commands.

Guides & How-tos
- `LINTING_STANDARDS.md` -> `docs/guides/`
  Project linting/formatting/security rules, CI hooks and developer IDE settings.
- `MESSAGE_QUEUE_GUIDE.md` -> `docs/guides/`
  Design and operations of the DB-backed message queue (lifecyle, best practices).
- `TESTING_POSTGRESQL.md` -> `docs/guides/`
  PostgreSQL testing strategy and recommended commands.
- `TOOL_DETECTION_AND_SETUP.md` -> `docs/guides/`
  Tool detection and first-run wizard architecture; how the setup wizard separates install vs user config.
- `WIZARD_YAML_TO_DB_CONVERSION.md` -> `docs/guides/`
  Notes on converting wizard YAML/JSON state into DB-backed setup state (migration guidance).

Research / Plans / Proposals
- `MCP_REGISTRATION_RESEARCH.md` -> `docs/research/`
  Research on registering multiple AI CLI tools (Claude, Codex, Gemini) and adapters for TOML/JSON configs.
- `LocalLLM_plan.md` -> `docs/research/`
  Local LLM tier matrix, serving, quantization and routing strategy for on-prem model tiers.
- `PRODUCT_PROPOSAL.md` -> `docs/research/`
  High-level product proposal and market positioning.
- `PRODUCT_PROPOSAL_CONTINUED.MD` -> `docs/research/`
  Continuation and extended business notes.
- `INTEGRATE_CLAUDE_CODE.md` -> `docs/agents/`
  Detailed integration plan for Claude Code sub-agent orchestration (modes, bootstrapping agent profiles).
- `LocalLLM_plan.md` -> `docs/research/` (duplicate noted)

Projects & Orchestration
- `PROJECT_ORCHESTRATION_PLAN.md` -> `docs/projects/`
  Master plan for orchestrating projects and templates, activation flow and dashboard integration.
- `PROJECT_CARDS.md` -> `docs/projects/`
  Ready-to-use project cards (missions) for the orchestrator to run.
- `PROJECT_FLOW_VISUAL.md` -> `docs/projects/`
  Visual ASCII/flow timeline of project dependencies and critical path.
- `PRODUCT_AGENT_TEMPLATES.md` -> `docs/agents/`
  Agent profile templates to be installed into Claude or other tools.

Security & Policy
- `SECURITY.md` -> `docs/security/`
  Security policy, scanning tools (Bandit/Trivy), intentional exceptions and deployment guidance.

Misc / Other
- `README_FIRST.md` -> `docs/misc/`
  High-level README and quick navigation for the docs folder (READ FIRST overview).
- `Techdebt.md` -> `docs/misc/`
  Consolidated technical debt, quick fixes, and recommended release priorities.
- `TOOL_DETECTION_AND_SETUP.md` -> `docs/guides/` (duplicate noted)
- `Website colors.txt` -> `docs/misc/`
  Color palette used by the project (UI design tokens).

Notes & next steps
- I created the folders and small README placeholders for each category (see below). Please review the proposed destinations and summaries. If you approve, I can move the actual markdown files into the folders and update internal links/references. I can move all files in one batch or do it category-by-category. Tell me which you prefer.

If you'd like me to start moving files now, respond "Move now" (I will then relocate files and update this index with exact new paths). If you'd rather adjust categories first, tell me what to change and I'll update the index.
# Documentation Index — GiljoAI MCP

This index was generated automatically (files read on Oct 7, 2025) and provides a single place to find the project's documentation and short descriptions.

Notes:
- One attempted read failed: `"Website colors.txt"` (the quoted filename could not be found). If a file named `Website colors.txt` exists without the surrounding quotes, tell me and I'll add it.

Docs included (file -> short purpose):

- `Oct_6_LAN_implementation.md` — LAN enablement implementation plan: gaps, endpoints, UI flows, and rollout plan.
- `PLATFORM_TESTING_MATRIX.md` — Cross-platform testing matrix and verification commands for Windows/macOS/Linux.
- `PROJECT_CARDS.md` — Project cards / roadmap items and short milestone descriptions.
- `PROJECT_FLOW_VISUAL.md` — ASCII and schedule-style visualization of the project flow and critical path.
- `PROVEN_FEATURES_TO_PRESERVE.md` — Features that must be preserved during refactors and why.
- `SECURITY.md` — Security policy, scans, and intentional exceptions.
- `SUB_AGENT_INTEGRATION_SUMMARY.md` — Summary and plan for integrating Claude Code sub-agents.
- `WIZARD_YAML_TO_DB_CONVERSION.md` — (If present) guide for migrating wizard YAMLs into DB-backed configs.
- `UNINSTALLER_TEST_REPORT.md` — Uninstaller test results and recommendations.
- `TOOL_DETECTION_AND_SETUP.md` — Tool detection and first-run setup/wizard architecture.
- `TESTING_POSTGRESQL.md` — PostgreSQL testing strategy and commands.
- `TECHNICAL_ARCHITECTURE.md` — System architecture, components, and schemas.
- `Techdebt.md` — Consolidated technical debt and future enhancements.
- `RELEASE_QUICK_START.md` — Release checklist and quick start for creating releases.
- `README_FIRST.md` — Top-level README-first project navigation and status.
- `PROJECT_ORCHESTRATION_PLAN.md` — Orchestration plan and project cards mapping.
- `PRODUCT_PROPOSAL_CONTINUED.MD` — Product proposal continuation and notes.
- `PRODUCT_PROPOSAL.md` — Main product proposal and positioning.
- `PRODUCT_AGENT_TEMPLATES.md` — Agent template guidance and examples.
- `PRODUCTION_READINESS_CERTIFICATION_FINAL.md` — Certification / validation summary for production readiness.
- `MESSAGE_QUEUE_GUIDE.md` — Design and operation guide for the database-backed message queue.
- `MCP_REGISTRATION_RESEARCH.md` — Research into registering MCP servers for various CLI tools.
- `LINTING_STANDARDS.md` — Ruff/ESLint/Prettier standards and CI enforcement.
- `LAN_SETUP_GUIDE.md` — Step-by-step LAN/server mode setup and troubleshooting (user-facing guide).
- `INTEGRATE_CLAUDE_CODE.md` — Detailed plan for integrating Claude Code sub-agents with MCP.
- `CONFIGURATION_AND_REFERENCE_INDEX.md` — Index of configuration and environment files.
- `ARCHITECTURE_V2.md` — HTTP-based multi-user v2 architecture overview and migration.
- `AI_TOOL_INTEGRATION.md` — General AI tool integration guide and register scripts.
- `AI_CODING_TOOLS_COMPARISON.md` — Comparison of multi-agent capabilities across AI coding tools.
- `AGENT_INSTRUCTIONS.md` — Agent instructions, ports, project structure, and development constraints.

If you'd like I can:

- Create a categorized folder structure (e.g., `docs/architecture/`, `docs/manuals/`, `docs/integration/`) and move or symlink these files into it.
- Produce per-file one-paragraph summaries inside `docs/INDEX.md` (longer summaries).
- Generate a simple HTML TOC from this index for quick browsing.

What would you like me to do next? (I can start with move/categorize, or generate longer summaries.)
