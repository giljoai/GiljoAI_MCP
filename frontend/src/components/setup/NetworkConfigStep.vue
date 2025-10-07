<template>
  <v-card-text class="pa-8">
    <h2 class="text-h5 mb-2">Network Configuration</h2>
    <p class="text-body-1 mb-6">Configure how your team will access GiljoAI MCP</p>

    <!-- Mode Selection -->
    <v-radio-group v-model="selectedMode" class="mb-4">
      <v-row dense>
        <!-- Localhost Mode -->
        <v-col cols="12" md="4">
          <v-card
            variant="outlined"
            class="h-100 mode-card"
            :class="{ selected: selectedMode === 'localhost' }"
            @click="selectedMode = 'localhost'"
            role="button"
            tabindex="0"
            aria-label="Select localhost mode for single user"
          >
            <v-card-text class="pa-4">
              <v-radio value="localhost">
                <template #label>
                  <div class="ml-2">
                    <div class="text-h6 d-flex align-center">
                      <v-icon class="mr-2">mdi-laptop</v-icon>
                      Localhost
                    </div>
                    <div class="text-caption text-medium-emphasis">
                      (Recommended)
                    </div>
                  </div>
                </template>
              </v-radio>

              <v-list density="compact" class="mt-3 bg-transparent">
                <v-list-item
                  prepend-icon="mdi-check"
                  title="No network configuration"
                  class="text-caption"
                />
                <v-list-item
                  prepend-icon="mdi-check"
                  title="No authentication"
                  class="text-caption"
                />
                <v-list-item
                  prepend-icon="mdi-check"
                  title="Fastest performance"
                  class="text-caption"
                />
                <v-list-item
                  prepend-icon="mdi-check"
                  title="Most secure"
                  class="text-caption"
                />
              </v-list>
            </v-card-text>
          </v-card>
        </v-col>

        <!-- LAN Mode -->
        <v-col cols="12" md="4">
          <v-card
            variant="outlined"
            class="h-100 mode-card"
            :class="{ selected: selectedMode === 'lan' }"
            @click="selectedMode = 'lan'"
            role="button"
            tabindex="0"
            aria-label="Select LAN mode for team access"
          >
            <v-card-text class="pa-4">
              <v-radio value="lan">
                <template #label>
                  <div class="ml-2">
                    <div class="text-h6 d-flex align-center">
                      <v-icon class="mr-2">mdi-network</v-icon>
                      LAN
                    </div>
                    <div class="text-caption text-medium-emphasis">
                      Team access on your network
                    </div>
                  </div>
                </template>
              </v-radio>

              <v-list density="compact" class="mt-3 bg-transparent">
                <v-list-item
                  prepend-icon="mdi-check"
                  title="Multiple users"
                  class="text-caption"
                />
                <v-list-item
                  prepend-icon="mdi-check"
                  title="Network configuration"
                  class="text-caption"
                />
                <v-list-item
                  prepend-icon="mdi-check"
                  title="Authentication enabled"
                  class="text-caption"
                />
                <v-list-item
                  prepend-icon="mdi-check"
                  title="Small teams (2-10)"
                  class="text-caption"
                />
              </v-list>
            </v-card-text>
          </v-card>
        </v-col>

        <!-- WAN/Hosted Mode (Future) -->
        <v-col cols="12" md="4">
          <v-card
            variant="outlined"
            class="h-100 mode-card disabled-card"
            disabled
            aria-label="WAN/Hosted mode coming soon"
          >
            <v-card-text class="pa-4">
              <div class="d-flex align-center mb-1">
                <v-icon class="mr-2" color="disabled" size="large">mdi-cloud</v-icon>
                <div>
                  <div class="text-h6 text-disabled">
                    WAN/Hosted
                  </div>
                  <v-chip size="small" color="info" class="mt-1">Future</v-chip>
                </div>
              </div>

              <v-list density="compact" class="mt-3 bg-transparent">
                <v-list-item
                  prepend-icon="mdi-check"
                  title="Global internet access"
                  class="text-caption text-disabled"
                />
                <v-list-item
                  prepend-icon="mdi-check"
                  title="Cloud deployment"
                  class="text-caption text-disabled"
                />
                <v-list-item
                  prepend-icon="mdi-check"
                  title="Enterprise security"
                  class="text-caption text-disabled"
                />
                <v-list-item
                  prepend-icon="mdi-check"
                  title="Unlimited users"
                  class="text-caption text-disabled"
                />
              </v-list>
            </v-card-text>
          </v-card>
        </v-col>
      </v-row>
    </v-radio-group>

    <!-- LAN Configuration Panel (Expandable) -->
    <v-expand-transition>
      <v-card v-if="selectedMode === 'lan'" variant="outlined" class="lan-config-panel mb-4">
        <v-card-title class="bg-surface-variant">
          <v-icon start>mdi-cog</v-icon>
          LAN Configuration
        </v-card-title>
        <v-card-text class="pt-4">
          <!-- Server IP -->
          <v-text-field
            v-model="lanConfig.serverIp"
            label="Server IP Address"
            variant="outlined"
            placeholder="e.g., 192.168.1.100 or 10.1.0.164"
            hint="Enter the IP address of this computer on your physical network (not virtual adapters)"
            persistent-hint
            class="mb-4"
            :rules="[rules.required, rules.ipAddress]"
          />

          <!-- Port -->
          <v-text-field
            v-model="lanConfig.port"
            label="API Port"
            variant="outlined"
            type="number"
            hint="Default: 7272"
            persistent-hint
            class="mb-4"
            :rules="[rules.required, rules.port]"
          />

          <!-- Admin Credentials -->
          <h3 class="text-h6 mb-3">Administrator Account</h3>
          <p class="text-caption text-medium-emphasis mb-3">
            Create an admin account for the GiljoAI API. This is used for API authentication and user management, not your operating system login.
          </p>

          <v-text-field
            v-model="lanConfig.adminUsername"
            label="Admin Username"
            variant="outlined"
            hint="Username for the GiljoAI administrator account"
            persistent-hint
            class="mb-4"
            :rules="[rules.required]"
          />

          <v-text-field
            v-model="lanConfig.adminPassword"
            label="Admin Password"
            variant="outlined"
            type="password"
            hint="Strong password for the GiljoAI administrator account"
            persistent-hint
            class="mb-4"
            :rules="[rules.required, rules.password]"
          />

          <!-- Firewall Configuration -->
          <h3 class="text-h6 mb-3">Firewall Configuration</h3>

          <div class="d-flex align-center mb-2">
            <v-checkbox
              v-model="lanConfig.firewallConfigured"
              label="I have configured my firewall to allow access on the API port"
              color="primary"
              hide-details
            />
            <v-icon
              size="small"
              class="ml-2"
              color="warning"
              style="cursor: pointer"
              @click="showFirewallHelp = true"
            >
              mdi-help-circle-outline
            </v-icon>
          </div>

          <!-- Network Setup Guide Download -->
          <v-alert type="info" variant="tonal" class="mt-4">
            <div class="text-body-2">
              <strong>After completing setup:</strong>
              <a @click="downloadLanGuide" class="lan-guide-link cursor-pointer ml-1">
                <v-icon size="small" class="mr-1">mdi-download</v-icon>
                Download LAN setup and testing guide
              </a>
              for firewall configuration, connectivity testing, and troubleshooting.
            </div>
          </v-alert>

          <!-- Optional Hostname -->
          <v-text-field
            v-model="lanConfig.hostname"
            label="Custom Hostname (Optional)"
            variant="outlined"
            hint="Friendly name for this server (e.g., giljo-dev-server)"
            persistent-hint
            class="mt-4"
          />

          <!-- LAN Warning -->
          <v-alert type="warning" variant="tonal" class="mt-4">
            <v-icon start>mdi-shield-alert</v-icon>
            <strong>Security Notice:</strong> LAN mode enables network access with API key
            authentication. Ensure your network is trusted and secure.
          </v-alert>
        </v-card-text>
      </v-card>
    </v-expand-transition>

    <!-- Info Alert -->
    <v-alert type="info" variant="tonal" class="mb-6">
      You can change deployment mode later in Settings, but this may require service restart.
    </v-alert>

    <!-- Progress -->
    <v-card variant="outlined" class="mb-6">
      <v-card-text>
        <div class="d-flex justify-space-between mb-2">
          <span class="text-caption">Progress: Step 4 of 5</span>
          <span class="text-caption">80%</span>
        </div>
        <v-progress-linear :model-value="80" color="warning" />
      </v-card-text>
    </v-card>

    <!-- Firewall Help Modal -->
    <v-dialog v-model="showFirewallHelp" max-width="700">
      <v-card>
        <v-card-title class="d-flex align-center bg-warning">
          <v-icon start color="white">mdi-shield-lock</v-icon>
          <span class="text-white">Firewall Configuration Help</span>
        </v-card-title>
        <v-card-text class="pt-4">
          <v-alert type="info" variant="tonal" class="mb-4">
            <strong>Note:</strong> All commands require administrator/root privileges
          </v-alert>

          <!-- Windows -->
          <div class="mb-4">
            <h3 class="text-h6 mb-2">
              <v-icon color="primary">mdi-microsoft-windows</v-icon>
              Windows
            </h3>
            <p class="text-caption mb-2">Run in Command Prompt as Administrator:</p>
            <v-card variant="outlined" class="mb-2">
              <v-card-text class="pa-2">
                <div class="d-flex align-center">
                  <code class="flex-grow-1">netsh advfirewall firewall add rule name="GiljoAI API" dir=in action=allow protocol=TCP localport={{ lanConfig.port }}</code>
                  <v-btn
                    icon="mdi-content-copy"
                    size="small"
                    variant="text"
                    @click="copyToClipboard(`netsh advfirewall firewall add rule name=&quot;GiljoAI API&quot; dir=in action=allow protocol=TCP localport=${lanConfig.port}`, 'firewall-win')"
                  />
                </div>
              </v-card-text>
            </v-card>
          </div>

          <!-- Linux (UFW) -->
          <div class="mb-4">
            <h3 class="text-h6 mb-2">
              <v-icon color="primary">mdi-linux</v-icon>
              Linux (Ubuntu/Debian - UFW)
            </h3>
            <p class="text-caption mb-2">Run in terminal with sudo:</p>
            <v-card variant="outlined" class="mb-2">
              <v-card-text class="pa-2">
                <div class="d-flex align-center">
                  <code class="flex-grow-1">sudo ufw allow {{ lanConfig.port }}/tcp</code>
                  <v-btn
                    icon="mdi-content-copy"
                    size="small"
                    variant="text"
                    @click="copyToClipboard(`sudo ufw allow ${lanConfig.port}/tcp`, 'firewall-ufw')"
                  />
                </div>
              </v-card-text>
            </v-card>
            <v-card variant="outlined" class="mb-2">
              <v-card-text class="pa-2">
                <div class="d-flex align-center">
                  <code class="flex-grow-1">sudo ufw enable</code>
                  <v-btn
                    icon="mdi-content-copy"
                    size="small"
                    variant="text"
                    @click="copyToClipboard('sudo ufw enable', 'firewall-ufw-enable')"
                  />
                </div>
              </v-card-text>
            </v-card>
          </div>

          <!-- Linux (firewalld) -->
          <div class="mb-4">
            <h3 class="text-h6 mb-2">
              <v-icon color="primary">mdi-linux</v-icon>
              Linux (RHEL/CentOS/Fedora - firewalld)
            </h3>
            <p class="text-caption mb-2">Run in terminal with sudo:</p>
            <v-card variant="outlined" class="mb-2">
              <v-card-text class="pa-2">
                <div class="d-flex align-center">
                  <code class="flex-grow-1">sudo firewall-cmd --permanent --add-port={{ lanConfig.port }}/tcp</code>
                  <v-btn
                    icon="mdi-content-copy"
                    size="small"
                    variant="text"
                    @click="copyToClipboard(`sudo firewall-cmd --permanent --add-port=${lanConfig.port}/tcp`, 'firewall-firewalld')"
                  />
                </div>
              </v-card-text>
            </v-card>
            <v-card variant="outlined" class="mb-2">
              <v-card-text class="pa-2">
                <div class="d-flex align-center">
                  <code class="flex-grow-1">sudo firewall-cmd --reload</code>
                  <v-btn
                    icon="mdi-content-copy"
                    size="small"
                    variant="text"
                    @click="copyToClipboard('sudo firewall-cmd --reload', 'firewall-firewalld-reload')"
                  />
                </div>
              </v-card-text>
            </v-card>
          </div>

          <!-- macOS -->
          <div class="mb-4">
            <h3 class="text-h6 mb-2">
              <v-icon color="primary">mdi-apple</v-icon>
              macOS
            </h3>
            <p class="text-body-2">
              1. Open System Preferences → Security & Privacy → Firewall<br>
              2. Click "Firewall Options"<br>
              3. Click "+" and add the GiljoAI API application<br>
              4. Set to "Allow incoming connections"
            </p>
          </div>
        </v-card-text>
        <v-card-actions>
          <v-spacer />
          <v-btn color="primary" @click="showFirewallHelp = false">
            <span class="text-white">Close</span>
          </v-btn>
        </v-card-actions>
      </v-card>
    </v-dialog>

    <!-- Navigation -->
    <div class="d-flex justify-space-between">
      <v-btn variant="outlined" @click="$emit('back')" aria-label="Go back to tool attachment">
        <v-icon start>mdi-arrow-left</v-icon>
        Back
      </v-btn>
      <v-btn
        color="primary"
        :disabled="!canProceed"
        @click="handleNext"
        aria-label="Continue to completion"
      >
        Continue
        <v-icon end>mdi-arrow-right</v-icon>
      </v-btn>
    </div>
  </v-card-text>
