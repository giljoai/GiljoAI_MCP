# Server Architecture & Tech Stack

**Document Version**: 10_13_2025
**Status**: Single Source of Truth
**Last Updated**: October 13, 2025

---

## v3.0 Unified Architecture Overview

GiljoAI MCP v3.0 implements a **unified architecture** with no deployment modes. The system ALWAYS binds to all network interfaces while using OS firewall for access control, providing consistent behavior across localhost, LAN, and WAN deployments.

### Core Architectural Principles

**Single Network Binding**:
- API server ALWAYS binds to `0.0.0.0` (all network interfaces)
- OS firewall controls actual access (defense in depth)
- Database ALWAYS on localhost (never exposed to network)
- ONE authentication flow for ALL connections (localhost, LAN, WAN)

**Defense in Depth Security**:
1. **OS Firewall** - First layer of protection
2. **Application Authentication** - JWT + password validation  
3. **Password Policy** - Complexity requirements and forced changes
4. **Database Isolation** - PostgreSQL never exposed to network
5. **HTTPS/TLS** - Encrypted transport for WAN deployments

---

## Network Topology

### ASCII Architecture Diagram

**VERIFIED AGAINST CODE** (`api/app.py:185-188`, `database.py:40-60`):

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
       │  Host: localhost       │ ← NEVER changes
       │  Port: 5432            │
       │  Binding: 127.0.0.1    │
       └────────────────────────┘
```

**Code Verification**:
- **API Binding**: `api/app.py:532-538` - CORS middleware configured for 0.0.0.0 binding
- **Database Host**: `api/app.py:185` - `state.config.database.host` (always "localhost")
- **Port Configuration**: `api/app.py:467-468` - Default ports 7272 (API), 7274 (frontend)

### Network Access Control

**Firewall Configuration** (Windows PowerShell example):
```powershell
# Block external access by default
New-NetFirewallRule -DisplayName "GiljoAI MCP - Block External" `
    -Direction Inbound -Action Block -Protocol TCP -LocalPort 7272

# Allow localhost access
New-NetFirewallRule -DisplayName "GiljoAI MCP - Allow Localhost" `
    -Direction Inbound -Action Allow -Protocol TCP -LocalPort 7272 `
    -RemoteAddress 127.0.0.1,::1

# Optional: Allow specific LAN range
New-NetFirewallRule -DisplayName "GiljoAI MCP - Allow LAN" `
    -Direction Inbound -Action Allow -Protocol TCP -LocalPort 7272 `
    -RemoteAddress 192.168.1.0/24
```

**Linux iptables Configuration**:
```bash
# Block external access
sudo iptables -A INPUT -p tcp --dport 7272 -s ! 127.0.0.1 -j DROP

# Allow localhost
sudo iptables -I INPUT -p tcp --dport 7272 -s 127.0.0.1 -j ACCEPT

# Optional: Allow specific LAN range  
sudo iptables -I INPUT -p tcp --dport 7272 -s 192.168.1.0/24 -j ACCEPT
```

---

## Technology Stack

### Backend Stack

**Core Framework**:
- **FastAPI 0.104+** - Modern Python web framework
- **Python 3.11+** - Required minimum version
- **SQLAlchemy 2.0** - Database ORM with async support
- **PostgreSQL 18** - Primary database (REQUIRED)

**Code Reference**: `api/app.py:361-425` - FastAPI app configuration

**Authentication & Security**:
- **JWT (JSON Web Tokens)** - Session management
- **bcrypt** - Password hashing (cost factor: 12)
- **CORS Middleware** - Cross-origin request handling
- **Rate Limiting** - 60 requests/minute default

**Code Reference**: `api/app.py:518-538` - Middleware stack configuration

