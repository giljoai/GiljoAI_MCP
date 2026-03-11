# Agent State Transition Diagram

## State Transition Flow (Mermaid)

```mermaid
stateDiagram-v2
    [*] --> waiting: Job Created

    waiting --> preparing: Agent Acknowledges
    waiting --> failed: Initialization Error
    waiting --> cancelled: User Cancels
    
    preparing --> working: Environment Ready
    preparing --> failed: Preparation Error
    preparing --> cancelled: User Cancels
    
    working --> review: Work Complete
    working --> complete: Direct Complete
    working --> failed: Execution Error
    working --> blocked: Needs Input
    working --> cancelled: User Cancels
    
    review --> complete: Review Approved
    review --> working: Revisions Needed
    review --> failed: Review Rejected
    
    blocked --> working: report_progress()
    blocked --> cancelled: User Cancels
    blocked --> failed: Cannot Unblock
    
    complete --> [*]: Terminal
    failed --> [*]: Terminal
    cancelled --> [*]: Terminal
    decommissioned --> [*]: Terminal

    note right of waiting
        Agent awaiting acknowledgment
        Timeout: 2 minutes
    end note

    note right of preparing
        Agent setting up environment
        Loading context, tools
    end note

    note right of working
        Agent actively executing
        Updates progress regularly
    end note

    note right of review
        Work complete, awaiting
        human review/approval
    end note

    note right of blocked
        Agent needs human decision
        or additional input
    end note

    note right of complete
        TERMINAL STATE
        Mission accomplished
    end note

    note right of failed
        TERMINAL STATE
        Mission failed
    end note

    note right of cancelled
        TERMINAL STATE
        User cancelled work
    end note

    note right of decommissioned
        TERMINAL STATE
        Agent retired from project
    end note
```

## Transition Triggers

### User Actions
| From State | To State | Trigger | API Endpoint |
|-----------|----------|---------|--------------|
| waiting | cancelled | User cancels job | POST /{job_id}/cancel |
| preparing | cancelled | User cancels job | POST /{job_id}/cancel |
| working | cancelled | User cancels job | POST /{job_id}/cancel |
| blocked | cancelled | User gives up | POST /{job_id}/cancel |
| review | working | User requests revisions | POST /{job_id}/transition |
| review | complete | User approves work | POST /{job_id}/transition |
| review | failed | User rejects work | POST /{job_id}/transition |
| blocked | working | User provides input | POST /{job_id}/transition |
| * | decommissioned | User retires agent | POST /{job_id}/decommission |

### Agent Actions
| From State | To State | Trigger | MCP Tool |
|-----------|----------|---------|----------|
| waiting | preparing | Agent acknowledges | acknowledge_job() |
| preparing | working | Agent ready | update_job_status() |
| working | review | Agent completes work | update_job_status() |
| working | complete | Agent finishes | complete_job() |
| working | blocked | Agent needs help | update_job_status() |
| working | failed | Agent encounters error | fail_job() |

### System Events
| From State | To State | Trigger | Source |
|-----------|----------|---------|--------|
| waiting | failed | Timeout (2 min) | Health Monitor |
| preparing | failed | Timeout (5 min) | Health Monitor |
| working | blocked | Timeout (10 min) | Health Monitor |
| working | blocked | Health critical | Health Monitor |

## State Properties

### Active States

**waiting**
- Messages: Queued for delivery after acknowledgment
- Progress: 0%
- Can transition to: preparing, failed, cancelled
- Timeout: 2 minutes (configurable per agent type)

**preparing**
- Messages: Queued, agent may poll
- Progress: 0-10%
- Can transition to: working, failed, cancelled
- Timeout: 5 minutes

**working**
- Messages: Delivered immediately
- Progress: 10-99%
- Can transition to: review, complete, failed, blocked, cancelled
- Timeout: 10 minutes of no progress (configurable)

**review**
- Messages: Delivered (agent may be idle)
- Progress: 100%
- Can transition to: complete, working, failed
- No timeout (human review pending)

**blocked**
- Messages: Delivered with flag indicating blocked state
- Progress: Frozen at current value
- Can transition to: working, cancelled, failed
- No timeout (human action required)

### Terminal States

**complete**
- Messages: Blocked (auto-response: "Agent completed mission")
- Progress: 100%
- No further transitions
- Audit trail preserved

**failed**
- Messages: Blocked (auto-response: "Agent failed, review logs")
- Progress: Frozen at failure point
- No further transitions
- Error details in block_reason

**cancelled**
- Messages: Blocked (auto-response: "Agent cancelled by user")
- Progress: Frozen
- No further transitions
- Cancellation reason in block_reason

**decommissioned**
- Messages: Blocked (auto-response: "Agent retired from project")
- Progress: Final value preserved
- No further transitions
- Cannot be reactivated

## Error Recovery Paths

```mermaid
graph LR
    A[working] -->|Error| B{Recoverable?}
    B -->|Yes| C[blocked]
    B -->|No| D[failed]
    C -->|Input Provided| A
    C -->|Cannot Recover| D
    
    E[preparing] -->|Error| F{Critical?}
    F -->|Yes| D
    F -->|No| G[Retry]
    G -->|Success| H[working]
    G -->|Max Retries| D
```

## Message Interception Logic

```mermaid
sequenceDiagram
    participant O as Orchestrator
    participant MI as MessageInterceptor
    participant AJ as AgentJob
    
    O->>MI: send_message(job_id, content)
    MI->>AJ: Check job status
    
    alt Status is TERMINAL (complete/failed/cancelled/decommissioned)
        AJ-->>MI: Status: cancelled
        MI-->>O: Auto-response: "Agent cancelled by user"
        Note over MI,O: Message blocked, logged
    else Status is ACTIVE (working/review/blocked)
        AJ-->>MI: Status: working
        MI->>AJ: Append message to queue
        AJ-->>MI: Success
        MI-->>O: Message delivered
    end
```

