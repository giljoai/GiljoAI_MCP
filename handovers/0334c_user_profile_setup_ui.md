# Handover 0334c: User Profile Setup UI - Claude Code Plugin

**Handover ID**: 0334c
**Title**: User Profile Setup UI - Claude Code Plugin
**Date**: 2025-12-07
**From**: Documentation Manager Agent
**To**: Frontend Implementation Agent
**Priority**: HIGH
**Status**: READY FOR IMPLEMENTATION
**Parent Handover**: 0334 (Claude Code Plugin Integration)

---

## Overview

This handover implements the user-facing UI component for one-time Claude Code plugin installation. The component provides users with a pre-configured installation command containing their unique tenant_key and allows them to test the connection to verify successful setup.

## Context

### Why This Component Exists

1. **One-Time Setup Model**: Each user needs to install the Claude Code plugin once, not per-project
2. **Tenant Isolation**: Each user has a unique `tenant_key` that identifies their data partition
3. **Simplified Agent Discovery**: Once installed, agents are available via `/agents` and `@agent_name` syntax
4. **User Experience**: Pre-filled install command eliminates manual configuration errors

### User Journey

1. User navigates to My Settings → Integrations
2. User sees "Claude Code CLI Plugin" card with pre-filled install command
3. User copies the command and runs it in their terminal
4. User clicks "Test Connection" to verify installation
5. Status indicator shows verification result

### Technical Background

- **Parent Handover 0334a**: Backend API endpoint `/api/agents/cli-plugin/verify`
- **Parent Handover 0334b**: CLI plugin implementation
- **This Handover (0334c)**: Frontend UI for user setup

---

## Technical Specification

### New Component

**File**: `frontend/src/components/settings/ClaudeCodePluginSetup.vue`

**Purpose**: Provide one-time installation UI for Claude Code plugin integration

**Component Type**: Vue 3 Composition API with Vuetify 3 components

### Component Props

**None** - Component is self-contained and fetches its own data from auth store and config.

### Component State

```javascript
const serverUrl = ref('');          // Computed from config or window.location
const tenantKey = ref('');          // From auth store (authStore.user.tenant_key)
const installCommand = computed(() => {
  return `claude plugins install giljoai-agents \\
  --config server_url=${serverUrl.value} \\
  --config tenant_key=${tenantKey.value}`;
});
const testStatus = ref('idle');     // 'idle' | 'testing' | 'success' | 'error'
const lastTestResult = ref(null);   // Error message or success message
const copyFeedback = ref(false);    // Show "Copied!" confirmation
```

### Component Template

```vue
<template>
  <v-card class="mb-4" variant="outlined">
    <v-card-title class="d-flex align-center">
      <v-icon start color="primary">mdi-console</v-icon>
      Claude Code CLI Plugin
    </v-card-title>

    <v-card-subtitle>
      Install the GiljoAI agent plugin for Claude Code CLI
    </v-card-subtitle>

    <v-card-text>
      <!-- Description -->
      <div class="mb-4">
        <p class="text-body-2 mb-2">
          This plugin connects Claude Code CLI to your GiljoAI agent templates.
          Once installed, your agents will be available via <code>/agents</code>
          and <code>@agent_name</code> syntax.
        </p>
        <p class="text-body-2 text-medium-emphasis">
          <strong>One-time setup:</strong> Run this command in your terminal to install the plugin.
        </p>
      </div>

      <!-- Install Command -->
      <v-text-field
        :model-value="installCommand"
        label="Installation Command"
        readonly
        variant="outlined"
        density="comfortable"
        append-inner-icon="mdi-content-copy"
        @click:append-inner="copyCommand"
        class="mb-3"
        hint="Click the copy icon to copy the command"
        persistent-hint
      />

      <!-- Copy Feedback -->
      <v-snackbar
        v-model="copyFeedback"
        :timeout="2000"
        color="success"
        location="bottom"
      >
        <v-icon start>mdi-check</v-icon>
        Command copied to clipboard!
      </v-snackbar>

      <!-- Status Indicator -->
      <div class="d-flex align-center mt-3">
        <v-chip
          :color="statusColor"
          :prepend-icon="statusIcon"
          size="small"
          variant="flat"
        >
          {{ statusText }}
        </v-chip>

        <!-- Error Message -->
        <v-tooltip
          v-if="testStatus === 'error' && lastTestResult"
          location="top"
        >
          <template v-slot:activator="{ props }">
            <v-icon
              v-bind="props"
              color="error"
              size="small"
              class="ml-2"
            >
              mdi-information-outline
            </v-icon>
          </template>
          <span>{{ lastTestResult }}</span>
        </v-tooltip>
      </div>
    </v-card-text>

    <v-card-actions>
      <v-btn
        variant="text"
        color="primary"
        @click="testConnection"
        :loading="testStatus === 'testing'"
        prepend-icon="mdi-check-network"
      >
        Test Connection
      </v-btn>

      <v-spacer />

      <v-btn
        variant="text"
        href="https://docs.giljo.ai/integrations/claude-code"
        target="_blank"
        append-icon="mdi-open-in-new"
        size="small"
      >
        Documentation
      </v-btn>
    </v-card-actions>
  </v-card>
</template>
```

