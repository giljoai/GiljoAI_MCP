# LAN Enablement Implementation Plan - October 6, 2025

**Status**: Planning Phase
**Created**: October 6, 2025
**Owner**: GiljoAI Development Team
**Next Review**: After implementation completion

---

## 1. Executive Summary

### Current State
The GiljoAI MCP setup wizard successfully handles localhost mode installation but has critical gaps in LAN mode enablement. The wizard UI exists (NetworkConfigStep.vue with IP detection, admin fields, and firewall checkboxes), but the backend implementation is incomplete.

### Critical Gaps Identified
1. CORS origins not updated with LAN IP in config.yaml
2. API key generation exists in code but not exposed to user
3. No backend IP detection endpoint (only WebRTC in frontend)
4. No service restart instructions after LAN configuration
5. No post-restart validation mechanism

### Scope of Implementation
This plan addresses all critical gaps to deliver a fully functional LAN setup wizard that:
- Detects server IP (backend + frontend)
- Updates CORS origins automatically
- Generates and displays API key securely
- Provides clear restart instructions
- Validates LAN access post-restart (optional v2 feature)

### Estimated Effort
**Total**: 11-17 hours (1.5-2 days)
- Backend work: 4-6 hours
- Frontend work: 4-6 hours
- Integration testing: 2-3 hours
- Documentation: 1-2 hours

---

## 2. Current State Analysis

### What Exists
#### Frontend Components
- **Setup wizard** with 3-step flow (Welcome → Mode Selection → Configuration → Complete)
- **NetworkConfigStep.vue** with complete LAN UI:
  - WebRTC-based IP detection (line 349)
  - Admin username/password fields
  - Firewall configuration checkboxes
  - Network accessibility warnings
- **setupService.js** with `completeSetup()` method

#### Backend Infrastructure
- **`/api/setup/complete` endpoint** (api/endpoints/setup.py, line 191+)
  - Updates config.yaml mode (localhost → lan)
  - Changes API host binding (127.0.0.1 → 0.0.0.0)
  - Calls `_apply_mode_settings()` which generates API key internally
- **NetworkManager** class (installer/core/network.py)
  - IP detection logic already implemented
  - Hostname detection
  - Network interface enumeration

#### Documentation
- **LAN Deployment Guide** (docs/deployment/LAN_DEPLOYMENT.md)
- **Quick Start Guide** (docs/manuals/QUICK_START.md)
- **Technical Architecture** (docs/TECHNICAL_ARCHITECTURE.md)

### What's Missing (Critical Gaps)

#### Gap 1: CORS Origins Not Updated
**Severity**: CRITICAL
**Impact**: LAN clients cannot access API due to browser CORS blocking

**Current behavior**:
```python
# api/endpoints/setup.py (line 191+)
def complete_setup():
    config["installation"]["mode"] = "lan"
    config["services"]["api"]["host"] = "0.0.0.0"
    # ❌ MISSING: config["security"]["cors"]["allowed_origins"] update
    write_config(config)
```

**Expected behavior**:
```yaml
# config.yaml should contain:
security:
  cors:
    allowed_origins:
      - http://127.0.0.1:7274
      - http://localhost:7274
      - http://192.168.1.50:7274  # ← MISSING: LAN IP origin
      - http://DESKTOP-XYZ:7274   # ← MISSING: Hostname origin (optional)
```

#### Gap 2: API Key Not Generated/Displayed
**Severity**: CRITICAL
**Impact**: User cannot authenticate to LAN API, setup appears broken

**Current behavior**:
- `_apply_mode_settings()` generates API key internally
- Key stored somewhere (location TBD by system-architect)
- User never sees the key
- No way to authenticate

**Expected behavior**:
- Generate key during setup
- Display in modal with copy-to-clipboard
- Warn user to save securely
- Provide key regeneration documentation

#### Gap 3: No Backend IP Detection Endpoint
**Severity**: HIGH
**Impact**: Frontend relies on WebRTC only, may fail in some networks

**Current behavior**:
- NetworkConfigStep.vue uses WebRTC peer connection trick (line 349)
- No server-side validation
- No fallback if WebRTC fails

**Expected behavior**:
- `GET /api/network/detect-ip` endpoint using NetworkManager
- Frontend tries backend first, WebRTC as fallback
- Returns all detected IPs + recommended primary IP

#### Gap 4: No Restart Instructions
**Severity**: HIGH
**Impact**: User completes wizard but LAN mode doesn't activate (services not restarted)

**Current behavior**:
- Setup completes with generic success message
- User expects LAN mode to work immediately
- Configuration changes require service restart (not hot-reloadable)

**Expected behavior**:
- Clear modal with platform-specific restart commands
- "I've restarted services" confirmation required
- Explanation of why restart is necessary

#### Gap 5: No Post-Restart Validation
**Severity**: MEDIUM (v2 feature)
**Impact**: No way to verify LAN setup actually works

**Expected behavior**:
- Optional `GET /api/setup/validate-lan` endpoint
- Tests CORS, API key auth, network accessibility
- UI shows validation results with troubleshooting tips

### Architectural Findings from system-architect

#### Configuration Flow
```
config.yaml → ConfigManager → AuthManager → FastAPI startup
                                           → CORS middleware
```

**Key insights**:
1. CORS origins loaded at startup from config.yaml
2. Not hot-reloadable (requires service restart)
3. AuthManager reads API keys from config/database during startup
4. Mode changes require full service restart

#### Mode Switching Mechanics
```python
# src/giljo_mcp/config_manager.py
def get_mode() -> str:
    return config["installation"]["mode"]  # 'localhost' or 'server' or 'lan'

# api/middleware/auth.py
if config_manager.get_mode() in ["server", "lan", "wan"]:
    # Require API key authentication
```

**Implication**: Setup wizard must:
1. Update config.yaml
2. Instruct user to restart services
3. Validate after restart

#### API Key Generation Location
```python
# installer/core/config.py (_apply_mode_settings)
if mode in ["server", "lan", "wan"]:
    api_key = f"gk_{secrets.token_urlsafe(32)}"
    # TODO: Where is this stored? Database? File?
```

**Action needed**: system-architect to clarify key storage mechanism

#### Database Security Boundary
**Critical**: PostgreSQL always binds to localhost only, even in LAN mode
- API server binds to 0.0.0.0 (network accessible)
- Database binds to 127.0.0.1 (localhost only)
- This is intentional security boundary

---

## 3. Implementation Plan

### Phase 1: Backend API Enhancements
**Priority**: CRITICAL
**Owner**: tdd-implementor
**Dependencies**: backend-integration-tester writes tests first

#### 1.1 Create Network Detection Endpoint

**New File**: `api/endpoints/network.py`

**Purpose**: Provide server-side IP detection using existing NetworkManager class

**Endpoint Specification**:
```python
@router.get("/detect-ip", response_model=NetworkDetectionResponse)
async def detect_ip() -> NetworkDetectionResponse:
    """
    Detect server network information using NetworkManager.

    Returns:
        NetworkDetectionResponse: Hostname, all local IPs, and recommended primary IP

    Example Response:
        {
            "hostname": "DESKTOP-XYZ",
            "local_ips": ["192.168.1.50", "10.0.0.5"],
            "primary_ip": "192.168.1.50"
        }
    """
```

**Implementation Steps**:
1. Import NetworkManager from `installer.core.network`
2. Call `network_mgr.get_local_ips()` to detect all IPs
3. Filter out loopback addresses (127.x.x.x)
4. Select primary IP (first non-loopback IP)
5. Get hostname using `socket.gethostname()`
6. Return structured response

