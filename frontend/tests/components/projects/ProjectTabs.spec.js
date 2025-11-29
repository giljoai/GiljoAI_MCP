/**
 * ProjectTabs Component Tests
 * Testing button relocation from LaunchTab to tab header level
 */

import { describe, it, expect, beforeEach, vi } from 'vitest'
import { mount } from '@vue/test-utils'
import { createPinia, setActivePinia } from 'pinia'
import ProjectTabs from '@/components/projects/ProjectTabs.vue'
import { useProjectTabsStore } from '@/stores/projectTabs'

// Mock Vue Router (Composition API)
const mockRoute = {
  query: {},
  hash: ''
}

const mockRouter = {
  replace: vi.fn()
}

vi.mock('vue-router', () => ({
  useRoute: () => mockRoute,
  useRouter: () => mockRouter
}))

// Mock WebSocket composable
vi.mock('@/composables/useWebSocket', () => ({
  useWebSocket: () => ({
    on: vi.fn(),
    off: vi.fn(),
    emit: vi.fn()
  })
}))

// Mock API
vi.mock('@/services/api', () => ({
  default: {
    prompts: {
      staging: vi.fn().mockResolvedValue({
        data: {
          prompt: 'Test staging prompt',
          estimated_prompt_tokens: 100
        }
      })
    }
  }
}))

// Mock child components to isolate ProjectTabs testing
vi.mock('@/components/projects/LaunchTab.vue', () => ({
  default: {
    name: 'LaunchTab',
    template: '<div class="launch-tab-mock">LaunchTab</div>',
    props: ['project', 'orchestrator', 'isStaging', 'readonly']
  }
}))

vi.mock('@/components/projects/JobsTab.vue', () => ({
  default: {
    name: 'JobsTab',
    template: '<div class="jobs-tab-mock">JobsTab</div>',
    props: ['project', 'agents', 'messages', 'allAgentsComplete', 'readonly']
  }
}))

