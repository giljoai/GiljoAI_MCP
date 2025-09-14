# Docker Deployment Test Plan
## GiljoAI MCP Orchestrator

### Test Overview
This test plan validates the Docker deployment for the GiljoAI MCP Orchestrator system across all components and configurations.

### Success Criteria
All tests must pass for deployment to be considered production-ready:

1. **Build Success** - All containers build without errors
2. **Startup Time** - Full stack operational within 5 seconds
3. **Image Size** - Production images under 500MB each
4. **Data Persistence** - Data survives container restarts
5. **Health Checks** - All services report healthy status
6. **Cross-Platform** - Works on Windows Docker Desktop and Linux
7. **Zero-Config** - Local deployment requires no manual configuration

---

## Test Categories

### 1. Build Tests (`test_build.sh`)
#### 1.1 Backend Container Build
- [ ] Dockerfile.backend exists in docker/
- [ ] Multi-stage build implemented
- [ ] Python 3.11 base image used
- [ ] All dependencies from requirements.txt installed
- [ ] Build completes without errors
- [ ] Final image size < 500MB
- [ ] .dockerignore properly configured

#### 1.2 Frontend Container Build
- [ ] Dockerfile.frontend exists in docker/
- [ ] Multi-stage build (build + nginx)
- [ ] Node 18+ for build stage
- [ ] Nginx alpine for production stage
- [ ] Build completes without errors
- [ ] Final image size < 100MB
- [ ] Static assets properly copied

#### 1.3 Build Time Performance
- [ ] Backend builds in < 3 minutes (fresh)
- [ ] Frontend builds in < 2 minutes (fresh)
- [ ] Rebuild with cache < 30 seconds

### 2. Composition Tests (`test_compose.sh`)
#### 2.1 Docker Compose Files
- [ ] docker-compose.yml exists (base)
- [ ] docker-compose.dev.yml exists (development)
- [ ] docker-compose.prod.yml exists (production)
- [ ] All use version 3.8+
- [ ] Networks properly defined
- [ ] Volumes properly mapped

#### 2.2 Service Orchestration
- [ ] PostgreSQL starts first (depends_on)
- [ ] Backend waits for database
- [ ] Frontend waits for backend
- [ ] All services on same network
- [ ] Port mappings correct:
  - Frontend: 6000
  - Backend API: 6002
  - WebSocket: 6003
  - PostgreSQL: 5432 (internal only)

#### 2.3 Environment Configuration
- [ ] .env.example file provided
- [ ] Environment variables properly passed
- [ ] Database credentials secured
- [ ] API keys configurable
- [ ] CORS settings correct

### 3. Health Check Tests (`test_health.sh`)
#### 3.1 Database Health
- [ ] PostgreSQL accepts connections
- [ ] Database created successfully
- [ ] Tables initialized
- [ ] Connection pooling works
- [ ] Restart recovery works

#### 3.2 Backend Health
- [ ] FastAPI responds on /health
- [ ] Database connection verified
- [ ] WebSocket endpoint active
- [ ] API documentation available (/docs)
- [ ] Authentication working

#### 3.3 Frontend Health
- [ ] Nginx serves static files
- [ ] Vue app loads successfully
- [ ] API proxy configured
- [ ] WebSocket connection established
- [ ] Assets load correctly

#### 3.4 Container Health Checks
- [ ] All containers have HEALTHCHECK
- [ ] Health checks use appropriate intervals
- [ ] Unhealthy containers restart
- [ ] Logs indicate health status

### 4. Persistence Tests (`test_persistence.sh`)
#### 4.1 Database Persistence
- [ ] Data survives container restart
- [ ] Data survives stack restart
- [ ] Volume backup/restore works
- [ ] Migration scripts run once
- [ ] No data loss on upgrade

#### 4.2 File System Persistence
- [ ] Upload directory persists
- [ ] Configuration files persist
- [ ] Log files persist
- [ ] Session data persists

#### 4.3 State Management
- [ ] Active sessions resume
- [ ] Message queue preserved
- [ ] Agent states maintained
- [ ] Project data intact

### 5. Performance Tests (`test_performance.sh`)
#### 5.1 Startup Performance
- [ ] Full stack up in < 5 seconds
- [ ] Database ready in < 2 seconds
- [ ] Backend ready in < 3 seconds
- [ ] Frontend ready in < 1 second

