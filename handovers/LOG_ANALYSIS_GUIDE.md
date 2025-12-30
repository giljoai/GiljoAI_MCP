# Log Analysis Guide for AI Coding Agents

**Purpose**: Manual for AI agents to analyze logs, debug issues, and use structured logging in GiljoAI MCP.

**When to use this guide**:
- User reports a bug or error
- Debugging production issues
- Investigating test failures
- Writing new error handling code
- User asks "check the logs"

---

## Quick Reference: Error Code Catalog

### AUTH (Authentication/Authorization)
| Code | Meaning | Common Causes |
|------|---------|---------------|
| AUTH001 | Invalid credentials | Wrong password, user typo |
| AUTH002 | Token expired | JWT timeout, session timeout |
| AUTH003 | Token invalid | Malformed JWT, tampered token |
| AUTH004 | Unauthorized | User lacks permission for resource |
| AUTH005 | Session expired | Session timeout |
| AUTH006 | PIN invalid | Wrong recovery PIN |
| AUTH007 | PIN expired | Recovery PIN timeout |
| AUTH008 | Rate limit exceeded | Too many login attempts |
| AUTH009 | User not found | Account doesn't exist, deleted user |
| AUTH010 | Tenant mismatch | Cross-tenant access attempt |
| AUTH011 | CSRF validation failed | Missing/invalid CSRF token |

### DB (Database)
| Code | Meaning | Common Causes |
|------|---------|---------------|
| DB001 | Connection failed | PostgreSQL down, wrong credentials, network issue |
| DB002 | Query timeout | Slow query, missing index, deadlock |
| DB003 | Transaction rollback | Constraint violation, app error during transaction |
| DB004 | Constraint violation | Unique key, foreign key violation |
| DB005 | Record not found | ID doesn't exist, already deleted |
| DB006 | Duplicate entry | Unique constraint violated |
| DB007 | Migration failed | Alembic migration error |
| DB008 | Pool exhausted | Too many concurrent connections |
| DB009 | Deadlock detected | Concurrent transactions conflicting |
| DB010 | Integrity error | Data consistency violation |

### WS (WebSocket)
| Code | Meaning | Common Causes |
|------|---------|---------------|
| WS001 | Connection failed | Network issue, auth failure |
| WS002 | Message send failed | Client disconnected, network error |
| WS003 | Message parse failed | Malformed JSON, protocol error |
| WS004 | Authentication failed | No token, invalid token |
| WS005 | Tenant isolation violated | Cross-tenant message attempt |
| WS006 | Broadcast failed | Multiple client send failures |
| WS007 | Disconnected unexpectedly | Network drop, client crash |
| WS008 | Subscription failed | Auth issue, invalid entity |
| WS009 | Heartbeat timeout | Client stopped responding |

### MCP (MCP Tools & Agents)
| Code | Meaning | Common Causes |
|------|---------|---------------|
| MCP001 | Tool execution error | Tool crashed, invalid params |
| MCP002 | Agent spawn failed | Template error, DB error |
| MCP003 | Context fetch failed | Vision doc missing, DB error |
| MCP004 | Mission not found | Agent job doesn't exist |
| MCP005 | Orchestrator error | Orchestrator crashed, logic error |
| MCP006 | Succession failed | Handover error, context too large |
| MCP007 | Agent not found | Job deleted, invalid ID |
| MCP008 | Invalid tenant | Tenant key mismatch |
| MCP009 | Tool schema invalid | Pydantic validation failed |
| MCP010 | Session expired | MCP session timeout |
| MCP011 | HTTP transport error | Network error, API down |

### API (API/Request Errors)
| Code | Meaning | Common Causes |
|------|---------|---------------|
| API001 | Validation error | Pydantic validation failed, bad input |
| API002 | Rate limit exceeded | Too many requests |
| API003 | Resource not found | 404, deleted resource |
| API004 | Method not allowed | Wrong HTTP method |
| API005 | Internal error | Unhandled exception, 500 error |
| API006 | Bad request | Malformed JSON, missing required field |
| API007 | Timeout | Request took too long |
| API008 | Payload too large | Request body exceeds limit |
| API009 | Unsupported media type | Wrong Content-Type |
| API010 | Conflict | Resource already exists, version conflict |
| API011 | Dependency failed | External service down |

---

## How to Search Logs

