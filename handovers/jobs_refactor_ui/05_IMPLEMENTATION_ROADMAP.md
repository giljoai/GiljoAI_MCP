# Jobs Page UI Refactor - Implementation Roadmap

**Document ID**: jobs_refactor_ui/05_IMPLEMENTATION_ROADMAP.md
**Created**: 2025-11-21
**Status**: Planning Phase
**Priority**: High

---

## Document Purpose

This roadmap provides a detailed, phase-by-phase implementation plan for the Jobs Page UI Refactor, including timelines, dependencies, resource allocation, and testing strategies.

---

## Implementation Overview

**Total Duration**: 5-6 weeks
**Team Size**: 1-2 developers (frontend/backend capabilities)
**Risk Level**: Medium (breaking changes to existing UI)
**Rollback Strategy**: Feature flag toggle between old/new UI

---

## Phase 1: Foundation & Launch Tab (Week 1)

### Objectives
- Establish new tab-based architecture
- Implement Launch tab with three-column layout
- Build project staging workflow
- Set up backend endpoints for staging

### Tasks

#### Frontend Tasks (3-4 days)
1. **Create Tab Navigation Structure** (4 hours)
   - Create `TabNavigation.vue` component
   - Integrate with `ProjectView.vue`
   - Add route guards for tab transitions
   - **Files**: `frontend/src/components/jobs/TabNavigation.vue`

2. **Build Launch Tab Layout** (8 hours)
   - Create `LaunchTabPanel.vue` container
   - Implement three-column grid layout (Project / Orchestrator / Agents)
   - Create `ProjectDescriptionPanel.vue` with edit functionality
   - Create `OrchestratorMissionPanel.vue` (read-only display)
   - Create `AgentTeamPanel.vue` with agent cards
   - **Files**: `frontend/src/components/jobs/launch/`

3. **Implement Stage Project Button** (4 hours)
   - Add "Stage project" button with loading states
   - Integrate with Pinia `projectJobsStore`
   - Add copy-to-clipboard functionality for prompts
   - Add toast notifications for user feedback
   - **Files**: `LaunchTabPanel.vue`, `projectJobsStore.ts`

4. **Add Launch Jobs Button** (2 hours)
   - Add "Launch Jobs" button (disabled until staging complete)
   - Add confirmation modal
   - Wire up to backend endpoint
   - **Files**: `LaunchTabPanel.vue`

#### Backend Tasks (2-3 days)
1. **Create Staging Endpoints** (4 hours)
   - `POST /api/projects/{project_id}/stage/prompt` - Generate staging prompt
   - `POST /api/projects/{project_id}/stage` - Initialize staging process
   - Add request/response schemas
   - **Files**: `api/endpoints/staging.py`, `api/schemas/staging.py`

2. **Create PromptGeneratorService** (4 hours)
   - Extract prompt generation logic from existing code
   - Create `generate_staging_prompt()` method
   - Support both CLI modes (Claude Code CLI vs General CLI)
   - **Files**: `src/giljo_mcp/services/prompt_generator.py`

3. **Add Project Status Tracking** (2 hours)
   - Add `staging_status` field to `mcp_projects` table (if not exists)
   - Update `ProjectService` with staging methods
   - **Files**: `src/giljo_mcp/models.py`, `src/giljo_mcp/services/project_service.py`

#### Testing (1 day)
- Unit tests for `PromptGeneratorService`
- Integration tests for staging endpoints
- E2E test: Stage project workflow
- Manual UI testing: Launch tab interactions

### Deliverables
- ✅ Functional Launch tab with three-column layout
- ✅ Stage project workflow (button → API → prompt generation)
- ✅ Launch Jobs button (UI only, functionality in Phase 4)
- ✅ Backend staging endpoints with tests

### Dependencies
- None (clean start)

### Risks
- **Risk**: Existing `ProjectView.vue` may have tight coupling with old layout
- **Mitigation**: Create new components without modifying old ones, toggle via feature flag

---

## Phase 2: Status Board & Implementation Tab (Week 2)

### Objectives
- Build Implementation tab structure
- Create agent status board table
- Implement CLI mode toggle
- Add agent status tracking to database

