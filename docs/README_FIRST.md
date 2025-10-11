# README FIRST - GiljoAI MCP Architecture Overview

> **Central navigation hub for understanding GiljoAI MCP v3.0 architecture, fresh installation flow, security model, and system design.**

## Table of Contents

1. [System Architecture Summary](#system-architecture-summary)
2. [Fresh Factory Installation Flow](#fresh-factory-installation-flow)
3. [v3.0 Unified Authentication](#v30-unified-authentication)
4. [Security Setup](#security-setup)
5. [Network Topology & Implementation](#network-topology--implementation)
6. [Core Components](#core-components)
7. [Context Management Logic](#context-management-logic)
8. [Additional Documentation](#additional-documentation)

---

## System Architecture Summary

GiljoAI MCP Coding Orchestrator is a multi-agent orchestration system that transforms AI coding assistants into coordinated development teams. It breaks through context limits by orchestrating multiple specialized agents that work together on complex tasks.

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

### v3.0 Unified Architecture Principles

**ONE Authentication Flow**:
- NO localhost auto-login
- Same authentication for localhost, LAN, WAN
- Default credentials: admin/admin (fresh install only)
- Forced password change on first access
- JWT-based session management

**Network Binding**:
- API always binds to 0.0.0.0 (all network interfaces)
- OS firewall controls access (defense in depth)
- Database always on localhost (never exposed to network)

**Multi-Tenant Isolation**:
- All database queries filtered by `tenant_key`
- Default tenant: "default"
- Tenant scoping for projects, agents, messages, tasks

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
- Validates database connectivity (password: 4010)
- Checks port availability (7272, 7274)

**2. Database Setup**:
- Creates `giljo_mcp` database
- **Creates all tables using Base.metadata.create_all()** (NOT Alembic)
- Initializes setup state

**3. Default Admin Account Creation**:
- Creates user with username: `admin`, password: `admin`
- Password hashed with bcrypt
- Sets `default_password_active: true` in setup_state table
- Displays credentials in terminal:
  ```
  ====================================
  Default Admin Credentials:
    Username: admin
    Password: admin

  ⚠️ IMPORTANT: Change this password on first login!
  ====================================
  ```

**4. Configuration Generation**:
- Creates `config.yaml` at project root
- Creates `.env` with database credentials
- Both files are gitignored (local only)

**5. Service Startup**:
- Starts API server on port 7272 (binds to 0.0.0.0)
- Starts frontend dev server on port 7274
- Opens browser to `http://localhost:7274`

### 2. First Access (Any IP)

**User visits**: `http://localhost:7274` OR `http://<network-ip>:7274`

**Flow**:

**1. Router Navigation Guard**:
- Checks setup state via `GET /api/setup/status`
- If `default_password_active: true`, redirects to `/change-password`

**2. Password Change Screen** (`/change-password`):
- Forced password change form (cannot skip)
- Pre-filled username: `admin`
- Current password hint: `admin`
- New password requirements:
  - Minimum 12 characters
  - At least 1 uppercase letter
  - At least 1 lowercase letter
  - At least 1 digit
  - At least 1 special character (!@#$%^&*()_+-=[]{}|;:,.<>?)
- Real-time password strength meter
- Confirmation field (must match)

**3. Password Change Submission**:
- `POST /api/auth/change-password`
- Backend validates current password is `admin`
- Validates new password meets requirements
- Updates admin user password_hash (bcrypt)
- Sets `default_password_active: false`
- Records `password_changed_at` timestamp
- Returns JWT token for immediate login
- Token stored in localStorage

**4. Redirect to Setup Wizard**:
- User redirected to `/setup`
- WebSocket connection established (setup mode - no auth required)

### 3. Setup Wizard (3 Steps)

**Step 1: MCP Configuration** (Optional)
- Configure Model Context Protocol integration
- Download setup scripts:
  - Claude Desktop MCP config (`.claude.json`)
  - VS Code MCP config (`.vscode/settings.json`)
  - CLI setup scripts
- Enable/disable toggle
- Skip button allowed
- Saves state: `mcp_configured: true/false`

**Step 2: Serena Activation** (Optional)
- Enable/disable Serena MCP server
- Serena provides:
  - Advanced code analysis
  - Symbolic navigation
  - Semantic search
- Installation guide (uvx or local)
- Skip button allowed
- Saves state: `serena_enabled: true/false`

**Step 3: Complete** (Summary)
- Configuration summary:
  - MCP Integration: Enabled/Disabled
  - Serena MCP Server: Enabled/Disabled
- Links to documentation
- "Go to Dashboard" button
- Marks `setup_completed: true`
- `POST /api/setup/complete`

### 4. Normal Operation

**Login Flow** (after setup):
- User visits application
- Router redirects to `/login` (if not authenticated)
- Login with new password (not default)
- `POST /api/auth/login`
- JWT token returned and stored
- Redirected to `/dashboard`
- WebSocket connection requires JWT token

**Dashboard**:
- Real-time agent monitoring
- Project and task management
- Live updates via WebSocket
- Multi-tenant data isolation

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

**Setup Mode** (`setup_completed: false`):
```javascript
// Allow WebSocket without authentication for setup progress updates
if (!setup_completed && path === '/ws/setup') {
  return { allowed: true, context: 'setup' }
}
```

**Post-Setup** (`setup_completed: true`):
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

**Default Admin Account**:
- Created during installation
- Username: `admin`
- Password: `admin` (temporary, must change)
- Role: `admin`
- Tenant: `default`

**Password Policy**:
- Minimum 12 characters
- At least 1 uppercase letter
- At least 1 lowercase letter
- At least 1 digit
- At least 1 special character
- bcrypt hashing

**Role-Based Access Control (RBAC)**:
- Admin: Full system access
- User: Project-level access (coming soon)

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
    host: 0.0.0.0       # Always bind to all interfaces
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
- Alembic migrations

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
- Task management (`task.py`, `task_templates.py`)
- Context management (`context.py`, `chunking.py`, `context_manager.py`)
- Template management (`template.py`)
- Git integration (`git.py`)

**Total**: 22+ tools for agent coordination

### API Layer

**File**: `api/app.py`

**Endpoints**:
- `/auth/*` - Authentication (login, password change)
- `/projects/*` - Project CRUD
- `/agents/*` - Agent management
- `/tasks/*` - Task management
- `/messages/*` - Message queue
- `/setup/*` - Setup wizard state
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
- Setup Wizard (`/setup`)
- Dashboard (`/dashboard`)
- Projects, Agents, Tasks, Messages

---

## Context Management Logic

**Status**: Core feature, actively used

### Hierarchical Context Loading

**Purpose**: Reduce token usage by 60% via smart loading

**Strategy**:
1. Load base context (project info, current task)
2. Load role-specific context (only relevant templates)
3. Load related context (parent agent, recent messages)
4. Skip irrelevant context (other projects, old messages)

### Vision Document Chunking

**Purpose**: Handle large files that exceed token limits

**Process**:
1. Detect file size > threshold (default: 100KB)
2. Split into semantic chunks (functions, classes, sections)
3. Store chunks with metadata (file, line range, hash)
4. Load relevant chunks only (based on query/task)

### Context Usage Tracking

**Purpose**: Monitor and optimize token consumption

**Metrics**:
- Total tokens used per agent
- Tokens per message
- Context size per request
- Chunking efficiency

**Optimization**:
- Adaptive chunk sizing
- Cache frequently accessed chunks
- Expire old context automatically

---

## Additional Documentation

### Core Documentation

- **`CLAUDE.md`** - Agent context and coding guidelines for Claude Code
- **`docs/TECHNICAL_ARCHITECTURE.md`** - Detailed system design and patterns
- **`docs/deployment/`** - Deployment guides (LAN, WAN, Docker)
- **`docs/guides/`** - Setup and configuration guides

### Development Documentation

- **`docs/manuals/MCP_TOOLS_MANUAL.md`** - MCP tools reference
- **`docs/manuals/TESTING_MANUAL.md`** - Testing strategies and guides
- **`docs/devlog/`** - Development logs and completion reports
- **`docs/sessions/`** - Agent session memories

### Migration Guides

- **`docs/MIGRATION_GUIDE_V3.md`** - v2.x to v3.0 upgrade guide (if exists)
- **`docs/VERIFICATION_OCT9.md`** - v3.0 architecture verification

### API Documentation

- **Interactive docs**: `http://localhost:7272/docs` (Swagger UI)
- **ReDoc**: `http://localhost:7272/redoc`
- **OpenAPI spec**: `http://localhost:7272/openapi.json`

---

## Quick Start

**Fresh Installation**:
```bash
# 1. Clone repository
git clone https://github.com/patrik-giljoai/GiljoAI-MCP.git
cd GiljoAI_MCP

# 2. Install dependencies
pip install -r requirements.txt

# 3. Run installer
python install.py

# 4. Access application
# Browser opens to http://localhost:7274
# Change default password (admin/admin)
# Complete setup wizard
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

- **Issues**: https://github.com/patrik-giljoai/GiljoAI-MCP/issues
- **Documentation**: `docs/README_FIRST.md` (this file)
- **License**: See LICENSE file
- **Contributing**: See CONTRIBUTING.md

---

**Last Updated**: October 11, 2025 (v3.0.0)
