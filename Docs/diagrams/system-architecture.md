# GiljoAI MCP System Architecture

## Overview
This document provides visual representations of the GiljoAI MCP Coding Orchestrator architecture using Mermaid diagrams. The diagrams use the color themes defined in `docs/color_themes.md`.

## System Architecture Diagram

```mermaid
graph TB
    %% Define styles matching color themes
    classDef primary fill:#ffc300,stroke:#0e1c2d,stroke-width:3px,color:#0e1c2d
    classDef secondary fill:#315074,stroke:#e1e1e1,stroke-width:2px,color:#e1e1e1
    classDef surface fill:#1e3147,stroke:#315074,stroke-width:2px,color:#e1e1e1
    classDef success fill:#67bd6d,stroke:#0e1c2d,stroke-width:2px,color:#0e1c2d
    classDef special fill:#8b5cf6,stroke:#e1e1e1,stroke-width:2px,color:#e1e1e1
    classDef danger fill:#c6298c,stroke:#e1e1e1,stroke-width:2px,color:#e1e1e1

    %% User Interface Layer
    subgraph UI["🖥️ User Interface Layer"]
        CLI["Command Line Interface<br/>- Claude Code Integration<br/>- Terminal Commands"]:::primary
        VUE["Vue 3 Dashboard<br/>- Vuetify 3 UI<br/>- Real-time Updates"]:::primary
        API_CLIENT["API Client<br/>- REST/WebSocket<br/>- Auth Handling"]:::primary
    end

    %% API Gateway
    subgraph GATEWAY["🔌 API Gateway"]
        MCP["MCP Protocol Server<br/>- Tool Registration<br/>- Message Routing"]:::special
        REST["REST API<br/>- FastAPI Framework<br/>- OAuth/API Keys"]:::secondary
        WS["WebSocket Server<br/>- Real-time Events<br/>- Bidirectional Comm"]:::secondary
    end

    %% Orchestration Core
    subgraph ORCHESTRATOR["🎯 Orchestration Engine"]
        PM["Project Manager<br/>- Multi-tenant Isolation<br/>- Context Management"]:::success
        AS["Agent Spawner<br/>- Lifecycle Management<br/>- Resource Allocation"]:::success
        MR["Message Router<br/>- Queue Management<br/>- Priority Handling"]:::success
        TM["Template Manager<br/>- Mission Templates<br/>- Dynamic Loading"]:::success
    end

    %% Agent Layer
    subgraph AGENTS["🤖 Agent Pool"]
        ORCH_AGENT["Orchestrator Agent<br/>- Project Planning<br/>- Coordination"]:::special
        WORKER1["Worker Agents<br/>- Code Analysis<br/>- Implementation"]:::secondary
        WORKER2["Specialist Agents<br/>- Testing<br/>- Documentation"]:::secondary
        SERENA["Serena MCP<br/>- AI Guidance<br/>- Code Analysis"]:::special
    end

    %% Data Layer
    subgraph DATA["💾 Data Layer"]
        ORM["SQLAlchemy ORM<br/>- Async Support<br/>- Migration Tools"]:::surface
        SQLITE["SQLite<br/>Local Development<br/>Zero Config"]:::secondary
        POSTGRES["PostgreSQL<br/>Production Ready<br/>Multi-tenant"]:::success
        REDIS["Redis Cache<br/>Session Store<br/>Message Buffer"]:::secondary
    end

    %% File System
    subgraph FILES["📁 File System"]
        VISION["Vision Documents<br/>50K+ Token Support<br/>Chunked Storage"]:::surface
        MEMORY["Session Memory<br/>Agent History<br/>Decision Logs"]:::surface
        CODE["Codebase<br/>Project Files<br/>Templates"]:::surface
    end

    %% External Services
    subgraph EXTERNAL["🌐 External Services"]
        CLAUDE["Claude API<br/>LLM Processing<br/>Code Generation"]:::primary
        GIT["Git Integration<br/>Version Control<br/>Commit Management"]:::secondary
        DOCKER["Docker Registry<br/>Container Images<br/>Deployment"]:::secondary
    end

    %% Connections
    CLI --> MCP
    VUE --> REST
    VUE --> WS
    API_CLIENT --> GATEWAY

    MCP --> PM
    REST --> PM
    WS --> MR

    PM --> AS
    PM --> MR
    PM --> TM
    AS --> AGENTS
    MR --> AGENTS

    ORCH_AGENT --> WORKER1
    ORCH_AGENT --> WORKER2
    WORKER1 --> SERENA
    WORKER2 --> SERENA

    PM --> ORM
    AS --> ORM
    MR --> ORM
    TM --> ORM

    ORM --> SQLITE
    ORM --> POSTGRES
    MR --> REDIS

    AGENTS --> FILES
    PM --> VISION
    AS --> MEMORY
    WORKER1 --> CODE

    WORKER1 --> CLAUDE
    WORKER2 --> GIT
    PM --> DOCKER
```

