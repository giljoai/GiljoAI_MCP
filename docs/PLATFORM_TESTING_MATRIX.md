# Platform Testing Matrix

**GiljoAI MCP Cross-Platform Testing Coverage**

Last Updated: 2025-10-04

---

## Testing Status Legend

- ✅ Fully Tested: Extensively tested, production-ready
- ⚠️ Compatible: Should work, limited testing
- 🔄 In Progress: Currently being tested
- ❌ Not Supported: Known incompatibilities
- ❓ Unknown: Not yet tested

---

## Operating Systems Support

| Platform | Version | Status | Installation | API | Database | WebSocket | Frontend | Service | Notes |
|----------|---------|--------|--------------|-----|----------|-----------|----------|---------|-------|
| Windows 10 | 21H2+ | ✅ | ✅ | ✅ | ✅ | ✅ | ✅ | ✅ | Primary development |
| Windows 11 | All | ✅ | ✅ | ✅ | ✅ | ✅ | ✅ | ✅ | Production ready |
| Windows Server 2019 | All | ⚠️ | ⚠️ | ⚠️ | ⚠️ | ⚠️ | ⚠️ | ⚠️ | Compatible |
| Windows Server 2022 | All | ⚠️ | ⚠️ | ⚠️ | ⚠️ | ⚠️ | ⚠️ | ⚠️ | Recommended server |
| Ubuntu 20.04 LTS | Focal | ⚠️ | ⚠️ | ⚠️ | ⚠️ | ⚠️ | ⚠️ | ⚠️ | systemd + apt |
| Ubuntu 22.04 LTS | Jammy | ⚠️ | ⚠️ | ⚠️ | ⚠️ | ⚠️ | ⚠️ | ⚠️ | Recommended Linux |
| Debian 11 | Bullseye | ⚠️ | ⚠️ | ⚠️ | ⚠️ | ⚠️ | ⚠️ | ⚠️ | systemd + apt |
| Debian 12 | Bookworm | ⚠️ | ⚠️ | ⚠️ | ⚠️ | ⚠️ | ⚠️ | ⚠️ | Latest Debian |
| RHEL 8/9 | All | ⚠️ | ⚠️ | ⚠️ | ⚠️ | ⚠️ | ⚠️ | ⚠️ | systemd + dnf |
| macOS 12+ | Monterey+ | ⚠️ | ⚠️ | ⚠️ | ⚠️ | ⚠️ | ⚠️ | ⚠️ | Homebrew recommended |

---

## Feature Testing Status

### Core Components

| Feature | Windows | Linux | macOS | Notes |
|---------|---------|-------|-------|-------|
| CLI Installer | ✅ | ⚠️ | ⚠️ | Windows fully tested |
| Database Setup | ✅ | ⚠️ | ⚠️ | PostgreSQL 18 |
| API Server | ✅ | ⚠️ | ⚠️ | FastAPI + Uvicorn |
| WebSocket | ✅ | ⚠️ | ⚠️ | Real-time comm |
| Frontend | ✅ | ⚠️ | ⚠️ | Vue 3 + Vite |
| MCP Tools | ✅ | ⚠️ | ⚠️ | All 20+ tools |
| Multi-Tenant | ✅ | ⚠️ | ⚠️ | tenant_key isolation |
| Service Manager | ✅ | ⚠️ | ⚠️ | NSSM/systemd/launchd |
| Firewall Config | ✅ | ⚠️ | ⚠️ | Platform scripts |
| SSL/TLS | ❓ | ❓ | ❓ | Not yet tested |

### Path Handling

| Component | Windows | Linux | macOS | Notes |
|-----------|---------|-------|-------|-------|
| pathlib.Path | ✅ | ✅ | ✅ | Cross-platform by design |
| PathResolver | ✅ | ✅ | ✅ | Utility tested |
| File Uploads | ✅ | ⚠️ | ⚠️ | Product vision files |
| Temp Files | ✅ | ⚠️ | ⚠️ | Platform temp dirs |

---

## Known Issues

### Windows
- Path length limit (260): Enable long paths in registry
- Process orphans: Use stop_giljo.bat
- PostgreSQL service: Manual start may be needed

### Linux  
- Port <1024: Use default ports >=1024 or grant capability
- PostgreSQL auth: Change peer to md5 in pg_hba.conf
- Package managers: Scripts detect distro

### macOS
- Gatekeeper: xattr -d com.apple.quarantine
- psycopg2: Install PostgreSQL client libraries
- Homebrew paths: Set PATH correctly

---

## Test Coverage

### Unit Tests

| Component | Coverage | Windows | Linux | macOS |
|-----------|----------|---------|-------|-------|
| MCP Tools | 85% | ✅ | ❓ | ❓ |
| Database | 90% | ✅ | ❓ | ❓ |
| API Endpoints | 80% | ✅ | ❓ | ❓ |
| Orchestrator | 75% | ✅ | ❓ | ❓ |

### Integration Tests

| Suite | Windows | Linux | macOS |
|-------|---------|-------|-------|
| API + DB | ✅ | ❓ | ❓ |
| WebSocket | ✅ | ❓ | ❓ |
| Agent Lifecycle | ✅ | ❓ | ❓ |

---

## Testing Priorities

### High Priority (Next Sprint)
1. Linux testing (Ubuntu 22.04)
2. macOS testing (macOS 14)
3. WAN deployment with SSL/TLS

### Medium Priority
1. Docker deployment
2. Additional Linux distros (RHEL, Fedora)
3. Performance benchmarks

### Low Priority
1. Older platform versions
2. ARM64 architecture

---

## Verification Commands

### Windows
```powershell
python --version
psql --version
node --version
python start_giljo.py --backend-only
Get-NetFirewallRule -DisplayName "GiljoAI*"
```

### Linux
```bash
python3 --version
psql --version
node --version
python3 start_giljo.py --backend-only
sudo ufw status verbose
```

### macOS
```bash
python3 --version
psql --version  
node --version
python3 start_giljo.py --backend-only
sudo pfctl -s rules | grep 7272
```

---

**Last Updated:** 2025-10-04  
**Test Coordinator:** GiljoAI MCP Architecture Team
