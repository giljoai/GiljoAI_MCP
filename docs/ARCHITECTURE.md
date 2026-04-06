# GiljoAI MCP: Architecture

This document describes the technical architecture of GiljoAI MCP for developers
working on or integrating with the platform.

---

## Tech Stack

| Layer | Technology | Version |
|---|---|---|
| API server | FastAPI | >= 0.100.0 |
| ASGI runtime | Uvicorn | >= 0.23.0 |
| Data validation | Pydantic | >= 2.0.0 |
| ORM | SQLAlchemy | >= 2.0.0 |
| Migrations | Alembic | >= 1.12.0 |
| Database | PostgreSQL | 14 minimum, 18 recommended |
| Async DB driver | asyncpg | >= 0.29.0 |
| Frontend framework | Vue 3 | >= 3.4.0 |
| UI component library | Vuetify | >= 3.4.0 |
| Frontend build tool | Vite | >= 7.1.8 |
| State management | Pinia | >= 3.0.3 |
| Python runtime | Python | 3.12+ recommended |

---

## System Overview

```
AI Coding Tool (Claude Code / Codex CLI / Gemini CLI)
        |
        | MCP over HTTP/SSE
        v
   FastAPI Server (api/endpoints/mcp_sdk_server.py)
        |
        | Python function calls
        v
   Service Layer (src/giljo_mcp/services/)
        |
        | SQLAlchemy ORM
        v
   PostgreSQL 18
        |
        | NOTIFY/LISTEN
        v
   WebSocket Broker (api/broker/postgres_notify.py)
        |
        | WebSocket
        v
   Vue 3 Frontend (browser)
```

**AI coding tool:** Claude Code, Codex CLI, Gemini CLI, or any MCP-compatible client.
Connects to the MCP endpoint using an API key. Sends tool calls over HTTP/SSE.

**FastAPI server:** Handles all HTTP traffic. Exposes MCP tool endpoints, REST API
routes for the dashboard, WebSocket connections, and authentication endpoints.
Routes are registered in `api/app.py` via `include_router` calls.

**Service layer:** Contains all business logic. Services are called by endpoints and
call repositories for data access. No endpoint writes to the database directly.

**PostgreSQL:** Single source of truth. All tables include a `tenant_key` column.
The database also drives real-time push via `pg_notify`.

**WebSocket broker:** Listens on a PostgreSQL channel using `LISTEN`. When the server
calls `pg_notify`, the broker receives the payload and forwards it to all connected
WebSocket clients in the matching tenant. This keeps the Vue frontend in sync with
agent state changes without polling.

**Vue 3 frontend:** Single-page application served by the FastAPI server. Connects
to the WebSocket endpoint on load. Pinia stores receive WebSocket events and update
reactive state.

---

## Backend Layer

### Endpoints

Source: `api/endpoints/`

Each file in this directory corresponds to a domain area. Examples include:

- `mcp_sdk_server.py`: MCP tool definitions served over HTTP/SSE. All 29 public MCP
  tools are defined here. This is the primary integration point for AI coding tools.
- `projects.py`, `products.py`, `agent_jobs.py`, `messages.py`, `tasks.py`: REST
  endpoints for the dashboard frontend.
- `auth.py`, `auth_pin_recovery.py`, `oauth.py`: Authentication and session management.
- `users.py`, `user_settings.py`, `settings.py`: User and configuration management.
- `configuration.py`, `system_prompts.py`, `templates.py`: Context configuration.
- `statistics.py`: Usage and performance metrics.

SaaS-only endpoints live in `api/saas_endpoints/` and are never imported by CE code.

Middleware is registered in `api/app.py` in this order (outermost to innermost):
CORS, security headers, input validation, API metrics, rate limiting, auth, CSRF.

### Services

Source: `src/giljo_mcp/services/`

Services contain all business logic. Each service class takes a database session
(or session factory) as a dependency. Services raise exceptions on error; they never
return error dicts. Key services include:

- `project_lifecycle_service.py`: Project state transitions (staging, active,
  inactive, cancelled, closeout).
- `orchestration_service.py`, `mission_orchestration_service.py`: Agent coordination.
- `product_service.py`, `product_lifecycle_service.py`: Product CRUD and activation.
- `message_service.py`, `message_routing_service.py`: Message storage and routing.
- `task_service.py`: Task CRUD and status tracking.
- `auth_service.py`, `user_auth_service.py`: Authentication and credential management.
- `settings_service.py`, `config_service.py`: System and user configuration.
- `job_lifecycle_service.py`, `agent_job_manager.py`: Agent job state management.
- `project_closeout_service.py`, `project_summary_service.py`: Closeout and memory.

