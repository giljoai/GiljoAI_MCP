# Docker Deployment
## GiljoAI MCP Coding Orchestrator

### Quick Start

```bash
# Clone the repository
git clone https://github.com/your-org/giljoai-mcp.git
cd giljoai-mcp/docker

# Copy environment template
cp .env.example .env

# Start the stack
docker-compose up -d

# View logs
docker-compose logs -f

# Access the application
# Frontend: http://localhost:6000
# API Docs: http://localhost:6002/docs
# MCP Server: localhost:6001
```

---

## Architecture

The GiljoAI MCP Orchestrator consists of four main components:

1. **PostgreSQL Database** - Data persistence layer
2. **Backend API** - FastAPI application with MCP server
3. **Frontend** - Vue 3 dashboard with Vuetify
4. **WebSocket Server** - Real-time communication

### Container Structure

```
┌─────────────────────────────────────────────┐
│                 Frontend (Nginx)             │
│                  Port: 6000                  │
└─────────────────────────────────────────────┘
                        │
                        ├── HTTP API
                        ├── WebSocket
                        │
┌─────────────────────────────────────────────┐
│              Backend (FastAPI)               │
│         API: 6002 | WebSocket: 6003          │
│              MCP Server: 6001                │
└─────────────────────────────────────────────┘
                        │
                        │
┌─────────────────────────────────────────────┐
│            PostgreSQL Database               │
│              Port: 5432 (internal)           │
└─────────────────────────────────────────────┘
```

---

## Configuration

### Environment Variables

Create a `.env` file in the docker directory:

```env
# Database Configuration
POSTGRES_USER=postgres
POSTGRES_PASSWORD=your_secure_password_here
POSTGRES_DB=giljoai
DATABASE_URL=postgresql://postgres:your_secure_password_here@postgres:5432/giljoai

# Backend Configuration
API_HOST=0.0.0.0
API_PORT=6002
WS_PORT=6003
MCP_PORT=6001
ENVIRONMENT=production
DEBUG=false

# Frontend Configuration
VITE_API_URL=http://localhost:6002
VITE_WS_URL=ws://localhost:6003

# Security
SECRET_KEY=your_secret_key_here
API_KEY=your_api_key_here

# Optional: External Services
SERENA_MCP_URL=http://serena-mcp:5000
```

---

## Deployment Modes

### Development Mode

```bash
# Start with hot-reload and debugging
docker-compose -f docker-compose.yml -f docker-compose.dev.yml up

# Features:
# - Hot reload for backend (FastAPI)
# - HMR for frontend (Vite)
# - Debug ports exposed
# - Source code mounted as volumes
# - Verbose logging
```

### Production Mode

```bash
# Start optimized production stack
docker-compose -f docker-compose.yml -f docker-compose.prod.yml up -d

# Features:
# - Multi-stage builds for minimal size
# - Nginx serving static files
# - Health checks enabled
# - Restart policies configured
# - Security hardening applied
```

### Local Development (without Docker)

```bash
# If you prefer local development
# See ../README.md for local setup instructions
```

---

## Container Management

### Basic Commands

```bash
# Start all services
docker-compose up -d

# Stop all services
docker-compose down

# Restart a specific service
docker-compose restart backend

# View logs
docker-compose logs -f [service]

# Execute command in container
docker-compose exec backend bash

# List running containers
docker-compose ps

# Check health status
docker-compose ps | grep healthy
```

### Database Management

```bash
# Access PostgreSQL shell
docker-compose exec postgres psql -U postgres -d giljoai

# Backup database
docker-compose exec postgres pg_dump -U postgres giljoai > backup.sql

# Restore database
docker-compose exec -T postgres psql -U postgres giljoai < backup.sql

# Reset database (CAUTION: destroys all data)
docker-compose down -v
docker-compose up -d
```

### Debugging

```bash
# View container health
docker inspect --format='{{json .State.Health}}' giljoai-backend | jq

# Check resource usage
docker stats

# Access backend shell
docker-compose exec backend bash

# Test API endpoint
curl http://localhost:6002/health

# Monitor real-time logs
docker-compose logs -f --tail=100
```

---

## Health Checks

All containers include health checks that automatically restart unhealthy services:

| Service | Endpoint | Interval | Timeout | Retries |
|---------|----------|----------|---------|---------|
| PostgreSQL | `pg_isready` | 10s | 5s | 5 |
| Backend | `/health` | 30s | 10s | 3 |
| Frontend | `/` | 30s | 3s | 3 |

Monitor health status:
```bash
watch -n 2 'docker-compose ps'
```

---

## Volumes and Persistence

### Data Volumes

- `postgres_data`: PostgreSQL database files
- `uploads`: User uploaded files
- `logs`: Application logs
- `config`: Configuration files

### Backup Strategy

```bash
# Backup all volumes
docker run --rm -v postgres_data:/data -v $(pwd)/backups:/backup \
  alpine tar czf /backup/postgres_data_$(date +%Y%m%d).tar.gz -C /data .

# Restore volume
docker run --rm -v postgres_data:/data -v $(pwd)/backups:/backup \
  alpine tar xzf /backup/postgres_data_20250114.tar.gz -C /data
```