### Development (Console Logs)
Logs are in colorized console format. Use grep:

```bash
# Search by error code
grep "AUTH001" logs/app.log

# Search by event name
grep "authentication_failed" logs/app.log

# Search by user
grep "user_id.*abc123" logs/app.log

# All auth errors
grep "error_code.*AUTH" logs/app.log

# Last hour of errors
tail -n 1000 logs/app.log | grep "ERROR"
```

### Production (JSON Logs)
Logs are in JSON format. Use `jq` for queries:

```bash
# All AUTH errors
jq 'select(.error_code | startswith("AUTH"))' logs/app.json

# Specific error code
jq 'select(.error_code == "DB001")' logs/app.json

# Count errors by code
jq -r '.error_code' logs/app.json | sort | uniq -c

# Errors for specific user
jq 'select(.user_id == "abc123")' logs/app.json

# Errors in time range
jq 'select(.timestamp > "2025-12-27T10:00:00Z" and .timestamp < "2025-12-27T11:00:00Z")' logs/app.json

# WebSocket errors with context
jq 'select(.error_code | startswith("WS")) | {time: .timestamp, code: .error_code, client: .client_id, error: .error_message}' logs/app.json
```

---

## Common Debugging Scenarios

### Scenario 1: "Users can't log in"

**Step 1**: Search for AUTH errors
```bash
grep "AUTH" logs/app.log | tail -20
# or
jq 'select(.error_code | startswith("AUTH"))' logs/app.json | tail -20
```

**Step 2**: Identify pattern
- **AUTH001** (invalid credentials) → User typo or wrong password
- **AUTH002** (token expired) → Session timeout, check JWT expiry
- **AUTH004** (unauthorized) → Permission issue, check user roles
- **AUTH008** (rate limit) → Brute force protection triggered
- **AUTH010** (tenant mismatch) → Multi-tenant isolation bug

**Step 3**: Check context fields
```bash
jq 'select(.error_code == "AUTH001") | {user: .user_id, ip: .ip_address, reason: .reason}' logs/app.json
```

**Step 4**: Look for related errors
```bash
# Check if DB is down (might cause AUTH failures)
jq 'select(.error_code | startswith("DB"))' logs/app.json | tail -10
```

---

### Scenario 2: "WebSocket disconnects"

**Step 1**: Find WS errors
```bash
jq 'select(.error_code | startswith("WS"))' logs/app.json
```

**Step 2**: Identify type
- **WS001** (connection failed) → Network or auth issue
- **WS002** (send failed) → Client disconnected mid-message
- **WS007** (unexpected disconnect) → Network instability
- **WS009** (heartbeat timeout) → Client crashed or frozen

**Step 3**: Check affected clients
```bash
jq 'select(.error_code == "WS007") | .client_id' logs/app.json | sort | uniq -c
```

**Step 4**: Correlate with other errors
```bash
# Check if tenant has other issues
jq 'select(.tenant_key == "tenant_abc" and .level == "error")' logs/app.json
```

---

### Scenario 3: "Database errors"

**Step 1**: Find DB errors
```bash
jq 'select(.error_code | startswith("DB"))' logs/app.json
```

**Step 2**: Identify issue
- **DB001** (connection failed) → PostgreSQL down, check `psql -U postgres -l`
- **DB002** (timeout) → Slow query, check `query` field
- **DB003** (rollback) → Transaction error, check `error_message`
- **DB008** (pool exhausted) → Too many connections, check pool config
- **DB009** (deadlock) → Concurrent transaction conflict

**Step 3**: Check query details
```bash
jq 'select(.error_code == "DB002") | {query: .query, timeout: .timeout_ms}' logs/app.json
```

**Step 4**: Investigate root cause
```bash
# Check if specific operation causing timeouts
jq 'select(.error_code == "DB002") | .query' logs/app.json | grep "SELECT" | sort | uniq -c
```

---

### Scenario 4: "MCP agent failures"

**Step 1**: Find MCP errors
```bash
jq 'select(.error_code | startswith("MCP"))' logs/app.json
```

**Step 2**: Identify failure point
- **MCP001** (tool error) → Tool crashed, check `error_message`
- **MCP002** (spawn failed) → Can't create agent, check DB/template
- **MCP003** (context fetch failed) → Vision doc or product missing
- **MCP005** (orchestrator error) → Orchestrator logic bug
- **MCP006** (succession failed) → Handover context too large

