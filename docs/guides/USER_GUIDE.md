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
- SQLite (included with Python)
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
- **Status**: active, completed, or archived

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
GILJO_DB_URL=sqlite:///giljo.db
GILJO_LOG_LEVEL=INFO
GILJO_MAX_AGENTS=10
GILJO_CONTEXT_BUDGET=150000
```

### Database Configuration

```yaml
# config.yaml
database:
  # Local development (default)
  url: sqlite:///giljo.db

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

# Switch to a project
client.switch_project(project_id)

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

### Project Templates

```python
# Use a project template
from giljo_mcp.templates import ProjectTemplate

template = ProjectTemplate.web_application()
project = client.create_project(**template)
```

## Agent Management

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

#### 3. Database Lock (SQLite)

**Problem**: Database locked error in local mode

```bash
# Solution: Increase timeout and use WAL mode
sqlite3 giljo.db "PRAGMA journal_mode=WAL;"
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

## Next Steps

- Explore [Example Projects](../examples/) for real-world patterns
- Read [Architecture Guide](ARCHITECTURE.md) for system design
- Check [Best Practices](BEST_PRACTICES.md) for optimization tips
- Join our [Discord Community](https://discord.gg/giljo) for support

---

_Last Updated: 2025-09-16_
_Version: 1.0.0_
