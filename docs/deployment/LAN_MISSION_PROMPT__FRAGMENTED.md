# LAN Deployment Mission Prompt

## Mission Overview

Transform GiljoAI MCP from localhost-only operation to **production-ready LAN deployment** for internal network access. Enable team collaboration on trusted networks with proper security, authentication, and monitoring.

**Target:** Windows, Linux, and macOS LAN deployments
**Timeline:** 4 weeks (2 sprints)
**Success Criteria:** Multiple team members accessing from different machines on the same network

---

## Critical Context

### Current State
- ✅ **Localhost mode fully functional** - Development environment working well
- ✅ **Architecture ready** - Multi-tenant, async, PostgreSQL 18, FastAPI + Vue 3
- ✅ **Documentation complete** - Comprehensive LAN guides and scripts created
- ⚠️ **Parallel development ongoing** - User is actively fixing agent workflows, messaging, products, tasks, projects

### Important Constraints

**🚨 CRITICAL: Expect App Restarts**
- Backend and frontend will restart randomly during your work
- User is fixing agent flow, messaging, products/tasks/projects concurrently
- Your changes must be resilient to app restarts
- Test frequently - don't assume the app will stay running
- Save configuration changes immediately
- Use git commits frequently to checkpoint progress

**File Coordination Required:**
- `api/app.py` - You: middleware/CORS (lines 292-330), User: endpoints (lines 400-600)
- `config.yaml` - You: network section, User: feature flags
- `.env` - You: API keys/CORS, User: database/features
- **Strategy:** Work in different sections, commit often, communicate conflicts

---

## Your Mission

### Phase 1: Security Hardening (Week 1-2)

**Critical Security Fixes (7 items from analysis):**

1. **Fix Default Host Binding**
   - File: `api/run_api.py` line 119
   - Change: Default from `0.0.0.0` to `127.0.0.1`
   - Add: Mode detection to enable `0.0.0.0` only when `mode: server` in config.yaml
   - Test: Verify localhost mode stays on 127.0.0.1, server mode binds to 0.0.0.0

2. **Activate Rate Limiting**
   - File: `api/app.py`
   - Activate: `RateLimitMiddleware` (exists but not enabled)
   - Configure: 60 requests/minute for LAN (moderate)
   - Test: Verify rate limiting with burst tests

3. **Harden CORS Configuration**
   - File: `api/app.py` lines 292-318
   - Remove: Wildcard patterns (`http://localhost:*`)
   - Add: Explicit allowed origins from config
   - LAN mode: Allow specific network IPs only
   - Test: Verify cross-origin requests work from allowed IPs, rejected from others

4. **Enable API Key Authentication**
   - File: `config.yaml` line 33
   - Change: `api_keys_required: false` → `true` for LAN mode
   - Generate: Strong API keys using `secrets.token_urlsafe(32)`
   - Distribute: Document API key distribution process
   - Test: Verify endpoints reject requests without valid API key

5. **Add Security Headers Middleware**
   - File: `api/middleware.py` (create new class)
   - Add: `SecurityHeadersMiddleware` with:
     - X-Frame-Options: DENY
     - X-Content-Type-Options: nosniff
     - X-XSS-Protection: 1; mode=block
     - Content-Security-Policy (basic)
   - Enable: Add to middleware stack in `api/app.py`
   - Test: Verify headers present in responses

6. **Remove Default Tenant Fallback (Server Mode Only)**
   - File: `api/dependencies.py` lines 36-40
   - Change: Return 401 when tenant key missing in server mode
   - Keep: Fallback for localhost mode
   - Test: Verify tenant isolation enforced

7. **Encrypt API Keys at Rest**
   - File: `src/giljo_mcp/auth.py` lines 69-78
   - Add: Encryption for API keys in `~/.giljo-mcp/api_keys.json`
   - Use: `cryptography` library with Fernet symmetric encryption
   - Test: Verify keys stored encrypted, decrypted on load

### Phase 2: Network Configuration (Week 2)

**Network Setup:**

1. **Configure Server Mode**
   - File: `config.yaml`
   - Add server mode configuration section
   - Set network binding, ports, SSL settings
   - Document configuration options

2. **Firewall Configuration**
   - Platform: Windows, Linux, macOS
   - Rules: Allow 7272 (API), 7274 (Frontend), Block 5432 (PostgreSQL)
   - Scripts: Use existing scripts in `scripts/deployment/`
   - Test: Verify API accessible from network, database not accessible

3. **Database Network Security**
   - File: PostgreSQL `pg_hba.conf`
   - Restrict: Connections to 127.0.0.1 only
   - Add: SSL/TLS support (optional for LAN, recommended)
   - File: `src/giljo_mcp/database.py`
   - Add: SSL connection parameter support
   - Test: Verify database only accessible from localhost

4. **Update Frontend for Network Access**
   - File: `frontend/src/config/api.js`
   - Support: Dynamic API URL based on deployment
   - Environment: `VITE_API_URL` for network deployments
   - Test: Frontend connects to API from different machine

### Phase 3: Testing & Validation (Week 3)

