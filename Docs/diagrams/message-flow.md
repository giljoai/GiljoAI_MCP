# Message Flow and Communication Patterns

## Message Queue Architecture and Flow

This diagram details the message-driven communication system that enables coordination between all agents in the GiljoAI MCP orchestrator.

## Message Flow Overview

```mermaid
flowchart TB
    %% Define styles matching color themes
    classDef primary fill:#ffc300,stroke:#0e1c2d,stroke-width:3px,color:#0e1c2d
    classDef secondary fill:#315074,stroke:#e1e1e1,stroke-width:2px,color:#e1e1e1
    classDef surface fill:#1e3147,stroke:#315074,stroke-width:2px,color:#e1e1e1
    classDef success fill:#67bd6d,stroke:#0e1c2d,stroke-width:2px,color:#0e1c2d
    classDef special fill:#8b5cf6,stroke:#e1e1e1,stroke-width:2px,color:#e1e1e1
    classDef danger fill:#c6298c,stroke:#e1e1e1,stroke-width:2px,color:#e1e1e1
    classDef info fill:#8f97b7,stroke:#315074,stroke-width:1px,color:#e1e1e1

    %% Message Sources
    subgraph SOURCES[" 📤 Message Sources "]
        USER[User Interface<br/>CLI/Dashboard]:::primary
        ORCH[Orchestrator<br/>Coordination]:::special
        AGENT[Agent<br/>Worker/Specialist]:::secondary
        SYSTEM[System<br/>Events/Alerts]:::info
    end

    %% Message Router
    ROUTER[Message Router<br/>Priority Handler]:::special

    %% Message Types
    subgraph TYPES[" 📨 Message Types "]
        DIRECT[Direct Message<br/>Point-to-Point]:::secondary
        BROADCAST[Broadcast<br/>All Agents]:::primary
        TASK[Task Assignment<br/>Work Item]:::success
        HANDOFF[Handoff Request<br/>Context Transfer]:::info
        STATUS[Status Update<br/>Progress Report]:::info
        ERROR[Error Report<br/>Exception Alert]:::danger
    end

    %% Message Queue
    subgraph QUEUE[" 🗂️ Message Queue "]
        HIGH[High Priority<br/>Urgent/Blocking]:::danger
        NORMAL[Normal Priority<br/>Standard Flow]:::secondary
        LOW[Low Priority<br/>Non-Critical]:::info

        HIGH --> PROCESSOR
        NORMAL --> PROCESSOR
        LOW --> PROCESSOR
    end

    %% Message Processing
    PROCESSOR[Queue Processor<br/>FIFO + Priority]:::special

    %% Database Operations
    subgraph DATABASE[" 💾 Database Operations "]
        PERSIST[Persist Message<br/>SQLAlchemy ORM]:::surface
        ACK_ARRAY[Update Acknowledgment<br/>Array]:::surface
        STATUS_UPDATE[Update Status<br/>pending/delivered/acknowledged]:::surface
        ARCHIVE[Archive Old<br/>Messages]:::surface
    end

    %% Delivery
    subgraph DELIVERY[" 📥 Message Delivery "]
        CHECK_AGENT{Agent<br/>Available?}:::info
        DELIVER[Deliver to Agent<br/>Update Status]:::success
        RETRY[Retry Queue<br/>Exponential Backoff]:::info
        DLQ[Dead Letter Queue<br/>Failed Messages]:::danger
    end

    %% Agent Processing
    subgraph AGENT_PROCESS[" ⚙️ Agent Processing "]
        RECEIVE[Receive Message]:::secondary
        VALIDATE[Validate Format]:::info
        ACK_MSG[Acknowledge Receipt]:::success
        PROCESS_MSG[Process Content]:::success
        COMPLETE[Mark Complete<br/>Send Result]:::success
    end

    %% Flow Connections
    SOURCES --> ROUTER
    ROUTER --> TYPES
    TYPES --> QUEUE
    PROCESSOR --> DATABASE
    DATABASE --> CHECK_AGENT
    CHECK_AGENT -->|Yes| DELIVER
    CHECK_AGENT -->|No| RETRY
    RETRY -->|Max Retries| DLQ
    DELIVER --> AGENT_PROCESS
    AGENT_PROCESS --> COMPLETE
    COMPLETE --> DATABASE
```

## Message Lifecycle

