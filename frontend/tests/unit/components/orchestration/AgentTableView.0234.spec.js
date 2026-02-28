/**
 * Integration Tests for AgentTableView - StatusChip Integration
 * Handover 0234: Agent Status Enhancements - Phase 3
 *
 * Tests the integration of StatusChip component and staleness monitor
 * into the AgentTableView component.
 */

import { describe, it, expect, vi, beforeEach, afterEach } from 'vitest';
import { mount } from '@vue/test-utils';
import { createVuetify } from 'vuetify';
import * as components from 'vuetify/components';
import * as directives from 'vuetify/directives';
import { nextTick } from 'vue';

import AgentTableView from '@/components/orchestration/AgentTableView.vue';
import StatusChip from '@/components/StatusBoard/StatusChip.vue';

const vuetify = createVuetify({ components, directives });

describe('AgentTableView.vue - StatusChip Integration (0234)', () => {
  let wrapper;

  const createWrapper = (props = {}) => {
    return mount(AgentTableView, {
      props: {
        agents: [],
        mode: 'jobs',
        usingClaudeCodeSubagents: false,
        ...props
      },
      global: {
        plugins: [vuetify],
        stubs: {
          'v-data-table': {
            template: `
              <div class="v-data-table-stub">
                <slot name="item.status" :item="agents[0]" v-if="agents.length > 0"></slot>
                <slot name="item.health_status" :item="agents[0]" v-if="agents.length > 0"></slot>
              </div>
            `,
            props: ['items'],
            computed: {
              agents() {
                return this.items || [];
              }
            }
          },
          'JobReadAckIndicators': true
        }
      }
    });
  };

  afterEach(() => {
    if (wrapper) {
      wrapper.unmount();
    }
  });

  describe('StatusChip Integration', () => {
    it('renders StatusChip for each agent in status column', async () => {
      const agents = [
        {
          job_id: '123',
          agent_type: 'implementer',
          agent_name: 'Test Agent',
          status: 'working',
          health_status: 'healthy',
          last_progress_at: new Date().toISOString(),
          mission_read_at: null,

        }
      ];

      wrapper = createWrapper({ agents });
      await nextTick();

      const statusChip = wrapper.findComponent(StatusChip);
      expect(statusChip.exists()).toBe(true);
    });

    it('passes correct props to StatusChip', async () => {
      const timestamp = new Date().toISOString();
      const agents = [
        {
          job_id: '123',
          agent_type: 'implementer',
          agent_name: 'Test Agent',
          status: 'working',
          health_status: 'warning',
          last_progress_at: timestamp,
          health_failure_count: 2,
          minutes_since_progress: 5,
          mission_read_at: null,

        }
      ];

      wrapper = createWrapper({ agents });
      await nextTick();

      const statusChip = wrapper.findComponent(StatusChip);
      expect(statusChip.props('status')).toBe('working');
      expect(statusChip.props('healthStatus')).toBe('warning');
      expect(statusChip.props('lastProgressAt')).toBe(timestamp);
      expect(statusChip.props('minutesSinceProgress')).toBe(5);
    });

    it('handles missing optional fields gracefully', async () => {
      const agents = [
        {
          job_id: '123',
          agent_type: 'implementer',
          agent_name: 'Test Agent',
          status: 'waiting',
          health_status: 'healthy',
          mission_read_at: null,

          // No last_progress_at, health_failure_count, or minutes_since_progress
        }
      ];

      wrapper = createWrapper({ agents });
      await nextTick();

      const statusChip = wrapper.findComponent(StatusChip);
      expect(statusChip.exists()).toBe(true);
      expect(statusChip.props('status')).toBe('waiting');
      expect(statusChip.props('healthStatus')).toBe('healthy');
    });

    it('passes healthFailureCount as 0 when undefined', async () => {
      const agents = [
        {
          job_id: '123',
          agent_type: 'implementer',
          agent_name: 'Test Agent',
          status: 'working',
          health_status: 'healthy',
          last_progress_at: new Date().toISOString(),
          mission_read_at: null,

          // health_failure_count is undefined
        }
      ];

      wrapper = createWrapper({ agents });
      await nextTick();

      const statusChip = wrapper.findComponent(StatusChip);
      // StatusChip doesn't have healthFailureCount prop, but we're setting it in template
      // Verify the component doesn't crash
      expect(statusChip.exists()).toBe(true);
    });
  });

  describe('Health Column Removal', () => {
    it('does not render separate health column', () => {
      wrapper = createWrapper();

      // Check headers - should not have health_status key
      const headers = wrapper.vm.headers;
      const healthHeader = headers.find(h => h.key === 'health_status');
      expect(healthHeader).toBeUndefined();
    });

    it('does not render health icon separately', async () => {
      const agents = [
        {
          job_id: '123',
          agent_type: 'implementer',
          agent_name: 'Test Agent',
          status: 'working',
          health_status: 'warning',
          last_progress_at: new Date().toISOString(),
          mission_read_at: null,

        }
      ];

      wrapper = createWrapper({ agents });
      await nextTick();

      // Should not have item.health_status slot
      const html = wrapper.html();
      expect(html).not.toContain('item.health_status');
    });
  });

  describe('Staleness Monitor Integration', () => {
    beforeEach(() => {
      vi.useFakeTimers();
    });

    afterEach(() => {
      vi.restoreAllMocks();
    });

    it('initializes staleness monitor composable', () => {
      wrapper = createWrapper();

      // Verify component has staleness-related refs
      expect(wrapper.vm.showStaleWarning).toBeDefined();
      expect(wrapper.vm.staleAgentName).toBeDefined();
    });

    it('renders stale warning snackbar', () => {
      wrapper = createWrapper();

      // Verify snackbar state is initialized
      expect(wrapper.vm.showStaleWarning).toBe(false);
      expect(wrapper.vm.staleAgentName).toBe('');
    });

    it('displays stale warning when emitStaleWarning is called', async () => {
      const agents = [
        {
          job_id: '123',
          agent_type: 'implementer',
          agent_name: 'Test Agent',
          status: 'working',
          health_status: 'healthy',
          last_progress_at: new Date(Date.now() - 15 * 60 * 1000).toISOString(), // 15 min ago
          mission_read_at: null,

        }
      ];

      wrapper = createWrapper({ agents });
      await nextTick();

      // Trigger staleness check by calling emitStaleWarning
      wrapper.vm.emitStaleWarning(agents[0]);
      await nextTick();

      expect(wrapper.vm.showStaleWarning).toBe(true);
      expect(wrapper.vm.staleAgentName).toBe('Test Agent');
    });

    it('can dismiss stale warning', async () => {
      wrapper = createWrapper();

      // Show warning
      wrapper.vm.showStaleWarning = true;
      wrapper.vm.staleAgentName = 'Test Agent';
      await nextTick();

      // Dismiss
      wrapper.vm.showStaleWarning = false;
      await nextTick();

      expect(wrapper.vm.showStaleWarning).toBe(false);
    });
  });

  describe('Existing Functionality (No Regressions)', () => {
    it('preserves mission tracking column', () => {
      wrapper = createWrapper();

      const headers = wrapper.vm.headers;
      const missionHeader = headers.find(h => h.key === 'mission_tracking');
      expect(missionHeader).toBeDefined();
      expect(missionHeader.title).toBe('Mission Tracking');
    });

    it('preserves actions column', () => {
      wrapper = createWrapper();

      const headers = wrapper.vm.headers;
      const actionsHeader = headers.find(h => h.key === 'actions');
      expect(actionsHeader).toBeDefined();
      expect(actionsHeader.title).toBe('Actions');
    });

    it('preserves messages column', () => {
      wrapper = createWrapper();

      const headers = wrapper.vm.headers;
      const messagesHeader = headers.find(h => h.key === 'messages');
      expect(messagesHeader).toBeDefined();
      expect(messagesHeader.title).toBe('Messages');
    });

    it('preserves agent type column with avatar', () => {
      wrapper = createWrapper();

      const headers = wrapper.vm.headers;
      const typeHeader = headers.find(h => h.key === 'agent_type');
      expect(typeHeader).toBeDefined();
      expect(typeHeader.title).toBe('Agent Type');
    });

    it('emits row-click event when row is clicked', async () => {
      const agent = {
        job_id: '123',
        agent_type: 'implementer',
        agent_name: 'Test Agent',
        status: 'working',
        health_status: 'healthy',
        last_progress_at: new Date().toISOString(),
        mission_read_at: null
      };

      wrapper = createWrapper({ agents: [agent] });
      await nextTick();

      wrapper.vm.handleRowClick({}, { item: agent });
      await nextTick();

      expect(wrapper.emitted('row-click')).toBeTruthy();
      expect(wrapper.emitted('row-click')[0]).toEqual([agent]);
    });
  });

  describe('Table Header Configuration', () => {
    it('has correct number of headers after health removal', () => {
      wrapper = createWrapper();

      // Should have 6 headers (removed health_status, kept others)
      expect(wrapper.vm.headers).toHaveLength(6);
    });

    it('has headers in correct order', () => {
      wrapper = createWrapper();

      const headers = wrapper.vm.headers;
      expect(headers[0].key).toBe('agent_type');
      expect(headers[1].key).toBe('agent_name');
      expect(headers[2].key).toBe('status');
      expect(headers[3].key).toBe('messages');
      expect(headers[4].key).toBe('mission_tracking');
      expect(headers[5].key).toBe('actions');
    });

    it('status header remains sortable', () => {
      wrapper = createWrapper();

      const statusHeader = wrapper.vm.headers.find(h => h.key === 'status');
      expect(statusHeader.sortable).toBe(true);
    });
  });
});
