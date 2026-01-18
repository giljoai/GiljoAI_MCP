# JSONB Message Repair Script

## Overview

This script repairs a bug where broadcast messages stored incorrect `message_id` values in the `AgentExecution.messages` JSONB array.

## The Problem

**Symptom**: Message acknowledgments fail, causing message counters to stay inflated even after agents read messages.

**Root Cause**: When broadcasting to multiple agents, the old code reused the same `message_id` for all recipients instead of assigning each recipient their unique `message_id` from the Message table.

**Impact**:
- Frontend displays messages from JSONB (`agent_executions.messages`)
- Acknowledgment updates the Message table by `message_id`
- Wrong `message_id` → acknowledgment updates the wrong Message row
- Result: Message appears "unread" in UI even though agent acknowledged it

## The Solution

This script rebuilds all JSONB message arrays from the Message table (source of truth):

1. **Clears** all existing `agent_executions.messages` arrays
2. **Rebuilds** them by querying the Message table
3. **Preserves** correct `message_id` → agent relationships
4. **Updates** status based on Message.status (pending → "waiting", acknowledged → "read")

## Prerequisites

- Python 3.11+ with virtual environment activated
- PostgreSQL database running
- Valid `config.yaml` with database credentials

## Usage

**Important**: Always run with the virtual environment Python:

```bash
# Windows
./venv/Scripts/python.exe scripts/repair_jsonb_messages.py

# Linux/macOS
./venv/bin/python scripts/repair_jsonb_messages.py
```

### Dry Run (Recommended First)

Preview changes without modifying the database:

```bash
# Windows
./venv/Scripts/python.exe scripts/repair_jsonb_messages.py --dry-run

# Linux/macOS
./venv/bin/python scripts/repair_jsonb_messages.py --dry-run
```

With verbose output to see every message processed:

```bash
# Windows
./venv/Scripts/python.exe scripts/repair_jsonb_messages.py --dry-run --verbose

# Linux/macOS
./venv/bin/python scripts/repair_jsonb_messages.py --dry-run --verbose
```

### Live Repair

Repair all tenants:

```bash
# Windows
./venv/Scripts/python.exe scripts/repair_jsonb_messages.py

# Linux/macOS
./venv/bin/python scripts/repair_jsonb_messages.py
```

Repair specific tenant only:

```bash
# Windows
./venv/Scripts/python.exe scripts/repair_jsonb_messages.py --tenant-key tk_abc123...

# Linux/macOS
./venv/bin/python scripts/repair_jsonb_messages.py --tenant-key tk_abc123...
```

### Command-Line Options

| Option | Description |
|--------|-------------|
| `--dry-run` | Preview changes without modifying database |
| `--tenant-key TENANT_KEY` | Repair only specific tenant (default: all) |
| `--verbose` | Show detailed progress for each message |

## Safety Features

✅ **Atomic Transaction**: All changes commit together or roll back on error
✅ **Dry-Run Mode**: Preview changes before committing
✅ **Idempotent**: Safe to run multiple times
✅ **Read-Only Source**: Message table is never modified (source of truth)
✅ **Confirmation Prompt**: Requires explicit confirmation in live mode

## What It Does

### Step 1: Clear Existing JSONB Arrays

Clears `agent_executions.messages` for all agents (filtered by tenant if specified).

**Before:**
```json
{
  "messages": [
    {"id": "wrong-id-1", "status": "waiting", ...},
    {"id": "wrong-id-2", "status": "waiting", ...}
  ]
}
```

**After Step 1:**
```json
{
  "messages": []
}
```

### Step 2: Rebuild from Message Table

Queries Message table and rebuilds JSONB arrays with correct structure:

**For Senders** (outbound messages):
```json
{
  "id": "correct-message-id",
  "from": "orchestrator",
  "direction": "outbound",
  "status": "sent",
  "text": "Message content...",
  "priority": "normal",
  "timestamp": "2026-01-05T10:30:00Z",
  "to_agents": ["agent-uuid-1", "agent-uuid-2"]
}
```

**For Recipients** (inbound messages):
```json
{
  "id": "correct-message-id",
  "from": "orchestrator",
  "direction": "inbound",
  "status": "waiting",  # or "read" if acknowledged
  "text": "Message content...",
  "priority": "normal",
  "timestamp": "2026-01-05T10:30:00Z"
}
```

