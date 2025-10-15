# Handover 0019: Agent Job Management System

**Handover ID**: 0019
**Creation Date**: 2025-10-14
**Target Date**: 2025-10-28 (2 week timeline)
**Priority**: HIGH
**Type**: IMPLEMENTATION
**Status**: Not Started
**Dependencies**: Handover 0017 (Database Schema) must be completed first

---

## 1. Context and Background

**Purpose**: Implement agent job tracking separate from user tasks, enabling true multi-agent coordination with message passing and acknowledgment tracking.

**Current State**:
- Only user task tracking exists
- No agent-to-agent communication
- No job lifecycle management
- No message acknowledgment system

**Target State**:
- Complete agent job management system
- Agent-to-agent messaging with acknowledgments
- Job lifecycle tracking (pending → active → completed)
- Message queue with JSONB storage
- Coordination between multiple agents

---

## 2. Core Components to Build

### Component 1: Agent Job Manager

```python
class AgentJobManager:
    """Manage agent jobs separately from user tasks"""

    async def create_agent_job(
        self,
        tenant_key: str,
        agent_type: str,
        mission: str,
        context_chunks: List[str],
        spawned_by: str = "orchestrator"
    ) -> str:
        """Create new agent job in database"""

    async def update_job_status(
        self,
        tenant_key: str,
        job_id: str,
        status: str,
        metadata: Dict = None
    ):
        """Update job status with optional metadata"""

    async def get_active_jobs(self, tenant_key: str) -> List[Dict]:
        """Get all active jobs for tenant"""

    async def complete_job(
        self,
        tenant_key: str,
        job_id: str,
        final_state: Dict
    ):
        """Mark job as completed with final state"""
```

### Component 2: Agent Communication Queue

```python
class AgentCommunicationQueue:
    """Handle agent-to-agent messaging"""

    async def send_message(
        self,
        tenant_key: str,
        from_agent: str,
        to_agent: str,
        message: Dict,
        priority: str = "normal"
    ) -> str:
        """Send message between agents"""

    async def acknowledge_message(
        self,
        tenant_key: str,
        message_id: str,
        agent_id: str
    ):
        """Mark message as acknowledged by agent"""

    async def get_unacknowledged_messages(
        self,
        tenant_key: str,
        agent_id: str
    ) -> List[Dict]:
        """Get messages not yet acknowledged"""

    async def broadcast_message(
        self,
        tenant_key: str,
        from_agent: str,
        message: Dict
    ):
        """Broadcast to all active agents"""
```

### Component 3: Job Coordinator

```python
class JobCoordinator:
    """Coordinate multiple agent jobs"""

    async def coordinate_jobs(
        self,
        tenant_key: str,
        job_ids: List[str]
    ):
        """Monitor and coordinate multiple jobs"""

    async def handle_job_dependencies(
        self,
        tenant_key: str,
        job: Dict,
        dependencies: List[str]
    ):
        """Wait for dependencies before starting job"""

    async def spawn_continuation_agent(
        self,
        tenant_key: str,
        original_job_id: str,
        reason: str
    ):
        """Spawn new agent to continue work"""
```

---

## 3. Implementation Requirements

### Database Operations

1. **Job Creation and Updates**
   - Atomic job creation with unique IDs
   - Status transitions with timestamp tracking
   - Context chunk association

2. **Message Queue Implementation**
   - JSONB array for message storage
   - Acknowledgment tracking per agent
   - Message priority handling

3. **Multi-Tenant Isolation**
   - All queries filtered by tenant_key
   - No cross-tenant message leakage
   - Tenant-specific job queues

### API Endpoints

```python
# Agent job management
POST   /api/agent-jobs                 # Create new job
GET    /api/agent-jobs/active         # List active jobs
PATCH  /api/agent-jobs/{job_id}       # Update job status
GET    /api/agent-jobs/{job_id}       # Get job details

# Agent messaging
POST   /api/agent-messages             # Send message
POST   /api/agent-messages/broadcast   # Broadcast message
POST   /api/agent-messages/{id}/ack   # Acknowledge message
GET    /api/agent-messages/unread     # Get unacknowledged

# Coordination
POST   /api/agent-jobs/coordinate     # Start coordination
GET    /api/agent-jobs/dependencies   # Check dependencies
```

### WebSocket Integration

```python
# Real-time events
- agent_job_created
- agent_job_status_changed
- agent_message_received
- agent_message_acknowledged
- coordination_update
```

---

## 4. Testing Requirements

### Unit Tests
- Job creation and lifecycle
- Message queue operations
- Acknowledgment tracking
- Tenant isolation

### Integration Tests
- Complete job workflow
- Multi-agent messaging
- Dependency handling
- WebSocket notifications

### Performance Tests
- Handle 100+ concurrent jobs
- Message throughput testing
- JSONB query performance

---

## 5. Success Criteria

- [ ] Agent jobs tracked separately from tasks
- [ ] Agent-to-agent messaging functional
- [ ] Message acknowledgments prevent duplicates
- [ ] Job dependencies handled correctly
- [ ] WebSocket updates working
- [ ] Multi-tenant isolation verified
- [ ] Performance targets met

---

## 6. Deliverables

1. **AgentJobManager class** with full implementation
2. **AgentCommunicationQueue** with messaging
3. **JobCoordinator** for orchestration
4. **API endpoints** with documentation
5. **WebSocket event handlers**
6. **Comprehensive test suite**
7. **Performance benchmarks**

---

## 7. Getting Started

1. Review database schema from Handover 0017
2. Study existing task management for patterns
3. Implement core job manager first
4. Add messaging layer
5. Build coordination on top
6. Test thoroughly with multiple agents

---

**Handover Status**: Ready for implementation (after 0017)
**Estimated Effort**: 80 hours (2 weeks)
**Enables**: True multi-agent coordination