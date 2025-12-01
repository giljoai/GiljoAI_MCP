# Handover 0281: Backend Monolithic Context Implementation

**Status**: 📋 READY FOR IMPLEMENTATION
**Priority**: 🔴 CRITICAL
**Parent**: Handover 0280 (Monolithic Context Architecture Roadmap)
**Created**: 2025-12-01
**Estimated Effort**: 2 weeks
**Team**: Backend Development + TDD Implementor Agents

---

## 🎯 Mission

Implement the monolithic context architecture by enhancing `get_orchestrator_instructions()` to:
1. Read user's field_priority_config and depth_config from database
2. Apply toggle logic (ON/OFF binary per context dimension)
3. Apply priority framing (CRITICAL/IMPORTANT/REFERENCE verbal markers)
4. Apply depth config (control token volume via chunk counts, pagination limits)
5. Delete 9 unused fetch_* tools (3,800 lines of dead code)
6. Achieve 80%+ test coverage

**Outcome**: User toggles context → Backend builds exact prompt user wants → No "WHO DECIDED?" questions.

---

## 📋 Implementation Checklist

### Phase 1: Core Enhancement (Days 1-2)

**File**: `src/giljo_mcp/tools/orchestration.py`

- [ ] **Task 1.1**: Add `user_id` parameter to `get_orchestrator_instructions()` signature
  ```python
  async def get_orchestrator_instructions(
      orchestrator_id: str,
      tenant_key: str,
      user_id: Optional[str] = None,  # NEW
      db: Optional[AsyncSession] = None
  ) -> dict[str, Any]:
  ```

- [ ] **Task 1.2**: Create `_get_user_config()` helper function
  ```python
  async def _get_user_config(
      user_id: str,
      tenant_key: str,
      db: AsyncSession
  ) -> Dict[str, Any]:
      """
      Fetch user's field_priority_config and depth_config.
      Returns system defaults if user config missing.
      """
      # Query users table for field_priority_config + depth_config
      # Return defaults if None
  ```

- [ ] **Task 1.3**: Define default configurations
  ```python
  DEFAULT_FIELD_PRIORITIES = {
      "product_core": {"toggle": True, "priority": 1},
      "project_context": {"toggle": True, "priority": 1},
      "vision_documents": {"toggle": True, "priority": 2},
      "tech_stack": {"toggle": True, "priority": 2},
      "architecture": {"toggle": True, "priority": 3},
      "testing_config": {"toggle": True, "priority": 3},
      "memory_360": {"toggle": True, "priority": 2},
      "git_history": {"toggle": False, "priority": 4},
      "agent_templates": {"toggle": True, "priority": 2}
  }

  DEFAULT_DEPTH_CONFIG = {
      "vision_chunking": "moderate",  # 4 chunks
      "memory_last_n_projects": 5,
      "git_commits": 15,
      "agent_template_detail": "standard"
  }
  ```

### Phase 2: Toggle & Priority Logic (Days 3-4)

**File**: `src/giljo_mcp/tools/orchestration.py`

- [ ] **Task 2.1**: Implement toggle filtering
  ```python
  # In get_orchestrator_instructions(), after fetching user config:
  enabled_contexts = [
      field for field, config in field_priorities.items()
      if config["toggle"] and config["priority"] < 4
  ]

  # Skip disabled contexts entirely (don't query database)
  ```

- [ ] **Task 2.2**: Create `_get_priority_frame()` helper
  ```python
  def _get_priority_frame(priority: int) -> Dict[str, str]:
      """
      Get priority framing headers and labels.

      Returns:
          {
              "header": "## **CRITICAL:",  # Markdown header
              "subheader": "**REQUIRED FOR ALL OPERATIONS**",
              "guidance": "**Why This Matters**: ..."
          }
      """
      frames = {
          1: {
              "header": "## **CRITICAL:",
              "subheader": "**REQUIRED FOR ALL OPERATIONS**",
              "guidance": "**Why This Matters**: This context defines fundamental requirements..."
          },
          2: {
              "header": "## **IMPORTANT:",
              "subheader": "**High priority context**",
              "guidance": "**Guidance**: Use this context to align implementation decisions..."
          },
          3: {
              "header": "##",
              "subheader": "**Supplemental information**",
              "guidance": "**Note**: Refer to this context when making structural decisions..."
          }
      }
      return frames.get(priority, frames[3])
  ```

