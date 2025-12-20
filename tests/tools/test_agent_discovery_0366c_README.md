# Test Suite: agent_discovery.py - Phase C TDD (RED Phase)

**Handover**: 0366c - Agent Identity Refactor (Phase C)
**Status**: RED Phase Complete - All tests passing (10/10)
**Created**: 2025-12-20

## Purpose

This test suite enforces the new semantic parameter naming convention from the Agent Identity Refactor:
- `job_id` = Work order UUID (the WHAT - persistent across succession)
- `agent_id` = Executor UUID (the WHO - specific instance)

## Test Coverage

### TestAgentDiscoverySemantics (7 tests)
1. `test_get_available_agents_returns_agent_metadata` - Verifies agent template discovery returns correct metadata
2. `test_get_available_agents_multi_tenant_isolation` - Ensures multi-tenant isolation (critical security test)
3. `test_get_available_agents_depth_type_only` - Tests minimal metadata mode (~50 tokens)
4. `test_get_available_agents_depth_full` - Tests full metadata mode (~1.2k tokens)
5. `test_format_agent_info_handles_missing_fields` - Tests graceful handling of missing version/role/description
6. `test_get_available_agents_filters_inactive_templates` - Ensures only active templates are discovered
7. `test_get_available_agents_invalid_tenant_key` - Tests graceful handling of invalid tenant keys

### TestAgentDiscoveryDocumentation (2 tests)
1. `test_get_available_agents_signature_clarity` - Verifies parameter naming clarity (no job_id/agent_id in discovery)
2. `test_format_agent_info_signature_clarity` - Verifies _format_agent_info accepts AgentTemplate

### TestAgentDiscoveryIntegrationWithNewModel (1 test)
1. `test_discovery_independent_of_job_execution_state` - Critical test: template discovery should NOT be affected by running jobs/executions

## Key Findings

### Current Implementation Analysis
The `agent_discovery.py` tool is CORRECTLY implemented:
- **No job_id or agent_id parameters** - Discovery returns templates (the WHAT), not executions (the WHO)
- **Multi-tenant isolation enforced** - All queries filter by tenant_key
- **Depth configuration supported** - type_only (~50 tokens) vs full (~1.2k tokens)
- **Graceful error handling** - Invalid tenant keys return empty lists, not crashes

### Database Model Considerations
- `AgentTemplate.version` has a database default of "1.0.0"
- `AgentTemplate.template_content` is required (NOT NULL) but deprecated
- `AgentTemplate.system_instructions` has a default empty string

### Semantic Clarity
The tool correctly separates concerns:
- **Templates** (AgentTemplate) = Job types available (WHAT can be done)
- **Jobs** (AgentJob) = Work orders (WHAT needs to be done)
- **Executions** (AgentExecution) = Executor instances (WHO is doing the work)

Discovery returns templates, which spawn jobs, which create executions.

## Test Results

```
tests/tools/test_agent_discovery_0366c.py::TestAgentDiscoverySemantics::test_get_available_agents_returns_agent_metadata PASSED
tests/tools/test_agent_discovery_0366c.py::TestAgentDiscoverySemantics::test_get_available_agents_multi_tenant_isolation PASSED
tests/tools/test_agent_discovery_0366c.py::TestAgentDiscoverySemantics::test_get_available_agents_depth_type_only PASSED
tests/tools/test_agent_discovery_0366c.py::TestAgentDiscoverySemantics::test_get_available_agents_depth_full PASSED
tests/tools/test_agent_discovery_0366c.py::TestAgentDiscoverySemantics::test_format_agent_info_handles_missing_fields PASSED
tests/tools/test_agent_discovery_0366c.py::TestAgentDiscoverySemantics::test_get_available_agents_filters_inactive_templates PASSED
tests/tools/test_agent_discovery_0366c.py::TestAgentDiscoverySemantics::test_get_available_agents_invalid_tenant_key PASSED
tests/tools/test_agent_discovery_0366c.py::TestAgentDiscoveryDocumentation::test_get_available_agents_signature_clarity PASSED
tests/tools/test_agent_discovery_0366c.py::TestAgentDiscoveryDocumentation::test_format_agent_info_signature_clarity PASSED
tests/tools/test_agent_discovery_0366c.py::TestAgentDiscoveryIntegrationWithNewModel::test_discovery_independent_of_job_execution_state PASSED

======================= 10 passed in 4.30s ==========================
```

## Next Steps (GREEN Phase)

Since all tests are PASSING, this indicates the current implementation of `agent_discovery.py` is ALREADY CORRECT and follows the new semantic naming conventions. No refactoring needed for this tool.

**Recommendation**: Move to next tool in Phase C refactoring pipeline.

## Files

- Test Suite: `tests/tools/test_agent_discovery_0366c.py`
- Implementation: `src/giljo_mcp/tools/agent_discovery.py`
- Models: `src/giljo_mcp/models/agent_identity.py`, `src/giljo_mcp/models/templates.py`
