# Handover Instructions for GiljoAI MCP Development

## Purpose
This document provides standardized instructions for creating effective handovers between development agents/sessions working on the GiljoAI MCP project.

---

## 🎯 Quick Reference: The Golden Rules

**Before you start ANY handover implementation:**
READ FIRST `handovers/Reference_docs/QUICK_LAUNCH.txt` and `handovers/Reference_docs/AGENT_FLOW_SUMMARY.md`

Follow these principles " "Use Test-Driven Development (TDD):
  1. Write the test FIRST (it should fail initially)
  2. Implement minimal code to make test pass
  3. Refactor if needed
  4. Test should focus on BEHAVIOR (what the code does),
     not IMPLEMENTATION (how it does it)
  5. Use descriptive test names like 'test_reconnection_uses_exponential_backoff'
  6. Avoid testing internal implementation details""

## THEN ##
1. **Quality**: Chef's kiss production-grade code ONLY - no shortcuts, no bandaids
2. **Freedom**: Dev mode - modify code freely, no production concerns
3. **Installation**: Changes affecting setup? Update `install.py` + related scripts
4. **Clean Code**: DELETE old code, don't comment out. Remove bloat.
5. **Subagents**: Use specialized agents for complex work (database-expert, tdd-implementor, etc.)
6. **Serena MCP**: Use Serena tools for codebase navigation
7. **Docs**: Update ORIGINAL handover (max 1000 words). User summaries max 400 words, 10 bullets.
8. **No Bloat**: Don't create 4000-line documentation! Keep it concise.

---

## Code Discipline: Fold, Don't Reinvent (CRITICAL)

This is a **commercial product** that ships to real users. Every shortcut becomes a support ticket. Every parallel implementation becomes a maintenance burden. The 0700 cleanup series (Feb 2026) removed ~15,800 lines of accumulated drift across ~110 files. We do not go backwards.

**Before writing ANY new code, verify these exist and USE them:**
- **Service layer** (`src/giljo_mcp/services/`) - Business logic lives here, not in endpoints or tools
- **WebSocket events** (`api/websocket_manager.py`) - Real-time updates use the existing broadcast system
- **AgentJobManager** - Agent lifecycle, not ad-hoc status updates
- **TenantManager** - Tenant filtering, not manual WHERE clauses
- **UnifiedTemplateManager** - Template operations, not direct DB queries
- **ProductMemoryRepository** - Memory entries, not raw JSONB manipulation
- **Exception-based error handling** (post-0480) - Raise, don't return dicts

**The discipline:**
1. **Search before you build.** Use Serena `find_symbol` and `get_symbols_overview` to check if the functionality already exists.
2. **Extend, don't duplicate.** Add a method to an existing service rather than creating a new module.
3. **Root-cause fixes only.** If something is broken, find out WHY and fix that. No workarounds, no "good enough" patches.
4. **Leave the codebase cleaner than you found it.** If you touch a file and see dead code or a bandaid fix, clean it up.
5. **Measure against the 0700 baseline.** If your change adds complexity, justify it. If it adds lines without adding capability, rethink it.

---

## Edition Scope: Community vs SaaS (MANDATORY)

The codebase serves TWO editions (not three — Enterprise is a deployment mode of SaaS, not a separate codebase). Development happens in one repo with two long-lived branches: `main` (CE) and `saas`.

**Know which edition your work targets BEFORE writing code.**

| Community Edition (CE) | SaaS Edition |
|------------------------|-------------|
| Branch: `main` (public) | Branch: `saas` (private) |
| Core orchestration engine | OAuth / MFA / SSO |
| Agent management & templates | Billing & subscription (Stripe) |
| Single-user auth (login/password, JWT) | Organization & team management |
| Tenant isolation (kept, hidden in single-user) | Multi-user admin tools, viewer roles |
| WebSocket & MCP protocol | Usage analytics & metering |
| Frontend dashboard | SaaS onboarding flows |
| Community Edition branding | Twilio, email notifications |
| `python install.py` deployment | Docker/K8s deployment |

### Code Isolation Rules

