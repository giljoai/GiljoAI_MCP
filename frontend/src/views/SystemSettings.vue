<template>
  <v-container>
    <!-- Page Header -->
    <h1 class="text-h4 mb-2">Admin Settings</h1>
    <p class="text-subtitle-1 mb-4">Configure server and system-wide settings (Admin only)</p>

    <!-- Settings Tabs -->
    <v-tabs v-model="activeTab" class="mb-6">
      <v-tab value="network">
        <v-icon start>mdi-network-outline</v-icon>
        Network
      </v-tab>
      <v-tab value="database">
        <v-icon start>mdi-database</v-icon>
        Database
      </v-tab>
      <v-tab value="integrations">
        <v-icon start>mdi-api</v-icon>
        Integrations
      </v-tab>
      <v-tab value="users">
        <v-icon start>mdi-account-multiple</v-icon>
        Users
      </v-tab>
    </v-tabs>

    <!-- Tab Content -->
    <v-window v-model="activeTab">
      <!-- Network Settings -->
      <v-window-item value="network">
        <v-card>
          <v-card-title>Network Configuration</v-card-title>
          <v-card-subtitle>Manage deployment mode and network access</v-card-subtitle>

          <v-card-text>
            <!-- Current Mode Display -->
            <v-alert type="info" variant="tonal" class="mb-4">
              <div class="d-flex align-center">
                <v-icon start>mdi-information</v-icon>
                <div>
                  <strong>Current Mode:</strong>
                  <v-chip :color="modeColor" size="small" class="ml-2" data-test="mode-chip">
                    {{ currentMode.toUpperCase() }}
                  </v-chip>
                </div>
              </div>
            </v-alert>

            <!-- API Binding Info -->
            <h3 class="text-h6 mb-3">API Server Configuration</h3>

            <v-text-field
              :model-value="networkSettings.apiHost"
              label="API Host Binding"
              variant="outlined"
              readonly
              hint="127.0.0.1 = localhost only, specific IP = network accessible"
              persistent-hint
              class="mb-4"
              data-test="api-host-field"
            />

            <v-text-field
              :model-value="networkSettings.apiPort"
              label="API Port"
              variant="outlined"
              readonly
              hint="Default: 7272"
              persistent-hint
              class="mb-4"
              data-test="api-port-field"
            />

            <!-- CORS Origins Management -->
            <v-divider class="my-6" />

            <h3 class="text-h6 mb-3">CORS Allowed Origins</h3>

            <div data-test="cors-origins-section">
              <v-list density="compact" class="mb-4">
                <v-list-item v-for="(origin, index) in corsOrigins" :key="index">
                  <v-list-item-title>{{ origin }}</v-list-item-title>

                  <template v-slot:append>
                    <v-btn
                      icon="mdi-content-copy"
                      size="small"
                      variant="text"
                      @click="copyOrigin(origin)"
                    />
                    <v-btn
                      v-if="!isDefaultOrigin(origin)"
                      icon="mdi-delete"
                      size="small"
                      variant="text"
                      color="error"
                      @click="removeOrigin(index)"
                    />
                  </template>
                </v-list-item>
              </v-list>

              <v-text-field
                v-model="newOrigin"
                label="Add New Origin"
                variant="outlined"
                placeholder="http://192.168.1.100:7274"
                hint="Format: http://hostname:port or http://ip:port"
                persistent-hint
                :append-icon="'mdi-plus'"
                @click:append="addOrigin"
                @keyup.enter="addOrigin"
              />
            </div>

            <!-- API Key Info (Readonly for now) -->
            <v-divider class="my-6" />

            <h3 class="text-h6 mb-3">API Key Information</h3>

            <!-- v3.0 Unified: Authentication always enabled for all IPs -->
            <template v-if="currentMode === 'localhost'">
              <v-alert type="info" variant="tonal">
                <div class="d-flex align-center">
                  <v-icon start>mdi-shield-check</v-icon>
                  <div>v3.0 Unified: Authentication required for all network access</div>
                </div>
              </v-alert>
            </template>

            <template v-else-if="currentMode === 'lan'">
              <v-alert type="success" variant="tonal" class="mb-4">
                <div class="d-flex align-center">
                  <v-icon start>mdi-shield-check</v-icon>
                  <div>LAN mode requires API key authentication for secure network access</div>
                </div>
              </v-alert>

              <v-text-field
                v-if="apiKeyInfo"
                :model-value="maskedApiKey"
                label="Active API Key"
                variant="outlined"
                readonly
                hint="Key is masked for security. Clients must use this key to authenticate."
                persistent-hint
                class="mb-2"
                data-test="api-key-field"
              >
                <template v-slot:append>
                  <v-btn
                    icon="mdi-content-copy"
                    size="small"
                    variant="text"
                    @click="copyApiKey"
                    title="Copy API Key"
                  />
                </template>
              </v-text-field>

              <v-text-field
                v-if="apiKeyInfo"
                :model-value="apiKeyInfo.created_at"
                label="Created At"
                variant="outlined"
                readonly
                class="mb-4"
              />

              <v-btn variant="outlined" color="warning" @click="showRegenerateDialog = true">
                <v-icon start>mdi-refresh</v-icon>
                Regenerate API Key
              </v-btn>
            </template>

            <!-- Deployment Mode Change via Setup Wizard -->
            <v-divider class="my-6" />

            <h3 class="text-h6 mb-3">Change Deployment Mode</h3>

            <v-alert type="info" variant="tonal" class="mb-4">
              To change deployment mode (localhost ↔ LAN), use the Setup Wizard below. This ensures
              all network settings, API keys, and configurations are properly updated.
            </v-alert>
          </v-card-text>

          <v-card-actions>
            <v-btn variant="outlined" @click="navigateToSetupWizard">
              <v-icon start>mdi-wizard-hat</v-icon>
              Re-run Setup Wizard
            </v-btn>
            <v-spacer />
            <v-btn variant="text" @click="loadNetworkSettings">
              <v-icon start>mdi-refresh</v-icon>
              Reload
            </v-btn>
            <v-btn color="primary" :disabled="!networkSettingsChanged" @click="saveNetworkSettings">
              Save Changes
            </v-btn>
          </v-card-actions>
        </v-card>
      </v-window-item>

      <!-- Database Settings -->
      <v-window-item value="database">
        <DatabaseConnection
          :readonly="true"
          :show-title="true"
          title="PostgreSQL Database Configuration"
          :show-info-banner="true"
          info-banner-text="Database settings are configured during installation"
          :show-test-button="true"
          test-button-text="Test Connection"
          @connection-success="handleDatabaseSuccess"
          @connection-error="handleDatabaseError"
        >
          <template #actions>
            <v-btn variant="text" @click="loadDatabaseSettings">
              <v-icon start>mdi-refresh</v-icon>
              Reload from Config
            </v-btn>
          </template>
        </DatabaseConnection>
      </v-window-item>

      <!-- Integrations -->
      <v-window-item value="integrations">
        <v-card>
          <v-card-title>Integrations</v-card-title>
          <v-card-subtitle>Agent coding tools and native integrations (Admin overview)</v-card-subtitle>

          <v-card-text>
            <!-- Agent Coding Tools Section -->
            <h2 class="text-h5 mb-4">Agent Coding Tools</h2>
            
            <!-- Claude Code CLI -->
            <v-card variant="outlined" class="mb-4">
              <v-card-text>
                <div class="d-flex align-center mb-3">
                  <v-avatar size="48" class="mr-4">
                    <v-img src="/Claude_AI_symbol.svg" alt="Claude Code CLI" />
                  </v-avatar>
                  <div>
                    <h3 class="text-h6">Claude Code CLI</h3>
                    <p class="text-caption text-medium-emphasis mb-0">AI-powered development with MCP integration</p>
                  </div>
                </div>

                <v-alert color="warning" variant="tonal" class="mb-3">
                  <v-icon start>mdi-alert</v-icon>
                  <strong>FINISH THESE INSTRUCTIONS AFTER ALPHA TESTING AND AGENT CREATION IS DONE</strong>
                </v-alert>

                <p class="text-body-2 mb-3">
                  GiljoAI Agent Orchestration MCP Server integrates seamlessly with Claude Code CLI, leveraging 
                  MCP configuration through Claude Code marketplace tools and specialized sub-agents. Our system 
                  creates coordinated agent teams that break through context limits with 70% token reduction.
                </p>

                <p class="text-body-2 mb-3">
                  <strong>Sub-agent Architecture:</strong> Claude Code spawns specialized sub-agents for different 
                  development tasks while GiljoAI MCP serves as the persistent orchestration brain, managing state, 
                  memory, and coordination across agent teams.
                </p>

                <p class="text-body-2 mb-3">
                  <strong>Configuration:</strong> Each user must generate an API key under their user profile and 
                  configure Claude Code either through the marketplace function or manually.
                </p>

                <v-btn variant="outlined" color="primary" @click="showClaudeConfigModal = true">
                  <v-icon start>mdi-cog</v-icon>
                  How to Configure Claude Code
                </v-btn>
              </v-card-text>
            </v-card>

            <!-- Codex CLI -->
            <v-card variant="outlined" class="mb-4">
              <v-card-text>
                <div class="d-flex align-center mb-3">
                  <v-avatar size="48" class="mr-4">
                    <v-img src="/codex_logo.svg" alt="Codex CLI" />
                  </v-avatar>
                  <div>
                    <h3 class="text-h6">Codex CLI</h3>
                    <p class="text-caption text-medium-emphasis mb-0">Advanced code generation and analysis</p>
                  </div>
                </div>

                <p class="text-body-2 mb-3">
                  Codex CLI integrates with our sub-agent architecture to provide powerful code generation and 
                  analysis capabilities. Sub-agents coordinate through GiljoAI MCP for complex development workflows, 
                  maintaining context and state across multiple coding sessions.
                </p>

                <p class="text-body-2 mb-3">
                  <strong>Configuration:</strong> Generate an API key under your user profile and configure Codex 
                  manually using our copy/paste method or downloadable instructions.
                </p>

                <v-btn variant="outlined" color="secondary" @click="showCodexConfigModal = true">
                  <v-icon start>mdi-cog</v-icon>
                  How to Configure Codex
                </v-btn>
              </v-card-text>
            </v-card>

            <!-- Gemini CLI -->
            <v-card variant="outlined" class="mb-6">
              <v-card-text>
                <div class="d-flex align-center mb-3">
                  <v-avatar size="48" class="mr-4">
                    <v-img src="/gemini-icon.svg" alt="Gemini CLI" />
                  </v-avatar>
                  <div class="d-flex align-center">
                    <div class="mr-3">
                      <h3 class="text-h6">Gemini CLI</h3>
                      <p class="text-caption text-medium-emphasis mb-0">Google's advanced AI development platform</p>
                    </div>
                    <v-chip color="warning" size="small" variant="flat">
                      COMING SOON
                    </v-chip>
                  </div>
                </div>

                <p class="text-body-2 mb-0">
                  Integration with Google's Gemini AI platform for enhanced development capabilities. 
                  Sub-agent architecture and MCP integration planned for future releases.
                </p>
              </v-card-text>
            </v-card>

            <!-- Native Integrations Section -->
            <v-divider class="my-6"></v-divider>
            
            <h2 class="text-h5 mb-4">Native Integrations</h2>

            <!-- Serena Integration -->
            <v-card variant="outlined" class="mb-4">
              <v-card-text>
                <div class="d-flex align-center mb-3">
                  <v-avatar size="48" class="mr-4">
                    <v-img src="/Serena.png" alt="Serena MCP" />
                  </v-avatar>
                  <div>
                    <h3 class="text-h6">Serena MCP</h3>
                    <p class="text-caption text-medium-emphasis mb-0">Intelligent codebase understanding and navigation</p>
                  </div>
                </div>

                <p class="text-body-2 mb-3">
                  Serena provides deep semantic code analysis, intelligent symbol navigation, and contextual 
                  understanding of your codebase. It enables agents to efficiently explore and understand 
                  project structure without reading unnecessary code, significantly improving performance 
                  and reducing token usage.
                </p>

                <div class="d-flex align-center mb-3">
                  <v-btn variant="text" size="small" color="primary" href="https://github.com/oraios/serena" target="_blank">
                    <v-icon start>mdi-github</v-icon>
                    GitHub Repository
                  </v-btn>
                  <span class="text-caption text-medium-emphasis ml-3">
                    Credit: Oraios
                  </span>
                </div>

                <v-alert type="info" variant="tonal" class="mb-0">
                  <v-icon start>mdi-account-cog</v-icon>
                  <strong>User Configuration:</strong> Each user enables Serena under User Settings → Integrations
                </v-alert>
              </v-card-text>
            </v-card>

            <!-- More Coming Soon -->
            <v-card variant="outlined" color="surface-variant">
              <v-card-text class="text-center py-6">
                <v-icon size="48" color="medium-emphasis" class="mb-3">mdi-plus-circle-outline</v-icon>
                <h3 class="text-h6 text-medium-emphasis mb-2">More Integrations Coming Soon</h3>
                <p class="text-body-2 text-medium-emphasis mb-0">
                  Additional native integrations and agent tools will be added in future releases
                </p>
              </v-card-text>
            </v-card>
          </v-card-text>
        </v-card>
      </v-window-item>

      <!-- Users Management (Phase 5) -->
      <v-window-item value="users">
        <UserManager />
      </v-window-item>
    </v-window>

    <!-- Regenerate API Key Dialog -->
    <v-dialog v-model="showRegenerateDialog" max-width="500">
      <v-card>
        <v-card-title>Regenerate API Key</v-card-title>
        <v-card-text>
          <v-alert type="warning" variant="tonal" class="mb-4">
            <v-icon start>mdi-alert</v-icon>
            This will invalidate the current API key. All clients will need to update their configuration with the new key.
          </v-alert>
          Are you sure you want to regenerate the API key?
        </v-card-text>
        <v-card-actions>
          <v-spacer />
          <v-btn variant="text" @click="showRegenerateDialog = false">Cancel</v-btn>
          <v-btn color="warning" variant="flat" @click="regenerateApiKey">Regenerate</v-btn>
        </v-card-actions>
      </v-card>
    </v-dialog>

    <!-- Claude Code Configuration Modal -->
    <v-dialog v-model="showClaudeConfigModal" max-width="800" scrollable>
      <v-card>
        <v-card-title class="d-flex align-center">
          <v-icon start color="primary">mdi-robot-outline</v-icon>
          How to Configure Claude Code
        </v-card-title>
        
        <v-card-text>
          <v-alert type="info" variant="tonal" class="mb-4">
            <v-icon start>mdi-information</v-icon>
            First, generate an API key under your User Profile → Settings → API and Integrations
          </v-alert>

          <v-tabs v-model="claudeConfigTab" class="mb-4">
            <v-tab value="marketplace">Marketplace Configuration</v-tab>
            <v-tab value="manual">Manual Configuration</v-tab>
            <v-tab value="download">Download Instructions</v-tab>
          </v-tabs>

          <v-window v-model="claudeConfigTab">
            <!-- Marketplace Configuration -->
            <v-window-item value="marketplace">
              <h3 class="text-h6 mb-3">Claude Code Marketplace Configuration</h3>
              <ol class="text-body-2 mb-3">
                <li class="mb-2">Open Claude Code and navigate to the MCP Tools Marketplace</li>
                <li class="mb-2">Search for "GiljoAI Agent Orchestration MCP Server"</li>
                <li class="mb-2">Click "Install" and follow the marketplace prompts</li>
                <li class="mb-2">When prompted for the API endpoint, enter: <code>http://your-server-ip:7272</code></li>
                <li class="mb-2">Enter your API key from your user profile</li>
                <li class="mb-2">Test the connection and confirm installation</li>
              </ol>
            </v-window-item>

            <!-- Manual Configuration -->
            <v-window-item value="manual">
              <h3 class="text-h6 mb-3">Manual Configuration</h3>
              <p class="text-body-2 mb-3">
                Add the following to your Claude Code MCP configuration file. 
                See <a href="https://docs.claude.com/en/docs/claude-code/mcp" target="_blank" class="text-primary">Claude Code MCP Documentation</a> for complete setup instructions.
              </p>
              
              <v-alert type="info" variant="tonal" class="mb-3" density="compact">
                <v-icon start size="small">mdi-file-document</v-icon>
                <strong>Configuration File Location:</strong>
                <br>• macOS/Linux: <code>~/.claude.json</code>
                <br>• Windows: <code>%USERPROFILE%\.claude.json</code>
              </v-alert>
              
              <v-card variant="outlined" class="mb-3">
                <v-card-text>
                  <pre class="text-caption"><code>{
  "servers": {
    "giljo-mcp": {
      "command": "mcp-client",
      "args": [
        "--server-url", "http://your-server-ip:7272",
        "--api-key", "{your-api-key-here}"
      ],
      "description": "GiljoAI Agent Orchestration MCP Server"
    }
  }
}</code></pre>
                </v-card-text>
                <v-card-actions>
                  <v-btn variant="text" size="small" @click="copyClaudeConfig">
                    <v-icon start>mdi-content-copy</v-icon>
                    Copy Configuration
                  </v-btn>
                </v-card-actions>
              </v-card>

              <p class="text-body-2">
                Replace <code>{your-api-key-here}</code> with your actual API key from your user profile.
              </p>
            </v-window-item>

            <!-- Download Instructions -->
            <v-window-item value="download">
              <h3 class="text-h6 mb-3">Download Configuration Instructions</h3>
              <p class="text-body-2 mb-3">
                Download a complete setup guide with your server-specific configuration:
              </p>
              
              <v-btn variant="outlined" color="primary" @click="downloadClaudeInstructions">
                <v-icon start>mdi-download</v-icon>
                Download Claude Code Setup Guide
              </v-btn>
            </v-window-item>
          </v-window>
        </v-card-text>

        <v-card-actions>
          <v-spacer />
          <v-btn variant="text" @click="showClaudeConfigModal = false">Close</v-btn>
        </v-card-actions>
      </v-card>
    </v-dialog>

    <!-- Codex Configuration Modal -->
    <v-dialog v-model="showCodexConfigModal" max-width="800" scrollable>
      <v-card>
        <v-card-title class="d-flex align-center">
          <v-icon start color="secondary">mdi-code-braces</v-icon>
          How to Configure Codex CLI
        </v-card-title>
        
        <v-card-text>
          <v-alert type="info" variant="tonal" class="mb-4">
            <v-icon start>mdi-information</v-icon>
            First, generate an API key under your User Profile → Settings → API and Integrations
          </v-alert>

          <v-tabs v-model="codexConfigTab" class="mb-4">
            <v-tab value="manual">Manual Configuration</v-tab>
            <v-tab value="download">Download Instructions</v-tab>
          </v-tabs>

          <v-window v-model="codexConfigTab">
            <!-- Manual Configuration -->
            <v-window-item value="manual">
              <h3 class="text-h6 mb-3">Manual Configuration</h3>
              <p class="text-body-2 mb-3">
                Add the following to your Codex CLI configuration file. 
                See <a href="https://developers.openai.com/codex/local-config#cli" target="_blank" class="text-primary">Codex CLI Configuration</a> 
                and <a href="https://developers.openai.com/codex/mcp" target="_blank" class="text-primary">Codex MCP Documentation</a> for complete setup instructions.
              </p>
              
              <v-alert type="info" variant="tonal" class="mb-3" density="compact">
                <v-icon start size="small">mdi-file-document</v-icon>
                <strong>Configuration File Location:</strong>
                <br>• macOS/Linux: <code>~/.codex/config.toml</code>
                <br>• Windows: <code>%USERPROFILE%\\.codex\\config.toml</code>
              </v-alert>
              
              <v-card variant="outlined" class="mb-3">
                <v-card-text>
                  <pre class="text-caption"><code>[giljo-mcp]
