# Handover 0313: Priority System Refactor

**Status**: Not Started
**Tool**: Claude Code (CLI) - Requires backend + frontend implementation
**Created**: 2025-11-17
**Dependencies**: 0312 (v2.0 Design)
**Next**: 0314 (Depth Controls)

---

## Objective

Migrate v1.0 priority semantics to v2.0 fetch order/mandatory flag model. Refactor UI from 13 individual field cards to 6 category cards with drag-and-drop priority ordering.

---

## Scope

### Backend Changes

1. **Update Priority Semantics**:
   - Change `User.field_priority_config` structure from 10/7/4 → 1/2/3/4
   - Priority 1 = CRITICAL (always fetch)
   - Priority 2 = IMPORTANT (fetch if budget allows)
   - Priority 3 = NICE_TO_HAVE (fetch if budget remaining)
   - Priority 4 = EXCLUDED (never fetch)

2. **Update Pydantic Schema**:
   ```python
   # api/schemas/user_schemas.py
   class FieldPriorityConfigV2(BaseModel):
       version: str = "2.0"
       priorities: Dict[str, int] = {
           "product_core": 1,        # CRITICAL
           "vision_documents": 2,    # IMPORTANT
           "agent_templates": 1,     # CRITICAL
           "memory_360": 3,          # NICE_TO_HAVE
           "project_context": 2,     # IMPORTANT
           "git_history": 4          # EXCLUDED
       }

   class UpdateFieldPrioritiesRequest(BaseModel):
       priorities: Dict[str, int]  # key: category name, value: 1-4
   ```

3. **Validation Logic**:
   - Ensure at least one category has Priority 1 (CRITICAL)
   - Validate priority values in range [1, 4]
   - Reject requests with all categories EXCLUDED

4. **Migration Script** (optional, seed defaults):
   ```python
   # For new users, seed default priorities
   DEFAULT_PRIORITIES_V2 = {
       "product_core": 1,
       "vision_documents": 2,
       "agent_templates": 1,
       "memory_360": 3,
       "project_context": 2,
       "git_history": 4
   }
   ```

5. **API Endpoint**:
   - Endpoint: `PUT /api/users/me/context/priorities`
   - Request body: `{"priorities": {"product_core": 1, ...}}`
   - Response: Updated priority config + WebSocket event

6. **WebSocket Metadata Emission**:
   - Event: `priority_config_updated`
   - Payload: `{user_id, timestamp, changes_applied: {...}}`

### Frontend Changes

1. **Refactor UI from 13 cards → 6 category cards**:
   - **Product Core**: description, tech stack, additional fields
   - **Vision Documents**: chunked vision uploads
   - **Agent Templates**: active agent behavior configurations
   - **Project Context**: project description, user notes
   - **360 Memory**: cumulative project history
   - **Git History**: recent commits

2. **New Component**: `PriorityConfiguration.vue`
   - Location: `frontend/src/components/settings/PriorityConfiguration.vue`
   - Features:
     - Drag-and-drop card ordering (affects fetch order)
     - Priority label toggles (CRITICAL/IMPORTANT/NICE/EXCLUDED)
     - Real-time preview of fetch order
     - WebSocket listener for `priority_config_updated` events

3. **UI Design** (ASCII mockup in 0312):
   ```
   Priority Configuration

   Drag cards to reorder fetch priority (top = Priority 1)
   Use toggles to mark as CRITICAL/IMPORTANT/NICE/EXCLUDED

   [CRITICAL: Product Core]
   [IMPORTANT: Vision Documents]
   [CRITICAL: Agent Templates]
   [NICE_TO_HAVE: 360 Memory]
   [NICE_TO_HAVE: Project Context]
   [EXCLUDED: Git History]

   [Save Priority Configuration]
   ```

4. **Integration with My Settings**:
   - Add "Context Configuration" section to My Settings
   - Tab 1: Priority Configuration (this handover)
   - Tab 2: Depth Configuration (handover 0314)

---

## Code Reuse from v1.0

**Keep**:
- `UserService.update_field_priorities()` method (update semantics only)
- `ContextConfiguration.vue` component structure (refactor card design)
- WebSocket emission logic (reuse event pattern)

**Update**:
- `FieldPrioritySchema` Pydantic model (change valid values 10/7/4 → 1/2/3/4)
- Priority validation logic (ensure at least one CRITICAL)
- Frontend card rendering (13 cards → 6 categories)

**Remove**:
- v1.0 uniform trimming logic (no longer needed)
- Priority-based token reduction calculations (moved to depth controls)

---

## Testing Strategy

### Unit Tests (`tests/api/test_priority_system.py`)

1. **Priority Validation**:
   - Test priority range enforcement (1-4 only)
   - Test at-least-one-CRITICAL requirement
   - Test rejection of all-EXCLUDED configuration
   - Test invalid category names

2. **API Endpoint**:
   - Test successful priority update
   - Test validation errors (invalid priority values)
   - Test multi-tenant isolation (user A can't update user B's priorities)
   - Test WebSocket metadata emission

3. **Default Seeding**:
   - Test new users get default v2.0 priorities
   - Test existing users (v1.0 priorities) are migrated on next update

### Integration Tests (`tests/integration/test_priority_system_integration.py`)

1. **End-to-End Workflow**:
   - Create user → verify default priorities seeded
   - Update priorities via API → verify database updated
   - Trigger WebSocket event → verify frontend receives update
   - Fetch user settings → verify updated priorities returned

2. **Frontend Integration**:
   - Simulate drag-and-drop → verify API called with new order
   - Toggle priority label → verify API called with new priority
   - WebSocket event received → verify UI updates without page reload

**Coverage Target**: >80%

---

## Deliverables

1. Updated `User.field_priority_config` semantics (1-4 range)
2. Refactored API endpoint: `PUT /api/users/me/context/priorities`
3. New frontend component: `PriorityConfiguration.vue`
4. Migration logic (seed defaults for new users)
5. Tests: `test_priority_system.py` (>80% coverage)
6. Updated documentation: My Settings → Context Configuration

---

## Success Criteria

- [ ] Priority system supports 4 levels (CRITICAL/IMPORTANT/NICE/EXCLUDED)
- [ ] API validates at-least-one-CRITICAL requirement
- [ ] Frontend displays 6 category cards (not 13 individual fields)
- [ ] Drag-and-drop priority ordering functional
- [ ] WebSocket metadata emitted on priority changes
- [ ] Tests pass with >80% coverage
- [ ] Migration logic seeds defaults for new users

---

## Dependencies

**Blocked by**: 0312 (v2.0 Design)

**Blocks**: 0315 (MCP Thin Client) - orchestrator needs priority config to decide WHAT to fetch

---

## Notes

**No Database Migration Required**: Repurposing existing `User.field_priority_config` JSONB column. Updating semantics only (10/7/4 → 1/2/3/4).

**Hard Cutover**: Clean implementation, no feature flags. v1.0 semantics removed after v2.0 deployment.

**Follow 013A Patterns**:
- Use `UserService` for CRUD operations
- Emit WebSocket events for real-time UI updates
- Multi-tenant isolation (filter by user_id/tenant_key)
- Production-grade code from start (no TODOs, no bandaids)