**Run Comprehensive Tests:**

1. **Network Connectivity Tests**
   - File: `tests/integration/test_network_connectivity.py` (already created)
   - Run: All 8 network connectivity tests
   - Verify: API accessible from LAN IP addresses
   - Test: WebSocket connections from remote clients
   - Measure: Network latency benchmarks

2. **API Key Authentication Tests**
   - File: `tests/integration/test_server_mode_auth.py` (already created)
   - Run: All 8 authentication tests
   - Verify: API key requirement enforced
   - Test: Invalid key rejection, tenant isolation

3. **Multi-Client Load Tests**
   - Simulate: 5-10 concurrent clients from different machines
   - Test: Database connection pooling under load
   - Measure: Performance degradation with network latency
   - Verify: No connection pool exhaustion

4. **Security Validation**
   - Checklist: Use `docs/deployment/LAN_SECURITY_CHECKLIST.md`
   - Verify: All 81 checklist items completed
   - Test: Penetration testing basics (invalid inputs, brute force attempts)
   - Document: Any security gaps found

### Phase 4: Documentation & Handoff (Week 4)

**Deliverables:**

1. **Update Configuration Documentation**
   - Document: Final config.yaml settings for LAN mode
   - Create: Example .env file for LAN deployment
   - Write: API key generation and distribution guide

2. **Create Deployment Runbook**
   - Step-by-step: How to deploy LAN from scratch
   - Troubleshooting: Common issues and solutions
   - Platform-specific: Windows, Linux, macOS instructions

3. **Performance Benchmarks**
   - Document: Baseline performance metrics
   - Record: Latency, throughput, concurrent users supported
   - Compare: localhost vs LAN performance

4. **Handoff to User**
   - Demo: Live demonstration of LAN deployment
   - Training: How to add new users (API key distribution)
   - Support: Known issues and workarounds

---

## Key Resources (READ THESE FIRST)

### Primary Documentation
1. **`docs/deployment/LAN_DEPLOYMENT_GUIDE.md`** - Complete LAN deployment guide (120KB)
2. **`docs/deployment/LAN_SECURITY_CHECKLIST.md`** - 81-point security validation (22KB)
3. **`docs/CROSS_PLATFORM_GUIDE.md`** - Platform-specific instructions (6.8KB)
4. **`docs/PLATFORM_TESTING_MATRIX.md`** - Testing status by platform (4.5KB)

### Analysis Documents (Background)
5. **System Architecture Analysis** - In session memory from system-architect agent
6. **Security Assessment** - In session memory from network-security-engineer agent
7. **Testing Strategy** - `tests/SERVER_MODE_TESTING_STRATEGY.md`

### Deployment Scripts (Use These)
8. **`scripts/deployment/deploy_lan_windows.ps1`** - Automated Windows deployment
9. **`scripts/install_dependencies_windows.ps1`** - Dependency installer (Windows)
10. **`scripts/install_dependencies_linux.sh`** - Dependency installer (Linux)
11. **`scripts/install_dependencies_macos.sh`** - Dependency installer (macOS)

### Test Files (Run These)
12. **`tests/integration/test_network_connectivity.py`** - 8 network tests
13. **`tests/integration/test_server_mode_auth.py`** - 8 authentication tests

### Configuration Templates
14. **`config.yaml`** - Main configuration file
15. **`.env.example`** - Environment variables template

---

## Success Criteria

### Technical Validation
- ✅ API accessible from 3+ different machines on LAN
- ✅ WebSocket connections work from remote clients
- ✅ API key authentication enforced (100% rejection without key)
- ✅ Rate limiting active (verified with burst tests)
- ✅ Security headers present in all responses
- ✅ PostgreSQL accessible only from localhost
- ✅ Firewall rules configured correctly on all platforms
- ✅ All 81 security checklist items completed
- ✅ Network latency < 50ms average (LAN)
- ✅ 10+ concurrent clients supported

### User Acceptance
- ✅ User can access from their laptop while another agent works on desktop
- ✅ API keys distributed to team members
- ✅ No disruption to ongoing localhost development
- ✅ App restarts don't break LAN configuration

### Documentation
- ✅ Complete deployment runbook
- ✅ API key management guide
- ✅ Troubleshooting guide with solutions
- ✅ Performance benchmarks documented

---

## Agent Team Composition

### Recommended Agents

**Lead: orchestrator-coordinator**
- Coordinate overall mission
- Track progress across agents
- Resolve conflicts between agents
- Report status to user

**Security: network-security-engineer**
- Implement all 7 security fixes
- Configure firewalls (Windows, Linux, macOS)
- Validate security checklist
- Conduct security testing

**Architecture: system-architect**
- Review configuration changes for platform compatibility
- Ensure network architecture is sound
- Database network security
- Resolve architectural questions

**Implementation: tdd-implementor** (optional, if code changes needed)
- Implement middleware changes
- Add security headers
- Fix configuration loading logic
- Write unit tests for changes

**Testing: backend-integration-tester**
- Run network connectivity tests
- Run authentication tests
- Load testing with concurrent clients
- Performance benchmarking

