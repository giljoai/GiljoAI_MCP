# Deprecation Notice: AgentExecution.messages JSONB Column

**Deprecated In**: v3.2 (Handover 0387i)
**Removal Planned**: v4.0

## What Changed
The `AgentExecution.messages` JSONB column has been replaced by counter columns:
- `messages_sent_count`
- `messages_waiting_count`
- `messages_read_count`

## Migration Path
No action required. The system automatically uses counter columns.

## Why Deprecated
1. Single source of truth (Message table + counters)
2. No dual-write sync risk
3. Better performance (O(1) counter read vs O(n) JSONB iteration)

## Timeline
- v3.2: Column deprecated, counter columns authoritative
- v4.0: Column removed from database
