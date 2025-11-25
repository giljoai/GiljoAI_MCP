# CLAUDE.md

Guidance for Claude Code working with the **GiljoAI Agent Orchestration MCP Server** codebase.

## What We're Building

**GiljoAI Agent Orchestration MCP Server** - Multi-tenant server orchestrating specialized AI agents for complex software development. context prioritization and orchestration through intelligent agent coordination.

**Product**: Server application • **Deployment**: Local/network via web dashboard • **Tech**: Python/FastAPI/PostgreSQL/Vue3

**Recent Updates (v3.2+)**: Orchestrator Workflow & Token Optimization (0246a-0246c) • GUI Redesign Series (0234-0235) • Context Management v2.0 (0312-0316) • 360 Memory Management (0135-0139) • Remediation Project (0500-0515) • Nuclear Migration Reset (0601) • Agent Monitoring & Cancellation (0107) • One-Liner Installation (0100) • Production npm (0082) • Orchestrator Succession (0080) • Native MCP for Codex & Gemini (0069) • Static Agent Grid (0073) • Project Soft Delete with Recovery (0070) • Agent Template Management (0041) • Unified Installer (0035) • Admin Settings v3.0 (0025-0029) • Password Reset via PIN (0023) • Orchestrator Enhancement (0020) • Agent Job Management (0019)

**Orchestrator Workflow Series (Nov 2025)** - Handovers 0246a-0246c:
- 0246a: 7-Task Staging Workflow (931 tokens, 22% under budget)
- 0246b: Generic Agent Template with 6-phase protocol (1,253 tokens)
- 0246c: Dynamic Agent Discovery (71% token savings, 420 tokens)
- **Total Impact**: 85% reduction in orchestrator prompts (~3,500 → ~450-550 tokens)
- Complete pipeline: Staging → Discovery → Spawning → Execution

**GUI Redesign (Nov 2025)** - Handovers 0234-0235:
- StatusBoard components (StatusChip with health indicators, ActionIcons with 5 actions, JobReadAckIndicators)
- Status board table with real-time WebSocket updates
- Agent health monitoring with staleness detection
- Action management (launch, copy prompt, view messages, cancel, hand over)

Per-User Tenancy Policy (Nov 2025)
- Each user is isolated in their own tenant (unique tenant_key assigned at registration)
- /api/auth/register ignores provided tenant_key and generates a per-user tenant
- “Active Product” is tenant-specific; effective behavior is per user under this policy
- WebSocket product events are tenant-scoped (no cross-tenant leakage)

HTTP-only MCP (Nov 2025)
- MCP-over-HTTP JSON-RPC endpoint (/mcp) is authoritative
- Stdio adapter is deprecated; use HTTP transport with X-API-Key

**Backend Refactoring (v3.1)**: Handovers 0120-0130 completed backend transformation (Nov 2025):
- ✅ 89% Complete (8/9 handovers, 1 deferred)
- Service layer extracted: 5 services (ProjectService, TemplateService, TaskService, MessageService, ContextService, OrchestrationService)
- ToolAccessor reduced 48%: 2,324 → 1,200 lines
- Endpoints modularized: 4 monoliths → 24 focused modules
- Test coverage: >80% achieved
- See: `handovers/completed/REFACTORING_ROADMAP_0120-0130.md` (RETIRED - Mission Accomplished)

**Critical Remediation (v3.1.1)**: Handovers 0500-0515 completed major remediation after 0120-0130 refactoring:
- Vision upload with chunking (<25K tokens per chunk)
- Project lifecycle methods (activate, deactivate, summary, launch)
- Orchestrator succession with context tracking (90% auto-trigger)
- Settings endpoints (general, network, product-info)
- Test suite restored (>80% coverage across services, endpoints, integration)
- E2E integration tests for critical workflows

**Database Migrations (v3.1+)**: Single baseline migration approach (Handover 0601) • Fresh installs in <1 second • 32 tables from pristine SQLAlchemy models • See [Migration Strategy](docs/architecture/migration-strategy.md)

**Roadmap Management (Nov 2025)**: Active roadmap tracking and retirement strategy:
- ✅ **RETIRED**: `REFACTORING_ROADMAP_0120-0130.md` (89% complete - backend refactoring mission accomplished)
- ⛔ **RETIRED**: `REFACTORING_ROADMAP_0131-0200_OLD.md` (11% complete - superseded by Context Management, Remediation, GUI Redesign)
- ⚡ **ACTIVE**: `handovers/0300_EXECUTION_ROADMAP_REACTIVATED.md` (71% v2.0 complete - final phase, 2 handovers remaining: 0316, 0318)
- **Strategy**: Focused roadmaps (10-15 handovers) complete successfully; massive roadmaps (90+ handovers) stall due to changing priorities

