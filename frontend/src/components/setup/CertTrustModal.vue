<template>
  <Teleport to="body">
    <Transition name="overlay-fade">
      <div
        v-if="modelValue"
        class="setup-wizard-overlay"
        role="dialog"
        aria-modal="true"
        aria-label="Install HTTPS Certificate"
      >
        <!-- Backdrop — click does NOT close (same as setup wizard) -->
        <div class="setup-wizard-backdrop" />

        <!-- Content panel — identical structure to SetupWizardOverlay -->
        <div class="setup-wizard-panel smooth-border" tabindex="-1">
          <!-- Header -->
          <div class="setup-wizard-header">
            <h2 class="setup-wizard-title">
              <span class="setup-wizard-title-gradient">Certificate</span>
            </h2>
            <v-btn
              icon
              variant="text"
              size="small"
              class="setup-wizard-close-btn"
              aria-label="Close certificate dialog"
              @click="handleSkip"
            >
              <v-icon>mdi-close</v-icon>
            </v-btn>
          </div>

          <!-- Step content -->
          <div class="setup-wizard-content">
            <p class="step-question">
              You're connecting from another machine over HTTPS
            </p>
            <p class="cert-intro">
              Your browser accepted the connection, but AI coding tools
              (Claude Code, Codex CLI, Gemini CLI) need the server's root
              certificate installed on this machine to work properly.
            </p>

            <!-- Step 1: Download -->
              <div class="cert-step">
                <div class="cert-step-number">1</div>
                <div class="cert-step-content">
                  <div class="cert-step-title">Download the root certificate</div>
                  <v-btn
                    color="primary"
                    variant="flat"
                    prepend-icon="mdi-download"
                    class="mt-2 footer-btn-next"
                    :loading="downloading"
                    @click="downloadCert"
                  >
                    Download rootCA.pem
                  </v-btn>
                  <div v-if="downloadError" class="cert-error mt-2">{{ downloadError }}</div>
                </div>
              </div>

              <!-- Step 2: Install into OS trust store -->
              <div class="cert-step">
                <div class="cert-step-number">2</div>
                <div class="cert-step-content">
                  <div class="cert-step-title">Install it into your OS trust store</div>
                  <p class="cert-hint">Save the file to your Downloads folder, then run:</p>

                  <div class="os-tabs">
                    <button
                      v-for="os in osList"
                      :key="os.id"
                      :class="['os-tab', { 'os-tab--active': activeOs === os.id }]"
                      @click="activeOs = os.id"
                    >
                      {{ os.label }}
                    </button>
                  </div>

                  <div class="cert-command-block smooth-border">
                    <code class="cert-command">{{ osCommands[activeOs] }}</code>
                    <v-btn
                      icon
                      variant="text"
                      size="x-small"
                      class="cert-copy-btn"
                      aria-label="Copy command"
                      @click="copyCommand(osCommands[activeOs], 'os')"
                    >
                      <v-icon size="14">{{ copiedOs ? 'mdi-check' : 'mdi-content-copy' }}</v-icon>
                    </v-btn>
                  </div>
                </div>
              </div>

              <!-- Step 3: NODE_EXTRA_CA_CERTS -->
              <div class="cert-step">
                <div class="cert-step-number">3</div>
                <div class="cert-step-content">
                  <div class="cert-step-title">Trust certificate in Node.js</div>
                  <p class="cert-hint">Required for Claude Code, Codex CLI, and Gemini CLI (all Node versions):</p>

                  <div class="cert-command-block smooth-border">
                    <code class="cert-command">{{ nodeCommand }}</code>
                    <v-btn
                      icon
                      variant="text"
                      size="x-small"
                      class="cert-copy-btn"
                      aria-label="Copy NODE_EXTRA_CA_CERTS command"
                      @click="copyCommand(nodeCommand, 'node')"
                    >
                      <v-icon size="14">{{ copiedNode ? 'mdi-check' : 'mdi-content-copy' }}</v-icon>
                    </v-btn>
                  </div>
                </div>
              </div>
          </div>

          <!-- Footer — same pattern as setup wizard -->
          <div class="setup-wizard-footer">
            <v-btn variant="text" class="footer-btn-back" @click="handleSkip">
              Skip for now
            </v-btn>
            <v-spacer />
            <v-btn
              color="primary"
              variant="flat"
              class="footer-btn-next"
              @click="handleContinue"
            >
              Continue to Setup
            </v-btn>
          </div>
        </div>
      </div>
    </Transition>
  </Teleport>
