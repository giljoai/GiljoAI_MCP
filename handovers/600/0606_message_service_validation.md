# Handover 0606: MessageService Validation

**Phase**: 1
**Tool**: CCW (Cloud)
**Agent Type**: tdd-implementor
**Duration**: 1 day
**Parallel Group**: Group A (Services)
**Depends On**: 0602

---

## Context

**Read First**: `handovers/600/AGENT_REFERENCE_GUIDE.md` for universal project context.

**Previous Handovers**: Handover 0602 established test baseline.

**This Handover**: Create comprehensive unit and integration tests for MessageService, achieving 80%+ coverage while validating JSONB message handling, agent-to-agent communication queue operations, message routing, and multi-tenant isolation.

---

## Specific Objectives

- **Objective 1**: Create comprehensive unit tests for all MessageService methods (80%+ coverage)
- **Objective 2**: Create integration tests for message queue operations and JSONB handling
- **Objective 3**: Validate agent-to-agent messaging workflow
- **Objective 4**: Test JSONB message storage and retrieval (schema-less data)
- **Objective 5**: Verify message routing and filtering
- **Objective 6**: Ensure multi-tenant isolation

---

## Tasks

### Task 1: Read and Analyze MessageService
**What**: Read MessageService implementation to understand all methods
**Files**: `src/giljo_mcp/services/message_service.py`

**Methods to Test**:
- `send_message(from_agent, to_agent, message_type, payload, tenant_key)`
- `get_message(message_id, tenant_key)`
- `get_messages_for_agent(agent_id, tenant_key, filters=None)`
- `get_unread_messages(agent_id, tenant_key)`
- `mark_message_read(message_id, tenant_key)`
- `mark_all_messages_read(agent_id, tenant_key)`
- `delete_message(message_id, tenant_key)`
- `get_message_thread(message_id, tenant_key)` - Get conversation thread
- `search_messages(tenant_key, query, filters=None)` - JSONB search

### Task 2: Implement CRUD Tests
**What**: Write unit tests for message operations
**Files**: `tests/unit/test_message_service.py`

**Test Coverage** (25+ tests):

**Send Message Tests** (7 tests):
- `test_send_message_success`
- `test_send_message_with_jsonb_payload`
- `test_send_message_nested_jsonb`
- `test_send_message_invalid_agent`
- `test_send_message_missing_required_fields`
- `test_send_message_wrong_tenant`
- `test_send_message_sets_timestamp`

**Read Message Tests** (6 tests):
- `test_get_message_success`
- `test_get_message_not_found`
- `test_get_message_wrong_tenant`
- `test_get_messages_for_agent`
- `test_get_unread_messages`
- `test_get_message_thread`

**Update Message Tests** (4 tests):
- `test_mark_message_read`
- `test_mark_message_read_idempotent`
- `test_mark_all_messages_read`
- `test_mark_message_read_wrong_tenant`

**Delete Message Tests** (3 tests):
- `test_delete_message_success`
- `test_delete_message_not_found`
- `test_delete_message_wrong_tenant`

**Search Tests** (5 tests):
- `test_search_messages_by_type`
- `test_search_messages_by_jsonb_field`
- `test_search_messages_by_date_range`
- `test_search_messages_multi_criteria`
- `test_search_messages_empty_results`

### Task 3: Implement JSONB Handling Tests
**What**: Write tests specifically for JSONB payload storage and querying
**Files**: `tests/unit/test_message_service.py`

**Test Coverage** (8 tests):
- `test_jsonb_payload_simple_dict`
- `test_jsonb_payload_nested_objects`
- `test_jsonb_payload_arrays`
- `test_jsonb_payload_mixed_types`
- `test_jsonb_query_by_field`
- `test_jsonb_query_nested_field`
- `test_jsonb_payload_preserves_types`
- `test_jsonb_payload_unicode_support`

**Example Test**:
```python
def test_jsonb_payload_nested_objects(self, message_service, test_tenant_key):
    """Test JSONB storage with deeply nested objects"""
    # Arrange: Complex nested payload
    payload = {
        "task": {
            "id": 123,
            "name": "Complex Task",
            "metadata": {
                "priority": "high",
                "tags": ["urgent", "review"],
                "assignee": {
                    "id": 456,
                    "name": "John Doe"
                }
            }
        }
    }

    # Act: Send message with nested payload
    message = message_service.send_message(
        from_agent="agent-1",
        to_agent="agent-2",
        message_type="task_update",
        payload=payload,
        tenant_key=test_tenant_key
    )

    # Assert: Nested data preserved
    retrieved = message_service.get_message(message.id, test_tenant_key)
    assert retrieved.payload["task"]["metadata"]["priority"] == "high"
    assert "urgent" in retrieved.payload["task"]["metadata"]["tags"]
    assert retrieved.payload["task"]["metadata"]["assignee"]["id"] == 456
```

### Task 4: Implement Agent Communication Queue Tests
**What**: Write tests for agent-to-agent messaging workflows
**Files**: `tests/unit/test_message_service.py`

**Test Coverage** (6 tests):
- `test_agent_send_to_specific_agent`
- `test_agent_broadcast_to_multiple_agents`
- `test_agent_receive_messages_fifo_order`
- `test_agent_message_filtering_by_type`
- `test_agent_unread_count_tracking`
- `test_agent_message_thread_retrieval`

### Task 5: Create Integration Tests
**What**: Create integration tests for message queue operations
**Files**: `tests/integration/test_message_service.py`

**Test Coverage** (10 tests):

**Multi-Tenant Isolation** (3 tests):
- `test_tenant_isolation_send`
- `test_tenant_isolation_retrieve`
- `test_tenant_isolation_search`

**Queue Operations** (4 tests):
- `test_message_queue_concurrency`
- `test_message_queue_ordering`
- `test_message_queue_filtering_performance`
- `test_message_thread_construction`

**JSONB Performance** (3 tests):
- `test_jsonb_search_performance`
- `test_jsonb_indexing_effectiveness`
- `test_large_payload_handling`

### Task 6: Run Tests and Verify Coverage
**Commands**:
```bash
pytest tests/unit/test_message_service.py -v \
  --cov=src/giljo_mcp/services/message_service.py \
  --cov-report=term-missing

pytest tests/integration/test_message_service.py -v
```

---

## Success Criteria

- [ ] **Unit Tests**: 44+ unit tests created
- [ ] **Integration Tests**: 10+ integration tests
- [ ] **Coverage**: ≥ 80% coverage on MessageService
- [ ] **JSONB Tested**: All JSONB operations validated
- [ ] **All Tests Pass**: 100% pass rate
- [ ] **PR Created**: Branch `0606-message-service-tests`

---

## Deliverables

### Code
- **Created**:
  - `tests/unit/test_message_service.py` (44+ tests)
  - `tests/integration/test_message_service.py` (10+ tests)

### Git Commit
- **Message**: `test: Add comprehensive MessageService tests (Handover 0606)`
- **Branch**: `0606-message-service-tests`

---

## Dependencies

### Requires
- **Handover 0602**: Test baseline established
- **Files**: `src/giljo_mcp/services/message_service.py`

### Blocks
- **Handover 0617**: Messages API validation

---

## Notes for Agent

### CCW (Cloud) Execution
- Create branch: `0606-message-service-tests`
- Focus on JSONB testing (PostgreSQL-specific)
- Test complex nested payloads

---

**Document Control**:
- **Handover**: 0606
- **Created**: 2025-11-14
- **Status**: Ready for execution