**Database Layer**:
```python
# From src/giljo_mcp/database.py:40-80
class DatabaseManager:
    def _create_sync_engine(self) -> Engine:
        return create_engine(
            self.database_url,
            poolclass=QueuePool,
            pool_size=20,         # Production-optimized
            max_overflow=40,      # Handle burst traffic
            pool_pre_ping=True,   # Connection health checks
            pool_recycle=3600,    # 1-hour connection recycling
            echo=False,           # Disable SQL logging in production
        )
```

**WebSocket Support**:
- **Real-time updates** for agent monitoring
- **Authentication-gated** WebSocket connections
- **Heartbeat mechanism** (30-second intervals)

**Code Reference**: `api/app.py:597-710` - WebSocket endpoint implementation

### Frontend Stack

**Core Framework**:
- **Vue 3** - Progressive JavaScript framework (Composition API)
- **Vuetify 3** - Material Design 3 component library
- **Node.js 18+** - JavaScript runtime requirement
- **Vite** - Build tool and development server

**State Management**:
- **Pinia** - Vue 3 state management
- **WebSocket Integration** - Real-time state updates
- **JWT Token Management** - Client-side authentication

**Development Server**:
- **Port 7274** - Production frontend port
- **Port 5173** - Vite development server port
- **Hot Module Replacement** - Development-time features

### Database Architecture

**PostgreSQL 18 Requirements**:
```sql
-- Required PostgreSQL version
SELECT version();
-- Expected: PostgreSQL 18.x

-- Connection pooling configuration
SHOW max_connections;        -- Default: 100
SHOW shared_buffers;         -- Recommended: 256MB+
SHOW effective_cache_size;   -- Recommended: 1GB+
```

**Multi-Tenant Isolation**:
```sql
-- All tables include tenant_key for isolation
CREATE TABLE products (
    id VARCHAR(36) PRIMARY KEY,
    tenant_key VARCHAR(36) NOT NULL,  -- ← ISOLATION COLUMN
    name VARCHAR(255) NOT NULL,
    -- ... other columns
);

-- Optimized indexes for multi-tenant queries  
CREATE INDEX idx_products_tenant_name ON products(tenant_key, name);
CREATE INDEX idx_projects_tenant_status ON projects(tenant_key, status);
```

**Performance Optimizations**:
- **GIN indexes** for JSONB config data (PostgreSQL-specific)
- **Connection pooling** with health checks
- **Query optimization** with tenant-first indexing
- **Connection recycling** to prevent memory leaks

**Code Reference**: `src/giljo_mcp/models.py:80-100` - Index configurations

---

## Component Architecture

### API Server Structure

**Application Layout**:
```
api/
├── app.py                  # FastAPI application factory
├── middleware/             # Custom middleware stack
│   ├── auth.py            # JWT authentication middleware
│   ├── rate_limit.py      # Rate limiting middleware
│   ├── security.py        # Security headers middleware
│   └── setup.py           # Setup mode middleware
├── endpoints/             # API endpoint modules
│   ├── auth.py           # Authentication endpoints
│   ├── projects.py       # Project management
│   ├── agents.py         # Agent orchestration
│   ├── messages.py       # Inter-agent messaging
│   ├── setup.py          # Setup wizard endpoints
│   ├── ai_tools.py       # AI tool configuration generator (425 lines)
│   └── templates.py      # Template CRUD operations
└── websocket/            # WebSocket handlers
    ├── manager.py        # WebSocket connection management
    └── auth.py           # WebSocket authentication
```

**Middleware Stack** (execution order):
```python
# From api/app.py:514-538
# Middleware executes in REVERSE order of addition

# 5th - Authentication (JWT validation)
app.add_middleware(AuthMiddleware)

# 4th - Rate limiting (60 requests/minute)  
app.add_middleware(RateLimitMiddleware, requests_per_minute=60)

# 3rd - Security headers (HSTS, CSP, etc.)
app.add_middleware(SecurityHeadersMiddleware)

# 2nd - Setup mode (database initialization check)
app.add_middleware(SetupModeMiddleware)

# 1st - CORS (handles OPTIONS preflight)
app.add_middleware(CORSMiddleware, allow_origins=cors_origins)
```