### Component Script

```vue
<script setup>
import { ref, computed, onMounted } from 'vue';
import { useAuthStore } from '@/stores/auth';
import axios from 'axios';

// Stores
const authStore = useAuthStore();

// State
const serverUrl = ref('');
const tenantKey = ref('');
const testStatus = ref('idle');
const lastTestResult = ref(null);
const copyFeedback = ref(false);

// Computed
const installCommand = computed(() => {
  if (!serverUrl.value || !tenantKey.value) {
    return 'Loading...';
  }
  return `claude plugins install giljoai-agents \\
  --config server_url=${serverUrl.value} \\
  --config tenant_key=${tenantKey.value}`;
});

const statusColor = computed(() => {
  switch (testStatus.value) {
    case 'success': return 'success';
    case 'error': return 'error';
    case 'testing': return 'info';
    default: return 'grey';
  }
});

const statusText = computed(() => {
  switch (testStatus.value) {
    case 'success': return 'Verified';
    case 'error': return 'Connection Failed';
    case 'testing': return 'Testing...';
    default: return 'Not Verified';
  }
});

const statusIcon = computed(() => {
  switch (testStatus.value) {
    case 'success': return 'mdi-check-circle';
    case 'error': return 'mdi-alert-circle';
    case 'testing': return 'mdi-loading mdi-spin';
    default: return 'mdi-help-circle-outline';
  }
});

// Methods
const copyCommand = async () => {
  try {
    await navigator.clipboard.writeText(installCommand.value);
    copyFeedback.value = true;
  } catch (err) {
    console.error('Failed to copy:', err);
    // Fallback for older browsers
    const textArea = document.createElement('textarea');
    textArea.value = installCommand.value;
    document.body.appendChild(textArea);
    textArea.select();
    document.execCommand('copy');
    document.body.removeChild(textArea);
    copyFeedback.value = true;
  }
};

const testConnection = async () => {
  testStatus.value = 'testing';
  lastTestResult.value = null;

  try {
    const response = await axios.get('/api/agents/cli-plugin/verify', {
      params: { tenant_key: tenantKey.value }
    });

    if (response.status === 200 && response.data.status === 'ok') {
      testStatus.value = 'success';
      lastTestResult.value = 'Connection verified successfully';
    } else {
      testStatus.value = 'error';
      lastTestResult.value = response.data.message || 'Unexpected response from server';
    }
  } catch (error) {
    testStatus.value = 'error';
    if (error.response?.data?.detail) {
      lastTestResult.value = error.response.data.detail;
    } else if (error.message) {
      lastTestResult.value = error.message;
    } else {
      lastTestResult.value = 'Failed to connect to server';
    }
  }
};

const initializeComponent = () => {
  // Get tenant key from auth store
  tenantKey.value = authStore.user?.tenant_key || '';

  // Determine server URL
  // Priority: external_host from config > window.location
  const protocol = window.location.protocol;
  const hostname = window.location.hostname;
  const port = window.location.port;

  // Check if external_host is configured (for LAN access)
  // This would be available from a config store or settings API
  // For now, construct from window.location
  if (hostname === 'localhost' || hostname === '127.0.0.1') {
    serverUrl.value = `${protocol}//${hostname}:${port || '7272'}`;
  } else {
    // Use external hostname (LAN or public IP)
    serverUrl.value = `${protocol}//${hostname}${port ? ':' + port : ''}`;
  }
};

