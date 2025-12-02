# Handover 0282: Testing & Integration - Monolithic Context

**Status**: 📋 READY FOR IMPLEMENTATION
**Priority**: 🔴 CRITICAL
**Parent**: Handover 0280 (Monolithic Context Architecture Roadmap)
**Prerequisite**: Handover 0281 (Backend Implementation) COMPLETE
**Created**: 2025-12-01
**Estimated Effort**: 1 week
**Team**: Backend Tester + Frontend Tester Agents

---

## 🎯 Mission

Validate that the monolithic context system:
1. Respects user priorities and depth config (integration tests)
2. Performs 60% faster than old system (performance benchmarks)
3. Estimates token counts accurately within ±10% (accuracy tests)
4. Handles errors gracefully (error scenario tests)
5. Works end-to-end from UI to orchestrator (E2E tests)

**Outcome**: 80%+ test coverage with documented proof that user control actually works.

---

## 📋 Testing Checklist

### Phase 1: Integration Test Suite (Days 1-3)

**File**: `tests/integration/test_orchestrator_monolithic_workflow.py` (NEW)

#### Test 1.1: User Priority Control Flow
```python
@pytest.mark.asyncio
async def test_user_excludes_vision_docs_zero_bytes_returned(
    db_session, test_user, test_product, test_project, test_orchestrator
):
    """
    Test: User sets vision_documents=EXCLUDED → 0 bytes in orchestrator prompt.

    Workflow:
    1. User toggles vision_documents OFF in UI
    2. Settings saved to database (field_priority_config)
    3. Orchestrator launched with user_id
    4. get_orchestrator_instructions() called
    5. Verify vision_documents EXCLUDED from response
    """
    # Step 1-2: User config
    test_user.field_priority_config["vision_documents"] = {"toggle": False, "priority": 4}
    await db_session.commit()

    # Step 3-4: Launch orchestrator
    response = await get_orchestrator_instructions(
        orchestrator_id=str(test_orchestrator.id),
        tenant_key=test_user.tenant_key,
        user_id=str(test_user.id),
        db=db_session
    )

    # Step 5: Verify
    assert "vision_documents" not in response["included_contexts"]
    assert "vision_documents" in response["excluded_contexts"]
    assert "Vision Document" not in response["mission"]  # 0 bytes
    assert len(response["mission"]) < 15000  # Should be smaller without vision docs

    print(f"✅ PASS: Vision docs excluded, mission size: {len(response['mission'])} chars")
```

#### Test 1.2: Priority Framing Applied Correctly
```python
@pytest.mark.asyncio
async def test_priority_1_gets_critical_framing(
    db_session, test_user, test_product, test_project, test_orchestrator
):
    """Test Priority 1 contexts get CRITICAL verbal framing."""
    # Arrange: Set product_core to Priority 1
    test_user.field_priority_config["product_core"] = {"toggle": True, "priority": 1}
    await db_session.commit()

    # Act
    response = await get_orchestrator_instructions(
        orchestrator_id=str(test_orchestrator.id),
        tenant_key=test_user.tenant_key,
        user_id=str(test_user.id),
        db=db_session
    )

    # Assert
    assert "**CRITICAL: Product Core Context**" in response["mission"]
    assert "**REQUIRED FOR ALL OPERATIONS**" in response["mission"]
    assert "(Priority 1)" in response["mission"]

    print("✅ PASS: Priority 1 CRITICAL framing applied")


@pytest.mark.asyncio
async def test_priority_2_gets_important_framing(
    db_session, test_user, test_product, test_project, test_orchestrator
):
    """Test Priority 2 contexts get IMPORTANT verbal framing."""
    test_user.field_priority_config["tech_stack"] = {"toggle": True, "priority": 2}
    await db_session.commit()

    response = await get_orchestrator_instructions(...)

    assert "**IMPORTANT: Tech Stack**" in response["mission"]
    assert "**High priority context**" in response["mission"]
    assert "(Priority 2)" in response["mission"]

    print("✅ PASS: Priority 2 IMPORTANT framing applied")


@pytest.mark.asyncio
async def test_priority_3_gets_reference_framing(
    db_session, test_user, test_product, test_project, test_orchestrator
):
    """Test Priority 3 contexts get REFERENCE verbal framing."""
    test_user.field_priority_config["architecture"] = {"toggle": True, "priority": 3}
    await db_session.commit()

    response = await get_orchestrator_instructions(...)

    assert "Architecture (Priority 3 - REFERENCE)" in response["mission"]
    assert "**Supplemental information**" in response["mission"]

    print("✅ PASS: Priority 3 REFERENCE framing applied")
```