### Backend Service Layer

**Core Services**:
```
src/giljo_mcp/
├── orchestrator.py         # Multi-agent coordination engine
├── database.py            # PostgreSQL connection management
├── tenant.py              # Multi-tenant isolation manager  
├── models.py              # SQLAlchemy ORM models
├── template_manager.py    # ✨ NEW: Unified template system (342 lines)
├── auth/                  # Authentication services
│   ├── manager.py         # AuthManager class
│   ├── jwt_handler.py     # JWT token operations
│   └── password.py        # bcrypt password handling
├── tools/                 # MCP tool implementations (22+ tools)
│   ├── project.py         # Project management tools
│   ├── agent.py           # Agent orchestration tools
│   ├── message.py         # Message queue tools
│   ├── context.py         # Context management tools
│   ├── template.py        # ✨ NEW: Template CRUD operations
│   └── task_templates.py  # Task template management
└── setup/                 # Setup wizard backend
    ├── state_manager.py   # Setup state tracking
    └── wizard.py          # Multi-step setup logic
```

**MCP Tools Architecture**:
- **22+ specialized tools** for agent coordination
- **Tool registration** via decorator pattern
- **Database session management** for each tool call
- **Tenant isolation** enforced at tool level

### Frontend Architecture

**Vue 3 Application Structure**:
```
frontend/
├── src/
│   ├── main.js            # Application entry point
│   ├── App.vue            # Root component
│   ├── router/            # Vue Router configuration
│   │   └── index.js       # Route definitions + auth guards
│   ├── stores/            # Pinia state management
│   │   ├── auth.js        # Authentication state
│   │   ├── products.js    # Product management state
│   │   ├── agents.js      # Agent monitoring state
│   │   └── websocket.js   # WebSocket connection state
│   ├── views/             # Page-level components
│   │   ├── Login.vue      # Authentication page
│   │   ├── Setup.vue      # Setup wizard (3 steps)
│   │   ├── Dashboard.vue  # Main dashboard
│   │   └── Projects.vue   # Project management
│   ├── components/        # Reusable components
│   │   ├── AgentCard.vue  # Agent status display
│   │   ├── ProjectCard.vue# Project overview cards
│   │   ├── MessageQueue.vue# Real-time message display
│   │   ├── AIToolSetup.vue # ✨ NEW: AI tool configuration UI (243 lines)
│   │   └── setup/         # ✨ NEW: Enhanced setup components
│   │       └── WelcomePasswordStep.vue # Two-phase auth welcome
│   └── utils/             # Utility modules
│       ├── api.js         # Axios HTTP client configuration
│       ├── auth.js        # JWT token management
│       └── websocket.js   # WebSocket client wrapper
├── public/                # Static assets
├── index.html             # HTML template
└── package.json           # NPM dependencies
```

**Real-time Updates**:
```javascript
// WebSocket integration for live updates
// From frontend/src/stores/websocket.js
export const useWebSocketStore = defineStore('websocket', () => {
  const connect = async () => {
    const token = localStorage.getItem('auth_token')
    const ws = new WebSocket(`ws://localhost:7272/ws/client-id?token=${token}`)
    
    ws.onmessage = (event) => {
      const data = JSON.parse(event.data)
      // Update Pinia stores based on message type
      if (data.type === 'agent_status_update') {
        agentStore.updateAgentStatus(data.agent_id, data.status)
      }
    }
  }
})
```

---

## Security Architecture

### Authentication Flow

**v3.0 Unified Authentication** (NO auto-login):

```mermaid
graph TD
    A[User Accesses System] --> B{Setup Completed?}
    B -->|No| C[Setup Wizard - No Auth Required]
    B -->|Yes| D[Login Required]
    D --> E[Username + Password]
    E --> F{Credentials Valid?}
    F -->|No| G[Login Failed - Retry]
    F -->|Yes| H[JWT Token Issued]
    H --> I[Token Stored Client-Side]
    I --> J[API Requests Include JWT]
    J --> K[Middleware Validates JWT]
    K --> L[Tenant Context Extracted]
    L --> M[Database Queries Filtered by Tenant]
