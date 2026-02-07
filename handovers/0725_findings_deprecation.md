# Handover 0725: Code Health Audit - Deprecation & Legacy Patterns Findings

**Type**: Research Report (NO IMPLEMENTATION)
**Status**: Complete
**Date**: 2026-02-07
**Agent**: Deep Researcher

---

## Executive Summary

This audit identified 89+ instances of deprecated markers, legacy compatibility patterns, and technical debt across the GiljoAI MCP codebase.

Key findings:
- 2 legitimate TODO comments (mcp_installer.py has 1 actionable TODO)
- 48+ backward compatibility patterns requiring evaluation for removal
- 12+ deprecated field references documented in code
- 3 method stubs remaining after feature removal
- 1 placeholder API key in ai_tools.py (security concern)


---

## 1. DEPRECATED Markers

### 1.1 Explicitly Documented Deprecations

| File | Line | Deprecation | Status |
|------|------|-------------|--------|
| src/giljo_mcp/models/product_memory_entry.py | 6 | Product.product_memory.sequential_history JSONB deprecated | Replaced by normalized table |
| src/giljo_mcp/config_manager.py | 396-407 | mode field in config.yaml | Warns on detection |
| src/giljo_mcp/tools/orchestration.py | 230 | optional vision depth value | Normalized to light |
| src/giljo_mcp/thin_prompt_generator.py | 878 | Agent template section | Templates via MCP tool |
| src/giljo_mcp/tools/context_tools/get_project.py | 5, 35, 96 | context_budget field | Excluded from response |
| api/endpoints/templates/models.py | 37-39 | category, project_type, preferred_tool | Still in schema |
| api/middleware/security.py | 60, 147 | X-XSS-Protection header | Legacy, harmless |
| src/giljo_mcp/template_manager.py | 252 | Ollama references (12 instances) | Not yet removed |

### 1.2 Deprecated Fields Still in Models

- src/giljo_mcp/models/products.py:77 - Vision fields removed in 0128e
- src/giljo_mcp/models/products.py:279-341 - Migration helper properties for deprecated fields

---

## 2. TODO/FIXME/HACK Comments

### 2.1 False Positives (Feature Names, Not Tasks)
Most TODO matches are false positives - references to the TODO feature (AgentTodo model):
- agent_identity.py:321-365 - AgentTodo model class
- orchestration.py:884-886 - Documentation of TODO completion requirements
- orchestration_service.py:294-322 - Documentation text

### 2.2 Actual TODO Comments (Should Be GitHub Issues)

| File | Line | Comment | Recommendation |
|------|------|---------|----------------|
| api/endpoints/mcp_installer.py | 232 | TODO: Query from APIKey table if needed | Create GitHub issue |

### 2.3 XXXX Marker (Log Obfuscation)
- api/startup/core_services.py:97 - API key suffix obfuscation (intentional)

---

## 3. Legacy Wrapper Patterns

### 3.1 Backward Compatibility Layer - Agent Message Queue
**File**: src/giljo_mcp/agent_message_queue.py (Lines 345-747)

Complete compatibility layer for AgentCommunicationQueue with methods:
send_message(), send_messages(), get_messages(), get_unread_count(), acknowledge_all()

**Assessment**: Large compatibility layer (400+ lines). Evaluate if old API still used.

### 3.2 Logging Backward Compatibility
**File**: src/giljo_mcp/logging/__init__.py

- Line 155: get_colored_logger() - alias for get_logger()
- Lines 170-177: Auto-configure on import

**Assessment**: Low impact, can remain for convenience.

### 3.3 WebSocket Event Type Aliases
**File**: api/websocket.py (Lines 21-79)

Legacy underscore variants: product_update vs product:update
emit_legacy_aliases flag controls dual emission

**Assessment**: Evaluate frontend usage before removing.

### 3.4 Dependencies Module Re-export
**File**: api/dependencies/__init__.py (Lines 11-31)

Re-exports: get_tenant_key, get_db for backwards compatibility

### 3.5 Model Exports for Backward Compatibility
**File**: src/giljo_mcp/models/__init__.py

- Line 22: Backward compatibility maintained for 427 existing imports
- Line 150: Export all for backward compatibility

**Assessment**: Large-scale import pattern, keep for stability.

---

## 4. Commented-Out Code Blocks

### 4.1 Commented Imports
**File**: api/endpoints/setup.py:70-71

```python
# from sqlalchemy import select
# from src.giljo_mcp.models import User
```

**Assessment**: Dead code, safe to remove.

---

## 5. Backward-Compatibility Shims

### 5.1 Service Layer Session Wrappers
Pattern found in 5+ services with _test_session_wrapper():

- services/agent_job_manager.py:84-87
- services/message_service.py:94-97
- services/orchestration_service.py:478-481
- services/product_service.py:93-96
- services/project_service.py:98-101
- tools/tool_accessor.py:137-140

**Assessment**: Test infrastructure, not production code debt.

### 5.2 Legacy Mode Execution
**File**: src/giljo_mcp/tools/orchestration.py:279-342

_infer_execution_mode() returns claude-code or legacy

**Assessment**: Active feature for non-Claude Code clients.

