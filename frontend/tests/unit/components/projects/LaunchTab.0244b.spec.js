/**
 * LaunchTab.0244b.spec.js
 *
 * Test suite for Agent Mission Edit Functionality (Handover 0244b)
 * Integration tests for AgentMissionEditModal in LaunchTab
 *
 * Following strict TDD: Write tests FIRST, watch them FAIL, then implement
 *
 * Requirements:
 * 1. Import and register AgentMissionEditModal component
 * 2. Modal opens on Edit button click for non-orchestrator agents
 * 3. Orchestrator shows info message instead of opening modal
 * 4. Mission updates reflect in local agent data
 * 5. WebSocket listener updates agents when missions change
 * 6. Real-time updates across all clients
 */

import { describe, it, expect, beforeEach, vi } from 'vitest'
import { mount } from '@vue/test-utils'
import { createVuetify } from 'vuetify'
import * as components from 'vuetify/components'
import * as directives from 'vuetify/directives'
import { nextTick } from 'vue'
import LaunchTab from '@/components/projects/LaunchTab.vue'

// Create Vuetify instance for testing
const vuetify = createVuetify({
  components,
  directives,
})

// Mock WebSocket composable
let mockWebSocketOn
let mockWebSocketOff
let mockWebSocketEmit

vi.mock('@/composables/useWebSocket', () => ({
  useWebSocket: () => ({
    on: mockWebSocketOn,
    off: mockWebSocketOff,
    emit: mockWebSocketEmit,
  })
}))

// Mock Toast composable
let mockShowToast

vi.mock('@/composables/useToast', () => ({
  useToast: () => ({
    showToast: mockShowToast,
  })
}))

// Mock user store with tenant_key
vi.mock('@/stores/user', () => ({
  useUserStore: vi.fn().mockReturnValue({
    currentUser: {
      tenant_key: 'test-tenant-key-123'
    }
  })
}))

