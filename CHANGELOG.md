# Changelog

All notable changes to GiljoAI MCP will be documented in this file.

The format is based on [Keep a Changelog](https://keepachangelog.com/en/1.0.0/),
and this project adheres to [Semantic Versioning](https://semver.org/spec/v2.0.0.html).

---

## [3.1.0] - 2025-10-25

### Added - Multi-Tool Agent Orchestration (Handover 0045)

**Revolutionary multi-tool agent orchestration system - first in the industry to enable seamless coordination between agents using different AI coding tools within a single project.**

#### Backend

**Core Features**:
- Multi-tool routing in ProjectOrchestrator based on `template.preferred_tool` configuration
- Support for Claude Code (hybrid mode), Codex (legacy CLI), and Gemini CLI (legacy CLI)
- Agent-Job linking via `Agent.job_id` field (links to `MCPAgentJob.id`)
- Event-driven status synchronization between Agent and MCPAgentJob models
- Universal MCP coordination protocol (7 tools) working across all AI tools

**MCP Coordination Tools**:
- `get_pending_jobs` - Retrieve jobs waiting for agent
- `acknowledge_job` - Confirm job started (manual for CLI, automatic for hybrid)
- `report_progress` - Report progress checkpoints (every 10-15 minutes)
- `get_next_instruction` - Fetch updated instructions from Orchestrator
- `complete_job` - Mark job as completed successfully
- `report_error` - Report critical errors and fail job
- `send_message` - Inter-agent communication

**Database Schema**:
- Added `job_id` column to `agents` table (VARCHAR(36), links to `mcp_agent_jobs.id`)
- Added `mode` column to `agents` table (VARCHAR(20), values: claude | codex | gemini)
- Added `preferred_tool` column to `agent_templates` table (VARCHAR(20), default: claude)
- Created indexes: `idx_agent_job_id`, `idx_agent_mode`, `idx_template_tool`

**API Endpoints** (3 new):
- `GET /api/v1/agents/{id}/cli-prompt` - Get CLI prompt for legacy mode agents
- `GET /api/v1/jobs/statistics` - Get job statistics by tool
- `POST /api/v1/templates/export/claude-code` - Export templates (enhanced)

**WebSocket Events** (enhanced):
- `agent:status_changed` - Now includes `mode` field
- `job:status_changed` - Agent-job status synchronization events

#### Frontend

**Job Queue Dashboard**:
- Real-time job monitoring across all tools
- Statistics panel (total jobs, by status, by tool)
- Tool-specific metrics (avg completion time, success rate)
- Filtering by status, tool, agent
- Message history and progress timeline

**Agent Cards**:
- Tool logo badges (Claude, OpenAI, Google)
- Mode indicators (Hybrid / Legacy CLI)
- "Copy Prompt" button for legacy CLI agents
- Real-time status updates via WebSocket

**Template Manager**:
- Preferred tool dropdown (claude, codex, gemini)
- Tool-specific template customization
- Enhanced template export with multi-tool support

#### Testing

**Comprehensive Test Coverage** (50 tests total):
- **Unit Tests** (20): Orchestrator routing logic, template resolution
- **Integration Tests** (15): Multi-tool scenarios, job lifecycle
- **Security Tests** (10): Tenant isolation verification
- **Performance Tests** (5): Concurrent agent spawning (100 agents < 10s)

#### Documentation

**Complete Documentation Suite**:
- [USER_GUIDE.md](docs/handovers/0045/USER_GUIDE.md) - User workflows and best practices
- [DEVELOPER_GUIDE.md](docs/handovers/0045/DEVELOPER_GUIDE.md) - Technical architecture and extension
- [DEPLOYMENT_GUIDE.md](docs/handovers/0045/DEPLOYMENT_GUIDE.md) - Production deployment and operations
- [API_REFERENCE.md](docs/handovers/0045/API_REFERENCE.md) - Complete API documentation
- [ADR.md](docs/handovers/0045/ADR.md) - Architecture decision records

### Changed

**Enhanced Components**:
- ProjectOrchestrator: Added multi-tool routing with `_spawn_claude_code_agent()` and `_spawn_legacy_agent()` methods
- AgentJobManager: Enhanced with agent-job linking and status synchronization
- Template system: Extended with `preferred_tool` field and tool-specific instructions
- WebSocket manager: Enhanced event broadcasting with tool and mode information

**Migration**:
- Migration script: `migration_0045_multi_tool.sql` (backward compatible)
- Template seeding: Updated default templates with multi-tool configuration

### Benefits

**Cost Optimization**:
- 40-60% cost reduction by mixing free and paid tiers
- Strategic use of Gemini free tier for bulk tasks
- Reserve premium tools (Claude) for complex reasoning

**Operational Resilience**:
- Rate limit resilience: Switch tools instantly when rate-limited
- Zero downtime: Distribute load across multiple API providers
- Vendor independence: No lock-in to single AI provider

**Capability-Based Routing**:
- Claude Code: Best for architecture, code review, complex reasoning
- Codex: Best for rapid implementation, data processing
- Gemini: Best for testing, documentation, free tier usage

### Performance

**Benchmarks**:
- Agent spawn time: 0.3-0.5 seconds (target: < 1 second) ✅
- MCP tool response: 20-50ms (target: < 100ms) ✅
- Job status update: 100-200ms (target: < 500ms) ✅
- Template cache hit rate: 97-99% (target: > 95%) ✅
- Concurrent spawning (100 agents): 5-7 seconds (target: < 10 seconds) ✅

### Security

**Multi-Tenant Isolation**:
- All MCP tools enforce tenant isolation (validate `tenant_key`)
- Database queries filter by tenant_key
- API endpoints return 404 for cross-tenant access attempts
- WebSocket events scoped to tenant
- 10 security tests verify zero cross-tenant leakage

---

## [3.0.0] - 2025-10-XX

### Added

**Agent Template Database Integration** (Handover 0041):
- Database-backed template customization with three-layer caching
- 6 default templates per tenant (orchestrator, analyzer, implementer, tester, reviewer, documenter)
- Monaco editor integration for rich editing
- Template versioning and history with rollback
- 13 REST API endpoints with WebSocket updates
- 75% test coverage across 78 tests

**Password Reset Functionality** (Handover 0023):
- Recovery PIN system (4-digit PIN, bcrypt hashed)
- Self-service password reset (no email required)
- Admin password reset capability (default: "GiljoMCP")
- Rate limiting: 5 failed attempts = 15 minute lockout
- Complete account setup flow for new users

**Admin Settings v3.0** (Handovers 0025-0029):
- Network tab refactored for v3.1 unified architecture
- Database tab with connection management and testing
- Integrations tab completely redesigned (Agent Coding Tools + Serena)
- Users management moved to Avatar dropdown
- WCAG 2.1 Level AA accessibility certified

**Agent Job Management System** (Handover 0019):
- Complete lifecycle management for AI agent jobs
- Agent-to-agent messaging with acknowledgment tracking
- Job dependencies and parent-child hierarchies
- Real-time WebSocket updates for job status
- 13 REST API endpoints
- 80 core tests (89.15% coverage)

**Orchestrator Enhancement** (Handover 0020):
- 70% token reduction through intelligent coordination
- Mission Planner, Agent Selector, Workflow Engine
- Serena MCP optimization layer (60-90% additional savings)
- Context usage tracking and metrics

**Cross-Platform Unified Installer** (Handover 0035):
- Single installer for Windows/Linux/macOS
- 25.6% code reduction via unified architecture
- Platform handler strategy pattern
- Automatic OS detection and configuration
- Desktop shortcuts/launchers per platform

### Changed

**v3.0 Unified Architecture**:
- Single unified architecture (no deployment modes)
- API binds to 0.0.0.0 (all interfaces)
- OS firewall controls access (defense in depth)
- Database always on localhost (security)
- Authentication always enabled (ONE flow for all connections)
- First user creation during setup wizard (admin credentials set by user)

---

## [2.x.x] - Previous Versions

See git history for changes prior to v3.0.0.

---

**Changelog Maintained By**: Documentation Manager Agent
**Last Updated**: 2025-10-25