### Step 3: Commit Changes

In live mode, commits the transaction. In dry-run mode, rolls back.

## Example Output

```
============================================================
JSONB MESSAGE REPAIR SCRIPT
============================================================
Mode:        DRY RUN (no changes)
Tenant:      ALL TENANTS
Verbose:     False
============================================================

[1/3] Found 12 agent executions to process

[2/3] Clearing existing JSONB message arrays...
      Cleared 12 agents

[3/3] Rebuilding JSONB arrays from Message table...
Processing 45 messages from Message table...
      Rebuilt 90 message entries

[DRY RUN] Rolling back changes (no modifications made)

============================================================
REPAIR SUMMARY
============================================================
Agents Processed:      12
Agents Cleared:        12
Messages Rebuilt:      90
Errors:                0
Duration:              1.23s
============================================================
```

## When to Run

**Run this script if:**
- Message counters show unread messages that agents have already acknowledged
- Message acknowledgments fail with "message not found" errors
- You deployed the broadcast fix and need to repair existing data

**Don't run this script if:**
- Message system is working correctly
- You haven't deployed the broadcast message fix yet (repair won't help)

## Technical Details

### Database Tables

**Message Table** (source of truth):
- `id`: Unique message_id (UUID)
- `to_agents`: JSONB array of recipient agent_ids
- `status`: "pending" or "acknowledged"
- `content`: Message text
- `created_at`: Timestamp

**AgentExecution Table** (JSONB storage):
- `agent_id`: Executor UUID (primary key)
- `messages`: JSONB array of message objects
- Used by frontend for message counter display

### JSONB Structure

The `agent_executions.messages` JSONB column stores:

```typescript
interface MessageEntry {
  id: string;           // Message ID from Message table
  from: string;         // Sender agent type or ID
  direction: "inbound" | "outbound";
  status: "waiting" | "read" | "sent";
  text: string;         // Truncated to 200 chars
  priority: string;     // "low", "normal", "high"
  timestamp: string;    // ISO8601 format
  to_agents?: string[]; // Only for outbound messages
}
```

### Status Mapping

| Message Table Status | JSONB Inbound Status | JSONB Outbound Status |
|---------------------|---------------------|----------------------|
| pending | waiting | sent |
| acknowledged | read | sent |

## Troubleshooting

### Error: "Could not connect to database"

**Solution**: Check that PostgreSQL is running and `config.yaml` has correct credentials.

```bash
# Test database connection
python scripts/init_database.py
```

### Error: "No messages found"

**Cause**: Message table is empty (fresh install).

**Solution**: This is normal for new installations. No repair needed.

### Error: "Foreign key constraint violation"

**Cause**: Message references non-existent agent or project.

**Solution**: Run with `--verbose` to identify problematic message, then investigate:

```sql
-- Find orphaned messages
SELECT id, project_id, to_agents
FROM messages
WHERE project_id NOT IN (SELECT id FROM projects);
```

## Post-Repair Verification

After running the repair, verify message counters are correct:

1. **Check Agent Dashboard**: Message counters should match actual unread messages
2. **Test Acknowledgment**: Send a test message and acknowledge it - counter should decrement
3. **Check Database**:

```sql
-- Count JSONB messages per agent
SELECT
  agent_type,
  agent_id,
  jsonb_array_length(messages) as message_count
FROM agent_executions
WHERE messages IS NOT NULL
ORDER BY message_count DESC;

-- Compare to Message table
SELECT
  COUNT(*) as total_messages,
  COUNT(CASE WHEN status = 'pending' THEN 1 END) as pending,
  COUNT(CASE WHEN status = 'acknowledged' THEN 1 END) as acknowledged
FROM messages;
```

## Files Modified

- `F:\GiljoAI_MCP\scripts\repair_jsonb_messages.py` - Main repair script
- `F:\GiljoAI_MCP\scripts\README_repair_jsonb_messages.md` - This documentation

## Related Files

- `src/giljo_mcp/models/tasks.py` - Message model definition
- `src/giljo_mcp/models/agent_identity.py` - AgentExecution model with JSONB column
- `src/giljo_mcp/services/message_service.py` - Message service with fixed broadcast logic

## Author

**Claude Code** (Implementation Specialist)
**Date**: 2026-01-05
**Handover**: Message JSONB Repair (Post-Broadcast Fix)
