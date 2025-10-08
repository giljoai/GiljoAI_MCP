# Agent Mission: User Management & Setup Wizard Enhancement

## 🎯 Mission Objective

Implement a comprehensive user management system and redesign the setup wizard to provide a streamlined, mode-aware configuration experience for GiljoAI MCP.

---

## 📋 Task Breakdown

### **Phase 1: User Management System** (Priority: HIGH)

#### 1.1 Backend: User CRUD Endpoints
**File:** `api/endpoints/users.py` (NEW)

**Requirements:**
- Create REST endpoints for user management:
  - `GET /api/users/` - List all users (admin only, filtered by tenant)
  - `POST /api/users/` - Create new user (admin only)
  - `GET /api/users/{id}` - Get user details
  - `PUT /api/users/{id}` - Update user (admin or self)
  - `DELETE /api/users/{id}` - Deactivate user (admin only, soft delete)
  - `PUT /api/users/{id}/role` - Change user role (admin only)

**Role-Based Access:**
- **Admin** - Can manage all users, change roles, access all settings
- **User** - Can only view/edit their own profile, generate API keys

**Dependencies:**
```python
from giljo_mcp.auth.dependencies import get_current_active_user, require_admin
from giljo_mcp.models import User
```

**Security Requirements:**
- All endpoints require authentication (no localhost bypass for user management)
- Multi-tenant isolation enforced (filter by tenant_key)
- Password changes require old password verification
- Admin cannot demote themselves (prevent lockout)

---

#### 1.2 Frontend: User Management UI
**File:** `frontend/src/views/UsersView.vue` (NEW)

**UI Requirements:**

**User List (Data Table):**
- Columns: Username, Email, Role, Status, Last Login, Actions
- Filters: Role (Admin/User), Status (Active/Inactive)
- Search: By username or email
- Actions: Edit, Deactivate/Activate, Delete (admin only)

**Add User Dialog:**
```vue
Fields:
- Username (required, unique)
- Email (optional)
- Full Name (optional)
- Password (required, min 8 chars)
- Confirm Password (required)
- Role (Admin/User dropdown) - admin only
- Is Active (checkbox, default: true)
```

**Edit User Dialog:**
```vue
Fields:
- Email (editable)
- Full Name (editable)
- Role (admin only can edit)
- Is Active (admin only can edit)
- Reset Password button (shows password change dialog)
```

**Integration:**
- Add "Users" menu item in sidebar (admin only)
- Route: `/users`
- Icon: `mdi-account-multiple`

---

#### 1.3 Role-Based UI Visibility
**Files to Update:**
- `frontend/src/router/index.js` - Add route guards for admin-only pages
- `frontend/src/App.vue` - Hide admin menu items for regular users
- `frontend/src/views/SettingsView.vue` - Hide network settings tab for regular users

**Visibility Rules:**
- **Admin sees:** All tabs, Users menu, Network settings, API Keys (all users)
- **User sees:** Dashboard, Projects, Tasks, Messages, Settings (limited), API Keys (own only)

---

### **Phase 2: API Key Manager Enhancement** (Priority: HIGH)

#### 2.1 Update API Key Generation Modal
**File:** `frontend/src/components/ApiKeyManager.vue`

**Requirements:**
When a key is generated, show modal with:

1. **Key Display** (show once):
   ```
   ⚠️ Save this key now - shown only once!
   [gk_abc123...] [Copy]
   ```

2. **MCP Configuration Section**:
   - Expansion panel: "Claude Code CLI"
     - Shows: `~/.claude.json` config snippet
     - Copy button for full config
     - Instructions: "Add to ~/.claude.json, restart Claude Code, type /mcp"

   - Expansion panel: "Other MCP Clients"
     - Table showing env vars:
       - `GILJO_API_KEY`: [key value]
       - `GILJO_SERVER_URL`: [server URL]

3. **Confirmation Checkbox**:
   ```
   ☐ I have saved this key and configuration
   ```
   - Dialog cannot close until checked

**Computed Properties:**
```javascript
const serverUrl = computed(() => {
  // Detect from config: http://{server.ip}:{api.port}
})

const claudeCodeConfig = computed(() => {
  // Generate JSON config with key and server URL
})
```

---

