# Frontend Implementation - Handover 0094 Detailed Code Guide

**File:** `frontend/src/views/UserSettings.vue`
**Current Location:** Integrations Tab (v-window-item value="integrations")
**Lines to Replace:** 470-551 (SlashCommandSetup section)

---

## STEP 1: API Service Methods

**File:** `F:\GiljoAI_MCP\frontend\src\services\api.js`

**Location:** Add after line ~600 (after templates module)

### Code to Add:

```javascript
  // Downloads for slash commands and agent templates (Handover 0094)
  downloads: {
    slashCommands: () => apiClient.get('/api/download/slash-commands.zip', {
      responseType: 'blob'
    }),
    agentTemplates: (activeOnly = true) => apiClient.get('/api/download/agent-templates.zip', {
      params: { active_only: activeOnly },
      responseType: 'blob'
    }),
    installScript: (scriptType, extension) => apiClient.get(
      `/api/download/install-script.${extension}`,
      {
        params: { type: scriptType },
        responseType: 'blob'
      }
    )
  },
```

**Line Count:** 15 lines (new)

---

## STEP 2: Update UserSettings.vue - Data Properties

**File:** `F:\GiljoAI_MCP\frontend\src/views/UserSettings.vue`

**Location:** In `<script setup>` block, after line ~615 (after existing state definitions)

### Code to Add Before `settings` Object:

```javascript
// Download functionality state (Handover 0094)
const slashCommandInstallPrompt = ref('/setup_slash_commands')
const slashCommandsCopied = ref(false)
const agentImportType = ref('product') // 'product' or 'personal'
const agentsCopied = ref(false)
const downloadingType = ref(null) // Track which download is in progress
let slashCommandsCopyTimeout
let agentsCopyTimeout
```

**Line Count:** 8 lines (new)

---

## STEP 3: Update UserSettings.vue - Methods

**Location:** In `<script setup>` block, add after all existing methods (around line ~780, before lifecycle hooks)

### Code to Add:

```javascript
// Download Methods (Handover 0094)

/**
 * Copy MCP command prompt to clipboard with visual feedback
 * @param {string} type - 'slashCommands' or 'agents'
 */
async function copyPrompt(type) {
  let prompt = ''
  let refName = null

  if (type === 'slashCommands') {
    prompt = slashCommandInstallPrompt.value
    refName = slashCommandsCopied
  } else if (type === 'agents') {
    prompt = getAgentInstallPrompt()
    refName = agentsCopied
  }

  if (!prompt) return

  // Try Clipboard API first (modern browsers)
  if (navigator.clipboard && typeof navigator.clipboard.writeText === 'function') {
    try {
      await navigator.clipboard.writeText(prompt)
      refName.value = true
      console.log('[USER SETTINGS] Copied to clipboard via Clipboard API:', type)

      // Reset copied state after 2 seconds
      const timeout = setTimeout(() => {
        refName.value = false
      }, 2000)

      // Store timeout reference for cleanup
      if (type === 'slashCommands') {
        if (slashCommandsCopyTimeout) clearTimeout(slashCommandsCopyTimeout)
        slashCommandsCopyTimeout = timeout
      } else if (type === 'agents') {
        if (agentsCopyTimeout) clearTimeout(agentsCopyTimeout)
        agentsCopyTimeout = timeout
      }
      return
    } catch (error) {
      console.warn('[USER SETTINGS] Clipboard API failed, trying fallback:', error)
    }
  }

  // Fallback method for older browsers or when Clipboard API fails
  try {
    const textarea = document.createElement('textarea')
    textarea.value = prompt
    textarea.setAttribute('readonly', '')
    textarea.style.position = 'absolute'
    textarea.style.left = '-9999px'
    textarea.style.top = '0'
    document.body.appendChild(textarea)

    // Select and copy
    textarea.focus()
    textarea.select()

    // iOS compatibility
    if (navigator.userAgent.match(/ipad|iphone/i)) {
      const range = document.createRange()
      range.selectNodeContents(textarea)
      const selection = window.getSelection()
      selection.removeAllRanges()
      selection.addRange(range)
      textarea.setSelectionRange(0, prompt.length)
    }

    const success = document.execCommand('copy')
    document.body.removeChild(textarea)

    if (success) {
      refName.value = true
      console.log('[USER SETTINGS] Copied to clipboard via fallback:', type)

      // Reset copied state after 2 seconds
      const timeout = setTimeout(() => {
        refName.value = false
      }, 2000)

      if (type === 'slashCommands') {
        if (slashCommandsCopyTimeout) clearTimeout(slashCommandsCopyTimeout)
        slashCommandsCopyTimeout = timeout
      } else if (type === 'agents') {
        if (agentsCopyTimeout) clearTimeout(agentsCopyTimeout)
        agentsCopyTimeout = timeout
      }
    } else {
      console.error('[USER SETTINGS] Copy command failed')
    }
  } catch (err) {
    console.error('[USER SETTINGS] Fallback copy method failed:', err)
  }
}

/**
 * Download file (ZIP) and trigger browser download
 * @param {string} fileType - 'slash-commands' or 'agent-templates'
 */
async function downloadFile(fileType) {
  downloadingType.value = fileType

  try {
    const response = await api.downloads[
      fileType === 'slash-commands' ? 'slashCommands' : 'agentTemplates'
    ]()

    const blob = response
    const url = window.URL.createObjectURL(blob)
    const link = document.createElement('a')
    link.href = url
    link.download = `${fileType}.zip`
    document.body.appendChild(link)
    link.click()
    document.body.removeChild(link)
    window.URL.revokeObjectURL(url)

    console.log('[USER SETTINGS] Downloaded:', fileType)
  } catch (error) {
    console.error('[USER SETTINGS] Download failed:', fileType, error)
    // TODO: Show snackbar error notification
  } finally {
    downloadingType.value = null
  }
}

/**
 * Download install script (bash or PowerShell)
 * @param {string} scriptType - 'slash-commands' or 'agent-templates'
 * @param {string} extension - 'sh' or 'ps1'
 */
async function downloadInstallScript(scriptType, extension) {
  const downloadKey = `${scriptType}-${extension}`
  downloadingType.value = downloadKey

  try {
    const response = await api.downloads.installScript(scriptType, extension)

    const blob = response
    const url = window.URL.createObjectURL(blob)
    const link = document.createElement('a')
    link.href = url
    link.download = `install.${extension}`
    document.body.appendChild(link)
    link.click()
    document.body.removeChild(link)
    window.URL.revokeObjectURL(url)

    console.log('[USER SETTINGS] Downloaded install script:', downloadKey)
  } catch (error) {
    console.error('[USER SETTINGS] Script download failed:', downloadKey, error)
    // TODO: Show snackbar error notification
  } finally {
    downloadingType.value = null
  }
}

/**
 * Get appropriate MCP install prompt based on agent import type
 * @returns {string} MCP command prompt
 */
function getAgentInstallPrompt() {
  if (agentImportType.value === 'personal') {
    return '/gil_import_personalagents'
  }
  return '/gil_import_productagents'
}
```

**Line Count:** 160 lines (new)

---

## STEP 4: Update UserSettings.vue - Remove Old Import

**Location:** Line ~577

**Remove:**
```javascript
import SlashCommandSetup from '@/components/SlashCommandSetup.vue'
```

---

## STEP 5: Update UserSettings.vue - Replace Template Section

**Location:** Replace lines 470-475 (current SlashCommandSetup section)

**Remove:**
```vue
            <!-- Slash Command Setup -->
            <SlashCommandSetup />
```

**Replace With:**

