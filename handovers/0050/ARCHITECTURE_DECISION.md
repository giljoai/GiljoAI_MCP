# Architecture Decision: Single Active Product

**Date**: 2025-10-27
**Decision Owner**: System Architect
**Status**: Approved

## Context

The GiljoAI MCP Server orchestrates AI agents using mission-based architecture where agents operate on a focused product context. The current implementation allows products to be marked active but lacks enforcement of mutual exclusivity. This decision addresses how many products can be active simultaneously per tenant.

## Decision Context

### Current System Behavior

1. **Database Schema**: `products.is_active` BOOLEAN field exists
2. **No Constraint**: Database allows multiple products with `is_active=True` per tenant
3. **UI Behavior**: Product activation toggle works but no warnings
4. **API Behavior**: `POST /products/{id}/activate` sets one product active but doesn't clear others
5. **Orchestration**: Mission planner expects single product context

### Problem Triggers

This architectural decision became necessary due to:
- Field Priority Configuration (Handover 0048) assumes single product context
- Active Product Token Visualization (Handover 0049) displays one product in top bar
- Mission generation uses 2000 token budget per product (not shared)
- MCP tools designed for focused context delivery
- User testing revealed confusion about "which product am I working on?"

## Options Considered

### Option A: Single Active Product + Single Active Project (SELECTED)

**Architecture**:
- Only ONE product active per tenant at any time
- Only ONE project active per product at any time
- Activating a product deactivates all others
- Activating a project requires parent product to be active

**Enforcement**:
- Backend validation in activation endpoints
- Frontend warning dialogs before state change
- UI controls disabled when preconditions not met

**User Experience**:
```
User activates Product B
  → Warning: "This will deactivate Product A (which has 2 active projects)"
  → User confirms
  → Product A deactivated, Product B activated
  → Top bar updates to "Active: Product B"
```

**Pros**:
- ✅ Clean mental model (one focus at a time)
- ✅ Aligns with mission-based orchestration design
- ✅ Simple implementation (validation + warnings)
- ✅ No database schema changes needed
- ✅ Prevents token budget confusion
- ✅ MCP tools receive consistent context

**Cons**:
- ❌ User must manually switch between products
- ❌ Can't compare two products side-by-side in agent context
- ❌ Switching products deactivates current projects

**Complexity**: LOW
**Implementation Time**: 2-3 days
**Risk**: LOW (additive changes only)

---

### Option B: Multiple Active Products + Priority System

**Architecture**:
- Multiple products can be active simultaneously
- Each product has a priority level (1-10)
- Highest priority product is "primary" for orchestration
- Mission planner uses primary product context
- Token budget shared across all active products

**Enforcement**:
- Database adds `priority` column to products
- UI shows priority badges on active products
- Mission planner selects primary by priority

**User Experience**:
```
User has Products A (priority 5), B (priority 3) active
  → Orchestrator uses Product A context
  → User can promote Product B to priority 6
  → Orchestrator switches to Product B context
```

**Pros**:
- ✅ Flexible product management
- ✅ Can monitor multiple products
- ✅ Quick switching via priority change

