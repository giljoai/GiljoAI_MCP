# LAN Authentication Implementation - Coordination Guide

**Version:** 1.0
**Date:** 2025-10-07
**Purpose:** Coordinate work between agents during LAN auth implementation

---

## Team Structure

### Core Team (4 Agents)

| Agent | Role | Phase | Daily Hours | Total Days |
|-------|------|-------|-------------|------------|
| **Database Expert** | Schema & utilities | Phase 1 | 8h | 1 day |
| **Backend Integration Tester** | Auth endpoints & middleware | Phase 1 | 8h | 2-3 days |
| **Frontend Tester** | Login UI & API key management | Phase 2 | 8h | 2-3 days |
| **Documentation Manager** | Testing & documentation | Phase 4 | 6h | 1-2 days |

### Supporting Roles

- **UX Designer** (optional): UI polish, accessibility review
- **Orchestrator**: Overall coordination, decision making, handoffs

---

## Daily Standup Format

Each agent reports daily progress in this format:

### Standup Template

**Date:** YYYY-MM-DD
**Agent:** [Your Name]
**Phase:** [Current Phase]

**Yesterday:**
- What I completed
- Tests passing/failing
- Blockers resolved

**Today:**
- What I'm working on
- Expected completion time
- New blockers

**Tomorrow:**
- Planned work
- Handoffs needed

**Blockers:**
- Current blockers (if any)
- Help needed

**Questions:**
- Questions for team/orchestrator

---

## Integration Points

### Handoff 1: Database Expert → Backend Tester

**When:** After database schema complete (Day 1 end)

**Database Expert provides:**
- ✅ Users and APIKeys models in `src/giljo_mcp/models.py`
- ✅ Alembic migration tested and verified
- ✅ PasswordManager utility (`src/giljo_mcp/auth/password_manager.py`)
- ✅ APIKeyManager utility (`src/giljo_mcp/auth/api_key_manager.py`)
- ✅ All unit tests passing

**Backend Tester receives:**
- Database schema ready to use
- Password hashing functions ready
- API key generation functions ready
- Migration can be applied to any database

**Validation:**
```bash
# Backend Tester runs these commands to verify handoff
alembic upgrade head  # Should succeed
pytest tests/unit/test_user_model.py -xvs  # Should pass
pytest tests/unit/test_password_manager.py -xvs  # Should pass
```

### Handoff 2: Backend Tester → Frontend Tester

**When:** After auth endpoints complete (Day 3-4 end)

**Backend Tester provides:**
- ✅ POST /api/auth/login endpoint (returns JWT cookie)
- ✅ POST /api/auth/logout endpoint (clears cookie)
- ✅ GET /api/auth/me endpoint (returns current user)
- ✅ API key endpoints (GET/POST/DELETE /api/auth/api-keys)
- ✅ Authentication middleware updated (JWT + API keys)
- ✅ Integration tests passing

**Frontend Tester receives:**
- Complete authentication API ready to use
- JWT tokens work in httpOnly cookies
- API key generation/validation works
- Localhost mode bypasses authentication

**Validation:**
```bash
# Frontend Tester runs these tests
curl -X POST http://localhost:7272/api/auth/login \
  -H "Content-Type: application/json" \
  -d '{"username":"test","password":"Test123!"}'
# Should return 200 with Set-Cookie header

curl http://localhost:7272/api/auth/me \
  -H "Cookie: session_token=<token>"
# Should return user info
```

### Handoff 3: Frontend Tester → Documentation Manager

**When:** After frontend UI complete (Day 6-7 end)

**Frontend Tester provides:**
- ✅ Login page at /login
- ✅ API key management in Settings → API Keys
- ✅ User management in /users (admin only)
- ✅ Route guards protecting authenticated routes
- ✅ Axios interceptor handling 401s

**Documentation Manager receives:**
- Complete authentication system ready for documentation
- E2E flow testable (register → login → generate key)
- Screenshots can be captured for docs

**Validation:**
```
# Documentation Manager tests manually
1. Navigate to http://localhost:7274/login
2. Login with test credentials
3. Verify redirect to dashboard
4. Navigate to Settings → API Keys
5. Generate new API key
6. Copy key and verify MCP config example
```

---

## Shared Dependencies

### Configuration Files

**Location:** `config.yaml`

**Who Modifies:** Setup wizard (automated)

**What Changes:**
```yaml
security:
  api_key_required: true  # Changed from false
  user_accounts: true     # NEW
  jwt_auth: true          # NEW
```

**Coordination:** No manual changes needed during development

### Database Migrations

**Location:** `migrations/versions/`

**Who Creates:** Database Expert

**Who Runs:** All agents (for testing)

