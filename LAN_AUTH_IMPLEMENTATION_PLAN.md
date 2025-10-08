# LAN Authentication Implementation Plan

**Version:** 1.0
**Date:** 2025-10-07
**Status:** Ready for Implementation
**Estimated Timeline:** 7-11 days
**Owner:** GiljoAI Development Team

---

## Executive Summary

### What: Implementing User Authentication for LAN Mode

Transform GiljoAI MCP from single-user localhost to multi-user LAN deployment with secure per-user authentication.

**Current State:**
- Localhost mode: Complete (no authentication needed)
- LAN mode: Works but no authentication (insecure)
- What exists: Basic API structure, setup wizard, frontend

**Target State:**
- LAN mode with: Username/password login, JWT tokens, personal API keys
- Building blocks ready for: WAN (HTTPS/domain) and SaaS (OAuth, multi-tenancy)

### Why: Enable Secure Multi-User Access

**Business Value:**
- Teams (3-10 users) can share one GiljoAI MCP server
- Each user has individual accountability and audit trail
- Secure API access for MCP tools with revocable credentials
- Foundation for enterprise deployment (WAN/SaaS)

**Technical Value:**
- Per-user authentication and authorization
- Role-based access control (Admin, Developer, Viewer)
- Personal API keys for MCP tools (revocable, trackable)
- Clean migration path: localhost → LAN → WAN → SaaS

### Foundation For: WAN and SaaS Modes (Future)

This implementation provides the authentication foundation that will extend to:
- **WAN Mode:** Add HTTPS, enhanced rate limiting, public internet access
- **SaaS Mode:** Add OAuth2, multi-tenancy, billing/quotas

---

## Current State Analysis

### What's Complete

**Localhost Mode (Production Ready):**
- CLI installer creates database
- API server binds to 127.0.0.1 (localhost only)
- Frontend dashboard accessible at http://localhost:7274
- No authentication required (development mode)
- Single implicit user (local developer)

**LAN Mode (Network Config Only):**
- Setup wizard can detect server IP
- API can bind to 0.0.0.0 (network accessible)
- Firewall configuration documented
- CORS origin configuration exists
- Network deployment runbook complete

### What's Missing (Critical Gaps)

**Authentication System:**
- No user accounts database schema
- No login endpoint or JWT token generation
- No password hashing implementation
- No API key generation/validation
- No authentication middleware

**User Management:**
- No admin account creation flow
- No user CRUD operations
- No role-based access control
- No user dashboard UI

**API Key System:**
- No personal API key generation
- No key storage/hashing
- No key validation middleware
- No key management UI

---

## Implementation Phases

### Phase 1: Database Schema & Backend Auth (3-4 days)

**Lead Agents:** Database Expert + Backend Integration Tester

**Objective:** Create authentication backend infrastructure

#### Tasks:

**1.1 Database Schema (Database Expert - 4h)**
- Design User and APIKey database models
- Create Alembic migration
- Add indexes for performance
- Test migration on clean database

**1.2 Password Security (Backend Tester - 2h)**
- Implement bcrypt password hashing
- Create password validation utilities
- Add password strength requirements
- Write comprehensive tests

**1.3 JWT Token System (Backend Tester - 3h)**
- Install PyJWT library
- Implement token generation
- Implement token validation
- Add token expiry handling (24h)

**1.4 Authentication Endpoints (Backend Tester - 4h)**
- POST /api/auth/register (admin only)
- POST /api/auth/login (returns JWT)
- POST /api/auth/logout (clear cookie)
- GET /api/auth/me (current user)