SaaS-only code MUST live in designated directories:
- Backend services: `src/giljo_mcp/saas/`
- API endpoints: `api/saas_endpoints/`
- Middleware: `api/saas_middleware/`
- Frontend: `frontend/src/saas/`
- Tests: `tests/saas/`
- Database migrations (new tables only): `migrations/saas_versions/`

**Import direction rule:** CE code NEVER imports from `saas/` directories. SaaS code may import from CE code. If CE needs to invoke SaaS functionality, use the conditional registration pattern in `app.py`.

**Deletion test:** If all `saas/` directories were deleted, CE must still start, serve requests, and pass all CE tests. If it doesn't, there is a dependency leak — fix it.

**Placement decision:** Does the feature require external infrastructure (Stripe, Twilio, LDAP, OAuth provider) or only make sense with multiple users/orgs? → `saas/` directory. Does it improve core orchestration for any user including solo? → CE directory.

**Existing SaaS-adjacent code stays in CE.** TenantManager, Organization model, multi-user auth, API key system, WebSocket broker — these are in CE directories because CE needs them to function. Do NOT move them to `saas/`.

**Full reference:** `docs/EDITION_ISOLATION_GUIDE.md` — the authoritative guide for directory structure, conditional loading patterns, git workflow, and migration strategy.

---

## Entity Hierarchy & Cascading Impact (CRITICAL)

Every handover plan must account for the full ownership hierarchy and its cascading implications. Changes are never made in pure isolation.

### Ownership Hierarchy

```
Organization
  └── User (admin or member of org)
        └── Product (belongs to user)
              ├── Project (belongs to product)
              │     └── Job (belongs to project)
              │           └── Agent (belongs to assigned job)
              └── Task (belongs to product)
```

**Key relationships:**
- **Organization** is the top-level tenant boundary
- **User** belongs to an organization (admin or regular member)
- **Product** is owned by a user and is the primary work container
- **Project** and **Task** both belong to a product (Task.product_id is NOT NULL)
- **Job** belongs to a project and represents an agent assignment
- **Agent** is bound to a specific job for its lifecycle

**Future considerations (not yet implemented):**
- Admin retirement flow: admins may retire users and reassign their products to a new user
- Collaboration: users may invite viewers and contributors to products
- These are NOT in the system yet, but designs should not paint us into a corner

### Upstream & Downstream Cascading

**Every plan must answer these questions:**

1. **Downstream impact** — If I change entity X, what happens to everything below it?
   - Deleting/deactivating a user: what happens to their products, projects, jobs, agents?
   - Modifying a product: do its projects, tasks, and active jobs remain consistent?
   - Changing a project: do running jobs and their agents break?

2. **Upstream impact** — If I change entity X, does anything above it need updating?
   - Adding a constraint on tasks: does the product or project layer need migration?
   - Changing job behavior: does the project or product need new state tracking?

3. **Sibling impact** — If I change one child, do its siblings stay consistent?
   - Modifying one project under a product: do other projects or tasks conflict?
   - Changing one job in a project: do parallel jobs or agents collide?

**Non-negotiable:** Handover plans that touch any layer of this hierarchy must explicitly document the cascading analysis. "I only changed the task layer" is not sufficient — you must confirm the product, project, and job layers are unaffected.

When modifying or removing code, trace the full chain:
model → repository → service → tool → endpoint → frontend component → test
When removing a DB column: grep for the column name across ALL layers
When removing a tool: check MCP registration, frontend tool lists, and test fixtures

### Installation Flow Protection

A customer downloading GiljoAI originates with `install.py`. The installation flow is the front door to the product and **must never break**.

**Before finalizing any handover plan, verify:**
- **Schema changes**: Does `install.py` create the correct baseline schema? Does the migration path handle both fresh installs and upgrades?
- **New dependencies**: Are they added to `install.py`'s dependency installation step?
- **Configuration changes**: Does `config.yaml` generation in `install.py` account for new fields with sensible defaults?
- **First-run flow**: Does `/welcome` → `/first-login` still work after your changes? New required fields need defaults or wizard steps.
- **Idempotency**: Can `install.py` be run twice without errors? Migrations must be idempotent.

**If your handover touches models, config, dependencies, or auth flow — the installation impact section is mandatory, not optional.**

### Database Migration Protocol

