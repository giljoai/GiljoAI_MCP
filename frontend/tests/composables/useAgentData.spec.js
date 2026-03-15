import { describe, it, expect, beforeEach } from 'vitest'
import { ref } from 'vue'
import { useAgentData } from '@/composables/useAgentData'

/**
 * Test suite for useAgentData composable
 *
 * This composable extracts shared logic from AgentCardGrid and AgentCard
 * to prevent duplication between card and table views.
 *
 * Handover 0228: StatusBoardTable Component
 */
describe('useAgentData', () => {
  let agents

  beforeEach(() => {
    agents = ref([
      {
        id: 'agent-1',
        job_id: 'job-1',
        agent_name: 'Backend Agent',
        agent_display_name: 'implementer',
        status: 'working',
        progress: 50,
        messages_sent_count: 3,
        messages_waiting_count: 2,
        messages_read_count: 1,
        health_status: 'healthy'
      },
      {
        id: 'agent-2',
        job_id: 'job-2',
        agent_name: 'Test Agent',
        agent_display_name: 'tester',
        status: 'complete',
        progress: 100,
        messages_sent_count: 0,
        messages_waiting_count: 0,
        messages_read_count: 0,
        health_status: 'healthy'
      },
      {
        id: 'agent-3',
        job_id: 'job-3',
        agent_name: 'Orchestrator',
        agent_display_name: 'orchestrator',
        status: 'working',
        progress: 75,
        messages_sent_count: 1,
        messages_waiting_count: 0,
        messages_read_count: 0,
        health_status: 'critical'
      },
      {
        id: 'agent-4',
        job_id: 'job-4',
        agent_name: 'Waiting Agent',
        agent_display_name: 'analyzer',
        status: 'waiting',
        progress: 0,
        messages_sent_count: 0,
        messages_waiting_count: 0,
        messages_read_count: 0,
        health_status: 'healthy'
      },
      {
        id: 'agent-5',
        job_id: 'job-5',
        agent_name: 'Blocked Agent',
        agent_display_name: 'reviewer',
        status: 'blocked',
        progress: 30,
        messages_sent_count: 0,
        messages_waiting_count: 0,
        messages_read_count: 1,
        health_status: 'warning'
      }
    ])
  })

  describe('sortedAgents', () => {
    it('sorts agents by priority correctly (working > blocked > silent > waiting > complete > decommissioned)', () => {
      const { sortedAgents } = useAgentData(agents)

      // Based on AGENT_STATUS_PRIORITY: working=0, blocked=1, silent=2, waiting=3, complete=4
      expect(sortedAgents.value[0].status).toBe('working')
      expect(sortedAgents.value[1].status).toBe('working')
      expect(sortedAgents.value[2].status).toBe('blocked')
      expect(sortedAgents.value[3].status).toBe('waiting')
      expect(sortedAgents.value[4].status).toBe('complete')
    })

    it('places orchestrator first within same priority level', () => {
      const { sortedAgents } = useAgentData(agents)

      // Both agent-1 (implementer) and agent-3 (orchestrator) have status 'working'
      const workingAgents = sortedAgents.value.filter(a => a.status === 'working')
      expect(workingAgents[0].agent_display_name).toBe('orchestrator')
      expect(workingAgents[1].agent_display_name).toBe('implementer')
    })

    it('sorts alphabetically by name as tertiary sort', () => {
      agents.value = ref([
        { id: '1', agent_name: 'Zebra Agent', agent_display_name: 'implementer', status: 'working' },
        { id: '2', agent_name: 'Alpha Agent', agent_display_name: 'implementer', status: 'working' },
        { id: '3', agent_name: 'Beta Agent', agent_display_name: 'implementer', status: 'working' }
      ]).value

      const { sortedAgents } = useAgentData(agents)

      expect(sortedAgents.value[0].agent_name).toBe('Alpha Agent')
      expect(sortedAgents.value[1].agent_name).toBe('Beta Agent')
      expect(sortedAgents.value[2].agent_name).toBe('Zebra Agent')
    })

    it.skip('handles cancelled status correctly - cancelled not in AGENT_STATUS_PRIORITY', () => {
      // cancelled is not defined in the current AGENT_STATUS_PRIORITY constant
    })

    it('handles decommissioned status correctly (lowest priority)', () => {
      agents.value.push({
        id: 'agent-7',
        agent_name: 'Decommissioned Agent',
        agent_display_name: 'implementer',
        status: 'decommissioned',
        messages_sent_count: 0,
        messages_waiting_count: 0,
        messages_read_count: 0,
      })

      const { sortedAgents } = useAgentData(agents)

      const lastAgent = sortedAgents.value[sortedAgents.value.length - 1]
      expect(lastAgent.status).toBe('decommissioned')
    })
  })

  describe('getMessageCounts', () => {
    it('calculates message counts correctly using server-provided counters', () => {
      const { getMessageCounts } = useAgentData(agents)

      const job = agents.value[0] // Has sent=3, waiting=2, read=1
      const counts = getMessageCounts(job)

      expect(counts.sent).toBe(3)
      expect(counts.waiting).toBe(2)
      expect(counts.read).toBe(1)
    })

    it('handles job with no messages (zero counts)', () => {
      const { getMessageCounts } = useAgentData(agents)

      const job = agents.value[1] // All zeroes
      const counts = getMessageCounts(job)

      expect(counts.sent).toBe(0)
      expect(counts.waiting).toBe(0)
      expect(counts.read).toBe(0)
    })

    it('handles job with only read messages', () => {
      const { getMessageCounts } = useAgentData(agents)

      const job = agents.value[4] // Has read=1
      const counts = getMessageCounts(job)

      expect(counts.sent).toBe(0)
      expect(counts.waiting).toBe(0)
      expect(counts.read).toBe(1)
    })

    it('handles job with undefined counter fields', () => {
      const { getMessageCounts } = useAgentData(agents)

      const job = { id: 'no-counters' } // No counter fields
      const counts = getMessageCounts(job)

      expect(counts.sent).toBe(0)
      expect(counts.waiting).toBe(0)
      expect(counts.read).toBe(0)
    })
  })

  describe('getStatusColor', () => {
    it('returns correct color for waiting status', () => {
      const { getStatusColor } = useAgentData(agents)
      expect(getStatusColor('waiting')).toBe('grey')
    })

    it('returns correct color for working status', () => {
      const { getStatusColor } = useAgentData(agents)
      expect(getStatusColor('working')).toBe('blue')
    })

    it('returns correct color for blocked status', () => {
      const { getStatusColor } = useAgentData(agents)
      expect(getStatusColor('blocked')).toBe('orange')
    })

    it('returns correct color for complete status', () => {
      const { getStatusColor } = useAgentData(agents)
      expect(getStatusColor('complete')).toBe('green')
    })

    it('returns correct color for silent status', () => {
      const { getStatusColor } = useAgentData(agents)
      expect(getStatusColor('silent')).toBe('amber-darken-2')
    })

    it('returns correct color for decommissioned status', () => {
      const { getStatusColor } = useAgentData(agents)
      expect(getStatusColor('decommissioned')).toBe('grey-lighten-1')
    })

    it('returns grey for unknown status', () => {
      const { getStatusColor } = useAgentData(agents)
      expect(getStatusColor('unknown-status')).toBe('grey')
    })
  })

  describe('getAgentDisplayNameColor', () => {
    it('returns color config object for orchestrator', () => {
      const { getAgentDisplayNameColor } = useAgentData(agents)
      const color = getAgentDisplayNameColor('orchestrator')
      expect(color.hex).toBe('#D4A574')
      expect(color.name).toBe('ORCHESTRATOR')
    })

    it('returns color config object for analyzer', () => {
      const { getAgentDisplayNameColor } = useAgentData(agents)
      const color = getAgentDisplayNameColor('analyzer')
      expect(color.hex).toBe('#E74C3C')
      expect(color.name).toBe('ANALYZER')
    })

    it('returns color config object for implementer', () => {
      const { getAgentDisplayNameColor } = useAgentData(agents)
      const color = getAgentDisplayNameColor('implementer')
      expect(color.hex).toBe('#3498DB')
      expect(color.name).toBe('IMPLEMENTER')
    })

    it('returns color config object for tester', () => {
      const { getAgentDisplayNameColor } = useAgentData(agents)
      const color = getAgentDisplayNameColor('tester')
      expect(color.hex).toBe('#FFC300')
      expect(color.name).toBe('TESTER')
    })

    it('returns color config object for reviewer', () => {
      const { getAgentDisplayNameColor } = useAgentData(agents)
      const color = getAgentDisplayNameColor('reviewer')
      expect(color.hex).toBe('#9B59B6')
      expect(color.name).toBe('REVIEWER')
    })

    it('returns orchestrator color for unknown agent type', () => {
      const { getAgentDisplayNameColor } = useAgentData(agents)
      const color = getAgentDisplayNameColor('unknown-type')
      expect(color.hex).toBe('#D4A574')
    })
  })

  describe('getAgentAbbreviation', () => {
    it('returns two-letter abbreviation from hyphenated name', () => {
      const { getAgentAbbreviation } = useAgentData(agents)
      expect(getAgentAbbreviation('backend-implementer')).toBe('BI')
    })

    it('returns first two uppercase letters for single word', () => {
      const { getAgentAbbreviation } = useAgentData(agents)
      expect(getAgentAbbreviation('custom')).toBe('CU')
      expect(getAgentAbbreviation('builder')).toBe('BU')
    })

    it('returns ?? for empty/null display name', () => {
      const { getAgentAbbreviation } = useAgentData(agents)
      expect(getAgentAbbreviation('')).toBe('??')
      expect(getAgentAbbreviation(null)).toBe('??')
      expect(getAgentAbbreviation(undefined)).toBe('??')
    })

    it('handles underscore-separated names', () => {
      const { getAgentAbbreviation } = useAgentData(agents)
      expect(getAgentAbbreviation('backend_tester')).toBe('BT')
    })

    it('handles space-separated names', () => {
      const { getAgentAbbreviation } = useAgentData(agents)
      expect(getAgentAbbreviation('Backend Tester')).toBe('BT')
    })
  })

  describe('getHealthColor', () => {
    it('returns correct color for healthy status', () => {
      const { getHealthColor } = useAgentData(agents)
      expect(getHealthColor('healthy')).toBe('success')
    })

    it('returns correct color for warning status', () => {
      const { getHealthColor } = useAgentData(agents)
      expect(getHealthColor('warning')).toBe('warning')
    })

    it('returns correct color for critical status', () => {
      const { getHealthColor } = useAgentData(agents)
      expect(getHealthColor('critical')).toBe('error')
    })

    it('returns correct color for timeout status', () => {
      const { getHealthColor } = useAgentData(agents)
      expect(getHealthColor('timeout')).toBe('error')
    })

    it('returns correct color for unknown status', () => {
      const { getHealthColor } = useAgentData(agents)
      expect(getHealthColor('unknown')).toBe('grey')
    })

    it('returns grey for undefined status', () => {
      const { getHealthColor } = useAgentData(agents)
      expect(getHealthColor(undefined)).toBe('grey')
    })
  })

  describe('getHealthIcon', () => {
    it('returns correct icon for healthy status', () => {
      const { getHealthIcon } = useAgentData(agents)
      expect(getHealthIcon('healthy')).toBe('mdi-check-circle')
    })

    it('returns correct icon for warning status', () => {
      const { getHealthIcon } = useAgentData(agents)
      expect(getHealthIcon('warning')).toBe('mdi-alert')
    })

    it('returns correct icon for critical status', () => {
      const { getHealthIcon } = useAgentData(agents)
      expect(getHealthIcon('critical')).toBe('mdi-alert-octagon')
    })

    it('returns correct icon for timeout status', () => {
      const { getHealthIcon } = useAgentData(agents)
      expect(getHealthIcon('timeout')).toBe('mdi-timer-alert')
    })

    it('returns correct icon for unknown status', () => {
      const { getHealthIcon } = useAgentData(agents)
      expect(getHealthIcon('unknown')).toBe('mdi-help-circle')
    })

    it('returns help-circle for undefined status', () => {
      const { getHealthIcon } = useAgentData(agents)
      expect(getHealthIcon(undefined)).toBe('mdi-help-circle')
    })
  })

  describe('Reactive Updates', () => {
    it('updates sortedAgents when agents array changes', () => {
      const { sortedAgents } = useAgentData(agents)

      expect(sortedAgents.value).toHaveLength(5)

      // Add new agent
      agents.value.push({
        id: 'agent-6',
        agent_name: 'New Agent',
        agent_display_name: 'implementer',
        status: 'working',
        messages_sent_count: 0,
        messages_waiting_count: 0,
        messages_read_count: 0,
      })

      expect(sortedAgents.value).toHaveLength(6)
    })

    it('re-sorts when agent status changes', () => {
      const { sortedAgents } = useAgentData(agents)

      // Initially complete is last sorted status
      expect(sortedAgents.value[sortedAgents.value.length - 1].status).toBe('complete')

      // Change complete agent to working
      agents.value[1].status = 'working'

      // Should now have more working agents
      const workingAgents = sortedAgents.value.filter(a => a.status === 'working')
      expect(workingAgents).toHaveLength(3)
      expect(workingAgents.some(a => a.agent_name === 'Test Agent')).toBe(true)
    })
  })
})
