# Handover 0480c: Service Migration - Core Services (REVISED)

**Date:** 2026-01-27
**From Agent:** Orchestrator
**To Agent:** TDD Implementor
**Priority:** HIGH
**Estimated Complexity:** 8-10 hours
**Status:** Ready for Implementation
**Series:** 0480 (Exception Handling Remediation - REVISED)
**Prerequisite:** 0480a must be complete (can run parallel with 0480b)

---

## Executive Summary

### What
Migrate `project_service.py`, `orchestration_service.py`, and `template_service.py` from dict returns to raising exceptions.

---

## Tasks

### Task 1: Migrate project_service.py

**File:** `src/giljo_mcp/services/project_service.py`

**Mapping:**

| Error Message | Exception to Raise |
|--------------|-------------------|
| "Project not found" | `ResourceNotFoundError` |
| "Project already exists" | `ValidationError` |
| Invalid status transitions | `ProjectStateError` |

### Task 2: Migrate orchestration_service.py

**File:** `src/giljo_mcp/services/orchestration_service.py`

Use existing orchestration exceptions from `exceptions.py`:
- `OrchestrationError`
- `AgentCreationError`
- `ProjectStateError`
- `HandoffError`

### Task 3: Migrate template_service.py

**File:** `src/giljo_mcp/services/template_service.py`

Use existing template exceptions:
- `TemplateNotFoundError`
- `TemplateValidationError`
- `TemplateRenderError`

### Task 4: Update Return Types and Write Tests

Same pattern as 0480b.

---

## Success Criteria

- [ ] Zero `{"success": False` patterns in all three services
- [ ] Return types updated
- [ ] Tests verify exception raising

---

## Reference

- Exceptions: `src/giljo_mcp/exceptions.py`
- Master handover: `handovers/0480_exception_handling_remediation_REVISED.md`
