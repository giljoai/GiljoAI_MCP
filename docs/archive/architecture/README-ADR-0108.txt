ADR-0108: Unified Agent State Architecture - Summary

STATUS: Proposed
RISK: MEDIUM
TIMELINE: 4 weeks
RECOMMENDATION: APPROVE with phased rollout

PROBLEM:
- Dual models (Agent + MCPAgentJob) causing sync issues
- No explicit cancelled/decommissioned states
- No message interception for inactive agents
- Race conditions in state updates
- Health monitoring disconnected from states

SOLUTION:
Standardize on MCPAgentJob with 9 states, optimistic locking, message interception

9 STATUS STATES:

Active:
- waiting (awaiting ack)
- preparing (setting up)
- working (executing)
- review (awaiting review)
- blocked (needs input)

Terminal (no transitions):
- complete
- failed
- cancelled
- decommissioned

KEY FEATURES:
1. Optimistic locking (version field)
2. Message interception (block messages to terminal agents)
3. State audit trail (job_metadata.state_history)
4. Health integration (auto-transitions)
5. WebSocket events (real-time updates)

DOCUMENTS:
1. ADR-0108-unified-agent-state-architecture.md - Decision record
2. state-transition-diagram.md - Mermaid diagrams
3. database-schema-changes.md - SQL migrations
4. python-type-definitions.md - Code specs
5. implementation-guide.md - Step-by-step guide
6. migration-strategy.md - Rollout plan

TIMELINE:
Week 1: Database schema migration
Week 2: Core components + API
Week 3-4: Agent model deprecation

SUCCESS CRITERIA:
- Zero data loss
- All tests passing
- Performance < 100ms
- Zero production incidents

ARCHITECT: System Architect Agent
DATE: 2025-01-07