## 📋 Quick Reference

**Essential Docs**: [System Overview](docs/GILJOAI_MCP_PURPOSE.md) • [Architecture](docs/SERVER_ARCHITECTURE_TECH_STACK.md) • [Installation](docs/INSTALLATION_FLOW_PROCESS.md) • [Vision](docs/vision/)

**Navigation Hub**: [docs/README_FIRST.md](docs/README_FIRST.md)

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
│   ├── src/components/
│   │   ├── StatusBoard/               # Status board components (Handovers 0234-0235)
│   │   │   ├── StatusChip.vue         # Status badge with health indicators
│   │   │   ├── ActionIcons.vue        # Agent action buttons (launch/copy/message/cancel/handover)
│   │   │   └── JobReadAckIndicators.vue  # Read/acknowledged checkmarks
│   │   ├── orchestration/
│   │   │   └── AgentTableView.vue     # Reusable status board table
│   │   └── projects/
│   │       ├── LaunchTab.vue          # Project launch interface
│   │       └── JobsTab.vue            # Agent jobs monitoring
│   ├── src/utils/
│   │   ├── statusConfig.js            # Status/health configuration utilities
│   │   └── actionConfig.js            # Action availability and configuration
│   └── src/composables/
│       └── useStalenessMonitor.js     # Staleness detection for agents
├── docs/              # Documentation
│   ├── user_guides/                   # User-facing guides
│   └── components/                    # Component API documentation
└── install.py         # Single cross-platform installer
```

## Development Environment

**Location**: `F:\GiljoAI_MCP`
**Shell Environment**: Windows PowerShell (default terminal)
**Never Commit** (gitignored): `.env`, `config.yaml`, `data/`, `logs/`, `temp/`, `venv/`, `node_modules/`

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

## Context Management (v2.0)

GiljoAI uses a 2-dimensional context management model:

**Priority Dimension** (WHAT to fetch):
- Priority 1 (CRITICAL) - Always included
- Priority 2 (IMPORTANT) - High priority
- Priority 3 (NICE_TO_HAVE) - Medium priority
- Priority 4 (EXCLUDED) - Never included

**Depth Dimension** (HOW MUCH detail):
- Product Core: include/exclude (~100 tokens)
- Vision Documents: none/light/moderate/heavy (0-30K tokens)
- Tech Stack: required/all (200-400 tokens)
- Architecture: overview/detailed (300-1.5K tokens)
- Testing: none/basic/full (0-400 tokens)
- 360 Memory: 1/3/5/10 projects (500-5K tokens)
- Git History: 10/25/50/100 commits (500-5K tokens)
- Agent Templates: minimal/standard/full (400-2.4K tokens)

**9 MCP Context Tools** (with Context Configurator badges):
1. `fetch_product_context` - Product name, description, features → **"Product Core" badge**
2. `fetch_vision_document` - Vision document chunks (paginated) → **"Vision Documents" badge**
3. `fetch_tech_stack` - Programming languages, frameworks, databases → **"Tech Stack" badge**
4. `fetch_architecture` - Architecture patterns, API style, design patterns → **"Architecture" badge**
5. `fetch_testing_config` - Quality standards, strategy, frameworks → **"Testing" badge**
6. `fetch_360_memory` - Project closeout summaries (paginated) → **"360 Memory" badge**
7. `fetch_git_history` - Aggregated git commits from all projects → **"Git History" badge**
8. `fetch_agent_templates` - Agent template library → **"Agent Templates" badge**
9. `fetch_project_context` - Current project metadata → **"Project Context" badge**

**Configuration**:
- Priority: My Settings → Context → Field Priority Configuration
- Depth: My Settings → Context → Depth Configuration

## Orchestrator Workflow Pipeline (v3.2 Handovers 0246a-c)

**Complete 4-Phase Pipeline**:
1. **Staging** (7 tasks, 931 tokens) - Identity verification, MCP health, environment understanding, agent discovery, context prioritization, job spawning, activation
2. **Discovery** (420 tokens saved) - Dynamic agent discovery via `get_available_agents()` MCP tool (no embedded templates)
3. **Spawning** (1,253 tokens per agent) - Generic agent template with 6-phase protocol, mission fetching via `get_agent_mission()`
4. **Execution** - Agents run 6-phase protocol with real-time coordination

**Key Features**:
- **85% Token Reduction**: ~3,500 → ~450-550 tokens per orchestrator
- **Dynamic Agent Discovery**: 71% token savings (420 tokens) via MCP tool
- **Client-Server Separation**: Server = HTTP tool provider, Client = code executor
- **Multi-Tenant Isolation**: All MCP tools filter by tenant_key

**MCP Tools** (0246 Series):
- `get_available_agents(tenant_key, active_only)` - Discover agents dynamically (0246c)
- `get_generic_agent_template(agent_id, job_id, ...)` - Unified template (0246b)
- `get_agent_mission(job_id, tenant_key)` - Fetch agent-specific mission
- Staging prompt generated by `ThinClientPromptGenerator._build_staging_prompt()` (0246a)

**Documentation**: [ORCHESTRATOR.md](docs/ORCHESTRATOR.md) • [STAGING_WORKFLOW.md](docs/components/STAGING_WORKFLOW.md)

## Thin Client Architecture (v3.1+ Handover 0088)

**CRITICAL**: Thin client prompt generation for context prioritization and orchestration.

- ✅ Use `ThinClientPromptGenerator` for new development
- ✅ Prompts are ~450-550 tokens (down from ~3,500 via 0246 series)
- ✅ Mission fetched via `get_orchestrator_instructions()` MCP tool
- ✅ Field priorities applied (context prioritization and orchestration ACTIVE)
- ⚠️ `OrchestratorPromptGenerator` DEPRECATED (remove in v4.0)

**Migration**: Replace fat prompt calls with thin prompt generator.
**Guide**: [docs/guides/thin_client_migration_guide.md](docs/guides/thin_client_migration_guide.md)

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
PGPASSWORD=$DB_PASSWORD /f/PostgreSQL/bin/psql.exe -U postgres -d giljo_mcp

# Example queries:
PGPASSWORD=$DB_PASSWORD /f/PostgreSQL/bin/psql.exe -U postgres -d giljo_mcp -c "\dt"  # List tables
PGPASSWORD=$DB_PASSWORD /f/PostgreSQL/bin/psql.exe -U postgres -d giljo_mcp -c "SELECT * FROM mcp_agent_jobs LIMIT 5;"
```