- [ ] **Task 2.3**: Implement context formatting functions
  ```python
  def _format_product_core(product: Product, priority: int) -> str:
      """Format product core with priority framing."""
      frame = _get_priority_frame(priority)
      content = f"{frame['header']} Product Core Context** (Priority {priority})\n"
      content += f"{frame['subheader']}\n\n"
      content += f"**Product Name**: {product.name}\n"
      content += f"**Description**: {product.description}\n\n"
      content += f"{frame['guidance']}\n\n"
      return content

  def _format_vision_documents(docs: List[Dict], priority: int) -> str:
      """Format vision documents with priority framing."""
      # Similar pattern...

  def _format_360_memory(history: List[Dict], priority: int) -> str:
      """Format 360 Memory with priority framing."""
      # Similar pattern...

  # Implement for all 9 context dimensions
  ```

### Phase 3: Depth Config Implementation (Days 5-6)

**File**: `src/giljo_mcp/tools/orchestration.py`

- [ ] **Task 3.1**: Implement vision chunking depth control
  ```python
  async def _fetch_vision_documents(
      product_id: str,
      depth: str,  # "none", "light", "moderate", "heavy"
      tenant_key: str,
      db: AsyncSession
  ) -> List[Dict[str, Any]]:
      """
      Fetch vision document chunks based on depth setting.

      Depth mapping:
      - none: 0 chunks (0 tokens)
      - light: 2 chunks (~10K tokens)
      - moderate: 4 chunks (~17.5K tokens)
      - heavy: 6 chunks (~25K tokens)
      """
      chunk_limits = {"none": 0, "light": 2, "moderate": 4, "heavy": 6}
      limit = chunk_limits.get(depth, 4)

      if limit == 0:
          return []

      # Query vision_documents table with LIMIT
      # Return list of chunks
  ```

- [ ] **Task 3.2**: Implement 360 Memory pagination
  ```python
  async def _fetch_360_memory(
      product_id: str,
      depth: int,  # 1, 3, 5, or 10 projects
      tenant_key: str,
      db: AsyncSession
  ) -> List[Dict[str, Any]]:
      """
      Fetch 360 Memory project history based on depth setting.

      Depth = number of recent projects to include.
      Returns list in reverse chronological order.
      """
      # Fetch product_memory JSONB column
      # Extract sequential_history array
      # Sort by sequence DESC
      # LIMIT to depth value
      # Return list of project summaries
  ```

- [ ] **Task 3.3**: Implement git history limiting
  ```python
  async def _fetch_git_history(
      product_id: str,
      depth: int,  # 5, 15, or 25 commits
      tenant_key: str,
      db: AsyncSession
  ) -> List[Dict[str, Any]]:
      """
      Fetch Git commit history from product_memory based on depth setting.

      Depth = number of recent commits to include.
      Returns list in reverse chronological order.
      """
      # Fetch product_memory JSONB column
      # Check git_integration.enabled
      # Aggregate commits from sequential_history
      # Sort by timestamp DESC
      # LIMIT to depth value
      # Return list of commits
  ```

- [ ] **Task 3.4**: Implement agent template detail control
  ```python
  async def _fetch_agent_templates(
      tenant_key: str,
      depth: str,  # "minimal", "standard", "full"
      db: AsyncSession
  ) -> List[Dict[str, Any]]:
      """
      Fetch agent templates based on depth setting.

      Depth levels:
      - minimal: name + agent_type only (~400 tokens)
      - standard: name + agent_type + description (~1,200 tokens)
      - full: complete template with expertise + constraints (~2,400 tokens)
      """
      # Query agent_templates table
      # Build response based on depth
      # Return list of agents
  ```

### Phase 4: Error Handling & Graceful Degradation (Days 7-8)

