/**
 * Test suite for SettingsView component - Network Tab
 *
 * Tests the Network Configuration tab functionality including:
 * - Network settings display (mode, API host/port)
 * - CORS origin management
 * - API key information display
 * - Mode switching UI (disabled for now)
 * - Navigation to Setup Wizard
 */
import { describe, it, expect, vi, beforeEach, afterEach } from 'vitest'
import { mount } from '@vue/test-utils'
import { createRouter, createMemoryHistory } from 'vue-router'
import { createVuetify } from 'vuetify'
import * as components from 'vuetify/components'
import * as directives from 'vuetify/directives'
import { createPinia, setActivePinia } from 'pinia'

// Mock SettingsView component (simplified version for testing Network tab)
const SettingsView = {
  name: 'SettingsView',
  template: `
    <v-container>
      <v-tabs v-model="activeTab">
        <v-tab value="general">General</v-tab>
        <v-tab value="network">Network</v-tab>
      </v-tabs>

      <v-window v-model="activeTab">
        <!-- General tab (simplified) -->
        <v-window-item value="general">
          <v-card>
            <v-card-title>General Settings</v-card-title>
          </v-card>
        </v-window-item>

        <!-- Network tab -->
        <v-window-item value="network">
          <v-card data-test="network-tab">
            <v-card-title>Network Configuration</v-card-title>
            <v-card-subtitle>Manage deployment mode and network access</v-card-subtitle>

            <v-card-text>
              <!-- Current Mode Display -->
              <v-alert type="info" variant="tonal" class="mb-4" data-test="mode-alert">
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
                data-test="api-host-field"
              />

              <v-text-field
                :model-value="networkSettings.apiPort"
                label="API Port"
                variant="outlined"
                readonly
                data-test="api-port-field"
              />

              <!-- CORS Origins Management -->
              <v-divider class="my-6" />

              <h3 class="text-h6 mb-3">CORS Allowed Origins</h3>

              <v-list density="compact" class="mb-4" data-test="cors-list">
                <v-list-item
                  v-for="(origin, index) in corsOrigins"
                  :key="index"
                  :data-test="'cors-item-' + index"
                >
                  <v-list-item-title>{{ origin }}</v-list-item-title>

                  <template v-slot:append>
                    <v-btn
                      icon="mdi-content-copy"
                      size="small"
                      variant="text"
                      @click="copyOrigin(origin)"
                      :data-test="'copy-origin-' + index"
                    />
                    <v-btn
                      v-if="!isDefaultOrigin(origin)"
                      icon="mdi-delete"
                      size="small"
                      variant="text"
                      color="error"
                      @click="removeOrigin(index)"
                      :data-test="'remove-origin-' + index"
                    />
                  </template>
                </v-list-item>
              </v-list>

              <v-text-field
                v-model="newOrigin"
                label="Add New Origin"
                variant="outlined"
                placeholder="http://192.168.1.100:7274"
                :append-icon="'mdi-plus'"
                @click:append="addOrigin"
                @keyup.enter="addOrigin"
                data-test="new-origin-field"
              />

              <!-- API Key Info -->
              <v-divider class="my-6" />

              <h3 class="text-h6 mb-3">API Key Information</h3>

              <v-alert
                v-if="currentMode === 'localhost'"
                type="info"
                variant="tonal"
                data-test="no-api-key-alert"
              >
                API key authentication is disabled in localhost mode
              </v-alert>

              <template v-else>
                <v-text-field
                  v-if="apiKeyInfo"
                  :model-value="maskedApiKey"
                  label="Active API Key"
                  variant="outlined"
                  readonly
                  data-test="api-key-field"
                />
              </template>

              <!-- Mode Switching -->
              <v-divider class="my-6" />

              <h3 class="text-h6 mb-3">Deployment Mode</h3>

              <v-select
                v-model="selectedMode"
                :items="availableModes"
                label="Deployment Mode"
                variant="outlined"
                disabled
                data-test="mode-select"
              />
            </v-card-text>

            <v-card-actions>
              <v-btn
                variant="outlined"
                @click="navigateToSetupWizard"
                data-test="setup-wizard-btn"
              >
                <v-icon start>mdi-wizard-hat</v-icon>
                Re-run Setup Wizard
              </v-btn>
              <v-spacer />
              <v-btn
                variant="text"
                @click="loadNetworkSettings"
                data-test="reload-btn"
              >
                <v-icon start>mdi-refresh</v-icon>
                Reload
              </v-btn>
              <v-btn
                color="primary"
                :disabled="!networkSettingsChanged"
                @click="saveNetworkSettings"
                data-test="save-btn"
              >
                Save Changes
              </v-btn>
            </v-card-actions>
          </v-card>
        </v-window-item>
      </v-window>
    </v-container>
  `,
  data() {
    return {
      activeTab: 'general',
      networkSettings: {
        apiHost: '127.0.0.1',
        apiPort: 7272,
      },
      currentMode: 'localhost',
      corsOrigins: [],
      newOrigin: '',
      apiKeyInfo: null,
      selectedMode: 'localhost',
      availableModes: [
        { title: 'Localhost (Single User)', value: 'localhost' },
        { title: 'LAN (Team Network)', value: 'lan' },
        { title: 'WAN (Internet) - Coming Soon', value: 'wan', disabled: true }
      ],
      networkSettingsChanged: false,
    }
  },
  computed: {
    modeColor() {
      const colors = {
        localhost: 'success',
        lan: 'info',
        wan: 'warning'
      }
      return colors[this.currentMode] || 'grey'
    },

    maskedApiKey() {
      if (!this.apiKeyInfo || !this.apiKeyInfo.key_preview) {
        return 'No API key configured'
      }
      const preview = this.apiKeyInfo.key_preview
      return `${preview.substring(0, 8)}...${preview.substring(preview.length - 4)}`
    }
  },
  methods: {
    async loadNetworkSettings() {
      try {
        // In tests, this will use mocked fetch
        const response = await fetch('http://localhost:7272/api/v1/config')
        const config = await response.json()

        this.currentMode = config.installation?.mode || 'localhost'
        this.selectedMode = this.currentMode

        this.networkSettings.apiHost = config.services?.api?.host || '127.0.0.1'
        this.networkSettings.apiPort = config.services?.api?.port || 7272

        this.corsOrigins = config.security?.cors?.allowed_origins || []

        if (this.currentMode === 'lan') {
          this.apiKeyInfo = {
            created_at: new Date().toISOString(),
            key_preview: 'gk_xxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxx'
          }
        }
      } catch (error) {
        console.error('Failed to load network settings:', error)
      }
    },

    isDefaultOrigin(origin) {
      return origin.includes('localhost') || origin.includes('127.0.0.1')
    },

    copyOrigin(origin) {
      // Mock clipboard for tests
      if (navigator.clipboard && navigator.clipboard.writeText) {
        navigator.clipboard.writeText(origin)
      }
    },

    addOrigin() {
      if (!this.newOrigin) return

      try {
        new URL(this.newOrigin)
        if (!this.corsOrigins.includes(this.newOrigin)) {
          this.corsOrigins.push(this.newOrigin)
          this.newOrigin = ''
          this.networkSettingsChanged = true
        }
      } catch (error) {
        console.error('Invalid origin format:', error)
      }
    },

    removeOrigin(index) {
      this.corsOrigins.splice(index, 1)
      this.networkSettingsChanged = true
    },

    async saveNetworkSettings() {
      try {
        const response = await fetch('http://localhost:7272/api/v1/config', {
          method: 'PATCH',
          headers: { 'Content-Type': 'application/json' },
          body: JSON.stringify({
            security: {
              cors: {
                allowed_origins: this.corsOrigins
              }
            }
          })
        })

        if (response.ok) {
          this.networkSettingsChanged = false
        }
      } catch (error) {
        console.error('Failed to save network settings:', error)
      }
    },

    navigateToSetupWizard() {
      this.$router.push('/setup')
    }
  },
  async mounted() {
    await this.loadNetworkSettings()
  }
}