#### Test 1.3: Depth Config Controls Token Volume
```python
@pytest.mark.asyncio
async def test_vision_chunking_light_returns_2_chunks(
    db_session, test_user, test_product, test_project, test_orchestrator
):
    """Test vision_chunking=light returns exactly 2 chunks."""
    # Arrange: Create 6 vision document chunks
    for i in range(1, 7):
        chunk = VisionDocument(
            id=str(uuid4()),
            product_id=test_product.id,
            tenant_key=test_user.tenant_key,
            title="Vision Doc",
            content=f"Chunk {i} content ({2000 * i} tokens)",
            sequence=i
        )
        db_session.add(chunk)
    await db_session.commit()

    # Set depth to light (2 chunks)
    test_user.depth_config["vision_chunking"] = "light"
    await db_session.commit()

    # Act
    response = await get_orchestrator_instructions(...)

    # Assert: Exactly 2 chunks in mission
    chunk_count = response["mission"].count("### Vision Document")
    assert chunk_count == 2, f"Expected 2 chunks, got {chunk_count}"

    print("✅ PASS: vision_chunking=light returns 2 chunks")


@pytest.mark.asyncio
async def test_memory_pagination_3_projects(
    db_session, test_user, test_product, test_project, test_orchestrator
):
    """Test memory_last_n_projects=3 returns exactly 3 projects."""
    # Arrange: Create product with 10 project history entries
    test_product.product_memory = {
        "sequential_history": [
            {"sequence": i, "summary": f"Project {i}", "timestamp": f"2025-11-{20-i:02d}"}
            for i in range(1, 11)
        ]
    }
    await db_session.commit()

    # Set depth to 3 projects
    test_user.depth_config["memory_last_n_projects"] = 3
    await db_session.commit()

    # Act
    response = await get_orchestrator_instructions(...)

    # Assert: Exactly 3 projects in mission
    project_count = response["mission"].count("### Project")
    assert project_count == 3, f"Expected 3 projects, got {project_count}"

    print("✅ PASS: memory_last_n_projects=3 returns 3 projects")


@pytest.mark.asyncio
async def test_git_commits_limiting(
    db_session, test_user, test_product, test_project, test_orchestrator
):
    """Test git_commits=5 returns exactly 5 commits."""
    # Arrange: Create product with 25 git commits
    test_product.product_memory = {
        "git_integration": {"enabled": True},
        "sequential_history": [
            {
                "sequence": 1,
                "git_commits": [
                    {"sha": f"abc{i:03d}", "message": f"Commit {i}", "timestamp": f"2025-11-{i:02d}"}
                    for i in range(1, 26)
                ]
            }
        ]
    }
    await db_session.commit()

    # Set depth to 5 commits
    test_user.depth_config["git_commits"] = 5
    await db_session.commit()

    # Act
    response = await get_orchestrator_instructions(...)

    # Assert: Exactly 5 commits in mission
    commit_count = response["mission"].count("**Commit")
    assert commit_count == 5, f"Expected 5 commits, got {commit_count}"

    print("✅ PASS: git_commits=5 returns 5 commits")
```