**Cons**:
- ❌ Confusing mental model (which is "really" active?)
- ❌ Token budget sharing requires complex allocation logic
- ❌ MCP tools must handle multi-product context
- ❌ Field priority config unclear (which product's settings?)
- ❌ Requires database migration (priority column)
- ❌ UI complexity (priority management interface)

**Complexity**: HIGH
**Implementation Time**: 2-3 weeks
**Risk**: MEDIUM (requires refactoring mission planner, token budget logic)

---

### Option C: Product Workspaces (Multi-Context)

**Architecture**:
- Each product is a separate "workspace"
- User explicitly switches workspace (like IDE tabs)
- All orchestration scoped to current workspace
- No "active" flag - workspace selection is transient state
- Session state tracks current workspace

**Enforcement**:
- Frontend stores current workspace in Pinia
- Backend validates workspace_id in all requests
- No database changes (workspace is UI concept)

**User Experience**:
```
User opens Product A workspace
  → All views (projects, agents, missions) scoped to Product A
  → Top bar shows "Workspace: Product A"
  → User switches to Product B workspace
  → All views refresh to show Product B data
```

**Pros**:
- ✅ Natural isolation between products
- ✅ No database changes needed
- ✅ Aligns with modern IDE patterns
- ✅ Clean separation of concerns

**Cons**:
- ❌ Requires significant UI refactoring (workspace context everywhere)
- ❌ Session state management complexity
- ❌ Existing `is_active` flag becomes unused
- ❌ All views need workspace-aware filtering
- ❌ URL routing needs workspace parameter
- ❌ WebSocket events need workspace scoping

**Complexity**: VERY HIGH
**Implementation Time**: 4-6 weeks
**Risk**: HIGH (major refactoring, potential for breaking changes)

---

## Comparison Matrix

| Criteria | Option A (Single Active) | Option B (Priority) | Option C (Workspaces) |
|----------|--------------------------|---------------------|-----------------------|
| **Implementation Complexity** | LOW | HIGH | VERY HIGH |
| **User Mental Model** | Simple | Moderate | Simple |
| **Development Time** | 2-3 days | 2-3 weeks | 4-6 weeks |
| **Breaking Changes** | None | Medium | High |
| **Database Migration** | None | Required | None |
| **Code Changes** | Localized | Widespread | Architecture-wide |
| **Testing Effort** | LOW | HIGH | VERY HIGH |
| **Risk** | LOW | MEDIUM | HIGH |
| **Aligns with 70% Token Reduction** | ✅ YES | ❌ NO | ✅ YES |
| **MCP Tool Simplicity** | ✅ YES | ❌ NO | ✅ YES |
| **Production Ready** | 2-3 days | 3-4 weeks | 6-8 weeks |

## Selected Option: A (Single Active Product)

**Decision**: Implement single active product architecture with validation and warnings.

## Rationale

### 1. Architecture Alignment

The mission-based orchestration architecture is fundamentally designed for focused context:
- **MissionPlanner** generates missions from ONE product's vision + config
- **AgentSelector** chooses agents based on ONE product's requirements
- **WorkflowEngine** coordinates agents working on ONE product's tasks
- **Token Budget** (2000 tokens) is product-specific, not shared

**Verdict**: Multi-product active state contradicts core architecture.

### 2. Token Efficiency

The 70% token reduction was achieved through:
- Condensed mission generation (single product focus)
- Field priority configuration (per-product settings)
- Targeted context delivery (one product's vision chunks)

**Verdict**: Multiple active products dilutes token efficiency.

### 3. MCP Server Design

MCP tools are designed for single product context:
- `get_active_product()` returns ONE product
- `get_product_context()` builds context for ONE product
- Agent jobs reference ONE product_id
- Mission templates assume ONE product's config_data

**Verdict**: MCP tools not designed for multi-product context.

### 4. User Mental Model

User interviews and testing revealed:
- Users think in terms of "what am I working on right now?" (singular)
- Multiple active products created confusion: "Which one is really active?"
- Switching products is rare (typically once per day/session)
- Clear focus improves productivity

**Verdict**: Single active product matches user expectations.

### 5. Implementation Simplicity

Option A requires:
- 4 validation checks in backend (activate product, activate project, create job, delete product)
- 1 warning dialog in frontend
- 1 disabled state for project activation button
- No database changes, no migrations, no refactoring

**Verdict**: Lowest risk, fastest delivery, immediate value.

## Trade-offs Acknowledged

### What We Gain
- ✅ Clear focus and mental model
- ✅ Architecture consistency
- ✅ Token efficiency maintained
- ✅ Simple implementation (2-3 days)
- ✅ No breaking changes
- ✅ Prevents data integrity issues

### What We Give Up
- ❌ Cannot have multiple products active simultaneously
- ❌ Switching products requires explicit user action
- ❌ Cannot compare two products in real-time agent context

### Mitigation Strategies

For users who need to work on multiple products:
1. **Quick Switch**: Add keyboard shortcut for product switching (future enhancement)
2. **Recent Products**: Show recently active products in dropdown (future enhancement)
3. **Product Tabs**: Implement workspace tabs if demand grows (Option C, future)

**Verdict**: Trade-offs are acceptable given architecture benefits and user needs.

## Future Considerations

### When to Revisit This Decision

Consider Option C (Workspaces) if:
- 50%+ of users request multi-product workflows
- Mission architecture evolves to support multi-product context
- Token budgets can be safely shared across products
- MCP tools are redesigned for workspace isolation

### Evolution Path

1. **Phase 1 (Now)**: Single active product (Option A)
2. **Phase 2 (3-6 months)**: Quick switch enhancements
3. **Phase 3 (6-12 months)**: Evaluate workspace demand
4. **Phase 4 (12+ months)**: Consider workspace architecture if needed

## Decision Record

**Decided By**: System Architect
**Approved By**: Product Owner
**Date**: 2025-10-27
**Review Date**: 2026-04-27 (6 months)

**Recorded in**:
- This document (handovers/0050/ARCHITECTURE_DECISION.md)
- TECHNICAL_ARCHITECTURE.md (to be updated)
- CLAUDE.md (to be updated)

---

**End of Architecture Decision**