```vue
            <!-- Slash Command Installation Section (Handover 0094) -->
            <v-card variant="outlined" class="mb-4">
              <v-card-title>Slash Command Installation</v-card-title>
              <v-card-subtitle>Install CLI commands for Claude Code, Codex CLI, and Gemini CLI</v-card-subtitle>

              <v-card-text>
                <!-- MCP Method (Recommended) -->
                <v-alert type="info" variant="tonal" density="compact" class="mb-4" :icon="false">
                  <div class="d-flex align-center">
                    <v-icon start size="small">mdi-lightbulb-on</v-icon>
                    <div class="text-body-2">Recommended: Use MCP method for zero token cost installation</div>
                  </div>
                </v-alert>

                <v-card variant="tonal" color="success" class="mb-4">
                  <v-card-text class="pa-3">
                    <div class="text-subtitle-2 font-weight-medium mb-2">
                      <v-icon start size="small">mdi-lightning-bolt</v-icon>
                      MCP Method (Automated)
                    </div>
                    <div class="text-caption mb-3">Zero token cost - downloads handled automatically</div>

                    <div class="d-flex align-center gap-2 mb-2">
                      <v-text-field
                        :model-value="slashCommandInstallPrompt"
                        readonly
                        variant="outlined"
                        density="compact"
                        hide-details
                        class="command-field"
                      />
                      <v-btn
                        color="white"
                        variant="flat"
                        size="default"
                        @click="copyPrompt('slashCommands')"
                        :prepend-icon="slashCommandsCopied ? 'mdi-check' : 'mdi-content-copy'"
                      >
                        {{ slashCommandsCopied ? 'Copied!' : 'Copy' }}
                      </v-btn>
                    </div>

                    <v-chip size="small" color="white" variant="outlined">
                      <v-icon start size="x-small">mdi-check-circle</v-icon>
                      100% token efficient
                    </v-chip>
                  </v-card-text>
                </v-card>

                <!-- Manual Method (Fallback) -->
                <v-expansion-panels class="mb-0" variant="accordion">
                  <v-expansion-panel>
                    <v-expansion-panel-title>
                      <v-icon start size="small">mdi-download</v-icon>
                      Manual Installation (Fallback)
                    </v-expansion-panel-title>
                    <v-expansion-panel-text>
                      <p class="text-caption mb-3">
                        Download ZIP files and run install scripts for your operating system.
                      </p>

                      <div class="d-flex flex-column gap-2 mb-4">
                        <v-btn
                          variant="outlined"
                          @click="downloadFile('slash-commands')"
                          :loading="downloadingType === 'slash-commands'"
                          prepend-icon="mdi-download"
                        >
                          Download slash-commands.zip
                        </v-btn>

                        <v-btn
                          variant="outlined"
                          @click="downloadInstallScript('slash-commands', 'sh')"
                          :loading="downloadingType === 'slash-commands-sh'"
                          prepend-icon="mdi-bash"
                        >
                          Download install.sh (Unix/macOS)
                        </v-btn>

                        <v-btn
                          variant="outlined"
                          @click="downloadInstallScript('slash-commands', 'ps1')"
                          :loading="downloadingType === 'slash-commands-ps1'"
                          prepend-icon="mdi-powershell"
                        >
                          Download install.ps1 (Windows)
                        </v-btn>
                      </div>

                      <v-alert type="info" variant="tonal" density="compact" class="mb-0">
                        <div class="text-subtitle-2 mb-2">Installation Steps</div>
                        <ol class="text-caption">
                          <li>Download the ZIP file and install script for your OS</li>
                          <li>Run the script: <code>bash install.sh</code> or <code>powershell install.ps1</code></li>
                          <li>Restart your CLI tool to load the commands</li>
                        </ol>
                      </v-alert>
                    </v-expansion-panel-text>
                  </v-expansion-panel>
                </v-expansion-panels>
              </v-card-text>
            </v-card>

            <!-- Agent Template Installation Section (Handover 0094) -->
            <v-card variant="outlined" class="mb-4">
              <v-card-title>Agent Template Installation</v-card-title>
              <v-card-subtitle>Install agent templates for Claude Code development</v-card-subtitle>

              <v-card-text>
                <v-alert type="info" variant="tonal" density="compact" class="mb-4">
                  <v-icon start size="small">mdi-information</v-icon>
                  Claude Code only - Codex and Gemini CLI do not support agent templates yet
                </v-alert>

                <!-- Installation Type Toggle -->
                <div class="mb-4">
                  <div class="text-subtitle-2 mb-2">Installation Location</div>
                  <v-btn-toggle v-model="agentImportType" mandatory color="primary" class="mb-3">
                    <v-btn value="product" variant="flat">
                      <v-icon start>mdi-folder-home</v-icon>
                      Product Agents
                    </v-btn>
                    <v-btn value="personal" variant="flat">
                      <v-icon start>mdi-home</v-icon>
                      Personal Agents
                    </v-btn>
                  </v-btn-toggle>

                  <v-alert type="subtle" variant="tonal" density="compact" class="text-caption">
                    <strong>Product:</strong> Install to current project (.claude/agents/)<br />
                    <strong>Personal:</strong> Install to home directory (~/.claude/agents/)
                  </v-alert>
                </div>

                <!-- MCP Method (Recommended) -->
                <v-card variant="tonal" color="success" class="mb-4">
                  <v-card-text class="pa-3">
                    <div class="text-subtitle-2 font-weight-medium mb-2">
                      <v-icon start size="small">mdi-lightning-bolt</v-icon>
                      MCP Method (Automated)
                    </div>
                    <div class="text-caption mb-3">Recommended for fastest installation</div>

                    <div class="d-flex align-center gap-2 mb-3">
                      <v-text-field
                        :model-value="getAgentInstallPrompt()"
                        readonly
                        variant="outlined"
                        density="compact"
                        hide-details
                        class="command-field"
                      />
                      <v-btn
                        color="white"
                        variant="flat"
                        size="default"
                        @click="copyPrompt('agents')"
                        :prepend-icon="agentsCopied ? 'mdi-check' : 'mdi-content-copy'"
                      >
                        {{ agentsCopied ? 'Copied!' : 'Copy' }}
                      </v-btn>
                    </div>

                    <div class="d-flex gap-2">
                      <v-chip size="small" color="white" variant="outlined">
                        <v-icon start size="x-small">mdi-speedometer</v-icon>
                        ~500 tokens (97% savings)
                      </v-chip>
                      <v-chip size="small" color="white" variant="outlined">
                        <v-icon start size="x-small">mdi-backup-restore</v-icon>
                        Auto-backup enabled
                      </v-chip>
                    </div>
                  </v-card-text>
                </v-card>

                <!-- Manual Method (Fallback) -->
                <v-expansion-panels class="mb-0" variant="accordion">
                  <v-expansion-panel>
                    <v-expansion-panel-title>
                      <v-icon start size="small">mdi-download</v-icon>
                      Manual Installation (Fallback)
                    </v-expansion-panel-title>
                    <v-expansion-panel-text>
                      <p class="text-caption mb-3">
                        Download agent template ZIP and run install scripts manually.
                      </p>

                      <div class="d-flex flex-column gap-2 mb-4">
                        <v-btn
                          variant="outlined"
                          @click="downloadFile('agent-templates')"
                          :loading="downloadingType === 'agent-templates'"
                          prepend-icon="mdi-download"
                        >
                          Download agent-templates.zip
                        </v-btn>

                        <v-btn
                          variant="outlined"
                          @click="downloadInstallScript('agent-templates', 'sh')"
                          :loading="downloadingType === 'agent-templates-sh'"
                          prepend-icon="mdi-bash"
                        >
                          Download install.sh (Unix/macOS)
                        </v-btn>

                        <v-btn
                          variant="outlined"
                          @click="downloadInstallScript('agent-templates', 'ps1')"
                          :loading="downloadingType === 'agent-templates-ps1'"
                          prepend-icon="mdi-powershell"
                        >
                          Download install.ps1 (Windows)
                        </v-btn>
                      </div>

                      <v-alert type="warning" variant="tonal" density="compact" class="mb-3">
                        <v-icon start size="small">mdi-backup-restore</v-icon>
                        <strong>Backup:</strong> Automatic backup created before installation
                      </v-alert>

                      <v-alert type="info" variant="tonal" density="compact" class="mb-0">
                        <div class="text-subtitle-2 mb-2">Installation Steps</div>
                        <ol class="text-caption">
                          <li>Download the ZIP file and install script for your OS</li>
                          <li>Run the script: <code>bash install.sh {{ agentImportType }}</code> or <code>powershell install.ps1 {{ agentImportType }}</code></li>
                          <li>Restart Claude Code to load the templates</li>
                        </ol>
                      </v-alert>
                    </v-expansion-panel-text>
                  </v-expansion-panel>
                </v-expansion-panels>
              </v-card-text>
            </v-card>
```

