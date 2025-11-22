# 0240 Series Execution Plan: GUI Redesign

**Series Overview**: Complete Launch/Implement tab GUI redesign based on PDF vision document
**Total Handovers**: 4 (0240a, 0240b, 0240c, 0240d)
**Total Estimated Effort**: 24-30 hours
**Parallel Execution**: ✅ 2-3 simultaneous CCW sessions possible
**Timeline**: 3-4 days wall-clock time

---

## 📋 Series Goals

Transform the GiljoAI dashboard Launch and Implement tabs to match the professional design shown in `F:\GiljoAI_MCP\handovers\Launch-Jobs_panels2\Refactor visuals for launch and implementation.pdf` (slides 2-27).

**Key Deliverables**:
- Launch Tab visual redesign (panels, buttons, typography)
- Implement Tab status board table (6 new components)
- Real-time WebSocket updates preserved
- Cross-browser compatibility (Chrome, Firefox, Edge)
- Comprehensive documentation and user guides

---

## 🗂️ Handover Files

### 0240a: Launch Tab Visual Redesign
**File**: `F:\GiljoAI_MCP\handovers\0240a_launch_tab_visual_redesign.md`
**Tool**: 🌐 CCW (Cloud)
**Effort**: 6-8 hours
**Parallel**: ✅ Yes (Group 1 with 0240b)

**Scope**:
- Update panel styling (rounded borders, dark theme, custom scrollbars)
- Apply monospace font to Orchestrator Mission panel
- Enhance button styling ("Stage Project" yellow outlined, "Launch Jobs" yellow filled)
- Add info/lock icons to agent cards
- Refine typography and empty states
- Responsive design (mobile/tablet/desktop)

**Success Criteria**:
- Visual design matches PDF slides 2-9
- All existing functionality preserved
- Unit tests >80% coverage
- No visual regressions

---

### 0240b: Implement Tab Component Refactor
**File**: `F:\GiljoAI_MCP\handovers\0240b_implement_tab_component_refactor.md`
**Tool**: 🌐 CCW (Cloud)
**Effort**: 12-16 hours
**Parallel**: ✅ Yes (Group 1 with 0240a)

**Scope**:
- Create 6 new StatusBoard components:
  1. `statusConfig.js` - Status/health configuration utilities
  2. `StatusChip.vue` - Status badge with health indicators
  3. `JobReadAckIndicators.vue` - Read/acknowledged checkmarks
  4. `ActionIcons.vue` - Action buttons (play/copy/message/info/cancel)
  5. `AgentTableView.vue` - Reusable status board table
  6. (Bonus) `MessageInput.vue` updates - Message recipient dropdown
- Replace horizontal agent cards in `JobsTab.vue` with table
- Implement 8-column table structure
- Add message recipient dropdown

**Success Criteria**:
- All 6 components created and unit tested
- Status board table matches PDF slides 10-27
- Real-time WebSocket updates work
- Unit tests >80% coverage (54 tests)
- No functional regressions

---

### 0240c: GUI Redesign Integration Testing
**File**: `F:\GiljoAI_MCP\handovers\0240c_gui_redesign_integration_testing.md`
**Tool**: 🖥️ CLI (Local)
**Effort**: 4-6 hours
**Parallel**: ❌ No (Sequential after 0240a & 0240b merge)
**Dependencies**: 0240a AND 0240b must be merged first

**Scope**:
- Manual UI testing (Launch Tab + Implement Tab)
- WebSocket real-time updates verification
- Responsive design testing (mobile/tablet/desktop)
- Cross-browser compatibility (Chrome, Firefox, Edge)
- Performance testing (bundle size, load time)
- End-to-end user workflows (Stage → Launch → Monitor)
- Bug fixing

**Success Criteria**:
- All visual elements match PDF vision document
- WebSocket updates work correctly
- Cross-browser compatibility verified
- No console errors
- Performance metrics within acceptable ranges
- All bugs fixed (P0/P1 priority)

---

### 0240d: GUI Redesign Documentation
**File**: `F:\GiljoAI_MCP\handovers\0240d_gui_redesign_documentation.md`
**Tool**: 🌐 CCW (Cloud)
**Effort**: 2-3 hours
**Parallel**: ✅ Yes (can run during 0240c testing)
**Optional**: Can defer if time-constrained

**Scope**:
- Update `CLAUDE.md` with new component locations
- Create `docs/user_guides/dashboard_guide.md` (user workflows)
- Create `docs/components/status_board_components.md` (component API docs)
- Add screenshots to `docs/screenshots/` directory

**Success Criteria**:
- CLAUDE.md accurate and up-to-date
- User guide complete with workflows
- Component API docs complete with props/events
- All code examples tested
- Screenshots current (optional)

---

## 🚀 Execution Strategy

