# E2E Test Fixes Required for Closeout Workflow (0249c)

**Created**: November 26, 2025
**Priority**: HIGH - Blocking test execution
**Component Files Affected**: 3 files
**Estimated Fix Time**: 45-60 minutes

---

## Issue #1: Missing data-testid Attributes on Login Form

### Location
File: `/f/GiljoAI_MCP/frontend/src/views/Login.vue`

### Current HTML (From Page Snapshot)
```html
<v-text-field
  v-model="username"
  label="Username"
  prepend-inner-icon="mdi-account"
  ...
/>

<v-text-field
  v-model="password"
  label="Password"
  prepend-inner-icon="mdi-lock"
  ...
/>

<v-btn
  type="submit"
  color="primary"
  ...
>
  Sign In
</v-btn>
```

### Test Expectation (Lines 15-17 of closeout-workflow.spec.ts)
```typescript
await page.fill('[data-testid="email-input"]', 'test@example.com')
await page.fill('[data-testid="password-input"]', 'testpassword')
await page.click('[data-testid="login-button"]')
```

### Problems
1. **No data-testid attributes** - Form inputs don't have test IDs
2. **Field name mismatch** - Test expects "email-input" but form uses "username"
3. **Button has no test ID** - Sign In button lacks data-testid

### Solution

**Option A: Add data-testid attributes and fix field name** (RECOMMENDED)

Update Login.vue lines 56-98:

```vue
<!-- Change username field -->
<v-text-field
  v-model="username"
  label="Username"
  prepend-inner-icon="mdi-account"
  variant="outlined"
  :rules="[rules.required]"
  :disabled="loading"
  autofocus
  autocomplete="username"
  @keyup.enter="handleLogin"
  @input="error = ''"
  data-testid="email-input"  <!-- ADD THIS LINE -->
/>

<!-- Change password field -->
<v-text-field
  v-model="password"
  label="Password"
  prepend-inner-icon="mdi-lock"
  :append-inner-icon="showPassword ? 'mdi-eye' : 'mdi-eye-off'"
  :type="showPassword ? 'text' : 'password'"
  variant="outlined"
  :rules="[rules.required]"
  :disabled="loading"
  autocomplete="current-password"
  class="mt-4"
  @click:append-inner="showPassword = !showPassword"
  @keyup.enter="handleLogin"
  @input="error = ''"
  data-testid="password-input"  <!-- ADD THIS LINE -->
/>

<!-- Change sign in button -->
<v-btn
  type="submit"
  color="primary"
  size="large"
  block
  :loading="loading"
  :disabled="!username || !password || loading"
  class="mt-4"
  data-testid="login-button"  <!-- ADD THIS LINE -->
>
  <v-icon start v-if="!loading">mdi-login</v-icon>
  {{ loading ? 'Logging in...' : 'Sign In' }}
</v-btn>
```

**Changes Required**:
- Line ~56: Add `data-testid="email-input"` to username v-text-field
- Line ~68: Add `data-testid="password-input"` to password v-text-field
- Line ~87: Add `data-testid="login-button"` to sign in v-btn

---

## Issue #2: Missing data-testid on Project Components

### Test References (closeout-workflow.spec.ts Lines 44-45)
```typescript
const projectCards = page.locator('[data-testid="project-card"]')
await expect(projectCards.first()).toBeVisible()
await projectCards.first().click()
```

### Component Location
File: Likely in `/f/GiljoAI_MCP/frontend/src/components/ProjectCard.vue` or similar

### Required Fix
Add `data-testid="project-card"` to the project card component element

### Search Command
```bash
find /f/GiljoAI_MCP/frontend/src/components -name "*Project*.vue" -type f
```

### Solution

Add to the root element of the ProjectCard component:
```vue
<v-card
  data-testid="project-card"
  @click="selectProject"
  class="project-card"
>
  <!-- Card content -->
</v-card>
```

---

## Issue #3: Missing data-testid on Closeout Modal Components

### Test References (closeout-workflow.spec.ts Lines 52-71)
```typescript
// Line 52: Closeout modal
const closeoutButton = page.locator('[data-testid="closeout-button"]')
await closeoutButton.click()

// Line 56: Modal
const modal = page.locator('.closeout-modal')
await expect(modal).toBeVisible()

// Line 60: Copy button
const copyBtn = page.locator('button:has-text("Copy Closeout Prompt")')
await copyBtn.click()

// Line 64: Confirm checkbox
const confirmBox = page.locator('label:has-text("I have executed the closeout commands")')
await confirmBox.click()

// Line 68: Complete button
await page.click('button:has-text("Complete Project")')
```