**Line Count:** 350 lines (replacement)

---

## STEP 6: Add CSS Styling

**Location:** In `<style scoped>` block, add at end (before closing `</style>`)

```css
/* Command field styling (Handover 0094) */
.command-field {
  font-family: 'Courier New', monospace;
  font-size: 0.9rem;
}

.command-field :deep(input) {
  font-family: 'Courier New', monospace;
  color: rgb(var(--v-theme-primary));
  font-weight: 500;
}

/* Utility classes */
.gap-2 {
  gap: 8px;
}

.flex-column {
  flex-direction: column;
}

/* Expansion panel text formatting */
:deep(.v-expansion-panel-text__wrapper) {
  padding: 12px 16px;
}

/* Code styling in instructions */
code {
  background-color: rgba(var(--v-theme-on-surface), 0.05);
  padding: 2px 6px;
  border-radius: 4px;
  font-family: 'Courier New', monospace;
  font-size: 0.875em;
}
```

**Line Count:** 30 lines (new)

---

## Summary of Changes

| Component | File | Lines | Action |
|-----------|------|-------|--------|
| API Service | `api.js` | +15 | Add downloads module |
| Data State | `UserSettings.vue` | +8 | Add download state refs |
| Methods | `UserSettings.vue` | +160 | Add 4 methods for copy/download |
| Template | `UserSettings.vue` | -5 / +350 | Replace SlashCommandSetup |
| Import | `UserSettings.vue` | -1 | Remove SlashCommandSetup import |
| Styling | `UserSettings.vue` | +30 | Add CSS classes |
| **Total** | | **~557** | **New functionality** |