</template>

<script setup>
import { ref, computed, watch, onMounted } from 'vue'
import setupService from '@/services/setupService'

/**
 * NetworkConfigStep - Network configuration step (Step 2 of 3)
 *
 * Allows user to choose between localhost and LAN modes
 */

const props = defineProps({
  mode: {
    type: String,
    required: true,
    validator: (value) => ['localhost', 'lan'].includes(value),
  },
  lanSettings: {
    type: Object,
    default: null,
  },
})

const emit = defineEmits(['update:mode', 'update:lanSettings', 'next', 'back'])

// State
const selectedMode = ref(props.mode)
const detectingIp = ref(false)
const showFirewallHelp = ref(false)

const lanConfig = ref({
  serverIp: props.lanSettings?.serverIp || '',
  port: props.lanSettings?.port || 7272,
  adminUsername: props.lanSettings?.adminUsername || '',
  adminPassword: props.lanSettings?.adminPassword || '',
  firewallConfigured: props.lanSettings?.firewallConfigured || false,
  hostname: props.lanSettings?.hostname || '',
})

// Validation rules
const rules = {
  required: (value) => !!value || 'This field is required',
  ipAddress: (value) => {
    if (!value) return true
    const ipPattern = /^(\d{1,3}\.){3}\d{1,3}$/
    return ipPattern.test(value) || 'Invalid IP address format'
  },
  port: (value) => {
    const port = parseInt(value)
    return (port >= 1 && port <= 65535) || 'Port must be between 1 and 65535'
  },
  password: (value) => {
    if (!value) return true
    return value.length >= 8 || 'Password must be at least 8 characters'
  },
}