### **Phase 3: Setup Wizard Redesign** (Priority: HIGH)

#### 3.1 New Wizard Step Order

**Current Steps (TO REPLACE):**
1. Welcome
2. Database Connection
3. Attach Tools
4. Serena
5. Network Config
6. Complete

**New Steps (IMPLEMENT):**
1. **Database Test** (NEW - always first)
2. **Deployment Mode** (MOVED - was Network Config)
3. **Admin Setup** (NEW - LAN/WAN only, conditional)
4. **MCP Tool Config** (ENHANCED - mode-aware)
5. **Serena Config** (ENHANCED - better explanation)
6. **Summary** (ENHANCED - mode-aware, show credentials)

---

#### 3.2 Step 1: Database Connection Test (NEW)
**File:** `frontend/src/components/setup/DatabaseTestStep.vue` (NEW)

**UI:**
```vue
<template>
  <v-card-text>
    <h2>Database Connection Test</h2>
    <p>Verifying database connection...</p>

    <v-progress-linear v-if="testing" indeterminate />

    <v-list v-if="testComplete">
      <v-list-item>
        <v-icon :color="dbConnected ? 'success' : 'error'">
          {{ dbConnected ? 'mdi-check-circle' : 'mdi-alert-circle' }}
        </v-icon>
        PostgreSQL Connection
      </v-list-item>
      <v-list-item>
        <v-icon :color="dbExists ? 'success' : 'error'">
          {{ dbExists ? 'mdi-check-circle' : 'mdi-alert-circle' }}
        </v-icon>
        Database: giljo_mcp
      </v-list-item>
    </v-list>

    <v-alert v-if="error" type="error">
      {{ error }}
    </v-alert>
  </v-card-text>
</template>
```

**API Call:**
```javascript
const testDatabase = async () => {
  const response = await fetch('/api/v1/config/health/database')
  // Check response, set dbConnected and dbExists
}
```

**Validation:**
- Cannot proceed to next step if database test fails
- Show troubleshooting link if error occurs

---

#### 3.3 Step 2: Deployment Mode (ENHANCED)
**File:** `frontend/src/components/setup/DeploymentModeStep.vue` (NEW)

**UI:**
```vue
<v-radio-group v-model="selectedMode">
  <v-radio value="localhost">
    <template #label>
      <div>
        <strong>Localhost (Solo Development)</strong>
        <p class="text-caption">No authentication, auto-configuration, 127.0.0.1 only</p>
      </div>
    </template>
  </v-radio>

  <v-radio value="lan">
    <template #label>
      <div>
        <strong>LAN (Team Network)</strong>
        <p class="text-caption">User authentication, network accessible, API keys required</p>
      </div>
    </template>
  </v-radio>

  <v-radio value="wan" disabled>
    <template #label>
      <div>
        <strong>WAN (Future)</strong>
        <v-chip size="small" color="info">Coming Soon</v-chip>
      </div>
    </template>
  </v-radio>
</v-radio-group>
```

**Emit:**
```javascript
emit('update:deploymentMode', selectedMode)
emit('next')
```

---

#### 3.4 Step 3: Admin Account Setup (NEW - Conditional)
**File:** `frontend/src/components/setup/AdminSetupStep.vue` (NEW)

**Show Only If:** `deploymentMode === 'lan' || deploymentMode === 'wan'`

**UI:**
```vue
<v-card-text>
  <h2>Create Administrator Account</h2>
  <p>This account will have full access to manage users and settings.</p>

  <v-text-field
    v-model="adminUsername"
    label="Admin Username"
    required
  />

  <v-text-field
    v-model="adminPassword"
    label="Password"
    type="password"
    :rules="[passwordRules.min8]"
  />

  <v-text-field
    v-model="adminPasswordConfirm"
    label="Confirm Password"
    type="password"
    :rules="[passwordRules.match]"
  />

  <v-text-field
    v-model="serverIp"
    label="Server IP Address"
    hint="Your network IP (not 169.254.x.x)"
    persistent-hint
  />
</v-card-text>
```

**API Call on Next:**
```javascript
POST /api/setup/complete
{
  network_mode: "lan",
  lan_config: {
    admin_username: adminUsername,
    admin_password: adminPassword,
    server_ip: serverIp
  }
}
```