endpoint = "http://your-server-ip:7272"
api_key = "{your-api-key-here}"
description = "GiljoAI Agent Orchestration MCP Server"

[agents]
orchestrator_enabled = true
subagent_coordination = true
context_sharing = true</code></pre>
                </v-card-text>
                <v-card-actions>
                  <v-btn variant="text" size="small" @click="copyCodexConfig">
                    <v-icon start>mdi-content-copy</v-icon>
                    Copy Configuration
                  </v-btn>
                </v-card-actions>
              </v-card>

              <p class="text-body-2">
                Replace <code>{your-api-key-here}</code> with your actual API key from your user profile.
              </p>
            </v-window-item>

            <!-- Download Instructions -->
            <v-window-item value="download">
              <h3 class="text-h6 mb-3">Download Configuration Instructions</h3>
              <p class="text-body-2 mb-3">
                Download a complete setup guide with your server-specific configuration:
              </p>
              
              <v-btn variant="outlined" color="secondary" @click="downloadCodexInstructions">
                <v-icon start>mdi-download</v-icon>
                Download Codex CLI Setup Guide
              </v-btn>
            </v-window-item>
          </v-window>
        </v-card-text>

        <v-card-actions>
          <v-spacer />
          <v-btn variant="text" @click="showCodexConfigModal = false">Close</v-btn>
        </v-card-actions>
      </v-card>
    </v-dialog>
  </v-container>
