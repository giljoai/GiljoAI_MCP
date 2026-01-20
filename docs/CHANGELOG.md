# Changelog

All notable changes to this project will be documented in this file.

The format is based on [Keep a Changelog](https://keepachangelog.com/en/1.0.0/),
and this project adheres to [Semantic Versioning](https://semver.org/spec/v2.0.0.html).

## [Unreleased]

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
  - Two-dimensional model: Priority (1/2/3/4) × Depth (per source)
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
- Prompt size reduced: 3,500 tokens → <600 tokens
- Context tool response time: <100ms average
- Handles documents >100K tokens with pagination

## [3.1.1] - 2025-11-03

### Fixed
- **Thin Client Production Fixes (Handover 0089)**:
  - External URL now uses `services.network.external_host` instead of bind address `0.0.0.0` in prompt generator
  - Health check MCP tool exposed for early connectivity verification
  - Improved copy-to-clipboard workflow with robust HTTP fallback

## [3.1.0] - 2025-10-31

### Fixed
- **Tenant JWT Mismatch (Handover 0078)**: Resolved multi-tenant isolation bug where tasks saved with `product_id = null` due to incompatible JWT payloads between creation and verification

## [3.0.0] - 2025-10-28

### Added
- **External Agent Coordination Tools (Handover 0060)**: HTTP-based MCP tools enabling true multi-agent orchestration across internal and external agents
  - 7 production-grade MCP tools: create_agent_job_external, send_agent_message_external, get_agent_job_status_external, acknowledge_agent_job_external, complete_agent_job_external, fail_agent_job_external, list_active_agent_jobs_external
  - JWT authentication with auto-retry and exponential backoff
  - Comprehensive error handling

- **Project Launch Panel (Handover 0062)**: Comprehensive two-tab interface for project activation and agent job management
  - Database: `description` field added to Projects table, `project_id` field added to MCPAgentJob table
  - API: POST `/api/v1/projects/{id}/activate` and GET `/api/v1/projects/{id}/summary` endpoints
  - Frontend: LaunchPanelView, AgentMiniCard, KanbanJobsView components
  - 12 agent type mappings with semantic color choices

## [2.5.0] - 2025-10-26

### Added
- **Vision Document Chunking (Handover 0047)**: Fixed critical async/sync architecture mismatch
  - Async conversion of entire chunking pipeline
  - CASCADE constraints for proper product deletion
  - File size tracking for vision documents (bonus feature)

### Fixed
- Vision document chunking now fully operational with async-first architecture
- Product deletion working with proper cleanup of dependent entities
- Missing `await` on `db.delete()` calls

### Changed
- Repository layer: Converted `delete_chunks_by_vision_document()` and `mark_chunked()` to async
- Chunker layer: Converted `chunk_vision_document()` to async
- API endpoints: Added proper `await` to all async operations

## [2.4.0] - 2025-10-25

### Added
- **Claude Code Agent Template Export (Handover 0044-R)**: Production-grade export system for Claude Code integration
  - Backend: `api/endpoints/claude_export.py` (433 lines) with POST `/api/export/claude-code` endpoint
  - Frontend: `ClaudeCodeExport.vue` component in Settings → API and Integrations
  - Automatic backups with `.old.YYYYMMDD_HHMMSS` format
  - Multi-tenant isolation and path validation
  - YAML frontmatter generation for Claude Code compatibility

### Testing
- 21 backend tests (100% passing)
- 81 frontend tests (85.2% passing, 12 non-critical CSS selector issues)
- Cross-platform path handling verified

## [2.3.0] - 2025-10-21

### Added
- **Password Reset Functionality (Handover 0023)**: Comprehensive self-service password recovery system
  - 4-digit Recovery PIN system with bcrypt hashing
  - Rate limiting: 5 failed attempts trigger 15-minute lockout
  - Frontend components: FirstLogin.vue, ForgotPasswordPin.vue
  - Backend endpoints: 3 new + 2 updated API endpoints
  - WCAG 2.1 AA accessibility compliance

### Changed
- **Documentation Updates**:
  - `SERVER_ARCHITECTURE_TECH_STACK.md`: Updated with handovers 0019, 0020, 0023, 0025-0029, 0035 (500+ lines added)
  - `GILJOAI_MCP_PURPOSE.md`: Emphasized 70% token reduction capability (130+ lines added)

### Security
- bcrypt hashing with timing-safe comparison for PINs
- Generic error messages to prevent user enumeration
- Audit logging for all PIN verification attempts

## [2.2.0] - 2025-10-16

### Added
- **Two-Layout Authentication Pattern (Handover 0024)**: Industry-standard authentication architecture
  - Separate AuthLayout and DefaultLayout components
  - Clean separation between authentication routes and application routes
  - Zero dashboard flashing during authentication flow
  - User avatar correctly displays username and admin badge

### Changed
- App.vue reduced from 537 lines to 58 lines (90% reduction)
- Backend: Removed setup mode check from `/api/auth/me` endpoint
- Router: Added `meta.layout` to all routes for dynamic layout selection

### Fixed
- Setup mode blocking user data after password change
- Dashboard flashing between authentication screens
- User profile loading race conditions

## [2.1.0] - 2025-10-15

### Added
- **Handover 0012 Documentation Validation**: Comprehensive verification of vision documents and handover projects
  - 3 vision documents validated (AGENTIC_PROJECT_MANAGEMENT_VISION, TOKEN_REDUCTION_ARCHITECTURE, MULTI_AGENT_COORDINATION_PATTERNS)
  - 5 handover projects validated (0017-0021)
  - 81 pages of technical documentation created

## [2.0.0] - 2025-10-13

### Added
- **Advanced UI/UX Implementation (Handover 0009)**: Comprehensive verification of design system
  - 90% implementation complete with professional-grade quality
  - 80+ custom icons integrated
  - 4 mascot animation states (loader, working, thinker, active)
  - WCAG 2.1 AA accessibility compliance (85/100, 92/100 with minor fixes)
  - 81 pages of technical verification documentation

- **User API Key Management (Handover 0015)**: Secure per-user API key system for MCP configuration
  - ApiKeyManager.vue component integrated into UserSettings
  - AIToolSetup.vue with automatic API key generation
  - httpOnly cookie authentication (XSS and CSRF protection)
  - Multi-tenant isolation at all layers
  - Bcrypt hashing with cost factor 12

### Changed
- Frontend authentication: Migrated to httpOnly cookie pattern (removed localStorage token handling)
- Theme system: Uses `#FFC300` (minor deviation from official `#FFD93D` brand color)

### Fixed
- Authentication 401 errors caused by manual cookie management attempts
- Token injection in API requests (now automatic via browser)

### Security
- XSS Protection: Tokens not accessible to JavaScript via httpOnly cookies
- CSRF Protection: SameSite=lax prevents cross-site attacks
- API key security: One-time plaintext display, bcrypt hashing, audit logging

## [1.5.0] - 2025-10-11

### Fixed
- **Installation Authentication Fix**: Critical bug preventing fresh installations
  - Removed `db_manager = None` in setup mode (database always initialized)
  - Made setup endpoints public (`/api/setup`, `/api/auth/change-password`)
  - Fixed login password validation (min_length: 8 → 1 to allow default "admin" password)

### Changed
- Simplified installation flow to match industry standards (WordPress, GitLab)
- Setup endpoints work without authentication during installation

## [1.0.0] - 2024-11

### Added
- **Stage Project Feature**: Production implementation achieving 70-80% token reduction through field prioritization
  - Intelligent mission generation with MissionPlanner (630 lines)
  - Smart agent selection with AgentSelector (287 lines)
  - Multi-agent workflow coordination with WorkflowEngine (500 lines)
  - Real-time WebSocket updates with dependency injection
  - Standardized event schemas with Pydantic validation

### Performance
- 70-80% context prioritization validated in production testing
- WebSocket broadcast latency: 78ms (target: <100ms)
- Mission generation time: 1.4s (target: <2s)
- Zero memory leaks after 1000+ cycles

### Testing
- 95 comprehensive tests (87% backend coverage, 78% frontend coverage)
- Unit tests: 42 backend + 14 frontend
- Integration tests: 18 tests
- API tests: 24 tests
- WebSocket tests: 11 tests

### Architecture
- Production-grade WebSocket dependency injection
- Field priority system (10/7/4 scores) for token optimization
- Context chunking for vision documents
- Progressive abbreviation maintaining structure
- Serena MCP integration toggle

### Quality
- Zero technical debt (no band-aids or TODO comments)
- Professional code quality throughout
- Comprehensive error handling
- WCAG 2.1 AA accessibility compliance
- Cross-platform compatibility

---

## Version History Summary

- **v3.3.0** (2025-12-21): MCPAgentJob deprecation and identity model cleanup
- **v3.2.0** (2025-11-17): Context Management v2.0 with user empowerment focus
- **v3.1.1** (2025-11-03): Thin client production fixes
- **v3.1.0** (2025-10-31): Tenant JWT mismatch fix
- **v3.0.0** (2025-10-28): External agent coordination and project launch panel
- **v2.5.0** (2025-10-26): Vision document chunking async fix
- **v2.4.0** (2025-10-25): Claude Code agent template export
- **v2.3.0** (2025-10-21): Password reset and comprehensive documentation updates
- **v2.2.0** (2025-10-16): Two-layout authentication pattern
- **v2.1.0** (2025-10-15): Documentation validation (Handover 0012)
- **v2.0.0** (2025-10-13): UI/UX verification and user API key management
- **v1.5.0** (2025-10-11): Installation authentication fix
- **v1.0.0** (2024-11): Stage Project feature with 70% token reduction

---

**Note**: This CHANGELOG was generated from the devlog folder on 2026-01-19. Historical entries may be consolidated. For detailed implementation notes, see individual devlog files in `docs/archive/retired-2026-01/devlog-history/`.
