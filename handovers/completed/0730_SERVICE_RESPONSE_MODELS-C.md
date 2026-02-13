# Handover 0730: Service Layer Response Models

**Series:** 0700 Code Cleanup (Post-Audit Follow-Up)
**Priority:** P2 - MEDIUM
**Estimated Effort:** 24-32 hours
**Prerequisites:** Handover 0725b Complete, 0727 Complete
**Status:** READY
**Depends On:** 0480 series

MISSION: Migrate 122 dict wrapper patterns to Pydantic models with exception-based error handling

WHY THIS MATTERS:
- Architectural consistency with FastAPI best practices
- Type safety via Pydantic models
- Clear separation of happy path and error path
- Proper HTTP status codes from exception types
- Improved maintainability and testability

VALIDATION SOURCE: AST-based audit in 0725b with under 5 percent false positive rate

---

## Affected Services By Impact

TIER 1 (Start Here) - 69 instances (57 percent):
- OrgService (services/org_service.py): 33 instances
- UserService (services/user_service.py): 19 instances  
- ProductService (services/product_service.py): 17 instances

TIER 2 - 31 instances (26 percent):
- TaskService (services/task_service.py): 14 instances
- ProjectService (services/project_service.py): 9 instances
- MessageService (services/message_service.py): 8 instances

TIER 3 - 22 instances (18 percent):
- OrchestrationService: 6 instances
- ContextService: 4 instances
- ConsolidationService: 4 instances
- AgentJobManager: 4 instances
- VisionSummarizer: 4 instances
- TemplateService: 4 instances

GRAND TOTAL: 122 instances across 12 services

---

## Implementation Plan

PHASE 1: Design Response Models (4-6 hours)
Sub-Agent: system-architect

Deliverables:
1. Response Model Audit (docs/architecture/service_response_models.md)
2. Exception Mapping Strategy (docs/architecture/exception_mapping.md)
3. API Layer Updates (docs/architecture/api_exception_handling.md)

Success Criteria:
- All 122 instances mapped to target exceptions
- Pydantic models designed for each service
- Exception handling strategy documented
- Clear migration path for each service


PHASE 2: Refactor Services by Tier (16-24 hours)
Sub-Agent: tdd-implementor

CRITICAL TDD APPROACH:
1. Update tests FIRST to expect new return types and exceptions
2. Run tests to confirm failures
3. Update service implementation
4. Run tests to confirm fixes

Sub-Phase 2a: Tier 1 Services (8-12 hours)
- OrgService (33), UserService (19), ProductService (17)
- Process: Update tests -> Update service -> Run tests and fix

Sub-Phase 2b: Tier 2 Services (4-6 hours)
- TaskService (14), ProjectService (9), MessageService (8)
- Follow same TDD process

Sub-Phase 2c: Tier 3 Services (4-6 hours)
- All remaining services (6 services, 22 total instances)
- Follow same TDD process

PHASE 3: Update API Endpoints (2-4 hours)
Sub-Agent: backend-integration-tester

Process:
1. Identify affected endpoints (grep for result success checks)
2. Remove dict checking logic
3. Verify exception handlers exist
4. Run integration tests

PHASE 4: Testing and Validation (2-4 hours)
Sub-Agent: backend-integration-tester

Process:
1. Service layer tests (pytest tests/services/)
2. API integration tests (pytest tests/api/)
3. Manual testing via dashboard
4. Validation audit (grep for remaining dict wrappers)

Success Criteria:
- Zero dict wrapper patterns remaining
- 100 percent service tests passing
- 100 percent API tests passing
- Over 80 percent test coverage maintained
- No regressions


---

## Success Criteria Overall

CODE QUALITY:
- Zero return success/error dict patterns in services
- All service methods return Pydantic models or domain objects
- All service methods document raised exceptions in docstrings
- Type hints added to all service method signatures