---

## Testing Code Examples

### Test: copyPrompt() Function
```javascript
describe('copyPrompt()', () => {
  it('copies slash command prompt to clipboard', async () => {
    const copyMock = vi.fn().mockResolvedValue(undefined)
    Object.assign(navigator, { clipboard: { writeText: copyMock } })

    await copyPrompt('slashCommands')

    expect(copyMock).toHaveBeenCalledWith('/setup_slash_commands')
    expect(slashCommandsCopied.value).toBe(true)

    // Check it resets after 2 seconds
    vi.useFakeTimers()
    vi.advanceTimersByTime(2000)
    expect(slashCommandsCopied.value).toBe(false)
  })
})
```

### Test: downloadFile() Function
```javascript
describe('downloadFile()', () => {
  it('downloads slash-commands.zip', async () => {
    const blobMock = new Blob(['test'], { type: 'application/zip' })
    vi.spyOn(api.downloads, 'slashCommands').mockResolvedValue(blobMock)

    // Mock document methods
    const createElementMock = vi.spyOn(document, 'createElement')
    const clickMock = vi.fn()

    await downloadFile('slash-commands')

    // Verify blob was downloaded
    expect(api.downloads.slashCommands).toHaveBeenCalled()

    // Verify download was triggered
    const link = createElementMock.mock.results.find(r => r.value.click === clickMock)
    expect(link.value.download).toBe('slash-commands.zip')
  })
})
```

### Test: getAgentInstallPrompt()
```javascript
describe('getAgentInstallPrompt()', () => {
  it('returns product command when agentImportType is product', () => {
    agentImportType.value = 'product'
    expect(getAgentInstallPrompt()).toBe('/gil_import_productagents')
  })

  it('returns personal command when agentImportType is personal', () => {
    agentImportType.value = 'personal'
    expect(getAgentInstallPrompt()).toBe('/gil_import_personalagents')
  })
})
```

---

**Implementation Status:** Ready for development

**Next Phase:** Backend implementation (api/endpoints/downloads.py)