</template>

<script setup>
import { ref, onMounted, computed } from 'vue'
import { useRouter } from 'vue-router'
import DatabaseConnection from '@/components/DatabaseConnection.vue'
import UserManager from '@/components/UserManager.vue'
import { API_CONFIG } from '@/config/api'

// Router
const router = useRouter()

// State
const activeTab = ref('network')

// Network settings state
const networkSettings = ref({
  apiHost: '127.0.0.1',
  apiPort: 7272,
})
const currentMode = ref('localhost')
const corsOrigins = ref([])
const newOrigin = ref('')
const apiKeyInfo = ref(null)
const networkSettingsChanged = ref(false)
const showRegenerateDialog = ref(false)

// Configuration modal state
const showClaudeConfigModal = ref(false)
const showCodexConfigModal = ref(false)
const claudeConfigTab = ref('marketplace')
const codexConfigTab = ref('manual')

// Computed Properties
const modeColor = computed(() => {
  const colors = {
    localhost: 'success',
    lan: 'info',
    wan: 'warning',
  }
  return colors[currentMode.value] || 'grey'
})

const maskedApiKey = computed(() => {
  if (!apiKeyInfo.value || !apiKeyInfo.value.key_preview) {
    return 'No API key configured'
  }
  const preview = apiKeyInfo.value.key_preview
  return `${preview.substring(0, 8)}...${preview.substring(preview.length - 4)}`
})


