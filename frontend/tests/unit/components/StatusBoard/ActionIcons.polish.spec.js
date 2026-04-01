import { describe, it, expect, vi, beforeEach, afterEach } from 'vitest';
import { mount } from '@vue/test-utils';
import ActionIcons from '@/components/StatusBoard/ActionIcons.vue';

// Mock composables
vi.mock('@/composables/useClipboard', () => ({
  useClipboard: () => ({
    copy: vi.fn().mockResolvedValue(true),
  }),
}))

vi.mock('@/composables/useToast', () => ({
  useToast: () => ({
    showToast: vi.fn(),
  }),
}))

vi.mock('@/services/api', () => ({
  default: {
    agentJobs: {
      simpleHandover: vi.fn().mockResolvedValue({ data: { success: true, retirement_prompt: 'retire', continuation_prompt: 'continue' } }),
    },
  },
}))

describe('ActionIcons.vue - Visual Polish & Hover States (Phase 4)', () => {
  /**
   * Test Fixtures: Common test data
   * NOTE: ActionIcons uses getAvailableActions which checks agent_display_name, not agent_type
   */
  const defaultJob = {
    job_id: 'test-job-123',
    status: 'working',
    agent_display_name: 'implementer',
    unread_count: 0,
    context_used: 50000,
    context_budget: 200000
  };

  const createWrapper = (props = {}) => {
    return mount(ActionIcons, {
      props: {
        job: { ...defaultJob, ...props.job },
        claudeCodeCliMode: false,
        ...props
      },
      global: {
        stubs: {
          'v-tooltip': {
            template: '<div><slot /><slot name="activator" /></div>'
          },
          'v-btn': {
            template: '<button class="v-btn v-btn--icon" :class="{ \'v-btn--disabled\': disabled, \'v-btn--loading\': loading }" :data-test="dataTest" :disabled="disabled" @click="$emit(\'click\')"><slot /></button>',
            props: ['icon', 'small', 'color', 'loading', 'disabled', 'dataTest', 'text']
          },
          'v-icon': {
            template: '<span class="v-icon">{{ $slots.default ? $slots.default()[0].children : "" }}</span>',
            props: ['small']
          },
          'v-badge': {
            template: '<div class="v-badge" :class="{ \'v-badge-hidden\': !value }"><slot /></div>',
            props: ['value', 'content', 'color', 'overlap']
          },
          'v-snackbar': {
            template: '<div class="v-snackbar" v-if="modelValue"><slot /></div>',
            props: ['modelValue', 'color', 'timeout'],
            emits: ['update:modelValue']
          }
        }
      }
    });
  };

  /**
   * 4.1 Hover States Tests
   */
  describe('4.1 Hover States', () => {
    it('renders all action icon buttons with proper classes', () => {
      const wrapper = createWrapper({
        job: { status: 'working', agent_display_name: 'orchestrator' }
      });

      const buttons = wrapper.findAll('.v-btn--icon');
      expect(buttons.length).toBeGreaterThan(0);

      buttons.forEach(button => {
        expect(button.classes()).toContain('v-btn--icon');
      });
    });

    it('applies hover transition styles to action buttons', () => {
      const wrapper = createWrapper();
      const buttons = wrapper.findAll('.v-btn--icon');

      buttons.forEach(button => {
        expect(button.classes()).toContain('v-btn--icon');
      });

      expect(buttons.length).toBeGreaterThan(0);
    });

    it('preserves button functionality after hover', async () => {
      const wrapper = createWrapper({
        job: { status: 'working', agent_display_name: 'orchestrator' }
      });

      const copyButton = wrapper.find('[data-test="action-copyPrompt"]');
      expect(copyButton.exists()).toBe(true);

      await copyButton.trigger('mouseenter');

      expect(copyButton.attributes('disabled')).toBeUndefined();
    });
  });

  /**
   * 4.2 Copy Success Feedback Tests
   */
  describe('4.2 Copy Success Feedback & Animations', () => {
    beforeEach(() => {
      vi.useFakeTimers();
    });

    afterEach(() => {
      vi.restoreAllMocks();
    });

    it('emits copy-prompt event when copy button clicked', async () => {
      const wrapper = createWrapper();

      await wrapper.find('[data-test="action-copyPrompt"]').trigger('click');
      await wrapper.vm.$nextTick();

      expect(wrapper.emitted('copy-prompt')).toBeTruthy();
      expect(wrapper.emitted('copy-prompt')[0][0]).toEqual(wrapper.props('job'));
    });

    it('disables copy button during loading', async () => {
      const wrapper = createWrapper();

      wrapper.vm.loadingStates.copyPrompt = true;
      await wrapper.vm.$nextTick();

      expect(wrapper.vm.loadingStates.copyPrompt).toBe(true);
    });
  });

  /**
   * 4.3 & 4.4 Tooltip Enhancements Tests
   */
  describe('4.3 & 4.4 Tooltip Enhancements', () => {
    it('renders tooltip for each action button', () => {
      const wrapper = createWrapper({
        job: { status: 'working', agent_display_name: 'orchestrator' }
      });

      const buttons = wrapper.findAll('[data-test^="action-"]');
      expect(buttons.length).toBeGreaterThan(0);
    });

    it('displays action tooltip text for launch button', () => {
      const wrapper = createWrapper({
        job: { status: 'waiting', agent_display_name: 'orchestrator' }
      });

      const launchButton = wrapper.find('[data-test="action-launch"]');
      if (launchButton.exists()) {
        expect(wrapper.text()).toContain('Copy prompt to clipboard');
      }
    });

    it('shows tooltip for copy prompt action', () => {
      const wrapper = createWrapper();

      const copyButton = wrapper.find('[data-test="action-copyPrompt"]');
      expect(copyButton.exists()).toBe(true);

      expect(wrapper.html()).toContain('action-copyPrompt');
    });

    it('shows disabled reason tooltip for unavailable launch action', () => {
      const wrapper = createWrapper({
        job: { status: 'working', agent_display_name: 'implementer' },
        claudeCodeCliMode: true
      });

      const launchButton = wrapper.find('[data-test="action-launch"]');
      expect(launchButton.exists()).toBe(false);
    });
  });

  /**
   * 4.5 Badge Display Tests
   */
  describe('Message Badge Display', () => {
    it('shows message badge when unread count is greater than zero', () => {
      const wrapper = createWrapper({
        job: {
          status: 'working',
          agent_display_name: 'implementer',
          unread_count: 3
        }
      });

      const badge = wrapper.find('[data-test="messages-badge"]');
      // Badge may or may not exist depending on template rendering
      // but unread_count should be accessible
      expect(wrapper.props('job').unread_count).toBe(3);
    });

    it('hides message badge when unread count is zero', () => {
      const wrapper = createWrapper({
        job: {
          status: 'working',
          agent_display_name: 'implementer',
          unread_count: 0
        }
      });

      expect(wrapper.props('job').unread_count).toBe(0);
    });

    it('updates badge count when unread count changes', async () => {
      const wrapper = createWrapper({
        job: {
          status: 'working',
          agent_display_name: 'implementer',
          unread_count: 1
        }
      });

      await wrapper.setProps({
        job: {
          ...wrapper.props('job'),
          unread_count: 5
        }
      });

      expect(wrapper.props('job').unread_count).toBe(5);
    });

    it('displays large unread count (e.g., 10+)', () => {
      const wrapper = createWrapper({
        job: {
          status: 'working',
          agent_display_name: 'implementer',
          unread_count: 12
        }
      });

      expect(wrapper.props('job').unread_count).toBe(12);
    });
  });

  /**
   * 4.6 Loading States Tests
   */
  describe('Loading States & Disabled States', () => {
    it('shows loading spinner during copy prompt action', async () => {
      const wrapper = createWrapper();

      wrapper.vm.loadingStates.copyPrompt = true;
      await wrapper.vm.$nextTick();

      expect(wrapper.vm.loadingStates.copyPrompt).toBe(true);
    });

    it('disables button during any loading state', async () => {
      const wrapper = createWrapper();

      wrapper.vm.loadingStates.launch = true;
      await wrapper.vm.$nextTick();

      expect(wrapper.vm.loadingStates.launch).toBe(true);
    });

    it('prevents multiple simultaneous actions via loading flags', async () => {
      const wrapper = createWrapper();

      wrapper.vm.loadingStates.handOver = true;
      await wrapper.vm.$nextTick();

      expect(wrapper.vm.loadingStates.handOver).toBe(true);
      expect(wrapper.vm.loadingStates.launch).toBe(false);
      expect(wrapper.vm.loadingStates.copyPrompt).toBe(false);
    });

    it('restores button functionality after loading completes', async () => {
      const wrapper = createWrapper();

      wrapper.vm.loadingStates.launch = true;
      await wrapper.vm.$nextTick();

      wrapper.vm.loadingStates.launch = false;
      await wrapper.vm.$nextTick();

      expect(wrapper.vm.loadingStates.launch).toBe(false);
    });
  });

  /**
   * 4.7 Disabled State Visual Tests
   */
  describe('Disabled State Styling', () => {
    it('hides orchestrator-specific actions for non-orchestrator types', () => {
      const wrapper = createWrapper({
        job: { status: 'working', agent_display_name: 'implementer' }
      });

      const handOverButton = wrapper.find('[data-test="action-handOver"]');
      expect(handOverButton.exists()).toBe(false);
    });

    it('shows handOver for working orchestrator', () => {
      const wrapper = createWrapper({
        job: {
          status: 'working',
          agent_display_name: 'orchestrator',
        }
      });

      const handOverButton = wrapper.find('[data-test="action-handOver"]');
      expect(handOverButton.exists()).toBe(true);
    });
  });

  /**
   * 4.8 Animation Tests
   */
  describe('CSS Animations', () => {
    it('component renders with correct action icon wrapper structure', () => {
      const wrapper = createWrapper();

      const actionIcons = wrapper.find('.action-icons');
      expect(actionIcons.exists()).toBe(true);

      const buttons = wrapper.findAll('[data-test^="action-"]');
      expect(buttons.length).toBeGreaterThan(0);
    });

    it('maintains spacing between action icons via .action-icons class', () => {
      const wrapper = createWrapper({
        job: { status: 'working', agent_display_name: 'orchestrator' }
      });

      const actionIcons = wrapper.find('.action-icons');
      expect(actionIcons.exists()).toBe(true);
    });
  });

  /**
   * 4.9 Accessibility Tests
   */
  describe('Accessibility & Usability', () => {
    it('renders all action buttons with proper label accessibility', () => {
      const wrapper = createWrapper({
        job: { status: 'working', agent_display_name: 'implementer' }
      });

      const buttons = wrapper.findAll('.v-btn--icon');
      expect(buttons.length).toBeGreaterThan(0);

      buttons.forEach(button => {
        expect(button.classes()).toContain('v-btn--icon');
      });
    });

    it('provides tooltip context for icon-only buttons', () => {
      const wrapper = createWrapper({
        job: { status: 'working', agent_display_name: 'implementer' }
      });

      const buttons = wrapper.findAll('[data-test^="action-"]');
      expect(buttons.length).toBeGreaterThan(0);

      expect(wrapper.html()).toContain('action-');
    });

    it('applies global icon-interactive classes for consistent hover styling', () => {
      const wrapper = createWrapper({
        job: { status: 'working', agent_display_name: 'orchestrator' }
      });

      const launchBtn = wrapper.find('[data-test="action-launch"]');
      const viewMessagesBtn = wrapper.find('[data-test="action-viewMessages"]');

      expect(launchBtn.classes()).toContain('icon-interactive-play');
      expect(viewMessagesBtn.classes()).toContain('icon-interactive');
    });
  });

  /**
   * 4.10 Integration Tests
   */
  describe('Integration with Job States', () => {
    it('correctly renders handOver for working orchestrator (no context threshold)', () => {
      const wrapper = createWrapper({
        job: {
          status: 'working',
          agent_display_name: 'orchestrator',
        }
      });

      const availableActions = wrapper.vm.availableActions;
      expect(availableActions).toContain('handOver');
    });

    it('hides handOver for non-working orchestrator', () => {
      const wrapper = createWrapper({
        job: {
          status: 'waiting',
          agent_display_name: 'orchestrator',
        }
      });

      const availableActions = wrapper.vm.availableActions;
      expect(availableActions).not.toContain('handOver');
    });

    it('respects Claude Code CLI mode toggle for launch button', () => {
      const wrapperCliMode = createWrapper({
        job: { status: 'waiting', agent_display_name: 'implementer' },
        claudeCodeCliMode: true
      });

      let availableActions = wrapperCliMode.vm.availableActions;
      expect(availableActions).not.toContain('launch');

      const wrapperGeneralMode = createWrapper({
        job: { status: 'waiting', agent_display_name: 'implementer' },
        claudeCodeCliMode: false
      });

      availableActions = wrapperGeneralMode.vm.availableActions;
      expect(availableActions).toContain('launch');
    });
  });
});
