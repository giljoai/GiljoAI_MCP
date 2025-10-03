# PHASE 2 AGENT INSTRUCTIONS

## 📝 HOW TO REPORT PROGRESS

### Use PHASE2_AGENT_LOG.jsonl for all status updates

**APPEND** (don't overwrite) a single line JSON object with this format:

```json
{
  "timestamp": "2025-09-26T10:30:00",
  "agent_id": "DOC-01",
  "status": "IN_PROGRESS|COMPLETE|BLOCKED|ERROR",
  "message": "What you did or what happened",
  "deliverables": ["installer/dependencies/docker.py"],
  "blockers": ["Need profile system API clarification"],
  "progress": 45,
  "integration_ready": false
}
```

### Status Values:

- `IN_PROGRESS` - Currently working
- `COMPLETE` - Mission accomplished
- `BLOCKED` - Need help
- `ERROR` - Something failed
- `READY` - Ready for integration

### Example Commands:

```python
# Python append example
import json
from datetime import datetime

log_entry = {
    "timestamp": datetime.now().isoformat(),
    "agent_id": "DOC-01",
    "status": "IN_PROGRESS",
    "message": "Created DockerInstaller class",
    "deliverables": ["installer/dependencies/docker.py"],
    "blockers": [],
    "progress": 30,
    "integration_ready": False
}

with open("PHASE2_AGENT_LOG.jsonl", "a") as f:
    f.write(json.dumps(log_entry) + "\n")
```

```bash
# Bash append example
echo '{"timestamp":"2025-09-26T10:30:00","agent_id":"SVC-01","status":"IN_PROGRESS","message":"Creating service manager","deliverables":[],"blockers":[],"progress":10}' >> PHASE2_AGENT_LOG.jsonl
```

---

## 🎯 PHASE 2 AGENT MISSIONS

### DOC-01: Docker Installer Agent

**Files to create:**

- `installer/dependencies/docker.py`
- `installer/docker/Dockerfile.app`
- `installer/docker/docker-compose.yml`

**Requirements:**

- Follow PostgreSQL/Redis installer pattern
- Docker Desktop download automation
- Container health checks
- docker-compose verification

### SVC-01: Service Manager Agent

**Files to create:**

- `installer/services/service_manager.py`
- `installer/services/windows/giljo_service.py`
- `installer/services/macos/com.giljo.mcp.plist`
- `installer/services/linux/giljo-mcp.service`

**Requirements:**

- Cross-platform service control
- Auto-start on boot
- Status monitoring
- Clean stop/start/restart

### CFG-01: Configuration Manager Agent

**Files to create:**

- `installer/config/config_manager.py`
- `installer/config/templates/.env.local`
- `installer/config/templates/.env.network`
- `installer/config/templates/.env.production`
- `installer/config/templates/.env.containerized`

**Requirements:**

- Profile-based config generation
- Secure credential handling
- Migration from existing configs
- Validation and backup

### TST-01: Testing Agent

**Files to create:**

```
tests/installer/
├── unit/
│   ├── test_profile.py
│   ├── test_postgresql_installer.py
│   ├── test_redis_installer.py
│   ├── test_docker_installer.py
│   └── test_health_checker.py
├── integration/
│   └── test_installation_flow.py
└── conftest.py
```

**Requirements:**

- 90%+ code coverage
- Mock external dependencies
- Cross-platform tests
- Fast execution (<30s)

### INT-01: Integration Agent

**Files to update:**

- `bootstrap.py` - Add all features
- `setup.py` - CLI integration
- `setup_gui.py` - Final GUI polish

**Documentation to create:**

- `docs/installer_user_guide.md`
- `docs/installer_developer_guide.md`
- `docs/installer_troubleshooting.md`

**Requirements:**

- Merge all components
- Resolve conflicts
- End-to-end testing
- Rollback capability

---

## 📊 MONITORING YOUR PROGRESS

The orchestrator will read the JSONL file periodically:

```python
# Orchestrator monitoring script
import json

def read_agent_status():
    with open("PHASE2_AGENT_LOG.jsonl", "r") as f:
        for line in f:
            entry = json.loads(line)
            print(f"[{entry['timestamp']}] {entry['agent_id']}: {entry['status']} - {entry['message']}")
```

---

## 🔗 AVAILABLE APIS FROM PHASE 1

```python
# Profile System
from installer.core.profile import ProfileManager, ProfileType

# Database Installers
from installer.dependencies.postgresql import PostgreSQLInstaller
from installer.dependencies.redis import RedisInstaller

# Health Checks
from installer.core.health import HealthChecker
from installer.core.health_integration import InstallationHealthCheck

# GUI Components
# ProfileSelectionPage in setup_gui.py
```

---

## ⚠️ IMPORTANT NOTES

1. **APPEND ONLY** to PHASE2_AGENT_LOG.jsonl - never overwrite
2. **One JSON object per line** - this is JSONL format
3. **Report frequently** - at least every 30 minutes
4. **Include file paths** in deliverables array
5. **List blockers immediately** - don't wait

---

## 🎮 ORCHESTRATOR WILL RESPOND TO:

- `BLOCKED` status - Will provide help
- `COMPLETE` status - Will verify deliverables
- `ERROR` status - Will assist with debugging
- `READY` status - Will coordinate integration

Start working and append your progress to PHASE2_AGENT_LOG.jsonl!
