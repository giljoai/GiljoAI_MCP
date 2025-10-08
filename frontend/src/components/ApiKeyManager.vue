<template>
  <v-card>
    <v-card-title class="d-flex align-center">
      <v-icon class="mr-2">mdi-key-variant</v-icon>
      API Keys
      <v-spacer />
      <v-btn color="primary" @click="showGenerateDialog = true" :disabled="loading">
        <v-icon start>mdi-plus</v-icon>
        Generate New Key
      </v-btn>
    </v-card-title>

    <v-card-subtitle class="mt-2">
      Manage API keys for programmatic access to GiljoAI MCP
    </v-card-subtitle>

    <v-divider class="mt-4" />

    <v-card-text>
      <!-- Empty State -->
      <v-alert v-if="!loading && apiKeys.length === 0" type="info" variant="tonal" class="mb-4">
        <div class="d-flex align-center">
          <v-icon start>mdi-information</v-icon>
          <div>
            No API keys created yet. Generate a new key to enable programmatic access to the API.
          </div>
        </div>
      </v-alert>

      <!-- API Keys Table -->
      <v-data-table
        v-if="apiKeys.length > 0"
        :items="apiKeys"
        :headers="headers"
        :loading="loading"
        class="elevation-1"
      >
        <!-- Name Column -->
        <template #item.name="{ item }">
          <div class="d-flex align-center">
            <v-icon size="small" class="mr-2">mdi-label</v-icon>
            <span class="font-weight-medium">{{ item.name }}</span>
          </div>
        </template>

        <!-- Key Preview Column -->
        <template #item.key_prefix="{ item }">
          <code class="text-caption">{{ item.key_prefix }}...</code>
        </template>

        <!-- Created Date Column -->
        <template #item.created_at="{ item }">
          <span class="text-caption">{{ formatDate(item.created_at) }}</span>
        </template>

        <!-- Actions Column -->
        <template #item.actions="{ item }">
          <v-tooltip text="Revoke this API key">
            <template v-slot:activator="{ props }">
              <v-btn
                icon="mdi-delete"
                size="small"
                variant="text"
                color="error"
                v-bind="props"
                @click="confirmRevoke(item)"
              />
            </template>
          </v-tooltip>
        </template>
      </v-data-table>
    </v-card-text>

    <!-- Generate Key Dialog -->
    <v-dialog v-model="showGenerateDialog" max-width="500" persistent>
      <v-card>
        <v-card-title>
          <v-icon class="mr-2">mdi-key-plus</v-icon>
          Generate New API Key
        </v-card-title>

        <v-card-text>
          <v-form ref="generateForm" @submit.prevent="generateKey">
            <v-text-field
              v-model="newKeyName"
              label="Key Name"
              hint="A descriptive name for this API key (e.g., 'Production Server', 'Dev Environment')"
              persistent-hint
              variant="outlined"
              :rules="[rules.required]"
              autofocus
              class="mt-4"
            />
          </v-form>
        </v-card-text>

        <v-card-actions>
          <v-spacer />
          <v-btn variant="text" @click="cancelGenerate" :disabled="generating">Cancel</v-btn>
          <v-btn color="primary" @click="generateKey" :loading="generating" :disabled="!newKeyName">
            Generate
          </v-btn>
        </v-card-actions>
      </v-card>
    </v-dialog>

    <!-- Show New Key Dialog (ONCE) -->
    <v-dialog v-model="showNewKeyDialog" max-width="700" persistent>
      <v-card>
        <v-card-title class="bg-warning">
          <v-icon class="mr-2">mdi-alert</v-icon>
          Save Your API Key
        </v-card-title>

        <v-card-text class="pt-6">
          <v-alert type="warning" variant="tonal" prominent class="mb-4">
            <v-alert-title class="text-h6 mb-2">
              <v-icon start>mdi-shield-alert</v-icon>
              Important: Copy this key now!
            </v-alert-title>
            This API key will only be shown ONCE. After you close this dialog, you will not be able
            to retrieve it again. If you lose it, you'll need to generate a new key.
          </v-alert>

          <v-text-field
            :model-value="newApiKey"
            label="Your New API Key"
            variant="outlined"
            readonly
            class="mt-4 mb-2"
          >
            <template #append-inner>
              <v-tooltip text="Copy to clipboard">
                <template v-slot:activator="{ props }">
                  <v-btn
                    icon="mdi-content-copy"
                    size="small"
                    variant="text"
                    color="primary"
                    v-bind="props"
                    @click="copyToClipboard"
                  />
                </template>
              </v-tooltip>
            </template>
          </v-text-field>

          <v-alert v-if="copied" type="success" variant="tonal" density="compact" class="mb-4">
            <v-icon start size="small">mdi-check-circle</v-icon>
            API key copied to clipboard!
          </v-alert>

          <v-divider class="my-4" />

          <h3 class="text-subtitle-1 mb-2">How to use this API key:</h3>
          <v-code class="d-block pa-3 bg-surface-variant rounded">
            # HTTP Header<br />
            X-API-Key: {{ newApiKey }}
          </v-code>
        </v-card-text>

        <v-card-actions class="pa-4">
          <v-checkbox
            v-model="confirmSaved"
            label="I have copied and saved this key securely"
            color="primary"
            density="compact"
          />
          <v-spacer />
          <v-btn
            color="primary"
            variant="flat"
            @click="closeNewKeyDialog"
            :disabled="!confirmSaved"
          >
            I've Saved It
          </v-btn>
        </v-card-actions>
      </v-card>
    </v-dialog>

    <!-- Revoke Confirmation Dialog -->
    <v-dialog v-model="showRevokeDialog" max-width="500">
      <v-card>
        <v-card-title class="bg-error">
          <v-icon class="mr-2">mdi-alert-circle</v-icon>
          Revoke API Key?
        </v-card-title>

        <v-card-text class="pt-6">
          <p class="text-body-1 mb-4">
            Are you sure you want to revoke the API key <strong>{{ keyToRevoke?.name }}</strong
            >?
          </p>

          <v-alert type="warning" variant="tonal" density="compact">
            This action cannot be undone. Any applications using this key will immediately lose
            access to the API.
          </v-alert>
        </v-card-text>

        <v-card-actions>
          <v-spacer />
          <v-btn variant="text" @click="showRevokeDialog = false" :disabled="revoking">
            Cancel
          </v-btn>
          <v-btn color="error" @click="revokeKey" :loading="revoking"> Revoke Key </v-btn>
        </v-card-actions>
      </v-card>
    </v-dialog>
  </v-card>
