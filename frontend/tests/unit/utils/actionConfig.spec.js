import { describe, it, expect } from 'vitest';
import {
  getAvailableActions,
  getActionConfig,
  ACTION_CONFIG
} from '@/utils/actionConfig';

describe('actionConfig.js', () => {
  describe('getActionConfig', () => {
    it('returns correct config for each action', () => {
      expect(getActionConfig('launch').icon).toBe('mdi-rocket-launch');
      expect(getActionConfig('copyPrompt').icon).toBe('mdi-content-copy');
      expect(getActionConfig('viewMessages').icon).toBe('mdi-message-text');
      expect(getActionConfig('cancel').icon).toBe('mdi-cancel');
      expect(getActionConfig('handOver').icon).toBe('mdi-hand-left');
    });

    it('returns null for unknown action', () => {
      expect(getActionConfig('invalid')).toBeNull();
    });

    it('includes confirmation config for destructive actions', () => {
      expect(getActionConfig('cancel').confirmation).toBe(true);
      expect(getActionConfig('cancel').confirmationTitle).toBe('Cancel Agent Job?');
      expect(getActionConfig('handOver').confirmation).toBe(true);
    });
  });

  describe('getAvailableActions - Launch Button', () => {
    it('shows launch for orchestrator in Claude Code CLI mode', () => {
      const job = { status: 'waiting', agent_type: 'orchestrator' };
      const actions = getAvailableActions(job, true);
      expect(actions).toContain('launch');
    });

    it('hides launch for non-orchestrator in Claude Code CLI mode', () => {
      const job = { status: 'waiting', agent_type: 'implementer' };
      const actions = getAvailableActions(job, true);
      expect(actions).not.toContain('launch');
    });

    it('shows launch for all agents in General CLI mode', () => {
      const job = { status: 'waiting', agent_type: 'implementer' };
      const actions = getAvailableActions(job, false);
      expect(actions).toContain('launch');
    });

    it('hides launch for non-waiting status', () => {
      const job = { status: 'working', agent_type: 'orchestrator' };
      const actions = getAvailableActions(job, false);
      expect(actions).not.toContain('launch');
    });
  });

  describe('getAvailableActions - Cancel Button', () => {
    it('shows cancel for working jobs', () => {
      const job = { status: 'working', agent_type: 'implementer' };
      const actions = getAvailableActions(job, false);
      expect(actions).toContain('cancel');
    });

    it('shows cancel for waiting jobs', () => {
      const job = { status: 'waiting', agent_type: 'implementer' };
      const actions = getAvailableActions(job, false);
      expect(actions).toContain('cancel');
    });

    it('shows cancel for blocked jobs', () => {
      const job = { status: 'blocked', agent_type: 'implementer' };
      const actions = getAvailableActions(job, false);
      expect(actions).toContain('cancel');
    });

    it('hides cancel for completed jobs', () => {
      const job = { status: 'complete', agent_type: 'implementer' };
      const actions = getAvailableActions(job, false);
      expect(actions).not.toContain('cancel');
    });
  });

  describe('getAvailableActions - Hand Over Button', () => {
    it('shows hand over for orchestrator at 90% context', () => {
      const job = {
        status: 'working',
        agent_type: 'orchestrator',
        context_used: 180000,
        context_budget: 200000
      };
      const actions = getAvailableActions(job, false);
      expect(actions).toContain('handOver');
    });

    it('hides hand over for orchestrator below 90% context', () => {
      const job = {
        status: 'working',
        agent_type: 'orchestrator',
        context_used: 100000,
        context_budget: 200000
      };
      const actions = getAvailableActions(job, false);
      expect(actions).not.toContain('handOver');
    });

    it('hides hand over for non-orchestrator', () => {
      const job = {
        status: 'working',
        agent_type: 'implementer',
        context_used: 180000,
        context_budget: 200000
      };
      const actions = getAvailableActions(job, false);
      expect(actions).not.toContain('handOver');
    });
  });

  describe('getAvailableActions - Always Available Actions', () => {
    it('always shows copy prompt except for decommissioned', () => {
      const job = { status: 'working', agent_type: 'implementer' };
      const actions = getAvailableActions(job, false);
      expect(actions).toContain('copyPrompt');
    });

    it('hides copy prompt for decommissioned', () => {
      const job = { status: 'decommissioned', agent_type: 'implementer' };
      const actions = getAvailableActions(job, false);
      expect(actions).not.toContain('copyPrompt');
    });

    it('always shows view messages', () => {
      const job = { status: 'complete', agent_type: 'implementer' };
      const actions = getAvailableActions(job, false);
      expect(actions).toContain('viewMessages');
    });
  });
});