**Step 3**: Check agent details
```bash
jq 'select(.error_code == "MCP002") | {agent: .agent_type, job: .job_id, error: .error_message}' logs/app.json
```

**Step 4**: Trace execution flow
```bash
# Find all logs for specific job_id
jq 'select(.job_id == "job_123")' logs/app.json | jq -s 'sort_by(.timestamp)'
```

---

## Writing Code with Structured Logging

### Import Pattern
```python
from giljo_mcp.logging import get_logger, ErrorCode

logger = get_logger(__name__)
```

### Error Logging Template
```python
try:
    # Your code here
    result = some_operation()
except SomeSpecificError as e:
    logger.error(
        "operation_failed",  # Event name (lowercase_with_underscores)
        error_code=ErrorCode.RELEVANT_CODE.value,  # Choose from catalog
        # Context fields (what would help debug this?)
        user_id=user_id,
        operation="operation_name",
        error_message=str(e),
        # Add relevant context
    )
    raise
```

### Examples by Category

#### Authentication Errors
```python
# Invalid credentials
logger.warning(
    "authentication_failed",
    error_code=ErrorCode.AUTH_INVALID_CREDENTIALS.value,
    user_id=user_id,
    ip_address=request.client.host,
    reason="invalid_password"
)

# Token expired
logger.warning(
    "token_expired",
    error_code=ErrorCode.AUTH_TOKEN_EXPIRED.value,
    user_id=user_id,
    token_age_seconds=token_age,
    max_age_seconds=max_age
)
```

#### Database Errors
```python
# Connection failed
logger.error(
    "database_connection_failed",
    error_code=ErrorCode.DB_CONNECTION_FAILED.value,
    host=db_config.host,
    port=db_config.port,
    database=db_config.database,
    error_message=str(e)
)

# Query timeout
logger.error(
    "database_query_timeout",
    error_code=ErrorCode.DB_QUERY_TIMEOUT.value,
    query=query[:200],  # First 200 chars
    timeout_ms=timeout,
    table=table_name
)
```

#### WebSocket Errors
```python
# Send failed
logger.warning(
    "websocket_send_failed",
    error_code=ErrorCode.WS_MESSAGE_SEND_FAILED.value,
    client_id=client_id,
    message_type=message_type,
    error_message=str(e)
)

# Unauthorized subscription
logger.warning(
    "unauthorized_subscription_attempt",
    error_code=ErrorCode.WS_AUTHENTICATION_FAILED.value,
    client_id=client_id,
    entity_type=entity_type,
    entity_id=entity_id,
    tenant_key=tenant_key
)
```

#### MCP Tool Errors
```python
# Tool execution failed
logger.error(
    "mcp_tool_execution_failed",
    error_code=ErrorCode.MCP_TOOL_EXECUTION_ERROR.value,
    tool_name=tool_name,
    params=params,
    error_message=str(e),
    exc_info=True  # Include traceback
)

# Agent spawn failed
logger.error(
    "agent_spawn_failed",
    error_code=ErrorCode.MCP_AGENT_SPAWN_FAILED.value,
    agent_type=agent_type,
    project_id=project_id,
    tenant_key=tenant_key,
    error_message=str(e)
)
```

#### API Errors
```python
# Validation error
logger.warning(
    "request_validation_failed",
    error_code=ErrorCode.API_VALIDATION_ERROR.value,
    endpoint=request.url.path,
    method=request.method,
    validation_errors=str(e.errors())
)

# Rate limit
logger.warning(
    "rate_limit_exceeded",
    error_code=ErrorCode.API_RATE_LIMIT_EXCEEDED.value,
    user_id=user_id,
    ip_address=request.client.host,
    endpoint=request.url.path,
    limit=rate_limit,
    window_seconds=window
)
```

---

## Log Analysis Workflow for Agents

### When User Reports Bug

1. **Ask for specifics**:
   - What happened? (error message, symptom)
   - When? (timestamp, frequency)
   - Who? (user ID, all users, specific tenant)

2. **Search logs**:
   ```bash
   # By time range
   jq 'select(.timestamp > "2025-12-27T10:00:00Z")' logs/app.json

   # By user
   jq 'select(.user_id == "USER_ID")' logs/app.json

   # By error level
   jq 'select(.level == "error")' logs/app.json
   ```