**File**: `src/giljo_mcp/tools/orchestration.py`

- [ ] **Task 4.1**: Implement `_fetch_context_with_fallback()` wrapper
  ```python
  async def _fetch_context_with_fallback(
      context_type: str,
      fetch_func: Callable,
      *args,
      **kwargs
  ) -> Tuple[Optional[Any], Optional[str]]:
      """
      Fetch context with graceful fallback.

      Returns:
          (data, warning_message)
          - data: Fetched context or None
          - warning_message: Error description if fetch failed
      """
      try:
          data = await fetch_func(*args, **kwargs)
          if not data:
              return None, f"{context_type} unavailable: No data found"
          return data, None
      except Exception as e:
          logger.error(f"Failed to fetch {context_type}: {e}")
          return None, f"{context_type} unavailable: {str(e)}"
  ```

- [ ] **Task 4.2**: Update main function to collect warnings
  ```python
  # In get_orchestrator_instructions():
  warnings = []

  vision_docs, vision_warning = await _fetch_context_with_fallback(
      "Vision documents",
      _fetch_vision_documents,
      product.id, depth_config["vision_chunking"], tenant_key, db
  )
  if vision_warning:
      warnings.append(vision_warning)

  # ... collect warnings from all context fetches

  # Return warnings in response
  return {
      "orchestrator_id": orchestrator_id,
      "mission": mission,
      "warnings": warnings if warnings else None
  }
  ```

- [ ] **Task 4.3**: Add fail-fast error handling for critical paths
  ```python
  from src.giljo_mcp.exceptions import (
      OrchestratorNotFoundError,
      ProductNotFoundError,
      DatabaseError
  )

  # At start of get_orchestrator_instructions():
  try:
      # Step 1: Fetch orchestrator (CRITICAL)
      orchestrator = await _fetch_orchestrator(orchestrator_id, tenant_key, db)
      if not orchestrator:
          raise OrchestratorNotFoundError(f"Orchestrator {orchestrator_id} not found")

      # Step 2: Fetch project (CRITICAL)
      project = await _fetch_project(orchestrator.project_id, tenant_key, db)
      if not project:
          raise ProductNotFoundError(f"Project {orchestrator.project_id} not found")

      # Step 3: Fetch product (CRITICAL)
      product = await _fetch_product(project.product_id, tenant_key, db)
      if not product:
          raise ProductNotFoundError(f"Product {project.product_id} not found")

      # ... rest of implementation

  except (OrchestratorNotFoundError, ProductNotFoundError) as e:
      logger.error(f"Resource not found: {e}")
      raise
  except Exception as e:
      logger.critical(f"Database error: {e}")
      raise DatabaseError(f"Failed to fetch orchestrator instructions: {str(e)}")
  ```

### Phase 5: Code Deletion (Days 9-10)

**Files to DELETE**:

- [ ] **Task 5.1**: Delete individual fetch_* MCP tool definitions
  - File: `src/giljo_mcp/tools/context.py`
  - Functions to DELETE:
    - `fetch_product_context()`
    - `fetch_vision_document()`
    - `fetch_tech_stack()`
    - `fetch_architecture()`
    - `fetch_testing_config()`
    - `fetch_360_memory()`
    - `fetch_git_history()`
    - `fetch_agent_templates()`
    - `fetch_project_context()`
  - **Lines deleted**: ~1,852 lines

- [ ] **Task 5.2**: Delete implementation modules
  - Directory: `src/giljo_mcp/tools/context_tools/`
  - Files to DELETE:
    - `fetch_product_context.py`
    - `fetch_vision_document.py`
    - `fetch_tech_stack.py`
    - `fetch_architecture.py`
    - `fetch_testing_config.py`
    - `fetch_360_memory.py`
    - `fetch_git_history.py`
    - `fetch_agent_templates.py`
    - `fetch_project_context.py`
  - **Lines deleted**: ~2,200 lines

- [ ] **Task 5.3**: Remove tool registrations
  - File: `src/giljo_mcp/tools/__init__.py`
  - Remove MCP tool registration calls for all 9 fetch_* tools