**Response Handling:**
- Store generated API key: `response.api_key`
- Pass to next step (MCP Tool Config)

---

#### 3.5 Step 4: MCP Tool Configuration (ENHANCED)
**File:** Update `frontend/src/components/setup/AttachToolsStep.vue`

**Mode-Aware Behavior:**

**If Localhost:**
- Show: "Configuring Claude Code automatically..."
- Call: `POST /api/setup/register-mcp` (auto-inject)
- Show: "✓ Claude Code configured successfully"

**If LAN/WAN:**
- Show: "Your admin API key: [key from previous step]" with copy button
- Display: JSON config snippet (same as ApiKeyManager) with copy button
- Instructions: "Add to ~/.claude.json and restart Claude Code"
- Show note: "Future MCP Clients: Codex CLI (Coming Soon), Gemini CLI (Coming Soon)"

**No API call** - User copies manually

**UI Implementation:**
```vue
<v-card-text>
  <h2>Configure Your MCP Client</h2>

  <!-- API Key Display -->
  <v-alert type="info" class="mb-4">
    <strong>Your Admin API Key:</strong>
    <v-text-field
      :value="apiKey"
      readonly
      density="compact"
      variant="outlined"
      class="mt-2"
    >
      <template #append-inner>
        <v-btn icon="mdi-content-copy" size="small" @click="copyApiKey" />
      </template>
    </v-text-field>
  </v-alert>

  <!-- MCP Config -->
  <p>Add this configuration to your MCP client:</p>
  <v-card variant="outlined" class="mb-2">
    <v-card-text>
      <pre>{{ mcpConfig }}</pre>
    </v-card-text>
    <v-card-actions>
      <v-btn prepend-icon="mdi-content-copy" @click="copyConfig">
        Copy Configuration
      </v-btn>
    </v-card-actions>
  </v-card>

  <v-alert type="info" density="compact">
    ℹ️ Add to ~/.claude.json and restart Claude Code
  </v-alert>

  <!-- Future Clients Note -->
  <v-alert type="info" variant="tonal" class="mt-4">
    <strong>Future MCP Clients:</strong>
    <ul class="mt-2">
      <li>Codex CLI (Coming Soon)</li>
      <li>Gemini CLI (Coming Soon)</li>
    </ul>
  </v-alert>
</v-card-text>
```

---

#### 3.6 Step 5: Serena Configuration (ENHANCED)
**File:** Update `frontend/src/components/setup/SerenaAttachStep.vue`

**Add Explanation:**
```vue
<v-card-text>
  <h2>Enable Serena MCP Enhancement?</h2>

  <p>Serena adds semantic code navigation tools for intelligent editing.</p>

  <v-expansion-panels class="mb-4">
    <v-expansion-panel>
      <v-expansion-panel-title>What is Serena?</v-expansion-panel-title>
      <v-expansion-panel-text>
        Serena enhances agent prompts with tools for:
        • Symbol-level code understanding (classes, methods)
        • Smart find/replace operations
        • Code relationship mapping
        • Cross-file refactoring
      </v-expansion-panel-text>
    </v-expansion-panel>
  </v-expansion-panels>

  <!-- IMPORTANT: Installation Required -->
  <v-alert type="warning" variant="tonal" class="mb-4">
    <strong>⚠️ Serena MCP must be installed separately</strong>
    <p class="mt-2">
      Serena is a separate MCP server that needs to be installed on your system.
    </p>
    <v-btn
      href="https://github.com/oraios/serena"
      target="_blank"
      variant="outlined"
      size="small"
      class="mt-2"
    >
      <v-icon start>mdi-github</v-icon>
      Install Serena MCP
    </v-btn>
  </v-alert>

  <v-checkbox
    v-model="serenaEnabled"
    label="Enable Serena (I have installed it separately)"
  />
</v-card-text>
```

---

#### 3.7 Step 6: Summary (ENHANCED - Mode-Aware)
**File:** Update `frontend/src/components/setup/SetupCompleteStep.vue`

**Conditional Content Based on Mode:**

