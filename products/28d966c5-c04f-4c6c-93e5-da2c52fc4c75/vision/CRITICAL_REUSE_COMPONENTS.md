# CRITICAL COMPONENTS TO REUSE (Enhanced Analysis)

## MUST REUSE (Core Infrastructure)

### 1. Database Manager
**File**: `F:\AKE-MCP\database_manager.py`
**Why**: Solid implementation with proper connection handling
**Changes Needed**: 
- Add methods for new tables (mcp_agent_jobs, mcp_agent_messages, mcp_agent_sessions, mcp_decisions)
- Add support for enum types (agent_state, message_type)
- Enhance connection pooling for WebSocket load
- Add LISTEN/NOTIFY support for real-time updates

### 2. Dashboard HTML Templates  
**Files**: 
- `F:\AKE-MCP\templates\orchestrator_dashboard.html`
- `F:\AKE-MCP\templates\task_dashboard_api.html`
**Why**: Working UI structure, good foundation
**Changes Needed**: 
- Add WebSocket client code
- Replace polling with event listeners
- Add connection status indicator
- Implement optimistic UI updates
- Add real-time message stream component
- Create agent status cards with state indicators

### 3. Vision Handler
**File**: `F:\AKE-MCP\vision_handler.py`
**Why**: Works well for external content integration
**Changes Needed**: Minor path updates if any

### 4. Database Schemas
**Files**: `F:\AKE-MCP\sql\*.sql`
**Why**: Good foundation
**Changes Needed**: Add new tables script

## PARTIAL REUSE (Cherry-pick Good Parts)

### 1. Project Orchestrator
**File**: `F:\AKE-MCP\project_orchestrator.py`
**Keep**: 
- Project creation logic
- Basic structure
**Discard**: 
- Complex message queue tracking
- Agent recognition phrases
- File-based state

### 2. Server.py Tools
**File**: `F:\AKE-MCP\server.py`
**Keep These Tools**:
- create_task
- list_tasks  
- update_task
- complete_task
- create_project
- get_project_status
- close_project
- search_vision

**Discard**: 
- Deprecated tools
- Complex health tracking
- Magic phrase detection

## DO NOT REUSE (Too Messy)

### 1. Agent Lifecycle Manager
**File**: `F:\AKE-MCP\agent_lifecycle.py`
**Why**: Over-engineered health tracking
**Replace With**: Simple active/inactive states

### 2. Scripts Folder
**Files**: `F:\AKE-MCP\scripts\*`
**Why**: Mostly patches and fixes
**Replace With**: Clean implementation

### 3. Tests
**Files**: `F:\AKE-MCP\tests\*`
**Why**: Tests for old architecture
**Replace With**: New test suite

### 4. Config Manager
**File**: `F:\AKE-MCP\config_manager.py`
**Why**: Complex multi-source config
**Replace With**: Simple config class

## ADDITIONAL COMPONENTS TO ANALYZE

### Conversation Middleware
**File**: `F:\AKE-MCP\conversation_middleware.py`
**Potential**: High value for conversation tracking
**Extract**: Conversation logging logic, context building

### Handoff Handler
**File**: `F:\AKE-MCP\handoff_handler.py`
**Potential**: Useful handoff patterns
**Extract**: Context transfer logic, state preservation

### Enhanced Orchestrator
**File**: `F:\AKE-MCP\enhanced_orchestrator.py`
**Potential**: Advanced orchestration patterns
**Extract**: Decision making logic, coordination patterns

## ALL 27 STANDARDIZED COMMANDS TO IMPLEMENT

