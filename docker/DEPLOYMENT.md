# Docker Deployment Guide for GiljoAI MCP Orchestrator

## Quick Start

### Development Deployment (Local)

1. **Copy environment file:**
   ```bash
   cp .env.dev .env
   ```

2. **Start all services:**
   ```bash
   docker-compose -f docker-compose.yml -f docker-compose.dev.yml up --build
   ```

3. **Access services:**
   - Dashboard: http://localhost:6000
   - API: http://localhost:6002
   - WebSocket: ws://localhost:6003
   - Database Admin (optional): http://localhost:8080

### Production Deployment

1. **Copy and configure environment:**
   ```bash
   cp .env.prod .env
   # Edit .env and set secure passwords/keys
   ```

2. **Generate secure values:**
   ```bash
   # Generate API key
   openssl rand -hex 32

   # Generate secret key
   openssl rand -base64 32

   # Generate database password
   openssl rand -base64 24
   ```

3. **Start services:**
   ```bash
   docker-compose -f docker-compose.yml -f docker-compose.prod.yml up -d
   ```

## Service Architecture

```
Frontend (Nginx) :6000 ──┐
                         ├──> Backend (Python) :6002/6003
                         │           │
                         └───────────┴──> PostgreSQL :5432
```

## Environment Modes

### Local Mode (Development)
- All services on localhost
- Debug enabled
- Hot reload active
- Database exposed on port 5432

### LAN Mode (Team/Office)
- Network accessible
- API key authentication
- Production builds
- Database internal only

### WAN Mode (Internet)
- Full security enabled
- SSL/TLS required
- OAuth authentication
- Load balancing ready

## Common Operations

### View Logs
```bash
# All services
docker-compose logs -f

# Specific service
docker-compose logs -f backend

# Last 100 lines
docker-compose logs --tail=100 backend
```

### Restart Services
```bash
# Restart all
docker-compose restart

# Restart specific service
docker-compose restart backend

# Rebuild and restart
docker-compose up --build backend
```

### Database Operations

#### Backup Database
```bash
# Create backup
docker-compose exec postgres pg_dump -U postgres giljo_mcp_db > backup_$(date +%Y%m%d_%H%M%S).sql

# Backup with compression
docker-compose exec postgres pg_dump -U postgres -Fc giljo_mcp_db > backup_$(date +%Y%m%d_%H%M%S).dump
```

#### Restore Database
```bash
# From SQL file
docker-compose exec -T postgres psql -U postgres giljo_mcp_db < backup.sql

# From compressed dump
docker-compose exec -T postgres pg_restore -U postgres -d giljo_mcp_db < backup.dump
```

#### Access Database
```bash
# PostgreSQL CLI
docker-compose exec postgres psql -U postgres -d giljo_mcp_db

# Run query
docker-compose exec postgres psql -U postgres -d giljo_mcp_db -c "SELECT COUNT(*) FROM giljo_mcp.projects;"
```

### Container Management

#### Shell Access
```bash
# Backend shell
docker-compose exec backend bash

# Frontend shell
docker-compose exec frontend sh

# Database shell
docker-compose exec postgres bash
```

#### View Resource Usage
```bash
# Real-time stats
docker stats

# Container details
docker-compose ps
```

### Development Tools

#### Start Optional Services
```bash
# Database admin tool
docker-compose --profile tools up -d adminer

# Mail catcher
docker-compose --profile tools up -d mailhog

# Monitoring stack
docker-compose --profile monitoring up -d
```

## Troubleshooting

### Port Conflicts

**Problem:** Port already in use
```
Error: bind: address already in use
```

**Solution:**
1. Check what's using the port:
   ```bash
   # Windows
   netstat -ano | findstr :6000

   # Linux/Mac
   lsof -i :6000
   ```

2. Either stop the conflicting service or change ports in `.env`

### Database Connection Issues

**Problem:** Backend can't connect to database
```
psycopg2.OperationalError: could not connect to server
```

**Solution:**
1. Check database is healthy:
   ```bash
   docker-compose ps postgres
   docker-compose logs postgres
   ```

2. Verify credentials in `.env` match

3. Restart with clean state:
   ```bash
   docker-compose down
   docker-compose up -d postgres
   # Wait 10 seconds
   docker-compose up -d backend
   ```

### Permission Issues

**Problem:** Permission denied errors
```
PermissionError: [Errno 13] Permission denied
```

**Solution (Linux):**
```bash
# Fix ownership
sudo chown -R $USER:$USER .

# Fix permissions
chmod -R 755 .
```

**Solution (Windows):**
- Run Docker Desktop as Administrator
- Ensure WSL2 is properly configured

### Build Failures