describe('LaunchTab - Agent Mission Edit Integration (0244b)', () => {
  let wrapper

  const mockProject = {
    id: 'project-123',
    name: 'Test Project',
    mission: 'Test project mission',
    description: 'Test project description',
  }

  const mockOrchestrator = {
    id: 'orch-123',
    agent_type: 'orchestrator',
    agent_name: 'Orchestrator',
    mission: 'Orchestrate the project',
    status: 'active',
  }

  const mockAgent = {
    id: 'agent-456',
    agent_type: 'implementor',
    agent_name: 'Implementor Agent',
    mission: 'Original implementation mission',
    status: 'pending',
  }

  beforeEach(() => {
    // Reset mocks before each test
    mockWebSocketOn = vi.fn()
    mockWebSocketOff = vi.fn()
    mockWebSocketEmit = vi.fn()
    mockShowToast = vi.fn()
  })

  describe('Component Integration', () => {
    it('should import and register AgentMissionEditModal component', async () => {
      wrapper = mount(LaunchTab, {
        props: {
          project: mockProject,
          orchestrator: mockOrchestrator,
          isStaging: false,
        },
        global: {
          plugins: [vuetify],
        },
      })

      // Check that the component imports exist
      expect(wrapper.vm).toBeDefined()
      expect(wrapper.findComponent({ name: 'AgentMissionEditModal' })).toBeDefined()
    })

    it('should have showMissionEditModal and selectedAgentForEdit state', async () => {
      wrapper = mount(LaunchTab, {
        props: {
          project: mockProject,
          orchestrator: mockOrchestrator,
          isStaging: false,
        },
        global: {
          plugins: [vuetify],
        },
      })

      // Access component instance to check reactive state
      expect(wrapper.vm.showMissionEditModal).toBeDefined()
      expect(wrapper.vm.selectedAgentForEdit).toBeDefined()
      expect(wrapper.vm.showMissionEditModal).toBe(false)
      expect(wrapper.vm.selectedAgentForEdit).toBeNull()
    })
  })

  describe('handleAgentEdit Function', () => {
    it('should open modal for non-orchestrator agents', async () => {
      wrapper = mount(LaunchTab, {
        props: {
          project: mockProject,
          orchestrator: mockOrchestrator,
          isStaging: false,
        },
        global: {
          plugins: [vuetify],
        },
      })

      // Call handleAgentEdit with non-orchestrator agent
      wrapper.vm.handleAgentEdit(mockAgent)
      await nextTick()

      // Modal should be visible
      expect(wrapper.vm.showMissionEditModal).toBe(true)
      expect(wrapper.vm.selectedAgentForEdit).toEqual(mockAgent)
    })

    it('should show info toast for orchestrator and not open modal', async () => {
      wrapper = mount(LaunchTab, {
        props: {
          project: mockProject,
          orchestrator: mockOrchestrator,
          isStaging: false,
        },
        global: {
          plugins: [vuetify],
        },
      })

      // Call handleAgentEdit with orchestrator
      wrapper.vm.handleAgentEdit(mockOrchestrator)
      await nextTick()

      // Modal should NOT be visible
      expect(wrapper.vm.showMissionEditModal).toBe(false)

      // Toast notification should be shown
      expect(mockShowToast).toHaveBeenCalledWith({
        message: 'Orchestrator configuration cannot be edited here',
        type: 'info',
        timeout: 3000,
      })
    })
  })

  describe('handleMissionUpdated Function', () => {
    it('should update local agent data when mission is updated', async () => {
      wrapper = mount(LaunchTab, {
        props: {
          project: {
            ...mockProject,
            agents: [mockAgent],
          },
          orchestrator: mockOrchestrator,
          isStaging: false,
        },
        global: {
          plugins: [vuetify],
        },
      })

      await nextTick()

      // Verify agent is loaded
      expect(wrapper.vm.agents).toHaveLength(1)
      expect(wrapper.vm.agents[0].mission).toBe('Original implementation mission')

      // Call handleMissionUpdated with new mission
      const updatedMission = 'Updated mission text'
      wrapper.vm.handleMissionUpdated({
        jobId: 'agent-456',
        mission: updatedMission,
      })
      await nextTick()

      // Verify agent mission was updated
      expect(wrapper.vm.agents[0].mission).toBe(updatedMission)

      // Verify success toast was shown
      expect(mockShowToast).toHaveBeenCalledWith({
        message: 'Agent mission updated successfully',
        type: 'success',
        timeout: 3000,
      })
    })

    it('should handle mission update for non-existent agent gracefully', async () => {
      wrapper = mount(LaunchTab, {
        props: {
          project: mockProject,
          orchestrator: mockOrchestrator,
          isStaging: false,
        },
        global: {
          plugins: [vuetify],
        },
      })

      // Call with non-existent job ID
      wrapper.vm.handleMissionUpdated({
        jobId: 'non-existent-id',
        mission: 'Some mission',
      })
      await nextTick()

      // Should not crash and still show toast
      expect(mockShowToast).toHaveBeenCalledWith({
        message: 'Agent mission updated successfully',
        type: 'success',
        timeout: 3000,
      })
    })
  })

  describe('WebSocket Integration', () => {
    it('should register agent:mission_updated WebSocket listener on mount', async () => {
      wrapper = mount(LaunchTab, {
        props: {
          project: mockProject,
          orchestrator: mockOrchestrator,
          isStaging: false,
        },
        global: {
          plugins: [vuetify],
        },
      })

      await nextTick()

      // Verify WebSocket listener was registered
      expect(mockWebSocketOn).toHaveBeenCalled()
      const calls = mockWebSocketOn.mock.calls
      const missionUpdateCall = calls.find(call => call[0] === 'agent:mission_updated')
      expect(missionUpdateCall).toBeDefined()
      expect(typeof missionUpdateCall[1]).toBe('function')
    })

    it('should unregister agent:mission_updated WebSocket listener on unmount', async () => {
      wrapper = mount(LaunchTab, {
        props: {
          project: mockProject,
          orchestrator: mockOrchestrator,
          isStaging: false,
        },
        global: {
          plugins: [vuetify],
        },
      })

      await nextTick()

      // Unmount component
      wrapper.unmount()

      // Verify WebSocket listener was unregistered
      expect(mockWebSocketOff).toHaveBeenCalled()
      const calls = mockWebSocketOff.mock.calls
      const missionUpdateCall = calls.find(call => call[0] === 'agent:mission_updated')
      expect(missionUpdateCall).toBeDefined()
    })

    it('should update agent mission when WebSocket event is received', async () => {
      wrapper = mount(LaunchTab, {
        props: {
          project: {
            ...mockProject,
            agents: [mockAgent],
          },
          orchestrator: mockOrchestrator,
          isStaging: false,
        },
        global: {
          plugins: [vuetify],
        },
      })

      await nextTick()

      // Get the WebSocket handler
      const calls = mockWebSocketOn.mock.calls
      const missionUpdateCall = calls.find(call => call[0] === 'agent:mission_updated')
      const handler = missionUpdateCall[1]

      // Simulate WebSocket event
      const websocketData = {
        job_id: 'agent-456',
        agent_name: 'Implementor Agent',
        mission: 'WebSocket updated mission',
        project_id: 'project-123',
      }

      handler(websocketData)
      await nextTick()

      // Verify agent mission was updated
      expect(wrapper.vm.agents[0].mission).toBe('WebSocket updated mission')

      // Verify toast notification was shown (modal is closed)
      expect(mockShowToast).toHaveBeenCalledWith({
        message: 'Mission updated for Implementor Agent',
        type: 'info',
        timeout: 3000,
      })
    })

    it('should not show toast when modal is open (own edit)', async () => {
      wrapper = mount(LaunchTab, {
        props: {
          project: {
            ...mockProject,
            agents: [mockAgent],
          },
          orchestrator: mockOrchestrator,
          isStaging: false,
        },
        global: {
          plugins: [vuetify],
        },
      })

      await nextTick()

      // Open modal
      wrapper.vm.showMissionEditModal = true
      await nextTick()

      // Get the WebSocket handler
      const calls = mockWebSocketOn.mock.calls
      const missionUpdateCall = calls.find(call => call[0] === 'agent:mission_updated')
      const handler = missionUpdateCall[1]

      // Clear previous toast calls
      mockShowToast.mockClear()

      // Simulate WebSocket event
      const websocketData = {
        job_id: 'agent-456',
        agent_name: 'Implementor Agent',
        mission: 'WebSocket updated mission',
        project_id: 'project-123',
      }

      handler(websocketData)
      await nextTick()

      // Verify agent mission was updated
      expect(wrapper.vm.agents[0].mission).toBe('WebSocket updated mission')

      // Verify toast notification was NOT shown (modal is open = own edit)
      expect(mockShowToast).not.toHaveBeenCalled()
    })

    it('should handle WebSocket event for non-existent agent gracefully', async () => {
      wrapper = mount(LaunchTab, {
        props: {
          project: mockProject,
          orchestrator: mockOrchestrator,
          isStaging: false,
        },
        global: {
          plugins: [vuetify],
        },
      })

      await nextTick()

      // Get the WebSocket handler
      const calls = mockWebSocketOn.mock.calls
      const missionUpdateCall = calls.find(call => call[0] === 'agent:mission_updated')
      const handler = missionUpdateCall[1]

      // Simulate WebSocket event for non-existent agent
      const websocketData = {
        job_id: 'non-existent-id',
        agent_name: 'Ghost Agent',
        mission: 'Some mission',
        project_id: 'project-123',
      }

      // Should not crash
      expect(() => {
        handler(websocketData)
      }).not.toThrow()
    })
  })

  describe('Template Integration', () => {
    it('should render AgentMissionEditModal in template', async () => {
      wrapper = mount(LaunchTab, {
        props: {
          project: mockProject,
          orchestrator: mockOrchestrator,
          isStaging: false,
        },
        global: {
          plugins: [vuetify],
          stubs: {
            AgentMissionEditModal: {
              template: '<div class="agent-mission-edit-modal-stub"></div>',
              props: ['modelValue', 'agent'],
            },
          },
        },
      })

      // Check that modal stub is rendered
      expect(wrapper.find('.agent-mission-edit-modal-stub').exists()).toBe(true)
    })

    it('should pass correct props to AgentMissionEditModal', async () => {
      wrapper = mount(LaunchTab, {
        props: {
          project: mockProject,
          orchestrator: mockOrchestrator,
          isStaging: false,
        },
        global: {
          plugins: [vuetify],
        },
      })

      // Open modal
      wrapper.vm.handleAgentEdit(mockAgent)
      await nextTick()

      // Find modal component
      const modal = wrapper.findComponent({ name: 'AgentMissionEditModal' })

      // Check props
      expect(modal.props('modelValue')).toBe(true)
      expect(modal.props('agent')).toEqual(mockAgent)
    })

    it('should handle mission-updated event from modal', async () => {
      wrapper = mount(LaunchTab, {
        props: {
          project: {
            ...mockProject,
            agents: [mockAgent],
          },
          orchestrator: mockOrchestrator,
          isStaging: false,
        },
        global: {
          plugins: [vuetify],
        },
      })

      await nextTick()

      // Open modal
      wrapper.vm.handleAgentEdit(mockAgent)
      await nextTick()

      // Find modal and emit event
      const modal = wrapper.findComponent({ name: 'AgentMissionEditModal' })
      modal.vm.$emit('mission-updated', {
        jobId: 'agent-456',
        mission: 'Updated via modal',
      })
      await nextTick()

      // Verify mission was updated
      expect(wrapper.vm.agents[0].mission).toBe('Updated via modal')
    })
  })
})
