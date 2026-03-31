<template>
  <v-container>
    <!-- Page Header -->
    <div class="d-flex justify-space-between align-center mb-6">
      <div>
        <h1 class="text-h4 mb-2">MCP Tool Integration</h1>
        <p class="text-subtitle-1">
          Download installer scripts or generate share links for your team
        </p>
      </div>
    </div>

    <!-- Section 1: Download Installer Scripts -->
    <v-card class="mb-6">
      <v-card-title>
        <v-icon class="mr-2">mdi-download</v-icon>
        Download Installer Scripts
      </v-card-title>

      <v-card-text>
        <p class="text-body-1 mb-4">
          Download a pre-configured installer script that automatically sets up GiljoAI MCP
          integration in supported AI coding agents (Claude Code, Codex CLI, Gemini CLI, etc.). The script
          includes your API credentials and server connection details.
        </p>

        <!-- Download Buttons -->
        <div class="d-flex gap-4 mb-6">
          <v-btn
            color="primary"
            size="large"
            :loading="downloading.windows"
            prepend-icon="mdi-microsoft-windows"
            @click="downloadScript('windows')"
          >
            Download for Windows
          </v-btn>

          <v-btn
            color="primary"
            size="large"
            variant="outlined"
            :loading="downloading.unix"
            prepend-icon="mdi-apple"
            @click="downloadScript('unix')"
          >
            Download for macOS/Linux
          </v-btn>
        </div>

        <!-- Instructions -->
        <v-alert type="info" variant="tonal" class="mb-4">
          <div>
            <strong>Next steps after download:</strong>
            <ol class="mt-2 ml-4">
              <li>Run the downloaded script in your terminal</li>
              <li>The script will automatically configure your MCP tools</li>
              <li>Restart your AI coding agent (Claude Code, Codex CLI, etc.)</li>
              <li>GiljoAI MCP commands will be available immediately</li>
            </ol>
          </div>
        </v-alert>

        <!-- Success Message -->
        <v-alert
          v-if="downloadSuccess"
          type="success"
          variant="tonal"
          closable
          @click:close="downloadSuccess = false"
        >
          Script downloaded successfully! Follow the instructions above to complete installation.
        </v-alert>
      </v-card-text>
    </v-card>

    <!-- Section 2: Share with Team Members -->
    <v-card class="mb-6">
      <v-card-title>
        <v-icon class="mr-2">mdi-share-variant</v-icon>
        Share with Team Members
      </v-card-title>

      <v-card-text>
        <p class="text-body-1 mb-4">
          Generate secure, temporary download links to share with your team. Links expire after 7
          days and include embedded credentials for easy setup.
        </p>

        <!-- Generate Button -->
        <v-btn
          v-if="!shareLinks"
          color="primary"
          size="large"
          :loading="generatingLinks"
          prepend-icon="mdi-link-variant-plus"
          @click="generateShareLinks"
        >
          Generate Share Links
        </v-btn>

        <!-- Share Links Display -->
        <div v-if="shareLinks">
          <v-alert type="success" variant="tonal" class="mb-4">
            <div>
              <strong>Share links generated successfully!</strong>
              <div class="text-caption mt-1">
                Expires: {{ formatExpiryDate(shareLinks.expires_at) }}
              </div>
            </div>
          </v-alert>

          <!-- Windows Link -->
          <v-text-field
            :model-value="shareLinks.windows_url"
            label="Windows Download Link"
            variant="outlined"
            readonly
            class="mb-4"
            hide-details
          >
            <template v-slot:append>
              <v-btn
                icon="mdi-content-copy"
                size="small"
                variant="text"
                title="Copy Windows link"
                @click="copyToClipboard(shareLinks.windows_url, 'Windows link')"
              />
            </template>
          </v-text-field>

          <!-- Unix Link -->
          <v-text-field
            :model-value="shareLinks.unix_url"
            label="macOS/Linux Download Link"
            variant="outlined"
            readonly
            class="mb-4"
            hide-details
          >
            <template v-slot:append>
              <v-btn
                icon="mdi-content-copy"
                size="small"
                variant="text"
                title="Copy Unix link"
                @click="copyToClipboard(shareLinks.unix_url, 'Unix link')"
              />
            </template>
          </v-text-field>

          <!-- Email Template -->
          <v-expansion-panels class="mt-4">
            <v-expansion-panel>
              <v-expansion-panel-title>
                <v-icon class="mr-2">mdi-email-outline</v-icon>
                View Email Template
              </v-expansion-panel-title>
              <v-expansion-panel-text>
                <v-card variant="flat" class="smooth-border pa-4 bg-grey-lighten-4">
                  <pre class="email-template">
