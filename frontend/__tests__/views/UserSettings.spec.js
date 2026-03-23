import { describe, it, expect, beforeEach, afterEach, vi } from 'vitest'
import { mount } from '@vue/test-utils'
import { createVuetify } from 'vuetify'
import { createPinia } from 'pinia'
import { createRouter, createMemoryHistory } from 'vue-router'
import UserSettings from '@/views/UserSettings.vue'
import setupService from '@/services/setupService'

// Mock modules
vi.mock('@/services/setupService')
vi.mock('@/components/settings/ContextPriorityConfig.vue', () => ({
  default: { name: 'ContextPriorityConfig', template: '<div>Mock Context</div>' },
}))
vi.mock('@/components/TemplateManager.vue', () => ({
  default: { name: 'TemplateManager', template: '<div>Mock Manager</div>' },
}))
vi.mock('@/components/ApiKeyManager.vue', () => ({
  default: { name: 'ApiKeyManager', template: '<div>Mock Keys</div>' },
}))
vi.mock('@/components/AgentExport.vue', () => ({
  default: { name: 'AgentExport', template: '<div>Mock Agent Export</div>' },
}))
vi.mock('@/components/SerenaAdvancedSettingsDialog.vue', () => ({
  default: { name: 'SerenaAdvancedSettingsDialog', template: '<div>Mock Dialog</div>' },
}))
vi.mock('@/components/GitAdvancedSettingsDialog.vue', () => ({
  default: { name: 'GitAdvancedSettingsDialog', template: '<div>Mock Dialog</div>' },
}))
vi.mock('@/components/settings/integrations/McpIntegrationCard.vue', () => ({
  default: { name: 'McpIntegrationCard', template: '<div>Mock Card</div>' },
}))
vi.mock('@/components/settings/integrations/SerenaIntegrationCard.vue', () => ({
  default: { name: 'SerenaIntegrationCard', template: '<div>Mock Card</div>' },
}))
vi.mock('@/components/settings/integrations/GitIntegrationCard.vue', () => ({
  default: { name: 'GitIntegrationCard', template: '<div>Mock Card</div>' },
}))

