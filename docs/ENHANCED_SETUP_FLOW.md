# Enhanced Setup Flow & Two-Phase Authentication

**Document Version**: 10_13_2025  
**Status**: Single Source of Truth  
**Last Updated**: October 13, 2025

---

## Overview

GiljoAI MCP v3.0 implements an **enhanced two-phase setup flow** that separates welcome/password setup from authenticated configuration. This redesign eliminates authentication confusion and ensures WebSocket connectivity throughout the setup process.

### Two-Phase Design Principles

**Phase 1: Welcome & Password Setup** (Unauthenticated)
- Clean password setup without authentication context
- Security-focused first impression
- Clear progression to authentication

**Phase 2: Authenticated Setup** (Post-Login)  
- WebSocket-enabled real-time updates
- Full system access for configuration
- Persistent authentication context

---

## Authentication Flow Architecture

### Before: Broken Single-Phase Flow

```
Setup Wizard → Change Password → Still Unauthenticated → WebSocket Fails → Confusion
```

**Problems with Original Flow**:
- ❌ Users remained unauthenticated during entire setup
- ❌ ConnectionStatus showed "Disconnected" throughout setup
- ❌ No WebSocket connection for real-time updates  
- ❌ Broken authentication chain after password change
- ❌ User confusion about authentication state

### After: Enhanced Two-Phase Flow

```
Welcome → Set Password → Login → Setup (Connected) → Dashboard
```

**Benefits of Enhanced Flow**:
- ✅ Clear authentication boundary: Welcome (unauth) → Login → Setup (auth)
- ✅ WebSocket connected throughout authenticated portions
- ✅ ConnectionStatus shows "Connected" during setup
- ✅ Logical user journey: Password → Login → Configure → Use
- ✅ Real-time updates during setup process

---

## Implementation Components

### 1. Welcome Password Setup Component

**Location**: `frontend/src/components/setup/WelcomePasswordStep.vue`

**Purpose**: Standalone password setup before authentication

**Key Features**:
- Clean, focused UI matching Login.vue patterns
- Password validation with strength meter
- Automatic redirect to login after success
- No authentication context required