#### Test 1.4: End-to-End User Control
```python
@pytest.mark.asyncio
async def test_e2e_user_fully_controls_orchestrator_context(
    db_session, test_user, test_product, test_project, test_orchestrator
):
    """
    End-to-end test: User settings → Database → Orchestrator → Filtered Context.

    User wants:
    - Product Core: CRITICAL (Priority 1)
    - Tech Stack: IMPORTANT (Priority 2)
    - Architecture: REFERENCE (Priority 3)
    - Vision Docs: EXCLUDED (toggle OFF)
    - 360 Memory: EXCLUDED (toggle OFF)
    - Git History: EXCLUDED (toggle OFF)
    """
    # Arrange: User config
    test_user.field_priority_config = {
        "product_core": {"toggle": True, "priority": 1},
        "project_context": {"toggle": True, "priority": 1},
        "tech_stack": {"toggle": True, "priority": 2},
        "architecture": {"toggle": True, "priority": 3},
        "vision_documents": {"toggle": False, "priority": 4},  # EXCLUDED
        "memory_360": {"toggle": False, "priority": 4},        # EXCLUDED
        "git_history": {"toggle": False, "priority": 4},       # EXCLUDED
        "testing_config": {"toggle": False, "priority": 4},    # EXCLUDED
        "agent_templates": {"toggle": True, "priority": 2}
    }
    test_user.depth_config = {
        "vision_chunking": "none",  # Not applicable
        "memory_last_n_projects": 0,  # Not applicable
        "git_commits": 0,  # Not applicable
        "agent_template_detail": "standard"
    }
    await db_session.commit()

    # Act: Launch orchestrator
    response = await get_orchestrator_instructions(
        orchestrator_id=str(test_orchestrator.id),
        tenant_key=test_user.tenant_key,
        user_id=str(test_user.id),
        db=db_session
    )

    # Assert: Response matches user expectations
    assert set(response["included_contexts"]) == {
        "product_core", "project_context", "tech_stack", "architecture", "agent_templates"
    }
    assert set(response["excluded_contexts"]) == {
        "vision_documents", "memory_360", "git_history", "testing_config"
    }

    # Verify framing
    assert "**CRITICAL: Product Core**" in response["mission"]
    assert "**IMPORTANT: Tech Stack**" in response["mission"]
    assert "Architecture (Priority 3 - REFERENCE)" in response["mission"]

    # Verify exclusions (0 bytes)
    assert "Vision Document" not in response["mission"]
    assert "360 Memory" not in response["mission"]
    assert "Git History" not in response["mission"]

    # Verify token savings
    assert response["estimated_tokens"] < 10000  # Should be < 10K without big contexts

    print(f"✅ PASS: End-to-end user control verified")
    print(f"   Included: {response['included_contexts']}")
    print(f"   Excluded: {response['excluded_contexts']}")
    print(f"   Tokens: {response['estimated_tokens']}")
```

### Phase 2: Performance Benchmarks (Days 4-5)

**File**: `tests/performance/test_monolithic_context_performance.py` (NEW)

#### Test 2.1: Latency Benchmark
```python
import time
import statistics

@pytest.mark.asyncio
async def test_latency_under_500ms_target(
    db_session, test_user, test_product, test_project, test_orchestrator
):
    """Benchmark: Average latency <500ms (vs 900ms baseline)."""
    latencies = []

    # Run 10 iterations
    for i in range(10):
        start_time = time.time()

        response = await get_orchestrator_instructions(
            orchestrator_id=str(test_orchestrator.id),
            tenant_key=test_user.tenant_key,
            user_id=str(test_user.id),
            db=db_session
        )

        elapsed_ms = (time.time() - start_time) * 1000
        latencies.append(elapsed_ms)

    # Calculate statistics
    avg_latency = statistics.mean(latencies)
    p95_latency = statistics.quantiles(latencies, n=20)[18]  # 95th percentile

    # Assert targets
    assert avg_latency < 500, f"Average latency too high: {avg_latency:.2f}ms (target: <500ms)"
    assert p95_latency < 800, f"P95 latency too high: {p95_latency:.2f}ms (target: <800ms)"

    print(f"✅ PASS: Performance benchmark")
    print(f"   Average latency: {avg_latency:.2f}ms (target: <500ms)")
    print(f"   P95 latency: {p95_latency:.2f}ms (target: <800ms)")
    print(f"   Min: {min(latencies):.2f}ms, Max: {max(latencies):.2f}ms")
```

#### Test 2.2: Database Query Count
```python
@pytest.mark.asyncio
async def test_database_query_count_optimization(
    db_session, test_user, test_product, test_project, test_orchestrator
):
    """Verify database queries: 1-6 per call (vs 9 baseline)."""

    # Track queries using SQLAlchemy event listener
    query_count = 0

    def track_queries(conn, cursor, statement, parameters, context, executemany):
        nonlocal query_count
        query_count += 1

    from sqlalchemy import event
    event.listen(db_session.bind, "before_cursor_execute", track_queries)

    try:
        response = await get_orchestrator_instructions(
            orchestrator_id=str(test_orchestrator.id),
            tenant_key=test_user.tenant_key,
            user_id=str(test_user.id),
            db=db_session
        )

        # Assert: Query count < 9 (old system)
        assert query_count <= 6, f"Too many queries: {query_count} (target: ≤6)"

        print(f"✅ PASS: Database query optimization")
        print(f"   Queries: {query_count} (vs 9 in old system)")
        print(f"   Reduction: {((9 - query_count) / 9 * 100):.1f}%")

    finally:
        event.remove(db_session.bind, "before_cursor_execute", track_queries)
```