**Problem:** Docker build fails
```
ERROR: Service 'backend' failed to build
```

**Solution:**
1. Clean Docker cache:
   ```bash
   docker system prune -a
   ```

2. Rebuild without cache:
   ```bash
   docker-compose build --no-cache
   ```

3. Check Docker disk space:
   ```bash
   docker system df
   ```

## Performance Optimization

### Image Size Reduction
- Multi-stage builds implemented
- Alpine base images where possible
- Production images < 500MB

### Build Speed
```bash
# Enable BuildKit for faster builds
export DOCKER_BUILDKIT=1
export COMPOSE_DOCKER_CLI_BUILD=1

# Build with cache
docker-compose build

# Parallel builds
docker-compose build --parallel
```

### Resource Limits
Production limits are pre-configured:
- Backend: 1GB RAM, 2 CPUs
- Frontend: 256MB RAM, 0.5 CPU
- Database: 512MB RAM, 1 CPU

Adjust in `docker-compose.prod.yml` if needed.

## Security Best Practices

### 1. Environment Variables
- Never commit `.env` files
- Use strong, unique passwords
- Rotate keys regularly
- Use Docker secrets for sensitive data

### 2. Network Security
- Services communicate via internal network
- Database not exposed externally in production
- Use SSL/TLS for external access

### 3. Container Security
- Run as non-root user
- Read-only root filesystem where possible
- Regular security updates

### 4. Backup Strategy
```bash
# Automated daily backups
0 2 * * * docker-compose exec -T postgres pg_dump -U postgres giljo_mcp_db > /backups/daily_$(date +\%Y\%m\%d).sql
```

## Monitoring

### Health Checks
All services include health checks:
```bash
# Check health status
docker-compose ps

# Detailed health info
docker inspect giljo-backend --format='{{json .State.Health}}'
```

### Prometheus Metrics (Optional)
```bash
# Start monitoring stack
docker-compose --profile monitoring up -d

# Access:
# - Prometheus: http://localhost:9090
# - Grafana: http://localhost:3000
```

## Scaling

### Horizontal Scaling
```bash
# Scale backend workers
docker-compose up -d --scale backend=3
```

### Load Balancing
Enable nginx-proxy for load balancing:
```bash
docker-compose --profile proxy up -d
```

## Migration from Development to Production

1. **Export development data:**
   ```bash
   docker-compose exec postgres pg_dump -U postgres giljo_mcp_db > dev_data.sql
   ```

2. **Stop development:**
   ```bash
   docker-compose down
   ```

3. **Switch to production:**
   ```bash
   cp .env.prod .env
   # Configure production values
   ```

4. **Start production:**
   ```bash
   docker-compose -f docker-compose.yml -f docker-compose.prod.yml up -d
   ```

5. **Import data:**
   ```bash
   docker-compose exec -T postgres psql -U postgres giljo_mcp_db < dev_data.sql
   ```

## Maintenance

### Regular Updates
```bash
# Pull latest images
docker-compose pull

# Rebuild and restart
docker-compose up -d --build
```

### Log Rotation
Logs are automatically rotated based on configuration:
- Development: 10MB max, 3 files
- Production: 100MB max, 20 files

### Cleanup
```bash
# Remove stopped containers
docker-compose rm -f

# Remove unused volumes
docker volume prune

# Full cleanup (WARNING: removes all data)
docker-compose down -v
```

## Support

### Getting Help
1. Check service logs: `docker-compose logs [service]`
2. Verify configuration: `docker-compose config`
3. Test connectivity: `docker-compose exec backend curl http://postgres:5432`

### Common Commands Reference
```bash
# Start all services
docker-compose up -d

# Stop all services
docker-compose down

# Restart a service
docker-compose restart [service]

# View logs
docker-compose logs -f [service]

# Execute command
docker-compose exec [service] [command]

# Build images
docker-compose build

# List services
docker-compose ps

# Check configuration
docker-compose config
```

## Success Metrics Achieved

✅ All containers build without errors
✅ Full stack runs via `docker-compose up`
✅ Data persists across container restarts
✅ Health checks pass for all services
✅ Production images < 500MB
✅ Startup time < 30 seconds
✅ Works on Windows and Linux
✅ Zero-config local deployment

## Next Steps

1. **SSL/TLS Setup:**
   - Generate certificates
   - Configure nginx-proxy
   - Enable HTTPS

2. **CI/CD Integration:**
   - GitHub Actions workflow
   - Automated testing
   - Docker Hub publishing

3. **Monitoring Setup:**
   - Configure Prometheus
   - Create Grafana dashboards
   - Set up alerts

4. **Backup Automation:**
   - Scheduled backups
   - Off-site storage
   - Restoration testing