**Code Template**:
```python
# api/endpoints/network.py
from fastapi import APIRouter
from pydantic import BaseModel
from typing import List
import socket

from installer.core.network import NetworkManager

router = APIRouter(prefix="/api/network", tags=["network"])

class NetworkDetectionResponse(BaseModel):
    hostname: str
    local_ips: List[str]
    primary_ip: str

@router.get("/detect-ip", response_model=NetworkDetectionResponse)
async def detect_ip() -> NetworkDetectionResponse:
    network_mgr = NetworkManager()
    all_ips = network_mgr.get_local_ips()

    # Filter out loopback
    local_ips = [ip for ip in all_ips if not ip.startswith("127.")]

    # Select primary (first non-loopback)
    primary_ip = local_ips[0] if local_ips else "127.0.0.1"

    # Get hostname
    hostname = socket.gethostname()

    return NetworkDetectionResponse(
        hostname=hostname,
        local_ips=local_ips,
        primary_ip=primary_ip
    )
```

**Router Registration**:
```python
# api/app.py (line ~40, after other router imports)
from api.endpoints.network import router as network_router

# Line ~80, after other router includes
app.include_router(network_router)
```

**Testing Requirements**:
- Unit test: Mock NetworkManager to return test IPs
- Integration test: Call endpoint, verify JSON structure
- Edge case: No network interfaces (should return localhost)

**Estimated Effort**: 1 hour

---

#### 1.2 Enhance Setup Complete Endpoint

**Modified File**: `api/endpoints/setup.py` (line 191+)

**Purpose**: Update CORS origins and expose generated API key

**Changes Required**:

**Step 1: Add CORS Update Helper Function**

```python
# api/endpoints/setup.py (add after imports, before routes)

def update_cors_origins(config: dict, server_ip: str, hostname: str = None) -> None:
    """
    Update CORS allowed origins to include LAN IP and hostname.

    Args:
        config: Configuration dictionary to modify
        server_ip: Server IP address (e.g., "192.168.1.50")
        hostname: Optional hostname (e.g., "DESKTOP-XYZ")

    Modifies:
        config["security"]["cors"]["allowed_origins"] in place
    """
    # Ensure nested structure exists
    if "security" not in config:
        config["security"] = {}
    if "cors" not in config["security"]:
        config["security"]["cors"] = {}

    # Get existing origins or create list
    origins = config["security"]["cors"].get("allowed_origins", [
        "http://127.0.0.1:7274",
        "http://localhost:7274"
    ])

    # Add server IP origin
    frontend_port = config.get("services", {}).get("frontend", {}).get("port", 7274)
    lan_origin = f"http://{server_ip}:{frontend_port}"
    if lan_origin not in origins:
        origins.append(lan_origin)

    # Add hostname origin if provided
    if hostname:
        hostname_origin = f"http://{hostname}:{frontend_port}"
        if hostname_origin not in origins:
            origins.append(hostname_origin)

    # Update config
    config["security"]["cors"]["allowed_origins"] = origins
```

**Step 2: Modify SetupCompleteResponse Model**

```python
# api/endpoints/setup.py (line ~150)

class SetupCompleteResponse(BaseModel):
    success: bool
    message: str
    api_key: Optional[str] = None  # NEW: API key for LAN/server modes
    requires_restart: bool = False  # NEW: Indicates service restart needed
```

**Step 3: Update complete_setup() Endpoint Logic**

```python
# api/endpoints/setup.py (line 191+, inside complete_setup function)

@router.post("/complete", response_model=SetupCompleteResponse)
async def complete_setup(request: SetupCompleteRequest) -> SetupCompleteResponse:
    # ... existing code to load config ...

    # Update mode in config
    config["installation"]["mode"] = request.network_mode.value

    # Handle LAN-specific configuration
    if request.network_mode == NetworkMode.LAN:
        # Update API binding
        config["services"]["api"]["host"] = "0.0.0.0"

        # ✅ NEW: Update CORS origins
        update_cors_origins(
            config,
            server_ip=request.lan_config.server_ip,
            hostname=request.lan_config.hostname if request.lan_config else None
        )

        # ✅ NEW: Generate API key
        import secrets
        api_key = f"gk_{secrets.token_urlsafe(32)}"

        # TODO: Store API key (system-architect to provide storage location)
        # Options:
        #   1. Database: INSERT INTO api_keys (key_hash, name, created_at)
        #   2. Config file: config["security"]["api_keys"][0]
        #   3. Separate keys.yaml file
        # For now, just return to user (insecure but functional)

        # Write updated config
        write_config(config)

        return SetupCompleteResponse(
            success=True,
            message="LAN setup completed. Please restart services to apply changes.",
            api_key=api_key,
            requires_restart=True
        )

    else:  # Localhost mode
        config["services"]["api"]["host"] = "127.0.0.1"
        write_config(config)

        return SetupCompleteResponse(
            success=True,
            message="Localhost setup completed successfully.",
            requires_restart=False  # Localhost might not require restart
        )
```

**Testing Requirements**:
- Test CORS origins updated for LAN mode
- Test API key generated and returned
- Test localhost mode doesn't generate key
- Test hostname included in CORS if provided
- Test frontend port read from config

**Estimated Effort**: 2-3 hours

---

#### 1.3 Create Restart Validation Endpoint (Optional - v2)

**New Endpoint**: `GET /api/setup/validate-lan`

**Purpose**: Validate LAN configuration after service restart

**Specification**:
```python
class LANValidationResponse(BaseModel):
    success: bool
    checks: dict  # {"cors": true, "api_auth": true, "network": true}
    errors: List[str]

@router.get("/validate-lan", response_model=LANValidationResponse)
async def validate_lan_setup() -> LANValidationResponse:
    """
    Validate LAN setup is working correctly.

    Checks:
        - CORS origins include LAN IP
        - API key authentication enabled
        - Server binding to 0.0.0.0
        - Frontend accessible from network
    """
```

**Priority**: Low (v2 feature)
**Estimated Effort**: 1 hour

---

### Phase 2: Frontend Wizard Updates
**Priority**: HIGH
**Owner**: tdd-implementor + ux-designer (optional)
**Dependencies**: Phase 1 backend endpoints deployed

#### 2.1 Add Backend IP Detection to NetworkConfigStep

**Modified File**: `frontend/src/components/setup/NetworkConfigStep.vue`

**Current State** (line 349):
```javascript
// WebRTC-based IP detection
const pc = new RTCPeerConnection({ iceServers: [] });
// ... WebRTC logic ...
```

**Changes Required**:

**Step 1: Add Backend Detection Method**

```javascript
// Add new method to detect IP from backend
async detectServerIP() {
  try {
    // Try backend endpoint first
    const response = await setupService.detectIp();
    if (response.local_ips && response.local_ips.length > 0) {
      this.detectedIPs = response.local_ips;
      this.serverIP = response.primary_ip;
      this.hostname = response.hostname;

      // If multiple IPs, show dropdown
      if (response.local_ips.length > 1) {
        this.showIPDropdown = true;
      }

      return; // Success, don't try WebRTC
    }
  } catch (error) {
    console.warn('Backend IP detection failed, falling back to WebRTC:', error);
  }

  // Fallback to WebRTC if backend fails
  this.detectIPWebRTC();
}

// Rename existing method
detectIPWebRTC() {
  // Existing WebRTC logic (line 349+)
  const pc = new RTCPeerConnection({ iceServers: [] });
  // ... existing code ...
}
```

**Step 2: Update Component Data**

```javascript
data() {
  return {
    // ... existing data ...
    detectedIPs: [],      // NEW: All detected IPs
    showIPDropdown: false, // NEW: Show dropdown if multiple IPs
  }
}
```

**Step 3: Update Template (if multiple IPs detected)**

```vue
<!-- Add after existing IP input field -->
<v-select
  v-if="showIPDropdown"
  v-model="serverIP"
  :items="detectedIPs"
  label="Select Server IP"
  hint="Multiple network interfaces detected. Choose the IP clients will use."
  persistent-hint
  outlined
  dense
/>
```

**Testing Requirements**:
- Test backend detection called first
- Test WebRTC fallback if backend fails
- Test multiple IPs show dropdown
- Test single IP auto-populates field