### Tasks

#### Frontend Tasks (3-4 days)
1. **Create Implementation Tab Structure** (4 hours)
   - Create `ImplementationTabPanel.vue` container
   - Add CLI mode toggle banner (red/green)
   - Create `CLIModeToggle.vue` component
   - **Files**: `frontend/src/components/jobs/implementation/`

2. **Build Status Board Table** (8 hours)
   - Create `StatusBoard.vue` table component
   - Create `AgentRow.vue` for individual agent rows
   - Add column headers (Agent Type, ID, Status, Job Read, Job Ack, Msgs Sent/Wait/Read)
   - Implement responsive layout
   - **Files**: `StatusBoard.vue`, `AgentRow.vue`

3. **Create Agent Status Badge** (2 hours)
   - Create `AgentStatusBadge.vue` component
   - Support statuses: `Waiting.`, `Working.`, `Working...`, `Completed!`
   - Add animated dots for working states
   - **Files**: `AgentStatusBadge.vue`

4. **Add Action Buttons** (4 hours)
   - Play button (copy prompt)
   - Refresh/sync icon (re-copy prompt)
   - Message folder icon (placeholder for Phase 3)
   - Info icon (view agent template)
   - **Files**: `AgentRow.vue`, `ActionButtons.vue`

#### Backend Tasks (2-3 days)
1. **Database Schema Updates** (3 hours)
   - Add fields to `mcp_agent_jobs` table:
     - `job_read` BOOLEAN DEFAULT FALSE
     - `job_acknowledged` BOOLEAN DEFAULT FALSE
     - `messages_sent` INTEGER DEFAULT 0
     - `messages_waiting` INTEGER DEFAULT 0
     - `messages_read` INTEGER DEFAULT 0
   - Create migration script
   - **Files**: `src/giljo_mcp/models.py`, migration script

2. **Create Agent Status Endpoints** (4 hours)
   - `PATCH /api/agents/{agent_id}/status` - Update agent status
   - `GET /api/agents/{agent_id}` - Get agent with message counts
   - Add status validation (enum: Waiting, Working, Completed)
   - **Files**: `api/endpoints/agents.py`

3. **Update AgentJobManager** (3 hours)
   - Add methods for status tracking:
     - `update_agent_status()`
     - `mark_job_read()`
     - `mark_job_acknowledged()`
   - **Files**: `src/giljo_mcp/services/agent_job_manager.py`

#### Testing (1 day)
- Unit tests for `AgentJobManager` status methods
- Integration tests for agent status endpoints
- E2E test: Status board updates
- Manual UI testing: CLI mode toggle, status display

### Deliverables
- ✅ Functional Implementation tab with status board
- ✅ CLI mode toggle (UI + backend setting)
- ✅ Agent status tracking in database
- ✅ Status board displaying real-time agent states

### Dependencies
- Phase 1 completion (tab navigation must exist)

### Risks
- **Risk**: Database migration may affect existing agent jobs
- **Mitigation**: Add fields with default values, test on staging database first

---

## Phase 3: Message Queue System (Week 3)

### Objectives
- Build message sending interface
- Implement message history viewing
- Add broadcast functionality
- Create message queue backend

### Tasks

#### Frontend Tasks (3-4 days)
1. **Create Message Queue Panel** (6 hours)
   - Create `MessageQueuePanel.vue` component
   - Add agent selector dropdown
   - Add "Broadcast" toggle button
   - Add message input field
   - Add send button with loading state
   - **Files**: `MessageQueuePanel.vue`

2. **Create Message History Modal** (6 hours)
   - Create `MessageHistoryModal.vue` component
   - Display sent/received messages with timestamps
   - Add filtering (sent/received/all)
   - Add pagination for large message lists
   - **Files**: `MessageHistoryModal.vue`

3. **Wire Message Folder Icon** (2 hours)
   - Update `ActionButtons.vue` to open message history modal
   - Pass agent_id to modal
   - Fetch messages on modal open
   - **Files**: `ActionButtons.vue`

