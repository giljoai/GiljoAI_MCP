# Test Capture: Orchestrator Instructions

**Test ID:** 0347 test_Agent_Type_Only_Vision_Full_CLI-mode_3_agents_enabled-V2

**Timestamp:** 2025-12-14

**Orchestrator ID:** 6792fae5-c46b-4ed7-86d6-df58aa833df3

**Tenant Key:** ***REMOVED***

## MCP Tool Call

```
Tool: mcp__giljo-mcp__get_orchestrator_instructions
Parameters:
  - orchestrator_id: 6792fae5-c46b-4ed7-86d6-df58aa833df3
  - tenant_key: ***REMOVED***
```

## Response

```json
{
  "error": "INTERNAL_ERROR",
  "message": "Unexpected error: 'AgentTemplate' object has no attribute 'content'"
}
```

## Status

**ERROR:** The MCP server returned an internal error. The error suggests that the server is attempting to access a 'content' attribute on an 'AgentTemplate' object that doesn't exist. This is likely a server-side implementation issue that needs to be investigated.

## Notes

- The error occurred when attempting to fetch orchestrator instructions for the specified orchestrator job
- This may indicate a schema mismatch or incomplete implementation in the MCP server
- The tenant key and orchestrator ID appear to be valid format-wise but the server encountered an internal processing error