// Network Settings Methods
async function loadNetworkSettings() {
  try {
    let config
    try {
      // First, try loading from /api/v1/config
      const response = await fetch(`${API_CONFIG.REST_API.baseURL}/api/v1/config`, {
        credentials: 'include',
        timeout: 5000,
      })

      if (!response.ok) {
        throw new Error('Config endpoint failed')
      }

      config = await response.json()
    } catch (configError) {
      console.warn(
        '[SYSTEM SETTINGS] Failed to load config from /api/v1/config, falling back to /api/setup/status',
      )

      // Fallback to /api/setup/status
      const fallbackResponse = await fetch(`${API_CONFIG.REST_API.baseURL}/api/setup/status`, {
        credentials: 'include',
      })

      if (!fallbackResponse.ok) {
        throw fallbackResponse.statusText
      }

      const fallbackConfig = await fallbackResponse.json()

      // Map the fallback response to the expected config structure
      config = {
        installation: { mode: fallbackConfig.network_mode || 'localhost' },
        services: {
          api: {
            host: fallbackConfig.host || '127.0.0.1',
            port: fallbackConfig.port || 7272,
          },
        },
        security: {
          cors: {
            allowed_origins: fallbackConfig.allowed_origins || [],
          },
        },
      }
    }

    // Set mode with robust fallback
    currentMode.value = config.installation?.mode?.toLowerCase() || 'localhost'

    // Set API settings
    networkSettings.value.apiHost = config.services?.api?.host || '127.0.0.1'
    networkSettings.value.apiPort = config.services?.api?.port || 7272

    // Set CORS origins
    corsOrigins.value = config.security?.cors?.allowed_origins || []

    // Load API key info for LAN mode
    if (currentMode.value === 'lan') {
      try {
        const apiKeyResponse = await fetch(`${API_CONFIG.REST_API.baseURL}/api/setup/api-key-info`, {
          credentials: 'include',
        })
        const apiKeyData = await apiKeyResponse.json()

        apiKeyInfo.value = {
          created_at: apiKeyData.created_at || new Date().toISOString(),
          key_preview: apiKeyData.key_preview || 'gk_xxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxx',
        }
      } catch (apiKeyError) {
        console.warn('[SYSTEM SETTINGS] Failed to load API key info', apiKeyError)
        apiKeyInfo.value = null
      }
    }

    console.log('[SYSTEM SETTINGS] Network settings loaded successfully')
  } catch (error) {
    console.error('Completely failed to load network settings:', error)

    // Absolute last resort fallback
    currentMode.value = 'localhost'
    networkSettings.value.apiHost = '127.0.0.1'
    networkSettings.value.apiPort = 7272
    corsOrigins.value = []
  }
}