3. **Identify error code**:
   - Match symptom to error code
   - Check catalog above for meaning
   - Look at context fields

4. **Trace execution**:
   ```bash
   # All logs for request/job
   jq 'select(.request_id == "REQ_ID")' logs/app.json | jq -s 'sort_by(.timestamp)'
   ```

5. **Find root cause**:
   - Check related systems (DB, WS, MCP)
   - Look for cascading failures
   - Check timing patterns

6. **Report findings**:
   - Error code(s) found
   - Context fields
   - Root cause hypothesis
   - Suggested fix

---

## Advanced Queries

### Aggregate Errors by Type
```bash
jq -r '.error_code' logs/app.json | sort | uniq -c | sort -rn
```

### Errors Per Minute
```bash
jq -r '.timestamp[:16]' logs/app.json | uniq -c
```

### Top Error-Prone Users
```bash
jq -r 'select(.level == "error") | .user_id' logs/app.json | sort | uniq -c | sort -rn | head -10
```

### Errors by Tenant
```bash
jq -r 'select(.level == "error") | .tenant_key' logs/app.json | sort | uniq -c
```

### Error Timeline
```bash
jq 'select(.level == "error") | {time: .timestamp, code: .error_code, msg: .event}' logs/app.json
```

### Correlation Analysis
```bash
# Find errors that happen together
jq -r 'select(.level == "error") | "\(.timestamp[:16]) \(.error_code)"' logs/app.json | \
  awk '{print $1}' | uniq -c | awk '$1 > 1 {print $2}'
```

---

## Log Files Locations

### Development
- **Console**: `stdout` (colorized)
- **File**: `logs/app.log` (if configured)

### Production
- **JSON**: `logs/app.json` (structured)
- **Service logs**: Check `journalctl -u giljo-mcp` (systemd)

### Test Logs
- **pytest output**: `pytest -v` (shows all logs)
- **pytest logs**: `.pytest_cache/` (cached test logs)

---

## Configuration

### Environment Variables
```bash
# Set log level (DEBUG, INFO, WARNING, ERROR, CRITICAL)
export LOG_LEVEL=INFO

# Set environment (affects output format)
export ENVIRONMENT=production  # JSON output
export ENVIRONMENT=development  # Console output
```

### Force JSON Output
```python
from giljo_mcp.logging import configure_logging

configure_logging(environment="production", force_json=True)
```

---

## Best Practices for Agents

### DO
✅ **Always include error codes** for errors
✅ **Add context fields** that would help debug
✅ **Use specific event names** (`user_login_failed` not `error`)
✅ **Search logs before asking user** for more info
✅ **Trace full request path** using request_id/job_id
✅ **Look for patterns** (timing, users, tenants)

### DON'T
❌ **Use error codes for info logs** (only errors/warnings)
❌ **Log sensitive data** (passwords, tokens, API keys)
❌ **Assume single root cause** (check for cascading failures)
❌ **Skip context fields** (`error_message=str(e)` at minimum)
❌ **Use f-strings for error logs** (use structured fields)

---

## Quick Troubleshooting

### "Can't find logs"
```bash
# Check if logs directory exists
ls -la logs/

# Check log configuration
python -c "from giljo_mcp.logging import get_logger; logger = get_logger('test'); logger.info('test')"
```

### "jq not installed"
```bash
# Install jq
# Ubuntu/Debian
sudo apt-get install jq

# macOS
brew install jq

# Windows (Git Bash)
# Download from https://stedolan.github.io/jq/
```

### "Logs too large to parse"
```bash
# Last 1000 lines
tail -n 1000 logs/app.json | jq 'select(.error_code | startswith("AUTH"))'

# Use grep before jq
grep "AUTH" logs/app.json | jq '.'

# Split by date
jq 'select(.timestamp | startswith("2025-12-27"))' logs/app.json > today.json
```

---

## Error Code Lookup Shortcut

```bash
# Create alias for quick lookup
alias errcode='grep -A1 "class ErrorCode" src/giljo_mcp/logging/error_codes.py'

# Usage
errcode | grep AUTH001
```

---

## Summary

**When user says**: "Check the logs"
**You do**:
1. Identify time range + user/tenant
2. Search by error code or event name
3. Analyze context fields
4. Trace request/job flow
5. Report findings with error codes

**Error Code = GPS Coordinates in Logs** 🎯
