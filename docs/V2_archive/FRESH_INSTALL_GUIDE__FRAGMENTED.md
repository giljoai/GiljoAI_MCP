# Fresh Install Guide - Setup State Architecture

**Last Updated:** 2025-10-07
**For:** C: Drive (Localhost Mode) Fresh Installation

---

## ✅ What's Been Fixed

All setup state architecture changes are now committed to the repository:

1. ✅ **Database Model** - `SetupState` table with version tracking
2. ✅ **State Manager** - `SetupStateManager` with hybrid file/database storage
3. ✅ **API Integration** - Setup endpoints use SetupStateManager
4. ✅ **Migrations** - Alembic migration for setup_state table
5. ✅ **SQLite Removed** - Alembic now PostgreSQL-only (no SQLite fallback)

---

## 📋 Pre-Installation Checklist

### 1. PostgreSQL Running
```bash
# Verify PostgreSQL is running
# The installer will test this automatically
```

### 2. Clean Slate (If Re-installing)
```bash
# Drop the database (if exists from previous install)
PGPASSWORD=4010 psql -U postgres -c "DROP DATABASE IF EXISTS giljo_mcp;"
```

### 3. Pull Latest Code
```bash
cd C:\Projects\GiljoAI_MCP
git pull
```

---

## 🚀 Installation Steps

### Step 1: Install Python Dependencies
```bash
cd C:\Projects\GiljoAI_MCP
pip install -r requirements.txt
```

### Step 2: Run the Installer
```bash
# Interactive mode (recommended)
python installer/cli/install.py

# OR Batch mode (if you know all settings)
python installer/cli/install.py --mode localhost --pg-password 4010 --batch
```

### Step 3: What the Installer Does Automatically

The installer will:
1. ✅ Check PostgreSQL connection
2. ✅ Create `giljo_mcp` database
3. ✅ Create database users (`giljo_owner`, `giljo_user`)
4. ✅ **Run ALL Alembic migrations** (including setup_state table)
5. ✅ Copy source code (including `src/giljo_mcp/setup/state_manager.py`)
6. ✅ Generate `config.yaml`
7. ✅ Generate `.env` with database credentials
8. ✅ Create launch scripts (`start_giljo.bat`, etc.)

### Step 4: Verify Installation
```bash
# Check that setup directory exists
dir src\giljo_mcp\setup

# Should show:
# __init__.py
# state_manager.py
```

---

## 🧪 Testing After Installation

### Test 1: Verify Migration Applied
```bash
cd C:\Projects\GiljoAI_MCP
alembic current
```

**Expected Output:**
```
e2639692ae52 (head)
```

### Test 2: Start API Server
```bash
python api/run_api.py
```

**Expected:**
- No errors about SetupStateManager
- Server binds to `127.0.0.1:7272`
- Log shows: "✅ Setup state version is current" or version mismatch warning (okay)

### Test 3: Check Setup State in Database
```bash
PGPASSWORD=4010 psql -U postgres -d giljo_mcp -c "SELECT tenant_key, completed, setup_version FROM setup_state;"
```

**Expected:**
- Either 0 rows (fresh install, setup not run yet)
- Or 1 row with data from installer

---

## 🎯 Next: Run Setup Wizard

### Step 1: Start Services
```bash
# Terminal 1: API Server
python api/run_api.py

# Terminal 2: Frontend
cd frontend
npm install  # First time only
npm run dev
```

### Step 2: Access Setup Wizard
```
Open browser: http://localhost:7274
```

**What Happens:**
- Router guard checks setup status via `GET /api/setup/status`
- If not completed, redirects to `/setup`
- Complete wizard steps
- Submit with "Save and Exit"
- **Setup state saved to database** via SetupStateManager

### Step 3: Test LAN Conversion (Optional)
After completing localhost setup:
1. Navigate back to `/setup`
2. Change mode to LAN
3. Fill in LAN configuration
4. Click "Save and Exit"
5. **API key modal should appear** ← This was the original bug!
6. Copy API key
7. Restart services
8. Dashboard shows green "LAN Mode Activated" banner

---

## 🐛 Troubleshooting

### Problem: API Server Won't Start

**Symptom:**
```
ImportError: cannot import name 'SetupStateManager'
```

**Solution:**
```bash
# 1. Verify setup directory exists
dir src\giljo_mcp\setup

# 2. If missing, pull again
git pull

# 3. Re-run installer
python installer/cli/install.py
```

---

### Problem: Alembic Shows SQLite Error

**Symptom:**
```
NotImplementedError: No support for ALTER of constraints in SQLite dialect
```

**Solution:**
```bash
# 1. Verify you pulled latest code (SQLite removal fix)
git log --oneline -1
# Should show: "fix: Remove SQLite fallback from Alembic migrations"

# 2. Check .env has DATABASE_URL
cat .env | grep DATABASE_URL

# 3. Re-run migration
alembic upgrade head
```

---

### Problem: Migration Fails with "setup_state already exists"

**Symptom:**
```
Table 'setup_state' already exists
```

**Solution:**
```bash
# The table exists but Alembic tracking is wrong
# Check current migration
alembic current

# If it shows a migration before e2639692ae52, stamp to latest
alembic stamp head

# Verify
alembic current
# Should show: e2639692ae52 (head)
```

---

### Problem: Setup Wizard Shows "Setup Already Completed"

**Symptom:**
- Can't access setup wizard
- Redirects to dashboard
- But you want to re-run setup

**Solution:**
```bash
# Option 1: Reset setup state in database
PGPASSWORD=4010 psql -U postgres -d giljo_mcp -c "DELETE FROM setup_state WHERE tenant_key='default';"

# Option 2: Use API to reset
curl -X DELETE http://localhost:7272/api/setup/reset

# Then refresh browser and access /setup
```

---

## ✅ Success Criteria

After fresh install, you should have:

- [x] PostgreSQL database `giljo_mcp` created
- [x] All migrations applied (`alembic current` shows `e2639692ae52`)
- [x] `src/giljo_mcp/setup/state_manager.py` exists
- [x] API server starts without errors
- [x] Setup wizard accessible at `/setup`
- [x] Can complete setup (localhost mode)
- [x] Setup state saved to database
- [x] Dashboard accessible after setup

---

## 📚 Additional Resources

- **Architecture Documentation:** `docs/architecture/SETUP_STATE_ARCHITECTURE.md`
- **Migration Guide:** `docs/architecture/SETUP_STATE_MIGRATION_GUIDE.md`
- **Test Checklist:** `docs/testing/QUICK_START_TESTING.md`
- **LAN Conversion Test:** `docs/testing/LAN_CONVERSION_TEST_CHECKLIST.md`

---

## 🆘 Emergency Rollback

If everything breaks and you need to start completely fresh:

```bash
# 1. Drop database
PGPASSWORD=4010 psql -U postgres -c "DROP DATABASE IF EXISTS giljo_mcp;"

# 2. Delete generated files
rm -rf data/ logs/ uploads/ temp/
rm -f config.yaml .env
rm -rf frontend/node_modules frontend/dist

# 3. Pull latest code
git pull

# 4. Re-run installer
python installer/cli/install.py
```

---

**Good luck with your fresh install! 🚀**

If you encounter any issues not covered here, the diagnostic script can help:
```bash
python diagnose_startup.py
```