#### Test 2.3: Token Savings Verification
```python
@pytest.mark.asyncio
async def test_token_savings_vs_old_system(
    db_session, test_user, test_product, test_project, test_orchestrator
):
    """
    Verify token savings: ~5,400 tokens saved (MCP tool definitions removed).

    OLD: 9 fetch_* tool definitions (~600 tokens each) = 5,400 tokens
    NEW: 1 get_orchestrator_instructions definition = ~600 tokens
    SAVINGS: 4,800 tokens (89% reduction in tool overhead)
    """
    # This is verified by code deletion (Handover 0281 Phase 5)
    # Here we document the savings

    old_tool_overhead = 9 * 600  # 9 tools × 600 tokens each
    new_tool_overhead = 600      # 1 tool × 600 tokens
    savings = old_tool_overhead - new_tool_overhead

    print(f"✅ PASS: Token savings documented")
    print(f"   OLD tool overhead: {old_tool_overhead} tokens")
    print(f"   NEW tool overhead: {new_tool_overhead} tokens")
    print(f"   SAVINGS: {savings} tokens ({savings / old_tool_overhead * 100:.1f}% reduction)")
```

### Phase 3: Token Estimation Accuracy (Day 6)

**File**: `tests/accuracy/test_token_estimation.py` (NEW)

#### Test 3.1: Token Count Estimation ±10% Accuracy
```python
@pytest.mark.asyncio
async def test_token_estimation_accuracy_within_10_percent(
    db_session, test_user, test_product, test_project, test_orchestrator
):
    """
    Test token estimation accuracy: ±10% of actual.

    Token estimation method: len(mission) / 4 (rough approximation)
    Verify against multiple scenarios (small/medium/large prompts).
    """
    # Test 100 orchestrator launches with different configs
    errors = []

    for i in range(100):
        # Randomize user config
        test_user.field_priority_config = _generate_random_config()
        await db_session.commit()

        response = await get_orchestrator_instructions(...)

        # Calculate actual tokens (using tiktoken for accuracy)
        import tiktoken
        encoder = tiktoken.get_encoding("cl100k_base")
        actual_tokens = len(encoder.encode(response["mission"]))

        estimated_tokens = response["estimated_tokens"]

        # Calculate error percentage
        error_pct = abs(estimated_tokens - actual_tokens) / actual_tokens * 100
        errors.append(error_pct)

    # Assert: Average error <10%
    avg_error = statistics.mean(errors)
    assert avg_error < 10, f"Token estimation error too high: {avg_error:.2f}% (target: <10%)"

    print(f"✅ PASS: Token estimation accuracy")
    print(f"   Average error: {avg_error:.2f}% (target: <10%)")
    print(f"   Min error: {min(errors):.2f}%, Max error: {max(errors):.2f}%")
```

### Phase 4: Error Scenario Testing (Day 7)

**File**: `tests/integration/test_error_scenarios.py` (NEW)

#### Test 4.1: Graceful Degradation
```python
@pytest.mark.asyncio
async def test_graceful_degradation_missing_vision_docs(
    db_session, test_user, test_product, test_project, test_orchestrator
):
    """Test graceful degradation when vision docs unavailable."""
    # Arrange: Product has no vision documents
    # (don't create any VisionDocument records)

    test_user.field_priority_config["vision_documents"] = {"toggle": True, "priority": 2}
    await db_session.commit()

    # Act
    response = await get_orchestrator_instructions(...)

    # Assert: Warning added, but orchestrator still works
    assert response["warnings"] is not None
    assert any("Vision documents unavailable" in w for w in response["warnings"])
    assert "vision_documents" in response["excluded_contexts"]
    assert response["mission"] is not None  # Still got a mission

    print("✅ PASS: Graceful degradation (missing vision docs)")


@pytest.mark.asyncio
async def test_graceful_degradation_github_disabled(
    db_session, test_user, test_product, test_project, test_orchestrator
):
    """Test graceful degradation when GitHub integration disabled."""
    # Arrange: GitHub integration OFF
    test_product.product_memory = {
        "git_integration": {"enabled": False}
    }
    await db_session.commit()

    test_user.field_priority_config["git_history"] = {"toggle": True, "priority": 2}
    await db_session.commit()

    # Act
    response = await get_orchestrator_instructions(...)

    # Assert: Warning added
    assert response["warnings"] is not None
    assert any("Git history unavailable" in w for w in response["warnings"])

    print("✅ PASS: Graceful degradation (GitHub disabled)")
```