describe('ProjectTabs - Action Buttons in Header', () => {
  let wrapper
  let store

  const mockProject = {
    id: 'project-123',
    project_id: 'project-123',
    name: 'Test Project',
    description: 'Test description',
    status: 'active',
    mission: '',
    agents: []
  }

  beforeEach(() => {
    setActivePinia(createPinia())
    store = useProjectTabsStore()

    // Reset router mocks
    mockRoute.query = {}
    mockRoute.hash = ''
    mockRouter.replace.mockClear()

    wrapper = mount(ProjectTabs, {
      props: {
        project: mockProject,
        orchestrator: null,
        readonly: false
      },
      global: {
        stubs: {
          VCard: true,
          VTabs: true,
          VTab: true,
          VWindow: true,
          VWindowItem: true,
          VBtn: true,
          VIcon: true,
          VBadge: true,
          VSnackbar: true,
          LaunchTab: true,
          JobsTab: true
        }
      }
    })
  })

  // ==================== LAYOUT TESTS ====================

  describe('Button Layout', () => {
    it('renders action buttons at tab header level', () => {
      // Buttons should be in the tabs-header container
      const header = wrapper.find('.tabs-header')
      expect(header.exists()).toBe(true)

      // Should contain action buttons container
      const actionButtons = header.find('.action-buttons')
      expect(actionButtons.exists()).toBe(true)
    })

    it('positions action buttons on the right side of tab headers', () => {
      const header = wrapper.find('.tabs-header')
      const actionButtons = header.find('.action-buttons')

      // Check for right alignment class/style
      expect(actionButtons.classes()).toContain('ml-auto')
    })

    it('displays Stage Project button', () => {
      const stageButton = wrapper.find('.stage-button')
      expect(stageButton.exists()).toBe(true)
      expect(stageButton.text()).toContain('Stage project')
    })

    it('displays "Waiting:" status text', () => {
      const statusText = wrapper.find('.status-text')
      expect(statusText.exists()).toBe(true)
      expect(statusText.text()).toBe('Waiting:')
    })

    it('displays Launch Jobs button', () => {
      const launchButton = wrapper.find('.launch-button')
      expect(launchButton.exists()).toBe(true)
      expect(launchButton.text()).toContain('Launch jobs')
    })

    it('maintains horizontal alignment of buttons and tabs', () => {
      const header = wrapper.find('.tabs-header')

      // Header should use flexbox for horizontal alignment
      const styles = window.getComputedStyle(header.element)
      expect(styles.display).toBe('flex')
      expect(styles.alignItems).toBe('center')
    })
  })

  // ==================== BUTTON STATE TESTS ====================

  describe('Stage Project Button', () => {
    it('is enabled by default', () => {
      const stageButton = wrapper.find('.stage-button')
      expect(stageButton.attributes('disabled')).toBeUndefined()
    })

    it('shows loading state when staging', async () => {
      store.isStaging = true
      await wrapper.vm.$nextTick()

      const stageButton = wrapper.find('.stage-button')
      expect(stageButton.attributes('loading')).toBe('true')
    })

    it('emits stage-project event when clicked', async () => {
      const stageButton = wrapper.find('.stage-button')
      await stageButton.trigger('click')

      expect(wrapper.emitted('stage-project')).toBeTruthy()
    })

    it('calls store.stageProject when clicked', async () => {
      const stageProjectSpy = vi.spyOn(store, 'stageProject').mockResolvedValue({})

      const stageButton = wrapper.find('.stage-button')
      await stageButton.trigger('click')

      expect(stageProjectSpy).toHaveBeenCalled()
    })

    // ==================== NEW: FIX FOR ORCHESTRATOR WAITING STATE ====================

    it('remains enabled when orchestrator exists with status="waiting"', async () => {
      // Orchestrator just created but hasn't started staging yet
      store.agents = [
        { job_id: 'orch-1', agent_type: 'orchestrator', status: 'waiting' }
      ]
      await wrapper.vm.$nextTick()

      const stageButton = wrapper.find('.stage-button')
      // Button should be enabled - allow retry if user didn't paste prompt
      expect(stageButton.attributes('disabled')).toBeUndefined()
      expect(stageButton.text()).toContain('Stage project')
    })

    it('disables when orchestrator status is "working"', async () => {
      // Orchestrator is actively executing staging workflow
      store.agents = [
        { job_id: 'orch-1', agent_type: 'orchestrator', status: 'working' }
      ]
      await wrapper.vm.$nextTick()

      const stageButton = wrapper.find('.stage-button')
      // Vuetify returns disabled="" as empty string
      expect(stageButton.attributes('disabled')).toBeDefined()
      expect(stageButton.text()).toContain('Orchestrator Active')
    })

    it('disables when orchestrator has spawned specialist agents', async () => {
      // Staging complete: orchestrator spawned implementer, tester, reviewer
      store.agents = [
        { job_id: 'orch-1', agent_type: 'orchestrator', status: 'waiting' },
        { job_id: 'impl-1', agent_type: 'implementer', status: 'waiting' },
        { job_id: 'test-1', agent_type: 'tester', status: 'waiting' }
      ]
      await wrapper.vm.$nextTick()

      const stageButton = wrapper.find('.stage-button')
      // Staging is complete - agents spawned
      expect(stageButton.attributes('disabled')).toBeDefined()
      expect(stageButton.text()).toContain('Orchestrator Active')
    })

    it('shows "Orchestrator Active" text when spawned agents exist', async () => {
      store.agents = [
        { job_id: 'orch-1', agent_type: 'orchestrator', status: 'waiting' },
        { job_id: 'impl-1', agent_type: 'implementer', status: 'waiting' }
      ]
      await wrapper.vm.$nextTick()

      const stageButton = wrapper.find('.stage-button')
      expect(stageButton.text()).toContain('Orchestrator Active')
    })

    it('allows retry when orchestrator exists but no agents spawned yet', async () => {
      // User clicked "Stage Project" but forgot to paste prompt
      // Only orchestrator exists (status='waiting'), no specialist agents yet
      store.agents = [
        { job_id: 'orch-1', agent_type: 'orchestrator', status: 'waiting' }
      ]
      await wrapper.vm.$nextTick()

      const stageButton = wrapper.find('.stage-button')
      // Should allow user to click again to retry
      expect(stageButton.attributes('disabled')).toBeUndefined()
      expect(stageButton.text()).toContain('Stage project')
    })
  })

  describe('Launch Jobs Button', () => {
    it('is disabled when project not ready to launch', () => {
      store.orchestratorMission = ''
      store.agents = []

      const launchButton = wrapper.find('.launch-button')
      expect(launchButton.attributes('disabled')).toBe('true')
    })

    it('is enabled when project ready to launch', async () => {
      store.orchestratorMission = 'Test mission'
      store.agents = [{ job_id: 'agent-1', agent_type: 'implementor' }]
      store.isStaging = false
      await wrapper.vm.$nextTick()

      const launchButton = wrapper.find('.launch-button')
      expect(launchButton.attributes('disabled')).toBeUndefined()
    })

    it('emits launch-jobs event when clicked', async () => {
      store.orchestratorMission = 'Test mission'
      store.agents = [{ job_id: 'agent-1', agent_type: 'implementor' }]
      store.isStaging = false
      await wrapper.vm.$nextTick()

      const launchButton = wrapper.find('.launch-button')
      await launchButton.trigger('click')

      expect(wrapper.emitted('launch-jobs')).toBeTruthy()
    })

    it('calls store.launchJobs when clicked', async () => {
      store.orchestratorMission = 'Test mission'
      store.agents = [{ job_id: 'agent-1', agent_type: 'implementor' }]
      store.isStaging = false

      const launchJobsSpy = vi.spyOn(store, 'launchJobs').mockResolvedValue({})

      const launchButton = wrapper.find('.launch-button')
      await launchButton.trigger('click')

      expect(launchJobsSpy).toHaveBeenCalled()
    })

    it('switches to jobs tab after successful launch', async () => {
      store.orchestratorMission = 'Test mission'
      store.agents = [{ job_id: 'agent-1', agent_type: 'implementor' }]
      store.isStaging = false

      vi.spyOn(store, 'launchJobs').mockResolvedValue({})

      const launchButton = wrapper.find('.launch-button')
      await launchButton.trigger('click')
      await wrapper.vm.$nextTick()

      expect(wrapper.vm.activeTab).toBe('jobs')
    })
  })

  // ==================== STYLING TESTS ====================

  describe('Button Styling', () => {
    it('Stage button has yellow-darken-2 color', () => {
      const stageButton = wrapper.find('.stage-button')
      expect(stageButton.attributes('color')).toBe('yellow-darken-2')
    })

    it('Stage button has outlined variant', () => {
      const stageButton = wrapper.find('.stage-button')
      expect(stageButton.attributes('variant')).toBe('outlined')
    })

    it('Stage button is rounded', () => {
      const stageButton = wrapper.find('.stage-button')
      expect(stageButton.attributes('rounded')).toBe('true')
    })

    it('Launch button has yellow-darken-2 color when enabled', async () => {
      store.orchestratorMission = 'Test mission'
      store.agents = [{ job_id: 'agent-1', agent_type: 'implementor' }]
      store.isStaging = false
      await wrapper.vm.$nextTick()

      const launchButton = wrapper.find('.launch-button')
      expect(launchButton.attributes('color')).toBe('yellow-darken-2')
    })

    it('Launch button has grey color when disabled', () => {
      store.orchestratorMission = ''
      store.agents = []

      const launchButton = wrapper.find('.launch-button')
      expect(launchButton.attributes('color')).toBe('grey')
    })

    it('Status text has correct styling', () => {
      const statusText = wrapper.find('.status-text')
      expect(statusText.classes()).toContain('status-text')
    })
  })

  // ==================== PROP PASSING TESTS ====================

  describe('LaunchTab Integration', () => {
    it('no longer passes button-related props to LaunchTab', () => {
      const launchTab = wrapper.findComponent({ name: 'LaunchTab' })

      // LaunchTab should not receive is-staging prop anymore
      // (buttons are in ProjectTabs now)
      expect(launchTab.props()).toBeDefined()
    })

    it('still passes essential props to LaunchTab', () => {
      const launchTab = wrapper.findComponent({ name: 'LaunchTab' })

      expect(launchTab.props('project')).toEqual(mockProject)
      expect(launchTab.props('readonly')).toBe(false)
    })

    it('still emits edit events from LaunchTab', async () => {
      const launchTab = wrapper.findComponent({ name: 'LaunchTab' })

      launchTab.vm.$emit('edit-description')
      await wrapper.vm.$nextTick()

      expect(wrapper.emitted('edit-description')).toBeTruthy()
    })
  })

  // ==================== RESPONSIVE TESTS ====================

  describe('Responsive Design', () => {
    it('buttons remain visible on mobile breakpoint', () => {
      // Simulate mobile viewport
      global.innerWidth = 600

      const actionButtons = wrapper.find('.action-buttons')
      expect(actionButtons.exists()).toBe(true)
    })

    it('maintains proper spacing between elements', () => {
      const actionButtons = wrapper.find('.action-buttons')
      expect(actionButtons.classes()).toContain('d-flex')
      expect(actionButtons.classes()).toContain('gap-2')
    })
  })

  // ==================== ACCESSIBILITY TESTS ====================

  describe('Accessibility', () => {
    it('Stage button has proper ARIA attributes', () => {
      const stageButton = wrapper.find('.stage-button')
      expect(stageButton.attributes('role')).toBeDefined()
    })

    it('Launch button indicates disabled state to screen readers', () => {
      store.orchestratorMission = ''
      store.agents = []

      const launchButton = wrapper.find('.launch-button')
      expect(launchButton.attributes('aria-disabled')).toBe('true')
    })

    it('buttons are keyboard accessible', async () => {
      const stageButton = wrapper.find('.stage-button')
      await stageButton.trigger('keydown.enter')

      expect(wrapper.emitted('stage-project')).toBeTruthy()
    })
  })

  // ==================== ERROR HANDLING TESTS ====================

  describe('Error Handling', () => {
    it('displays error when stage fails', async () => {
      const error = new Error('Staging failed')
      vi.spyOn(store, 'stageProject').mockRejectedValue(error)

      const stageButton = wrapper.find('.stage-button')
      await stageButton.trigger('click')
      await wrapper.vm.$nextTick()

      // Should show error message
      expect(wrapper.vm.errorVisible).toBe(true)
    })

    it('displays error when launch fails', async () => {
      store.orchestratorMission = 'Test mission'
      store.agents = [{ job_id: 'agent-1', agent_type: 'implementor' }]

      const error = new Error('Launch failed')
      vi.spyOn(store, 'launchJobs').mockRejectedValue(error)

      const launchButton = wrapper.find('.launch-button')
      await launchButton.trigger('click')
      await wrapper.vm.$nextTick()

      expect(wrapper.vm.errorVisible).toBe(true)
    })
  })

  // ==================== HANDOVER 0251 PHASE 2: BUTTON RENAMING TESTS ====================

  describe('Copy Orchestrator Prompt Button (Handover 0253)', () => {
    it('should display "Stage project" with copy icon', () => {
      // BEHAVIOR: Button text should remain "Stage project" but have copy icon (Handover 0253)
      const stageButton = wrapper.find('.stage-button')
      expect(stageButton.text()).toContain('Stage project')
    })

    it('should have mdi-content-copy prepend icon', () => {
      // BEHAVIOR: Button should have prepend-icon="mdi-content-copy"
      // Expected to FAIL initially (RED phase)
      const stageButton = wrapper.find('.stage-button')
      expect(stageButton.attributes('prepend-icon')).toBe('mdi-content-copy')
    })

    it('should show universal toast message when prompt copied', async () => {
      // BEHAVIOR: Toast message should say "Orchestrator prompt copied - paste into ANY terminal"
      // Expected to FAIL initially (RED phase)
      const stageButton = wrapper.find('.stage-button')
      await stageButton.trigger('click')
      await wrapper.vm.$nextTick()

      expect(wrapper.vm.toastMessage).toBe('Orchestrator prompt copied - paste into ANY terminal (fresh or existing)')
    })
  })
})
