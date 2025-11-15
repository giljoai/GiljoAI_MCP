# CLAUDE.md

Guidance for Claude Code working with the **GiljoAI Agent Orchestration MCP Server** codebase.

## What We're Building

**GiljoAI Agent Orchestration MCP Server** - Multi-tenant server orchestrating specialized AI agents for complex software development. 70% token reduction through intelligent agent coordination.

**Product**: Server application • **Deployment**: Local/network via web dashboard • **Tech**: Python/FastAPI/PostgreSQL/Vue3

**Recent Updates (v3.1+)**: Remediation Project (0500-0515) • Nuclear Migration Reset (0601) • Agent Monitoring & Cancellation (0107) • One-Liner Installation (0100) • Production npm (0082) • Orchestrator Succession (0080) • Native MCP for Codex & Gemini (0069) • Static Agent Grid (0073) • Project Soft Delete with Recovery (0070) • Agent Template Management (0041) • Unified Installer (0035) • Admin Settings v3.0 (0025-0029) • Password Reset via PIN (0023) • Orchestrator Enhancement (0020) • Agent Job Management (0019)

**Critical Remediation (v3.1.1)**: Handovers 0500-0515 completed major remediation after 0120-0130 refactoring:
- ProductService vision upload with chunking (<25K tokens per chunk)
- ProjectService lifecycle methods (activate, deactivate, summary, launch_orchestrator)
- OrchestrationService with context tracking (context_used / context_budget for 90% auto-succession trigger)
- Settings endpoints (general_settings, network_settings, product_info)
- Vision upload error handling with user notifications via WebSocket
- Succession UI components (SuccessionTimeline, LaunchSuccessorDialog) with manual handover support
- Test suite restored (>80% coverage across services, endpoints, integration workflows)
- E2E integration tests for critical workflows (product → vision → project → orchestrator)

**Database Migrations (v3.1+)**: Single baseline migration approach (Handover 0601) • Fresh installs in <1 second • 32 tables from pristine SQLAlchemy models • See [Migration Strategy](docs/architecture/migration-strategy.md)

## 📋 Quick Reference

**Essential Docs**: [System Overview](docs/GILJOAI_MCP_PURPOSE.md) • [Architecture](docs/SERVER_ARCHITECTURE_TECH_STACK.md) • [Installation](docs/INSTALLATION_FLOW_PROCESS.md) • [Vision](docs/vision/)

**Navigation Hub**: [docs/README_FIRST.md](docs/README_FIRST.md)

## Thin Client Architecture (v3.1+ Handover 0088)

**CRITICAL**: Thin client prompt generation for 70% token reduction.

- ✅ Use `ThinClientPromptGenerator` for new development
- ✅ Prompts are ~10 lines (not 3000)
- ✅ Mission fetched via `get_orchestrator_instructions()` MCP tool
- ✅ Field priorities applied (70% token reduction ACTIVE)
- ⚠️ `OrchestratorPromptGenerator` DEPRECATED (remove in v4.0)

**Migration**: Replace fat prompt calls with thin prompt generator.
**Guide**: [docs/guides/thin_client_migration_guide.md](docs/guides/thin_client_migration_guide.md)

## Tech Stack

**Backend**: Python 3.11+ • FastAPI • SQLAlchemy • PostgreSQL 18
**Frontend**: Vue 3 • Vuetify • WebSockets
**Database**: Multi-tenant isolation • Local PostgreSQL only
**Auth**: Always enabled • First user created via /welcome → /first-login (no defaults)

**Key Folders**:
```
F:\GiljoAI_MCP/
├── src/giljo_mcp/     # Core orchestrator & MCP tools
├── api/               # FastAPI server & endpoints
├── frontend/          # Vue dashboard
├── docs/              # Documentation
└── install.py         # Single cross-platform installer
```

## Development Environment

**Location**: `F:\GiljoAI_MCP`

**Shell Environment**: Windows PowerShell (default terminal)