```python
# Task Management (5)
create_task(title: str, description: str, priority: str = "medium", tags: List[str] = []) -> str
list_tasks(status: str = None, priority: str = None, limit: int = 50) -> str
update_task(task_id: str, **updates) -> str
complete_task(task_id: str, notes: str = None) -> str
convert_task_to_project(task_id: str, auto_activate: bool = False) -> str

# Project/Orchestration (5)
create_project(name: str, description: str, product_id: str = None) -> str
mcp_activate_orchestrator(project_id: str, context_mode: str = 'full') -> str
mcp_spawn_agent(project_id: str, agent_name: str, role: str, auto_handoff: bool = True) -> str
get_project_status(project_id: str, include_metrics: bool = True) -> str
close_project(project_id: str, summary: str, archive_conversations: bool = True) -> str

# Agent Communication (6)
broadcast_message(project_id: str, from_agent: str, content: str, to_agents: List[str] = [], priority: int = 5) -> str
send_direct_message(project_id: str, from_agent: str, to_agent: str, content: str, await_response: bool = False) -> str
acknowledge_message(message_id: str, agent_name: str, notes: str = None) -> str
complete_message(message_id: str, agent_name: str, result: str = None) -> str
get_agent_messages(project_id: str, agent_name: str, status: str = 'pending', limit: int = 20) -> str
get_message_status(project_id: str, include_expired: bool = False) -> str

# Vision/Context (4)
search_vision(keywords: str, product_id: str = None, limit: int = 10) -> str
get_product_context(product_id: str = None, include_architecture: bool = True) -> str
switch_product(product_name: str, load_vision: bool = True) -> str
get_active_product(include_stats: bool = True) -> str

# Agent Lifecycle (4)
track_agent_activity(agent_name: str, activity_type: str, details: str, metrics: Dict = {}) -> str
check_agent_health(agent_name: str, include_history: bool = False) -> str
prepare_handoff(from_agent: str, to_agent: str, context_summary: Dict) -> str
decommission_agent(agent_name: str, save_state: bool = True) -> str

# History & Audit (3)
log_decision(project_id: str, agent_name: str, decision: str, rationale: str, alternatives: List[str] = []) -> str
search_project_history(query: str, project_id: str = None, search_type: str = 'all', limit: int = 50) -> str
get_conversation_context(project_id: str, agent_name: str = None, last_n_messages: int = 20) -> str
```

## FILE STRUCTURE TO CREATE

```
AKE-MCP-V2/
├── core/
│   ├── __init__.py
│   ├── config.py          # NEW - Simple config
│   ├── database.py        # FROM database_manager.py + additions
│   └── models.py          # NEW - Clean models
├── orchestration/
│   ├── __init__.py
│   ├── orchestrator.py    # PARTIAL from project_orchestrator.py
│   ├── messaging.py       # NEW - Broadcast system
│   └── agent_manager.py   # NEW - Simple lifecycle
├── mcp_tools/
│   ├── __init__.py
│   ├── task_tools.py      # FROM server.py (selected tools)
│   ├── project_tools.py   # FROM server.py (selected tools)
│   ├── agent_tools.py     # NEW - Standardized commands
│   ├── message_tools.py   # NEW - Broadcast tools
│   └── vision_tools.py    # FROM server.py + vision_handler.py
├── api/
│   ├── __init__.py
│   └── web_server.py      # PARTIAL from web_server.py
├── templates/
│   ├── orchestrator_dashboard.html  # COPY AS-IS
│   └── task_dashboard_api.html      # COPY AS-IS
├── sql/
│   ├── create_database.sql          # COPY AS-IS
│   └── add_new_tables.sql           # NEW
├── requirements.txt                  # COPY AS-IS
├── run_mcp_server.bat               # NEW
├── launch_dashboard.bat             # NEW
└── mcp_server.py                    # NEW - Main entry point
```

## DATABASE CHANGES

Add these tables to existing AKE_MCP_DB:

```sql
CREATE TABLE mcp_agent_jobs (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    project_id UUID REFERENCES mcp_projects(id),
    agent_name VARCHAR(100) NOT NULL,
    job_title VARCHAR(255) NOT NULL,
    job_description TEXT,
    status VARCHAR(50) DEFAULT 'pending',
    assigned_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    started_at TIMESTAMP,
    completed_at TIMESTAMP,
    result TEXT,
    metadata JSONB DEFAULT '{}'
);

CREATE TABLE mcp_agent_messages (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    project_id UUID REFERENCES mcp_projects(id),
    from_agent VARCHAR(100) NOT NULL,
    to_agents TEXT[] NOT NULL,
    message_type VARCHAR(50),
    content TEXT NOT NULL,
    acknowledged_by TEXT[] DEFAULT '{}',
    completed_by TEXT[] DEFAULT '{}',
    status VARCHAR(50) DEFAULT 'pending',
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    metadata JSONB DEFAULT '{}'
);
```