```

**Code Reference**: `api/middleware/auth.py` - JWT validation middleware

### Password Security

**bcrypt Implementation**:
```python
# Password hashing with high cost factor
import bcrypt

def hash_password(password: str) -> str:
    salt = bcrypt.gensalt(rounds=12)  # High security cost
    return bcrypt.hashpw(password.encode('utf-8'), salt).decode('utf-8')

def verify_password(password: str, hashed: str) -> bool:
    return bcrypt.checkpw(
        password.encode('utf-8'), 
        hashed.encode('utf-8')
    )
```

**Password Policy** (enforced in frontend and backend):
- Minimum 12 characters
- At least 1 uppercase letter (A-Z)
- At least 1 lowercase letter (a-z)  
- At least 1 digit (0-9)
- At least 1 special character (!@#$%^&*()_+-=[]{}|;:,.<>?)

### Database Security

**Connection Security**:
```python
# PostgreSQL connection with security optimizations
DATABASE_URL = "postgresql://user:password@localhost:5432/giljo_mcp"

# Connection pooling with security features
engine = create_engine(
    DATABASE_URL,
    pool_pre_ping=True,      # Detect connection failures
    pool_recycle=3600,       # Recycle connections hourly  
    echo=False,              # Never log SQL in production
    isolation_level="READ_COMMITTED"  # Transaction isolation
)
```

**Multi-Tenant Query Filtering**:
```python
# All queries automatically filtered by tenant
async def get_projects(session: AsyncSession, tenant_key: str):
    stmt = select(Project).where(Project.tenant_key == tenant_key)
    result = await session.execute(stmt)
    return result.scalars().all()
```

---

## Performance & Scalability

### Database Performance

**Connection Pooling Configuration**:
```python
# Optimized for production workloads
# From src/giljo_mcp/database.py:40-55
create_engine(
    database_url,
    poolclass=QueuePool,
    pool_size=20,           # 20 persistent connections
    max_overflow=40,        # 40 additional burst connections
    pool_pre_ping=True,     # Health check before use
    pool_recycle=3600,      # Recycle connections after 1 hour
)
```

**Index Optimization**:
```sql
-- Multi-tenant optimized indexes
CREATE INDEX idx_products_tenant_name ON products(tenant_key, name);
CREATE INDEX idx_projects_tenant_status ON projects(tenant_key, status);  
CREATE INDEX idx_agents_tenant_project ON agents(tenant_key, project_id);
CREATE INDEX idx_messages_tenant_timestamp ON messages(tenant_key, created_at);

-- JSONB performance indexes (PostgreSQL-specific)
CREATE INDEX idx_product_config_gin ON products 
    USING gin(config_data jsonb_path_ops);
```

### API Performance

**Rate Limiting**:
```python
# Production-grade rate limiting
# From api/middleware/rate_limit.py
class RateLimitMiddleware:
    def __init__(self, requests_per_minute: int = 60):
        self.requests_per_minute = requests_per_minute
        
    async def __call__(self, request, call_next):
        # Implement token bucket algorithm
        # Track requests per client IP + tenant
```

**Async Performance**:
```python
# All I/O operations are async for maximum throughput
async def create_project(project_data: dict, tenant_key: str):
    async with db_manager.get_session_async() as session:
        project = Project(**project_data, tenant_key=tenant_key)
        session.add(project)
        await session.commit()
        return project
```

### WebSocket Scalability

**Connection Management**:
```python
# From api/websocket/manager.py
class WebSocketManager:
    def __init__(self):
        self.connections: Dict[str, WebSocket] = {}
        self.subscriptions: Dict[str, Set[str]] = {}
        
    async def broadcast_to_tenant(self, tenant_key: str, message: dict):
        # Efficient tenant-scoped broadcasting
        for client_id, ws in self.connections.items():
            if self.get_client_tenant(client_id) == tenant_key:
                await ws.send_json(message)
