# Harmony Fixes Implementation Guide

## URGENT: Configuration Fixes Required

### Step 1: Backup Current Installation
```bash
cp .env .env.backup_before_harmony
cp config.yaml config.yaml.backup_before_harmony
```

### Step 2: Update Installer Code

#### Option A: Quick Fix (Recommended)
Replace the import in your main installer:

```python
# In universal_mcp_installer.py or wherever ConfigManager is used
# Change this:
from installer.core.config import ConfigManager

# To this:
from installer.core.config_fixed import ConfigManager as ConfigManager
```

#### Option B: Full Replacement
```bash
# Backup original
mv installer/core/config.py installer/core/config_original.py

# Replace with fixed version
cp installer/core/config_fixed.py installer/core/config.py
```

### Step 3: Migrate Existing Configurations
For existing installations:

```bash
# Run migration script
python installer/scripts/migrate_config.py

# Check the migrated .env
cat .env | grep GILJO_API_PORT
# Should show: GILJO_API_PORT=7272
```

### Step 4: Test the Fix

#### Test 1: Validate Configuration
```bash
python -c "
from installer.core.config_fixed import ConfigManager
cm = ConfigManager({'mode': 'localhost', 'api_port': 7272})
result = cm.validate_config()
print('Valid:', result['valid'])
print('Issues:', result['issues'])
"
```

#### Test 2: Generate New Config
```bash
python -c "
from installer.core.config_fixed import ConfigManager
settings = {
    'mode': 'localhost',
    'pg_host': 'localhost',
    'pg_port': 5432,
    'api_port': 7272,
    'dashboard_port': 6000,
    'owner_password': '4010',
    'user_password': '4010'
}
cm = ConfigManager(settings)
cm.generate_all()
"
```

#### Test 3: Verify Application Starts
```bash
# After generating new config
cd C:/Projects/GiljoAI_MCP
python -m api.run_api

# Should see:
# Starting server on 0.0.0.0:7272
# NOT on port 8000 or 8080
```

### Step 5: Verify Critical Variables

Check that your .env has these critical variables:

```bash
# Ports (MUST be 7272, not 8000/8080)
GILJO_API_PORT=7272
GILJO_PORT=7272

# Database (both formats)
DB_HOST=localhost
DB_USER=giljo_user
DB_PASSWORD=<your_password>
DATABASE_URL=postgresql://giljo_user:<password>@localhost:5432/giljo_mcp

# Frontend URLs
VITE_API_URL=http://localhost:7272
VITE_WS_URL=ws://localhost:7272

# Feature flags
ENABLE_VISION_CHUNKING=true
ENABLE_MULTI_TENANT=true

# Agent config
MAX_AGENTS_PER_PROJECT=20
AGENT_CONTEXT_LIMIT=150000
```

### Step 6: Run Harmony Validation Tests
```bash
cd C:/Projects/GiljoAI_MCP
python -m pytest installer/tests/test_harmony_validation.py -v
```

Expected: 9-10 tests passing

## Quick Troubleshooting

### If API won't start:
1. Check `GILJO_API_PORT` is set to 7272
2. Verify `DATABASE_URL` is present and correct
3. Ensure PostgreSQL is running on port 5432

### If Frontend can't connect:
1. Check `VITE_API_URL=http://localhost:7272`
2. Verify `VITE_WS_URL=ws://localhost:7272`
3. Ensure NOT using port 8000/8080

### If Database connection fails:
1. Verify both `POSTGRES_*` and `DB_*` variables exist
2. Check `DATABASE_URL` format
3. Test with: `psql -U giljo_user -d giljo_mcp`

## Emergency Rollback

If something goes wrong:
```bash
# Restore backups
cp .env.backup_before_harmony .env
cp config.yaml.backup_before_harmony config.yaml

# Use original config generator
mv installer/core/config_original.py installer/core/config.py
```

## Files Changed

- `installer/core/config_fixed.py` - New fixed generator
- `installer/scripts/migrate_config.py` - Migration tool
- `installer/tests/test_harmony_validation.py` - Tests
- `.env` - Will be updated with correct variables

## Success Criteria

✅ Application starts on port 7272 (not 8000/8080)
✅ Frontend connects to backend
✅ Database operations work
✅ No "variable not found" errors
✅ Health check endpoint responds

## Contact

Issues? Check:
1. `installer/HARMONY_VALIDATION_REPORT.md` - Detailed findings
2. `installer/FINAL_HARMONY_REPORT.md` - Complete analysis
3. Run tests: `pytest installer/tests/test_harmony_validation.py`