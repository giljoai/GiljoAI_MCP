# LAN Authentication - API Reference

**Version:** 1.0.0
**Last Updated:** 2025-10-07
**Base URL:** `http://YOUR_SERVER_IP:7272`

---

## Table of Contents

1. [Overview](#overview)
2. [Authentication Methods](#authentication-methods)
3. [Error Responses](#error-responses)
4. [Rate Limiting](#rate-limiting)
5. [Endpoints](#endpoints)
   - [POST /api/auth/login](#post-apiauthlogin)
   - [POST /api/auth/logout](#post-apiauthlogout)
   - [GET /api/auth/me](#get-apiauthme)
   - [GET /api/auth/api-keys](#get-apiauthapi-keys)
   - [POST /api/auth/api-keys](#post-apiauthapi-keys)
   - [DELETE /api/auth/api-keys/{id}](#delete-apiauthapi-keysid)
   - [POST /api/auth/register](#post-apiauthregister)
6. [Code Examples](#code-examples)

---

## Overview

The GiljoAI MCP Authentication API provides secure access control for LAN/WAN deployments. All endpoints follow RESTful conventions and return JSON responses.

### Base URL

```
http://YOUR_SERVER_IP:7272
```

**Development:** `http://127.0.0.1:7272`
**LAN:** `http://192.168.1.100:7272` (use your server's IP)

### Interactive Documentation

FastAPI provides auto-generated interactive API docs:

- **Swagger UI:** http://YOUR_SERVER_IP:7272/docs
- **ReDoc:** http://YOUR_SERVER_IP:7272/redoc

---

## Authentication Methods

### Method 1: JWT Cookie (Web Sessions)

**Use Case:** Web dashboard authentication

**How it works:**
1. Login via `/api/auth/login` to get JWT cookie
2. Browser automatically includes cookie in subsequent requests
3. Server validates cookie on each request

**Example:**
```bash
# Login (sets cookie)
curl -X POST http://localhost:7272/api/auth/login \
  -H "Content-Type: application/json" \
  -d '{"username":"admin","password":"pass123"}' \
  -c cookies.txt

# Use cookie for authenticated request
curl -X GET http://localhost:7272/api/auth/me \
  -b cookies.txt
```

**Cookie Details:**
- **Name:** `access_token`
- **Attributes:** httpOnly, SameSite=Lax
- **Expiration:** 24 hours
- **Storage:** Browser cookies (automatic)

### Method 2: API Key Header (MCP Tools)

**Use Case:** Programmatic access, MCP clients

**How it works:**
1. Generate API key via `/api/auth/api-keys`
2. Include `X-API-Key` header in all requests
3. Server validates key hash against database

**Example:**
```bash
curl -X GET http://localhost:7272/api/projects \
  -H "X-API-Key: gk_your_api_key_here"
```

**Header Format:**
```
X-API-Key: gk_<32-byte-urlsafe-token>
```

### Method 3: Localhost Bypass (Development)

**Use Case:** Local development on 127.0.0.1

**How it works:**
- Requests from `127.0.0.1`, `localhost`, or `::1` bypass authentication
- Only works when server binding to localhost (not `0.0.0.0`)

**Example:**
```bash
# No authentication needed on localhost
curl http://127.0.0.1:7272/api/projects
```

---

## Error Responses

All error responses follow this format:

```json
{
  "detail": "Error message describing what went wrong"
}
```

### Common HTTP Status Codes

| Code | Meaning | When It Occurs |
|------|---------|----------------|
| **200** | OK | Request successful |
| **201** | Created | Resource created successfully |
| **400** | Bad Request | Invalid input data |
| **401** | Unauthorized | Authentication failed or missing |
| **403** | Forbidden | Insufficient permissions |
| **404** | Not Found | Resource doesn't exist |
| **422** | Validation Error | Request validation failed |
| **500** | Server Error | Internal server error |

### Authentication Errors

```json
// 401: Not authenticated
{
  "detail": "Not authenticated. Please login or provide a valid API key."
}

// 401: Token expired
{
  "detail": "Token has expired. Please login again."
}

// 401: Invalid API key
{
  "detail": "Not authenticated. Please login or provide a valid API key."
}

// 403: Insufficient permissions
{
  "detail": "Admin access required. Your role: developer"
}

// 401: Localhost mode limitation
{
  "detail": "This endpoint requires authentication (not available in localhost mode)"
}
```

### Validation Errors

```json
// 422: Field validation failed
{
  "detail": [
    {
      "loc": ["body", "password"],
      "msg": "ensure this value has at least 8 characters",
      "type": "value_error.any_str.min_length"
    }
  ]
}
```

---

## Rate Limiting

**Status:** Configured in `config.yaml` but enforcement varies by deployment.

**Default Limits:**
```yaml
security:
  rate_limiting:
    enabled: true
    requests_per_minute: 60
```

**Rate Limit Headers:**
```
X-RateLimit-Limit: 60
X-RateLimit-Remaining: 42
X-RateLimit-Reset: 1696809600
```

**Rate Limit Exceeded:**
```json
// 429: Too Many Requests
{
  "detail": "Rate limit exceeded. Try again in 30 seconds."
}
```

---

## Endpoints

### POST /api/auth/login

Authenticate with username and password, returns JWT in httpOnly cookie.

**Authentication:** None required

**Request Body:**
```json
{
  "username": "admin",
  "password": "password123"
}
```

**Request Schema:**
| Field | Type | Required | Constraints |
|-------|------|----------|-------------|
| username | string | Yes | 3-64 characters |
| password | string | Yes | Min 8 characters |

**Success Response (200):**
```json
{
  "message": "Login successful",
  "username": "admin",
  "role": "admin",
  "tenant_key": "default"
}
```

**Response Headers:**
```
Set-Cookie: access_token=eyJhbGciOiJIUzI1NiIsInR5cCI6IkpXVCJ9...; HttpOnly; Path=/; SameSite=Lax; Max-Age=86400
```

**Error Responses:**

```json
// 401: Invalid credentials
{
  "detail": "Invalid credentials"
}

// 401: Inactive user
{
  "detail": "Invalid credentials"
}

// 422: Validation error
{
  "detail": [
    {
      "loc": ["body", "username"],
      "msg": "field required",
      "type": "value_error.missing"
    }
  ]
}
```

**Example:**

```bash
curl -X POST http://localhost:7272/api/auth/login \
  -H "Content-Type: application/json" \
  -d '{"username":"admin","password":"pass123"}' \
  -c cookies.txt
```

```python
import httpx

response = httpx.post(
    "http://localhost:7272/api/auth/login",
    json={"username": "admin", "password": "pass123"}
)
cookies = response.cookies
print(response.json())
```

---

### POST /api/auth/logout

Clear JWT cookie to log out.

**Authentication:** None required (but typically called when logged in)

**Request Body:** None

**Success Response (200):**
```json
{
  "message": "Logout successful"
}
```

**Response Headers:**
```
Set-Cookie: access_token=; Max-Age=0; Path=/
```

**Example:**

```bash
curl -X POST http://localhost:7272/api/auth/logout \
  -b cookies.txt
```

```python
response = httpx.post(
    "http://localhost:7272/api/auth/logout",
    cookies=cookies
)
print(response.json())
```

---

### GET /api/auth/me

Get current authenticated user's profile.

**Authentication:** JWT cookie required

**Query Parameters:** None

**Success Response (200):**
```json
{
  "id": "550e8400-e29b-41d4-a716-446655440000",
  "username": "admin",
  "email": "admin@example.com",
  "full_name": "System Administrator",
  "role": "admin",
  "tenant_key": "default",
  "is_active": true,
  "created_at": "2025-10-07T10:00:00Z",
  "last_login": "2025-10-07T15:30:00Z"
}
```

**Response Schema:**
| Field | Type | Description |
|-------|------|-------------|
| id | string (UUID) | User's unique identifier |
| username | string | Username (login name) |
| email | string | Email address (nullable) |
| full_name | string | Full name (nullable) |
| role | string | User role (admin/developer/viewer) |
| tenant_key | string | Tenant isolation key |
| is_active | boolean | Account active status |
| created_at | string (ISO 8601) | Account creation timestamp |
| last_login | string (ISO 8601) | Last login timestamp (nullable) |

**Error Responses:**

```json
// 401: Not authenticated
{
  "detail": "Not authenticated. Please login or provide a valid API key."
}

// 401: Token expired
{
  "detail": "Token has expired. Please login again."
}
```

**Example:**

```bash
curl -X GET http://localhost:7272/api/auth/me \
  -b cookies.txt
```

```python
response = httpx.get(
    "http://localhost:7272/api/auth/me",
    cookies=cookies
)
print(response.json())
```

---

### GET /api/auth/api-keys

List all API keys for current user (masked for security).

**Authentication:** JWT cookie required

**Query Parameters:** None

**Success Response (200):**
```json
[
  {
    "id": "660e8400-e29b-41d4-a716-446655440000",
    "name": "MCP Claude Desktop",
    "key_prefix": "gk_xJ4kL9mN...",
    "permissions": ["*"],
    "is_active": true,
    "created_at": "2025-10-05T08:00:00Z",
    "last_used": "2025-10-07T14:22:00Z",
    "revoked_at": null
  },
  {
    "id": "770e8400-e29b-41d4-a716-446655440001",
    "name": "CI/CD Pipeline",
    "key_prefix": "gk_pQ7rS8tU...",
    "permissions": ["projects:read", "tasks:write"],
    "is_active": false,
    "created_at": "2025-09-20T12:00:00Z",
    "last_used": "2025-10-01T09:15:00Z",
    "revoked_at": "2025-10-02T10:00:00Z"
  }
]
```

**Response Schema:**
| Field | Type | Description |
|-------|------|-------------|
| id | string (UUID) | API key's unique identifier |
| name | string | Descriptive label |
| key_prefix | string | First 12 chars (masked: `gk_abc...`) |
| permissions | array[string] | Granted permissions |
| is_active | boolean | Active status |
| created_at | string (ISO 8601) | Creation timestamp |
| last_used | string (ISO 8601) | Last authentication (nullable) |
| revoked_at | string (ISO 8601) | Revocation timestamp (nullable) |

**Note:** Full API key is NEVER returned after creation.

**Error Responses:**

```json
// 401: Not authenticated
{
  "detail": "Not authenticated. Please login or provide a valid API key."
}
```

**Example:**

```bash
curl -X GET http://localhost:7272/api/auth/api-keys \
  -b cookies.txt
```

```python
response = httpx.get(
    "http://localhost:7272/api/auth/api-keys",
    cookies=cookies
)
print(response.json())
```

---

### POST /api/auth/api-keys

Generate a new API key for current user.

**Authentication:** JWT cookie required

**Request Body:**
```json
{
  "name": "MCP Claude Desktop",
  "permissions": ["*"]
}
```

**Request Schema:**
| Field | Type | Required | Default | Constraints |
|-------|------|----------|---------|-------------|
| name | string | Yes | - | 3-255 characters, descriptive label |
| permissions | array[string] | No | `["*"]` | List of permissions |

**Success Response (201):**
```json
{
  "id": "660e8400-e29b-41d4-a716-446655440000",
  "name": "MCP Claude Desktop",
  "api_key": "gk_xJ4kL9mN2pQ7rS8tU1vW3xY5zAbCdEfGhIjKlMnOpQrStUvWxYz",
  "key_prefix": "gk_xJ4kL9mN...",
  "message": "API key created successfully. Store this key securely - it will not be shown again!"
}
```

**⚠️ CRITICAL:** The `api_key` field contains the full plaintext key and is shown **ONLY ONCE**. Store it securely immediately.

**Response Schema:**
| Field | Type | Description |
|-------|------|-------------|
| id | string (UUID) | New API key's identifier |
| name | string | Your provided label |
| api_key | string | **Full plaintext key (shown once)** |
| key_prefix | string | Display prefix for future reference |
| message | string | Warning to store key securely |

**Error Responses:**

```json
// 401: Not authenticated
{
  "detail": "Not authenticated. Please login or provide a valid API key."
}

// 422: Validation error
{
  "detail": [
    {
      "loc": ["body", "name"],
      "msg": "ensure this value has at least 3 characters",
      "type": "value_error.any_str.min_length"
    }
  ]
}
```

**Example:**

```bash
curl -X POST http://localhost:7272/api/auth/api-keys \
  -H "Content-Type: application/json" \
  -b cookies.txt \
  -d '{"name":"MCP Claude Desktop","permissions":["*"]}'
```

```python
response = httpx.post(
    "http://localhost:7272/api/auth/api-keys",
    json={"name": "MCP Claude Desktop", "permissions": ["*"]},
    cookies=cookies
)
data = response.json()
api_key = data["api_key"]  # STORE THIS SECURELY!
print(f"Generated API key: {api_key}")
```

---

### DELETE /api/auth/api-keys/{id}

Revoke an API key (makes it inactive).

**Authentication:** JWT cookie required

**Path Parameters:**
| Parameter | Type | Description |
|-----------|------|-------------|
| id | UUID | API key ID to revoke |

**Request Body:** None

**Success Response (200):**
```json
{
  "id": "660e8400-e29b-41d4-a716-446655440000",
  "name": "MCP Claude Desktop",
  "message": "API key revoked successfully"
}
```

**Response Schema:**
| Field | Type | Description |
|-------|------|-------------|
| id | string (UUID) | Revoked key's identifier |
| name | string | Key's descriptive label |
| message | string | Confirmation message |

**Effects:**
- `is_active` set to `false`
- `revoked_at` timestamp recorded
- Key stops working immediately
- Cannot be un-revoked (create new key if needed)

**Error Responses:**

```json
// 404: Key not found or access denied
{
  "detail": "API key not found or access denied"
}

// 401: Not authenticated
{
  "detail": "Not authenticated. Please login or provide a valid API key."
}
```

**Example:**

```bash
curl -X DELETE http://localhost:7272/api/auth/api-keys/660e8400-e29b-41d4-a716-446655440000 \
  -b cookies.txt
```

```python
key_id = "660e8400-e29b-41d4-a716-446655440000"
response = httpx.delete(
    f"http://localhost:7272/api/auth/api-keys/{key_id}",
    cookies=cookies
)
print(response.json())
```

---

### POST /api/auth/register

Create a new user account (admin only).

**Authentication:** JWT cookie required (admin role)

**Request Body:**
```json
{
  "username": "newuser",
  "password": "secure_password123",
  "email": "newuser@example.com",
  "full_name": "New User",
  "role": "developer",
  "tenant_key": "default"
}
```

**Request Schema:**
| Field | Type | Required | Default | Constraints |
|-------|------|----------|---------|-------------|
| username | string | Yes | - | 3-64 chars, unique |
| password | string | Yes | - | Min 8 characters |
| email | string (email) | No | null | Valid email, unique if provided |
| full_name | string | No | null | Any string |
| role | string | No | "developer" | One of: admin, developer, viewer |
| tenant_key | string | No | "default" | Tenant isolation key |

**Success Response (201):**
```json
{
  "id": "880e8400-e29b-41d4-a716-446655440002",
  "username": "newuser",
  "email": "newuser@example.com",
  "role": "developer",
  "tenant_key": "default",
  "message": "User registered successfully"
}
```

**Response Schema:**
| Field | Type | Description |
|-------|------|-------------|
| id | string (UUID) | New user's identifier |
| username | string | Username |
| email | string | Email address (nullable) |
| role | string | Assigned role |
| tenant_key | string | Tenant key |
| message | string | Success message |

**Error Responses:**

```json
// 403: Not admin
{
  "detail": "Admin access required. Your role: developer"
}

// 400: Username exists
{
  "detail": "Username 'newuser' already exists"
}

// 400: Email exists
{
  "detail": "Email 'newuser@example.com' already exists"
}

// 422: Validation error
{
  "detail": [
    {
      "loc": ["body", "role"],
      "msg": "Role must be one of: admin, developer, viewer",
      "type": "value_error"
    }
  ]
}
```

**Example:**

```bash
curl -X POST http://localhost:7272/api/auth/register \
  -H "Content-Type: application/json" \
  -b cookies.txt \
  -d '{
    "username":"newuser",
    "password":"secure_pass123",
    "email":"newuser@example.com",
    "role":"developer"
  }'
```

```python
response = httpx.post(
    "http://localhost:7272/api/auth/register",
    json={
        "username": "newuser",
        "password": "secure_pass123",
        "email": "newuser@example.com",
        "full_name": "New User",
        "role": "developer"
    },
    cookies=cookies  # Must be admin user
)
print(response.json())
```

---

## Code Examples

### Complete Authentication Flow (Python)

```python
import httpx

BASE_URL = "http://localhost:7272"

# 1. Login
response = httpx.post(
    f"{BASE_URL}/api/auth/login",
    json={"username": "admin", "password": "password123"}
)
cookies = response.cookies
print(f"Logged in as: {response.json()['username']}")

# 2. Get user profile
response = httpx.get(f"{BASE_URL}/api/auth/me", cookies=cookies)
user = response.json()
print(f"User: {user['username']} ({user['role']})")

# 3. Generate API key
response = httpx.post(
    f"{BASE_URL}/api/auth/api-keys",
    json={"name": "My API Key", "permissions": ["*"]},
    cookies=cookies
)
api_key = response.json()["api_key"]
print(f"API Key: {api_key}")

# 4. Use API key for authenticated request
response = httpx.get(
    f"{BASE_URL}/api/projects",
    headers={"X-API-Key": api_key}
)
projects = response.json()
print(f"Projects: {len(projects)}")

# 5. List all API keys
response = httpx.get(f"{BASE_URL}/api/auth/api-keys", cookies=cookies)
keys = response.json()
print(f"Total keys: {len(keys)}")

# 6. Revoke API key
key_id = keys[0]["id"]
response = httpx.delete(
    f"{BASE_URL}/api/auth/api-keys/{key_id}",
    cookies=cookies
)
print(response.json()["message"])

# 7. Logout
response = httpx.post(f"{BASE_URL}/api/auth/logout", cookies=cookies)
print(response.json()["message"])
```

### JavaScript/TypeScript Example

```javascript
const BASE_URL = 'http://localhost:7272';

// 1. Login
const loginResponse = await fetch(`${BASE_URL}/api/auth/login`, {
  method: 'POST',
  headers: { 'Content-Type': 'application/json' },
  credentials: 'include',  // Include cookies
  body: JSON.stringify({ username: 'admin', password: 'password123' })
});
const loginData = await loginResponse.json();
console.log(`Logged in as: ${loginData.username}`);

// 2. Get user profile
const meResponse = await fetch(`${BASE_URL}/api/auth/me`, {
  credentials: 'include'
});
const user = await meResponse.json();
console.log(`User: ${user.username} (${user.role})`);

// 3. Generate API key
const keyResponse = await fetch(`${BASE_URL}/api/auth/api-keys`, {
  method: 'POST',
  headers: { 'Content-Type': 'application/json' },
  credentials: 'include',
  body: JSON.stringify({ name: 'My API Key', permissions: ['*'] })
});
const { api_key } = await keyResponse.json();
console.log(`API Key: ${api_key}`);
// STORE THIS SECURELY!

// 4. Use API key
const projectsResponse = await fetch(`${BASE_URL}/api/projects`, {
  headers: { 'X-API-Key': api_key }
});
const projects = await projectsResponse.json();
console.log(`Projects: ${projects.length}`);

// 5. Logout
await fetch(`${BASE_URL}/api/auth/logout`, {
  method: 'POST',
  credentials: 'include'
});
console.log('Logged out');
```

### cURL Examples

```bash
# Login
curl -X POST http://localhost:7272/api/auth/login \
  -H "Content-Type: application/json" \
  -d '{"username":"admin","password":"password123"}' \
  -c cookies.txt

# Get user profile
curl http://localhost:7272/api/auth/me -b cookies.txt

# Generate API key
curl -X POST http://localhost:7272/api/auth/api-keys \
  -H "Content-Type: application/json" \
  -d '{"name":"My Key","permissions":["*"]}' \
  -b cookies.txt

# Use API key
curl http://localhost:7272/api/projects \
  -H "X-API-Key: gk_your_key_here"

# Revoke API key
curl -X DELETE http://localhost:7272/api/auth/api-keys/KEY_UUID \
  -b cookies.txt

# Logout
curl -X POST http://localhost:7272/api/auth/logout -b cookies.txt
```

---

## Additional Resources

- **[User Guide](LAN_AUTH_USER_GUIDE.md)** - End-user documentation
- **[Architecture](LAN_AUTH_ARCHITECTURE.md)** - Technical deep dive
- **[Deployment Checklist](LAN_AUTH_DEPLOYMENT_CHECKLIST.md)** - Production setup
- **[Interactive Docs](http://localhost:7272/docs)** - Try the API live

---

**Document Version:** 1.0.0
**Last Updated:** 2025-10-07
**Maintained By:** Documentation Manager Agent
