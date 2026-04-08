# README FIRST - GiljoAI MCP Architecture Overview

> **Central navigation hub for understanding GiljoAI MCP v3.0 architecture, fresh installation flow, security model, and system design.**

## 📋 Core Documentation (October 2025)

**New single-truth documents** - Start here for comprehensive understanding:

- **[System Purpose & Capabilities](GILJOAI_MCP_PURPOSE.md)** - What GiljoAI MCP does, key features, and value proposition
- **Multi-Tenant Architecture** - User management, tenant isolation, and database design (see Server Architecture below)
- **[Server Architecture & Tech Stack](SERVER_ARCHITECTURE_TECH_STACK.md)** - v3.0 unified architecture, ASCII diagrams, tech stack
- **[Installation Flow & Process](INSTALLATION_FLOW_PROCESS.md)** - Complete installation walkthrough and cross-platform setup
- **[First Launch Experience](user_guides/FIRST_LAUNCH_EXPERIENCE.md)** - Step-by-step onboarding from install to dashboard
- **[MCP-over-HTTP Integration](api/MCP_OVER_HTTP_INTEGRATION.md)** - Connecting Claude Code via HTTP transport (zero dependencies)
- **[Edition & Licensing Strategy](../LICENSING_AND_COMMERCIALIZATION_PHILOSOPHY.md)** - Community Edition (single-user, free) vs SaaS Edition (multi-user, commercial). Architecture split: [0770 SaaS Edition Proposal](../handovers/0770_SAAS_EDITION_PROPOSAL.md)

### 📌 Single Source of Truth (SSoT) Documents

**Authoritative references for critical workflows** - These documents are maintained as the definitive source for their topics:

- **[Orchestrator Context Flow SSoT](architecture/ORCHESTRATOR_CONTEXT_FLOW_SSoT.md)** - Complete orchestrator workflow from user setup to agent execution (13 context cards, 77% context prioritization, 9 context sources)
- **[SaaS Edition Proposal (0770)](../handovers/0770_SAAS_EDITION_PROPOSAL.md)** - Architectural decision record: Community vs SaaS split, fork strategy (one repo now, split before publish), resolved licensing decisions
- **[Edition Isolation Guide](EDITION_ISOLATION_GUIDE.md)** - Authoritative guide for CE/SaaS code separation: directory structure, import rules, conditional loading patterns, git workflow, migration strategy

**New Implementation Features** (October 2025):

- **[AI Tool Configuration Management](guides/AI_TOOL_CONFIGURATION_MANAGEMENT.md)** - Multi-AI coding agent support via user settings (Claude, CODEX, Gemini)
- **Template System Evolution** - Database-backed templates with AI coding agent preferences (managed via UnifiedTemplateManager)

**Recent Production Features**:

- **Agent Monitoring & Graceful Cancellation (Handover 0107)** - Contextual check-ins, passive health monitoring, graceful cancellation
- **Project Soft Delete with Recovery (Handover 0070)** - 10-day recovery window with UI in Settings → Database
- Single Active Product Architecture (Handover 0050) - One active product per tenant with database enforcement. **Extension (0050b)**: Projects also follow single-active pattern - one active project per product with cascade deactivation. See features/project_state_management.md and SERVER_ARCHITECTURE_TECH_STACK.md for details.
- Context Toggle Management (Handover 0052) - User-customizable field toggles and depth controls
- Multi-Tool Agent Orchestration (Handover 0045) - 40-60% cost optimization via tool mixing
- Products View Unified Management (Handover 0046) - Complete product lifecycle management
- Product Rich Context Fields (Handover 0042) - 13+ fields for maximum agent context
- Agent Template Database Integration (Handover 0041) - Customizable agent behavior with three-layer caching
- Unified Cross-Platform Installer (Handover 0035) - Windows, Linux, macOS support
- Admin Settings v3.0 Overhaul (Handovers 0025-0029) - Modern, cohesive interface
- Context-Focused Orchestration (Handover 0020) - Efficient context delivery
- Agent Job Management System (Handover 0019) - Multi-agent coordination foundation
- Agent Flow Visualization (Handover 0040) - Flow-based, real-time UI for multi-agent orchestration