// Computed
const canProceed = computed(() => {
  if (selectedMode.value === 'localhost') {
    return true
  }

  // For LAN mode, require all required fields (hostname is optional)
  return !!(
    lanConfig.value.serverIp &&
    lanConfig.value.port &&
    lanConfig.value.adminUsername &&
    lanConfig.value.adminPassword &&
    lanConfig.value.adminPassword.length >= 8 &&
    lanConfig.value.firewallConfigured
  )
})

// Watch for mode changes
watch(selectedMode, (newMode) => {
  emit('update:mode', newMode)
})

// Watch for LAN config changes
watch(
  lanConfig,
  (newConfig) => {
    if (selectedMode.value === 'lan') {
      emit('update:lanSettings', { ...newConfig })
    }
  },
  { deep: true },
)

// Methods
const copyToClipboard = async (text, id) => {
  try {
    await navigator.clipboard.writeText(text)
    console.log(`[NETWORK_CONFIG] Copied ${id} to clipboard`)
  } catch (err) {
    console.error(`[NETWORK_CONFIG] Failed to copy ${id}:`, err)
  }
}

const handleNext = () => {
  // Emit final configuration
  if (selectedMode.value === 'lan') {
    emit('update:lanSettings', { ...lanConfig.value })
  } else {
    emit('update:lanSettings', null)
  }

  console.log('[NETWORK_CONFIG] Moving to next step with mode:', selectedMode.value)
  emit('next')
}