**Never Commit** (gitignored): `.env`, `config.yaml`, `data/`, `logs/`, `temp/`, `venv/`, `node_modules/`

**npm Installation** (v3.1): Production-grade system with smart fallback (npm ci → npm install), pre-flight checks (registry, disk space, lockfile), 3-attempt retry with exponential backoff, and two-tier verification. All operations logged to `logs/install_npm.log` for diagnostics. See Handover 0082.

### Cross-Platform Coding Standards (CRITICAL)

```python
# ✅ CORRECT - Cross-platform
from pathlib import Path
data_dir = Path.cwd() / 'data'
log_file = Path('logs') / 'app.log'

# ❌ WRONG - Hardcoded paths
data_dir = 'F:\\GiljoAI_MCP\\data'
log_file = 'F:/logs/app.log'
```

**Always use**: `pathlib.Path()` • `Path.cwd()` • Relative paths in configs

## v3.0 Unified Architecture

**Single unified architecture** with NO deployment modes:

- ✅ Binds to all interfaces • User selects external IP during install
- ✅ **OS firewall** controls access (defense in depth)
- ✅ Authentication **ALWAYS** enabled (ONE flow for all connections)
- ✅ **First user creation** via fresh-install flow (user count = 0 detection)
- ✅ Database **ALWAYS** on localhost (security)
- ✅ **Single codebase** for all deployment contexts

**Single Active Product Architecture (Handover 0050)**:
- ✅ Only ONE product active per tenant at any time
- ✅ Database enforcement via partial unique index (atomic, race-condition-proof)
- ✅ Warning dialog before product switch (user confirmation flow)
- ✅ Project validation (parent product must be active)
- ✅ Agent job validation (product must be active)
- ✅ Orchestrator validation (mission assignment requires active product)

**Single Active Project Per Product (Handover 0050b)**:
- ✅ Only ONE project active per product at any time
- ✅ Database constraint via partial unique index (product_id, status='active')
- ✅ Cascade deactivation when switching products (projects auto-paused)
- ✅ Product-scoped project filtering in UI
- ✅ Enhanced warning dialog shows project impact

**Project Soft Delete with Recovery (Handover 0070)**:
- ✅ Soft delete with 10-day recovery window
- ✅ Projects marked deleted (status='deleted', deleted_at timestamp)
- ✅ Recovery UI in Settings → Database tab
- ✅ Auto-purge after 10 days (startup-based)
- ✅ Cascade delete for permanent purge
- ✅ Multi-tenant isolation in recovery

**Details**: [docs/SERVER_ARCHITECTURE_TECH_STACK.md](docs/SERVER_ARCHITECTURE_TECH_STACK.md)

## Quick Install

**One-Line Installation** (Recommended):

**macOS / Linux**:
```bash
curl -fsSL https://install.giljoai.com/install.sh | bash
```

**Windows (PowerShell)**:
```powershell
irm https://install.giljoai.com/install.ps1 | iex
```

**Manual Installation** (Developers):
```bash
git clone https://github.com/patrik-giljoai/GiljoAI-MCP
cd GiljoAI-MCP
python install.py
```

**Prerequisites**: Python 3.11+ • PostgreSQL 14+ • Node.js 18+

---

## Quick Start Commands

```powershell
# Server Setup
python install.py              # Fresh installation (manual install)
python startup.py              # Run server (detects first run)
python startup.py --dev        # Development mode

# Development
ruff src/; black src/          # Python linting & formatting
pytest tests/                  # Run tests
cd frontend/; npm run dev      # Frontend dev server

# Database (Password: 4010)
# NOTE: Claude Code runs in Git Bash on Windows, not PowerShell
# Use Git Bash path format: /f/PostgreSQL/bin/ (not F:\PostgreSQL\bin\)
PGPASSWORD=4010 /f/PostgreSQL/bin/psql.exe -U postgres -d giljo_mcp

# Example queries:
PGPASSWORD=4010 /f/PostgreSQL/bin/psql.exe -U postgres -d giljo_mcp -c "\dt"  # List tables
PGPASSWORD=4010 /f/PostgreSQL/bin/psql.exe -U postgres -d giljo_mcp -c "SELECT * FROM mcp_agent_jobs LIMIT 5;"
```

