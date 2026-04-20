# Handover 0035 Quick Verification Guide

**Post-Installation Verification Checklist**

---

## 1. PostgreSQL Extension Check (CRITICAL)

```sql
psql -U postgres -d giljo_mcp -c "SELECT * FROM pg_extension WHERE extname='pg_trgm';"
```

**Expected Output**:
```
 extname | extowner | extnamespace | extrelocatable | extversion
---------+----------+--------------+----------------+------------
 pg_trgm |    ...   |      ...     | t              | 1.6
```

**If Missing**: Full-text search will FAIL. Run manually:
```sql
CREATE EXTENSION IF NOT EXISTS pg_trgm;
```

---

## 2. SetupState Fields Check

```sql
psql -U postgres -d giljo_mcp -c "
SELECT column_name, data_type, is_nullable
FROM information_schema.columns
WHERE table_name = 'setup_state'
  AND column_name IN ('first_admin_created', 'first_admin_created_at');"
```

**Expected Output**:
```
      column_name       |          data_type           | is_nullable
------------------------+------------------------------+-------------
 first_admin_created    | boolean                      | NO
 first_admin_created_at | timestamp with time zone     | YES
```

---

## 3. Table Count Check

```sql
psql -U postgres -d giljo_mcp -c "SELECT COUNT(*) FROM pg_tables WHERE schemaname = 'public';"
```

**Expected Output**: `28`

---

## 4. Authentication Endpoint Test

**First Admin Creation** (should SUCCEED):
```bash
curl -X POST http://localhost:7272/api/auth/create-first-admin \
  -H "Content-Type: application/json" \
  -d '{
    "username": "admin",
    "password": "SecurePass123!",
    "email": "admin@example.com"
  }'
```

**Expected**: HTTP 201 Created

**Second Admin Attempt** (should FAIL):
```bash
curl -X POST http://localhost:7272/api/auth/create-first-admin \
  -H "Content-Type: application/json" \
  -d '{
    "username": "attacker",
    "password": "AttackerPass123!"
  }'
```

**Expected**: HTTP 403 Forbidden with message "Administrator account already exists"

---

## 5. SetupState Flag Verification

```sql
psql -U postgres -d giljo_mcp -c "
SELECT first_admin_created, first_admin_created_at
FROM setup_state
LIMIT 1;"
```

**Expected Output** (after first admin created):
```
 first_admin_created |      first_admin_created_at
---------------------+----------------------------------
 t                   | 2025-10-19 12:34:56.789+00
```

---

## Quick Troubleshooting

### Issue: pg_trgm extension missing
**Symptom**: Error during table creation: "type tsvector does not exist"
**Fix**:
```sql
psql -U postgres -d giljo_mcp -c "CREATE EXTENSION IF NOT EXISTS pg_trgm;"
```

### Issue: SetupState fields missing
**Symptom**: Error: "column first_admin_created does not exist"
**Fix**: Database created from old schema. Run:
```sql
ALTER TABLE setup_state ADD COLUMN first_admin_created BOOLEAN DEFAULT false NOT NULL;
ALTER TABLE setup_state ADD COLUMN first_admin_created_at TIMESTAMP WITH TIME ZONE;
```

### Issue: Authentication endpoint doesn't block second admin
**Symptom**: Can create multiple admins via /api/auth/create-first-admin
**Check**: Verify SetupState.first_admin_created is True after first admin
**Fix**: Application bug - report to developers

---

## All-in-One Verification Script

```bash
#!/bin/bash
# Save as verify_handover_0035.sh

echo "=== Handover 0035 Verification Script ==="

echo ""
echo "1. Checking pg_trgm extension..."
psql -U postgres -d giljo_mcp -c "SELECT extname, extversion FROM pg_extension WHERE extname='pg_trgm';"

echo ""
echo "2. Checking SetupState fields..."
psql -U postgres -d giljo_mcp -c "
SELECT column_name, data_type, is_nullable
FROM information_schema.columns
WHERE table_name = 'setup_state'
  AND column_name IN ('first_admin_created', 'first_admin_created_at');"

echo ""
echo "3. Counting tables..."
psql -U postgres -d giljo_mcp -c "SELECT COUNT(*) as table_count FROM pg_tables WHERE schemaname = 'public';"

echo ""
echo "4. Checking CHECK constraint..."
psql -U postgres -d giljo_mcp -c "SELECT conname FROM pg_constraint WHERE conname = 'ck_first_admin_created_at_required';"

echo ""
echo "5. Checking partial index..."
psql -U postgres -d giljo_mcp -c "SELECT indexname FROM pg_indexes WHERE indexname = 'idx_setup_fresh_install';"

echo ""
echo "=== Verification Complete ==="
```

**Run**: `chmod +x verify_handover_0035.sh && ./verify_handover_0035.sh`

---

## Success Criteria

✅ pg_trgm extension exists (version 1.6+)
✅ SetupState has first_admin_created (boolean, NOT NULL)
✅ SetupState has first_admin_created_at (timestamp, NULLABLE)
✅ 28 tables exist in public schema
✅ ck_first_admin_created_at_required constraint exists
✅ idx_setup_fresh_install index exists
✅ First admin creation succeeds (HTTP 201)
✅ Second admin creation fails (HTTP 403)
✅ SetupState.first_admin_created = true after first admin

---

**If all checks pass**: ✅ **HANDOVER 0035 VERIFICATION COMPLETE**

---