**Estimated Effort**: 1 hour

---

#### 2.2 Display API Key After Setup

**Modified File**: `frontend/src/views/SetupWizard.vue`

**Purpose**: Show generated API key in modal with copy-to-clipboard

**Changes Required**:

**Step 1: Add Data Properties**

```javascript
data() {
  return {
    // ... existing data ...
    showApiKeyModal: false,
    generatedApiKey: null,
    apiKeyCopied: false,
    apiKeyConfirmed: false,
  }
}
```

**Step 2: Add Modal Template**

```vue
<!-- Add after existing wizardComplete modal -->
<v-dialog v-model="showApiKeyModal" max-width="600" persistent>
  <v-card>
    <v-card-title class="text-h5">
      🔑 Your API Key
    </v-card-title>

    <v-card-text>
      <v-alert type="warning" outlined class="mb-4">
        <strong>Important:</strong> Save this API key securely. You will need it to access the API from network clients.
      </v-alert>

      <v-text-field
        :value="generatedApiKey"
        label="API Key"
        readonly
        outlined
        dense
        :append-icon="apiKeyCopied ? 'mdi-check' : 'mdi-content-copy'"
        @click:append="copyApiKey"
      />

      <v-checkbox
        v-model="apiKeyConfirmed"
        label="I have saved this API key securely"
        color="primary"
      />
    </v-card-text>

    <v-card-actions>
      <v-spacer />
      <v-btn
        color="primary"
        :disabled="!apiKeyConfirmed"
        @click="proceedToRestartInstructions"
      >
        Continue
      </v-btn>
    </v-card-actions>
  </v-card>
</v-dialog>
```

**Step 3: Add Methods**

```javascript
methods: {
  async completeSetup() {
    try {
      const response = await setupService.completeSetup(this.setupData);

      if (response.api_key) {
        // LAN mode: show API key modal
        this.generatedApiKey = response.api_key;
        this.showApiKeyModal = true;
      } else {
        // Localhost mode: skip to completion
        this.wizardComplete = true;
      }
    } catch (error) {
      // ... error handling ...
    }
  },

  copyApiKey() {
    navigator.clipboard.writeText(this.generatedApiKey);
    this.apiKeyCopied = true;
    setTimeout(() => { this.apiKeyCopied = false; }, 3000);
  },

  proceedToRestartInstructions() {
    this.showApiKeyModal = false;
    this.showRestartModal = true; // Next modal
  }
}
```

**Testing Requirements**:
- Test modal shows only in LAN mode
- Test copy-to-clipboard works
- Test confirmation checkbox required
- Test localhost mode skips modal

**Estimated Effort**: 2 hours

---

#### 2.3 Add Restart Instructions Modal

**Modified File**: `frontend/src/views/SetupWizard.vue`

**Purpose**: Provide clear, platform-specific restart instructions

**Changes Required**:

**Step 1: Add Data Property**

```javascript
data() {
  return {
    // ... existing data ...
    showRestartModal: false,
    restartConfirmed: false,
  }
}
```

**Step 2: Detect Platform**

```javascript
computed: {
  platform() {
    const userAgent = window.navigator.userAgent.toLowerCase();
    if (userAgent.includes('win')) return 'windows';
    if (userAgent.includes('mac')) return 'macos';
    return 'linux';
  },

  restartInstructions() {
    const instructions = {
      windows: [
        'Open Command Prompt or PowerShell',
        'Navigate to the project directory',
        'Run: stop_giljo.bat',
        'Run: start_giljo.bat',
        'Wait 10-15 seconds for services to start'
      ],
      macos: [
        'Open Terminal',
        'Navigate to the project directory',
        'Run: ./stop_giljo.sh',
        'Run: ./start_giljo.sh',
        'Wait 10-15 seconds for services to start'
      ],
      linux: [
        'Open Terminal',
        'Navigate to the project directory',
        'Run: ./stop_giljo.sh',
        'Run: ./start_giljo.sh',
        'Wait 10-15 seconds for services to start'
      ]
    };
    return instructions[this.platform];
  }
}
```

**Step 3: Add Modal Template**

```vue
<v-dialog v-model="showRestartModal" max-width="700" persistent>
  <v-card>
    <v-card-title class="text-h5">
      🔄 Restart Services Required
    </v-card-title>

    <v-card-text>
      <v-alert type="info" outlined class="mb-4">
        Configuration changes require restarting GiljoAI services to take effect.
      </v-alert>

      <h3 class="mb-2">Restart Instructions ({{ platform }})</h3>
      <v-list dense>
        <v-list-item v-for="(step, index) in restartInstructions" :key="index">
          <v-list-item-icon>
            <v-icon>mdi-numeric-{{ index + 1 }}-circle</v-icon>
          </v-list-item-icon>
          <v-list-item-content>
            <v-list-item-title>{{ step }}</v-list-item-title>
          </v-list-item-content>
        </v-list-item>
      </v-list>

      <v-checkbox
        v-model="restartConfirmed"
        label="I have restarted the services"
        color="primary"
        class="mt-4"
      />
    </v-card-text>

    <v-card-actions>
      <v-spacer />
      <v-btn
        color="primary"
        :disabled="!restartConfirmed"
        @click="finishSetup"
      >
        Finish Setup
      </v-btn>
    </v-card-actions>
  </v-card>
</v-dialog>
```

**Step 4: Add Method**

```javascript
methods: {
  finishSetup() {
    this.showRestartModal = false;
    this.wizardComplete = true;
    // Optional v2: Call validateLanSetup() here
  }
}
```

**Testing Requirements**:
- Test platform detection (Windows/macOS/Linux)
- Test instructions display correctly
- Test confirmation required
- Test flow from API key → restart → completion

**Estimated Effort**: 1 hour

---

#### 2.4 Post-Restart Validation (Optional - v2)

**Modified File**: `frontend/src/views/SetupWizard.vue`

**Purpose**: Validate LAN setup after restart

**Implementation**:

```javascript
async finishSetup() {
  this.showRestartModal = false;

  // Optional: validate setup
  try {
    const validation = await setupService.validateLanSetup();
    if (!validation.success) {
      // Show validation errors
      this.validationErrors = validation.errors;
      this.showValidationErrorsModal = true;
      return;
    }
  } catch (error) {
    console.warn('Validation failed:', error);
  }

  this.wizardComplete = true;
}
```

**Priority**: Low (v2 feature)
**Estimated Effort**: 1 hour

---

### Phase 3: Services & Integration
**Priority**: MEDIUM
**Owner**: tdd-implementor
**Dependencies**: Phase 1 and Phase 2 components

#### 3.1 Update Setup Service

**Modified File**: `frontend/src/services/setupService.js`

**Changes Required**:

```javascript
// Add new methods

async detectIp() {
  /**
   * Detect server IP using backend endpoint.
   *
   * @returns {Promise<{hostname: string, local_ips: string[], primary_ip: string}>}
   */
  const response = await fetch(`${API_BASE_URL}/api/network/detect-ip`);
  if (!response.ok) {
    throw new Error('IP detection failed');
  }
  return response.json();
}

async completeSetup(setupData) {
  /**
   * Complete setup wizard.
   *
   * @param {Object} setupData - Setup configuration
   * @returns {Promise<{success: bool, message: string, api_key?: string, requires_restart: bool}>}
   */
  const response = await fetch(`${API_BASE_URL}/api/setup/complete`, {
    method: 'POST',
    headers: { 'Content-Type': 'application/json' },
    body: JSON.stringify(setupData)
  });

  if (!response.ok) {
    throw new Error('Setup completion failed');
  }

  return response.json();
}

async validateLanSetup() {
  /**
   * Validate LAN setup (optional v2 feature).
   *
   * @returns {Promise<{success: bool, checks: object, errors: string[]}>}
   */
  const response = await fetch(`${API_BASE_URL}/api/setup/validate-lan`);
  if (!response.ok) {
    throw new Error('Validation failed');
  }
  return response.json();
}
```