The project uses a **single consolidated baseline migration** (`baseline_v33_unified.py`) that creates the entire schema from scratch. Incremental migrations descend from this baseline for ongoing changes.

**When adding/modifying/removing model columns or tables:**
1. Create an incremental Alembic migration as usual (for existing DB upgrades)
2. The incremental migration MUST include idempotency guards (check if column/table exists before acting)
3. Do NOT update the baseline for every change — incremental migrations handle upgrades

**Periodic baseline squash (before releases or every ~50 handovers):**
1. Regenerate the baseline from current SQLAlchemy models (delete all incrementals, create a new `baseline_vNN`)
2. Update `install.py` stamp logic to recognize old revision IDs and stamp to the new baseline
3. Verify with a fresh install: drop DB, `python install.py`, confirm server starts and `/welcome` works
4. The goal: fresh installs always get one clean migration, existing installs stamp past it

**Why this matters:** Drift between models and baseline caused fresh installs to crash (March 2026). The baseline is the front door for new users — it must match the models exactly.

---

## Commercial-Grade Code Quality Gate (Non-Negotiable)

This is a professional product built to community-facing standards. Code quality minimum: **7/10 or better**. Every commit should maintain or improve the 0700 cleanup baseline (8/10 architecture score, zero lint issues).

### Pre-Commit Quality Checks

Before EVERY commit, verify:

1. **Zero lint issues**: `ruff check src/ api/` must pass clean
2. **No dict return regression**: All Python layers raise exceptions (post-0480/0730) — services, tools, orchestration, helpers, and context management. NOT `return {"success": False, ...}`
3. **Tenant isolation**: Every new DB query filters by `tenant_key` (security-critical)
4. **No dead code introduced**: If you add a method, it must be called. If you remove a caller, remove the method.
5. **Valid agent statuses only**: `waiting`, `working`, `blocked`, `complete`, `silent`, `decommissioned` (post-0491)
6. **No bare expressions**: Every computed value must be assigned or used
7. **No commented-out code**: Delete it. Git has the history.
8. **Pre-commit hooks must pass**: Do NOT use `--no-verify` without explicit user approval

### Periodic Code Quality Audits

Every 15-30 commits, run the code quality audit:
**Read and execute:** `handovers/Code_quality_prompt.md`

This launches parallel subagents to check for drift from the 0700 clean baseline.

### Handover Number Assignment Protocol

When creating a new handover, you MUST validate the number:

1. **Read `handovers/HANDOVER_CATALOGUE.md`** to find available gaps
2. **Check `handovers/completed/` folder** for conflicts with archived numbers
3. **Verify via git**: `git log --oneline --all | grep "0XXX"` to ensure no commit references this number
4. **Prefer filling gaps** in existing ranges rather than jumping to higher numbers
5. **Current known gaps** (check catalogue for latest): 0021, 0033, 0054-0059, 0068, 0097-0099, 0133-0134, 0259, 0277, 0317, 0398-0399, 0413, 0418, 0435-0439, 0441-0449, 0493-0499
6. **Use gaps appropriate to the domain**: Foundation (0001-0100), Architecture (0101-0200), GUI/Context (0201-0300), Services (0301-0400), Agent/Org (0401-0500)

### Endpoint Security
- Every API router MUST inject `Depends(get_current_active_user)` for authentication
- Admin-only endpoints (configuration, database, system management) MUST additionally check user role
- Only explicitly public endpoints (login, health check, frontend config) may skip auth
- Pattern: `async def my_endpoint(current_user: User = Depends(get_current_active_user)):`

### Frontend Code Discipline
- Shared logic goes in `composables/` — do not duplicate utility functions across components
- Use Vuetify theme variables for colors — no `!important` CSS overrides unless compensating for a verified framework bug
- When removing a parent event listener, also remove the child `$emit` call
- **UI accessibility baseline:** Sufficient color contrast (WCAG AA 4.5:1 ratio), color-blind safe palettes (no red/green as sole state differentiator), keyboard navigability for all interactive elements (tab order, enter/space to activate). Screen reader optimization (ARIA roles, live regions) is not required at this stage.
- **Frontend tests exist**: `frontend/tests/` with Vitest + @vue/test-utils + @pinia/testing. Run `npm run test:run` from `frontend/`. Setup: `frontend/tests/setup.js` (499 lines, Vuetify stubs + API mocks). 105+ existing spec files — add tests for new components.