Subject: GiljoAI MCP Setup Instructions

Hi team,

I've set up GiljoAI MCP for our project. Here are the download links to get started:

Windows: {{ shareLinks.windows_url }}

macOS/Linux: {{ shareLinks.unix_url }}

Installation is simple:
1. Download the appropriate script for your OS
2. Run it in your terminal
3. Restart your AI coding agent
4. You're ready to use GiljoAI MCP commands!

These links expire on {{ formatExpiryDate(shareLinks.expires_at) }}.

Questions? Let me know!
</pre
                  >
                  <v-btn
                    variant="outlined"
                    class="mt-2"
                    prepend-icon="mdi-content-copy"
                    @click="copyEmailTemplate"
                  >
                    Copy Email Template
                  </v-btn>
                </v-card>
              </v-expansion-panel-text>
            </v-expansion-panel>
          </v-expansion-panels>

          <!-- Regenerate Button -->
          <v-btn variant="text" class="mt-4" prepend-icon="mdi-refresh" @click="resetShareLinks">
            Generate New Links
          </v-btn>
        </div>
      </v-card-text>
    </v-card>

    <!-- Section 3: Manual Configuration -->
    <v-card class="mb-6">
      <v-card-title>
        <v-icon class="mr-2">mdi-cog</v-icon>
        Manual Configuration
      </v-card-title>

      <v-card-text>
        <v-expansion-panels>
          <v-expansion-panel>
            <v-expansion-panel-title>
              <div>
                <div class="text-h6">Advanced: Manual MCP Configuration</div>
                <div class="text-caption text-grey">
                  For users who prefer to configure their tools manually
                </div>
              </div>
            </v-expansion-panel-title>
            <v-expansion-panel-text>
              <p class="text-body-2 mb-4">
                If you prefer to manually configure your MCP tools, add the following JSON to your
                tool's configuration file:
              </p>

              <!-- JSON Config Display -->
              <v-card variant="flat" class="smooth-border mb-4">
                <v-card-text>
                  <div class="d-flex justify-space-between align-center mb-2">
                    <span class="text-caption text-grey">JSON Configuration</span>
                    <v-btn
                      size="small"
                      variant="text"
                      prepend-icon="mdi-content-copy"
                      @click="copyManualConfig"
                    >
                      Copy Config
                    </v-btn>
                  </div>
                  <pre class="config-block"><code>{{ manualConfigJson }}</code></pre>
                </v-card-text>
              </v-card>

              <!-- Config File Locations -->
              <v-alert type="info" variant="tonal">
                <div>
                  <strong>Configuration file locations:</strong>
                  <ul class="mt-2 ml-4">
                    <li><strong>Claude Code:</strong> <code>~/.claude.json</code></li>
                    <li><strong>Windsurf:</strong> <code>~/.windsurf/mcp.json</code></li>
                    <li>
                      <strong>VSCode (Continue):</strong> <code>~/.continue/config.json</code>
                    </li>
                  </ul>
                </div>
              </v-alert>
            </v-expansion-panel-text>
          </v-expansion-panel>
        </v-expansion-panels>
      </v-card-text>
    </v-card>

    <!-- Section 4: Troubleshooting -->
    <v-card>
      <v-card-title>
        <v-icon class="mr-2">mdi-help-circle</v-icon>
        Troubleshooting
      </v-card-title>

      <v-card-text>
        <v-expansion-panels>
          <!-- Permission Denied -->
          <v-expansion-panel>
            <v-expansion-panel-title>
              <v-icon class="mr-2" color="warning">mdi-alert</v-icon>
              Permission denied when running the script
            </v-expansion-panel-title>
            <v-expansion-panel-text>
              <p class="mb-2"><strong>Windows:</strong></p>
              <v-card variant="flat" class="smooth-border mb-3 pa-3">
                <code>Right-click the .bat file > Run as administrator</code>
              </v-card>

              <p class="mb-2"><strong>macOS/Linux:</strong></p>
              <v-card variant="flat" class="smooth-border pa-3">
                <code>chmod +x giljo-mcp-setup.sh && ./giljo-mcp-setup.sh</code>
              </v-card>
            </v-expansion-panel-text>
          </v-expansion-panel>

          <!-- Tool Not Detected -->
          <v-expansion-panel>
            <v-expansion-panel-title>
              <v-icon class="mr-2" color="warning">mdi-alert</v-icon>
              Script says "Tool not detected"
            </v-expansion-panel-title>
            <v-expansion-panel-text>
              <p class="mb-3">
                The installer looks for common MCP tool configuration files. If your tool is
                installed in a non-standard location:
              </p>
              <ol class="ml-4">
                <li>Use the Manual Configuration section above</li>
                <li>Find your tool's config file manually</li>
                <li>Copy the JSON configuration provided</li>
                <li>Add it to your tool's MCP server section</li>
              </ol>
            </v-expansion-panel-text>
          </v-expansion-panel>

          <!-- Python Not Found -->
          <v-expansion-panel>
            <v-expansion-panel-title>
              <v-icon class="mr-2" color="warning">mdi-alert</v-icon>
              Python not found
            </v-expansion-panel-title>
            <v-expansion-panel-text>
              <p class="mb-3">GiljoAI MCP requires Python 3.8 or higher. Install Python from:</p>
              <v-list density="compact">
                <v-list-item>
                  <v-list-item-title>
                    <strong>Windows:</strong>
                    <a href="https://www.python.org/downloads/" target="_blank" class="ml-2">
                      python.org/downloads
                    </a>
                  </v-list-item-title>
                </v-list-item>
                <v-list-item>
                  <v-list-item-title>
                    <strong>macOS:</strong>
                    <code class="ml-2">brew install python3</code>
                  </v-list-item-title>
                </v-list-item>
                <v-list-item>
                  <v-list-item-title>
                    <strong>Linux:</strong>
                    <code class="ml-2">sudo apt install python3</code>
                  </v-list-item-title>
                </v-list-item>
              </v-list>
            </v-expansion-panel-text>
          </v-expansion-panel>

          <!-- Configuration Not Working -->
          <v-expansion-panel>
            <v-expansion-panel-title>
              <v-icon class="mr-2" color="warning">mdi-alert</v-icon>
              Configuration applied but commands not working
            </v-expansion-panel-title>
            <v-expansion-panel-text>
              <p class="mb-3">Try these steps:</p>
              <ol class="ml-4 mb-3">
                <li>Completely restart your AI coding agent (not just reload window)</li>
                <li>Verify the API server is running (check System Settings)</li>
                <li>Check network connectivity to the API endpoint</li>
                <li>Verify your API key is correct (if in LAN mode)</li>
                <li>Check tool logs for connection errors</li>
              </ol>

              <v-alert type="info" variant="tonal">
                <v-icon start>mdi-information</v-icon>
                Still having issues? Contact your system administrator or check the GiljoAI MCP
                documentation for detailed troubleshooting steps.
              </v-alert>
            </v-expansion-panel-text>
          </v-expansion-panel>
        </v-expansion-panels>
      </v-card-text>
    </v-card>

  </v-container>