**Testing Requirements**:
- Test detectIp() returns expected structure
- Test completeSetup() handles both localhost and LAN modes
- Test error handling for network failures

**Estimated Effort**: 1 hour

---

#### 3.2 Update Pydantic Models

**Modified File**: `api/endpoints/setup.py`

**Changes Required**:

Already covered in Phase 1.2:
```python
class SetupCompleteResponse(BaseModel):
    success: bool
    message: str
    api_key: Optional[str] = None
    requires_restart: bool = False
```

**Testing Requirements**:
- Test model serialization with api_key
- Test model serialization without api_key (localhost mode)

**Estimated Effort**: 30 minutes (included in Phase 1.2)

---

### Phase 4: Admin Password Decision
**Priority**: LOW (Decision Required)
**Owner**: Product Decision / Orchestrator

#### Current State
The NetworkConfigStep.vue wizard collects admin username and password fields but:
- No user table in database
- No authentication logic for users
- Fields are displayed but not processed
- API key authentication is sufficient for LAN mode

#### Options Analysis

**Option A: Remove Admin Password Fields** (RECOMMENDED)

**Pros**:
- Simplifies wizard flow (less user friction)
- Reduces implementation complexity
- API keys are industry-standard for service auth
- Fewer security vulnerabilities (no password storage)
- Faster time to production

**Cons**:
- No user-specific authentication
- Cannot track which user performed actions
- Limits future multi-user features

**Implementation**:
- Remove username/password fields from NetworkConfigStep.vue
- Remove from request models
- ~80 lines of code removed
- 1 hour effort

---

**Option B: Implement User Account Creation**

**Pros**:
- Supports multi-user environments
- Audit logging per user
- Future-proof for RBAC features
- Better enterprise compatibility

**Cons**:
- Adds 2-3 days of development time
- Requires user table schema
- Password hashing/security concerns
- Session management complexity
- Not immediately needed for LAN mode

**Implementation**:
- Add users table to database
- Implement password hashing (bcrypt)
- Add user creation during setup
- Add login endpoint
- Add session management
- ~500 lines of code
- 2-3 days effort

---

#### Recommendation: **Option A** (Remove Admin Fields)

**Rationale**:
1. LAN mode authentication achieved via API keys (sufficient)
2. Wizard should be as simple as possible
3. User accounts can be added in future phase if needed
4. Prioritizes getting LAN mode working quickly
5. Reduces security surface area

**Decision Required**: Confirm with orchestrator before proceeding

---

## 4. Implementation Order (TDD Approach)

### Day 1: Backend Foundation

#### Morning (4 hours)
1. **backend-integration-tester** writes tests (1 hour):
   - `test_network_detect_ip_endpoint()`
   - `test_setup_complete_updates_cors_for_lan()`
   - `test_setup_complete_generates_api_key()`
   - `test_setup_localhost_mode_unchanged()`

2. **tdd-implementor** implements backend (3 hours):
   - Create `api/endpoints/network.py` with IP detection endpoint
   - Register network router in `api/app.py`
   - Add `update_cors_origins()` helper to setup.py
   - Modify `/api/setup/complete` endpoint for LAN mode
   - Update SetupCompleteResponse model
   - Run tests, iterate until green

#### Afternoon (2 hours)
3. **tdd-implementor** manual testing (1 hour):
   - Start API server
   - Test `/api/network/detect-ip` with curl
   - Test `/api/setup/complete` with LAN config
   - Verify config.yaml updated correctly
   - Verify CORS origins include LAN IP

4. **documentation-manager** creates session memory (1 hour):
   - Document implementation decisions
   - Capture API key storage decision (pending system-architect)
   - Record any issues encountered

---

### Day 2: Frontend Integration

#### Morning (4 hours)
5. **tdd-implementor** implements frontend updates (4 hours):
   - Update `setupService.js` with new methods
   - Add backend IP detection to NetworkConfigStep.vue
   - Create API key display modal in SetupWizard.vue
   - Create restart instructions modal in SetupWizard.vue
   - Wire up modal flow (complete → API key → restart → finish)

#### Afternoon (3 hours)
6. **frontend-tester** component testing (1 hour):
   - Test NetworkConfigStep IP detection (backend + WebRTC fallback)
   - Test SetupWizard modal flow
   - Test copy-to-clipboard functionality
   - Test platform-specific restart instructions

7. **Integration testing** (2 hours):
   - Complete full wizard flow on F: drive (server mode system)
   - Verify CORS origins updated in config.yaml
   - Verify API key displayed in modal
   - Restart services manually
   - Access API from localhost with API key
   - Access API from another device on LAN with API key
   - Verify no CORS errors in browser console
   - Test WebSocket connection from LAN device

---

### Day 3: Polish & Documentation

#### Morning (2 hours)
8. **Bug fixes** based on integration testing (1 hour)
9. **ux-designer** (optional) UI polish (1 hour):
   - Improve modal styling
   - Add animations
   - Refine error messages

#### Afternoon (2 hours)
10. **documentation-manager** updates documentation (2 hours):
    - Update QUICK_START.md with wizard screenshots
    - Add troubleshooting section to LAN_DEPLOYMENT.md
    - Create devlog completion report
    - Update MCP_TOOLS_MANUAL.md if needed

---

## 5. Testing Strategy

### Manual Testing Checklist

#### Regression Testing (Localhost Mode)
- [ ] Complete wizard in localhost mode
- [ ] Verify mode set to 'localhost' in config.yaml
- [ ] Verify API binds to 127.0.0.1
- [ ] Verify no API key required
- [ ] Verify CORS origins include localhost only
- [ ] Verify services start without errors

#### LAN Mode Testing
- [ ] Complete wizard in LAN mode
- [ ] Verify IP auto-detection works (backend endpoint)
- [ ] Verify multiple IPs show dropdown (if applicable)
- [ ] Verify CORS origins updated in config.yaml with LAN IP
- [ ] Verify hostname added to CORS origins (if provided)
- [ ] Verify API key generated and displayed in modal
- [ ] Verify copy-to-clipboard works
- [ ] Verify "I've saved this key" confirmation required
- [ ] Verify restart instructions modal shows
- [ ] Verify platform-specific instructions (Windows/macOS/Linux)
- [ ] Restart services manually (stop_giljo.bat && start_giljo.bat)
- [ ] Access API from localhost:7272 with API key in header
- [ ] Access API from LAN device (e.g., 192.168.1.50:7272) with API key
- [ ] Verify no CORS errors in browser console
- [ ] Access frontend from LAN device (e.g., 192.168.1.50:7274)
- [ ] Test WebSocket connection from LAN device
- [ ] Verify database stays on localhost (security check)

#### Edge Cases
- [ ] WebRTC fallback if backend IP detection fails
- [ ] Manual IP entry if auto-detection fails completely
- [ ] No network interfaces detected (should handle gracefully)
- [ ] Config.yaml already has CORS origins (should append, not replace)
- [ ] Wizard run twice (should handle re-configuration)

---

### Automated Tests Needed

#### Backend Integration Tests
**File**: `tests/integration/test_network_endpoints.py` (NEW)

```python
def test_network_detect_ip_endpoint():
    """Test IP detection endpoint returns valid structure"""
    response = client.get("/api/network/detect-ip")
    assert response.status_code == 200
    data = response.json()
    assert "hostname" in data
    assert "local_ips" in data
    assert "primary_ip" in data
    assert isinstance(data["local_ips"], list)

def test_network_detect_ip_filters_loopback():
    """Test that loopback IPs are filtered out"""
    response = client.get("/api/network/detect-ip")
    data = response.json()
    assert "127.0.0.1" not in data["local_ips"]
```

**File**: `tests/integration/test_setup_endpoints.py` (MODIFIED)

