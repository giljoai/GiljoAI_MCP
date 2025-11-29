# README FIRST - GiljoAI MCP Architecture Overview

> **Central navigation hub for understanding GiljoAI MCP v3.0 architecture, fresh installation flow, security model, and system design.**

## 📋 Core Documentation (October 2025)

**New single-truth documents** - Start here for comprehensive understanding:

- **[System Purpose & Capabilities](GILJOAI_MCP_PURPOSE.md)** - What GiljoAI MCP does, key features, and value proposition
- **[Multi-Tenant Architecture](USER_STRUCTURES_TENANTS.md)** - User management, tenant isolation, and database design
- **[Server Architecture & Tech Stack](SERVER_ARCHITECTURE_TECH_STACK.md)** - v3.0 unified architecture, ASCII diagrams, tech stack
- **[Installation Flow & Process](INSTALLATION_FLOW_PROCESS.md)** - Complete installation walkthrough and cross-platform setup
- **[First Launch Experience](FIRST_LAUNCH_EXPERIENCE.md)** - Step-by-step onboarding from install to dashboard
- **[MCP-over-HTTP Integration](MCP_OVER_HTTP_INTEGRATION.md)** - Connecting Claude Code via HTTP transport (zero dependencies)

### 📌 Single Source of Truth (SSoT) Documents

**Authoritative references for critical workflows** - These documents are maintained as the definitive source for their topics:

- **[SSoT Index](SSoT_INDEX.md)** - Master index of all SSoT documents
- **[Orchestrator Context Flow SSoT](ORCHESTRATOR_CONTEXT_FLOW_SSoT.md)** - Complete orchestrator workflow from user setup to agent execution (13 context cards, 77% context prioritization, 9 context sources)

**New Implementation Features** (October 2025):

- **[AI Tool Configuration Management](AI_TOOL_CONFIGURATION_MANAGEMENT.md)** - Multi-AI tool support via user settings (Claude, CODEX, Gemini)
- **[Template System Evolution](TEMPLATE_SYSTEM_EVOLUTION.md)** - Database-backed templates with AI tool preferences