## Deployment Modes

```mermaid
graph LR
    %% Define styles
    classDef local fill:#315074,stroke:#e1e1e1,stroke-width:2px,color:#e1e1e1
    classDef lan fill:#67bd6d,stroke:#0e1c2d,stroke-width:2px,color:#0e1c2d
    classDef wan fill:#ffc300,stroke:#0e1c2d,stroke-width:2px,color:#0e1c2d
    classDef cloud fill:#8b5cf6,stroke:#e1e1e1,stroke-width:2px,color:#e1e1e1

    LOCAL["🏠 Local Mode<br/>SQLite Database<br/>No Auth Required<br/>localhost:8000"]:::local
    LAN["🏢 LAN Mode<br/>PostgreSQL<br/>API Key Auth<br/>Network Access"]:::lan
    WAN["🌍 WAN Mode<br/>PostgreSQL<br/>OAuth + TLS<br/>Internet Access"]:::wan
    CLOUD["☁️ Cloud Mode<br/>Managed Service<br/>Auto-scaling<br/>Global Deploy"]:::cloud

    LOCAL -->|Progressive<br/>Enhancement| LAN
    LAN -->|Security<br/>Hardening| WAN
    WAN -->|Managed<br/>Service| CLOUD
```

## Database Schema Overview

```mermaid
erDiagram
    PROJECT ||--o{ AGENT : "has"
    PROJECT ||--o{ MESSAGE : "contains"
    PROJECT ||--o{ TASK : "tracks"
    PROJECT ||--o{ SESSION : "logs"
    PROJECT ||--o{ VISION : "references"
    AGENT ||--o{ MESSAGE : "sends/receives"
    AGENT ||--o{ TASK : "assigned"
    AGENT ||--o{ JOB : "performs"
    AGENT_TEMPLATE ||--o{ AGENT : "uses"
    TEMPLATE_ARCHIVE ||--o{ AGENT_TEMPLATE : "versions"

    PROJECT {
        uuid id PK
        string name
        string tenant_key UK
        text mission
        string status
        timestamp created_at
        int context_budget
        int context_used
    }

    AGENT {
        uuid id PK
        uuid project_id FK
        string name
        string type
        string status
        text current_context
        timestamp last_active
        int context_used
    }

    MESSAGE {
        uuid id PK
        uuid project_id FK
        uuid from_agent FK
        uuid to_agent FK
        string type
        text content
        string priority
        string status
        array acknowledged_by
        timestamp created_at
    }

    TASK {
        uuid id PK
        uuid project_id FK
        uuid agent_id FK
        string title
        text description
        string status
        string priority
        timestamp due_date
        timestamp completed_at
    }

    AGENT_TEMPLATE {
        uuid id PK
        string tenant_key
        string name UK
        text template
        json metadata
        boolean is_active
        timestamp created_at
    }
```

## Key Features

### 🚀 Progressive Architecture
- **Local First**: Start with SQLite, zero configuration
- **Scale When Ready**: Seamlessly upgrade to PostgreSQL
- **Cloud Native**: Container-ready with Docker support
- **Multi-tenant**: Isolated projects via tenant keys

### 🔧 Core Capabilities
- **Vision Chunking**: Handle 50K+ token documents
- **Message Acknowledgment**: Reliable multi-agent coordination
- **Dynamic Discovery**: No static indexing required
- **Template System**: Database-backed mission templates
- **Real-time Updates**: WebSocket for live dashboard

### 🛡️ Security & Performance
- **API Key Authentication**: Secure LAN/WAN access
- **OAuth Integration**: Enterprise-ready authentication
- **Context Management**: Efficient token usage
- **Redis Caching**: High-performance message queue
- **Async Operations**: Non-blocking database access

## Color Legend

- 🟡 **Yellow (#ffc300)**: Primary components and user interfaces
- 🟢 **Green (#67bd6d)**: Core orchestration and healthy systems
- 🟣 **Purple (#8b5cf6)**: Special features and MCP integration
- 🔵 **Blue (#315074)**: Standard services and infrastructure
- 🌑 **Dark (#1e3147)**: Data storage and file systems
- 🔴 **Pink (#c6298c)**: Error states and critical alerts

## References

- Color themes: [`docs/color_themes.md`](../color_themes.md)
- Technical architecture: [`docs/TECHNICAL_ARCHITECTURE.md`](../TECHNICAL_ARCHITECTURE.md)
- MCP tools documentation: [`docs/manuals/MCP_TOOLS_MANUAL.md`](../manuals/MCP_TOOLS_MANUAL.md)
- Frontend assets: [`frontend/public/`](../../frontend/public/)