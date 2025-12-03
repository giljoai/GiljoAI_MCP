# E2E Test Setup Guide
## Handover 0243f: Test Data Preparation & Execution

---

## Prerequisites

### System Requirements
- Node.js >= 20.19.0
- npm >= 8.0.0
- Python 3.11+ (for backend)
- PostgreSQL 18+ (for database)
- Chrome/Chromium (for Playwright)

### Backend Running
```bash
# From GiljoAI_MCP root directory
python startup.py
# Verify: http://localhost:7272 is accessible
# API should be at: http://localhost:7272/api
```

### Frontend Installation
```bash
cd frontend
npm install
npx playwright install chromium firefox webkit
```

---

## Test Data Setup

### Option 1: Manual Setup via UI

```bash
# 1. Start frontend dev server
npm run dev
# Navigates to: http://localhost:7274

# 2. First-time setup wizard
#    - Create admin user with email/password
#    - Confirm user creation

# 3. Login with admin credentials
#    - Email: admin@example.com (or your choice)
#    - Password: Your secure password

# 4. Create test project
#    - Name: "E2E Test Project"
#    - Description: "Automated testing project"
#    - Click Create

# 5. Test data is now ready for E2E tests
```

### Option 2: API Setup (Faster)

#### 1. Create Admin User
```bash
curl -X POST http://localhost:7272/api/auth/register \
  -H "Content-Type: application/json" \
  -d '{
    "email": "test@example.com",
    "password": "testpassword",
    "name": "Test User"
  }'

# Response:
# {
#   "access_token": "eyJhbGciOiJIUzI1NiIs...",
#   "token_type": "bearer",
#   "user_id": "uuid",
#   "tenant_key": "tenant-uuid"
# }
```

#### 2. Create Test Project
```bash
# Save the access_token from previous response

curl -X POST http://localhost:7272/api/products/projects \
  -H "Content-Type: application/json" \
  -H "Authorization: Bearer <YOUR_TOKEN_HERE>" \
  -d '{
    "name": "E2E Test Project",
    "description": "Automated E2E testing"
  }'

# Response:
# {
#   "id": "project-uuid",
#   "name": "E2E Test Project",
#   "status": "created"
# }
```

#### 3. Create Additional Test Users (for Multi-Tenant Tests)
```bash
# Create User A
curl -X POST http://localhost:7272/api/auth/register \
  -H "Content-Type: application/json" \
  -d '{
    "email": "user-a@example.com",
    "password": "password",
    "name": "User A"
  }'

# Create User B
curl -X POST http://localhost:7272/api/auth/register \
  -H "Content-Type: application/json" \
  -d '{
    "email": "user-b@example.com",
    "password": "password",
    "name": "User B"
  }'

# Create User C
curl -X POST http://localhost:7272/api/auth/register \
  -H "Content-Type: application/json" \
  -d '{
    "email": "user-c@example.com",
    "password": "password",
    "name": "User C"
  }'
```

---

## Test User Accounts

### Primary Test User
```
Email: test@example.com
Password: testpassword
Purpose: Main E2E tests
```

### Multi-Tenant Test Users
```
User A:
  Email: user-a@example.com
  Password: password
  Purpose: Multi-tenant isolation tests

User B:
  Email: user-b@example.com
  Password: password
  Purpose: Multi-tenant isolation tests

User C:
  Email: user-c@example.com
  Password: password
  Purpose: Concurrent session tests
```

---

## Test Project Setup

### Primary Test Project
```
Name: E2E Test Project
Description: Automated E2E testing
Status: Created and ready
```

### Additional Projects (Optional)

For more comprehensive testing:

```bash
# Project for User A
curl -X POST http://localhost:7272/api/products/projects \
  -H "Authorization: Bearer <USER_A_TOKEN>" \
  -d '{"name": "User A Project", "description": "User A only"}'

# Project for User B
curl -X POST http://localhost:7272/api/products/projects \
  -H "Authorization: Bearer <USER_B_TOKEN>" \
  -d '{"name": "User B Project", "description": "User B only"}'
```

---

## Running E2E Tests

### Quick Start

```bash
# 1. Ensure backend is running
python startup.py &

# 2. Navigate to frontend directory
cd frontend

# 3. Run E2E tests (headless)
npm run test:e2e

# 4. View results
npm run test:e2e:report
```

