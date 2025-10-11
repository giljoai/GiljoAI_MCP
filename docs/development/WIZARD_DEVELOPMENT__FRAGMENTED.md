# Setup Wizard Development Guide

**Version**: 2.0.0
**Last Updated**: October 5, 2025
**Target Audience**: Developers implementing Phase 0

## Overview

This guide provides technical specifications and implementation guidance for developing the GiljoAI MCP Setup Wizard. The wizard is a critical component of the Phase 0 installer/wizard harmonization, moving MCP registration and configuration from CLI to a web-based interface.

## Architecture

### High-Level Design

```
┌─────────────────────────────────────────────────────────┐
│                  Frontend (Vue 3)                        │
│  ┌──────────────────────────────────────────────────┐  │
│  │  SetupWizard.vue (Main Container)                │  │
│  │  ├─ WelcomeStep.vue                              │  │
│  │  ├─ DatabaseStep.vue                             │  │
│  │  ├─ DeploymentModeStep.vue                       │  │
│  │  ├─ AdminAccountStep.vue                         │  │
│  │  ├─ ToolIntegrationStep.vue                      │  │
│  │  ├─ FirewallConfigStep.vue                       │  │
│  │  └─ VerificationStep.vue                         │  │
│  └──────────────────────────────────────────────────┘  │
└──────────────────────┬──────────────────────────────────┘
                       │ HTTP/REST API
┌──────────────────────▼──────────────────────────────────┐
│                  Backend (FastAPI)                       │
│  ┌──────────────────────────────────────────────────┐  │
│  │  api/endpoints/setup.py                          │  │
│  │  ├─ POST /setup/test-database                    │  │
│  │  ├─ GET  /setup/detect-tools                     │  │
│  │  ├─ POST /setup/generate-mcp-config              │  │
│  │  ├─ POST /setup/register-mcp                     │  │
│  │  ├─ POST /setup/test-mcp-connection              │  │
│  │  ├─ POST /setup/create-admin                     │  │
│  │  ├─ GET  /setup/network-info                     │  │
│  │  └─ POST /setup/complete                         │  │
│  └──────────────────────────────────────────────────┘  │
└─────────────────────────────────────────────────────────┘
```

### Technology Stack

- **Frontend Framework**: Vue 3 with Composition API
- **UI Library**: Vuetify 3 (Material Design components)
- **State Management**: Pinia store
- **Routing**: Vue Router 4
- **HTTP Client**: Axios
- **Backend Framework**: FastAPI
- **Validation**: Pydantic models
- **File I/O**: Python pathlib, json modules

## Frontend Implementation

### Component Structure

#### 1. SetupWizard.vue (Main Container)

**Location**: `frontend/src/views/Setup/SetupWizard.vue`

**Responsibilities**:
- Manage wizard state and navigation
- Track current step and progress
- Handle step transitions
- Persist state across page refreshes
- Display progress indicator

**Key State**:
```javascript
const state = reactive({
  currentStep: 0,
  totalSteps: 7,
  deploymentMode: null,
  adminCreated: false,
  toolsConfigured: [],
  setupComplete: false
})
```

**Navigation Logic**:
```javascript
function nextStep(data) {
  // Save step data
  saveStepData(state.currentStep, data)

  // Conditional navigation
  if (state.currentStep === 2 && state.deploymentMode === 'localhost') {
    // Skip admin account step for localhost
    state.currentStep += 2
  } else {
    state.currentStep++
  }

  // Persist to localStorage
  localStorage.setItem('wizardState', JSON.stringify(state))
}
```

**Template Structure**:
```vue
<template>
  <v-container class="setup-wizard">
    <v-stepper v-model="state.currentStep">
      <v-stepper-header>
        <v-stepper-item
          v-for="(step, index) in steps"
          :key="index"
          :value="index"
          :title="step.title"
          :complete="index < state.currentStep"
        />
      </v-stepper-header>

      <v-stepper-window>
        <v-stepper-window-item :value="0">
          <WelcomeStep @next="nextStep" />
        </v-stepper-window-item>
        <!-- Additional steps... -->
      </v-stepper-window>
    </v-stepper>
  </v-container>
</template>
```