### Repositories

Source: `src/giljo_mcp/repositories/`

Repositories handle all direct database queries. Services call repositories; endpoints
do not call repositories directly. Every repository query filters by `tenant_key`.

- `agent_job_repository.py`: Agent job and execution records.
- `message_repository.py`: Project messages and conversation history.
- `context_repository.py`: Context assembly for prompt generation.
- `statistics_repository.py`, `job_statistics_repository.py`: Usage metrics.
- `vision_document_repository.py`: Vision document storage.
- `configuration_repository.py`: System and product configuration.
- `base.py`: Shared base repository with common query helpers.

### Models

Source: `src/giljo_mcp/models/`

SQLAlchemy ORM models using `DeclarativeBase`. Every table that stores user data
includes a `tenant_key` column with a database index. Multi-tenant isolation is
enforced at the model level via column constraints and at the service level via
mandatory filter arguments.

Key model files:

- `auth.py`: `User`, `APIKey`, `MCPSession`. Users have a `role` field with values
  `admin`, `developer`, or `viewer`.
- `products.py`: `Product`, `ProductTechStack`, `ProductArchitecture`,
  `ProductTestConfig`, `VisionDocument`, `VisionDocumentSummary`.
- `projects.py`: `Project`, `ProjectType`.
- `agent_identity.py`: `AgentJob`, `AgentExecution`, `AgentTodoItem`.
- `tasks.py`: `Task`.
- `organizations.py`: Organization and membership (used in both CE and SaaS).
- `config.py`, `settings.py`, `templates.py`, `context.py`: Supporting data.

---

## Frontend Layer

### Views

Source: `frontend/src/views/`

Each view corresponds to a top-level page in the application:

- `DashboardView.vue`: Home dashboard with activity summary.
- `ProductsView.vue`, `ProductDetailView.vue`: Product list and detail editor.
- `ProjectsView.vue`, `ProjectLaunchView.vue`: Project board and launch workflow.
- `MessagesView.vue`: Agent message log.
- `TasksView.vue`: Task board.
- `McpIntegration.vue`: MCP connection setup and API key management.
- `SystemSettings.vue`, `UserSettings.vue`, `OrganizationSettings.vue`: Settings pages.
- `Users.vue`: User management (admin only).
- `Login.vue`, `CreateAdminAccount.vue`, `WelcomeView.vue`: Authentication and onboarding.

### Components

Source: `frontend/src/components/`

Reusable UI components. Components are organized by domain. They receive props and
emit events; they do not call APIs directly. API calls go through composables or
Pinia store actions.

### Composables and Stores

Source: `frontend/src/composables/`, `frontend/src/stores/`

Composables encapsulate reusable logic and follow the `use*` naming convention.
Examples:

- `useProjectMessages.js`: Message loading and pagination.
- `useProjectCloseout.js`: Closeout workflow state.
- `useProductActivation.js`: Product activation flow.
- `useWebSocket.js`: WebSocket connection lifecycle.
- `useTaskCrud.js`, `useTaskFilters.js`: Task board operations.
- `useTemplateData.js`: Agent template loading.
- `useStalenessMonitor.js`: Detects when displayed data may be stale.

Pinia stores manage global state:

- `agentJobsStore.js`: Agent job state for the Jobs page.
- `projects.js`: Project list and active project.
- `products.js`: Product list and active product.
- `messages.js`, `projectMessagesStore.js`: Message data.
- `tasks.js`: Task board data.
- `websocket.js`, `websocketEventRouter.js`: WebSocket connection and event routing.
- `notifications.js`: Toast notification queue.
- `user.js`, `orgStore.js`, `settings.js`, `systemStore.js`: Auth and configuration.

---

## Real-Time Communication

GiljoAI uses PostgreSQL `NOTIFY/LISTEN` combined with WebSockets to push updates to
the browser without polling.

**Write path:** When a service modifies state (agent status change, new message,
task update), it calls `pg_notify` with a JSON payload on a named channel.

**Broker:** `api/broker/postgres_notify.py` contains
`PostgresNotifyWebSocketEventBroker`. It holds a persistent asyncpg connection and
issues `LISTEN` on startup. When a notification arrives, the broker extracts the
tenant from the payload and calls `WebSocketManager.broadcast_event_to_tenant`.