---

## Networking

### Port Mappings

| Service | Internal Port | External Port | Description |
|---------|--------------|---------------|-------------|
| Frontend | 80 | 6000 | Web Dashboard |
| Backend API | 8000 | 6002 | REST API |
| WebSocket | 8001 | 6003 | Real-time updates |
| MCP Server | 5000 | 6001 | MCP Protocol |
| PostgreSQL | 5432 | - | Internal only |

### Custom Network

All services communicate on the `giljoai_network` bridge network:

```bash
# Inspect network
docker network inspect giljoai_network

# Test connectivity between containers
docker-compose exec backend ping postgres
```

---

## Security

### Best Practices

1. **Never commit `.env` files** - Use `.env.example` as template
2. **Use strong passwords** - Generate with `openssl rand -base64 32`
3. **Limit exposed ports** - Only expose necessary services
4. **Run as non-root** - Containers use unprivileged users
5. **Keep images updated** - Regularly rebuild with latest base images

### SSL/TLS Setup (Production)

```yaml
# docker-compose.prod.yml addition
frontend:
  volumes:
    - ./ssl:/etc/nginx/ssl:ro
  environment:
    - SSL_CERT=/etc/nginx/ssl/cert.pem
    - SSL_KEY=/etc/nginx/ssl/key.pem
```

---

## Troubleshooting

### Common Issues

#### Container won't start
```bash
# Check logs
docker-compose logs [service]

# Verify configuration
docker-compose config

# Check port conflicts
netstat -tulpn | grep -E '6000|6001|6002|6003'
```

#### Database connection errors
```bash
# Verify PostgreSQL is running
docker-compose exec postgres pg_isready

# Check credentials
docker-compose exec backend env | grep DATABASE_URL

# Test connection
docker-compose exec backend python -c "from sqlalchemy import create_engine; engine = create_engine('$DATABASE_URL'); engine.connect()"
```

#### Frontend can't reach backend
```bash
# Check CORS settings
curl -I http://localhost:6002/api/health

# Verify proxy configuration
docker-compose exec frontend cat /etc/nginx/conf.d/default.conf

# Test from frontend container
docker-compose exec frontend curl backend:8000/health
```

#### Out of disk space
```bash
# Clean up unused images
docker system prune -a

# Remove unused volumes
docker volume prune

# Check volume sizes
docker system df
```

---

## Testing

Run the comprehensive test suite:

```bash
# Build tests
cd tests
./test_build.sh

# Health checks (requires running stack)
./test_health.sh

# Persistence tests
./test_persistence.sh

# Performance tests
./test_performance.sh

# Run all tests
./run_all_tests.sh
```

---

## Scaling

### Horizontal Scaling

```yaml
# docker-compose.scale.yml
backend:
  deploy:
    replicas: 3

# Scale backend to 3 instances
docker-compose -f docker-compose.yml -f docker-compose.scale.yml up -d --scale backend=3
```

### Resource Limits

```yaml
# docker-compose.prod.yml
services:
  backend:
    deploy:
      resources:
        limits:
          cpus: '2.0'
          memory: 2G
        reservations:
          cpus: '1.0'
          memory: 1G
```

---

## Monitoring

### Prometheus Integration

```yaml
# docker-compose.monitoring.yml
prometheus:
  image: prom/prometheus
  volumes:
    - ./prometheus.yml:/etc/prometheus/prometheus.yml
  ports:
    - "9090:9090"
```

### Logging

```bash
# Configure log driver
docker-compose logs --tail=100 -f

# Export logs
docker-compose logs > deployment.log

# Log rotation (in docker-compose.yml)
logging:
  driver: "json-file"
  options:
    max-size: "10m"
    max-file: "3"
```

---

## Maintenance

### Updates

```bash
# Pull latest changes
git pull origin main

# Rebuild images
docker-compose build --no-cache

# Restart with new images
docker-compose down
docker-compose up -d
```

### Database Migrations

```bash
# Run migrations
docker-compose exec backend alembic upgrade head

# Create new migration
docker-compose exec backend alembic revision --autogenerate -m "Description"
```

---

## Support

### Getting Help

1. Check the [test results](./tests/test_results/)
2. Review [health check patterns](./tests/HEALTHCHECK_PATTERNS.md)
3. Consult the [main documentation](../docs/)
4. Open an issue on GitHub

### Useful Resources

- [Docker Documentation](https://docs.docker.com/)
- [Docker Compose Reference](https://docs.docker.com/compose/)
- [FastAPI Deployment](https://fastapi.tiangolo.com/deployment/)
- [Vue.js Deployment](https://vuejs.org/guide/best-practices/production-deployment.html)

---

## License

See [LICENSE](../LICENSE) file in the root directory.

---

**Version:** 1.0.0
**Last Updated:** 2025-01-14
**Maintainer:** GiljoAI Development Team