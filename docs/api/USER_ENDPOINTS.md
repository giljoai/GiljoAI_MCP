# User Management API Reference

**Version:** 1.0.0
**Last Updated:** 2025-10-08
**Base URL:** `http://YOUR_SERVER_IP:7272/api`

---

## Table of Contents

1. [Overview](#overview)
2. [Authentication](#authentication)
3. [Common Response Codes](#common-response-codes)
4. [Endpoints](#endpoints)
   - [List Users](#list-users)
   - [Create User](#create-user)
   - [Get User](#get-user)
   - [Update User](#update-user)
   - [Delete User (Deactivate)](#delete-user-deactivate)
   - [Change User Role](#change-user-role)
   - [Change Password](#change-password)
5. [Data Models](#data-models)
6. [Multi-Tenant Notes](#multi-tenant-notes)
7. [Error Handling](#error-handling)

---

## Overview

The User Management API provides complete CRUD operations for user accounts in LAN/WAN deployment modes. All endpoints enforce role-based access control and multi-tenant isolation.

**Key Features**:
- Admin-only user creation and role management
- Self-service profile updates
- Secure password changes with verification
- Soft-delete (deactivation) for audit trail
- Multi-tenant data isolation

**Base URL**: `http://YOUR_SERVER_IP:7272/api`

**API Prefix**: All user endpoints are under `/api/users/`

---

## Authentication

All user management endpoints require authentication using one of these methods:

### Method 1: JWT Cookie (Web Dashboard)

Obtained via `/api/auth/login`. Set automatically in httpOnly cookie.

**Example**:
```bash
# Login first to get cookie
curl -X POST http://YOUR_SERVER_IP:7272/api/auth/login \
  -H "Content-Type: application/json" \
  -d '{"username": "admin", "password": "password"}' \
  -c cookies.txt

# Use cookie for authenticated request
curl http://YOUR_SERVER_IP:7272/api/users/ \
  -b cookies.txt
```

### Method 2: API Key Header (Programmatic Access)

Generate API key via dashboard or `/api/auth/api-keys` endpoint.

**Example**:
```bash
curl http://YOUR_SERVER_IP:7272/api/users/ \
  -H "X-API-Key: gk_your_api_key_here"
```

### Authorization Levels

| Endpoint | Required Role | Can Access |
|----------|---------------|------------|
| `GET /users/` | Admin | All users in tenant |
| `POST /users/` | Admin | Create any user |
| `GET /users/{id}` | Admin or Self | Admin: any user, Self: own profile |
| `PUT /users/{id}` | Admin or Self | Admin: any user, Self: own profile |
| `DELETE /users/{id}` | Admin | Any user in tenant |
| `PUT /users/{id}/role` | Admin | Any user except self |
| `PUT /users/{id}/password` | Admin or Self | Admin: any user, Self: own password |

---

## Common Response Codes

| Code | Meaning | When Used |
|------|---------|-----------|
| `200` | OK | Successful GET, PUT, DELETE |
| `201` | Created | Successful POST (user created) |
| `400` | Bad Request | Invalid input, validation error |
| `401` | Unauthorized | Not authenticated (no token/key) |
| `403` | Forbidden | Authenticated but insufficient permissions |
| `404` | Not Found | User not found or in different tenant |
| `500` | Internal Server Error | Database error, unexpected failure |

---

## Endpoints

### List Users

**GET** `/api/users/`

Lists all users in the current tenant. Admin only.

#### Request

**Headers**:
```
X-API-Key: gk_your_admin_api_key
# OR
Cookie: access_token=your_jwt_token
```

**Query Parameters**: None

#### Response

**200 OK**:
```json
[
  {
    "id": "550e8400-e29b-41d4-a716-446655440000",
    "username": "admin",
    "email": "admin@example.com",
    "full_name": "System Administrator",
    "role": "admin",
    "tenant_key": "default",
    "is_active": true,
    "created_at": "2025-10-01T10:00:00Z",
    "last_login": "2025-10-08T09:30:00Z"
  },
  {
    "id": "660e8400-e29b-41d4-a716-446655440001",
    "username": "jsmith",
    "email": "jsmith@example.com",
    "full_name": "John Smith",
    "role": "developer",
    "tenant_key": "default",
    "is_active": true,
    "created_at": "2025-10-05T14:22:00Z",
    "last_login": "2025-10-08T08:15:00Z"
  }
]
```

**403 Forbidden** (non-admin):
```json
{
  "detail": "Admin role required"
}
```

#### cURL Example

```bash
curl http://YOUR_SERVER_IP:7272/api/users/ \
  -H "X-API-Key: gk_admin_api_key"
```

#### Notes

- Returns users filtered by `tenant_key` (multi-tenant isolation)
- Ordered by `created_at` ascending (oldest first)
- Passwords are never included in response
- Non-admin users cannot access this endpoint

---

### Create User

**POST** `/api/users/`

Creates a new user account. Admin only.

#### Request

**Headers**:
```
Content-Type: application/json
X-API-Key: gk_your_admin_api_key
```

**Body** (JSON):
```json
{
  "username": "jsmith",
  "email": "jsmith@example.com",
  "full_name": "John Smith",
  "password": "SecurePassword123!",
  "role": "developer",
  "is_active": true
}
```

**Field Validation**:

| Field | Required | Type | Validation |
|-------|----------|------|------------|
| `username` | ✅ | string | 3-64 chars, alphanumeric + underscore, globally unique |
| `email` | ❌ | string | Valid email format, unique if provided |
| `full_name` | ❌ | string | Max 255 chars |
| `password` | ✅ | string | Min 8 chars (recommend 12+) |
| `role` | ✅ | string | One of: `admin`, `developer`, `viewer` |
| `is_active` | ❌ | boolean | Default: `true` |

#### Response

**201 Created**:
```json
{
  "id": "660e8400-e29b-41d4-a716-446655440001",
  "username": "jsmith",
  "email": "jsmith@example.com",
  "full_name": "John Smith",
  "role": "developer",
  "tenant_key": "default",
  "is_active": true,
  "created_at": "2025-10-08T10:30:00Z",
  "last_login": null
}
```

**400 Bad Request** (username exists):
```json
{
  "detail": "Username 'jsmith' already exists"
}
```

**400 Bad Request** (email exists):
```json
{
  "detail": "Email 'jsmith@example.com' already exists"
}
```

**400 Bad Request** (invalid role):
```json
{
  "detail": "Role must be one of: admin, developer, viewer"
}
```

**403 Forbidden** (non-admin):
```json
{
  "detail": "Admin role required"
}
```

#### cURL Example

```bash
curl -X POST http://YOUR_SERVER_IP:7272/api/users/ \
  -H "Content-Type: application/json" \
  -H "X-API-Key: gk_admin_api_key" \
  -d '{
    "username": "jsmith",
    "email": "jsmith@example.com",
    "full_name": "John Smith",
    "password": "SecurePassword123!",
    "role": "developer",
    "is_active": true
  }'
```

#### Notes

- New user inherits `tenant_key` from admin creator
- Password is hashed with bcrypt (cost 12) before storage
- Username is globally unique across all tenants
- Email is optional but must be unique if provided
- Default role is `developer` if not specified

---

### Get User

**GET** `/api/users/{user_id}`

Retrieves user details by ID. Admin can view any user, non-admin can only view self.

#### Request

**Headers**:
```
X-API-Key: gk_your_api_key
```

**Path Parameters**:
- `user_id` (UUID): User ID to retrieve

**Example URL**:
```
GET /api/users/550e8400-e29b-41d4-a716-446655440000
```

#### Response

**200 OK**:
```json
{
  "id": "550e8400-e29b-41d4-a716-446655440000",
  "username": "jsmith",
  "email": "jsmith@example.com",
  "full_name": "John Smith",
  "role": "developer",
  "tenant_key": "default",
  "is_active": true,
  "created_at": "2025-10-05T14:22:00Z",
  "last_login": "2025-10-08T08:15:00Z"
}
```

**403 Forbidden** (non-admin viewing other user):
```json
{
  "detail": "Cannot view other users' profiles"
}
```

**404 Not Found** (user not in tenant or doesn't exist):
```json
{
  "detail": "User not found"
}
```

#### cURL Example

```bash
curl http://YOUR_SERVER_IP:7272/api/users/550e8400-e29b-41d4-a716-446655440000 \
  -H "X-API-Key: gk_your_api_key"
```

#### Notes

- User ID must be valid UUID format
- Multi-tenant isolation: cannot access users from other tenants
- Authorization: admin can view any user, non-admin can only view self
- Password is never included in response

---

### Update User

**PUT** `/api/users/{user_id}`

Updates user profile. Admin can update any user, non-admin can only update self.

#### Request

**Headers**:
```
Content-Type: application/json
X-API-Key: gk_your_api_key
```

**Path Parameters**:
- `user_id` (UUID): User ID to update

**Body** (JSON, all fields optional):
```json
{
  "email": "newemail@example.com",
  "full_name": "Updated Name",
  "is_active": true
}
```

**Updatable Fields**:

| Field | Admin Can Update | User Can Update Self |
|-------|------------------|----------------------|
| `email` | ✅ | ✅ |
| `full_name` | ✅ | ✅ |
| `is_active` | ✅ | ❌ |

**Non-Updatable Fields**:
- `username` (immutable)
- `password` (use `/password` endpoint)
- `role` (use `/role` endpoint)
- `tenant_key` (immutable)

#### Response

**200 OK**:
```json
{
  "id": "550e8400-e29b-41d4-a716-446655440000",
  "username": "jsmith",
  "email": "newemail@example.com",
  "full_name": "Updated Name",
  "role": "developer",
  "tenant_key": "default",
  "is_active": true,
  "created_at": "2025-10-05T14:22:00Z",
  "last_login": "2025-10-08T08:15:00Z"
}
```

**400 Bad Request** (email exists):
```json
{
  "detail": "Email 'newemail@example.com' already exists"
}
```

**403 Forbidden** (non-admin updating other user):
```json
{
  "detail": "Cannot update other users' profiles"
}
```

**404 Not Found**:
```json
{
  "detail": "User not found"
}
```

#### cURL Example

```bash
curl -X PUT http://YOUR_SERVER_IP:7272/api/users/550e8400-e29b-41d4-a716-446655440000 \
  -H "Content-Type: application/json" \
  -H "X-API-Key: gk_your_api_key" \
  -d '{
    "email": "newemail@example.com",
    "full_name": "Updated Name"
  }'
```

#### Notes

- Only provided fields are updated (partial update)
- Email uniqueness is validated if changing email
- Non-admin users cannot change `is_active` status
- Returns updated user object

---

### Delete User (Deactivate)

**DELETE** `/api/users/{user_id}`

Soft-deletes user by setting `is_active = false`. Admin only.

#### Request

**Headers**:
```
X-API-Key: gk_admin_api_key
```

**Path Parameters**:
- `user_id` (UUID): User ID to deactivate

#### Response

**200 OK**:
```json
{
  "message": "User deactivated successfully",
  "user_id": "550e8400-e29b-41d4-a716-446655440000",
  "username": "jsmith"
}
```

**403 Forbidden** (non-admin):
```json
{
  "detail": "Admin role required"
}
```

**404 Not Found**:
```json
{
  "detail": "User not found"
}
```

#### cURL Example

```bash
curl -X DELETE http://YOUR_SERVER_IP:7272/api/users/550e8400-e29b-41d4-a716-446655440000 \
  -H "X-API-Key: gk_admin_api_key"
```

#### Notes

- This is a **soft delete** (sets `is_active = false`)
- User record is preserved for audit trail
- User cannot log in after deactivation
- Existing API keys stop working immediately
- User can be reactivated using `PUT /users/{id}` with `is_active: true`
- Hard deletion requires direct database access (not exposed via API)

---

### Change User Role

**PUT** `/api/users/{user_id}/role`

Changes user's role. Admin only. Cannot change own role.

#### Request

**Headers**:
```
Content-Type: application/json
X-API-Key: gk_admin_api_key
```

**Path Parameters**:
- `user_id` (UUID): User ID to change role

**Body** (JSON):
```json
{
  "role": "admin"
}
```

**Valid Roles**:
- `admin`
- `developer`
- `viewer`

#### Response

**200 OK**:
```json
{
  "message": "User role updated successfully",
  "user_id": "550e8400-e29b-41d4-a716-446655440000",
  "username": "jsmith",
  "role": "admin"
}
```

**400 Bad Request** (admin changing own role):
```json
{
  "detail": "You cannot change your own role (prevents lockout)"
}
```

**400 Bad Request** (invalid role):
```json
{
  "detail": "Role must be one of: admin, developer, viewer"
}
```

**403 Forbidden** (non-admin):
```json
{
  "detail": "Admin role required"
}
```

**404 Not Found**:
```json
{
  "detail": "User not found"
}
```

#### cURL Example

```bash
curl -X PUT http://YOUR_SERVER_IP:7272/api/users/550e8400-e29b-41d4-a716-446655440000/role \
  -H "Content-Type: application/json" \
  -H "X-API-Key: gk_admin_api_key" \
  -d '{
    "role": "admin"
  }'
```

#### Notes

- Admin cannot change their own role (security protection)
- Prevents accidental admin lockout scenarios
- Role change takes effect immediately
- User's permissions change on next request
- Ensure at least one active admin exists per tenant

---

### Change Password

**PUT** `/api/users/{user_id}/password`

Changes user password. Users can change own password (with verification). Admins can reset any password (no verification required).

#### Request

**Headers**:
```
Content-Type: application/json
X-API-Key: gk_your_api_key
```

**Path Parameters**:
- `user_id` (UUID): User ID to change password

**Body (User Changing Own Password)**:
```json
{
  "old_password": "CurrentPassword123!",
  "new_password": "NewSecurePassword456!"
}
```

**Body (Admin Resetting User Password)**:
```json
{
  "new_password": "AdminResetPassword789!"
}
```

**Field Requirements**:

| Field | User Changing Self | Admin Resetting User |
|-------|-------------------|----------------------|
| `old_password` | ✅ Required | ❌ Not required |
| `new_password` | ✅ Required (min 8 chars) | ✅ Required (min 8 chars) |

#### Response

**200 OK**:
```json
{
  "message": "Password updated successfully"
}
```

**400 Bad Request** (old password required):
```json
{
  "detail": "Current password is required to change your password"
}
```

**400 Bad Request** (old password incorrect):
```json
{
  "detail": "Current password is incorrect"
}
```

**403 Forbidden** (non-admin changing other user's password):
```json
{
  "detail": "Cannot change other users' passwords"
}
```

**404 Not Found**:
```json
{
  "detail": "User not found"
}
```

#### cURL Example (User Changing Own)

```bash
curl -X PUT http://YOUR_SERVER_IP:7272/api/users/550e8400-e29b-41d4-a716-446655440000/password \
  -H "Content-Type: application/json" \
  -H "X-API-Key: gk_user_api_key" \
  -d '{
    "old_password": "CurrentPassword123!",
    "new_password": "NewSecurePassword456!"
  }'
```

#### cURL Example (Admin Reset)

```bash
curl -X PUT http://YOUR_SERVER_IP:7272/api/users/550e8400-e29b-41d4-a716-446655440000/password \
  -H "Content-Type: application/json" \
  -H "X-API-Key: gk_admin_api_key" \
  -d '{
    "new_password": "AdminResetPassword789!"
  }'
```

#### Notes

- Non-admin users must provide correct `old_password` to change their password
- Admin users can reset any password without knowing the old password
- All passwords are hashed with bcrypt (cost 12) before storage
- Password change invalidates active sessions (future feature)
- Recommend minimum 12 characters for strong passwords

---

## Data Models

### UserResponse

Response model for user data (password excluded).

```typescript
{
  id: string;              // UUID
  username: string;        // 3-64 chars, unique
  email: string | null;    // Optional email
  full_name: string | null;  // Optional display name
  role: "admin" | "developer" | "viewer";
  tenant_key: string;      // Multi-tenant isolation
  is_active: boolean;      // Account status
  created_at: string;      // ISO 8601 timestamp
  last_login: string | null;  // ISO 8601 timestamp or null
}
```

### UserCreate

Request model for creating users.

```typescript
{
  username: string;        // Required, 3-64 chars
  email?: string;          // Optional, valid email
  full_name?: string;      // Optional, max 255 chars
  password: string;        // Required, min 8 chars
  role: "admin" | "developer" | "viewer";  // Required
  is_active?: boolean;     // Optional, default: true
}
```

### UserUpdate

Request model for updating user profile.

```typescript
{
  email?: string;          // Optional, valid email
  full_name?: string;      // Optional, max 255 chars
  is_active?: boolean;     // Optional (admin only)
}
```

### PasswordChange

Request model for password change.

```typescript
{
  old_password?: string;   // Required for non-admin self-change
  new_password: string;    // Required, min 8 chars
}
```

### RoleChange

Request model for role change.

```typescript
{
  role: "admin" | "developer" | "viewer";  // Required
}
```

---

## Multi-Tenant Notes

All user endpoints enforce strict multi-tenant isolation:

### Tenant Key Filtering

- All queries automatically filter by `tenant_key`
- Users can only see/modify users in same tenant
- Tenant key inherited from admin on user creation
- Cannot be changed after creation

### Query Examples

```sql
-- List users (automatically filtered)
SELECT * FROM users WHERE tenant_key = 'default' ORDER BY created_at;

-- Get user (tenant isolation)
SELECT * FROM users WHERE id = '...' AND tenant_key = 'default';

-- Update user (tenant verification)
UPDATE users SET email = '...' WHERE id = '...' AND tenant_key = 'default';
```

### Cross-Tenant Access Prevention

- JWT tokens include `tenant_key` claim
- API keys linked to user's `tenant_key`
- All requests validate tenant membership
- 404 returned if user in different tenant (security through obscurity)

### Indexes for Performance

```sql
-- Primary indexes
CREATE INDEX idx_user_tenant ON users(tenant_key);
CREATE INDEX idx_user_username ON users(username);
CREATE INDEX idx_user_email ON users(email);
CREATE INDEX idx_user_active ON users(is_active);

-- Composite index for common query
CREATE INDEX idx_user_tenant_active ON users(tenant_key, is_active);
```

---

## Error Handling

### Standard Error Response

All errors return JSON with `detail` field:

```json
{
  "detail": "Human-readable error message"
}
```

### Common Error Scenarios

#### 400 Bad Request

**Causes**:
- Validation failure (invalid email, short password)
- Duplicate username or email
- Invalid role value
- Admin trying to change own role
- Incorrect current password

**Example**:
```json
{
  "detail": "Password must be at least 8 characters long"
}
```

#### 401 Unauthorized

**Causes**:
- No authentication provided (no cookie or API key)
- Invalid or expired JWT token
- Invalid or revoked API key

**Example**:
```json
{
  "detail": "Not authenticated"
}
```

#### 403 Forbidden

**Causes**:
- Authenticated but insufficient permissions
- Non-admin trying admin-only operation
- Non-admin trying to modify other users

**Example**:
```json
{
  "detail": "Admin role required"
}
```

#### 404 Not Found

**Causes**:
- User ID doesn't exist
- User exists but in different tenant (isolation)
- Malformed UUID

**Example**:
```json
{
  "detail": "User not found"
}
```

#### 500 Internal Server Error

**Causes**:
- Database connection failure
- Unexpected exception
- Configuration error

**Example**:
```json
{
  "detail": "Database connection failed"
}
```

### Error Handling Best Practices

**Client-Side**:
```javascript
try {
  const response = await fetch('/api/users/', {
    headers: { 'X-API-Key': apiKey }
  });

  if (!response.ok) {
    const error = await response.json();
    console.error(`API Error: ${error.detail}`);

    if (response.status === 401) {
      // Redirect to login
    } else if (response.status === 403) {
      // Show permission denied message
    } else if (response.status === 404) {
      // Show not found message
    }
  }

  const data = await response.json();
  // Process data...

} catch (error) {
  console.error('Network error:', error);
}
```

---

## Additional Resources

- **[User Management Guide](../guides/USER_MANAGEMENT.md)** - Comprehensive user management guide
- **[LAN Authentication User Guide](../LAN_AUTH_USER_GUIDE.md)** - Authentication and API keys
- **[LAN Authentication Architecture](../LAN_AUTH_ARCHITECTURE.md)** - Technical architecture
- **[Setup Wizard Guide](../guides/SETUP_WIZARD_GUIDE.md)** - First-time setup
- **[API Reference (General)](../guides/API_REFERENCE.md)** - Complete API documentation

---

**Document Version:** 1.0.0
**Last Updated:** 2025-10-08
**Maintained By:** Documentation Manager Agent