function isDefaultOrigin(origin) {
  return origin.includes('localhost') || origin.includes('127.0.0.1')
}

function copyOrigin(origin) {
  navigator.clipboard.writeText(origin)
  console.log('[SYSTEM SETTINGS] Origin copied to clipboard:', origin)
}

function copyApiKey() {
  if (apiKeyInfo.value && apiKeyInfo.value.key_preview) {
    navigator.clipboard.writeText(apiKeyInfo.value.key_preview)
    console.log('[SYSTEM SETTINGS] API key copied to clipboard')
  }
}

function addOrigin() {
  if (!newOrigin.value) return

  // Validate origin format
  try {
    new URL(newOrigin.value)
    if (!corsOrigins.value.includes(newOrigin.value)) {
      corsOrigins.value.push(newOrigin.value)
      newOrigin.value = ''
      networkSettingsChanged.value = true
      console.log('[SYSTEM SETTINGS] Origin added successfully')
    }
  } catch (error) {
    console.error('Invalid origin format:', error)
  }
}

function removeOrigin(index) {
  corsOrigins.value.splice(index, 1)
  networkSettingsChanged.value = true
  console.log('[SYSTEM SETTINGS] Origin removed')
}

async function saveNetworkSettings() {
  try {
    // Save CORS origins back to config
    const response = await fetch(`${API_CONFIG.REST_API.baseURL}/api/v1/config`, {
      method: 'PATCH',
      credentials: 'include',
      headers: { 'Content-Type': 'application/json' },
      body: JSON.stringify({
        security: {
          cors: {
            allowed_origins: corsOrigins.value,
          },
        },
      }),
    })

    if (response.ok) {
      networkSettingsChanged.value = false
      console.log('[SYSTEM SETTINGS] Network settings saved successfully')
    }
  } catch (error) {
    console.error('Failed to save network settings:', error)
  }
}