### Components Affected

#### Component 1: JobsTab.vue or similar (Closeout Button)
```vue
<v-btn
  data-testid="closeout-button"
  @click="openCloseoutModal"
  color="warning"
>
  Closeout Project
</v-btn>
```

#### Component 2: CloseoutModal.vue or similar (Modal Container)
```vue
<v-dialog v-model="show" width="600">
  <v-card class="closeout-modal" data-testid="closeout-modal">
    <!-- Modal content -->
  </v-card>
</v-dialog>
```

#### Component 3: CloseoutModal.vue (Copy Button)
- Currently found by text: `button:has-text("Copy Closeout Prompt")`
- Recommendation: Add `data-testid="copy-closeout-button"` for reliability

#### Component 4: CloseoutModal.vue (Confirm Checkbox)
- Currently found by text: `label:has-text("I have executed the closeout commands")`
- Recommendation: Add `data-testid="confirm-closeout-checkbox"`

#### Component 5: CloseoutModal.vue (Submit Button)
- Currently found by text: `button:has-text("Complete Project")`
- Recommendation: Add `data-testid="complete-project-button"`

### Solution: Full CloseoutModal Component Structure

```vue
<template>
  <v-dialog v-model="show" width="600">
    <v-card class="closeout-modal" data-testid="closeout-modal">
      <v-card-title>Project Closeout</v-card-title>

      <v-card-text>
        <!-- Checklist Display -->
        <div class="checklist">
          <div v-for="item in checklist" :key="item" class="checklist-item">
            {{ item }}
          </div>
        </div>

        <!-- Closeout Prompt Display -->
        <div class="closeout-prompt">
          <v-code-block
            :code="closeoutPrompt"
            language="text"
            class="mt-4"
          />
        </div>

        <!-- Copy Button -->
        <v-btn
          data-testid="copy-closeout-button"
          @click="copyPrompt"
          class="mt-4"
        >
          Copy Closeout Prompt
        </v-btn>

        <!-- Confirm Checkbox -->
        <v-checkbox
          v-model="confirmed"
          data-testid="confirm-closeout-checkbox"
          label="I have executed the closeout commands"
          class="mt-4"
        />
      </v-card-text>

      <v-card-actions>
        <v-btn @click="show = false">Cancel</v-btn>
        <v-btn
          data-testid="complete-project-button"
          @click="submitCompletion"
          color="success"
          :disabled="!confirmed"
        >
          Complete Project
        </v-btn>
      </v-card-actions>
    </v-card>
  </v-dialog>
</template>
```

---

## Implementation Checklist

### Phase 1: Update Login Component
- [ ] Open `/f/GiljoAI_MCP/frontend/src/views/Login.vue`
- [ ] Add `data-testid="email-input"` to username field (line ~56)
- [ ] Add `data-testid="password-input"` to password field (line ~68)
- [ ] Add `data-testid="login-button"` to sign in button (line ~87)
- [ ] Run basic component test to verify selectors work

### Phase 2: Find and Update ProjectCard Component
- [ ] Search for ProjectCard component in `/f/GiljoAI_MCP/frontend/src/components/`
- [ ] Add `data-testid="project-card"` to root element
- [ ] Verify component still renders correctly

### Phase 3: Find and Update JobsTab Component
- [ ] Search for JobsTab component in `/f/GiljoAI_MCP/frontend/src/components/`
- [ ] Add `data-testid="closeout-button"` to closeout trigger button
- [ ] Verify button visibility and click behavior

### Phase 4: Find and Update CloseoutModal Component
- [ ] Search for CloseoutModal component in `/f/GiljoAI_MCP/frontend/src/components/`
- [ ] Add `data-testid="closeout-modal"` to modal card
- [ ] Add `data-testid="copy-closeout-button"` to copy button
- [ ] Add `data-testid="confirm-closeout-checkbox"` to confirmation checkbox
- [ ] Add `data-testid="complete-project-button"` to submit button

### Phase 5: Backend Services Setup (Prerequisite)
- [ ] Start PostgreSQL database
- [ ] Start API backend server (port 7272)
- [ ] Verify API is responding: `curl http://localhost:7272/health`
- [ ] Seed test database with test user: `test@example.com` / `testpassword`
- [ ] Seed test database with projects for test user

### Phase 6: Test Execution
- [ ] Navigate to `/f/GiljoAI_MCP/frontend`
- [ ] Run: `npm run test:e2e -- tests/e2e/closeout-workflow.spec.ts --project=chromium`
- [ ] Verify test passes
- [ ] Run full suite: `npm run test:e2e -- tests/e2e/closeout-workflow.spec.ts`
- [ ] Generate report: `npm run test:e2e:report`

