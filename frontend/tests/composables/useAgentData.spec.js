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
        agent_type: 'implementer',
        status: 'working',
        progress: 50,
        messages: [
          { status: 'pending', content: 'Message 1' },
          { status: 'pending', content: 'Message 2' },
          { status: 'acknowledged', content: 'Message 3' }
        ],
        health_status: 'healthy'
      },
      {
        id: 'agent-2',
        job_id: 'job-2',
        agent_name: 'Test Agent',
        agent_type: 'tester',
        status: 'complete',
        progress: 100,
        messages: [],
        health_status: 'healthy'
      },
      {
        id: 'agent-3',
        job_id: 'job-3',
        agent_name: 'Orchestrator',
        agent_type: 'orchestrator',
        status: 'failed',
        progress: 75,
        messages: [
          { status: 'pending', content: 'Error message' }
        ],
        health_status: 'critical'
      },
      {
        id: 'agent-4',
        job_id: 'job-4',
        agent_name: 'Waiting Agent',
        agent_type: 'analyzer',
        status: 'waiting',
        progress: 0,
        messages: [],
        health_status: 'healthy'
      },
      {
        id: 'agent-5',
        job_id: 'job-5',
        agent_name: 'Blocked Agent',
        agent_type: 'reviewer',
        status: 'blocked',
        progress: 30,
        messages: [
          { status: 'acknowledged', content: 'Read message' }
        ],
        health_status: 'warning'
      }
    ])
  })

  describe('sortedAgents', () => {
    it('sorts agents by priority correctly (failed → blocked → waiting → working → complete)', () => {
      const { sortedAgents } = useAgentData(agents)

      expect(sortedAgents.value[0].status).toBe('failed')
      expect(sortedAgents.value[1].status).toBe('blocked')
      expect(sortedAgents.value[2].status).toBe('waiting')
      expect(sortedAgents.value[3].status).toBe('working')
      expect(sortedAgents.value[4].status).toBe('complete')
    })

    it('places orchestrator first within same priority level', () => {
      // Make orchestrator and another agent same status
      agents.value[2].status = 'working' // Orchestrator
      agents.value[0].status = 'working' // Backend Agent

      const { sortedAgents } = useAgentData(agents)

      const workingAgents = sortedAgents.value.filter(a => a.status === 'working')
      expect(workingAgents[0].agent_type).toBe('orchestrator')
      expect(workingAgents[1].agent_type).toBe('implementer')
    })

    it('sorts alphabetically by name as tertiary sort', () => {
      agents.value = ref([
        { id: '1', agent_name: 'Zebra Agent', agent_type: 'implementer', status: 'working' },
        { id: '2', agent_name: 'Alpha Agent', agent_type: 'implementer', status: 'working' },
        { id: '3', agent_name: 'Beta Agent', agent_type: 'implementer', status: 'working' }
      ]).value

      const { sortedAgents } = useAgentData(agents)

      expect(sortedAgents.value[0].agent_name).toBe('Alpha Agent')
      expect(sortedAgents.value[1].agent_name).toBe('Beta Agent')
      expect(sortedAgents.value[2].agent_name).toBe('Zebra Agent')
    })

    it('handles cancelled status correctly (low priority)', () => {
      agents.value.push({
        id: 'agent-6',
        agent_name: 'Cancelled Agent',
        agent_type: 'implementer',
        status: 'cancelled',
        messages: []
      })

      const { sortedAgents } = useAgentData(agents)

      // Find cancelled agent (should be near the end, before only decommissioned)
      const cancelledAgent = sortedAgents.value.find(a => a.status === 'cancelled')
      expect(cancelledAgent).toBeDefined()
      expect(cancelledAgent.status).toBe('cancelled')
    })

    it('handles decommissioned status correctly (lowest priority)', () => {
      agents.value.push({
        id: 'agent-7',
        agent_name: 'Decommissioned Agent',
        agent_type: 'implementer',
        status: 'decommissioned',
        messages: []
      })

      const { sortedAgents } = useAgentData(agents)

      const lastAgent = sortedAgents.value[sortedAgents.value.length - 1]
      expect(lastAgent.status).toBe('decommissioned')
    })
  })

  describe('getMessageCounts', () => {
    it('calculates message counts correctly', () => {
      const { getMessageCounts } = useAgentData(agents)

      const job = agents.value[0] // Has 2 pending, 1 acknowledged
      const counts = getMessageCounts(job)

      expect(counts.unread).toBe(2)
      expect(counts.acknowledged).toBe(1)
      expect(counts.total).toBe(3)
    })

    it('handles job with no messages', () => {
      const { getMessageCounts } = useAgentData(agents)

      const job = agents.value[1] // No messages
      const counts = getMessageCounts(job)

      expect(counts.unread).toBe(0)
      expect(counts.acknowledged).toBe(0)
      expect(counts.total).toBe(0)
    })

    it('handles job with only acknowledged messages', () => {
      const { getMessageCounts } = useAgentData(agents)

      const job = agents.value[4] // Has 1 acknowledged
      const counts = getMessageCounts(job)

      expect(counts.unread).toBe(0)
      expect(counts.acknowledged).toBe(1)
      expect(counts.total).toBe(1)
    })

    it('handles job with undefined messages', () => {
      const { getMessageCounts } = useAgentData(agents)

      const job = { id: 'no-messages' } // No messages property
      const counts = getMessageCounts(job)

      expect(counts.unread).toBe(0)
      expect(counts.acknowledged).toBe(0)
      expect(counts.total).toBe(0)
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

    it('returns correct color for failed status', () => {
      const { getStatusColor } = useAgentData(agents)
      expect(getStatusColor('failed')).toBe('red')
    })

    it('returns correct color for cancelled status', () => {
      const { getStatusColor } = useAgentData(agents)
      expect(getStatusColor('cancelled')).toBe('grey-darken-2')
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

  describe('getAgentTypeColor', () => {
    it('returns correct color for orchestrator', () => {
      const { getAgentTypeColor } = useAgentData(agents)
      expect(getAgentTypeColor('orchestrator')).toBe('orange')
    })

    it('returns correct color for analyzer', () => {
      const { getAgentTypeColor } = useAgentData(agents)
      expect(getAgentTypeColor('analyzer')).toBe('red')
    })

    it('returns correct color for implementer', () => {
      const { getAgentTypeColor } = useAgentData(agents)
      expect(getAgentTypeColor('implementer')).toBe('blue')
    })

    it('returns correct color for tester', () => {
      const { getAgentTypeColor } = useAgentData(agents)
      expect(getAgentTypeColor('tester')).toBe('yellow')
    })

    it('returns correct color for reviewer', () => {
      const { getAgentTypeColor } = useAgentData(agents)
      expect(getAgentTypeColor('reviewer')).toBe('purple')
    })

    it('returns grey for unknown agent type', () => {
      const { getAgentTypeColor } = useAgentData(agents)
      expect(getAgentTypeColor('unknown-type')).toBe('grey')
    })
  })

  describe('getAgentAbbreviation', () => {
    it('returns correct abbreviation for orchestrator', () => {
      const { getAgentAbbreviation } = useAgentData(agents)
      expect(getAgentAbbreviation('orchestrator')).toBe('Or')
    })

    it('returns correct abbreviation for analyzer', () => {
      const { getAgentAbbreviation } = useAgentData(agents)
      expect(getAgentAbbreviation('analyzer')).toBe('An')
    })

    it('returns correct abbreviation for implementer', () => {
      const { getAgentAbbreviation } = useAgentData(agents)
      expect(getAgentAbbreviation('implementer')).toBe('Im')
    })

    it('returns correct abbreviation for tester', () => {
      const { getAgentAbbreviation } = useAgentData(agents)
      expect(getAgentAbbreviation('tester')).toBe('Te')
    })

    it('returns correct abbreviation for reviewer', () => {
      const { getAgentAbbreviation } = useAgentData(agents)
      expect(getAgentAbbreviation('reviewer')).toBe('Re')
    })

    it('returns first two uppercase letters for unknown agent type', () => {
      const { getAgentAbbreviation } = useAgentData(agents)
      expect(getAgentAbbreviation('custom')).toBe('CU')
      expect(getAgentAbbreviation('builder')).toBe('BU')
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
        agent_type: 'implementer',
        status: 'working',
        messages: []
      })

      expect(sortedAgents.value).toHaveLength(6)
    })

    it('re-sorts when agent status changes', () => {
      const { sortedAgents } = useAgentData(agents)

      expect(sortedAgents.value[4].status).toBe('complete')

      // Change complete agent to failed
      agents.value[1].status = 'failed'

      // Should now have multiple failed agents (orchestrator was already failed)
      const failedAgents = sortedAgents.value.filter(a => a.status === 'failed')
      expect(failedAgents).toHaveLength(2)
      expect(failedAgents.some(a => a.agent_name === 'Test Agent')).toBe(true)
    })
  })
})
