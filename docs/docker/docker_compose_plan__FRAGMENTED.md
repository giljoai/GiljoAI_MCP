# Docker Compose Architecture Plan

## GiljoAI MCP Orchestrator

### Service Architecture Overview

```
┌─────────────────────────────────────────────────────────────┐
│                     External Access                          │
│                                                              │
│  Browser ──> :6000 (Dashboard)  :6002 (API)  :6003 (WS)    │
└─────────────────────────────────────────────────────────────┘
                              │
                              ▼
┌─────────────────────────────────────────────────────────────┐
│                    Docker Network: giljo-net                 │
├─────────────────────────────────────────────────────────────┤
│                                                              │
│  ┌──────────────┐  ┌──────────────┐  ┌──────────────┐     │
│  │   Frontend   │  │   Backend    │  │  PostgreSQL  │     │
│  │              │  │              │  │              │     │
│  │ nginx:alpine │  │ Python 3.11  │  │  postgres:15 │     │
│  │              │  │              │  │              │     │
│  │ Port: 6000   │  │ Ports:       │  │ Port: 5432   │     │
│  │              │  │ - 6002 (API) │  │              │     │
│  │ Vue 3 SPA    │  │ - 6003 (WS)  │  │ Volume:      │     │
│  │              │  │              │  │ pgdata:/var  │     │
│  └──────────────┘  └──────────────┘  └──────────────┘     │
│                                                              │
└─────────────────────────────────────────────────────────────┘
```

### Service Definitions

#### 1. PostgreSQL Database (postgres)

- **Image**: postgres:15-alpine
- **Container Name**: giljo-postgres
- **Ports**: 5432:5432 (internal only in production)
- **Environment Variables**:
  - POSTGRES_DB=giljo_mcp_db
  - POSTGRES_USER=postgres
  - POSTGRES_PASSWORD=${DB_PASSWORD}
- **Volumes**:
  - postgres_data:/var/lib/postgresql/data
  - ./docker/postgres/init.sql:/docker-entrypoint-initdb.d/01-init.sql (optional)
- **Health Check**:
  - Command: pg_isready -U postgres
  - Interval: 10s
  - Timeout: 5s
  - Retries: 5
- **Restart Policy**: unless-stopped

#### 2. Backend API (backend)

- **Build Context**: ./
- **Dockerfile**: ./docker/backend.Dockerfile
- **Container Name**: giljo-backend
- **Ports**:
  - 6002:6002 (REST API)
  - 6003:6003 (WebSocket)
- **Environment Variables**:
  - DB_HOST=postgres
  - DB_PORT=5432
  - DB_NAME=giljo_mcp_db
  - DB_USER=postgres
  - DB_PASSWORD=${DB_PASSWORD}
  - GILJO_MCP_MODE=${GILJO_MCP_MODE:-local}
  - GILJO_MCP_API_PORT=6002
  - GILJO_MCP_WEBSOCKET_PORT=6003
  - LOG_LEVEL=${LOG_LEVEL:-INFO}
- **Volumes**:
  - ./logs:/app/logs
  - ./data:/app/data (for PostgreSQL in dev mode)
  - ./docs/vision:/app/docs/vision (read-only)
- **Depends On**: postgres (with health check)
- **Health Check**:
  - Command: curl -f http://localhost:6002/health || exit 1
  - Interval: 30s
  - Timeout: 10s
  - Retries: 3
- **Restart Policy**: unless-stopped

#### 3. Frontend Dashboard (frontend)

- **Build Context**: ./frontend
- **Dockerfile**: ./docker/frontend.Dockerfile
- **Container Name**: giljo-frontend
- **Ports**: 6000:80
- **Environment Variables**:
  - VITE_API_URL=http://backend:6002
  - VITE_WS_URL=ws://backend:6003
  - VITE_APP_MODE=${GILJO_MCP_MODE:-local}
- **Volumes**: None (static build)
- **Depends On**: backend
- **Health Check**:
  - Command: wget --no-verbose --tries=1 --spider http://localhost:80 || exit 1
  - Interval: 30s
  - Timeout: 10s
  - Retries: 3
- **Restart Policy**: unless-stopped

### Network Configuration

#### Internal Network (giljo-net)

- **Driver**: bridge
- **IPAM Config**:
  - Subnet: 172.20.0.0/16
- **Service IPs** (optional static assignment):
  - postgres: 172.20.0.2
  - backend: 172.20.0.3
  - frontend: 172.20.0.4

### Volume Definitions

1. **postgres_data**:

   - Driver: local
   - Purpose: PostgreSQL data persistence

2. **logs** (bind mount):

   - Host: ./logs
   - Container: /app/logs
   - Purpose: Application logs persistence

3. **vision_docs** (bind mount):
   - Host: ./docs/vision
   - Container: /app/docs/vision
   - Mode: read-only
   - Purpose: Vision document access

### Environment Files

#### Development (.env.dev)