**Recent Production Features** (See [Recent Handovers](#recent-production-handovers-v30) for details):

- **Agent Monitoring & Graceful Cancellation (Handover 0107)** - Contextual check-ins, passive health monitoring, graceful cancellation
- **Project Soft Delete with Recovery (Handover 0070)** - 10-day recovery window with UI in Settings → Database
- Single Active Product Architecture (Handover 0050) - One active product per tenant with database enforcement. **Extension (0050b)**: Projects also follow single-active pattern - one active project per product with cascade deactivation. See features/project_state_management.md and SERVER_ARCHITECTURE_TECH_STACK.md for details.
- Context Priority Management (Handover 0052) - User-customizable token budgets per field
- Multi-Tool Agent Orchestration (Handover 0045) - 40-60% cost optimization via tool mixing
- Products View Unified Management (Handover 0046) - Complete product lifecycle management
- Product Rich Context Fields (Handover 0042) - 13+ fields for maximum agent context
- Agent Template Database Integration (Handover 0041) - Customizable agent behavior with three-layer caching
- Unified Cross-Platform Installer (Handover 0035) - Windows, Linux, macOS support
- Admin Settings v3.0 Overhaul (Handovers 0025-0029) - Modern, cohesive interface
- 70% Token Reduction via Orchestrator Enhancement (Handover 0020) - Breakthrough efficiency
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
9. [Recent Production Handovers (v3.0+)](#recent-production-handovers-v30)
10. [Testing & Validation Documentation](#testing--validation-documentation)
11. [Additional Documentation](#additional-documentation)

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
   - **MCP-over-HTTP** endpoint for zero-dependency Claude Code integration

### v3.0 Unified Architecture Principles

**ONE Authentication Flow**:
- NO localhost auto-login
- Same authentication for localhost, LAN, WAN
- Fresh install detection: User count = 0
- Admin account: Created via /welcome → /first-login flow
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

## Platform Support

**Unified Cross-Platform Installer** (v3.1.0+ - Handover 0035):

**Status**: ✅ Production ready (October 2025) - See [Handover 0035](#unified-cross-platform-installer-october-2025)

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

**Complete Documentation**: [Handover 0035 - Unified Cross-Platform Installer](../handovers/completed/0035_HANDOVER_20251019_UNIFIED_CROSS_PLATFORM_INSTALLER-C.md)

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
- Starts API server on port 7272 (binds to 0.0.0.0)
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

**AI Tool Configuration** (Avatar → My Settings → API and Integrations):
- **AI Tool MCP Configurator**: One-click setup for Claude Code, CODEX, Gemini
- **Manual AI Tool Configuration**: Custom setup for any AI tool
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
- Task management (`task.py`)
- Context management (`context.py`, `chunking.py`, `context_manager.py`)
- Template management (`template.py`)

**Total**: 22+ tools for agent coordination

### API Layer

**File**: `api/app.py`

**Endpoints**:
- `/auth/*` - Authentication (login, password change)
- `/users/*` - User settings and AI tool configuration
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

### User Guides

- **[Orchestrator Succession Guide](user_guides/orchestrator_succession_guide.md)** - End-user guide for orchestrator succession (Handover 0080)

### Developer Guides

- **[Orchestrator Succession Developer Guide](developer_guides/orchestrator_succession_developer_guide.md)** - Technical implementation details for orchestrator succession (Handover 0080)

### Quick Reference

- **[Orchestrator Succession Quick Reference](quick_reference/succession_quick_ref.md)** - One-page cheat sheet for succession features

### UI/UX Technical Documentation (October 2025)

**Handover 0009 - Advanced UI/UX Verification** (✅ COMPLETE - HARMONIZED - 90% Implementation):
- **[UI/UX Implementation Status Summary](UI_UX_IMPLEMENTATION_STATUS_SUMMARY.md)** - Executive summary and roadmap
- **[Vue Component Brand Consistency Audit](VUE_COMPONENT_BRAND_CONSISTENCY_AUDIT.md)** (15 pages)
- **[Vuetify Theme Configuration Verification](VUETIFY_THEME_CONFIGURATION_VERIFICATION.md)** (26 pages)
- **[Asset Integration Testing Report](ASSET_INTEGRATION_TESTING.md)** (18 pages)
- **[WCAG 2.1 AA Accessibility Verification](WCAG_2.1_AA_ACCESSIBILITY_VERIFICATION.md)** (22 pages)

**Key Findings**:
- Production-ready UI/UX with 85/100 accessibility score (92/100 after 45-min fixes)
- Comprehensive asset integration (80+ icons, 4 mascot states)
- Minor brand color consistency fixes needed (#FFC300 → #FFD93D)

### Serena MCP Optimization Layer (October 2025)

**Handover 0010 - Serena MCP Optimization Implementation** (✅ COMPLETE - HARMONIZED):
- **Serena Context Analytics**: context-usage analytics and optimization signals powered by symbolic operations
- **Production Ready**: 37 passing unit tests, full database integration
- **Core Components**:
  - `src/giljo_mcp/optimization/serena_optimizer.py` - Optimization engine
  - `src/giljo_mcp/optimization/tool_interceptor.py` - MCP tool optimization
  - `src/giljo_mcp/tools/optimization.py` - 6 control tools
- **Features**:
  - Automatic symbolic operation enforcement (find_symbol vs read_file)
  - Mission-time optimization rule injection
  - Real-time token usage tracking and savings analytics
  - Intelligent context-based handoff triggers

**Integration**: Automatically active in ProjectOrchestrator for all agent spawns

### User API Key Management (October 2025)

**Handover 0015 - User API Key Management** (✅ COMPLETE - HARMONIZED):
- **Frontend Components**:
  - `ApiKeyManager.vue` (266 lines) - Full-featured key management UI
  - `ApiKeyWizard.vue` - Key generation modal
  - Integrated into UserSettings → API and Integrations tab
- **AI Tools Integration**:
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

## Recent Production Handovers (v3.0+)

### Agent Job Management System (October 2025)

**Handover 0019 - Agent Job Management System** (✅ COMPLETE):
- **[Complete Documentation](../handovers/completed/0019_HANDOVER_20251014_AGENT_JOB_MANAGEMENT-C.md)**
- **Purpose**: Implement agent job tracking separate from user tasks, enabling true multi-agent coordination
- **Key Features**:
  - Agent-to-agent messaging with acknowledgments
  - Job lifecycle tracking (pending → active → completed)
  - Message queue with JSONB storage
  - Coordination between multiple agents
- **Core Components**:
  - `AgentJobManager` - Job creation and status tracking
  - Message acknowledgment system
  - Job coordination engine
- **Impact**: Foundation for intelligent multi-agent workflows

### Orchestrator Enhancement - 70% Token Reduction (October 2025)

**Handover 0020 - Orchestrator Enhancement for Intelligent Coordination** (✅ COMPLETE):
- **[Complete Documentation](../handovers/completed/0020_HANDOVER_20251014_ORCHESTRATOR_ENHANCEMENT-C.md)**
- **[Completion Summary](../handovers/completed/0020_COMPLETION_SUMMARY-C.md)**
- **Purpose**: Enhance orchestrator to become the intelligent brain for mission generation and agent coordination
- **Key Achievements**:
  - Context prioritization and orchestration for terminal-based coding agents through intelligent context management
  - Automated mission generation from vision documents
  - Smart agent selection logic
  - Multi-agent workflow coordination
  - Progress monitoring and failure handling
- **Core Components**:
  - `EnhancedOrchestrator` - Context summarization and mission creation
  - `MissionGenerator` - Automated mission planning
  - `AgentSelector` - Intelligent agent type selection
  - `WorkflowCoordinator` - Multi-agent coordination
- **Impact**: Breakthrough efficiency enabling complex projects within token limits

### Orchestrator Succession Architecture (November 2025)

**Handover 0080 - Orchestrator Succession for Unlimited Project Duration** (✅ COMPLETE):
- **[Complete Documentation](../handovers/0080_orchestrator_succession_architecture.md)**
- **[User Guide](user_guides/orchestrator_succession_guide.md)** | **[Developer Guide](developer_guides/orchestrator_succession_developer_guide.md)** | **[Quick Reference](quick_reference/succession_quick_ref.md)**
- **Purpose**: Enable unlimited project duration through automatic orchestrator succession when context windows approach capacity
- **Key Features**:
  - Automatic succession at 90% context usage
  - Compressed handover summaries (<10K tokens)
  - Full lineage tracking via spawned_by chain
  - UI timeline visualization
  - Manual launch control for successors
- **Core Components**:
  - `OrchestratorSuccessionManager` - Succession lifecycle management
  - MCP Tools: `create_successor_orchestrator()`, `check_succession_status()`
  - Database schema: 7 new columns (instance_number, handover_to, handover_summary, etc.)
  - Vue Components: SuccessionTimeline, LaunchSuccessorDialog, AgentCardEnhanced
- **Testing**: 45 integration tests (80.5% coverage), multi-tenant isolation verified, performance benchmarks validated
- **Impact**: Projects can continue indefinitely without context limitations, context prioritization and orchestration, graceful context management

### Password Reset via Recovery PIN (October 2025)

**Handover 0023 - Password Reset Functionality** (✅ COMPLETE - PRODUCTION READY):
- **[Complete Documentation](../handovers/completed/0023_HANDOVER_20251015_PASSWORD_RESET_FUNCTIONALITY-C.md)**
- **Implementation Date**: October 21, 2025
- **Status**: All 6/6 integration tests passing, WCAG 2.1 AA compliant
- **Key Features**:
  - Recovery PIN generation (4-digit secure PIN)
  - Self-service password reset flow
  - Rate limiting (5 failed attempts = 15-minute lockout)
  - Timing-safe PIN comparisons
  - Comprehensive audit logging
- **Backend Components**:
  - 3 new API endpoints (`/generate-pin`, `/validate-pin`, `/reset-password`)
  - User model updates (recovery_pin_hash, recovery_pin_generated_at)
  - bcrypt PIN hashing (same security as passwords)
- **Frontend Components**:
  - `ForgotPasswordPin.vue` - PIN generation interface
  - `ResetPasswordPin.vue` - Password reset with PIN validation
  - Updated Login.vue with "Forgot Password" link
- **Security Measures**:
  - Generic error messages (prevents user enumeration)
  - PIN expiration (24 hours)
  - Rate limiting per user
  - Full audit trail
- **Impact**: Self-service account recovery without admin intervention

### Admin Settings v3.0 Refactoring (October 2025)

**Handovers 0025-0029 - Complete Admin Settings Overhaul** (✅ COMPLETE):

**Handover 0025 - Network Settings Refactor**:
- **[Documentation](../handovers/completed/0025_HANDOVER_20251016_ADMIN_SETTINGS_NETWORK_REFACTOR.md)**
- **[Completion Report](../handovers/completed/0025_COMPLETION_REPORT.md)**
- Removed deployment mode references (v3.0 unified architecture)
- Display 0.0.0.0 binding with OS firewall control
- Enhanced CORS configuration UI
- 44 tests passing (100% coverage)

**Handover 0026 - Database Tab Redesign**:
- **[Documentation](../handovers/completed/0026_HANDOVER_20251016_ADMIN_SETTINGS_DATABASE_TAB_REDESIGN.md)**
- Fresh Material Design 3 interface
- Real-time PostgreSQL connection status
- Connection pool metrics and health monitoring
- Tenant key management UI

**Handover 0027 - Integrations Tab Redesign**:
- **[Documentation](../handovers/completed/0027_HANDOVER_20251016_INTEGRATIONS_TAB_REDESIGN-C.md)**
- MCP-over-HTTP configuration management
- Serena MCP integration controls
- GitHub integration settings
- Clean, modern UI with copy-to-clipboard functionality

**Handover 0028 - User Settings Panel Consolidation**:
- **[Documentation](../handovers/completed/0028_HANDOVER_20251016_USER_PANEL_CONSOLIDATION.md)**
- Unified user settings architecture
- Consistent navigation pattern
- Improved user experience

**Handover 0029 - Users Management Relocation**:
- **[Documentation](../handovers/completed/0029_HANDOVER_20251016_USERS_TAB_RELOCATION.md)**
- Moved Users tab from Admin Settings to Avatar Dropdown
- Standalone Users management page
- Improved information architecture
- Cleaner admin settings interface

**Combined Impact**: Modern, cohesive admin interface aligned with v3.0 architecture principles

### Unified Cross-Platform Installer (October 2025)

**Handover 0035 - Unified Cross-Platform Installer Architecture** (✅ COMPLETE):
- **[Complete Documentation](../handovers/completed/0035_HANDOVER_20251019_UNIFIED_CROSS_PLATFORM_INSTALLER-C.md)**
- **Completion Date**: October 19, 2025
- **Status**: Production ready, all platforms fully tested
- **Problem Solved**: Eliminated 2,500 lines of duplicated code across separate Windows/Linux installers
- **Key Achievements**:
  - Single unified installer for Windows, Linux, and macOS
  - Strategy pattern with platform handlers (`installer/platforms/`)
  - Auto-detection of OS and appropriate handler selection
  - Consistent pg_trgm extension creation across all platforms
  - Fixed critical Linux installer bugs (missing pg_trgm, misleading messages)
- **Platform Support**:
  - Windows 10/11 - Desktop shortcuts, Program Files detection
  - Linux (Ubuntu 22.04+, Fedora 40+, Debian 12+) - Desktop launchers, distribution-specific guides
  - macOS (13+, Intel and ARM) - Homebrew support, Postgres.app detection
- **Architecture**:
  - `installer/platforms/base.py` - Abstract PlatformHandler interface
  - `installer/platforms/windows.py` - Windows-specific operations
  - `installer/platforms/linux.py` - Linux-specific operations
  - `installer/platforms/macos.py` - macOS-specific operations
  - `installer/core/` - Unified platform-agnostic modules
- **Impact**: Single codebase, consistent behavior, easier maintenance, platform-specific features where needed

### Agent Template Database Integration (October 2025)

**Handover 0041 - Agent Template Management System** (✅ COMPLETE):
- **[Complete Documentation](../docs/handovers/0041/)** - 6 comprehensive guides
- **Completion Date**: October 24, 2025
- **Status**: Production ready with minor fixes
- **Problem Solved**: Hard-coded agent templates prevented per-tenant customization and flexible behavior tuning
- **Key Achievements**:
  - Database-backed template storage with three-layer caching (Memory → Redis → Database)
  - 6 default templates per tenant with automatic seeding during installation
  - Monaco editor integration for rich template editing experience
  - Template versioning and full audit trail with rollback capability
  - 95%+ cache hit rate achieving <1ms memory cache response times
  - 13 REST API endpoints for comprehensive template management
  - Real-time template updates via WebSocket events
- **Performance Metrics**:
  - Memory cache hit: <1ms (p95) ✅
  - Database query: <10ms (p95) ✅
  - Template seeding: <2s for 6 templates ✅
  - 75% test coverage across 78 tests ✅
- **Core Components**:
  - `src/giljo_mcp/template_seeder.py` - Idempotent template seeding (263 lines)
  - `src/giljo_mcp/template_cache.py` - Three-layer cache implementation (349 lines)
  - `api/endpoints/templates.py` - 13 REST endpoints (1096 lines)
  - `frontend/src/components/TemplateManager.vue` - Rich UI with Monaco editor
- **Multi-Tenant Security**:
  - Zero cross-tenant leakage across 100+ test iterations
  - JWT authentication required on all endpoints
  - Tenant-scoped cache keys and database queries
  - System templates read-only protection
- **Impact**: Enables per-tenant agent behavior customization, foundation for template marketplace, intelligent template selection

### Product Rich Context Fields UI (October 2025)

**Handover 0042 - Product Rich Context Fields UI** (✅ COMPLETE):
- **[Implementation](../handovers/completed/0042_COMPLETION_SUMMARY.md)**
- **Completion Date**: October 2025
- **Status**: Production ready
- **Problem Solved**: Limited product context prevented agents from understanding full project scope and technical requirements
- **Key Features**:
  - 5-tab product form (Basic Info, Tech Stack, Architecture, Features, Test Configuration)
  - Vision type selector (file upload / inline text / none)
  - 13+ configuration fields for rich agent context
  - Free-text format for maximum flexibility
  - JSONB config_data schema for extensibility
- **Core Components**:
  - Frontend: `frontend/src/views/Products.vue` (enhanced form with tabs)
  - Backend: `api/models/product.py` (config_data JSONB schema)
- **Impact**: Agents receive complete project context including tech stack, architecture patterns, feature requirements, and testing preferences

### Multi-Vision Document Support (October 2025)

**Handover 0043 - Multi-Vision Document Support** (❌ RETIRED - DESIGN ONLY):
- **Status**: Design document only, no implementation
- **Rationale**: Feature proposal for multiple vision documents per product. Retired in favor of simpler single-vision approach with rich context fields (Handover 0042)
- **Archive**: Preserved as reference for potential future implementation

### Agent Template Export System (October 2025)

**Handover 0044 - Agent Template Export System** (✅ COMPLETE):
- **[Implementation](../handovers/completed/0044_HANDOVER_AGENT_TEMPLATE_EXPORT_SYSTEM-C.md)**
- **Completion Date**: October 2025
- **Status**: Production ready
- **Problem Solved**: Manual template file management for Claude Code integration
- **Key Features**:
  - Export agent templates to `.claude/agents/` directory
  - Seamless Claude Code workflow integration
  - Integrated with template management system (Handover 0041)
- **Core Components**:
  - Backend: `src/giljo_mcp/template_manager.py` (export functionality)
  - API: Template management endpoints (export operations)
- **Impact**: One-click export of customized agent templates for external AI tool usage

### Multi-Tool Agent Orchestration (October 2025)

**Handover 0045 - Multi-Tool Agent Orchestration** (✅ COMPLETE):
- **[Implementation](../handovers/completed/0045_COMPLETION_SUMMARY.md)**
- **[Migration Guide](../MIGRATION_GUIDE_V3_TO_V3.1.md)**
- **[Reference Documentation](../references/0045/)** - 8 comprehensive guides
- **Completion Date**: October 2025
- **Status**: Production ready with comprehensive documentation
- **Problem Solved**: Single-tool limitation prevented cost optimization through strategic AI tool mixing
- **Key Achievements**:
  - Template-based routing system (agent_config.json specifies preferred tools)
  - 7 new MCP coordination tools for agent lifecycle management
  - Agent-Job linking for backward compatibility with legacy modes
  - 40-60% cost optimization through intelligent tool mixing
  - Seamless multi-tool coordination within single missions
- **Core Components**:
  - Core: `src/giljo_mcp/multi_tool_manager.py` (routing engine, 450+ lines)
  - MCP Tools: `src/giljo_mcp/tools/agent_*.py` (7 coordination tools)
  - API: `api/endpoints/agents.py` (agent-job linking endpoints)
- **7 MCP Coordination Tools**:
  - `agent_create` - Spawn agents with tool preferences
  - `agent_assign_job` - Link agents to jobs
  - `agent_get_status` - Query agent state
  - `agent_send_message` - Inter-agent messaging
  - `agent_complete_job` - Mark jobs complete
  - `agent_fail_job` - Handle failures
  - `agent_list_jobs` - Query job status
- **Documentation**:
  - [Developer Guide](../references/0045/DEVELOPER_GUIDE.md) - Implementation details
  - [User Guide](../references/0045/USER_GUIDE.md) - Configuration and usage
  - [API Reference](../references/0045/API_REFERENCE.md) - 7 MCP tools documented
  - [Migration Guide](../MIGRATION_GUIDE_V3_TO_V3.1.md) - Upgrade instructions
- **Impact**: Foundation for cost-optimized multi-AI orchestration, enabling strategic tool selection per mission phase

### Products View Unified Management (October 2025)

**Handover 0046 - Products View Unified Management** (✅ COMPLETE):
- **[Implementation](../handovers/completed/0046_HANDOVER_PRODUCTS_VIEW_UNIFIED_MANAGEMENT-C.md)**
- **[Testing Documentation](../testing/HANDOVER_0046_INDEX.md)** - 7 comprehensive test documents
- **Completion Date**: October 2025
- **Status**: Production ready with comprehensive testing
- **Problem Solved**: Fragmented product management across multiple views, inconsistent vision document handling
- **Key Features**:
  - Vision document upload in create/edit dialogs
  - Product cards with metrics display (missions count, agents count, token usage)
  - Activate/deactivate functionality with visual state indicators
  - Delete with cascade impact display (warns about affected missions/agents)
  - Product-as-context architecture foundation
- **Core Components**:
  - Frontend: `frontend/src/views/Products.vue` (unified interface)
  - API: `api/endpoints/products.py` (vision upload endpoints)
- **Testing Highlights**:
  - [Validation Report](../testing/HANDOVER_0046_VALIDATION_REPORT.md) - 9 issues identified and documented
  - [Accessibility Audit](../testing/HANDOVER_0046_ACCESSIBILITY_AUDIT.md) - WCAG 2.1 AA compliance
  - 7 comprehensive test documents covering UI, UX, and accessibility
- **Impact**: Single source of truth for product management, streamlined vision document workflow

### Vision Document Chunking Async Fix (October 2025)

**Handover 0047 - Vision Document Chunking Async Fix** (✅ COMPLETE):
- **[Implementation](../handovers/completed/0047_HANDOVER_VISION_DOCUMENT_CHUNKING_ASYNC_FIX-C.md)**
- **[Testing Documentation](../testing/HANDOVER_0047_TEST_FIX_REPORT.md)**
- **Completion Date**: October 2025
- **Status**: Production ready with bug fixes
- **Problem Solved**: Blocking synchronous chunking caused UI freezes, product deletion bugs
- **Key Features**:
  - EnhancedChunker with 25K token chunks (optimized for Sonnet 4.5)
  - Async chunking implementation prevents UI blocking
  - Product deletion cascade fixes
  - Vision document processing optimization
- **Core Components**:
  - Core: `src/giljo_mcp/vision_chunker.py` (EnhancedChunker implementation)
  - API: `api/endpoints/products.py` (async integration, deletion fixes)
- **Testing Highlights**:
  - [Bug Report](../testing/HANDOVER_0047_BUG_REPORT.md) - Product deletion bug analysis and resolution
  - [Test Fix Report](../testing/HANDOVER_0047_TEST_FIX_REPORT.md) - Test suite updates
- **Impact**: Responsive UI during vision document processing, reliable product lifecycle management

### Product Field Priority Configuration (October 2025)

**Handover 0048 - Product Field Priority Configuration** (✅ COMPLETE):
- **[Implementation](../handovers/completed/0048_HANDOVER_PRODUCT_FIELD_PRIORITY_CONFIGURATION-C.md)**
- **Completion Date**: October 2025
- **Status**: Production ready
- **Problem Solved**: Fixed token budgets prevented users from controlling context trade-offs per mission
- **Key Features**:
  - 3-tier priority system (P1/P2/P3) for product context fields
  - Drag-drop UI in User Settings for intuitive configuration
  - Token budget enforcement per priority tier
  - User-customizable priorities per field (tech_stack, features, architecture, etc.)
  - Default priority configuration for new users
- **Core Components**:
  - Frontend: `frontend/src/components/UserSettings.vue` (priority configuration UI)
  - Backend: `src/giljo_mcp/models.py` (field_priority_config JSONB column)
  - API: `api/endpoints/users.py` (3 endpoints: get, update, reset)
- **Priority Tiers**:
  - P1 (Critical): Always included, high token budget
  - P2 (Standard): Included when budget allows
  - P3 (Optional): Included only if excess budget available
- **Documentation**: Field priority schema documented in `SERVER_ARCHITECTURE_TECH_STACK.md`
- **Impact**: Users control context inclusion per mission type, optimized token usage based on task requirements

### Active Product Token Visualization (October 2025)

**Handover 0049 - Active Product Token Visualization** (✅ COMPLETE):
- **[Implementation](../handovers/completed/harmonized/0049_IMPLEMENTATION_SUMMARY.md)**
- **Completion Date**: October 2025
- **Status**: Foundation complete
- **Problem Solved**: No visibility into active product context or token consumption
- **Key Features**:
  - Active product display in dashboard header (click to open Products)
  - Real-time token estimator in User Settings tied to the active product
  - Priority badges surfaced alongside Product fields (indicate P1/P2/P3 impact)
  - ActiveProductDisplay component integration (WebSocket-updated)
  - New Products API for real token estimate: `GET /api/v1/products/active/token-estimate`
    - Response includes `product_name`, per-field token counts, `total_tokens`, and `token_budget`
    - Updates when field priorities change, the active product changes, or product config updates
  - Default estimator budget raised to 2000 tokens (configurable via field priority config)

See also:
- Context API “Get Token Statistics” for chunk-level metrics
- Products API “Active Product Token Estimate” for priority-aware, real-time estimates
- **Core Components**:
  - Frontend: `frontend/src/components/ActiveProductDisplay.vue`
- **Impact**: Foundation for real-time context budget monitoring and active product awareness

### Single Active Product Architecture (October 2025)

**Handover 0050 - Single Active Product Architecture** (✅ COMPLETE):
- **[Implementation Summary](../handovers/0050_IMPLEMENTATION_SUMMARY.md)** - Complete implementation details
- **[Implementation Status](../handovers/0050_IMPLEMENTATION_STATUS.md)** - Phase-by-phase breakdown
- **Completion Date**: October 27, 2025
- **Status**: Production ready with database migration
- **Problem Solved**: Multiple active products per tenant caused context confusion and invalid orchestration states
- **Key Features**:
  - Database-enforced single active product per tenant (partial unique index)
  - Warning dialog before product switch (user confirmation flow)
  - Auto-activation on deletion (oldest product becomes active)
  - Project validation (parent product must be active)
  - Agent job validation (product must be active)
  - Orchestrator validation (mission assignment requires active product)
- **Core Components**:
  - Database: `migrations/versions/20251027_enforce_single_active_product.py` (migration with auto-repair)
  - Backend: `api/endpoints/products.py` (enhanced endpoints with rich context)
  - Frontend: `frontend/src/components/products/ActivationWarningDialog.vue` (warning dialog)
  - Validation: Enhanced project, agent job, and orchestrator validation
- **Architecture**:
  - Defense-in-depth enforcement (database, API, frontend, business logic)
  - Atomic database operations (no race conditions)
  - Clear error messages with resolution hints
  - Migration includes auto-repair for existing conflicts
- **Migration Required**: Database migration with auto-repair logic
- **Impact**: Clear product lifecycle semantics, prevents context confusion, foundation for product-scoped workflows

---

### Context Priority Unassigned Category (October 2025)

**Handover 0052 - Context Priority Management** (✅ COMPLETE):
- **[Implementation](../handovers/completed/0052_COMPLETION_SUMMARY.md)**
- **[Testing Documentation](../testing/HANDOVER_0052_README.md)** - 6 comprehensive test documents
- **Completion Date**: October 2025
- **Status**: Production ready with 100% deployment readiness
- **Problem Solved**: Critical bugs in field priority system and missing token refresh functionality
- **Key Achievements**:
  - Fixed resetGeneralSettings() bug (proper defaults restoration)
  - Token estimator connected to active product context
  - Automatic token refresh after save/reset operations
  - Unassigned category handling for uncategorized fields
  - Integration testing with active product token system
- **Core Components**:
  - Frontend: `frontend/src/components/UserSettings.vue` (bug fixes and token integration)
  - API: `api/endpoints/users.py` (reset defaults endpoint)
- **Testing Highlights**:
  - [Test Results](../testing/HANDOVER_0052_TEST_RESULTS.md) - 32 detailed test cases (100% pass rate)
  - [Executive Report](../testing/HANDOVER_0052_EXECUTIVE_REPORT.md) - Deployment readiness summary
  - 6 comprehensive test documents (1200+ lines of validation)
  - 32 test cases covering UI, API, integration, edge cases
- **Impact**: Production-grade field priority system with complete token budget integration and validation

---

### Projects View v2 Redesign (October 2025)

**Handover 0053 - ProjectsView v2.0 Complete Redesign** (✅ PRODUCTION-READY):
- **[Overview](features/projects_view_v2.md)**
- **Completion Date**: October 2025
- **Status**: Production-ready
- **Problem Solved**: Outdated projects UI lacking search, filters, and accessible status management
- **Key Features**:
  - Real-time search (name, mission, ID)
  - Status tabs with counts; multi-column sorting
  - Interactive StatusBadge: Activate, Deactivate, Complete, Cancel, Restore, Delete
  - Deleted projects modal with restore
  - Product isolation and multi-tenant safety
  - WCAG 2.1 AA accessibility and keyboard navigation
- **Interplay**:
  - Honors Single Active constraints (0050b)
  - Aligns with state simplification (0071) — Deactivate replaces Pause
  - Integrates with soft delete + recovery (0070)

### Task Management Integration Map (October 2025)

**Handover 0072 - Task Management Integration Map** (✅ COMPLETE):
- Links user tasks to MCP agent jobs for grounded assignments
- Clarifies task data model and product/project scoping
- Establishes conventions for task-to-job references and status propagation
- Developer impact: APIs and models reflect explicit linkage (no ad‑hoc joins)

### Static Agent Grid with Enhanced Messaging (October 2025)

**Handover 0073 - Static Agent Grid (Canonical)** (✅ COMPLETE):
- **[Overview](features/agent_grid_static_0073.md)**
- **Completion Date**: October 2025
- **Status**: Canonical orchestration UI
- **Problem Solved**: Replaces the two-tab Launch/Jobs pattern and Kanban concepts with a stable, low-latency grid optimized for multi-terminal workflows
- **Key Features**:
  - Fixed grid of agent roles with live status and counters
  - Enhanced messaging area with event-driven updates
  - WebSocket DI and standardized EventFactory schemas
  - Multi-tenant filtering and project-scoped broadcasts
- **Supersession**:
  - Supersedes 0062 (Active Jobs tab) and 0066 (Kanban dashboard)
  - See handovers/completed/harmonized/0073_SUPERSEDES_0062_0066-C.md for ADR context

### Orchestrator Succession (October 2025)

**Handovers 0080/0080a - Succession Architecture + Slash Command** (✅ COMPLETE):
- **Dev Guide**: developer_guides/orchestrator_succession_developer_guide.md
- **Slash Command**: `/gil_handover [<job_id>]` — creates successor orchestrator and returns launch prompt
- **Events**: `job:succession_triggered`, `job:successor_created` (UI updates grid and dialog)
- **Use Cases**: Context approaching budget, phase transitions, long-running missions

### Hybrid Launch Route Architecture (October 2025)

**Handover 0081 - Hybrid Launch Route Architecture** (✅ COMPLETE):
- Clarifies routing and separation of concerns between staging, orchestration, and agent job APIs
- Improves consistency of launch flows across UI and CLI
- Developer impact: cleaner FastAPI router layout and predictable request/response schemas

### Installation Experience Validation (October 2025)

**Handover 0014 - Installation Experience Validation** (✅ COMPLETE - ARCHIVED):
- **[Installation Validation Summary](INSTALLATION_VALIDATION_SUMMARY.md)** - Comprehensive validation report
- **[Marketing Claims Recommendations](MARKETING_CLAIMS_RECOMMENDATIONS.md)** - Updated messaging guidance
- **[Installation Test Report](test_reports/INSTALLATION_TEST_REPORT_HANDOVER_0014.md)** - Detailed testing results

**Key Findings**:
- Installation system architecturally sound (8.2/10 weighted score)
- Production ready with minor UX improvements recommended (30 min fixes)
- Timing: 6-10 minutes typical (vs. claimed "5 minutes")
- Cross-platform excellence (100% pathlib usage verified)
- Security-first design validated (forced password change, bcrypt)

**Recommendations**:
- Update marketing claims to "6-10 minute guided installation"
- Implement Priority 1 friction point fixes (30 minutes total)
- Launch approval granted with 95% readiness score

### Migration Guides

- **`docs/MIGRATION_GUIDE_V3.md`** - v2.x to v3.0 upgrade guide (if exists)
- **`docs/VERIFICATION_OCT9.md`** - v3.0 architecture verification

### API Documentation

- **Interactive docs**: `http://localhost:7272/docs` (Swagger UI)
- **ReDoc**: `http://localhost:7272/redoc`
- **OpenAPI spec**: `http://localhost:7272/openapi.json`
- **Prompts API**: See `docs/api/prompts_endpoints.md` (Thin Client endpoint)

---

## Testing & Validation Documentation

### Testing Infrastructure

- **[Testing Guide](TESTING_GUIDE.md)** - Comprehensive testing strategies (unit, integration, frontend)
- **[Testing Reports](/docs/testing/)** - Per-handover validation and QA reports

### Handover Validation Reports

All testing artifacts organized by handover number in `/docs/testing/`:

#### Handover 0046: Products View Unified Management

Frontend UI validation, accessibility audit, UX testing

- [Validation Report](testing/HANDOVER_0046_VALIDATION_REPORT.md) - 9 issues identified
- [Accessibility Audit](testing/HANDOVER_0046_ACCESSIBILITY_AUDIT.md) - WCAG compliance
- [Full Test Suite](testing/HANDOVER_0046_INDEX.md) - 7 comprehensive documents

#### Handover 0047: Vision Document Chunking Async Fix

Backend fix validation, async testing, bug resolution

- [Test Fix Report](testing/HANDOVER_0047_TEST_FIX_REPORT.md) - Test suite fixes
- [Bug Report](testing/HANDOVER_0047_BUG_REPORT.md) - Product deletion bug analysis

#### Handover 0052: Context Priority Management

Integration testing, token budget validation, user settings

- [Test Results](testing/HANDOVER_0052_TEST_RESULTS.md) - 32 detailed test cases
- [Executive Report](testing/HANDOVER_0052_EXECUTIVE_REPORT.md) - Deployment readiness
- [Full Test Suite](testing/HANDOVER_0052_README.md) - 6 comprehensive documents

### System-Wide Testing

- **[Installation Validation](INSTALLATION_VALIDATION_SUMMARY.md)** - Install testing (19KB)
- **[WCAG 2.1 AA Audit](WCAG_2_1_AA_ACCESSIBILITY_AUDIT.md)** - System-wide accessibility
- **[Backup Tests](testing/BACKUP_TEST_SUMMARY.md)** - Database backup utility

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
# First Login
# Configure AI tools via Avatar → My Settings → API & Integrations
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

---

## 📚 Documentation Harmonization (October 13, 2025)

As of October 13, 2025, GiljoAI MCP documentation has been **harmonized** into single-truth documents to eliminate fragmentation and architectural conflicts. The five core documents listed above replace 70+ scattered documentation files.

**Legacy documentation** has been archived to `docs/archive/2025-10-13/` for reference.

---

**Last Updated**: October 27, 2025 (v3.0.0 - Handovers 0042-0052 & Testing Documentation Added)
- 0088 Thin Client Migration (Completed): Stage Project prompts now use thin identity prompts that fetch missions via MCP tools. See `guides/thin_client_migration_guide.md` and `STAGE_PROJECT_FEATURE.md`.