### Option 1: Maximum Parallelization (Recommended)

**Wall-Clock Time**: 3-4 days

**Day 1-2: Parallel CCW Development**
```
┌─────────────────────────────────────────────────────┐
│ CCW Session 1: 0240a (Launch Tab Styling)          │
│ Duration: 6-8 hours                                 │
│ Branch: feature/0240a-launch-tab-visual-redesign   │
│ Pull Request #1                                     │
└─────────────────────────────────────────────────────┘

┌─────────────────────────────────────────────────────┐
│ CCW Session 2: 0240b (Implement Tab Components)    │
│ Duration: 12-16 hours                               │
│ Branch: feature/0240b-implement-tab-components      │
│ Pull Request #2                                     │
└─────────────────────────────────────────────────────┘

↓ User merges both PRs into master (resolve any conflicts)
```

**Day 2 PM - Day 3 AM: CLI Integration Testing**
```
┌─────────────────────────────────────────────────────┐
│ CLI: 0240c (Integration Testing)                    │
│ Duration: 4-6 hours                                 │
│ Test merged changes, fix bugs                       │
│ Commit fixes directly to master                     │
└─────────────────────────────────────────────────────┘

┌─────────────────────────────────────────────────────┐
│ CCW Session 3: 0240d (Documentation)                │
│ Duration: 2-3 hours                                 │
│ Branch: feature/0240d-gui-redesign-docs             │
│ Can run DURING 0240c testing (parallel)             │
│ Pull Request #3                                     │
└─────────────────────────────────────────────────────┘

↓ User merges documentation PR
```

**Day 3 PM - Day 4: Buffer & User Acceptance**
```
┌─────────────────────────────────────────────────────┐
│ Buffer time for edge cases, polish, user testing    │
│ Address any final bugs                              │
│ Performance tuning if needed                        │
│ Deploy to production                                │
└─────────────────────────────────────────────────────┘
```

**Total Wall-Clock**: 3-4 days (vs 5-6 days sequential)

---

### Option 2: Sequential Execution (Conservative)

**Wall-Clock Time**: 5-6 days

**Day 1-2: 0240a (Launch Tab)**
- CCW Session 1: 6-8 hours
- Merge to master

**Day 2-4: 0240b (Implement Tab)**
- CCW Session 2: 12-16 hours
- Merge to master

**Day 4-5: 0240c (Integration Testing)**
- CLI: 4-6 hours
- Fix bugs, commit to master

**Day 5: 0240d (Documentation)**
- CCW Session 3: 2-3 hours
- Merge to master

**Day 6: Buffer**
- User acceptance, deploy

**Total Wall-Clock**: 5-6 days

---

## 📊 Dependency Graph

```
┌──────────┐     ┌──────────┐
│  0240a   │     │  0240b   │
│ Launch   │     │Implement │
│  Tab     │     │   Tab    │
│ (6-8h)   │     │ (12-16h) │
└────┬─────┘     └────┬─────┘
     │                │
     └────────┬───────┘
              ↓
         ┌────────────┐
         │   MERGE    │
         │  (User)    │
         └────┬───────┘
              ↓
         ┌────────────┐     ┌──────────┐
         │   0240c    │     │  0240d   │
         │Integration │◄────┤   Docs   │
         │  Testing   │     │ (2-3h)   │
         │  (4-6h)    │     │(optional)│
         └────────────┘     └──────────┘
              ↓
         ┌────────────┐
         │  Complete  │
         └────────────┘
```

**Key Dependencies**:
- 0240a and 0240b are **independent** (can run in parallel)
- 0240c **depends on** 0240a AND 0240b being merged
- 0240d **can run in parallel** with 0240c (docs can be drafted during testing)

---

## 🎯 CCW vs CLI Assignments

### CCW-Suitable Handovers (3 handovers)

**0240a**: Launch Tab Visual Redesign
- ✅ Pure frontend styling (Vue component CSS/markup)
- ✅ No database access needed
- ✅ Independent of other handovers
- ✅ Can run in parallel with 0240b

**0240b**: Implement Tab Component Refactor
- ✅ Pure frontend components (6 new Vue files)
- ✅ No database access needed
- ✅ Independent of other handovers
- ✅ Can run in parallel with 0240a

**0240d**: GUI Redesign Documentation
- ✅ Pure documentation writing (Markdown files)
- ✅ No code execution needed
- ✅ Can run during 0240c testing (parallel)
- ✅ Optional (can defer)

**Total CCW Work**: 20-27 hours (can be split across 2-3 parallel sessions)

---

### CLI-Only Handovers (1 handover)

**0240c**: GUI Redesign Integration Testing
- 🖥️ Requires backend server access (10.1.0.164:7274)
- 🖥️ Requires database access (PostgreSQL)
- 🖥️ Requires WebSocket testing (live backend connection)
- 🖥️ Requires browser DevTools (performance profiling)
- 🖥️ Sequential after 0240a + 0240b merge