**Note**: Using Windows PowerShell. Command chaining uses `;` instead of `&&`.
**Claude Code Note**: Bash tool runs Git Bash (not PowerShell), use Unix-style paths: `/f/` not `F:\`

## Important Coding Guidelines

- **No Emojis in Code**: Never use unless specifically requested
- **Professional Code**: Clean and production-grade
- **File Creation**: Only when necessary; prefer editing existing files
- **Documentation**: Only create docs when explicitly requested
- **Cross-Platform**: All paths use `pathlib.Path()`
- **Database**: PostgreSQL required - no SQLite support
- **Template System**: Use `template_manager.py` (new) not `mission_templates.py` (deprecated)
- **Authentication**: Always enabled - first user created during setup wizard
- **Password Reset**: Recovery PIN system - 4-digit PIN with rate limiting (Handover 0023)
- **Default Password**: "GiljoMCP" for admin resets only (never admin/admin)
- **Agent Jobs**: Use AgentJobManager for lifecycle, AgentCommunicationQueue for messaging
- **Context Management v2.0**: 2-dimensional model (Priority × Depth) - orchestrator fetches context via MCP tools based on user configuration
- **Serena MCP**: Use Serena's symbolic tools for code navigation (find_symbol, get_symbols_overview, find_referencing_symbols) - REQUIRED for exploring codebase efficiently and avoiding full file reads

## Service Layer Architecture & Patterns

**See [docs/SERVICES.md](docs/SERVICES.md)** for complete service layer documentation.

**Core Services**:
- `ProductService` - Product & vision document management with chunked uploads
- `ProjectService` - Project lifecycle operations (activate, deactivate, summary, launch)
- `OrchestrationService` - Context tracking, succession management, orchestrator coordination
- `SettingsService` - System settings persistence and retrieval
- `AgentJobManager` - Agent job lifecycle management

**Service Pattern** (all services follow this):
- AsyncSession injection for database transactions
- Multi-tenant isolation (tenant_key parameter)
- Pydantic schemas for request/response validation
- WebSocket event emission for real-time UI updates
- Comprehensive error handling with domain-specific exceptions

## Orchestrator Context Tracking & Succession

**See [docs/ORCHESTRATOR.md](docs/ORCHESTRATOR.md)** for complete orchestrator documentation.

**Key Features**:
- Real-time context monitoring (context_used / context_budget tracked per message)
- Automatic succession trigger at 90% capacity (configurable)
- Handover summary generation (<10K tokens via mission condensation)
- Full lineage tracking (spawned_by chain preserved across instances)
- Manual succession via `/gil_handover` slash command or UI "Hand Over" button

## 360 Memory Management

**See [docs/360_MEMORY_MANAGEMENT.md](docs/360_MEMORY_MANAGEMENT.md)** for complete documentation.

**Purpose**: Provide orchestrators with cumulative product knowledge and project history.

**Key Features**:
- Product memory stored in `Product.product_memory` JSONB column
- Sequential project history with auto-incrementing sequence numbers
- GitHub integration for commit tracking (optional)
- Manual summaries for non-GitHub users (mini-git fallback)
- Real-time WebSocket updates when memory changes

**Data Structure**:
```json
{
  "product_memory": {
    "objectives": [...],
    "decisions": [...],
    "context": {...},
    "knowledge_base": {...},
    "sequential_history": [
      {
        "sequence": 1,
        "type": "project_closeout",
        "project_id": "uuid",
        "summary": "...",
        "git_commits": [...],
        "timestamp": "2025-11-16T10:00:00Z"
      }
    ]
  }
}
```

**MCP Tool**:
- `close_project_and_update_memory(project_id, summary, key_outcomes, decisions_made)`
- Called by orchestrator at project completion
- Automatically fetches GitHub commits if integration enabled
- Emits WebSocket event for real-time UI updates

**GitHub Integration**:
- Toggle: My Settings → Integrations → GitHub Integration
- Stored in: `Product.product_memory.git_integration`
- Fallback: Manual summaries when GitHub disabled

## Testing Strategy

**See [docs/TESTING.md](docs/TESTING.md)** for complete testing documentation.

**Coverage Target**: >80% across all services and endpoints (verified via pytest-cov)

**Running Tests**:
```bash
# All tests with coverage
pytest tests/ --cov=src/giljo_mcp --cov-report=html