**Component Structure**:
```vue
<template>
  <v-container class="fill-height" fluid>
    <v-row justify="center" align="center">
      <v-col cols="12" sm="8" md="6" lg="4">
        <v-card class="elevation-12">
          <v-card-title class="text-h4 text-center pa-8">
            <div class="d-flex flex-column align-center">
              <v-icon size="64" color="primary" class="mb-4">
                mdi-shield-key
              </v-icon>
              Welcome to GiljoAI MCP
            </div>
          </v-card-title>
          
          <v-card-text class="pa-8">
            <p class="text-h6 text-center mb-6 text-medium-emphasis">
              Set your admin password to continue
            </p>
            
            <v-form @submit.prevent="submitPassword" ref="passwordForm">
              <v-text-field
                v-model="password"
                label="New Password"
                type="password"
                variant="outlined"
                :rules="passwordRules"
                required
                class="mb-4"
              />
              
              <v-text-field
                v-model="confirmPassword"
                label="Confirm Password"
                type="password"
                variant="outlined"
                :rules="confirmPasswordRules"
                required
                class="mb-4"
              />
              
              <!-- Password Strength Indicator -->
              <div class="password-strength mb-4">
                <v-progress-linear
                  :model-value="passwordStrength.score * 25"
                  :color="passwordStrength.color"
                  height="8"
                  rounded
                />
                <p class="text-caption mt-2">
                  Strength: {{ passwordStrength.label }}
                </p>
              </div>
              
              <!-- Password Requirements -->
              <div class="password-requirements mb-6">
                <p class="text-subtitle2 mb-2">Password Requirements:</p>
                <div class="requirements-list">
                  <div 
                    v-for="requirement in passwordRequirements" 
                    :key="requirement.key"
                    class="requirement-item d-flex align-center"
                  >
                    <v-icon 
                      :color="requirement.met ? 'success' : 'grey'"
                      size="small"
                      class="me-2"
                    >
                      {{ requirement.met ? 'mdi-check-circle' : 'mdi-circle-outline' }}
                    </v-icon>
                    <span 
                      :class="requirement.met ? 'text-success' : 'text-grey'"
                      class="text-caption"
                    >
                      {{ requirement.text }}
                    </span>
                  </div>
                </div>
              </div>
              
              <v-btn
                type="submit"
                color="primary"
                size="large"
                block
                :loading="isSubmitting"
                :disabled="!isFormValid"
              >
                Continue to Login
              </v-btn>
            </v-form>
            
            <!-- Error Display -->
            <v-alert
              v-if="error"
              type="error"
              class="mt-4"
              dismissible
              @click:close="error = null"
            >
              {{ error }}
            </v-alert>
          </v-card-text>
        </v-card>
      </v-col>
    </v-row>
  </v-container>
</template>

<script setup>
import { ref, computed, watch } from 'vue'
import { useRouter } from 'vue-router'
import api from '@/utils/api'

const router = useRouter()

// Form state
const password = ref('')
const confirmPassword = ref('')
const isSubmitting = ref(false)
const error = ref(null)

// Password validation
const passwordRules = [
  v => !!v || 'Password is required',
  v => v.length >= 12 || 'Password must be at least 12 characters',
  v => /[A-Z]/.test(v) || 'Password must contain an uppercase letter',
  v => /[a-z]/.test(v) || 'Password must contain a lowercase letter',
  v => /[0-9]/.test(v) || 'Password must contain a number',
  v => /[!@#$%^&*()_+\-=\[\]{};':"\\|,.<>\/?]/.test(v) || 'Password must contain a special character'
]

const confirmPasswordRules = [
  v => !!v || 'Confirm password is required',
  v => v === password.value || 'Passwords must match'
]

// Password strength calculation
const passwordStrength = computed(() => {
  const pass = password.value
  if (!pass) return { score: 0, label: 'No password', color: 'grey' }
  
  let score = 0
  
  // Length scoring
  if (pass.length >= 12) score += 1
  if (pass.length >= 16) score += 1
  
  // Character variety scoring  
  if (/[A-Z]/.test(pass)) score += 1
  if (/[a-z]/.test(pass)) score += 1
  if (/[0-9]/.test(pass)) score += 1
  if (/[!@#$%^&*()_+\-=\[\]{};':"\\|,.<>\/?]/.test(pass)) score += 1
  
  // Complexity bonus
  if (score >= 5) score += 1
  
  const labels = ['Very Weak', 'Weak', 'Fair', 'Good', 'Strong', 'Very Strong']
  const colors = ['error', 'warning', 'orange', 'primary', 'success', 'success']
  
  return {
    score: Math.min(score, 5),
    label: labels[Math.min(score, 5)],
    color: colors[Math.min(score, 5)]
  }
})

// Password requirements tracking
const passwordRequirements = computed(() => [
  { key: 'length', text: 'At least 12 characters', met: password.value.length >= 12 },
  { key: 'uppercase', text: 'One uppercase letter', met: /[A-Z]/.test(password.value) },
  { key: 'lowercase', text: 'One lowercase letter', met: /[a-z]/.test(password.value) },
  { key: 'number', text: 'One number', met: /[0-9]/.test(password.value) },
  { key: 'special', text: 'One special character', met: /[!@#$%^&*()_+\-=\[\]{};':"\\|,.<>\/?]/.test(password.value) },
  { key: 'match', text: 'Passwords match', met: password.value === confirmPassword.value && password.value.length > 0 }
])

// Form validation
const isFormValid = computed(() => {
  return passwordRequirements.value.every(req => req.met) && 
         passwordStrength.value.score >= 3 // Minimum "Good" strength
})

// Submit password setup
const submitPassword = async () => {
  if (!isFormValid.value) return
  
  isSubmitting.value = true
  error.value = null
  
  try {
    const response = await api.post('/api/setup/welcome-password', {
      password: password.value,
      confirmPassword: confirmPassword.value
    })
    
    if (response.data.success) {
      // Redirect to login page
      await router.push('/login?message=password-set&username=admin')
    }
  } catch (err) {
    error.value = err.response?.data?.detail || 'Failed to set password. Please try again.'
  } finally {
    isSubmitting.value = false
  }
}
</script>
```

### 2. Welcome Setup View Container

**Location**: `frontend/src/views/WelcomeSetup.vue`

**Purpose**: Route container for welcome password setup

