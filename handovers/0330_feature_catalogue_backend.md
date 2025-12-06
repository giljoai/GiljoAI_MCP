# Backend Feature Catalogue (Handover 0330)

**Date**: 2025-12-05
**Purpose**: Comprehensive inventory of GiljoAI MCP backend features for maintainability and knowledge transfer
**Status**: Complete

---

## Table of Contents

1. [User Management & Authentication](#1-user-management--authentication)
2. [Product Management](#2-product-management)
3. [Project Management](#3-project-management)
4. [Task Management](#4-task-management)
5. [Message System](#5-message-system)
6. [Context Management](#6-context-management)
7. [Agent Template Management](#7-agent-template-management)
8. [Orchestration & Agent Jobs](#8-orchestration--agent-jobs)
9. [MCP Tools & Tool Management](#9-mcp-tools--tool-management)
10. [Database Models](#10-database-models)
11. [WebSocket Events](#11-websocket-events)
12. [Configuration & Settings](#12-configuration--settings)
13. [Thin Client & Prompt Generation](#13-thin-client--prompt-generation)
14. [Git Integration](#14-git-integration)
15. [Download & File Management](#15-download--file-management)
16. [Optimization](#16-optimization)
17. [Slash Commands](#17-slash-commands)
18. [Vision Documents](#18-vision-documents)
19. [Agent Discovery](#19-agent-discovery)
20. [System Utilities](#20-system-utilities)
21. [Middleware & Security](#21-middleware--security)
22. [Validation](#22-validation)
23. [Statistics & Monitoring](#23-statistics--monitoring)
24. [Workflow Engine](#24-workflow-engine)
25. [Exceptions & Enums](#25-exceptions--enums)
26. [System Roles](#26-system-roles)
27. [Claude Config](#27-claude-config)

---

## Feature Categories

### 1. User Management & Authentication

**Purpose**: Complete user lifecycle management including registration, login, API key management, and password recovery via PIN system.

**Key Files**:
- `src/giljo_mcp/services/auth_service.py` (762 lines)
- `src/giljo_mcp/services/user_service.py` (1,361 lines)
- `src/giljo_mcp/auth_manager.py`
- `api/endpoints/auth.py` (907 lines)
- `api/endpoints/auth_pin_recovery.py`
- `api/endpoints/users.py` (1,011 lines)
- `src/giljo_mcp/models/auth.py` (266 lines)

**Key Classes/Functions**:
- `AuthService` - Authentication operations (login, logout, token management)
- `UserService` - User CRUD operations, profile management
- `AuthManager` - Middleware and tool registration
- `LoginRequest`, `RegisterUserRequest`, `PinPasswordResetRequest` - Pydantic schemas
- `login()`, `logout()`, `register_user()`, `create_first_admin_user()` - API endpoints

**Dependencies**:
- Database Models (User, APIKey, Session)
- JWT token management
- WebSocket events for user state changes
- Multi-tenant isolation (tenant_key)

**Complexity**: **High**
- Complex password reset flow with PIN recovery (Handover 0023)
- First-time setup wizard integration
- API key lifecycle management
- Per-user tenant isolation (Nov 2025 policy)
- Session management and token refresh

---

### 2. Product Management

**Purpose**: Manage products (codebases), vision documents with chunked uploads, and 360 Memory for cumulative knowledge.

**Key Files**:
- `src/giljo_mcp/services/product_service.py` (1,589 lines)
- `api/endpoints/products/*.py` (lifecycle.py, crud.py, vision.py)
- `src/giljo_mcp/models/products.py` (550 lines)
- `src/giljo_mcp/repositories/vision_document_repository.py`

**Key Classes/Functions**:
- `ProductService` - Product CRUD, activation, vision document management
- `VisionDocumentRepository` - Vision document storage and chunking
- Product model with `product_memory` JSONB column (360 Memory)

**Dependencies**:
- Vision chunking (<25K tokens per chunk)
- WebSocket events (`product:created`, `product:memory_updated`)
- GitHub integration (optional, fallback to manual summaries)
- Multi-tenant isolation

**Complexity**: **High**
- Vision document chunking and pagination
- 360 Memory management (sequential project history)
- Product activation/deactivation lifecycle
- GitHub integration with fallback
- Product-level context aggregation

---

### 3. Project Management

**Purpose**: Project lifecycle operations including creation, activation, soft delete with recovery, and closeout with 360 Memory updates.

**Key Files**:
- `src/giljo_mcp/services/project_service.py` (2,563 lines - largest service)
- `api/endpoints/projects/*.py` (crud.py 406 lines, lifecycle.py 511 lines)
- `src/giljo_mcp/models/projects.py` (210 lines)

**Key Classes/Functions**:
- `ProjectService` - Comprehensive project lifecycle management
- Methods: `activate()`, `deactivate()`, `summary()`, `launch()`, `soft_delete()`, `recover()`
- Project model with `description` (user input) vs `mission` (AI-generated) fields

**Dependencies**:
- Product management (must belong to active product)
- Orchestrator coordination (launch triggers orchestration)
- WebSocket events (`project:created`, `project:activated`, `project:deleted`)
- 360 Memory updates on closeout
- Cascade deletion for related entities (Handover 0329)

**Complexity**: **High**
- Largest service file (2,563 lines)
- Complex lifecycle state machine
- Soft delete with 30-day recovery window
- Integration with orchestration pipeline
- Field naming conventions (description vs mission)

---

### 4. Task Management

**Purpose**: Task creation, assignment, and lifecycle management for agent coordination.

**Key Files**:
- `src/giljo_mcp/services/task_service.py` (1,070 lines)
- `api/endpoints/tasks.py` (447 lines)
- `src/giljo_mcp/models/tasks.py` (148 lines)

**Key Classes/Functions**:
- `TaskService` - Task CRUD and assignment operations
- Methods: `create()`, `update()`, `assign()`, `complete()`, `list_tasks()`
- Task model with status tracking (pending, in_progress, completed, failed)

**Dependencies**:
- Agent job management (tasks assigned to agents)
- Project association
- WebSocket events for task updates
- Multi-tenant isolation

**Complexity**: **Medium**
- Straightforward CRUD operations
- Task-to-agent assignment logic
- Status state transitions
- Project-scoped task queries

---

### 5. Message System

**Purpose**: Agent-to-agent and orchestrator-to-agent communication with auto-acknowledge, priority routing, and dead-letter queue.

**Key Files**:
- `src/giljo_mcp/services/message_service.py` (1,018 lines)
- `src/giljo_mcp/agent_message_queue.py`
- `api/endpoints/messages.py`

**Key Classes/Functions**:
- `MessageService` - Message creation, delivery, auto-acknowledge (Handover 0326)
- `AgentMessageQueue` - Priority queue with routing engine
- `RoutingEngine`, `CircuitBreaker`, `DeadLetterQueue` - Advanced queue features
- `MessagePriority` enum (low, normal, high)

**Dependencies**:
- Agent job status tracking
- WebSocket events for real-time message delivery
- Auto-acknowledge on receive (Handover 0326 - removed manual acknowledge)
- Multi-tenant isolation

**Complexity**: **High**
- Auto-acknowledge simplification (Handover 0326)
- Priority-based routing
- Dead-letter queue for failed deliveries
- Circuit breaker for fault tolerance
- Real-time counter persistence and WebSocket sync

---

### 6. Context Management

**Purpose**: 2-dimensional context management (Priority × Depth) with 9 MCP context tools for orchestrator configuration.

**Key Files**:
- `src/giljo_mcp/services/context_service.py` (184 lines)
- `src/giljo_mcp/tools/context_tools/*.py` (10 files)
- `api/endpoints/context.py` (477 lines)
- `src/giljo_mcp/models/context.py` (175 lines)

**Key Classes/Functions**:
- `ContextService` - Context priority and depth configuration
- 9 context tools: `fetch_product_context`, `fetch_vision_document`, `fetch_tech_stack`, `fetch_architecture`, `fetch_testing_config`, `fetch_360_memory`, `fetch_git_history`, `fetch_agent_templates`, `fetch_project_context`
- Priority levels: CRITICAL, IMPORTANT, NICE_TO_HAVE, EXCLUDED
- Depth levels: Configurable per field (e.g., vision: none/light/moderate/heavy)

**Dependencies**:
- Product and project data
- User settings for context configuration
- Vision document repository
- Git service for commit history
- Template service for agent templates

**Complexity**: **High**
- 2-dimensional configuration model (v2.0 Nov 2025)
- 9 specialized context fetch tools
- Token budget management (0-30K tokens per field)
- Pagination for large data sets
- Context Configurator UI integration

---

### 7. Agent Template Management

**Purpose**: Agent template lifecycle including system templates, user templates, seeding, validation, and materialization.

**Key Files**:
- `src/giljo_mcp/services/template_service.py` (483 lines)
- `src/giljo_mcp/template_manager.py`
- `src/giljo_mcp/template_seeder.py`
- `src/giljo_mcp/template_validation.py`
- `src/giljo_mcp/template_materializer.py`
- `api/endpoints/templates/*.py` (crud.py 467 lines)
- `src/giljo_mcp/models/templates.py` (253 lines)

**Key Classes/Functions**:
- `TemplateService` - Template CRUD and validation
- `UnifiedTemplateManager` - Template discovery and loading
- `TemplateMaterializer` - Variable substitution and rendering
- `TemplateValidator` - Schema and content validation
- Template model with augmentation support

**Dependencies**:
- File system for .md templates
- Variable extraction and substitution
- Validation rules
- Multi-tenant isolation (system vs user templates)
- USER_MANAGED_AGENT_LIMIT constant

**Complexity**: **High**
- Dual template system (system vs user-managed)
- Template seeding on first run
- Variable substitution engine
- Augmentation type support
- Template discovery across multiple paths

---

### 8. Orchestration & Agent Jobs

**Purpose**: Orchestrator workflow pipeline (Staging → Discovery → Spawning → Execution) with thin-client architecture and succession management.

**Key Files**:
- `src/giljo_mcp/orchestrator.py` (1,891 lines)
- `src/giljo_mcp/agent_job_manager.py` (1,196 lines)
- `src/giljo_mcp/services/orchestration_service.py` (1,211 lines)
- `src/giljo_mcp/orchestrator_succession.py`
- `api/endpoints/orchestration.py`
- `api/endpoints/agent_jobs/orchestration.py` (436 lines)

**Key Classes/Functions**:
- `ProjectOrchestrator` - Main orchestration logic
- `AgentJobManager` - Agent job lifecycle (create, spawn, monitor, cancel)
- `OrchestrationService` - Context tracking, succession management
- Methods: `request_job_cancellation()`, `force_fail_job()`, succession triggers

**Dependencies**:
- Thin prompt generator (450-550 tokens)
- Context service for orchestrator instructions
- Agent discovery (dynamic via MCP tool)
- WebSocket events for job status
- Multi-tenant isolation

**Complexity**: **High**
- 85% token reduction (Handovers 0246a-c)
- 7-task staging workflow (0246a)
- Dynamic agent discovery (0246c - 71% savings)
- Orchestrator succession at 90% capacity
- Context tracking per message
- Agent job cancellation and monitoring (Handover 0107)

---

### 9. MCP Tools & Tool Management

**Purpose**: 23+ MCP tools for agent coordination, context fetching, project management, and orchestration.

**Key Files**:
- `src/giljo_mcp/tools/tool_accessor.py` (1,293 lines - reduced 48% from 2,324)
- `src/giljo_mcp/tools/*.py` (35 tool files)
- `src/giljo_mcp/tools/__init__.py` - Tool registration
- `api/endpoints/mcp_tools.py` (673 lines)
- `api/endpoints/mcp_http.py` (754 lines)

**Key Classes/Functions**:
- `ToolAccessor` - Centralized tool access and registration
- Categories: Agent coordination, context fetching, project management, succession tools, optimization
- HTTP-only MCP (stdio deprecated Nov 2025)
- JSON-RPC endpoint at `/mcp`

**Dependencies**:
- All service layers (tools are thin wrappers)
- Multi-tenant isolation (all tools filter by tenant_key)
- Authentication via X-API-Key header
- WebSocket events for state changes

**Complexity**: **High**
- 35 tool files covering all backend features
- ToolAccessor reduced 48% (Handover 0120-0130)
- HTTP transport layer (stdio deprecated)
- Tool registration and discovery
- Multi-tenant filtering in all tools

---

### 10. Database Models

**Purpose**: SQLAlchemy models for 12 entity types with multi-tenant isolation and cascade deletion.

**Key Files**:
- `src/giljo_mcp/models/*.py` (3,098 total lines)
- `src/giljo_mcp/models/agents.py` (311 lines)
- `src/giljo_mcp/models/auth.py` (266 lines)
- `src/giljo_mcp/models/products.py` (550 lines)
- `src/giljo_mcp/models/projects.py` (210 lines)
- `src/giljo_mcp/models/tasks.py` (148 lines)
- `src/giljo_mcp/models/templates.py` (253 lines)
- `src/giljo_mcp/models/context.py` (175 lines)
- `src/giljo_mcp/models/config.py` (677 lines)
- `src/giljo_mcp/models/settings.py` (51 lines)
- `src/giljo_mcp/models/schemas.py` (241 lines)
- `src/giljo_mcp/models/base.py` (37 lines)

**Key Classes/Functions**:
- 32 tables from pristine SQLAlchemy models (Handover 0601)
- Entity types: User, Product, Project, Task, Message, AgentJob, Template, Vision, Context, Settings, APIKey, Session
- Cascade deletion for product-related tables (Handover 0329)
- JSONB columns for flexible data (product_memory, context_config)

**Dependencies**:
- PostgreSQL 18 required
- Single baseline migration (Handover 0601)
- Multi-tenant isolation via tenant_key
- Soft delete support (is_deleted, deleted_at columns)

**Complexity**: **High**
- 32 tables with complex relationships
- JSONB columns for structured data
- Cascade deletion rules
- Soft delete pattern
- Multi-tenant isolation constraints
- Field naming conventions (description vs mission)

---

### 11. WebSocket Events

**Purpose**: Real-time UI updates via WebSocket events for all state changes with tenant-scoped broadcasts.

**Key Files**:
- `api/websocket.py`
- `api/websocket_manager.py`
- `api/websocket_service.py`
- `api/event_bus.py`
- `api/websocket_event_listener.py`

**Key Classes/Functions**:
- `WebSocketManager` - Connection management and broadcast
- `EventBus` - Event publication and subscription
- Event types: `product:*`, `project:*`, `agent_job:*`, `message:*`, `context:*`
- Tenant-scoped events (no cross-tenant leakage)

**Dependencies**:
- All service layers (emit events on state changes)
- Frontend Vue components (subscribe to events)
- Per-user tenancy policy (Nov 2025)

**Complexity**: **Medium**
- Tenant-scoped event filtering
- WebSocket connection lifecycle
- Event bus pub/sub pattern
- Real-time counter updates (Handover 0326)

---

### 12. Configuration & Settings

**Purpose**: System configuration management and user-specific settings persistence.

**Key Files**:
- `src/giljo_mcp/config_manager.py`
- `src/giljo_mcp/services/settings_service.py` (112 lines)
- `src/giljo_mcp/services/config_service.py` (84 lines)
- `api/endpoints/settings.py`
- `api/endpoints/configuration.py` (615 lines)
- `src/giljo_mcp/models/config.py` (677 lines)
- `src/giljo_mcp/models/settings.py` (51 lines)

**Key Classes/Functions**:
- `ConfigManager` - System config loading and watching
- `SettingsService` - User settings CRUD
- Config classes: `ServerConfig`, `DatabaseConfig`, `LoggingConfig`, `SessionConfig`, `AgentConfig`, `MessageConfig`, `TenantConfig`, `FeatureFlags`
- Methods: `get_config()`, `set_config()`, `generate_sample_config()`

**Dependencies**:
- `config.yaml` file (gitignored)
- Database for user settings
- WebSocket events for settings updates
- v3.0 unified architecture (0.0.0.0 binding, firewall control)

**Complexity**: **Medium**
- Config file watching and hot reload
- User-specific settings vs system config
- Feature flags support
- Network configuration (v3.0)

---

### 13. Thin Client & Prompt Generation

**Purpose**: Thin-client prompt generation for context prioritization and orchestration (450-550 tokens vs 3,500 legacy).

**Key Files**:
- `src/giljo_mcp/thin_prompt_generator.py` (1,263 lines)
- `src/giljo_mcp/prompt_generation/*.py`
- `api/endpoints/prompts.py` (680 lines)

**Key Classes/Functions**:
- `ThinClientPromptGenerator` - Staging workflow generation (7 tasks, 931 tokens)
- `ThinPromptResponse` - Response schema
- Methods: `_build_staging_prompt()`, `_build_generic_agent_prompt()`
- 85% token reduction (Handovers 0246a-c)

**Dependencies**:
- Context service (field priorities)
- Orchestration service (orchestrator metadata)
- Agent discovery (dynamic template loading)
- MCP tools (`get_orchestrator_instructions`, `get_agent_mission`)

**Complexity**: **High**
- 7-task staging workflow (0246a)
- Generic agent template (6-phase protocol, 1,253 tokens, 0246b)
- Dynamic agent discovery (420 tokens, 0246c)
- Client-server separation (server provides tools, client executes)
- Context prioritization integration

---

### 14. Git Integration

**Purpose**: Optional GitHub integration for commit tracking in 360 Memory with manual summary fallback.

**Key Files**:
- `src/giljo_mcp/services/git_service.py` (323 lines)
- `api/endpoints/git.py`

**Key Classes/Functions**:
- `GitService` - Commit fetching and aggregation
- Methods: `fetch_commits()`, `aggregate_git_history()`
- GitHub API integration (optional)

**Dependencies**:
- Product-level GitHub configuration
- 360 Memory system (git commits in sequential history)
- Manual summary fallback when disabled
- Multi-tenant isolation

**Complexity**: **Medium**
- Optional feature with fallback
- GitHub API rate limiting
- Commit aggregation across projects
- Integration with 360 Memory

---

### 15. Download & File Management

**Purpose**: Secure file downloads via expiring tokens and file staging for agent templates.

**Key Files**:
- `src/giljo_mcp/downloads/*.py`
- `src/giljo_mcp/download_tokens.py`
- `src/giljo_mcp/file_staging.py`
- `api/endpoints/downloads.py` (842 lines)

**Key Classes/Functions**:
- Download token generation (expiring URLs)
- File staging for template exports
- Secure file serving with token validation

**Dependencies**:
- Template service (for agent template downloads)
- Authentication (token validation)
- File system access

**Complexity**: **Medium**
- Token expiration management
- File staging and cleanup
- Secure download URLs
- Template export functionality

---

### 16. Optimization

**Purpose**: Serena MCP detection, tool interception, and optimization strategies.

**Key Files**:
- `src/giljo_mcp/optimization/*.py`
- `src/giljo_mcp/optimization/serena_optimizer.py`
- `src/giljo_mcp/optimization/tool_interceptor.py`
- `src/giljo_mcp/services/serena_detector.py` (166 lines)

**Key Classes/Functions**:
- `SerenaDetector` - Detect Serena MCP availability
- `SerenaOptimizer` - Optimize tool usage with Serena
- `ToolInterceptor` - Intercept and optimize tool calls

**Dependencies**:
- Serena MCP (optional)
- Tool accessor
- Configuration settings

**Complexity**: **Medium**
- Optional optimization layer
- Serena detection logic
- Tool call interception
- Performance optimizations

---

### 17. Slash Commands

**Purpose**: MCP slash commands for agent template imports and orchestrator handover.

**Key Files**:
- `src/giljo_mcp/slash_commands/*.py`
- `src/giljo_mcp/tools/slash_command_templates.py`

**Key Classes/Functions**:
- `/gil_import_productagents` - Import templates to product
- `/gil_import_personalagents` - Import templates to personal folder
- `/gil_handover` - Trigger orchestrator succession
- `/gil_fetch` - Stage and return download URL
- `/gil_activate` - Activate project and ensure orchestrator
- `/gil_launch` - Launch project execution

**Dependencies**:
- Template service
- Orchestration service
- File system access
- Multi-tenant isolation

**Complexity**: **Low**
- Simple command implementations
- File copy operations
- Tool call wrappers

---

### 18. Vision Documents

**Purpose**: Vision document management with chunking (<25K tokens per chunk) and pagination.

**Key Files**:
- `src/giljo_mcp/repositories/vision_document_repository.py`
- `api/endpoints/vision_documents.py` (465 lines)
- Vision model in `products.py`

**Key Classes/Functions**:
- `VisionDocumentRepository` - CRUD and chunking operations
- Chunking logic (<25K tokens)
- Pagination for large documents

**Dependencies**:
- Product service
- Chunking utilities
- Token counting
- Multi-tenant isolation

**Complexity**: **Medium**
- Automatic chunking on upload
- Token budget management
- Pagination API
- Product association

---

### 19. Agent Discovery

**Purpose**: Dynamic agent discovery via MCP tool (71% token savings) replacing embedded templates.

**Key Files**:
- `src/giljo_mcp/discovery.py`
- `src/giljo_mcp/agent_selector.py`
- `src/giljo_mcp/tools/agent_discovery.py`

**Key Classes/Functions**:
- `DiscoveryManager` - Agent template discovery
- `AgentSelector` - Agent selection logic
- `PathResolver` - Template path resolution
- `SerenaHooks` - Serena integration hooks
- `get_available_agents()` MCP tool (Handover 0246c)

**Dependencies**:
- Template service
- File system discovery
- Multi-tenant isolation
- Thin prompt generator

**Complexity**: **Medium**
- Dynamic discovery vs embedded templates
- 71% token reduction (420 tokens)
- Path resolution across multiple sources
- Serena integration

---

### 20. System Utilities

**Purpose**: Logging, network detection, port management, tenant utilities, and database operations.

**Key Files**:
- `src/giljo_mcp/colored_logger.py`
- `src/giljo_mcp/network_detector.py`
- `src/giljo_mcp/port_manager.py`
- `src/giljo_mcp/tenant.py`
- `src/giljo_mcp/database.py`
- `src/giljo_mcp/database_backup.py`

**Key Classes/Functions**:
- `ColoredLogger` - Structured logging with colors
- `AdapterIPDetector` - Network interface detection
- `PortManager` - Dynamic port allocation
- Tenant utilities (per-user isolation)
- Database connection management

**Dependencies**:
- Configuration settings
- File system access
- Network interfaces
- PostgreSQL connection

**Complexity**: **Low to Medium**
- Utility functions
- Network detection logic
- Database connection pooling
- Tenant isolation utilities

---

### 21. Middleware & Security

**Purpose**: Authentication, CSRF protection, rate limiting, input validation, logging, and security headers.

**Key Files**:
- `api/middleware/auth.py`
- `api/middleware/csrf.py`
- `api/middleware/rate_limiter.py`
- `api/middleware/input_validator.py`
- `api/middleware/security.py`
- `api/middleware/logging_middleware.py`
- `api/middleware/metrics.py`

**Key Classes/Functions**:
- Auth middleware (JWT validation)
- CSRF token validation
- Rate limiter (per-user, per-endpoint)
- Input sanitization
- Security headers (CORS, CSP, etc.)
- Request/response logging
- Metrics collection

**Dependencies**:
- Authentication service
- Configuration settings
- User service
- WebSocket manager (for blocked events)

**Complexity**: **Medium**
- Multiple middleware layers
- Rate limiting algorithms
- CSRF token management
- Security header configuration

---

### 22. Validation

**Purpose**: Template validation and business rule enforcement.

**Key Files**:
- `src/giljo_mcp/validation/*.py`
- `src/giljo_mcp/validation/rules.py`
- `src/giljo_mcp/validation/template_validator.py`

**Key Classes/Functions**:
- `TemplateValidator` - Schema and content validation
- Business rule validators
- Input sanitization rules

**Dependencies**:
- Template models
- Configuration rules
- Exception handling

**Complexity**: **Low**
- Schema validation
- Business rule checks
- Error formatting

---

### 23. Statistics & Monitoring

**Purpose**: System statistics, agent job monitoring, and performance metrics.

**Key Files**:
- `api/endpoints/statistics.py` (652 lines)
- `src/giljo_mcp/monitoring/*.py`
- `src/giljo_mcp/job_monitoring.py`

**Key Classes/Functions**:
- Statistics aggregation endpoints
- Job monitoring and staleness detection
- Performance metrics collection

**Dependencies**:
- All service layers (data aggregation)
- WebSocket events for real-time updates
- Database queries for statistics

**Complexity**: **Medium**
- Data aggregation across entities
- Real-time monitoring
- Staleness detection algorithms
- Performance metrics

---

### 24. Workflow Engine

**Purpose**: Workflow orchestration engine for multi-step agent coordination.

**Key Files**:
- `src/giljo_mcp/workflow_engine.py`

**Key Classes/Functions**:
- `WorkflowEngine` - Workflow state machine
- Step execution and coordination
- Workflow status tracking

**Dependencies**:
- Agent job manager
- Orchestration service
- Task service

**Complexity**: **Medium**
- State machine implementation
- Step dependency management
- Workflow persistence

---

### 25. Exceptions & Enums

**Purpose**: Domain-specific exceptions and enumeration types for type safety.

**Key Files**:
- `src/giljo_mcp/exceptions.py` (46+ exception classes)
- `src/giljo_mcp/enums.py` (13 enum types)

**Key Classes/Functions**:
- Exception hierarchy: `BaseGiljoException` → domain-specific exceptions
- Enums: `AgentRole`, `AgentStatus`, `JobStatus`, `MessageType`, `MessagePriority`, `MessageStatus`, `ProjectStatus`, `ProjectType`, `AugmentationType`, `TemplateCategory`, `ArchiveType`, `InteractionType`, `ContextStatus`
- `create_error_from_exception()` - Error mapping utility

**Dependencies**:
- Used across all backend features
- Exception handling in API endpoints
- Type safety in service layers

**Complexity**: **Low**
- Well-structured exception hierarchy
- Comprehensive enum coverage
- Centralized error handling

---

### 26. System Roles

**Purpose**: Define system-managed agent roles and permissions.

**Key Files**:
- `src/giljo_mcp/system_roles.py`

**Key Classes/Functions**:
- `SYSTEM_MANAGED_ROLES` constant - List of protected roles

**Dependencies**:
- Agent template system
- Template service (role validation)
- User permissions

**Complexity**: **Low**
- Simple role definition
- Permission checking
- Template filtering

---

### 27. Claude Config

**Purpose**: Claude Code configuration management for .claude/agents and project setup.

**Key Files**:
- `src/giljo_mcp/services/claude_config_manager.py` (307 lines)

**Key Classes/Functions**:
- `ClaudeConfigManager` - Manage .claude directory structure
- Agent template synchronization
- Project configuration

**Dependencies**:
- Template service
- File system access
- Product configuration

**Complexity**: **Medium**
- File system synchronization
- Template export to .claude/agents
- Configuration file generation

---

## Summary Statistics

**Total Backend Features**: 27 categories
**Total Service Files**: 14 services (11,274 lines)
**Total Endpoint Files**: 34+ endpoints (~19,820 lines)
**Total Model Files**: 12 entity types (3,098 lines)
**Total Tool Files**: 35 MCP tools
**Total Middleware**: 7 middleware layers

**Largest Components**:
1. ProjectService - 2,563 lines
2. Orchestrator - 1,891 lines
3. ProductService - 1,589 lines
4. UserService - 1,361 lines
5. ThinPromptGenerator - 1,263 lines
6. OrchestrationService - 1,211 lines
7. AgentJobManager - 1,196 lines

**Key Architectural Patterns**:
- Service layer architecture (Handover 0120-0130 refactoring)
- Multi-tenant isolation (per-user tenancy policy Nov 2025)
- WebSocket event-driven updates
- Thin-client prompt generation (85% token reduction)
- HTTP-only MCP (stdio deprecated)
- Cascade deletion with soft delete support
- 2-dimensional context management (Priority × Depth)

**Recent Major Changes** (Nov 2025):
- Handover 0246a-c: Orchestrator workflow pipeline (85% token reduction)
- Handover 0326: Message auto-acknowledge simplification
- Handover 0329: Cascade deletion for project-related tables
- Handover 0120-0130: Backend refactoring (89% complete)
- Context Management v2.0 (0312-0318)
- 360 Memory Management (0135-0139)
- GUI Redesign Series (0243a-f)

---

**End of Backend Feature Catalogue**