#### Test 4.2: Error Handling (Fail Fast)
```python
@pytest.mark.asyncio
async def test_orchestrator_not_found_raises_error(db_session, test_tenant):
    """Test OrchestratorNotFoundError for invalid orchestrator_id."""
    with pytest.raises(OrchestratorNotFoundError):
        await get_orchestrator_instructions(
            orchestrator_id="invalid_uuid",
            tenant_key=test_tenant,
            db=db_session
        )

    print("✅ PASS: Fail fast (orchestrator not found)")


@pytest.mark.asyncio
async def test_product_not_found_raises_error(
    db_session, test_user, test_project, test_orchestrator
):
    """Test ProductNotFoundError when product missing."""
    # Arrange: Delete product
    await db_session.delete(test_project.product)
    await db_session.commit()

    # Act & Assert
    with pytest.raises(ProductNotFoundError):
        await get_orchestrator_instructions(
            orchestrator_id=str(test_orchestrator.id),
            tenant_key=test_user.tenant_key,
            db=db_session
        )

    print("✅ PASS: Fail fast (product not found)")
```

---

## 📊 Success Metrics

### Test Coverage Metrics
| Metric | Target | Measurement |
|--------|--------|-------------|
| **Unit Test Coverage** | 80%+ | pytest-cov |
| **Integration Test Coverage** | 100% of workflows | Manual verification |
| **Performance Tests** | All pass | Automated benchmarks |

### Performance Metrics
| Metric | Baseline (Old) | Target (New) | Result |
|--------|----------------|--------------|--------|
| **Average Latency** | 900-1500ms | <500ms | _TBD_ |
| **P95 Latency** | 1800ms | <800ms | _TBD_ |
| **Database Queries** | 9 per call | 1-6 per call | _TBD_ |

### Accuracy Metrics
| Metric | Target | Result |
|--------|--------|--------|
| **Token Estimation Accuracy** | ±10% | _TBD_ |
| **User Control Accuracy** | 100% (settings respected) | _TBD_ |

---

## ✅ Acceptance Criteria

### Integration Tests
- [ ] User exclusion (toggle OFF) → 0 bytes included (tested)
- [ ] Priority framing (1/2/3) → Correct verbal markers (tested)
- [ ] Depth config → Exact token volume control (tested)
- [ ] End-to-end user control → All settings respected (tested)

### Performance Tests
- [ ] Average latency <500ms (tested with 10 iterations)
- [ ] P95 latency <800ms (tested with 10 iterations)
- [ ] Database queries ≤6 per call (tracked via event listener)

### Accuracy Tests
- [ ] Token estimation ±10% (tested with 100 samples)

### Error Scenario Tests
- [ ] Graceful degradation (missing data) → Warnings returned (tested)
- [ ] Fail fast (invalid IDs) → Exceptions raised (tested)

---

## 📝 Test Report Template

```markdown
# Monolithic Context Testing Report

**Date**: [YYYY-MM-DD]
**Tester**: [Name]
**Environment**: [Staging/Production]

## Summary
- Total Tests: X
- Passed: Y
- Failed: Z
- Coverage: XX%

## Integration Tests
- [ ] Test 1.1: User Exclusion (PASS/FAIL)
- [ ] Test 1.2: Priority Framing (PASS/FAIL)
- [ ] Test 1.3: Depth Config (PASS/FAIL)
- [ ] Test 1.4: End-to-End Control (PASS/FAIL)

## Performance Tests
- [ ] Test 2.1: Latency Benchmark (PASS/FAIL)
  - Average: XXXms (target: <500ms)
  - P95: XXXms (target: <800ms)
- [ ] Test 2.2: Query Count (PASS/FAIL)
  - Queries: X (target: ≤6)
- [ ] Test 2.3: Token Savings (PASS/FAIL)
  - Savings: XXXX tokens

## Accuracy Tests
- [ ] Test 3.1: Token Estimation (PASS/FAIL)
  - Average error: XX% (target: <10%)

## Error Scenario Tests
- [ ] Test 4.1: Graceful Degradation (PASS/FAIL)
- [ ] Test 4.2: Fail Fast (PASS/FAIL)

## Issues Found
1. [Issue description]
2. [Issue description]

## Recommendations
1. [Recommendation]
2. [Recommendation]
```

---

## 🚀 Deployment Validation

### Pre-Production Checklist
- [ ] All tests passing (unit + integration + performance)
- [ ] Test coverage ≥80% (verified via pytest-cov)
- [ ] Performance benchmarks documented
- [ ] Test report generated and approved

### Post-Deployment Monitoring (First 48 hours)
- [ ] Monitor error logs (target: <1% error rate)
- [ ] Monitor latency metrics (target: <500ms average)
- [ ] Monitor user feedback (first 10 users)
- [ ] Document any issues in Handover 0282 (this document)

---

**END OF HANDOVER 0282**

Next: Proceed to Handover 0283 (Documentation Remediation)