4. **Add Message Store** (4 hours)
   - Create `messageStore.ts` in Pinia
   - Actions: `sendMessage()`, `broadcastMessage()`, `loadMessages()`
   - State: `messages[]`, `unreadCounts{}`
   - **Files**: `frontend/src/stores/messageStore.ts`

#### Backend Tasks (3-4 days)
1. **Create agent_messages Table** (2 hours)
   - Create migration script for new table:
     ```sql
     CREATE TABLE agent_messages (
         id UUID PRIMARY KEY,
         project_id UUID,
         from_agent_id UUID,
         to_agent_id UUID,
         message_type VARCHAR(20),
         content TEXT,
         read BOOLEAN DEFAULT FALSE,
         created_at TIMESTAMP,
         read_at TIMESTAMP
     );
     ```
   - **Files**: Migration script, `src/giljo_mcp/models.py`

2. **Create MessageQueueService** (8 hours)
   - Create new service class
   - Methods:
     - `send_message(from_id, to_id, content)`
     - `broadcast_message(from_id, project_id, content)`
     - `get_messages(agent_id, filters)`
     - `mark_message_read(message_id)`
     - `get_unread_count(agent_id)`
   - Update message counters on `mcp_agent_jobs` table
   - **Files**: `src/giljo_mcp/services/message_queue_service.py`

3. **Create Message Endpoints** (4 hours)
   - `GET /api/agents/{agent_id}/messages` - Get message history
   - `POST /api/agents/messages` - Send direct message
   - `POST /api/agents/broadcast` - Broadcast to all agents
   - `PATCH /api/messages/{message_id}/read` - Mark as read
   - **Files**: `api/endpoints/messages.py`

4. **Add WebSocket Events** (2 hours)
   - Emit `agent:message_sent` on send
   - Emit `agent:message_received` to recipient
   - Update frontend to listen for real-time message events
   - **Files**: `api/websocket_manager.py`

#### Testing (1 day)
- Unit tests for `MessageQueueService`
- Integration tests for message endpoints
- WebSocket event testing
- E2E test: Send message → receive notification → view history
- Manual UI testing: Message sending, broadcast, history viewing

### Deliverables
- ✅ Functional message queue system
- ✅ Message sending interface (direct + broadcast)
- ✅ Message history viewing
- ✅ Real-time message notifications via WebSocket

### Dependencies
- Phase 2 completion (status board with agent IDs must exist)

### Risks
- **Risk**: WebSocket message delivery may fail under load
- **Mitigation**: Implement message batching, add retry logic, test with 10+ agents

---

## Phase 4: Agent Launch & Prompt Generation (Week 4)

### Objectives
- Implement "Launch Jobs" functionality
- Build prompt copying mechanism for both CLI modes
- Add real-time status updates
- Complete WebSocket integration

### Tasks

#### Frontend Tasks (3-4 days)
1. **Wire Launch Jobs Button** (4 hours)
   - Connect to backend `POST /api/projects/{project_id}/launch-jobs`
   - Show loading spinner during launch
   - Transition to Implementation tab on success
   - Display success toast notification
   - **Files**: `LaunchTabPanel.vue`, `projectJobsStore.ts`

2. **Implement Prompt Copying (Claude Code CLI Mode)** (6 hours)
   - Add "Copy Orchestrator Prompt" button (for CLI mode ON)
   - Generate prompt with:
     - Project context
     - Orchestrator mission
     - Subagent definitions (Analyzer, Implementer, Tester)
   - Copy to clipboard with success feedback
   - **Files**: `StatusBoard.vue`, `ActionButtons.vue`

3. **Implement Prompt Copying (General CLI Mode)** (6 hours)
   - Add individual "Copy Prompt" buttons per agent (CLI mode OFF)
   - Generate agent-specific prompts:
     - Project context
     - Agent mission
     - Agent role definition
   - Copy to clipboard with agent name in toast
   - **Files**: `AgentRow.vue`, `ActionButtons.vue`

4. **Add Real-Time Status Updates** (4 hours)
   - Listen for WebSocket events:
     - `agent:status_changed`
     - `agent:job_read`
     - `agent:job_acknowledged`
   - Update status board table in real-time
   - Add visual feedback (pulse animation on status change)
   - **Files**: `StatusBoard.vue`, `agentStore.ts`