#### 5.2 Resource Usage
- [ ] Memory usage < 2GB total
- [ ] CPU usage reasonable
- [ ] Disk I/O optimized
- [ ] Network traffic efficient

#### 5.3 Concurrent Operations
- [ ] Handles 10 concurrent agents
- [ ] 100 messages/second throughput
- [ ] WebSocket connections stable
- [ ] No memory leaks detected

### 6. Security Tests (`test_security.sh`)
#### 6.1 Network Security
- [ ] Database not exposed externally
- [ ] Internal network isolated
- [ ] HTTPS ready (prod mode)
- [ ] CORS properly configured

#### 6.2 Credential Security
- [ ] No hardcoded passwords
- [ ] Secrets in environment only
- [ ] Default passwords documented
- [ ] Password change documented

#### 6.3 Container Security
- [ ] Non-root users in containers
- [ ] Minimal base images used
- [ ] Security updates applied
- [ ] No unnecessary packages

### 7. Cross-Platform Tests (`test_platforms.sh`)
#### 7.1 Windows Docker Desktop
- [ ] Builds successfully
- [ ] Runs without errors
- [ ] Volumes work correctly
- [ ] Networking functions

#### 7.2 Linux Docker
- [ ] Builds successfully
- [ ] Runs without errors
- [ ] Permissions correct
- [ ] SELinux compatible (if applicable)

#### 7.3 Development Mode
- [ ] Hot reload works (backend)
- [ ] HMR works (frontend)
- [ ] Debug ports accessible
- [ ] Source maps available

### 8. Integration Tests (`test_integration.sh`)
#### 8.1 End-to-End Flow
- [ ] Create project via API
- [ ] Spawn agent successfully
- [ ] Send/receive messages
- [ ] WebSocket updates received
- [ ] UI reflects changes

#### 8.2 MCP Protocol
- [ ] MCP server accessible
- [ ] Commands execute properly
- [ ] Context management works
- [ ] Vision documents load

#### 8.3 External Services
- [ ] Serena MCP integration works
- [ ] External API calls succeed
- [ ] Webhook delivery works
- [ ] Email notifications (if configured)

---

## Test Execution Plan

### Phase 1: Pre-Flight Checks
1. Verify Docker/Docker Compose installed
2. Check port availability (6000-6003)
3. Ensure sufficient disk space (5GB+)
4. Verify directory structure

### Phase 2: Build Testing
1. Run `test_build.sh`
2. Verify all images created
3. Check image sizes
4. Validate build logs

### Phase 3: Composition Testing
1. Run `test_compose.sh`
2. Verify service startup order
3. Check network connectivity
4. Validate environment injection

### Phase 4: Health & Performance
1. Run `test_health.sh`
2. Run `test_performance.sh`
3. Monitor resource usage
4. Check response times

### Phase 5: Persistence & Security
1. Run `test_persistence.sh`
2. Run `test_security.sh`
3. Verify data integrity
4. Check security posture

### Phase 6: Platform Testing
1. Run `test_platforms.sh` on Windows
2. Run `test_platforms.sh` on Linux
3. Test development mode
4. Test production mode

### Phase 7: Integration Testing
1. Run `test_integration.sh`
2. Full workflow validation
3. Error scenario testing
4. Load testing

---

## Test Output Requirements

Each test script should:
1. Output clear pass/fail status
2. Log detailed results to `test_results/`
3. Generate summary report
4. Return appropriate exit codes
5. Be idempotent (can run multiple times)

## Failure Handling

If any test fails:
1. Capture complete logs
2. Document failure reason
3. Suggest remediation steps
4. Create issue for tracking
5. Block deployment until resolved

## Test Automation

Future enhancement:
- GitHub Actions workflow
- Automated nightly builds
- Performance regression tracking
- Security scanning integration
- Deployment gate checks

---

## Sign-Off Criteria

Deployment approved when:
- [ ] All test categories pass
- [ ] Performance meets targets
- [ ] Security scan clean
- [ ] Documentation complete
- [ ] Rollback plan ready

**Test Plan Version:** 1.0.0
**Last Updated:** 2025-01-14
**Owner:** deployment-tester agent