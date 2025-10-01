# Mission Templates Test Suite

## Overview

Comprehensive test suite for the MissionTemplateGenerator system in Project 3.4.

## Test Structure

### Unit Tests (`test_mission_templates.py`)

- **TestMissionTemplateGenerator**: Core template generation tests
  - Orchestrator template generation with all required elements
  - Role-specific templates (analyzer, implementer, tester, reviewer)
  - Project-type customization (feature, bugfix, refactor, testing)
  - Behavioral instructions inclusion
  - Custom parameter injection
  - Template validation
  - Template caching for performance

### Integration Tests

- **TestOrchestratorIntegration**: Integration with ProjectOrchestrator
  - Spawning agents with templates
  - Custom mission overrides
  - Orchestrator agent with comprehensive template
  - Template context from project data
  - Parallel agent spawning
  - Context limit handling
  - Handoff instructions

### Edge Cases

- **TestEdgeCases**: Boundary conditions and error handling
  - Empty/null project parameters
  - Very long vision documents (100K+ characters)
  - Missing configuration values
  - Concurrent template generation
  - Memory/performance with large templates

### Behavioral Instructions

- **TestBehavioralInstructions**: Behavioral features
  - Parallel execution instructions
  - Message acknowledgment behavior
  - Handoff protocol
  - Status reporting instructions

## Running Tests

### All Tests

```bash
pytest tests/test_mission_templates.py -v
```

### Specific Test Classes

```bash
# Unit tests only
pytest tests/test_mission_templates.py::TestMissionTemplateGenerator -v

# Integration tests only
pytest tests/test_mission_templates.py::TestOrchestratorIntegration -v

# Edge cases only
pytest tests/test_mission_templates.py::TestEdgeCases -v
```

### With Coverage

```bash
pytest tests/test_mission_templates.py --cov=src.giljo_mcp.mission_templates --cov-report=html
```

### Performance Tests

```bash
pytest tests/test_mission_templates.py::TestEdgeCases::test_memory_performance_large_templates -v
```

## Test Fixtures (conftest.py)

### Database Fixtures

- `test_db`: In-memory PostgreSQL database
- `db_session`: Async database session
- `populated_db`: Database with sample data

### Object Fixtures

- `orchestrator`: ProjectOrchestrator instance
- `sample_project`: Test project
- `sample_agent`: Test agent
- `sample_template_context`: Template context

### Mock Fixtures

- `mock_vision_loader`: Vision document loader
- `mock_serena_mcp`: Serena MCP client
- `mock_message_router`: Message router

### Utility Fixtures

- `temp_dir`: Temporary directory
- `performance_monitor`: Performance tracking
- `event_loop`: Async event loop

## Expected Behavior

### Template Generation

1. All placeholders should be replaced
2. Key sections must be present (Vision Guardian, Scope Sheriff, etc.)
3. Vision chunking instructions included
4. Serena MCP integration mentioned
5. No unresolved placeholders

### Integration Points

1. Orchestrator uses template generator for missions
2. Custom missions override templates
3. Parallel agents receive coordination instructions
4. Context limits trigger proper instructions
5. Handoffs include transfer instructions

### Performance Requirements

- Template generation < 100ms per template
- Memory usage < 100MB for 100 templates
- Concurrent generation supports 10+ simultaneous requests
- Template caching reduces repeated generation time

## Test Coverage Goals

- Unit test coverage: > 90%
- Integration test coverage: > 80%
- Edge case coverage: 100% of identified scenarios
- Performance benchmarks: All pass

## Known Issues

- None currently identified

## Future Enhancements

- Add stress testing for 1000+ concurrent templates
- Add template versioning tests
- Add multi-language template tests
- Add template inheritance tests
