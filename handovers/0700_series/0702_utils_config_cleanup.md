# Handover 0702: Utils & Config Cleanup

## Context

This handover addresses technical debt in utility functions and configuration handling code. The GiljoAI MCP codebase has accumulated multiple config-related modules, duplicate utility implementations, and legacy aliases that need consolidation or cleanup.

**Why this cleanup is needed:**
1. **Duplicate PathResolver classes**: Two separate PathResolver implementations exist - one in discovery.py (path resolution with DB/config fallback) and one in utils/path_resolver.py (cross-platform path normalization)
2. **Legacy aliases proliferation**: config_manager.py contains 15+ legacy property aliases for backward compatibility
3. **Orphan utility module**: download_utils.py has no active importers in production code
4. **Config fragmentation**: 7 different config-related files with overlapping concerns
5. **Cleanup index finding**: The cleanup index (0700 series) shows 0 entries in utils/config components despite obvious cleanup opportunities

## Research Findings

### 1. Duplicate PathResolver Implementations

| File | Purpose | Active Usage |
|------|---------|--------------|
| src/giljo_mcp/discovery.py:26 | Path resolution with env/db/config fallback | Used by context.py tools |
| src/giljo_mcp/utils/path_resolver.py:10 | Cross-platform path normalization | Only used by test file |

**Issue**: Different classes with same name, different responsibilities. The utils/path_resolver.py version is only referenced by:
- Self-references (convenience functions)
- tests/test_windows_paths.py

**Recommendation**: 
- Rename utils/path_resolver.py to utils/path_normalizer.py (or similar)
- OR merge functionality into the discovery.PathResolver class
- Keep tests working by updating imports

### 2. Legacy Aliases in config_manager.py

The config_manager.py file contains multiple legacy alias properties for backward compatibility:

**DatabaseConfig aliases (lines 96-135):**
- database_type (alias for type)
- pg_host (alias for host)
- pg_port (alias for port)
- pg_database (alias for database_name)
- pg_user (alias for username)
- pg_password (alias for password)

**AgentConfig aliases (lines 231-254):**
- max_per_project (alias for max_agents)
- context_limit (alias for default_context_budget)
- handoff_threshold (alias for context_warning_threshold)

**MessageConfig aliases (lines 267-289):**
- batch_size (internal _batch_size)
- retry_attempts (alias for max_retries)
- retry_delay (internal _retry_delay)

**TenantConfig aliases (lines 301-324):**
- enabled (alias for enable_multi_tenant)
- default_key (alias for default_tenant_key)
- isolation_strict (computed from tenant_isolation_level)

**FeatureFlags aliases (lines 337-344):**
- websocket_updates (alias for enable_websockets)

**Recommendation**: Mark these aliases with explicit DEPRECATED comments and schedule removal in v4.0

### 3. Orphan Utility Module - download_utils.py

**File**: src/giljo_mcp/tools/download_utils.py

**Functions**:
- get_server_url_from_config() - Returns server URL from env or default
- download_file() - HTTP download with API key auth
- extract_zip_to_directory() - ZIP extraction to target dir

**Usage**: Zero production imports found (only historical reference in REFACTORING_SUMMARY.md)

**Recommendation**: Delete or mark for removal if no planned usage

### 4. Config Module Fragmentation

Seven config-related modules exist with overlapping concerns:

| Module | Purpose | Actively Used |
|--------|---------|---------------|
| config_manager.py | Main configuration (YAML, env vars, dataclasses) | Yes - primary |
| services/config_service.py | Serena config reading with caching | Yes - template_manager |
| services/claude_config_manager.py | Claude Code .claude dir management | Yes - tests only |
| repositories/configuration_repository.py | DB-based config (tenant keys, etc.) | Yes - endpoints |
| prompt_generation/testing_config_generator.py | Testing context generation | Yes - mission_planner |
| monitoring/health_config.py | Health check timeouts | Unknown |
| models/config.py | Config database models | Yes - core models |

**Recommendation**: Document clear responsibilities, no immediate action needed

### 5. api_helpers Directory Review

**File**: src/giljo_mcp/api_helpers/task_helpers.py