---

#### 2. DatabaseStep.vue

**Responsibilities**:
- Test database connection
- Display connection status
- Provide troubleshooting link
- Retry connection on failure

**API Calls**:
```javascript
async function testConnection() {
  loading.value = true
  try {
    const response = await axios.post('/api/setup/test-database')
    connectionStatus.value = response.data.status
    if (response.data.status === 'connected') {
      emit('next', { database: 'connected' })
    }
  } catch (error) {
    connectionStatus.value = 'failed'
    errorMessage.value = error.response?.data?.detail || 'Connection failed'
  } finally {
    loading.value = false
  }
}
```

**UI States**:
- **Initial**: "Test Connection" button enabled
- **Testing**: Loading spinner, button disabled
- **Success**: Green checkmark, "Continue" button enabled
- **Failure**: Red X, error message, "Retry" button, "Troubleshoot" link

---

#### 3. DeploymentModeStep.vue

**Responsibilities**:
- Display deployment mode options
- Explain differences between modes
- Validate selection
- Pass mode to next steps

**Template**:
```vue
<template>
  <v-card>
    <v-card-title>Select Deployment Mode</v-card-title>

    <v-card-text>
      <v-radio-group v-model="selectedMode">
        <v-card v-for="mode in deploymentModes" :key="mode.value" class="mb-4">
          <v-card-text>
            <v-radio :value="mode.value">
              <template v-slot:label>
                <div>
                  <div class="text-h6">{{ mode.title }}</div>
                  <div class="text-body-2">{{ mode.description }}</div>
                  <v-chip-group class="mt-2">
                    <v-chip
                      v-for="feature in mode.features"
                      :key="feature"
                      size="small"
                      variant="outlined"
                    >
                      {{ feature }}
                    </v-chip>
                  </v-chip-group>
                </div>
              </template>
            </v-radio>
          </v-card-text>
        </v-card>
      </v-radio-group>
    </v-card-text>

    <v-card-actions>
      <v-btn @click="$emit('back')">Back</v-btn>
      <v-spacer />
      <v-btn
        color="primary"
        :disabled="!selectedMode"
        @click="$emit('next', { mode: selectedMode })"
      >
        Continue
      </v-btn>
    </v-card-actions>
  </v-card>
</template>
```

---

#### 4. ToolIntegrationStep.vue (Most Complex)

**Responsibilities**:
- Detect installed AI tools
- Generate tool-specific MCP configurations
- Display configuration preview
- Write configurations to tool config files
- Test MCP connections
- Handle backup and merge of existing configs

**State Management**:
```javascript
const state = reactive({
  detecting: false,
  detectedTools: [],
  selectedTool: null,
  generatedConfig: null,
  showConfigPreview: false,
  applying: false,
  testResults: {}
})
```

**Detection Flow**:
```javascript
async function detectTools() {
  state.detecting = true
  try {
    const response = await axios.get('/api/setup/detect-tools')
    state.detectedTools = response.data
  } catch (error) {
    console.error('Tool detection failed:', error)
  } finally {
    state.detecting = false
  }
}

onMounted(() => {
  detectTools()
})
```

**Configuration Flow**:
```javascript
async function configureTool(tool) {
  try {
    // 1. Generate config
    const configResponse = await axios.post('/api/setup/generate-mcp-config', {
      tool: tool.tool_name,
      mode: props.deploymentMode
    })

    state.generatedConfig = configResponse.data
    state.selectedTool = tool
    state.showConfigPreview = true
  } catch (error) {
    // Handle error
  }
}

async function applyConfig() {
  state.applying = true
  try {
    // 2. Write config to file
    const applyResponse = await axios.post('/api/setup/register-mcp', {
      tool: state.selectedTool.tool_name,
      config: state.generatedConfig
    })

    // 3. Test connection
    const testResponse = await axios.post('/api/setup/test-mcp-connection', {
      tool: state.selectedTool.tool_name
    })

    state.testResults[state.selectedTool.tool_name] = testResponse.data
    state.showConfigPreview = false

    // Show success notification
    showSuccess(`${state.selectedTool.tool_name} configured successfully!`)
  } catch (error) {
    showError(`Configuration failed: ${error.response?.data?.detail}`)
  } finally {
    state.applying = false
  }
}
```

