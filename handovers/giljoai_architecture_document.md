# GiljoAI MCP Server - Architecture & Workflow Documentation

## Table of Contents
1. [System Architecture Overview](#system-architecture-overview)
2. [Network Architecture](#network-architecture)
3. [Application Stack](#application-stack)
4. [Installation & Setup Flow](#installation--setup-flow)
5. [Core Workflows](#core-workflows)
6. [Component Interactions](#component-interactions)
7. [Data Flow Patterns](#data-flow-patterns)

---

## 1. System Architecture Overview

### 1.1 High-Level Architecture
```ascii
┌─────────────────────────────────────────────────────────────────┐
│                    GiljoAI MCP Server                           │
│                  (LAN / WAN / Hosted)                           │
├─────────────────────────────────────────────────────────────────┤
│                                                                  │
│  ┌──────────────┐  ┌──────────────┐  ┌──────────────┐        │
│  │   Frontend   │  │   Backend    │  │  PostgreSQL  │        │
│  │   (Web UI)   │◄─►│  (MCP/HTTP)  │◄─►│   Database   │        │
│  └──────────────┘  └──────────────┘  └──────────────┘        │
│         ▲                 ▲                                     │
└─────────┼─────────────────┼─────────────────────────────────────┘
          │                 │
          │    Browser      │    MCP over HTTP
          │                 │
    ┌─────▼──────┐    ┌─────▼──────┐
    │ Developer  │    │   CLI/     │
    │    PC      │    │  Terminal  │
    └────────────┘    └────────────┘
```

### 1.2 Multi-User Architecture
```ascii
                    ┌────────────────────────┐
                    │  GiljoAI MCP Server    │
                    │   (Centralized)        │
                    └──────────┬─────────────┘
                               │
           ┌───────────────────┼───────────────────┐
           │                   │                   │
    ┌──────▼──────┐     ┌──────▼──────┐    ┌──────▼──────┐
    │ Developer 1 │     │ Developer 2 │    │ Developer 3 │
    ├─────────────┤     ├─────────────┤    ├─────────────┤
    │ • Browser   │     │ • Browser   │    │ • Browser   │
    │ • CLI Tools │     │ • CLI Tools │    │ • CLI Tools │
    │ • MCP Client│     │ • MCP Client│    │ • MCP Client│
    └─────────────┘     └─────────────┘    └─────────────┘
```

---

## 2. Network Architecture

### 2.1 Communication Layers
```ascii
┌──────────────────────────────────────────────────────┐
│                    PUBLIC IP                         │
│                 (External Access)                    │
├──────────────────────────────────────────────────────┤
│                                                      │
│  Frontend Port: 7274        API Port: Configurable  │
│                                                      │
├──────────────────────────────────────────────────────┤
│                   LOCALHOST                         │
│              (Internal Communication)               │
│                                                      │
│  Backend ◄──► Frontend ◄──► PostgreSQL              │
│                                                      │
└──────────────────────────────────────────────────────┘
```

### 2.2 Protocol Stack
- **External**: MCP over HTTP (not STDIO)
- **Internal**: REST API + WebSocket
- **Database**: PostgreSQL native protocol
- **Authentication**: API Key / Bearer Token per tenant

---

## 3. Application Stack

### 3.1 Server Components
```ascii
┌────────────────────────────────────────────────────────────┐
│                     PostgreSQL Database                     │
├────────────────────────────────────────────────────────────┤
│                    Tenant Management Layer                  │
│         • User Management    • Admin Controls               │
│         • Single Org Architecture                           │
├────────────────────────────────────────────────────────────┤
│                   MCP Integration Layer                     │
│  • CLI Tool Integration (Claude, Codex, Gemini)            │
│  • Slash Command Setup                                      │
│  • Agent Template Import/Export                             │
├────────────────────────────────────────────────────────────┤
│                  Core Business Logic                        │
│  • Task Management      • Product Management                │
│  • Project Management   • Jobs Management                   │
│  • Context Management   • Priority Assignment               │
├────────────────────────────────────────────────────────────┤
│                 Agent Orchestration Layer                   │
│  • Agent Templates      • Serena MCP Integration            │
│  • Mission Generation   • Job Assignment                    │
│  • Message Center       • Status Tracking                   │
└────────────────────────────────────────────────────────────┘
```

### 3.2 Database Schema (Conceptual)
```ascii
┌─────────────┐     ┌─────────────┐     ┌─────────────┐
│   Tenants   │────►│    Users    │     │   Agents    │
└─────────────┘     └─────────────┘     └─────────────┘
       │                   │                    │
       ▼                   ▼                    ▼
┌─────────────┐     ┌─────────────┐     ┌─────────────┐
│   Products  │────►│   Projects  │────►│    Jobs     │
└─────────────┘     └─────────────┘     └─────────────┘
       │                   │                    │
       ▼                   ▼                    ▼
┌─────────────┐     ┌─────────────┐     ┌─────────────┐
│    Tasks    │     │   Missions  │     │  Messages   │
└─────────────┘     └─────────────┘     └─────────────┘
```

---

## 4. Installation & Setup Flow

### 4.1 Installation Process
```ascii
START
  │
  ▼
┌─────────────────────┐
│ Download from       │
│ GitHub/Website      │
└──────────┬──────────┘
           │
           ▼
┌─────────────────────┐
│ Run: python         │
│ install.py          │
│ (OS Agnostic)       │
└──────────┬──────────┘
           │
           ▼
┌─────────────────────┐     ┌─────────────────────┐
│ Configure IP        │────►│ PostgreSQL Check    │
│ Address Binding     │     │ • Request Creds     │
└─────────────────────┘     │ • Test Connection   │
                            └──────────┬──────────┘
                                       │
                                       ▼
                            ┌─────────────────────┐
                            │ Install             │
                            │ Dependencies        │
                            │ (requirements.txt)  │
                            └──────────┬──────────┘
                                       │
                                       ▼
                            ┌─────────────────────┐
                            │ Database Setup      │
                            │ • Create Tables     │
                            │ • Default Templates │
                            └──────────┬──────────┘
                                       │
                                       ▼
                            ┌─────────────────────┐
                            │ Launch Instructions │
                            │ http://{ip}:7274    │
                            └─────────────────────┘
```

### 4.2 First Run Configuration
```ascii
┌─────────────────┐
│ Browse to       │
│ http://{ip}:7274│
└────────┬────────┘
         │
         ▼
┌─────────────────┐     ┌─────────────────┐     ┌─────────────────┐
│ Setup Admin     │────►│ Create Tenant   │────►│ Welcome Page    │
│ User            │     │ for Admin       │     │                 │
└─────────────────┘     └─────────────────┘     └─────────────────┘
```

---

## 5. Core Workflows

### 5.1 Product-Project-Job Hierarchy
```ascii
┌─────────────────────────────────────────────────┐
│                  PRODUCT                        │
│         (One Active per Tenant)                 │
│  • Vision Document                              │
│  • Tech Stack                                   │
│  • Context Source                               │
└───────────────────┬─────────────────────────────┘
                    │
                    ▼
┌─────────────────────────────────────────────────┐
│                 PROJECT                         │
│       (One Active per Product)                  │
│  • Description                                  │
│  • Mission (Generated)                          │
│  • Context Budget                               │
└───────────────────┬─────────────────────────────┘
                    │
                    ▼
┌─────────────────────────────────────────────────┐
│                   JOB                           │
│        (Multiple per Project)                   │
│  • Assigned Agents                              │
│  • Status Tracking                              │
│  • Message Thread                               │
└──────────────────────────────────────────────────┘
```

### 5.2 Product Workflow State Machine
```ascii
         ┌──────────┐
         │  CREATE  │
         └────┬─────┘
              │
              ▼
         ┌──────────┐
         │ INACTIVE │◄────────────┐
         └────┬─────┘             │
              │                   │
              ▼                   │
         ┌──────────┐             │
    ┌───►│  ACTIVE  │─────────────┤
    │    └────┬─────┘             │
    │         │                   │
    │         ▼                   │
    │    ┌──────────┐             │
    │    │ PROJECTS │             │
    │    │  CREATED │             │
    │    └────┬─────┘             │
    │         │                   │
    └─────────┴───────────────────┘
         (Deactivate)
```

### 5.3 Project Lifecycle
```ascii
┌────────┐     ┌──────────┐     ┌────────┐     ┌──────────┐
│ CREATE │────►│ INACTIVE │────►│ ACTIVE │────►│ STAGING  │
└────────┘     └──────────┘     └────────┘     └────┬─────┘
                    ▲                                 │
                    │                                 ▼
┌──────────┐        │            ┌────────┐     ┌──────────┐
│COMPLETED │◄───────┴────────────│  JOBS  │◄────│ MISSION  │
└──────────┘                     └────────┘     │GENERATED │
                                                 └──────────┘
```

### 5.4 Task Management Flow
```ascii
┌─────────────┐
│ Create Task │
└──────┬──────┘
       │
       ▼
┌─────────────────────────┐
│ Task Properties:        │
│ • Name                  │
│ • Status                │
│ • Priority              │
│ • Description           │
└──────┬──────────────────┘
       │
       ▼
┌─────────────────────────┐     ┌──────────────┐
│ NULL Tagged             │────►│ Show in All  │
│ (No Active Product)     │     │ Products     │
└─────────────────────────┘     └──────────────┘
       │
       ▼
┌─────────────────────────┐     ┌──────────────┐
│ Product Tagged          │────►│ Convert to   │
│ (Active Product Exists) │     │ Project      │
└─────────────────────────┘     └──────────────┘
```

---

## 6. Component Interactions

### 6.1 MCP Integration Setup
```ascii
┌──────────────┐     ┌──────────────┐     ┌──────────────┐
│ User Settings│────►│ MCP Setup    │────►│ Generate     │
│              │     │              │     │ Auth Prompt  │
└──────────────┘     └──────────────┘     └──────┬───────┘
                                                  │
                          ┌───────────────────────┼───────────────────────┐
                          │                       │                       │
                    ┌─────▼─────┐          ┌─────▼─────┐          ┌──────▼──────┐
                    │Claude Code│          │   Codex   │          │   Gemini    │
                    │    CLI    │          │    CLI    │          │     CLI     │
                    │ (API Key) │          │(Bearer Key)│         │ (API Key)   │
                    └───────────┘          └───────────┘          └─────────────┘
```

### 6.2 Agent Management System
```ascii
┌─────────────────────────────────────────────────┐
│            Agent Template Manager               │
├─────────────────────────────────────────────────┤
│                                                 │
│  ┌──────────┐  ┌──────────┐  ┌──────────┐    │
│  │Orchestrator│ │ Backend  │  │ Frontend │    │
│  │(Protected)│ │  Agent   │  │  Agent   │    │
│  └──────────┘  └──────────┘  └──────────┘    │
│                                                 │
│  ┌──────────┐  ┌──────────┐  ┌──────────┐    │
│  │  Tester  │  │ Analyzer │  │  DevOps  │    │
│  │  Agent   │  │  Agent   │  │  Agent   │    │
│  └──────────┘  └──────────┘  └──────────┘    │
│                                                 │
│  Rules:                                        │
│  • Max 8 agent types active                    │
│  • Unlimited instances per type                │
│  • Templates unique per tenant                 │
└─────────────────────────────────────────────────┘
```

### 6.3 Job Staging Process
```ascii
┌──────────────┐
│Project Active│
└──────┬───────┘
       │
       ▼
┌──────────────────────────────┐
│ Launch Panel                 │
│ ┌──────────┬──────────────┐ │
│ │Orchestra │Mission Window │ │
│ │   Card   │   (Empty)     │ │
│ └──────────┴──────────────┘ │
└──────────┬───────────────────┘
           │ [Stage Project]
           ▼
┌──────────────────────────────┐
│ Generate System Prompt       │
│ • Product Context            │
│ • Project Description        │
│ • Available Agents           │
│ • Serena MCP Config          │
└──────────┬───────────────────┘
           │ Copy & Paste
           ▼
┌──────────────────────────────┐
│ Orchestrator Execution       │
│ • Creates Mission            │
│ • Selects Agents             │
│ • Assigns Jobs               │
└──────────┬───────────────────┘
           │ Updates via MCP
           ▼
┌──────────────────────────────┐
│ UI Updates                   │
│ • Mission Displayed          │
│ • Agent Cards Shown          │
│ • [Launch Jobs] Enabled      │
└──────────────────────────────┘
```

### 6.4 Job Implementation Modes
```ascii
                    ┌─────────────────┐
                    │ [Launch Jobs]   │
                    └────────┬────────┘
                             │
                ┌────────────▼────────────┐
                │   Implementation Mode   │
                └────────────┬────────────┘
                             │
           ┌─────────────────┴─────────────────┐
           │                                   │
    ┌──────▼──────┐                   ┌───────▼───────┐
    │Claude Code  │                   │  Legacy CLI   │
    │    Mode     │                   │     Mode      │
    └──────┬──────┘                   └───────┬───────┘
           │                                   │
    ┌──────▼──────────────┐          ┌────────▼────────────┐
    │Single Terminal      │          │Multiple Terminals   │
    │• Orchestrator runs  │          │• Individual prompts │
    │• Uses subagents     │          │• Per-agent windows  │
    └─────────────────────┘          └─────────────────────┘
```

---

## 7. Data Flow Patterns

### 7.1 Context Hierarchy
```ascii
┌─────────────────────────────────────┐
│         CONTEXT SOURCES             │
├─────────────────────────────────────┤
│ Priority 1: Product Vision          │
│ Priority 2: Tech Stack              │
│ Priority 3: Project Description     │
│ Priority 4: Active Mission          │
│ Priority 5: Agent Templates         │
│ Priority 6: Previous Messages       │
└─────────────────────────────────────┘
                 │
                 ▼
    ┌────────────────────────┐
    │  Context Budget (2000) │
    │      Tokens Max        │
    └────────────────────────┘
```

### 7.2 Message Flow Architecture
```ascii
┌────────────┐     ┌────────────┐     ┌────────────┐
│   Agent    │────►│ MCP Server │────►│  Message   │
│ (Terminal) │     │            │     │   Center   │
└────────────┘     └────────────┘     └────────────┘
                          │                   │
                          ▼                   ▼
                   ┌────────────┐      ┌────────────┐
                   │  Database  │      │ Developer  │
                   │   (Audit)  │      │    View    │
                   └────────────┘      └────────────┘
```

### 7.3 Status Progression
```ascii
Agent Status Flow:
┌──────┐     ┌──────┐     ┌──────────┐     ┌──────────┐
│ IDLE │────►│ACTIVE│────►│PROCESSING│────►│COMPLETED │
└──────┘     └──────┘     └──────────┘     └──────────┘
                │                │                │
                ▼                ▼                ▼
           ┌──────┐        ┌──────┐        ┌──────────┐
           │ERROR │        │BLOCKED│        │REACTIVATE│
           └──────┘        └──────┘        └──────────┘
```

---

## 8. Security & Isolation

### 8.1 Multi-Tenant Isolation
```ascii
┌─────────────────────────────────────────┐
│           Tenant Boundary               │
├─────────────────────────────────────────┤
│  • Unique API/Bearer Keys               │
│  • Isolated Data Spaces                 │
│  • Separate Agent Templates             │
│  • Independent Products/Projects        │
│  • Isolated Message Threads             │
└─────────────────────────────────────────┘
```

### 8.2 Authentication Flow
```ascii
┌──────────┐     ┌──────────┐     ┌──────────┐
│   User   │────►│   Login  │────►│  Tenant  │
│          │     │          │     │   Check  │
└──────────┘     └──────────┘     └────┬─────┘
                                        │
                                        ▼
                              ┌──────────────────┐
                              │ Generate Session │
                              │ • Cookie Domain  │
                              │ • API Key        │
                              └──────────────────┘
```

---

## 9. Admin Configuration

### 9.1 Admin Settings Structure
```ascii
┌────────────────────────────────────────────┐
│              ADMIN SETTINGS                │
├────────────────────────────────────────────┤
│                                            │
│ ┌─────────┐ ┌──────────┐ ┌─────────────┐ │
│ │Network  │ │Database  │ │Integrations │ │
│ │• Host IP│ │• Host    │ │• List       │ │
│ │• Ports  │ │• Port    │ │• Config     │ │
│ │• CORS   │ │• Creds   │ │• Docs       │ │
│ └─────────┘ └──────────┘ └─────────────┘ │
│                                            │
│ ┌─────────┐ ┌──────────────────────────┐ │
│ │Security │ │    System                │ │
│ │• Cookie │ │• Orchestrator Template  │ │
│ │• Domain │ │• User Management        │ │
│ └─────────┘ └──────────────────────────┘ │
└────────────────────────────────────────────┘
```

---

## 10. Key Implementation Notes

### For Agentic Coding Tools

1. **Database Requirements**
   - PostgreSQL is mandatory
   - JSONB support required for message storage
   - Proper indexing on tenant_key for isolation

2. **Network Configuration**
   - Frontend Port: 7274 (default)
   - API Port: Configurable
   - MCP over HTTP (not STDIO)
   - CORS must be properly configured

3. **Agent Limits**
   - Maximum 8 agent types active simultaneously
   - Unlimited instances of each type
   - Orchestrator agent is protected (admin-only edit)

4. **Context Management**
   - 2000 token budget for context
   - Priority-based inclusion
   - User-configurable priority order

5. **State Management**
   - Only one product active per tenant
   - Only one project active per product
   - Projects retain all data when deactivated

6. **Message System**
   - Auditable message trails
   - Broadcast capability to all agents
   - Individual agent messaging
   - MCP-based communication

7. **CLI Integration**
   - Supports Claude Code CLI, Codex CLI, Gemini CLI
   - Slash commands via downloadable ZIP
   - Agent templates exportable to CLI tools

8. **Workflow Constraints**
   - Tasks must have active product to convert to projects
   - Projects must be staged before launching jobs
   - Orchestrator must complete mission before job launch

---

## 11. API Endpoints Summary

### Core Endpoints (Inferred from Workflow)
```
Authentication:
  POST   /api/auth/login
  POST   /api/auth/logout
  GET    /api/auth/verify

Products:
  GET    /api/products
  POST   /api/products
  PUT    /api/products/{id}
  DELETE /api/products/{id}
  POST   /api/products/{id}/activate

Projects:
  GET    /api/projects
  POST   /api/projects
  PUT    /api/projects/{id}
  DELETE /api/projects/{id}
  POST   /api/projects/{id}/activate
  POST   /api/projects/{id}/stage

Jobs:
  GET    /api/jobs
  POST   /api/jobs
  GET    /api/jobs/{id}
  PUT    /api/jobs/{id}/status

Agents:
  GET    /api/agents
  POST   /api/agents
  PUT    /api/agents/{id}
  GET    /api/agents/templates

Messages:
  GET    /api/messages/job/{job_id}
  POST   /api/messages
  POST   /api/messages/broadcast

Tasks:
  GET    /api/tasks
  POST   /api/tasks
  PUT    /api/tasks/{id}
  POST   /api/tasks/{id}/convert
```

---

## 12. Development Guidelines

### For Implementation Teams

1. **Frontend Development**
   - Vue.js framework (implied from TAB references)
   - Responsive design for developer workflow
   - Real-time updates via WebSocket

2. **Backend Development**
   - Python-based (from install.py reference)
   - RESTful API design
   - MCP protocol implementation
   - Multi-tenant architecture

3. **Database Design**
   - PostgreSQL with proper normalization
   - Tenant isolation at query level
   - Audit trail for all operations
   - Soft delete with expiry (10 days)

4. **Security Considerations**
   - API key/Bearer token per tenant
   - CORS configuration for external access
   - Cookie domain whitelisting
   - Admin role separation

---

## Appendix A: State Definitions

### Product States
- **INACTIVE**: Created but not in use
- **ACTIVE**: Currently selected for work
- **ARCHIVED**: Soft deleted (10-day expiry)

### Project States
- **INACTIVE**: Created but not active
- **ACTIVE**: Currently being worked on
- **STAGING**: Mission being generated
- **RUNNING**: Jobs in progress
- **COMPLETED**: All jobs finished
- **CANCELLED**: Stopped before completion

### Job States
- **PENDING**: Created but not started
- **ACTIVE**: Currently being processed
- **BLOCKED**: Waiting for dependency
- **COMPLETED**: Successfully finished
- **FAILED**: Terminated with error

### Agent States
- **AVAILABLE**: Can be assigned
- **ASSIGNED**: Allocated to job
- **WORKING**: Actively processing
- **IDLE**: Waiting for input
- **COMPLETED**: Finished task
- **ERROR**: Failed state

---

## Appendix B: Integration Points

### CLI Tool Integration
```
Claude Code CLI:
  - API Key authentication
  - Subagent system support
  - Single terminal mode

Codex CLI:
  - Bearer token authentication
  - Individual agent terminals
  - Legacy mode support

Gemini CLI:
  - API Key authentication
  - Individual agent terminals
  - Legacy mode support
```

### Serena MCP Integration
```
Configuration:
  - Enable/Disable toggle
  - Prompt modification
  - Tool catalog management
  - Range reading preferences
  - Context halo settings
```

---

## Appendix C: Troubleshooting Paths

### Common Issues and Resolution
```
Installation Issues:
  └─> Check PostgreSQL connection
  └─> Verify Python dependencies
  └─> Confirm network ports available

Authentication Issues:
  └─> Verify API/Bearer key
  └─> Check tenant configuration
  └─> Confirm CORS settings

Agent Issues:
  └─> Check template activation
  └─> Verify MCP connection
  └─> Confirm agent limits (max 8 types)

Job Issues:
  └─> Ensure project is active
  └─> Verify mission generation
  └─> Check agent assignments
```

---

*This document provides a comprehensive technical overview of the GiljoAI MCP Server architecture and workflows, structured for easy consumption by agentic coding tools and development teams.*