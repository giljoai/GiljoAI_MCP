# Quick Start: Setup Wizard Testing

**5-Minute Guide to Verify Setup Wizard**

---

## Prerequisites (2 minutes)

1. **Backend Running**
   ```bash
   cd F:\GiljoAI_MCP
   python api/run_api.py
   ```
   Backend should be on: `http://localhost:7272`

2. **Frontend Running**
   ```bash
   cd F:\GiljoAI_MCP\frontend
   npm run dev
   ```
   Frontend should be on: `http://localhost:7274`

3. **Database Running**
   - PostgreSQL 18 on localhost:5432
   - Database: `giljo_mcp`

---

## Quick Test: Fresh Install (5 minutes)

### 1. Reset Setup State
```bash
# Option A: Clear database
psql -U postgres -d giljo_mcp -c "DELETE FROM setup_state;"

# Option B: Remove state file (if using file storage)
rm F:\GiljoAI_MCP\setup_state.json
```

### 2. Navigate to Frontend
Open browser: `http://localhost:7274`

**Expected:** Automatic redirect to `/setup`

### 3. Complete Wizard
- **Step 1:** Database Check → Click "Next"
- **Step 2:** Attach Tools → Select tools (or skip) → Click "Next"
- **Step 3:** Serena MCP → Toggle on/off → Click "Next"
- **Step 4:** Network → Select "Localhost" → Click "Next"
- **Step 5:** Complete → Click "Save and Exit"

**Expected:** Redirect to dashboard (no modals in localhost mode)

### 4. Verify Status
```bash
curl http://localhost:7272/api/setup/status
```

**Expected:**
```json
{
  "completed": true,
  "network_mode": "localhost",
  "tools_attached": [...],
  "serena_enabled": true/false
}
```

**Result:** ✅ Fresh install works

---

## Quick Test: LAN Conversion (10 minutes)

### 1. Navigate to Setup
With setup already completed, go to: `http://localhost:7274/setup`

**Expected:** Wizard loads (re-run mode)

### 2. Navigate to Network Step
- Skip to Step 4 (Network Configuration)

### 3. Select LAN Mode
- Click "LAN" radio button
- **Expected:** LAN configuration fields appear

### 4. Fill LAN Configuration
- Server IP: `192.168.1.100` (your LAN IP)
- Hostname: `giljo.local`
- Admin Username: `admin`
- Admin Password: `testpass123`
- Check "Firewall configured"
- Click "Next" → "Save and Exit"

### 5. Verify LAN Confirmation Modal
**Expected:**
- Modal appears: "Confirm LAN Mode Configuration"
- Warning about network access
- "Cancel" and "Yes, Configure for LAN" buttons

Click: **"Yes, Configure for LAN"**

### 6. Verify API Key Modal
**Expected:**
- Modal appears: "Your API Key"
- API key displayed: `gk_xxxxxxxxxxxxxxxx`
- Copy button (clipboard icon)
- Confirmation checkbox: "I have saved this API key securely"
- "Continue" button (initially disabled)

**Actions:**
1. Click copy button → Icon changes to checkmark
2. Check confirmation checkbox → "Continue" button enables
3. Click "Continue"

### 7. Verify Restart Modal
**Expected:**
- Modal appears: "Restart Services Required"
- Success message
- Platform-specific instructions (Windows: stop_backend.bat, start_backend.bat)
- "I've Restarted - Go to Dashboard" button

**Actions:**
1. Open terminal
2. Run: `cd F:\GiljoAI_MCP`
3. Run: `stop_backend.bat`
4. Run: `start_backend.bat`
5. Wait 15 seconds
6. Click "I've Restarted - Go to Dashboard"

### 8. Verify Dashboard
**Expected:**
- Dashboard loads
- Green banner: "LAN Mode Activated" (or similar)
- No errors in console

### 9. Verify Backend Configuration
```bash
# Check backend logs - should show:
# API binding to 0.0.0.0:7272 (not 127.0.0.1)
# API key authentication enabled

# Test from another device (optional):
curl http://192.168.1.100:7272/api/setup/status -H "X-API-Key: gk_xxxxxxxx"
```

**Result:** ✅ LAN conversion works

---

## Quick Test: Router Guards (3 minutes)

### Test 1: Fresh Install Redirect
1. Reset setup state (see above)
2. Navigate to: `http://localhost:7274/`
3. **Expected:** Redirect to `/setup`

### Test 2: Completed Setup Access
1. Complete setup (any mode)
2. Navigate to: `http://localhost:7274/`
3. **Expected:** Dashboard loads (no redirect)

### Test 3: Re-run Wizard
1. With setup completed, navigate to: `http://localhost:7274/setup`
2. **Expected:** Wizard loads (can modify config)

**Result:** ✅ Router guards work

---

## Quick Test: Error Handling (5 minutes)

