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
      expect(getActionConfig('handOver').icon).toBe('mdi-refresh');
    });

    it('returns null for unknown action', () => {
      expect(getActionConfig('invalid')).toBeNull();
    });

    it('cancel action does not exist in ACTION_CONFIG', () => {
      expect(getActionConfig('cancel')).toBeNull();
    });

    it('handOver does not require confirmation', () => {
      expect(getActionConfig('handOver').confirmation).toBe(false);
    });
  });

  describe('shouldShowLaunchAction - Consolidated from duplicates', () => {
    describe('Claude Code CLI mode (enabled)', () => {
      it('shows launch for orchestrator in CLI mode', () => {
        const job = { status: 'waiting', agent_display_name: 'orchestrator' };
        expect(shouldShowLaunchAction(job, true)).toBe(true);
      });

      it('hides launch for non-orchestrator agents in CLI mode', () => {
        const specialistTypes = ['implementer', 'implementor', 'tester', 'reviewer', 'analyzer', 'documenter', 'researcher'];
        specialistTypes.forEach((agentType) => {
          const job = { status: 'waiting', agent_display_name: agentType };
          expect(shouldShowLaunchAction(job, true)).toBe(false);
        });
      });

      it('shows launch for orchestrator regardless of status in CLI mode', () => {
        const job = { status: 'working', agent_display_name: 'orchestrator' };
        expect(shouldShowLaunchAction(job, true)).toBe(true);
      });

      it('hides launch for waiting specialist in CLI mode', () => {
        const job = { status: 'waiting', agent_display_name: 'implementer' };
        expect(shouldShowLaunchAction(job, true)).toBe(false);
      });

      it('hides launch for blocked non-orchestrator in CLI mode', () => {
        const job = { status: 'blocked', agent_display_name: 'implementer' };
        expect(shouldShowLaunchAction(job, true)).toBe(false);
      });
    });

    describe('Multi-terminal mode (disabled)', () => {
      it('shows launch for any agent regardless of type or status', () => {
        const agentTypes = ['orchestrator', 'implementer', 'tester', 'reviewer', 'analyzer', 'documenter', 'researcher'];
        agentTypes.forEach((agentType) => {
          const job = { status: 'waiting', agent_display_name: agentType };
          expect(shouldShowLaunchAction(job, false)).toBe(true);
        });
      });

      it('shows launch even for non-waiting agents in multi-terminal mode', () => {
        const statuses = ['working', 'complete', 'failed', 'cancelled', 'blocked', 'decommissioned'];
        statuses.forEach((status) => {
          const job = { status, agent_display_name: 'orchestrator' };
          expect(shouldShowLaunchAction(job, false)).toBe(true);
        });
      });

      it('shows launch for working specialist in multi-terminal mode', () => {
        const job = { status: 'working', agent_display_name: 'implementer' };
        expect(shouldShowLaunchAction(job, false)).toBe(true);
      });

      it('shows launch for waiting specialist in multi-terminal mode', () => {
        const job = { status: 'waiting', agent_display_name: 'implementer' };
        expect(shouldShowLaunchAction(job, false)).toBe(true);
      });
    });

    describe('edge cases', () => {
      it('allows orchestrator to launch in CLI mode', () => {
        const job = { status: 'waiting', agent_display_name: 'orchestrator' };
        expect(shouldShowLaunchAction(job, true)).toBe(true);
      });

      it('prevents specialist from launching in CLI mode', () => {
        const job = { status: 'waiting', agent_display_name: 'specialist' };
        expect(shouldShowLaunchAction(job, true)).toBe(false);
      });

      it('handles missing agent_display_name gracefully', () => {
        const job = { status: 'waiting', agent_display_name: undefined };
        expect(shouldShowLaunchAction(job, true)).toBe(false);
        expect(shouldShowLaunchAction(job, false)).toBe(true);
      });

      it('handles null agent_display_name gracefully', () => {
        const job = { status: 'waiting', agent_display_name: null };
        expect(shouldShowLaunchAction(job, true)).toBe(false);
        expect(shouldShowLaunchAction(job, false)).toBe(true);
      });

      it('allows orchestrator at 90% context in CLI mode', () => {
        const job = { status: 'waiting', agent_display_name: 'orchestrator', context_used: 90, context_budget: 100 };
        expect(shouldShowLaunchAction(job, true)).toBe(true);
      });

      it('always shows launch in multi-terminal mode regardless of status', () => {
        const waitingJob = { status: 'waiting', agent_display_name: 'implementer' };
        const workingJob = { status: 'working', agent_display_name: 'implementer' };
        const blockedJob = { status: 'blocked', agent_display_name: 'implementer' };

        expect(shouldShowLaunchAction(waitingJob, false)).toBe(true);
        expect(shouldShowLaunchAction(workingJob, false)).toBe(true);
        expect(shouldShowLaunchAction(blockedJob, false)).toBe(true);
      });
    });

    describe('consistency across duplicate locations', () => {
      it('behavior matches JobsTab.shouldShowCopyButton pattern', () => {
        const job = { status: 'waiting', agent_display_name: 'orchestrator' };
        expect(shouldShowLaunchAction(job, true)).toBe(true);

        const specialist = { status: 'waiting', agent_display_name: 'implementer' };
        expect(shouldShowLaunchAction(specialist, true)).toBe(false);
        expect(shouldShowLaunchAction(specialist, false)).toBe(true);
      });

      it('behavior matches AgentTableView.canLaunchAgent pattern', () => {
        // In multi-terminal mode, launch is always available
        const terminalStates = ['complete', 'failed', 'cancelled', 'decommissioned'];
        terminalStates.forEach((status) => {
          const job = { status, agent_display_name: 'orchestrator' };
          expect(shouldShowLaunchAction(job, false)).toBe(true);
        });

        // In CLI mode, only orchestrator gets launch
        const blockedJob = { status: 'blocked', agent_display_name: 'implementer' };
        expect(shouldShowLaunchAction(blockedJob, true)).toBe(false);
      });

      it('ensures no divergent behavior between consolidated function and original locations', () => {
        const testCases = [
          // (job, claudeCodeCliMode, expectedResult)
          // In CLI mode: only orchestrator gets launch (always true for orchestrator)
          [{ status: 'waiting', agent_display_name: 'orchestrator' }, true, true],
          [{ status: 'waiting', agent_display_name: 'orchestrator' }, false, true],
          [{ status: 'waiting', agent_display_name: 'implementer' }, true, false],
          [{ status: 'waiting', agent_display_name: 'implementer' }, false, true],
          [{ status: 'working', agent_display_name: 'orchestrator' }, true, true],
          [{ status: 'working', agent_display_name: 'orchestrator' }, false, true],
          // In non-CLI mode, always true; in CLI mode, non-orchestrator = false
          [{ status: 'complete', agent_display_name: 'orchestrator' }, true, true],
          [{ status: 'complete', agent_display_name: 'orchestrator' }, false, true],
          [{ status: 'blocked', agent_display_name: 'orchestrator' }, true, true],
          [{ status: 'blocked', agent_display_name: 'orchestrator' }, false, true],
          [{ status: 'failed', agent_display_name: 'implementer' }, true, false],
          [{ status: 'failed', agent_display_name: 'implementer' }, false, true],
        ];

        testCases.forEach(([job, mode, expected]) => {
          expect(shouldShowLaunchAction(job, mode)).toBe(expected);
        });
      });
    });
  });

  describe('getAvailableActions - Launch Button', () => {
    it('shows launch for orchestrator in Claude Code CLI mode', () => {
      const job = { status: 'waiting', agent_display_name: 'orchestrator' };
      const actions = getAvailableActions(job, true);
      expect(actions).toContain('launch');
    });

    it('hides launch for non-orchestrator in Claude Code CLI mode', () => {
      const job = { status: 'waiting', agent_display_name: 'implementer' };
      const actions = getAvailableActions(job, true);
      expect(actions).not.toContain('launch');
    });

    it('shows launch for all agents in General CLI mode', () => {
      const job = { status: 'waiting', agent_display_name: 'implementer' };
      const actions = getAvailableActions(job, false);
      expect(actions).toContain('launch');
    });

    it('shows launch for non-waiting status in multi-terminal mode', () => {
      const job = { status: 'working', agent_display_name: 'orchestrator' };
      const actions = getAvailableActions(job, false);
      expect(actions).toContain('launch');
    });
  });

  describe('getAvailableActions - Hand Over Button', () => {
    it('shows hand over for working orchestrator', () => {
      const job = {
        status: 'working',
        agent_display_name: 'orchestrator',
      };
      const actions = getAvailableActions(job, false);
      expect(actions).toContain('handOver');
    });

    it('hides hand over for non-working orchestrator', () => {
      const job = {
        status: 'waiting',
        agent_display_name: 'orchestrator',
      };
      const actions = getAvailableActions(job, false);
      expect(actions).not.toContain('handOver');
    });

    it('hides hand over for non-orchestrator', () => {
      const job = {
        status: 'working',
        agent_display_name: 'implementer',
      };
      const actions = getAvailableActions(job, false);
      expect(actions).not.toContain('handOver');
    });
  });

  describe('getAvailableActions - Always Available Actions', () => {
    it('always shows copy prompt except for decommissioned', () => {
      const job = { status: 'working', agent_display_name: 'implementer' };
      const actions = getAvailableActions(job, false);
      expect(actions).toContain('copyPrompt');
    });

    it('hides copy prompt for decommissioned', () => {
      const job = { status: 'decommissioned', agent_display_name: 'implementer' };
      const actions = getAvailableActions(job, false);
      expect(actions).not.toContain('copyPrompt');
    });

    it('always shows view messages', () => {
      const job = { status: 'complete', agent_display_name: 'implementer' };
      const actions = getAvailableActions(job, false);
      expect(actions).toContain('viewMessages');
    });
  });
});