**Note**: Using Windows PowerShell. Command chaining uses `;` instead of `&&`.
**Claude Code Note**: Bash tool runs Git Bash (not PowerShell), use Unix-style paths: `/f/` not `F:\`

**Complete guides**: [Installation](docs/INSTALLATION_FLOW_PROCESS.md) • [Architecture](docs/SERVER_ARCHITECTURE_TECH_STACK.md)

## MCP Integration (Native Support)

**Supported AI Coding Tools**:
- ✅ **Claude Code** - Full MCP support via `claude-code mcp add` command
- ✅ **Codex CLI** - Native MCP support via `codex mcp add` command
- ✅ **Gemini CLI** - Native MCP support via `gemini mcp add` command

**Configuration**: Users configure MCP in **My Settings → MCP Configuration** (one-click copy commands)

**Admin View**: Admin Settings → Integrations shows overview of available tools

### Serena MCP (Code Navigation & Editing)

**CRITICAL**: Serena MCP provides symbolic code navigation tools that MUST be used for efficient codebase exploration.

**Why Use Serena**:
- ⚡ **Token Efficient**: Read only necessary symbols instead of entire files
- 🎯 **Precise Navigation**: Find symbols by name path, understand references
- 📊 **Smart Overview**: Get file structure without reading full content
- ✅ **Avoid Full Reads**: Only read symbol bodies when truly needed

**Core Tools** (use these FIRST before reading files):
- `mcp__serena__get_symbols_overview` - Get high-level view of symbols in a file
- `mcp__serena__find_symbol` - Find classes/functions by name path (e.g., "MyClass/my_method")
- `mcp__serena__find_referencing_symbols` - Find all references to a symbol
- `mcp__serena__search_for_pattern` - Flexible regex search across codebase
- `mcp__serena__replace_symbol_body` - Edit symbol bodies precisely
- `mcp__serena__insert_after_symbol` / `insert_before_symbol` - Add code at specific locations

**Usage Pattern** (REQUIRED):
1. **First**: Use `get_symbols_overview` to understand file structure
2. **Then**: Use `find_symbol` with `depth=1` to see methods/fields
3. **Only if needed**: Use `include_body=True` to read specific symbol implementation
4. **Last resort**: Use Read tool for full file (rare - only for non-code files or when symbolic approach fails)

**Example Workflow**:
```
Task: "Update the create_product method in ProductService"

❌ WRONG: Read entire src/giljo_mcp/services/product_service.py file
✅ CORRECT:
  1. get_symbols_overview("src/giljo_mcp/services/product_service.py")
  2. find_symbol(name_path="ProductService/create_product", include_body=True)
  3. replace_symbol_body() to update only that method
