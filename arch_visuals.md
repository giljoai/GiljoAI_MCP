# GiljoAI MCP — Architecture Visual Guide

Use this document to generate diagrams with any LLM or diagramming tool.

---

## 1. Three-Layer Architecture (The Rule)

```
┌─────────────────────────────────────────────────┐
│  ENDPOINTS (api/endpoints/)                     │
│  Thin HTTP adapters — parse request, call       │
│  service, return response. No DB access.        │
└──────────────────────┬──────────────────────────┘
                       │ calls
                       ▼
┌─────────────────────────────────────────────────┐
│  SERVICES (src/giljo_mcp/services/)             │
│  Business logic — validation, orchestration,    │
│  tenant checks, field allowlists. No DB access. │
└──────────────────────┬──────────────────────────┘
                       │ calls
                       ▼
┌─────────────────────────────────────────────────┐
│  REPOSITORIES (src/giljo_mcp/repositories/)     │
│  ALL database access lives here. Every query    │
│  filters by tenant_key. session.execute,        │
│  session.commit, session.add — ONLY here.       │
└──────────────────────┬──────────────────────────┘
                       │ reads/writes
                       ▼
┌─────────────────────────────────────────────────┐
│  MODELS (src/giljo_mcp/models/)                 │
│  SQLAlchemy ORM definitions. tenant_key NOT     │
│  NULL + indexed on every user data table.       │
└─────────────────────────────────────────────────┘
```

**MCP Tools** (`src/giljo_mcp/tools/`) sit beside endpoints — they call services, never repositories or DB directly.

---

## 2. Request Flow (API → DB → Response)

```
User Browser                    Agent (Claude/Codex/Gemini)
     │                                    │
     │ REST API                           │ MCP over HTTP/SSE
     ▼                                    ▼
┌──────────┐                    ┌──────────────────┐
│ Endpoint │                    │ MCP SDK Server   │
│ (FastAPI │                    │ (mcp_sdk_server) │
│  route)  │                    │                  │
└────┬─────┘                    └────────┬─────────┘
     │                                   │
     │  Both call the SAME services      │
     └──────────────┬────────────────────┘
                    ▼
          ┌──────────────────┐
          │    Service       │
          │  (business logic,│
          │   validation,    │
          │   tenant check)  │
          └────────┬─────────┘
                   ▼
          ┌──────────────────┐
          │   Repository     │
          │ (tenant_key in   │
          │  every WHERE)    │
          └────────┬─────────┘
                   ▼
          ┌──────────────────┐
          │   PostgreSQL     │
          │  (tenant_key     │
          │   indexed)       │
          └──────────────────┘
```

---

## 3. Entity Hierarchy (Data Model)

```
Organization (tenant boundary)
  └── User (belongs to org via OrgMembership)
        └── Product (user's AI project portfolio)
              ├── Project (a unit of work)
              │     ├── AgentJob (work order for one agent)
              │     │     └── AgentExecution (running instance)
              │     ├── Message (inter-agent communication)
              │     └── 360 Memory Entry (project closeout record)
              └── Task (technical debt / TODO items)
```

Every entity has `tenant_key` — data never leaks between tenants.

---

## 4. Agent Orchestration Flow

```
User creates Project
        │
        ▼
┌─────────────────┐
│  STAGING PHASE   │  Orchestrator reads context, plans, spawns agents
│  (Opus model)    │
└────────┬────────┘
         │ spawn_job() for each agent
         ▼
┌─────────────────┐     ┌─────────────────┐
│  Implementer A  │     │  Implementer B  │  Parallel execution
│  (Sonnet model) │     │  (Sonnet model) │
└────────┬────────┘     └────────┬────────┘
         │ complete_job()        │ complete_job()
         └──────────┬────────────┘
                    ▼
         ┌─────────────────┐
         │  IMPLEMENTATION  │  Orchestrator spawns tester/reviewer
         │  PHASE           │  from real agent results
         └────────┬────────┘
                  │
         ┌────────┴────────┐
         ▼                 ▼
┌──────────────┐  ┌──────────────┐
│   Tester     │  │   Reviewer   │
│  (Sonnet)    │  │  (Sonnet)    │
└──────┬───────┘  └──────┬───────┘
       │ PASS             │ PASS
       └────────┬─────────┘
                ▼
       ┌─────────────────┐
       │  CLOSEOUT PHASE  │  Write 360 memory, close project
       │  (HITL gate)     │  User approves before final close
       └─────────────────┘
```

---

## 5. Edition Isolation (CE / SaaS / Demo)

```
┌─────────────────────────────────────────────────────┐
│                   ONE CODEBASE                       │
│                                                      │
│  ┌─────────────────────────────────────────────┐    │
│  │  CE (Community Edition)                      │    │
│  │  Everything outside saas/ and demo/ dirs     │    │
│  │  Always loaded. Must work standalone.        │    │
│  │                                              │    │
│  │  ┌────────────────────┐                      │    │
│  │  │  SaaS Extension    │ ◄── only loads when  │    │
│  │  │  saas/             │     GILJO_MODE=saas   │    │
│  │  │  saas_endpoints/   │     AND dir exists    │    │
│  │  │  saas_middleware/  │                       │    │
│  │  └────────────────────┘                      │    │
│  │                                              │    │
│  │  ┌────────────────────┐                      │    │
│  │  │  Demo Config       │ ◄── GILJO_MODE=demo  │    │
│  │  │  demo/             │     reuses SaaS infra │    │
│  │  └────────────────────┘                      │    │
│  │                                              │    │
│  └─────────────────────────────────────────────┘    │
│                                                      │
│  DELETION TEST: Delete saas/ + demo/ → CE still runs │
└─────────────────────────────────────────────────────┘
```

---

## 6. Write Discipline (Data Protection)

```
Agent Input (untrusted)
        │
        ▼
┌──────────────────────────┐
│  MCP Tool                │  Type-check, length-cap,
│  (input validation)      │  enum-validate
└──────────┬───────────────┘
           ▼
┌──────────────────────────┐
│  Service                 │  Field allowlist (frozenset)
│  (business rules)        │  JSONB validator (Pydantic)
│                          │  tenant_key enforcement
└──────────┬───────────────┘
           ▼
┌──────────────────────────┐
│  Repository              │  tenant_key in WHERE clause
│  (single write path)     │  session.commit here ONLY
└──────────┬───────────────┘
           ▼
┌──────────────────────────┐
│  PostgreSQL              │  NOT NULL constraints
│  (last line of defense)  │  Unique indexes
└──────────────────────────┘

No shortcuts. No parallel paths. Every write goes through all 4 layers.
```

---

## 7. Two-Repo Delivery Pipeline

```
GiljoAI_MCP_Private (this repo)
│  Contains: CE + SaaS + Demo + Handovers
│
├── git push origin master
│
├── export_ce_dev.sh --push ──► GiljoAI_MCP (public)
│   Strips: saas/, demo/, handovers/         branch: dev/v1.1.7
│   Adds: license headers                    (test server pulls this)
│
└── merge_to_public.sh ──────► GiljoAI_MCP (public)
    Full preflight: lint + pytest + vitest    branch: master
    PR → CI → squash merge                   (release tagged here)
```