---

## Database Fixtures Required

### Test User

```sql
-- Create test user if not exists
INSERT INTO users (username, email, password_hash, tenant_key, status, created_at)
VALUES (
  'test',
  'test@example.com',
  'bcrypt_hash_of_testpassword',  -- Use bcrypt to hash
  'tenant-test-001',
  'active',
  NOW()
)
ON CONFLICT (email) DO NOTHING;
```

### Test Project

```sql
-- Create test project for test user
INSERT INTO projects (id, tenant_key, name, description, status, created_by, created_at)
VALUES (
  'project-test-001',
  'tenant-test-001',
  'Mock Project',
  'Test project for E2E testing',
  'active',
  (SELECT id FROM users WHERE email = 'test@example.com' LIMIT 1),
  NOW()
)
ON CONFLICT (id) DO NOTHING;
```

### Test Agents

The test expects agents in the Jobs tab. Create 3 test agents with completed status:

```sql
-- Create test agents for test project
INSERT INTO mcp_agents (id, project_id, tenant_key, name, status, role, created_at)
VALUES
  ('agent-test-001', 'project-test-001', 'tenant-test-001', 'Agent 1', 'completed', 'orchestrator', NOW()),
  ('agent-test-002', 'project-test-001', 'tenant-test-001', 'Agent 2', 'completed', 'orchestrator', NOW()),
  ('agent-test-003', 'project-test-001', 'tenant-test-001', 'Agent 3', 'completed', 'orchestrator', NOW())
ON CONFLICT (id) DO NOTHING;
```

---

## Summary of Changes

| File | Changes | Severity |
|------|---------|----------|
| `/f/GiljoAI_MCP/frontend/src/views/Login.vue` | Add 3 data-testid attributes | HIGH |
| ProjectCard Component | Add 1 data-testid attribute | HIGH |
| JobsTab Component | Add 1 data-testid attribute | HIGH |
| CloseoutModal Component | Add 4 data-testid attributes | HIGH |
| Database (fixtures) | Create test user, project, agents | CRITICAL |

---

## Testing After Fixes

### Commands to Run Tests

```bash
# Navigate to frontend
cd /f/GiljoAI_MCP/frontend

# Run test with Chromium only (fastest)
npm run test:e2e -- tests/e2e/closeout-workflow.spec.ts --project=chromium

# Run test in headed mode (see browser)
npm run test:e2e:headed -- tests/e2e/closeout-workflow.spec.ts

# Run with full debug output
npm run test:e2e -- tests/e2e/closeout-workflow.spec.ts --verbose

# View test report
npm run test:e2e:report
```

### Expected Test Output (When Passing)

```
Running 1 test using 1 worker

✓ tests\e2e\closeout-workflow.spec.ts:23:7 › Project Closeout Workflow › User can complete project closeout from Jobs tab

1 passed
  tests\e2e\closeout-workflow.spec.ts:23:7 › Project Closeout Workflow › User can complete project closeout from Jobs tab
```

---

## Verification Steps

After implementing all fixes:

1. **Component Renders**: Verify no console errors when Login component mounts
2. **Selectors Found**: Confirm all data-testid attributes are accessible via DevTools
3. **Test Passes**: Run test suite and verify green check mark
4. **All Browsers**: Run test on all three browsers (Chromium, Firefox, WebKit)
5. **Report Generated**: Verify HTML report generates without errors

---

## Related Files

- Test file: `/f/GiljoAI_MCP/frontend/tests/e2e/closeout-workflow.spec.ts`
- Config file: `/f/GiljoAI_MCP/frontend/playwright.config.ts` (newly created)
- Analysis report: `/f/GiljoAI_MCP/E2E_TEST_ANALYSIS_REPORT.md`
- Backend config: `/f/GiljoAI_MCP/config.yaml`

---

## Notes for Handover 0249c Completion

This document provides specific, actionable fixes to enable the E2E test to pass. The test infrastructure is production-ready and requires only:

1. **Component updates**: Add data-testid attributes (5 components, ~15 lines of code)
2. **Database fixtures**: Create test data (3 SQL INSERT statements)
3. **Service startup**: Run backend and database (configuration already in place)

Once these fixes are implemented, the closeout workflow E2E test will validate the complete user journey from login through project completion.

---

**Status**: Ready for implementation
**Created**: November 26, 2025
**Assignee**: Frontend Developer
**Timeline**: 1-2 hours to complete and verify