describe('UserSettings.vue - Git Integration', () => {
  let wrapper
  const mockSetupService = setupService

  beforeEach(() => {
    vi.clearAllMocks()

    // Setup default mock responses
    mockSetupService.getSerenaStatus.mockResolvedValue({
      enabled: false,
    })

    mockSetupService.getGitSettings.mockResolvedValue({
      enabled: false,
      use_in_prompts: false,
      include_commit_history: true,
      max_commits: 50,
      branch_strategy: 'main',
    })

    mockSetupService.toggleGit.mockResolvedValue({
      success: true,
      enabled: true,
      message: 'Git integration enabled',
      settings: {
        enabled: true,
        use_in_prompts: true,
        include_commit_history: true,
        max_commits: 50,
        branch_strategy: 'main',
      },
    })

    mockSetupService.updateGitSettings.mockResolvedValue({
      success: true,
      enabled: true,
      message: 'Git settings updated',
      settings: {
        enabled: true,
        use_in_prompts: true,
        include_commit_history: true,
        max_commits: 100,
        branch_strategy: 'develop',
      },
    })
  })

  afterEach(() => {
    if (wrapper) {
      wrapper.unmount()
    }
  })

  function createWrapper() {
    const vuetify = createVuetify()
    const pinia = createPinia()
    const router = createRouter({
      history: createMemoryHistory(),
      routes: [
        {
          path: '/settings',
          component: UserSettings,
        },
      ],
    })

    return mount(UserSettings, {
      global: {
        plugins: [vuetify, pinia, router],
        stubs: {
          ContextPriorityConfig: true,
          TemplateManager: true,
          ApiKeyManager: true,
          AgentExport: true,
          SerenaAdvancedSettingsDialog: true,
          GitAdvancedSettingsDialog: true,
          McpIntegrationCard: true,
          SerenaIntegrationCard: true,
          GitIntegrationCard: true,
        },
      },
    })
  }

  // Test 1: Component mounts and loads git settings
  it('UT-GI-001: Component mounts and loads git settings on initialization', async () => {
    wrapper = createWrapper()
    await wrapper.vm.$nextTick()
    await new Promise(resolve => setTimeout(resolve, 100))

    // Verify setupService was called
    expect(mockSetupService.getGitSettings).toHaveBeenCalled()

    // Verify state was updated
    expect(wrapper.vm.gitEnabled).toBe(false) // From default mock
    expect(wrapper.vm.gitConfig.max_commits).toBe(50)
  })

  // Test 2: Toggle git integration enables/disables
  it('UT-GI-002: Toggle git integration updates state correctly', async () => {
    wrapper = createWrapper()
    await wrapper.vm.$nextTick()
    await new Promise(resolve => setTimeout(resolve, 100))

    // Mock successful toggle
    mockSetupService.toggleGit.mockResolvedValueOnce({
      success: true,
      enabled: true,
      message: 'Git enabled',
      settings: {
        enabled: true,
        use_in_prompts: true,
        include_commit_history: true,
        max_commits: 50,
        branch_strategy: 'main',
      },
    })

    // Call toggleGit
    await wrapper.vm.toggleGit(true)
    await wrapper.vm.$nextTick()

    // Verify toggle was called
    expect(mockSetupService.toggleGit).toHaveBeenCalledWith(true)

    // Verify UI state was updated
    expect(wrapper.vm.gitEnabled).toBe(true)
  })

  // Test 3: Toggle shows loading state during request
  it('UT-GI-002: Toggle sets loading state during API call', async () => {
    wrapper = createWrapper()
    await wrapper.vm.$nextTick()

    // Create promise that we can control
    let resolveFn
    const togglePromise = new Promise(resolve => {
      resolveFn = resolve
    })

    mockSetupService.toggleGit.mockReturnValueOnce(togglePromise)

    // Start toggle without awaiting
    const togglePromise2 = wrapper.vm.toggleGit(true)

    // Immediately check loading state
    expect(wrapper.vm.togglingGit).toBe(true)

    // Resolve the mock
    resolveFn({
      success: true,
      enabled: true,
      message: 'Success',
      settings: {},
    })

    // Wait for completion
    await togglePromise2
    await wrapper.vm.$nextTick()

    // Verify loading state cleared
    expect(wrapper.vm.togglingGit).toBe(false)
  })

  // Test 4: Toggle failure reverts UI state
  it('UT-GI-004: Toggle failure reverts UI state to original', async () => {
    wrapper = createWrapper()
    await wrapper.vm.$nextTick()
    await new Promise(resolve => setTimeout(resolve, 100))

    // Set initial state
    wrapper.vm.gitEnabled = false

    // Mock failed toggle
    mockSetupService.toggleGit.mockRejectedValueOnce(new Error('Network error'))

    // Call toggle (should fail)
    await wrapper.vm.toggleGit(true)
    await wrapper.vm.$nextTick()

    // Verify state was reverted
    expect(wrapper.vm.gitEnabled).toBe(false)
  })

  // Test 5: Toggle error response reverts UI
  it('UT-GI-004: Toggle error response reverts UI state', async () => {
    wrapper = createWrapper()
    await wrapper.vm.$nextTick()
    await new Promise(resolve => setTimeout(resolve, 100))

    // Set initial state
    wrapper.vm.gitEnabled = false

    // Mock failed response
    mockSetupService.toggleGit.mockResolvedValueOnce({
      success: false,
      enabled: false,
      message: 'Failed to toggle Git',
    })

    // Call toggle
    await wrapper.vm.toggleGit(true)
    await wrapper.vm.$nextTick()

    // Verify state was reverted
    expect(wrapper.vm.gitEnabled).toBe(false)
  })

  // Test 6: Open advanced settings dialog loads fresh config
  it('UT-GI-003: Open advanced settings loads fresh config from API', async () => {
    wrapper = createWrapper()
    await wrapper.vm.$nextTick()
    await new Promise(resolve => setTimeout(resolve, 100))

    // Mock fresh settings
    mockSetupService.getGitSettings.mockResolvedValueOnce({
      enabled: true,
      use_in_prompts: true,
      include_commit_history: false,
      max_commits: 75,
      branch_strategy: 'develop',
    })

    // Call openAdvanced
    await wrapper.vm.openGitAdvanced()
    await wrapper.vm.$nextTick()

    // Verify API was called
    expect(mockSetupService.getGitSettings).toHaveBeenCalled()

    // Verify settings updated
    expect(wrapper.vm.gitConfig.max_commits).toBe(75)
    expect(wrapper.vm.gitConfig.branch_strategy).toBe('develop')

    // Verify dialog opened
    expect(wrapper.vm.showGitAdvanced).toBe(true)
  })

  // Test 7: Save advanced settings updates config
  it('IT-GI-004: Save advanced settings updates config and closes dialog', async () => {
    wrapper = createWrapper()
    await wrapper.vm.$nextTick()
    await new Promise(resolve => setTimeout(resolve, 100))

    // Prepare new settings
    const newSettings = {
      use_in_prompts: true,
      include_commit_history: true,
      max_commits: 100,
      branch_strategy: 'develop',
    }

    // Mock save response
    mockSetupService.updateGitSettings.mockResolvedValueOnce({
      success: true,
      enabled: true,
      message: 'Settings saved',
      settings: {
        enabled: true,
        use_in_prompts: true,
        include_commit_history: true,
        max_commits: 100,
        branch_strategy: 'develop',
      },
    })

    // Open dialog first
    wrapper.vm.showGitAdvanced = true

    // Save settings
    await wrapper.vm.saveGitConfig(newSettings, () => {})
    await wrapper.vm.$nextTick()

    // Verify API was called
    expect(mockSetupService.updateGitSettings).toHaveBeenCalledWith(newSettings)

    // Verify config updated
    expect(wrapper.vm.gitConfig.max_commits).toBe(100)
    expect(wrapper.vm.gitConfig.branch_strategy).toBe('develop')

    // Verify dialog closed
    expect(wrapper.vm.showGitAdvanced).toBe(false)
  })

  // Test 8: Save advanced settings with done callback
  it('UT-GI-003: Save advanced settings calls done callback when provided', async () => {
    wrapper = createWrapper()
    await wrapper.vm.$nextTick()
    await new Promise(resolve => setTimeout(resolve, 100))

    const doneCallback = vi.fn()
    const newSettings = { max_commits: 80 }

    mockSetupService.updateGitSettings.mockResolvedValueOnce({
      success: true,
      enabled: true,
      message: 'Saved',
      settings: { max_commits: 80 },
    })

    // Save with callback
    await wrapper.vm.saveGitConfig(newSettings, doneCallback)
    await wrapper.vm.$nextTick()

    // Verify callback was called
    expect(doneCallback).toHaveBeenCalled()
  })

  // Test 9: Load git settings on error sets defaults
  it('UT-GI-001: Load git settings handles error gracefully with defaults', async () => {
    wrapper = createWrapper()

    // Mock error response
    mockSetupService.getGitSettings.mockRejectedValueOnce(new Error('Connection failed'))

    // Call loadGitSettings
    await wrapper.vm.loadGitSettings()
    await wrapper.vm.$nextTick()

    // Verify defaults are set
    expect(wrapper.vm.gitEnabled).toBe(false)
    expect(wrapper.vm.gitConfig.use_in_prompts).toBe(false)
    expect(wrapper.vm.gitConfig.include_commit_history).toBe(true)
    expect(wrapper.vm.gitConfig.max_commits).toBe(50)
    expect(wrapper.vm.gitConfig.branch_strategy).toBe('main')
  })

  // Test 10: Toggling git integration passes correct parameters
  it('IT-GI-001: toggleGit passes correct enabled parameter to API', async () => {
    wrapper = createWrapper()
    await wrapper.vm.$nextTick()

    // Mock response
    mockSetupService.toggleGit.mockResolvedValueOnce({
      success: true,
      enabled: true,
      settings: { enabled: true },
    })

    // Toggle to true
    await wrapper.vm.toggleGit(true)

    // Verify correct parameter passed
    expect(mockSetupService.toggleGit).toHaveBeenCalledWith(true)

    // Reset mock
    mockSetupService.toggleGit.mockClear()
    mockSetupService.toggleGit.mockResolvedValueOnce({
      success: true,
      enabled: false,
      settings: { enabled: false },
    })

    // Toggle to false
    await wrapper.vm.toggleGit(false)

    // Verify correct parameter passed
    expect(mockSetupService.toggleGit).toHaveBeenCalledWith(false)
  })

  // Test 11: Open advanced settings handles API error
  it('UT-GI-003: Open advanced settings handles API error gracefully', async () => {
    wrapper = createWrapper()
    await wrapper.vm.$nextTick()

    // Mock error
    mockSetupService.getGitSettings.mockRejectedValueOnce(new Error('API error'))

    // Spy on console.error
    const consoleSpy = vi.spyOn(console, 'error').mockImplementation(() => {})

    // Call openAdvanced
    await wrapper.vm.openGitAdvanced()
    await wrapper.vm.$nextTick()

    // Verify error was logged
    expect(consoleSpy).toHaveBeenCalled()

    // Verify dialog not opened (failed to load)
    expect(wrapper.vm.showGitAdvanced).toBe(false)

    consoleSpy.mockRestore()
  })

  // Test 12: Save advanced settings handles API error
  it('IT-GI-004: Save advanced settings handles API error gracefully', async () => {
    wrapper = createWrapper()
    await wrapper.vm.$nextTick()

    // Mock error
    mockSetupService.updateGitSettings.mockRejectedValueOnce(new Error('Save failed'))

    // Spy on console.error
    const consoleSpy = vi.spyOn(console, 'error').mockImplementation(() => {})

    // Call saveGitConfig
    await wrapper.vm.saveGitConfig({ max_commits: 80 }, () => {})
    await wrapper.vm.$nextTick()

    // Verify error was logged
    expect(consoleSpy).toHaveBeenCalled()

    consoleSpy.mockRestore()
  })

  // Test 13: Initial state is correct
  it('UT-GI-001: Initial git integration state is correct', async () => {
    wrapper = createWrapper()
    await wrapper.vm.$nextTick()

    // Verify initial state
    expect(wrapper.vm.gitEnabled).toBe(false)
    expect(wrapper.vm.togglingGit).toBe(false)
    expect(wrapper.vm.showGitAdvanced).toBe(false)
    expect(typeof wrapper.vm.gitConfig).toBe('object')
  })

  // Test 14: Git settings contain expected fields
  it('UT-GI-001: Loaded git settings contain all expected fields', async () => {
    wrapper = createWrapper()
    await wrapper.vm.$nextTick()
    await new Promise(resolve => setTimeout(resolve, 100))

    // Verify all expected fields are present
    expect(wrapper.vm.gitConfig).toHaveProperty('enabled')
    expect(wrapper.vm.gitConfig).toHaveProperty('use_in_prompts')
    expect(wrapper.vm.gitConfig).toHaveProperty('include_commit_history')
    expect(wrapper.vm.gitConfig).toHaveProperty('max_commits')
    expect(wrapper.vm.gitConfig).toHaveProperty('branch_strategy')
  })

  // Test 15: Toggle updates settings from response
  it('UT-GI-002: Toggle updates gitConfig from API response', async () => {
    wrapper = createWrapper()
    await wrapper.vm.$nextTick()
    await new Promise(resolve => setTimeout(resolve, 100))

    // Mock response with different settings
    mockSetupService.toggleGit.mockResolvedValueOnce({
      success: true,
      enabled: true,
      settings: {
        enabled: true,
        use_in_prompts: true,
        include_commit_history: false,
        max_commits: 75,
        branch_strategy: 'develop',
      },
    })

    // Toggle
    await wrapper.vm.toggleGit(true)
    await wrapper.vm.$nextTick()

    // Verify gitConfig was updated from response
    expect(wrapper.vm.gitConfig.max_commits).toBe(75)
    expect(wrapper.vm.gitConfig.branch_strategy).toBe('develop')
    expect(wrapper.vm.gitConfig.include_commit_history).toBe(false)
  })
})