**WebSocket manager:** `api/websocket.py` tracks active WebSocket connections keyed
by `client_id`. `broadcast_event_to_tenant` filters to connections belonging to the
target tenant and sends the JSON payload.

**Frontend:** `frontend/src/composables/useWebSocket.js` manages the client
connection. `frontend/src/stores/websocketEventRouter.js` receives events and routes
them to the appropriate Pinia store action.

This design supports multi-worker deployments: any worker can call `pg_notify` and
all connected clients receive the update regardless of which worker they are
connected to.

---

## Authentication

GiljoAI uses two authentication paths depending on the client type.

**Browser sessions:** Login via `POST /api/auth/login`. On success the server sets
an `access_token` httpOnly cookie containing a signed JWT. The browser cannot read
this cookie via JavaScript, which prevents XSS token theft. A separate `csrf_token`
cookie (not httpOnly) is set simultaneously. State-mutating requests must include
the CSRF token value in the `X-CSRF-Token` request header. The server validates that
the header value matches the cookie value (double-submit pattern).

**MCP clients:** AI coding tools authenticate using an API key passed as a query
parameter or Authorization header. API keys are stored hashed in the `api_keys`
table. Each key is scoped to a single user and inherits that user's `tenant_key`.

**Session context:** `MCPSession` records (table: `mcp_sessions`) persist
`tenant_key` and `project_id` across tool calls within a session. This allows the
MCP server to assemble context without the client re-sending project identifiers on
every call.

**Authorization:** Users have a `role` field with three values: `admin`, `developer`,
`viewer`. Admin-only endpoints check the role at the dependency level using FastAPI
dependencies in `api/dependencies.py`.

---

## Multi-Tenant Isolation

Every table that stores user data has a `tenant_key` column of type `VARCHAR(36)`.
Database indexes exist on every `tenant_key` column.

Isolation is enforced at three levels:

1. **Model level:** `tenant_key` has a `NOT NULL` constraint and an index on every
   relevant table.
2. **Repository level:** Every repository query includes a `WHERE tenant_key = ?`
   filter. The base repository in `src/giljo_mcp/repositories/base.py` provides
   shared helpers that enforce this.
3. **Service level:** `TenantManager` (`src/giljo_mcp/tenant.py`) validates and
   resolves tenant context before service operations run.

CE uses `tenant_key` as the isolation unit. SaaS adds Organization-level grouping
on top of this foundation.

---

## Agent Lifecycle

### Project Phases

A project moves through three phases during its lifetime:

1. **Staging:** The project is queued for activation. The platform generates a
   staging prompt. The user pastes this into their AI coding tool to start the
   orchestrator.
2. **Implementation (active):** The orchestrator and subagents are running. Agent
   jobs update their status in real time. Messages and task updates stream to the
   dashboard.
3. **Closeout:** The orchestrator signals completion. GiljoAI writes a 360 Memory
   entry from the session summary and marks the project closed. The next project
   inherits this accumulated context.

Project statuses: `staging`, `active`, `inactive`, `cancelled`.

### Agent Job Statuses

Each agent execution (`AgentExecution` record) has one of these statuses:

| Status | Meaning |
|---|---|
| `waiting` | Spawned but not yet started |
| `working` | Actively processing a task |
| `blocked` | Waiting on another agent or user input |
| `idle` | Between tasks, ready for work |
| `sleeping` | Paused (rate limit or explicit wait) |
| `complete` | Finished successfully |
| `silent` | No updates received within silence threshold |
| `decommissioned` | Permanently shut down |

The `phase` column on `AgentJob` controls multi-terminal ordering. Jobs in phase 1
run first; jobs with the same phase number run in parallel.

---

## Edition Isolation

GiljoAI ships two editions from one repository:

- **Community Edition (CE):** Standard directories. Public.
- **SaaS Edition:** CE plus code in `saas/`, `saas_endpoints/`, `saas_middleware/`,
  and `frontend/src/saas/`. Private.

CE code never imports from any SaaS directory. SaaS extends CE via EventBus
subscriptions and conditional router registration. If all SaaS directories were
removed, CE must start, serve requests, and pass all tests without modification.

See `docs/EDITION_ISOLATION_GUIDE.md` for the full placement decision tree,
directory rules, and the SaaS extension pattern.