// Lifecycle - load existing config
onMounted(async () => {
  console.log('[NETWORK_CONFIG] Loading existing configuration')
  
  try {
    const status = await setupService.checkStatus()
    console.log('[NETWORK_CONFIG] Current status:', status)
    
    // Set mode from existing config
    if (status.network_mode) {
      selectedMode.value = status.network_mode
      console.log('[NETWORK_CONFIG] Loaded mode:', status.network_mode)
    }
    
    // Load existing config from config.yaml
    const response = await fetch(`${setupService.baseURL}/api/v1/config`)
    if (response.ok) {
      const config = await response.json()
      console.log('[NETWORK_CONFIG] Loaded config:', config)
      
      // If LAN mode, populate fields from server config
      if (config.server) {
        lanConfig.value.serverIp = config.server.ip || lanConfig.value.serverIp
        lanConfig.value.hostname = config.server.hostname || lanConfig.value.hostname
        lanConfig.value.adminUsername = config.server.admin_user || lanConfig.value.adminUsername
        lanConfig.value.firewallConfigured = config.server.firewall_configured || false
        console.log('[NETWORK_CONFIG] Loaded LAN settings from config')
      }
      
      // Load API port if available
      if (config.services?.api?.port) {
        lanConfig.value.port = config.services.api.port
      }
    }
  } catch (error) {
    console.error('[NETWORK_CONFIG] Failed to load existing config:', error)
    // Non-fatal, continue with defaults
  }
})