```

**Serena Memory System**:
- Use `mcp__serena__write_memory` to save important codebase insights
- Use `mcp__serena__list_memories` to see available memories
- Use `mcp__serena__read_memory` when relevant to current task

## Important Coding Guidelines

- **No Emojis in Code**: Never use unless specifically requested
- **Professional Code**: Clean and production-grade
- **File Creation**: Only when necessary; prefer editing existing files
- **Documentation**: Only create docs when explicitly requested
- **Cross-Platform**: All paths use `pathlib.Path()`
- **Database**: PostgreSQL required - no SQLite support
- **Template System**: Use `template_manager.py` (new) not `mission_templates.py` (deprecated)
- **v3.0 Architecture**: Always bind to 0.0.0.0, ONE authentication flow
- **Authentication**: Always enabled - first user created during setup wizard
- **Password Reset**: Recovery PIN system - 4-digit PIN with rate limiting (Handover 0023)
- **Default Password**: "GiljoMCP" for admin resets only (never admin/admin)
- **Agent Jobs**: Use AgentJobManager for lifecycle, AgentCommunicationQueue for messaging
- **Token Reduction**: MissionPlanner + AgentSelector + WorkflowEngine = 70% reduction
- **Serena MCP**: Use Serena's symbolic tools for code navigation (find_symbol, get_symbols_overview, find_referencing_symbols) - REQUIRED for exploring codebase efficiently and avoiding full file reads

## Service Layer Architecture (v3.1+)

**Core Services** (all use AsyncSession for database access, multi-tenant isolation via tenant_key):
- `ProductService` (src/giljo_mcp/services/product_service.py) - Product & vision document management with chunked uploads
- `ProjectService` (src/giljo_mcp/services/project_service.py) - Project lifecycle operations (activate, deactivate, launch, summary)
- `OrchestrationService` (src/giljo_mcp/services/orchestration_service.py) - Context tracking, succession management, orchestrator coordination
- `SettingsService` (src/giljo_mcp/services/settings_service.py) - System settings persistence and retrieval
- `AgentJobManager` (src/giljo_mcp/agent_job_manager.py) - Agent job lifecycle management

**Service Pattern** (all services follow this pattern):
- AsyncSession injection for database transactions
- Multi-tenant isolation (tenant_key parameter)
- Pydantic schemas for request/response validation
- WebSocket event emission for real-time UI updates
- Comprehensive error handling with domain-specific exceptions

**Example Usage**:
```python
from src.giljo_mcp.services.project_service import ProjectService

# Inject session and tenant
service = ProjectService(session, tenant_key="user123")

# Lifecycle operations
await service.activate_project(project_id)
await service.deactivate_all_projects_except(project_id)
summary = await service.get_project_summary(project_id)
```

## Testing Strategy (v3.1+)

**Unit Tests** (`tests/services/`):
- ProductService: Vision upload, chunking (<25K tokens), config_data persistence
- ProjectService: Lifecycle methods (activate/deactivate), Single Active Project constraint
- OrchestrationService: Context tracking, succession triggers, handover summary generation
- SettingsService: General settings, network settings, product info retrieval

**Integration Tests** (`tests/integration/`):
- Complete E2E workflows (product creation → vision upload → project activation → orchestrator launch)
- Multi-tenant isolation verification (zero cross-tenant leakage)
- Error condition handling (failed uploads, invalid transitions, succession failures)
- WebSocket real-time updates (job status changes, completion events)

**Coverage Target**: >80% across all services and endpoints (verified via pytest-cov)

**Running Tests**:
```bash
# All tests with coverage
pytest tests/ --cov=src/giljo_mcp --cov-report=html

# Service layer only
pytest tests/services/ -v

# Integration tests only
pytest tests/integration/ -v