---

### State Management (Pinia Store)

**Location**: `frontend/src/stores/setupWizard.js`

```javascript
import { defineStore } from 'pinia'

export const useSetupWizardStore = defineStore('setupWizard', {
  state: () => ({
    currentStep: 0,
    deploymentMode: null,
    databaseConnected: false,
    adminAccount: null,
    toolsConfigured: [],
    firewallConfigured: false,
    setupComplete: false,

    // Step data
    stepData: {
      database: null,
      deployment: null,
      admin: null,
      tools: [],
      firewall: null,
      verification: null
    }
  }),

  actions: {
    setCurrentStep(step) {
      this.currentStep = step
      this.persist()
    },

    saveStepData(step, data) {
      const stepKeys = ['database', 'deployment', 'admin', 'tools', 'firewall', 'verification']
      this.stepData[stepKeys[step]] = data
      this.persist()
    },

    persist() {
      localStorage.setItem('wizardState', JSON.stringify(this.$state))
    },

    restore() {
      const saved = localStorage.getItem('wizardState')
      if (saved) {
        Object.assign(this.$state, JSON.parse(saved))
      }
    },

    reset() {
      this.$reset()
      localStorage.removeItem('wizardState')
    }
  }
})
```

---

## Backend Implementation

### API Endpoint Specifications

#### POST /api/setup/test-database

**Purpose**: Test PostgreSQL connection

**Request**: None (uses .env credentials)

**Response**:
```json
{
  "status": "connected",
  "version": "PostgreSQL 18.1",
  "database": "giljo_mcp",
  "latency_ms": 12
}
```

**Error Response**:
```json
{
  "status": "failed",
  "error": "Connection refused",
  "details": "Could not connect to localhost:5432",
  "troubleshooting_link": "/docs/troubleshooting/POSTGRES_TROUBLESHOOTING.txt"
}
```

**Implementation**:
```python
from fastapi import APIRouter, HTTPException
from src.giljo_mcp.database import test_connection
import time

router = APIRouter(prefix="/setup", tags=["setup"])

@router.post("/test-database")
async def test_database():
    """Test database connection and return status."""
    start = time.time()
    try:
        result = test_connection()
        latency = int((time.time() - start) * 1000)

        return {
            "status": "connected",
            "version": result.get("version"),
            "database": result.get("database"),
            "latency_ms": latency
        }
    except Exception as e:
        raise HTTPException(
            status_code=500,
            detail={
                "status": "failed",
                "error": str(e),
                "troubleshooting_link": "/docs/troubleshooting/POSTGRES_TROUBLESHOOTING.txt"
            }
        )
```

---

#### GET /api/setup/detect-tools

**Purpose**: Detect installed AI coding tools

**Response**:
```json
[
  {
    "tool_name": "Claude Code",
    "installed": true,
    "version": "1.2.3",
    "config_path": "C:\\Users\\username\\.claude.json"
  },
  {
    "tool_name": "Cline",
    "installed": true,
    "version": "2.0.1",
    "config_path": "C:\\Users\\username\\AppData\\Roaming\\Code\\User\\globalStorage\\saoudrizwan.claude-dev\\settings.json"
  },
  {
    "tool_name": "Cursor",
    "installed": false,
    "version": null,
    "config_path": null
  }
]
```

