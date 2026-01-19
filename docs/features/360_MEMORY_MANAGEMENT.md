# 360 Memory Management

**Version**: v3.3+
**Last Updated**: 2026-01-18
**Status**: Implemented (Handovers 0135-0139, 0249, 0390 Series)

## Overview

360 Memory Management provides orchestrators with cumulative product knowledge and project history through persistent memory storage. This allows orchestrators to build upon previous work and maintain context across multiple projects.

---

## Technical Requirements

### Database Schema

**Architecture**: Normalized `product_memory_entries` table (v3.3+, Handover 0390)

**DEPRECATED**: `Product.product_memory.sequential_history` JSONB array is deprecated.
Do not read from or write to this field. Use the `product_memory_entries` table via `ProductMemoryRepository`.

```python
class ProductMemoryEntry(Base):
    __tablename__ = 'product_memory_entries'

    id = Column(UUID, primary_key=True)
    product_id = Column(UUID, ForeignKey('products.id', ondelete='CASCADE'))
    project_id = Column(UUID, ForeignKey('projects.id', ondelete='SET NULL'), nullable=True)
    sequence = Column(Integer, nullable=False)
    entry_type = Column(String(50), nullable=False)
    summary = Column(Text, nullable=False)
    key_outcomes = Column(ARRAY(Text), nullable=True)
    decisions_made = Column(ARRAY(Text), nullable=True)
    git_commits = Column(JSONB, nullable=True)
    created_at = Column(DateTime(timezone=True), server_default=func.now())
```

**Key Features**:
- Foreign key relationships with cascade delete (product) and soft-delete (project)
- Proper indexes for query performance
- Sequential numbering maintained via database sequence
- Projects numbered chronologically (1, 2, 3, ...) for history tracking

### Data Structure (Normalized Table)

**Current Architecture** (v3.3+):
Memory entries are stored as normalized table rows in `product_memory_entries`:

```python
# Example entry from database
{
    "id": "uuid-789",
    "product_id": "uuid-456",
    "project_id": "uuid-123",
    "sequence": 1,
    "entry_type": "project_closeout",
    "summary": "Set up authentication system...",
    "key_outcomes": ["JWT implemented", "OAuth2 integrated"],
    "decisions_made": ["Chose RS256 over HS256", "Redis for sessions"],
    "git_commits": [  # Optional: Only with GitHub integration
        {
            "hash": "abc123",
            "message": "feat: Add OAuth2 provider",
            "author": "developer@example.com",
            "timestamp": "2025-11-16T10:00:00Z"
        }
    ],
    "created_at": "2025-11-16T10:00:00Z"
}
```

**DEPRECATED Structure** (JSONB, pre-v3.3):
```json
{
  "product_memory": {
    "sequential_history": [...]  # DEPRECATED - Do not use
  }
}
```

**Note**: Git integration settings remain in `Product.product_memory.git_integration` JSONB field.

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

**ProductMemoryRepository** (`src/giljo_mcp/repositories/product_memory_repository.py`):
- `create_entry()` - Adds new entry to `product_memory_entries` table
- `get_entries()` - Retrieves memory entries for orchestrator context
- `get_next_sequence()` - Gets next sequence number for product
- `delete_entries_for_product()` - Removes all entries (cascade on product delete)

**Deprecated** (JSONB approach, pre-v3.3):
- ~~`update_product_memory()`~~ - Deprecated, use `ProductMemoryRepository.create_entry()`
- ~~`get_product_memory()`~~ - Deprecated, use `ProductMemoryRepository.get_entries()`

### API Endpoints

**Closeout Endpoint** (`/api/projects/{id}/closeout`):
- Marks project as complete
- Updates 360 memory
- Fetches GitHub commits if enabled
- Emits WebSocket event

---

## Migration Notes (0390 Series)

**Timeline**: January 2026 (v3.3)

### What Changed

The 0390 handover series migrated 360 memory from JSONB arrays to a normalized `product_memory_entries` table:

1. **0390a**: Added `product_memory_entries` table with proper foreign keys
2. **0390b**: Updated all read operations to use the table
3. **0390c**: Stopped all writes to JSONB `sequential_history` array
4. **0390d**: Marked JSONB column as deprecated (scheduled for removal in v4.0)

### Why the Change

The normalized architecture provides:
- **Proper relational integrity**: Foreign keys with cascade delete
- **Better query performance**: Indexes on product_id and sequence
- **Cleaner data model**: No nested JSONB arrays to manage
- **Easier maintenance**: Standard SQL operations instead of JSONB manipulation

### For Developers

- **Use**: `ProductMemoryRepository` for all memory operations
- **Avoid**: Reading or writing `Product.product_memory.sequential_history`
- **Migration**: Existing JSONB data remains but is not read; table is source of truth
- **Removal**: JSONB column will be dropped in v4.0

---

## See Also

- [CLAUDE.md](../CLAUDE.md) - 360 Memory Management section
- [SERVICES.md](../SERVICES.md) - ProductService memory methods
- [ORCHESTRATOR.md](../ORCHESTRATOR.md) - How orchestrators use memory
- Handovers: 0135-0139 (implementation), 0249 (closeout workflow), 0390 (normalization)