### Function Size Limits
- No function or method exceeds 200 lines without explicit justification documented in the handover
- No class exceeds 1000 lines — split into focused modules

### No Placeholder Data
- No `random.randint()` or fabricated values in production code paths
- No hardcoded fake metrics or statistics
- If real data is unavailable: return null, raise an exception, or mark as "not yet implemented" — never fabricate

---

## Code Quality Standards

### Production-Grade Requirements
All code must meet these non-negotiable standards:

- ✅ **Chef's Kiss Quality**: Production-grade code only - no shortcuts, no bandaids, no quick fixes
- ✅ **Dev Mode Freedom**: We are in development mode - modify any code freely without production concerns
- ✅ **Installation Flow Awareness**: If changes impact setup/installation, MUST update `install.py` and related scripts
- ✅ **Clean Refactoring**: When changing existing code, REMOVE it - do not comment out. Remove bloat when amending/replacing
- ✅ **Use Subagents**: Leverage specialized subagents (database-expert, tdd-implementor, ux-designer, etc.) for complex work
- ✅ **Serena MCP Available**: Use Serena MCP tools for advanced codebase navigation and symbol manipulation

### Documentation Standards

**Summary Documentation:**
- ✅ **Write back to scope document**: Update the ORIGINAL handover document with completion summary
- ✅ **Max 1000 words**: Keep summaries concise and scannable
- ✅ **Separate docs for complexity**: Only create `###_[projectname]_summary.md` for extremely complex implementations
- ✅ **Avoid documentation bloat**: Recent project had 4000+ lines of docs - too much!
- ✅ **User summaries**: Max 400 words when complete
- ✅ **Lists**: Max 10 bullets if lists are required
- ✅ **Expect follow-up**: User will ask questions if they need more detail

**Example of Good Documentation:**
```markdown
## Implementation Summary (Added to Original Handover)

### What Was Built
- Database schema: 7 new columns in mcp_agent_jobs table
- Backend: OrchestratorSuccessionManager class (561 lines)
- Frontend: 3 UI components (SuccessionTimeline, LaunchDialog, AgentCard updates)
- Tests: 45 integration tests (80% coverage)

### Key Files Modified
- `install.py` (migration logic, lines 1447-1589)
- `src/giljo_mcp/models.py` (schema additions)
- `frontend/src/components/projects/AgentCardEnhanced.vue`

### Installation Impact
Migration runs automatically in install.py. Idempotent - safe for fresh installs and upgrades.

### Status
✅ Production ready. All tests passing. Documentation complete.
```

**Example of Too Much Documentation:**
```markdown
❌ Creating separate files:
   - 0080_DATABASE_IMPLEMENTATION_SUMMARY.md (12 sections, 500+ lines)
   - 0080_QUICK_START.md (250 lines)
   - 0080_completion_summary.md (500 lines)
   - 0080_implementation_checklist.md (400 lines)
   - 0080_integration_tests_summary.md (600+ lines)

   Total: 2,250+ lines across 5 files ❌ TOO MUCH!
```

---

## Pre-Handover Checklist

### 1. Git Status Check
**ALWAYS check git status before creating a handover:**

```bash
git status
git diff
git log --oneline -5
```

**Document:**
- Current branch
- Uncommitted changes
- Recent commits relevant to the task
- Any merge conflicts or pending PRs

### 2. Review Sub-Agent Profiles
**Location:** `.claude/agent_profiles/`

**Read the relevant profiles:**
- `orchestrator-coordinator.md` - Project planning and multi-agent coordination
- `system-architect.md` - Architecture decisions and system design
- `database-expert.md` - Database schema and optimization
- `tdd-implementor.md` - Test-driven development implementation
- `network-security-engineer.md` - Network configuration and security
- `installation-flow-agent.md` - Installation and deployment
- `frontend-tester.md` - Frontend testing and validation
- `ux-designer.md` - UI/UX design and accessibility
- `backend-integration-tester.md` - Backend integration testing
- `documentation-manager.md` - Documentation creation and maintenance
- `deep-researcher.md` - Research and investigation