# Service layer only
pytest tests/services/ -v

# Integration tests only
pytest tests/integration/ -v
```

## Handover Format & Tool Selection

**See [docs/HANDOVERS.md](docs/HANDOVERS.md)** for complete handover documentation.

**Handovers are SCOPED DOCUMENTS, not folders:**
- ✅ **Correct**: `handovers/0060_mcp_agent_coordination_tool_exposure.md` (single file)
- ❌ **Incorrect**: `handovers/0060/` folder with multiple files

**Format**: `[SEQUENCE]_[SHORT_DESCRIPTION].md` (all lowercase, underscores)

**Tool Selection (CCW vs CLI)**:
- **Use CLI**: Database changes, service layer, integration testing, MCP tools
- **Use CCW**: Frontend work, documentation, pure code (no DB), parallel tasks

## Development Workflow

**Adding MCP Tool**: `src/giljo_mcp/tools/` → Register in `__init__.py` → Add tests
**Adding API Endpoint**: `api/endpoints/` → Import in `api/app.py` → Add models & tests
**Database Changes**: Update `src/giljo_mcp/models.py` → Run `python install.py`
**Frontend Changes**: Edit `frontend/` → Test with `npm run dev` → Update user guides if workflows changed
**Adding Frontend Component**: Create in `frontend/src/components/` → Add unit tests → Document in `docs/components/` if reusable
**Adding StatusBoard Component**: Follow pattern in `StatusChip.vue` (props-based, emits events, unit tested) → Document props/events in component API docs

**Correct Order**: Database schema → Service layer → API endpoints → Frontend components → Documentation

## Common Issues

**Database**: Verify PostgreSQL running: `psql -U postgres -l` • Check `config.yaml`
**Ports**: Check `config.yaml` • Use `--port` flag: `python api/run_api.py --port 7272`
**Frontend**: `cd frontend/ && rm -rf node_modules/ && npm install && npm run build`

**Config files** (gitignored): `config.yaml` (system config) • `.env` (secrets)

## Detailed Documentation

**Service Layer**: [docs/SERVICES.md](docs/SERVICES.md) - Service patterns, code examples, multi-tenant isolation
**Orchestrator**: [docs/ORCHESTRATOR.md](docs/ORCHESTRATOR.md) - Context tracking, succession, handover protocol
**Testing**: [docs/TESTING.md](docs/TESTING.md) - Unit/integration test patterns, pytest commands
**Handovers**: [docs/HANDOVERS.md](docs/HANDOVERS.md) - Handover format, tool selection, execution workflow
**Architecture**: [docs/SERVER_ARCHITECTURE_TECH_STACK.md](docs/SERVER_ARCHITECTURE_TECH_STACK.md) - System architecture
**Installation**: [docs/INSTALLATION_FLOW_PROCESS.md](docs/INSTALLATION_FLOW_PROCESS.md) - Complete installation guide

## Need More?

**Start**: [docs/README_FIRST.md](docs/README_FIRST.md) • **Recent**: [docs/devlog/](docs/devlog/)