### Test 1: Network Error
1. Start wizard
2. Stop backend: `stop_backend.bat`
3. Try to complete wizard
4. **Expected:** Error message displayed (not crash)

### Test 2: Invalid Input
1. Start wizard, go to LAN configuration
2. Enter invalid IP: `999.999.999.999`
3. Try to proceed
4. **Expected:** Validation error (if implemented)

### Test 3: Cancel Flow
1. Complete wizard in LAN mode
2. When LAN confirmation modal appears, click "Cancel"
3. **Expected:** Return to summary screen (no save)

**Result:** ✅ Error handling works

---

## Pass/Fail Criteria

### Must Pass (Critical)
- ✅ Fresh install completes without errors
- ✅ Dashboard accessible after setup
- ✅ Router guard redirects when setup incomplete
- ✅ LAN mode shows API key modal
- ✅ LAN mode shows restart modal

### Should Pass (Important)
- ✅ API key copy button works
- ✅ Confirmation checkbox enables Continue button
- ✅ Platform-specific restart instructions shown
- ✅ Dashboard shows LAN banner (if LAN mode)

### Nice to Have (Optional)
- ✅ Wizard allows back navigation
- ✅ Configuration persists across steps
- ✅ Error messages are clear and actionable

---

## Common Issues

### Issue: Wizard not loading
**Symptoms:** Blank page, 404 error
**Solutions:**
1. Check frontend is running: `npm run dev`
2. Check URL is correct: `http://localhost:7274`
3. Check browser console for errors

### Issue: Router not redirecting
**Symptoms:** Dashboard loads when setup incomplete
**Solutions:**
1. Check backend is running
2. Verify `/api/setup/status` endpoint works
3. Clear browser cache

### Issue: API key modal not appearing
**Symptoms:** Direct redirect to dashboard in LAN mode
**Solutions:**
1. Verify "LAN" mode selected (not localhost)
2. Check network logs for `/api/setup/complete` response
3. Verify response includes `api_key` field

### Issue: Backend not in LAN mode after restart
**Symptoms:** Still binds to 127.0.0.1, no API key required
**Solutions:**
1. Check `setup_state.json` has `network_mode: "lan"`
2. Verify backend reads state on startup
3. Check backend logs for mode detection

---

## Automated Tests

### Run All Tests
```bash
cd frontend/
npm run test
```

### Run Setup Wizard Tests Only
```bash
npm run test -- tests/integration/setup-wizard-integration.spec.js
```

### Expected Results
- 12/27 tests passing (44%)
- Test infrastructure needs refinement
- Manual testing is primary validation method

---

## Files to Check

### Frontend
- `frontend/src/views/SetupWizard.vue` - Main wizard component
- `frontend/src/services/setupService.js` - API service
- `frontend/src/router/index.js` - Router guards

### Backend
- `api/endpoints/setup.py` - Setup API endpoints
- `api/setup/setup_state_manager.py` - State persistence
- `setup_state.json` - State file (created after setup)

### Tests
- `frontend/tests/integration/setup-wizard-integration.spec.js` - Automated tests
- `frontend/tests/mocks/setup.js` - Test utilities

### Documentation
- `docs/testing/TESTING_SUMMARY.md` - Quick reference
- `docs/testing/SETUP_WIZARD_TEST_REPORT.md` - Full report
- `docs/testing/SETUP_WIZARD_FRONTEND_TEST_CHECKLIST.md` - Detailed checklist

---

## Next Steps

### If Tests Pass
1. Document results
2. Get stakeholder approval
3. Deploy to production

### If Tests Fail
1. Document failure details
2. Check common issues above
3. Review full test report: `docs/testing/SETUP_WIZARD_TEST_REPORT.md`
4. Create bug tickets
5. Fix issues
6. Re-test

---

## Time Estimates

| Task | Time | Priority |
|------|------|----------|
| Quick test: Fresh install | 5 min | Critical |
| Quick test: LAN conversion | 10 min | Critical |
| Quick test: Router guards | 3 min | Important |
| Quick test: Error handling | 5 min | Important |
| Run automated tests | 2 min | Optional |
| Full manual testing | 2 hours | Recommended |

**Minimum:** 23 minutes (all quick tests)
**Recommended:** 2 hours (full manual testing)

---

## Success Checklist

- [ ] Fresh install works
- [ ] Dashboard accessible after setup
- [ ] Router guards redirect correctly
- [ ] LAN mode shows API key modal
- [ ] API key can be copied
- [ ] Restart modal shows instructions
- [ ] Backend restarts in LAN mode
- [ ] Dashboard shows LAN banner
- [ ] No console errors
- [ ] Tests documented

**When all checked:** ✅ Setup wizard is verified and ready for production

---

**Created:** 2025-10-07
**Version:** 1.0.0
**Agent:** Frontend Tester Agent
