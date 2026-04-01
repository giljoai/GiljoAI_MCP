<template>
  <v-card variant="flat" class="smooth-border security-card">
    <v-card-title>Security Settings</v-card-title>
    <v-card-subtitle class="security-subtitle">Manage authentication and cross-origin security</v-card-subtitle>

    <v-card-text>
      <!-- Loading Indicator -->
      <v-progress-linear
        v-if="loading"
        data-test="loading-indicator"
        indeterminate
        color="primary"
        class="mb-4"
      />

      <!-- Cookie Domain Whitelist Section -->
      <h3 class="text-h6 mb-3">Cookie Domain Whitelist</h3>

      <p class="text-body-2 mb-3">
        Configure which domain names are allowed for cross-port authentication cookies. This enables
        secure authentication when accessing the dashboard from different ports or subdomains on the
        same machine.
      </p>

      <v-alert type="info" variant="tonal" class="mb-4" :icon="false">
        <v-icon start>mdi-information</v-icon>
        IP addresses are automatically allowed. Only add domain names here (e.g., app.example.com,
        localhost).
      </v-alert>

      <!-- Domain List -->
      <div v-if="cookieDomains.length > 0" class="mb-4">
        <v-list density="compact" class="mb-3">
          <v-list-item v-for="domain in cookieDomains" :key="domain" :title="domain">
            <template v-slot:append>
              <v-btn
                icon="mdi-delete"
                size="small"
                variant="text"
                color="error"
                data-test="delete-domain-btn"
                :disabled="loading"
                :aria-label="`Delete domain ${domain}`"
                @click="removeDomain(domain)"
              />
            </template>
          </v-list-item>
        </v-list>
      </div>

      <!-- Empty State -->
      <v-alert v-else type="info" variant="outlined" class="mb-4">
        No domain names configured. IP-based access only.
      </v-alert>

      <!-- Add Domain Form -->
      <v-text-field
        v-model="newDomain"
        data-test="new-domain-input"
        label="Add Domain Name"
        variant="outlined"
        placeholder="app.example.com"
        hint="Enter a domain name (no IP addresses)"
        persistent-hint
        :rules="[validateDomain]"
        :error-messages="domainError"
        :disabled="loading"
        class="mb-2"
        @keyup.enter="addDomain"
      >
        <template v-slot:append>
          <v-btn
            icon="mdi-plus"
            color="primary"
            variant="text"
            data-test="add-domain-btn"
            :disabled="!newDomain || !!domainError || loading"
            aria-label="Add domain"
            @click="addDomain"
          />
        </template>
      </v-text-field>

      <!-- Success/Error Feedback -->
      <v-alert
        v-if="feedback"
        :type="feedback.type"
        variant="tonal"
        class="mb-4"
        closable
        data-test="feedback-alert"
        @click:close="clearFeedback"
      >
        {{ feedback.message }}
      </v-alert>
    </v-card-text>

    <v-card-actions>
      <v-spacer />
      <v-btn variant="text" data-test="reload-btn" :disabled="loading" @click="reload">
        <v-icon start>mdi-refresh</v-icon>
        Reload
      </v-btn>
    </v-card-actions>
  </v-card>
</template>

<script setup>
import { ref, watch } from 'vue'

const props = defineProps({
  cookieDomains: {
    type: Array,
    default: () => [],
  },
  loading: {
    type: Boolean,
    default: false,
  },
  feedback: {
    type: Object,
    default: null,
  },
})

const emit = defineEmits(['add-domain', 'remove-domain', 'reload', 'clear-feedback'])

// Local state
const newDomain = ref('')
const domainError = ref('')

// Validation function
function validateDomain(value) {
  if (!value) {
    domainError.value = ''
    return true
  }

  const trimmed = value.trim()

  // Check for IP address pattern (reject IPs)
  const ipPattern = /^(\d{1,3}\.){3}\d{1,3}$/
  if (ipPattern.test(trimmed)) {
    domainError.value = 'IP addresses are not allowed. Use domain names only.'
    return false
  }

  // Validate domain format
  const domainPattern =
    /^[a-zA-Z0-9]([a-zA-Z0-9-]{0,61}[a-zA-Z0-9])?(\.[a-zA-Z0-9]([a-zA-Z0-9-]{0,61}[a-zA-Z0-9])?)*$/
  if (!domainPattern.test(trimmed)) {
    domainError.value = 'Invalid domain format. Example: app.example.com'
    return false
  }

  domainError.value = ''
  return true
}

// Watch for input changes to validate
watch(newDomain, (value) => {
  validateDomain(value)
})

// Add domain handler
function addDomain() {
  const trimmed = newDomain.value.trim()

  if (!trimmed) {
    return
  }

  // Validate before submitting
  if (!validateDomain(trimmed)) {
    return
  }

  // Check for duplicates
  if (props.cookieDomains.includes(trimmed)) {
    domainError.value = `Domain "${trimmed}" is already in the whitelist.`
    return
  }

  // Emit the add event
  emit('add-domain', trimmed)

  // Clear input
  newDomain.value = ''
  domainError.value = ''
}

// Remove domain handler
function removeDomain(domain) {
  emit('remove-domain', domain)
}

// Reload handler
function reload() {
  emit('reload')
}

// Clear feedback handler
function clearFeedback() {
  emit('clear-feedback')
}
</script>

<style lang="scss" scoped>
@use '../../../styles/design-tokens' as *;
.security-card {
  background: var(--bg-raised, #1e3147);
  border-radius: $border-radius-rounded;
}

.security-subtitle {
  color: var(--text-muted);
}
</style>
