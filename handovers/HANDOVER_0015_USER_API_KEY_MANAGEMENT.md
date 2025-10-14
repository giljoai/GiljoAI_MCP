# HANDOVER 0015 - User API Key Management for MCP Configuration

**Handover ID**: 0015
**Parent**: 0008
**Created**: 2025-10-13
**Status**: ACTIVE
**Type**: BUILD
**Priority**: CRITICAL

## Problem Statement

**Current State**: Multi-user setup lacks individual API key management for MCP configuration.
**Vision**: Each user gets personal API keys for secure, isolated MCP server access.
**Gap**: No user-specific API key generation/management in user settings.

## Critical Issues Identified

### 1. Authentication Failure
- All API endpoints returning 401 Unauthorized
- Frontend has no valid auth token
- AI Tools setup failing due to auth issues

### 2. Multi-Tenant MCP Access Problem
**Scenario**: 10 users working against server
- How does Claude Code know which project context to use?
- How does it know user permissions?
- Each user needs individual API key for MCP config
- Current system lacks user-scoped API keys

### 3. Missing Components
- No user API key generation in settings
- No tenant-specific project isolation
- AI Tools config generator failing due to 401 errors

## Technical Analysis

### Current API Key System (Admin-Only)
```
Location: /admin/settings → Network tab
Scope: System-wide API key
Problem: All users share same key (security issue)
```

### Required User API Key System
```
Location: /settings → API and Integrations tab
Scope: User-specific API keys
Benefits:
- Individual user authentication
- Project/permission isolation
- Revocable per-user access
- Audit trail per user
```

### MCP Configuration Requirements
Each user's Claude Code config needs:
```json
{
  "mcpServers": {
    "giljo-mcp": {
      "command": "uvx",
      "args": ["giljo-mcp-client"],
      "env": {
        "GILJO_SERVER_URL": "http://10.1.0.164:7272",
        "GILJO_TENANT_KEY": "usr_abc123",        ← User-specific
        "GILJO_API_KEY": "gk_user_xyz789..."    ← User-specific API key
      }
    }
  }
}
```

## Implementation Plan

### Phase 0: Research Existing API Generation System (PRIORITY)
**Research existing API key generation modals and tenant-specific functionality**
- Investigate current API generation modals in codebase
- Analyze tenant-specific API key capabilities
- Document existing user API key management features
- Map current authentication flow and token handling
- Identify gaps between existing system and multi-user MCP requirements

**Files to investigate**:
- Search for API key generation components/modals
- Check existing user API key endpoints
- Analyze tenant isolation in current API key system
- Review authentication middleware and token validation

## Research Findings - Existing API Key System

### 🔍 **DISCOVERY**: User API Key System Already Exists!

**Key Components Found**:
1. **`ApiKeyManager.vue`** - Full-featured user API key management component (266 lines)
   - **Location**: `frontend/src/components/ApiKeyManager.vue`
   - **Features**: List, create, revoke API keys with confirmation dialogs
   - **Status**: Production-ready with professional UI

2. **`ApiKeyWizard.vue`** - Referenced but not found yet (imported in ApiKeyManager)
   - **Purpose**: Modal for generating new API keys
   - **Integration**: Called when "Generate New Key" button clicked

3. **API Service Integration**:
   - Uses `api.apiKeys.list()` service method
   - Uses `api.apiKeys.delete(keyId)` for revocation
   - Handles authentication (401) errors gracefully

### 📊 **Component Analysis - ApiKeyManager.vue**

**UI Features**:
- ✅ Professional data table with sorting
- ✅ Key preview display (prefix + "...")
- ✅ Created date and last used timestamps
- ✅ Delete confirmation with "DELETE" typing requirement
- ✅ Loading states and error handling
- ✅ Empty state messaging
- ✅ Accessibility features (focus indicators, ARIA labels)

**Security Features**:
- ✅ Only shows key prefix, never full key
- ✅ Secure deletion confirmation process
- ✅ Handles 401 errors (authentication failures)

**Table Columns**:
- Name (user-friendly key names)
- Key Prefix (gk_xxxxx... format)
- Created (formatted timestamp)
- Last Used (humanized "X ago" format)
- Actions (revoke button)

### 🔧 **Integration Status**

**Current Integration Points**:
- Component exists but **NOT integrated** into any settings page
- API service methods exist (`api.apiKeys.*`)
- Professional UI ready for deployment

**Missing Integration**:
- ❌ Not imported/used in `/settings` (UserSettings.vue)
- ❌ Not imported/used in `/admin/settings` (SystemSettings.vue)
- ❌ ApiKeyWizard component location unknown
- ❌ Backend API endpoints status unknown

### 🎯 **Gap Analysis**

**What Exists** (90% complete):
- Full user API key management UI
- Professional data table interface
- Secure key handling (preview only)
- Delete confirmation workflows
- Authentication error handling

**What's Missing** (10% remaining):
- Integration into settings pages
- ApiKeyWizard modal component
- Backend API endpoint verification
- Tenant-specific key generation
- MCP configuration integration

### 📍 **Files Located**
```
✅ frontend/src/components/ApiKeyManager.vue (266 lines)
❓ frontend/src/components/ApiKeyWizard.vue (referenced but not found)
❓ API service methods (api.apiKeys.list, api.apiKeys.delete)
❓ Backend endpoints (/api/users/me/api-keys/)
```

### Phase 1: Verify/Complete Backend API Key System
**Investigate Existing Endpoints**:
- Verify `/api/users/me/api-keys/` endpoints exist
- Check database schema for user API keys
- Test tenant isolation in API key generation
- Validate authentication middleware integration