**Simple Implementation**:
```vue
<template>
  <div class="welcome-setup">
    <WelcomePasswordStep />
  </div>
</template>

<script setup>
import WelcomePasswordStep from '@/components/setup/WelcomePasswordStep.vue'

// Route guard handled at router level
// This component only renders when appropriate
</script>

<style scoped>
.welcome-setup {
  min-height: 100vh;
  background: linear-gradient(135deg, #667eea 0%, #764ba2 100%);
}
</style>
```

### 3. Enhanced Router Configuration  

**Location**: `frontend/src/router/index.js`

**New Route Definition**:
```javascript
{
  path: '/welcome-setup',
  name: 'WelcomeSetup',
  component: () => import('@/views/WelcomeSetup.vue'),
  meta: { 
    requiresAuth: false,
    hideNavigation: true,
    title: 'Welcome Setup'
  }
}
```

**Enhanced Route Guards**:
```javascript
router.beforeEach(async (to, from, next) => {
  try {
    // Check setup status
    const setupStatus = await api.get('/api/setup/status')
    const {
      password_setup_complete,
      user_authenticated, 
      setup_wizard_complete
    } = setupStatus.data
    
    // Route logic for two-phase setup
    if (!password_setup_complete) {
      // Phase 1: Welcome password setup
      if (to.path !== '/welcome-setup') {
        return next('/welcome-setup')
      }
    } else if (!user_authenticated) {
      // Between phases: Redirect to login
      if (to.path !== '/login') {
        return next('/login')
      }
    } else if (!setup_wizard_complete) {
      // Phase 2: Authenticated setup wizard
      if (to.path !== '/setup') {
        return next('/setup')
      }
    } else if (to.path === '/welcome-setup' || to.path === '/setup') {
      // Setup complete, redirect to dashboard
      return next('/dashboard')
    }
    
    next()
  } catch (error) {
    console.error('Route guard error:', error)
    next('/welcome-setup') // Safe fallback
  }
})
```

### 4. Backend API Enhancements

**Location**: `api/endpoints/setup.py`

**New Endpoint**:
```python
@router.post("/welcome-password")
async def set_welcome_password(
    request: WelcomePasswordRequest,
    session: AsyncSession = Depends(get_db_session)
):
    """Set initial admin password during welcome setup"""
    
    # Validate password requirements
    if not validate_password_complexity(request.password):
        raise HTTPException(
            status_code=400,
            detail="Password does not meet complexity requirements"
        )
    
    if request.password != request.confirm_password:
        raise HTTPException(
            status_code=400, 
            detail="Passwords do not match"
        )
    
    try:
        # Update admin user password
        admin_user = await session.execute(
            select(User).where(
                and_(User.username == "admin", User.tenant_key == "default")
            )
        )
        admin_user = admin_user.scalar_one_or_none()
        
        if not admin_user:
            raise HTTPException(status_code=404, detail="Admin user not found")
        
        # Hash and set new password
        admin_user.password_hash = hash_password(request.password)
        
        # Update setup state
        setup_state = await session.execute(
            select(SetupState).where(SetupState.tenant_key == "default")
        )
        setup_state = setup_state.scalar_one_or_none()
        
        if setup_state:
            setup_state.default_password_active = False
            setup_state.password_setup_complete = True
            setup_state.password_changed_at = datetime.utcnow()
        
        await session.commit()
        
        return {
            "success": True,
            "message": "Password set successfully",
            "next_step": "login"
        }
        
    except Exception as e:
        await session.rollback()
        raise HTTPException(
            status_code=500,
            detail=f"Failed to set password: {str(e)}"
        )

class WelcomePasswordRequest(BaseModel):
    password: str = Field(..., min_length=12)
    confirm_password: str = Field(..., min_length=12)
    
    @validator('password')
    def validate_password_complexity(cls, v):
        """Validate password meets complexity requirements"""
        
        requirements = [
            (len(v) >= 12, "Password must be at least 12 characters"),
            (re.search(r'[A-Z]', v), "Password must contain an uppercase letter"),
            (re.search(r'[a-z]', v), "Password must contain a lowercase letter"),
            (re.search(r'[0-9]', v), "Password must contain a number"),
            (re.search(r'[!@#$%^&*()_+\-=\[\]{};\':"\\|,.<>\/?]', v), 
             "Password must contain a special character")
        ]
        
        for requirement, message in requirements:
            if not requirement:
                raise ValueError(message)
                
        return v
```