**Purpose:** Understanding which sub-agents should handle specific aspects of the handover task.

### 3. Project Resources Awareness

**Essential Documentation Folders:**

**a) `/docs/sessions/`**
- Previous agent session memories
- Context from earlier work
- Lessons learned
- Known issues and solutions

**b) `/docs/devlog/`**
- Development timeline
- Feature implementation logs
- Architectural decision records
- Completion reports

**c) `/docs/guides/`**
- Implementation guides
- Best practices
- Architecture patterns

**d) `/docs/manuals/`**
- MCP tools manual
- API reference
- Testing manuals

**e) `/handovers/`**
- Previous handover documents
- Active task assignments

### 4. Serena MCP Tools

**Serena MCP Server provides advanced code navigation:**

Available tools:
- `mcp__serena__find_symbol` - Find code symbols by name path
- `mcp__serena__get_symbols_overview` - Get file overview
- `mcp__serena__find_referencing_symbols` - Find references
- `mcp__serena__replace_symbol_body` - Edit code symbols
- `mcp__serena__search_for_pattern` - Pattern search
- `mcp__serena__read_memory` - Read project memories
- `mcp__serena__write_memory` - Write project memories

**Use Serena for:**
- Understanding codebase structure
- Finding related code sections
- Analyzing dependencies
- Researching implementation patterns

### 5. Git Repository Research

**CRITICAL: Always check GitHub for:**
- Open issues related to the task
- Recent PRs that may affect the work
- Contributor discussions
- Release notes and changelogs

**Repository:** `https://github.com/patrik-giljoai/GiljoAI-MCP`

---

## Handover Document Structure

Every handover document MUST contain:

### 1. Handover Metadata

```markdown
# Handover: [Task Name]

**Date:** YYYY-MM-DD
**From Agent:** [Agent name/session ID]
**To Agent:** [Target agent profile or "Next Session"]
**Priority:** [Critical | High | Medium | Low]
**Estimated Complexity:** [Hours/Days]
**Status:** [Not Started | In Progress | Blocked | Ready for Testing]
```

### 2. Task Summary

**Brief Overview (2-3 sentences):**
- What needs to be done
- Why it's important
- Expected outcome

### 3. Context and Background

**Include:**
- Previous discussion that led to this task
- Related issues or features
- Architectural decisions already made
- User requirements and constraints

### 4. Technical Details

**Files to Modify:**
- List all files that need changes
- Explain what changes are needed in each file
- Note any file dependencies

**Key Code Sections:**
- Reference specific line numbers
- Include relevant code snippets
- Explain current implementation

**Database Changes:**
- Schema modifications needed
- Migration strategy
- Data impact assessment

**API Changes:**
- New endpoints or modifications
- Request/response format changes
- Authentication/authorization impact

**Frontend Changes:**
- UI components affected
- State management updates
- WebSocket integration needs

### 5. Implementation Plan

**Step-by-Step Approach:**
1. Phase 1: [Description]
   - Specific actions
   - Expected outcome
   - Testing criteria

2. Phase 2: [Description]
   - Specific actions
   - Expected outcome
   - Testing criteria

3. Phase 3: [Description]
   - Specific actions
   - Expected outcome
   - Testing criteria

**Recommended Sub-Agent:**
- Which agent profile is best suited
- Why this agent should handle it

### 6. Testing Requirements

**Unit Tests:**
- Which tests need to be written
- Test coverage expectations

**Integration Tests:**
- Component integration testing
- API endpoint testing

**Manual Testing:**
- Step-by-step manual test procedure
- Expected results for each step
- Known edge cases

### 7. Dependencies and Blockers

**Dependencies:**
- Tasks that must complete first
- External library requirements
- Infrastructure needs

**Known Blockers:**
- Issues preventing progress
- Questions needing answers
- Decisions requiring user input

### 8. Success Criteria

**Definition of Done:**
- Feature works as specified
- All tests pass
- Code reviewed and approved
- Documentation updated
- Deployed/merged to appropriate branch

### 9. Rollback Plan

