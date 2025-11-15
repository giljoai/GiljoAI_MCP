# Handover 0515: Frontend Consolidation & WebSocket V2 Completion

**Date Created**: 2025-11-15
**Priority**: P1 (High - Pre-launch requirement)
**Duration**: 4-5 days total
**Status**: READY TO EXECUTE
**Dependencies**: Documentation updates (0512, 0514) should be complete

---

## Executive Summary

This handover consolidates all remaining frontend structural work into a single, comprehensive project. It merges work from:
- **0130c**: Consolidate duplicate components
- **0130d**: Centralize API calls
- **0130a**: Complete WebSocket V2 migration
- **0130b**: Remove flowWebSocket.js

The goal is to achieve a clean, maintainable frontend architecture before v3.0 launch.

---

## Background

After the 0120-0130 refactoring series, several frontend tasks were identified but not completed:
1. Multiple duplicate components exist (5+ versions of AgentCard)
2. API calls are scattered across 30+ components
3. WebSocket V2 was built but not migrated to
4. Old flowWebSocket.js layer still exists

This handover completes all this work in a structured, testable way.

---

## Sub-Task Breakdown

### 0515a: Merge Duplicate Components (from 0130c)
**Duration**: 1-2 days
**Tool**: CCW
**Parallel**: Can run with 0515b

**Scope**:
- Consolidate 5 AgentCard variants into one
- Merge 3 StatusBadge components
- Unify 4 LoadingSpinner implementations
- Standardize Modal/Dialog components
- Update all imports to use consolidated versions

**Files to modify**:
```
frontend/src/components/
├── agents/
│   ├── AgentCard.vue (keep)
│   ├── AgentCardMinimal.vue (merge into AgentCard)
│   ├── AgentCardDetailed.vue (merge into AgentCard)
│   └── AgentJobCard.vue (merge into AgentCard)
├── common/
│   ├── StatusBadge.vue (consolidate all variants here)
│   └── LoadingSpinner.vue (consolidate all variants here)
└── projects/
    └── Remove duplicate agent cards
```

**Success Criteria**:
- Single source of truth for each component type
- Props-based variants instead of separate files
- No duplicate component definitions
- All imports updated

---

### 0515b: Centralize API Calls (from 0130d)
**Duration**: 1-2 days
**Tool**: CCW
**Parallel**: Can run with 0515a

**Scope**:
- Move all axios calls from components to `api.js`
- Create typed API service methods
- Implement consistent error handling
- Add request/response interceptors
- Update 30+ components to use centralized API

**Files to modify**:
```
frontend/src/
├── api.js (expand with all endpoints)
├── services/
│   ├── productService.js (create)
│   ├── projectService.js (create)
│   ├── agentService.js (create)
│   └── settingsService.js (create)
└── components/ (update all to use services)
```

**API Methods to Centralize**:
```javascript
// Products
api.products.list()
api.products.create(data)
api.products.update(id, data)
api.products.delete(id)
api.products.uploadVision(id, file)

// Projects
api.projects.list()
api.projects.create(data)
api.projects.activate(id)
api.projects.complete(id, summary)

// Agent Jobs
api.agents.list()
api.agents.spawn(data)
api.agents.getStatus(id)
api.agents.triggerSuccession(id)

// Settings
api.settings.get()
api.settings.update(data)
api.settings.getFieldPriorities()
```

**Success Criteria**:
- Zero direct axios calls in components
- All API calls go through centralized services
- Consistent error handling across app
- Type safety for API calls

---

### 0515c: Complete WebSocket V2 Migration (from 0130a)
**Duration**: 1 day
**Tool**: CCW
**Parallel**: Must wait for 0515a+b completion
**Dependencies**: 0515a and 0515b should be merged first

**Scope**:
- Migrate from old WebSocket to V2 implementation
- Update all WebSocket event listeners
- Implement new reconnection logic
- Update store to use V2 patterns
- Test real-time updates

**Files to modify**:
```
frontend/src/
├── websocket/
│   ├── websocketV2.js (activate - may need creation)
│   ├── useWebSocketV2.js (activate - may need creation)
│   └── websocketIntegrations.js (update)
├── store/
│   └── websocket.js (migrate to V2)
└── components/ (update WebSocket usage)
```

**WebSocket V2 Features**:
- Exponential backoff reconnection
- Centralized subscription management
- Map-based event tracking
- Single reconnection system
- Better error handling

**Migration Steps**:
1. Create/verify websocketV2.js exists
2. Update store to use V2
3. Update all components using WebSocket
4. Test real-time updates work
5. Verify multi-tenant isolation

---

### 0515d: Remove flowWebSocket.js (from 0130b)
**Duration**: 2-3 hours
**Tool**: CLI (file deletion)
**Dependencies**: 0515c must be complete and tested

