# Test Collection Errors Analysis

## Summary
- **Total Collection Errors**: 5
- **Collection Error Types**: Import errors (4), pytest configuration (1)
- **Tests Collected**: 1348 tests (out of expected 2061)
- **Tests Skipped**: 13 tests (installer components + refactoring TODOs)

## Collection Errors Detail

### 1. Missing Module: `installer.core.installer`
**File**: `tests/installer/test_installer_v3.py:20`
**Error**: `ModuleNotFoundError: No module named 'installer.core.installer'`
**Impact**: Installer v3 tests cannot run
**Root Cause**: Module was removed or moved during refactoring
**Fix Strategy**: Either restore module or remove obsolete tests

### 2. IndentationError in Test File
**File**: `tests/integration/test_0104_complete_integration.py:81`
**Error**: `IndentationError: unexpected indent`
**Impact**: Complete integration test cannot run
**Root Cause**: Syntax error in test file
**Fix Strategy**: Fix indentation (5 min quick win)

### 3. Missing Module: `src.giljo_mcp.agent_communication_queue`
**File**: `tests/integration/test_multi_tool_orchestration.py:31`
**Error**: `ModuleNotFoundError: No module named 'src.giljo_mcp.agent_communication_queue'`
**Impact**: Multi-tool orchestration tests cannot run
**Root Cause**: Module moved to different location during service extraction
**Fix Strategy**: Update import path to correct location

### 4. Missing Pytest Marker: `security`
**File**: `tests/integration/test_server_mode_auth.py`
**Error**: `'security' not found in markers configuration option`
**Impact**: Server mode auth tests cannot run
**Root Cause**: Pytest marker not registered in pyproject.toml
**Fix Strategy**: Add `security` marker to pytest configuration (5 min quick win)

### 5. Missing Model: `AgentJob`
**File**: `tests/integration/test_stage_project_workflow.py:27`
**Error**: `ImportError: cannot import name 'AgentJob' from 'src.giljo_mcp.models'`
**Impact**: Stage project workflow tests cannot run
**Root Cause**: `AgentJob` model removed or renamed during refactoring
**Fix Strategy**: Update imports to use `MCPAgentJob` or remove if obsolete

## Tests Skipped (TODO Markers)
These tests are intentionally skipped with TODO markers:
- `test_backup_integration.py` - TODO(0127a-2): MCPAgentJob refactoring needed
- `test_claude_code_integration.py` - TODO(0127a-2): MCPAgentJob refactoring needed
- `test_hierarchical_context.py` - TODO(0127a-2): MCPAgentJob refactoring needed
- `test_message_queue_integration.py` - TODO(0127a-2): MCPAgentJob refactoring needed
- `test_orchestrator_template.py` - TODO(0127a-2): MCPAgentJob refactoring needed

## Installer Tests Skipped
These installer tests are skipped due to missing components:
- `test_installation_flow.py` - Not all components available
- `test_config_manager.py` - Configuration Manager not available
- `test_docker.py` - Docker installer not available
- `test_health_checker.py` - Health check system not available
- `test_postgresql.py` - PostgreSQL installer not available
- `test_profile.py` - Profile system not available
- `test_redis.py` - Redis installer not available
- `test_service_manager.py` - Service Manager not available

## Impact on Test Suite
- **Original Test Count**: 2061 tests
- **Collected**: 1348 tests
- **Unable to Collect**: 713 tests (34.5%)
- **Collection Errors**: 5 files
- **Intentionally Skipped**: 13 tests

## Fix Priority
**P0 Critical** (blocking collection):
1. Fix indentation error (5 min)
2. Add security marker (5 min)
3. Update AgentJob imports to MCPAgentJob

**P1 High** (significant test loss):
4. Update agent_communication_queue import path
5. Investigate installer.core.installer removal

**P2 Medium** (TODO markers):
6. Address MCPAgentJob refactoring TODOs (Phase 5)
