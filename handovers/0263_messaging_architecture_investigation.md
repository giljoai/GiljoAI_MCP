# Handover 0263: Messaging Architecture Investigation

**Status**: ✅ COMPLETE
**Date**: 2025-11-29
**Completed**: 2025-11-29
**Priority**: CRITICAL
**Follow-up**: Handover 0262 (FLOW.md documentation updates)

## Executive Summary

Investigation into the GiljoAI MCP messaging architecture revealed **two distinct messaging systems** with unclear boundaries between obsolete and active components. The user raised critical questions about agent communication functionality, broadcast messaging, and whether the messaging system is currently functional.

## Current Findings

### Two Messaging Systems Discovered

1. **JSONB-based Peer Messaging System** (Active)
   - **Location**: `MCPAgentJob.messages` JSONB column
   - **Purpose**: Agent-to-agent communication queue
   - **Type**: In-process message queue embedded in job records

2. **Table-based Messaging System** (Status Unknown)
   - **Location**: Separate `MCPMessage` table (if exists)
   - **Purpose**: Traditional message persistence
   - **Type**: Relational table with sender/recipient/status fields

### Evidence

#### Database Schema
- **File**: `src/giljo_mcp/models.py`
- **MCPAgentJob Model**: Contains `messages` JSONB column
  ```python
  messages = Column(JSONB, nullable=False, default=list, server_default='[]')
  ```
- **Purpose**: Stores message queue for each agent job

#### JobsTab UI Implementation
- **File**: `frontend/src/components/projects/JobsTab.vue`
- **Data Source**: `GET /api/agent-jobs?project_id={projectId}`
- **Columns Populated**:
  - `agent_name`: From `job.agent_name`
  - `status`: From `job.status`
  - `health`: From `job.health`
  - `Messages`: From `job.messages.length` (JSONB array count)
  - `Read`: From `job.read` boolean
  - `Acknowledged`: From `job.acknowledged` boolean

#### Code Evidence for JSONB Messages
```vue
// JobsTab.vue - Message count display
{
  title: 'Messages',
  key: 'messages',
  align: 'center',
  width: '100px',
  sortable: true,
  value: item => item.messages?.length || 0
}
```

### Confusion Points

1. **What's "Obsolete"?**
   - User mentioned "obsolete table-based system" but unclear which tables
   - JSONB system appears active based on UI integration
   - No clear deprecation warnings found in code

2. **Two Systems or One?**
   - If JSONB is primary, why mention separate table system?
   - Are they complementary (queue + history) or competitive (old vs new)?

3. **Messaging Functionality Status**
   - Is messaging fully functional?
   - Are there disabled features?
   - Are there UI buttons that don't work?

## Critical Questions (User-Raised)

### Question 1: How do agents broadcast/send messages to each other?
- What function handles agent-to-agent messaging?
- Is there broadcast vs direct message support?
- Where is the implementation (`send_mcp_message()` in `src/giljo_mcp/tools/`)?

### Question 2: How does orchestrator tell other agents "XYZ"?
- Special orchestrator message functions?
- Broadcast capability for orchestrator?
- Message flow: Orchestrator → Database → Agents

### Question 3: Dashboard feature to see agent communication
- Where is the message history UI?
- What component shows agent communication log?
- Does it read from JSONB queue or separate table?

### Question 4: Send message to orchestrator feature
- UI button/form location for "Send to Orchestrator"
- API endpoint traced
- Database write location verification

### Question 5: Broadcast message feature
- UI button/form for "Broadcast" functionality
- API endpoint implementation
- Multiple records vs single broadcast record?

### Question 6: Database audit trail
- Are ALL messages persisted (not ephemeral)?
- Message history/archive location
- Audit fields: timestamp, sender, recipient, status

### Question 7: Has messaging been disabled?
- Commented out MCP tools?
- Non-functional API endpoints?
- Disabled UI buttons?
- Feature flags for messaging?

## Next Steps

### Investigation Tasks

1. **Find Message Sending Implementation**
   - Search for `send_mcp_message()` in `src/giljo_mcp/tools/`
   - Check `send_message()` variants
   - Trace message creation flow

2. **Verify Database Schema**
   - Confirm JSONB system is primary
   - Check for `MCPMessage` table existence
   - Audit trail verification

3. **UI Component Analysis**
   - Find message history viewer component
   - Locate "Send to Orchestrator" button
   - Locate "Broadcast" button
   - Verify functionality status

4. **API Endpoint Tracing**
   - Message sending endpoints
   - Message retrieval endpoints
   - Broadcast endpoints

5. **Feature Status Check**
   - Feature flags in code
   - Disabled/commented code
   - Error handling for messaging

### Tools to Use
- `find_symbol` for function definitions
- `search_for_pattern` for "broadcast", "send_message", "mcp_message"
- `get_symbols_overview` for file structure
- `find_referencing_symbols` for usage tracking

## Notes

- **Multi-tenant isolation**: All messaging must respect `tenant_key`
- **WebSocket integration**: Real-time message delivery mechanism?
- **MCP tool exposure**: Are message tools exposed via MCP server?

## References

- `src/giljo_mcp/models.py` - Database schema
- `frontend/src/components/projects/JobsTab.vue` - UI implementation
- `src/giljo_mcp/tools/` - MCP tool implementations (to investigate)
- `api/endpoints/` - API endpoints (to investigate)

