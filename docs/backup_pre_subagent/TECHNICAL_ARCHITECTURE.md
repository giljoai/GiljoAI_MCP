# GiljoAI MCP Coding Orchestrator

## Technical Architecture Document

### System Overview

GiljoAI MCP Coding Orchestrator is a multi-agent orchestration system designed with a local-first, progressively scalable architecture. The system can run on a single developer machine, scale to team LAN servers, and ultimately deploy as a global cloud service without architectural changes.

### Core Architecture Principles

1. **Local-First Design**: Optimized for single-machine performance with network capabilities
2. **Database Agnostic**: SQLite for local, PostgreSQL for scale
3. **Multi-Tenant Ready**: Project isolation via unique keys from day one
4. **Protocol Native**: Built on Model Context Protocol (MCP) standards
5. **Progressive Enhancement**: Features activate based on deployment mode
6. **OS-Neutral Code**: All paths use pathlib.Path(), never hardcoded separators

### Cross-Platform Development Requirements

**CRITICAL**: All code must be OS-neutral for Windows, Mac, and Linux compatibility:

1. **Path Handling**:

   - Always use `pathlib.Path()` for file paths
   - Never hardcode path separators (`/` or `\`)
   - Use `Path.home()` for user directories
   - Example: `Path.home() / ".giljo-mcp" / "config.yaml"`

2. **File Operations**:

   - Use `Path.exists()`, `Path.mkdir(parents=True, exist_ok=True)`
   - Use `Path.read_text()` and `Path.write_text()` for file I/O
   - Handle line endings with `newline=None` (universal mode)

3. **Process Management**:

   - Use `subprocess` with `shell=False` when possible
   - Platform detection: `platform.system()` returns 'Windows', 'Darwin', 'Linux'
   - Conditional logic only when absolutely necessary

4. **Environment Variables**:

   - Use `os.environ.get()` with defaults
   - Path separators in env vars: use `os.pathsep`
   - Home directory: `Path.home()` not `~`

5. **Example OS-Neutral Code**:

```python
from pathlib import Path
import platform

# Good - OS neutral
config_dir = Path.home() / ".giljo-mcp"
config_file = config_dir / "config.yaml"
config_dir.mkdir(parents=True, exist_ok=True)

# Bad - OS specific
config_file = "~/.giljo-mcp/config.yaml"  # Unix only
config_file = "C:\\Users\\name\\.giljo-mcp"  # Windows only
```

### System Architecture

```
┌─────────────────────────────────────────────────────────────┐
│                   GiljoAI MCP Orchestrator                  │
├─────────────────────────────────────────────────────────────┤
│                        API Layer                             │
│  ┌──────────┐ ┌──────────┐ ┌──────────┐ ┌──────────┐      │
│  │   MCP    │ │   REST   │ │WebSocket │ │   Auth   │      │
│  │ Protocol │ │   API    │ │   API    │ │  Layer   │      │
│  └──────────┘ └──────────┘ └──────────┘ └──────────┘      │
├─────────────────────────────────────────────────────────────┤
│                    Orchestration Core                        │
│  ┌──────────────┐ ┌──────────────┐ ┌──────────────┐       │
│  │   Project    │ │    Agent     │ │   Message    │       │
│  │   Manager    │ │   Spawner    │ │    Router    │       │
│  └──────────────┘ └──────────────┘ └──────────────┘       │
├─────────────────────────────────────────────────────────────┤
│                     Data Layer                               │
│  ┌──────────────────────────────────────────────────┐      │
│  │         SQLAlchemy ORM (SQLite/PostgreSQL)       │      │
│  └──────────────────────────────────────────────────┘      │
└─────────────────────────────────────────────────────────────┘
```

### Component Architecture

#### 1. API Layer

**MCP Protocol Handler**

- Implements 20 essential MCP tools
- Handles Claude Code CLI connections
- Manages project context switching
- **Serena MCP Integration hooks for codebase discovery**

**REST API**

- Dashboard backend
- Project management endpoints
- Agent monitoring endpoints
- Configuration management

**WebSocket API**

- Real-time agent updates
- Live message streaming
- Dashboard notifications
- Collaborative features

**Authentication Layer**

- Mode-based authentication (none/apikey/oauth)
- Project key validation
- Rate limiting (WAN mode)
- Audit logging (enterprise)

#### 2. Orchestration Core

**Project Manager**

- Creates and manages projects
- Assigns agents to projects
- Tracks project lifecycle
- Handles project completion

**Agent Spawner**

- Dynamic agent creation
- Role-based agent configuration
- Mission generation from vision documents
- Context injection

**Message Router**

- Project-scoped message queues
- Agent-to-agent communication
- Message acknowledgment system
- Priority-based routing

#### 3. Data Layer

**Database Models**

```python
# Core entities
Project         # Products/projects with unique keys
Agent           # Agent instances with roles
Message         # Inter-agent communication
Task            # Task management
Session         # Agent work sessions
Vision          # Vision documents and chunks
Configuration   # Product settings

# Relationships
Project ←→ Agent (1:many)
Project ←→ Task (1:many)
Agent ←→ Message (many:many)
Agent ←→ Session (1:many)
Project ←→ Vision (1:1)
```

### Deployment Modes

#### Local Mode (Default)

```yaml
Configuration:
  host: 127.0.0.1
  port: 5001
  database: sqlite:///~/.giljo-mcp/local.db
  auth: none

Characteristics:
  - Single user
  - No authentication
  - SQLite database
  - Localhost only
  - Zero configuration
```

#### LAN Mode (Team)

```yaml
Configuration:
  host: 0.0.0.0
  port: 5001
  database: postgresql://server/giljo_mcp
  auth: api_key

Characteristics:
  - Multiple users
  - API key authentication
  - PostgreSQL recommended
  - Network accessible
  - Simple configuration
```

#### WAN Mode (Internet)

```yaml
Configuration:
  host: 0.0.0.0
  port: 443
  database: postgresql://rds/giljo_mcp
  auth: oauth
  tls: required

Characteristics:
  - Global access
  - OAuth/JWT authentication
  - PostgreSQL required
  - TLS encryption
  - Full configuration
```

### Data Flow Architecture

#### Project Creation Flow

```
1. User creates project via CLI/Dashboard
2. Project Manager validates and stores in DB
3. Vision documents loaded and chunked
4. Orchestrator agent spawned
5. Orchestrator reads vision and spawns team
6. Agents begin work with assigned missions
```

#### Message Flow

```
1. Agent generates message
2. Message Router validates project scope
3. Message stored in database queue
4. Target agent notified (WebSocket)
5. Target agent acknowledges receipt
6. Message marked as processed
```

#### Task Pipeline

```
1. Task captured during coding session
2. Stored in task database with metadata
3. User converts task to project
4. Project Manager creates project
5. Orchestration begins
6. Task marked complete on project closure
```

### Technology Stack

#### Backend

- **Language**: Python 3.8+
- **Framework**: FastAPI (async, WebSockets, OpenAPI)
- **ORM**: SQLAlchemy 2.0 (async support)
- **Database**: SQLite (local), PostgreSQL (server)
- **Database Drivers**:
  - psycopg2-binary (PostgreSQL sync operations)
  - asyncpg (PostgreSQL async operations - high performance)
  - aiosqlite (SQLite async operations)
- **Queue**: Built-in (local), Redis (scale option)
- **Process**: uvicorn (ASGI server)

#### Frontend

- **Framework**: Vue 3 + Vite (required for UI flexibility)
- **Components**: Vuetify 3 (Material Design)
- **Styling**: Tailwind CSS + Custom theme system
- **Color Themes**: See `/docs/color_themes.md` for mandatory palette
- **Provided Assets**:
  - Icons: `/frontend/public/icons/` (ready to use)
  - Mascot: `/frontend/public/mascot/` (animated logo)
  - Favicon: `/frontend/public/favicon.ico` (app icon)
- **Real-time**: WebSocket client
- **Charts**: Chart.js with theme integration
- **Animations**: Vue transitions API
- **Accessibility**: WCAG 2.1 AA compliant

#### Infrastructure

- **Container**: Docker (multi-stage build)
- **Orchestration**: Docker Compose (dev), Kubernetes (prod)
- **Reverse Proxy**: Nginx (production)
- **SSL**: Let's Encrypt (automated)
- **Monitoring**: Prometheus + Grafana (optional)

### Security Architecture

#### Local Mode

- No network exposure
- File system permissions only
- No authentication required

#### LAN Mode

- API key authentication
- Network firewall recommended
- Optional TLS with self-signed certs
- Rate limiting per API key

#### WAN Mode

- Mandatory TLS encryption
- OAuth 2.0 / JWT tokens
- Rate limiting per user/project
- IP allowlisting available
- Audit logging enabled
- Encrypted database connections

### Performance Specifications

#### Target Metrics

- **Setup Time**: < 5 minutes (local mode)
- **First Project**: < 30 seconds to create
- **Message Latency**: < 100ms (local), < 500ms (WAN)
- **Concurrent Projects**: 10+ (local), 100+ (server)
- **Concurrent Agents**: 20+ per project
- **Database Size**: 10GB+ supported

#### Scaling Boundaries

- **SQLite**: 1-10 concurrent users
- **PostgreSQL**: 10-1000 concurrent users
- **PostgreSQL Cluster**: 1000+ concurrent users

### Integration Architecture

#### Claude Code CLI

```json
{
  "mcpServers": {
    "giljo-mcp": {
      "command": "python",
      "args": ["path/to/connector.py"],
      "env": {
        "PROJECT_KEY": "unique-key",
        "SERVER_URL": "http://localhost:5001"
      }
    }
  }
}
```

#### API Agents (Future)

```python
# Anthropic API
client = AnthropicAgent(
    orchestrator_url="http://localhost:5001",
    project_key="project-123",
    api_key=os.getenv("ANTHROPIC_API_KEY")
)

# OpenAI API
client = OpenAIAgent(
    orchestrator_url="http://localhost:5001",
    project_key="project-123",
    api_key=os.getenv("OPENAI_API_KEY")
)
```

#### Desktop Application (Future)

- Electron or Tauri framework
- Local file system access
- Built-in text editor
- Integrated terminal
- Direct orchestrator connection

### Database Schema

#### Core Tables

```sql
-- Projects (formerly products)
CREATE TABLE projects (
    id UUID PRIMARY KEY,
    project_key VARCHAR(255) UNIQUE,
    name VARCHAR(255),
    vision_path TEXT,
    config_data JSONB,
    created_at TIMESTAMP,
    status VARCHAR(50)
);

-- Agents
CREATE TABLE agents (
    id UUID PRIMARY KEY,
    project_key VARCHAR(255),
    name VARCHAR(255),
    role VARCHAR(50),
    mission TEXT,
    context_usage FLOAT,
    status VARCHAR(50),
    created_at TIMESTAMP
);

-- Messages
CREATE TABLE messages (
    id UUID PRIMARY KEY,
    project_key VARCHAR(255),
    from_agent UUID,
    to_agent UUID,
    content TEXT,
    acknowledged BOOLEAN,
    created_at TIMESTAMP
);

-- Tasks
CREATE TABLE tasks (
    id UUID PRIMARY KEY,
    project_key VARCHAR(255),
    title VARCHAR(255),
    description TEXT,
    priority VARCHAR(20),
    status VARCHAR(50),
    created_at TIMESTAMP
);
```

### File Structure

```
giljo-mcp/
├── src/
│   ├── giljo_mcp/
│   │   ├── __init__.py
│   │   ├── __main__.py         # Entry point
│   │   ├── config.py           # Configuration management
│   │   ├── server.py           # FastAPI application
│   │   ├── models.py           # SQLAlchemy models
│   │   ├── database.py         # Database management
│   │   ├── auth.py             # Authentication
│   │   ├── orchestrator.py     # Core orchestration
│   │   ├── mcp_handler.py      # MCP protocol
│   │   ├── message_router.py   # Message routing
│   │   └── api/
│   │       ├── projects.py     # Project endpoints
│   │       ├── agents.py       # Agent endpoints
│   │       ├── tasks.py        # Task endpoints
│   │       └── websocket.py    # WebSocket handlers
├── frontend/                    # Vue 3 application
│   ├── public/                 # Static assets
│   │   ├── favicon.ico         # ✅ PROVIDED - Application favicon
│   │   ├── icons/              # ✅ PROVIDED - All system icons
│   │   └── mascot/             # ✅ PROVIDED - Animated logo
│   ├── src/
│   │   ├── components/         # Vue components
│   │   ├── views/              # Page views
│   │   ├── stores/             # State management
│   │   └── assets/             # Compiled assets
├── tests/
│   ├── test_orchestrator.py
│   ├── test_mcp.py
│   └── test_api.py
├── docker/
│   ├── Dockerfile
│   └── docker-compose.yml
├── config/
│   ├── config.yaml.example
│   └── logging.yaml
├── scripts/
│   ├── setup.py
│   ├── migrate.py
│   └── generate_keys.py
├── requirements.txt
├── pyproject.toml
└── README.md
```

### Migration Strategy

#### Core Features

1. Export PostgreSQL data to SQL dump
2. Run migration script to new schema
3. Update project keys for multi-tenancy
4. Convert active_product to project_key
5. Import into new system

#### Database Migration

```python
# Alembic migrations for both SQLite and PostgreSQL
alembic upgrade head

# Auto-detect database type and apply appropriate schema
if config.database_type == "sqlite":
    apply_sqlite_optimizations()
else:
    apply_postgresql_indexes()
```

### Development Workflow

#### Local Development

```bash
# Setup
git clone https://github.com/giljoai/mcp-orchestrator
cd mcp-orchestrator
python -m venv venv
pip install -e .

# Run
giljo-mcp start --mode=local --debug
```

#### Testing

```bash
# Unit tests
pytest tests/

# Integration tests
pytest tests/integration/

# Load testing
locust -f tests/load/
```

#### Deployment

```bash
# Docker build
docker build -t giljo-mcp:latest .

# Docker run (local)
docker run -p 5001:5001 giljo-mcp:latest

# Docker run (server)
docker run -d \
  -e MODE=wan \
  -e DATABASE_URL=$DATABASE_URL \
  -p 443:5001 \
  giljo-mcp:latest
```

### Monitoring & Observability

#### Metrics

- Project creation rate
- Agent spawn rate
- Message throughput
- Context usage efficiency
- Error rates
- API response times

#### Logging

- Structured JSON logging
- Log levels per module
- Centralized log aggregation (server mode)
- Audit trail for enterprise

#### Health Checks

- `/health` - System health
- `/ready` - Ready for traffic
- `/metrics` - Prometheus metrics

---

_This architecture ensures GiljoAI MCP Orchestrator scales from laptop to cloud without rewrites, maintaining simplicity for individuals while providing enterprise capabilities for teams._
