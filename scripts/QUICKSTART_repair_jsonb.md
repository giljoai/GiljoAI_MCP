# Quick Start: JSONB Message Repair

## What This Script Does

Fixes broadcast message bug where wrong `message_id` values were stored in agent JSONB arrays.

## Do I Need This?

**Run this script if you see:**
- ✗ Message counters showing unread messages that agents already acknowledged
- ✗ "Message not found" errors when acknowledging messages
- ✗ Message badges stuck at high numbers

**Skip this script if:**
- ✓ Message system is working correctly
- ✓ This is a fresh installation (no existing messages to repair)

## Quick Run (Windows)

```bash
# 1. Preview changes (safe, no modifications)
./venv/Scripts/python.exe scripts/repair_jsonb_messages.py --dry-run

# 2. If preview looks good, run the repair
./venv/Scripts/python.exe scripts/repair_jsonb_messages.py
```

## Quick Run (Linux/macOS)

```bash
# 1. Preview changes (safe, no modifications)
./venv/bin/python scripts/repair_jsonb_messages.py --dry-run

# 2. If preview looks good, run the repair
./venv/bin/python scripts/repair_jsonb_messages.py
```

## What to Expect

**Dry Run Output:**
```
============================================================
JSONB MESSAGE REPAIR SCRIPT
============================================================
Mode:        DRY RUN (no changes)
Tenant:      ALL TENANTS

[1/3] Found 12 agent executions to process
[2/3] Clearing existing JSONB message arrays...
      Cleared 12 agents
[3/3] Rebuilding JSONB arrays from Message table...
      Rebuilt 90 message entries

[DRY RUN] Rolling back changes (no modifications made)

============================================================
REPAIR SUMMARY
============================================================
Agents Processed:      12
Messages Rebuilt:      90
Errors:                0
============================================================
```

**Live Run:**
- Same output, but commits changes to database
- Asks for confirmation before proceeding
- Creates a database transaction (all-or-nothing)

## Safety

- ✅ Dry-run mode available
- ✅ Requires confirmation before changes
- ✅ Atomic transaction (rolls back on error)
- ✅ Can be run multiple times safely

## Need More Info?

See `README_repair_jsonb_messages.md` for:
- Detailed explanation of the bug
- Technical details
- Troubleshooting guide
- Post-repair verification steps

## Support

If you encounter errors, run with verbose flag to see details:

```bash
# Windows
./venv/Scripts/python.exe scripts/repair_jsonb_messages.py --dry-run --verbose

# Linux/macOS
./venv/bin/python scripts/repair_jsonb_messages.py --dry-run --verbose
```

Then check the error message and consult `README_repair_jsonb_messages.md` troubleshooting section.
