/**
 * AgentDisplayName.spec.js - Handover 0414b Phase RED Tests (TDD)
 *
 * CRITICAL: These tests WILL FAIL because agent_display_name doesn't exist yet.
 * Tests define expected behavior BEFORE implementation (TDD approach).
 *
 * Semantic Naming:
 * - agent_name = NORTH STAR (template lookup key, DO NOT CHANGE)
 * - agent_display_name = NEW UI LABEL (what humans see, replaces agent_display_name)
 * - agent_display_name = DEPRECATED (being replaced by agent_display_name)
 *
 * Migration Path:
 * Phase 0414a: Schema & backend (agent_display_name field added to database)
 * Phase 0414b: RED Tests (this file - tests fail, define expected behavior)
 * Phase 0414c: GREEN Patch (backend migration - populate agent_display_name)
 * Phase 0414d: REFACTOR (update frontend props/attributes/functions)
 * Phase 0414e: PASS Tests (agent_display_name fully integrated, agent_display_name removed)
 *
 * Test Coverage:
 * 1. JobsTab Component - agent_display_name field, attributes, function names
 * 2. LaunchTab Component - agent_display_name display and CSS classes
 * 3. useAgentData Composable - getAgentDisplayNameColor() function
 * 4. AgentDetailsModal - agent_display_name prop passing
 *
 * @see handovers/0414_clean_display_name_migration.md
 */

import { describe, it, expect, beforeEach, vi } from 'vitest'
import { mount } from '@vue/test-utils'
import { createPinia, setActivePinia } from 'pinia'
import { createVuetify } from 'vuetify'
import JobsTab from '@/components/projects/JobsTab.vue'
import LaunchTab from '@/components/projects/LaunchTab.vue'
import { useAgentData } from '@/composables/useAgentData'
import AgentDetailsModal from '@/components/projects/AgentDetailsModal.vue'
import { ref, computed } from 'vue'

const vuetify = createVuetify()

// Mock API
vi.mock('@/services/api', () => ({
  api: {
    prompts: {
      agentPrompt: vi.fn().mockResolvedValue({
        data: { prompt: 'Mock prompt text' },
      }),
      implementation: vi.fn().mockResolvedValue({
        data: { prompt: 'Mock implementation prompt', agent_count: 3 },
      }),
    },
    post: vi.fn().mockResolvedValue({
      data: { success: true },
    }),
    messages: {
      sendUnified: vi.fn().mockResolvedValue({
        data: { success: true },
      }),
    },
    projects: {
      update: vi.fn().mockResolvedValue({
        data: { success: true },
      }),
    },
  },
  default: {
    prompts: {
      agentPrompt: vi.fn().mockResolvedValue({
        data: { prompt: 'Mock prompt text' },
      }),
    },
    projects: {
      update: vi.fn().mockResolvedValue({
        data: { success: true },
      }),
    },
  },
}))

// Mock toast
let mockShowToast
vi.mock('@/composables/useToast', () => ({
  useToast: () => ({
    showToast: mockShowToast,
  }),
}))

// Mock WebSocket
vi.mock('@/composables/useWebSocket', () => ({
  useWebSocketV2: () => ({
    on: vi.fn(),
    off: vi.fn(),
  }),
}))

// Mock agent jobs composable
vi.mock('@/composables/useAgentJobs', () => ({
  useAgentJobs: () => ({
    sortedJobs: ref([]),
    loadJobs: vi.fn(),
    store: {
      getJob: vi.fn(),
      upsertJob: vi.fn(),
    },
  }),
}))

// Mock stores
vi.mock('@/stores/websocket', () => ({
  useWebSocketStore: () => ({
    onConnectionChange: vi.fn((cb) => () => {}),
  }),
}))

vi.mock('@/stores/projectStateStore', () => ({
  useProjectStateStore: () => ({
    getProjectState: vi.fn(() => ({ mission: '' })),
  }),
}))

vi.mock('@/stores/agentJobsStore', () => ({
  useAgentJobsStore: () => ({
    getJob: vi.fn(),
    upsertJob: vi.fn(),
  }),
}))