// Lifecycle
onMounted(() => {
  initializeComponent();
});
</script>
```

### Component Styling

```vue
<style scoped>
code {
  background-color: rgba(0, 0, 0, 0.05);
  padding: 2px 6px;
  border-radius: 4px;
  font-family: 'Courier New', monospace;
  font-size: 0.9em;
}

.v-theme--dark code {
  background-color: rgba(255, 255, 255, 0.1);
}

.mdi-spin {
  animation: spin 1s linear infinite;
}

@keyframes spin {
  from { transform: rotate(0deg); }
  to { transform: rotate(360deg); }
}
</style>
```

---

## Integration into UserSettings.vue

### Location

File: `frontend/src/views/UserSettings.vue`

### Modification Required

**Add Import:**
```javascript
import ClaudeCodePluginSetup from '@/components/settings/ClaudeCodePluginSetup.vue';
```

**Register Component:**
```javascript
components: {
  // ... existing components
  ClaudeCodePluginSetup,
}
```

**Add to Template:**
Insert the new component in the Integrations tab, after `ClaudeCodeExport` and before `SerenaIntegrationCard`:

```vue
<!-- Integrations -->
<v-window-item value="integrations">
  <v-card>
    <v-card-title>Integrations</v-card-title>
    <v-card-subtitle>Configure MCP tools and integrations</v-card-subtitle>
    <v-card-text>
      <!-- GiljoAI MCP Integration -->
      <McpIntegrationCard />

      <!-- Slash Command Setup -->
      <SlashCommandSetup />

      <!-- Claude Code Agent Export -->
      <ClaudeCodeExport />

      <!-- Claude Code Plugin Setup (NEW) -->
      <ClaudeCodePluginSetup />

      <!-- Serena MCP Integration -->
      <SerenaIntegrationCard ... />

      <!-- Git + 360 Memory Integration -->
      <GitIntegrationCard ... />
    </v-card-text>
  </v-card>
</v-window-item>
```

---

## Test-Driven Development Requirements

### Test File

**Location**: `tests/frontend/components/ClaudeCodePluginSetup.spec.js`

### Test Suite Structure

```javascript
import { describe, it, expect, vi, beforeEach } from 'vitest';
import { mount } from '@vue/test-utils';
import { createVuetify } from 'vuetify';
import * as components from 'vuetify/components';
import * as directives from 'vuetify/directives';
import ClaudeCodePluginSetup from '@/components/settings/ClaudeCodePluginSetup.vue';
import { createPinia, setActivePinia } from 'pinia';
import axios from 'axios';

// Mock axios
vi.mock('axios');

const vuetify = createVuetify({
  components,
  directives,
});

