# Docker Health Check Patterns

## Best Practices for GiljoAI MCP Orchestrator

### Overview

Health checks are critical for container orchestration, enabling Docker to automatically restart unhealthy containers and ensure service availability.

---

## Health Check Patterns by Service Type

### 1. PostgreSQL Database

```dockerfile
HEALTHCHECK --interval=10s --timeout=5s --retries=5 \
  CMD pg_isready -U postgres || exit 1
```

**Alternative with data check:**

```dockerfile
HEALTHCHECK --interval=10s --timeout=5s --retries=5 \
  CMD psql -U postgres -c "SELECT 1" || exit 1
```

**Docker Compose:**

```yaml
healthcheck:
  test: ["CMD-SHELL", "pg_isready -U postgres"]
  interval: 10s
  timeout: 5s
  retries: 5
  start_period: 30s
```

### 2. FastAPI Backend

```dockerfile
HEALTHCHECK --interval=30s --timeout=10s --retries=3 \
  CMD curl -f http://localhost:8000/health || exit 1
```

**With database connectivity check:**

```python
# health_check.py
import sys
import httpx
from sqlalchemy import create_engine

def check_health():
    # Check API
    try:
        response = httpx.get("http://localhost:8000/health")
        if response.status_code != 200:
            sys.exit(1)
    except:
        sys.exit(1)

    # Check database
    try:
        engine = create_engine(DATABASE_URL)
        with engine.connect() as conn:
            conn.execute("SELECT 1")
    except:
        sys.exit(1)

    sys.exit(0)
```

**Docker Compose:**

```yaml
healthcheck:
  test: ["CMD", "python", "/app/health_check.py"]
  interval: 30s
  timeout: 10s
  retries: 3
  start_period: 40s
```

### 3. Nginx Frontend

```dockerfile
HEALTHCHECK --interval=30s --timeout=3s --retries=3 \
  CMD curl -f http://localhost:80/ || exit 1
```

**With specific endpoint:**

```dockerfile
HEALTHCHECK --interval=30s --timeout=3s --retries=3 \
  CMD curl -f http://localhost:80/health.html || exit 1
```

**Docker Compose:**

```yaml
healthcheck:
  test: ["CMD", "curl", "-f", "http://localhost:80/"]
  interval: 30s
  timeout: 3s
  retries: 3
  start_period: 10s
```

### 4. WebSocket Service

```dockerfile
# Using custom script for WebSocket health
HEALTHCHECK --interval=30s --timeout=5s --retries=3 \
  CMD python /app/ws_health_check.py || exit 1
```

**WebSocket health check script:**

```python
# ws_health_check.py
import asyncio
import websockets
import sys

async def check_websocket():
    try:
        async with websockets.connect("ws://localhost:8000/ws") as websocket:
            await websocket.send("ping")
            response = await asyncio.wait_for(websocket.recv(), timeout=3)
            if response == "pong":
                sys.exit(0)
    except:
        pass
    sys.exit(1)

asyncio.run(check_websocket())
```

---

## Health Check Parameters

### Interval

- **Default:** 30s
- **Recommended:** 10-30s for critical services, 30-60s for stable services
- **Consideration:** Balance between detection speed and resource usage

### Timeout

- **Default:** 30s
- **Recommended:** 3-10s depending on service complexity
- **Consideration:** Should be less than interval

### Retries

- **Default:** 3
- **Recommended:** 3-5 for production
- **Consideration:** Prevents false positives from temporary issues

### Start Period

- **Default:** 0s
- **Recommended:** 30-60s for services with slow startup
- **Consideration:** Grace period during container startup

---

## Implementation Strategies

### 1. Lightweight Checks

```dockerfile
# Good - minimal resource usage
HEALTHCHECK CMD curl -f http://localhost/health || exit 1

# Bad - heavy resource usage
HEALTHCHECK CMD python full_integration_test.py
```

### 2. Dependency-Aware Checks

```yaml
# Backend waits for database
backend:
  depends_on:
    postgres:
      condition: service_healthy
  healthcheck:
    test: ["CMD", "curl", "-f", "http://localhost:8000/health"]
    interval: 30s
    timeout: 10s
    retries: 5
    start_period: 40s
```

### 3. Multi-Level Health Checks

```python
# /health - basic liveness
@app.get("/health")
def health():
    return {"status": "alive"}

# /health/ready - readiness with dependencies
@app.get("/health/ready")
async def health_ready():
    checks = {
        "api": "ok",
        "database": check_database(),
        "cache": check_cache(),
        "mcp": check_mcp_connection()
    }

    if all(v == "ok" for v in checks.values()):
        return {"status": "ready", "checks": checks}
    else:
        raise HTTPException(503, {"status": "not ready", "checks": checks})
```

### 4. Exit Code Patterns

```bash
#!/bin/bash
# health_check.sh

# Check multiple conditions
if ! curl -f http://localhost:8000/health > /dev/null 2>&1; then
    exit 1
fi

if ! nc -z localhost 5432 2>/dev/null; then
    exit 1
fi

# All checks passed
exit 0
```

---