**If Things Go Wrong:**
- How to revert changes
- Backup/restore procedures
- Fallback configuration

### 10. Additional Resources

**Links:**
- Related GitHub issues
- Documentation references
- External resources
- Similar implementations

---

## Handover File Naming Convention

**Format:**
```
[NNNN]_[SHORT_DESCRIPTION].md
```

**Numbering Rules:**
1. **ALWAYS check [HANDOVER_CATALOGUE.md](./HANDOVER_CATALOGUE.md) first**
2. Check `completed/reference/[range]/` for conflicts
3. Use available gaps when appropriate
4. Use 4-digit zero-padded sequence number: `0001`, `0325`, `0400`, etc.

**Current Number Ranges:**
| Range | Domain | Next Available |
|-------|--------|----------------|
| 0001-0100 | Foundation | Check catalogue |
| 0101-0200 | Architecture | Check catalogue |
| 0201-0300 | GUI & Context | Check catalogue |
| 0301-0400 | Services & Security | **0326+** |
| 0401-0500 | Reserved | 0401 |
| 0501-0600 | Remediation | Check catalogue |
| 0601-0700 | Migration | Check catalogue |

**Available Gaps (Dec 2025):**
- 0304, 0307, 0308, 0317, 0319 (Context series)
- 0326+ (Next sequential)

**Examples:**
- `0325_TENANT_ISOLATION_SURGICAL_FIX.md`
- `0326_NEW_FEATURE.md`
- `0400_MAJOR_REFACTOR.md`

**How to Determine Next Sequence Number:**
```bash
# 1. Check the catalogue first!
cat handovers/HANDOVER_CATALOGUE.md | grep "Available\|Next"

# 2. Check reference archives for conflicts
ls handovers/completed/reference/0301-0400/

# 3. Use the next available number from catalogue
```

---

## Agent Communication Protocol

### When Creating a Handover

**DO:**
- ✅ Be explicit and detailed
- ✅ Include code snippets and line numbers
- ✅ Document your reasoning
- ✅ List open questions
- ✅ Provide testing steps
- ✅ Reference related files and docs

**DON'T:**
- ❌ Assume knowledge of previous discussions
- ❌ Use vague language ("fix the thing", "update that file")
- ❌ Skip testing requirements
- ❌ Ignore edge cases
- ❌ Forget to document blockers

### When Receiving a Handover

**DO:**
- ✅ Read the entire handover document first
- ✅ Check git status and recent changes
- ✅ Review referenced documentation
- ✅ Use Serena MCP to explore codebase
- ✅ Ask questions if anything is unclear
- ✅ Update the handover with your progress

**DON'T:**
- ❌ Start coding immediately
- ❌ Ignore the implementation plan
- ❌ Skip the context section
- ❌ Make assumptions about requirements
- ❌ Forget to test thoroughly

---

## Handover Update Protocol

**As work progresses, update the handover document:**

```markdown
## Progress Updates

### [Date] - [Agent/Session]
**Status:** [In Progress | Completed | Blocked]
**Work Done:**
- [Specific changes made]
- [Tests added/passed]
- [Issues discovered]

**Next Steps:**
- [What's remaining]
- [New blockers]
- [Questions for user]
```

---

## Special Cases

### Blocked Handovers

If blocked, document:
1. **What's blocking:** Specific blocker description
2. **Who can unblock:** User decision, external dependency, etc.
3. **Workarounds:** Temporary solutions if available
4. **Impact:** What can't proceed until unblocked

### Emergency Handovers

For critical bugs or production issues:
1. Use priority: **CRITICAL**
2. Include reproduction steps
3. Document impact on users
4. Provide immediate workaround if available
5. Escalation path

### Research Handovers

When research is needed before implementation:
1. Define research questions
2. List sources to investigate
3. Document findings format
4. Set research scope/time limit

---

## Git Commit Standards for Handover Work

```bash
# When completing a handover task
git add .
git commit -m "feat: [task name] - [brief description]

Completes handover: handovers/HANDOVER_YYYYMMDD_TASK_NAME.md

- [Bullet point of major change 1]
- [Bullet point of major change 2]
- [Bullet point of major change 3]

Closes #[issue number if applicable]"
```

