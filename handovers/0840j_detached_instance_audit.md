# Handover 0840j: Detached Instance Audit & Fix

**Date:** 2026-03-26
**From Agent:** Orchestrator (Live Testing Session)
**To Agent:** Next Session (backend-tester + tdd-implementor)
**Priority:** Critical
**Estimated Complexity:** 2-3 hours
**Status:** Not Started
**Edition Scope:** CE

---

## Task Summary

The 0840 JSONB normalization added relationship attributes (tech_stack, architecture, test_config) to Product, and junction table relationships (recipients, acknowledgments, completions) to Message. Any code path that does `session.refresh(obj)` without `attribute_names` or accesses these relationships after a session closes will crash with `DetachedInstanceError`.

Scan the ENTIRE codebase for:

1. **Every `session.refresh(` call** — verify it includes `attribute_names` for all relationship attributes on the model being refreshed
2. **Every endpoint that accesses `product.tech_stack`, `product.architecture`, `product.test_config`, `product.vision_documents`** — verify the product was loaded with eager loading (selectinload/joinedload) or the access happens within an active session
3. **Every endpoint that accesses `message.recipients`, `message.acknowledgments`, `message.completions`** — same check
4. **Every `_build_product_response()` caller** — verify the product passed in has relationships loaded
5. **Every place where an ORM object is returned from a service method and then accessed in an endpoint** — check if the session is still active when the endpoint reads relationships
6. **Check for `metadata` keyword arg** — any remaining callers using the old `metadata=` parameter on TokenManager or DownloadToken methods (we already found 2, there may be more)
7. **Check for `token_info.get("metadata"` patterns** — any code still reading from the old nested metadata dict structure

## What Models Have New Relationships (0840 series)?

### Product model (0840c)
- `tech_stack` → ProductTechStack (1:1)
- `architecture` → ProductArchitecture (1:1)
- `test_config` → ProductTestConfig (1:1)
- `vision_documents` → VisionDocument (1:many, pre-existing but affected by refresh)

### Message model (0840b)
- `recipients` → MessageRecipient (1:many)
- `acknowledgments` → MessageAcknowledgment (1:many)
- `completions` → MessageCompletion (1:many)

### User model (0840d)
- `field_priorities` → UserFieldPriority (1:many)

## Fix Pattern

For each bare `session.refresh(obj)` found:
```python
# BEFORE (will crash on detached access):
await session.refresh(product)

# AFTER (eager-loads relationships):
await session.refresh(
    product,
    attribute_names=["tech_stack", "architecture", "test_config", "vision_documents"],
)
```

For endpoints accessing relationships after service calls:
- Either add `selectinload`/`joinedload` to the query
- Or ensure the access happens within the session context

## Search Scope

Search ALL of these directories:
- `src/giljo_mcp/services/` — all service files
- `src/giljo_mcp/repositories/` — all repository files
- `api/endpoints/` — all endpoint files
- `src/giljo_mcp/tools/` — all tool files
- `src/giljo_mcp/` — root files (context_manager, thin_prompt_generator, etc.)

## Also Check: Frontend API Mismatches

While scanning, also check if the frontend is sending/receiving field names that don't match what the backend expects after 0840i removed backward compat. Look for:
- `config_data` references in frontend stores/components
- `to_agent` (singular) references
- Old field names like `languages` instead of `programming_languages`

## Reporting

Write results to `prompts/0840_chain/0840j_results.json`:
```json
{
  "session_id": "0840j",
  "title": "Detached Instance Audit",
  "status": "complete",
  "fixes": [
    {"file": "...", "line": N, "issue": "...", "fix": "...", "status": "fixed"}
  ],
  "total_issues_found": N,
  "total_fixed": N,
  "remaining_risks": [],
  "summary": "..."
}
```

## Success Criteria

- [ ] Every `session.refresh()` on Product/Message/User includes attribute_names
- [ ] Every endpoint accessing normalized relationships has proper eager loading
- [ ] No remaining `metadata=` keyword args on token methods
- [ ] No remaining `token_info.get("metadata"` patterns
- [ ] All fixes committed
- [ ] Server tested: create product, list products, update product, delete/restore product