#### Backend Tasks (2-3 days)
1. **Create Launch Jobs Endpoint** (4 hours)
   - `POST /api/projects/{project_id}/launch-jobs`
   - Initialize all agent jobs with `Waiting.` status
   - Emit `project:jobs_launched` WebSocket event
   - Return agent IDs and initial statuses
   - **Files**: `api/endpoints/projects.py`

2. **Create Agent Prompt Endpoints** (6 hours)
   - `GET /api/agents/{agent_id}/prompt` - Generate agent-specific prompt
   - Support two modes:
     - `mode=claude_code_cli` - Orchestrator prompt with subagents
     - `mode=general_cli` - Individual agent prompt
   - Use `PromptGeneratorService` from Phase 1
   - **Files**: `api/endpoints/agents.py`, `prompt_generator.py`

3. **Add WebSocket Status Events** (2 hours)
   - Emit events on status changes:
     - `agent:status_changed` (payload: agent_id, new_status)
     - `agent:job_read` (payload: agent_id)
     - `agent:job_acknowledged` (payload: agent_id)
   - **Files**: `api/websocket_manager.py`, `agent_job_manager.py`

#### Testing (1 day)
- Unit tests for prompt generation (both CLI modes)
- Integration tests for launch jobs endpoint
- WebSocket event testing (status changes propagate)
- E2E test: Launch jobs → copy prompt → update status → view in UI
- Manual UI testing: Both CLI modes, prompt copying, real-time updates

### Deliverables
- ✅ Functional "Launch Jobs" button
- ✅ Prompt copying for both CLI modes
- ✅ Real-time status updates via WebSocket
- ✅ Complete agent lifecycle (stage → launch → monitor)

### Dependencies
- Phase 1 completion (staging workflow)
- Phase 2 completion (status board)
- Phase 3 completion (message queue)

### Risks
- **Risk**: Prompt generation may fail if project data incomplete
- **Mitigation**: Add validation before launch, show clear error messages

---

## Phase 5: Polish, Testing & Deployment (Week 5)

### Objectives
- UI/UX refinements
- Comprehensive error handling
- End-to-end testing
- Feature flag setup
- Documentation
- Production deployment

### Tasks

#### Frontend Tasks (2 days)
1. **UI/UX Polish** (6 hours)
   - Add loading skeletons for async operations
   - Improve responsive layout (mobile/tablet support)
   - Add keyboard shortcuts (e.g., Ctrl+Enter to send message)
   - Polish animations and transitions
   - Add empty states (no agents, no messages)
   - **Files**: All frontend components

2. **Error Handling** (4 hours)
   - Add error boundaries for component failures
   - Display user-friendly error messages
   - Add retry buttons for failed operations
   - Log errors to console for debugging
   - **Files**: `ErrorBoundary.vue`, all async components

3. **Accessibility (A11y)** (2 hours)
   - Add ARIA labels to interactive elements
   - Ensure keyboard navigation works
   - Test with screen reader
   - **Files**: All frontend components

#### Backend Tasks (1 day)
1. **Error Handling & Validation** (4 hours)
   - Add input validation to all endpoints
   - Add error response schemas
   - Log errors with stack traces
   - **Files**: All endpoint files

2. **Performance Optimization** (2 hours)
   - Add database indexes on frequently queried fields
   - Implement query result caching (if applicable)
   - Optimize WebSocket message batching
   - **Files**: `models.py`, `websocket_manager.py`

#### Testing (2 days)
1. **End-to-End Test Suite** (8 hours)
   - E2E test: Complete workflow (stage → launch → monitor → message)
   - E2E test: CLI mode toggle (verify different prompts)
   - E2E test: Multi-agent coordination (send messages, broadcast)
   - E2E test: Error scenarios (network failure, invalid input)
   - **Files**: `tests/e2e/`

2. **Load Testing** (3 hours)
   - Simulate 10+ concurrent agents
   - Test WebSocket connection stability
   - Verify database performance under load
   - **Tools**: Locust, pytest-benchmark

