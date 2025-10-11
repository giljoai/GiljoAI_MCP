# WAN Deployment Mission Prompt

## Mission Overview

Transform GiljoAI MCP from LAN-only operation to **production-ready internet-facing deployment** (WAN mode). Enable secure, scalable access from anywhere in the world with enterprise-grade security, monitoring, and reliability.

**Target:** Linux production servers (primary), Windows Server, Cloud platforms (AWS, Azure, GCP)
**Timeline:** 7-10 weeks (4-5 sprints) - includes UX/installation enhancements
**Success Criteria:** Secure public access with SSL/TLS, DDoS protection, monitoring, 99.9% uptime, and seamless installation experience

---

## Critical Context

### Prerequisites (MANDATORY)

**🚨 DO NOT START UNTIL:**
- ✅ **LAN deployment is production-ready and validated**
- ✅ **All LAN security checklist items completed (81/81)**
- ✅ **LAN performance benchmarks established**
- ✅ **Multi-client LAN access tested and working**
- ✅ **LAN UX improvements complete** (installer wizard, first-launch setup, settings interface)
- ✅ **User approval to proceed with WAN deployment**

**Starting WAN before LAN is complete will result in failure.**

**Related Mission:** See `LAN_UX_MISSION_PROMPT.md` for foundational UX patterns that will be adapted for WAN deployment. The LAN UX provides the base installer framework, setup wizard patterns, and settings interface that WAN will extend with cloud-specific features.

### Current State (After LAN Deployment)
- ✅ **LAN deployment working** - Multiple clients accessing on internal network
- ✅ **Security hardened for LAN** - API keys, rate limiting, tenant isolation validated
- ✅ **Cross-platform tested** - Windows, Linux, macOS deployments verified
- ✅ **Performance baseline established** - LAN latency, throughput, concurrent users documented

### What Changes for WAN
- **Trust Model:** Trusted network → Zero-trust internet
- **Authentication:** API keys → API keys + JWT tokens
- **Encryption:** Optional SSL → Mandatory HTTPS with HSTS
- **Infrastructure:** Direct access → Reverse proxy + load balancing
- **State Management:** In-memory → Distributed (Redis)
- **Monitoring:** Basic → Comprehensive (Prometheus, Grafana, Loki)
- **Security:** Firewall → Firewall + WAF + DDoS protection + fail2ban
- **Storage:** Local files → Object storage (S3/MinIO)
- **Installation:** Simple LAN setup → Cloud deployment automation
- **UX Complexity:** Network IP configuration → Domain + DNS + SSL + Reverse Proxy wizards
- **Admin Interface:** Basic settings → Full WAN management (SSL, WAF, multi-tenant, monitoring)
- **Client Setup:** LAN IP address → Internet URL with certificate validation

---

## Your Mission

### Phase 1: Production Hardening (Week 1-2)

**Build on LAN Foundation:**

1. **Mandatory HTTPS Enforcement**
   - File: `api/run_api.py`
   - Add: SSL/TLS requirement for WAN mode (no HTTP fallback)
   - Implement: Automatic HTTP → HTTPS redirect
   - Add: HSTS headers (Strict-Transport-Security)
   - Test: Verify HTTPS-only access, HTTP requests redirect

2. **SSL/TLS Certificate Setup**
   - Platform: Linux (Let's Encrypt), Windows (commercial cert or Let's Encrypt)
   - Automation: Certbot for automatic renewal
   - Configuration: TLS 1.2+ only, strong cipher suites (Mozilla Modern)
   - Test: SSL Labs A+ rating, certificate auto-renewal works

3. **JWT Authentication Layer**
   - File: `src/giljo_mcp/auth.py`
   - Add: JWT token generation and validation
   - Implement: Token expiration (15 min access, 7 day refresh)
   - Integration: JWT + API key dual authentication
   - Test: Token lifecycle, expiration, renewal, revocation

4. **Harden CORS for Internet**
   - File: `api/app.py`
   - Remove: LAN wildcard origins
   - Add: Explicit production domain whitelist
   - Configure: Credentials handling for production
   - Test: Only allowed domains can access API

5. **Distributed Rate Limiting (Redis)**
   - File: `api/middleware.py`
   - Replace: In-memory rate limiting with Redis-backed
   - Configure: Per-endpoint limits (auth: 10/min, read: 100/min, write: 30/min)
   - Add: Burst protection, IP-based limiting
   - Test: Rate limits work across multiple API instances

6. **Advanced Security Headers**
   - File: `api/middleware.py`
   - Add to existing SecurityHeadersMiddleware:
     - Content-Security-Policy (strict)
     - Referrer-Policy: no-referrer
     - Permissions-Policy
     - Expect-CT
   - Test: Security headers validator (securityheaders.com)

7. **Database SSL/TLS Enforcement**
   - File: `src/giljo_mcp/database.py`
   - Add: `sslmode=require` or `sslmode=verify-full` for PostgreSQL connections
   - Configure: SSL certificates for database encryption
   - Test: Verify all database traffic encrypted

