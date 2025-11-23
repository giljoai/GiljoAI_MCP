<template>
  <v-card>
    <v-card-title>Network Configuration</v-card-title>
    <v-card-subtitle>Server network settings (configured during installation)</v-card-subtitle>

    <v-card-text>
      <!-- Loading State -->
      <div v-if="loading" class="d-flex justify-center py-8">
        <v-progress-circular indeterminate color="primary" />
      </div>

      <template v-else>
        <!-- Unified Architecture Info -->
        <v-alert
          type="info"
          variant="tonal"
          class="mb-4"
          data-test="v3-unified-alert"
          :icon="false"
        >
          <div class="d-flex align-center">
            <v-icon start>mdi-information</v-icon>
            <div>
              <strong>Unified Architecture:</strong> Server binds to all interfaces with
              authentication always enabled. OS firewall controls network access (defense in depth).
            </div>
          </div>
        </v-alert>

        <!-- Server Configuration -->
        <h3 class="text-h6 mb-3">Server Configuration from Installation</h3>

        <v-text-field
          :model-value="config.externalHost"
          label="External Host"
          variant="outlined"
          readonly
          hint="Host/IP configured during installation for external access"
          persistent-hint
          class="mb-4"
          data-test="external-host-field"
        />

        <v-text-field
          :model-value="config.apiPort"
          label="API Port"
          variant="outlined"
          readonly
          hint="Default: 7272"
          persistent-hint
          class="mb-4"
          data-test="api-port-field"
        />

        <v-text-field
          :model-value="config.frontendPort"
          label="Frontend Port"
          variant="outlined"
          readonly
          hint="Default: 7274"
          persistent-hint
          class="mb-4"
          data-test="frontend-port-field"
        />

        <!-- CORS Origins Management -->
        <v-divider class="my-6" />

        <h3 class="text-h6 mb-3 text-medium-emphasis">CORS Allowed Origins</h3>

        <v-alert type="info" variant="tonal" class="mb-4">
          <strong>Foundation implementation exists.</strong> Reserved for future use when frontend
          and backend are hosted on separate domains (e.g., SaaS deployments). Not needed for
          current single-server installations where frontend and backend run together.
        </v-alert>

        <div data-test="cors-origins-section" class="disabled-section">
          <v-list v-if="corsOrigins.length > 0" density="compact" class="mb-4" disabled>
            <v-list-item v-for="(origin, index) in corsOrigins" :key="index" disabled>
              <v-list-item-title class="text-medium-emphasis">{{ origin }}</v-list-item-title>

              <template v-slot:append>
                <v-btn
                  icon="mdi-content-copy"
                  size="small"
                  variant="text"
                  @click="copyOrigin(origin)"
                  title="Copy Origin"
                  disabled
                />
                <v-btn
                  v-if="!isDefaultOrigin(origin)"
                  icon="mdi-delete"
                  size="small"
                  variant="text"
                  color="error"
                  @click="removeOrigin(index)"
                  title="Remove Origin"
                  disabled
                />
              </template>
            </v-list-item>
          </v-list>

          <v-alert v-else type="info" variant="outlined" class="mb-4">
            <span class="text-medium-emphasis"
              >No CORS origins configured. Foundation ready for future SaaS deployments.</span
            >
          </v-alert>

          <v-text-field
            v-model="newOrigin"
            label="Add New Origin"
            variant="outlined"
            placeholder="http://192.168.1.100:7274"
            hint="Disabled for single-server installations"
            persistent-hint
            :append-icon="'mdi-plus'"
            @click:append="addOrigin"
            @keyup.enter="addOrigin"
            disabled
          />
        </div>

        <!-- Network Configuration Info -->
        <v-divider class="my-6" />

        <h3 class="text-h6 mb-3">Configuration Notes</h3>

        <v-alert type="info" variant="tonal" class="mb-0">
          <div class="mb-2">
            <strong>Network settings are configured during installation.</strong>
          </div>
          <div class="text-body-2">
            To modify the external host or ports, update <code>config.yaml</code> and restart the
            server. Authentication is always enabled for all connections (local and remote). Use OS
            firewall to control network access.
          </div>
        </v-alert>
      </template>
    </v-card-text>

    <v-card-actions>
      <v-spacer />
      <v-btn variant="text" @click="handleRefresh" data-test="reload-button">
        <v-icon start>mdi-refresh</v-icon>
        Reload
      </v-btn>
      <v-btn color="primary" disabled data-test="save-button"> Save Changes </v-btn>
    </v-card-actions>
  </v-card>
</template>

<script setup>
import { ref } from 'vue'

const props = defineProps({
  config: {
    type: Object,
    required: true,
    default: () => ({
      externalHost: 'localhost',
      apiPort: 7272,
      frontendPort: 7274,
    }),
  },
  corsOrigins: {
    type: Array,
    default: () => [],
  },
  loading: {
    type: Boolean,
    default: false,
  },
})

const emit = defineEmits(['refresh', 'save'])

// Local state for CORS management (disabled for now)
const newOrigin = ref('')

// Methods
function handleRefresh() {
  emit('refresh')
}

function isDefaultOrigin(origin) {
  return origin.includes('localhost') || origin.includes('127.0.0.1')
}

function copyOrigin(origin) {
  navigator.clipboard.writeText(origin)
  console.log('[NETWORK SETTINGS] Origin copied to clipboard:', origin)
}

function addOrigin() {
  if (!newOrigin.value) return

  // Validate origin format
  try {
    new URL(newOrigin.value)
    // Would emit save event with updated origins
    // For now this is disabled
    newOrigin.value = ''
    console.log('[NETWORK SETTINGS] Origin add attempted (disabled)')
  } catch (error) {
    console.error('Invalid origin format:', error)
  }
}

function removeOrigin(index) {
  // Would emit save event with updated origins
  // For now this is disabled
  console.log('[NETWORK SETTINGS] Origin remove attempted at index:', index, '(disabled)')
}
</script>