**Enhanced Setup Status Endpoint**:
```python
@router.get("/status")
async def get_setup_status(session: AsyncSession = Depends(get_db_session)):
    """Get enhanced setup status for two-phase flow"""
    
    setup_state = await session.execute(
        select(SetupState).where(SetupState.tenant_key == "default")
    )
    setup_state = setup_state.scalar_one_or_none()
    
    if not setup_state:
        # Create default setup state if missing
        setup_state = SetupState(
            tenant_key="default",
            database_initialized=True,
            password_setup_complete=False,
            setup_completed=False
        )
        session.add(setup_state)
        await session.commit()
    
    return {
        "database_initialized": setup_state.database_initialized,
        "password_setup_complete": setup_state.password_setup_complete,
        "user_authenticated": False,  # Will be True if JWT valid
        "setup_wizard_complete": setup_state.setup_completed,
        "mcp_configured": setup_state.mcp_enabled,
        "serena_configured": setup_state.serena_enabled,
        "setup_version": "3.0.0"
    }
```

---

## User Experience Flow

### Phase 1: Welcome Password Setup

**Step 1: Fresh Installation Access**
```
User visits: http://localhost:7274
↓
Router detects: password_setup_complete = false
↓  
Auto-redirect to: /welcome-setup
```

**Step 2: Welcome Screen**
```
┌─────────────────────────────────────────────────────┐
│                 🔐 Welcome to GiljoAI MCP          │
│                                                     │
│        Set your admin password to continue         │
│                                                     │
│  New Password:     [                    ]          │
│  Confirm Password: [                    ]          │
│                                                     │
│  Password Strength: ████████░░ Strong              │
│                                                     │
│  Requirements:                                      │
│  ✓ At least 12 characters                         │
│  ✓ One uppercase letter                           │
│  ✓ One lowercase letter                           │  
│  ✓ One number                                      │
│  ✓ One special character                           │
│  ✓ Passwords match                                 │
│                                                     │
│         [ Continue to Login ]                      │
└─────────────────────────────────────────────────────┘
```

**Step 3: Password Submission**
- Real-time validation during typing
- Strength meter updates dynamically  
- Requirements checklist visual feedback
- Submit only when all requirements met

**Step 4: Automatic Redirect**
```
POST /api/setup/welcome-password
↓
Success response
↓
Router redirect: /login?message=password-set&username=admin
```

### Phase 2: Login & Authenticated Setup

**Step 5: Login Screen**
```
┌─────────────────────────────────────────────────────┐
│                   🔐 Login                         │
│                                                     │
│  ✅ Password set successfully!                     │
│     Please login with your new credentials         │
│                                                     │
│  Username: [admin              ] (pre-filled)      │
│  Password: [                   ]                   │
│                                                     │
│            [ Login ]                               │
└─────────────────────────────────────────────────────┘
```

**Step 6: Authenticated Setup Wizard**
```
After successful login:
POST /api/auth/login
↓
JWT token received & stored
↓
Router redirect: /setup (authenticated context)
↓
WebSocket connection established with JWT
```

**Step 7: Setup Wizard (3 Steps)**
- **Step 1**: MCP Configuration (with real-time updates)
- **Step 2**: Serena Activation (WebSocket progress)
- **Step 3**: Complete (connection status: Connected)

### Phase 3: Dashboard Access

**Step 8: Setup Complete**
```
POST /api/setup/complete
↓  
setup_wizard_complete = true
↓
Router redirect: /dashboard
↓
Full system access with persistent authentication
```

---

## WebSocket Integration

### Setup-Phase WebSocket Behavior

**Before Authentication** (Welcome Setup):
```javascript
// No WebSocket connection during welcome setup
// Clean, focused password setup without distractions
```

**During Setup Wizard** (Authenticated):
```javascript
// WebSocket connected with JWT token
const token = localStorage.getItem('auth_token')
const ws = new WebSocket(`ws://localhost:7272/ws/setup?token=${token}`)

ws.onopen = () => {
  // ConnectionStatus shows "Connected" 
  updateConnectionStatus('connected')
}

