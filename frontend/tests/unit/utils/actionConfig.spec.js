import { describe, it, expect } from 'vitest';
import {
  getAvailableActions,
  getActionConfig,
  ACTION_CONFIG,
  shouldShowLaunchAction
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

  describe('shouldShowLaunchAction - Consolidated from duplicates', () => {
    describe('Claude Code CLI mode (enabled)', () => {
      it('shows launch for waiting orchestrator', () => {
        const job = { status: 'waiting', agent_type: 'orchestrator' };
        expect(shouldShowLaunchAction(job, true)).toBe(true);
      });

      it('hides launch for waiting specialist agents', () => {
        const specialistTypes = ['implementer', 'implementor', 'tester', 'reviewer', 'analyzer', 'documenter', 'researcher'];
        specialistTypes.forEach((agentType) => {
          const job = { status: 'waiting', agent_type: agentType };
          expect(shouldShowLaunchAction(job, true)).toBe(false);
        });
      });

      it('hides launch for working orchestrator in CLI mode', () => {
        const job = { status: 'working', agent_type: 'orchestrator' };
        expect(shouldShowLaunchAction(job, true)).toBe(false);
      });

      it('hides launch for waiting specialist in CLI mode', () => {
        const job = { status: 'waiting', agent_type: 'implementer' };
        expect(shouldShowLaunchAction(job, true)).toBe(false);
      });

      it('hides launch for blocked orchestrator even though orchestrator', () => {
        const job = { status: 'blocked', agent_type: 'orchestrator' };
        expect(shouldShowLaunchAction(job, true)).toBe(false);
      });
    });

    describe('Multi-terminal mode (disabled)', () => {
      it('shows launch for any waiting agent regardless of type', () => {
        const agentTypes = ['orchestrator', 'implementer', 'tester', 'reviewer', 'analyzer', 'documenter', 'researcher'];
        agentTypes.forEach((agentType) => {
          const job = { status: 'waiting', agent_type: agentType };
          expect(shouldShowLaunchAction(job, false)).toBe(true);
        });
      });

      it('hides launch for non-waiting agents in multi-terminal mode', () => {
        const statuses = ['working', 'complete', 'failed', 'cancelled', 'blocked', 'decommissioned'];
        statuses.forEach((status) => {
          const job = { status, agent_type: 'orchestrator' };
          expect(shouldShowLaunchAction(job, false)).toBe(false);
        });
      });

      it('hides launch for working specialist in multi-terminal mode', () => {
        const job = { status: 'working', agent_type: 'implementer' };
        expect(shouldShowLaunchAction(job, false)).toBe(false);
      });

      it('shows launch for waiting specialist in multi-terminal mode', () => {
        const job = { status: 'waiting', agent_type: 'implementer' };
        expect(shouldShowLaunchAction(job, false)).toBe(true);
      });
    });

    describe('terminal states', () => {
      const terminalStates = ['complete', 'failed', 'cancelled', 'decommissioned'];

      it('hides launch for all terminal states in both modes', () => {
        terminalStates.forEach((status) => {
          const orchestratorJob = { status, agent_type: 'orchestrator' };
          const specialistJob = { status, agent_type: 'implementer' };

          expect(shouldShowLaunchAction(orchestratorJob, true)).toBe(false);
          expect(shouldShowLaunchAction(orchestratorJob, false)).toBe(false);
          expect(shouldShowLaunchAction(specialistJob, true)).toBe(false);
          expect(shouldShowLaunchAction(specialistJob, false)).toBe(false);
        });
      });

      it('prevents launch for completed agents in CLI mode', () => {
        const job = { status: 'complete', agent_type: 'orchestrator' };
        expect(shouldShowLaunchAction(job, true)).toBe(false);
      });

      it('prevents launch for failed agents in multi-terminal mode', () => {
        const job = { status: 'failed', agent_type: 'implementer' };
        expect(shouldShowLaunchAction(job, false)).toBe(false);
      });

      it('prevents launch for cancelled agents', () => {
        const job = { status: 'cancelled', agent_type: 'orchestrator' };
        expect(shouldShowLaunchAction(job, true)).toBe(false);
      });

      it('prevents launch for decommissioned agents', () => {
        const job = { status: 'decommissioned', agent_type: 'tester' };
        expect(shouldShowLaunchAction(job, false)).toBe(false);
      });
    });

    describe('edge cases', () => {
      it('allows orchestrator to launch when waiting in CLI mode', () => {
        const job = { status: 'waiting', agent_type: 'orchestrator' };
        expect(shouldShowLaunchAction(job, true)).toBe(true);
      });

      it('prevents specialist from launching when waiting in CLI mode', () => {
        const job = { status: 'waiting', agent_type: 'specialist' };
        expect(shouldShowLaunchAction(job, true)).toBe(false);
      });

      it('handles missing agent_type gracefully', () => {
        const job = { status: 'waiting', agent_type: undefined };
        expect(shouldShowLaunchAction(job, true)).toBe(false);
        expect(shouldShowLaunchAction(job, false)).toBe(true);
      });

      it('handles null agent_type gracefully', () => {
        const job = { status: 'waiting', agent_type: null };
        expect(shouldShowLaunchAction(job, true)).toBe(false);
        expect(shouldShowLaunchAction(job, false)).toBe(true);
      });

      it('allows orchestrator at exactly 90% context in CLI mode', () => {
        const job = { status: 'waiting', agent_type: 'orchestrator', context_used: 90, context_budget: 100 };
        expect(shouldShowLaunchAction(job, true)).toBe(true);
      });

      it('distinguishes between waiting and other states accurately', () => {
        const waitingJob = { status: 'waiting', agent_type: 'implementer' };
        const workingJob = { status: 'working', agent_type: 'implementer' };
        const blockedJob = { status: 'blocked', agent_type: 'implementer' };

        expect(shouldShowLaunchAction(waitingJob, false)).toBe(true);
        expect(shouldShowLaunchAction(workingJob, false)).toBe(false);
        expect(shouldShowLaunchAction(blockedJob, false)).toBe(false);
      });
    });

    describe('consistency across duplicate locations', () => {
      it('behavior matches JobsTab.shouldShowCopyButton pattern (lines 577-590)', () => {
        // From JobsTab: return agent.status === 'waiting' for general mode
        // Or return agent.agent_type === 'orchestrator' for CLI mode
        const job = { status: 'waiting', agent_type: 'orchestrator' };
        expect(shouldShowLaunchAction(job, true)).toBe(true);

        const specialist = { status: 'waiting', agent_type: 'implementer' };
        expect(shouldShowLaunchAction(specialist, true)).toBe(false);
        expect(shouldShowLaunchAction(specialist, false)).toBe(true);
      });

      it('behavior matches AgentTableView.canLaunchAgent pattern (lines 208-227)', () => {
        // From AgentTableView: exclude terminal states and blocked
        // Then check agent type in CLI mode
        const terminalStates = ['complete', 'failed', 'cancelled', 'decommissioned'];
        terminalStates.forEach((status) => {
          const job = { status, agent_type: 'orchestrator' };
          expect(shouldShowLaunchAction(job, false)).toBe(false);
        });

        const blockedJob = { status: 'blocked', agent_type: 'orchestrator' };
        expect(shouldShowLaunchAction(blockedJob, false)).toBe(false);
      });

      it('ensures no divergent behavior between consolidated function and original locations', () => {
        const testCases = [
          // (job, claudeCodeCliMode, expectedResult)
          ({ status: 'waiting', agent_type: 'orchestrator' }, true, true),
          ({ status: 'waiting', agent_type: 'orchestrator' }, false, true),
          ({ status: 'waiting', agent_type: 'implementer' }, true, false),
          ({ status: 'waiting', agent_type: 'implementer' }, false, true),
          ({ status: 'working', agent_type: 'orchestrator' }, true, false),
          ({ status: 'working', agent_type: 'orchestrator' }, false, false),
          ({ status: 'complete', agent_type: 'orchestrator' }, true, false),
          ({ status: 'complete', agent_type: 'orchestrator' }, false, false),
          ({ status: 'blocked', agent_type: 'orchestrator' }, true, false),
          ({ status: 'blocked', agent_type: 'orchestrator' }, false, false),
          ({ status: 'failed', agent_type: 'implementer' }, true, false),
          ({ status: 'failed', agent_type: 'implementer' }, false, false),
        ];

        testCases.forEach(([job, mode, expected]) => {
          expect(shouldShowLaunchAction(job, mode)).toBe(expected);
        });
      });
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
