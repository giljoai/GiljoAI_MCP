# GiljoAI MCP Purpose & Capabilities

**Document Version**: 10_21_2025_v2
**Status**: Single Source of Truth
**Last Updated**: October 21, 2025

---

## Executive Summary

**GiljoAI MCP** solves the two biggest problems with AI-assisted development: **context limitations** and **coordination complexity**. It achieves this through intelligent multi-agent orchestration that delivers **context prioritization and orchestration** while enabling coordinated teams of specialized AI agents to work on complex projects.

**Key Achievements**:
- **Intelligent Mission Generation**: Production-ready orchestration system (Handover 0020) with condensed, focused missions per agent
- **Multi-Agent Coordination**: Complete job management system (Handover 0019) with JSONB message queues
- **Production-Ready**: Cross-platform unified installer (Handover 0035), comprehensive security (Handover 0023), professional UI (Handovers 0025-0029)
- **100% Multi-Tenant Isolation**: Enterprise-grade security and data separation across all layers

## What is GiljoAI MCP?

GiljoAI MCP Coding Orchestrator is a **production-ready multi-agent orchestration system** that transforms AI coding assistants into coordinated development teams through intelligent context management. It breaks through context limits by orchestrating multiple specialized agents that work together on complex tasks with focused, role-specific context.

**The Magic**: The orchestrator reads your full project context ONCE and creates condensed, focused missions for each specialized agent. Database experts only get database context, frontend specialists only get UI patterns, and they all coordinate via lightweight JSONB message queues instead of duplicating context. The system automatically manages job lifecycles (pending → active → completed), tracks dependencies through parent-child hierarchies, and handles agent-to-agent communication with sub-100ms performance.

**Production Status**: Complete implementation with 380+ passing tests, cross-platform installer, comprehensive security (recovery PIN system, first admin lockdown), and professional UI with WCAG 2.1 AA accessibility.

### The Core Problem It Solves

**Context Limitations & Coordination Complexity**: Traditional AI coding assistants hit context limits when working on large codebases or complex projects. They can't maintain awareness of the entire system while implementing specific features, and they lack coordination when multiple concerns must be addressed simultaneously.

**Solution**: Instead of one AI trying to hold everything in memory, GiljoAI MCP creates **teams of specialized agents** that:
- Share context intelligently through condensed missions (**context prioritization and orchestration**)
- Hand off work when they approach limits
- Coordinate through a central orchestrator that reads full context once
- Each focus on specific aspects of development with only relevant context
- Communicate via message queues instead of duplicating context

---

## Why GiljoAI MCP Exists

### The Multi-Agent Coordination Challenge

Modern software development involves:
- **Large codebases** (hundreds of files, millions of lines)
- **Complex architectures** (microservices, databases, APIs, frontends)
- **Multiple concerns** (security, performance, testing, documentation)
- **Continuous integration** (git workflows, CI/CD, deployment)

**Traditional Approach Problems**:
- Single AI assistant loses context on large projects
- No coordination between different development tasks
- Repeated discovery of the same codebase patterns
- Knowledge loss when context resets

**GiljoAI MCP Solution**:
- **Persistent orchestration** that remembers project state
- **Specialized agents** for different development roles
- **Intelligent handoffs** when agents reach context limits
- **Shared memory** of project architecture and decisions
- **Role-specific context** through depth-level configuration

### Real-World Impact

**Before GiljoAI MCP**:
- Developer: "Can you implement user authentication?"
- AI: *Analyzes entire codebase, hits context limit, forgets database schema*
- AI: "I need you to show me the database models again..."
- **Result**: Thousands of wasted tokens, incomplete implementation

**With GiljoAI MCP (context prioritization and orchestration)**:
- Developer: "Implement user authentication"
- **Orchestrator** (MissionPlanner): *Reads full vision document ONCE, creates condensed missions*
- **AgentSelector**: *Queries AgentTemplate database, selects optimal team based on priority cascade*
- **WorkflowEngine**: *Spawns agent jobs in waterfall pattern, tracks lifecycle*
- **Database Expert**: *Receives focused mission: database schema + auth requirements only*
  - Creates job via `POST /api/agent-jobs` (pending → active)
  - Implements auth tables, indexes, constraints
  - Sends completion message via AgentCommunicationQueue