- [ ] **Task 5.4**: Update thin_prompt_generator.py
  - File: `src/giljo_mcp/thin_prompt_generator.py`
  - Remove `category_to_tool` mapping (lines 563-580)
  - Remove tool template generation logic
  - Simplify to single tool call: `get_orchestrator_instructions(orchestrator_id, tenant_key)`

**TOTAL CODE DELETED**: 3,800 lines (67% reduction)

### Phase 6: Unit Testing (Days 11-12)

**File**: `tests/tools/test_context_orchestration.py` (NEW)

- [ ] **Task 6.1**: Test user config fetching
  ```python
  @pytest.mark.asyncio
  async def test_get_user_config_with_custom_settings(db_session, test_user):
      """Test fetching user config with custom priorities."""
      config = await _get_user_config(test_user.id, test_user.tenant_key, db_session)
      assert config["field_priority_config"]["vision_documents"]["priority"] == 2

  @pytest.mark.asyncio
  async def test_get_user_config_with_defaults(db_session, test_tenant):
      """Test fetching user config returns defaults when user has none."""
      config = await _get_user_config("nonexistent_user", test_tenant, db_session)
      assert config["field_priority_config"] == DEFAULT_FIELD_PRIORITIES
  ```

- [ ] **Task 6.2**: Test toggle logic
  ```python
  @pytest.mark.asyncio
  async def test_toggle_off_excludes_context(db_session, test_user, test_product):
      """Test that toggle OFF results in 0 bytes included."""
      # Set vision_documents toggle=False
      test_user.field_priority_config["vision_documents"]["toggle"] = False

      result = await get_orchestrator_instructions(
          orchestrator_id="test-orch",
          tenant_key=test_user.tenant_key,
          user_id=test_user.id,
          db=db_session
      )

      assert "vision_documents" not in result["included_contexts"]
      assert "vision_documents" in result["excluded_contexts"]
      assert "Vision Documents" not in result["mission"]  # 0 bytes
  ```

- [ ] **Task 6.3**: Test priority framing
  ```python
  @pytest.mark.asyncio
  async def test_priority_1_critical_framing(db_session, test_user, test_product):
      """Test Priority 1 contexts get CRITICAL framing."""
      test_user.field_priority_config["product_core"]["priority"] = 1

      result = await get_orchestrator_instructions(...)

      assert "**CRITICAL: Product Core Context**" in result["mission"]
      assert "**REQUIRED FOR ALL OPERATIONS**" in result["mission"]

  @pytest.mark.asyncio
  async def test_priority_2_important_framing(db_session, test_user, test_product):
      """Test Priority 2 contexts get IMPORTANT framing."""
      test_user.field_priority_config["vision_documents"]["priority"] = 2

      result = await get_orchestrator_instructions(...)

      assert "**IMPORTANT: Vision Documents**" in result["mission"]
      assert "**High priority context**" in result["mission"]

  @pytest.mark.asyncio
  async def test_priority_3_reference_framing(db_session, test_user, test_product):
      """Test Priority 3 contexts get REFERENCE framing."""
      test_user.field_priority_config["architecture"]["priority"] = 3

      result = await get_orchestrator_instructions(...)

      assert "Architecture (Priority 3 - REFERENCE)" in result["mission"]
      assert "**Supplemental information**" in result["mission"]
  ```

- [ ] **Task 6.4**: Test depth config
  ```python
  @pytest.mark.asyncio
  async def test_vision_chunking_light(db_session, test_user, test_product):
      """Test vision_chunking=light fetches exactly 2 chunks."""
      test_user.depth_config["vision_chunking"] = "light"

      result = await get_orchestrator_instructions(...)

      # Verify 2 chunks in mission
      assert result["mission"].count("### Vision Document") == 2

  @pytest.mark.asyncio
  async def test_memory_pagination(db_session, test_user, test_product):
      """Test memory_last_n_projects limits history correctly."""
      test_user.depth_config["memory_last_n_projects"] = 3

      result = await get_orchestrator_instructions(...)

      # Verify exactly 3 projects in mission
      assert result["mission"].count("### Project") == 3

  @pytest.mark.asyncio
  async def test_git_commit_limiting(db_session, test_user, test_product):
      """Test git_commits limits commit count correctly."""
      test_user.depth_config["git_commits"] = 5

      result = await get_orchestrator_instructions(...)

      # Verify exactly 5 commits in mission
      assert result["mission"].count("**Commit") == 5
  ```