ws.onmessage = (event) => {
  const data = JSON.parse(event.data)
  
  switch (data.type) {
    case 'setup_progress':
      updateSetupProgress(data.step, data.status)
      break
      
    case 'mcp_configuration':
      updateMCPStatus(data.status)
      break
      
    case 'serena_status':  
      updateSerenaActivation(data.enabled)
      break
  }
}
```

### Real-Time Setup Updates

**MCP Configuration Progress**:
```javascript
// Real-time feedback during MCP setup
{
  type: 'mcp_configuration',
  status: 'downloading',
  message: 'Generating Claude Desktop configuration...',
  progress: 50
}
```

**Serena Installation Status**:
```javascript
// Live updates during Serena setup
{
  type: 'serena_status',
  status: 'installing', 
  message: 'Installing Serena MCP server via uvx...',
  progress: 75
}
```

---

## Technical Implementation Details

### Database Schema Updates

**SetupState Model Enhancement**:
```python
class SetupState(Base):
    __tablename__ = 'setup_state'
    
    tenant_key = Column(String(36), primary_key=True)
    
    # Existing fields
    database_initialized = Column(Boolean, default=False)
    setup_completed = Column(Boolean, default=False)
    
    # NEW: Two-phase setup fields
    password_setup_complete = Column(Boolean, default=False) 
    password_changed_at = Column(DateTime)
    
    # Authentication tracking
    default_password_active = Column(Boolean, default=True)
    
    # Setup wizard state
    mcp_enabled = Column(Boolean, default=False)
    serena_enabled = Column(Boolean, default=False)
    
    # Timestamps
    created_at = Column(DateTime, default=func.now())
    updated_at = Column(DateTime, default=func.now(), onupdate=func.now())
```

### Router Logic Flow

**Complete Route Decision Tree**:
```javascript
async function determineRoute(to, from) {
  const setupStatus = await getSetupStatus()
  
  // Phase 1: Welcome password setup (unauthenticated)
  if (!setupStatus.password_setup_complete) {
    return to.path !== '/welcome-setup' ? '/welcome-setup' : null
  }
  
  // Between phases: Must authenticate
  const isAuthenticated = await checkAuthToken()
  if (!isAuthenticated) {
    return to.path !== '/login' ? '/login' : null
  }
  
  // Phase 2: Authenticated setup wizard
  if (!setupStatus.setup_wizard_complete) {
    return to.path !== '/setup' ? '/setup' : null
  }
  
  // Setup complete: Normal application flow
  if (to.path === '/welcome-setup' || to.path === '/setup') {
    return '/dashboard'
  }
  
  return null // Continue to requested route
}
```

### Error Handling & Recovery

**Password Setup Errors**:
```javascript
// Handle password setup failures gracefully
try {
  await submitWelcomePassword(password)
} catch (error) {
  if (error.response?.status === 400) {
    // Validation errors - show specific feedback
    showPasswordValidationError(error.response.data.detail)
  } else if (error.response?.status === 500) {
    // Server errors - offer recovery options
    showServerErrorWithRecovery()
  } else {
    // Network errors - retry mechanism
    showNetworkErrorWithRetry()
  }
}
```

**Setup State Recovery**:
```python
# Backend recovery for inconsistent setup states
@router.post("/reset-setup-state")
async def reset_setup_state(
    tenant_key: str = "default",
    session: AsyncSession = Depends(get_db_session)
):
    """Reset setup state for recovery purposes"""
    
    setup_state = await get_setup_state(tenant_key, session)
    
    # Reset to appropriate phase
    setup_state.password_setup_complete = False
    setup_state.setup_completed = False
    setup_state.default_password_active = True
    
    await session.commit()
    
    return {"message": "Setup state reset to welcome phase"}