**Total CLI Work**: 4-6 hours (sequential, cannot parallelize)

---

## 💡 Parallel Execution Groups

### Group 1: Frontend Development (Parallel)
```
CCW Branch 1: 0240a-launch-tab-styling
CCW Branch 2: 0240b-implement-tab-components

Both work independently on separate files
Both create pull requests
User merges both PRs (minimal conflicts)
```

**Benefit**: 18-24 hours of work done in 12-16 hours wall-clock time

---

### Group 2: Testing + Documentation (Parallel)
```
CLI: 0240c-integration-testing (4-6 hours)
CCW Branch 3: 0240d-documentation (2-3 hours, during testing)

Documentation drafted while testing in progress
Docs finalized after testing reveals final implementation
```

**Benefit**: 6-9 hours of work done in 4-6 hours wall-clock time

---

## ⚠️ Potential Conflicts & Mitigation

### Merge Conflicts Between 0240a and 0240b

**Risk**: Both handovers modify frontend files, could have conflicts

**Mitigation**:
- 0240a modifies: `LaunchTab.vue` (styling only)
- 0240b modifies: `JobsTab.vue`, creates new `StatusBoard/` components
- **No file overlap** - minimal risk

**If conflicts occur**:
- User resolves conflicts manually
- Prefer 0240b changes if both touch same utility files
- Re-test after merge

---

### WebSocket Updates Breaking in 0240b

**Risk**: New table structure might break WebSocket subscription logic

**Mitigation**:
- 0240b explicitly preserves `useJobsWebSocket` composable
- 0240b handover includes WebSocket testing instructions
- 0240c dedicated to testing WebSocket updates

**If breaks occur**:
- 0240c will catch and fix
- Bug fix commits go directly to master
- No rollback needed (fix in place)

---

### Documentation Outdated from Bug Fixes

**Risk**: 0240d documentation written before 0240c bug fixes

**Mitigation**:
- 0240d can run **during** 0240c (parallel)
- 0240d drafts documentation based on original plan
- 0240d **updated after** 0240c reveals any implementation changes

**If changes occur**:
- Update docs after 0240c complete
- Add screenshots after final implementation
- Note any deviations in docs

---

## 📈 Progress Tracking

### Handover Completion Checklist

**0240a: Launch Tab Visual Redesign**
- [ ] Component styling updated (panels, buttons, cards)
- [ ] Unit tests passing (>80% coverage)
- [ ] Pull request created
- [ ] Code review passed
- [ ] Merged to master

**0240b: Implement Tab Component Refactor**
- [ ] 6 components created (StatusChip, ActionIcons, etc.)
- [ ] Unit tests passing (54 tests, >80% coverage)
- [ ] Pull request created
- [ ] Code review passed
- [ ] Merged to master

**0240c: GUI Redesign Integration Testing**
- [ ] Manual UI testing complete
- [ ] WebSocket real-time updates verified
- [ ] Cross-browser compatibility verified
- [ ] Performance metrics acceptable
- [ ] All P0/P1 bugs fixed
- [ ] Changes committed to master

**0240d: GUI Redesign Documentation**
- [ ] CLAUDE.md updated
- [ ] User guide created
- [ ] Component API docs created
- [ ] Screenshots added (optional)
- [ ] Pull request created
- [ ] Merged to master

---

### Daily Progress Summary Template

**End of Day X**:
- Handovers completed: [0240a, 0240b, 0240c, or 0240d]
- Handovers in progress: [List]
- Handovers blocked: [List with reason]
- Bugs found: [Count, priority breakdown]
- Bugs fixed: [Count]
- Estimated completion: [Date]

---

## 🔧 Troubleshooting

### CCW Session Issues

**Problem**: CCW session times out before handover complete
- **Solution**: Break handover into smaller commits, push frequently

**Problem**: CCW cannot access vision PDF
- **Solution**: Provide PDF content in handover file (key slides extracted)

**Problem**: CCW creates non-Vuetify components
- **Solution**: Handover specifies "Use Vuetify v-card, v-btn, etc."

---

### CLI Session Issues

**Problem**: Backend not accessible at 10.1.0.164:7274
- **Solution**: Start backend with `python startup.py`, verify with `curl http://10.1.0.164:7274/api/health`

**Problem**: WebSocket tests failing
- **Solution**: Check DevTools Network → WS tab, verify connection established, check `useJobsWebSocket` composable

**Problem**: Cross-browser testing unavailable
- **Solution**: Use Chrome DevTools device emulation, skip browser-specific tests if unavailable

---

## ✅ Series Success Criteria