### Phase 2: Infrastructure Setup (Week 3-4)

**Production Infrastructure:**

1. **Reverse Proxy Deployment**
   - **Option A: nginx (Recommended for Linux)**
     - File: `configs/wan/nginx.conf` (template provided)
     - Setup: Proxy pass to Uvicorn backend
     - Configure: WebSocket proxying, SSL termination
     - Add: Request buffering, timeouts, keepalive

   - **Option B: Caddy (Simpler Alternative)**
     - File: `configs/wan/Caddyfile` (template provided)
     - Setup: Automatic HTTPS with Let's Encrypt
     - Configure: Reverse proxy, WebSocket support

   - **Option C: IIS (Windows Server)**
     - File: `configs/wan/IIS_CONFIG.md` (guide provided)
     - Setup: Application Request Routing (ARR)
     - Configure: URL rewrite, SSL binding

   - Test: All traffic routes through proxy, SSL works, WebSockets stable

2. **Redis Cluster Setup**
   - Deploy: Redis Sentinel (3 nodes for high availability)
   - Configure: Master-slave replication
   - Use: Rate limiting, session storage, WebSocket state
   - File: Update `docker-compose.wan.yml` (template provided)
   - Test: Failover, persistence, performance

3. **Object Storage Integration**
   - **Option A: AWS S3** (if using AWS)
   - **Option B: Azure Blob Storage** (if using Azure)
   - **Option C: MinIO** (self-hosted S3-compatible)
   - **Option D: GCP Cloud Storage** (if using GCP)
   - File: `api/endpoints/products.py` (vision document uploads)
   - Migrate: Local file storage to object storage
   - Test: Upload, download, large file handling

4. **Production ASGI Server**
   - Replace: Development Uvicorn with production setup
   - Deploy: Gunicorn with Uvicorn workers
   - Configure: 4 workers (adjust based on CPU cores)
   - Add: Graceful shutdown, worker timeout, keepalive
   - File: Create `gunicorn_conf.py`
   - Test: Load balancing across workers, no downtime during restarts

5. **Frontend Production Build**
   - Build: Production Vue 3 bundle
   - Optimize: Code splitting, tree shaking, minification
   - Configure: Environment variables for production API URL
   - Deploy: Static files via nginx/Caddy/IIS
   - CDN: Optional CloudFlare or AWS CloudFront
   - Test: Page load < 2 seconds, assets cached correctly

### Phase 3: Advanced Security (Week 5)

**Defense in Depth:**

1. **Web Application Firewall (WAF)**
   - **Option A: ModSecurity** (nginx module, free)
   - **Option B: CloudFlare WAF** (paid, easy)
   - **Option C: AWS WAF** (if using AWS)
   - Rules: OWASP Core Rule Set
   - Configure: SQL injection, XSS, CSRF protection
   - Test: Attack simulation, false positive tuning

2. **DDoS Protection**
   - **Layer 7 (Application):** Rate limiting, connection limits
   - **Layer 4 (Network):** CloudFlare, AWS Shield, or iptables rules
   - Configure: Connection rate limits, request size limits
   - Test: Stress testing, simulated attacks

3. **Intrusion Prevention (fail2ban)**
   - Platform: Linux servers
   - Rules: Ban IPs after failed auth attempts (5 failures = 1 hour ban)
   - Monitor: API auth failures, suspicious patterns
   - Configure: Email alerts on bans
   - Test: Verify brute force protection

4. **Secrets Management**
   - **Option A: HashiCorp Vault** (enterprise)
   - **Option B: AWS Secrets Manager** (if AWS)
   - **Option C: Azure Key Vault** (if Azure)
   - **Option D: Encrypted environment variables** (minimum)
   - Migrate: All secrets from .env to vault
   - Rotate: JWT secrets, API keys, database passwords
   - Test: Secret rotation, access logging

5. **Security Scanning and Auditing**
   - **Static Analysis:** Bandit (Python), ESLint (JavaScript)
   - **Dependency Scanning:** Safety, npm audit
   - **Container Scanning:** Trivy (if using Docker)
   - **Penetration Testing:** OWASP ZAP, Burp Suite
   - Schedule: Weekly automated scans
   - Test: No critical vulnerabilities

### Phase 4: Monitoring & Observability (Week 6)

**Production Operations:**

1. **Metrics Collection (Prometheus)**
   - Deploy: Prometheus server
   - Exporters: Node exporter, PostgreSQL exporter, Redis exporter
   - Metrics: Add custom metrics to API
     - Request rate, latency, errors
     - Database query performance
     - WebSocket connection count
     - Agent spawn rate, task completion time
   - File: Create `prometheus.yml` configuration
   - Test: Metrics scraped, stored, queryable

2. **Dashboards (Grafana)**
   - Deploy: Grafana server
   - Dashboards: Create production dashboards
     - System overview (CPU, memory, disk, network)
     - API performance (requests/sec, latency, errors)
     - Database performance (connections, query time, slow queries)
     - Business metrics (active projects, agents, tasks)
   - Alerts: Configure alerting rules
   - Test: Real-time updates, alerts trigger correctly

