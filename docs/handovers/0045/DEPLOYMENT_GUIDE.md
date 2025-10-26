# Multi-Tool Agent Orchestration - Deployment Guide

**Version**: 3.1.0
**Last Updated**: 2025-10-25
**Audience**: DevOps Engineers, System Administrators, Technical Operations

---

## Table of Contents

1. [Pre-Deployment Checklist](#pre-deployment-checklist)
2. [Deployment Steps](#deployment-steps)
3. [Migration Script](#migration-script)
4. [Rollback Procedure](#rollback-procedure)
5. [Production Configuration](#production-configuration)
6. [Monitoring](#monitoring)
7. [Troubleshooting](#troubleshooting)

---

## Pre-Deployment Checklist

Before deploying multi-tool orchestration to production:

### 1. Database Backup

```bash
# Backup PostgreSQL database
pg_dump -U postgres -d giljo_mcp > backup_pre_v3.1.0_$(date +%Y%m%d_%H%M%S).sql

# Verify backup
ls -lh backup_pre_v3.1.0_*.sql
```

### 2. Test Migration on Staging

```bash
# 1. Restore production backup to staging
psql -U postgres -d giljo_mcp_staging < backup_pre_v3.1.0_YYYYMMDD_HHMMSS.sql

# 2. Run migration script
psql -U postgres -d giljo_mcp_staging < migration_0045_multi_tool.sql

# 3. Verify migration
psql -U postgres -d giljo_mcp_staging -c "SELECT COUNT(*) FROM agents WHERE mode IS NOT NULL"

# Expected: Returns total count (all agents should have mode field)
```

### 3. Verify Dependencies

**Python Dependencies**:
```bash
pip install -r requirements.txt

# Verify critical packages
python -c "import fastapi; print(f'FastAPI: {fastapi.__version__}')"
python -c "import sqlalchemy; print(f'SQLAlchemy: {sqlalchemy.__version__}')"
python -c "import pydantic; print(f'Pydantic: {pydantic.__version__}')"
```

**Frontend Dependencies**:
```bash
cd frontend/
npm install

# Verify build
npm run build

# Expected: dist/ folder created with production build
```

### 4. Review Configuration

**Check `config.yaml`**:
```yaml
# Multi-tool orchestration configuration
agent_orchestration:
  supported_tools:
    - claude
    - codex
    - gemini
  default_tool: claude
  hybrid_mode_tools:
    - claude
  legacy_cli_tools:
    - codex
    - gemini

# MCP coordination
mcp:
  coordination_enabled: true
  checkpoint_interval_minutes: 10
  job_timeout_minutes: 120
```

**Check `.env`** (if using environment variables):
```bash
# Database
DATABASE_URL=postgresql://postgres:password@localhost:5432/giljo_mcp

# Redis (for caching)
REDIS_URL=redis://localhost:6379/0

# API Server
API_HOST=0.0.0.0
API_PORT=7272

# Frontend
FRONTEND_PORT=7274
```

---

## Deployment Steps

### Step 1: Stop Services

```bash
# Stop API server
pkill -f "uvicorn api.app:app"

# Stop frontend server (if running standalone)
pkill -f "npm run serve"

# Verify services stopped
ps aux | grep -E "uvicorn|npm"

# Expected: No results
```

### Step 2: Backup Database

```bash
# Create backup with timestamp
BACKUP_FILE="backup_pre_deployment_$(date +%Y%m%d_%H%M%S).sql"
pg_dump -U postgres -d giljo_mcp > "$BACKUP_FILE"

# Compress backup
gzip "$BACKUP_FILE"

# Store backup in safe location
mv "${BACKUP_FILE}.gz" /backups/giljo_mcp/

echo "Backup created: /backups/giljo_mcp/${BACKUP_FILE}.gz"
```

### Step 3: Run Migration Script

**Migration SQL** (creates multi-tool fields):

```sql
-- migration_0045_multi_tool.sql
-- Multi-Tool Agent Orchestration (Handover 0045)
-- Date: 2025-10-25

BEGIN;

-- 1. Add job_id column to agents (links to MCP jobs)
ALTER TABLE agents
ADD COLUMN IF NOT EXISTS job_id VARCHAR(36) NULL;

-- 2. Add mode column to agents (tool identifier)
ALTER TABLE agents
ADD COLUMN IF NOT EXISTS mode VARCHAR(20) DEFAULT 'claude';

-- 3. Create indexes for performance
CREATE INDEX IF NOT EXISTS idx_agent_job_id ON agents(job_id);
CREATE INDEX IF NOT EXISTS idx_agent_mode ON agents(mode);

-- 4. Add preferred_tool to agent_templates (if not exists)
DO $$
BEGIN
    IF NOT EXISTS (
        SELECT 1 FROM information_schema.columns
        WHERE table_name = 'agent_templates'
        AND column_name = 'preferred_tool'
    ) THEN
        ALTER TABLE agent_templates
        ADD COLUMN preferred_tool VARCHAR(20) DEFAULT 'claude';

        CREATE INDEX idx_template_tool ON agent_templates(preferred_tool);
    END IF;
END $$;

-- 5. Update existing agents to have mode='claude' (default)
UPDATE agents
SET mode = 'claude'
WHERE mode IS NULL OR mode = '';

-- 6. Verify migration
DO $$
DECLARE
    agent_count INTEGER;
    mode_count INTEGER;
BEGIN
    -- Count total agents
    SELECT COUNT(*) INTO agent_count FROM agents;

    -- Count agents with mode set
    SELECT COUNT(*) INTO mode_count FROM agents WHERE mode IS NOT NULL;

    -- Verify all agents have mode
    IF agent_count != mode_count THEN
        RAISE EXCEPTION 'Migration verification failed: % agents without mode', (agent_count - mode_count);
    END IF;

    RAISE NOTICE 'Migration verified: % agents with mode field', mode_count;
END $$;

COMMIT;
```

**Run Migration**:
```bash
# Execute migration
psql -U postgres -d giljo_mcp < migration_0045_multi_tool.sql

# Expected output:
# BEGIN
# ALTER TABLE
# ALTER TABLE
# CREATE INDEX
# CREATE INDEX
# DO
# UPDATE [count]
# NOTICE: Migration verified: [count] agents with mode field
# COMMIT
```

### Step 4: Update Code

```bash
# Pull latest code
git fetch origin
git checkout v3.1.0

# Or for development:
git pull origin master

# Verify version
cat version.txt
# Expected: 3.1.0
```

### Step 5: Re-seed Templates

Update default templates with multi-tool configuration:

```bash
# Run template seeding script
python scripts/seed_multi_tool_templates.py

# Expected output:
# Seeding multi-tool agent templates...
# - Orchestrator (preferred_tool: claude)
# - Analyzer (preferred_tool: claude)
# - Implementer (preferred_tool: codex)
# - Tester (preferred_tool: gemini)
# - Reviewer (preferred_tool: claude)
# - Documenter (preferred_tool: gemini)
# Templates seeded successfully.
```

**Seeding Script** (`scripts/seed_multi_tool_templates.py`):

```python
"""
Seed multi-tool agent templates.
"""

import asyncio
from src.giljo_mcp.database import DatabaseManager
from src.giljo_mcp.models import AgentTemplate
from src.giljo_mcp.utils import generate_uuid

MULTI_TOOL_TEMPLATES = [
    {
        "role": "orchestrator",
        "preferred_tool": "claude",
        "content": "[Template content...]"
    },
    {
        "role": "analyzer",
        "preferred_tool": "claude",
        "content": "[Template content...]"
    },
    {
        "role": "implementer",
        "preferred_tool": "codex",
        "content": "[Template content...]"
    },
    {
        "role": "tester",
        "preferred_tool": "gemini",
        "content": "[Template content...]"
    },
    {
        "role": "reviewer",
        "preferred_tool": "claude",
        "content": "[Template content...]"
    },
    {
        "role": "documenter",
        "preferred_tool": "gemini",
        "content": "[Template content...]"
    }
]


async def seed_templates():
    """Seed multi-tool templates."""
    db_manager = DatabaseManager(database_url="postgresql://postgres@localhost/giljo_mcp")

    async with db_manager.get_session_async() as session:
        for template_data in MULTI_TOOL_TEMPLATES:
            # Check if template exists
            existing = await session.execute(
                select(AgentTemplate).filter(
                    AgentTemplate.role == template_data["role"],
                    AgentTemplate.tenant_key == "system"
                )
            )

            if existing.scalar_one_or_none():
                print(f"Template {template_data['role']} already exists, skipping...")
                continue

            # Create template
            template = AgentTemplate(
                id=generate_uuid(),
                tenant_key="system",
                role=template_data["role"],
                preferred_tool=template_data["preferred_tool"],
                content=template_data["content"],
                category="role",
                is_active=True
            )

            session.add(template)
            print(f"Seeded template: {template_data['role']} (tool: {template_data['preferred_tool']})")

        await session.commit()

    print("Templates seeded successfully.")


if __name__ == "__main__":
    asyncio.run(seed_templates())
```

### Step 6: Restart Services

```bash
# Start API server
python api/run_api.py &

# Wait for API to start
sleep 5

# Verify API running
curl http://localhost:7272/health

# Expected: {"status": "healthy", "version": "3.1.0"}

# Start frontend (if standalone)
cd frontend/
npm run serve &

# Verify frontend running
curl http://localhost:7274

# Expected: HTML content
```

### Step 7: Verify Functionality

**Test multi-tool agent spawning**:

```bash
# Test API endpoint
curl -X POST http://localhost:7272/api/v1/agents \
  -H "Content-Type: application/json" \
  -d '{
    "project_id": "test_project",
    "agent_name": "Implementer-001",
    "role": "implementer",
    "mission": "Test mission"
  }'

# Expected response:
# {
#   "id": "agent_abc123",
#   "name": "Implementer-001",
#   "mode": "codex",  ← Should match template's preferred_tool
#   "job_id": "job_xyz789",
#   ...
# }
```

**Test MCP coordination**:

```bash
# Test acknowledge_job endpoint
curl -X POST http://localhost:7272/mcp/acknowledge_job \
  -H "Content-Type: application/json" \
  -d '{
    "job_id": "job_xyz789",
    "agent_id": "agent_abc123",
    "tenant_key": "test_tenant"
  }'

# Expected response:
# {
#   "success": true,
#   "message": "Job acknowledged",
#   "status": "in_progress"
# }
```

**Test dashboard**:

1. Open browser: `http://localhost:7274`
2. Login with admin credentials
3. Navigate to "Job Queue" tab
4. Verify job appears with correct tool badge (Codex)
5. Verify agent status updates in real-time

---

## Migration Script

Complete migration script for production deployment:

**File**: `migration_0045_multi_tool.sql`

```sql
-- Multi-Tool Agent Orchestration Migration
-- Handover: 0045
-- Version: 3.1.0
-- Date: 2025-10-25

-- ============================================================================
-- PART 1: Schema Changes
-- ============================================================================

BEGIN;

-- Add job_id to agents (links to MCPAgentJob)
ALTER TABLE agents
ADD COLUMN IF NOT EXISTS job_id VARCHAR(36) NULL;

COMMENT ON COLUMN agents.job_id IS 'Links to mcp_agent_jobs.id for MCP coordination';

-- Add mode to agents (tool identifier)
ALTER TABLE agents
ADD COLUMN IF NOT EXISTS mode VARCHAR(20) DEFAULT 'claude';

COMMENT ON COLUMN agents.mode IS 'AI tool used: claude | codex | gemini | cursor | windsurf';

-- Create indexes
CREATE INDEX IF NOT EXISTS idx_agent_job_id ON agents(job_id);
CREATE INDEX IF NOT EXISTS idx_agent_mode ON agents(mode);

-- Add preferred_tool to agent_templates
DO $$
BEGIN
    IF NOT EXISTS (
        SELECT 1 FROM information_schema.columns
        WHERE table_name = 'agent_templates'
        AND column_name = 'preferred_tool'
    ) THEN
        ALTER TABLE agent_templates
        ADD COLUMN preferred_tool VARCHAR(20) DEFAULT 'claude';

        COMMENT ON COLUMN agent_templates.preferred_tool IS 'Preferred AI tool for this template';

        CREATE INDEX idx_template_tool ON agent_templates(preferred_tool);
    END IF;
END $$;

COMMIT;

-- ============================================================================
-- PART 2: Data Migration
-- ============================================================================

BEGIN;

-- Update existing agents to have default mode
UPDATE agents
SET mode = 'claude'
WHERE mode IS NULL OR mode = '';

-- Update existing templates to have default preferred_tool
UPDATE agent_templates
SET preferred_tool = 'claude'
WHERE preferred_tool IS NULL OR preferred_tool = '';

COMMIT;

-- ============================================================================
-- PART 3: Verification
-- ============================================================================

DO $$
DECLARE
    agent_count INTEGER;
    mode_count INTEGER;
    template_count INTEGER;
    tool_count INTEGER;
BEGIN
    -- Verify agents
    SELECT COUNT(*) INTO agent_count FROM agents;
    SELECT COUNT(*) INTO mode_count FROM agents WHERE mode IS NOT NULL AND mode != '';

    IF agent_count != mode_count THEN
        RAISE EXCEPTION 'Agent migration failed: % agents without mode', (agent_count - mode_count);
    END IF;

    -- Verify templates
    SELECT COUNT(*) INTO template_count FROM agent_templates;
    SELECT COUNT(*) INTO tool_count FROM agent_templates WHERE preferred_tool IS NOT NULL AND preferred_tool != '';

    IF template_count != tool_count THEN
        RAISE EXCEPTION 'Template migration failed: % templates without preferred_tool', (template_count - tool_count);
    END IF;

    -- Success
    RAISE NOTICE '✅ Migration verified successfully:';
    RAISE NOTICE '   - % agents with mode field', mode_count;
    RAISE NOTICE '   - % templates with preferred_tool field', tool_count;
END $$;
```

---

## Rollback Procedure

If deployment fails, follow this rollback procedure:

### Step 1: Stop Services

```bash
# Stop all services
pkill -f "uvicorn api.app:app"
pkill -f "npm run serve"
```

### Step 2: Restore Database Backup

```bash
# Find latest backup
ls -lht /backups/giljo_mcp/ | head -5

# Restore backup (DESTRUCTIVE - all data since backup will be lost)
gunzip /backups/giljo_mcp/backup_pre_deployment_YYYYMMDD_HHMMSS.sql.gz
psql -U postgres -d giljo_mcp < /backups/giljo_mcp/backup_pre_deployment_YYYYMMDD_HHMMSS.sql

# Verify restoration
psql -U postgres -d giljo_mcp -c "SELECT version FROM schema_migrations ORDER BY version DESC LIMIT 1"

# Expected: Version before migration
```

### Step 3: Revert Code

```bash
# Revert to previous version
git checkout v3.0.0  # Or previous stable version

# Verify version
cat version.txt
# Expected: 3.0.0
```

### Step 4: Restart Services

```bash
# Restart API
python api/run_api.py &

# Restart frontend
cd frontend/
npm run serve &

# Verify services
curl http://localhost:7272/health
curl http://localhost:7274
```

### Step 5: Verify Rollback

```bash
# Test agent spawning (should use old single-tool logic)
curl -X POST http://localhost:7272/api/v1/agents \
  -H "Content-Type: application/json" \
  -d '{
    "project_id": "test_project",
    "agent_name": "Implementer-001",
    "mission": "Test mission"
  }'

# Expected: Agent created without mode/job_id fields
```

---

## Production Configuration

Optimize configuration for production deployment.

### Database Configuration

**PostgreSQL tuning** (`postgresql.conf`):

```ini
# Connection pooling
max_connections = 200

# Memory settings
shared_buffers = 256MB
effective_cache_size = 1GB
work_mem = 16MB

# Query performance
random_page_cost = 1.1  # For SSD
effective_io_concurrency = 200

# Logging
log_min_duration_statement = 1000  # Log slow queries (> 1 second)
```

### Redis Configuration

**Redis caching** (`redis.conf`):

```ini
# Memory limit
maxmemory 512mb
maxmemory-policy allkeys-lru  # Evict least recently used keys

# Persistence (optional for caching)
save ""  # Disable persistence (cache-only mode)

# Connection
bind 127.0.0.1
port 6379
```

### API Server Configuration

**Uvicorn settings** (`api/run_api.py`):

```python
import uvicorn

if __name__ == "__main__":
    uvicorn.run(
        "api.app:app",
        host="0.0.0.0",
        port=7272,
        workers=4,  # 2x CPU cores
        log_level="info",
        access_log=True,
        use_colors=False,  # Disable colors for log parsing
        proxy_headers=True,  # If behind reverse proxy
        forwarded_allow_ips="*"  # If behind reverse proxy
    )
```

### Environment Variables

**Production `.env`**:

```bash
# Environment
NODE_ENV=production
PYTHON_ENV=production

# Database (use connection pooling)
DATABASE_URL=postgresql://postgres:password@localhost:5432/giljo_mcp
DATABASE_POOL_SIZE=20
DATABASE_MAX_OVERFLOW=10

# Redis
REDIS_URL=redis://localhost:6379/0
REDIS_POOL_SIZE=10

# API Server
API_HOST=0.0.0.0
API_PORT=7272
API_WORKERS=4

# Frontend
FRONTEND_PORT=7274

# Security
SECRET_KEY=<generate-strong-key>  # Use: openssl rand -hex 32
JWT_EXPIRATION_HOURS=24

# Multi-tool orchestration
SUPPORTED_TOOLS=claude,codex,gemini
DEFAULT_TOOL=claude
MCP_CHECKPOINT_INTERVAL_MINUTES=10
MCP_JOB_TIMEOUT_MINUTES=120

# Monitoring
LOG_LEVEL=INFO
ENABLE_METRICS=true
METRICS_PORT=9090
```

---

## Monitoring

Set up monitoring for multi-tool orchestration system.

### Key Metrics to Track

**1. Agent Spawning Rate**:
```python
# Prometheus metric
agent_spawn_total = Counter(
    'agent_spawn_total',
    'Total agents spawned',
    ['tool', 'role', 'status']
)

# Track spawns
agent_spawn_total.labels(tool='codex', role='implementer', status='success').inc()
```

**2. Job Completion Rate**:
```python
job_completion_total = Counter(
    'job_completion_total',
    'Total jobs completed',
    ['tool', 'status']
)

job_completion_duration = Histogram(
    'job_completion_duration_seconds',
    'Job completion time',
    ['tool', 'role']
)

# Track completions
job_completion_total.labels(tool='gemini', status='completed').inc()
job_completion_duration.labels(tool='gemini', role='tester').observe(1800)  # 30 minutes
```

**3. MCP Coordination Metrics**:
```python
mcp_tool_calls = Counter(
    'mcp_tool_calls_total',
    'MCP tool invocations',
    ['tool_name', 'status']
)

# Track MCP calls
mcp_tool_calls.labels(tool_name='acknowledge_job', status='success').inc()
```

**4. Cost Tracking**:
```python
agent_cost_total = Counter(
    'agent_cost_total_dollars',
    'Total cost in dollars',
    ['tool']
)

# Track costs
agent_cost_total.labels(tool='claude').inc(2.50)  # $2.50 per job
agent_cost_total.labels(tool='codex').inc(1.00)
agent_cost_total.labels(tool='gemini').inc(0.00)  # Free tier
```

### Monitoring Dashboard

**Grafana Dashboard** (JSON configuration):

```json
{
  "dashboard": {
    "title": "Multi-Tool Agent Orchestration",
    "panels": [
      {
        "title": "Agent Spawns by Tool",
        "type": "graph",
        "targets": [
          {
            "expr": "rate(agent_spawn_total[5m])",
            "legendFormat": "{{tool}}"
          }
        ]
      },
      {
        "title": "Job Completion Rate",
        "type": "graph",
        "targets": [
          {
            "expr": "rate(job_completion_total{status='completed'}[5m])",
            "legendFormat": "{{tool}}"
          }
        ]
      },
      {
        "title": "Avg Job Duration by Tool",
        "type": "graph",
        "targets": [
          {
            "expr": "avg(job_completion_duration_seconds) by (tool)",
            "legendFormat": "{{tool}}"
          }
        ]
      },
      {
        "title": "Total Cost by Tool",
        "type": "stat",
        "targets": [
          {
            "expr": "sum(agent_cost_total_dollars) by (tool)"
          }
        ]
      }
    ]
  }
}
```

### Log Aggregation

**Collect logs** with structured logging:

```python
import logging
import json

# Configure structured logging
logging.basicConfig(
    format='%(message)s',
    level=logging.INFO
)

logger = logging.getLogger(__name__)

def log_agent_spawn(agent_id, tool, role, status):
    """Log agent spawn event (structured JSON)."""
    logger.info(json.dumps({
        "event": "agent_spawn",
        "agent_id": agent_id,
        "tool": tool,
        "role": role,
        "status": status,
        "timestamp": datetime.now(timezone.utc).isoformat()
    }))

def log_job_completion(job_id, tool, duration_seconds, status):
    """Log job completion event."""
    logger.info(json.dumps({
        "event": "job_completion",
        "job_id": job_id,
        "tool": tool,
        "duration_seconds": duration_seconds,
        "status": status,
        "timestamp": datetime.now(timezone.utc).isoformat()
    }))
```

**Query logs** with ELK stack or similar:

```bash
# Find all Codex agent spawns
cat logs/api.log | jq 'select(.event == "agent_spawn" and .tool == "codex")'

# Calculate average job duration by tool
cat logs/api.log | jq 'select(.event == "job_completion") | {tool, duration_seconds}' | jq -s 'group_by(.tool) | map({tool: .[0].tool, avg_duration: (map(.duration_seconds) | add / length)})'
```

### Alerting

**Setup alerts** for critical conditions:

```yaml
# alerting.yml (Prometheus AlertManager)
groups:
  - name: multi_tool_orchestration
    interval: 1m
    rules:
      # Alert if job failure rate > 10%
      - alert: HighJobFailureRate
        expr: |
          (rate(job_completion_total{status="failed"}[5m]) /
           rate(job_completion_total[5m])) > 0.1
        for: 5m
        labels:
          severity: warning
        annotations:
          summary: "High job failure rate: {{ $value }}%"
          description: "Tool {{ $labels.tool }} has {{ $value }}% failure rate"

      # Alert if no jobs completed in 1 hour
      - alert: NoJobsCompleted
        expr: |
          rate(job_completion_total{status="completed"}[1h]) == 0
        for: 1h
        labels:
          severity: critical
        annotations:
          summary: "No jobs completed in 1 hour"
          description: "System may be stuck or rate-limited"

      # Alert if cost exceeds budget
      - alert: CostBudgetExceeded
        expr: |
          sum(agent_cost_total_dollars) > 100  # $100/day budget
        labels:
          severity: warning
        annotations:
          summary: "Daily cost budget exceeded"
          description: "Total cost: ${{ $value }}"
```

---

## Troubleshooting

Common deployment issues and solutions.

### Issue: Migration Fails with Constraint Violation

**Error**:
```
ERROR: duplicate key value violates unique constraint "uq_agent_project_name"
```

**Cause**: Duplicate agent names in project.

**Solution**:
```sql
-- Find duplicates
SELECT project_id, name, COUNT(*)
FROM agents
GROUP BY project_id, name
HAVING COUNT(*) > 1;

-- Remove duplicates (keep most recent)
DELETE FROM agents a
WHERE id NOT IN (
    SELECT MAX(id)
    FROM agents
    GROUP BY project_id, name
);

-- Re-run migration
```

### Issue: Templates Not Seeded

**Error**:
```
Template 'implementer' not found
```

**Cause**: Template seeding script didn't run or failed.

**Solution**:
```bash
# Check existing templates
psql -U postgres -d giljo_mcp -c "SELECT role, preferred_tool FROM agent_templates WHERE tenant_key = 'system'"

# If empty, run seeding manually
python scripts/seed_multi_tool_templates.py

# Verify
psql -U postgres -d giljo_mcp -c "SELECT role, preferred_tool FROM agent_templates WHERE tenant_key = 'system'"
```

### Issue: Agents Stuck in "Waiting Acknowledgment"

**Symptoms**: All legacy CLI agents show "Waiting for CLI" status indefinitely.

**Cause**: MCP endpoint not accessible or agent not calling acknowledge_job.

**Solution**:
```bash
# 1. Verify MCP endpoint accessible
curl http://localhost:7272/mcp/health

# 2. Check API logs for errors
tail -f logs/api.log | grep "mcp"

# 3. Manually acknowledge job for testing
curl -X POST http://localhost:7272/mcp/acknowledge_job \
  -H "Content-Type: application/json" \
  -d '{
    "job_id": "<job_id>",
    "agent_id": "<agent_id>",
    "tenant_key": "<tenant_key>"
  }'

# 4. If works, agent needs to call acknowledge_job
```

### Issue: High Database CPU Usage

**Symptoms**: Database CPU at 100%, slow queries.

**Cause**: Missing indexes or inefficient queries.

**Solution**:
```sql
-- Find slow queries
SELECT
    pid,
    now() - pg_stat_activity.query_start AS duration,
    query
FROM pg_stat_activity
WHERE state = 'active'
ORDER BY duration DESC;

-- Check missing indexes
SELECT
    schemaname,
    tablename,
    attname,
    n_distinct,
    correlation
FROM pg_stats
WHERE schemaname = 'public'
    AND correlation < 0.5
    AND n_distinct > 100;

-- Add missing indexes
CREATE INDEX CONCURRENTLY idx_agents_mode_tenant ON agents(mode, tenant_key);
CREATE INDEX CONCURRENTLY idx_jobs_status_created ON mcp_agent_jobs(status, created_at);
```

---

**Document Version**: 1.0
**Last Updated**: 2025-10-25
**Next**: [API_REFERENCE.md](./API_REFERENCE.md)
