# Agent Orchestration Flow

## Agent Lifecycle and Interaction Patterns

This diagram illustrates how agents are created, coordinated, and interact within the GiljoAI MCP system.

## Agent Orchestration Flow

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

    %% Start
    START([User Creates Project]):::primary

    %% Project Initialization
    INIT[Initialize Project<br/>Generate Tenant Key]:::secondary
    VISION[Load Vision Documents<br/>Chunk if >50K tokens]:::surface
    TEMPLATE[Load Agent Templates<br/>From Database]:::surface

    %% Orchestrator Activation
    ORCH_CREATE[Spawn Orchestrator Agent<br/>Assign Mission]:::special
    ORCH_ANALYZE[Orchestrator Analyzes<br/>Project Requirements]:::special

    %% Planning Phase
    PLAN[Create Execution Plan<br/>Define Agent Pipeline]:::success
    IDENTIFY[Identify Required Agents<br/>Match to Templates]:::success

    %% Agent Spawning
    subgraph SPAWN[" 🚀 Agent Spawning Process "]
        CHECK_EXIST{Agent Exists?}:::info
        CREATE_NEW[Create New Agent<br/>Allocate Resources]:::secondary
        REUSE[Reuse Existing Agent<br/>Clear Old Context]:::secondary
        ASSIGN_MISSION[Assign Mission<br/>Set Context Budget]:::success
    end

    %% Agent Execution
    subgraph EXECUTE[" ⚙️ Agent Execution Loop "]
        RECEIVE_MSG[Receive Message<br/>From Queue]:::secondary
        ACK[Acknowledge Message<br/>Update Status]:::info
        PROCESS[Process Task<br/>Execute Tools]:::success
        CONTEXT_CHECK{Context<br/>Limit?}:::danger
        COMPLETE_TASK[Complete Task<br/>Update Results]:::success
    end

    %% Inter-Agent Communication
    subgraph COMM[" 💬 Communication Flow "]
        SEND_MSG[Send Message<br/>To Target Agent]:::secondary
        ROUTE[Message Router<br/>Priority Queue]:::special
        BROADCAST[Broadcast Update<br/>All Agents]:::special
    end

    %% Handoff Process
    subgraph HANDOFF[" 🤝 Agent Handoff "]
        PREPARE_HANDOFF[Prepare Context<br/>Summary]:::secondary
        TRANSFER[Transfer Work<br/>To Next Agent]:::success
        DECOMMISSION[Decommission<br/>Release Resources]:::info
    end

    %% Monitoring
    subgraph MONITOR[" 📊 Health Monitoring "]
        HEALTH_CHECK[Check Agent Health<br/>Context Usage]:::info
        ALERT{Critical<br/>State?}:::danger
        INTERVENE[Orchestrator<br/>Intervention]:::special
    end

    %% Project Completion
    COLLECT[Collect Results<br/>From All Agents]:::success
    SUMMARY[Generate Summary<br/>Close Project]:::primary
    END([Project Complete]):::primary

    %% Flow connections
    START --> INIT
    INIT --> VISION
    VISION --> TEMPLATE
    TEMPLATE --> ORCH_CREATE
    ORCH_CREATE --> ORCH_ANALYZE
    ORCH_ANALYZE --> PLAN
    PLAN --> IDENTIFY

    IDENTIFY --> CHECK_EXIST
    CHECK_EXIST -->|No| CREATE_NEW
    CHECK_EXIST -->|Yes| REUSE
    CREATE_NEW --> ASSIGN_MISSION
    REUSE --> ASSIGN_MISSION

    ASSIGN_MISSION --> RECEIVE_MSG
    RECEIVE_MSG --> ACK
    ACK --> PROCESS
    PROCESS --> CONTEXT_CHECK
    CONTEXT_CHECK -->|OK| COMPLETE_TASK
    CONTEXT_CHECK -->|Near Limit| PREPARE_HANDOFF
    COMPLETE_TASK --> SEND_MSG

    SEND_MSG --> ROUTE
    ROUTE --> RECEIVE_MSG
    ROUTE --> BROADCAST

    PREPARE_HANDOFF --> TRANSFER
    TRANSFER --> DECOMMISSION
    TRANSFER --> CHECK_EXIST

    PROCESS --> HEALTH_CHECK
    HEALTH_CHECK --> ALERT
    ALERT -->|Yes| INTERVENE
    ALERT -->|No| PROCESS
    INTERVENE --> ORCH_ANALYZE

    COMPLETE_TASK -->|All Done| COLLECT
    COLLECT --> SUMMARY
    SUMMARY --> END
```

## Agent State Diagram

```mermaid
stateDiagram-v2
    classDef active fill:#67bd6d,color:#0e1c2d
    classDef pending fill:#ffc300,color:#0e1c2d
    classDef error fill:#c6298c,color:#e1e1e1
    classDef inactive fill:#315074,color:#e1e1e1

    [*] --> Created: spawn_agent()
    Created --> Active: assign_job()
    Active --> Processing: receive_message()
    Processing --> Active: complete_message()
    Processing --> Blocked: context_limit()
    Blocked --> Handoff: prepare_handoff()
    Handoff --> Decommissioned: transfer_complete()
    Active --> Idle: no_messages()
    Idle --> Active: new_message()
    Active --> Failed: error_state()
    Failed --> Active: retry()
    Active --> Completed: all_tasks_done()
    Completed --> Decommissioned: cleanup()
    Decommissioned --> [*]

    class Active active
    class Processing active
    class Idle pending
    class Failed error
    class Blocked error
    class Created,Handoff,Completed,Decommissioned inactive