3. **Log Aggregation (Loki)**
   - Deploy: Loki + Promtail stack
   - Configure: Collect logs from all services
     - API server logs
     - nginx/Caddy access logs
     - PostgreSQL logs
     - Redis logs
   - Retention: 30 days for debug, 90 days for errors
   - Test: Log search, filtering, correlation

4. **Health Checks and Uptime Monitoring**
   - Endpoint: Enhance `/health` with detailed checks
     - Database connectivity
     - Redis connectivity
     - Disk space
     - Memory usage
   - External: UptimeRobot or Pingdom for external monitoring
   - Alerts: Email/SMS on downtime
   - Test: Health endpoint, alert delivery

5. **Error Tracking (Optional)**
   - **Option A: Sentry** (paid, excellent)
   - **Option B: Rollbar** (alternative)
   - **Option C: ELK Stack** (self-hosted, complex)
   - Integration: Capture exceptions, stack traces
   - Alerts: Email on critical errors
   - Test: Error capturing, grouping, alerting

### Phase 5: Backup & Disaster Recovery (Week 7)

**Data Protection:**

1. **Automated Database Backups**
   - Schedule: Daily full backups, hourly incrementals
   - Storage: S3/Azure Blob/GCS with versioning
   - Retention: 7 days daily, 4 weeks Sunday backups, 12 months yearly
   - Encryption: Backup files encrypted at rest
   - File: Create backup script `scripts/backup_database.sh`
   - Test: Backup creation, restoration, integrity

2. **Application State Backup**
   - Vision documents: Already in object storage (replicated)
   - Configuration: Backup config.yaml, .env (encrypted)
   - Redis data: Persistence enabled, backed up
   - Test: Full system restoration from backups

3. **Disaster Recovery Plan**
   - Document: `docs/deployment/DISASTER_RECOVERY_PLAN.md`
   - Scenarios: Database failure, API server crash, complete data center loss
   - Procedures: Step-by-step recovery for each scenario
   - RTO/RPO: Define Recovery Time Objective and Recovery Point Objective
   - Test: Simulate failures, execute recovery procedures

4. **High Availability Setup (Optional)**
   - Load Balancer: nginx, HAProxy, or cloud load balancer
   - API Servers: 2+ instances behind load balancer
   - Database: PostgreSQL streaming replication (master + read replica)
   - Redis: Sentinel cluster (already set up in Phase 2)
   - Test: Failover scenarios, zero-downtime deployments

### Phase 6: Installation & User Experience (Week 7-8)

**Production-Grade UX (Builds on LAN UX Foundation):**

**Note:** This phase extends the LAN UX patterns for internet-facing deployment. The LAN installer provides the base framework; WAN adds cloud deployment automation, domain configuration, SSL setup, and advanced networking.