describe('ClaudeCodePluginSetup.vue', () => {
  let wrapper;
  let pinia;

  beforeEach(() => {
    pinia = createPinia();
    setActivePinia(pinia);

    // Mock auth store
    const authStore = {
      user: {
        tenant_key: 'test-tenant-123'
      }
    };

    // Mock useAuthStore
    vi.mock('@/stores/auth', () => ({
      useAuthStore: () => authStore
    }));

    wrapper = mount(ClaudeCodePluginSetup, {
      global: {
        plugins: [vuetify, pinia],
      },
    });
  });

  it('renders the component with correct title', () => {
    expect(wrapper.text()).toContain('Claude Code CLI Plugin');
  });

  it('renders with correct install command including tenant_key', () => {
    const textField = wrapper.findComponent({ name: 'VTextField' });
    expect(textField.props('modelValue')).toContain('test-tenant-123');
    expect(textField.props('modelValue')).toContain('claude plugins install giljoai-agents');
  });

  it('install command includes server_url', () => {
    const textField = wrapper.findComponent({ name: 'VTextField' });
    const command = textField.props('modelValue');
    expect(command).toMatch(/--config server_url=http/);
  });

  it('copy button copies to clipboard', async () => {
    // Mock clipboard API
    const writeText = vi.fn().mockResolvedValue();
    Object.assign(navigator, {
      clipboard: {
        writeText,
      },
    });

    const textField = wrapper.findComponent({ name: 'VTextField' });
    await textField.vm.$emit('click:append-inner');

    expect(writeText).toHaveBeenCalled();
    expect(writeText).toHaveBeenCalledWith(expect.stringContaining('test-tenant-123'));
  });

  it('copy button shows success feedback', async () => {
    const writeText = vi.fn().mockResolvedValue();
    Object.assign(navigator, {
      clipboard: {
        writeText,
      },
    });

    const textField = wrapper.findComponent({ name: 'VTextField' });
    await textField.vm.$emit('click:append-inner');

    await wrapper.vm.$nextTick();

    const snackbar = wrapper.findComponent({ name: 'VSnackbar' });
    expect(snackbar.props('modelValue')).toBe(true);
  });

  it('test connection button shows loading state', async () => {
    axios.get.mockImplementation(() => new Promise(() => {})); // Never resolves

    const button = wrapper.findAllComponents({ name: 'VBtn' })[0];
    await button.trigger('click');

    await wrapper.vm.$nextTick();

    expect(button.props('loading')).toBe(true);
  });

  it('test connection shows success on 200 response', async () => {
    axios.get.mockResolvedValue({
      status: 200,
      data: {
        status: 'ok',
        message: 'Connection verified'
      }
    });

    const button = wrapper.findAllComponents({ name: 'VBtn' })[0];
    await button.trigger('click');

    await wrapper.vm.$nextTick();
    await new Promise(resolve => setTimeout(resolve, 0));

    const chip = wrapper.findComponent({ name: 'VChip' });
    expect(chip.props('color')).toBe('success');
    expect(chip.text()).toContain('Verified');
  });

  it('test connection shows error on failure', async () => {
    axios.get.mockRejectedValue({
      response: {
        data: {
          detail: 'Invalid tenant key'
        }
      }
    });

    const button = wrapper.findAllComponents({ name: 'VBtn' })[0];
    await button.trigger('click');

    await wrapper.vm.$nextTick();
    await new Promise(resolve => setTimeout(resolve, 0));

    const chip = wrapper.findComponent({ name: 'VChip' });
    expect(chip.props('color')).toBe('error');
    expect(chip.text()).toContain('Connection Failed');
  });

  it('displays error message in tooltip on failure', async () => {
    axios.get.mockRejectedValue({
      response: {
        data: {
          detail: 'Database connection failed'
        }
      }
    });

    const button = wrapper.findAllComponents({ name: 'VBtn' })[0];
    await button.trigger('click');

    await wrapper.vm.$nextTick();
    await new Promise(resolve => setTimeout(resolve, 0));

    expect(wrapper.vm.lastTestResult).toBe('Database connection failed');
  });

  it('status shows "Not Verified" initially', () => {
    const chip = wrapper.findComponent({ name: 'VChip' });
    expect(chip.props('color')).toBe('grey');
    expect(chip.text()).toContain('Not Verified');
  });

  it('fallback copy mechanism works when clipboard API unavailable', async () => {
    // Mock old-style document.execCommand
    const execCommand = vi.fn();
    document.execCommand = execCommand;

    // Remove clipboard API
    Object.assign(navigator, {
      clipboard: undefined,
    });

    const textField = wrapper.findComponent({ name: 'VTextField' });
    await textField.vm.$emit('click:append-inner');

    expect(execCommand).toHaveBeenCalledWith('copy');
  });
});
```

### Test Execution

```bash
# Run tests
npm run test:unit -- ClaudeCodePluginSetup.spec.js