## Table of Contents

1. [System Architecture Summary](#system-architecture-summary)
2. [Platform Support](#platform-support)
3. [Fresh Factory Installation Flow](#fresh-factory-installation-flow)
4. [v3.0 Unified Authentication](#v30-unified-authentication)
5. [Security Setup](#security-setup)
6. [Network Topology & Implementation](#network-topology--implementation)
7. [Core Components](#core-components)
8. [Context Management Logic](#context-management-logic)
9. [Additional Documentation](#additional-documentation)
10. [Testing](#testing)
11. [Quick Start](#quick-start)

---

## System Architecture Summary

GiljoAI MCP is a multi-agent orchestration system that transforms AI coding assistants into coordinated development teams. It breaks through context limits by orchestrating multiple specialized agents that work together on complex tasks.

### Core Components

1. **Orchestrator** (`src/giljo_mcp/orchestrator.py`)
   - Multi-agent coordination engine
   - Agent spawning with role templates
   - Intelligent handoff mechanism
   - Context usage tracking
   - Multi-project support with tenant isolation

2. **Database** (PostgreSQL 18 - Required)
   - Connection pooling via SQLAlchemy
   - Multi-tenant isolation through filtered queries
   - Async and sync session support
   - **Tables created via Base.metadata.create_all()** (NOT Alembic)

3. **API Server** (FastAPI - REST + WebSocket)
   - RESTful endpoints for all resources
   - WebSocket for real-time updates
   - JWT-based authentication
   - CORS and rate limiting

4. **Frontend** (Vue 3 + Vuetify)
   - Real-time agent monitoring
   - Project and task management UI
   - WebSocket integration for live updates
   - Responsive design (mobile, tablet, desktop)

5. **MCP Integration Layer**
   - 22+ MCP tools for agent coordination
   - Project, agent, message, task, context management
   - Template system for agent roles
   - Git integration for version control
   - **MCP-over-HTTP** endpoint for zero-dependency Claude Code integration

### v3.0 Unified Architecture Principles

**ONE Authentication Flow**:
- NO localhost auto-login
- Same authentication for localhost, LAN, WAN
- Fresh install detection: User count = 0
- Admin account: Created via /welcome → /first-login flow
- JWT-based session management

**Network Binding**:
- Localhost installs: API binds to 127.0.0.1 (HTTP, no network exposure)
- LAN/WAN installs: API binds to 0.0.0.0 with mandatory HTTPS (mkcert)
- Database always on localhost (never exposed to network)

**Multi-Tenant Isolation**:
- All database queries filtered by `tenant_key`
- Default tenant: "default"
- Tenant scoping for projects, agents, messages, tasks

---

## Platform Support

**Unified Cross-Platform Installer** (v3.1.0+ - Handover 0035):

**Status**: Production ready (October 2025)

Supported Platforms:
- Windows 10/11 - Fully tested
- Linux (Ubuntu 22.04+, Fedora 40+, Debian 12+) - Fully tested
- macOS (13+, Intel and ARM) - Fully tested

**Single installer for all platforms:**
```bash
python install.py
```

**Platform auto-detection**: Automatically detects your OS and uses appropriate platform handlers.

**Platform-Specific Features:**
- **Windows**: Desktop shortcuts (.lnk), PostgreSQL detection in Program Files
- **Linux**: Desktop launchers (.desktop), distribution-specific installation guides
- **macOS**: Homebrew support (Intel and ARM), Postgres.app detection

**Architecture**: Strategy pattern with isolated platform handlers (`installer/platforms/`)

**Complete Documentation**: See [Installation Flow & Process](INSTALLATION_FLOW_PROCESS.md) for the full installation guide.

---

## Fresh Factory Installation Flow

### 1. Installation (install.py)

**Command**:
```bash
python install.py
```

**CRITICAL**: Uses `DatabaseManager.create_tables_async()` (same as api/app.py:186)

**What Happens**:

**1. Environment Detection**:
- Detects PostgreSQL 18 installation
- Validates database connectivity
- Checks port availability (7272, 7274)

**2. Database Setup**:
- Creates `giljo_mcp` database
- **Creates all tables using Base.metadata.create_all()** (NOT Alembic)
- Initializes setup state (user count = 0)

**3. NO Default Admin Created**:
- **User count = 0** → Fresh install detected by router
- No default credentials (admin/admin eliminated)
- First admin created via browser flow

**4. Configuration Generation**:
- Creates `config.yaml` at project root
- Creates `.env` with database credentials
- Both files are gitignored (local only)

**5. Service Startup**:
- Starts API server on port 7272 (bind address from install config)
- Starts frontend dev server on port 7274
- Opens browser to `http://localhost:7274`

### 2. First Access (Fresh Install Flow)

**User visits**: `http://localhost:7274`

**Flow**:

**1. Router Navigation Guard**:
- Checks user count via `GET /api/auth/user-count`
- If count = 0, redirects to `/welcome`

**2. Welcome Screen** (`/welcome`):
- Displays welcome message
- Explains fresh install setup
- "Continue" button → redirects to `/first-login`

**3. First Login Screen** (`/first-login`):
- Create admin account form
- Fields:
  - Username (required)
  - Password (minimum 12 characters, complexity requirements)
  - Confirm Password
  - Recovery PIN (4-digit, for password reset)
  - Confirm Recovery PIN
- Real-time validation and password strength meter

**4. Admin Account Creation**:
- `POST /api/auth/create-first-admin`
- Backend validates user count = 0 (race condition protection)
- Creates admin user with bcrypt-hashed password and PIN
- Endpoint automatically disables (user count > 0)
- Returns JWT token for immediate login
- Token stored in localStorage

**5. Redirect to Dashboard**:
- User redirected to `/dashboard`
- WebSocket connection established (authenticated mode)
- Ready for normal operation

### 3. Normal Operation

**Login Flow**:
- User visits application
- Router redirects to `/login` (if not authenticated)
- Login with username and password
- `POST /api/auth/login`
- JWT token returned and stored
- Redirected to `/dashboard`
- WebSocket connection requires JWT token

**Dashboard**:
- Real-time agent monitoring
- Project and task management
- Live updates via WebSocket
- Multi-tenant data isolation

**AI Coding Agent Configuration** (Avatar → My Settings → API and Integrations):
- **AI Coding Agent MCP Configurator**: One-click setup for Claude Code, CODEX, Gemini
- **Manual AI Coding Agent Configuration**: Custom setup for any AI coding agent
- **Personal API Keys**: Generate and manage user API keys
- **Serena MCP**: Advanced code analysis integration

**Project Recovery** (Avatar → Settings → Database tab):
- **Deleted Projects**: View all soft-deleted projects
- **Recovery Window**: 10-day window to restore deleted projects
- **Purge Countdown**: Visual countdown showing days until permanent deletion
- **One-Click Restore**: Restore deleted projects to inactive status
- **Auto-Purge**: Projects automatically purged after 10 days (on startup)

---

## v3.0 Unified Authentication

### Architecture

**ONE Authentication Flow for ALL Connections**:
- Localhost (`127.0.0.1`): Requires authentication
- LAN (`10.x.x.x`, `192.168.x.x`): Requires authentication
- WAN (public IP/domain): Requires authentication
- **No IP-based special treatment**

### Authentication Mechanism

**JWT Tokens**:
- Issued on successful login or password change
- Stored in localStorage (client-side)
- Included in API requests via `Authorization: Bearer <token>` header
- Included in WebSocket connections via query params or headers
- Expiration: Configurable (default: 24 hours)

**Password Security**:
- bcrypt hashing (cost factor: 12)
- Minimum 12 characters
- Complexity requirements enforced
- Default password forced change

### WebSocket Authentication

**Standard Operation**:
```javascript
// Require JWT token for ALL WebSocket connections
const token = websocket.query_params.get('token')
if (!token || !validate_token(token)) {
  close_connection(code=1008, reason='Authentication required')
}
```

---

## Security Setup

### User Management

**First User Setup**:
- No default credentials exist
- First user is created via the `/welcome` setup wizard
- After setup, login at `/first-login`
- Admin resets use recovery PIN (4-digit PIN with rate limiting)
- Default password for admin resets only: "GiljoMCP"

**Password Policy**:
- Minimum 12 characters
- At least 1 uppercase letter
- At least 1 lowercase letter
- At least 1 digit
- At least 1 special character
- bcrypt hashing

**Role-Based Access Control (RBAC)**:
- Admin: Full system access
- User: Project-level access

### Multi-Tenancy

**Tenant Isolation at Database Level**:
- All queries filtered by `tenant_key`
- Default tenant: `"default"`
- Projects, agents, messages, tasks scoped to tenant
- No cross-tenant data leakage

**Tenant Structure**:
```sql
-- All tables have tenant_key column
SELECT * FROM projects WHERE tenant_key = 'default';
SELECT * FROM agents WHERE tenant_key = 'default';
SELECT * FROM messages WHERE tenant_key = 'default';
```

### Orchestration Security

**Agent Authentication**:
- Agents authenticated via parent project
- Project validates tenant_key
- Agent spawning requires valid project context

**Message Queue Validation**:
- All messages validated for tenant_key
- No cross-tenant message passing
- Priority-based queue per tenant

**Context Access Isolation**:
- Context chunks scoped to tenant
- Vision documents tenant-isolated
- Template tenant scoping

### User/Project Roles

**Status**: Coming soon (v3.1)
- User roles per project (owner, contributor, viewer)
- Permission inheritance
- Project-level access control
- Fine-grained permissions

---

## Network Topology & Implementation

### v3.0 Architecture Diagram

```
User Access (controlled by OS firewall):
┌──────────────────────────────────────────┐
│ Localhost:    http://127.0.0.1:7272      │
│ LAN (if fw):  http://10.1.0.164:7272     │
│ WAN (if fw):  https://example.com:443    │
└───────────────────┬──────────────────────┘
                    │
                    ▼
       ┌────────────────────────┐
       │  API Server (FastAPI)  │
       │  Binds to: 0.0.0.0     │ ← ALWAYS all interfaces
       │  Port: 7272            │
       │  Auth: JWT Required    │
       └────────────┬───────────┘
                    │
                    │ ALWAYS localhost (security)
                    ▼
       ┌────────────────────────┐
       │  PostgreSQL Database   │
       │  Host: localhost       │ ← NEVER exposed to network
       │  Port: 5432            │
       │  Binding: 127.0.0.1    │
       └────────────────────────┘
```

### Security Layers (Defense in Depth)

**1. OS Firewall** - First layer
- Blocks unauthorized network access
- Configurable rules per deployment
- Default: Localhost only

**2. Application Authentication** - Second layer
- JWT token validation
- Password-based login
- Session management

**3. Password Policy** - Third layer
- Complexity requirements
- Forced change from default
- bcrypt hashing

**4. Database Isolation** - Fourth layer
- PostgreSQL on localhost only
- Never exposed to network
- Multi-tenant row-level isolation

**5. HTTPS/TLS** - Fifth layer (WAN deployments)
- Encrypted transport
- Certificate validation
- Reverse proxy (nginx, Caddy)

### Network Configuration

**Configured during install.py**:
- User selects `external_host`:
  - `localhost` - Local development
  - `<LAN IP>` - LAN access (e.g., `10.1.0.164`)
  - `<domain>` - WAN access (e.g., `example.com`)
- Frontend uses `external_host` for API/WebSocket connections
- Backend always `localhost` for database

**Example config.yaml**:
```yaml
services:
  api:
    host: 127.0.0.1     # localhost track; LAN/WAN uses 0.0.0.0 + HTTPS
    port: 7272
    external_host: localhost  # How clients connect

database:
  host: localhost     # Always localhost
  port: 5432
```

---

## Core Components

### Orchestrator

**File**: `src/giljo_mcp/orchestrator.py`

**Responsibilities**:
- Multi-agent coordination
- Agent spawning with role templates
- Intelligent handoff mechanism
- Context usage tracking
- Project lifecycle management

**Key Features**:
- Template-based agent creation
- Message queue for inter-agent communication
- Context chunking for large files
- Tenant isolation
- Graceful error handling

### Database Layer

**File**: `src/giljo_mcp/database.py`

**Architecture**:
- PostgreSQL 18 (required)
- SQLAlchemy ORM
- Connection pooling
- Async and sync sessions
- Table creation via install.py (Base.metadata.create_all)

**Models** (`src/giljo_mcp/models.py`):
- User, Project, Agent, Message, Task
- Context, ContextChunk, Template
- SetupState, SystemConfig

**Table Creation**:
- Uses DatabaseManager.create_tables_async()
- Called during install.py and api/app.py startup
- **NOT using Alembic migrations**

### MCP Tools

**Location**: `src/giljo_mcp/tools/`

**Categories**:
- Project management (`project.py`)
- Agent management (`agent.py`)
- Message passing (`message.py`)
- Task management (`task.py`)
- Context management (`context.py`, `chunking.py`, `context_manager.py`)
- Template management (`template.py`)

**Total**: 22+ tools for agent coordination

### API Layer

**File**: `api/app.py`

**Endpoints**:
- `/auth/*` - Authentication (login, password change)
- `/users/*` - User settings and AI coding agent configuration
- `/projects/*` - Project CRUD
- `/agents/*` - Agent management
- `/tasks/*` - Task management
- `/messages/*` - Message queue
- `/ws` - WebSocket for real-time updates

**Technologies**:
- FastAPI framework
- Pydantic models for validation
- JWT authentication
- CORS middleware
- Rate limiting

### Frontend

**Location**: `frontend/`

**Stack**:
- Vue 3 (Composition API)
- Vuetify 3 (Material Design 3)
- Vue Router for navigation
- Axios for API calls
- WebSocket for real-time updates

**Views**:
- Login (`/login`)
- Password Change (`/change-password`)
- Dashboard (`/dashboard`)
- User Settings (`/settings`)
- Projects, Agents, Tasks, Messages

---

## Context Management Logic

**Status**: Core feature, actively used

### Hierarchical Context Loading

**Purpose**: Smart context loading for focused agent delivery

**Strategy**:
1. Load base context (project info, current task)
2. Load role-specific context (only relevant templates)
3. Load related context (parent agent, recent messages)
4. Skip irrelevant context (other projects, old messages)

### Vision Document Chunking

**Purpose**: Handle large files via chunking (25K ingest limit)

**Process**:
1. Detect file size > threshold (default: 100KB)
2. Split into semantic chunks (functions, classes, sections)
3. Store chunks with metadata (file, line range, hash)
4. Load relevant chunks only (based on query/task)

---

## Additional Documentation

### Core Documentation

- **[Server Architecture & Tech Stack](SERVER_ARCHITECTURE_TECH_STACK.md)** - Detailed system design and patterns
- **`docs/guides/`** - Setup and configuration guides

### Development Documentation

- **`docs/devlog/`** - Development logs and completion reports
- **`docs/sessions/`** - Agent session memories

### User Guides

- **[Orchestrator Succession Guide](user_guides/orchestrator_succession_guide.md)** - End-user guide for orchestrator succession (Handover 0080)

### Developer Guides

- **[Orchestrator Succession Developer Guide](guides/orchestrator_succession_developer_guide.md)** - Technical implementation details for orchestrator succession (Handover 0080)

### Quick Reference

- **[Orchestrator Succession Quick Reference](guides/succession_quick_ref.md)** - One-page cheat sheet for succession features

### UI/UX (October 2025)

**Handover 0009 - Advanced UI/UX Verification** (COMPLETE - HARMONIZED - 90% Implementation):
- Production-ready UI/UX with 85/100 accessibility score (92/100 after 45-min fixes)
- Comprehensive asset integration (80+ icons, 4 mascot states)
- Detailed audit documents archived to `docs/archive/retired-2026-01/`

### Serena MCP Optimization Layer (October 2025)

**Handover 0010 - Serena MCP Optimization Implementation** (✅ COMPLETE - HARMONIZED):
- **Serena Context Analytics**: Optimization signals powered by symbolic operations
- **Core Concept**: Encourages symbolic operations (find_symbol) over naive file reading for focused context delivery
- **Features**:
  - Automatic symbolic operation enforcement (find_symbol vs read_file)
  - Mission-time optimization rule injection
  - Intelligent context-based handoff triggers

**Integration**: Automatically active in ProjectOrchestrator for all agent spawns

### User API Key Management (October 2025)

**Handover 0015 - User API Key Management** (✅ COMPLETE - HARMONIZED):
- **Frontend Components**:
  - `ApiKeyManager.vue` (266 lines) - Full-featured key management UI
  - `ApiKeyWizard.vue` - Key generation modal
  - Integrated into UserSettings → API and Integrations tab
- **AI Coding Agent Integration**:
  - `AIToolSetup.vue` - Automatic key generation during config creation
  - One-click generation for Claude Code, CODEX, Gemini
  - User API keys automatically embedded in configurations
- **Security Features**:
  - Per-user API key generation with tenant isolation
  - Bcrypt hashing with one-time plaintext display
  - Full lifecycle management (generate, list, revoke)
  - httpOnly cookie authentication documented

**Integration**: Available in Settings → API and Integrations → Personal API Keys

---

### API Documentation

- **Interactive docs**: `http://localhost:7272/docs` (Swagger UI)
- **ReDoc**: `http://localhost:7272/redoc`
- **OpenAPI spec**: `http://localhost:7272/openapi.json`
- **Prompts API**: See `docs/api/prompts_endpoints.md` (Thin Client endpoint)


---

## Testing

See [TESTING.md](TESTING.md) for testing strategies, pytest commands, and coverage targets (>80% across all services and endpoints).

```bash
# Run all tests with coverage
pytest tests/ --cov=src/giljo_mcp --cov=api --cov-report=html

# Service layer only
pytest tests/services/ -v

# Integration tests only
pytest tests/integration/ -v
```

---

## Quick Start

**Fresh Installation**:
```bash
# 1. Clone repository
git clone https://github.com/giljoai/GiljoAI_MCP.git
cd GiljoAI_MCP

# 2. Install dependencies
pip install -r requirements.txt

# 3. Run installer
python install.py

# 4. Access application
# Browser opens to http://localhost:7274
# First Login
# Configure AI coding agents via Avatar → My Settings → API & Integrations
# Start building!
```

**Service Management**:
```bash
# Start all services
python start_giljo.py

# Start API only
python api/run_api.py

# Start frontend only
cd frontend/ && npm run dev
```

---

## Support & Contribution

- **Issues**: https://github.com/giljoai/GiljoAI_MCP/issues
- **Documentation**: `docs/README_FIRST.md` (this file)
- **License**: See LICENSE file
- **Edition**: GiljoAI MCP Community Edition (GiljoAI Community License v1.1). See [Licensing Philosophy](../LICENSING_AND_COMMERCIALIZATION_PHILOSOPHY.md)
- **Contributing**: See CONTRIBUTING.md

---

## Documentation Harmonization

GiljoAI MCP documentation has been harmonized into single-truth documents to eliminate fragmentation and architectural conflicts. The core documents listed at the top of this file are the authoritative references.

**Legacy documentation** has been archived to `docs/archive/` for reference.

---

**Last Updated**: February 2026 (broken link cleanup, removed dead handover references)
