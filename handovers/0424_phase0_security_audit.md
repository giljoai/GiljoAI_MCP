# Phase 0: Tenant Key Security Audit

**Auditor**: Deep Researcher Agent  
**Date**: 2026-01-20  
**Scope**: Comprehensive tenant_key security audit across GiljoAI MCP codebase  
**Classification**: Security - Internal Only

---

## Executive Summary

The GiljoAI MCP codebase demonstrates strong tenant isolation at the authentication and WebSocket layers, but contains several vulnerabilities in internal service functions that rely on optional tenant_key parameters with backward-compatible fallbacks. The most critical finding is the client-provided tenant_key pattern in MCP tools - while mitigated by session-based authentication, the current architecture trusts client-supplied tenant_key values without server-side enforcement.

Overall Risk Level: MEDIUM (3 HIGH, 2 MEDIUM, 4 LOW findings)

---

## Risk Matrix

| Area | Risk Level | Finding Count | Critical Issues |
|------|------------|---------------|-----------------|
| MCP Tools | HIGH | 3 | Client-provided tenant_key, no validation against session |
| Database Queries | HIGH | 2 | Missing tenant_key filtering in fallback paths |
| Discovery Service | HIGH | 1 | No tenant_key filtering in config lookups |
| Prompt Generators | MEDIUM | 1 | Tenant_key embedded in prompts (shareable) |
| Export/Import | LOW | 0 | Properly isolated via authentication |
| WebSocket | LOW | 0 | Strong tenant isolation enforced |
| 360 Memory | LOW | 0 | Dual tenant_key filtering |
| Slash Commands | LOW | 0 | API-authenticated only |
| Agent Templates | LOW | 0 | Tenant-scoped via authentication |

---

## Detailed Findings

### 1. MCP Tools - Client-Provided tenant_key (HIGH)

Location: api/endpoints/mcp_http.py (lines 580-682)

Issue: MCP tools receive tenant_key as a client parameter and pass it directly to tool functions without validating against the session authenticated tenant_key.

Vulnerability: A malicious client could authenticate with their own API key, then call tools with a different tenant_key in arguments, potentially accessing cross-tenant data.

Mitigating Factors:
- Line 606 sets state.tenant_manager.set_current_tenant(session.tenant_key) from session
- Most tool implementations use db_manager.get_tenant_session_async(tenant_key) which may filter
- Session tenant_key is derived from API key authentication (secure)

Recommendation: Implement server-side tenant_key enforcement - validate client tenant_key against session.tenant_key before tool execution.

### 2. Database Queries - Optional tenant_key Fallback (HIGH)

Location: src/giljo_mcp/services/project_service.py (lines 204-210, 479-483)

Issue: Backward-compatible fallback allows queries without tenant_key filtering. Comment indicates will be deprecated but code still active.

Attack Vector: Internal callers that omit tenant_key bypass isolation.

Recommendation: Remove fallback, make tenant_key mandatory for all queries.

### 3. Discovery Service - Missing tenant_key Filtering (HIGH)

Location: src/giljo_mcp/discovery.py (lines 383-391)

Issue: Config discovery queries projects and products without tenant_key filtering.

Risk: If project_id is guessable (UUID), any agent could potentially access another tenant product configuration.

Recommendation: Add tenant_key parameter and filtering to all discovery queries.

### 4. Prompt Generators - Embedded tenant_key (MEDIUM)

Location: src/giljo_mcp/tools/orchestration.py (multiple locations)

Issue: Tenant_key is embedded in generated prompts that could be copied/shared.

Exposure Points:
- Line 610: tenant_key in get_orchestrator_instructions example
- Line 620: get_available_agents example
- Lines 644-667: spawn_agent_job, update_agent_mission, send_message examples
- Lines 878-897: write_360_memory, complete_job examples

Risk Level: Medium - tenant_key alone does not grant access (requires API key authentication), but represents information disclosure.

### 5-9. SECURE Areas (LOW)

- WebSocket Broadcasts: Strong tenant validation at lines 154-156, subscription authorization at lines 251-261
- Export/Download: Token-based downloads use tenant_key from authenticated token, path validation prevents traversal
- 360 Memory: Dual tenant_key filtering (query WHERE + explicit check)
- Slash Commands: All endpoints require authentication, tenant_key derived from session
- Agent Templates: Template seeding uses authenticated user tenant_key, no hardcoded values

---

## Recommendations Summary (Prioritized)

### Priority 1 - Critical (Fix Immediately)

1. MCP Tool tenant_key Validation
   - File: api/endpoints/mcp_http.py
   - Action: Validate client-provided tenant_key against session.tenant_key
   - Effort: 1-2 hours

2. Remove Optional tenant_key Fallbacks
   - File: src/giljo_mcp/services/project_service.py
   - Action: Make tenant_key mandatory, remove backward compatibility paths
   - Effort: 2-3 hours

3. Discovery Service tenant_key Filtering
   - File: src/giljo_mcp/discovery.py
   - Action: Add tenant_key parameter and WHERE clause filtering
   - Effort: 1-2 hours

### Priority 2 - Important (Fix This Sprint)

4. Review All Prompt Generators
   - Files: src/giljo_mcp/tools/orchestration.py
   - Action: Audit for sensitive data exposure
   - Effort: 3-4 hours

### Priority 3 - Maintenance (Schedule)

5. Comprehensive Query Audit
   - Scope: All select() queries in services and repositories
   - Effort: 8-12 hours

---

## Updated Phase 0 Scope

Immediate Fixes (Security-Critical):
1. MCP tenant_key validation middleware
2. Remove optional tenant_key fallbacks in project_service.py
3. Add tenant_key filtering to discovery.py

Documentation Updates:
1. Document tenant_key enforcement requirements
2. Add security checklist to PR template
3. Update CLAUDE.md with tenant isolation patterns

Testing Requirements:
1. Add cross-tenant access tests for MCP tools
2. Add negative tests for missing tenant_key scenarios
3. Verify WebSocket isolation in E2E tests

---

End of Security Audit Report