- [ ] **Task 6.5**: Test error handling
  ```python
  @pytest.mark.asyncio
  async def test_orchestrator_not_found(db_session, test_tenant):
      """Test OrchestratorNotFoundError raised for invalid ID."""
      with pytest.raises(OrchestratorNotFoundError):
          await get_orchestrator_instructions(
              orchestrator_id="invalid_id",
              tenant_key=test_tenant,
              db=db_session
          )

  @pytest.mark.asyncio
  async def test_graceful_degradation_missing_vision_docs(db_session, test_user, test_product):
      """Test graceful degradation when vision docs unavailable."""
      # Product has no vision documents
      test_product.vision_documents = []

      result = await get_orchestrator_instructions(...)

      assert "Vision documents unavailable: No data found" in result["warnings"]
      assert "vision_documents" in result["excluded_contexts"]
  ```

**TARGET COVERAGE**: 80%+ for all new/modified functions

### Phase 7: Integration Testing (Days 13-14)

**File**: `tests/integration/test_orchestrator_monolithic_context.py` (NEW)

- [ ] **Task 7.1**: End-to-end user control flow
  ```python
  @pytest.mark.asyncio
  async def test_e2e_user_control_flow(db_session, test_user, test_product, test_project):
      """
      Test complete user control flow:
      1. User sets priorities in UI
      2. Settings saved to database
      3. Orchestrator launched with user_id
      4. get_orchestrator_instructions() respects user settings
      5. Response mission matches user expectations
      """
      # Step 1: User config
      test_user.field_priority_config = {
          "product_core": {"toggle": True, "priority": 1},
          "vision_documents": {"toggle": False, "priority": 4},  # EXCLUDED
          "tech_stack": {"toggle": True, "priority": 2},
          "architecture": {"toggle": True, "priority": 3},
          "memory_360": {"toggle": False, "priority": 4},  # EXCLUDED
          "git_history": {"toggle": False, "priority": 4},  # EXCLUDED
          "agent_templates": {"toggle": True, "priority": 2}
      }
      test_user.depth_config = {
          "vision_chunking": "none",  # Not applicable (disabled)
          "memory_last_n_projects": 0,  # Not applicable (disabled)
          "git_commits": 0,  # Not applicable (disabled)
          "agent_template_detail": "standard"
      }
      await db_session.commit()

      # Step 2-4: Launch orchestrator
      result = await get_orchestrator_instructions(
          orchestrator_id=test_orchestrator.id,
          tenant_key=test_user.tenant_key,
          user_id=test_user.id,
          db=db_session
      )

      # Step 5: Verify response
      assert result["included_contexts"] == ["product_core", "tech_stack", "architecture", "agent_templates"]
      assert result["excluded_contexts"] == ["vision_documents", "memory_360", "git_history"]
      assert "Vision Documents" not in result["mission"]  # 0 bytes
      assert "360 Memory" not in result["mission"]  # 0 bytes
      assert "Git History" not in result["mission"]  # 0 bytes
      assert "**CRITICAL: Product Core**" in result["mission"]
      assert "**IMPORTANT: Tech Stack**" in result["mission"]
  ```

- [ ] **Task 7.2**: Token count estimation accuracy
  ```python
  @pytest.mark.asyncio
  async def test_token_count_estimation_accuracy(db_session, test_user, test_product, test_project):
      """Test that estimated_tokens is within ±10% of actual."""
      result = await get_orchestrator_instructions(...)

      # Calculate actual token count (rough approximation: len / 4)
      actual_tokens = len(result["mission"]) // 4
      estimated_tokens = result["estimated_tokens"]

      # Verify within ±10%
      error_percentage = abs(estimated_tokens - actual_tokens) / actual_tokens * 100
      assert error_percentage < 10, f"Token estimation error: {error_percentage}%"
  ```