**Scope**:
- Delete flowWebSocket.js and related files
- Remove all imports/references
- Clean up unused WebSocket code
- Verify no breaking changes

**Files to delete**:
```
frontend/src/
├── flowWebSocket.js (DELETE)
├── websocket/
│   └── flowWebSocket.js (DELETE if exists)
└── Any other old WebSocket files
```

**Validation**:
```bash
# Ensure no references remain
grep -r "flowWebSocket" frontend/src/
grep -r "FlowWebSocket" frontend/src/

# Check for broken imports
npm run build
```

---

### 0515e: Integration Testing
**Duration**: 4-6 hours
**Tool**: CLI (requires live environment)
**Dependencies**: All 0515a-d must be complete

**Scope**:
- Test all consolidated components render correctly
- Verify API calls work through centralized service
- Test WebSocket real-time updates
- Verify no regressions
- Check multi-tenant isolation

**Test Scenarios**:
1. **Component Testing**:
   - All agent cards display correctly
   - Status badges show proper states
   - Loading spinners animate

2. **API Testing**:
   - Create product → Upload vision → Create project
   - All CRUD operations work
   - Error handling displays properly

3. **WebSocket Testing**:
   - Real-time updates when agent status changes
   - Mission updates appear immediately
   - Multi-tenant isolation maintained
   - Reconnection works after disconnect

4. **Performance Testing**:
   - Bundle size reduced (target: -10%)
   - No duplicate code in build
   - WebSocket connection stable

---

## Execution Strategy

### Parallel Execution Plan

**Day 1-2**: Launch two CCW sessions in parallel
```
CCW Session 1: 0515a-merge-components
└── Consolidate duplicate components

CCW Session 2: 0515b-centralize-api
└── Create API services, update components
```

**Day 2 PM**: User merges both branches, CLI tests

**Day 3**: Single CCW session
```
CCW Session 3: 0515c-websocket-v2
└── Complete WebSocket migration
```

**Day 3 PM**: User merges, then CLI cleanup
```
CLI: 0515d - Delete old WebSocket files
CLI: 0515e - Run integration tests
```

**Day 4**: Buffer for fixes and final testing

---

## Dependencies

### Required Before Starting
- Git branches should be clean
- Frontend builds successfully
- No pending merges

### Required From Other Handovers
- None - this is independent work

### Will Enable
- 0131a-d: Production readiness work
- v3.0 launch

---

## Success Criteria

### Quantitative
- [ ] Zero duplicate components (from 15+ to 0)
- [ ] Zero direct axios calls in components (from 30+ to 0)
- [ ] Single WebSocket implementation (from 2 to 1)
- [ ] Bundle size reduced by 10%+
- [ ] All tests passing

### Qualitative
- [ ] Cleaner, more maintainable codebase
- [ ] Consistent patterns across frontend
- [ ] Better developer experience
- [ ] Easier to onboard new developers

---

## Risk Mitigation

### Risks
1. **Merge conflicts**: Parallel work might conflict
2. **Breaking changes**: Consolidation might break features
3. **WebSocket issues**: Migration might break real-time updates

### Mitigations
1. **Design different components**: 0515a works on components/, 0515b on api/
2. **Incremental testing**: Test after each merge
3. **Keep old code briefly**: Don't delete flowWebSocket until V2 verified

---

## Notes for Implementers

### For 0515a (Components)
- Use props for variants, not separate components
- Follow Vue 3 Composition API patterns
- Document component APIs clearly
- Update Storybook if exists

### For 0515b (API)
- Use TypeScript interfaces if possible
- Implement proper error boundaries
- Add loading states consistently
- Consider adding request caching

### For 0515c (WebSocket)
- Test thoroughly before removing old system
- Verify reconnection logic works
- Check memory leaks don't occur
- Test with network interruptions

### For 0515d (Cleanup)
- Use git to verify deletions are safe
- Check build still works after deletion
- Verify no console errors in browser

---

## References

### Source Handovers (Now Integrated)
- 0130a: WebSocket Consolidation (frontend/README_0130a.md)
- 0130b: Remove flowWebSocket.js
- 0130c: Consolidate duplicate components
- 0130d: Centralize API calls

### Related Documentation
- Frontend Architecture: docs/FRONTEND_ARCHITECTURE.md
- WebSocket Design: docs/WEBSOCKET_V2_DESIGN.md
- API Patterns: docs/API_PATTERNS.md

---

## Completion Checklist

- [ ] 0515a: Components consolidated
- [ ] 0515b: API calls centralized
- [ ] 0515c: WebSocket V2 migrated
- [ ] 0515d: Old WebSocket removed
- [ ] 0515e: Integration tests pass
- [ ] Documentation updated
- [ ] Bundle size verified
- [ ] Performance validated
- [ ] Merged to master
- [ ] Deployed to dev environment

---

**End of Handover 0515**