# Run with coverage
npm run test:unit -- --coverage ClaudeCodePluginSetup.spec.js
```

---

## API Dependency

This component depends on the backend API endpoint from **Handover 0334a**:

**Endpoint**: `GET /api/agents/cli-plugin/verify`

**Query Parameters**:
- `tenant_key`: string (required)

**Response (Success)**:
```json
{
  "status": "ok",
  "message": "Agent templates endpoint is accessible",
  "tenant_key": "user-tenant-123",
  "available_agents": ["orchestrator", "frontend-specialist", ...]
}
```

**Response (Error)**:
```json
{
  "detail": "Invalid tenant key"
}
```

**Status Codes**:
- `200`: Success - connection verified
- `400`: Bad request - missing tenant_key
- `403`: Forbidden - invalid tenant_key
- `500`: Server error

---

## Files Summary

### New Files

1. **`frontend/src/components/settings/ClaudeCodePluginSetup.vue`**
   - Purpose: User-facing plugin setup UI
   - Lines: ~250
   - Dependencies: Vuetify 3, auth store, axios

2. **`tests/frontend/components/ClaudeCodePluginSetup.spec.js`**
   - Purpose: Unit tests for plugin setup component
   - Lines: ~200
   - Coverage Target: >90%

### Modified Files

1. **`frontend/src/views/UserSettings.vue`**
   - Changes: Import and register `ClaudeCodePluginSetup` component
   - Location: Add to Integrations tab after `ClaudeCodeExport`

---

## Success Criteria Checklist

- [ ] Component renders in My Settings → Integrations tab
- [ ] Install command includes correct `server_url` (from config or window.location)
- [ ] Install command includes user's `tenant_key` (from auth store)
- [ ] Copy button successfully copies command to clipboard
- [ ] Copy button shows visual confirmation ("Copied!" snackbar)
- [ ] Fallback copy mechanism works in older browsers
- [ ] Test Connection button makes API call to `/api/agents/cli-plugin/verify`
- [ ] Test Connection shows loading state during request
- [ ] Status indicator updates to "Verified" on success (200)
- [ ] Status indicator updates to "Connection Failed" on error
- [ ] Error message displayed in tooltip on failure
- [ ] Initial status shows "Not Verified" (grey chip)
- [ ] Component matches Vuetify theme (light/dark mode)
- [ ] Component follows existing card styling in Integrations tab
- [ ] Documentation link opens in new tab
- [ ] All unit tests pass (>90% coverage)
- [ ] Component is accessible (ARIA labels, keyboard navigation)

---

## UI/UX Considerations

### Design Consistency

- **Match Existing Pattern**: Follow the same card structure as `SerenaIntegrationCard` and `ClaudeCodeExport`
- **Icon Usage**: Use `mdi-console` for Claude Code CLI branding
- **Color Scheme**: Use Vuetify's semantic colors (success, error, info, grey)
- **Spacing**: Maintain consistent margins (`mb-4` for cards, `mb-3` for form elements)

### User Experience

1. **Clarity**: Use clear, concise language explaining what the plugin does
2. **Guidance**: Provide step-by-step instructions (copy command → run in terminal → test connection)
3. **Feedback**: Show visual confirmation for all user actions (copy, test)
4. **Error Handling**: Display helpful error messages, not technical stack traces
5. **Loading States**: Show loading indicator during async operations

### Accessibility

- Use semantic HTML elements
- Provide ARIA labels for icon-only buttons
- Ensure keyboard navigation works
- Use sufficient color contrast for status indicators
- Provide text alternatives for icons

### Responsive Design

- Component should work on all screen sizes
- Install command should wrap gracefully on narrow screens
- Card layout should stack vertically on mobile

---

## Implementation Notes

### Server URL Detection

**CRITICAL**: The server URL is the IP/hostname that Claude Code machines will use to reach this GiljoAI server. This MUST be the `external_host` configured during `install.py` installation.

The component needs to construct the correct server URL for the install command:

1. **Localhost Development**: `http://localhost:7272` or custom port
2. **LAN Access**: `http://192.168.1.100:7272` (external_host from install.py)
3. **Production**: `https://giljo.example.com`

**Priority Order**:
1. **REQUIRED**: Fetch `external_host` from `/api/v1/config` endpoint (set during installation)
2. Fall back to `window.location.hostname` ONLY if config unavailable
3. Use API port from config (default 7272)

**Admin Note**: The `external_host` is visible in Admin Settings → Network tab. A reminder alert has been added there (Handover 0334) to ensure admins understand this value is used by the Claude Code plugin.

### Tenant Key Security

