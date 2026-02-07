# Architecture Consistency Audit - Findings Report

**Handover**: 0725
**Date**: 2026-02-07
**Type**: Research / Audit (NO CHANGES MADE)
**Auditor**: Deep Researcher Agent

---

## Executive Summary

This audit examined the GiljoAI MCP codebase for API and architecture consistency across 5 key areas: response format consistency, service layer returns, repository statelessness, multi-tenant isolation, and error handling patterns. The codebase shows STRONG overall architecture with proper patterns in place, but several inconsistencies were identified that represent technical debt and potential security risks.

**Key Findings**:
- **120+ instances** of services returning dicts instead of objects/Pydantic models
- **5 services** with missing or inconsistent tenant_key filtering (SECURITY RISK)
- **2 endpoint files** with inconsistent error response patterns
- Repositories are properly stateless (GOOD)
- Pydantic validation is widely used in endpoints (GOOD)

---

## 1. Services Returning Dicts Instead of Objects

**Status**: INCONSISTENT - Technical Debt
**Severity**: Medium
**Count**: 120+ instances across 15 service files

Services should return domain objects or Pydantic models, not raw dicts.

### Affected Services (by severity):

#### OrgService (org_service.py) - 33 instances
MOST AFFECTED - Nearly every method uses dict returns:
Lines 63, 85, 90, 108, 110, 114, 125, 127, 131, 159, 175, 180, 206, 210, 229, 234, 242, 245, 252, 257, 265, 268, 271, 278, 283, 291, 296, 306, 311, 325, 329, 348, 352

#### ProjectService (project_service.py) - 28 instances
Lines 171, 258, 347, 516, 681, 732, 821, 921, 1060, 1199, 1279, 1360, 1477, 1587, 1622, 1693, 1736, 1833, 1958, 2043, 2087, 2143, 2368, 2489, 2522, 2549, 2573, 2631, 2655

#### ProductService (product_service.py) - 18 instances
Lines 217, 312, 393, 466, 569, 656, 714, 772, 831, 905, 949, 954, 1015, 1086, 1202, 1376, 1559, 1681, 1740, 1766

#### TaskService (task_service.py) - 10 instances
Lines 196, 304, 359, 431, 558, 634, 808, 901, 997

#### OrchestrationService (orchestration_service.py) - 15 instances
Lines 597, 875, 994, 1147, 1249, 1332, 1340, 1648, 1993, 2162, 2626, 3034, 3165, 3228

#### MessageService (message_service.py) - 8 instances
Lines 687, 896, 1012, 1038, 1078, 1148, 1260

#### UserService (user_service.py) - 16 instances
Lines 155, 206, 317, 411, 467, 548, 618, 671, 715, 753, 797, 845, 850, 924, 971, 1021, 1088, 1119, 1183

#### AuthService (auth_service.py) - 5 instances
Lines 172, 269, 414, 615, 867

#### TemplateService (template_service.py) - 4 instances
Lines 125, 196, 293, 392

#### Other Services with Dict Returns:
ConsolidatedVisionService: Lines 55, 65, 76, 107
VisionSummarizer: Lines 106, 119, 158, 284
ClaudeConfigManager: Lines 87, 135, 148, 154, 181
SettingsService: Line 59
ContextService: Lines 80, 106, 130, 155
ConfigService: Lines 68, 75, 78
AgentJobManager: Lines 177, 265, 322, 387

---

## 2. Missing Tenant Key Filtering (SECURITY RISK)

**Status**: CRITICAL - Security Vulnerability
**Severity**: HIGH

Several database queries lack tenant_key filtering.

### Affected Queries:

#### AuthService (auth_service.py)
Line 127: select(User).where(User.username == username) - NO tenant filter
Line 206: select(User).where(User.id == user_id) - NO tenant filter
Line 547: select(User).where(User.username == username) - NO tenant filter
Line 556: select(User).where(User.email == email) - NO tenant filter
Line 657: select(User).where(User.id == admin_user_id) - NO tenant filter

Note: AuthService may be intentionally cross-tenant for authentication.

#### ConsolidationService (consolidation_service.py)
Line 49: select(Product).where(Product.id == product_id) - NO tenant filter (mitigated at line 58)

#### MessageService (message_service.py)
Line 153, 512, 665, 1016, 1113 - Various missing tenant filters

#### OrchestrationService (orchestration_service.py)
Lines 1318, 1516, 1602, 1960 - NO tenant filter on AgentJob/AgentTodoItem queries

#### TaskService (task_service.py)
Lines 149, 396, 614, 729, 792 - Missing tenant filters

#### TemplateService (template_service.py)
Lines 478, 943 - NO tenant filter

#### ProjectService (project_service.py)
Lines 507, 2126 - Fallback paths lack tenant

#### AgentJobManager (agent_job_manager.py)
Line 374 - NO tenant filter

---

## 3. Repository Layer Statelessness

**Status**: GOOD - Properly Stateless
**Severity**: None

All repositories are properly stateless.

---

## 4. Pydantic Validation in Endpoints

**Status**: GOOD - Widely Used
**Severity**: None

150+ BaseModel subclasses defined across 40+ endpoint files.

---

## 5. Error Handling Patterns

**Status**: MIXED - Some Inconsistency
**Severity**: Low

Direct dict error returns found in:
configuration.py: Lines 573, 584, 587
database_setup.py: Lines 113, 118

---

## Summary of Findings

| Area | Status | Risk | Priority |
|------|--------|------|----------|
| Services returning dicts | INCONSISTENT | Medium | P2 |
| Missing tenant isolation | CRITICAL | HIGH | P0 |
| Repository statelessness | GOOD | None | - |
| Pydantic validation | GOOD | None | - |
| Error handling patterns | MIXED | Low | P3 |

---

## Recommended Actions

### P0 - Critical (Security)
1. Audit and fix all queries missing tenant_key filtering
2. Add automated tests for tenant isolation
3. Consider query interceptor for automatic tenant filtering

### P2 - Medium (Technical Debt)
1. Create Pydantic response models for service layer
2. Migrate OrgService first (highest impact)
3. Establish service layer return type guidelines

### P3 - Low (Consistency)
1. Replace dict error returns in configuration.py and database_setup.py
2. Remove HTTPException usage from ProductService (move to endpoint layer)
3. Standardize on exception-based error handling in services

---

**Report Generated**: 2026-02-07
**No code changes made - research only**