**Expected Database Schema** (may already exist):
```sql
-- Existing table (to verify)
CREATE TABLE user_api_keys (
    id UUID PRIMARY KEY,
    user_id UUID REFERENCES users(id),
    tenant_key VARCHAR REFERENCES tenants(tenant_key),
    key_hash VARCHAR NOT NULL,     -- Hashed API key
    key_preview VARCHAR NOT NULL,  -- First 8 + last 4 chars
    name VARCHAR,                  -- User-friendly name
    scopes JSON,                   -- Permissions array
    created_at TIMESTAMP,
    last_used_at TIMESTAMP,
    expires_at TIMESTAMP,
    is_active BOOLEAN DEFAULT TRUE
);
```

### Phase 2: Complete Frontend Integration (Mostly Done!)
**Status**: `ApiKeyManager.vue` component is 90% complete

**Remaining Tasks**:
1. **Find/Create ApiKeyWizard.vue** - Modal for key generation
2. **Add to UserSettings.vue** - Import and integrate into "API and Integrations" tab
3. **Verify API service methods** - Check `api.apiKeys.*` implementation
4. **Test tenant isolation** - Ensure users only see their own keys

**Integration Location**: `/settings` → "API and Integrations" tab
```vue
<!-- Add to UserSettings.vue -->
<div class="mb-6">
  <h3 class="text-h6 mb-4">Personal API Keys</h3>
  <ApiKeyManager />
</div>
```

### Phase 3: Enhanced AI Tools Config Generator
**Update AIToolSetup.vue** (already in UserSettings.vue):
- Integrate with user's personal API keys
- Auto-populate tenant_key from user context
- Show authentication status and API key availability
- Handle 401 errors gracefully with API key creation prompts

**Updated Config Generation Logic**:
```javascript
// Instead of hardcoded values, use user's data:
const config = {
  mcpServers: {
    "giljo-mcp": {
      command: "uvx",
      args: ["giljo-mcp-client"],
      env: {
        GILJO_SERVER_URL: serverUrl,
        GILJO_TENANT_KEY: user.tenant_key,        // From authenticated user
        GILJO_API_KEY: user.active_api_key        // From user's API keys
      }
    }
  }
}
```

**User Experience Flow**:
1. User opens AI Tools setup
2. If no API keys exist → Show "Create API Key" prompt
3. If API keys exist → Use most recent active key
4. Generate config with user-specific credentials

### Phase 4: Authentication Fixes
**Frontend Auth Issues**:
- Fix token storage/retrieval
- Add auth retry logic
- Handle 401 responses properly
- Show login prompts when needed

**Backend Auth Issues**:
- Verify user API key authentication
- Add tenant isolation to all endpoints
- Fix middleware auth chain

## Current Failures Analysis

### Console Errors Breakdown
```
❌ "GET /api/v1/projects/ HTTP/1.1" 401 Unauthorized
❌ "GET /api/ai-tools/supported HTTP/1.1" 401 Unauthorized
❌ "GET /api/serena/status HTTP/1.1" 401 Unauthorized

Root Cause: No valid auth token being sent
```

### Vue Component Errors
```
❌ Failed to resolve component: AppAlert-title
Fixed: Use v-alert title slots instead
```

### Authentication Chain Broken
```
Frontend: [Auth] Auth token available: No
Backend: All protected endpoints returning 401
```

## Success Metrics

1. **User API Key Generation**: Each user can generate personal API keys
2. **MCP Config Works**: Generated config connects successfully to server
3. **Multi-Tenant Isolation**: User A cannot access User B's projects
4. **Authentication Fixed**: All 401 errors resolved
5. **AI Tools Setup**: "Select AI tool" dropdown populates correctly

## Risk Assessment

**High Risk**: Current system unusable due to auth failures
**Timeline**: Critical - blocks all MCP functionality
**Dependencies**: Auth system, user management, API key infrastructure

## Implementation Priority (UPDATED)

```
✅ 0. Research existing API generation system (COMPLETE)
1. Fix immediate auth issues (emergency)
2. Find/create ApiKeyWizard.vue component (1-2 hours)
3. Integrate ApiKeyManager into UserSettings.vue (30 minutes)
4. Verify backend API endpoints exist (30 minutes)
5. Connect AI tools config generator to user API keys (1 hour)
6. Test multi-tenant API key isolation (validation)
```

## Expected Deliverables (UPDATED)

### ✅ **Already Complete (90%)**:
1. **Frontend**: Full-featured ApiKeyManager.vue component (266 lines)
2. **UI/UX**: Professional data table, delete confirmations, error handling
3. **Security**: Key preview only, secure deletion process

### 🔧 **Still Needed (10%)**:
1. **Frontend**: Find/create ApiKeyWizard.vue modal component
2. **Integration**: Add ApiKeyManager to UserSettings.vue "API and Integrations" tab
3. **Backend Verification**: Confirm API endpoints exist and work
4. **AI Tools Integration**: Connect config generator to user's API keys
5. **Testing**: Verify tenant isolation and multi-user scenarios

---

**Next Actions**:
0. Research existing API generation modals and tenant-specific functionality
1. Investigate and fix current authentication failures
2. Analyze existing user API key database schema
3. Enhance existing user API key backend endpoints
4. Integrate user API key management UI
5. Update AI tools config generator for user keys

This handover addresses the critical gap between single admin API keys and the multi-user reality of MCP server usage.