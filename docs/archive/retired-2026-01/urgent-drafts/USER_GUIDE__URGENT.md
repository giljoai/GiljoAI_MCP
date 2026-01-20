# GiljoAI MCP Orchestrator User Guide

## Table of Contents

1. [Getting Started](#getting-started)
2. [Core Concepts](#core-concepts)
3. [Configuration](#configuration)
4. [Working with Projects](#working-with-projects)
5. [Agent Management](#agent-management)
6. [Message System](#message-system)
7. [Vision Documents](#vision-documents)
8. [Orchestration Patterns](#orchestration-patterns)
9. [API Reference](#api-reference)
10. [Troubleshooting](#troubleshooting)

## Getting Started

### Prerequisites

- Python 3.11 or higher
- PostgreSQL (included with Python)
- Git
- 4GB RAM minimum (8GB recommended)

### Installation

1. **Clone the repository:**

```bash
git clone https://github.com/yourusername/giljo-mcp.git
cd giljo-mcp
```

2. **Create virtual environment:**

```bash
python -m venv venv
source venv/bin/activate  # On Windows: venv\Scripts\activate
```

3. **Install dependencies:**

```bash
pip install -r requirements.txt
```

4. **Initialize the database:**

```bash
python scripts/setup.py init
```

5. **Configure MCP server:**

```bash
# Copy the example configuration
cp .mcp.example.json .mcp.json

# Edit .mcp.json with your paths
```

### Your First Orchestration (5 Minutes)

1. **Start the MCP server:**

```bash
python -m giljo_mcp.server
```

2. **Create your first project:**

```python
# In a new terminal or Python REPL
from giljo_mcp.client import GiljoClient

client = GiljoClient()

# Create a project
project = client.create_project(
    name="Hello Orchestration",
    mission="Build a simple hello world application"
)
print(f"Created project: {project.id}")
```

3. **Activate the orchestrator:**

```python
# The orchestrator will analyze your mission and create a plan
orchestrator = client.activate_agent(
    project_id=project.id,
    agent_name="orchestrator",
    mission="Analyze the project mission and create an execution plan"
)
```

4. **Watch the magic happen:**

```python
# The orchestrator will spawn needed agents automatically
status = client.project_status(project.id)
print(f"Active agents: {status['agents']}")
print(f"Messages sent: {status['message_count']}")
```

## Core Concepts

### Projects

A project is the top-level container for an orchestration session. Each project has:

- **Unique ID**: UUID for identification
- **Name**: Human-readable identifier
- **Mission**: The goal to accomplish
- **Tenant Key**: For multi-tenant isolation
- **Status**: active, inactive, completed, cancelled, or deleted

### Agents

Agents are the workers in the orchestration system. Types include:

- **Orchestrator**: Plans and coordinates work
- **Implementer**: Writes code
- **Tester**: Validates implementations
- **Documenter**: Creates documentation
- **Analyst**: Reviews and analyzes
- **Custom Agents**: Specialized for your needs

### Messages

The message system enables agent communication:

- **Direct Messages**: One agent to another
- **Broadcast**: To all agents in project
- **Priority Levels**: high, normal, low
- **Acknowledgment**: Track message receipt
- **Completion**: Track task completion

### Vision Documents

Vision documents provide context and guidance:

- Support for 50K+ token documents
- Automatic chunking for large files
- Indexed for quick navigation
- Version controlled

## Configuration

### Basic Configuration (.mcp.json)

```json
{
  "mcpServers": {
    "giljo-mcp": {
      "command": "python",
      "args": ["-m", "giljo_mcp.server"],
      "env": {
        "GILJO_HOME": "F:\\GiljoAI_MCP",
        "GILJO_ENV": "development"
      }
    }
  }
}
```

### Environment Variables

```bash
# Required
GILJO_HOME=/path/to/giljo-mcp
GILJO_ENV=development|staging|production

# Optional
GILJO_DB_URL=postgresql:///giljo.db
GILJO_LOG_LEVEL=INFO
GILJO_MAX_AGENTS=10
GILJO_CONTEXT_BUDGET=150000
```

### Database Configuration

```yaml
# config.yaml
database:
  # Local development (default)
  url: postgresql:///giljo.db

  # LAN deployment
  url: postgresql://user:pass@192.168.1.100/giljo

  # WAN deployment with SSL
  url: postgresql://user:pass@db.example.com/giljo?sslmode=require

  pool_size: 20
  max_overflow: 40
```

## Working with Projects

### Creating Projects

```python
# Simple project
project = client.create_project(
    name="Web Scraper",
    mission="Build a web scraper for news articles"
)

# Project with predefined agents
project = client.create_project(
    name="API Service",
    mission="Create a REST API with authentication",
    agents=["orchestrator", "backend_dev", "frontend_dev", "tester"]
)
```

### Managing Project Lifecycle

```python
# List all projects
projects = client.list_projects()
for p in projects:
    print(f"{p['name']}: {p['status']}")

# Activate a project for orchestrator staging
client.gil_activate(project_id)

# Update mission after discovery
client.update_project_mission(
    project_id,
    mission="Enhanced mission with specific requirements..."
)

# Close completed project
client.close_project(
    project_id,
    summary="Successfully implemented all features"
)
```

### Projects View (V2)

Use the Projects view to manage projects with real-time search, status filters, sorting, and status transitions.

- Search: filter by project name, mission keywords, or ID (updates instantly)
- Status tabs: Active, Inactive, Completed, Cancelled, Deleted (with counts)
- Sorting: sort by name, status, dates (ascending/descending)
- StatusBadge actions:
  - Activate (enforces one active project per product)
  - Deactivate (replaces older “Pause” terminology)
  - Complete / Cancel
  - Delete (soft delete, recoverable for 10 days)
  - Restore (Deleted/Completed → Inactive)
- Product isolation: lists only projects for the active product

See also: features/project_state_management.md for state rules and constraints.

### Project Templates

```python
# Use a project template
from giljo_mcp.templates import ProjectTemplate

template = ProjectTemplate.web_application()
project = client.create_project(**template)
```

## Agent Management

### Agent Orchestration UI (Static Agent Grid)

The orchestration UI uses a static agent grid for clarity and throughput. It shows agents by role with live status and messaging summaries.

- Fixed grid layout for agent roles and statuses
- Live updates via WebSocket events (tenant- and project-scoped)
- Controls for spawning agents, sending messages, and tracking progress
- Supersedes older Launch/Jobs dual-tab and Kanban concepts

See: features/agent_grid_static_0073.md for details.

### Orchestrator Succession

When an orchestrator nears its context budget or you’re transitioning phases, create a successor orchestrator and hand over state.

- Trigger: In your CLI, run `/gil_handover` (optionally `/gil_handover <ORCHESTRATOR_JOB_ID>`)
- Result: A successor orchestrator (instance +1) is created in “waiting”; a compressed handover summary is returned
- UI: The grid marks the predecessor as complete and shows the successor with a NEW badge
- Events: `job:succession_triggered`, `job:successor_created`

See: developer_guides/orchestrator_succession_developer_guide.md

### Agent Lifecycle

```python
# Ensure agent exists (idempotent)
agent = client.ensure_agent(
    project_id,
    agent_name="code_reviewer",
    mission="Review code for quality and standards"
)

# Assign specific job
job = client.assign_job(
    project_id=project_id,
    agent_name="implementer",
    job_type="implementation",
    tasks=[
        "Create user authentication module",
        "Implement JWT token generation",
        "Add password hashing"
    ],
    scope_boundary="Only modify files in src/auth/",
    vision_alignment="Support multi-factor authentication per vision doc"
)

# Check agent health
health = client.agent_health("implementer")
print(f"Context used: {health['context_used']}/{health['context_budget']}")

# Handoff between agents
client.handoff(
    project_id=project_id,
    from_agent="analyst",
    to_agent="implementer",
    context={
        "findings": "Security vulnerabilities found",
        "recommendations": ["Use bcrypt", "Add rate limiting"],
        "priority": "high"
    }
)

# Decommission when done
client.decommission_agent(
    project_id,
    agent_name="code_reviewer",
    reason="Code review complete"
)
```

### Agent Templates

```python
from giljo_mcp.template_manager import TemplateManager

tm = TemplateManager(session, tenant_key, product_id)

# Get agent mission from template
mission = await tm.get_template(
    name="security_auditor",
    augmentations="Focus on OWASP Top 10",
    variables={"project_name": project.name}
)

# Create agent with templated mission
agent = client.ensure_agent(
    project_id,
    agent_name="security_auditor",
    mission=mission
)
```

## Message System

### Sending Messages

```python
# Direct message to specific agent
client.send_message(
    project_id=project_id,
    to_agents=["implementer"],
    content="Please add input validation to the login form",
    priority="high"
)

# Message to multiple agents
client.send_message(
    project_id=project_id,
    to_agents=["tester", "documenter"],
    content="Feature X is ready for testing and documentation",
    message_type="handoff"
)

# Broadcast to all agents
client.broadcast(
    project_id=project_id,
    content="Code freeze at 5 PM for release",
    priority="high"
)
```

### Receiving and Processing Messages

```python
# Get pending messages for agent
messages = client.get_messages(
    agent_name="implementer",
    project_id=project_id
)

for msg in messages:
    print(f"From: {msg['from']}")
    print(f"Content: {msg['content']}")

    # Acknowledge receipt
    client.acknowledge_message(
        message_id=msg['id'],
        agent_name="implementer"
    )

    # Process the message...
    result = process_message(msg)

    # Mark as complete
    client.complete_message(
        message_id=msg['id'],
        agent_name="implementer",
        result=result
    )
```

### Task Logging

```python
# Quick task capture
client.log_task(
    content="Investigate performance bottleneck in query",
    category="optimization",
    priority="medium"
)
```

## Vision Documents

### Loading Vision Documents

```python
# Get vision document (auto-chunks if >20K tokens)
vision_part1 = client.get_vision(part=1, max_tokens=20000)
print(f"Part 1 of {vision_part1['total_parts']}")

# Get vision index for navigation
index = client.get_vision_index()
for file_info in index['files']:
    print(f"{file_info['name']}: {file_info['topics']}")
```

### Using Context

```python
# Get context index
context = client.get_context_index(product_id)
print(f"Available sections: {context['sections']}")

# Get specific section
section = client.get_context_section(
    product_id=product_id,
    document_name="architecture",
    section_name="database_design"
)
```

## Orchestration Patterns

### Pattern 1: Sequential Pipeline

```python
# Each agent completes before the next starts
agents = ["analyzer", "designer", "implementer", "tester", "deployer"]

for i, agent_name in enumerate(agents):
    if i > 0:
        # Handoff from previous agent
        client.handoff(
            project_id,
            from_agent=agents[i-1],
            to_agent=agent_name,
            context={"stage": i}
        )

    # Activate and wait for completion
    client.activate_agent(project_id, agent_name)
    wait_for_agent_completion(agent_name)
```

### Pattern 2: Parallel Execution

```python
# Multiple agents work simultaneously
parallel_agents = ["frontend_dev", "backend_dev", "database_dev"]

for agent in parallel_agents:
    client.ensure_agent(project_id, agent)
    client.assign_job(
        project_id=project_id,
        agent_name=agent,
        job_type="development",
        tasks=get_tasks_for_agent(agent)
    )

# Coordinator monitors progress
client.ensure_agent(project_id, "coordinator")
client.send_message(
    project_id=project_id,
    to_agents=["coordinator"],
    content="Monitor parallel development and coordinate integration"
)
```

### Pattern 3: Dynamic Spawning

```python
# Orchestrator creates agents as needed
orchestrator = client.activate_agent(
    project_id=project_id,
    agent_name="orchestrator",
    mission="Analyze requirements and spawn necessary agents"
)

# Orchestrator will dynamically create agents based on discovery
# Monitor spawned agents
import time
while True:
    status = client.project_status(project_id)
    print(f"Active agents: {len(status['agents'])}")

    if status['status'] == 'completed':
        break

    time.sleep(5)
```

### Pattern 4: Feedback Loop

```python
# Continuous improvement cycle
stages = {
    "developer": "Implement feature",
    "tester": "Test implementation",
    "reviewer": "Review code quality",
    "developer": "Address feedback"  # Loop back
}

iteration = 0
max_iterations = 3

while iteration < max_iterations:
    for agent, task in stages.items():
        result = client.assign_job(
            project_id=project_id,
            agent_name=agent,
            job_type="iteration",
            tasks=[f"{task} (iteration {iteration + 1})"]
        )

        # Check if standards met
        if agent == "reviewer":
            if check_quality_passed(result):
                break

    iteration += 1
```

## API Reference

See [MCP Tools Manual](../manuals/MCP_TOOLS_MANUAL.md) for complete API documentation with request/response examples for all 20+ tools.

## Troubleshooting

### Common Issues

#### 1. Agent Context Overflow

**Problem**: Agent runs out of context budget

```python
# Solution: Monitor and manage context
health = client.agent_health(agent_name)
if health['context_used'] > health['context_budget'] * 0.8:
    # Handoff to fresh agent
    client.handoff(
        project_id,
        from_agent=agent_name,
        to_agent=f"{agent_name}_continued",
        context={"reason": "context_limit"}
    )
```

#### 2. Message Queue Backlog

**Problem**: Messages piling up unprocessed

```python
# Solution: Check message processing
for agent in active_agents:
    pending = client.get_messages(agent, project_id)
    if len(pending) > 10:
        # Spawn helper agent
        client.ensure_agent(
            project_id,
            f"{agent}_helper",
            mission=f"Assist {agent} with message backlog"
        )
```

#### 3. Database Lock (PostgreSQL)

**Problem**: Database locked error in local mode

```bash
# Solution: Increase timeout and use WAL mode
postgresql3 giljo.db "PRAGMA journal_mode=WAL;"
```

#### 4. Vision Document Too Large

**Problem**: Vision document exceeds memory

```python
# Solution: Use chunked reading
for part in range(1, 10):
    try:
        chunk = client.get_vision(part=part, max_tokens=10000)
        process_chunk(chunk)
    except:
        break  # No more parts
```

#### 5. Agent Stuck in Loop

**Problem**: Agent repeating same actions

```python
# Solution: Recalibrate mission
client.recalibrate_mission(
    project_id,
    changes_summary="Break out of current loop, try alternative approach"
)
```

### Performance Tuning

```python
# Monitor performance metrics
metrics = client.session_info()
print(f"Total messages: {metrics['message_count']}")
print(f"Agents spawned: {metrics['agent_count']}")
print(f"Uptime: {metrics['uptime_seconds']}s")

# Optimize based on metrics
if metrics['message_count'] > 1000:
    # Consider batching or filtering
    pass

if metrics['agent_count'] > 20:
    # Consolidate agents
    pass
```

### Debug Mode

```bash
# Enable debug logging
export GILJO_LOG_LEVEL=DEBUG
python -m giljo_mcp.server --debug

# Check logs
tail -f logs/giljo-mcp.log
```

## Product Management

### Product Configuration

Products in GiljoAI MCP can be configured with rich context fields to provide agents with comprehensive information about your project.

#### 5-Tab Product Form

When creating or editing a product, you'll use a multi-tabbed interface that organizes configuration into logical sections:

**Tab 1: Basic Info**
- **Product Name**: Unique identifier for your product (required)
- **Description**: Overview of the product that provides context for AI agents
- **Vision Type**: Choose how to provide vision context:
  - **File**: Upload a vision document from your file system
  - **Inline**: Write vision directly in the form editor
  - **None**: No vision document

**Tab 2: Tech Stack**
Configure the technologies, frameworks, and tools used in your product:
- **Programming Languages**: Languages used in the project (e.g., Python 3.11+, TypeScript 5.0)
- **Backend Stack**: Backend frameworks and runtime (e.g., FastAPI, Node.js)
- **Frontend Stack**: Frontend frameworks and libraries (e.g., Vue 3, React)
- **Databases**: Database systems (e.g., PostgreSQL 18, MongoDB)
- **Infrastructure**: Deployment and infrastructure details (e.g., Docker, Kubernetes)

**Tab 3: Architecture**
Describe your product's architectural approach:
- **Architecture Pattern**: Overall architectural style (e.g., Microservices, Modular Monolith)
- **API Style**: API communication style (e.g., REST, GraphQL, gRPC)
- **Design Patterns**: Specific design patterns used (e.g., Repository, Factory, Strategy)
- **Additional Notes**: Extra architectural context and decisions

**Tab 4: Features**
Document your product's features and roadmap:
- **Core Features**: Currently implemented features
- **Optional Features**: Planned or future features
- **Integrations**: External system integrations

**Tab 5: Test Config**
Define testing requirements and strategies:
- **Testing Strategy**: Testing methodology (e.g., TDD, BDD)
- **Testing Frameworks**: Tools and frameworks used (e.g., pytest, vitest)
- **Coverage Target**: Required code coverage percentage
- **Additional Notes**: Extra testing context

#### Best Practices for Product Configuration

- **Use free-text format**: All fields accept any text format for maximum flexibility
- **Provide detailed context**: More information helps agents work more effectively
- **Update regularly**: Keep product configuration current as your product evolves
- **Use consistent terminology**: Maintain consistency across all configuration fields

### Products View Management

The Products view provides unified management for all your products, including vision documents, metrics, and lifecycle operations.

#### Product Cards

Each product is displayed as a card showing:
- **Product Name** and description
- **Status**: Active (highlighted) or Inactive
- **Metrics**:
  - Unresolved Tasks count
  - Unfinished Projects count
  - Vision Documents count
- **Date Created**: When the product was first created
- **Actions**: Edit, Activate/Deactivate, Delete buttons

#### Creating a Product

1. Click the **"+ New Product"** button in the Products view
2. Fill in the **Basic Info** tab:
   - Enter a unique product name (required)
   - Add a description
   - Select vision type and provide vision content if needed
3. Configure **Tech Stack** (optional but recommended):
   - Enter programming languages
   - Specify backend and frontend frameworks
   - List databases and infrastructure
4. Define **Architecture** details (optional):
   - Document architectural patterns
   - Specify API style
   - Note design patterns used
5. Describe **Features** (optional):
   - List core features
   - Document planned features
   - Note integrations
6. Configure **Test Settings** (optional):
   - Define testing strategy
   - List testing frameworks
   - Set coverage targets
7. Click **"Create Product"** to save

**Vision Document Upload** (if using File type):
- Drag and drop files into the upload area
- OR click to browse and select files
- Supported formats: .md, .txt, .pdf, .docx
- Multiple files can be uploaded
- Files are automatically chunked for efficient processing (25K tokens per chunk)

#### Editing a Product

1. Click the **"Edit"** button on the product card
2. Modify any fields across the 5 tabs
3. **Update vision documents** if needed:
   - View existing vision documents
   - Upload additional files
   - Remove existing files
4. Click **"Save Changes"** to apply updates

#### Managing Vision Documents in Edit Mode

When editing a product:
- **Existing Documents** section shows all attached vision files with:
  - Filename
  - Chunk count (indicates processing status)
  - Created date
  - Delete button (with confirmation)
- **Add More Documents** section allows uploading additional files
- Removing a document also deletes its chunks from the system

#### Activating and Deactivating Products

Products use a **single-active-product architecture** - only one product can be active at a time:

- **Active products** are available for mission creation and appear in agent context
- **Inactive products** can be reactivated anytime
- Click **"Activate"** button on a product card to set it as active
- The previously active product automatically becomes inactive
- Active product is visually indicated with a highlighted border or badge

**Active Product Benefits**:
- Tasks and projects are filtered to show only those belonging to the active product
- AI agents receive context specific to the active product
- Dashboard displays active product name for quick reference

#### Deleting a Product

**Warning**: Product deletion is irreversible and cascades to all related data.

1. Click the **"Delete"** button on the product card
2. Review the **cascade impact** display showing what will be deleted:
   - Number of projects (total and unfinished)
   - Number of tasks (total and unresolved)
   - Number of vision documents
   - Number of context chunks
3. Read the warning: **"THIS ACTION CANNOT BE UNDONE"**
4. Type the product name exactly to confirm deletion (safety measure)
5. Check the confirmation box: "I understand this action is permanent"
6. Click **"Delete Forever"** to proceed

**What Gets Deleted**:
- The product record
- All associated projects (and their tasks)
- All associated tasks
- All vision documents and their chunks
- All product-specific context data

### Field Priority Configuration

Control how product configuration fields are prioritized for token budget allocation when building AI agent context.

#### Overview

When AI agents are created for missions, they receive product context from the fields you configured. The Field Priority system (also called **Context Priority Management**) allows you to control which fields are most important and should be prioritized when building agent context within token budget constraints.

#### Accessing Field Priority Settings

1. Click the **Avatar dropdown** in the top right corner
2. Select **"Settings"**
3. Navigate to the **"General"** tab
4. Scroll to the **"Context Priority Management"** section

#### Understanding the Priority System

The system uses a **3-tier priority hierarchy** plus an **Unassigned** category:

**Priority 1 (P1) - Always Included**
- Highest token allocation (~40% of budget)
- Fields essential for agent understanding
- Always sent to AI agents in missions
- Badge color: Red

**Priority 2 (P2) - High Priority**
- Medium token allocation (~35% of budget)
- Important context that significantly improves agent performance
- Included when token budget allows
- Badge color: Orange

**Priority 3 (P3) - Medium Priority**
- Lower token allocation (~25% of budget)
- Nice-to-have context that provides additional detail
- Included last, may be dropped if budget exceeded
- Badge color: Blue

**Unassigned Fields**
- Zero token allocation
- Fields not currently assigned to any priority level
- Excluded from agent missions
- Can be dragged back to priority categories anytime
- Badge color: Grey (dashed border)

#### Default Priority Configuration

The system comes with smart defaults optimized for most projects:

**Priority 1 (P1)**:
- Programming Languages
- Backend Stack
- Frontend Stack
- Architecture Pattern
- Core Features

**Priority 2 (P2)**:
- Databases
- API Style
- Testing Strategy

**Priority 3 (P3)**:
- Infrastructure
- Design Patterns
- Architecture Notes
- Testing Frameworks
- Coverage Target

#### Customizing Field Priorities

**Drag-and-Drop Reordering**:

1. Navigate to **Settings → General → Context Priority Management**
2. **Drag fields** between priority sections using the drag handle icon
3. Drop fields in the desired priority level (P1, P2, P3, or Unassigned)
4. Fields update position immediately
5. Token estimator recalculates in real-time

**Removing Fields from Priority**:

1. Click the **"X"** button on any field chip
2. Field moves to the **Unassigned** category automatically
3. Token count decreases immediately
4. Field remains visible and can be restored by dragging back

**Restoring Fields**:

1. Find the field in the **Unassigned** category
2. Drag it to your desired priority level (P1, P2, or P3)
3. Token count increases immediately

#### Token Budget Estimator

The real-time token estimator shows:

**Header Information**:
- Active product name (context for estimates)
- Current token usage vs. budget (e.g., "1,247 / 2,000 tokens")
- Percentage indicator with color-coded status:
  - Green: Under 70% (healthy)
  - Yellow/Orange: 70-90% (warning)
  - Red: Over 90% (at capacity)

**How It Works**:
- Fetches actual field content from your active product
- Calculates real token usage based on field values
- Updates automatically when you change priorities
- Refreshes after saving changes
- Shows accurate impact of your configuration

**Token Allocation**:
- Priority 1 fields: ~50 tokens per field
- Priority 2 fields: ~30 tokens per field
- Priority 3 fields: ~20 tokens per field
- Unassigned fields: 0 tokens
- Mission overhead: ~500 tokens (always included)

#### Saving Priority Changes

1. Adjust field priorities using drag-and-drop or remove buttons
2. Review the token estimate to ensure it fits your budget
3. Click **"Save Field Priority"** button
4. Token estimator refreshes with updated calculations
5. Changes apply to the **active product** immediately

**When changes take effect**:
- New missions created after saving use the updated priorities
- Existing missions are not affected
- Each mission snapshot preserves the configuration at creation time

#### Resetting to Defaults

If you want to start over or undo customizations:

1. Click the **"Reset to Defaults"** button
2. Confirm the reset action in the dialog
3. System restores the original default priority configuration
4. Token estimator refreshes automatically
5. All customizations are lost (cannot be undone)

**When to reset**:
- Experimenting with priorities went wrong
- Want to return to proven defaults
- Unsure about current configuration
- Starting fresh with a new project type

#### Best Practices for Field Priorities

**Prioritize Essential Information**:
- Put fields agents need for every mission in P1
- Consider which fields appear in most of your mission types
- Tech stack and architecture are usually high priority

**Balance Token Budget**:
- Monitor the token percentage indicator
- Keep under 90% to leave room for mission-specific context
- If over budget, move less critical fields to lower priorities or Unassigned

**Test Different Configurations**:
- Try different priority arrangements for your workflow
- Monitor agent performance with different configurations
- Use Reset to Defaults if uncertain - defaults are well-tested

**Context Matters**:
- Backend-heavy projects: Prioritize backend stack, databases, API style
- Frontend-heavy projects: Prioritize frontend stack, design patterns
- Testing-focused work: Elevate testing fields to higher priorities

### Active Product Indicator

The dashboard displays the currently active product for quick reference throughout your workflow.

#### Features

- **Product name** displayed in the application header (top navigation bar)
- **Visual indicator** showing active status (highlighted chip or badge)
- **Click-through**: Click the indicator to navigate to the Products view
- **Always visible**: Displayed on all pages for consistent context awareness

#### Understanding the Indicator

**Active Product Shown**:
- Displays as: "Active: [Product Name]"
- Color: Primary color (blue/purple)
- Icon: Package or project icon
- Clickable to navigate to Products view

**No Active Product**:
- Displays as: "No Active Product"
- Color: Grey/disabled
- Indicates you need to activate a product before creating missions

#### Changing the Active Product

1. Navigate to the **Products** view (click the active product indicator or use main navigation)
2. Click the **"Activate"** button on your desired product
3. The active product indicator updates immediately
4. Tasks and projects filter to show only items for the newly active product
5. Future missions will use the new active product's context

#### Benefits of Active Product Context

- **Focused Workflow**: See only tasks and projects relevant to current work
- **Accurate Agent Context**: Agents receive configuration specific to the active product
- **Clear Visual Feedback**: Always know which product context you're working in
- **Quick Switching**: Change context instantly from any page

**Note**: The active product indicator also serves as the foundation for token visualization features, showing where agent context is coming from.

#### Single Active Product Rule (Handover 0050)

- Only ONE product can be active per tenant at any time (database-enforced).
- Activating a product automatically deactivates the previously active product.
- UI and API are tenant-scoped; switching active product updates filters across views.

#### Product Switch Effects (Handover 0050b)

- Projects are single-active per product. When you switch the active product:
  - Any previously active project under the former product is set to Inactive (cascade deactivation).
  - Projects for the newly active product can be activated as needed.
- This preserves clear context and prevents cross-product confusion.

See also: features/project_state_management.md and SERVER_ARCHITECTURE_TECH_STACK.md for enforcement details.

### Priority Badges in Product Edit Form

When editing product configuration, you'll see visual priority indicators on each field showing how it's prioritized for AI agent missions.

#### What Are Priority Badges?

Priority badges are small colored chips that appear next to field labels in the product edit form, indicating the field's priority level for agent context generation.

**Badge Format**: `[Priority 1]` with an info icon (ⓘ)

**Badge Colors**:
- **Red**: Priority 1 - Always Included
- **Orange**: Priority 2 - High Priority
- **Blue**: Priority 3 - Medium Priority
- **No Badge**: Unassigned (not sent to agents)

#### Where Badges Appear

Badges are shown on all configuration fields across tabs:

**Tech Stack Tab**:
- Programming Languages
- Backend Stack
- Frontend Stack
- Databases
- Infrastructure

**Architecture Tab**:
- Architecture Pattern
- API Style
- Design Patterns
- Architecture Notes

**Features Tab**:
- Core Features

**Test Config Tab**:
- Testing Strategy
- Testing Frameworks
- Coverage Target

#### Understanding Badge Tooltips

Hover over the **info icon (ⓘ)** next to any badge to see:

**Priority 1 Tooltip**:
```
Priority 1 - Always Included
This field is always sent to AI agents in missions.

You can change field priorities in:
User Settings → General → Field Priority Configuration
```

**Priority 2 Tooltip**:
```
Priority 2 - High Priority
This field is included when token budget allows.

You can change field priorities in:
User Settings → General → Field Priority Configuration
```

**Priority 3 Tooltip**:
```
Priority 3 - Medium Priority
This field is included last, may be dropped if budget exceeded.

You can change field priorities in:
User Settings → General → Field Priority Configuration
```

#### Using Badges to Guide Data Entry

**High Priority Fields** (Red/Orange badges):
- Fill these first - they're most important for agents
- Provide detailed, accurate information
- Update these regularly as your product evolves

**Medium Priority Fields** (Blue badges):
- Fill after high priority fields
- Provide good context but not critical
- Can be more general or high-level

**Unassigned Fields** (No badge):
- These fields won't be sent to agents
- Still useful for documentation purposes
- Consider assigning priority if agents need this info

#### Changing Field Priorities

If you notice a field that should have different priority:

1. Click the info icon tooltip to see the link to Settings
2. Navigate to **User Settings → General → Field Priority Configuration**
3. Drag the field to your desired priority level
4. Save changes
5. Return to product edit form - badge will update on next page load

**Note**: Priority changes affect all products, not just the one you're editing. Priorities are a user-wide preference for how you want agents to receive context.

## Next Steps

- Explore [Example Projects](../examples/) for real-world patterns
- Read [Architecture Guide](ARCHITECTURE.md) for system design
- Check [Best Practices](BEST_PRACTICES.md) for optimization tips
- Join our [Discord Community](https://discord.gg/giljo) for support

---

_Last Updated: 2025-10-27_
_Version: 1.1.0_