**Coordination:**
- Database Expert creates migration (Day 1)
- All other agents run `alembic upgrade head` before starting work
- If migration changes, Database Expert announces in standup

### Environment Variables

**Location:** `.env` (gitignored)

**New Variables Needed:**
```bash
# JWT secret key (generated once, shared in team)
JWT_SECRET_KEY=<random-256-bit-key>
```

**Coordination:**
- Backend Tester generates JWT_SECRET_KEY (Day 2)
- Shares with team via secure channel (not git)
- All agents add to their local .env

**Generate Key:**
```bash
# Backend Tester runs this once
python -c "import secrets; print(secrets.token_urlsafe(32))"
# Output: dGVzdF9zZWNyZXRfa2V5XzEyMzQ1Njc4OTBhYmNkZWY=
```

---

## Testing Coordination

### Unit Tests

**Responsibility:** Each agent tests their own code

**Coverage Target:** 95%+ for new code

**Coordination:**
- Database Expert: User/APIKey models (100% coverage)
- Backend Tester: Auth endpoints (90%+ coverage)
- Frontend Tester: Vue components (80%+ coverage)

**Shared Test Database:**
```bash
# All agents use same test database config
# tests/conftest.py handles setup/teardown
pytest tests/unit/  # Each agent runs their tests
```

### Integration Tests

**Responsibility:** Backend Integration Tester

**Scope:** Complete auth flow (register → login → API call)

**Coordination:**
- Backend Tester writes integration tests (Day 3-4)
- Frontend Tester helps validate UI interactions (Day 6)
- Documentation Manager runs full E2E suite (Day 8)

**Test Environment:**
```bash
# Shared test environment setup
export GILJO_MODE=test
export JWT_SECRET_KEY=test_key_for_testing
pytest tests/integration/test_auth_endpoints.py -xvs
```

### E2E Testing

**Responsibility:** All agents collaborate

**Scope:** Complete user journey (setup → login → use)

**Coordination:**
- Day 7: Frontend Tester + Backend Tester pair on E2E
- Day 8: Documentation Manager validates and documents

**E2E Checklist:**
```
□ Fresh install (clean database)
□ Run setup wizard → create admin
□ Login as admin
□ Generate API key
□ Configure MCP tool with key
□ Make API request with key
□ Verify request succeeds
```

---

## Communication Protocols

### Daily Updates

**When:** End of each day (or major milestone)

**Where:** Project channel / shared document

**Format:** Use standup template above

### Blocker Escalation

**If blocked:**
1. Try to resolve independently (30 min)
2. Ask relevant agent for help (1 hour)
3. Escalate to Orchestrator

**Critical Blockers:**
- Database migration failing
- Auth endpoints not working
- Frontend can't connect to backend
- Test failures blocking progress

**Non-Critical:**
- UI polish decisions
- Performance optimization
- Documentation formatting

### Questions & Decisions

**Technical Questions:**
- Ask relevant agent directly (via comment/message)
- Response expected within 4 hours (same working day)

**Architecture Decisions:**
- Ask Orchestrator
- Document decision in plan
- Notify all agents of change

**User Experience Questions:**
- Ask UX Designer (if available)
- Otherwise, Frontend Tester decides
- Document decision in code comments

---

## Code Review Process

### Who Reviews What

**Database Expert code:**
- Reviewed by: Backend Integration Tester
- Focus: Schema correctness, migration safety

**Backend Tester code:**
- Reviewed by: Database Expert (auth utilities) + Frontend Tester (API contracts)
- Focus: Security, API design, error handling

**Frontend Tester code:**
- Reviewed by: UX Designer (if available) or Backend Tester
- Focus: UX, accessibility, API integration

### Review Checklist

**All Code:**
- [ ] Tests passing
- [ ] Code formatted (black for Python, prettier for Vue)
- [ ] No hardcoded secrets or credentials
- [ ] Error handling comprehensive
- [ ] Logging appropriate

**Security-Critical Code:**
- [ ] No SQL injection vulnerabilities
- [ ] No XSS vulnerabilities
- [ ] Passwords hashed (never plaintext)
- [ ] API keys hashed (never plaintext)
- [ ] JWT tokens properly validated

---

## Rollback Plan

### If Critical Issues Found

**During Development:**
1. Revert problematic commit
2. Notify team in standup
3. Fix issue in new branch
4. Re-review before merge

**During Testing:**
1. Document issue in bug tracker
2. Assess severity (critical, high, medium, low)
3. Critical: Fix immediately (all hands)
4. High: Fix within 24h
5. Medium/Low: Schedule for future sprint

### Database Rollback

