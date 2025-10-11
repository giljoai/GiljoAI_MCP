# Network Authentication Architecture - GiljoAI MCP

**Version:** 2.0
**Date:** 2025-10-07
**Status:** Production Ready
**Scope:** All Network Deployment Modes (LAN, WAN, SaaS)

---

## Table of Contents

1. [Overview](#overview)
2. [Four Deployment Modes](#four-deployment-modes)
3. [Authentication Architecture by Mode](#authentication-architecture-by-mode)
4. [User Management](#user-management)
5. [API Key System](#api-key-system)
6. [Security Model](#security-model)
7. [Migration Paths](#migration-paths)
8. [Implementation Guide](#implementation-guide)
9. [MCP Tool Configuration](#mcp-tool-configuration)
10. [Troubleshooting](#troubleshooting)

---

## Overview

This document describes the authentication and authorization architecture for GiljoAI MCP across all deployment modes, from local development to global SaaS.

### Design Principles

**Security in Depth:**
- Multiple authentication layers
- Per-user access control and audit trails
- Revocable credentials at any level
- Principle of least privilege

**User Experience:**
- Single sign-on for web dashboard
- Personal API keys for tools/CLI
- Seamless mode transitions (localhost → LAN → WAN → SaaS)
- Clear separation between user auth and service auth

**Scalability:**
- Supports 1 to 100,000+ users
- Multi-tenancy ready (company/organization isolation)
- Efficient token management
- Horizontal scaling support

### Key Concepts

**User Account:** Individual identity with username/password for web dashboard access

**Personal API Key:** User-specific credential for MCP tools, CLI, and API access (multiple keys per user allowed)

**JWT Token:** Short-lived session token for web dashboard (stored in httpOnly cookies)

**Admin User:** Privileged account that can create/manage other users and system settings

**Tenant:** Organization/company isolation boundary (for multi-tenant SaaS mode)

---

## Four Deployment Modes

### Mode Comparison Matrix

| Feature | LOCALHOST | LAN | WAN | HOSTED/SaaS |
|---------|-----------|-----|-----|-------------|
| **Network Access** | 127.0.0.1 only | LAN/Subnet | Internet | Global Internet |
| **User Accounts** | ❌ No | ✅ Yes | ✅ Yes | ✅ Yes |
| **Authentication** | None | Username/Password + JWT | Username/Password + JWT | OAuth2 + Username/Password |
| **API Keys** | ❌ No | ✅ Personal (per-user) | ✅ Personal (per-user) | ✅ Personal + Service Keys |
| **Multi-Tenancy** | N/A | ❌ No | ❌ No | ✅ Yes (company isolation) |
| **Setup Method** | CLI Install | Setup Wizard | Setup Wizard + Manual | Automated Provisioning |
| **First User** | N/A | Admin (via wizard) | Admin (via wizard) | OAuth or Invite |
| **SSL/TLS** | ❌ Optional | ⚠️ Optional | ✅ Required | ✅ Required |
| **Typical Users** | 1 developer | 3-10 team | 10-1000 users | 1000+ users |

---

## Authentication Architecture by Mode

### 1. LOCALHOST MODE (Current - Complete)

**Status:** ✅ Production Ready
**Target:** Single-user development environment

#### Architecture

```
Developer Machine
├─ Server binds to 127.0.0.1
├─ No authentication required
├─ No API keys
├─ Single local user (implicit)
└─ Development environment only
```

#### Access Flow

```
User → Browser → http://localhost:7274
                    ↓
              No authentication check
                    ↓
              Full access granted
```

#### Security Model

- **Network Security:** localhost-only binding (no network exposure)
- **Physical Security:** Machine access = application access
- **Assumptions:** Single developer, trusted environment
- **Not Suitable For:** Any network deployment, multi-user, production

#### Configuration

```yaml
# config.yaml
installation:
  mode: localhost

services:
  api:
    host: 127.0.0.1  # Localhost only
    port: 7272

security:
  api_key_required: false
  user_accounts: false
```

---

### 2. LAN MODE (Updated - Auth Refactor)

**Status:** 🔧 In Development - New Architecture
**Target:** Local Area Network / Team environment (3-10 users)

#### Architecture

```
LAN Network (Trusted)
├─ Server binds to 0.0.0.0 (all interfaces)
├─ User accounts with username/password
├─ JWT tokens for web dashboard
├─ Personal API keys for MCP tools (per-user)
└─ Admin manages user accounts
```

#### NEW Authentication Flow

##### Web Dashboard Access (JWT-based)

```
User → https://lan-server:7274/login
         ├─ Enter username + password
         ├─ Backend validates credentials
         ├─ Issues JWT token (24h expiry)
         ├─ Stores JWT in httpOnly cookie
         └─ User authenticated

Subsequent Requests:
Browser → Dashboard (with JWT cookie)
           ├─ Middleware validates JWT
           ├─ Extracts user_id from token
           └─ Authorizes access
```

##### MCP Tool Access (API Key-based)

```
User → Requests personal API key from dashboard
        ├─ Settings → API Keys → Generate New Key
        ├─ Key format: gk_[user_id]_[random_32chars]
        ├─ Displayed ONCE (must save!)
        └─ Key stored hashed in database

MCP Tool Request:
Claude Code → MCP Tool → API Request
                           ├─ Header: X-API-Key: gk_abc123...
                           ├─ Backend validates key
                           ├─ Identifies user from key
                           └─ Authorizes request with user context
```

#### User Management

**First User Creation (Setup Wizard):**

```
Setup Wizard Step 3: Network Configuration
├─ Select "LAN" mode
├─ Auto-detect or enter server IP
├─ Create Admin Account
│   ├─ Username: admin (or custom)
│   ├─ Password: (strong password, bcrypt hashed)
│   └─ Email: (optional)
├─ Wizard completes
└─ Admin can now log in
```

**Additional Users (Admin Console):**

```
Admin Dashboard → Users → Add New User
├─ Enter username, email, password
├─ Assign role: Admin | Developer | Viewer
├─ User receives credentials
└─ User logs in → generates own API keys
```

#### Security Model

- **Authentication:** Username/password (bcrypt hashed, rounds=12)
- **Session Management:** JWT tokens (24h expiry, httpOnly cookies)
- **API Access:** Personal API keys (hashed, per-user, revocable)
- **Network:** Firewall-protected LAN, CORS restrictions
- **Audit:** Per-user action logging

#### Configuration

```yaml
# config.yaml (NEW for LAN auth refactor)
installation:
  mode: lan

services:
  api:
    host: 0.0.0.0  # Network accessible
    port: 7272

security:
  api_key_required: true
  user_accounts: true  # NEW
  jwt_auth: true       # NEW

  jwt:
    algorithm: HS256
    expiry_hours: 24
    secret_key: ${JWT_SECRET_KEY}  # From .env

  password:
    min_length: 12
    require_uppercase: true
    require_lowercase: true
    require_numbers: true
    require_special: true
    bcrypt_rounds: 12

  api_keys:
    format: "gk_{user_id}_{random}"
    max_per_user: 5
    rotation_days: 90  # Optional enforcement

  cors:
    allowed_origins:
      - http://10.1.0.118:7274  # Server IP
      - http://10.1.0.*:7274    # Subnet wildcard
```

#### Database Schema (NEW)

```sql
-- Users table
CREATE TABLE users (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    username VARCHAR(64) UNIQUE NOT NULL,
    email VARCHAR(255) UNIQUE,
    password_hash VARCHAR(255) NOT NULL,
    role VARCHAR(32) DEFAULT 'developer',  -- admin, developer, viewer
    created_at TIMESTAMP DEFAULT NOW(),
    last_login TIMESTAMP,
    is_active BOOLEAN DEFAULT true
);

-- API Keys table
CREATE TABLE api_keys (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    user_id UUID REFERENCES users(id) ON DELETE CASCADE,
    key_hash VARCHAR(255) UNIQUE NOT NULL,
    key_prefix VARCHAR(16) NOT NULL,  -- gk_abc123 (for user identification)
    name VARCHAR(128),  -- User-friendly name ("Laptop", "CI/CD")
    created_at TIMESTAMP DEFAULT NOW(),
    last_used TIMESTAMP,
    expires_at TIMESTAMP,  -- Optional expiry
    is_active BOOLEAN DEFAULT true
);

-- Audit log
CREATE TABLE audit_log (
    id BIGSERIAL PRIMARY KEY,
    user_id UUID REFERENCES users(id),
    action VARCHAR(64) NOT NULL,
    resource_type VARCHAR(64),
    resource_id VARCHAR(128),
    ip_address INET,
    user_agent TEXT,
    timestamp TIMESTAMP DEFAULT NOW(),
    details JSONB
);
```

---

### 3. WAN MODE (Future - Foundation in Place)

**Status:** 🔮 Planned - Auth Foundation Ready
**Target:** Internet-facing deployment (10-1000+ users)

#### Additional Features (vs LAN)

**Enhanced Security:**
- HTTPS/TLS mandatory (Let's Encrypt or commercial cert)
- Enhanced rate limiting (per-IP, per-user, per-endpoint)
- IP allowlisting/blocklisting (optional)
- DDoS protection (CloudFlare/AWS WAF)
- Security headers (HSTS, CSP, etc.)

**Authentication Enhancements:**
- Session fixation protection
- CSRF token protection
- Brute-force protection (account lockout)
- 2FA/MFA (optional, future)

**User Management:**
- Self-service registration (optional)
- Email verification required
- Password reset flow
- Account recovery

**Configuration:**

```yaml
# config.yaml (WAN mode)
installation:
  mode: wan

security:
  ssl_enabled: true
  ssl_cert: /path/to/cert.pem
  ssl_key: /path/to/key.pem

  rate_limiting:
    enabled: true
    auth_endpoint: "5/minute"
    api_endpoint: "100/minute"
    global: "1000/hour"

  session:
    cookie_secure: true  # HTTPS only
    cookie_samesite: "strict"
    csrf_protection: true
```

---

### 4. HOSTED/SaaS MODE (Future - Foundation in Place)

**Status:** 🔮 Planned - Multi-Tenant Ready
**Target:** Global SaaS offering (1000+ users, multiple companies)

#### Additional Features (vs WAN)

**Multi-Tenancy:**
- Company/Organization isolation (tenant_key)
- Separate databases or row-level security
- Cross-tenant access prevention

**OAuth2 Integration:**
- Google OAuth2
- GitHub OAuth2
- Microsoft OAuth2 / Azure AD
- Custom SAML/SSO

**Billing & Quotas:**
- Usage tracking per tenant
- API rate limits per plan
- Storage quotas
- Agent concurrency limits

**User Management:**
- Company admin (can manage company users)
- Invite-based user provisioning
- Role-based access control (RBAC)
- Team/project-based permissions

**Example OAuth2 Flow:**

```
User → Login Page → "Sign in with Google"
         ↓
    Google OAuth2 Flow
         ↓
    User grants permissions
         ↓
    Google redirects with auth code
         ↓
    Backend exchanges code for tokens
         ↓
    Backend creates/links user account
         ↓
    Issues JWT session token
         ↓
    User authenticated + redirected to dashboard
```

---

## User Management

### Admin User Creation (LAN/WAN)

**Method 1: Setup Wizard (Recommended)**

```
1. Navigate to: http://localhost:7274/setup (or https://server:7274/setup)
2. Complete wizard steps:
   - Step 1: Welcome
   - Step 2: Tool Attachment (optional MCP tools)
   - Step 3: Network Configuration
     → Select mode: LAN or WAN
     → Auto-detect server IP (or manual entry)
     → CREATE ADMIN ACCOUNT:
        - Username: [choose]
        - Password: [strong password, 12+ chars]
        - Email: [optional]
     → Confirm firewall settings
   - Step 4: Completion
     → Admin account created
     → Login credentials displayed
     → Restart services
3. Log in with admin credentials
4. Generate personal API keys in Settings → API Keys
```

**Method 2: CLI (Advanced)**

```bash
# Create first admin user via CLI
python scripts/create_admin_user.py \
  --username admin \
  --password "YourStrongPassword123!" \
  --email admin@company.com

# Output:
# ✅ Admin user created successfully
# Username: admin
# Login at: http://your-server:7274/login
```

### Creating Additional Users (Admin Console)

```
Admin Dashboard → Users Section
├─ Click "Add New User"
├─ Enter details:
│   ├─ Username: developer1
│   ├─ Email: dev1@company.com
│   ├─ Password: [generate strong or let user set]
│   ├─ Role: Developer (Admin, Developer, Viewer)
│   └─ Permissions: [select projects/resources]
├─ Click "Create User"
├─ User receives welcome email (if configured)
└─ User logs in → dashboard → generates API keys
```

### User Roles

| Role | Dashboard Access | Create Projects | Spawn Agents | Manage Users | System Settings |
|------|------------------|-----------------|--------------|--------------|-----------------|
| **Admin** | ✅ Full | ✅ Yes | ✅ Yes | ✅ Yes | ✅ Yes |
| **Developer** | ✅ Full | ✅ Yes | ✅ Yes | ❌ No | ❌ No |
| **Viewer** | ✅ Read-only | ❌ No | ❌ No | ❌ No | ❌ No |

---

## API Key System

### Personal API Keys (Per-User)

**Purpose:** Authenticate MCP tools, CLI scripts, CI/CD pipelines

**Format:** `gk_{user_id}_{random_32chars}`

Example: `gk_550e8400_7f3d2e1a9b8c4d6f1e2a3b5c7d9f0e1a`

**Generation:**

```
User Dashboard → Settings → API Keys
├─ Click "Generate New API Key"
├─ Enter key name: "Laptop" or "CI/CD Pipeline"
├─ Key generated and displayed ONCE
│   ├─ Key: gk_550e8400_7f3d2e1a9b8c4d6f1e2a3b5c7d9f0e1a
│   ├─ Created: 2025-10-07 14:23:15
│   └─ ⚠️ Save this key now! It won't be shown again.
├─ User copies key to secure location
└─ Key can be revoked anytime from dashboard
```

**Storage:**

- **User sees:** Full key (only during generation)
- **Database stores:** Hash of key (bcrypt/Argon2)
- **API requests include:** Full key in header
- **Backend validates:** Hash comparison

**Usage:**

```bash
# In MCP tool configuration (~/.claude.json)
{
  "mcpServers": {
    "giljo-mcp": {
      "command": "python",
      "args": ["-m", "giljo_mcp"],
      "env": {
        "GILJO_SERVER_URL": "http://lan-server:7272",
        "GILJO_API_KEY": "gk_550e8400_7f3d2e1a9b8c4d6f1e2a3b5c7d9f0e1a"
      }
    }
  }
}
```

```bash
# Or via environment variable
export GILJO_API_KEY=gk_550e8400_7f3d2e1a9b8c4d6f1e2a3b5c7d9f0e1a

# Or in .env file
GILJO_API_KEY=gk_550e8400_7f3d2e1a9b8c4d6f1e2a3b5c7d9f0e1a
```

**API Request:**

```bash
# Include API key in X-API-Key header
curl -H "X-API-Key: gk_550e8400_7f3d2e1a9b8c4d6f1e2a3b5c7d9f0e1a" \
     https://lan-server:7272/api/v1/projects
```

**Key Management:**

```
User Dashboard → Settings → API Keys
├─ List all keys:
│   ├─ "Laptop" - Created 2025-10-01 - Last used: 2 hours ago
│   ├─ "CI/CD" - Created 2025-09-15 - Last used: 1 day ago
│   └─ "Old Key" - Created 2025-08-01 - Last used: 30 days ago
├─ Actions:
│   ├─ View details (creation date, last used, request count)
│   ├─ Revoke key (immediate effect)
│   └─ Rotate key (generate new, deprecate old)
└─ Audit trail: All key usage logged
```

**Best Practices:**

- ✅ One key per device/environment ("Laptop", "Work Desktop", "CI/CD")
- ✅ Store keys in password manager or secrets vault
- ✅ Rotate keys every 90 days (or on compromise)
- ✅ Revoke unused keys
- ✅ Monitor key usage in dashboard
- ❌ Never commit keys to git
- ❌ Never share keys between users
- ❌ Never use same key across multiple environments

---

## Security Model

### Authentication Layers

**Layer 1: Network Security**
- Localhost: 127.0.0.1 binding (no network access)
- LAN: Firewall rules (ports 7272, 7274 on LAN only)
- WAN: HTTPS/TLS, WAF, DDoS protection

**Layer 2: User Authentication**
- Web Dashboard: Username/Password → JWT tokens
- API/MCP Tools: Personal API keys (per-user)

**Layer 3: Authorization**
- Role-based access control (Admin, Developer, Viewer)
- Per-user permissions (future: project-level access)
- Resource-level access control

**Layer 4: Audit & Monitoring**
- All user actions logged
- Failed authentication attempts tracked
- API key usage monitored
- Anomaly detection (future)

### Session Security

**JWT Token Structure:**

```json
{
  "header": {
    "alg": "HS256",
    "typ": "JWT"
  },
  "payload": {
    "sub": "user_id_here",
    "username": "admin",
    "role": "admin",
    "iat": 1696700000,
    "exp": 1696786400
  },
  "signature": "..."
}
```

**Token Lifecycle:**

```
User Login → JWT issued (24h expiry)
              ↓
          httpOnly cookie
              ↓
      Browser stores (secure)
              ↓
      Subsequent requests include cookie
              ↓
      Backend validates:
       ├─ Signature valid?
       ├─ Not expired?
       ├─ User still active?
       └─ Grant access
              ↓
      Token expires after 24h
              ↓
      User redirected to login
```

**Token Storage:**
- **Web Dashboard:** httpOnly cookies (no JavaScript access)
- **Security Flags:** Secure (HTTPS only), SameSite=Strict

**Token Refresh:**
- Short-lived tokens (24h)
- Silent refresh via refresh token (future)
- User re-authenticates on expiry

### Password Security

**Hashing:**
- Algorithm: bcrypt
- Cost factor: 12 rounds (balance security/performance)
- Salt: Unique per password (automatic with bcrypt)

**Requirements:**
- Minimum length: 12 characters
- Must include: uppercase, lowercase, number, special char
- Cannot be: common passwords, username variants

**Storage:**

```sql
-- Example password_hash value
users.password_hash = '$2b$12$eIJv3xKjD9lP6Q2R7sT8uO...'
                       ^   ^
                       |   |
                     bcrypt rounds=12
```

**Validation Flow:**

```
User submits password
    ↓
bcrypt.compare(submitted_password, stored_hash)
    ↓
Match? → Grant access
No match? → Deny + log attempt
```

---

## Migration Paths

### Localhost → LAN

**Step 1: Prepare**
```bash
# Backup localhost configuration
cp config.yaml config.yaml.localhost.backup
cp .env .env.localhost.backup

# Backup database
pg_dump -U postgres giljo_mcp > localhost_backup.sql
```

**Step 2: Run Setup Wizard**
```
Navigate to: http://localhost:7274/setup
→ Select "LAN" mode
→ Enter server IP
→ Create admin account:
   - Username: admin
   - Password: [strong password]
→ Complete wizard
```

**Step 3: Update Configuration**
```yaml
# config.yaml automatically updated by wizard
installation:
  mode: lan  # Changed from localhost

services:
  api:
    host: 0.0.0.0  # Changed from 127.0.0.1

security:
  user_accounts: true  # NEW
  jwt_auth: true  # NEW
```

**Step 4: Configure Firewall**
```bash
# Windows
netsh advfirewall firewall add rule name="GiljoAI MCP API" dir=in action=allow protocol=TCP localport=7272 profile=domain,private
netsh advfirewall firewall add rule name="GiljoAI MCP Dashboard" dir=in action=allow protocol=TCP localport=7274 profile=domain,private

# Linux
sudo ufw allow 7272/tcp
sudo ufw allow 7274/tcp
```

**Step 5: Restart & Test**
```bash
# Restart services
stop_giljo.bat && start_giljo.bat  # Windows
sudo systemctl restart giljo-mcp    # Linux

# Test from LAN device
curl http://lan-server-ip:7272/health

# Login via browser
http://lan-server-ip:7274/login
```

### LAN → WAN

**Key Changes:**
- Add HTTPS/TLS (mandatory)
- Configure reverse proxy (nginx/Caddy)
- Obtain domain name
- Obtain SSL certificate
- Enable enhanced rate limiting
- Add WAF/DDoS protection

**See:** `LAN_TO_WAN_MIGRATION.md` for detailed steps

### WAN → SaaS (Future)

**Key Changes:**
- Add OAuth2 providers
- Implement multi-tenancy (tenant_key isolation)
- Add billing/subscription management
- Implement usage quotas
- Add company/team management
- Deploy to multiple regions

---

## Implementation Guide

### Backend Implementation (Python/FastAPI)

**File Structure:**

```
src/giljo_mcp/
├─ auth/
│   ├─ __init__.py
│   ├─ user_manager.py      # User CRUD operations
│   ├─ password_manager.py  # Password hashing/validation
│   ├─ jwt_manager.py        # JWT token operations
│   ├─ api_key_manager.py    # API key generation/validation
│   └─ middleware.py         # Auth middleware for FastAPI
├─ models.py                 # SQLAlchemy models (User, APIKey)
└─ database.py               # Database connection
```

**Example: User Authentication Middleware**

```python
# src/giljo_mcp/auth/middleware.py
from fastapi import Request, HTTPException, Depends
from fastapi.security import HTTPBearer, HTTPAuthorizationCredentials
from jose import JWTError, jwt
from .jwt_manager import JWTManager
from .api_key_manager import APIKeyManager

security = HTTPBearer(auto_error=False)

async def get_current_user_jwt(request: Request):
    """Authenticate via JWT token (from cookie)"""
    token = request.cookies.get("session_token")
    if not token:
        raise HTTPException(status_code=401, detail="Not authenticated")

    try:
        payload = jwt.decode(token, settings.JWT_SECRET_KEY, algorithms=["HS256"])
        user_id = payload.get("sub")
        if not user_id:
            raise HTTPException(status_code=401, detail="Invalid token")

        # Fetch user from database
        user = await get_user_by_id(user_id)
        if not user or not user.is_active:
            raise HTTPException(status_code=401, detail="User inactive")

        return user
    except JWTError:
        raise HTTPException(status_code=401, detail="Invalid token")

async def get_current_user_api_key(credentials: HTTPAuthorizationCredentials = Depends(security)):
    """Authenticate via API key (from header)"""
    if not credentials:
        raise HTTPException(status_code=401, detail="API key required")

    api_key = credentials.credentials
    user = await APIKeyManager.validate_key(api_key)
    if not user:
        raise HTTPException(status_code=401, detail="Invalid API key")

    return user
```

**Example: Login Endpoint**

```python
# api/endpoints/auth.py
from fastapi import APIRouter, HTTPException, Response
from pydantic import BaseModel
from src.giljo_mcp.auth import PasswordManager, JWTManager

router = APIRouter()

class LoginRequest(BaseModel):
    username: str
    password: str

@router.post("/login")
async def login(request: LoginRequest, response: Response):
    # Validate credentials
    user = await get_user_by_username(request.username)
    if not user or not user.is_active:
        raise HTTPException(status_code=401, detail="Invalid credentials")

    # Verify password
    if not PasswordManager.verify_password(request.password, user.password_hash):
        # Log failed attempt
        await log_failed_login(user.id)
        raise HTTPException(status_code=401, detail="Invalid credentials")

    # Generate JWT token
    token = JWTManager.create_token(user_id=user.id, username=user.username, role=user.role)

    # Set httpOnly cookie
    response.set_cookie(
        key="session_token",
        value=token,
        httponly=True,
        secure=True,  # HTTPS only
        samesite="strict",
        max_age=86400  # 24 hours
    )

    # Update last login
    await update_last_login(user.id)

    return {"message": "Login successful", "user": {"username": user.username, "role": user.role}}
```

### Frontend Implementation (Vue 3)

**Login Page:**

```vue
<!-- frontend/src/views/Login.vue -->
<template>
  <v-container class="fill-height" fluid>
    <v-row align="center" justify="center">
      <v-col cols="12" sm="8" md="4">
        <v-card>
          <v-card-title>Login to GiljoAI MCP</v-card-title>
          <v-card-text>
            <v-form @submit.prevent="handleLogin">
              <v-text-field
                v-model="username"
                label="Username"
                required
                autofocus
              ></v-text-field>
              <v-text-field
                v-model="password"
                label="Password"
                type="password"
                required
              ></v-text-field>
              <v-btn type="submit" color="primary" block :loading="loading">
                Login
              </v-btn>
            </v-form>
          </v-card-text>
        </v-card>
      </v-col>
    </v-row>
  </v-container>
</template>

<script setup>
import { ref } from 'vue'
import { useRouter } from 'vue-router'
import api from '@/services/api'

const router = useRouter()
const username = ref('')
const password = ref('')
const loading = ref(false)

const handleLogin = async () => {
  loading.value = true
  try {
    const response = await api.post('/auth/login', {
      username: username.value,
      password: password.value
    })

    // JWT token stored in httpOnly cookie automatically
    router.push('/dashboard')
  } catch (error) {
    alert('Login failed: ' + error.message)
  } finally {
    loading.value = false
  }
}
</script>
```

**API Service (with cookie-based auth):**

```javascript
// frontend/src/services/api.js
import axios from 'axios'

const api = axios.create({
  baseURL: import.meta.env.VITE_API_URL || 'http://localhost:7272',
  withCredentials: true  // CRITICAL: Send cookies with requests
})

// Response interceptor (handle 401 unauthorized)
api.interceptors.response.use(
  response => response,
  error => {
    if (error.response?.status === 401) {
      // Redirect to login
      window.location.href = '/login'
    }
    return Promise.reject(error)
  }
)

export default api
```

---

## MCP Tool Configuration

### Claude Code CLI Configuration

**Location:** `~/.claude.json` or `C:\Users\<username>\.claude.json`

**With Personal API Key:**

```json
{
  "mcpServers": {
    "giljo-mcp": {
      "command": "F:\\GiljoAI_MCP\\venv\\Scripts\\python.exe",
      "args": ["-m", "giljo_mcp"],
      "env": {
        "GILJO_MCP_HOME": "F:/GiljoAI_MCP",
        "GILJO_SERVER_URL": "http://lan-server:7272",
        "GILJO_API_KEY": "gk_550e8400_7f3d2e1a9b8c4d6f1e2a3b5c7d9f0e1a"
      }
    }
  }
}
```

**For WAN deployment (HTTPS):**

```json
{
  "mcpServers": {
    "giljo-mcp": {
      "command": "python",
      "args": ["-m", "giljo_mcp"],
      "env": {
        "GILJO_SERVER_URL": "https://giljo.company.com",
        "GILJO_API_KEY": "gk_550e8400_7f3d2e1a9b8c4d6f1e2a3b5c7d9f0e1a"
      }
    }
  }
}
```

### MCP Tool API Client

**Python Example:**

```python
# Python client using personal API key
import os
import httpx

class GiljoMCPClient:
    def __init__(self):
        self.base_url = os.getenv("GILJO_SERVER_URL", "http://localhost:7272")
        self.api_key = os.getenv("GILJO_API_KEY")
        if not self.api_key:
            raise ValueError("GILJO_API_KEY environment variable required")

    def _headers(self):
        return {"X-API-Key": self.api_key}

    async def list_projects(self):
        async with httpx.AsyncClient() as client:
            response = await client.get(
                f"{self.base_url}/api/v1/projects",
                headers=self._headers()
            )
            response.raise_for_status()
            return response.json()

    async def spawn_agent(self, project_id: str, role: str, mission: str):
        async with httpx.AsyncClient() as client:
            response = await client.post(
                f"{self.base_url}/api/v1/agents",
                headers=self._headers(),
                json={"project_id": project_id, "role": role, "mission": mission}
            )
            response.raise_for_status()
            return response.json()
```

### Environment Variable Configuration

**Recommended: .env file in project directory**

```bash
# .env (gitignored!)
GILJO_SERVER_URL=http://lan-server:7272
GILJO_API_KEY=gk_550e8400_7f3d2e1a9b8c4d6f1e2a3b5c7d9f0e1a
```

**Load in Python:**

```python
from dotenv import load_dotenv
load_dotenv()  # Loads .env file

# Now environment variables available
import os
server_url = os.getenv("GILJO_SERVER_URL")
api_key = os.getenv("GILJO_API_KEY")
```

---

## Troubleshooting

### Issue: Setup Wizard - Auto-Detect IP Doesn't Work

**Symptom:** "Auto-Detect IP" button doesn't populate server IP

**Cause:** Backend `/api/setup/detect-ip` endpoint unavailable

**Solution:**
```bash
# 1. Check API server is running
curl http://localhost:7272/health

# 2. Check endpoint directly
curl http://localhost:7272/api/setup/detect-ip

# 3. Manually enter IP (use ipconfig / ifconfig to find)
ipconfig  # Windows
ifconfig  # Linux/Mac
```

### Issue: Cannot Login - Invalid Credentials

**Symptom:** Login fails with "Invalid credentials" error

**Possible Causes:**

1. **Wrong username/password:**
   - Verify credentials with admin
   - Check Caps Lock

2. **User account not created:**
   ```sql
   -- Check if user exists
   SELECT * FROM users WHERE username = 'admin';
   ```

3. **User account inactive:**
   ```sql
   -- Check is_active flag
   SELECT username, is_active FROM users WHERE username = 'admin';

   -- Activate user
   UPDATE users SET is_active = true WHERE username = 'admin';
   ```

4. **Password hash issue:**
   ```bash
   # Reset password via CLI
   python scripts/reset_password.py --username admin
   ```

### Issue: API Key Authentication Fails

**Symptom:** MCP tool requests return 401 Unauthorized

**Diagnosis:**

```bash
# Test API key manually
curl -H "X-API-Key: gk_your_key_here" http://lan-server:7272/api/v1/projects

# Expected: JSON response with projects
# Actual: {"detail":"Invalid API key"}
```

**Possible Causes:**

1. **Wrong header name:**
   - Must be: `X-API-Key` (case-sensitive)
   - Not: `Authorization: Bearer ...`

2. **Invalid key:**
   - Check key is complete (no truncation)
   - Verify key is active in database

   ```sql
   SELECT key_prefix, is_active, created_at
   FROM api_keys
   WHERE key_prefix LIKE 'gk_550e8400%';
   ```

3. **Key revoked:**
   - Check dashboard: Settings → API Keys
   - Regenerate new key if needed

4. **Server mode not enabled:**
   ```yaml
   # config.yaml must have:
   security:
     api_key_required: true
     user_accounts: true
   ```

### Issue: CORS Errors in Browser

**Symptom:** Browser console shows CORS error when accessing dashboard from LAN

**Error:**
```
Access to fetch at 'http://lan-server:7272/api/v1/projects' from origin
'http://client-ip:7274' has been blocked by CORS policy
```

**Solution:**

```yaml
# config.yaml - Add client IP to CORS origins
security:
  cors:
    allowed_origins:
      - http://127.0.0.1:7274
      - http://localhost:7274
      - http://lan-server-ip:7274
      - http://client-ip:7274  # Add this
      - http://10.1.0.*:7274   # Or use wildcard
```

**Restart API server after config change:**

```bash
stop_giljo.bat && start_giljo.bat  # Windows
sudo systemctl restart giljo-mcp    # Linux
```

### Issue: JWT Token Expired

**Symptom:** Dashboard redirects to login after 24 hours

**Explanation:** This is expected behavior (24h token expiry)

**Solution:**
- User must log in again
- Future: Implement refresh token for silent renewal

### Issue: Lost Admin Password

**Solution:**

```bash
# Reset admin password via CLI
python scripts/reset_password.py --username admin

# Output:
# Enter new password: ********
# Confirm password: ********
# ✅ Password updated successfully for user: admin
```

---

## Summary

This architecture provides a **secure, scalable, and user-friendly authentication system** for GiljoAI MCP across all deployment modes:

- **LOCALHOST:** No auth (development convenience)
- **LAN:** User accounts + personal API keys (team collaboration)
- **WAN:** Enhanced security + HTTPS (internet-facing)
- **SaaS:** Multi-tenancy + OAuth2 (global scale)

**Key Benefits:**

✅ **Per-User Authentication:** Individual accountability and audit trails
✅ **Personal API Keys:** Secure tool/CLI access, revocable per-user
✅ **Role-Based Access:** Admin, Developer, Viewer roles
✅ **Seamless Migration:** Easy upgrade path (localhost → LAN → WAN → SaaS)
✅ **Security in Depth:** Multiple authentication layers
✅ **Future-Proof:** Foundation ready for OAuth2, 2FA, multi-tenancy

**Next Steps:**

1. Review `DEPLOYMENT_MODE_COMPARISON.md` for quick reference
2. Follow `LAN_DEPLOYMENT_GUIDE.md` for LAN setup
3. Use Setup Wizard for easy admin account creation
4. Generate personal API keys for MCP tools
5. Monitor usage in audit logs

---

**Document Status:** Production Ready
**Version:** 2.0
**Last Updated:** 2025-10-07
**Next Review:** After WAN authentication implementation