---

## Handover Completion Protocol

**When a handover is COMPLETED, move it to the archive folder:**

### Steps:

1. **Update handover status** in Progress Updates section:
   ```markdown
   ### [Date] - [Agent/Session]
   **Status:** Completed
   **Work Done:**
   - [All completed tasks]
   - [All tests passed]
   - [Final verification complete]

   **Final Notes:**
   - [Any lessons learned]
   - [Future considerations]
   ```

2. **Create completed folder** if it doesn't exist:
   ```bash
   mkdir -p handovers/completed
   ```

3. **Move and rename the handover file:**
   ```bash
   # Format: [SEQUENCE]_HANDOVER_YYYYMMDD_[TASK_NAME]-C.md
   # The "-C" suffix indicates COMPLETED

   # Example:
   mv handovers/0002_HANDOVER_20251012_REMOVE_LOCALHOST_BYPASS_COMPLETE_V3_UNIFICATION.md \
      handovers/completed/0002_HANDOVER_20251012_REMOVE_LOCALHOST_BYPASS_COMPLETE_V3_UNIFICATION-C.md
   ```

4. **Commit the archive:**
   ```bash
   git add handovers/completed/
   git commit -m "docs: Archive completed handover 0002 - Localhost bypass removal complete"
   ```

### Naming Convention for Completed Handovers:

**Format:**
```
handovers/completed/[SEQUENCE]_HANDOVER_YYYYMMDD_[TASK_NAME]-C.md
```

**Examples:**
- `handovers/completed/0001_HANDOVER_20251012_REMOVE_DYNAMIC_IP_DETECTION-C.md`
- `handovers/completed/0002_HANDOVER_20251012_REMOVE_LOCALHOST_BYPASS_COMPLETE_V3_UNIFICATION-C.md`
- `handovers/completed/0003_HANDOVER_20251013_INSTALLER_CORS_FIX-C.md`

### Why Archive Completed Handovers?

- ✅ Keeps `/handovers/` clean (active tasks only)
- ✅ `-C` suffix clearly indicates completion
- ✅ `/handovers/completed/` serves as implementation history
- ✅ Easy to reference past solutions
- ✅ Maintains chronological order (sequence numbers preserved)

### Active vs Completed Handovers:

**Active Handovers (`/handovers/`):**
- Not Started
- In Progress
- Blocked
- Ready for Testing

**Completed Handovers (`/handovers/completed/`):**
- Fully implemented
- All tests passing
- Committed to git
- Documented in devlog
- Archived with `-C` suffix

---

## Cross-Platform Reminder

**ALWAYS use pathlib.Path() for file operations:**

```python
# ✅ CORRECT
from pathlib import Path
config_path = Path.cwd() / 'config.yaml'

# ❌ WRONG
config_path = 'F:\\GiljoAI_MCP\\config.yaml'
```

---

## Final Checklist Before Completing Handover

**Before Starting Work:**
- [ ] Git status checked and documented
- [ ] Relevant sub-agent profiles reviewed
- [ ] Project resources referenced (/docs/sessions, /docs/devlog)
- [ ] Serena MCP tools used for code exploration
- [ ] GitHub repository checked for related issues/PRs
- [ ] Handover document complete with all sections
- [ ] Implementation plan clear and actionable
- [ ] Testing requirements specified
- [ ] Success criteria defined
- [ ] Rollback plan documented
- [ ] File naming convention followed
- [ ] Progress tracking added to handover document

**After Completing Work:**
- [ ] All implementation phases completed
- [ ] All tests passing (unit, integration, manual)
- [ ] Code committed to git with descriptive message
- [ ] Documentation updated (devlog, technical docs)
- [ ] Progress Updates section marked as "Completed"
- [ ] Handover file moved to `/handovers/completed/` with `-C` suffix
- [ ] Archive commit created: `git commit -m "docs: Archive completed handover [SEQUENCE]"`

---

## Questions?

If anything is unclear about the handover process, ask the user or check:
- `/docs/README_FIRST.md` - Project navigation
- Previous handovers in `/handovers/` - Examples and patterns

---

**Remember:** A good handover enables the next agent to succeed. Take the time to be thorough.