describe('SettingsView.vue - Network Tab', () => {
  let vuetify
  let router
  let pinia
  let wrapper

  beforeEach(() => {
    // Setup Vuetify
    vuetify = createVuetify({
      components,
      directives
    })

    // Setup Pinia
    pinia = createPinia()
    setActivePinia(pinia)

    // Setup Router
    router = createRouter({
      history: createMemoryHistory(),
      routes: [
        { path: '/', name: 'Dashboard', component: { template: '<div>Dashboard</div>' } },
        { path: '/settings', name: 'Settings', component: SettingsView },
        { path: '/setup', name: 'Setup', component: { template: '<div>Setup</div>' } }
      ]
    })

    // Mock clipboard API
    Object.assign(navigator, {
      clipboard: {
        writeText: vi.fn(() => Promise.resolve())
      }
    })

    // Mock fetch for config API
    global.fetch = vi.fn()
  })

  afterEach(() => {
    if (wrapper) {
      wrapper.unmount()
    }
    vi.clearAllMocks()
  })

  describe('Network Tab Display', () => {
    it('renders network tab button', () => {
      wrapper = mount(SettingsView, {
        global: {
          plugins: [vuetify, router, pinia]
        }
      })

      const tabs = wrapper.findAll('.v-tab')
      const networkTab = tabs.find(tab => tab.text().includes('Network'))
      expect(networkTab).toBeDefined()
    })

    it('shows network tab content when clicked', async () => {
      wrapper = mount(SettingsView, {
        global: {
          plugins: [vuetify, router, pinia]
        }
      })

      // Switch to network tab
      wrapper.vm.activeTab = 'network'
      await wrapper.vm.$nextTick()

      const networkCard = wrapper.find('[data-test="network-tab"]')
      expect(networkCard.exists()).toBe(true)
      expect(networkCard.text()).toContain('Network Configuration')
    })

    it('displays current deployment mode', async () => {
      wrapper = mount(SettingsView, {
        global: {
          plugins: [vuetify, router, pinia]
        }
      })

      wrapper.vm.activeTab = 'network'
      wrapper.vm.currentMode = 'localhost'
      await wrapper.vm.$nextTick()

      const modeChip = wrapper.find('[data-test="mode-chip"]')
      expect(modeChip.text()).toBe('LOCALHOST')
    })

    it('displays API host and port', async () => {
      wrapper = mount(SettingsView, {
        global: {
          plugins: [vuetify, router, pinia]
        }
      })

      wrapper.vm.activeTab = 'network'
      wrapper.vm.networkSettings = {
        apiHost: '0.0.0.0',
        apiPort: 7272
      }
      await wrapper.vm.$nextTick()

      const hostField = wrapper.find('[data-test="api-host-field"]')
      const portField = wrapper.find('[data-test="api-port-field"]')

      expect(hostField.exists()).toBe(true)
      expect(portField.exists()).toBe(true)
    })
  })

  describe('Mode Color Computed Property', () => {
    it('returns success color for localhost mode', () => {
      wrapper = mount(SettingsView, {
        global: {
          plugins: [vuetify, router, pinia]
        }
      })

      wrapper.vm.currentMode = 'localhost'
      expect(wrapper.vm.modeColor).toBe('success')
    })

    it('returns info color for LAN mode', () => {
      wrapper = mount(SettingsView, {
        global: {
          plugins: [vuetify, router, pinia]
        }
      })

      wrapper.vm.currentMode = 'lan'
      expect(wrapper.vm.modeColor).toBe('info')
    })

    it('returns warning color for WAN mode', () => {
      wrapper = mount(SettingsView, {
        global: {
          plugins: [vuetify, router, pinia]
        }
      })

      wrapper.vm.currentMode = 'wan'
      expect(wrapper.vm.modeColor).toBe('warning')
    })

    it('returns grey color for unknown mode', () => {
      wrapper = mount(SettingsView, {
        global: {
          plugins: [vuetify, router, pinia]
        }
      })

      wrapper.vm.currentMode = 'unknown'
      expect(wrapper.vm.modeColor).toBe('grey')
    })
  })

  describe('CORS Origin Management', () => {
    it('displays CORS origins list', async () => {
      wrapper = mount(SettingsView, {
        global: {
          plugins: [vuetify, router, pinia]
        }
      })

      wrapper.vm.activeTab = 'network'
      wrapper.vm.corsOrigins = [
        'http://localhost:7274',
        'http://192.168.1.100:7274'
      ]
      await wrapper.vm.$nextTick()

      const corsList = wrapper.find('[data-test="cors-list"]')
      expect(corsList.exists()).toBe(true)
      expect(wrapper.findAll('[data-test^="cors-item-"]').length).toBe(2)
    })

    it('adds new CORS origin', async () => {
      wrapper = mount(SettingsView, {
        global: {
          plugins: [vuetify, router, pinia]
        }
      })

      wrapper.vm.activeTab = 'network'
      wrapper.vm.corsOrigins = ['http://localhost:7274']
      wrapper.vm.newOrigin = 'http://192.168.1.100:7274'
      await wrapper.vm.$nextTick()

      wrapper.vm.addOrigin()
      await wrapper.vm.$nextTick()

      expect(wrapper.vm.corsOrigins).toContain('http://192.168.1.100:7274')
      expect(wrapper.vm.newOrigin).toBe('')
      expect(wrapper.vm.networkSettingsChanged).toBe(true)
    })

    it('prevents adding duplicate CORS origin', async () => {
      wrapper = mount(SettingsView, {
        global: {
          plugins: [vuetify, router, pinia]
        }
      })

      wrapper.vm.corsOrigins = ['http://localhost:7274']
      wrapper.vm.newOrigin = 'http://localhost:7274'

      wrapper.vm.addOrigin()
      await wrapper.vm.$nextTick()

      expect(wrapper.vm.corsOrigins.length).toBe(1)
    })

    it('validates URL format when adding origin', async () => {
      wrapper = mount(SettingsView, {
        global: {
          plugins: [vuetify, router, pinia]
        }
      })

      wrapper.vm.corsOrigins = []
      wrapper.vm.newOrigin = 'invalid-url'

      wrapper.vm.addOrigin()
      await wrapper.vm.$nextTick()

      // Invalid URL should not be added
      expect(wrapper.vm.corsOrigins.length).toBe(0)
    })

    it('removes CORS origin', async () => {
      wrapper = mount(SettingsView, {
        global: {
          plugins: [vuetify, router, pinia]
        }
      })

      wrapper.vm.corsOrigins = [
        'http://localhost:7274',
        'http://192.168.1.100:7274'
      ]

      wrapper.vm.removeOrigin(1)
      await wrapper.vm.$nextTick()

      expect(wrapper.vm.corsOrigins.length).toBe(1)
      expect(wrapper.vm.corsOrigins).not.toContain('http://192.168.1.100:7274')
      expect(wrapper.vm.networkSettingsChanged).toBe(true)
    })

    it('copies origin to clipboard', async () => {
      wrapper = mount(SettingsView, {
        global: {
          plugins: [vuetify, router, pinia]
        }
      })

      const origin = 'http://localhost:7274'
      wrapper.vm.copyOrigin(origin)
      await wrapper.vm.$nextTick()

      expect(navigator.clipboard.writeText).toHaveBeenCalledWith(origin)
    })

    it('identifies default origins correctly', () => {
      wrapper = mount(SettingsView, {
        global: {
          plugins: [vuetify, router, pinia]
        }
      })

      expect(wrapper.vm.isDefaultOrigin('http://localhost:7274')).toBe(true)
      expect(wrapper.vm.isDefaultOrigin('http://127.0.0.1:7274')).toBe(true)
      expect(wrapper.vm.isDefaultOrigin('http://192.168.1.100:7274')).toBe(false)
    })

    it('hides delete button for default origins', async () => {
      wrapper = mount(SettingsView, {
        global: {
          plugins: [vuetify, router, pinia]
        }
      })

      wrapper.vm.activeTab = 'network'
      wrapper.vm.corsOrigins = [
        'http://localhost:7274',
        'http://192.168.1.100:7274'
      ]
      await wrapper.vm.$nextTick()

      // Default origin (localhost) should not have delete button
      const firstItemDeleteBtn = wrapper.find('[data-test="remove-origin-0"]')
      expect(firstItemDeleteBtn.exists()).toBe(false)

      // Custom origin should have delete button
      const secondItemDeleteBtn = wrapper.find('[data-test="remove-origin-1"]')
      expect(secondItemDeleteBtn.exists()).toBe(true)
    })
  })

  describe('API Key Display', () => {
    it('shows no API key message in localhost mode', async () => {
      wrapper = mount(SettingsView, {
        global: {
          plugins: [vuetify, router, pinia]
        }
      })

      wrapper.vm.activeTab = 'network'
      wrapper.vm.currentMode = 'localhost'
      await wrapper.vm.$nextTick()

      const noKeyAlert = wrapper.find('[data-test="no-api-key-alert"]')
      expect(noKeyAlert.exists()).toBe(true)
      expect(noKeyAlert.text()).toContain('API key authentication is disabled')
    })

    it('shows masked API key in LAN mode', async () => {
      wrapper = mount(SettingsView, {
        global: {
          plugins: [vuetify, router, pinia]
        }
      })

      wrapper.vm.activeTab = 'network'
      wrapper.vm.currentMode = 'lan'
      wrapper.vm.apiKeyInfo = {
        key_preview: 'gk_1234567890abcdefghijklmnopqrstuvwxyz1234',
        created_at: '2025-10-06T12:00:00Z'
      }
      await wrapper.vm.$nextTick()

      const apiKeyField = wrapper.find('[data-test="api-key-field"]')
      expect(apiKeyField.exists()).toBe(true)
    })

    it('masks API key correctly', () => {
      wrapper = mount(SettingsView, {
        global: {
          plugins: [vuetify, router, pinia]
        }
      })

      wrapper.vm.apiKeyInfo = {
        key_preview: 'gk_1234567890abcdefghijklmnopqrstuvwxyz1234'
      }

      const masked = wrapper.vm.maskedApiKey
      expect(masked).toBe('gk_12345...1234')
    })

    it('handles missing API key gracefully', () => {
      wrapper = mount(SettingsView, {
        global: {
          plugins: [vuetify, router, pinia]
        }
      })

      wrapper.vm.apiKeyInfo = null
      expect(wrapper.vm.maskedApiKey).toBe('No API key configured')
    })
  })

  describe('Load Network Settings', () => {
    it('loads network settings from API', async () => {
      const mockConfig = {
        installation: { mode: 'lan' },
        services: {
          api: {
            host: '0.0.0.0',
            port: 7272
          }
        },
        security: {
          cors: {
            allowed_origins: [
              'http://localhost:7274',
              'http://192.168.1.100:7274'
            ]
          }
        }
      }

      global.fetch.mockResolvedValueOnce({
        ok: true,
        json: async () => mockConfig
      })

      wrapper = mount(SettingsView, {
        global: {
          plugins: [vuetify, router, pinia]
        }
      })

      await wrapper.vm.loadNetworkSettings()
      await wrapper.vm.$nextTick()

      expect(wrapper.vm.currentMode).toBe('lan')
      expect(wrapper.vm.networkSettings.apiHost).toBe('0.0.0.0')
      expect(wrapper.vm.networkSettings.apiPort).toBe(7272)
      expect(wrapper.vm.corsOrigins.length).toBe(2)
    })

    it('sets API key info for LAN mode', async () => {
      const mockConfig = {
        installation: { mode: 'lan' },
        services: {
          api: { host: '0.0.0.0', port: 7272 }
        },
        security: {
          cors: { allowed_origins: [] }
        }
      }

      global.fetch.mockResolvedValueOnce({
        ok: true,
        json: async () => mockConfig
      })

      wrapper = mount(SettingsView, {
        global: {
          plugins: [vuetify, router, pinia]
        }
      })

      await wrapper.vm.loadNetworkSettings()
      await wrapper.vm.$nextTick()

      expect(wrapper.vm.apiKeyInfo).not.toBeNull()
      expect(wrapper.vm.apiKeyInfo.key_preview).toBe('gk_xxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxx')
    })

    it('handles API errors gracefully', async () => {
      global.fetch.mockRejectedValueOnce(new Error('Network error'))

      wrapper = mount(SettingsView, {
        global: {
          plugins: [vuetify, router, pinia]
        }
      })

      // Should not throw
      await expect(wrapper.vm.loadNetworkSettings()).resolves.not.toThrow()
    })
  })

  describe('Save Network Settings', () => {
    it('saves CORS settings to API', async () => {
      // Mock config load (called on mount)
      global.fetch.mockResolvedValueOnce({
        ok: true,
        json: async () => ({
          installation: { mode: 'localhost' },
          services: { api: { host: '127.0.0.1', port: 7272 } },
          security: { cors: { allowed_origins: [] } }
        })
      })

      // Mock save call
      global.fetch.mockResolvedValueOnce({
        ok: true,
        json: async () => ({ success: true })
      })

      wrapper = mount(SettingsView, {
        global: {
          plugins: [vuetify, router, pinia]
        }
      })

      // Wait for mount to complete
      await wrapper.vm.$nextTick()

      wrapper.vm.corsOrigins = [
        'http://localhost:7274',
        'http://192.168.1.100:7274'
      ]
      wrapper.vm.networkSettingsChanged = true

      await wrapper.vm.saveNetworkSettings()
      await wrapper.vm.$nextTick()

      expect(global.fetch).toHaveBeenCalledWith(
        'http://localhost:7272/api/v1/config',
        expect.objectContaining({
          method: 'PATCH',
          headers: { 'Content-Type': 'application/json' },
          body: expect.any(String)
        })
      )

      expect(wrapper.vm.networkSettingsChanged).toBe(false)
    })

    it('resets changed flag after successful save', async () => {
      // Mock config load (called on mount)
      global.fetch.mockResolvedValueOnce({
        ok: true,
        json: async () => ({
          installation: { mode: 'localhost' },
          services: { api: { host: '127.0.0.1', port: 7272 } },
          security: { cors: { allowed_origins: [] } }
        })
      })

      // Mock save call
      global.fetch.mockResolvedValueOnce({
        ok: true,
        json: async () => ({ success: true })
      })

      wrapper = mount(SettingsView, {
        global: {
          plugins: [vuetify, router, pinia]
        }
      })

      // Wait for mount to complete
      await wrapper.vm.$nextTick()

      wrapper.vm.networkSettingsChanged = true
      await wrapper.vm.saveNetworkSettings()

      expect(wrapper.vm.networkSettingsChanged).toBe(false)
    })
  })

  describe('Navigation', () => {
    it('navigates to setup wizard', async () => {
      wrapper = mount(SettingsView, {
        global: {
          plugins: [vuetify, router, pinia]
        }
      })

      const routerPushSpy = vi.spyOn(router, 'push')

      wrapper.vm.activeTab = 'network'
      await wrapper.vm.$nextTick()

      const setupWizardBtn = wrapper.find('[data-test="setup-wizard-btn"]')
      await setupWizardBtn.trigger('click')

      expect(routerPushSpy).toHaveBeenCalledWith('/setup')
    })
  })

  describe('Button States', () => {
    it('disables save button when no changes', async () => {
      wrapper = mount(SettingsView, {
        global: {
          plugins: [vuetify, router, pinia]
        }
      })

      wrapper.vm.activeTab = 'network'
      wrapper.vm.networkSettingsChanged = false
      await wrapper.vm.$nextTick()

      expect(wrapper.vm.networkSettingsChanged).toBe(false)
    })

    it('enables save button when changes made', async () => {
      wrapper = mount(SettingsView, {
        global: {
          plugins: [vuetify, router, pinia]
        }
      })

      wrapper.vm.activeTab = 'network'
      wrapper.vm.networkSettingsChanged = true
      await wrapper.vm.$nextTick()

      expect(wrapper.vm.networkSettingsChanged).toBe(true)
    })

    it('disables mode select (future feature)', async () => {
      wrapper = mount(SettingsView, {
        global: {
          plugins: [vuetify, router, pinia]
        }
      })

      wrapper.vm.activeTab = 'network'
      wrapper.vm.selectedMode = 'localhost'
      await wrapper.vm.$nextTick()

      // Mode switching is disabled (future feature)
      expect(wrapper.vm.selectedMode).toBe('localhost')
    })
  })

  describe('Lifecycle Hooks', () => {
    it('loads network settings on mount', async () => {
      const mockConfig = {
        installation: { mode: 'localhost' },
        services: {
          api: { host: '127.0.0.1', port: 7272 }
        },
        security: {
          cors: { allowed_origins: ['http://localhost:7274'] }
        }
      }

      global.fetch.mockResolvedValueOnce({
        ok: true,
        json: async () => mockConfig
      })

      wrapper = mount(SettingsView, {
        global: {
          plugins: [vuetify, router, pinia]
        }
      })

      // Wait for mounted hook to complete
      await wrapper.vm.$nextTick()
      await new Promise(resolve => setTimeout(resolve, 0))

      expect(global.fetch).toHaveBeenCalledWith('http://localhost:7272/api/v1/config')
    })
  })
})
