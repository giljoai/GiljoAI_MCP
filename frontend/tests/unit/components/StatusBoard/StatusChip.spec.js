import { describe, it, expect } from 'vitest';
import { mount } from '@vue/test-utils';
import StatusChip from '@/components/StatusBoard/StatusChip.vue';

describe('StatusChip.vue', () => {
  const createWrapper = (props = {}) => {
    return mount(StatusChip, {
      props: {
        status: 'working',
        ...props
      },
      global: {
        stubs: {
          'v-tooltip': {
            template: '<div><slot /></div>'
          },
          'v-chip': {
            template: '<div class="v-chip" :class="$attrs.class"><slot /></div>',
            props: ['color', 'prependIcon', 'size']
          },
          'v-icon': {
            template: '<span class="v-icon">{{ $slots.default ? $slots.default()[0].children : "" }}</span>'
          },
          'v-divider': {
            template: '<hr />'
          }
        }
      }
    });
  };

  describe('Status Icons', () => {
    it('renders correct icon for each status', () => {
      const statuses = {
        waiting: 'mdi-clock-outline',
        working: 'mdi-cog',
        blocked: 'mdi-alert-octagon',
        complete: 'mdi-check-circle',
        failed: 'mdi-alert-circle',
        cancelled: 'mdi-cancel',
        decommissioned: 'mdi-archive'
      };

      Object.entries(statuses).forEach(([status, expectedIcon]) => {
        const wrapper = createWrapper({ status });
        const component = wrapper.vm;
        expect(component.statusConfig.icon).toBe(expectedIcon);
      });
    });

    it('renders correct color for working status', () => {
      const wrapper = createWrapper({ status: 'working' });
      const component = wrapper.vm;
      expect(component.statusConfig.color).toBe('primary');
    });
  });

  describe('Health Indicator', () => {
    it('shows health indicator for warning state', () => {
      const wrapper = createWrapper({
        status: 'working',
        healthStatus: 'warning'
      });
      const component = wrapper.vm;
      expect(component.healthConfig.showIndicator).toBe(true);
      expect(component.healthConfig.dotColor).toBe('yellow darken-2');
      expect(component.healthConfig.pulse).toBe(false);
    });

    it('does not show health indicator for healthy state', () => {
      const wrapper = createWrapper({
        status: 'working',
        healthStatus: 'healthy'
      });
      const component = wrapper.vm;
      expect(component.healthConfig.showIndicator).toBe(false);
      expect(wrapper.find('.health-indicator').exists()).toBe(false);
    });

    it('applies pulse animation for critical health', () => {
      const wrapper = createWrapper({
        status: 'working',
        healthStatus: 'critical'
      });
      const component = wrapper.vm;
      expect(component.healthConfig.showIndicator).toBe(true);
      expect(component.healthConfig.pulse).toBe(true);
      expect(component.healthConfig.dotColor).toBe('red');
    });
  });

  describe('Staleness Indicator', () => {
    it('shows staleness icon for stale jobs', () => {
      const elevenMinutesAgo = new Date(Date.now() - 11 * 60 * 1000).toISOString();
      const wrapper = createWrapper({
        status: 'working',
        lastProgressAt: elevenMinutesAgo,
        minutesSinceProgress: 11
      });
      const component = wrapper.vm;
      expect(component.isStale).toBe(true);
      expect(component.formattedLastActivity).toBe('11 minutes ago');
      // Check that warning text is present in tooltip
      expect(wrapper.text()).toContain('Warning:');
      expect(wrapper.text()).toContain('No activity for 11 minutes');
    });

    it('does not show staleness for terminal states', () => {
      const elevenMinutesAgo = new Date(Date.now() - 11 * 60 * 1000).toISOString();
      const wrapper = createWrapper({
        status: 'complete',
        lastProgressAt: elevenMinutesAgo,
        minutesSinceProgress: 11
      });
      const component = wrapper.vm;
      expect(component.isStale).toBe(false);
      expect(wrapper.text()).not.toContain('Warning:');
    });
  });

  describe('Tooltips', () => {
    it('shows tooltip with status description', () => {
      const wrapper = createWrapper({ status: 'working' });
      expect(wrapper.text()).toContain('Agent is actively working');
    });

    it('shows last activity in tooltip', () => {
      const fiveMinutesAgo = new Date(Date.now() - 5 * 60 * 1000).toISOString();
      const wrapper = createWrapper({
        status: 'working',
        lastProgressAt: fiveMinutesAgo
      });
      expect(wrapper.text()).toContain('5 minutes ago');
    });

    it('shows staleness warning in tooltip', () => {
      const elevenMinutesAgo = new Date(Date.now() - 11 * 60 * 1000).toISOString();
      const wrapper = createWrapper({
        status: 'working',
        lastProgressAt: elevenMinutesAgo,
        minutesSinceProgress: 11
      });
      expect(wrapper.text()).toContain('Warning:');
      expect(wrapper.text()).toContain('No activity for 11 minutes');
    });
  });
});
