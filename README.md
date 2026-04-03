# GiljoAI MCP

<div align="center">

[![Python](https://img.shields.io/badge/Python-3.10%2B-blue)](https://www.python.org/)
[![FastAPI](https://img.shields.io/badge/FastAPI-0.100%2B-green)](https://fastapi.tiangolo.com/)
[![Vue 3](https://img.shields.io/badge/Vue-3.0%2B-brightgreen)](https://vuejs.org/)
[![Security](https://img.shields.io/badge/Security-Scanned-success)](SECURITY.md)
[![License](https://img.shields.io/badge/License-GiljoAI%20Community-blue)](LICENSE)
[![Setup Time](https://img.shields.io/badge/Setup-6--10%20minutes-success)]()
[![Context](https://img.shields.io/badge/Context-Unlimited-orange)]()

**Break through AI context limits. Orchestrate teams of specialized AI agents.**

[**Quick Start**](#quick-start) | [**Features**](#key-features) | [**Architecture**](#architecture-overview) | [**Documentation**](#documentation)

</div>

---

## Edition

This is the **GiljoAI MCP Community Edition** -- the full orchestration platform, free for single-user use under the [GiljoAI Community License v1.1](LICENSE).

**What's included in Community Edition:**
- Core orchestration engine (mission planning, agent coordination, context management)
- Agent management (templates, spawning, communication, job lifecycle)
- Single-user authentication (login/password, JWT)
- WebSocket & MCP protocol (real-time communication, tool integration)
- Full frontend dashboard (projects, agents, messages, settings)

**SaaS Edition** (multi-user, multi-org) is developed separately and adds OAuth/SSO, billing, team management, and enterprise deployment. Multi-user use requires a [commercial license](LICENSING_AND_COMMERCIALIZATION_PHILOSOPHY.md).

---

## Quick Start

```bash
# 1. Clone the repository
git clone https://github.com/patrik-giljoai/GiljoAI-MCP.git
cd GiljoAI_MCP

# 2. Run the installer (interactive, ~6 minutes)
python install.py

# 3. Start the application
python startup.py
```

**First run** opens the setup wizard in your browser. **Subsequent runs** go straight to the dashboard.

---

### Installation Modes

The installer asks how you plan to use GiljoAI:

| Mode | What it does | URL after startup |
|------|-------------|-------------------|
| **Production** (default) | Builds optimized frontend, serves everything on a single port | `http://localhost:7272` |
| **Development** | Runs Vite dev server with hot-reload on a separate port | Frontend: `http://localhost:7274`, API: `http://localhost:7272` |

```bash
# Production install (recommended for users)
python install.py
# Select "Production" when prompted
python startup.py          # Single port: http://localhost:7272

# Development install (for contributors)
python install.py
# Select "Development" when prompted
python startup.py          # Two ports: frontend :7274, API :7272
```

### Switching Between Modes

Already installed in production mode but want to contribute code?

```bash
python startup.py --dev    # Forces Vite dev server with hot-reload
```

Already installed in dev mode but want to test production serving?

```bash
cd frontend && npm run build && cd ..
python startup.py          # Auto-detects frontend/dist/ and serves on single port
```

### Command-Line Options

```bash
python startup.py              # Auto-detect mode and run
python startup.py --dev        # Force development mode (Vite HMR)
python startup.py --setup      # Force setup wizard
python startup.py --no-browser # Skip browser auto-open
python startup.py --verbose    # Detailed logging
python startup.py --stop       # Stop all services
```

### What Happens During Startup

**Production mode** (single port):
1. Validates Python 3.10+, PostgreSQL 18, dependencies
2. Runs database migrations if needed
3. Starts FastAPI on port 7272 (serves API + built frontend)
4. Opens browser to `http://localhost:7272`

**Development mode** (two ports):
1. Same validation and migration steps
2. Starts FastAPI API server on port 7272
3. Starts Vite dev server on port 7274 (proxies `/api` and `/ws` to 7272)
4. Opens browser to `http://localhost:7274`

**For complete details**, see [Installation Flow](docs/INSTALLATION_FLOW_PROCESS.md)

### Architecture

GiljoAI MCP uses a **unified architecture** -- one codebase, one configuration:

| Component | Configuration | Access Control |
|-----------|--------------|----------------|
| **Application** | Production: single port 7272. Dev: API 7272 + frontend 7274 | Bind address from install config |
| **Database** | Always on `localhost` (never exposed) | Local socket only (maximum security) |
| **Auth** | Always enabled | JWT authentication for all connections |
| **Network** | Firewall controls access | Localhost-only by default, configurable for LAN/WAN |

```
Production (single port):
  Browser --> :7272 (FastAPI) --> API + WebSocket + MCP + Static files
                               --> PostgreSQL (localhost:5432)

Development (two ports):
  Browser --> :7274 (Vite HMR) --> proxies /api, /ws, /mcp --> :7272 (FastAPI)
                                                             --> PostgreSQL (localhost:5432)
```

See [Server Architecture](docs/SERVER_ARCHITECTURE_TECH_STACK.md) for details.

### Next Steps

```bash
# Open the dashboard
# Production: http://localhost:7272
# Development: http://localhost:7274

# API documentation
# Swagger UI:  http://localhost:7272/docs
# ReDoc:       http://localhost:7272/redoc
```

### Linux Installer

```bash
python Linux_Installer/linux_install.py
```

The `Linux_Installer/` directory mirrors the Windows installer flow with Linux-specific logic (interactive CLI, config and database setup modules, runtime credential and script outputs).

---

## Key Features

### Agent Job Management System
**Complete lifecycle management for AI agent jobs**
- Agent-to-agent messaging with acknowledgment tracking
- Job dependencies and parent-child hierarchies
- Real-time WebSocket updates for job status changes
- Multi-tenant isolation at database level
- 13 REST API endpoints for comprehensive job control
- Priority-based message queuing (low, normal, high)
- Job coordination with automatic dependency resolution

**Implementation**: Handover 0019 - Production ready with 80 passing unit tests, 89% code coverage

### Orchestrator Enhancement - Context-Focused Architecture
**Intelligent agent coordination system**
- Template-based agent spawning with role specialization
- Hierarchical context loading with depth controls
- Smart handoff mechanism between agents
- Serena MCP optimization layer (symbolic operations for focused context delivery)
- Persistent project memory across sessions
- 22+ MCP tools for agent coordination

**Implementation**: Handover 0020 - Active with optimization interceptor and symbolic operation enforcement

### Password Reset via Recovery PIN
**Secure 4-digit PIN recovery system**
- Self-service password recovery (no email required)
- 4-digit numeric PIN (bcrypt hashed)
- Rate limiting: 5 attempts = 15 minute lockout
- Admin password reset capability (default: "GiljoMCP")
- Complete account setup flow for new users
- Works offline (perfect for local/LAN deployments)
- Comprehensive security with failed attempt tracking

**Implementation**: Handover 0023 - Production ready with comprehensive test suite

### Admin Settings v3.0 - Complete Refactoring
**Modern, accessible admin interface**

**Network Tab** (Handover 0025-0026):
- v3.1 unified architecture (conditional binding + HTTPS for LAN/WAN)
- External host configuration (localhost, LAN IP, or domain)
- Port management (single port 7272 in production, dual port in dev)
- WCAG 2.1 Level AA accessible
- Real-time validation and testing

**Database Tab** (Handover 0025):
- PostgreSQL connection management
- Connection testing with detailed feedback
- Credential management (host, port, database, user)
- Always localhost binding (security best practice)
- Connection pooling configuration

**Integrations Tab** (Handover 0027):
- AI Coding Agents section:
  - Claude Code CLI (MCP JSON config)
  - Codex CLI (TOML config)
  - Gemini CLI (JSON config with capabilities)
- Native Integrations section:
  - Serena MCP (deep semantic code analysis)
  - Future integrations placeholder
- One-click configuration download
- Copy-to-clipboard functionality
- Comprehensive setup guides

**Users Management Relocated** (Handover 0029):
- Moved from Admin Settings to Avatar dropdown
- Standalone "User Management" page
- Improved UX with dedicated focus
- Full user lifecycle management
- Role and tenant assignment

### Unified Cross-Platform Installer
**Single installer for all platforms** (Handover 0035)
- Windows 10/11 fully supported
- Linux (Ubuntu, Fedora, Debian) fully supported
- macOS (Intel and ARM) fully supported
- 25.6% code reduction via unified architecture
- Platform handler strategy pattern
- Automatic OS detection and configuration
- Desktop shortcuts/launchers per platform
- Comprehensive PostgreSQL detection

### Agent Template Database Integration
**Database-backed template customization** (Handover 0041)
- Three-layer caching architecture (Memory → Redis → Database)
- Template resolution cascade (<1ms p95 cache hits)
- 6 default templates per tenant with automatic seeding
- Monaco editor integration for template editing
- Real-time template updates via WebSocket
- Multi-tenant isolation at cache and database layers
- Version history and rollback capability
- 13 REST API endpoints for template management

---

## Recent Updates (v3.0+)

### October 2025 - Major Feature Releases

**Agent Template Management** (Handover 0041):
- Database-backed template customization with three-layer caching
- 6 default templates per tenant (orchestrator, analyzer, implementer, tester, reviewer, documenter)
- Monaco editor integration for rich editing experience
- Template versioning and history with rollback capability
- 13 REST API endpoints with WebSocket real-time updates
- 75% test coverage across 78 comprehensive tests

**Password Reset Functionality**:
- Recovery PIN system for self-service password reset
- Admin password reset capability
- Security with rate limiting (5 attempts, 15 min lockout)
- Complete onboarding flow for new users

**Admin Settings v3.0**:
- Network tab refactored for v3.1 architecture
- Database tab with connection management
- Integrations tab completely redesigned
- Users management moved to Avatar dropdown
- WCAG 2.1 Level AA accessibility certified

**Agent Orchestration**:
- Job management system (119+ tests, production ready)
- Context prioritization and orchestration through intelligent coordination
- Serena MCP optimization (symbolic operations for focused context delivery)
- Real-time WebSocket events for job updates
- Multi-tenant isolation throughout

**Cross-Platform Support**:
- Unified installer replacing platform-specific scripts
- 25.6% code reduction
- Consistent experience across Windows/Linux/macOS
- Automatic platform detection

---

## Architecture Overview

### Unified Architecture

**Network Topology** (production -- single port):
```
User Access (controlled by OS firewall):
┌──────────────────────────────────────────┐
│ Localhost:    http://127.0.0.1:7272      │
│ LAN (if fw):  https://10.1.0.164:7272   │
│ WAN (if fw):  https://example.com:443   │
└───────────────────┬──────────────────────┘
                    │
                    ▼
       ┌────────────────────────┐
       │  FastAPI Server        │
       │  Port: 7272            │
       │  Serves: API + WS +   │
       │  MCP + Frontend (SPA)  │
       │  Auth: JWT Required    │
       └────────────┬───────────┘
                    │
                    │ localhost only (security)
                    ▼
       ┌────────────────────────┐
       │  PostgreSQL Database   │
       │  Host: localhost       │
       │  Port: 5432            │
       └────────────────────────┘
```

**Architecture Principles**:
- Single unified architecture (production runs on one port)
- Development mode adds Vite HMR on port 7274 (optional)
- Database always on localhost (maximum security)
- ONE authentication flow for all connections
- Multi-tenant isolation at database level

### Agent Job Management Architecture

**Components**:
1. **AgentJobManager** - Job lifecycle management (92% test coverage)
2. **AgentCommunicationQueue** - Inter-agent messaging (100% pass rate)
3. **JobCoordinator** - Job spawning and coordination (90% coverage)
4. **WebSocket Integration** - Real-time job events
5. **REST API** - 13 endpoints for job control

**Features**:
- Parent-child job hierarchies
- Message acknowledgment tracking
- JSONB message storage for efficiency
- Priority-based queue system
- Terminal state management (completed/failed)

### Orchestrator Context Architecture

**Focused context delivery** achieved through:

1. **Hierarchical Context Loading**:
   - Load base context (project info, current task)
   - Load role-specific context only
   - Load related context (parent agent, recent messages)
   - Skip irrelevant context (other projects, old messages)

2. **Serena MCP Optimization Layer**:
   - Symbolic operations (find_symbol vs read_file)
   - Mission-time optimization rule injection
   - Context-based handoff triggers

**Key Features**:
- Agents receive focused, relevant context instead of full product dumps
- Vision document chunking for files > 100KB
- User-controlled depth settings via toggle cards in My Settings

### Multi-Tenant Isolation

**Isolation Throughout**:
- Database queries: ALL filter by tenant_key
- API endpoints: 404 for cross-tenant access
- WebSocket events: Scoped to tenant
- Job management: Tenant-specific queues
- Context chunks: Tenant isolation

**Security Verification**:
- 40+ item security checklist (Handover 0019)
- GDPR, SOC 2, HIPAA compliance ready
- Attack scenario testing completed
- 7-step isolation verification procedure

### Platform Handler System

**Cross-Platform Architecture** (Handover 0035):

**Strategy Pattern Implementation**:
```
installer/
├── platforms/
│   ├── base.py          # Abstract PlatformHandler interface
│   ├── windows.py       # Windows-specific operations
│   ├── linux.py         # Linux-specific operations
│   ├── macos.py         # macOS-specific operations
│   └── __init__.py      # Auto-detection logic
├── core/
│   ├── database.py      # Unified DB setup (pg_trgm extension)
│   └── config.py        # Configuration generation
└── shared/
    ├── postgres.py      # PostgreSQL discovery
    └── network.py       # Network utilities
```

**Benefits**:
- 25.6% code reduction vs platform-specific installers
- Unified configuration generation
- Consistent user experience
- Easy to add new platforms

---

## Security Features

### Password Security
- bcrypt hashing with cost factor 12
- Minimum 12 characters required
- Complexity requirements: uppercase, lowercase, digit, special character
- Default password forced change on first login
- Password strength meter with real-time feedback

### Recovery PIN System
- 4-digit numeric PIN (bcrypt hashed)
- Separate from password for redundancy
- Rate limiting: 5 failed attempts = 15 minute lockout
- Failed attempt tracking per user
- Self-service password reset (no email needed)

### Admin Password Reset
- Admins can reset user passwords to default: "GiljoMCP"
- User must set recovery PIN on next login
- Complete account setup flow enforced
- Audit trail of password resets

### Authentication
- JWT token-based authentication
- Token expiration: 24 hours (configurable)
- Required for ALL connections (localhost, LAN, WAN)
- WebSocket authentication via query params/headers
- No IP-based auto-login exceptions

### Defense in Depth
1. **OS Firewall** - First layer (access control)
2. **Application Authentication** - JWT validation
3. **Password Policy** - Complexity requirements
4. **Database Isolation** - Localhost only, never exposed
5. **HTTPS/TLS** - Encrypted transport (WAN deployments)

### First Admin Creation
- Created during setup wizard (no defaults)
- User defines all credentials
- Recovery PIN set immediately
- No hardcoded accounts
- Forced password change removed (user creates strong password upfront)

---

## Documentation

### Getting Started
- **[Installation Guide](docs/INSTALLATION_FLOW_PROCESS.md)** - Complete installation walkthrough
- **[Quick Start Guide](docs/FIRST_LAUNCH_EXPERIENCE.md)** - From install to first project
- **[Architecture Overview](docs/SERVER_ARCHITECTURE_TECH_STACK.md)** - System design and tech stack
- **[README First](docs/README_FIRST.md)** - Central navigation hub

### User Guides
- **[Password Reset Guide](docs/manuals/PASSWORD_RESET_USER_GUIDE.md)** - Recovery PIN and password reset
- **[MCP Tools Manual](docs/manuals/MCP_TOOLS_MANUAL.md)** - Complete MCP tools reference
- **[Testing Manual](docs/manuals/TESTING_MANUAL.md)** - Testing strategies and guides

### Technical Documentation
- **[Agent Job Management API](docs/api/AGENT_JOBS_API_REFERENCE.md)** - 13 REST endpoints, WebSocket events
- **[Multi-Tenant Architecture](docs/USER_STRUCTURES_TENANTS.md)** - Tenant isolation design
- **[MCP-over-HTTP Integration](docs/MCP_OVER_HTTP_INTEGRATION.md)** - Claude Code integration
- **[Serena Optimization](docs/optimization/)** - Context prioritization system

### Handover Documentation
- **[Handover 0019 - Agent Jobs](docs/HANDOVER_0019_COMPLETION_SUMMARY.md)** - Job management system
- **[Handover 0020 - Orchestrator](docs/archive/handovers/)** - context prioritization and orchestration
- **[Handover 0023 - Password Reset](docs/archive/handovers/)** - Recovery PIN system
- **[Handover 0027 - Integrations Tab](docs/handovers/0027_supporting_docs/)** - Admin settings redesign

### API Documentation
- **Swagger UI**: http://localhost:7272/docs
- **ReDoc**: http://localhost:7272/redoc
- **OpenAPI Spec**: http://localhost:7272/openapi.json

---

## Technology Stack

**Backend**:
- Python 3.12+
- FastAPI (REST API + WebSocket)
- SQLAlchemy (ORM with async support)
- PostgreSQL 18 (required - no SQLite)
- Pydantic v2 (validation)
- bcrypt (password hashing)

**Frontend**:
- Vue 3 (Composition API)
- Vuetify 3 (Material Design 3)
- Vue Router (navigation)
- Axios (HTTP client)
- WebSocket (real-time updates)

**Development**:
- pytest (testing framework)
- Ruff (linting)
- Black (formatting)
- Coverage.py (code coverage)

**Deployment**:
- Cross-platform installer (Windows/Linux/macOS)
- PostgreSQL 18 required
- No Docker required (native installation)

---

## For Developers

### Model Imports (Post-Handover 0128a)

The models package has been refactored into domain-specific modules for better organization.

**✅ Preferred (New Code)**:
```python
# Use modular imports for clarity
from src.giljo_mcp.models.auth import User, APIKey, MCPSession
from src.giljo_mcp.models.projects import Project
from src.giljo_mcp.models.agents import MCPAgentJob, AgentInteraction
from src.giljo_mcp.models.products import Product, VisionDocument
from src.giljo_mcp.models.tasks import Task, Message
```

**⚠️ Legacy (Existing Code Only)**:
```python
# This still works but is discouraged for new code
from src.giljo_mcp.models import User, Project, MCPAgentJob
```

**Module Organization**:
- `models.auth` - User authentication and API keys
- `models.projects` - Project and session management
- `models.agents` - Agent job orchestration
- `models.products` - Product and vision documents
- `models.tasks` - Task and message management
- `models.templates` - Agent templates
- `models.context` - Context indexing
- `models.config` - System configuration

See `src/giljo_mcp/models/__init__.py` for complete documentation.

---

### Smoke Tests for Critical Workflows (0511a)

Run lightweight smoke tests before deployments to verify the most important backend workflows:

```bash
pytest tests/smoke -m smoke -v
```

These tests cover:
- Product creation with vision upload + chunking
- Project lifecycle (create → activate → launch → deactivate)
- Orchestrator succession trigger
- Multi-tenant isolation behaviour
- Settings persistence for a test tenant

---

## Support

**Issues**: https://github.com/patrik-giljoai/GiljoAI-MCP/issues
**Documentation**: [docs/README_FIRST.md](docs/README_FIRST.md)
**License**: See LICENSE file
**Contributing**: See CONTRIBUTING.md

---

**Made with precision by GiljoAI - Breaking through AI context limits since 2024**
