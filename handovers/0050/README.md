# Handover 0050: Single Active Product Architecture

**Date**: 2025-10-27
**Status**: Ready for Implementation
**Priority**: High
**Estimated Duration**: 2-3 days
**Complexity**: LOW
**Risk**: LOW

## Executive Summary

The GiljoAI MCP Server currently allows products to be activated but lacks enforcement that only ONE product can be active per tenant at any time. This handover implements architectural safeguards to ensure a single active product per tenant, with proper warnings, validations, and UI controls. This prevents risks in MCP communication, agent coordination, and token budget management.

**Key Principle**: Mission-based orchestration operates on a single product context. Multiple active products would dilute the 70% token reduction achieved through focused context delivery.

## Problem Statement

### Current State

The system allows any product to be activated through the UI or API:
- No validation prevents multiple products from being marked `is_active=True`
- Users can accidentally activate multiple products
- No warning when activating a new product that would deactivate another
- Project activation doesn't validate parent product is active
- Agent jobs don't verify product is active before mission assignment

### Risks Without This Implementation

1. **Broken MCP Communication**: Tools designed for single product context receive mixed signals
2. **Token Budget Confusion**: 2000 token budget is product-specific, not shared across products
3. **Mission Integrity**: Agents could receive missions referencing wrong product's vision/config
4. **User Mental Model**: Unclear which product's context is "active" for orchestration
5. **Data Integrity**: Database allows multiple `is_active=True` products per tenant

## Architectural Decision

**Selected Approach**: Single Active Product + Single Active Project

- Only ONE product can be active per tenant at any time
- Only ONE project can be active per product at any time
- Activating a new product deactivates the current one
- Projects can only be activated if their parent product is active

**Rationale**: See [ARCHITECTURE_DECISION.md](ARCHITECTURE_DECISION.md) for full analysis.

## Success Criteria

### Functional Requirements
- [ ] Only one product can be active per tenant (enforced in backend)
- [ ] Activating a product shows warning if another is active
- [ ] Warning dialog lists active product's active projects
- [ ] Deactivating current product clears top bar active product indicator
- [ ] Deleting active product clears active state
- [ ] Project activation validates parent product is active
- [ ] Project activation button disabled if product not active
- [ ] Agent jobs validate product is active before creation

### User Experience Requirements
- [ ] Warning dialog shows clear before/after state
- [ ] Activation change refreshes top bar immediately
- [ ] Project activation tooltip explains why button is disabled
- [ ] Delete product refreshes store state immediately

### Technical Requirements
- [ ] Multi-tenant isolation maintained
- [ ] All validations async-safe
- [ ] No breaking changes to existing API contracts
- [ ] WebSocket events fire on state changes (reuse existing)

## Implementation Scope

### What's Included

**Phase 1**: Backend product activation rules
**Phase 2**: Frontend activation warnings
**Phase 3**: Project validation rules
**Phase 4**: Agent job safety checks
**Phase 5**: Testing and documentation

**Estimated LOC**: ~300 lines (backend: 150, frontend: 150)

### What's NOT Included

- Database schema changes (current schema already supports single active product)
- Alembic migrations (no schema changes needed)
- New WebSocket events (reuse existing `product:activated` event)
- UI bug fixes for active product indicator (separate work)
- Product configuration changes

## Related Handovers

- **Handover 0048**: Product Field Priority Configuration (COMPLETE)
  - Establishes field priority system this handover protects
  - Single active product ensures correct token budget application

- **Handover 0049**: Active Product Token Visualization (COMPLETE)
  - Top bar active product indicator (this handover ensures only one can be active)
  - Token visualization tied to active product

- **Handover 0051**: Multi-Product Management Enhancements (FUTURE)
  - May introduce "quick switch" between products
  - Builds on single active product architecture

## Dependencies

**Required Before Starting**:
- Handover 0049 complete (top bar active product indicator exists)
- Product activation endpoint exists (`POST /api/v1/products/{product_id}/activate`)
- Project activation logic exists

**Blocks Future Work**:
- Agent mission generation (needs stable active product context)
- Multi-agent orchestration (needs clear product scope)

## Documentation Updates Required

1. **User Guide**: Add section on active product concept and switching
2. **CLAUDE.md**: Update with single active product architecture
3. **API Documentation**: Document activation behavior and warnings
4. **TECHNICAL_ARCHITECTURE.md**: Add single active product principle

## Implementation Details

See:
- [ARCHITECTURE_DECISION.md](ARCHITECTURE_DECISION.md) - Full decision rationale
- [IMPLEMENTATION_PLAN.md](IMPLEMENTATION_PLAN.md) - Phase-by-phase guide
- [TESTING.md](TESTING.md) - Test scenarios and acceptance criteria
- [FILES_TO_MODIFY.md](FILES_TO_MODIFY.md) - Exact file changes needed
- [API_CHANGES.md](API_CHANGES.md) - Endpoint behavior changes

## Timeline Estimate

**Day 1**: Phase 1 (Backend) + Phase 2 (Frontend warning dialog)
**Day 2**: Phase 3 (Project validation) + Phase 4 (Agent job safety)
**Day 3**: Phase 5 (Testing) + Documentation + Close handover

**Total**: 2-3 days for experienced developer

## Sign-Off Checklist

Before marking this handover complete:
- [ ] All 5 phases implemented
- [ ] All test scenarios pass (see TESTING.md)
- [ ] Code committed with descriptive messages
- [ ] Documentation updated (User Guide, CLAUDE.md, API docs)
- [ ] Handover moved to `handovers/completed/` with `-C` suffix
- [ ] Completion summary created

---

**Next Steps**: Review [ARCHITECTURE_DECISION.md](ARCHITECTURE_DECISION.md) to understand the decision rationale, then proceed to [IMPLEMENTATION_PLAN.md](IMPLEMENTATION_PLAN.md) for step-by-step implementation guide.

---

**End of README**