**If Localhost:**
```vue
<v-card-text>
  <h2>✓ Setup Complete!</h2>

  <v-list>
    <v-list-item>Mode: Localhost</v-list-item>
    <v-list-item>Database: Connected</v-list-item>
    <v-list-item>Claude Code: Configured</v-list-item>
    <v-list-item>Serena: {{ serenaEnabled ? 'Enabled' : 'Disabled' }}</v-list-item>
  </v-list>

  <v-divider class="my-4" />

  <h3>Next Steps:</h3>
  <ol>
    <li>Restart Claude Code CLI</li>
    <li>Type /mcp to verify</li>
    <li>Start your first project!</li>
  </ol>

  <v-alert type="info">
    Server: http://127.0.0.1:7272<br>
    Dashboard: http://127.0.0.1:7274
  </v-alert>
</v-card-text>
```

**If LAN/WAN:**
```vue
<v-card-text>
  <h2>✓ Setup Complete!</h2>

  <v-list>
    <v-list-item>Mode: LAN</v-list-item>
    <v-list-item>Admin: {{ adminUsername }}</v-list-item>
    <v-list-item>MCP Config: Ready to paste</v-list-item>
  </v-list>

  <v-divider class="my-4" />

  <v-card variant="outlined">
    <v-card-title>Admin Credentials</v-card-title>
    <v-card-text>
      Username: {{ adminUsername }}<br>
      Password: {{ showPassword ? adminPassword : '••••••••' }}
      <v-btn @click="showPassword = !showPassword">
        {{ showPassword ? 'Hide' : 'Show' }}
      </v-btn>
    </v-card-text>
  </v-card>

  <v-divider class="my-4" />

  <h3>Team Access:</h3>
  <v-alert type="success">
    Server: http://{{ serverIp }}:7272<br>
    Dashboard: http://{{ serverIp }}:7274
  </v-alert>

  <h3>Next Steps:</h3>
  <ol>
    <li>Add MCP config to ~/.claude.json</li>
    <li>Restart Claude Code CLI</li>
    <li>Login at dashboard URL</li>
    <li>Invite team members (Settings → Users)</li>
  </ol>

  <v-btn @click="restartServices">Finish & Restart Services</v-btn>
</v-card-text>
```

---

### **Phase 4: Integration & Testing** (Priority: MEDIUM)

#### 4.1 Update SetupWizard.vue
**File:** `frontend/src/views/SetupWizard.vue`

**Changes:**
1. Update step array:
   ```javascript
   const steps = [
     { component: DatabaseTestStep },
     { component: DeploymentModeStep },
     { component: AdminSetupStep, showIf: () => config.deploymentMode !== 'localhost' },
     { component: AttachToolsStep },
     { component: SerenaAttachStep },
     { component: SetupCompleteStep }
   ]
   ```

2. Add conditional rendering:
   ```vue
   <component
     v-if="!step.showIf || step.showIf()"
     :is="step.component"
   />
   ```

3. State management:
   ```javascript
   const config = reactive({
     deploymentMode: 'localhost',
     adminUsername: '',
     adminPassword: '',
     serverIp: '',
     apiKey: '', // Stored from admin setup
     serenaEnabled: true
   })
   ```

---

#### 4.2 Backend Updates
**File:** `api/endpoints/setup.py`