</template>

<script setup>
import { ref, computed } from 'vue'
import { getApiBaseURL } from '@/config/api'
import { useClipboard } from '@/composables/useClipboard'
import { useToast } from '@/composables/useToast'

defineProps({
  modelValue: { type: Boolean, required: true },
})

const emit = defineEmits(['update:modelValue', 'continue'])

const { copy: clipboardCopy } = useClipboard()
const { showToast } = useToast()

const downloading = ref(false)
const downloadError = ref('')
const copiedOs = ref(false)
const copiedNode = ref(false)

// Detect client OS from navigator
const detectedOs = (() => {
  const ua = navigator.userAgent || ''
  if (/Win/.test(ua)) return 'windows'
  if (/Mac/.test(ua)) return 'macos'
  return 'linux'
})()

const activeOs = ref(detectedOs)

const osList = [
  { id: 'windows', label: 'Windows' },
  { id: 'macos', label: 'macOS' },
  { id: 'linux', label: 'Linux' },
]

const osCommands = {
  windows: 'certutil -addstore -f "ROOT" %USERPROFILE%\\Downloads\\rootCA.pem',
  macos: 'sudo security add-trusted-cert -d -r trustRoot -k /Library/Keychains/System.keychain ~/Downloads/rootCA.pem',
  linux: 'sudo cp ~/Downloads/rootCA.pem /usr/local/share/ca-certificates/giljoai.crt && sudo update-ca-certificates',
}

const nodeCommand = computed(() => {
  if (activeOs.value === 'windows') {
    return '$env:NODE_OPTIONS = "--use-system-ca"; [System.Environment]::SetEnvironmentVariable(\'NODE_OPTIONS\', \'--use-system-ca\', \'User\')'
  }
  const rcFile = activeOs.value === 'macos' ? '~/.zshrc' : '~/.bashrc'
  return `mkdir -p ~/.giljo && cp ~/Downloads/rootCA.pem ~/.giljo/rootCA.pem && echo 'export NODE_EXTRA_CA_CERTS="$HOME/.giljo/rootCA.pem"' >> ${rcFile} && source ${rcFile}`
})

async function downloadCert() {
  downloading.value = true
  downloadError.value = ''
  try {
    const csrfToken = document.cookie.match(/csrf_token=([^;]+)/)?.[1]
    const response = await fetch(`${getApiBaseURL()}/api/v1/config/root-ca`, {
      credentials: 'include',
      headers: {
        ...(csrfToken && { 'X-CSRF-Token': csrfToken }),
      },
    })
    if (!response.ok) {
      const err = await response.json().catch(() => ({}))
      throw new Error(err.detail || `Download failed (${response.status})`)
    }
    const blob = await response.blob()
    const url = URL.createObjectURL(blob)
    const a = document.createElement('a')
    a.href = url
    a.download = 'rootCA.pem'
    document.body.appendChild(a)
    a.click()
    document.body.removeChild(a)
    URL.revokeObjectURL(url)
  } catch (err) {
    downloadError.value = err.message
  } finally {
    downloading.value = false
  }
}

async function copyCommand(text, which) {
  const success = await clipboardCopy(text)
  if (which === 'node') {
    copiedNode.value = true
    setTimeout(() => { copiedNode.value = false }, 2000)
  } else {
    copiedOs.value = true
    setTimeout(() => { copiedOs.value = false }, 2000)
  }
  if (success) {
    showToast({ message: 'Copied to clipboard', type: 'success', duration: 2000 })
  }
}

function handleContinue() {
  emit('update:modelValue', false)
  emit('continue')
}

function handleSkip() {
  emit('update:modelValue', false)
  emit('continue')
}
</script>

<style scoped lang="scss">
@use '../../styles/variables' as *;
@use '../../styles/design-tokens' as *;

/* ── Reuse the exact same overlay/panel/header/footer styles as SetupWizardOverlay ── */

.overlay-fade-enter-active { transition: opacity 250ms ease-out; }
.overlay-fade-leave-active { transition: opacity 200ms ease-in; }
.overlay-fade-enter-from, .overlay-fade-leave-to { opacity: 0; }

.setup-wizard-overlay {
  position: fixed;
  inset: 0;
  z-index: 2100;
  display: flex;
  align-items: center;
  justify-content: center;
  padding: 24px;
}

.setup-wizard-backdrop {
  position: absolute;
  inset: 0;
  background: rgba($color-background-primary, 0.85);
}