**Implementation**:
```python
from pathlib import Path
import json
import platform

@router.get("/detect-tools")
async def detect_ai_tools():
    """Detect installed AI coding tools."""
    tools = []

    # Detect Claude Code
    claude_config = Path.home() / ".claude.json"
    tools.append({
        "tool_name": "Claude Code",
        "installed": claude_config.exists(),
        "version": get_claude_version(claude_config) if claude_config.exists() else None,
        "config_path": str(claude_config) if claude_config.exists() else None
    })

    # Detect Cline (VS Code extension)
    cline_config = get_cline_config_path()
    tools.append({
        "tool_name": "Cline",
        "installed": cline_config is not None,
        "version": get_cline_version(cline_config) if cline_config else None,
        "config_path": str(cline_config) if cline_config else None
    })

    # Detect Cursor
    cursor_config = get_cursor_config_path()
    tools.append({
        "tool_name": "Cursor",
        "installed": cursor_config is not None,
        "version": None,
        "config_path": str(cursor_config) if cursor_config else None
    })

    return tools

def get_claude_version(config_path: Path) -> str:
    """Extract Claude Code version from config."""
    try:
        with open(config_path) as f:
            config = json.load(f)
        return config.get("version", "unknown")
    except Exception:
        return "unknown"

def get_cline_config_path() -> Path | None:
    """Find Cline configuration file."""
    if platform.system() == "Windows":
        base = Path(os.getenv("APPDATA")) / "Code" / "User" / "globalStorage" / "saoudrizwan.claude-dev"
    elif platform.system() == "Darwin":  # macOS
        base = Path.home() / "Library" / "Application Support" / "Code" / "User" / "globalStorage" / "saoudrizwan.claude-dev"
    else:  # Linux
        base = Path.home() / ".config" / "Code" / "User" / "globalStorage" / "saoudrizwan.claude-dev"

    settings_file = base / "settings.json"
    return settings_file if settings_file.exists() else None
```

---

#### POST /api/setup/generate-mcp-config

**Purpose**: Generate tool-specific MCP configuration

**Request**:
```json
{
  "tool": "Claude Code",
  "mode": "localhost"
}
```

**Response**:
```json
{
  "mcpServers": {
    "giljo-mcp": {
      "command": "C:\\Projects\\GiljoAI_MCP\\venv\\Scripts\\python.exe",
      "args": ["-m", "giljo_mcp"],
      "env": {
        "GILJO_API_URL": "http://localhost:7272"
      }
    }
  }
}
```

**Implementation**:
```python
from pydantic import BaseModel

class MCPConfigRequest(BaseModel):
    tool: str
    mode: str  # "localhost", "lan", or "wan"

@router.post("/generate-mcp-config")
async def generate_mcp_config(request: MCPConfigRequest):
    """Generate MCP configuration for specified tool and mode."""
    config = load_config()

    if request.tool == "Claude Code":
        return generate_claude_code_config(config, request.mode)
    elif request.tool == "Cline":
        return generate_cline_config(config, request.mode)
    elif request.tool == "Cursor":
        return generate_cursor_config(config, request.mode)
    else:
        raise HTTPException(400, f"Unknown tool: {request.tool}")

def generate_claude_code_config(config, mode: str) -> dict:
    """Generate Claude Code .claude.json MCP config."""
    venv_python = str(Path(config.paths.install_dir) / "venv" / "Scripts" / "python.exe")

    mcp_config = {
        "command": venv_python,
        "args": ["-m", "giljo_mcp"],
        "env": {}
    }

    # Mode-specific configuration
    if mode == "localhost":
        mcp_config["env"]["GILJO_API_URL"] = f"http://localhost:{config.services.api.port}"
    elif mode == "lan":
        lan_ip = get_lan_ip()
        mcp_config["env"]["GILJO_API_URL"] = f"http://{lan_ip}:{config.services.api.port}"
        mcp_config["env"]["GILJO_API_KEY"] = config.security.api_key
    elif mode == "wan":
        mcp_config["env"]["GILJO_API_URL"] = config.services.api.public_url
        mcp_config["env"]["GILJO_API_KEY"] = config.security.api_key

    return {
        "mcpServers": {
            "giljo-mcp": mcp_config
        }
    }
```