```mermaid
stateDiagram-v2
    classDef pending fill:#ffc300,color:#0e1c2d
    classDef active fill:#67bd6d,color:#0e1c2d
    classDef error fill:#c6298c,color:#e1e1e1
    classDef complete fill:#315074,color:#e1e1e1

    [*] --> Created: send_message()
    Created --> Queued: enqueue()
    Queued --> Processing: dequeue()
    Processing --> Delivered: agent_available()
    Processing --> Retry: agent_unavailable()
    Retry --> Processing: backoff_complete()
    Retry --> Failed: max_retries()
    Delivered --> Acknowledged: acknowledge_message()
    Acknowledged --> InProgress: agent_processing()
    InProgress --> Completed: complete_message()
    InProgress --> Error: processing_failed()
    Error --> Retry: retry_allowed()
    Error --> Failed: retry_exhausted()
    Completed --> Archived: archive_old()
    Failed --> DeadLetter: move_to_dlq()
    Archived --> [*]
    DeadLetter --> [*]

    class Created,Queued pending
    class Processing,Delivered,Acknowledged,InProgress active
    class Error,Retry,Failed,DeadLetter error
    class Completed,Archived complete
```

## Message Priority System

```mermaid
graph TD
    %% Define styles
    classDef critical fill:#c6298c,stroke:#e1e1e1,color:#e1e1e1
    classDef high fill:#ffc300,stroke:#0e1c2d,color:#0e1c2d
    classDef normal fill:#67bd6d,stroke:#0e1c2d,color:#0e1c2d
    classDef low fill:#315074,stroke:#e1e1e1,color:#e1e1e1

    subgraph PRIORITY[" Priority Levels "]
        C[CRITICAL<br/>System Failures<br/>Blocking Issues<br/>Process: Immediate]:::critical
        H[HIGH<br/>Orchestrator Commands<br/>Handoffs<br/>Process: <1 min]:::high
        N[NORMAL<br/>Task Assignments<br/>Status Updates<br/>Process: <5 min]:::normal
        L[LOW<br/>Info Messages<br/>Logs<br/>Process: When Available]:::low
    end

    subgraph PROCESSING[" Processing Order "]
        QUEUE[Message Queue]
        C --> QUEUE
        H --> QUEUE
        N --> QUEUE
        L --> QUEUE

        QUEUE --> PROC[Processor]
        PROC --> OUTPUT[To Agents]
    end
```

## Communication Patterns

### 1. Direct Communication

```mermaid
sequenceDiagram
    participant A as Agent A
    participant Q as Message Queue
    participant DB as Database
    participant B as Agent B

    A->>Q: send_message(to: B, content)
    Q->>DB: persist_message()
    DB-->>Q: message_id
    Q->>B: deliver_message()
    B->>Q: acknowledge_message(id)
    Q->>DB: update_acknowledgment[]
    B->>B: process_message()
    B->>Q: complete_message(id, result)
    Q->>DB: update_status(completed)
```

### 2. Broadcast Pattern

```mermaid
sequenceDiagram
    participant O as Orchestrator
    participant Q as Message Queue
    participant A as Agent A
    participant B as Agent B
    participant C as Agent C

    O->>Q: broadcast(content, priority)
    Q->>Q: create_message_for_all()
    par Parallel Delivery
        Q->>A: deliver_broadcast()
        and
        Q->>B: deliver_broadcast()
        and
        Q->>C: deliver_broadcast()
    end
    A->>Q: acknowledge()
    B->>Q: acknowledge()
    C->>Q: acknowledge()
```

### 3. Task Assignment Pattern

```mermaid
sequenceDiagram
    participant O as Orchestrator
    participant Q as Message Queue
    participant W as Worker Agent
    participant DB as Database

    O->>Q: assign_job(agent, tasks[])
    Q->>DB: create_job_record()
    Q->>W: deliver_job_message()
    W->>Q: acknowledge_job()

    loop For Each Task
        W->>W: execute_task()
        W->>Q: update_progress()
        Q->>DB: persist_progress()
        Q->>O: notify_progress()
    end

    W->>Q: complete_job(results)
    Q->>DB: update_job_completed()
    Q->>O: notify_completion()
```

### 4. Handoff Pattern

```mermaid
sequenceDiagram
    participant A as Agent A
    participant Q as Message Queue
    participant O as Orchestrator
    participant B as Agent B

    A->>A: detect_context_limit()
    A->>Q: request_handoff(context)
    Q->>O: handoff_alert()
    O->>O: select_target_agent()
    O->>B: ensure_agent(B)
    O->>Q: handoff(from: A, to: B, context)
    Q->>B: deliver_context()
    B->>Q: acknowledge_handoff()
    Q->>A: confirm_transfer()
    A->>A: decommission()
```

## Message Format Specification