3. **Regression Testing** (2 hours)
   - Verify old UI still works (if feature flag enabled)
   - Test existing API endpoints not affected
   - **Files**: `tests/integration/`

#### Deployment (1 day)
1. **Feature Flag Setup** (2 hours)
   - Add `ENABLE_NEW_JOBS_UI` flag to config
   - Toggle between old/new UI in `ProjectView.vue`
   - Add admin setting to enable/disable flag
   - **Files**: `config.yaml`, `ProjectView.vue`

2. **Documentation** (4 hours)
   - Update user documentation (how to use new UI)
   - Update developer documentation (component architecture)
   - Create migration guide for existing users
   - **Files**: `docs/jobs_page_refactor.md`

3. **Production Deployment** (2 hours)
   - Deploy backend changes (database migration first)
   - Deploy frontend changes (npm build)
   - Enable feature flag for beta users
   - Monitor logs for errors
   - **Deployment**: Production server

### Deliverables
- ✅ Polished UI with error handling and accessibility
- ✅ Comprehensive test suite (unit, integration, E2E)
- ✅ Feature flag for gradual rollout
- ✅ Updated documentation
- ✅ Production-ready deployment

### Dependencies
- Phase 1-4 completion (all features implemented)

### Risks
- **Risk**: Production deployment may reveal unforeseen issues
- **Mitigation**: Use feature flag to limit exposure, have rollback plan ready

---

## Critical Path Analysis

**Critical Path** (tasks that block other work):
1. Phase 1: Tab navigation structure → All subsequent phases
2. Phase 2: Database schema updates → Phase 3 message queue
3. Phase 3: Message queue backend → Phase 4 real-time updates
4. Phase 4: Launch jobs workflow → Phase 5 testing

**Parallel Work Opportunities**:
- Phase 2: Frontend status board + Backend schema updates (can be done simultaneously)
- Phase 3: Frontend message UI + Backend message queue (can be done simultaneously)
- Phase 5: Testing + Documentation (can be done simultaneously)

---

## Resource Allocation

### Single Developer (5-6 weeks)
- Week 1: Phase 1 (Foundation)
- Week 2: Phase 2 (Status Board)
- Week 3: Phase 3 (Message Queue)
- Week 4: Phase 4 (Agent Launch)
- Week 5: Phase 5 (Polish & Testing)
- Week 6: Buffer for unexpected issues

### Two Developers (4 weeks)
- **Developer A (Frontend Focus)**:
  - Week 1: Phase 1 frontend
  - Week 2: Phase 2 frontend
  - Week 3: Phase 3 frontend
  - Week 4: Phase 4 frontend + Phase 5 polish

- **Developer B (Backend Focus)**:
  - Week 1: Phase 1 backend
  - Week 2: Phase 2 backend
  - Week 3: Phase 3 backend
  - Week 4: Phase 4 backend + Phase 5 testing

**Recommended**: Two developers for faster delivery and better code quality

---

## Testing Strategy

### Unit Tests (Throughout Development)
- **Frontend**: Vue component tests with Vue Test Utils
- **Backend**: Pytest for service layer and utilities
- **Coverage Target**: >80% for all new code

### Integration Tests (After Each Phase)
- API endpoint tests with test database
- WebSocket event tests
- Pinia store integration tests
- **Coverage Target**: >70% for API endpoints

### End-to-End Tests (Phase 5)
- Selenium or Playwright for full UI workflows
- Test both CLI modes
- Test multi-agent scenarios
- **Coverage Target**: 100% of critical user paths

### Manual Testing (Throughout Development)
- UI/UX testing on different screen sizes
- Cross-browser testing (Chrome, Firefox, Safari)
- Accessibility testing with screen reader

---

## Rollout Plan

### Stage 1: Internal Testing (Week 5)
- Deploy to staging environment
- Enable feature flag for internal users only
- Collect feedback from team

### Stage 2: Beta Release (Week 6)
- Deploy to production with feature flag OFF by default
- Enable for 10-20% of users via admin setting
- Monitor logs and error rates
- Collect user feedback