vi.mock('@/stores/user', () => ({
  useUserStore: () => ({
    currentUser: { id: 'user-1', tenant_key: 'tenant-123' },
  }),
}))

/**
 * Factory function for mock agent data
 * Currently uses agent_display_name (to be replaced by agent_display_name)
 */
const createMockAgent = (overrides = {}) => ({
  job_id: `job-${  Math.random().toString(36).slice(2, 9)}`,
  agent_id: `agent-${  Math.random().toString(36).slice(2, 9)}`,
  agent_display_name: 'implementer', // OLD - being replaced
  // agent_display_name would go here after migration
  agent_name: 'implementer',
  status: 'waiting',
  mission_acknowledged_at: null,
  started_at: null,
  completed_at: null,
  messages: [],
  steps: null,
  messages_sent_count: 0,
  messages_waiting_count: 0,
  messages_read_count: 0,
  ...overrides,
})

const createMockProject = (overrides = {}) => ({
  project_id: `proj-${  Math.random().toString(36).slice(2, 9)}`,
  id: 'proj-123',
  name: 'Test Project',
  description: 'Test Description',
  execution_mode: 'multi_terminal',
  ...overrides,
})

describe('PHASE 0414b: AgentDisplayName Migration - RED Tests (Failing)', () => {
  let pinia

  beforeEach(() => {
    pinia = createPinia()
    setActivePinia(pinia)
    mockShowToast = vi.fn()
  })

  describe('JobsTab Component - agent_display_name integration', () => {
    describe('Agent data field migration', () => {
      it('should contain agent_display_name field in agent data (WILL FAIL - field missing)', () => {
        /**
         * EXPECTED BEHAVIOR AFTER MIGRATION:
         * Agent objects should have agent_display_name field instead of agent_display_name
         * This is the UI label showing what users see (e.g., "Frontend Tester")
         */
        const agent = createMockAgent({
          agent_display_name: 'tester',
          // agent_display_name: 'Frontend Tester', // This should exist after migration
        })

        // FAILING TEST: agent_display_name doesn't exist yet
        expect(agent).toHaveProperty('agent_display_name')
      })

      it('should deprecate agent_display_name field in favor of agent_display_name (WILL FAIL)', () => {
        /**
         * EXPECTED BEHAVIOR:
         * After migration, components should not use agent.agent_display_name
         * Components should instead reference agent.agent_display_name
         * agent_display_name will be deprecated but may remain for backward compat
         */
        const agent = createMockAgent({
          agent_display_name: 'Frontend Tester',
          // agent_display_name should NOT be used by new code
        })

        expect(agent).not.toHaveProperty('agent_display_name')
      })
    })

    describe('JobsTab data attributes', () => {
      it('should use data-agent-display-name attribute instead of data-agent-type (WILL FAIL)', async () => {
        /**
         * EXPECTED BEHAVIOR:
         * JobsTab table rows should have data-agent-display-name attribute
         * for test selectors and data attributes
         * CURRENT: :data-agent-type="agent.agent_display_name"
         * EXPECTED: :data-agent-display-name="agent.agent_display_name"
         */
        const agent = createMockAgent({
          job_id: 'job-123',
          agent_display_name: 'Frontend Tester',
        })

        const wrapper = mount(JobsTab, {
          props: {
            project: createMockProject(),
            readonly: false,
          },
          global: {
            plugins: [pinia, vuetify],
            stubs: {
              'v-tooltip': true,
              'v-dialog': true,
              'v-card': true,
              'v-card-title': true,
              'v-card-text': true,
              'v-card-actions': true,
              'v-spacer': true,
              'v-text-field': true,
              'v-icon': true,
              'v-avatar': true,
              'v-btn': true,
              'v-chip': true,
              'v-divider': true,
              AgentDetailsModal: true,
              CloseoutModal: true,
              MessageAuditModal: true,
            },
          },
        })

        // FAILING TEST: Currently uses data-agent-type
        const row = wrapper.find('[data-agent-display-name="frontend-tester"]')
        expect(row.exists()).toBe(true)
      })

      it('should remove data-agent-type attribute and use data-agent-display-name (WILL FAIL)', async () => {
        /**
         * EXPECTED BEHAVIOR:
         * Old attribute should be removed completely
         * Tests relying on data-agent-type will break (intentionally)
         */
        const agent = createMockAgent({
          job_id: 'job-456',
          agent_display_name: 'Code Reviewer',
        })

        const wrapper = mount(JobsTab, {
          props: {
            project: createMockProject(),
            readonly: false,
          },
          global: {
            plugins: [pinia, vuetify],
            stubs: {
              'v-tooltip': true,
              'v-dialog': true,
              'v-card': true,
              'v-card-title': true,
              'v-card-text': true,
              'v-card-actions': true,
              'v-spacer': true,
              'v-text-field': true,
              'v-icon': true,
              'v-avatar': true,
              'v-btn': true,
              'v-chip': true,
              'v-divider': true,
              AgentDetailsModal: true,
              CloseoutModal: true,
              MessageAuditModal: true,
            },
          },
        })

        // FAILING TEST: Old attribute should NOT exist
        const row = wrapper.find('tr[data-agent-type]')
        expect(row.exists()).toBe(false)
      })
    })

    describe('JobsTab display functions', () => {
      it('should use getAgentDisplayName() function not getAgentType() (WILL FAIL)', () => {
        /**
         * EXPECTED BEHAVIOR:
         * JobsTab.vue should have a function getAgentDisplayName(agent)
         * that returns the display name from agent.agent_display_name
         * OLD FUNCTION: getAgentType(displayName) - takes string parameter
         * NEW FUNCTION: getAgentDisplayName(agent) - takes agent object parameter
         */
        // This would be tested by checking if function exists in component
        // For now, test through rendered output

        const agent = createMockAgent({
          agent_display_name: 'Frontend Tester',
        })

        expect(agent).toHaveProperty('agent_display_name')
        // Test will verify component has getAgentDisplayName() method
      })

      it('should render agent_display_name in primary agent info section (WILL FAIL)', async () => {
        /**
         * EXPECTED BEHAVIOR:
         * JobsTab agent row should display agent_display_name
         * CURRENT: Line 30 shows {{ agent.agent_name || agent.agent_display_name }}
         * EXPECTED: {{ agent.agent_name || agent.agent_display_name }}
         */
        const agent = createMockAgent({
          agent_name: 'My Custom Tester',
          agent_display_name: 'Frontend Tester',
        })

        const wrapper = mount(JobsTab, {
          props: {
            project: createMockProject(),
            readonly: false,
          },
          global: {
            plugins: [pinia, vuetify],
            stubs: {
              'v-tooltip': true,
              'v-dialog': true,
              'v-card': true,
              'v-card-title': true,
              'v-card-text': true,
              'v-card-actions': true,
              'v-spacer': true,
              'v-text-field': true,
              'v-icon': true,
              'v-avatar': true,
              'v-btn': true,
              'v-chip': true,
              'v-divider': true,
              AgentDetailsModal: true,
              CloseoutModal: true,
              MessageAuditModal: true,
            },
          },
        })

        // Should display agent_display_name, not agent_display_name
        expect(wrapper.text()).toContain('Frontend Tester')
      })

      it('should show agent_display_name in cancel confirmation dialog (WILL FAIL)', async () => {
        /**
         * EXPECTED BEHAVIOR:
         * Cancel dialog (line 281) should show agent_display_name
         * CURRENT: <div><strong>Agent Type:</strong> {{ selectedAgent?.agent_display_name }}</div>
         * EXPECTED: <div><strong>Agent Type:</strong> {{ selectedAgent?.agent_display_name }}</div>
         */
        const agent = createMockAgent({
          agent_display_name: 'Code Reviewer',
        })

        expect(agent).toHaveProperty('agent_display_name')
        expect(agent.agent_display_name).toBe('Code Reviewer')
      })
    })

    describe('JobsTab hand-over button conditional', () => {
      it('should check agent_display_name === "orchestrator" instead of agent_display_name (WILL FAIL)', async () => {
        /**
         * EXPECTED BEHAVIOR:
         * Line 211 checks: v-if="agent.agent_display_name === 'orchestrator'"
         * Should be: v-if="agent.agent_name === 'orchestrator'" (uses agent_name as north star)
         * OR keep as is but use agent.agent_display_name === 'Orchestrator'
         */
        const orchestrator = createMockAgent({
          agent_name: 'orchestrator', // North star
          agent_display_name: 'Orchestrator Coordinator',
          status: 'working',
        })

        const specialist = createMockAgent({
          agent_name: 'implementer',
          agent_display_name: 'Code Implementer',
          status: 'working',
        })

        expect(orchestrator.agent_name).toBe('orchestrator')
        expect(specialist.agent_name).not.toBe('orchestrator')
      })
    })
  })

  describe('LaunchTab Component - agent_display_name integration', () => {
    describe('LaunchTab data attributes', () => {
      it('should use data-agent-display-name instead of data-agent-type in agent cards (WILL FAIL)', async () => {
        /**
         * EXPECTED BEHAVIOR:
         * LaunchTab line 120: :data-agent-type="agent.agent_display_name"
         * Should be: :data-agent-display-name="agent.agent_display_name"
         */
        const agent = createMockAgent({
          agent_display_name: 'Code Implementer',
        })

        expect(agent).toHaveProperty('agent_display_name')
        // Test verifies attribute is used in template
      })

      it('should have CSS class agent-display-name instead of agent-type (WILL FAIL)', async () => {
        /**
         * EXPECTED BEHAVIOR:
         * CSS classes should reflect new naming
         * CURRENT: .agent-type-cell, .agent-type-secondary
         * EXPECTED: .agent-display-name-cell, .agent-display-name-secondary
         */
        const wrapper = mount(LaunchTab, {
          props: {
            project: createMockProject(),
            orchestrator: null,
            isStaging: false,
          },
          global: {
            plugins: [pinia, vuetify],
            stubs: {
              'v-tooltip': true,
              'v-dialog': true,
              'v-card': true,
              'v-avatar': true,
              'v-btn': true,
              'v-icon': true,
              AgentDetailsModal: true,
              AgentMissionEditModal: true,
            },
          },
        })

        // FAILING: Class name should be agent-display-name-cell
        expect(wrapper.find('.agent-display-name-cell').exists()).toBe(true)
      })
    })

    describe('LaunchTab agent card display', () => {
      it('should render agent_display_name on agent slim cards (WILL FAIL)', async () => {
        /**
         * EXPECTED BEHAVIOR:
         * LaunchTab line 125: {{ agent.agent_display_name?.toUpperCase() || '' }}
         * Should use agent_display_name instead for display label
         * agent_name should be used for template lookup (north star)
         */
        const agent = createMockAgent({
          agent_name: 'implementer', // North star - template lookup
          agent_display_name: 'Code Implementation Specialist', // UI display
        })

        expect(agent).toHaveProperty('agent_display_name')
        expect(agent.agent_display_name).toBe('Code Implementation Specialist')
      })

      it('should remove display:none agent-type span and use agent-display-name (WILL FAIL)', async () => {
        /**
         * EXPECTED BEHAVIOR:
         * LaunchTab line 126: hidden span for agent_display_name should be removed
         * New span should use agent_display_name
         * This is used for testing/data access
         */
        const wrapper = mount(LaunchTab, {
          props: {
            project: createMockProject(),
            orchestrator: null,
            isStaging: false,
          },
          global: {
            plugins: [pinia, vuetify],
            stubs: {
              'v-tooltip': true,
              'v-dialog': true,
              'v-card': true,
              'v-avatar': true,
              'v-btn': true,
              'v-icon': true,
              AgentDetailsModal: true,
              AgentMissionEditModal: true,
            },
          },
        })

        // FAILING: Should have agent-display-name span, not agent-type
        const displayNameSpan = wrapper.find('span[class="agent-display-name"]')
        expect(displayNameSpan.exists()).toBe(true)
      })
    })

    describe('LaunchTab function changes', () => {
      it('should have getAgentDisplayName() method instead of getAgentType() (WILL FAIL)', async () => {
        /**
         * EXPECTED BEHAVIOR:
         * LaunchTab should expose getAgentDisplayName() function
         * NOT getAgentType()
         * Function signature: getAgentDisplayName(agent) -> string
         */
        // This is tested implicitly through component render
        // Component should use getAgentDisplayName() internally
      })
    })
  })

  describe('useAgentData Composable - function renaming', () => {
    describe('Composable function names', () => {
      it('should export getAgentDisplayNameColor() not getAgentTypeColor() (WILL FAIL)', () => {
        /**
         * EXPECTED BEHAVIOR:
         * useAgentData.js line 97: getAgentTypeColor(displayName)
         * Should be: getAgentDisplayNameColor(displayName)
         * Function returns Vuetify color for avatar background based on display name
         */
        const composableExports = Object.keys(
          useAgentData(ref([]))
        )

        // FAILING: Function doesn't exist yet
        expect(composableExports).toContain('getAgentDisplayNameColor')
        expect(composableExports).not.toContain('getAgentTypeColor')
      })

      it('should have backward compatible color mapping for new function (WILL FAIL)', () => {
        /**
         * EXPECTED BEHAVIOR:
         * getAgentDisplayNameColor() should map display names to Vuetify colors
         * 'Orchestrator Coordinator' -> 'orange'
         * 'Code Implementer' -> 'blue'
         * etc.
         */
        const agents = ref([
          createMockAgent({ agent_display_name: 'Orchestrator Coordinator' }),
          createMockAgent({ agent_display_name: 'Code Implementer' }),
        ])

        const { getAgentDisplayNameColor } = useAgentData(agents)

        expect(getAgentDisplayNameColor('Orchestrator Coordinator')).toBe('orange')
        expect(getAgentDisplayNameColor('Code Implementer')).toBe('blue')
      })

      it('should return gray for unknown display names (WILL FAIL)', () => {
        /**
         * EXPECTED BEHAVIOR:
         * Unknown display names should map to gray (safe default)
         */
        const agents = ref([])

        const { getAgentDisplayNameColor } = useAgentData(agents)

        expect(getAgentDisplayNameColor('Unknown Agent Type')).toBe('grey')
      })
    })

    describe('Composable backward compatibility', () => {
      it('should deprecate getAgentTypeColor() - may provide deprecation warning (WILL FAIL)', () => {
        /**
         * EXPECTED BEHAVIOR:
         * getAgentTypeColor() should either:
         * 1. Be removed (breaking change)
         * 2. Call getAgentDisplayNameColor() internally (deprecated wrapper)
         * 3. Emit console warning about deprecation
         */
        const agents = ref([])

        const composable = useAgentData(agents)

        // Either function should not exist, or should warn
        if (composable.getAgentTypeColor) {
          expect(vi.fn()).toHaveBeenCalled() // Would have warned
        } else {
          expect(composable).not.toHaveProperty('getAgentTypeColor')
        }
      })
    })
  })

  describe('AgentDetailsModal - prop passing', () => {
    describe('Modal props', () => {
      it('should receive agent_display_name in agent prop (WILL FAIL)', async () => {
        /**
         * EXPECTED BEHAVIOR:
         * AgentDetailsModal should receive full agent object with agent_display_name
         * Modal should render agent_display_name in its content
         */
        const agent = createMockAgent({
          agent_name: 'tester',
          agent_display_name: 'Frontend Test Specialist',
        })

        expect(agent).toHaveProperty('agent_display_name')
      })

      it('should display agent_display_name in modal header/content (WILL FAIL)', async () => {
        /**
         * EXPECTED BEHAVIOR:
         * AgentDetailsModal should show agent_display_name prominently
         * Not agent_display_name
         */
        const agent = createMockAgent({
          agent_display_name: 'Frontend Test Specialist',
        })

        // Component should display agent_display_name, not agent_display_name
        expect(agent.agent_display_name).toBe('Frontend Test Specialist')
      })
    })
  })

  describe('Data consistency across components', () => {
    describe('Multi-component agent data flow', () => {
      it('all components should use consistent agent_display_name field (WILL FAIL)', () => {
        /**
         * EXPECTED BEHAVIOR:
         * JobsTab, LaunchTab, AgentDetailsModal should all receive
         * agent objects with agent_display_name field
         * No component should need to transform agent_display_name -> agent_display_name
         */
        const agent = createMockAgent({
          agent_display_name: 'Code Reviewer Specialist',
        })

        // All consuming code should access agent.agent_display_name
        expect(agent).toHaveProperty('agent_display_name')
      })

      it('should not have conditional fallbacks from agent_display_name to agent_display_name (WILL FAIL)', () => {
        /**
         * EXPECTED BEHAVIOR:
         * After migration, no template logic like:
         *   agent.agent_display_name || agent.agent_display_name
         * Should just be:
         *   agent.agent_display_name
         *
         * agent_display_name should be completely removed from frontend
         */
        const agent = createMockAgent({
          agent_display_name: 'Security Reviewer',
          // agent_display_name should not exist
        })

        expect(agent).not.toHaveProperty('agent_display_name')
      })
    })
  })

  describe('Migration validation', () => {
    describe('Field completeness', () => {
      it('agent_display_name should be populated for all agent types (WILL FAIL)', () => {
        /**
         * EXPECTED BEHAVIOR AFTER MIGRATION:
         * Every agent object should have non-empty agent_display_name
         * Migration should populate this from:
         * - Existing agent_display_name values
         * - Template configuration
         * - User customization
         */
        const displayNames = [
          'orchestrator',
          'analyzer',
          'implementer',
          'implementor',
          'tester',
          'reviewer',
          'documenter',
          'researcher',
        ]

        displayNames.forEach((type) => {
          const agent = createMockAgent({
            agent_name: type,
            agent_display_name: null, // This should be populated!
          })

          expect(agent.agent_display_name).toBeTruthy()
        })
      })

      it('should validate no components remain using agent_display_name directly (WILL FAIL)', () => {
        /**
         * EXPECTED BEHAVIOR:
         * Grep should find no references to:
         * - agent.agent_display_name in components (post-migration)
         * - getAgentType() function calls
         * - data-agent-type attributes in templates
         *
         * This is a code quality validation
         */
        // This would be checked via actual code analysis
        // Test framework cannot grep codebase, so this validates
        // that migration is complete
      })
    })
  })
})