```

---

## Testing Strategy

### Component Testing

**WelcomePasswordStep Component Tests**:
```javascript
describe('WelcomePasswordStep', () => {
  test('validates password complexity requirements', async () => {
    const wrapper = mount(WelcomePasswordStep)
    
    await wrapper.find('input[type="password"]').setValue('weak')
    expect(wrapper.vm.passwordStrength.score).toBe(0)
    
    await wrapper.find('input[type="password"]').setValue('StrongPassword123!')
    expect(wrapper.vm.passwordStrength.score).toBeGreaterThan(3)
  })
  
  test('requires password confirmation match', async () => {
    const wrapper = mount(WelcomePasswordStep)
    
    await wrapper.find('input[type="password"]').setValue('StrongPassword123!')
    await wrapper.findAll('input[type="password"]')[1].setValue('DifferentPassword')
    
    expect(wrapper.vm.isFormValid).toBe(false)
  })
  
  test('submits password and redirects to login', async () => {
    const mockRouter = { push: jest.fn() }
    const wrapper = mount(WelcomePasswordStep, {
      global: { mocks: { $router: mockRouter } }
    })
    
    await wrapper.vm.submitPassword()
    
    expect(mockRouter.push).toHaveBeenCalledWith(
      '/login?message=password-set&username=admin'
    )
  })
})
```

### Integration Testing

**Two-Phase Flow Integration**:
```python
async def test_two_phase_setup_flow():
    """Test complete two-phase setup integration"""
    
    # Phase 1: Welcome password setup
    response = await client.post("/api/setup/welcome-password", json={
        "password": "SecurePassword123!",
        "confirm_password": "SecurePassword123!"
    })
    assert response.status_code == 200
    
    # Verify setup state updated
    status = await client.get("/api/setup/status")
    assert status.json()["password_setup_complete"] is True
    
    # Phase 2: Login and authenticate
    login_response = await client.post("/api/auth/login", json={
        "username": "admin",
        "password": "SecurePassword123!"
    })
    assert login_response.status_code == 200
    
    token = login_response.json()["access_token"]
    
    # Phase 2: Authenticated setup wizard
    headers = {"Authorization": f"Bearer {token}"}
    
    # Complete setup wizard
    complete_response = await client.post(
        "/api/setup/complete", 
        headers=headers
    )
    assert complete_response.status_code == 200
    
    # Verify final setup state
    final_status = await client.get("/api/setup/status", headers=headers)
    assert final_status.json()["setup_wizard_complete"] is True
```

### End-to-End Testing

**Complete User Journey**:
```javascript  
describe('Enhanced Setup Flow E2E', () => {
  test('complete two-phase setup journey', async () => {
    // Start fresh installation
    await page.goto('http://localhost:7274')
    
    // Phase 1: Welcome setup
    await expect(page).toHaveURL('/welcome-setup')
    
    await page.fill('input[type="password"]', 'SecurePassword123!')
    await page.fill('input[type="password"]:nth-child(2)', 'SecurePassword123!')
    await page.click('button:has-text("Continue to Login")')
    
    // Verify redirect to login
    await expect(page).toHaveURL('/login')
    await expect(page.locator('.success-message')).toContainText('Password set')
    
    // Phase 2: Login
    await page.fill('input[name="password"]', 'SecurePassword123!')
    await page.click('button:has-text("Login")')
    
    // Phase 2: Authenticated setup
    await expect(page).toHaveURL('/setup')
    await expect(page.locator('.connection-status')).toContainText('Connected')
    
    // Complete setup wizard
    await page.click('button:has-text("Skip")') // MCP step
    await page.click('button:has-text("Skip")') // Serena step  
    await page.click('button:has-text("Go to Dashboard")')
    
    // Verify final state
    await expect(page).toHaveURL('/dashboard')
  })
})
```

---

## Troubleshooting

### Common Issues

**Issue: Stuck in welcome setup loop**

**Symptoms**: User keeps getting redirected to `/welcome-setup`

**Solution**:
```sql
-- Check setup state in database
SELECT * FROM setup_state WHERE tenant_key = 'default';

-- Reset if needed
UPDATE setup_state 
SET password_setup_complete = true,
    default_password_active = false 
WHERE tenant_key = 'default';
```

**Issue: WebSocket not connecting during setup**

**Symptoms**: ConnectionStatus shows "Disconnected" in setup wizard

**Solution**:
```javascript
// Verify JWT token is present and valid
const token = localStorage.getItem('auth_token')
console.log('JWT Token:', token)

// Check WebSocket URL construction  
const wsUrl = `ws://localhost:7272/ws/setup?token=${token}`
console.log('WebSocket URL:', wsUrl)

// Clear and re-authenticate if needed
localStorage.removeItem('auth_token')
// Redirect to login
```

**Issue: Password validation not working**

**Symptoms**: Form allows weak passwords or doesn't validate

**Solution**:
```javascript
// Check password validation function
const isValid = validatePasswordComplexity('testPassword123!')
console.log('Password valid:', isValid)