**1.5 API Key System (Backend Tester - 4h)**
- Generate personal API keys (format: gk_userid_random)
- Hash and store keys securely
- GET /api/auth/api-keys (list user's keys)
- POST /api/auth/api-keys (generate new)
- DELETE /api/auth/api-keys/{id} (revoke)

**1.6 Authentication Middleware (Backend Tester - 3h)**
- Update existing auth middleware
- Support JWT tokens (web dashboard)
- Support API keys (MCP tools)
- Skip auth for localhost mode (127.0.0.1)
- Add comprehensive logging

#### Acceptance Criteria:

- Users table created with username, email, password_hash, role
- APIKeys table created with user_id, key_hash, key_prefix
- Login endpoint returns JWT token in httpOnly cookie
- API key validation works for MCP tool requests
- Localhost mode bypasses authentication
- All integration tests pass (90%+ coverage)

---

### Phase 2: Frontend Login & User Management (2-3 days)

**Lead Agents:** Frontend Tester + UX Designer

**Objective:** Create user-facing authentication UI

#### Tasks:

**2.1 Login Page Component (Frontend Tester - 3h)**
- Create LoginView.vue
- Username/password form
- Error handling (invalid credentials)
- Redirect to dashboard on success
- "Remember me" functionality

**2.2 Axios Interceptor Update (Frontend Tester - 2h)**
- Configure withCredentials for cookies
- Add 401 response handler (redirect to login)
- Skip auth for localhost detection
- Test cookie-based auth flow

**2.3 API Key Management UI (Frontend Tester - 4h)**
- Create ApiKeyManager.vue component
- List user's API keys (name, created, last used)
- Generate new key button + modal
- Display full key ONCE (copy to clipboard)
- Delete key button (with confirmation)
- Add to Settings view

**2.4 User Management UI (Admin Only) (Frontend Tester - 3h)**
- Create UserManagementView.vue
- List all users (admin only)
- Add new user button + modal
- Edit user (role, active status)
- Delete user (with confirmation)

**2.5 Route Guards (Frontend Tester - 2h)**
- Add authentication check before routes
- Skip check for localhost mode
- Redirect to /login if not authenticated
- Store attempted route for post-login redirect

#### Acceptance Criteria:

- Login page works (correct credentials → dashboard)
- Invalid credentials show clear error message
- JWT stored in httpOnly cookie (not accessible via JS)
- 401 errors redirect to login page
- API key management UI works (generate, view, revoke)
- Admin can create/manage users
- Localhost mode bypasses login requirement

---

### Phase 3: Setup Wizard Integration (1-2 days)

**Lead Agent:** Frontend Tester

**Objective:** Create admin account during LAN setup

#### Tasks:

**3.1 Setup Wizard Update (Frontend Tester - 3h)**
- Add "Create Admin Account" step to wizard
- Fields: username, email, password, confirm password
- Password strength indicator
- Validate password requirements
- Submit to backend during setup completion

**3.2 Backend Setup Endpoint Update (Backend Tester - 2h)**
- Update /api/setup/complete to create admin user
- Hash password before storing
- Generate first API key for admin
- Return API key in setup response

**3.3 Completion Screen Update (Frontend Tester - 2h)**
- Display admin credentials created
- Show generated API key (copy button)
- Warning to save API key securely
- MCP configuration example with key
- Instructions for additional users

#### Acceptance Criteria:

- Wizard asks for admin username/email/password in LAN mode
- Password validation enforced (12+ chars, complexity)
- Admin user created successfully in database
- Admin's first API key generated and displayed
- Completion screen shows key with copy button
- MCP config example includes GILJO_API_KEY

---

### Phase 4: Testing & Documentation (1-2 days)

**Lead Agents:** Backend Integration Tester + Documentation Manager

**Objective:** Validate system and document implementation

#### Tasks:

**4.1 End-to-End Testing (Backend Tester - 4h)**
- Complete auth flow: register → login → API call
- MCP tool with API key can access server
- Localhost mode still works (no auth)
- LAN mode requires auth
- Token expiry works (24h)
- API key revocation works

**4.2 Integration Testing (Backend Tester - 3h)**
- Multi-user scenarios (3+ users)
- Role-based access control tests
- API key management tests
- Performance testing (auth overhead < 10ms)
- Security testing (SQL injection, XSS, CSRF)

**4.3 Documentation Updates (Documentation Manager - 4h)**
- Update LAN_DEPLOYMENT_GUIDE.md
- Create LAN_AUTH_USER_GUIDE.md
- Update QUICK_START.md with auth steps
- Document API endpoints in MCP_TOOLS_MANUAL.md
- Create troubleshooting section

**4.4 Devlog & Session Memories (Documentation Manager - 2h)**
- Create comprehensive devlog
- Document key decisions and rationale
- Capture lessons learned
- Create session memory for future reference

#### Acceptance Criteria:

- Complete auth flow works: register → login → API call
- MCP server with API key successfully accesses server
- All documentation updated and deployed
- Migration path documented for existing LAN users
- Troubleshooting guide comprehensive

---

## Total Timeline: 7-11 Days

**Conservative Estimate:** 11 days (buffer for integration issues, testing, refinement)

**Optimistic Estimate:** 7 days (if no major blockers, parallel work)

**Critical Path:**
```
Day 1-2: Database schema + Password/JWT implementation
Day 3: Auth endpoints + middleware
Day 4: Login UI + Axios setup
Day 5: API key UI + User management
Day 6: Setup wizard integration
Day 7: E2E testing + bug fixes
Days 8-9: Documentation + refinement
Days 10-11: Buffer for unexpected issues
```

---

## Agent Assignment Matrix

| Phase | Primary Agent | Supporting Agent | Estimated Time | Priority |
|-------|--------------|------------------|----------------|----------|
| Phase 1 (Backend) | Backend Integration Tester | Database Expert | 3-4 days | CRITICAL |
| Phase 2 (Frontend) | Frontend Tester | UX Designer | 2-3 days | CRITICAL |
| Phase 3 (Wizard) | Frontend Tester | Backend Tester | 1-2 days | HIGH |
| Phase 4 (Testing/Docs) | Backend Integration Tester | Documentation Manager | 1-2 days | HIGH |

---

## Dependencies & Risks

### Dependencies

**External Libraries:**
- PyJWT (JWT token handling) - `pip install pyjwt`
- bcrypt (password hashing) - `pip install bcrypt`
- Both already in requirements.txt

**Infrastructure:**
- PostgreSQL database (already in use)
- Existing API server architecture
- Existing frontend (Vue 3 + Vuetify)

**No External Dependencies** - All work internal to GiljoAI MCP

### Risks & Mitigation

**Risk 1: Breaking Localhost Mode (High Impact)**
- **Probability:** Medium
- **Impact:** Critical (blocks development workflow)
- **Mitigation:**
  - Comprehensive localhost mode tests before merging
  - Mode detection in middleware (127.0.0.1 bypasses auth)
  - Regression test suite for localhost

**Risk 2: JWT Token Security Issues (High Impact)**
- **Probability:** Low (using proven library)
- **Impact:** Critical (security vulnerability)
- **Mitigation:**
  - Use industry-standard PyJWT library
  - httpOnly cookies (prevent XSS)
  - Short expiry (24h)
  - Secure flag for HTTPS
  - CSRF protection in future WAN mode

**Risk 3: API Key Generation Collision (Medium Impact)**
- **Probability:** Very low (cryptographically secure random)
- **Impact:** Medium (user auth failure)
- **Mitigation:**
  - Use secrets.token_urlsafe(32) for randomness
  - Database unique constraint on key_hash
  - Retry logic on collision (unlikely)

**Risk 4: Migration Issues for Existing LAN Users (Medium Impact)**
- **Probability:** High (breaking change)
- **Impact:** Medium (requires manual intervention)
- **Mitigation:**
  - Clear migration documentation
  - Auto-create admin if no users exist
  - Provide CLI tool for user creation
  - Support backward compatibility flag (temporary)

---

## Success Metrics

### Functional Requirements

- Users can register and login with username/password
- Dashboard requires authentication in LAN mode
- Each user has personal API keys (multiple allowed)
- MCP tools work with personal API keys
- Localhost mode still works without authentication
- API key revocation takes immediate effect
- Role-based access control enforced (Admin, Developer, Viewer)

### Performance Requirements

- Login latency: < 200ms (p95)
- API key validation overhead: < 10ms
- JWT token validation: < 5ms
- No degradation in localhost mode performance

### Security Requirements

- Passwords hashed with bcrypt (12 rounds)
- JWT tokens in httpOnly cookies (XSS protection)
- API keys hashed in database (not plaintext)
- Failed login attempts logged
- Rate limiting on auth endpoints (60 req/min)
- Localhost mode detection cannot be bypassed

### Quality Requirements

- Test coverage: 90%+ for new code
- All integration tests passing
- No hardcoded credentials or secrets
- Comprehensive error handling
- Clear user-facing error messages
- Professional code (no emojis)

---

## Key Design Decisions

### Decision 1: JWT Tokens for Web, API Keys for Tools

**Rationale:**
- Web dashboard: Session-based (JWT in httpOnly cookies)
- MCP tools/CLI: API keys (long-lived, revocable)
- Two different use cases require different auth mechanisms

**Alternatives Considered:**
- API keys for everything (rejected: poor UX for web)
- OAuth2 (rejected: overkill for LAN, planned for SaaS)

### Decision 2: Personal API Keys (Per-User)

**Rationale:**
- Individual accountability (audit trails)
- Revocable per-user (not global)
- Multiple keys per user (laptop, CI/CD, etc.)
- Foundational for WAN/SaaS modes

**Alternatives Considered:**
- Single shared API key (rejected: no accountability)
- No API keys (rejected: MCP tools need auth)

### Decision 3: Setup Wizard Creates Admin

**Rationale:**
- Zero-trust default (no default credentials)
- User chooses secure password during setup
- Streamlined onboarding experience
- No separate admin creation step

**Alternatives Considered:**
- Default admin/admin credentials (rejected: security risk)
- CLI-only admin creation (rejected: poor UX)

### Decision 4: bcrypt for Password Hashing

**Rationale:**
- Industry standard for password hashing
- Built-in salting
- Configurable cost factor (balance security/performance)
- Widely vetted and trusted

**Alternatives Considered:**
- Argon2 (considered, bcrypt simpler and sufficient)
- SHA-256 (rejected: not designed for passwords)

### Decision 5: 24-Hour JWT Expiry

**Rationale:**
- Balance security (short-lived) and UX (not too frequent re-login)
- Industry standard for web sessions
- Future: Add refresh tokens for longer sessions

**Alternatives Considered:**
- 1 hour (rejected: too frequent re-login)
- 7 days (rejected: too long, security risk)

---

## Implementation Standards

### Code Quality

**Python Backend:**
- Type hints for all functions
- Docstrings for all public APIs
- Error handling with specific exceptions
- Logging at INFO level for auth events
- Tests for all endpoints (pytest)

**Vue Frontend:**
- Composition API (script setup)
- TypeScript for complex components
- Comprehensive error handling
- Loading states for async operations
- Accessibility (WCAG 2.1 AA)

### Security Standards

**Password Requirements:**
- Minimum 12 characters
- Must include: uppercase, lowercase, number, special character
- Cannot contain username
- Not in common password list

**API Key Format:**
- Format: `gk_{user_id}_{random_32chars}`
- Example: `gk_550e8400_7f3d2e1a9b8c4d6f1e2a3b5c7d9f0e1a`
- User ID prefix for easy identification
- Cryptographically secure random component

**Token Security:**
- JWT algorithm: HS256
- Secret key: 256-bit random (from environment variable)
- httpOnly cookie (no JavaScript access)
- Secure flag (HTTPS only in WAN mode)
- SameSite=Strict (CSRF protection)

### Testing Standards

**Test Coverage Requirements:**
- Unit tests: 95%+ for business logic
- Integration tests: All API endpoints
- E2E tests: Critical user flows
- Security tests: Auth bypass attempts, SQL injection, XSS

**Test Scenarios:**
- Happy path (valid credentials, successful operations)
- Error paths (invalid credentials, expired tokens)
- Edge cases (empty fields, SQL injection attempts)
- Concurrency (multiple login attempts, race conditions)

---

## Migration Path (Existing LAN Users)

### For Users Already Running LAN Mode (No Auth)

**Before Migration:**
- Current state: API accessible without authentication
- Users: Implicit single user (no accounts)
- API keys: None (not required)

**Migration Steps:**

1. **Backup Current State**
   ```bash
   # Backup database
   pg_dump -U postgres giljo_mcp > backup_pre_auth.sql

   # Backup config
   cp config.yaml config.yaml.backup
   ```

2. **Update GiljoAI MCP (git pull + install)**
   ```bash
   git pull
   pip install -r requirements.txt  # Installs PyJWT, bcrypt
   ```

3. **Run Database Migration**
   ```bash
   # Alembic migration will add users and api_keys tables
   alembic upgrade head
   ```

4. **Create Admin User (CLI or Wizard)**

   **Option A: CLI (Quick)**
   ```bash
   python scripts/create_admin_user.py \
     --username admin \
     --password "YourSecurePassword123!" \
     --email admin@company.com
   ```

   **Option B: Setup Wizard (Recommended)**
   ```
   Navigate to http://server:7274/setup
   → Select LAN mode
   → Create admin account
   → Complete wizard
   ```

5. **Restart Services**
   ```bash
   stop_giljo.bat && start_giljo.bat  # Windows
   sudo systemctl restart giljo-mcp    # Linux
   ```

6. **Generate API Keys for Team**
   ```
   Admin logs in → Dashboard → Users → Add Users
   Each user logs in → Settings → API Keys → Generate New Key
   ```

7. **Update MCP Tool Configurations**
   ```json
   // ~/.claude.json (each user)
   {
     "mcpServers": {
       "giljo-mcp": {
         "env": {
           "GILJO_SERVER_URL": "http://server:7272",
           "GILJO_API_KEY": "gk_user_generated_key_here"
         }
       }
     }
   }
   ```

**Downtime:** ~5-10 minutes (restart only)

**Rollback Plan:**
```bash
# Restore backup if issues
psql -U postgres -d giljo_mcp < backup_pre_auth.sql
cp config.yaml.backup config.yaml
git checkout [previous-commit]
stop_giljo.bat && start_giljo.bat
```

---

## Post-Implementation Checklist

### Before Deployment

- [ ] All unit tests passing (95%+ coverage)
- [ ] All integration tests passing
- [ ] E2E auth flow tested (register → login → API call)
- [ ] Localhost mode regression tests passed
- [ ] Security audit completed (no SQL injection, XSS, CSRF)
- [ ] Performance benchmarks met (auth overhead < 10ms)
- [ ] Documentation complete and reviewed

### Deployment

- [ ] Database migration tested on staging
- [ ] Rollback plan documented and tested
- [ ] Admin user creation process validated
- [ ] API key generation tested
- [ ] MCP tool integration tested

### Post-Deployment

- [ ] Monitor error logs for auth failures
- [ ] Verify localhost mode still works
- [ ] Verify LAN mode requires auth
- [ ] Collect user feedback (first 3 days)
- [ ] Address any critical issues within 24h
- [ ] Document lessons learned

---

## Next Steps

### Immediate Actions

1. **Review and Approve Plan** (Orchestrator)
   - Validate timeline and approach
   - Confirm agent assignments
   - Approve budget and priorities

2. **Create Agent Prompts** (Documentation Manager)
   - Database Expert prompt file
   - Backend Integration Tester prompt file
   - Frontend Tester prompt file
   - UX Designer prompt file (supporting)

3. **Initialize Project Tracking**
   - Create GitHub issues for each phase
   - Set up project board (Kanban)
   - Define done criteria for each task

4. **Kick Off Phase 1** (Database Expert + Backend Tester)
   - Database schema design
   - Alembic migration creation
   - Password hashing implementation

### Future Enhancements (Post-LAN Auth)

**Phase 2 (Future Sprints):**
- Refresh tokens for longer sessions
- 2FA/MFA support
- Password reset flow (email-based)
- Account recovery mechanisms
- IP allowlisting/blocklisting (optional)

**Phase 3 (WAN Mode):**
- HTTPS/TLS integration
- Enhanced rate limiting (per-IP, per-user)
- CSRF token protection
- Security headers middleware
- Brute-force protection (fail2ban)

**Phase 4 (SaaS Mode):**
- OAuth2 integration (Google, GitHub, Microsoft)
- Multi-tenancy (tenant_key isolation)
- Company/team management
- Billing and subscription integration
- Usage quotas per plan

---

## References

### Documentation
- NETWORK_AUTHENTICATION_ARCHITECTURE.md - Complete auth architecture
- DEPLOYMENT_MODE_COMPARISON.md - Mode comparison matrix
- LAN_DEPLOYMENT_GUIDE.md - LAN setup instructions
- IMPLEMENTATION_PLAN.md - Overall project plan

### Previous Work
- Oct 6 LAN implementation doc (network config, no auth)
- Setup wizard implementation (database creation, network detection)
- LAN deployment runbook (production-ready network setup)

### Technical Standards
- CLAUDE.md - Project coding standards
- MCP_TOOLS_MANUAL.md - MCP tool documentation
- TECHNICAL_ARCHITECTURE.md - System architecture

---

## Conclusion

This implementation plan provides a comprehensive roadmap for implementing user authentication in LAN mode, establishing the foundation for secure multi-user collaboration and future WAN/SaaS deployment.

**Key Outcomes:**
- Secure per-user authentication for LAN mode
- Personal API keys for MCP tools
- Admin-managed user accounts
- Role-based access control
- Seamless migration from localhost
- Foundation for WAN and SaaS modes

**Timeline:** 7-11 days (conservative estimate)

**Risk:** Low to medium (well-defined scope, proven technologies)

**Value:** High (enables team collaboration, foundational for enterprise)

---

**Document Status:** Ready for Implementation
**Version:** 1.0
**Last Updated:** 2025-10-07
**Next Review:** After Phase 1 completion