async function regenerateApiKey() {
  try {
    const response = await fetch(`${API_CONFIG.REST_API.baseURL}/api/setup/regenerate-api-key`, {
      method: 'POST',
      credentials: 'include',
    })

    if (response.ok) {
      showRegenerateDialog.value = false
      await loadNetworkSettings() // Reload to get new key
      console.log('[SYSTEM SETTINGS] API key regenerated successfully')
    }
  } catch (error) {
    console.error('Failed to regenerate API key:', error)
  }
}

// Database Methods
async function loadDatabaseSettings() {
  try {
    // Fetch database config from API
    const response = await fetch(`${API_CONFIG.REST_API.baseURL}/api/v1/config/database`, {
      credentials: 'include',
    })
    const config = await response.json()

    console.log('Database settings reloaded from config')
  } catch (error) {
    console.error('Failed to load database settings:', error)
  }
}

function handleDatabaseSuccess(result) {
  console.log('Database connection successful:', result)
}

function handleDatabaseError(error) {
  console.error('Database connection failed:', error)
}

// Setup Wizard Navigation
const navigateToSetupWizard = () => {
  router.push('/setup')
}

// Configuration Modal Methods
const copyClaudeConfig = () => {
  const config = `{
  "servers": {
    "giljo-mcp": {
      "command": "mcp-client",
      "args": [
        "--server-url", "http://your-server-ip:7272",
        "--api-key", "{your-api-key-here}"
      ],
      "description": "GiljoAI Agent Orchestration MCP Server"
    }
  }
}`
  navigator.clipboard.writeText(config)
  console.log('[INTEGRATIONS] Claude configuration copied to clipboard')
}