1. **Enhanced Installer with WAN Mode**
   - File: `installer/cli/install.py`
   - Extend: Add WAN deployment mode option
   - Features:
     - Cloud platform selection (AWS, Azure, GCP, DigitalOcean, Self-hosted)
     - Automated infrastructure provisioning
     - Domain name configuration wizard
     - SSL certificate automation (Let's Encrypt or custom)
     - Reverse proxy selection and setup (nginx/Caddy)
     - DNS configuration guidance
     - Monitoring stack installation (Prometheus/Grafana)
   - Integration: Detect LAN installer base, add WAN-specific modules
   - Test: One-command WAN deployment on fresh server

2. **Cloud Deployment Scripts**
   - **AWS Deployment Automation**
     - File: `installer/cloud/aws_deploy.py`
     - Features: EC2 provisioning, RDS setup, ELB configuration, Route53 DNS
     - CloudFormation/Terraform templates

   - **Azure Deployment Automation**
     - File: `installer/cloud/azure_deploy.py`
     - Features: VM provisioning, Azure Database, Application Gateway, DNS zones
     - ARM templates or Terraform

   - **GCP Deployment Automation**
     - File: `installer/cloud/gcp_deploy.py`
     - Features: Compute Engine, Cloud SQL, Load Balancing, Cloud DNS
     - Deployment Manager or Terraform

   - **DigitalOcean (Cost-Effective)**
     - File: `installer/cloud/digitalocean_deploy.py`
     - Features: Droplets, Managed PostgreSQL/Redis, Load Balancer, DNS
     - Simple API-based deployment

   - Test: Each cloud platform deploys successfully with one command

3. **Docker/Kubernetes Deployment**
   - File: `docker-compose.wan.yml` (already exists, enhance)
   - File: `kubernetes/wan-deployment.yaml` (create)
   - Features:
     - Multi-container orchestration
     - Auto-scaling configuration
     - Health checks and rolling updates
     - Secrets management (Kubernetes secrets or Docker secrets)
   - Helm charts for easy Kubernetes deployment
   - Test: Container orchestration works, auto-scaling functional

4. **First-Launch Setup Wizard (WAN)**
   - File: `frontend/src/views/setup/WANSetupWizard.vue`
   - Extends: LAN setup wizard with WAN-specific steps
   - Steps:
     1. Domain & SSL Configuration
        - Domain name entry and verification
        - DNS record validation (A, AAAA, CNAME)
        - SSL certificate selection (Let's Encrypt auto or custom upload)
        - Certificate auto-renewal setup
     2. Network & Security
        - Reverse proxy configuration (nginx/Caddy)
        - Firewall rules verification
        - WAF enablement and rule selection
        - DDoS protection settings
     3. Cloud Integration (if applicable)
        - Cloud provider credentials
        - Object storage configuration (S3/Azure Blob/GCS)
        - CDN setup (optional)
     4. Monitoring & Alerts
        - Prometheus/Grafana configuration
        - Alert destinations (email, Slack, PagerDuty)
        - Uptime monitoring setup
     5. Admin Account & Multi-Tenancy
        - Master admin account creation
        - Tenant management settings
        - User invitation system
   - UX: Progress indicator, validation, help tooltips
   - Test: Complete wizard flow, all integrations configured

5. **Admin Settings Interface (WAN Features)**
   - File: `frontend/src/views/admin/WANSettings.vue`
   - Sections:
     - **Domain & SSL Management**
       - View certificate status, expiration
       - Renew/replace certificates
       - Manage DNS records
       - HTTPS enforcement settings

     - **Security Configuration**
       - WAF rule management
       - DDoS protection tuning
       - Rate limiting per-endpoint
       - IP whitelist/blacklist
       - API key rotation
       - JWT token settings

     - **Infrastructure Monitoring**
       - Server health dashboard
       - Resource usage (CPU, memory, disk)
       - Database performance
       - Redis cluster status
       - Load balancer health

     - **Backup & Recovery**
       - Backup schedule configuration
       - Restore point management
       - Disaster recovery testing
       - Backup storage location

     - **Multi-Tenant Administration**
       - Tenant creation/deletion
       - Per-tenant resource limits
       - Usage analytics per tenant
       - Billing integration (optional)

   - UX: Real-time updates, clear status indicators, one-click actions
   - Test: All admin functions work, real-time updates via WebSocket

6. **Client PC Setup for WAN Access**
   - File: `installer/client/setup_wan_client.py`
   - Features:
     - One-command client setup
     - Server URL configuration (e.g., https://giljo.example.com)
     - API key entry and validation
     - SSL certificate trust (if custom CA)
     - Connection test and diagnostics
   - Cross-platform: Windows, Linux, macOS clients
   - CLI: `python setup_wan_client.py --server https://giljo.example.com --api-key <key>`
   - Test: Client connects from internet, all features work

7. **Certificate Management Automation**
   - File: `scripts/ssl/manage_certificates.sh`
   - Features:
     - Automated Let's Encrypt certificate issuance
     - Auto-renewal with cron/systemd timer
     - Certificate expiration monitoring
     - Alert before expiration (30, 14, 7 days)
     - Automatic nginx/Caddy reload after renewal
   - Integration: Works with manual certificates too
   - Test: Certificate renewal succeeds, no downtime

8. **Deployment Monitoring Dashboard**
   - File: `frontend/src/views/monitoring/WANDashboard.vue`
   - Real-time Metrics:
     - API request rate (requests/sec)
     - Response time distribution (p50, p95, p99)
     - Error rate by endpoint
     - Active connections (HTTP + WebSocket)
     - Database query performance
     - Cache hit ratio (Redis)
     - SSL handshake performance
   - Geographical Distribution:
     - User locations on map
     - Latency by region
     - Traffic by country
   - Alerts:
     - Recent alerts timeline
     - Alert configuration
     - Incident history
   - Test: Metrics update in real-time, alerts trigger correctly

9. **Multi-Tenant Admin Interface**
   - File: `frontend/src/views/admin/TenantManagement.vue`
   - Features:
     - **Tenant Dashboard**
       - List all tenants with status
       - Usage statistics per tenant
       - Resource consumption (projects, agents, tasks)

     - **Tenant Creation Wizard**
       - Tenant name and metadata
       - Initial admin user setup
       - Resource limits configuration
       - Custom domain support (optional)

     - **Tenant Administration**
       - Enable/disable tenant
       - Reset tenant API keys
       - View tenant activity logs
       - Export tenant data
       - Delete tenant (with confirmation)

     - **Resource Quotas**
       - Max concurrent agents per tenant
       - Storage limits
       - API rate limits per tenant
       - Database connection limits

   - UX: Searchable tenant list, inline editing, bulk actions
   - Test: Multi-tenant isolation verified, quotas enforced

10. **Installation Documentation**
    - Update: `docs/deployment/WAN_DEPLOYMENT_GUIDE.md`
    - Sections:
      - One-command installation guide
      - Cloud platform specific instructions
      - Domain and DNS configuration
      - SSL certificate setup walkthrough
      - Troubleshooting common installation issues
      - Migration from self-hosted to cloud

    - Create: `docs/deployment/WAN_INSTALLER_GUIDE.md`
    - Content:
      - Installer architecture and design
      - Customization options
      - Advanced deployment scenarios
      - Unattended/automated installation

    - Create: `docs/deployment/WAN_ADMIN_GUIDE.md`
    - Content:
      - Admin interface user manual
      - Day-to-day operations
      - Security best practices
      - Performance tuning
      - Multi-tenant management

### Phase 7: Testing & Launch (Week 9-10)

**Production Validation:**

1. **Load Testing**
   - Tool: Locust or k6
   - Scenarios:
     - 100 concurrent users
     - 500 requests/second sustained
     - WebSocket stress (200 concurrent connections)
   - Measure: Response times, error rates, resource usage
   - Pass Criteria: < 500ms p95 latency, < 1% error rate

2. **Security Penetration Testing**
   - Tool: OWASP ZAP, Burp Suite Pro
   - Tests:
     - SQL injection attempts
     - XSS attacks
     - CSRF attacks
     - Authentication bypass attempts
     - Rate limiting bypass attempts
     - DDoS simulation
   - Pass Criteria: No critical or high vulnerabilities

3. **End-to-End Testing**
   - Test: Complete user workflows from internet
     - Project creation
     - Agent spawning
     - Task management
     - Real-time updates via WebSocket
   - Browsers: Chrome, Firefox, Safari, Edge
   - Devices: Desktop, mobile browsers
   - Pass Criteria: All workflows function correctly

4. **SSL/TLS Validation**
   - Test: SSL Labs (https://www.ssllabs.com/ssltest/)
   - Target: A+ rating
   - Verify: Certificate chain, protocol support, cipher strength
   - Pass Criteria: A+ rating, no warnings

5. **Performance Benchmarking**
   - Establish: Production performance baseline
   - Compare: WAN vs LAN performance metrics
   - Document: Expected latency, throughput, concurrent users
   - Pass Criteria: Meets or exceeds targets

6. **Soft Launch**
   - Phase 1: Internal testing (team only)
   - Phase 2: Beta users (controlled rollout)
   - Phase 3: General availability (full public access)
   - Monitor: Errors, performance, user feedback
   - Rollback Plan: Documented rollback procedure

---

## Key Resources (READ THESE FIRST)

### Primary Documentation
1. **`docs/deployment/WAN_DEPLOYMENT_GUIDE.md`** - Complete WAN deployment guide (~500 lines)
2. **`docs/deployment/WAN_SECURITY_CHECKLIST.md`** - Comprehensive security validation (~400 lines)
3. **`docs/deployment/WAN_ARCHITECTURE.md`** - Production architecture reference (~550 lines)
4. **`docs/deployment/LAN_TO_WAN_MIGRATION.md`** - Upgrade path from LAN (~450 lines)

### LAN Foundation (Review)
5. **`docs/deployment/LAN_DEPLOYMENT_GUIDE.md`** - Understand what's already working
6. **`docs/deployment/LAN_SECURITY_CHECKLIST.md`** - LAN security baseline
7. **LAN deployment session memory** - Review what was done in Phase 1

### Configuration Templates (Use These)
8. **`configs/wan/nginx.conf`** - Production nginx configuration
9. **`configs/wan/Caddyfile`** - Caddy configuration (alternative)
10. **`configs/wan/IIS_CONFIG.md`** - Windows IIS setup guide
11. **`docker-compose.wan.yml`** - Complete production Docker stack

### Deployment Scripts
12. **`scripts/deployment/deploy_wan_linux.sh`** - Automated Linux WAN deployment

### Cross-Platform Reference
13. **`docs/CROSS_PLATFORM_GUIDE.md`** - Platform-specific considerations
14. **`docs/PLATFORM_TESTING_MATRIX.md`** - Testing status by platform

---

## Success Criteria

### Technical Validation
- ✅ HTTPS enforced with HSTS, SSL Labs A+ rating
- ✅ JWT authentication working with token refresh
- ✅ Distributed rate limiting via Redis functional
- ✅ Reverse proxy routing all traffic correctly
- ✅ WebSocket connections stable through proxy
- ✅ Object storage handling all file uploads
- ✅ WAF blocking malicious requests
- ✅ DDoS protection validated with stress tests
- ✅ fail2ban blocking brute force attempts
- ✅ All secrets in vault (no plaintext)
- ✅ Monitoring dashboards operational
- ✅ Alerts triggering correctly
- ✅ Logs aggregated and searchable
- ✅ Automated backups running daily
- ✅ Disaster recovery tested successfully

### Performance
- ✅ 100 concurrent users supported
- ✅ < 500ms p95 API latency
- ✅ < 1% error rate under load
- ✅ 99.9% uptime over 30 days
- ✅ Database query performance acceptable (< 100ms avg)
- ✅ WebSocket latency < 100ms

### Security
- ✅ All WAN security checklist items complete
- ✅ Penetration testing shows no critical vulnerabilities
- ✅ Security scanning shows no high-risk dependencies
- ✅ OWASP Top 10 protections validated
- ✅ Compliance requirements met (GDPR, SOC 2 if applicable)

### User Acceptance
- ✅ User can access from anywhere in world
- ✅ Team members can access from home/mobile
- ✅ Performance acceptable for remote users
- ✅ Zero security incidents during soft launch
- ✅ Monitoring provides visibility into system health

### Documentation
- ✅ Complete production runbook
- ✅ Disaster recovery plan documented and tested
- ✅ Monitoring playbook (how to respond to alerts)
- ✅ Security incident response plan
- ✅ Performance tuning guide

---

## Agent Team Composition

### Recommended Agents

**Lead: orchestrator-coordinator**
- Coordinate 7-10 week mission (extended for UX phase)
- Track progress across phases
- Manage dependencies between infrastructure and UX components
- Report status to user

**Security: network-security-engineer**
- SSL/TLS setup and hardening
- WAF configuration
- DDoS protection
- fail2ban and intrusion prevention
- Secrets management
- Security testing and validation

**Infrastructure: system-architect**
- Reverse proxy architecture
- Redis cluster design
- High availability setup
- Object storage integration
- Database replication
- Performance optimization
- Cloud deployment architecture

**Research: deep-researcher**
- Cloud platform best practices
- Monitoring stack recommendations
- Performance tuning strategies
- Security compliance requirements

**Implementation: tdd-implementor**
- JWT authentication implementation
- Distributed rate limiting
- Object storage integration
- Production ASGI server setup
- Code changes with tests

**Frontend/UX: frontend-developer**
- WAN setup wizard implementation (extends LAN wizard)
- Admin settings interface for WAN features
- Monitoring dashboard UI
- Multi-tenant admin interface
- Real-time metrics visualization
- Responsive design for admin panels

**Installer: installer-developer**
- Enhanced installer with WAN mode
- Cloud deployment automation (AWS, Azure, GCP, DigitalOcean)
- Docker/Kubernetes deployment scripts
- Certificate management automation
- Client setup utilities
- One-command installation experience
- Builds on LAN installer foundation

**Testing: backend-integration-tester**
- Load testing
- Penetration testing
- End-to-end testing
- Performance benchmarking
- Security validation
- Installation testing across platforms

**Documentation: documentation-manager**
- Production runbook
- Disaster recovery plan
- Monitoring playbook
- Security incident response
- WAN installer guide
- WAN admin guide
- Session summary and devlog

---

## Coordination Strategy

### Weekly Milestones
- **Week 1:** Production hardening complete
- **Week 2:** Infrastructure deployed
- **Week 3:** Advanced security operational
- **Week 4:** Monitoring and observability live
- **Week 5:** Backup and DR tested
- **Week 6:** Core functionality validated (checkpoint)
- **Week 7:** Installation & UX development (installer, wizards)
- **Week 8:** Installation & UX completion (admin interfaces, monitoring dashboards)
- **Week 9:** Load testing, security testing, installation testing
- **Week 10:** Soft launch and production launch

### Git Workflow
```bash
# Create WAN feature branch
git checkout -b feature/wan-deployment

# Commit at end of each day
git add .
git commit -m "WAN: [phase and specific work]"

# Push regularly
git push origin feature/wan-deployment

# Merge to master after each phase validation
git checkout master
git merge feature/wan-deployment
```

### Testing Gates
- Phase 1 → Phase 2: All security fixes validated
- Phase 2 → Phase 3: Infrastructure stable under load
- Phase 3 → Phase 4: Security testing passed
- Phase 4 → Phase 5: Monitoring operational
- Phase 5 → Phase 6: Backups tested, DR validated
- Phase 6 → Phase 7: Core WAN functionality complete, ready for UX layer
- Phase 7 → Launch: Installation tested, UX complete, all criteria met, user approval

---

## Risk Mitigation

### Known Risks

**Risk 1: SSL Certificate Issues**
- Mitigation: Use Let's Encrypt for automated renewal, test renewal process
- Recovery: Manual certificate renewal procedure documented

**Risk 2: Reverse Proxy Complexity**
- Mitigation: Use Caddy for simpler setup, or nginx with well-tested config
- Recovery: Fallback to direct API access temporarily

**Risk 3: DDoS Attack During Launch**
- Mitigation: CloudFlare in front, rate limiting, connection limits
- Recovery: Emergency rate limit tightening, IP blocking

**Risk 4: Database Performance Degradation**
- Mitigation: Connection pooling, read replicas, query optimization
- Recovery: Vertical scaling, add read replicas

**Risk 5: Cost Overruns (Cloud)**
- Mitigation: Set up billing alerts, monitor resource usage
- Recovery: Scale down non-essential resources, optimize

**Risk 6: Security Breach**
- Mitigation: Defense in depth, monitoring, alerts, incident response plan
- Recovery: Documented incident response procedure, backups

**Risk 7: Complex Installation Experience**
- Mitigation: Thorough installer testing, clear error messages, rollback capability
- Recovery: Manual installation documentation, support troubleshooting guide

**Risk 8: Cloud Platform Incompatibility**
- Mitigation: Test on all major cloud platforms, provide fallback options
- Recovery: Platform-specific workarounds documented, manual setup guide

**Risk 9: SSL/DNS Configuration Errors**
- Mitigation: Automated validation, clear setup wizard, DNS check utilities
- Recovery: Troubleshooting guide, manual certificate installation steps

---

## Platform-Specific Guidance

### Linux (Recommended for Production)
- **Distro:** Ubuntu 22.04 LTS or Debian 12
- **Reverse Proxy:** nginx (industry standard)
- **Process Manager:** systemd
- **Firewall:** ufw or iptables
- **SSL:** Let's Encrypt via Certbot
- **Advantages:** Best performance, most resources, lowest cost

### Windows Server
- **Reverse Proxy:** IIS with Application Request Routing
- **Process Manager:** Windows Services or NSSM
- **Firewall:** Windows Defender Firewall
- **SSL:** Commercial certificate or Let's Encrypt
- **Advantages:** Familiar for Windows admins, Active Directory integration

### Cloud Platforms

**AWS:**
- **Load Balancer:** Application Load Balancer (ALB)
- **Compute:** EC2 or ECS (Docker)
- **Database:** RDS PostgreSQL
- **Cache:** ElastiCache Redis
- **Storage:** S3
- **Monitoring:** CloudWatch + Prometheus
- **Advantages:** Comprehensive services, auto-scaling

**Azure:**
- **Load Balancer:** Application Gateway
- **Compute:** Virtual Machines or Container Instances
- **Database:** Azure Database for PostgreSQL
- **Cache:** Azure Cache for Redis
- **Storage:** Blob Storage
- **Monitoring:** Azure Monitor + Prometheus
- **Advantages:** Microsoft integration, hybrid cloud

**GCP:**
- **Load Balancer:** HTTP(S) Load Balancing
- **Compute:** Compute Engine or Cloud Run
- **Database:** Cloud SQL PostgreSQL
- **Cache:** Memorystore for Redis
- **Storage:** Cloud Storage
- **Monitoring:** Cloud Monitoring + Prometheus
- **Advantages:** Google infrastructure, Kubernetes integration

**DigitalOcean (Cost-Effective):**
- **Load Balancer:** DigitalOcean Load Balancer
- **Compute:** Droplets
- **Database:** Managed PostgreSQL
- **Cache:** Managed Redis
- **Storage:** Spaces (S3-compatible)
- **Monitoring:** Built-in + Prometheus
- **Advantages:** Simple, affordable, good for startups

---

## Cost Considerations

### Small Deployment (< 50 users)
- **Compute:** $50-100/month (1 server)
- **Database:** $30-60/month (managed PostgreSQL)
- **Redis:** $15-30/month (managed Redis)
- **Storage:** $5-20/month (S3/equivalent)
- **SSL:** $0 (Let's Encrypt)
- **Monitoring:** $0-50/month (self-hosted or basic tier)
- **Total:** $100-260/month

### Medium Deployment (50-500 users)
- **Compute:** $200-400/month (2-3 servers + load balancer)
- **Database:** $100-200/month (larger instance + replica)
- **Redis:** $50-100/month (cluster)
- **Storage:** $20-100/month
- **CDN:** $20-50/month (CloudFlare or equivalent)
- **Monitoring:** $50-100/month
- **Total:** $440-950/month

### Large Deployment (500+ users)
- **Compute:** $500-2000/month (auto-scaling, multiple regions)
- **Database:** $300-1000/month (HA setup, multiple replicas)
- **Redis:** $150-500/month (HA cluster)
- **Storage:** $100-500/month
- **CDN:** $100-500/month
- **Monitoring:** $100-300/month (Grafana Cloud or similar)
- **WAF/DDoS:** $200-500/month (CloudFlare Pro or AWS WAF)
- **Total:** $1,450-5,300/month

---

## Definition of Done

### Phase 1 Complete When:
- ✅ HTTPS enforced, SSL Labs A+
- ✅ JWT authentication working
- ✅ Distributed rate limiting functional
- ✅ All security headers present
- ✅ Database SSL enabled

### Phase 2 Complete When:
- ✅ Reverse proxy routing all traffic
- ✅ Redis cluster operational
- ✅ Object storage integrated
- ✅ Production ASGI server running
- ✅ Frontend production build deployed

### Phase 3 Complete When:
- ✅ WAF blocking attacks
- ✅ DDoS protection validated
- ✅ fail2ban preventing brute force
- ✅ All secrets in vault
- ✅ Security scans clean

### Phase 4 Complete When:
- ✅ Prometheus collecting metrics
- ✅ Grafana dashboards operational
- ✅ Loki aggregating logs
- ✅ Health checks functional
- ✅ Alerts configured and tested

### Phase 5 Complete When:
- ✅ Daily backups running
- ✅ Backup restoration tested
- ✅ Disaster recovery plan validated
- ✅ High availability tested (if implemented)

### Phase 6 Complete When:
- ✅ Enhanced installer with WAN mode functional
- ✅ Cloud deployment scripts working (at least 2 platforms)
- ✅ WAN setup wizard complete and tested
- ✅ Admin settings interface operational
- ✅ Client setup utility working
- ✅ Certificate management automated
- ✅ Monitoring dashboard live
- ✅ Multi-tenant admin interface complete
- ✅ Installation documentation comprehensive

### Phase 7 Complete When:
- ✅ Load testing passed
- ✅ Penetration testing clean
- ✅ End-to-end testing passed
- ✅ SSL validation A+
- ✅ Installation testing on all target platforms successful
- ✅ Soft launch successful

### Mission Complete When:
- ✅ User accessing from internet successfully
- ✅ Team members accessing from home/mobile
- ✅ One-command installation working on fresh servers
- ✅ Setup wizard provides smooth first-launch experience
- ✅ Admin can manage all WAN features through UI
- ✅ Client setup takes < 5 minutes
- ✅ 99.9% uptime over 7 days
- ✅ Zero security incidents
- ✅ Monitoring and alerts operational
- ✅ Backups running and tested
- ✅ Performance meets targets
- ✅ All documentation complete (deployment + installation + admin guides)
- ✅ User approval for production launch

---

## Important Notes

### What NOT to Do
- ❌ Don't start before LAN deployment is validated
- ❌ Don't start before LAN UX improvements are complete
- ❌ Don't skip security checklist items
- ❌ Don't deploy to production without penetration testing
- ❌ Don't store secrets in plaintext
- ❌ Don't skip backup testing
- ❌ Don't launch without monitoring
- ❌ Don't ignore performance benchmarks
- ❌ Don't create complex installation requiring manual configuration
- ❌ Don't skip installation testing on target platforms

### What TO Do
- ✅ Build on proven LAN foundation (code + UX patterns)
- ✅ Extend LAN installer for WAN capabilities
- ✅ Reuse LAN setup wizard patterns
- ✅ Test each phase before moving to next
- ✅ Document everything (technical + user-facing)
- ✅ Monitor continuously
- ✅ Validate security at every step
- ✅ Test disaster recovery procedures
- ✅ Test installation on fresh servers
- ✅ Ensure one-command deployment works
- ✅ Communicate with user before major changes
- ✅ Have rollback plan for every deployment

---

## Quick Start

### Step 1: Validate Prerequisites (1 hour)
```bash
# Verify LAN deployment is working
# Review LAN security checklist (should be 81/81)
# Review LAN performance benchmarks
# Get user approval to proceed
```

### Step 2: Read Documentation (2-3 hours)
```bash
# Read these in order:
1. docs/deployment/LAN_UX_MISSION_PROMPT.md (understand UX foundation)
2. docs/deployment/WAN_DEPLOYMENT_GUIDE.md
3. docs/deployment/WAN_SECURITY_CHECKLIST.md
4. docs/deployment/WAN_ARCHITECTURE.md
5. docs/deployment/LAN_TO_WAN_MIGRATION.md
```

### Step 3: Plan Infrastructure (1 day)
```bash
# Decide: Cloud platform or self-hosted?
# Choose: Reverse proxy (nginx/Caddy/IIS)
# Plan: Monitoring stack
# Budget: Estimate costs
# Document: Architecture decisions
```

### Step 4: Create Feature Branch
```bash
git checkout -b feature/wan-deployment
git push -u origin feature/wan-deployment
```

### Step 5: Begin Phase 1 Production Hardening
Start with HTTPS enforcement and SSL/TLS setup.

---

## Questions? Blockers?

- **Orchestrator**: Coordinate with other agents
- **User**: Get approval for infrastructure decisions
- **Documentation**: Reference guides in `docs/deployment/`
- **LAN Team**: Consult on foundation issues

---

## Final Reminders

**This is Phase 2 of 2:**
- WAN builds on LAN foundation (code + UX)
- LAN must be production-ready first (including UX improvements)
- Focus on security, reliability, monitoring, and seamless deployment

**Success = Secure, scalable, internet-accessible system with production-grade UX**
- Accessible from anywhere
- One-command installation
- Intuitive admin interface
- Enterprise-grade security
- 99.9%+ uptime
- Comprehensive monitoring
- Well-documented and maintainable

**You've got this! LAN foundation is solid. Now add production polish and world-class installation experience.**

---

**WAN UX Complexity Notes:**
- WAN installation is MORE complex than LAN (DNS, SSL, reverse proxy, cloud integration)
- Must guide users through: domain setup, certificate management, firewall configuration
- Automated installer should handle 90% of complexity
- Admin interface must expose all WAN-specific controls
- Client setup should be trivial: one command with server URL and API key
- Monitoring dashboard critical for internet-facing deployment

---

*Mission created: 2025-10-05*
*Updated: 2025-10-05 (added UX/installation phase)*
*Target start: After LAN deployment + LAN UX complete*
*Duration: 7-10 weeks (extended for UX enhancements)*
*Priority: HIGH (after LAN)*
*Complexity: HIGH*
*Risk: MEDIUM (with proper planning, testing, and LAN UX foundation)*