---

#### POST /api/setup/register-mcp

**Purpose**: Write MCP configuration to tool's config file

**Request**:
```json
{
  "tool": "Claude Code",
  "config": { /* MCP config object */ }
}
```

**Response**:
```json
{
  "success": true,
  "config_path": "C:\\Users\\username\\.claude.json",
  "backup_path": "C:\\Users\\username\\.claude.json.backup_20251005_143022"
}
```

**Implementation**:
```python
from datetime import datetime
import shutil

class MCPRegisterRequest(BaseModel):
    tool: str
    config: dict

@router.post("/register-mcp")
async def register_mcp(request: MCPRegisterRequest):
    """Register MCP server with AI tool by writing config file."""
    if request.tool == "Claude Code":
        return write_claude_config(request.config)
    elif request.tool == "Cline":
        return write_cline_config(request.config)
    elif request.tool == "Cursor":
        return write_cursor_config(request.config)
    else:
        raise HTTPException(400, f"Unknown tool: {request.tool}")

def write_claude_config(config: dict) -> dict:
    """Write Claude Code configuration with backup."""
    config_path = Path.home() / ".claude.json"
    backup_path = None

    # Backup existing config
    if config_path.exists():
        timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
        backup_path = config_path.with_suffix(f".json.backup_{timestamp}")
        shutil.copy(config_path, backup_path)

        # Load and merge existing config
        with open(config_path) as f:
            existing = json.load(f)

        # Merge mcpServers (preserve other existing servers)
        if "mcpServers" not in existing:
            existing["mcpServers"] = {}

        existing["mcpServers"].update(config["mcpServers"])
        final_config = existing
    else:
        final_config = config

    # Write final config
    with open(config_path, "w") as f:
        json.dump(final_config, f, indent=2)

    return {
        "success": True,
        "config_path": str(config_path),
        "backup_path": str(backup_path) if backup_path else None
    }
```

---

### Error Handling

**Consistent Error Format**:
```python
from fastapi import HTTPException
from pydantic import BaseModel

class ErrorDetail(BaseModel):
    error: str
    details: str | None = None
    troubleshooting_link: str | None = None
    retry_possible: bool = False

# Usage
raise HTTPException(
    status_code=500,
    detail=ErrorDetail(
        error="Configuration write failed",
        details="Permission denied writing to C:\\Users\\username\\.claude.json",
        troubleshooting_link="/docs/guides/SETUP_WIZARD_GUIDE.md#configuration-fails",
        retry_possible=True
    ).dict()
)
```

---

## Testing Strategy

### Frontend Unit Tests (Vitest)

```javascript
// tests/unit/SetupWizard.spec.js
import { describe, it, expect, vi } from 'vitest'
import { mount } from '@vue/test-utils'
import SetupWizard from '@/views/Setup/SetupWizard.vue'

describe('SetupWizard.vue', () => {
  it('initializes with welcome step', () => {
    const wrapper = mount(SetupWizard)
    expect(wrapper.vm.currentStep).toBe(0)
  })

  it('navigates to next step on continue', async () => {
    const wrapper = mount(SetupWizard)
    await wrapper.vm.nextStep({ data: 'test' })
    expect(wrapper.vm.currentStep).toBe(1)
  })

  it('skips admin step in localhost mode', async () => {
    const wrapper = mount(SetupWizard)
    wrapper.vm.deploymentMode = 'localhost'
    wrapper.vm.currentStep = 2
    await wrapper.vm.nextStep({})
    expect(wrapper.vm.currentStep).toBe(4)  // Skipped admin step
  })
})
```

### Backend Integration Tests (pytest)