const copyCodexConfig = () => {
  const config = `[giljo-mcp]
endpoint = "http://your-server-ip:7272"
api_key = "{your-api-key-here}"
description = "GiljoAI Agent Orchestration MCP Server"

[agents]
orchestrator_enabled = true
subagent_coordination = true
context_sharing = true`
  navigator.clipboard.writeText(config)
  console.log('[INTEGRATIONS] Codex configuration copied to clipboard')
}

const downloadClaudeInstructions = () => {
  const instructions = `# Claude Code Setup Guide for GiljoAI MCP Server

## Prerequisites
1. Generate an API key from your user profile in GiljoAI dashboard
2. Ensure Claude Code is installed and configured

## Marketplace Configuration (Recommended)
1. Open Claude Code
2. Navigate to MCP Tools Marketplace
3. Search for "GiljoAI Agent Orchestration MCP Server"
4. Click "Install"
5. Enter endpoint: http://your-server-ip:7272
6. Enter your API key
7. Test connection

## Manual Configuration

**Configuration File Location:**
- macOS/Linux: `~/.claude.json`
- Windows: `%USERPROFILE%\.claude.json`

**Documentation:** https://docs.claude.com/en/docs/claude-code/mcp

Add the following to your Claude Code MCP configuration file:

{
  "servers": {
    "giljo-mcp": {
      "command": "mcp-client",
      "args": [
        "--server-url", "http://your-server-ip:7272",
        "--api-key", "YOUR_API_KEY_HERE"
      ],
      "description": "GiljoAI Agent Orchestration MCP Server"
    }
  }
}

## Verification
- Restart Claude Code
- Verify GiljoAI MCP tools are available
- Test agent coordination functionality

## Support
Visit your GiljoAI dashboard for additional configuration help.`

  const blob = new Blob([instructions], { type: 'text/plain' })
  const url = URL.createObjectURL(blob)
  const a = document.createElement('a')
  a.href = url
  a.download = 'claude-code-giljo-mcp-setup.txt'
  a.click()
  URL.revokeObjectURL(url)
  console.log('[INTEGRATIONS] Claude setup instructions downloaded')
}