### Stage 3: Full Release (Week 7+)
- Enable feature flag for all users
- Monitor for 1 week
- If stable, remove feature flag and old UI code

### Rollback Plan
- If critical issues found:
  1. Disable feature flag immediately (revert to old UI)
  2. Investigate and fix issues in development
  3. Re-test and re-deploy
  4. Resume rollout

---

## Risk Assessment & Mitigation

### High-Risk Areas

#### Risk 1: Breaking Existing Functionality
- **Probability**: Medium
- **Impact**: High
- **Mitigation**:
  - Feature flag to toggle between old/new UI
  - Comprehensive regression testing
  - Gradual rollout (10% → 50% → 100%)
- **Contingency**: Immediate rollback via feature flag

#### Risk 2: WebSocket Performance Under Load
- **Probability**: Medium
- **Impact**: Medium
- **Mitigation**:
  - Load testing with 20+ agents
  - Message batching and debouncing
  - Connection pooling and retry logic
- **Contingency**: Fallback to polling if WebSocket fails

#### Risk 3: User Confusion with Two CLI Modes
- **Probability**: Medium
- **Impact**: Low
- **Mitigation**:
  - Clear labels and color coding (red/green banners)
  - Tooltips explaining each mode
  - User documentation with screenshots
- **Contingency**: Add in-app tutorial or walkthrough

### Medium-Risk Areas

#### Risk 4: Database Migration Failures
- **Probability**: Low
- **Impact**: High
- **Mitigation**:
  - Test migrations on staging database first
  - Add fields with default values (non-breaking)
  - Backup database before migration
- **Contingency**: Rollback migration script ready

#### Risk 5: Prompt Generation Failures
- **Probability**: Medium
- **Impact**: Medium
- **Mitigation**:
  - Add validation before generating prompts
  - Provide clear error messages if data missing
  - Add fallback prompts for edge cases
- **Contingency**: Manual prompt editing capability

---

## Success Criteria

### Technical Metrics
- [ ] <100ms response time for status updates (P95)
- [ ] WebSocket connection stability >99%
- [ ] Support for 10+ concurrent agents without performance degradation
- [ ] Test coverage >80% (unit tests) and >70% (integration tests)
- [ ] Zero critical bugs in production after 1 week

### User Experience Metrics
- [ ] Reduced clicks to launch agents (from 5+ to 2-3)
- [ ] Clear visual progression through workflow (stage → launch → monitor)
- [ ] Real-time status visibility without page refresh
- [ ] Positive user feedback (>80% satisfaction)

### Functional Metrics
- [ ] Both CLI modes working correctly
- [ ] Message queue with <1s delivery time
- [ ] Accurate agent status tracking (no ghost agents)
- [ ] Zero data loss during migration

---

## Post-Launch Maintenance

### Week 1-2 (Monitoring)
- Monitor error logs daily
- Track WebSocket connection stability
- Collect user feedback via surveys
- Fix critical bugs immediately

### Week 3-4 (Optimization)
- Analyze performance metrics
- Optimize slow queries
- Improve UI based on feedback
- Add quality-of-life improvements

### Month 2+ (Feature Enhancements)
- Add agent performance metrics (time to complete, success rate)
- Add agent collaboration graph (visualize message flow)
- Add agent history (view past missions and results)
- Add agent templates library (save/reuse agent configurations)

---

## Conclusion

This roadmap provides a structured, phase-by-phase approach to implementing the Jobs Page UI Refactor. By following this plan, the team can deliver a sophisticated, feature-rich interface that significantly improves the user experience while maintaining system stability and performance.

**Key Takeaways**:
- 5-6 weeks for single developer, 4 weeks for two developers
- Feature flag for safe rollout and rollback
- Comprehensive testing at every phase
- Clear success criteria and risk mitigation
- Post-launch monitoring and optimization plan

**Next Steps**:
1. Review this roadmap with stakeholders
2. Assign developers and set start date
3. Create GitHub issues for each phase
4. Set up staging environment
5. Begin Phase 1 implementation

---

**Document Version**: 1.0
**Last Updated**: 2025-11-21
**Status**: Ready for Review