```python
# tests/test_setup_endpoints.py
import pytest
from fastapi.testclient import TestClient
from api.main import app

client = TestClient(app)

def test_detect_tools():
    response = client.get("/api/setup/detect-tools")
    assert response.status_code == 200
    data = response.json()
    assert isinstance(data, list)
    assert all("tool_name" in tool for tool in data)

def test_generate_claude_config_localhost():
    response = client.post("/api/setup/generate-mcp-config", json={
        "tool": "Claude Code",
        "mode": "localhost"
    })
    assert response.status_code == 200
    config = response.json()
    assert "mcpServers" in config
    assert "giljo-mcp" in config["mcpServers"]
    assert "GILJO_API_URL" in config["mcpServers"]["giljo-mcp"]["env"]
    assert "localhost" in config["mcpServers"]["giljo-mcp"]["env"]["GILJO_API_URL"]

def test_generate_config_unknown_tool():
    response = client.post("/api/setup/generate-mcp-config", json={
        "tool": "Unknown Tool",
        "mode": "localhost"
    })
    assert response.status_code == 400
```

---

## Security Considerations

### 1. File System Access

**Risk**: Writing to arbitrary files based on user input

**Mitigation**:
- Whitelist allowed config paths
- Validate tool names against enum
- Use Path.resolve() to prevent directory traversal
- Check file permissions before writing

```python
ALLOWED_CONFIG_PATHS = {
    "Claude Code": Path.home() / ".claude.json",
    "Cline": get_cline_config_path(),
    "Cursor": get_cursor_config_path()
}

def validate_config_path(tool: str, path: Path) -> bool:
    """Ensure config path matches expected location for tool."""
    expected = ALLOWED_CONFIG_PATHS.get(tool)
    if not expected:
        return False
    return path.resolve() == expected.resolve()
```

### 2. Configuration Injection

**Risk**: Malicious config injection via generated configs

**Mitigation**:
- Use Pydantic models for validation
- Sanitize all user inputs
- Template-based config generation (no string concatenation)

### 3. Credential Exposure

**Risk**: Exposing API keys or passwords in responses

**Mitigation**:
- Never return full config in API responses
- Mask sensitive fields in logs
- Use environment variables for secrets

---

## Development Workflow

### 1. Local Development Setup

```bash
# Backend
cd C:\Projects\GiljoAI_MCP
python -m venv venv
venv\Scripts\activate
pip install -r requirements.txt
uvicorn api.main:app --reload --port 7272

# Frontend
cd frontend
npm install
npm run dev
```

### 2. Adding a New Wizard Step

1. Create new component: `frontend/src/views/Setup/NewStep.vue`
2. Add to SetupWizard.vue stepper
3. Implement step validation logic
4. Add to Pinia store state
5. Create unit tests
6. Update user documentation

### 3. Adding a New AI Tool

1. Add detection logic to `detect_ai_tools()`
2. Implement `generate_{tool}_config()` function
3. Implement `write_{tool}_config()` function
4. Add tool to frontend tool list
5. Test thoroughly with actual tool
6. Update documentation

---

## Performance Considerations

- **Lazy Loading**: Load step components only when needed
- **Debouncing**: Debounce connection tests to prevent rapid-fire requests
- **Caching**: Cache tool detection results for 5 minutes
- **Progress Indication**: Show progress for long-running operations
- **Timeout Handling**: Set reasonable timeouts for all API calls

---

## Accessibility

- Use semantic HTML elements
- Provide ARIA labels for all interactive elements
- Ensure keyboard navigation works
- Test with screen readers
- Maintain sufficient color contrast ratios

---

## Related Documentation

- [Setup Wizard User Guide](../guides/SETUP_WIZARD_GUIDE.md) - End-user documentation
- [Installation Guide](../manuals/INSTALL.md) - Overall installation process
- [Implementation Plan](../IMPLEMENTATION_PLAN.md) - Phase 0 specifications
- [Technical Architecture](../TECHNICAL_ARCHITECTURE.md) - System architecture

---

**Last Updated**: October 5, 2025
**Version**: 2.0.0 (Phase 0)
**Maintained By**: Documentation Manager Agent