- [ ] **Task 7.3**: Performance benchmark vs old system
  ```python
  import time

  @pytest.mark.asyncio
  async def test_performance_benchmark(db_session, test_user, test_product, test_project):
      """Benchmark latency vs old 9-tool system."""
      start_time = time.time()

      result = await get_orchestrator_instructions(
          orchestrator_id=test_orchestrator.id,
          tenant_key=test_user.tenant_key,
          user_id=test_user.id,
          db=db_session
      )

      elapsed_ms = (time.time() - start_time) * 1000

      # Target: <500ms (vs old system 900-1500ms)
      assert elapsed_ms < 500, f"Latency too high: {elapsed_ms}ms"

      print(f"Latency: {elapsed_ms}ms (Target: <500ms)")
  ```

---

## 🧪 Testing Strategy

### Unit Tests (80%+ Coverage Target)
- User config fetching (defaults + custom)
- Toggle logic (ON/OFF)
- Priority framing (CRITICAL/IMPORTANT/REFERENCE)
- Depth config (vision chunking, memory pagination, git limits, agent detail)
- Error handling (not found, graceful degradation)

### Integration Tests
- End-to-end user control flow
- Token count estimation accuracy (±10%)
- Performance benchmarks (<500ms latency)

### Manual Testing Checklist
- [ ] User toggles context OFF in UI → 0 bytes in orchestrator prompt
- [ ] User sets Priority 1 → "CRITICAL" framing in prompt
- [ ] User sets Priority 2 → "IMPORTANT" framing in prompt
- [ ] User sets Priority 3 → "REFERENCE" framing in prompt
- [ ] User sets vision_chunking=light → Exactly 2 chunks in prompt
- [ ] User sets memory_last_n_projects=3 → Exactly 3 projects in prompt
- [ ] User sets git_commits=5 → Exactly 5 commits in prompt

---

## 📊 Acceptance Criteria

### Functional Requirements
- [ ] `get_orchestrator_instructions()` reads user config from database
- [ ] Toggle OFF → 0 bytes included (tested for all 9 context dimensions)
- [ ] Priority 4 → 0 bytes included (tested)
- [ ] Priority framing applied correctly:
  - [ ] Priority 1 → "**CRITICAL: ...**" + "REQUIRED FOR ALL OPERATIONS"
  - [ ] Priority 2 → "**IMPORTANT: ...**" + "High priority context"
  - [ ] Priority 3 → "... (Priority 3 - REFERENCE)" + "Supplemental information"
- [ ] Depth config controls token count:
  - [ ] vision_chunking: none=0, light=2, moderate=4, heavy=6 chunks
  - [ ] memory_last_n_projects: 1/3/5/10 projects
  - [ ] git_commits: 5/15/25 commits
  - [ ] agent_template_detail: minimal/standard/full
- [ ] 9 fetch_* tools DELETED from codebase
- [ ] thin_prompt_generator.py simplified (no tool template generation)

### Performance Requirements
- [ ] Average latency <500ms (vs 900ms baseline)
- [ ] P95 latency <800ms (vs 1800ms baseline)
- [ ] Database queries: 1-6 per call (vs 9 baseline)

### Quality Requirements
- [ ] Unit test coverage: 80%+
- [ ] Integration tests: All pass
- [ ] Error rate: <1% of calls (monitored post-deployment)
- [ ] Warning rate: <10% of calls (monitored post-deployment)

### Code Quality
- [ ] No code smells (pylint/ruff passes)
- [ ] Type hints on all functions (mypy passes)
- [ ] Docstrings on all public functions
- [ ] Logging at appropriate levels (DEBUG/INFO/WARNING/ERROR)

---

## 🚀 Deployment Plan

### Pre-Deployment
1. [ ] All tests passing (unit + integration)
2. [ ] Code review approved
3. [ ] Performance benchmarks documented
4. [ ] Staging deployment successful

