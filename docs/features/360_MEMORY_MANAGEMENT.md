# 360 Memory Management

**Version**: v3.1+
**Last Updated**: 2025-11-26
**Status**: Implemented (Handovers 0135-0139, 0249)

## Overview

360 Memory Management provides orchestrators with cumulative product knowledge and project history through persistent memory storage. This allows orchestrators to build upon previous work and maintain context across multiple projects.

---

## Technical Requirements

### Database Schema

**Critical**: Memory is stored in `Product.product_memory` JSONB column, **NOT** in `config_data`.

```python
class Product(Base):
    __tablename__ = 'products'

    id = Column(UUID, primary_key=True)
    product_memory = Column(JSONB, nullable=True)  # ← Memory stored here
    config_data = Column(JSONB, nullable=True)     # ← Configuration here (separate)
```

**Sequential Numbering**: Projects are numbered chronologically (1, 2, 3, ...) for history tracking.

### Data Structure

```json
{
  "product_memory": {
    "objectives": ["Initial objectives..."],
    "decisions": ["Key architectural decisions..."],
    "context": {
      "technical_stack": "Python/FastAPI/PostgreSQL/Vue3",
      "deployment_target": "Local/network"
    },
    "knowledge_base": {
      "lessons_learned": ["Lessons from previous projects..."],
      "best_practices": ["Established patterns..."]
    },
    "sequential_history": [
      {
        "sequence": 1,
        "type": "project_closeout",
        "project_id": "uuid-123",
        "project_name": "Initial Setup",
        "summary": "Set up authentication system...",
        "key_outcomes": ["JWT implemented", "OAuth2 integrated"],
        "decisions_made": ["Chose RS256 over HS256", "Redis for sessions"],
        "git_commits": [  // Optional: Only with GitHub integration
          {
            "hash": "abc123",
            "message": "feat: Add OAuth2 provider",
            "author": "developer@example.com",
            "timestamp": "2025-11-16T10:00:00Z"
          }
        ],
        "timestamp": "2025-11-16T10:00:00Z"
      }
    ]
  }
}
```

---

## Integration Options

### GitHub API Integration (Optional)

**Toggle Location**: My Settings → Integrations → GitHub Integration

**Configuration Storage**: `Product.product_memory.git_integration`

When enabled:
- Git commits are tracked automatically during project closeout
- Commit history included in sequential_history entries
- Provides detailed development timeline

### Manual Summaries (Fallback)

When GitHub integration is disabled:
- Users provide manual summaries during project closeout
- Works as "mini-git" mode with text descriptions
- No external dependencies required

---

## Success Criteria

| Scenario | Expected Behavior |
|----------|-------------------|
| **Fresh product** | Orchestrator asks for details (empty memory indicates new product) |
| **Established product** | Orchestrator sees history, builds on previous decisions |
| **GitHub enabled** | Commits tracked automatically during closeout |
| **GitHub disabled** | Manual summaries work (mini-git fallback) |
| **UI updates** | User sees memory added in real-time via WebSocket |
| **Multi-project** | Sequential numbering maintains chronological order |

---

## Multi-Tenant Isolation

Memory is isolated per product per tenant:
- All memory operations filter by `tenant_key`
- WebSocket events broadcast only within tenant scope
- No cross-tenant memory leakage possible
- Each tenant has independent product memories

---

## MCP Tool Interface

### For Orchestrators

**Tool**: `close_project_and_update_memory`

```python
# At project completion, orchestrator calls:
result = await close_project_and_update_memory(
    project_id="uuid-123",
    summary="Implemented OAuth2 authentication with JWT refresh tokens",
    key_outcomes=[
        "Reduced login latency by 40%",
        "Added MFA support with TOTP",
        "Integrated with 3 OAuth providers"
    ],
    decisions_made=[
        "Chose JWT over session-based auth for scalability",
        "Adopted Redis for token blacklisting",
        "Used RS256 for token signing"
    ]
)
```

### For Reading Memory

**Tool**: `fetch_360_memory`

```python
# Orchestrator reads product memory:
memory = await fetch_360_memory(
    product_id="uuid-456",
    limit=5  # Last 5 projects
)
```

---

## Real-Time Updates

### WebSocket Events

When memory is updated, a WebSocket event is emitted:

```javascript
// Frontend receives:
{
  "event": "product:memory:updated",
  "data": {
    "product_id": "uuid-456",
    "project_closed": "uuid-123",
    "sequence_number": 12,
    "timestamp": "2025-11-16T10:00:00Z"
  }
}
```

### UI Components

- **Products View**: Shows memory status badge
- **Project Closeout Modal**: Collects summary and outcomes
- **Memory Timeline**: Displays sequential history

---

## Implementation Details

### Service Layer

**ProductService** (`src/giljo_mcp/services/product_service.py`):
- `update_product_memory()` - Adds new entry to sequential_history
- `get_product_memory()` - Retrieves memory for orchestrator context
- `clear_product_memory()` - Resets memory (admin only)

### API Endpoints

**Closeout Endpoint** (`/api/projects/{id}/closeout`):
- Marks project as complete
- Updates 360 memory
- Fetches GitHub commits if enabled
- Emits WebSocket event

---

## See Also

- [CLAUDE.md](../CLAUDE.md) - 360 Memory Management section
- [SERVICES.md](../SERVICES.md) - ProductService memory methods
- [ORCHESTRATOR.md](../ORCHESTRATOR.md) - How orchestrators use memory
- Handovers: 0135-0139 (implementation), 0249 (closeout workflow)