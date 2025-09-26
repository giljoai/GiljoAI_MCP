# Full Stack Feature Development Example

This example shows how GiljoAI MCP Orchestrator coordinates frontend, backend, and database development for implementing a complete feature.

## What This Example Shows

- Multi-layer development coordination
- Frontend-backend integration patterns
- Database schema evolution
- API contract management
- Automated testing across the stack

## The Scenario

You need to implement a "User Dashboard" feature that includes:

- Frontend: React components with real-time updates
- Backend: FastAPI endpoints with authentication
- Database: PostgreSQL schema with proper migrations
- Testing: End-to-end tests covering all layers

The orchestrator will coordinate specialized agents to build each layer while maintaining consistency.

## Architecture

```
┌─────────────────┐
│   Orchestrator  │ Manages the feature development workflow
└────────┬────────┘
         │
    ┌────┴────┬──────────┬──────────┬──────────┐
    ▼         ▼          ▼          ▼          ▼
┌────────┐ ┌───────┐ ┌───────┐ ┌──────┐ ┌────────┐
│Planner │ │Frontend│ │Backend│ │Database│ │Tester │
└────────┘ └───────┘ └───────┘ └──────┘ └────────┘
```

## Quick Start

```python
# 1. Initialize the orchestrator
from giljo_mcp import create_orchestrator

orchestrator = create_orchestrator(
    project_name="user-dashboard-feature",
    tenant_key="fullstack-demo"
)

# 2. Define the feature requirements
requirements = """
Implement a User Dashboard with:
- Real-time activity feed
- Usage statistics charts
- Settings management
- Export functionality
Must support 1000+ concurrent users with <100ms response time.
"""

# 3. Create the project
project = orchestrator.create_project(
    name="User Dashboard Feature",
    mission=requirements
)

# 4. Spawn full-stack agents
agents = orchestrator.spawn_agents([
    {"name": "planner", "type": "feature_planner"},
    {"name": "frontend", "type": "ui_developer"},
    {"name": "backend", "type": "api_developer"},
    {"name": "database", "type": "db_engineer"},
    {"name": "tester", "type": "qa_engineer"}
])

# 5. Execute the development workflow
orchestrator.execute()
```

## Agent Coordination Flow

### 1. Planning Phase

The **Planner Agent** creates:

- Feature specification document
- API contract definitions
- Database schema design
- Component architecture
- Test scenarios

### 2. Database Phase

The **Database Agent** implements:

- Schema creation with migrations
- Indexes for performance
- Stored procedures if needed
- Sample data for testing

### 3. Backend Phase

The **Backend Agent** develops:

- FastAPI endpoints matching contracts
- Business logic implementation
- Authentication/authorization
- WebSocket handlers for real-time

### 4. Frontend Phase

The **Frontend Agent** builds:

- React components
- State management (Redux/Context)
- WebSocket client for updates
- Responsive design

### 5. Testing Phase

The **Tester Agent** validates:

- Unit tests for each component
- Integration tests for APIs
- End-to-end user flows
- Performance benchmarks

## Implementation Details

See `fullstack_feature.py` for the complete orchestration code.

### Key Features Demonstrated

#### 1. Contract-First Development

```python
# Planner generates API contracts
contracts = planner.generate_contracts(requirements)

# Backend implements against contracts
backend.implement_endpoints(contracts)

# Frontend consumes using contracts
frontend.generate_client(contracts)
```

#### 2. Synchronized Schema Evolution

```python
# Database agent creates migration
migration = database.create_migration(schema_changes)

# Orchestrator ensures all agents update
orchestrator.broadcast({
    "event": "schema_updated",
    "migration": migration
})
```

#### 3. Cross-Layer Testing

```python
# Tester coordinates with all agents
test_suite = tester.create_e2e_tests(
    frontend_components=frontend.get_components(),
    api_endpoints=backend.get_endpoints(),
    database_schema=database.get_schema()
)
```

## Customization Options

### Adjust Technology Stack

```yaml
# config.yaml
frontend:
  framework: "vue" # or "react", "angular"
  state: "pinia" # or "redux", "mobx"

backend:
  framework: "django" # or "fastapi", "flask"
  orm: "sqlalchemy" # or "django-orm", "tortoise"

database:
  engine: "mysql" # or "postgresql", "mongodb"
```

### Define Custom Workflows

```python
# Custom coordination pattern
async def custom_workflow(orchestrator):
    # Parallel development of independent components
    await orchestrator.parallel_execute([
        ("frontend", "implement_ui"),
        ("backend", "implement_api")
    ])

    # Sequential integration
    await orchestrator.sequential_execute([
        ("database", "run_migrations"),
        ("backend", "connect_database"),
        ("frontend", "integrate_api"),
        ("tester", "run_e2e_tests")
    ])
```

## Expected Deliverables

After running this example, you'll have:

1. **Database**

   - Complete schema with tables, indexes, constraints
   - Migration scripts
   - Seed data

2. **Backend API**

   - RESTful endpoints
   - WebSocket handlers
   - Authentication middleware
   - API documentation (OpenAPI)

3. **Frontend Application**

   - Component library
   - Routing setup
   - State management
   - Real-time updates

4. **Test Suite**

   - Unit tests: 90%+ coverage
   - Integration tests: All API endpoints
   - E2E tests: Critical user paths
   - Performance tests: Load scenarios

5. **Documentation**
   - API reference
   - Component storybook
   - Deployment guide
   - Architecture diagrams

## Running the Example

```bash
# Install dependencies
pip install -r requirements.txt

# Run the orchestrator
python fullstack_feature.py

# Monitor progress
python monitor.py --project user-dashboard-feature

# View results
python view_results.py
```

## Monitoring Progress

The orchestrator provides real-time updates:

```python
# Subscribe to events
orchestrator.on("agent_update", lambda e: print(f"{e.agent}: {e.message}"))
orchestrator.on("phase_complete", lambda e: print(f"✅ {e.phase} completed"))

# Check agent status
status = orchestrator.get_status()
for agent, info in status.items():
    print(f"{agent}: {info['progress']}% - {info['current_task']}")
```

## Troubleshooting

### Agents Not Coordinating

```python
# Check message flow
messages = orchestrator.debug_messages()
print(f"Total messages: {len(messages)}")
print(f"Pending: {len([m for m in messages if not m.acknowledged])}")
```

### Schema Conflicts

```python
# Rollback and retry
database.rollback_migration()
orchestrator.retry_phase("database")
```

### Performance Issues

```python
# Get performance metrics
metrics = orchestrator.get_metrics()
print(f"API latency: {metrics['api_p95']}ms")
print(f"DB queries: {metrics['db_queries_per_second']}")
```

## Next Steps

- Modify the feature requirements to build different functionalities
- Add more specialized agents (e.g., security scanner, performance optimizer)
- Implement continuous deployment pipeline
- Create reusable feature templates

## Learn More

- [Orchestration Patterns](../../docs/patterns/)
- [Agent Communication](../../docs/guides/messaging.md)
- [Full API Reference](../../docs/api/)
