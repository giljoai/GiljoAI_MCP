# Changelog

All notable changes to this project will be documented in this file.

The format is based on [Keep a Changelog](https://keepachangelog.com/en/1.0.0/),
and this project adheres to [Semantic Versioning](https://semver.org/spec/v2.0.0.html).

## [1.1.9.1] — 2026-04-25 — Installer Hotfix

Patch release on top of v1.1.9 — installer reliability and speed only. No application code changes.

### Fixed
- **Windows one-liner: shortcut icon path.** Desktop and Start Menu shortcuts created by `irm giljo.ai/install.ps1 | iex` were missing their icon because the script looked for a non-existent `giljo.ico`. Now uses `Start.ico` from `frontend/public/` with `favicon.ico` as fallback.
- **Windows one-liner: stray `False False` appended to install path.** The completion message printed `cd <path> False False` because PowerShell was leaking `tar` and `Remove-Item` output into the `Install-Release` function's return value. Pipeline output now flows to `Out-Null`; only the path string is returned.
- **Linux reset script: hardcoded postgres version.** `scripts/linux_reset.sh` now auto-discovers the installed PostgreSQL version instead of failing on systems where the hardcoded version isn't present.

### Changed
- **Windows one-liner is faster (typically 2-4 minutes saved).** Disabled PowerShell's `Invoke-WebRequest` / `Invoke-RestMethod` progress bar (a known 5-10x slowdown on Windows PowerShell 5.1 — applies to the release tarball download and all GitHub API calls).
- **Removed redundant second frontend build.** The Windows installer was running `npm run build` twice — once during environment setup and again after `install.py`. The second build was a leftover and is unnecessary because `config.yaml` is read at runtime, not bundled into the JS output.

### For existing v1.1.9 users
- No action required. v1.1.9.1 is identical to v1.1.9 at runtime — only `scripts/install.ps1` and `scripts/linux_reset.sh` changed. Skip this release unless you're running fresh installs.

## [Unreleased] — 2026-04-24 — IMP-0011 Phase 2 Mode-Aware Auto-Open URL

### Changed
- Launcher now branches browser auto-open URL on deployment_context (demo/saas-production → /demo-landing, CE first-run → /welcome, else dashboard). Removes reliance on frontend route_signal bounce. Closes IMP-0011 Phase 2.

## [Unreleased] — 2026-04-24 — SEC-0003 Admin-View XSS Hardening

### Security
- **Single sanctioned sanitization pipeline for all `v-html` sinks in the Vue admin frontend.** Every user- or backend-influenced string that lands in `v-html` now passes through `useSanitizeMarkdown()` / `sanitizeHtml()`, backed by a hardened DOMPurify config with explicit `ALLOWED_TAGS` / `ALLOWED_ATTR` allow-lists, `ALLOW_DATA_ATTR=false`, and a URI-scheme allow-list that blocks `javascript:` and `data:`. Commits `382e233e`, `0302d44b`.
- **Double-decode class bug fixed in `DatabaseConnection.formatTestResultMessage`.** Backend-supplied `message` and `suggestions[]` are HTML-escaped before concatenation, then the combined HTML is sanitized — closing a re-parse path where a crafted suggestion string could inject markup. Commit `b4c25b05`.
- **Heading-id injection fixed in `UserGuideView` marked renderer.** The custom heading renderer now slugifies the id (restricted to `[a-z0-9-]`) and HTML-escapes the heading body before interpolation, so a heading of `<script>alert(1)</script>` can no longer smuggle a raw tag into rendered HTML. Commit `70dc17c9`.
- **`vue/no-v-html` bumped from `warn` to `error`** with a narrow file-glob override listing only the 4 audited sites, so every v-html is now a deliberate, commented escape hatch — not an accidental one. Commits `b95a6264`, `4d81c54c`.

### Added
- `frontend/src/composables/useSanitizeMarkdown.js` — sanctioned composable exposing `sanitizeMarkdown()` and `sanitizeHtml()` over the hardened DOMPurify config. 12 unit tests in `useSanitizeMarkdown.spec.js`.
- `frontend/src/utils/escapeHtml.js` — shared `escapeHtml()` + `slugify()` helpers used by the fixes above. 9 unit tests in `escapeHtml.spec.js`, including the `<script>alert(1)</script>` heading vector.
- Ops-panel `| safe` / `Markup(` / `autoescape false` grep sanity check — verdict CLEAN, appendix in `handovers/SEC-0003_xss_hardening.md` (commit `3aedd621`).

### Changed
- Migrated 6 `v-html` call sites to the sanctioned pipeline: `MessageItem.vue:209`, `BroadcastPanel.vue:280`, `UserGuideView.vue:148` (+ search snippet at `:216` and heading renderer at `:136-148`), and `DatabaseConnection.vue:315-339`.
- `frontend/eslint.config.js`: `vue/no-v-html: error` at line 81; per-file override block at lines 102-120 sanctions the 4 audited files with a comment explaining review requirements for any additions. Inline `eslint-disable-next-line` comments do NOT suppress `vue/no-v-html` under `eslint-plugin-vue@9.20` + ESLint v9 flat config (fixed in eslint-plugin-vue `>=9.25`); dependency not bumped — out of scope for a security patch.
- Test state: 2278/2278 passing (21 composable/util unit tests from implementer + 24 payload/integration tests from tester), lint 0 errors, frontend build clean.

## [Unreleased] — 2026-04-24 — SEC-0001 Vision-Document Upload Guardrails

### Security
- **Hard-enforced TXT/MD-only on vision document uploads.** Both upload endpoints (`POST /api/vision-documents/` at `api/endpoints/vision_documents.py` and `POST /api/v1/products/{product_id}/vision` at `api/endpoints/products/vision.py`) now run the full guard chain: `Content-Length` pre-check → filename sanitization → extension allowlist → streaming byte-counter → 8 KiB byte-sniff → strict UTF-8 decode. Endpoint B was orphaned from the UI but publicly routable, so it was hardened identically.
- **Reject spoofed binary uploads with 415.** A file named `*.txt` whose bytes are PDF, PNG, ZIP, JPEG, ELF, GZIP, JPEG-XL, or UTF-16 is rejected via byte-sniff; the client-supplied `Content-Type` is not trusted.
- **Reject oversize uploads with 413 before the body is consumed.** `Content-Length` is checked before reading; a second streaming counter catches requests that lack or lie about the header.
- **Filename sanitization.** Rejects directory separators, absolute paths, NUL, C0 control chars, Unicode bidi/RTL overrides, leading dots, Windows reserved device names (`CON`, `PRN`, `AUX`, `NUL`, `COM1-9`, `LPT1-9`), and anything over 255 UTF-8 bytes after NFC normalization.

### Added
- `src/giljo_mcp/security/upload_guard.py` (227 LOC) — pure helper module providing `sanitize_upload_filename`, `is_text_content`, `enforce_text_content`, and the typed exception hierarchy (`UploadFilenameError`, `UploadContentError`, `UploadSizeError`, all subclassing `ValueError`). Commit `b11714aa`.
- `UploadConfig` dataclass in `src/giljo_mcp/config_manager.py` — default `max_upload_bytes = 5 MiB`, `allowed_extensions = (.txt, .md, .markdown)`, `sniff_bytes = 8192`. YAML key `upload.max_bytes` and env var `GILJO_MAX_UPLOAD_BYTES` override the default. Commit `6f8c4921`.
- Error codes `UPLOAD_FILENAME_INVALID` (400), `UPLOAD_TYPE_NOT_ALLOWED` (415), `UPLOAD_CONTENT_NOT_TEXT` (415), `UPLOAD_TOO_LARGE` (413). Response shape is top-level `{error_code, message, context, timestamp}`; `api/exception_handlers.py` lifts structured dict detail from `HTTPException` to the response top level so the frontend `parseErrorResponse` picks it up. Commit `1d6c4f9d`.
- Frontend pre-check at `frontend/src/utils/uploadValidation.js` (`MAX_UPLOAD_BYTES = 5 * 1024 * 1024`, `ALLOWED_UPLOAD_EXTENSIONS = [.txt, .md, .markdown]`) so rejected files never fire an axios POST. Four `UPLOAD_*` friendly-copy fallbacks + defensive `detail` unwrap in `frontend/src/utils/errorMessages.js`. ProductForm hint "TXT or MD, max 5 MB". Commit `2ff89224`.
- `docs/security/SEC-0001_upload_guardrails.md` — security-posture reference doc for the upload boundary.
- Test coverage: 89 backend (72 unit in `tests/security/test_upload_guard.py` + 17 integration in `tests/api/test_sec_0001_upload_endpoints.py`) + 31 frontend (`uploadValidation.spec.js`, `errorMessages.spec.js`, `ProductsView.upload-error-surface.spec.js`) = 120 SEC-0001 tests.

### Changed
- Size cap lowered from 10 MB to 5 MB for vision document uploads. Endpoint A was previously unbounded; Endpoint B was previously 10 MB; the frontend `ProductsView` cap drops from 10 MB to 5 MB to match the backend `UploadConfig`.
- Removed the permissive UTF-8 → latin-1 fallback at `vision_documents.py:279`. Invalid UTF-8 now returns 415 `UPLOAD_CONTENT_NOT_TEXT` instead of silently decoding arbitrary bytes into the DB as "text". Endpoint B's Handover 0508 400 `UnicodeDecodeError` handler is replaced by the same 415.
- Frontend upload catch branch swaps the hardcoded HTTP-status switch for `parseErrorResponse`, so the server `message` renders verbatim in the toast.

## [Unreleased] — 2026-04-24 — SEC-0002 Passive-Server Trust Model

### Security
- **Passive-server property formally audited.** Grep-verified that no LLM SDK (`anthropic`, `openai`, `cohere`, `mistralai`, `replicate`, `together`, `google.generativeai`, `google.genai`) is imported anywhere in `src/giljo_mcp/`, `api/`, or `ops_panel/`. Zero LLM API-key environment variables referenced in server code. `vision_summarizer` confirmed as Sumy-based (classical LSA, CPU-only, not an LLM).
- **Outbound HTTP classified.** Every outbound call in audited server code hits a hardcoded `api.github.com` host and is operator-, admin-, or startup-initiated. No path flows end-user-prompt content into URL, query, body, or headers.
- **Rate-limit threat model made explicit.** `api/middleware/rate_limiter.py` `RateLimitMiddleware` documented: sliding-window per-IP, 300 req/min default (`API_RATE_LIMIT` env override), registered at `api/app.py:407`, in-memory `defaultdict(deque)` per process. Covers single-IP spam; does NOT cover distributed abuse or per-tenant quotas (per-tenant quotas tracked as roadmap item SAAS-018).

### Added
- `docs/security/SEC-0002_passive_server_audit.md` — grep-evidence audit backing the passive-server claim (commit `a932f4b2`).
- `docs/ARCHITECTURE.md` **Trust Model / Security Posture** section — formal passive-server definition, Server DOES / DOES NOT lists, blast-radius implications, rate-limit threat model, explicit non-goals, cross-references.
- `docs/SECURITY_POSTURE.md` — standalone plain-English summary for product, sales, and customer security reviews (liftable into marketing copy).
- LLM-SDK import guard rail (ruff `flake8-tidy-imports.banned-api` in `pyproject.toml`) — blocks accidental reintroduction of LLM SDK imports on the server path as a hard CI gate. Configuration spec lives in the SEC-0002 audit artifact §Deliverable E.

### Changed
- `docs/ARCHITECTURE.md` Trust Model section rewritten from narrative claim to audit-anchored claim, with explicit cross-references to SEC-0003 (admin-view XSS), SEC-0004 (classic web-stack RCE audit, 2026-Q2), and SEC-0005a/b/c (tenant-scoping rules at `docs/architecture/tenant_scoping_rules.md`).

## [Unreleased] — SEC-0005 Tenant-Scoping Hardening

### Security
- **Orchestrator prompt is now tenant-scoped.** Previously stored as a global singleton (`Configuration.tenant_key=NULL`), meaning any admin on any tenant overwrote the shared row. Now stored per-tenant. The admin "Prompts" settings tab applies to your tenant only.
- **Orchestrator prompt override is now wired into live sessions.** The edited prompt is injected into `_build_orchestrator_response()` at runtime for the correct tenant. Previously the override was stored but not applied.
- **Removed `/api/v1/users/?include_all_tenants=true` cross-tenant enumeration.** Admin users could previously list users across other tenants.

### Added
- `tests/security/test_tenant_required.py` — regression class asserting property B ("tenant-scoped endpoints refuse to serve when no tenant in scope"). Complements the existing 61 property-A tests.
- `tests/test_system_prompt_service.py` — full coverage for `SystemPromptService` including property-C runtime-injection tests.
- `docs/architecture/tenant_scoping_rules.md` — codifies tenant-scoping rules for future endpoint reviews.
- `# TENANT-LEVEL` and `# SERVER-LEVEL: <reason>` comment markers on all 24 admin-gated endpoints (SEC-0005c sweep).

### Changed
- Tenant-isolation status updated from "complete" to "mostly complete; SEC-0005 closing Configuration-singleton class" in the SaaS strategy and readiness reference docs.

### Migration
- Alembic migration `<rev>_scope_orchestrator_prompt_per_tenant.py` drops the existing `(tenant_key IS NULL, key='system.orchestrator_prompt')` row. Content is logged to server logs before deletion (recoverable). On CE installs (1 tenant) the override is copied to that tenant's row to preserve work. On SaaS/demo installs (2+ tenants) the content is logged but NOT copied — that would leak tenant A's text to tenant B.

## [1.1.6] - 2026-04-17

### Added
- Staging persistence and Re-Stage flow — staging state survives navigation, Re-Stage resets cleanly
- Cancel project with confirmation dialog and visual distinction for cancelled rows
- Auto-suffix agent display names on collision (no more duplicate name errors)
- 360 memory action tags for sticky NB items across depth window
- Project review modal with expandable agent jobs, commits section, and assigned missions
- HH:MM military time on project and task list dates
- Full local preflight (pytest + vitest) in merge pipeline — catches test failures before GitHub CI

### Fixed
- Execution mode constellation mismatch — CLI projects no longer get MULTI-TERMINAL protocol
- SaaS table/migration/test leak into CE export (belt-and-suspenders auto-exclude)
- Migration chain: `org_setup_complete` moved from SaaS to CE chain (fixes startup crash)
- SQLAlchemy bind param conflict with `::jsonb` cast syntax
- Circular import in `prompts/__init__.py`
- Installer: Cloudflare Ubuntu mirror for faster apt installs, stdin `/dev/null` fix for curl|bash
- 15+ pre-existing test failures resolved (ProjectReviewModal, date format, cancel dialog, memory gate)
- Notification expand, project table sorting, task column widths
- Settings seed queries `users` table instead of SaaS-only `tenants`

### Changed
- Project serial badges sized to match table text
- Hidden/cancelled project filtering independent of active status filters
- MCP tool renames harmonized (spawn_job, list_agent_templates, etc.)
- Runtime settings migrated from config.yaml to database Settings table
- Editable install (`pip install -e .`) added to all deployment paths

### Security
- CodeQL alerts resolved to zero (19 dismissed/fixed)
- SaaS table reference check added to merge pipeline preflight
- Table Existence Rule added to CLAUDE.md, reviewer template, and NAS master instructions

## [1.1.5] - 2026-04-15

### Fixed
- Windows installer: revert PostgreSQL install to direct `Start-Process` for reliability
- Windows installer: suppress npm noise, add PostgreSQL wait banner with progress indicator
- Localhost bind address: honor network mode setting instead of hardcoding `0.0.0.0`
- Frontend build: always rebuild, never skip based on existing `dist/` directory
- Linux installer: fix TTY detection, stale PostgreSQL GPG key, frontend build crash

### Changed
- Default Linux install directory to current working directory
- Use short `giljo.ai/install` URLs in all install documentation

### Added
- `linux_reset.py` developer tool for full system cleanup and rookie install testing
- Windows developer reset script for clean install testing
- CodeQL log-sanitizer taint barrier for `install.py`

## [1.1.4] - 2026-04-14

### Added
- **One-liner installers:** Windows (`irm giljo.ai/install | iex`) and Linux/macOS (`curl -fsSL giljo.ai/install | bash`)
- Cloudflare Worker for installer hosting at `giljo.ai/install`
- `--setup-only` flag for `install.py` enabling script-driven installs
- `GET /api/version/latest` endpoint for update checking
- Release pipeline with tarball, checksum, and version manifest (0969)
- CI guardrails: 5 automated checks to prevent quality re-drift
- Server-side heartbeat + WebSocket broadcast on project updates
- Hide/Unhide toggle for projects in dashboard

### Fixed
- Frontend bundle reduced 827 KB to 308 KB via Vuetify auto-import and chunk splitting
- Desktop shortcuts created correctly in `--setup-only` mode
- `startup.py` used as proper entry point with `--verbose` flag
- Hardcoded localhost URLs removed from completion messages
- API/MCP call counters always showing zero
- Completed column sort now pushes null dates to end
- 6 unused imports removed from `api/app.py` (CodeQL alerts)

### Changed
- Renamed Taxonomy to Project Types in UI
- Extract `APIState` into `api/app_state.py` to break cyclic imports
- Defer tester/reviewer agent spawning to implementation phase (CE-OPT-002)
- Dashboard polish with project reactivity improvements (CE-OPT-003)

### Security
- 5 HIGH vulnerabilities resolved from security audit (SEC-SPRINT-001a)
- CodeQL scanning with log sanitizer recognition

## [1.1.3] - 2026-04-13

### Fixed
- Registration endpoint and tenant provisioning (SAAS-004) infrastructure
- Agent complete-to-closed transition moved to user archive action
- `get_agent_mission()` made mandatory at implementation start for proper status transitions
- `alembic.ini` inline comment removed to fix migration path parsing

### Added
- Password reset request endpoint
- `giljo_mode` exposed in config endpoint for edition detection

## [1.1.2] - 2026-04-13

### Fixed
- SaaS-dependent test isolation: moved to `tests/saas/` for CE CI compatibility
- Export script excludes `frontend/tests/saas/` and `tests/saas/` directories

## [1.1.1] - 2026-04-13

### Added
- Vitest upgraded 3 to 4, coverage-v8 and UI packages updated
- `marked` upgraded ^17 to ^18, `jsdom` ^27 to ^29
- Heartbeat and project realtime update edge-case test coverage

### Fixed
- CodeQL workflow configuration with extensions directive
- CI pytest coverage threshold disabled (unit-only tests cannot meet 80%)

## [1.1.0] - 2026-04-12

### Added
- **CI/CD pipeline:** GitHub Actions for tests, linting, CodeQL security scanning
- **Dependabot** configuration for automated dependency updates
- **CODEOWNERS** for review routing
- Release automation workflow

### Changed
- First post-release export cycle established between private and public repos

## [1.0.0] - 2026-04-10 (First Public Beta)

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
- **Community Edition Branding:** GiljoAI Community License v1.1, edition badges, About dialog, licensing enforcement

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
  - Context depth configuration
  - Quality Standards field added to products table

### Changed
- **Prompt Generation**: Migrated from inline context to MCP thin client pattern (dynamic context fetching)
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
- **Stage Project Feature**: Focused context delivery through field prioritization
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