### Running Specific Tests

```bash
# Launch Tab tests only
npx playwright test tests/e2e/launch-tab-workflow.spec.ts

# Implement Tab tests only
npx playwright test tests/e2e/implement-tab-workflow.spec.ts

# Multi-tenant tests only
npx playwright test tests/e2e/multi-tenant-isolation.spec.ts

# Memory leak tests only
npx playwright test tests/e2e/memory-leak-detection.spec.ts
```

### Headed Mode (See Browser)

```bash
npm run test:e2e:headed

# Or with specific browser:
npx playwright test --headed --project=chromium
npx playwright test --headed --project=firefox
npx playwright test --headed --project=webkit
```

### Debug Mode (Interactive)

```bash
npm run test:e2e:debug

# Or specific test:
npx playwright test tests/e2e/launch-tab-workflow.spec.ts --debug
```

---

## Troubleshooting

### Test Fails: "Could not find a login button"

**Cause**: Selectors in tests don't match actual DOM
**Fix**:
1. Check if data-testid attributes exist in components
2. Update selector in test file
3. Or use alternative selectors (class, text content)

**Example**:
```typescript
// Instead of:
await page.click('[data-testid="login-button"]')

// Use:
await page.click('button:has-text("Login")')
// Or:
await page.click('.login-btn')
```

### Test Fails: "Timeout waiting for URL"

**Cause**: Backend not responding or navigation slow
**Fix**:
1. Verify backend is running: `http://localhost:7272`
2. Check network in DevTools
3. Increase timeout in test:
```typescript
await page.waitForURL('**/projects', { timeout: 20000 })
```

### Test Fails: "No projects found"

**Cause**: Test data not created
**Fix**:
1. Create test project via API (see Setup section)
2. Or modify test to create project first:
```typescript
await page.click('[data-testid="create-project"]')
await page.fill('[data-testid="project-name"]', 'Test Project')
await page.click('[data-testid="save-project"]')
```

### Test Fails: "WebSocket connection refused"

**Cause**: Backend WebSocket not running
**Fix**:
1. Verify backend startup output includes WebSocket server
2. Check backend logs for connection errors
3. Restart backend with proper config

### Tests Pass Locally but Fail in CI

**Cause**: Timing differences, missing environment setup
**Fix**:
1. Increase wait times for slower CI environment
2. Add retry logic:
```typescript
await expect(element).toBeVisible({ timeout: 5000 })
```
3. Use stable selectors (data-testid preferred)

---

## Test Data Validation

### Verify Test Users Created

```bash
# Check test user exists
curl -X GET http://localhost:7272/api/auth/me \
  -H "Authorization: Bearer <TOKEN>"

# Should return user info with tenant_key
```

### Verify Test Projects Created

```bash
# List all projects for user
curl -X GET http://localhost:7272/api/products/projects \
  -H "Authorization: Bearer <TOKEN>"

# Should return array of projects
```

### Database Verification (Optional)

```bash
# Connect to PostgreSQL
PGPASSWORD=$DB_PASSWORD psql -U postgres -d giljo_mcp

# Check users table
SELECT id, email, tenant_key FROM users LIMIT 5;

# Check projects table
SELECT id, name, created_by FROM projects LIMIT 5;

# Exit
\q
```

---

## GitHub Actions CI Setup (Optional)

### .github/workflows/e2e-tests.yml

```yaml
name: E2E Tests

on:
  push:
    branches: [ main, develop ]
  pull_request:
    branches: [ main, develop ]

jobs:
  test:
    runs-on: ubuntu-latest

    services:
      postgres:
        image: postgres:18
        env:
          POSTGRES_PASSWORD: 4010
          POSTGRES_DB: giljo_mcp
        options: >-
          --health-cmd pg_isready
          --health-interval 10s
          --health-timeout 5s
          --health-retries 5

    steps:
      - uses: actions/checkout@v3

      - name: Setup Node.js
        uses: actions/setup-node@v3
        with:
          node-version: '20'

      - name: Install dependencies
        run: npm install
        working-directory: frontend

      - name: Install Playwright
        run: npx playwright install --with-deps
        working-directory: frontend

      - name: Start backend
        run: |
          pip install -e .
          python startup.py &
          sleep 5
        working-directory: .

      - name: Create test data
        run: |
          curl -X POST http://localhost:7272/api/auth/register \
            -H "Content-Type: application/json" \
            -d '{"email":"test@example.com","password":"testpassword"}'

      - name: Run E2E tests
        run: npm run test:e2e
        working-directory: frontend
        env:
          PLAYWRIGHT_TEST_BASE_URL: http://localhost:7274

      - name: Upload test results
        if: always()
        uses: actions/upload-artifact@v3
        with:
          name: playwright-report
          path: frontend/playwright-report
```

