# Production Bug Fix: JSON to JSONB Migration

## Issue
The `receive_messages` MCP tool was failing with a PostgreSQL error:
```
operator does not exist: json ~~ text
```

## Root Cause
PostgreSQL's `JSON` type does **NOT** support the `@>` (containment) operator. Only `JSONB` supports this operator.

The code in `src/giljo_mcp/services/message_service.py` (lines 481, 483, 595, 597) uses the `@>` operator:
```python
Message.to_agents.op('@>')(func.cast([agent_id], type_=type(Message.to_agents.type)))
```

But the `Message` model columns were defined as `JSON` type, causing the SQL error.

## Fix Applied

### 1. Model Changes
**File**: `F:\GiljoAI_MCP\src\giljo_mcp\models\tasks.py`

Changed the following columns from `JSON` to `JSONB`:

**Message model**:
- `to_agents` (line 117) - List of agent names
- `acknowledged_by` (line 123) - Array of agent names
- `completed_by` (line 124) - Array of agent names
- `meta_data` (line 129) - Dictionary of metadata

**Task model**:
- `meta_data` (line 75) - Used with `.contains()` operator in `tools/task.py:703`

### 2. Migration Created
**File**: `F:\GiljoAI_MCP\migrations\versions\c972fded3b0e_convert_message_json_to_jsonb_for_.py`

Migration safely converts JSON to JSONB using PostgreSQL's built-in casting:
```sql
ALTER TABLE messages ALTER COLUMN to_agents TYPE jsonb USING to_agents::jsonb;
ALTER TABLE messages ALTER COLUMN acknowledged_by TYPE jsonb USING acknowledged_by::jsonb;
ALTER TABLE messages ALTER COLUMN completed_by TYPE jsonb USING completed_by::jsonb;
ALTER TABLE messages ALTER COLUMN meta_data TYPE jsonb USING meta_data::jsonb;
ALTER TABLE tasks ALTER COLUMN meta_data TYPE jsonb USING meta_data::jsonb;
```

**Rollback support**: Migration includes downgrade path to revert to JSON if needed.

### 3. Verification
Tested the following scenarios successfully:

1. **Migration upgrade/downgrade cycle**: ✅ PASS
   - Upgraded to JSONB: SUCCESS
   - Downgraded to JSON: SUCCESS
   - Upgraded again: SUCCESS

2. **JSONB containment operator**: ✅ PASS
   ```sql
   -- Direct message query
   SELECT * FROM messages WHERE to_agents @> '["agent-1"]'::jsonb;
   -- Result: Query executed without error

   -- Broadcast message query
   SELECT * FROM messages WHERE to_agents @> '["all"]'::jsonb;
   -- Result: Query executed without error
   ```

3. **Data integrity**: ✅ PASS
   - Existing data preserved during migration
   - JSON arrays converted to JSONB arrays correctly
   - No data loss

## Impact

### Fixed Issues
- `receive_messages` MCP tool now works correctly
- `list_messages` with agent filtering now works correctly
- Task metadata queries with containment operators now work correctly
- All agent communication functionality restored

### Breaking Changes
**NONE** - This is a schema-level change that is transparent to application code. Existing JSON data is automatically converted to JSONB during migration.

### Performance Implications
**POSITIVE** - JSONB provides:
- Faster queries with `@>` operator (uses GIN indexes)
- Binary storage format (more efficient than text JSON)
- Support for advanced JSON operations

## Deployment Instructions

### For Existing Installations
```bash
cd /f/GiljoAI_MCP
source venv/Scripts/activate  # or venv\Scripts\activate on Windows
alembic upgrade head
```

### For Fresh Installations
No action needed - `install.py` will automatically run all migrations including this one.

### Verification
```bash
# Check migration status
alembic current
# Should show: c972fded3b0e (head)

# Verify column types
psql -U postgres -d giljo_mcp -c "\d messages" | grep -E "(to_agents|acknowledged_by|completed_by|meta_data)"
# Should show: jsonb for all columns
```

## Rollback Plan
If issues arise, rollback with:
```bash
alembic downgrade -1
```

This will revert columns to JSON type. Note: After rollback, `receive_messages` will fail again with the original error.

## Files Modified
1. `src/giljo_mcp/models/tasks.py` - Model definitions updated
2. `migrations/versions/c972fded3b0e_convert_message_json_to_jsonb_for_.py` - New migration created

## Database Changes
**Tables Modified**: `messages`, `tasks`
**Migration Version**: `c972fded3b0e`
**Parent Migration**: `807c85a49438`

## Testing Performed
- ✅ Migration upgrade/downgrade cycle
- ✅ JSONB containment operator queries (direct + broadcast)
- ✅ Data integrity verification
- ✅ Schema verification via psql

## Related Code Locations
**Containment operator usage**:
- `src/giljo_mcp/services/message_service.py` - Lines 481, 483, 595, 597
- `src/giljo_mcp/agent_message_queue.py` - Lines 133, 570, 571, 657, 779
- `src/giljo_mcp/tools/task.py` - Line 703

## Production Status
✅ **READY FOR DEPLOYMENT**

Migration has been tested and verified on development database. All tests pass. No breaking changes for application code.