```python
def test_setup_complete_updates_cors_for_lan():
    """Test LAN setup updates CORS origins"""
    request_data = {
        "network_mode": "lan",
        "lan_config": {
            "server_ip": "192.168.1.50",
            "hostname": "TEST-SERVER"
        }
    }
    response = client.post("/api/setup/complete", json=request_data)
    assert response.status_code == 200

    # Verify config.yaml updated
    config = load_config()
    origins = config["security"]["cors"]["allowed_origins"]
    assert "http://192.168.1.50:7274" in origins
    assert "http://TEST-SERVER:7274" in origins

def test_setup_complete_generates_api_key():
    """Test LAN setup generates and returns API key"""
    request_data = {
        "network_mode": "lan",
        "lan_config": {"server_ip": "192.168.1.50"}
    }
    response = client.post("/api/setup/complete", json=request_data)
    data = response.json()

    assert data["success"] is True
    assert data["api_key"] is not None
    assert data["api_key"].startswith("gk_")
    assert data["requires_restart"] is True

def test_setup_localhost_mode_no_api_key():
    """Test localhost setup doesn't generate API key"""
    request_data = {"network_mode": "localhost"}
    response = client.post("/api/setup/complete", json=request_data)
    data = response.json()

    assert data["success"] is True
    assert data["api_key"] is None
    assert data["requires_restart"] is False
```

---

#### Frontend Component Tests
**File**: `frontend/tests/components/NetworkConfigStep.spec.js` (NEW)

```javascript
describe('NetworkConfigStep', () => {
  test('calls backend IP detection first', async () => {
    const mockDetectIp = jest.fn().mockResolvedValue({
      hostname: 'TEST-HOST',
      local_ips: ['192.168.1.50'],
      primary_ip: '192.168.1.50'
    });

    const wrapper = mount(NetworkConfigStep, {
      global: {
        mocks: {
          setupService: { detectIp: mockDetectIp }
        }
      }
    });

    await wrapper.vm.detectServerIP();
    expect(mockDetectIp).toHaveBeenCalled();
    expect(wrapper.vm.serverIP).toBe('192.168.1.50');
  });

  test('falls back to WebRTC if backend fails', async () => {
    const mockDetectIp = jest.fn().mockRejectedValue(new Error('Network error'));
    const wrapper = mount(NetworkConfigStep, {
      global: {
        mocks: {
          setupService: { detectIp: mockDetectIp }
        }
      }
    });

    await wrapper.vm.detectServerIP();
    expect(wrapper.vm.detectIPWebRTC).toHaveBeenCalled();
  });
});
```

**File**: `frontend/tests/views/SetupWizard.spec.js` (MODIFIED)

```javascript
describe('SetupWizard', () => {
  test('displays API key modal in LAN mode', async () => {
    const wrapper = mount(SetupWizard);

    // Mock LAN setup response
    wrapper.vm.completeSetup = jest.fn().mockResolvedValue({
      success: true,
      api_key: 'gk_test123',
      requires_restart: true
    });

    await wrapper.vm.completeSetup();
    expect(wrapper.vm.showApiKeyModal).toBe(true);
    expect(wrapper.vm.generatedApiKey).toBe('gk_test123');
  });

  test('copy to clipboard works', async () => {
    const wrapper = mount(SetupWizard);
    wrapper.vm.generatedApiKey = 'gk_test123';

    // Mock clipboard API
    Object.assign(navigator, {
      clipboard: {
        writeText: jest.fn().mockResolvedValue()
      }
    });

    await wrapper.vm.copyApiKey();
    expect(navigator.clipboard.writeText).toHaveBeenCalledWith('gk_test123');
    expect(wrapper.vm.apiKeyCopied).toBe(true);
  });

  test('restart instructions modal shows after API key', async () => {
    const wrapper = mount(SetupWizard);
    wrapper.vm.showApiKeyModal = true;
    wrapper.vm.apiKeyConfirmed = true;

    await wrapper.vm.proceedToRestartInstructions();
    expect(wrapper.vm.showApiKeyModal).toBe(false);
    expect(wrapper.vm.showRestartModal).toBe(true);
  });
});
```

---

## 6. Files to Create/Modify

### NEW FILES
| File | Purpose | Lines | Owner |
|------|---------|-------|-------|
| `api/endpoints/network.py` | IP detection endpoint | ~80 | tdd-implementor |
| `tests/integration/test_network_endpoints.py` | Network endpoint tests | ~100 | backend-integration-tester |
| `frontend/tests/components/NetworkConfigStep.spec.js` | Component tests | ~150 | frontend-tester |
| `frontend/tests/views/SetupWizard.spec.js` | Wizard flow tests | ~200 | frontend-tester |

---

### MODIFIED FILES
| File | Changes | Lines Added | Lines Removed | Owner |
|------|---------|-------------|---------------|-------|
| `api/endpoints/setup.py` | CORS update + API key generation | ~100 | ~10 | tdd-implementor |
| `api/app.py` | Register network router | ~5 | ~0 | tdd-implementor |
| `frontend/src/services/setupService.js` | New API methods | ~60 | ~0 | tdd-implementor |
| `frontend/src/views/SetupWizard.vue` | API key + restart modals | ~120 | ~0 | tdd-implementor |
| `frontend/src/components/setup/NetworkConfigStep.vue` | Backend IP detection | ~40 | ~0 | tdd-implementor |
| `tests/integration/test_setup_endpoints.py` | CORS + API key tests | ~80 | ~0 | backend-integration-tester |
| `docs/manuals/QUICK_START.md` | Wizard screenshots + troubleshooting | ~150 | ~0 | documentation-manager |
| `docs/deployment/LAN_DEPLOYMENT.md` | Wizard-based setup guide | ~100 | ~50 | documentation-manager |

---

### OPTIONAL REMOVALS (If Decision = Remove Admin Fields)
| File | Changes | Lines Removed | Owner |
|------|---------|---------------|-------|
| `frontend/src/components/setup/NetworkConfigStep.vue` | Remove admin username/password fields | ~80 | tdd-implementor |
| `api/endpoints/setup.py` | Remove admin field models | ~20 | tdd-implementor |

---

### TOTAL ESTIMATED CHANGES
- **New code**: ~530 lines (endpoints + tests + frontend)
- **Modified code**: ~655 lines (existing files enhanced)
- **Removed code**: ~100 lines (admin fields if removed, old code cleanup)
- **Net addition**: ~1,085 lines
- **Test coverage**: ~530 lines of tests (50% of new code)

---

## 7. Key Decisions & Recommendations

### Decision 1: Admin Password Handling
**Status**: AWAITING CONFIRMATION
**Recommendation**: **Remove from wizard** (Option A)

**Rationale**:
- API keys are industry-standard for service authentication
- Simplifies wizard flow (better UX)
- Reduces implementation time by 2-3 days
- Eliminates password security concerns
- Can add user accounts in future phase if needed

**Impact if accepted**:
- Remove ~80 lines from NetworkConfigStep.vue
- Remove ~20 lines from setup.py models
- Faster implementation (saves 2-3 days)

**Impact if rejected**:
- Add user table schema
- Implement password hashing + session management
- Add 2-3 days to timeline
- Increases security surface area

**Action**: Orchestrator to confirm decision before Phase 2 frontend work

---

### Decision 2: Hostname in CORS Origins
**Status**: RECOMMENDED (INCLUDE)
**Recommendation**: **Add hostname to CORS origins if provided**