const downloadCodexInstructions = () => {
  const instructions = `# Codex CLI Setup Guide for GiljoAI MCP Server

## Prerequisites
1. Generate an API key from your user profile in GiljoAI dashboard
2. Ensure Codex CLI is installed and configured

## Configuration
**Configuration File Location:**
- macOS/Linux: `~/.codex/config.toml`
- Windows: `%USERPROFILE%\.codex\config.toml`

**Documentation:** 
- MCP Integration: https://developers.openai.com/codex/mcp
- CLI Configuration: https://developers.openai.com/codex/local-config#cli

Add to your Codex CLI configuration file:

[giljo-mcp]
endpoint = "http://your-server-ip:7272"
api_key = "YOUR_API_KEY_HERE"
description = "GiljoAI Agent Orchestration MCP Server"

[agents]
orchestrator_enabled = true
subagent_coordination = true
context_sharing = true

## Sub-Agent Workflow
1. Codex spawns specialized sub-agents for different tasks
2. GiljoAI MCP coordinates agent state and memory
3. Context sharing enables seamless handoffs
4. 70% token reduction through intelligent coordination

## Verification
- Restart Codex CLI
- Verify GiljoAI MCP connection
- Test sub-agent coordination

## Support
Visit your GiljoAI dashboard for additional configuration help.`

  const blob = new Blob([instructions], { type: 'text/plain' })
  const url = URL.createObjectURL(blob)
  const a = document.createElement('a')
  a.href = url
  a.download = 'codex-cli-giljo-mcp-setup.txt'
  a.click()
  URL.revokeObjectURL(url)
  console.log('[INTEGRATIONS] Codex setup instructions downloaded')
}

// Lifecycle
onMounted(async () => {
  // Load database settings from config on mount
  await loadDatabaseSettings()

  // Load network settings from config on mount
  await loadNetworkSettings()
})
</script>

<style scoped>
</style>
