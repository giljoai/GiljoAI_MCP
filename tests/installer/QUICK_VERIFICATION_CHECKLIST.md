# Quick Verification Checklist
## Phase 4: Handover 0035 - Unified Installer

**5-Minute Verification** - Run these checks after fresh install

---

## Critical Checks (Must Pass)

### 1. pg_trgm Extension (Bug #1) ⚠️ CRITICAL
```sql
psql -U postgres -d giljo_mcp -c "SELECT * FROM pg_extension WHERE extname='pg_trgm';"
```
**Expected:** One row with extname='pg_trgm'
**If fails:** Full-text search will NOT work!

### 2. User Count (Handover 0034)
```sql
psql -U postgres -d giljo_mcp -c "SELECT COUNT(*) FROM users;"
```
**Expected:** 0 (fresh install)
**If not 0:** Default admin may have been created (Handover 0034 violation)

### 3. Table Count (All 28 Models)
```sql
psql -U postgres -d giljo_mcp -c "SELECT COUNT(*) FROM pg_tables WHERE schemaname='public';"
```
**Expected:** 28
**If not 28:** Database creation incomplete

### 4. SetupState Security Fields (Handover 0035)
```sql
psql -U postgres -d giljo_mcp -c "\d setup_state" | grep first_admin
```
**Expected:** Two lines (first_admin_created, first_admin_created_at)
**If missing:** Handover 0035 security enhancement not applied

### 5. Configuration Files
```bash
ls config.yaml .env
```
**Expected:** Both files exist
**If missing:** Configuration generation failed

---

## Quick Test Procedure

### Step 1: Fresh Install
```bash
python install.py
# Answer prompts
# Wait for completion
```

### Step 2: Run Verification Script
```bash
bash tests/installer/verify_install.sh
```
**Expected:** All tests PASS

### Step 3: Start Services
```bash
python startup.py
```

### Step 4: Test First Admin Creation
1. Open http://localhost:7274
2. Should redirect to /welcome
3. Create admin account: `admin` / `SecurePass123!`
4. Should succeed with 201 Created

### Step 5: Test Endpoint Lockdown
```bash
curl -X POST http://localhost:7272/api/auth/create-first-admin \
  -H "Content-Type: application/json" \
  -d '{"username":"hacker","password":"HackPass123!","email":"hack@test.com"}'
```
**Expected:** 403 Forbidden ("Administrator account already exists")

---

## Platform-Specific Checks

### Windows
- [ ] venv/Scripts/python.exe exists
- [ ] npm commands work (from frontend/)
- [ ] Desktop shortcuts created (if requested)

### Linux
- [ ] venv/bin/python exists
- [ ] npm commands work
- [ ] UFW firewall warning shown

### macOS
- [ ] venv/bin/python exists
- [ ] Homebrew PostgreSQL detected
- [ ] npm commands work

---

## Red Flags (Fail Immediately)

🚨 **pg_trgm extension NOT found**
→ Full-text search will FAIL
→ MCPContextIndex searches will FAIL

🚨 **User count > 0 on fresh install**
→ Default admin created (Handover 0034 violation)
→ Security vulnerability

🚨 **Table count != 28**
→ Database incomplete
→ API will crash on startup

🚨 **SetupState missing security fields**
→ First admin creation won't work
→ Endpoint lockdown broken

🚨 **.env has "REPLACE_ME" passwords**
→ Database connection will FAIL
→ Password synchronization bug

---

## Success Criteria (All Must Pass)

✅ pg_trgm extension installed
✅ 0 users in database (fresh install)
✅ 28 tables created
✅ SetupState has first_admin_created fields
✅ config.yaml exists with bind: 0.0.0.0
✅ .env exists with real database passwords
✅ venv created with correct structure
✅ First admin creation works
✅ Second admin creation fails with 403
✅ Services start without errors

---

## Troubleshooting

### pg_trgm extension not found
```sql
-- Check if extension available
SELECT * FROM pg_available_extensions WHERE name='pg_trgm';

-- If available, create manually
CREATE EXTENSION pg_trgm;
```

### User count > 0 on fresh install
```sql
-- Check users
SELECT username, created_at FROM users;

-- If default admin exists, this is a bug
-- Report to Backend Integration Tester Agent
```

### Database connection fails
```bash
# Check .env has real passwords
grep GILJO_OWNER_PASSWORD .env

# Should be 20-character alphanumeric (NOT "REPLACE_ME")
```

---

## Automated Verification

```bash
# Run full verification script
bash tests/installer/verify_install.sh

# Run Phase 4 test suite
pytest tests/installer/integration/test_phase_4_comprehensive.py -v

# Check specific bug fix
pytest tests/installer/integration/test_phase_4_comprehensive.py::TestBug1PgTrgmExtension -v
```

---

## Contact

**Issues or Questions?**
- See: `F:\GiljoAI_MCP\tests\installer\PHASE_4_TEST_REPORT.md`
- See: `F:\GiljoAI_MCP\tests\installer\PHASE_4_DELIVERABLE_SUMMARY.md`
- See: `F:\GiljoAI_MCP\docs\INSTALLATION_FLOW_PROCESS.md`

**Backend Integration Tester Agent**
**Phase 4 - Handover 0035**