.setup-wizard-panel {
  position: relative;
  width: 100%;
  max-width: 800px;
  max-height: calc(100vh - 48px);
  overflow-y: auto;
  background: $elevation-raised;
  border-radius: $border-radius-rounded;
  display: flex;
  flex-direction: column;
}

.setup-wizard-header {
  display: flex;
  align-items: center;
  justify-content: center;
  position: relative;
  padding: 20px 24px 12px;
}

.setup-wizard-title {
  font-size: 3rem;
  font-weight: 700;
  color: $color-text-primary;
  margin: 0;
  line-height: 1.2;
  letter-spacing: 0.5px;
  text-align: center;
}

.setup-wizard-title-gradient {
  background: var(--gradient-brand);
  -webkit-background-clip: text;
  -webkit-text-fill-color: transparent;
  background-clip: text;
}

.setup-wizard-close-btn {
  position: absolute;
  right: 24px;
  top: 50%;
  transform: translateY(-50%);
}

.setup-wizard-content {
  flex: 1;
  padding: 0 24px 16px;
  min-height: 240px;
}

.setup-wizard-footer {
  display: flex;
  align-items: center;
  padding: 12px 24px 20px;
}

.footer-btn-back {
  color: $lightest-blue !important;
}

.footer-btn-next {
  border-radius: $border-radius-default;
  min-width: 100px;
  font-weight: 600;
}

/* ── Step question — matches SetupWizardOverlay's .step-question ── */

.step-question {
  font-family: "Roboto", "Segoe UI", system-ui, -apple-system, sans-serif;
  font-size: 1rem;
  font-weight: 500;
  color: $color-text-primary;
  margin-bottom: 8px;
  text-align: center;
}

/* ── Cert-specific content styles ── */

.cert-intro {
  font-size: 0.8125rem;
  color: $lightest-blue;
  line-height: 1.6;
  margin-bottom: 24px;
  text-align: center;
  padding: 0 15%;
}

.cert-step {
  display: flex;
  flex-direction: column;
  align-items: center;
  text-align: center;
  margin-bottom: 20px;
}

.cert-step:last-child {
  margin-bottom: 0;
}

.cert-step-number {
  flex-shrink: 0;
  width: 28px;
  height: 28px;
  border-radius: 50%;
  background: $color-brand-yellow;
  color: $color-background-primary;
  font-size: 0.8rem;
  font-weight: 700;
  display: grid;
  place-items: center;
}

.cert-step-content {
  width: 100%;
}

.cert-step-title {
  font-size: 0.9375rem;
  font-weight: 600;
  color: $color-text-primary;
  margin-bottom: 4px;
}

.cert-hint {
  font-size: 0.8125rem;
  color: $lightest-blue;
  margin-bottom: 8px;
  text-align: center;
}

.os-tabs {
  display: flex;
  justify-content: center;
  gap: 4px;
  margin-bottom: 8px;
}

.os-tab {
  padding: 4px 12px;
  font-size: 0.75rem;
  font-weight: 500;
  border: none;
  border-radius: $border-radius-default;
  background: transparent;
  color: $lightest-blue;
  cursor: pointer;
  transition: all 150ms ease-out;
}

.os-tab:hover {
  background: rgba(255, 255, 255, 0.05);
}

.os-tab--active {
  background: rgba($color-brand-yellow, 0.15);
  color: $color-brand-yellow;
}

.cert-command-block {
  position: relative;
  background: rgba(0, 0, 0, 0.3);
  border-radius: $border-radius-default;
  padding: 10px 40px 10px 12px;
  margin: 0 15%;
}

.cert-command {
  font-family: 'IBM Plex Mono', monospace;
  font-size: 0.75rem;
  color: $color-text-primary;
  word-break: break-all;
  white-space: pre-wrap;
}

.cert-copy-btn {
  position: absolute;
  top: 6px;
  right: 6px;
  color: $lightest-blue !important;
}

.cert-error {
  font-size: 0.8125rem;
  color: rgb(var(--v-theme-error));
}

/* ── Responsive — matches SetupWizardOverlay breakpoints ── */

@media (max-width: 599px) {
  .setup-wizard-overlay { padding: 12px; }
  .setup-wizard-header { padding: 16px 16px 8px; }
  .setup-wizard-content { padding: 0 16px 12px; }
  .setup-wizard-footer { padding: 8px 16px 16px; }
}
</style>