# Specific test file
pytest tests/test_product_service.py -v
```

## Development Workflow

**Adding MCP Tool**: `src/giljo_mcp/tools/` → Register in `__init__.py` → Add tests
**Adding API Endpoint**: `api/endpoints/` → Import in `api/app.py` → Add models & tests
**Database Changes**: Update `src/giljo_mcp/models.py` → Run `python install.py`
**Frontend Changes**: Edit `frontend/` → Test with `npm run dev`

## Handover Format (CRITICAL)

**Handovers are SCOPED DOCUMENTS, not folders:**
- ✅ **Correct**: `handovers/0060_mcp_agent_coordination_tool_exposure.md` (single file)
- ❌ **Incorrect**: `handovers/0060/` folder with multiple files

**Format**: `[SEQUENCE]_[SHORT_DESCRIPTION].md` (all lowercase, underscores)
**Location**: `F:\GiljoAI_MCP\handovers/`
**Examples**:
- `0050_single_active_product_architecture.md`
- `0051_product_form_autosave_ux.md`

**Exception**: Large handovers (rare) may use folder structure like `0052/` with multiple markdown files

**See**: `handovers/HANDOVER_INSTRUCTIONS.md` for complete formatting guidance

## Agent Job Management System (v3.0+)

**Architecture**: Full lifecycle management for AI agent jobs with multi-tenant isolation

**Core Components**:
- `src/giljo_mcp/agent_job_manager.py` - Job lifecycle management (create, acknowledge, complete, fail)
- `src/giljo_mcp/agent_communication_queue.py` - JSONB message storage for agent-to-agent messaging
- `src/giljo_mcp/job_coordinator.py` - Multi-agent orchestration and coordination

**API Endpoints**: 13 REST endpoints in `api/endpoints/agent_jobs.py`
**WebSocket Events**: Real-time status updates via `job:status_changed`, `job:completed`, `job:failed`
**Testing**: 80 core tests (89.15% coverage) + 30 API tests + 9 WebSocket tests

## Orchestrator Enhancement (v3.0+)

**70% Token Reduction**: Achieved through intelligent mission condensation

**Components**:
- `src/giljo_mcp/mission_planner.py` (630 lines) - Generates condensed missions from vision docs
- `src/giljo_mcp/agent_selector.py` (287 lines) - Smart agent selection based on capabilities
- `src/giljo_mcp/workflow_engine.py` (500 lines) - Waterfall/parallel workflow execution

**Usage**: ProjectOrchestrator methods: `process_product_vision()`, `generate_mission_plan()`, `select_agents_for_mission()`, `coordinate_agent_workflow()`

## Orchestrator Succession (v3.0+ Handover 0080)

**Automatic orchestrator handover** when context windows reach 90% capacity.

**Features**:
- Context monitoring (context_used / context_budget)
- Automatic successor creation via MCP
- Handover summary generation (<10K tokens)
- Full lineage tracking (spawned_by chain)
- UI timeline visualization
- Manual launch control
- **NEW (0080a)**: `/gil_handover` slash command for manual succession trigger

**Manual Succession Triggers** (Handover 0080a):
- **Slash Command**: `/gil_handover` in Claude Code / Codex CLI
- **UI Button**: "Hand Over" button on working orchestrator cards (orchestrator-only)
- Both methods generate launch prompt for successor instance

**Database Fields**: `instance_number`, `handover_to`, `handover_summary`, `succession_reason`, `context_used`, `context_budget`, `handover_context_refs`

**Key Files**:
- `src/giljo_mcp/orchestrator_succession.py` (561 lines) - Core succession manager
- `src/giljo_mcp/tools/succession_tools.py` (295 lines) - MCP tools (create_successor_orchestrator, check_succession_status)
- `src/giljo_mcp/slash_commands/handover.py` - /gil_handover slash command handler (0080a)
- `api/endpoints/slash_commands.py` - Slash command HTTP endpoints (0080a)
- `api/endpoints/agent_jobs.py` - trigger_succession endpoint (0080a)
- `frontend/src/components/projects/SuccessionTimeline.vue` - Timeline UI
- `frontend/src/components/projects/LaunchSuccessorDialog.vue` - Launch prompt generator
- `frontend/src/components/projects/AgentCardEnhanced.vue` - Instance badges, context bars, "Hand Over" button

**Benefits**: Unlimited project duration, 70% token reduction, graceful context management

**User Guide**: [docs/user_guides/orchestrator_succession_guide.md](docs/user_guides/orchestrator_succession_guide.md)
**Developer Guide**: [docs/developer_guides/orchestrator_succession_developer_guide.md](docs/developer_guides/orchestrator_succession_developer_guide.md)

## Context Tracking Pattern (Orchestrator Succession)

**Implementation** (Handover 0502 - OrchestrationService):

```python
from src.giljo_mcp.services.orchestration_service import OrchestrationService

# Create orchestrator with context budget
service = OrchestrationService(session, tenant_key)
job = await service.create_orchestrator_job(
    project_id=project_id,
    mission=mission,
    context_budget=200000  # tokens
)

# Update context usage on message sends
await service.update_context_usage(job.id, additional_tokens=1500)

# Auto-succession triggers at 90% threshold
if (context_used / context_budget) >= 0.9:
    successor = await service.trigger_succession(
        job_id=job.id,
        reason="context_limit"
    )
    # successor.handover_summary contains condensed context (<10K tokens)