</template>

<script setup>
import { ref, onMounted } from 'vue'
import api from '@/services/api'

// State
const apiKeys = ref([])
const loading = ref(false)
const showGenerateDialog = ref(false)
const showNewKeyDialog = ref(false)
const showRevokeDialog = ref(false)
const newKeyName = ref('')
const newApiKey = ref('')
const generating = ref(false)
const revoking = ref(false)
const copied = ref(false)
const confirmSaved = ref(false)
const keyToRevoke = ref(null)
const generateForm = ref(null)

// Table headers
const headers = [
  { title: 'Name', key: 'name', sortable: true },
  { title: 'Key Prefix', key: 'key_prefix', sortable: false },
  { title: 'Created', key: 'created_at', sortable: true },
  { title: 'Actions', key: 'actions', sortable: false, align: 'end' },
]

// Validation rules
const rules = {
  required: (value) => !!value || 'This field is required',
}

// Methods
async function loadKeys() {
  loading.value = true
  try {
    const response = await api.apiKeys.list()
    apiKeys.value = response.data
    console.log('[API Keys] Loaded', apiKeys.value.length, 'keys')
  } catch (err) {
    console.error('[API Keys] Failed to load:', err)
    // Don't show error if it's just a 401 (not authenticated)
    if (err.response?.status !== 401) {
      // Could show a toast notification here
    }
  } finally {
    loading.value = false
  }
}

async function generateKey() {
  // Validate form
  const { valid } = await generateForm.value.validate()
  if (!valid) {
    return
  }

  generating.value = true
  try {
    const response = await api.apiKeys.create(newKeyName.value)
    newApiKey.value = response.data.api_key
    console.log('[API Keys] Generated new key:', newKeyName.value)

    // Close generate dialog and show new key dialog
    showGenerateDialog.value = false
    showNewKeyDialog.value = true

    // Reload keys list
    await loadKeys()
  } catch (err) {
    console.error('[API Keys] Failed to generate:', err)
    // Could show error toast here
  } finally {
    generating.value = false
  }
}

function cancelGenerate() {
  showGenerateDialog.value = false
  newKeyName.value = ''
}

function closeNewKeyDialog() {
  showNewKeyDialog.value = false
  newApiKey.value = ''
  newKeyName.value = ''
  confirmSaved.value = false
  copied.value = false
}

function confirmRevoke(key) {
  keyToRevoke.value = key
  showRevokeDialog.value = true
}

async function revokeKey() {
  if (!keyToRevoke.value) return

  revoking.value = true
  try {
    await api.apiKeys.delete(keyToRevoke.value.id)
    console.log('[API Keys] Revoked key:', keyToRevoke.value.name)

    // Reload keys list
    await loadKeys()

    // Close dialog
    showRevokeDialog.value = false
    keyToRevoke.value = null
  } catch (err) {
    console.error('[API Keys] Failed to revoke:', err)
    // Could show error toast here
  } finally {
    revoking.value = false
  }
}

async function copyToClipboard() {
  try {
    await navigator.clipboard.writeText(newApiKey.value)
    copied.value = true
    console.log('[API Keys] Copied to clipboard')

    // Reset copied state after 3 seconds
    setTimeout(() => {
      copied.value = false
    }, 3000)
  } catch (err) {
    console.error('[API Keys] Failed to copy:', err)
  }
}

function formatDate(dateString) {
  if (!dateString) return 'N/A'
  const date = new Date(dateString)
  return date.toLocaleDateString() + ' ' + date.toLocaleTimeString()
}

// Lifecycle
onMounted(() => {
  loadKeys()
})
</script>

<style scoped>
.v-data-table {
  border-radius: 8px;
}

code {
  background-color: rgba(var(--v-theme-surface-variant), 0.5);
  padding: 2px 6px;
  border-radius: 4px;
  font-family: 'Courier New', monospace;
}

.v-code {
  font-family: 'Courier New', monospace;
  font-size: 0.875rem;
  line-height: 1.5;
}

/* Accessibility: Focus indicators */
.v-btn:focus-visible {
  outline: 2px solid rgba(var(--v-theme-primary), 0.5);
  outline-offset: 2px;
}
</style>