## Docker Compose Health Check Dependencies

### Sequential Startup

```yaml
version: "3.8"

services:
  postgres:
    image: postgres:15
    healthcheck:
      test: ["CMD-SHELL", "pg_isready -U postgres"]
      interval: 10s
      timeout: 5s
      retries: 5

  backend:
    build: .
    depends_on:
      postgres:
        condition: service_healthy
    healthcheck:
      test: ["CMD", "curl", "-f", "http://localhost:8000/health"]
      interval: 30s
      timeout: 10s
      retries: 3
      start_period: 40s

  frontend:
    build: ./frontend
    depends_on:
      backend:
        condition: service_healthy
    healthcheck:
      test: ["CMD", "curl", "-f", "http://localhost:80/"]
      interval: 30s
      timeout: 3s
      retries: 3
```

---

## Monitoring Health Status

### Docker Commands

```bash
# Check health status
docker inspect --format='{{.State.Health.Status}}' container_name

# View health check logs
docker inspect --format='{{json .State.Health}}' container_name | jq

# List unhealthy containers
docker ps --filter health=unhealthy

# Watch health status
watch -n 2 'docker ps --format "table {{.Names}}\t{{.Status}}"'
```

### Automated Monitoring Script

```bash
#!/bin/bash
# monitor_health.sh

while true; do
    for container in postgres backend frontend; do
        health=$(docker inspect --format='{{.State.Health.Status}}' $container 2>/dev/null)
        timestamp=$(date '+%Y-%m-%d %H:%M:%S')

        if [ "$health" != "healthy" ]; then
            echo "[$timestamp] WARNING: $container is $health"
            # Send alert (email, webhook, etc.)
        fi
    done
    sleep 10
done
```

---

## Common Issues and Solutions

### 1. False Positives

**Problem:** Container marked unhealthy during normal operation
**Solution:** Increase timeout or retries, add start_period

### 2. Resource Exhaustion

**Problem:** Health checks consuming too many resources
**Solution:** Increase interval, simplify check logic

### 3. Cascading Failures

**Problem:** One unhealthy service causes others to fail
**Solution:** Implement circuit breakers, graceful degradation

### 4. Slow Startup

**Problem:** Container marked unhealthy before fully initialized
**Solution:** Add appropriate start_period

---

## Best Practices

1. **Keep It Simple:** Health checks should be lightweight and fast
2. **Check Dependencies:** Verify critical dependencies are accessible
3. **Use Appropriate Timeouts:** Balance between detection speed and stability
4. **Log Health Events:** Track health check failures for debugging
5. **Test Failure Scenarios:** Verify containers restart properly
6. **Monitor Trends:** Track health check patterns over time
7. **Implement Graceful Shutdown:** Handle SIGTERM properly

---

## GiljoAI-Specific Recommendations

### Backend Health Check

```python
# /app/health_check.py
import sys
import httpx
import psycopg2
from pathlib import Path

def check_health():
    # Check API endpoint
    try:
        r = httpx.get("http://localhost:6002/health", timeout=5)
        assert r.status_code == 200
    except:
        print("API check failed")
        sys.exit(1)

    # Check database
    try:
        conn = psycopg2.connect(
            host="postgres",
            database="giljoai",
            user="postgres",
            password=os.getenv("DB_PASSWORD")
        )
        cur = conn.cursor()
        cur.execute("SELECT 1")
        conn.close()
    except:
        print("Database check failed")
        sys.exit(1)

    # Check MCP server
    try:
        r = httpx.post("http://localhost:6001/",
                      json={"method": "ping"},
                      timeout=5)
        assert r.status_code == 200
    except:
        print("MCP check failed")
        sys.exit(1)

    print("All checks passed")
    sys.exit(0)

if __name__ == "__main__":
    check_health()
```

### Frontend Health Check

```nginx
# /usr/share/nginx/html/health.html
<!DOCTYPE html>
<html>
<head><title>Health</title></head>
<body>OK</body>
</html>
```

### Docker Compose Configuration

```yaml
version: "3.8"

services:
  postgres:
    healthcheck:
      test:
        [
          "CMD-SHELL",
          "pg_isready -U postgres && psql -U postgres -d giljoai -c 'SELECT 1'",
        ]
      interval: 10s
      timeout: 5s
      retries: 5
      start_period: 30s

  backend:
    healthcheck:
      test: ["CMD", "python", "/app/health_check.py"]
      interval: 30s
      timeout: 10s
      retries: 3
      start_period: 60s

  frontend:
    healthcheck:
      test: ["CMD", "curl", "-f", "http://localhost/health.html"]
      interval: 30s
      timeout: 3s
      retries: 3
      start_period: 10s
```

---

## References

- [Docker HEALTHCHECK Documentation](https://docs.docker.com/engine/reference/builder/#healthcheck)
- [Docker Compose Health Check](https://docs.docker.com/compose/compose-file/compose-file-v3/#healthcheck)
- [Best Practices for Container Health Checks](https://cloud.google.com/blog/products/containers-kubernetes/kubernetes-best-practices-setting-up-health-checks-with-readiness-and-liveness-probes)