TESTING:
- All service unit tests passing (122 methods updated)
- All API integration tests passing
- Test coverage over 80 percent maintained
- Exception scenarios covered in tests

ARCHITECTURE:
- Consistent exception-based error handling across all services
- HTTP status codes properly mapped (404, 409, 422, 403, 500)
- API endpoints simplified (no dict checking logic)
- Exception handlers complete for all service exceptions

DOCUMENTATION:
- Service response models documented
- Exception mapping documented
- SERVICES.md updated to remove dict wrapper examples

---

## Risks and Considerations

BREAKING CHANGES:
Risk: API consumers may depend on dict response format
Mitigation: All API endpoints already return Pydantic models

TRANSACTION MANAGEMENT:
Risk: Exception-based flow may bypass rollback logic
Mitigation: FastAPI dependency injection handles session lifecycle

TEST ISOLATION:
Risk: Existing tests may have transaction isolation issues
Reference: Known issue from SERVICES.md (Handover 0322)

BACKWARD COMPATIBILITY:
Risk: Old code may still expect dict wrappers
Mitigation: Audit entire codebase before starting


---

## Reference Materials

RELATED HANDOVERS:
- 0480 Series: Exception handling remediation (establishes exception hierarchy)
- 0725b: Code health re-audit (validates 122 instances via AST analysis)
- 0322: Service layer architecture patterns
- 0500-0515: Remediation series

DOCUMENTATION:
- SERVICES.md: Service layer patterns
- SERVER_ARCHITECTURE_TECH_STACK.md: Overall architecture
- TESTING.md: Testing patterns and coverage

CODE REFERENCES:
- src/giljo_mcp/exceptions.py: Exception hierarchy (BaseGiljoError and subclasses)
- api/exception_handlers.py: HTTP exception mapping (from 0480 series)
- tests/services/: Service unit test patterns
- tests/api/: Endpoint integration test patterns

---

## Recommended Sub-Agents

Phase 1 Design (4-6 hours): system-architect
- Architectural decisions, exception mapping, API design review

Phase 2 Refactoring (16-24 hours): tdd-implementor
- Test-driven development, systematic refactoring, regression prevention

Phase 3 API Updates (2-4 hours): backend-integration-tester
- Endpoint testing, HTTP status code validation, integration expertise

Phase 4 Validation (2-4 hours): backend-integration-tester
- Comprehensive testing, coverage analysis, manual validation

---

## Definition of Done

1. Code Changes Complete - All 122 dict wrapper instances replaced
2. Tests Passing - All service and API tests passing with over 80 percent coverage
3. Documentation Updated - Service response models and exception mapping documented
4. Validation Complete - Manual testing successful, error messages consistent
5. Handover Complete - All phases executed and verified

---

## Timeline Estimate

Phase 1 Design: 4-6 hours (system-architect)
Phase 2a Tier 1: 8-12 hours (tdd-implementor)
Phase 2b Tier 2: 4-6 hours (tdd-implementor)
Phase 2c Tier 3: 4-6 hours (tdd-implementor)
Phase 3 API: 2-4 hours (backend-integration-tester)
Phase 4 Validation: 2-4 hours (backend-integration-tester)

TOTAL: 24-38 hours
RECOMMENDED: 3-5 days with sub-agent handoffs

---

**Created:** 2026-02-07
**Status:** READY (Awaiting 0727 completion)
**Priority:** P2 - MEDIUM (Architectural debt, not blocking)
**Next Steps:** Execute Phase 1 design with system-architect agent

---

## Notes for Executor

1. Start Small - Begin with OrgService (33 instances) as reference
2. Test First - TDD approach is non-negotiable
3. Commit Frequently - One commit per service for easier rollback
4. Document Decisions - Capture exception mapping rationale
5. Ask Questions - Consult system-architect if unclear
6. Preserve Coverage - Run coverage after each service
7. Integration Test - Test full workflows after each tier

This refactor will significantly improve code quality and maintainability.