**Functions**:
- get_db_manager() - Global DB manager accessor
- create_task_for_api() - Task creation wrapper
- list_tasks_for_api() - Task listing wrapper
- update_task_for_api() - Task update wrapper
- get_product_task_summary_for_api() - Task summary wrapper

**Usage**: Only test_api_integration_fix.py imports these functions

**Recommendation**: Evaluate if these should be in TaskService instead

### 6. api_key_utils.py Review

**File**: src/giljo_mcp/api_key_utils.py

**Functions**:
- generate_api_key() - Generate new API keys
- hash_api_key() - Hash keys for storage
- verify_api_key() - Verify key against hash
- get_key_prefix() - Extract key prefix
- validate_api_key_format() - Validate format

**Usage**: Actively used across:
- auth/dependencies.py
- services/auth_service.py
- api/endpoints/mcp_session.py
- Multiple test files

**Recommendation**: Keep as-is, well-scoped utility module

### 7. framing_helpers.py Review

**File**: src/giljo_mcp/tools/context_tools/framing_helpers.py

**Usage**: Actively used in:
- tools/context_tools/__init__.py
- tools/context.py
- Test files for priority framing

**Recommendation**: Keep as-is, actively used

## Tasks

### Critical (Must Do)
1. [ ] Add DEPRECATED comments to all legacy aliases in config_manager.py with removal target v4.0
2. [ ] Create migration plan for consumers of legacy aliases

### High Priority
3. [ ] Resolve PathResolver naming collision:
   - Option A: Rename utils/path_resolver.py to utils/path_normalizer.py
   - Option B: Merge into discovery.PathResolver as a staticmethod utility
4. [ ] Update test imports after PathResolver resolution

### Medium Priority
5. [ ] Evaluate download_utils.py for deletion (no active usage)
6. [ ] Evaluate api_helpers/task_helpers.py for migration to TaskService
7. [ ] Add entry to cleanup_index.json for utils/config components

### Low Priority
8. [ ] Document config module responsibilities in docs/architecture/
9. [ ] Consider consolidating ClaudeConfigManager into ConfigService

## Files to Modify

| File | Change Type | Description |
|------|-------------|-------------|
| src/giljo_mcp/config_manager.py | Update | Add DEPRECATED comments to 15+ legacy aliases |
| src/giljo_mcp/utils/path_resolver.py | Rename/Update | Resolve naming collision with discovery.PathResolver |
| tests/test_windows_paths.py | Update | Update imports after PathResolver changes |
| handovers/0700_series/cleanup_index.json | Update | Add utils/config entries |

## Files to Delete

| File | Reason | Risk |
|------|--------|------|
| src/giljo_mcp/tools/download_utils.py | No active production usage | LOW - confirm no planned usage first |

## Verification

### Pre-cleanup Verification
```bash
# Verify no hidden usages of download_utils
grep -rn "download_utils" src/ api/ --include="*.py"

# Verify PathResolver usage
grep -rn "PathResolver" src/ api/ tests/ --include="*.py"

# Verify legacy alias usage (sample)
grep -rn "pg_host" src/ api/ --include="*.py"
```

### Post-cleanup Verification
```bash
# Run tests
pytest tests/ -v -x

# Verify no broken imports
python -c "from src.giljo_mcp.config_manager import ConfigManager"

# Verify API starts
python api/run_api.py --port 7273
```

## Risk Assessment

**Overall Risk**: LOW

**Rationale**:
- Legacy aliases are additive (old code keeps working)
- PathResolver change is isolated to test file
- download_utils has no production callers
- No database schema changes
- Changes are mostly cosmetic/organizational

**Rollback Plan**:
- Git revert for any problematic commits
- No migration scripts needed
- No data transformation required

## Dependencies

- None from other 0700-series handovers
- Should be done before v4.0 removal cycle

## Estimated Effort

| Task | Time |
|------|------|
| Add DEPRECATED comments | 30 min |
| PathResolver resolution | 45 min |
| Test updates | 30 min |
| Verification | 30 min |
| Documentation | 15 min |
| **Total** | ~2.5 hours |