**If migration causes issues:**
```bash
# Rollback to previous migration
alembic downgrade -1

# Rollback to specific revision
alembic downgrade <revision_id>

# Nuclear option: drop all tables and start fresh
alembic downgrade base
alembic upgrade head
```

**Coordination:**
- Database Expert announces rollback in team channel
- All agents re-run `alembic upgrade head` after fix

---

## Progress Tracking

### Daily Progress Report

**Location:** Shared document or project board

**Format:**

| Date | Agent | Phase | Tasks Completed | Tasks Remaining | Blocked? |
|------|-------|-------|-----------------|-----------------|----------|
| 2025-10-07 | Database Expert | Phase 1 | User model, migration | Tests | No |
| 2025-10-07 | Backend Tester | Phase 1 | JWT manager | Endpoints | Waiting on DB |

### Milestone Checklist

**Phase 1: Database & Backend (Days 1-4)**
- [ ] Day 1: Database schema complete (Database Expert)
- [ ] Day 2: JWT + password utilities (Backend Tester)
- [ ] Day 3: Auth endpoints (Backend Tester)
- [ ] Day 4: Middleware + integration tests (Backend Tester)

**Phase 2: Frontend (Days 5-7)**
- [ ] Day 5: Login page + axios interceptor (Frontend Tester)
- [ ] Day 6: API key management UI (Frontend Tester)
- [ ] Day 7: User management UI + route guards (Frontend Tester)

**Phase 3: Setup Wizard (Day 8)**
- [ ] Day 8: Wizard integration (Frontend Tester)

**Phase 4: Testing & Docs (Days 9-11)**
- [ ] Day 9: E2E testing (All agents)
- [ ] Day 10: Documentation (Documentation Manager)
- [ ] Day 11: Bug fixes + refinement (All agents)

---

## Success Metrics

### Daily Metrics

**Code Quality:**
- Test coverage: 90%+
- No linting errors
- No security vulnerabilities

**Progress:**
- Tasks completed vs planned
- Blockers resolved
- Handoffs on schedule

### Weekly Metrics

**End of Week 1 (Days 1-5):**
- [ ] Backend auth complete
- [ ] Integration tests passing
- [ ] Frontend login page works

**End of Week 2 (Days 6-11):**
- [ ] Full auth system working
- [ ] E2E tests passing
- [ ] Documentation complete

---

## Emergency Contacts

### Escalation Path

**Level 1: Agent-to-Agent**
- Direct communication between agents
- Expected response: 4 hours

**Level 2: Orchestrator**
- Technical blockers unresolved after 1 day
- Architecture decisions needed
- Expected response: 2 hours

**Level 3: Project Owner**
- Critical system-wide issues
- Scope changes needed
- Timeline at risk

---

## Post-Implementation Review

### After Completion

**Documentation Manager leads:**
- Review session (all agents)
- Lessons learned
- What went well
- What could improve
- Update this coordination guide for future projects

**Review Questions:**
1. Was the timeline accurate?
2. Were handoffs smooth?
3. What blockers could have been avoided?
4. What tools/processes would help next time?
5. How was team communication?

---

## Quick Reference

### Key Commands

```bash
# Database
alembic upgrade head  # Apply migrations
alembic downgrade -1  # Rollback last migration
psql -U postgres -d giljo_mcp  # Connect to database

# Testing
pytest tests/unit/ -xvs  # Run unit tests
pytest tests/integration/ -xvs  # Run integration tests
pytest tests/ --cov=giljo_mcp  # Run with coverage

# Development
python api/run_api.py  # Start API server
cd frontend && npm run dev  # Start frontend
```

### Key Files

```
src/giljo_mcp/
├── models.py                    # Database models (User, APIKey)
├── auth/
│   ├── password_manager.py      # Password hashing
│   ├── api_key_manager.py       # API key generation
│   └── jwt_manager.py           # JWT tokens
api/
├── endpoints/auth.py            # Auth endpoints
└── middleware/auth.py           # Auth middleware
frontend/
├── src/views/LoginView.vue      # Login page
├── src/components/ApiKeyManager.vue  # API key management
└── src/router/index.js          # Route guards
```

---

## Conclusion

This coordination guide ensures smooth collaboration between agents during the LAN authentication implementation. Follow the standup format, respect handoff points, and communicate blockers early for successful delivery.

**Remember:**
- Daily standups keep everyone aligned
- Integration points require validation before proceeding
- Shared dependencies need coordination
- Testing is everyone's responsibility
- Communication is key to success

**Let's build great authentication together!** 🔐

---

**Document Status:** Active
**Version:** 1.0
**Last Updated:** 2025-10-07
**Next Review:** Daily during implementation