```

## Agent Communication Patterns

```mermaid
sequenceDiagram
    participant U as User
    participant O as Orchestrator
    participant W1 as Worker Agent 1
    participant W2 as Worker Agent 2
    participant S as Serena MCP
    participant Q as Message Queue

    %% Project Start
    U->>O: Create Project
    activate O
    O->>O: Analyze Requirements
    O->>Q: Queue Agent Creation

    %% Spawn Agents
    O->>W1: Spawn with Mission
    activate W1
    O->>W2: Spawn with Mission
    activate W2

    %% Task Assignment
    O->>Q: Assign Tasks
    Q->>W1: Deliver Task 1
    Q->>W2: Deliver Task 2

    %% Agent Work
    W1->>W1: Process Task
    W1->>S: Request Guidance
    S-->>W1: Provide Analysis
    W1->>Q: Send Progress
    Q->>O: Deliver Update

    %% Inter-Agent Communication
    W1->>Q: Send to W2
    Q->>W2: Deliver Message
    W2->>W2: Process Message
    W2->>Q: Acknowledge

    %% Handoff
    W1->>W1: Near Context Limit
    W1->>Q: Request Handoff
    Q->>O: Handoff Alert
    O->>W2: Transfer Context
    W1->>W1: Decommission
    deactivate W1

    %% Completion
    W2->>Q: Task Complete
    Q->>O: All Tasks Done
    O->>U: Project Summary
    deactivate W2
    deactivate O
```

## Agent Pipeline Examples

### Example 1: Code Implementation Pipeline

```mermaid
graph LR
    classDef analyzer fill:#8b5cf6,stroke:#e1e1e1,color:#e1e1e1
    classDef developer fill:#67bd6d,stroke:#0e1c2d,color:#0e1c2d
    classDef tester fill:#ffc300,stroke:#0e1c2d,color:#0e1c2d
    classDef reviewer fill:#315074,stroke:#e1e1e1,color:#e1e1e1

    A[Code Analyzer<br/>Understand Codebase]:::analyzer
    B[Developer<br/>Implement Feature]:::developer
    C[Tester<br/>Write Tests]:::tester
    D[Reviewer<br/>Quality Check]:::reviewer

    A -->|Analysis Report| B
    B -->|Implementation| C
    C -->|Test Results| D
    D -->|Approval| E[Complete]
```

### Example 2: Documentation Pipeline

```mermaid
graph LR
    classDef analyzer fill:#8b5cf6,stroke:#e1e1e1,color:#e1e1e1
    classDef writer fill:#67bd6d,stroke:#0e1c2d,color:#0e1c2d
    classDef designer fill:#ffc300,stroke:#0e1c2d,color:#0e1c2d
    classDef publisher fill:#315074,stroke:#e1e1e1,color:#e1e1e1

    A[Doc Analyzer<br/>Audit Existing]:::analyzer
    B[Guide Writer<br/>Create Content]:::writer
    C[Visual Designer<br/>Add Diagrams]:::designer
    D[Publisher<br/>Deploy Docs]:::publisher

    A -->|Gap Analysis| B
    A -->|Asset List| C
    B -->|Draft Docs| D
    C -->|Diagrams| D
```

## Key Orchestration Features

### 🔄 Dynamic Agent Management
- **On-Demand Spawning**: Agents created when needed
- **Resource Recycling**: Reuse existing agents when possible
- **Automatic Cleanup**: Decommission on completion

### 📬 Message-Driven Coordination
- **Priority Queue**: High-priority messages processed first
- **Acknowledgment Tracking**: Ensure message delivery
- **Broadcast Support**: Notify all agents simultaneously

### 🤝 Seamless Handoffs
- **Context Transfer**: Pass work between agents
- **State Preservation**: Maintain progress across handoffs
- **Resource Optimization**: Release resources when switching

### 📊 Health Monitoring
- **Context Usage Tracking**: Monitor token consumption
- **Performance Metrics**: Track agent efficiency
- **Automatic Intervention**: Orchestrator handles issues

### 🎯 Template-Based Missions
- **Predefined Roles**: Database-backed templates
- **Dynamic Augmentation**: Runtime mission customization
- **Version Control**: Template archive for rollback

## Context Management Strategy

```mermaid
pie title "Context Budget Allocation"
    "Orchestrator" : 30
    "Primary Workers" : 40
    "Specialist Agents" : 20
    "Buffer/Reserve" : 10
```

## References

- Agent templates: [`src/giljo_mcp/template_manager.py`](../../src/giljo_mcp/template_manager.py)
- Message queue guide: [`docs/MESSAGE_QUEUE_GUIDE.md`](../MESSAGE_QUEUE_GUIDE.md)
- MCP tools: [`docs/manuals/MCP_TOOLS_MANUAL.md`](../manuals/MCP_TOOLS_MANUAL.md)