```

**Heartbeat System**:
```python
# From api/app.py:268-270
async def start_heartbeat(interval: int = 30):
    while True:
        await asyncio.sleep(interval)
        # Send heartbeat to all connections
        await self.broadcast_heartbeat()
```

---

## Development & Deployment

### Development Environment

**Requirements**:
```bash
# Python requirements
Python 3.11+
PostgreSQL 18
Node.js 18+

# Python packages (from requirements.txt)
fastapi>=0.104.0
sqlalchemy>=2.0.0
alembic>=1.12.0
psycopg2-binary>=2.9.7
uvicorn>=0.24.0
bcrypt>=4.0.0
python-multipart>=0.0.6
python-jose[cryptography]>=3.3.0

# Frontend packages (from frontend/package.json)  
vue@3.3.8
vuetify@3.4.4
@vue/router@4.2.5
pinia@2.1.7
axios@1.6.0
```

**Development Scripts**:
```bash
# Backend development
python api/run_api.py --reload --log-level debug

# Frontend development  
cd frontend/
npm run dev  # Starts on port 5173 with HMR

# Full stack development
python start_giljo.py --dev
```

### Production Deployment

**System Requirements**:
- **RAM**: 4GB minimum, 8GB recommended
- **CPU**: 2 cores minimum, 4 cores recommended  
- **Storage**: 10GB minimum for database and logs
- **Network**: Static IP recommended for LAN/WAN deployments

**Production Configuration**:
```yaml
# config.yaml (production example)
services:
  api:
    host: 0.0.0.0      # ALWAYS bind to all interfaces
    port: 7272         # Standard API port
  frontend:
    port: 7274         # Standard frontend port

database:
  host: localhost      # NEVER change this
  port: 5432
  name: giljo_mcp
  
security:
  cors:
    allowed_origins:
      - "https://yourdomain.com"
      - "https://api.yourdomain.com"
  rate_limiting:
    enabled: true
    requests_per_minute: 100  # Higher for production

features:
  authentication: true        # ALWAYS enabled in v3.0
  firewall_configured: true   # Set after firewall setup
```

**Production Startup**:
```bash
# Start with production settings
uvicorn api.app:app --host 0.0.0.0 --port 7272 --workers 4

# Or use the startup script
python startup.py --production
```

### Docker Deployment

**Multi-container Architecture**:
```yaml
# docker-compose.yml
version: '3.8'
services:
  api:
    build: .
    ports:
      - "7272:7272"
    environment:
      - DATABASE_URL=postgresql://user:pass@db:5432/giljo_mcp
    depends_on:
      - db
      
  frontend:
    build: ./frontend
    ports:
      - "7274:80"
    depends_on:
      - api
      
  db:
    image: postgres:18
    environment:
      - POSTGRES_DB=giljo_mcp
      - POSTGRES_USER=giljo_user
      - POSTGRES_PASSWORD=secure_password
    volumes:
      - postgres_data:/var/lib/postgresql/data
      
volumes:
  postgres_data:
```

---

## Monitoring & Observability

### Health Checks

**API Health Endpoint**:
```python
# From api/app.py:573-595
@app.get("/health")  
async def health_check():
    checks = {
        "api": "healthy",
        "database": "unknown", 
        "websocket": "unknown"
    }
    
    # Database connectivity test
    if state.db_manager:
        try:
            async with state.db_manager.get_session_async() as session:
                await session.execute(text("SELECT 1"))
                checks["database"] = "healthy"
        except Exception as e:
            checks["database"] = f"unhealthy: {e}"
            
    return {"status": "healthy", "checks": checks}
```

**Database Monitoring**:
```sql
-- Connection monitoring
SELECT count(*) as active_connections 
FROM pg_stat_activity 
WHERE datname = 'giljo_mcp';

