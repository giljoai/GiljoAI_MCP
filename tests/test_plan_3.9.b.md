# Test Plan for Project 3.9.b: Orchestrator Templates v2

## Testing Strategy

### 1. Performance Benchmarks
**Target: <0.1ms template generation**

- **Template Retrieval Speed**
  - Test single template retrieval from database
  - Test cached vs uncached performance
  - Measure with both SQLite and PostgreSQL
  - Benchmark with varying template sizes

- **Augmentation Performance**
  - Test runtime augmentation overhead
  - Measure variable substitution speed
  - Test complex augmentation chains

### 2. Product Isolation Tests

- **Multi-Tenant Verification**
  - Create templates for multiple products
  - Verify no cross-product template access
  - Test concurrent template operations
  - Validate product_id scoping in all queries

- **Template Namespace Isolation**
  - Same template names across different products
  - Verify correct template retrieval by product
  - Test archive isolation between products

### 3. Template Augmentation Edge Cases

- **Variable Substitution**
  - Test missing variables
  - Test recursive variable references
  - Test special characters in variables
  - Test empty augmentation maps

- **Base Template Integrity**
  - Verify base templates remain unchanged
  - Test augmentation doesn't modify database
  - Validate rollback on failed augmentations

- **Complex Augmentations**
  - Nested variable substitutions
  - Multi-level augmentations
  - Conflicting augmentation keys
  - Invalid augmentation formats

### 4. Database Migration Tests

- **Migration from mission_templates.py**
  - Verify all 5 base templates migrated
  - Test template content integrity
  - Validate template metadata preservation

- **Archive System**
  - Test auto-archiving on modification
  - Verify version history tracking
  - Test archive retrieval and restoration
  - Validate timestamp accuracy

### 5. MCP Tool Integration Tests

- **list_agent_templates()**
  - Test with various product_ids
  - Test empty template list
  - Test pagination if implemented
  - Verify response format

- **get_agent_template()**
  - Test with valid/invalid template names
  - Test augmentation parameter
  - Test missing templates
  - Test special characters in names

- **create_agent_template()**
  - Test duplicate name handling
  - Test invalid category
  - Test large mission content
  - Test special characters

- **archive_template()**
  - Test archiving non-existent templates
  - Test reason field limits
  - Test archive without modifications
  - Test concurrent archive operations

### 6. Backward Compatibility

- **Orchestrator.py Integration**
  - Test existing orchestrator functionality
  - Verify MissionTemplateGenerator compatibility
  - Test fallback to hardcoded templates
  - Validate smooth migration path

### 7. Edge Cases and Error Handling

- **Database Connection Issues**
  - Test template operations with disconnected DB
  - Test transaction rollback scenarios
  - Test concurrent access conflicts

- **Data Validation**
  - Test extremely long template names
  - Test invalid JSON in augmentations
  - Test SQL injection attempts
  - Test Unicode and special characters

- **Cache Invalidation**
  - Test cache updates on template modification
  - Test cache size limits
  - Test cache expiration if implemented

### 8. Integration Tests

- **Full Workflow**
  - Create project → Create templates → Spawn agents
  - Test template usage in agent missions
  - Verify template suggestions work
  - Test complete CRUD cycle

## Test Execution Plan

1. **Unit Tests** - Test individual functions in isolation
2. **Integration Tests** - Test component interactions
3. **Performance Tests** - Measure and validate speed targets
4. **Stress Tests** - Test system under high load
5. **Regression Tests** - Ensure existing functionality preserved

## Success Metrics

- ✅ All tests pass with >95% coverage
- ✅ Performance target <0.1ms achieved
- ✅ Zero cross-product data leakage
- ✅ All edge cases handled gracefully
- ✅ Backward compatibility maintained
- ✅ Migration completes without data loss