```env
# Database
DB_PASSWORD=dev_password_123
DB_HOST=postgres
DB_PORT=5432

# Mode
GILJO_MCP_MODE=local

# Logging
LOG_LEVEL=DEBUG
DEBUG=true

# Feature Flags
HOT_RELOAD=true
```

#### Production (.env.prod)

```env
# Database
DB_PASSWORD=${SECURE_DB_PASSWORD}
DB_HOST=postgres
DB_PORT=5432

# Mode
GILJO_MCP_MODE=lan

# Security
GILJO_MCP_API_KEY=${SECURE_API_KEY}
GILJO_MCP_SECRET_KEY=${SECURE_SECRET_KEY}

# Logging
LOG_LEVEL=INFO
DEBUG=false

# Feature Flags
HOT_RELOAD=false
```

### Docker Compose Variants

#### 1. docker-compose.yml (Base Configuration)

- Core service definitions
- Shared network configuration
- Base environment variables

#### 2. docker-compose.dev.yml (Development Override)

- Volume mounts for hot reload
- Exposed database port for debugging
- Development environment variables
- Build from local Dockerfiles

#### 3. docker-compose.prod.yml (Production Override)

- No exposed database port
- Production environment variables
- Pull from registry (future)
- Resource limits and reservations

### Deployment Commands

#### Development Mode

```bash
docker-compose -f docker-compose.yml -f docker-compose.dev.yml up --build
```

#### Production Mode

```bash
docker-compose -f docker-compose.yml -f docker-compose.prod.yml up -d
```

#### Useful Commands

```bash
# View logs
docker-compose logs -f [service_name]

# Restart a service
docker-compose restart [service_name]

# Execute command in container
docker-compose exec backend bash

# Clean up everything
docker-compose down -v
```

### Health Check Strategy

1. **PostgreSQL**: Native pg_isready
2. **Backend**: Custom /health endpoint
3. **Frontend**: HTTP check on nginx

### Backup Strategy

1. **Database Backups**:

   ```bash
   docker-compose exec postgres pg_dump -U postgres giljo_mcp_db > backup.sql
   ```

2. **Volume Backups**:
   ```bash
   docker run --rm -v giljo_postgres_data:/data -v $(pwd):/backup alpine tar czf /backup/postgres_backup.tar.gz /data
   ```

### Security Considerations

1. **Network Isolation**: All services communicate through internal network
2. **Secrets Management**: Use Docker secrets or environment files
3. **Non-root Users**: Run services as non-root where possible
4. **Read-only Mounts**: Vision documents mounted as read-only
5. **Resource Limits**: CPU and memory limits in production

### Migration Strategy

1. **Database Migrations**:

   - Use Alembic for schema migrations
   - Run migrations on container startup
   - Rollback capability

2. **Zero-downtime Deployment**:
   - Blue-green deployment pattern
   - Health checks before traffic switch
   - Graceful shutdown handling

### Monitoring & Observability

1. **Logging**:

   - Centralized logging to ./logs volume
   - Log rotation configured
   - Structured JSON logging

2. **Metrics** (Future):
   - Prometheus metrics endpoint
   - Grafana dashboard
   - Alert manager integration

### Cross-Platform Compatibility

1. **Windows Docker Desktop**:

   - Use named volumes instead of bind mounts where possible
   - Handle line ending differences (CRLF vs LF)
   - WSL2 backend recommended

2. **Linux**:
   - Native Docker performance
   - User namespace remapping for security
   - SELinux/AppArmor policies

### Performance Optimization

1. **Multi-stage Builds**:

   - Minimize final image size
   - Cache dependencies separately
   - Remove build tools from runtime

2. **Layer Caching**:

   - Order Dockerfile commands for optimal caching
   - Separate dependency installation from code

3. **Resource Allocation**:
   - Backend: 1GB RAM, 1 CPU
   - Frontend: 256MB RAM, 0.5 CPU
   - Database: 512MB RAM, 1 CPU

### Troubleshooting Guide

1. **Port Conflicts**:

   - Check: `docker ps` and `netstat -an`
   - Solution: Modify port mappings in .env

2. **Database Connection Issues**:

   - Check: Database logs and health status
   - Solution: Verify credentials and network

3. **Permission Issues**:
   - Check: Volume mount permissions
   - Solution: Set proper ownership/permissions

### Future Enhancements

1. **Redis Cache Service**:

   - Session storage
   - Message queue
   - Performance optimization

2. **Nginx Reverse Proxy**:

   - SSL termination
   - Load balancing
   - Rate limiting

3. **Monitoring Stack**:
   - Prometheus
   - Grafana
   - Loki for logs

### Success Metrics

- ✅ All containers start within 30 seconds
- ✅ Health checks pass within 1 minute
- ✅ Zero data loss on container restart
- ✅ Sub-500MB production images
- ✅ Works on Windows and Linux
- ✅ Single command deployment