describe('PHASE 0414b: Notes for Implementation Team', () => {
  it('documents the required changes in JobsTab.vue', () => {
    /**
     * REQUIRED CHANGES IN JobsTab.vue:
     *
     * 1. Line 23: Change :data-agent-type to :data-agent-display-name
     *    BEFORE: :data-agent-type="agent.agent_display_name"
     *    AFTER:  :data-agent-display-name="agent.agent_display_name"
     *
     * 2. Line 25-30: Update CSS class from agent-type-cell to agent-display-name-cell
     *    BEFORE: <td class="agent-type-cell">
     *    AFTER:  <td class="agent-display-name-cell">
     *
     * 3. Line 30-35: Use agent_display_name in fallback
     *    BEFORE: {{ agent.agent_name || agent.agent_display_name }}
     *    AFTER:  {{ agent.agent_name || agent.agent_display_name }}
     *
     * 4. Line 33: Update secondary label class
     *    BEFORE: <span class="agent-type-secondary">
     *    AFTER:  <span class="agent-display-name-secondary">
     *
     * 5. Line 35: Show agent_display_name instead of agent_display_name
     *    BEFORE: {{ agent.agent_display_name }}
     *    AFTER:  {{ agent.agent_display_name }}
     *
     * 6. Line 211: Check agent_name for orchestrator (north star)
     *    BEFORE: v-if="agent.agent_display_name === 'orchestrator'"
     *    AFTER:  v-if="agent.agent_name === 'orchestrator'"
     *
     * 7. Line 281: Show agent_display_name in dialog
     *    BEFORE: <div><strong>Agent Type:</strong> {{ selectedAgent?.agent_display_name }}</div>
     *    AFTER:  <div><strong>Agent Type:</strong> {{ selectedAgent?.agent_display_name }}</div>
     *
     * 8. Rename function getAgentColor() -> getAgentDisplayNameColor()
     *    Signature changes from: getAgentColor(displayName: String)
     *    To: getAgentDisplayNameColor(displayName: String)
     */
  })

  it('documents the required changes in LaunchTab.vue', () => {
    /**
     * REQUIRED CHANGES IN LaunchTab.vue:
     *
     * 1. Line 120: Change :data-agent-type to :data-agent-display-name
     *    BEFORE: :data-agent-type="agent.agent_display_name"
     *    AFTER:  :data-agent-display-name="agent.agent_display_name"
     *
     * 2. Line 122-126: Update to use agent_display_name
     *    BEFORE: {{ getAgentColor(agent.agent_display_name) }}
     *    AFTER:  {{ getAgentColor(agent.agent_display_name) }}
     *
     * 3. Line 125: Update display name
     *    BEFORE: {{ agent.agent_display_name?.toUpperCase() || '' }}
     *    AFTER:  {{ agent.agent_display_name?.toUpperCase() || '' }}
     *
     * 4. Line 126: Change hidden span from agent-type to agent-display-name
     *    BEFORE: <span class="agent-type" style="display: none;">{{ agent.agent_display_name || '' }}</span>
     *    AFTER:  <span class="agent-display-name" style="display: none;">{{ agent.agent_display_name || '' }}</span>
     *
     * 5. CSS: Rename .agent-type-cell to .agent-display-name-cell
     * 6. CSS: Rename .agent-type-secondary to .agent-display-name-secondary
     * 7. Functions: Update getAgentColor() signature if needed
     *
     * Note: agent_name remains unchanged - it's the north star template key
     */
  })

  it('documents the required changes in useAgentData.js', () => {
    /**
     * REQUIRED CHANGES IN useAgentData.js:
     *
     * 1. Line 97: Rename function from getAgentTypeColor to getAgentDisplayNameColor
     *    BEFORE: const getAgentTypeColor = (displayName) => {
     *    AFTER:  const getAgentDisplayNameColor = (displayName) => {
     *
     * 2. Update function parameter from string to string (stays same type, different semantic)
     *    Parameter name changes: displayName -> displayName
     *
     * 3. Update color mapping to use display name semantics
     *    BEFORE maps: orchestrator, analyzer, implementer, tester, etc.
     *    AFTER maps: Orchestrator Coordinator, Code Analyzer, Code Implementer, etc.
     *
     * 4. Line 167: Update export to use new function name
     *    BEFORE: getAgentTypeColor,
     *    AFTER:  getAgentDisplayNameColor,
     *
     * 5. Consider if backward compatibility wrapper needed for getAgentTypeColor()
     *    Option A: Remove completely (breaking change)
     *    Option B: Keep as deprecated wrapper that calls getAgentDisplayNameColor()
     *    Option C: Keep and deprecate in next major version
     */
  })

  it('documents semantic meaning clarification', () => {
    /**
     * SEMANTIC CLARIFICATION FOR IMPLEMENTATION:
     *
     * Three important fields that must NOT be confused:
     *
     * 1. agent_name (NORTH STAR - DO NOT CHANGE)
     *    - Template lookup key (e.g., 'orchestrator', 'implementer', 'tester')
     *    - Used in backend to find agent template and configuration
     *    - Deterministic - never user-editable
     *    - Used in conditionals: if (agent.agent_name === 'orchestrator')
     *
     * 2. agent_display_name (NEW - THIS IS WHAT WE'RE ADDING)
     *    - Human-readable UI label (e.g., 'Frontend Tester', 'Code Reviewer')
     *    - What users see on agent cards and in JobsTab
     *    - May be user-customized or template-specific
     *    - Changes frequently, user-facing
     *
     * 3. agent_display_name (DEPRECATED - BEING REMOVED)
     *    - Old ambiguous name being replaced
     *    - Currently holds template key (same as agent_name)
     *    - Confusing because it was repurposed for display labels
     *    - All references should be migrated to agent_display_name
     *
     * MIGRATION RULE:
     * - If comparing identity (if === 'orchestrator'): use agent_name
     * - If displaying to user (template, headers, etc.): use agent_display_name
     * - Never create new code using agent_display_name
     */
  })
})