```mermaid
classDiagram
    class Message {
        +UUID id
        +UUID project_id
        +String from_agent
        +String[] to_agents
        +String type
        +String subject
        +JSON content
        +String priority
        +String status
        +String[] acknowledged_by
        +DateTime created_at
        +DateTime delivered_at
        +DateTime completed_at
        +JSON metadata
    }

    class MessageType {
        <<enumeration>>
        DIRECT
        BROADCAST
        TASK
        HANDOFF
        STATUS
        ERROR
        SYSTEM
    }

    class Priority {
        <<enumeration>>
        CRITICAL
        HIGH
        NORMAL
        LOW
    }

    class Status {
        <<enumeration>>
        PENDING
        QUEUED
        DELIVERED
        ACKNOWLEDGED
        IN_PROGRESS
        COMPLETED
        ERROR
        FAILED
    }

    Message --> MessageType : has
    Message --> Priority : has
    Message --> Status : has
```

## Performance Metrics

```mermaid
graph LR
    subgraph METRICS[" 📊 Key Performance Indicators "]
        THROUGHPUT[Message Throughput<br/>Target: 1000/sec]
        LATENCY[Delivery Latency<br/>Target: <100ms]
        ACK_TIME[Acknowledgment Time<br/>Target: <500ms]
        QUEUE_DEPTH[Queue Depth<br/>Alert: >10000]
        RETRY_RATE[Retry Rate<br/>Alert: >5%]
        DLQ_RATE[DLQ Rate<br/>Alert: >1%]
    end
```

## Error Handling Strategy

```mermaid
flowchart TB
    classDef error fill:#c6298c,stroke:#e1e1e1,color:#e1e1e1
    classDef warning fill:#ffc300,stroke:#0e1c2d,color:#0e1c2d
    classDef success fill:#67bd6d,stroke:#0e1c2d,color:#0e1c2d

    ERROR[Message Error]:::error

    ERROR --> TYPE{Error Type}

    TYPE -->|Network| RETRY1[Retry with<br/>Exponential Backoff]:::warning
    TYPE -->|Agent Unavailable| RETRY2[Queue for<br/>Later Delivery]:::warning
    TYPE -->|Invalid Format| REJECT[Reject Message<br/>Log Error]:::error
    TYPE -->|Processing Failed| RETRY3[Retry with<br/>New Agent]:::warning

    RETRY1 --> CHECK1{Success?}
    RETRY2 --> CHECK2{Success?}
    RETRY3 --> CHECK3{Success?}

    CHECK1 -->|Yes| SUCCESS[Message Delivered]:::success
    CHECK1 -->|No| DLQ1[Dead Letter Queue]:::error

    CHECK2 -->|Yes| SUCCESS
    CHECK2 -->|No| DLQ2[Dead Letter Queue]:::error

    CHECK3 -->|Yes| SUCCESS
    CHECK3 -->|No| DLQ3[Dead Letter Queue]:::error
```

## Acknowledgment Array System

The acknowledgment array tracks which agents have received and processed broadcast messages:

```python
# Example acknowledgment array structure
{
    "message_id": "uuid-1234",
    "type": "broadcast",
    "acknowledged_by": [
        "orchestrator",      # First to acknowledge
        "agent_analyzer",    # Second
        "agent_developer",   # Third
        "agent_tester"      # Fourth
    ],
    "pending_acknowledgment": [
        "agent_reviewer",    # Not yet acknowledged
        "agent_deployer"    # Not yet acknowledged
    ]
}
```

## Key Features

### 🚀 High Performance

- **Database-First Design**: ACID compliance with PostgreSQL
- **Priority Queue**: Critical messages processed first
- **Batch Processing**: Efficient bulk operations
- **Connection Pooling**: Optimized database connections

### 🔒 Reliability

- **Acknowledgment Arrays**: Track message delivery
- **Retry Logic**: Exponential backoff for failures
- **Dead Letter Queue**: Handle undeliverable messages
- **Transaction Support**: Atomic operations

### 📊 Observability

- **Message Tracing**: Full audit trail
- **Performance Metrics**: Real-time monitoring
- **Status Tracking**: Complete lifecycle visibility
- **Error Reporting**: Detailed failure analysis

### 🔄 Scalability

- **Horizontal Scaling**: Add more workers
- **Redis Cache**: Optional performance boost
- **Async Processing**: Non-blocking operations
- **Batch Operations**: Efficient bulk handling

## References

- Message Queue Guide: [`docs/MESSAGE_QUEUE_GUIDE.md`](../MESSAGE_QUEUE_GUIDE.md)
- Database Schema: [`src/giljo_mcp/models.py`](../../src/giljo_mcp/models.py)
- API Documentation: [`docs/manuals/MCP_TOOLS_MANUAL.md`](../manuals/MCP_TOOLS_MANUAL.md)