</template>

<script setup>
import { ref, computed } from 'vue'
import { format } from 'date-fns'
import { getApiBaseURL, getDefaultTenantKey } from '@/config/api'
import { useClipboard } from '@/composables/useClipboard'
import { useToast } from '@/composables/useToast'

const { copy: clipboardCopy } = useClipboard()
const { showToast } = useToast()

// State
const downloading = ref({
  windows: false,
  unix: false,
})
const downloadSuccess = ref(false)
const generatingLinks = ref(false)
const shareLinks = ref(null)

// Computed Properties
const manualConfigJson = computed(() => {
  return JSON.stringify(
    {
      'giljo_mcp': {
        command: 'python',
        args: ['-m', 'giljo_mcp'],
        env: {
          GILJO_SERVER_URL: getApiBaseURL(),
          GILJO_API_KEY: '<your-api-key-here>',
        },
      },
    },
    null,
    2,
  )
})

// Methods
async function downloadScript(platform) {
  downloading.value[platform] = true
  downloadSuccess.value = false

  try {
    const endpoint =
      platform === 'windows' ? '/api/mcp-installer/windows' : '/api/mcp-installer/unix'

    const response = await fetch(`${getApiBaseURL()}${endpoint}`, {
      method: 'GET',
      headers: {
        Authorization: `Bearer ${localStorage.getItem('auth_token')}`,
        'X-Tenant-Key': getDefaultTenantKey(),
      },
    })

    if (!response.ok) {
      throw new Error(`Download failed: ${response.statusText}`)
    }

    // Get filename from Content-Disposition header or use default
    const contentDisposition = response.headers.get('Content-Disposition')
    let filename = platform === 'windows' ? 'giljo-mcp-setup.bat' : 'giljo-mcp-setup.sh'

    if (contentDisposition) {
      const filenameMatch = contentDisposition.match(/filename="?(.+)"?/)
      if (filenameMatch) {
        filename = filenameMatch[1]
      }
    }

    // Create blob and trigger download
    const blob = await response.blob()
    const url = window.URL.createObjectURL(blob)
    const a = document.createElement('a')
    a.href = url
    a.download = filename
    a.style.display = 'none'
    document.body.appendChild(a)
    a.click()

    // Cleanup
    window.URL.revokeObjectURL(url)
    document.body.removeChild(a)

    downloadSuccess.value = true
    showSnackbar('Script downloaded successfully!', 'success')
  } catch (error) {
    console.error('[MCP Integration] Download failed:', error)
    showSnackbar('Download failed. Please try again.', 'error')
  } finally {
    downloading.value[platform] = false
  }
}