-- Performance monitoring
SELECT schemaname, tablename, seq_scan, seq_tup_read, 
       idx_scan, idx_tup_fetch
FROM pg_stat_user_tables 
WHERE schemaname = 'public';
```

### Logging Architecture

**Structured Logging**:
```python
import logging
import sys

# Production logging configuration
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s',
    handlers=[
        logging.FileHandler('/var/log/giljoai/api.log'),
        logging.StreamHandler(sys.stdout)
    ]
)

logger = logging.getLogger("giljoai.api")
```

**Log Categories**:
- **Application Logs**: `/var/log/giljoai/api.log`
- **Access Logs**: `/var/log/giljoai/access.log`  
- **Error Logs**: `/var/log/giljoai/errors.log`
- **Audit Logs**: `/var/log/giljoai/audit.log` (authentication events)

---

## Migration & Upgrades

### Database Schema Management

**v3.0 Table Creation**:
```python
# From install.py and api/app.py:204
await state.db_manager.create_tables_async()

# Uses Base.metadata.create_all() - NOT Alembic
# All tables created directly from SQLAlchemy models
```

**Schema Evolution**:
- **No Alembic migrations** - direct table creation
- **Backward compatibility** maintained in model definitions
- **Data migration scripts** in `scripts/` directory for major upgrades

### Version Compatibility

**Supported Upgrade Paths**:
- v2.x → v3.0: Full architecture migration required
- v3.0.x → v3.0.y: In-place upgrades supported
- v3.x → v4.0: Future migration path planned

**Migration Tools**:
```bash
# Export tenant data for migration
python scripts/export_tenant.py --tenant-key "default" --output backup.sql

# Import tenant data to new instance
python scripts/import_tenant.py --tenant-key "default" --input backup.sql
```

---

## Troubleshooting

### Common Issues

**Issue: API server won't start**
```bash
# Check port availability
netstat -tulpn | grep :7272

# Check PostgreSQL connection
psql -U postgres -h localhost -p 5432 -l

# Check logs
tail -f logs/api.log
```

**Issue: Database connection failures**
```python
# Verify connection string format
DATABASE_URL = "postgresql://user:password@localhost:5432/giljo_mcp"

# Test connection manually
import psycopg2
conn = psycopg2.connect(DATABASE_URL)
conn.close()
```

**Issue: WebSocket authentication failures**
```javascript
// Check JWT token validity
const token = localStorage.getItem('auth_token')
const payload = JSON.parse(atob(token.split('.')[1]))
console.log('Token expires:', new Date(payload.exp * 1000))
```

### Performance Troubleshooting

**Slow Database Queries**:
```sql
-- Enable query logging
ALTER SYSTEM SET log_statement = 'all';
ALTER SYSTEM SET log_min_duration_statement = 1000;  -- Log queries > 1s
SELECT pg_reload_conf();

-- Analyze slow queries
SELECT query, mean_time, calls 
FROM pg_stat_statements 
ORDER BY mean_time DESC 
LIMIT 10;
```

**Memory Usage Issues**:
```python
# Monitor connection pool usage
print(f"Pool size: {engine.pool.size()}")
print(f"Active connections: {engine.pool.checkedout()}")
print(f"Pool overflow: {engine.pool.overflow()}")
```

---

**See Also**:
- [GiljoAI MCP Purpose](GILJOAI_MCP_PURPOSE_10_13_2025.md) - Understanding the overall system purpose
- [User Structures & Tenants](USER_STRUCTURES_TENANTS_10_13_2025.md) - Multi-tenant architecture details
- [Installation Flow & Process](INSTALLATION_FLOW_PROCESS_10_13_2025.md) - Setup and configuration procedures
- [First Launch Experience](FIRST_LAUNCH_EXPERIENCE_10_13_2025.md) - Complete onboarding walkthrough

---

*This document provides comprehensive technical details of GiljoAI MCP's server architecture and technology stack as the single source of truth for the October 13, 2025 documentation harmonization.*