**Update `/api/setup/complete` endpoint:**
- If LAN/WAN mode: Create User in database (not just encrypted file)
- Generate API key for admin user automatically
- Return API key in response (only time it's shown in plaintext)
- Store hashed version in database

**Response:**
```json
{
  "success": true,
  "mode": "lan",
  "admin_username": "admin",
  "api_key": "gk_abc123...",  // Only returned once!
  "server_url": "http://10.1.0.164:7272"
}
```

---

### **Phase 5: Testing Checklist**

#### 5.1 User Management Tests
- [ ] Create user (admin only)
- [ ] Edit user (admin can edit all, user can edit self)
- [ ] Delete user (soft delete, admin only)
- [ ] Change role (admin only)
- [ ] Role-based UI visibility works
- [ ] Multi-tenant isolation (users can't see other tenants)

#### 5.2 API Key Manager Tests
- [ ] Generate key shows modal with config
- [ ] Copy buttons work
- [ ] Config includes correct server URL
- [ ] Confirmation checkbox prevents closing
- [ ] Key is masked after dialog closes

#### 5.3 Wizard Flow Tests
- [ ] Database test step works
- [ ] Localhost flow: Auto-configures Claude Code
- [ ] LAN flow: Shows admin setup → API key → copy-paste instructions
- [ ] Summary shows correct info based on mode
- [ ] Wizard saves config correctly
- [ ] Services restart after completion

---

## 🎯 Success Criteria

### User Management
- ✅ Admin can create/edit/delete users
- ✅ Regular users can only manage themselves
- ✅ Role-based UI works (admin sees more)
- ✅ Multi-tenant isolation enforced

### API Key Manager
- ✅ Modal shows key once with copy-paste config
- ✅ Config is correct for Claude Code
- ✅ User must confirm before closing

### Setup Wizard
- ✅ Database test runs first
- ✅ Mode selection determines flow
- ✅ Localhost: Auto-configures
- ✅ LAN: Shows admin setup + API key + instructions
- ✅ Summary is mode-aware
- ✅ All data persists correctly

---

## 📁 Files to Create/Modify

### NEW Files (8):
1. `api/endpoints/users.py` - User CRUD endpoints
2. `frontend/src/views/UsersView.vue` - User management UI
3. `frontend/src/components/setup/DatabaseTestStep.vue` - DB test step
4. `frontend/src/components/setup/DeploymentModeStep.vue` - Mode selection
5. `frontend/src/components/setup/AdminSetupStep.vue` - Admin account creation

### MODIFIED Files (6):
1. `frontend/src/components/ApiKeyManager.vue` - Enhanced key generation modal
2. `frontend/src/components/setup/AttachToolsStep.vue` - Mode-aware MCP config
3. `frontend/src/components/setup/SerenaAttachStep.vue` - Better explanation
4. `frontend/src/components/setup/SetupCompleteStep.vue` - Mode-aware summary
5. `frontend/src/views/SetupWizard.vue` - New step flow
6. `api/endpoints/setup.py` - Return API key on admin creation

### UPDATED Files (3):
1. `frontend/src/router/index.js` - Add /users route, admin guards
2. `frontend/src/App.vue` - Hide admin menu items for regular users
3. `frontend/src/views/SettingsView.vue` - Hide network tab for regular users

---

## 🚀 Execution Strategy

### Recommended Agent Sequence:

1. **database-expert** - Create user CRUD endpoints (backend)
2. **frontend-tester** - Build UsersView.vue (user management UI)
3. **frontend-tester** - Enhance ApiKeyManager.vue (key generation modal)
4. **frontend-tester** - Create new wizard steps (DatabaseTest, DeploymentMode, AdminSetup)
5. **frontend-tester** - Update existing wizard steps (AttachTools, Serena, Complete)
6. **backend-integration-tester** - Update setup.py endpoint
7. **backend-integration-tester** - Test full flow (localhost + LAN)
8. **documentation-manager** - Update user guides and wizard docs

---

## 💡 Implementation Notes

### Security Considerations:
- User management endpoints require authentication (no localhost bypass)
- Admin role required for user CRUD operations
- Password changes require old password verification
- API keys shown once, then hashed

### UX Considerations:
- Wizard flow adapts to deployment mode (fewer steps for localhost)
- Clear visual feedback at each step
- Copy buttons for all config snippets
- Mode-aware summary shows relevant next steps

### Code Quality:
- Reuse existing auth patterns (JWT, role checks)
- Consistent Vuetify component usage
- Proper error handling and validation
- Multi-tenant isolation throughout

---

## 📞 Questions for User Before Starting

1. **User Roles:** Should we support more than Admin/User? (e.g., Viewer, Developer)
2. **Email Required:** Should email be required for users? (for password reset later)
3. **Self-Registration:** Should regular users be able to sign up themselves, or only admins create accounts?
4. **API Key Limits:** Should users have a limit on number of API keys? (e.g., max 5)
5. **Wizard Skip:** Should there be a "Skip wizard, I'll configure manually" option?

---

## 🎯 Ready to Execute

This mission is well-defined and ready for agent execution. Launch the specialized agents in sequence, starting with the database-expert for backend user management, then frontend-tester for UI implementation.

**Estimated Total Time:** 8-12 hours of agent work across multiple specialized agents.

**Go/No-Go Decision:** Awaiting your approval to proceed! 🚀
