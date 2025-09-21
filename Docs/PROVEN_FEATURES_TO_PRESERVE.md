# Proven Features to Preserve

## Critical Features Actually Implemented & Working

After reviewing the documentation and cross-referencing with the actual code, here are the **proven, working features** we must preserve:

### 1. Vision Document Chunking (FULLY IMPLEMENTED)
**Location**: `server.py` lines 1345-1440  
**Why It's Brilliant**: Solves the MCP 25K token transport limit while allowing unlimited vision document sizes

**Implementation Details**:
- `get_vision(part: int = 1, max_tokens: int = 20000)` - Returns chunks under token limit
- Automatically breaks at natural boundaries (newlines)
- Creates index in database for orchestrator navigation
- Returns `total_parts` and `current_part` for multi-part reading
- Orchestrator instructions include chunked reading logic

**Actual Code Pattern**:
```python
# Calculates chunks needed
chars_per_chunk = max_tokens * 4  # ~4 chars per token
total_chunks = (len(full_content) + chars_per_chunk - 1) // chars_per_chunk

# Smart breaking at line boundaries
if not full_content[end_pos].isspace():
    newline_pos = full_content.rfind('\n', start_pos, end_pos)
    if newline_pos > start_pos:
        end_pos = newline_pos
```

**MUST PRESERVE**: This elegant solution handles 43K+ token vision documents seamlessly

### 2. Message Acknowledgment System (PARTIALLY IMPLEMENTED)
**Location**: `core/database_manager.py`, `core/message_queue.py`, `server.py`  
**Status**: Database schema exists, basic acknowledgment works, but NOT the full array system from docs

**What's Actually Implemented**:
- `acknowledged_by` is TEXT[] array in PostgreSQL
- `acknowledge_message()` appends agent to array (no duplicates)
- Messages never deleted, only acknowledged
- Dashboard shows acknowledgment status

**What's Missing** (but documented):
- `completed_by` array tracking
- Completion timestamps
- Auto-acknowledgment on retrieval

**MUST ENHANCE**: The foundation is solid, needs the completion tracking added

### 3. Dynamic Discovery Architecture (FULLY WORKING)
**Location**: Throughout, especially `server.py`, `api/web_api.py`  
**Why It Works**: No pre-indexing, always fresh context

**Proven Pattern**:
1. Vision path configuration with priority system
2. `get_vision()` reads fresh from disk
3. `get_product_settings()` provides all paths
4. Orchestrator explores on-demand
5. Serena MCP integration for codebase discovery

**Configuration Priority (Actually Enforced)**:
1. `vision_path` - HIGHEST
2. `config_data` fields - HIGH 
3. `project_docs_path` - MEDIUM
4. `session_memories_path` - LOW

**MUST PRESERVE**: This eliminates stale context entirely

### 4. Project vs Product Distinction (CORE ARCHITECTURE)
**Location**: Database schema, all API endpoints  
**Critical Understanding**: Products = software apps, Projects = work items

**Database Implementation**:
- `mcp_products` table - Long-lived containers
- `mcp_projects` table - Temporary work items
- Projects have `product_id` foreign key
- Only ONE product active at a time (current limitation)

**MUST EVOLVE**: Keep distinction but enable multi-product via tenant keys

### 5. Orchestrator Mission Generation (PROVEN PATTERN)
**Location**: `server.py` line 95, `api/web_api.py` line 395  
**Why It Works**: Consistent, detailed instructions for every orchestrator

**The Template That Works**:
```python
def generate_orchestrator_mission(project_name, project_mission, product_name, agents):
    # Returns 434-line detailed mission
    # Includes vision guardian role
    # Scope sheriff responsibilities  
    # Chunked reading instructions
    # Dynamic discovery approach
```

**MUST PRESERVE**: This template ensures orchestrators behave consistently

### 6. Database-First Message Queue (ROBUST)
**Location**: `core/message_queue.py`, PostgreSQL tables  
**Why It's Solid**: ACID compliance, no lost messages

**Working Features**:
- Project-scoped queues
- Priority routing
- Broadcast support
- Acknowledgment tracking
- Message statistics

**Table Structure**:
```sql
mcp_messages (
    id, project_id, from_agent, to_agents[],
    content, priority, acknowledged_by[],
    created_at, subject, message_type
)
```

**MUST PRESERVE**: Database queues are more reliable than in-memory

### 7. Single Instance Enforcement (WORKING)
**Location**: `core/proxy_manager.py`  
**Implementation**: Port-based locking prevents multiple servers

**How It Works**:
- Tries to bind to port 5002
- If fails, another instance is running
- Clean shutdown releases port

**MUST EVOLVE**: Keep for local mode, adapt for multi-tenant server

## Features That Need Completion

### 1. Message Completion Tracking
**Documented but not fully implemented**:
- Need `completed_by` array
- Need completion timestamps
- Need completion notes

### 2. Auto-Acknowledgment
**Documented but not implemented**:
- Messages should auto-acknowledge when retrieved
- Reduces manual acknowledge calls

### 3. Vision Index Creation
**Partially implemented**:
- `_create_vision_index()` exists but not fully utilized
- Could help orchestrators navigate large visions better

## Technical Patterns to Preserve

### 1. The "Part" Pattern for Large Content
```python
def get_something(part: int = 1, max_tokens: int = 20000):
    # Calculate total parts
    # Return requested part
    # Include metadata about parts
```

### 2. Array Fields for Multi-Agent Tracking
```sql
-- PostgreSQL arrays track multiple agents
acknowledged_by TEXT[]
completed_by TEXT[]
to_agents TEXT[]
```

### 3. Dynamic Path Resolution
```python
# Read from configured paths, not hardcoded
vision_path = config.get('vision_path')
if Path(vision_path).exists():
    content = Path(vision_path).read_text()
```

### 4. Mission Templates with Detailed Instructions
```python
# Don't just spawn agents, give them detailed missions
mission = generate_detailed_mission(context)
activate_agent(agent_name, mission=mission)
```

## What NOT to Preserve

### 1. Single Active Product Limitation
- Current: `is_active` flag allows only one
- Future: `tenant_key` allows unlimited concurrent

### 2. Complex Health Tracking
- Was removed for good reason
- Context usage percentage is sufficient

### 3. Static Context Building
- All the indexing/manifest code can go
- Dynamic discovery proved superior

### 4. Separate Message Deletion
- Never delete messages
- Acknowledgment/completion is sufficient

## Implementation Priority for Rewrite

1. **Day 1**: Multi-tenant database schema with project keys
2. **Day 1**: Vision chunking system (copy the working code!)
3. **Day 2**: Message acknowledgment arrays
4. **Day 2**: Dynamic discovery paths
5. **Day 3**: Orchestrator mission generation
6. **Day 3**: Database message queue
7. **Day 4**: UI for acknowledgment visibility
8. **Day 5**: Testing with large visions

## Key Insight

The most valuable features are those that solve **real problems we encountered**:
- Vision chunking solved the 43K token document problem
- Message acknowledgment solved the "lost message" problem  
- Dynamic discovery solved the "stale context" problem
- Database-first solved the "crash recovery" problem

These aren't theoretical - they're battle-tested solutions that MUST be preserved in GiljoAI MCP.