### Deployment
1. [ ] Deploy to staging environment
2. [ ] Monitor logs for 24 hours
3. [ ] Run smoke tests (5 orchestrator launches)
4. [ ] Deploy to production
5. [ ] Monitor error rates for 48 hours

### Post-Deployment
1. [ ] Verify metrics meet targets (latency, error rate)
2. [ ] Collect user feedback (first 10 users)
3. [ ] Document any issues in Handover 0281 (this document)

---

## 📚 Reference Documents

### Architecture Design
- **File**: `docs/architecture/monolithic_context_design_spec_v2.md`
- **Sections to reference**:
  - Section 2: Function Signature Design
  - Section 4: Priority Framing Examples
  - Section 5: Depth Config Implementation
  - Section 6: Error Handling Strategy
  - Appendix A: Complete Implementation Skeleton

### Research Findings
- **File**: `handovers/0280_monolithic_context_architecture_roadmap.md`
- **Section 6**: Research Findings (3 Agents)
  - Agent 1: Current Architecture Audit
  - Agent 2: Monolithic Architecture Design
  - Agent 3: Documentation Audit

### Related Handovers
- **Handover 0279**: Context Priority Integration Fix (SUPERSEDED by this work)
- **Handover 0280**: Master Roadmap (parent handover)
- **Handover 0282**: Testing & Integration (next phase)
- **Handover 0283**: Documentation Remediation (final phase)

---

## 🤝 Team Coordination

### Backend Developer
**Responsibilities**:
- Implement core enhancement (Phase 1-4)
- Implement code deletion (Phase 5)
- Write unit tests (Phase 6)

### TDD Implementor Agent
**Responsibilities**:
- Write tests FIRST (TDD approach)
- Guide implementation via failing tests
- Ensure 80%+ coverage

### Database Expert (Consultation)
**Responsibilities**:
- Review database queries for performance
- Recommend indexes if needed
- Validate multi-tenant isolation

### System Architect (Review)
**Responsibilities**:
- Review architecture decisions
- Approve code deletions
- Final acceptance criteria verification

---

## 📝 Progress Tracking

### Week 1
- [ ] Day 1: Phase 1 (Core Enhancement) - Tasks 1.1-1.3
- [ ] Day 2: Phase 1 Complete
- [ ] Day 3: Phase 2 (Toggle & Priority) - Tasks 2.1-2.2
- [ ] Day 4: Phase 2 Complete (Task 2.3)
- [ ] Day 5: Phase 3 (Depth Config) - Tasks 3.1-3.2

### Week 2
- [ ] Day 6: Phase 3 Complete (Tasks 3.3-3.4)
- [ ] Day 7: Phase 4 (Error Handling) - Tasks 4.1-4.2
- [ ] Day 8: Phase 4 Complete (Task 4.3)
- [ ] Day 9: Phase 5 (Code Deletion) - Tasks 5.1-5.2
- [ ] Day 10: Phase 5 Complete (Tasks 5.3-5.4)
- [ ] Day 11: Phase 6 (Unit Testing) - Tasks 6.1-6.3
- [ ] Day 12: Phase 6 Complete (Tasks 6.4-6.5)
- [ ] Day 13: Phase 7 (Integration Testing) - Tasks 7.1-7.2
- [ ] Day 14: Phase 7 Complete (Task 7.3) + Final Review

---

## ✅ Definition of Done

**This handover is COMPLETE when**:
1. ✅ All 7 phases completed (checkboxes ticked)
2. ✅ Unit test coverage ≥80% (measured via pytest-cov)
3. ✅ Integration tests passing (all 3 scenarios)
4. ✅ Performance benchmarks documented (<500ms latency)
5. ✅ Code review approved by System Architect
6. ✅ Staging deployment successful
7. ✅ 3,800 lines of dead code DELETED (fetch_* tools removed)
8. ✅ No regressions in existing functionality

**Deliverable**: Working monolithic context tool that gives users absolute control over orchestrator context via priority toggles and depth config.

---

**END OF HANDOVER 0281**

Next: Proceed to Handover 0282 (Testing & Integration)