// Download LAN setup guide
const downloadLanGuide = () => {
  const guideContent = `# GiljoAI MCP - LAN/Server Mode Setup Guide

**After completing the Setup Wizard and restarting services**

This guide helps you verify and troubleshoot network connectivity for GiljoAI MCP in Server/LAN mode.

---

## Overview

In **Server/LAN mode**, GiljoAI MCP:
- Binds the API server to \`0.0.0.0\` (all network interfaces)
- Requires API key authentication
- Allows access from other devices on your network

**Important**: These tests only work AFTER you've completed the wizard and restarted the services.

---

## Step 1: Configure Firewall

### Windows

Open PowerShell as Administrator and run:

\`\`\`powershell
New-NetFirewallRule -DisplayName "GiljoAI MCP API" -Direction Inbound -LocalPort ${lanConfig.value.port} -Protocol TCP -Action Allow
\`\`\`

**Verify the rule:**
\`\`\`powershell
Get-NetFirewallRule -DisplayName "GiljoAI MCP API"
\`\`\`

### Linux (UFW)

\`\`\`bash
sudo ufw allow ${lanConfig.value.port}/tcp
sudo ufw enable
sudo ufw status
\`\`\`

### Linux (firewalld)

\`\`\`bash
sudo firewall-cmd --add-port=${lanConfig.value.port}/tcp --permanent
sudo firewall-cmd --reload
sudo firewall-cmd --list-ports
\`\`\`

### macOS

\`\`\`bash
# Add firewall rule (if firewall is enabled)
sudo /usr/libexec/ApplicationFirewall/socketfilterfw --add /path/to/python
sudo /usr/libexec/ApplicationFirewall/socketfilterfw --unblockapp /path/to/python
\`\`\`

Or configure via System Preferences > Security & Privacy > Firewall > Firewall Options

---

## Step 2: Verify Network Configuration

### Check Your Server IP Address

**Windows:**
\`\`\`powershell
ipconfig | findstr "IPv4"
\`\`\`

**Linux/macOS:**
\`\`\`bash
ip addr show | grep "inet "
# or
ifconfig | grep "inet "
\`\`\`

**Look for your local network IP** (usually starts with \`192.168.x.x\` or \`10.x.x.x\`)

Your detected IP: **${lanConfig.value.serverIp}**

### Verify Services Are Running

**Check API Server:**
\`\`\`bash
# On the server machine
curl http://localhost:${lanConfig.value.port}/health
\`\`\`

Expected response:
\`\`\`json
{"status": "ok"}
\`\`\`

---

## Step 3: Test Network Connectivity

**From another device on the same network:**

### Test 1: Ping Test (Basic Connectivity)

Replace \`SERVER_IP\` with your server's IP address (${lanConfig.value.serverIp}):

**Windows/Linux/macOS:**
\`\`\`bash
ping ${lanConfig.value.serverIp}
\`\`\`

**Expected:** You should see replies. If timeouts occur, check:
- Firewall configuration
- Both devices are on the same network
- Server is powered on and connected

### Test 2: API Health Check

\`\`\`bash
curl http://${lanConfig.value.serverIp}:${lanConfig.value.port}/health
\`\`\`

**Expected:**
\`\`\`json
{"status": "ok"}
\`\`\`

**If this fails:**
- Verify firewall allows port ${lanConfig.value.port}
- Check API server is running on the server machine
- Confirm API is bound to \`0.0.0.0\` (check \`config.yaml\` has \`mode: server\`)

### Test 3: Browser Access

Open a web browser on the client device and navigate to:

\`\`\`
http://${lanConfig.value.serverIp}:7274
\`\`\`

**Expected:** You should see the GiljoAI MCP dashboard login page.

**If this fails:**
- Verify frontend service is running
- Check firewall allows port 7274
- Clear browser cache and try again

---

## Step 4: API Authentication

In Server/LAN mode, API requests require authentication.

### Get Your API Key

1. Log into the dashboard: \`http://${lanConfig.value.serverIp}:7274\`
2. Navigate to **Settings** > **API Keys**
3. Copy your API key

### Test Authenticated API Request

Replace \`YOUR_API_KEY\`:

\`\`\`bash
curl -H "X-API-Key: YOUR_API_KEY" http://${lanConfig.value.serverIp}:${lanConfig.value.port}/api/projects
\`\`\`

**Expected:** JSON response with your projects list.

---

## Troubleshooting

### Issue: Ping works, but API/Browser doesn't

**Cause:** Firewall is blocking specific ports.

**Solution:**
1. Re-run firewall commands for ports ${lanConfig.value.port} and 7274
2. Restart firewall service (Linux)
3. Check Windows Defender isn't blocking Python

### Issue: "Connection Refused" on API

**Cause:** API server isn't running or not bound to \`0.0.0.0\`.

**Solution:**
1. Check API is running: \`curl http://localhost:${lanConfig.value.port}/health\`
2. Verify \`config.yaml\` has \`mode: server\` and \`host: 0.0.0.0\`
3. Restart API server: \`python api/run_api.py\`

### Issue: "401 Unauthorized" on API requests

**Cause:** Missing or invalid API key.

**Solution:**
1. Verify API key in dashboard Settings
2. Include header: \`-H "X-API-Key: YOUR_API_KEY"\`
3. Check API key hasn't been revoked

### Issue: Can't access from specific device

**Cause:** Client device firewall or network isolation.

**Solution:**
1. Check client device firewall settings
2. Verify both devices on same network (not guest network)
3. Try from another device to isolate the problem

### Issue: Intermittent connectivity

**Cause:** Router/network configuration issues.

**Solution:**
1. Assign static IP to server machine
2. Check router isn't blocking inter-device communication
3. Disable "AP Isolation" in router settings (if enabled)

---

## Security Recommendations

### For Local Network (LAN) Deployment:

- ✅ Use strong API keys (generated by the system)
- ✅ Rotate API keys periodically
- ✅ Firewall rules limit access to specific ports
- ✅ Database remains localhost-only (secure)

### For Internet (WAN) Deployment:

⚠️ **Additional security required:**
- Use HTTPS/TLS certificates (reverse proxy recommended)
- Implement rate limiting
- Use VPN for remote access
- Consider authentication beyond API keys (OAuth, SAML)
- Regular security audits

**Note:** GiljoAI MCP is designed for trusted networks. For internet exposure, consult security best practices and consider professional security review.

---

## Port Reference

| Service | Port | Protocol | Purpose |
|---------|------|----------|---------|
| API Server | ${lanConfig.value.port} | TCP | REST API and WebSocket |
| Frontend Dashboard | 7274 | TCP | Web UI |
| PostgreSQL | 5432 | TCP | Database (localhost only) |

**Important:** PostgreSQL should NEVER be exposed to the network. It only accepts connections from \`localhost\` (127.0.0.1).

---

## Getting Help

If you encounter issues not covered in this guide:

1. Check application logs:
   - API logs: \`logs/api.log\`
   - Application logs: \`logs/giljo_mcp.log\`

2. Review documentation:
   - \`docs/README_FIRST.md\` - Project overview
   - \`docs/TECHNICAL_ARCHITECTURE.md\` - System architecture

3. GitHub Issues:
   - Report bugs: https://github.com/yourusername/giljo-mcp/issues

---

**Generated by GiljoAI MCP Setup Wizard**
*Version 1.0 - Server/LAN Mode Configuration*
*Server IP: ${lanConfig.value.serverIp}*
*API Port: ${lanConfig.value.port}*
`

  // Create blob and download
  const blob = new Blob([guideContent], { type: 'text/markdown' })
  const url = URL.createObjectURL(blob)
  const link = document.createElement('a')
  link.href = url
  link.download = 'LAN_SETUP_GUIDE.md'
  link.click()
  URL.revokeObjectURL(url)
}
</script>