**Documentation: documentation-manager**
- Update deployment runbook
- Create API key distribution guide
- Document performance benchmarks
- Session summary and devlog

---

## Coordination Strategy

### Daily Standups (Not Required, but Helpful)
- What files are you editing today?
- Any blockers or conflicts discovered?
- Test results and findings
- Coordination needed with user's workflow changes?

### Git Workflow
```bash
# Create feature branch for LAN work
git checkout -b feature/lan-deployment

# Commit frequently (every 30-60 minutes)
git add .
git commit -m "LAN: [specific change]"

# Pull user's changes regularly
git fetch origin
git rebase origin/master  # Or merge if conflicts

# Push your work
git push origin feature/lan-deployment
```

### Conflict Resolution
- If user is editing same file section: **communicate immediately**
- If app restarts during testing: **restart tests, verify config persisted**
- If merge conflict: **prioritize user's workflow changes, adapt your LAN changes**

---

## Risk Mitigation

### Known Risks

**Risk 1: App Restarts During Configuration**
- Mitigation: Save config changes immediately, test after each change
- Recovery: Re-apply configuration, verify with quick test

**Risk 2: Merge Conflicts with User's Work**
- Mitigation: Work in different file sections, commit frequently
- Recovery: Coordinate with user, merge carefully

**Risk 3: Network Firewall Blocks Testing**
- Mitigation: Document firewall rules clearly, test on multiple machines
- Recovery: Adjust firewall rules, re-test

**Risk 4: API Key Distribution Complexity**
- Mitigation: Create simple, documented process
- Recovery: Simplify distribution, use secure channels

**Risk 5: Performance Degradation**
- Mitigation: Benchmark early, monitor connection pooling
- Recovery: Tune database pool sizes, adjust rate limiting

---

## Definition of Done

### Phase 1 Complete When:
- ✅ All 7 security fixes implemented
- ✅ Unit tests passing
- ✅ Code reviewed and committed

### Phase 2 Complete When:
- ✅ Network configuration working on Windows, Linux, macOS
- ✅ Firewall rules tested and documented
- ✅ Frontend connects from remote machine

### Phase 3 Complete When:
- ✅ All network connectivity tests passing
- ✅ All authentication tests passing
- ✅ Load tests with 10+ concurrent clients successful
- ✅ Security checklist 100% complete

### Phase 4 Complete When:
- ✅ Documentation complete and reviewed
- ✅ User demo successful
- ✅ Handoff accepted by user

### Mission Complete When:
- ✅ User can access GiljoAI MCP from 3+ different machines on LAN
- ✅ Security validated and documented
- ✅ Performance benchmarks meet targets
- ✅ Zero security vulnerabilities in LAN deployment
- ✅ Ready for production LAN use

---

## Important Notes

### What NOT to Do
- ❌ Don't modify workflow-related code (products, tasks, projects, agents, messaging)
- ❌ Don't assume app will stay running - test frequently
- ❌ Don't skip security checklist items
- ❌ Don't enable WAN features (reverse proxy, JWT, Redis) - that's Phase 2
- ❌ Don't modify database schema - focus on network/security only

### What TO Do
- ✅ Read all documentation before starting
- ✅ Commit frequently (every 30-60 minutes)
- ✅ Test after each major change
- ✅ Coordinate file edits with user's concurrent work
- ✅ Document everything (configs, issues, solutions)
- ✅ Ask questions if anything is unclear
- ✅ Focus on security first, convenience second

---

## Quick Start

### Step 1: Read Documentation (30 minutes)
```bash
# Read these in order:
1. docs/deployment/LAN_DEPLOYMENT_GUIDE.md
2. docs/deployment/LAN_SECURITY_CHECKLIST.md
3. docs/CROSS_PLATFORM_GUIDE.md
```

### Step 2: Review Current State (15 minutes)
```bash
# Check current configuration
cat config.yaml
cat .env

# Review current security
grep "api_keys_required" config.yaml
grep "ssl_enabled" config.yaml
```

### Step 3: Create Feature Branch (5 minutes)
```bash
git checkout -b feature/lan-deployment
git push -u origin feature/lan-deployment
```

### Step 4: Begin Phase 1 Security Fixes
Start with highest-priority security fix first (API key authentication).

---

## Questions? Blockers?

- **Orchestrator**: Coordinate with other agents
- **User**: Ask directly if configuration decision needed
- **Documentation**: Reference guides in `docs/deployment/`

---

## Final Reminders

**This is Phase 1 of 2:**
- LAN deployment is the foundation
- WAN deployment will build on this later
- Focus on security, testing, documentation

**Success = User can collaborate with team on LAN**
- Multiple machines accessing system
- Secure, fast, reliable
- Well-documented and maintainable

**You've got this! All the analysis and planning is done. Now execute.**

---

*Mission created: 2025-10-05*
*Target completion: 4 weeks from start*
*Priority: HIGH*
*Complexity: MEDIUM*
*Risk: LOW (with proper coordination)*