- Tenant key is NOT a secret (it's an identifier, not a credential)
- Safe to display in UI and copy to clipboard
- User-specific, provides multi-tenant data isolation
- Each user has exactly one tenant_key (assigned at registration)

### Copy to Clipboard Fallback

Modern browsers support `navigator.clipboard.writeText()`, but older browsers require the `document.execCommand('copy')` fallback. The component implements both methods for maximum compatibility.

### Test Connection Timing

- Show loading state immediately on button click
- Minimum loading duration: 500ms (for perceived responsiveness)
- Timeout: 10 seconds (API should respond faster, but handle network issues)
- Debounce: Prevent multiple simultaneous test requests

---

## Dependencies

### Frontend Dependencies (Already Installed)

- Vue 3 (Composition API)
- Vuetify 3 (UI components)
- Axios (HTTP client)
- Pinia (State management)

### Backend Dependencies (From Handover 0334a)

- FastAPI endpoint `/api/agents/cli-plugin/verify`
- Multi-tenant agent filtering by `tenant_key`
- Database connection to verify agent templates

### External Dependencies

- Claude Code CLI (user must install separately)
- GiljoAI Agent Plugin (installed via command in this UI)

---

## Rollout Strategy

### Phase 1: Component Implementation (This Handover)

1. Create `ClaudeCodePluginSetup.vue` component
2. Write comprehensive unit tests
3. Integrate into `UserSettings.vue`
4. Manual QA testing in dev environment

### Phase 2: User Documentation

1. Update user guides with plugin setup instructions
2. Add screenshots to documentation
3. Create troubleshooting section for common issues
4. Update integration documentation

### Phase 3: Release

1. Merge to master branch
2. Deploy to production
3. Announce feature to users
4. Monitor support requests for issues

---

## Known Limitations

1. **Windows Path Handling**: Install command uses backslashes for line continuation. Windows users may need to remove them for PowerShell.
   - **Solution**: Detect OS and format command accordingly (future enhancement)

2. **Server URL Auto-Detection**: May not work correctly behind reverse proxies or complex network setups.
   - **Solution**: Allow manual override in settings (future enhancement)

3. **Connection Test Persistence**: Test result is not persisted across page refreshes.
   - **Solution**: Store verification status in user settings (future enhancement)

4. **Plugin Version Management**: No version checking or update notification.
   - **Solution**: Add plugin version endpoint and update checker (future enhancement)

---

## Future Enhancements (Out of Scope)

1. **Auto-Installation**: Detect if plugin is already installed, skip setup if verified
2. **Multi-Server Support**: Allow users to configure multiple GiljoAI servers
3. **Plugin Health Monitoring**: Periodic connection checks, notify if plugin becomes unavailable
4. **Installation Wizard**: Step-by-step guided setup with validation at each step
5. **OS-Specific Commands**: Detect user's OS and provide platform-specific install commands
6. **Uninstall Option**: Provide UI button to uninstall plugin

---

## Questions for Implementer

If you encounter any ambiguity during implementation, please clarify:

1. **Server URL Priority**: Should we add a manual override field for server URL, or rely on auto-detection?
2. **Verification Persistence**: Should we store the verification result in the database, or keep it session-only?
3. **Error Recovery**: Should we provide actionable suggestions for common errors (e.g., "Install Claude Code first")?
4. **Multi-Line Command Formatting**: Should we detect OS and format line continuations accordingly (backslash vs backtick)?

---

## Completion Criteria

This handover is considered complete when:

1. ✅ Component is implemented and passing all tests
2. ✅ Component is integrated into UserSettings.vue Integrations tab
3. ✅ Unit tests achieve >90% code coverage
4. ✅ Manual QA confirms all user flows work as expected
5. ✅ Copy-to-clipboard works in Chrome, Firefox, Safari, Edge
6. ✅ Test connection successfully verifies plugin setup
7. ✅ UI matches existing Vuetify theme and design patterns
8. ✅ Component is accessible (passes WCAG 2.1 AA standards)
9. ✅ Code review approved by team lead
10. ✅ Documentation updated with component API reference

---

## References

- **Parent Handover**: [0334a: CLI Plugin Verification API](handovers/0334a_cli_plugin_verification_api.md)
- **Sibling Handover**: [0334b: Claude Code Plugin Implementation](handovers/0334b_claude_code_plugin_implementation.md)
- **User Settings View**: `frontend/src/views/UserSettings.vue`
- **Existing Integration Cards**: `frontend/src/components/settings/SerenaIntegrationCard.vue`, `frontend/src/components/settings/ClaudeCodeExport.vue`
- **Auth Store**: `frontend/src/stores/auth.js`

---

## End of Handover

**Next Steps**:
1. Assign to Frontend Implementation Agent
2. Create feature branch: `feature/0334c-plugin-setup-ui`
3. Implement component following TDD approach
4. Run full test suite and ensure coverage >90%
5. Manual QA testing in dev environment
6. Code review and approval
7. Merge to master and deploy

**Estimated Effort**: 4-6 hours (including tests and QA)

**Risk Level**: LOW - Isolated component, no database changes, comprehensive tests
