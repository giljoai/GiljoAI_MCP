# Handover 0368: Test Code Migration Roadmap

**Status**: PLANNED (not started)
**Priority**: MEDIUM
**Estimated Effort**: 22-30 hours
**Dependencies**: Handover 0367d complete

---

## Overview

Migrate test fixtures and test files from MCPAgentJob to AgentJob + AgentExecution.

## Scope

| Category | Files | References | Est. Hours |
|----------|-------|------------|------------|
| Test Fixtures | 20-30 | ~200 | 4-6 |
| Unit Tests | 100+ | ~800 | 12-16 |
| Integration Tests | 40+ | ~291 | 6-8 |
| **Total** | **169** | **1,291** | **22-30** |

## Phases

### Phase 1: Fixture Migration (0368a)
- Replace MCPAgentJob fixtures with AgentJob + AgentExecution
- Update factory functions in tests/helpers/test_factories.py
- Update base fixtures in tests/fixtures/base_fixtures.py

### Phase 2: Unit Test Migration (0368b)
- Update service layer tests
- Update API endpoint tests
- Replace job_id (int) assertions with agent_id (UUID)

### Phase 3: Integration Test Migration (0368c)
- Update end-to-end workflow tests
- Verify WebSocket event assertions use agent_id
- Update succession and spawning tests

## Field Mapping Reference

| MCPAgentJob | New Location |
|-------------|--------------|
| job_id | AgentJob.job_id (work order) |
| agent_type | AgentExecution.agent_type |
| mission | AgentJob.mission |
| status | AgentExecution.status |
| spawned_by | AgentExecution.spawned_by (agent_id UUID) |

See: handovers/Reference_docs/0358_model_mapping_reference.md

## Success Criteria

- [ ] Zero MCPAgentJob imports in tests/
- [ ] All test fixtures use AgentJob + AgentExecution
- [ ] All tests pass (no fixture-related failures)
- [ ] Coverage maintained at >80%

---

*This roadmap will be expanded when 0368 series begins.*