---

## Performance Testing Setup

### Lighthouse in CI

```bash
# 1. Build production bundle
npm run build

# 2. Start preview server
npm run preview &

# 3. Run Lighthouse
npx lighthouse http://localhost:7274 \
  --only-categories=performance \
  --output=json \
  --output-path=./lighthouse.json

# 4. Check results
cat lighthouse.json | jq '.categories.performance.score'
```

### Memory Profiling (Manual)

```bash
# 1. Start preview server
npm run preview

# 2. Open Chrome
# chrome://inspect

# 3. Open DevTools on http://localhost:7274

# 4. Go to Memory tab

# 5. Take heap snapshot before navigation
# 6. Navigate to LaunchTab
# 7. Take heap snapshot after navigation
# 8. Compare snapshots for memory increase
```

---

## Test Results Interpretation

### Passing Test Output

```
Running 28 tests using 3 workers

✓ Launch Tab Workflow (6 tests)
  ✓ User stages project and generates mission
  ✓ Verify panel responsiveness on resize
  ✓ Verify visual consistency with Nicepage design
  ✓ Verify accessibility of Launch Tab
  ✓ Verify performance metrics

✓ Implement Tab Workflow (8 tests)
  ✓ User manages agents and sends messages
  ✓ Verify health status indicators
  ✓ Verify action buttons conditional display
  ✓ Verify WebSocket real-time updates
  ✓ Verify table responsiveness and virtualization
  ✓ Verify message input accessibility
  ✓ Verify agent table sorting and filtering
  ✓ Verify performance under typical agent load

✓ Multi-Tenant Isolation (6 tests)
  ✓ User A cannot see User B projects
  ✓ WebSocket events isolated by tenant
  ✓ API endpoints enforce tenant isolation
  ✓ Cross-tenant request attempt returns unauthorized
  ✓ Tenant context preserved across navigation
  ✓ Logout clears tenant context
  ✓ Concurrent tenant sessions do not interfere

✓ Memory Leak Detection (8 tests)
  ✓ No memory leaks on repeated tab navigation
  ✓ WebSocket listeners properly cleaned up
  ✓ Event handlers properly removed on unmount
  ✓ Interval timers cleared on unmount
  ✓ No message listener accumulation
  ✓ DOM references properly garbage collected
  ✓ Console errors do not accumulate

28 passed (5m 30s)
```

### Failed Test Output

```
FAIL [chromium] › tests/e2e/launch-tab-workflow.spec.ts:...
Error: expect(received).toBeTruthy()

Received: null

Call log:
  - navigating to http://localhost:7274/login
  - waiting for selector [data-testid="email-input"]
  - selector [data-testid="email-input"] did not resolve

Screenshot: path/to/screenshot.png
Video: path/to/video.webm
```

**Interpretation**:
- Test couldn't find login form
- Selector [data-testid="email-input"] doesn't exist
- Check component markup for correct data-testid

---

## Next Steps After Tests Pass

1. **Commit test files**
   ```bash
   git add tests/e2e/ playwright.config.ts
   git commit -m "feat: Add E2E test suite (Handover 0243f)"
   ```

2. **Run in CI/CD**
   - Set up GitHub Actions workflow
   - Run tests on every PR
   - Block merge if tests fail

3. **Performance Audit**
   ```bash
   npm run build
   npm run analyze
   ```

4. **Memory Profiling**
   - Use Chrome DevTools
   - Verify no leaks detected

5. **Production Deployment**
   - Pass all E2E tests
   - Pass Lighthouse audit
   - No memory leaks
   - Proceed to production

---

## Support & Resources

- **Playwright Docs**: https://playwright.dev/
- **Playwright Locators**: https://playwright.dev/docs/locators
- **Test Report View**: `npm run test:e2e:report`
- **Debug Mode**: `npm run test:e2e:debug`

---

**Last Updated**: 2025-11-23
**Status**: Ready for Production Testing