**Must Have**:
- [ ] All 4 handovers completed successfully
- [ ] Launch Tab matches PDF slides 2-9 visually
- [ ] Implement Tab matches PDF slides 10-27 visually
- [ ] WebSocket real-time updates work correctly
- [ ] Cross-browser compatibility (Chrome, Firefox, Edge)
- [ ] Responsive design (mobile, tablet, desktop)
- [ ] No console errors in browser DevTools
- [ ] Performance metrics within acceptable ranges
- [ ] Documentation accurate and complete
- [ ] Unit tests >80% coverage across all components

**Nice to Have**:
- [ ] Screenshots in documentation
- [ ] Video walkthrough of workflows
- [ ] Accessibility compliance (ARIA, keyboard navigation)
- [ ] Smooth animations/transitions

---

## 📝 Final Deliverables

### Code Deliverables
1. **Frontend Components** (0240a, 0240b):
   - `frontend/src/components/projects/LaunchTab.vue` (modified)
   - `frontend/src/components/projects/JobsTab.vue` (modified)
   - `frontend/src/components/StatusBoard/*.vue` (6 new files)
   - `frontend/src/utils/statusConfig.js` (new)
   - `frontend/tests/unit/**/*.spec.js` (7+ new test files)

2. **Documentation** (0240d):
   - `CLAUDE.md` (updated)
   - `docs/user_guides/dashboard_guide.md` (new)
   - `docs/components/status_board_components.md` (new)
   - `docs/screenshots/*.png` (optional)

### Test Results
- **Unit tests**: 126+ tests passing (existing + new)
- **Coverage**: >80% across all components
- **Integration tests**: Manual checklist completed
- **Performance**: Bundle size <5% increase, load time <3s

### Documentation
- User guide with complete workflows
- Component API docs with props/events
- Updated architecture references
- Screenshots (optional)

---

## 🎉 Post-Series Next Steps

After completing the 0240 series:

1. **User Acceptance Testing**
   - Demonstrate new UI to stakeholders
   - Gather feedback
   - Create tickets for any requested improvements

2. **Production Deployment**
   - Deploy to production server
   - Monitor for errors
   - Rollback plan ready if issues arise

3. **Future Enhancements** (from 0240d docs)
   - Message Transcript Modal component
   - Agent Template Modal component
   - Table row expansion (click to expand details)
   - Column reordering (drag-and-drop)
   - Export table to CSV

4. **Performance Monitoring**
   - Track bundle size over time
   - Monitor load times in production
   - Optimize if performance degrades

---

## 📞 Support & Questions

**For Execution Questions**:
- Review handover file for specific task
- Check `QUICK_LAUNCH.txt` for code discipline
- Reference completed handovers (0233, 0235) for patterns

**For Technical Issues**:
- Check browser DevTools console for errors
- Verify backend running (`curl http://10.1.0.164:7274/api/health`)
- Review WebSocket connection in DevTools Network tab

**For Documentation Questions**:
- Reference existing docs in `docs/` directory
- Follow markdown format from other guides
- Use relative links for internal references

---

## 📊 Effort Summary

| Handover | Tool | Effort | Can Parallelize? |
|----------|------|--------|------------------|
| 0240a | CCW | 6-8h | ✅ Yes (with 0240b) |
| 0240b | CCW | 12-16h | ✅ Yes (with 0240a) |
| 0240c | CLI | 4-6h | ❌ No (sequential) |
| 0240d | CCW | 2-3h | ✅ Yes (with 0240c) |
| **Total** | - | **24-30h** | **2-3 parallel sessions** |

**Sequential Execution**: 5-6 days wall-clock
**Parallel Execution**: 3-4 days wall-clock

**CCW Credit Usage**: ~20-27 hours across 2-3 sessions
**CLI Time Required**: ~4-6 hours (1 session)

---

## 🚦 Execution Readiness Checklist

Before starting the 0240 series:

**Prerequisites**:
- [ ] Backend server accessible at 10.1.0.164:7274
- [ ] PostgreSQL database running
- [ ] Frontend build environment set up (`npm install` complete)
- [ ] Git repository clean (no uncommitted changes)
- [ ] Vision PDF accessible (`F:\GiljoAI_MCP\handovers\Launch-Jobs_panels2\Refactor visuals for launch and implementation.pdf`)

**CCW Setup**:
- [ ] CCW account has sufficient credits (20-27 hours needed)
- [ ] Can create 2-3 parallel sessions if desired
- [ ] CCW can access handover files (0240a.md, 0240b.md, 0240d.md)

**CLI Setup**:
- [ ] Local development environment ready
- [ ] Can access deployment server (10.1.0.164:7274)
- [ ] Browser DevTools available for testing
- [ ] Database access for manual queries (if needed)

**Ready to Execute**: ✅ All prerequisites met → Proceed with execution strategy

---

**End of 0240 Series Execution Plan**
