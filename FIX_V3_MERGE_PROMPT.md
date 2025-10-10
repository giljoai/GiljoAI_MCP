# GiljoAI MCP v3.0 - Fix Architecture and Complete Merge

**Priority**: CRITICAL - Fix v3.0 architecture to enable fresh install
**Estimated Time**: 2-4 hours
**Current Branch**: master
**Target**: Working v3.0 with correct architecture

---

## 🎯 Your Mission

Fix the GiljoAI MCP v3.0 implementation by merging the CORRECT architecture from `phase1-sessions-backup` branch with the COMPLETE features already built on master. The project is 75% complete but built on wrong foundation.

---

## 📊 Current Situation

### Two Divergent Implementations Exist:

**This PC (master branch) - 75% Complete but WRONG Architecture**:
- ✅ Phase 2: MCP Integration (100% complete - templates, API, tests)
- ✅ Phase 3: Testing (100% complete - 86% pass rate)
- ✅ Phase 4: Documentation (60% complete)
- ❌ Phase 1: WRONG - Still has DeploymentMode, no auto-login
- **Problem**: Fresh install broken - routes to login instead of setup wizard

**Other PC (phase1-sessions-backup branch) - 25% Complete but CORRECT Architecture**:
- ✅ Phase 1: CORRECT - DeploymentMode removed, auto-login implemented
- ❌ Phase 2-4: Not started
- **Has**: Correct v3.0 foundation we need

---

## 🔧 Step-by-Step Fix Plan

### Step 1: Analyze Current State (10 min)

Use the `deep-researcher` agent to:

```bash
# 1. Check what we have on master
ls -la installer/templates/
ls -la api/endpoints/mcp_installer.py
ls -la docs/guides/MCP*.md

# 2. Find all DeploymentMode references (THESE MUST BE REMOVED)
grep -r "DeploymentMode" --include="*.py" --include="*.vue" --include="*.js"
grep -r "deploymentMode" --include="*.vue" --include="*.js"

# 3. Check setup wizard current state
cat frontend/src/views/SetupWizard.vue | grep -A 20 "const allSteps"
```

### Step 2: Cherry-Pick Core Architecture Fixes (30 min)

Use the `orchestrator-coordinator` agent to coordinate:

```bash
# 1. View what's in phase1-sessions-backup
git log origin/phase1-sessions-backup --oneline -10

# 2. Cherry-pick ONLY the architecture fixes (in this order)
git cherry-pick 837f488  # feat: Implement v3.0 config system (remove DeploymentMode)
git cherry-pick 6a6e381  # feat: Implement AuthManager v3 with mode-independent auth
git cherry-pick cdca989  # feat: Implement mode-independent AuthMiddleware

# 3. If conflicts occur, resolve them keeping:
# - All MCP integration features from master
# - Architecture changes from cherry-picks
```

### Step 3: Fix Setup Wizard (CRITICAL) (30 min)

Use the `frontend-tester` agent to:

**File**: `frontend/src/views/SetupWizard.vue`

**Current (WRONG)**:
```javascript
const allSteps = [
  { component: DatabaseCheckStep, title: 'Database Test' },        // WRONG - should be last
  { component: DeploymentModeStep, title: 'Deployment Mode' },     // DELETE THIS
  { component: AdminAccountStep, title: 'Admin Setup',             // WRONG - should be first
    showIf: (config) => config.deploymentMode === 'lan' || ... },  // REMOVE condition
]
```

**Fix to**:
```javascript
const allSteps = [
  { component: AdminAccountStep, title: 'Create Admin Account' },  // FIRST, no condition
  { component: AttachToolsStep, title: 'MCP Configuration' },
  { component: SerenaAttachStep, title: 'Serena Integration' },
  { component: DatabaseCheckStep, title: 'Database Test' },        // LAST
  { component: SetupCompleteStep, title: 'Complete' },
]
```

**Also**:
1. Delete `frontend/src/components/setup/DeploymentModeStep.vue`
2. Remove import of DeploymentModeStep from SetupWizard.vue
3. Remove all `deploymentMode` references from config object
4. Remove `showIf` condition from AdminAccountStep

### Step 4: Add Auto-Login Implementation (30 min)

Use the `tdd-implementor` agent to:

Check if auto-login files exist, if not, get them from phase1-sessions-backup:
```bash
# Check if auto-login exists
ls -la src/giljo_mcp/auth/auto_login.py
ls -la src/giljo_mcp/auth/localhost_user.py

# If missing, get from phase1-sessions-backup
git checkout origin/phase1-sessions-backup -- src/giljo_mcp/auth/auto_login.py
git checkout origin/phase1-sessions-backup -- src/giljo_mcp/auth/localhost_user.py
git checkout origin/phase1-sessions-backup -- tests/unit/test_auto_login_middleware.py
git checkout origin/phase1-sessions-backup -- tests/unit/test_localhost_user.py
```

### Step 5: Remove ALL Mode References (30 min)

Use the `system-architect` agent to:

```bash
# Find and remove all deployment mode references
grep -r "deployment.*mode" --include="*.py" --include="*.vue" --include="*.js" -i

# Key files to check/fix:
# - api/app.py
# - src/giljo_mcp/config_manager.py
# - install.py
# - startup.py
# - Any remaining .vue files
```

Replace mode logic with:
- Always bind to 0.0.0.0
- Authentication always enabled
- Auto-login for 127.0.0.1 and ::1
- No conditional logic based on modes

### Step 6: Test Fresh Install (30 min)

Use the `backend-integration-tester` agent to:

```bash
# 1. Clean database for fresh install test
psql -U postgres -c "DROP DATABASE IF EXISTS giljo_mcp;"

# 2. Run installer
python install.py

# 3. Verify setup wizard flow:
# - Should show Admin Account creation FIRST
# - NO deployment mode selection
# - Database test should be near the end
# - Should complete successfully

# 4. Test auto-login
# - Access from localhost (127.0.0.1) should auto-authenticate
# - No login screen should appear
```

### Step 7: Fix Remaining Tests (30 min)

Use the `backend-integration-tester` agent to:

```bash
# Run tests and fix any failures
pytest tests/unit/test_mcp_installer_api.py -xvs
pytest tests/unit/test_mcp_templates.py -xvs

# Fix the 3 known failing tests:
# - test_share_link_token_expires_in_7_days (timezone issue)
# - test_download_via_invalid_platform_raises_400
# - test_missing_template_file_raises_error
```

---

## 📋 Success Criteria

- [ ] Fresh install works (no routing to login page)
- [ ] Setup wizard shows Admin Account FIRST
- [ ] NO DeploymentMode step in wizard
- [ ] Auto-login works for localhost (127.0.0.1)
- [ ] MCP templates still work
- [ ] Tests pass (at least 86%)
- [ ] No references to deployment modes remain

---

## 🛠 Use These Specialized Agents

1. **orchestrator-coordinator**: Coordinate the overall merge strategy
2. **system-architect**: Understand architecture and component dependencies
3. **tdd-implementor**: Fix auto-login implementation and tests
4. **frontend-tester**: Fix SetupWizard.vue and test UI
5. **backend-integration-tester**: Test the fresh install and API
6. **database-expert**: If any database issues arise
7. **deep-researcher**: Find all mode references to remove

---

## 📚 Important Context Files

Read these if you need more context:
- `V3_FINAL_MERGE_STRATEGY.md` - Complete analysis of the situation
- `docs/sessions/phase1_core_architecture_consolidation.md` - What Phase 1 should look like
- `docs/devlog/PHASE2_MCP_INSTALLER_COMPLETION.md` - Phase 2 work already done
- `docs/VERIFICATION_OCT9.md` - v3.0 architecture specification

---

## ⚠️ Critical Notes

1. **DO NOT** start over - 75% of work is complete and good
2. **DO NOT** merge master into phase1-sessions-backup (wrong direction)
3. **PRESERVE** all MCP integration work (Phase 2) - it's complete and working
4. **PRESERVE** all documentation (Phase 4) - it's mostly complete
5. **ONLY FIX** the architecture foundation (Phase 1)

---

## 🎯 Expected Outcome

After 2-4 hours, you should have:
- ✅ Working fresh install (setup wizard appears)
- ✅ Correct v3.0 architecture (no deployment modes)
- ✅ Auto-login for localhost
- ✅ All MCP features working
- ✅ Ready for v3.0 release

---

## 🚀 You're Very Close!

The project is actually 75% complete. You just need to fix the foundation. Once the architecture is corrected, everything else should work. The MCP integration, templates, and most documentation are already done!

**Start with Step 1 and work through systematically. Use the specialized agents for each task.**

Good luck! 🎯