```

**Key Features**:
- Real-time context monitoring (context_used / context_budget tracked per message)
- Automatic succession trigger at 90% capacity (configurable)
- Handover summary generation (<10K tokens via mission condensation)
- Full lineage tracking (spawned_by chain preserved across instances)
- Manual succession via `/gil_handover` slash command or UI "Hand Over" button

## Platform Handler Architecture (v3.1.0+)

**Overview**: Unified cross-platform installer using Strategy pattern (Handover 0035)

**Adding Platform Support**: Create handler in `installer/platforms/` implementing PlatformHandler interface

**Platform-Specific Code**: Isolated in platform handlers (Windows, Linux, macOS)
- `installer/platforms/windows.py` - Windows-specific operations
- `installer/platforms/linux.py` - Linux-specific operations
- `installer/platforms/macos.py` - macOS-specific operations
- `installer/platforms/base.py` - Abstract interface

**Core Modules**: Unified and platform-agnostic
- `installer/core/database.py` - PostgreSQL setup (includes pg_trgm extension)
- `installer/core/config.py` - Configuration generation
- `installer/shared/postgres.py` - PostgreSQL discovery
- `installer/shared/network.py` - Network utilities

**Auto-Detection**: `installer/platforms/__init__.py` returns correct handler for current OS

## Admin Settings v3.0 Interface

**Network Tab** (Handover 0025): Removed MODE setting, updated API server display
**Database Tab** (Handover 0026): Redesigned with clean display window, fixed test button
**Integrations Tab** (Handover 0027): Agent Coding Tools (Claude Code, Codex, Gemini CLI) + Serena
**Users Management** (Handover 0029): Moved from Admin Settings to Avatar dropdown

## Agent Template Management (v3.0+ Handover 0041)

**Overview**: Database-backed agent template system with three-layer caching and Vue dashboard integration

**Core Features**:
- **Database Seeding**: 6 default agent templates seeded per tenant during setup (idempotent)
- **Three-Layer Cache**: Memory LRU (<1ms) → Redis (<2ms) → Database (<10ms)
- **13 REST API Endpoints**: Full CRUD + Reset, Diff, Preview, History, Restore
- **Vue Dashboard Integration**: Monaco editor, real-time preview, WebSocket updates
- **Multi-Tenant Isolation**: Zero cross-tenant leakage (database + cache + API)
- **75% Test Coverage**: 78 comprehensive tests (unit, integration, security)

**Key Components**:
- `src/giljo_mcp/template_seeder.py` (263 lines) - Idempotent template seeding
- `src/giljo_mcp/template_cache.py` (349 lines) - Three-layer caching system
- `src/giljo_mcp/template_manager.py` (1019 lines) - Unified template resolution
- `api/endpoints/templates.py` (1096 lines) - 13 REST endpoints
- `frontend/src/components/TemplateManager.vue` (1032 lines) - Full UI with Monaco editor

**Template Resolution Cascade**:
1. Product-specific template (highest priority)
2. Tenant-specific template (user customizations)
3. System default template
4. Legacy fallback (always succeeds)

**Usage - Customize Templates**:
Dashboard → Templates tab → Edit template → Monaco editor → Save
Templates support: Behavioral rules, Success criteria, Variables, Tool preferences

**Documentation**: [docs/handovers/0041/](docs/handovers/0041/) (User Guide, Developer Guide, Deployment Guide)

## Common Issues

**Database**: Verify PostgreSQL running: `psql -U postgres -l` • Check `config.yaml`
**Ports**: Check `config.yaml` • Use `--port` flag: `python api/run_api.py --port 7272`
**Frontend**: `cd frontend/ && rm -rf node_modules/ && npm install && npm run build`

**Config files** (gitignored): `config.yaml` (system config) • `.env` (secrets)

## Need More?

**Start**: [docs/README_FIRST.md](docs/README_FIRST.md) • **Recent**: [docs/devlog/](docs/devlog/)
