# Changelog

All notable changes to this project will be documented in this file.

The format is based on [Keep a Changelog](https://keepachangelog.com/en/1.0.0/),
and this project adheres to [Semantic Versioning](https://semver.org/spec/v2.0.0.html).

## [1.0.0] - 2026-04 (First Public Release)

### Changed
- Version alignment: all public-facing version numbers unified to 1.0.0
- Release packaging updates (0732): CHANGELOG brought current, convention violations fixed

---

## Pre-Release Development History

> The versions below are internal development milestones predating the public CE release.
> They are preserved for historical accuracy and git commit traceability.

## [Internal 4.0.0] - 2026-03-08

### Highlights
- **Perfect Score Sprint (0765a-s):** 19-session quality sprint -- 67 commits, ~12,000 lines dead code removed, codebase score raised from 7.8 to 8.35/10
- **Edition Isolation Architecture (0771):** Two-edition model (CE + SaaS) with physical directory separation, import boundary enforcement, and conditional loading patterns
- **Community Edition Branding:** GiljoAI Community License v1.0, edition badges, About dialog, licensing enforcement

### Added
- CSRF double-submit cookie protection enabled end-to-end (0765f)
- Design token system with centralized `agentColors.js` and `design-tokens.scss` (0765c, 0765p)
- Design system sample page as single source of truth for UI patterns (0765m)
- SaaS directory scaffold with `saas/`, `saas_endpoints/`, `saas_middleware/`, `frontend/src/saas/` (0771)
- CE/SaaS import boundary pre-commit hook (0771)
- Edition Isolation Guide (`docs/EDITION_ISOLATION_GUIDE.md`) -- authoritative reference for code placement
- HTTPS/SSL support with config-driven toggle
- HTTPS status indicator in Network settings tab
- About dialog with licensing information

### Changed
- ESLint warning budget locked at 8 (down from 124)
- All 342 skipped tests resolved -- zero skips remaining (0765h)
- Hardcoded tenant keys replaced with config-based resolution (0765g)
- Exception narrowing: 10 broad catches narrowed, 163 annotated with justification (0765d)
- 35 oversized test files split into 85 focused modules (0765e)
- Branding standardized: design tokens, agent colors, status colors aligned to canonical sources (0765p)
- Pre-commit ruff updated to v0.15.0

### Fixed
- Cross-tenant slash command bypass -- CRITICAL security fix (0765s)
- WebSocket subscribe tenant bypass (0765s)
- 3 runtime crash bugs: git.py TypeError, auth.py Pydantic ValidationError, git.py wrong auth dependency (0765s)
- 3 tenant isolation gaps in context, MCP session, and vision documents (0765j)
- SQLAlchemy `.is_(None)` NULL filter bug (0765j)

### Removed
- ~12,000 lines of verified dead code across 0765 sprint (19 dead ToolAccessor methods, WebSocket bridge, 24 dead backend methods, dead test infrastructure, dead frontend exports)
- Legacy `0731` code removal items resolved by 0745/0765 sprints

### Security
- CSRF protection enabled with frontend Axios interceptor
- 5 security findings fixed: JWT ephemeral secret, network auth, username enumeration, API key tracking, placeholder key (0765l)
- Cross-tenant slash command execution prevented (0765s)
- WebSocket subscription tenant bypass prevented (0765s)

## [3.7.0] - 2026-02-26

### Added
- **Multi-Terminal Production Parity (0497a-e):** Full parity between CLI and multi-terminal modes
  - Thin agent prompt replacing stale bash-script generator (0497a)
  - Agent completion result storage with auto-message to orchestrator (0497b)
  - Multi-terminal orchestrator implementation prompt (0497c)
  - Agent protocol enhancements: `/gil_add` + git commit guidance (0497d)
  - Fresh agent recovery flow with successor spawning and predecessor context (0497e)
- **Early Termination Protocol (0498):** Handover modal with two-stage retirement/continuation flow, dashboard reduced from 9 to 5 columns
- **Phase Labels (0411a):** Recommended execution order with colored pill badges in Jobs tab

### Removed
- ~11,900 lines of dead orchestration pipeline code (WorkflowEngine, MissionPlanner legacy) (0411b)

## [3.6.0] - 2026-02-16

### Added
- **API Key Security Hardening (0492):** 5-key-per-user limit, 90-day key expiry, passive IP logging, frontend expiry display with color-coded urgency
- **Agent Status Simplification (0491):** Reduced 7-status model to 4 agent-reported + Silent (server-detected) + decommissioned. Removed `failed`/`cancelled` statuses.

### Fixed
- **Tenant Isolation Audit (Feb 2026):** Full security audit remediated all CRITICAL (5) + HIGH (20) findings across 5 commits with 61 regression tests
- Auth default tenant key hardening (0054)

### Changed
- API consistency fixes: URL kebab-case standardization + HTTPException errors (0732 API)
- Message display UX: recipient names, broadcast signal, field fixes (0410)

## [3.5.0] - 2026-02-11

### Added
- **Typed Service Returns (0731a-d):** 60+ Pydantic response models, 157 TDD tests across 78 files
- **Code Cleanup Sprint (0700-0750):** Systematic cleanup -- delint, code health audit, orphan removal, service response models, audit follow-up
  - ~15,800 lines removed across ~110 files
  - Architecture score raised from baseline to 8/10

### Changed
- All service layers use Pydantic response models instead of raw dicts
- Exception-based error handling enforced across all Python layers

## [3.4.0] - 2026-01-28

### Added
- **Exception Handling Remediation REVISED (0480a-f):** Production-grade exception handling across all layers -- foundation, services, endpoints, frontend
- **360 Memory Normalization (0390a-d):** Migrated from JSONB `sequential_history` to normalized `product_memory_entries` table with proper relational integrity
- **Organization Hierarchy (0424a-n):** Multi-user workspaces with org-based isolation, User.org_id FK, AuthService org-first pattern, welcome screen + AppBar integration

### Changed
- Agent lifecycle modernized (0411-0432): proper state machine, template system, Jobs tab improvements
- Consolidated vision documents with universal summarization (0377)

## [3.3.0] - 2025-12-21

### Changed
- **MCPAgentJob Deprecation (Handovers 0367a-e)**: Completed multi-phase cleanup of legacy `MCPAgentJob` model in favor of dual-model architecture (`AgentJob` for work orders, `AgentExecution` for executor instances)
- **Identity Model**: Standardized on `AgentJob`/`AgentExecution` for all orchestrator and agent spawning operations
- **Slash Commands**: Updated `/gil_handover` to operate on `AgentExecution` only
- **Generic Agent Template**: Updated to use `agent_id` for `get_agent_mission` tool

### Added
- Migration template: `migrations/archive_mcp_agent_jobs.sql` for archiving legacy records

## [3.2.0] - 2025-11-17

### Added
- **Context Management v2.0 (Handovers 0312-0316)**: Complete refactor from v1.0 (token optimization) to v2.0 (user empowerment)
  - Two-dimensional model: Priority (1/2/3/4) x Depth (per source)
  - MCP on-demand fetching (<600 token prompts, down from 3,500+)
  - Full user control via UI
  - `depth_config` JSONB column for flexible configuration
  - Six MCP context tools for on-demand fetching
  - Real-time token estimation
  - Quality Standards field added to products table

### Changed
- **Prompt Generation**: Migrated from inline context to MCP thin client pattern (76.5% token reduction)
- **Priority System**: Migrated from v1.0 (10/7/4 scores) to v2.0 (1/2/3/4 tier system)

### Performance
- Prompt size reduced: 3,500 tokens -> <600 tokens
- Context tool response time: <100ms average
- Handles documents >100K tokens with pagination

## [3.1.1] - 2025-11-03

### Fixed
- **Thin Client Production Fixes (Handover 0089)**: External URL, health check MCP tool, copy-to-clipboard workflow

## [3.1.0] - 2025-10-31

### Fixed
- **Tenant JWT Mismatch (Handover 0078)**: Resolved multi-tenant isolation bug

## [3.0.0] - 2025-10-28

### Added
- **External Agent Coordination Tools (Handover 0060)**: 7 HTTP-based MCP tools enabling multi-agent orchestration
- **Project Launch Panel (Handover 0062)**: Two-tab interface for project activation and agent job management

## [2.5.0] - 2025-10-26

### Added
- **Vision Document Chunking (Handover 0047)**: Async conversion of chunking pipeline

### Fixed
- Vision document chunking fully operational with async-first architecture
- Product deletion with proper CASCADE cleanup

## [2.4.0] - 2025-10-25

### Added
- **Claude Code Agent Template Export (Handover 0044-R)**: Production-grade export system

## [2.3.0] - 2025-10-21

### Added
- **Password Reset Functionality (Handover 0023)**: 4-digit Recovery PIN system with rate limiting

### Security
- bcrypt hashing with timing-safe comparison for PINs

## [2.2.0] - 2025-10-16

### Added
- **Two-Layout Authentication Pattern (Handover 0024)**: Industry-standard auth architecture
- App.vue reduced from 537 lines to 58 lines (90% reduction)

## [2.1.0] - 2025-10-15

### Added
- **Documentation Validation (Handover 0012)**: 3 vision documents + 5 handover projects validated

## [2.0.0] - 2025-10-13

### Added
- **Advanced UI/UX (Handover 0009)**: 80+ custom icons, 4 mascot animation states, WCAG 2.1 AA compliance
- **User API Key Management (Handover 0015)**: Secure per-user API key system

### Security
- Frontend authentication migrated to httpOnly cookie pattern

## [1.5.0] - 2025-10-11

### Fixed
- Critical installation authentication bug preventing fresh installations

## [Internal 1.0.0] - 2024-11

### Added
- **Stage Project Feature**: 70-80% token reduction through field prioritization
- Intelligent mission generation, smart agent selection, multi-agent workflow coordination
- Real-time WebSocket updates, standardized event schemas
- 95 comprehensive tests

---

## Pre-Release Version History Summary

- **Internal 4.0.0** (2026-03-08): Perfect Score Sprint, edition isolation, CE branding and licensing
- **Internal 3.7.0** (2026-02-26): Multi-terminal production parity, early termination, phase labels
- **Internal 3.6.0** (2026-02-16): Tenant isolation audit, API key hardening, agent status simplification
- **Internal 3.5.0** (2026-02-11): Typed service returns, code cleanup sprint (~15,800 lines removed)
- **Internal 3.4.0** (2026-01-28): Exception handling, 360 Memory normalization, org hierarchy
- **Internal 3.3.0** (2025-12-21): MCPAgentJob deprecation, identity model cleanup
- **Internal 3.2.0** (2025-11-17): Context Management v2.0
- **Internal 3.1.x** (2025-10/11): Thin client fixes, tenant JWT fix
- **Internal 3.0.0** (2025-10-28): External agent coordination, project launch panel
- **Internal 2.x** (2025-10): Vision chunking, Claude Code export, password reset, auth layout, UI/UX, API keys
- **Internal 1.x** (2024-11 to 2025-10): Stage Project, installation fixes

For detailed implementation notes, see `handovers/HANDOVER_CATALOGUE.md`.