### 5.3 Vision Document Backward Compatibility
**File**: src/giljo_mcp/tools/context_tools/get_vision_document.py:46-71

Mapping: moderate -> medium, heavy -> medium

**Assessment**: Can be removed after confirming no clients use old values.

### 5.4 Template Legacy Fallback
**File**: src/giljo_mcp/template_manager.py:619-649

Cache -> database cascade -> legacy fallback

**Assessment**: Required for database-less operation, keep.

### 5.5 Framing Helpers Legacy Format
**File**: src/giljo_mcp/tools/context_tools/framing_helpers.py:98-161

Supports legacy dict formats for priorities and fields

**Assessment**: User config migration needed before removal.

---

## 6. Method Stubs After Removal

### 6.1 trigger_succession() Stub
**File**: src/giljo_mcp/services/orchestration_service.py:2179-2190

REMOVED (Handover 0700d): Legacy Agent ID Swap succession removed.
Raises NotImplementedError with message to use simple_handover.py endpoint.

**Assessment**: Stub with clear error message, can be removed after 1-2 releases.

### 6.2 Serena MCP Placeholders
**File**: src/giljo_mcp/discovery.py:614-654

Three placeholder methods for Serena MCP integration (not implemented).

**Assessment**: Unimplemented features, either implement or remove.

### 6.3 Message Duplicate Detection Placeholder
**File**: src/giljo_mcp/agent_message_queue.py:857-859

Returns False as placeholder for future duplicate detection.

**Assessment**: Incomplete feature, evaluate need.

---

## 7. Security Concern - Placeholder API Key

### 7.1 Placeholder API Key in Production Code
**File**: api/endpoints/ai_tools.py:215-217

```python
api_key = "placeholder-api-key-please-use-wizard"
```

**Assessment**: HIGH PRIORITY - Should not exist in production code.
Either implement proper API key creation or remove endpoint.

---

## 8. Removed Features Documentation

Features with documented removal that may have residual code:

| Handover | Feature Removed | Location |
|----------|-----------------|----------|
| 0034 | Legacy password change endpoint | api/endpoints/auth.py:791 |
| 0035 | default_password_active field | api/auth_utils.py:89 |
| 0076 | assigned_to_user_id field | api/schemas/task.py:55,124 |
| 0371 | Duplicate /users endpoint | api/endpoints/auth.py:567 |
| 0388 | gil_activate, gil_launch, gil_handover slash commands | file_staging.py:126 |
| 0391 | gil_handover MCP tool | api/endpoints/mcp_http.py:705 |
| 0422 | update_context_usage and related methods | orchestration_service.py:2175-2177 |
| 0423 | TemplateAugmentation | api/endpoints/templates/crud.py:343 |
| 0450 | ProjectOrchestrator re-export | api/endpoints/orchestration.py:11 |
| 0503 | Duplicate vision upload endpoint | api/endpoints/agent_management.py:91 |
| 0700d | Agent ID Swap succession | orchestration_service.py:2183 |
| Dec 2025 | MCP task tools (list_tasks, update_task) | mcp_http.py:340,690 |
| Jan 2026 | Legacy agent-template installers | api/endpoints/downloads.py:737 |

---

## 9. Type Ignore Comments

**File**: src/giljo_mcp/tools/product.py

- Line 51: type: ignore[var-annotated]
- Line 52: type: ignore[unreachable]
- Line 162: type: ignore[var-annotated]
- Line 163: type: ignore[unreachable]

**Assessment**: Investigate if these can be properly typed.

---

## Recommendations by Priority

### High Priority (Immediate Action)
1. **Remove placeholder API key** in ai_tools.py:217 - Security risk
2. **Create GitHub issue** for TODO in mcp_installer.py:232

### Medium Priority (Next Cleanup Sprint)
1. **Remove commented imports** in setup.py:70-71
2. **Evaluate Serena MCP placeholders** - Implement or remove (discovery.py)
3. **Remove deprecated template fields** from API schemas after frontend audit
4. **Evaluate Agent Message Queue compatibility layer** usage

### Low Priority (Technical Debt Backlog)
1. **Ollama references removal** (12 instances noted in template_manager.py)
2. **Vision depth backward compat** values (moderate/heavy)
3. **Framing helpers legacy format** support
4. **WebSocket event type aliases** consolidation
5. **trigger_succession() stub** removal after transition period
6. **Type ignore comments** in product.py

---

## Appendix: Search Commands Used

```bash
# DEPRECATED/TODO/FIXME/HACK/XXX markers
grep -rn "DEPRECATED|TODO|FIXME|HACK|XXX" src/ api/ --include="*.py"

# Legacy/deprecated/backward references  
grep -rn "backward.compat|legacy|deprecated|obsolete" src/ api/ -i

# Alias/shim/wrapper patterns
grep -rn "alias|shim|wrapper|compat" src/ api/ -i

# Removed/deleted code references
grep -rn "REMOVED|DELETED|RETIRED|no longer|not used|unused" src/ api/ -i

# Stub/placeholder patterns
grep -rn "stub|placeholder|not.implemented|pass$" src/ api/ -i
```

---

*Generated by Deep Researcher Agent - Code Health Audit 0725*