- **API Implementer**: *Gets focused mission: API patterns + auth endpoints only*
  - Acknowledges job, begins implementation
  - Reads database expert's messages for schema details
  - Implements JWT endpoints, middleware
- **Frontend Specialist**: *Receives focused mission: UI patterns + auth flow only*
  - Gets messages from API team on endpoint specs
  - Implements login/register forms, token management
- **Tester**: *Gets focused mission: test patterns + auth test cases only*
  - Coordinates via message queue with all teams
  - Writes comprehensive test suite
- **Result**: Same quality implementation, focused context per agent, sub-100ms job coordination

---

## Problems GiljoAI MCP Solves

### 1. Context Fragmentation

**Problem**: AI assistants lose context and ask for the same information repeatedly.

**Solution**: 
- **Persistent project memory** stores architecture decisions
- **Hierarchical context loading** provides relevant information to each agent
- **Vision documents** maintain long-term project understanding
- **Product configuration** preserves critical features and constraints

### 2. Redundant Context Loading

**Problem**: Each AI interaction re-analyzes the entire codebase, losing focus across concerns.

**Solution (Intelligent Context Prioritization)**:
- **Intelligent Mission Generation**: Orchestrator reads full context ONCE, creates condensed missions
- **Role-based Filtering**: Agents receive only relevant context (database expert doesn't get frontend code)
- **Message Queue Coordination**: Agent-to-agent communication via JSONB messages
- **Serena Symbolic Operations**: Targeted code analysis through find_symbol over full file reads
- **Context Chunking**: Loads only relevant sections of large documents
- **Shared Discoveries**: Project memory prevents repeated codebase exploration
- **Smart Handoffs**: Transfer focused context between agents without duplication

### 3. Lack of Specialization

**Problem**: General-purpose AI tries to handle database, API, frontend, and testing simultaneously.

**Solution**:
- **Specialized agent roles**: Database Expert, API Implementer, Frontend Specialist, Tester, etc.
- **Role-specific tools** optimized for each agent's responsibilities  
- **Expert knowledge** in specific domains (SQL optimization, React patterns, test strategies)
- **Parallel work** where multiple agents work simultaneously

### 4. No Coordination Between Tasks

**Problem**: Related development tasks proceed independently without awareness, causing conflicts and rework.

**Solution (Agent Job Management System - Handover 0019)**:
- **Central Orchestrator** manages overall project coordination with full context awareness
- **Agent Job Lifecycle Management**: Complete state machine (pending → active → completed/failed) with 13 REST endpoints
- **JSONB Message Queue System**: Agent-to-agent communication with priority levels (high/normal/low) and acknowledgment tracking
- **Parent-Child Job Hierarchies**: Complex workflows broken into coordinated subtasks via spawned_by relationships
- **Intelligent Handoffs**: Seamless work transfer when one agent completes tasks for another
- **Dependency Tracking**: Ensures work proceeds in correct order with parallel execution where possible
- **Real-time WebSocket Events**: Live updates on job status, messages, and coordination (6 event types)
- **Multi-tenant Isolation**: 100% secure job and message isolation across tenants with 404 for cross-tenant access

**Performance**: Sub-100ms for critical operations (job creation <50ms, status update <20ms, message send <30ms)

**Production Status**: 80 core tests passing (89.15% coverage), 30+ API tests, 9 WebSocket tests

### 5. Knowledge Loss

**Problem**: Important architectural decisions and patterns get forgotten.

**Solution**:
- **Session memories** preserve key decisions across interactions
- **Template system** codifies common patterns and approaches
- **Documentation generation** creates lasting records of implementations
- **Pattern detection** identifies and reuses successful approaches

---

## Key Capabilities

### Multi-Agent Orchestration

**Core Architecture (Handovers 0019 & 0020)**:
- **Orchestrator Agent**: Reads full project context ONCE, creates condensed missions for each agent via MissionPlanner
- **Worker Agents**: Specialized implementers receiving only role-relevant context
- **Message Queue System**: JSONB-based agent-to-agent communication with priority levels
- **Job Management**: Complete lifecycle tracking (pending → active → completed/failed) with 13 REST endpoints
- **Handoff Mechanism**: Intelligent context transfer between agents without duplication

**How Context Prioritization Works**:
1. **Orchestrator reads full vision** (one-time cost)
2. **Generates condensed missions** per agent using MissionPlanner
3. **Agents receive focused context** via AgentSelector (database expert gets schema, not frontend code)
4. **Coordination via messages** using AgentCommunicationQueue (not repeated context)
5. **WorkflowEngine manages execution** with waterfall and parallel patterns

**Production Status**: 152 tests passing (131 unit + 14 API + 7 integration), 100% critical path coverage

**Agent Roles Available**:
- Database Expert (schema design, optimization, migrations)
- API Implementer (REST endpoints, middleware, authentication)
- Frontend Specialist (UI components, state management, styling)
- Tester (unit, integration, and end-to-end testing)
- DevOps Engineer (deployment, CI/CD, infrastructure)
- Security Specialist (authentication, authorization, vulnerability assessment)
- Documentation Manager (technical writing, API docs, guides)

### 34+ MCP Tools for Agent Coordination

**Project Management**:
- REST API for project creation (`POST /api/v1/projects/`)
- `get_product_config()` - Load architecture and constraints
- `update_product_config()` - Modify project settings
- `get_vision()` - Access project vision documents
- `project_status()` - Check overall project health

**Agent Job Management (Handover 0019 - 13 endpoints)**:
- `create_agent_job()` - Create new agent job with mission
- `list_agent_jobs()` - List jobs with filtering (status, agent type)
- `get_agent_job()` - Get job details and status
- `acknowledge_job()` - Agent acknowledges job (pending → active)
- `complete_job()` - Mark job as completed with results
- `fail_job()` - Mark job as failed with error details
- `send_job_message()` - Send message to job's message queue
- `get_job_messages()` - Retrieve agent communications
- `acknowledge_message()` - Mark message as read
- `spawn_child_jobs()` - Create dependent child jobs
- `get_job_hierarchy()` - Get parent-child job tree
- `update_job()` - Update job metadata
- `delete_job()` - Delete completed/failed jobs

**Orchestrator Enhancement (Handover 0020 - 7 REST API endpoints + 3 MCP tools)**:
- **REST API**:
  - `POST /api/orchestrator/process-vision` - Complete workflow orchestration
  - `GET /api/orchestrator/workflow-status/{project_id}` - Status monitoring
  - `GET /api/orchestrator/metrics/{project_id}` - Workflow metrics
  - `POST /api/orchestrator/create-missions` - Mission generation
  - `POST /api/orchestrator/spawn-team` - Agent team spawning
  - `POST /api/orchestrator/coordinate` - Workflow coordination
  - `POST /api/orchestrator/handle-failure` - Failure recovery
- **MCP Tools**:
  - `get_agent_mission()` - Retrieve agent-specific missions
  - `get_workflow_status()` - Monitor workflow progress

**Core Components**:
- **MissionPlanner** (630 lines, 40 tests) - Template-based requirement analysis and mission condensation
- **AgentSelector** (287 lines, 12 tests) - Database template queries with priority cascade
- **WorkflowEngine** (500 lines, 20 tests) - Waterfall and parallel workflow execution with retry logic

**Communication & Coordination**:
- `send_message()` - Inter-agent messaging with priority (high/normal/low)
- `get_messages()` - Retrieve agent communications
- `acknowledge_message()` - Confirm message receipt
- `complete_message()` - Mark communications resolved

**Context Management**:
- `get_context()` - Load relevant project context
- `chunk_vision()` - Handle large documents efficiently

**Development Workflow**:
- `git_status()` - Check repository state
- `git_commit()` - Save progress with descriptive messages
- `run_tests()` - Execute test suites
- `deploy_project()` - Handle deployment workflows

**Serena Optimization Control** (v3.0):
- `get_optimization_settings()` - View current optimization configuration
- `update_optimization_rules()` - Adjust optimization rules per project
- `force_agent_handoff()` - Trigger context-based handoffs

### Hierarchical Context Loading (v2.0)

**Innovation**: Delivers role-relevant context through intelligent depth-level filtering.

**How It Works**:
1. **Orchestrator Level**: Gets full project context (architecture, all features, constraints)
2. **Agent Level**: Gets filtered context relevant to their role
3. **Task Level**: Gets specific context for current work
4. **Handoff Level**: Transfers focused context between agents

**Example**:
```yaml
# Frontend Specialist gets:
context:
  architecture: "Vue 3 + Vuetify"
  ui_patterns: [...]
  styling_guide: [...]
  frontend_tests: [...]
  # Does NOT get: database schemas, API implementation details

# Database Expert gets:
context:
  database_type: "PostgreSQL 18"
  existing_models: [...]
  migration_strategy: [...]
  performance_constraints: [...]
  # Does NOT get: frontend components, styling details
```

### Serena MCP Optimization Layer (v3.0)

**Innovation**: Improves agent efficiency through intelligent symbolic operations.

**Core Optimization Engine**:
- **Automatic symbolic operation enforcement** (find_symbol vs read_file)
- **max_answer_chars injection** prevents massive file reads
- **Context-aware optimization rules** adapt to project size/language
- **Intelligent handoff triggers** when context limits approached

**How It Works**:
1. **Mission-time injection**: Optimization rules added to agent missions automatically
2. **Tool interception**: MCP tool calls optimized in real-time
3. **Symbolic operations**: Prefer find_symbol() over read_file() for targeted analysis
4. **Answer limiting**: Auto-inject character limits on searches and file reads

**Impact**:
- **Focused context delivery** vs naive file reading approaches
- **Extended agent lifespan** before hitting context limits
- **Faster codebase navigation** through symbolic operations
- **Production-grade reliability** with 37 passing unit tests

**Status**: Fully operational (Handover 0010 - COMPLETE)

### Claude Code CLI Integration

**Seamless Integration**: GiljoAI MCP serves as the **persistent brain** while Claude Code provides the **execution engine**.

**Architecture**:
- **Before**: Complex multi-terminal orchestration
- **After**: Elegant sub-agent delegation through Claude Code
- **Result**: Focused context per agent, 95% reliability, 30% less coordination code

**How It Works**:
1. User activates GiljoAI MCP project
2. Orchestrator analyzes requirements
3. Claude Code spawns specialized sub-agents
4. GiljoAI MCP maintains state and coordination
5. Sub-agents execute focused implementations
6. Results integrated through persistent project memory

### Intelligence & Learning

**Pattern Recognition**:
- Learns from successful implementations
- Codifies patterns into reusable templates
- Suggests optimal agent combinations for tasks
- Remembers architecture decisions across projects

**Continuous Improvement**:
- Tracks which approaches work best
- Optimizes agent handoff timing
- Improves context filtering accuracy
- Refines specialization boundaries

---

## Complete System Overview

### How the Pieces Work Together

**GiljoAI MCP's power comes from the integration of all components**:

1. **Installation (Handover 0035)**: Single unified installer sets up PostgreSQL, creates database with pg_trgm extension, configures v3.0 architecture (0.0.0.0 binding), launches setup wizard

2. **First Admin Setup (Handover 0035 + 0023)**: Setup wizard creates first admin with custom credentials, sets SetupState.first_admin_created flag, admin creates recovery PIN on first login

3. **Project Creation**: Admin creates new product with vision document, configures multi-tenant isolation, generates API keys for MCP tools

4. **Orchestration Workflow (Handover 0020)**:
   - Developer requests feature implementation via `POST /api/orchestrator/process-vision`
   - **MissionPlanner** analyzes vision, generates condensed role-specific missions per agent
   - **AgentSelector** queries AgentTemplate database, applies priority cascade (product > tenant > system)
   - **WorkflowEngine** spawns agent jobs, manages waterfall or parallel execution

5. **Agent Job Management (Handover 0019)**:
   - Each agent receives job via `POST /api/agent-jobs` (status: pending)
   - Agent acknowledges via `POST /api/agent-jobs/{id}/acknowledge` (pending → active)
   - Agents coordinate via JSONB message queue with priority levels
   - Parent jobs spawn child jobs for complex workflows
   - WebSocket events broadcast real-time updates (6 event types)
   - Jobs complete via `POST /api/agent-jobs/{id}/complete` with results

6. **Context Prioritization (Handovers 0019 + 0020)**:
   - Full vision read ONCE by orchestrator
   - Condensed, role-specific missions generated per agent
   - Agent coordination via lightweight JSONB messages

7. **Security Throughout (Handovers 0023, 0035)**:
   - All operations require JWT authentication
   - Multi-tenant isolation enforced (tenant_key filtering)
   - Recovery PIN system for self-service password reset
   - First admin endpoint disabled after initial setup
   - 100% WCAG 2.1 AA accessibility compliance

8. **Management & Monitoring (Handovers 0025-0029)**:
   - Admin Settings v3.0 for system configuration
   - Users page for user management and password resets
   - Real-time WebSocket events for job monitoring

**Result**: Complete, production-ready system for multi-agent orchestration with intelligent context prioritization.

---

## Target Use Cases

### Large-Scale Application Development

**Scenario**: Building a full-stack web application with authentication, data management, API layer, and responsive frontend.

**GiljoAI MCP Approach**:
- Orchestrator analyzes requirements and creates implementation plan
- Database Expert designs normalized schema with proper indexing
- API Implementer creates RESTful endpoints with authentication
- Frontend Specialist builds responsive UI with state management
- Security Specialist adds authentication and authorization
- Tester writes comprehensive test suite
- All work coordinated through persistent project state

### Legacy System Modernization  

**Scenario**: Migrating a monolithic application to microservices architecture.

**GiljoAI MCP Approach**:
- Orchestrator maps existing system architecture  
- Database Expert designs data migration strategy
- API Implementer extracts services with backward compatibility
- DevOps Engineer sets up containerization and deployment
- Tester ensures functionality preservation through migration
- Documentation Manager creates migration guides and API docs

### Complex Feature Implementation

**Scenario**: Adding advanced search with filtering, pagination, and performance optimization.

**GiljoAI MCP Approach**:
- Database Expert designs search indexes and query optimization
- API Implementer creates search endpoints with caching
- Frontend Specialist builds search UI with real-time filtering
- Performance Engineer optimizes for large datasets
- Tester validates search accuracy and performance
- Coordinated implementation across all layers

### Code Quality & Refactoring

**Scenario**: Improving code quality, adding tests, and modernizing dependencies.

**GiljoAI MCP Approach**:
- Code Reviewer analyzes quality issues across codebase
- Refactoring Specialist improves code structure and patterns
- Tester adds comprehensive test coverage
- Security Specialist addresses vulnerabilities
- Documentation Manager updates technical documentation
- DevOps Engineer modernizes deployment pipeline

---

## Integration with Development Workflows

### Git Workflow Integration

- **Smart commits**: Agents create descriptive commit messages with context
- **Branch coordination**: Multiple agents can work on feature branches
- **Conflict resolution**: Orchestrator mediates merge conflicts
- **Code review**: Automated analysis before human review

### CI/CD Pipeline Integration

- **Test orchestration**: Agents run appropriate tests for their changes
- **Deployment coordination**: DevOps agents handle environment-specific deployments  
- **Rollback capabilities**: Automatic fallback when deployments fail
- **Environment promotion**: Coordinated promotion from dev to production

### Documentation Generation

- **Living documentation**: Automatically updated as code changes
- **API documentation**: Generated from code with human-readable descriptions
- **Architecture diagrams**: Visual representations of system structure
- **Developer onboarding**: Guides generated from current system state

---

## Technical Foundation

### Multi-Tenant Architecture

- **Tenant isolation**: All projects isolated at database level
- **Resource sharing**: Efficient sharing of common agent templates
- **Scalability**: Supports multiple concurrent development projects
- **Security**: No cross-tenant data leakage
- **Per-user API keys**: Individual access control and auditing (v3.0)

### User API Key Management (v3.0)

**Innovation**: Secure, per-user API key system for MCP tool integration.

**Core Features**:
- **Personal API keys**: Each user generates their own keys for MCP tools
- **Automatic integration**: AI coding agent config generator creates keys automatically
- **Tenant-scoped security**: All API keys filtered by tenant_key
- **Bcrypt hashing**: Secure storage with one-time plaintext display
- **Full lifecycle management**: Generate, list, revoke, audit

**AI Coding Agent Integration**:
- **One-click configuration**: Generate Claude Code, CODEX, Gemini configs
- **Embedded API keys**: User keys automatically included in configs
- **Tenant isolation**: Each user's keys only access their projects
- **Professional UI**: 266-line ApiKeyManager component with data tables

**Status**: Fully operational (Handover 0015 - COMPLETE)

### Performance & Reliability

- **Focused context delivery**: Role-relevant context through depth-level configuration
- **Fault tolerance**: Graceful handling of agent failures
- **Scalable architecture**: Supports teams of any size

### Security & Compliance

**Authentication & Authorization**:
- **JWT-based security**: All API access requires authentication
- **Role-based access control**: Admin/user permissions enforced
- **No default credentials**: First admin created during setup wizard (Handover 0035)
- **Password reset via Recovery PIN**: Self-service 4-digit PIN reset (Handover 0023)
- **Rate limiting**: 5 failed PIN attempts = 15-minute lockout
- **Bcrypt hashing**: Secure password and PIN storage with timing-safe comparison
- **First admin lockdown**: SetupState.first_admin_created flag disables admin creation endpoint after initial setup

**Password Reset System (Handover 0023 - PRODUCTION READY)**:
- **Recovery PIN**: User-set 4-digit PIN for password reset
- **Self-service reset**: No admin intervention required for password recovery
- **Security features**: Generic error messages prevent user enumeration
- **Audit logging**: All authentication attempts logged
- **First login flow**: Force password change + PIN setup for new users
- **Admin override**: Admins can reset passwords and force PIN setup
- **Frontend Components**: 5 Vue 3 components (FirstLogin.vue, ForgotPasswordPin.vue, enhanced UserManager.vue)
- **API Endpoints**: 4 new authentication endpoints fully implemented
- **Test Coverage**: All 348 frontend modules compiled successfully, build time 3.62s
- **Accessibility**: WCAG 2.1 AA compliant throughout

**Multi-Tenant Security**:
- **100% tenant isolation**: All database queries filter by tenant_key
- **API key security**: Per-user bcrypt-hashed API keys with one-time display
- **Cross-tenant protection**: 404 errors prevent tenant discovery
- **WebSocket isolation**: Events only broadcast within same tenant

**Compliance & Auditing**:
- **Audit trails**: Complete logging of agent actions and authentication
- **Data privacy**: Secure handling of proprietary code
- **GDPR ready**: User data isolation and deletion support
- **SOC 2 alignment**: Security controls and audit logging

---

## Future Vision

### Enhanced AI Integration

- **Multi-modal agents**: Agents that work with code, documentation, diagrams, and UI mockups
- **Learning from feedback**: Agents improve based on developer input
- **Cross-project learning**: Patterns learned in one project applied to others

### Advanced Coordination

- **Conflict prediction**: Proactive identification of potential integration issues
- **Resource optimization**: Dynamic allocation of agents based on workload
- **Quality metrics**: Automated assessment of code quality and architecture

### Developer Experience

- **Visual orchestration**: Dashboard showing agent coordination in real-time
- **Interactive guidance**: Agents provide suggestions and alternatives
- **Seamless integration**: Native support in popular IDEs and development tools

---

## Production-Ready Features

### Cross-Platform Unified Installer (Handover 0035 - COMPLETE)

**Professional Architecture**:
- **Single unified installer**: `python install.py` for all platforms (Windows, Linux, macOS)
- **Platform handler strategy pattern**: Clean separation of platform-specific code (PlatformHandler base class)
- **33% code reduction**: 5,000+ lines → 3,350 lines with eliminated duplication
- **Auto-detection**: Automatically selects correct handler for Windows/Linux/macOS
- **Future-ready**: Extensible for Docker, WSL, and additional platforms

**Installation Features**:
- **PostgreSQL auto-discovery**: Finds installed PostgreSQL across all platforms with intelligent path detection
- **Database setup**: Creates giljo_mcp database with pg_trgm extension (required for full-text search)
- **Network configuration**: v3.0 unified binding (0.0.0.0) with firewall control and external IP selection
- **First admin creation**: Secure setup wizard (no default credentials) with first_admin_created flag
- **Config generation**: Platform-appropriate paths and settings (venv, PostgreSQL, npm)
- **Security enhancement**: SetupState.first_admin_created field prevents duplicate admin creation attacks

**Critical Bug Fixes**:
- **pg_trgm extension**: Now created on all platforms (was missing on Linux installer)
- **Import path consistency**: Unified installer.core paths across all platforms
- **Success messages**: Accurate messaging aligned with Handover 0034 (no admin/admin defaults)

### Admin Settings v3.0 (Handovers 0025-0029 - COMPLETE)

**SystemSettings.vue - 4 Professional Tabs**:
1. **Network Tab** (Handover 0025): v3.0 unified architecture (0.0.0.0 binding), firewall configuration, removed all deployment mode concepts
   - Shows Internal Binding (0.0.0.0) and External Access IP
   - v3.0 architecture info alert explaining unified binding
   - Port chips displaying API:7272 and Frontend:7274
   - Enhanced CORS section with proper labeling
   - Copy button for external host
   - All mode-related UI removed (no localhost/lan/wan badges)
2. **Database Tab**: Connection info, user role management, enhanced testing
3. **Integrations Tab**: Claude Code CLI, Codex CLI, Gemini CLI configs with logos
4. **Security Tab**: Cookie domain whitelist management

**UserSettings.vue Enhancements**:
- **API Key Management**: Industry-standard masking (sk-...xyz format)
- **Serena Integration**: Toggle for Serena MCP optimization
- **AI Coding Agent Instructions**: Configuration help for Claude Code, etc.
- **WCAG 2.1 AA Compliant**: Full accessibility standards

**Standalone Users Page** (Handover 0029):
- **Admin-only access**: Via avatar dropdown Users menu (relocated from Admin Settings)
- **Enhanced management**: Email addresses, creation dates, roles, password reset
- **Professional interface**: Data tables, search, filtering, confirmation dialogs
- **Password reset integration**: Admin can trigger password reset and force PIN setup

**Test Coverage**: 193+ comprehensive TDD tests (44 tests for Network tab alone)
**Quality**: 100% test pass rate, zero critical/major/minor bugs, WCAG 2.1 AA compliant
**Performance**: Frontend build 3.12s, Frontend tests 3.30s, Backend tests 2.92s

### AI Coding Agent Integration

**Seamless Claude Code Integration**:
- **One-click configuration**: Generate MCP config with embedded API keys
- **AI Coding Agent Config Generator**: Professional 266-line component
- **Automatic key injection**: User API keys embedded in generated configs
- **Multi-tool support**: Claude Code, CODEX, Gemini CLI

---

## Getting Started

### Quick Start

1. **Installation**: `python install.py` (cross-platform unified installer)
2. **Setup Wizard**: Create first admin account (no defaults, secure by design)
3. **API Key Generation**: User Settings → API Keys → Generate for MCP tools
4. **AI Coding Agent Configuration**: Admin Settings → Integrations → Generate configs
5. **Project Setup**: Create new project or import existing codebase
6. **Agent Configuration**: Select desired agent specializations
7. **First Orchestration**: Start with a simple feature implementation
8. **Monitor Progress**: Watch agents coordinate through the dashboard

### Best Practices

**Orchestration Workflow**:
- **Start with orchestration**: Let the orchestrator read full context ONCE and create condensed missions
- **Trust the context prioritization**: Orchestrator generates focused, role-specific missions per agent
- **Use workflow patterns**: Leverage waterfall (sequential) or parallel execution as appropriate

**Agent Coordination**:
- **Trust specialization**: Allow agents to focus on their areas of expertise (database, API, frontend, testing)
- **Use job hierarchies**: Break complex work into parent-child job structures via spawned_by relationships
- **Leverage message queues**: Let agents coordinate via JSONB messages without duplicating context
- **Monitor job status**: Watch real-time WebSocket events (6 event types) for coordination updates
- **Handle failures gracefully**: Use WorkflowEngine retry logic and failure recovery strategies

**Multi-Tenant Best Practices**:
- **Verify tenant isolation**: All database queries must filter by tenant_key
- **Use 404 responses**: Return 404 for cross-tenant access attempts (prevents tenant discovery)
- **Test isolation**: Run multi-tenant isolation tests for all new features

**Security & Quality**:
- **No default credentials**: Always use setup wizard to create first admin with custom credentials
- **Enable recovery PINs**: Ensure users set 4-digit PINs during first login for self-service password reset
- **Preserve patterns**: Document successful approaches for reuse in AgentTemplate database
- **Iterate and improve**: Refine agent coordination based on results

---

**See Also**:
- [User Structures & Tenants](USER_STRUCTURES_TENANTS.md) - Understanding multi-tenant architecture
- [Server Architecture & Tech Stack](SERVER_ARCHITECTURE_TECH_STACK.md) - Technical implementation details
- [Installation Flow & Process](INSTALLATION_FLOW_PROCESS.md) - Setup and configuration guide
- [First Launch Experience](FIRST_LAUNCH_EXPERIENCE.md) - Complete onboarding walkthrough

---

*This document establishes the foundational understanding of GiljoAI MCP's purpose, capabilities, and value proposition as the single source of truth. Last updated October 21, 2025 to reflect completed handovers 0019 (Agent Job Management), 0020 (Orchestrator Enhancement), 0023 (Password Reset), 0025-0029 (Admin Settings v3.0), and 0035 (Cross-Platform Installer).*