async function generateShareLinks() {
  generatingLinks.value = true

  try {
    const response = await fetch(`${getApiBaseURL()}/api/mcp-installer/share-link`, {
      method: 'POST',
      headers: {
        'Content-Type': 'application/json',
        Authorization: `Bearer ${localStorage.getItem('auth_token')}`,
        'X-Tenant-Key': getDefaultTenantKey(),
      },
    })

    if (!response.ok) {
      throw new Error(`Failed to generate links: ${response.statusText}`)
    }

    const data = await response.json()
    shareLinks.value = data

    showSnackbar('Share links generated successfully!', 'success')
  } catch (error) {
    console.error('[MCP Integration] Failed to generate share links:', error)
    showSnackbar('Failed to generate links. Please try again.', 'error')
  } finally {
    generatingLinks.value = false
  }
}

function resetShareLinks() {
  shareLinks.value = null
}

async function copyToClipboard(text, label) {
  const success = await clipboardCopy(text)
  if (success) {
    showSnackbar(`${label} copied to clipboard!`, 'success')
  } else {
    showSnackbar('Failed to copy to clipboard', 'error')
  }
}

function copyManualConfig() {
  copyToClipboard(manualConfigJson.value, 'Configuration')
}

function copyEmailTemplate() {
  const template = `Subject: GiljoAI MCP Setup Instructions

Hi team,

I've set up GiljoAI MCP for our project. Here are the download links to get started:

Windows: ${shareLinks.value.windows_url}

macOS/Linux: ${shareLinks.value.unix_url}

Installation is simple:
1. Download the appropriate script for your OS
2. Run it in your terminal
3. Restart your AI coding agent
4. You're ready to use GiljoAI MCP commands!

These links expire on ${formatExpiryDate(shareLinks.value.expires_at)}.

Questions? Let me know!`

  copyToClipboard(template, 'Email template')
}

function formatExpiryDate(dateString) {
  try {
    return format(new Date(dateString), "MMMM d, yyyy 'at' h:mm a")
  } catch {
    return dateString
  }
}

function showSnackbar(message, type = 'success') {
  showToast({ message, type })
}
</script>

<style scoped>
/* Professional code block styling */
.config-block {
  background-color: rgb(var(--v-theme-surface-variant));
  padding: 16px;
  border-radius: 8px;
  overflow-x: auto;
  font-family: 'Courier New', monospace;
  font-size: 0.875rem;
  line-height: 1.5;
  margin: 0;
}

.email-template {
  font-family: 'Courier New', monospace;
  font-size: 0.875rem;
  line-height: 1.6;
  white-space: pre-wrap;
  word-wrap: break-word;
  margin: 0;
}

/* Accessibility: Focus indicators */
.v-btn:focus-visible {
  outline: 2px solid rgb(var(--v-theme-primary));
  outline-offset: 2px;
}

.v-text-field:focus-within {
  outline: 2px solid rgb(var(--v-theme-primary));
  outline-offset: 2px;
}

/* Responsive spacing */
.gap-4 {
  gap: 1rem;
}

@media (max-width: 600px) {
  .d-flex.gap-4 {
    flex-direction: column;
  }

  .v-btn {
    width: 100%;
  }
}

/* High contrast mode support */
@media (prefers-contrast: high) {
  .config-block {
    border: 2px solid currentColor;
  }
}
</style>