<style scoped>
h2 {
  color: rgb(var(--v-theme-primary));
}

.mode-card {
  cursor: pointer;
  transition: all 0.2s ease;
  border-width: 2px;
}

.mode-card:hover {
  border-color: rgba(var(--v-theme-primary), 0.5);
  box-shadow: 0 2px 4px rgba(0, 0, 0, 0.1);
}

.mode-card.selected {
  border-color: rgb(var(--v-theme-warning));
  background-color: rgba(var(--v-theme-warning), 0.05);
  border-width: 3px;
}

.lan-config-panel {
  border-color: rgb(var(--v-theme-primary));
  border-width: 2px;
}

.disabled-card {
  opacity: 0.6;
  cursor: not-allowed;
}

.disabled-card:hover {
  border-color: rgba(var(--v-theme-surface-variant), 0.5) !important;
  box-shadow: none !important;
}

.cursor-pointer {
  cursor: pointer;
}

.lan-guide-link {
  color: #ffc300 !important; /* Giljo yellow for maximum visibility */
  font-weight: 600;
  text-decoration: none;
}

.lan-guide-link:hover {
  color: #ffffff !important; /* Pure white on hover */
  text-decoration: underline;
}

/* Disabled button styling - more faded */
.v-btn:disabled {
  opacity: 0.3 !important;
  background-color: rgba(158, 158, 158, 0.12) !important;
}

.v-btn:disabled .v-btn__content {
  color: rgba(158, 158, 158, 0.5) !important;
}
</style>
