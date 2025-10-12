# Setup API Endpoints Reference

**Version:** 2.0.0
**Last Updated:** 2025-10-07
**Base URL:** `http://localhost:7272/api` (localhost) or `http://<server-ip>:7272/api` (LAN/WAN)

---

## Table of Contents

1. [Overview](#overview)
2. [Authentication](#authentication)
3. [Endpoints](#endpoints)
   - [GET /setup/status](#get-setupstatus)
   - [POST /setup/complete](#post-setupcomplete)
   - [POST /setup/migrate](#post-setupmigrate)
4. [Request Models](#request-models)
5. [Response Models](#response-models)
6. [Error Handling](#error-handling)
7. [Examples](#examples)
8. [Version History](#version-history)

---

## Overview

The Setup API endpoints manage the GiljoAI MCP installation and configuration wizard. These endpoints track setup completion status, save wizard configuration, and handle version migrations.

### Key Features

- **Setup Status Tracking**: Check if setup wizard has been completed
- **Configuration Persistence**: Save wizard settings to database and config.yaml
- **Version Management**: Detect and resolve version mismatches
- **LAN Mode Support**: Generate API keys for network deployments
- **Backward Compatible**: v2.0 maintains compatibility with v1.x clients

### Architecture Changes (v2.0)

In version 2.0, setup state storage migrated from file-based (`config.yaml`) to hybrid file/database approach:

- **Before v2.0**: State stored in gitignored `config.yaml` file
- **After v2.0**: State stored in PostgreSQL `setup_state` table with file fallback
- **Migration**: Automatic migration from legacy sources
- **Benefit**: Survives code updates via `git pull`, prevents configuration drift

---

## Authentication

### Localhost Mode

**No authentication required** for localhost deployments:

```bash
# No headers needed
curl http://localhost:7272/api/setup/status
```

### LAN/WAN Mode

**API key authentication required** after setup completion:

```bash
# Include API key in Authorization header
curl -H "Authorization: Bearer gai_1a2b3c4d5e6f7g8h9i0j" \
     http://192.168.1.100:7272/api/setup/status
```

**Note:** API key is generated during setup wizard completion when selecting LAN or WAN mode.

---

## Endpoints

### GET /setup/status

Check if setup wizard has been completed and retrieve current configuration status.

#### Request

```http
GET /api/setup/status HTTP/1.1
Host: localhost:7272
```

**No request body required**

#### Response

**Status Code:** `200 OK`

```json
{
  "completed": true,
  "database_configured": true,
  "tools_attached": ["claude-code"],
  "network_mode": "localhost",
  "needs_migration": false
}
```

#### Response Fields

| Field | Type | Description |
|-------|------|-------------|
| `completed` | boolean | Whether setup wizard has been completed |
| `database_configured` | boolean | Always `true` (database configured by installer) |
| `tools_attached` | array[string] | List of attached MCP tools (e.g., `["claude-code", "serena"]`) |
| `network_mode` | string | Current deployment mode: `localhost`, `lan`, or `wan` |
| `needs_migration` | boolean | *(v2.0+)* Whether setup state needs version migration |

#### Use Cases

1. **Router Guards**: Frontend checks if setup completed before loading dashboard
2. **Status Monitoring**: Admin dashboard displays setup status
3. **Migration Detection**: Detect version mismatches after code updates

#### Example Usage

```javascript
// Frontend router guard
async function checkSetup() {
  const response = await fetch('/api/setup/status');
  const status = await response.json();

  if (!status.completed) {
    // Redirect to setup wizard
    router.push('/setup');
  }

  if (status.needs_migration) {
    // Show migration warning banner
    console.warn('Setup state needs migration');
  }
}
```

---

### POST /setup/complete

Complete setup wizard and persist configuration to database and config.yaml.

#### Request

```http
POST /api/setup/complete HTTP/1.1
Host: localhost:7272
Content-Type: application/json

{
  "tools_attached": ["claude-code"],
  "network_mode": "lan",
  "serena_enabled": true,
  "lan_config": {
    "server_ip": "192.168.1.100",
    "hostname": "giljo.local",
    "firewall_configured": true,
    "admin_username": "admin",
    "admin_password": "secure_password"
  }
}
```

#### Request Body Fields

| Field | Type | Required | Description |
|-------|------|----------|-------------|
| `tools_attached` | array[string] | Yes | MCP tools to attach (e.g., `["claude-code"]`) |
| `network_mode` | string | Yes | Deployment mode: `localhost`, `lan`, or `wan` |
| `serena_enabled` | boolean | No | Whether Serena MCP instructions are enabled (default: `false`) |
| `lan_config` | object | No | LAN-specific configuration (required if `network_mode` is `lan` or `wan`) |

#### LAN Config Object

| Field | Type | Required | Description |
|-------|------|----------|-------------|
| `server_ip` | string | Yes | Server IP address on LAN (e.g., `192.168.1.100`) |
| `hostname` | string | No | Hostname for LAN access (default: `giljo.local`) |
| `firewall_configured` | boolean | No | Whether firewall rules are configured (default: `false`) |
| `admin_username` | string | No | Admin username for server mode (default: `admin`) |
| `admin_password` | string | Yes | Admin password (will be hashed before storage) |

#### Response

**Status Code:** `200 OK`

```json
{
  "success": true,
  "message": "Setup completed successfully",
  "api_key": "gai_1a2b3c4d5e6f7g8h9i0j",
  "requires_restart": true
}
```

#### Response Fields

| Field | Type | Description |
|-------|------|-------------|
| `success` | boolean | Whether setup completion was successful |
| `message` | string | Human-readable status message |
| `api_key` | string | Generated API key (only for `lan` or `wan` modes, `null` for `localhost`) |
| `requires_restart` | boolean | Whether backend service restart is required (true for LAN/WAN) |

#### Side Effects

1. **Updates config.yaml**: Writes network mode, CORS origins, API key hash
2. **Persists to database**: Saves state to `setup_state` table via SetupStateManager
3. **Creates snapshot**: Stores complete config.yaml backup in `config_snapshot` column
4. **Generates API key**: Creates and hashes API key for LAN/WAN modes

#### Error Responses

**400 Bad Request** - Invalid configuration

```json
{
  "detail": "network_mode must be one of: localhost, lan, wan"
}
```

**500 Internal Server Error** - Failed to persist state

```json
{
  "detail": "Failed to persist setup state to database"
}
```

#### Example Usage

```javascript
// Frontend setup wizard
async function completeSetup(config) {
  const response = await fetch('/api/setup/complete', {
    method: 'POST',
    headers: { 'Content-Type': 'application/json' },
    body: JSON.stringify({
      tools_attached: ['claude-code'],
      network_mode: 'lan',
      serena_enabled: true,
      lan_config: {
        server_ip: '192.168.1.100',
        hostname: 'giljo.local',
        firewall_configured: true,
        admin_username: 'admin',
        admin_password: 'secure_password'
      }
    })
  });

  const result = await response.json();

  if (result.success && result.api_key) {
    // Show API key modal (user must save this)
    showApiKeyModal(result.api_key);
  }

  if (result.requires_restart) {
    // Show restart instructions modal
    showRestartModal();
  }
}
```

---

### POST /setup/migrate

Migrate setup state from older version to current version. This endpoint is called automatically when version mismatch is detected at startup.

#### Request

```http
POST /api/setup/migrate HTTP/1.1
Host: localhost:7272
```

**No request body required**

#### Response

**Status Code:** `200 OK`

```json
{
  "migrated": true,
  "old_version": "1.0.0",
  "current_version": "2.0.0",
  "message": "Migration completed successfully"
}
```

#### Response Fields

| Field | Type | Description |
|-------|------|-------------|
| `migrated` | boolean | Whether migration was performed (`false` if no migration needed) |
| `old_version` | string | Previous setup version (e.g., `"1.0.0"`, `null` if first-time setup) |
| `current_version` | string | Current setup version (e.g., `"2.0.0"`) |
| `message` | string | Human-readable migration status message |

#### Use Cases

1. **Automatic Startup Migration**: Called by application startup routine when version mismatch detected
2. **Manual Migration Trigger**: Admin can manually trigger migration after code updates
3. **Testing Migration Logic**: Developers can test migration paths

#### Error Responses

**500 Internal Server Error** - Migration failed

```json
{
  "detail": "No migration path from 1.0.0 to 2.0.0"
}
```

#### Example Usage

```bash
# Manual migration trigger
curl -X POST http://localhost:7272/api/setup/migrate

# Response:
# {
#   "migrated": true,
#   "old_version": "1.0.0",
#   "current_version": "2.0.0",
#   "message": "Migration completed successfully"
# }
```

---

## Request Models

### SetupCompleteRequest

Pydantic model for `/setup/complete` endpoint:

```python
class SetupCompleteRequest(BaseModel):
    """Request model for setup completion"""

    tools_attached: list[str] = Field(
        default_factory=list,
        description="List of MCP tools attached (e.g., ['claude-code'])"
    )
    network_mode: NetworkMode = Field(
        ...,
        description="Network deployment mode (localhost, lan, or wan)"
    )
    serena_enabled: bool = Field(
        False,
        description="Whether Serena MCP instructions are enabled"
    )
    lan_config: Optional[LANConfig] = Field(
        None,
        description="LAN-specific configuration (required for lan/wan modes)"
    )
```

### LANConfig

Configuration for LAN/WAN network deployments:

```python
class LANConfig(BaseModel):
    """LAN-specific configuration settings"""

    server_ip: str = Field(
        ...,
        description="Server IP address on LAN"
    )
    firewall_configured: bool = Field(
        False,
        description="Whether firewall rules are configured"
    )
    admin_username: str = Field(
        "admin",
        description="Admin username for server mode"
    )
    admin_password: str = Field(
        ...,
        description="Admin password (will be hashed)"
    )
    hostname: str = Field(
        "giljo.local",
        description="Hostname for LAN access"
    )
```

### NetworkMode

Valid network deployment modes:

```python
class NetworkMode(str, Enum):
    """Valid network deployment modes"""

    LOCALHOST = "localhost"
    LAN = "lan"
    WAN = "wan"
```

---

## Response Models

### SetupStatusResponse

Response model for `/setup/status` endpoint:

```python
class SetupStatusResponse(BaseModel):
    """Response model for setup status"""

    completed: bool = Field(
        ...,
        description="Whether setup wizard has been completed"
    )
    database_configured: bool = Field(
        ...,
        description="Whether database is configured (always true)"
    )
    tools_attached: list[str] = Field(
        default_factory=list,
        description="List of attached MCP tools"
    )
    network_mode: str = Field(
        ...,
        description="Current network deployment mode"
    )
    needs_migration: bool = Field(
        False,
        description="Whether setup state needs migration (v2.0+)"
    )
```

### SetupCompleteResponse

Response model for `/setup/complete` endpoint:

```python
class SetupCompleteResponse(BaseModel):
    """Response model for setup completion"""

    success: bool = Field(
        ...,
        description="Whether setup completion was successful"
    )
    message: str = Field(
        ...,
        description="Human-readable status message"
    )
    api_key: Optional[str] = Field(
        None,
        description="Generated API key for LAN/WAN modes"
    )
    requires_restart: bool = Field(
        False,
        description="Whether service restart is required"
    )
```

### MigrateResponse

Response model for `/setup/migrate` endpoint:

```python
class MigrateResponse(BaseModel):
    """Response model for setup migration"""

    migrated: bool = Field(
        ...,
        description="Whether migration was performed"
    )
    old_version: Optional[str] = Field(
        None,
        description="Previous setup version"
    )
    current_version: str = Field(
        ...,
        description="Current setup version"
    )
    message: str = Field(
        ...,
        description="Human-readable migration status"
    )
```

---

## Error Handling

### HTTP Status Codes

| Code | Meaning | When It Occurs |
|------|---------|----------------|
| `200` | OK | Request succeeded |
| `400` | Bad Request | Invalid request body or parameters |
| `401` | Unauthorized | Missing or invalid API key (LAN/WAN mode) |
| `403` | Forbidden | Valid API key but insufficient permissions |
| `500` | Internal Server Error | Database error or unexpected failure |

### Error Response Format

All errors return JSON with FastAPI standard format:

```json
{
  "detail": "Error message describing what went wrong"
}
```

### Common Errors

#### Invalid Network Mode

```json
{
  "detail": "network_mode must be one of: localhost, lan, wan"
}
```

**Cause:** Invalid value provided for `network_mode` field

**Solution:** Use valid enum value: `"localhost"`, `"lan"`, or `"wan"`

#### LAN Config Missing

```json
{
  "detail": "lan_config is required when network_mode is 'lan' or 'wan'"
}
```

**Cause:** LAN/WAN mode selected but no LAN configuration provided

**Solution:** Include `lan_config` object with required fields

#### Database Connection Failed

```json
{
  "detail": "Failed to persist setup state to database"
}
```

**Cause:** Database unavailable or connection error

**Solution:** Verify PostgreSQL is running, check database connection settings

#### Setup Already Completed

```json
{
  "detail": "Setup already completed. Use /setup to reconfigure."
}
```

**Cause:** Attempting to complete setup when already completed (v1.x behavior)

**Solution:** Navigate to `/setup` wizard to reconfigure settings

**Note:** In v2.0+, this error should not occur as setup can be re-run freely.

---

## Examples

### Example 1: Check Setup Status

```bash
curl http://localhost:7272/api/setup/status
```

**Response:**

```json
{
  "completed": false,
  "database_configured": true,
  "tools_attached": [],
  "network_mode": "localhost",
  "needs_migration": false
}
```

### Example 2: Complete Localhost Setup

```bash
curl -X POST http://localhost:7272/api/setup/complete \
  -H "Content-Type: application/json" \
  -d '{
    "tools_attached": ["claude-code"],
    "network_mode": "localhost",
    "serena_enabled": false
  }'
```

**Response:**

```json
{
  "success": true,
  "message": "Setup completed successfully",
  "api_key": null,
  "requires_restart": false
}
```

### Example 3: Complete LAN Setup

```bash
curl -X POST http://localhost:7272/api/setup/complete \
  -H "Content-Type: application/json" \
  -d '{
    "tools_attached": ["claude-code", "serena"],
    "network_mode": "lan",
    "serena_enabled": true,
    "lan_config": {
      "server_ip": "192.168.1.100",
      "hostname": "giljo.local",
      "firewall_configured": true,
      "admin_username": "admin",
      "admin_password": "secure_password123"
    }
  }'
```

**Response:**

```json
{
  "success": true,
  "message": "Setup completed successfully",
  "api_key": "gai_1a2b3c4d5e6f7g8h9i0j",
  "requires_restart": true
}
```

**Important:** Save the `api_key` - it will not be shown again.

### Example 4: Trigger Migration

```bash
curl -X POST http://localhost:7272/api/setup/migrate
```

**Response:**

```json
{
  "migrated": true,
  "old_version": "1.0.0",
  "current_version": "2.0.0",
  "message": "Migration completed successfully"
}
```

### Example 5: Frontend Integration

```javascript
// Vue.js setupService.js
class SetupService {
  async checkStatus() {
    const response = await fetch('/api/setup/status');
    return await response.json();
  }

  async completeSetup(config) {
    const response = await fetch('/api/setup/complete', {
      method: 'POST',
      headers: { 'Content-Type': 'application/json' },
      body: JSON.stringify(config)
    });

    if (!response.ok) {
      const error = await response.json();
      throw new Error(error.detail);
    }

    return await response.json();
  }

  async migrateState() {
    const response = await fetch('/api/setup/migrate', {
      method: 'POST'
    });
    return await response.json();
  }
}

export default new SetupService();
```

---

## Version History

### v2.0.0 (2025-10-07)

**Major Changes:**
- Migrated setup state from file-based (`config.yaml`) to hybrid file/database storage
- Added `SetupStateManager` for unified state management
- Added version tracking to prevent configuration drift
- Added `/setup/migrate` endpoint for version migrations
- Added `needs_migration` field to `/setup/status` response

**Backward Compatibility:**
- ✅ All v1.x API endpoints still work
- ✅ Response formats unchanged (except optional new fields)
- ✅ Request formats unchanged
- ✅ Automatic migration from v1.x to v2.0

**Breaking Changes:**
- None (fully backward compatible)

### v1.0.0 (2025-09-30)

**Initial Release:**
- `GET /api/setup/status` - Check setup status
- `POST /api/setup/complete` - Complete setup wizard
- File-based state storage in `config.yaml`

---

## Related Documentation

- **Architecture**: `docs/architecture/SETUP_STATE_ARCHITECTURE.md`
- **Migration Guide**: `docs/architecture/SETUP_STATE_MIGRATION_GUIDE.md`
- **Technical Architecture**: `docs/TECHNICAL_ARCHITECTURE.md`
- **Testing**: `docs/testing/SETUP_WIZARD_TEST_REPORT.md`

---

**Document Version:** 1.0.0
**Last Updated:** 2025-10-07
**Author:** Documentation Manager Agent
**Status:** Final
