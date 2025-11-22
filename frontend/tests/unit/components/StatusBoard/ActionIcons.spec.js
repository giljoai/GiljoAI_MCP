import { describe, it, expect, vi, beforeEach } from 'vitest';
import { mount } from '@vue/test-utils';
import ActionIcons from '@/components/StatusBoard/ActionIcons.vue';

describe('ActionIcons.vue', () => {
  const createWrapper = (props = {}) => {
    return mount(ActionIcons, {
      props: {
        job: { job_id: '123', status: 'working', agent_type: 'implementer' },
        claudeCodeCliMode: false,
        ...props
      },
      global: {
        stubs: {
          'v-tooltip': {
            template: '<div><slot name="activator" :props="{}" /><slot /></div>'
          },
          'v-btn': {
            template: '<button :data-test="$attrs[\'data-test\']" :disabled="disabled || loading" :class="{ \'v-btn--loading\': loading }"><slot /></button>',
            props: ['icon', 'color', 'size', 'variant', 'loading', 'disabled']
          },
          'v-badge': {
            template: '<div data-test="messages-badge" class="v-badge">{{ content }}<slot /></div>',
            props: ['content', 'color']
          },
          'v-dialog': {
            template: '<div v-if="modelValue" :data-test="$attrs[\'data-test\']"><slot /></div>',
            props: ['modelValue', 'maxWidth']
          },
          'v-card': {
            template: '<div><slot /></div>'
          },
          'v-card-title': {
            template: '<div><slot /></div>'
          },
          'v-card-text': {
            template: '<div><slot /></div>'
          },
          'v-card-actions': {
            template: '<div><slot /></div>'
          },
          'v-spacer': {
            template: '<div />'
          },
          'v-snackbar': {
            template: '<div v-if="modelValue"><slot /></div>',
            props: ['modelValue', 'color', 'timeout']
          }
        }
      }
    });
  };

  describe('Action Availability', () => {
    it('renders launch button for waiting jobs in General CLI mode', () => {
      const wrapper = createWrapper({
        job: { job_id: '123', status: 'waiting', agent_type: 'implementer' }
      });
      const launchButton = wrapper.find('[data-test="action-launch"]');
      expect(launchButton.exists()).toBe(true);
    });

    it('hides launch button for non-orchestrator in Claude Code CLI mode', () => {
      const wrapper = createWrapper({
        job: { job_id: '123', status: 'waiting', agent_type: 'implementer' },
        claudeCodeCliMode: true
      });
      const launchButton = wrapper.find('[data-test="action-launch"]');
      expect(launchButton.exists()).toBe(false);
    });

    it('renders copy prompt button for all jobs', () => {
      const wrapper = createWrapper();
      const copyButton = wrapper.find('[data-test="action-copyPrompt"]');
      expect(copyButton.exists()).toBe(true);
    });

    it('renders view messages button for all jobs', () => {
      const wrapper = createWrapper();
      const messagesButton = wrapper.find('[data-test="action-viewMessages"]');
      expect(messagesButton.exists()).toBe(true);
    });

    it('renders cancel button for working jobs', () => {
      const wrapper = createWrapper({
        job: { job_id: '123', status: 'working', agent_type: 'implementer' }
      });
      const cancelButton = wrapper.find('[data-test="action-cancel"]');
      expect(cancelButton.exists()).toBe(true);
    });

    it('hides cancel button for completed jobs', () => {
      const wrapper = createWrapper({
        job: { job_id: '123', status: 'complete', agent_type: 'implementer' }
      });
      const cancelButton = wrapper.find('[data-test="action-cancel"]');
      expect(cancelButton.exists()).toBe(false);
    });

    it('renders hand over button for orchestrator at 90% context', () => {
      const wrapper = createWrapper({
        job: {
          job_id: '123',
          status: 'working',
          agent_type: 'orchestrator',
          context_used: 180000,
          context_budget: 200000
        }
      });
      const handOverButton = wrapper.find('[data-test="action-handOver"]');
      expect(handOverButton.exists()).toBe(true);
    });
  });

  describe('Event Emission', () => {
    it('emits launch event when launch button clicked', async () => {
      const wrapper = createWrapper({
        job: { job_id: '123', status: 'waiting', agent_type: 'implementer' }
      });
      const launchButton = wrapper.find('[data-test="action-launch"]');
      await launchButton.trigger('click');
      expect(wrapper.emitted('launch')).toBeTruthy();
      expect(wrapper.emitted('launch')[0][0].status).toBe('waiting');
    });

    it('emits copy-prompt event when copy button clicked', async () => {
      const wrapper = createWrapper();
      const copyButton = wrapper.find('[data-test="action-copyPrompt"]');
      await copyButton.trigger('click');
      expect(wrapper.emitted('copy-prompt')).toBeTruthy();
    });

    it('emits view-messages event when messages button clicked', async () => {
      const wrapper = createWrapper();
      const messagesButton = wrapper.find('[data-test="action-viewMessages"]');
      await messagesButton.trigger('click');
      expect(wrapper.emitted('view-messages')).toBeTruthy();
    });

    it('shows confirmation before emitting cancel event', async () => {
      const wrapper = createWrapper({
        job: { job_id: '123', status: 'working', agent_type: 'implementer' }
      });
      const cancelButton = wrapper.find('[data-test="action-cancel"]');
      await cancelButton.trigger('click');

      // Confirmation dialog should show
      expect(wrapper.vm.showConfirmDialog).toBe(true);
      expect(wrapper.html()).toContain('Cancel Agent Job?');

      // Cancel event not emitted until confirmed
      expect(wrapper.emitted('cancel')).toBeFalsy();
    });

    it('emits cancel event after confirmation', async () => {
      const wrapper = createWrapper({
        job: { job_id: '123', status: 'working', agent_type: 'implementer' }
      });

      // Click cancel button
      const cancelButton = wrapper.find('[data-test="action-cancel"]');
      await cancelButton.trigger('click');

      // Confirm action
      const confirmButton = wrapper.find('[data-test="confirm-dialog-confirm"]');
      await confirmButton.trigger('click');

      expect(wrapper.emitted('cancel')).toBeTruthy();
    });
  });

  describe('Loading States', () => {
    it('shows loading spinner on launch action', async () => {
      const wrapper = createWrapper({
        job: { job_id: '123', status: 'waiting', agent_type: 'implementer' }
      });

      wrapper.vm.loadingStates.launch = true;
      await wrapper.vm.$nextTick();

      const launchButton = wrapper.find('[data-test="action-launch"]');
      expect(launchButton.attributes()).toHaveProperty('disabled');
    });

    it('disables button during loading', async () => {
      const wrapper = createWrapper();

      wrapper.vm.loadingStates.copyPrompt = true;
      await wrapper.vm.$nextTick();

      const copyButton = wrapper.find('[data-test="action-copyPrompt"]');
      expect(copyButton.attributes()).toHaveProperty('disabled');
    });
  });

  describe('Unread Message Badge', () => {
    it('shows badge with unread count on messages icon', () => {
      const wrapper = createWrapper({
        job: {
          job_id: '123',
          status: 'working',
          agent_type: 'implementer',
          unread_count: 5
        }
      });
      const badge = wrapper.find('[data-test="messages-badge"]');
      expect(badge.exists()).toBe(true);
      expect(badge.text()).toContain('5');
    });

    it('hides badge when no unread messages', () => {
      const wrapper = createWrapper({
        job: {
          job_id: '123',
          status: 'working',
          agent_type: 'implementer',
          unread_count: 0
        }
      });
      const badge = wrapper.find('[data-test="messages-badge"]');
      expect(badge.exists()).toBe(false);
    });
  });

  describe('Confirmation Dialogs', () => {
    it('shows confirmation dialog for cancel action', async () => {
      const wrapper = createWrapper({
        job: { job_id: '123', status: 'working', agent_type: 'implementer' }
      });
      const cancelButton = wrapper.find('[data-test="action-cancel"]');
      await cancelButton.trigger('click');
      await wrapper.vm.$nextTick();

      expect(wrapper.find('[data-test="confirm-dialog"]').exists()).toBe(true);
      const dialogText = wrapper.find('[data-test="confirm-dialog"]').text();
      expect(dialogText).toContain('Cancel Agent Job?');
      expect(dialogText).toContain('This action cannot be undone');
    });

    it('shows confirmation dialog for hand over action', async () => {
      const wrapper = createWrapper({
        job: {
          job_id: '123',
          status: 'working',
          agent_type: 'orchestrator',
          context_used: 180000,
          context_budget: 200000
        }
      });
      const handOverButton = wrapper.find('[data-test="action-handOver"]');
      await handOverButton.trigger('click');
      await wrapper.vm.$nextTick();

      expect(wrapper.find('[data-test="confirm-dialog"]').exists()).toBe(true);
      const dialogText = wrapper.find('[data-test="confirm-dialog"]').text();
      expect(dialogText).toContain('Trigger Orchestrator Handover?');
    });

    it('closes dialog when cancel clicked', async () => {
      const wrapper = createWrapper({
        job: { job_id: '123', status: 'working', agent_type: 'implementer' }
      });

      const cancelButton = wrapper.find('[data-test="action-cancel"]');
      await cancelButton.trigger('click');
      await wrapper.vm.$nextTick();
      expect(wrapper.vm.showConfirmDialog).toBe(true);

      const dialogCancelButton = wrapper.find('[data-test="confirm-dialog-cancel"]');
      await dialogCancelButton.trigger('click');
      await wrapper.vm.$nextTick();
      expect(wrapper.vm.showConfirmDialog).toBe(false);
    });
  });
});