**Rationale**:
- Allows users to access via friendly name (e.g., `http://my-server:7274`)
- No downside (extra origin doesn't hurt)
- Improves UX for users with DNS/mDNS configured
- Minimal code impact (~3 lines)

**Implementation**:
```python
if hostname:
    origins.append(f"http://{hostname}:{frontend_port}")
```

**Action**: Proceed with implementation (low-risk enhancement)

---

### Decision 3: Firewall Auto-Configuration
**Status**: KEEP MANUAL (RECOMMENDED)
**Recommendation**: **Do NOT auto-configure firewall**

**Rationale**:
- Too invasive to modify system firewall without explicit user action
- Cross-platform challenges (Windows Firewall, iptables, UFW, etc.)
- Security risk (could open ports unintentionally)
- User confirmation via checkboxes respects autonomy
- Better to provide clear instructions than automate poorly

**Current approach (keep)**:
- Display firewall configuration checkboxes
- User confirms they've configured firewall manually
- Provide platform-specific instructions

**Action**: No changes needed (current approach is correct)

---

### Decision 4: Post-Restart Validation
**Status**: OPTIONAL (v2 FEATURE)
**Recommendation**: **Phase 1 = Manual restart only, Phase 2 = Add validation**

**Rationale**:
- Validation endpoint adds complexity (2-3 hours)
- Manual restart instructions sufficient for v1
- Validation would improve UX but not critical for launch
- Can be added in follow-up iteration

**v1 Implementation** (recommended for initial release):
- Show restart instructions modal
- User confirms restart manually
- No automated validation

**v2 Implementation** (future enhancement):
- Add `GET /api/setup/validate-lan` endpoint
- Call after user confirms restart
- Show validation results with troubleshooting tips
- Auto-retry if validation fails

**Action**: Proceed with v1 (no validation), schedule v2 for next sprint

---

### Decision 5: API Key Storage Mechanism
**Status**: BLOCKED (AWAITING system-architect)
**Recommendation**: **Temporary insecure storage for v1, proper storage for v2**

**Context**:
The current code in `installer/core/config.py` generates API keys but storage location is unclear:
```python
# Where does this go?
api_key = f"gk_{secrets.token_urlsafe(32)}"
```

**Options**:
1. **Database table**: `CREATE TABLE api_keys (id, key_hash, name, created_at)`
   - Pros: Secure, scalable, allows multiple keys
   - Cons: Requires migration, hashing logic

2. **Config file**: `config["security"]["api_keys"] = [...]`
   - Pros: Simple, already have config system
   - Cons: Plaintext storage (security risk)

3. **Separate keys.yaml**: Similar to config but isolated
   - Pros: Separates secrets from config
   - Cons: Still plaintext, extra file to manage

**Temporary v1 Approach** (unblock implementation):
- Generate key in `/api/setup/complete`
- Return to user in API response
- Do NOT store anywhere (user responsible for saving)
- Add warning: "Save this key securely, we cannot recover it"

**Proper v2 Approach** (after system-architect decision):
- Implement chosen storage mechanism
- Add key hashing (bcrypt or similar)
- Add key regeneration endpoint
- Add key management UI

**Action**:
1. system-architect to decide storage mechanism
2. Proceed with v1 (no storage) to unblock testing
3. Implement proper storage in v2 follow-up

---

## 8. Success Criteria

### Must Have (v1 - MVP)

#### Configuration
- ✅ User completes wizard in LAN mode without errors
- ✅ config.yaml updated with:
  - `installation.mode = "lan"`
  - `services.api.host = "0.0.0.0"`
  - `security.cors.allowed_origins` includes LAN IP
  - `security.cors.allowed_origins` includes hostname (if provided)

#### API Key
- ✅ API key generated during setup (format: `gk_xxxxx...`)
- ✅ API key displayed to user in modal
- ✅ Copy-to-clipboard functionality works
- ✅ User must confirm they've saved the key before proceeding

#### Restart Flow
- ✅ Restart instructions modal shown after API key confirmation
- ✅ Platform-specific instructions displayed (Windows/macOS/Linux)
- ✅ User must confirm they've restarted before finishing

#### Network Access
- ✅ After manual restart, API accessible from localhost:7272 with API key
- ✅ After manual restart, API accessible from LAN device (e.g., 192.168.1.50:7272) with API key
- ✅ No CORS errors in browser console when accessing from LAN device
- ✅ Frontend accessible from LAN device (e.g., 192.168.1.50:7274)
- ✅ WebSocket connections work from LAN devices

#### Security
- ✅ API key authentication enforced in LAN mode (requests without key rejected)
- ✅ Database binds to localhost only (security boundary maintained)
- ✅ CORS origins do NOT include `*` wildcard (specific origins only)

#### Regression Testing
- ✅ Localhost mode still works (no API key, no CORS changes)
- ✅ Localhost mode doesn't show API key modal or restart instructions

---

### Nice to Have (v2 - Future Enhancements)

#### Validation
- 🔲 Post-restart validation endpoint (`/api/setup/validate-lan`)
- 🔲 Validation results displayed in UI with troubleshooting
- 🔲 Auto-retry if validation fails

#### User Accounts
- 🔲 User table in database
- 🔲 Admin account creation during setup
- 🔲 Login endpoint with session management
- 🔲 RBAC (role-based access control)

#### API Key Management
- 🔲 Proper storage (database with hashing)
- 🔲 Key regeneration endpoint
- 🔲 Multiple keys per deployment
- 🔲 Key management UI (list, create, revoke)

#### Firewall
- 🔲 Automated firewall configuration (optional, platform-specific)
- 🔲 Firewall validation (check if ports actually open)

#### UX Polish
- 🔲 Animated wizard transitions
- 🔲 Progress indicators during setup
- 🔲 Inline validation (real-time IP format checking)
- 🔲 QR code for API key (mobile device setup)

---

## 9. Risk Assessment

### HIGH RISK

#### Risk 1: CORS Misconfiguration
**Probability**: Medium
**Impact**: High (LAN access completely broken)

**Scenario**: CORS origins not added correctly, browser blocks all requests from LAN devices

**Symptoms**:
- Browser console: `Access to fetch at 'http://192.168.1.50:7272/api/...' blocked by CORS policy`
- API server logs show OPTIONS (preflight) requests failing
- Frontend loads but all API calls fail

**Mitigation**:
1. **Automated testing**: Integration test verifies CORS origins updated
2. **Manual testing**: Test from actual LAN device before release
3. **Troubleshooting guide**: Document how to verify CORS config
4. **Fallback**: Provide manual config.yaml editing instructions

**Contingency Plan**:
```yaml
# Manual fix if automated update fails
security:
  cors:
    allowed_origins:
      - http://127.0.0.1:7274
      - http://localhost:7274
      - http://192.168.1.50:7274  # Add manually
```

---

#### Risk 2: Services Not Restarted
**Probability**: High
**Impact**: High (User thinks LAN mode broken, files support ticket)

**Scenario**: User completes wizard but doesn't restart services, config changes not loaded

**Symptoms**:
- API still binds to 127.0.0.1 (not accessible from LAN)
- CORS still using old origins
- User reports "LAN mode doesn't work"

**Mitigation**:
1. **Clear modal**: Restart instructions modal with numbered steps
2. **Required confirmation**: User must check "I've restarted" to proceed
3. **Visual emphasis**: Use warning colors, icons in modal
4. **Documentation**: Quick Start guide includes restart steps
5. **Optional v2**: Post-restart validation to catch this issue

**Contingency Plan**:
- Troubleshooting section: "If LAN access not working, verify services restarted"
- Add `/api/setup/status` endpoint to check if config loaded

---

### MEDIUM RISK

#### Risk 3: API Key Lost
**Probability**: Medium
**Impact**: Medium (User can't authenticate, needs key regeneration)

**Scenario**: User closes modal without saving API key, can't access API

**Symptoms**:
- User completes setup
- Tries to access API from LAN
- Gets 401 Unauthorized (no valid key)

**Mitigation**:
1. **Warning alert**: "IMPORTANT: Save this key securely. You cannot recover it."
2. **Required checkbox**: "I have saved this API key securely"
3. **Copy button**: Make copying easy (one click)
4. **Documentation**: Provide key regeneration instructions (v2 feature)

**Contingency Plan** (v1 - no storage):
- User must re-run wizard to generate new key
- Document this clearly in modal

**Proper Fix** (v2 - with storage):
- Add `/api/setup/regenerate-key` endpoint
- Store hashed keys in database
- Allow key regeneration with existing key

---

#### Risk 4: Firewall Not Configured
**Probability**: Medium
**Impact**: Medium (LAN access fails, but fixable)

**Scenario**: User completes wizard but doesn't actually configure firewall

**Symptoms**:
- API server running and bound to 0.0.0.0
- LAN devices cannot connect (connection timeout)
- Windows Firewall blocking port 7272/7274

**Mitigation**:
1. **Required checkboxes**: User must check firewall configured
2. **Clear instructions**: Provide platform-specific firewall commands
3. **Testing instructions**: "Test from another device before finishing"
4. **Documentation**: Troubleshooting section for firewall issues

**Contingency Plan**:
```bash
# Windows Firewall commands (provide in docs)
netsh advfirewall firewall add rule name="GiljoAI API" dir=in action=allow protocol=TCP localport=7272
netsh advfirewall firewall add rule name="GiljoAI Frontend" dir=in action=allow protocol=TCP localport=7274
```

---

### LOW RISK

#### Risk 5: IP Detection Fails
**Probability**: Low
**Impact**: Low (User can manually enter IP)

**Scenario**: Both backend endpoint and WebRTC fail to detect IP

**Symptoms**:
- IP field empty after detection attempt
- User must enter IP manually

**Mitigation**:
1. **Fallback chain**: Backend → WebRTC → Manual entry
2. **Error message**: "Auto-detection failed. Please enter IP manually."
3. **Validation**: Check IP format (regex: `\d{1,3}\.\d{1,3}\.\d{1,3}\.\d{1,3}`)
4. **Help text**: "Run 'ipconfig' or 'ifconfig' to find your IP"

**Contingency Plan**:
- Allow manual IP entry at all times (not just on failure)
- Provide platform-specific IP detection commands in help text

---

#### Risk 6: Config.yaml Already Has Custom CORS Origins
**Probability**: Low
**Impact**: Low (Origins get duplicated or overwritten)

**Scenario**: User has manually added CORS origins, wizard overwrites them

**Symptoms**:
- Custom origins lost
- User reports LAN access works but other origins broken

**Mitigation**:
1. **Append, don't replace**: `origins.append()` instead of `origins = []`
2. **Duplicate check**: `if lan_origin not in origins:`
3. **Testing**: Test with pre-existing CORS origins

**Code Protection**:
```python
# Get existing origins or create list
origins = config["security"]["cors"].get("allowed_origins", [
    "http://127.0.0.1:7274",
    "http://localhost:7274"
])

# Add new origin if not present
if lan_origin not in origins:
    origins.append(lan_origin)
```

---

## 10. Timeline Estimate

### Phase 1: Backend Implementation
**Duration**: 4-6 hours

| Task | Owner | Time | Dependencies |
|------|-------|------|--------------|
| Write integration tests | backend-integration-tester | 1 hour | None |
| Create network endpoint | tdd-implementor | 1 hour | Tests written |
| Add CORS update logic | tdd-implementor | 1 hour | Tests written |
| Modify setup endpoint | tdd-implementor | 1 hour | Tests written |
| Manual testing | tdd-implementor | 1 hour | Backend deployed |
| Session memory | documentation-manager | 30 min | Backend complete |

**Deliverables**:
- `api/endpoints/network.py` with IP detection
- `api/endpoints/setup.py` updated with CORS + API key
- `tests/integration/test_network_endpoints.py`
- Backend session memory document

---

### Phase 2: Frontend Implementation
**Duration**: 4-6 hours

| Task | Owner | Time | Dependencies |
|------|-------|------|--------------|
| Update setupService.js | tdd-implementor | 1 hour | Backend deployed |
| Backend IP detection in wizard | tdd-implementor | 1 hour | setupService ready |
| API key modal | tdd-implementor | 1.5 hours | Backend returns key |
| Restart instructions modal | tdd-implementor | 1 hour | Wizard flow designed |
| Component tests | frontend-tester | 1.5 hours | Components complete |

**Deliverables**:
- Updated NetworkConfigStep.vue with backend detection
- API key display modal in SetupWizard.vue
- Restart instructions modal
- Frontend component tests

---

### Phase 3: Integration & Testing
**Duration**: 2-3 hours

| Task | Owner | Time | Dependencies |
|------|-------|------|--------------|
| Manual wizard flow testing | tdd-implementor | 1 hour | Frontend + backend ready |
| LAN access testing (F: drive) | tdd-implementor | 1 hour | Services restarted |
| Bug fixes | tdd-implementor | 1 hour | Issues identified |

**Deliverables**:
- Verified end-to-end wizard flow
- LAN access working from another device
- Known issues documented

---

### Phase 4: Documentation
**Duration**: 1-2 hours

| Task | Owner | Time | Dependencies |
|------|-------|------|--------------|
| Update QUICK_START.md | documentation-manager | 1 hour | Testing complete |
| Update LAN_DEPLOYMENT.md | documentation-manager | 30 min | Testing complete |
| Create devlog completion report | documentation-manager | 30 min | All work complete |

**Deliverables**:
- Updated Quick Start guide with wizard screenshots
- Updated LAN deployment guide
- Devlog completion report

---

### Critical Path
```
Day 1 Morning:  Tests → Backend endpoints
Day 1 Afternoon: Backend testing → Session memory
Day 2 Morning:  Frontend services → Wizard modals
Day 2 Afternoon: Component tests → Integration testing
Day 3 Morning:  Bug fixes → Documentation
```

**Total Estimate**: 11-17 hours
**Calendar Time**: 1.5-2 days (with breaks)

---

### Factors That Could Extend Timeline
- **API key storage decision delayed**: +2 hours (waiting for system-architect)
- **CORS issues during testing**: +1-2 hours (debugging browser behavior)
- **Frontend modal UX revisions**: +1-2 hours (design iterations)
- **LAN testing environment unavailable**: +1 hour (setup delay)
- **Regression issues in localhost mode**: +1-2 hours (unexpected side effects)

**Conservative Estimate**: 14-19 hours (2 days)

---

## 11. Post-Implementation Tasks

### 1. Update Documentation

#### QUICK_START.md
**Changes needed**:
- Add wizard screenshots (3-4 images)
- Document LAN mode selection
- Show API key modal screenshot
- Include restart instructions
- Add troubleshooting section

**Estimated effort**: 1 hour

---

#### LAN_DEPLOYMENT.md
**Changes needed**:
- Update setup section to reference wizard
- Remove manual config.yaml editing (wizard handles it)
- Keep firewall configuration section
- Add post-wizard validation steps

**Estimated effort**: 30 minutes

---

#### MCP_TOOLS_MANUAL.md (if needed)
**Changes needed**:
- Only if new MCP tools added (unlikely)
- Document any new endpoints used by tools

**Estimated effort**: 0 hours (probably not needed)

---

### 2. Create Session Memory

**File**: `docs/sessions/2025-10-06_lan_wizard_implementation.md`

**Content sections**:
- Implementation decisions made
- API key storage decision (temporary vs proper)
- Admin password decision (remove fields)
- Challenges encountered
- Testing results
- Known issues / future improvements

**Template**:
```markdown
# Session: LAN Wizard Implementation

**Date**: October 6, 2025
**Context**: Implementing LAN enablement in setup wizard

## Key Decisions
- Admin password fields removed (API keys sufficient)
- CORS origins include hostname if provided
- Firewall configuration remains manual
- Post-restart validation deferred to v2
- API key storage: temporary insecure for v1, proper storage for v2

## Technical Details
- Backend IP detection uses NetworkManager
- Frontend tries backend first, WebRTC fallback
- CORS update helper appends origins (doesn't replace)
- API key format: gk_{32 random bytes}

## Challenges Encountered
- [Document any issues during implementation]

## Testing Results
- [Summarize manual testing outcomes]

## Next Steps
- v2: Implement post-restart validation
- v2: Proper API key storage mechanism
- v2: User account management (if needed)

## Related Documentation
- docs/Oct_6_LAN_implementation.md (this plan)
- docs/devlogs/2025-10-06_lan_wizard_completion.md
```

**Estimated effort**: 30 minutes

---

### 3. Update Devlog

**File**: `docs/devlogs/2025-10-06_lan_wizard_completion.md`

**Content sections**:
- Objective (enable LAN mode in wizard)
- Implementation summary
- Files created/modified
- Testing performed
- Known issues
- Lessons learned

**Template**:
```markdown
# LAN Wizard Implementation - Completion Report

**Date**: October 6, 2025
**Agent**: tdd-implementor + backend-integration-tester + documentation-manager
**Status**: Complete

## Objective
Enable LAN mode configuration in setup wizard with CORS origin updates, API key generation, and restart instructions.

## Implementation

### Backend Changes
- Created `/api/network/detect-ip` endpoint using NetworkManager
- Enhanced `/api/setup/complete` to update CORS origins
- Added API key generation for LAN mode
- Updated SetupCompleteResponse model with api_key and requires_restart fields

### Frontend Changes
- Added backend IP detection to NetworkConfigStep.vue
- Created API key display modal in SetupWizard.vue
- Created restart instructions modal with platform detection
- Updated setupService.js with detectIp() and validateLanSetup() methods

### Testing
- Backend integration tests: 4 tests passing
- Frontend component tests: 3 tests passing
- Manual testing: LAN access verified from external device
- Regression testing: Localhost mode still works

## Challenges
- [Document challenges]

## Files Modified
- api/endpoints/network.py (NEW - 80 lines)
- api/endpoints/setup.py (MODIFIED - +100 lines)
- frontend/src/views/SetupWizard.vue (MODIFIED - +120 lines)
- [... other files ...]

## Next Steps
- v2: Post-restart validation endpoint
- v2: Proper API key storage
- v2: User account creation (if product decides to add)

## Lessons Learned
- [Capture insights]
```

**Estimated effort**: 30 minutes

---

### 4. Create Troubleshooting Guide

**File**: Add section to `docs/manuals/QUICK_START.md`

**Content**:
```markdown
## Troubleshooting LAN Setup

### LAN Access Not Working

**Symptom**: Cannot access API from LAN device, connection timeout

**Possible Causes**:
1. Services not restarted after wizard
2. Firewall blocking ports
3. Incorrect IP address

**Solutions**:
1. Restart services:
   ```bash
   # Windows
   stop_giljo.bat && start_giljo.bat

   # Linux/macOS
   ./stop_giljo.sh && ./start_giljo.sh
   ```

2. Verify firewall:
   ```bash
   # Windows - Check rules
   netsh advfirewall firewall show rule name="GiljoAI API"

   # Add if missing
   netsh advfirewall firewall add rule name="GiljoAI API" dir=in action=allow protocol=TCP localport=7272
   ```

3. Verify IP address:
   ```bash
   ipconfig  # Windows
   ifconfig  # Linux/macOS
   ```

---

### CORS Errors in Browser Console

**Symptom**: `Access to fetch blocked by CORS policy`

**Cause**: Frontend origin not in CORS allowed origins

**Solution**:
1. Check config.yaml:
   ```yaml
   security:
     cors:
       allowed_origins:
         - http://192.168.1.50:7274  # Should include your LAN IP
   ```

2. If missing, add manually and restart services

3. Verify frontend port matches (default 7274)

---

### API Key Authentication Fails

**Symptom**: `401 Unauthorized` when calling API

**Cause**: Missing or incorrect API key

**Solution**:
1. Verify API key in request header:
   ```bash
   curl -H "X-API-Key: gk_your_key_here" http://192.168.1.50:7272/api/projects
   ```

2. If key lost, re-run wizard to generate new key

3. Future v2: Use key regeneration endpoint

---

### Wizard Hangs on IP Detection

**Symptom**: "Detecting IP..." spinner never completes

**Cause**: Network detection failed

**Solution**:
1. Click "Skip" or "Manual Entry"
2. Manually enter IP from `ipconfig` / `ifconfig`
3. Continue wizard
```

**Estimated effort**: 30 minutes

---

### Summary of Post-Implementation Tasks
| Task | File | Effort | Owner |
|------|------|--------|-------|
| Update Quick Start | QUICK_START.md | 1 hour | documentation-manager |
| Update LAN Deployment | LAN_DEPLOYMENT.md | 30 min | documentation-manager |
| Create session memory | sessions/2025-10-06_lan_wizard.md | 30 min | documentation-manager |
| Create devlog | devlogs/2025-10-06_lan_wizard.md | 30 min | documentation-manager |
| Add troubleshooting | QUICK_START.md | 30 min | documentation-manager |

**Total Documentation Effort**: 3 hours

---

## 12. Next Steps

### Immediate Actions (Before Implementation Starts)

1. **Orchestrator Decision Required**:
   - ✅ Approve overall implementation plan
   - ✅ Confirm admin password removal (Decision 1)
   - ✅ Confirm API key storage approach (Decision 5)

2. **system-architect Consultation Required**:
   - ⚠️ Clarify API key storage mechanism (database vs config vs separate file)
   - ⚠️ Confirm CORS update approach is architecturally sound
   - ⚠️ Review security implications of temporary insecure key storage (v1)

3. **Agent Coordination**:
   - 📋 backend-integration-tester: Ready to write tests (Day 1 start)
   - 📋 tdd-implementor: Ready to implement backend (Day 1)
   - 📋 tdd-implementor: Ready to implement frontend (Day 2)
   - 📋 documentation-manager: Ready for documentation phase (Day 3)

---

### Implementation Sequence

**Day 1: Backend Foundation**
```
1. Orchestrator approves plan
2. backend-integration-tester writes tests (1 hour)
3. tdd-implementor implements network endpoint (1 hour)
4. tdd-implementor implements setup endpoint updates (2 hours)
5. tdd-implementor manual testing (1 hour)
6. documentation-manager creates session memory (30 min)
```

**Day 2: Frontend Integration**
```
1. tdd-implementor updates setupService.js (1 hour)
2. tdd-implementor adds backend IP detection (1 hour)
3. tdd-implementor creates API key modal (1.5 hours)
4. tdd-implementor creates restart modal (1 hour)
5. frontend-tester component testing (1.5 hours)
```

**Day 3: Testing & Documentation**
```
1. tdd-implementor integration testing on F: drive (2 hours)
2. tdd-implementor bug fixes (1 hour)
3. documentation-manager updates all docs (2 hours)
```

---

### Post-Implementation Review

**After completion, schedule review meeting to**:
- Demo LAN wizard flow
- Review testing results
- Discuss lessons learned
- Plan v2 features:
  - Post-restart validation
  - Proper API key storage
  - Key regeneration endpoint
  - User account management (if decided)

---

### Future Enhancements (v2 Backlog)

**Priority 1 (Next Sprint)**:
- ✅ Proper API key storage (database with hashing)
- ✅ Post-restart validation endpoint
- ✅ API key regeneration endpoint

**Priority 2 (Future)**:
- User account creation
- Multiple API keys per deployment
- Key management UI
- Automated firewall configuration

**Priority 3 (Nice to Have)**:
- QR code for API key (mobile setup)
- Network diagnostics tool
- Bandwidth monitoring

---

## Document Metadata

**Created**: October 6, 2025
**Status**: Planning Phase → Ready for Implementation
**Next Review**: After implementation completion (estimated October 7-8, 2025)
**Owner**: GiljoAI Development Team
**Primary Agents**: tdd-implementor, backend-integration-tester, documentation-manager
**Decisions Required**: Admin password removal, API key storage mechanism
**Estimated Effort**: 11-17 hours (1.5-2 days)
**Risk Level**: Medium (CORS and restart instructions are critical)

---

**End of Implementation Plan**