// Verify all requirements are checked
const requirements = getPasswordRequirements('testPassword123!')
console.log('Requirements status:', requirements)
```

### Recovery Procedures

**Reset to Welcome Setup**:
```sql
-- Reset setup state to beginning
UPDATE setup_state 
SET password_setup_complete = false,
    setup_completed = false,
    default_password_active = true
WHERE tenant_key = 'default';

-- Reset admin password to default
UPDATE users 
SET password_hash = '$2b$12$...' -- Hash of 'admin'
WHERE username = 'admin' AND tenant_key = 'default';
```

**Skip Welcome Setup** (development only):
```sql
-- Mark password setup as complete  
UPDATE setup_state 
SET password_setup_complete = true,
    default_password_active = false
WHERE tenant_key = 'default';
```

**Clear Browser State**:
```javascript
// Clear all authentication state
localStorage.removeItem('auth_token')
sessionStorage.clear()

// Clear router cache
router.go(0)

// Or hard refresh
window.location.reload(true)
```

---

## Security Considerations

### Password Security Enhancements

**Entropy Requirements**:
- Minimum 12 characters (increased from 8)
- Mixed case, numbers, special characters required
- Real-time strength calculation
- Visual feedback prevents weak passwords

**Storage Security**:
```python
# Secure password hashing with bcrypt
def hash_password(password: str) -> str:
    salt = bcrypt.gensalt(rounds=12)  # High cost factor
    return bcrypt.hashpw(password.encode('utf-8'), salt).decode('utf-8')

# Secure password verification
def verify_password(password: str, hashed: str) -> bool:
    return bcrypt.checkpw(
        password.encode('utf-8'), 
        hashed.encode('utf-8')
    )
```

### JWT Security

**Token Generation**:
```python
# Secure JWT token creation
def create_access_token(user_id: str, tenant_key: str) -> str:
    payload = {
        'user_id': user_id,
        'tenant_key': tenant_key,
        'iat': datetime.utcnow(),
        'exp': datetime.utcnow() + timedelta(hours=24),
        'scope': 'setup' if is_setup_phase() else 'full_access'
    }
    
    return jwt.encode(payload, JWT_SECRET_KEY, algorithm='HS256')
```

**Token Validation**:
```python
# Secure JWT validation for WebSocket
def validate_websocket_token(token: str) -> bool:
    try:
        payload = jwt.decode(token, JWT_SECRET_KEY, algorithms=['HS256'])
        return payload.get('exp', 0) > datetime.utcnow().timestamp()
    except jwt.InvalidTokenError:
        return False
```

---

## Performance Optimizations

### Component Loading

**Lazy Loading**:
```javascript
// Lazy load setup components
const WelcomeSetup = () => import('@/views/WelcomeSetup.vue')
const SetupWizard = () => import('@/views/SetupWizard.vue')

// Route-based code splitting
{
  path: '/welcome-setup',
  component: WelcomeSetup,
  meta: { preload: true }
}
```

### WebSocket Efficiency

**Connection Management**:
```javascript
class SetupWebSocketManager {
  constructor() {
    this.connection = null
    this.reconnectAttempts = 0
    this.maxReconnectAttempts = 3
  }
  
  connect() {
    const token = localStorage.getItem('auth_token')
    this.connection = new WebSocket(`ws://localhost:7272/ws/setup?token=${token}`)
    
    this.connection.onclose = () => {
      if (this.reconnectAttempts < this.maxReconnectAttempts) {
        setTimeout(() => this.connect(), 1000)
        this.reconnectAttempts++
      }
    }
  }
}
```

---

**See Also**:
- [First Launch Experience](FIRST_LAUNCH_EXPERIENCE.md) - Complete onboarding walkthrough
- [User Structures & Tenants](USER_STRUCTURES_TENANTS.md) - Authentication and tenant context
- [Server Architecture & Tech Stack](SERVER_ARCHITECTURE_TECH_STACK.md) - Technical implementation details
- [AI Tool Configuration Management](AI_TOOL_CONFIGURATION_MANAGEMENT.md) - Setup wizard integration

---

*This document provides comprehensive coverage of GiljoAI MCP's enhanced two-phase setup flow as the single source of truth for the October 13, 2025 documentation harmonization.*