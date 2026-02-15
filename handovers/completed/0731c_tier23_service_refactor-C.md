# Handover 0731c: Tier 2+3 Service Refactoring (52+ methods)

**Handover ID:** 0731c
**Series:** 0731 Typed Service Returns (Part 3/4)
**Phase:** Tier 2+3 Service Refactoring
**Priority:** P1 - HIGH
**Estimated Effort:** 6-10 hours
**Status:** BLOCKED (needs 0731b)
**Branch:** `feature/0731-typed-service-returns`
**Dependencies:** 0731b (Tier 1 services must be refactored)
**Blocks:** 0731d

---

## 1. Mission & Context

### What We're Doing
Refactor the remaining 11 services to replace `dict[str, Any]` returns with typed returns and exception-based error handling. After 0731b completed Tier 1 (OrgService, UserService, ProductService), this phase handles everything else.

### Services in Scope

**Tier 2 (Higher Impact):**

| Service | File | Dict Wrappers | Priority |
|---------|------|---------------|----------|
| ProjectService | `src/giljo_mcp/services/project_service.py` | 25 | HIGH |
| OrchestrationService | `src/giljo_mcp/services/orchestration_service.py` | 16 | HIGH |
| TaskService | `src/giljo_mcp/services/task_service.py` | 13 | HIGH |
| AuthService | `src/giljo_mcp/services/auth_service.py` | 9 | MEDIUM |
| MessageService | `src/giljo_mcp/services/message_service.py` | 8 | MEDIUM |

**Tier 3 (Lower Impact):**

| Service | File | Dict Wrappers | Priority |
|---------|------|---------------|----------|
| TemplateService | `src/giljo_mcp/services/template_service.py` | 4 | LOW |
| AgentJobManager | `src/giljo_mcp/services/agent_job_manager.py` | varies | MEDIUM |
| SettingsService | `src/giljo_mcp/services/settings_service.py` | 2 | LOW |
| ConfigService | `src/giljo_mcp/services/config_service.py` | 2 | LOW |
| VisionSummarizer | `src/giljo_mcp/services/vision_summarizer.py` | 2 | LOW |
| ConsolidationService | `src/giljo_mcp/services/consolidation_service.py` | 1 | LOW |

### Same Transformation Pattern as 0731b
See 0731b handover for the full pattern reference (Rule 1-8). The same rules apply here.

---

## 2. What Will Change

### Modified Files (11 service files)
- `src/giljo_mcp/services/project_service.py`
- `src/giljo_mcp/services/orchestration_service.py`
- `src/giljo_mcp/services/task_service.py`
- `src/giljo_mcp/services/auth_service.py`
- `src/giljo_mcp/services/message_service.py`
- `src/giljo_mcp/services/template_service.py`
- `src/giljo_mcp/services/agent_job_manager.py`
- `src/giljo_mcp/services/settings_service.py`
- `src/giljo_mcp/services/config_service.py`
- `src/giljo_mcp/services/vision_summarizer.py`
- `src/giljo_mcp/services/consolidation_service.py`

### Modified Test Files
- Corresponding test files for each service

---

## 3. Embedded Coding Principles

You MUST follow these principles:

1. **Use Serena MCP tools** for code exploration - find all callers before changing signatures
2. **Follow TDD**: Update tests FIRST to expect new return types, then modify service code
3. **One service at a time**: Complete and commit each service individually
4. **Multi-tenant isolation**: Preserve `tenant_key` filtering - do not change query logic
5. **Exception imports**: Use existing exceptions from `src/giljo_mcp/exceptions.py`
6. **AuthService special handling**: Auth methods often have side effects (token creation, session management) - be extra careful with error paths
7. **OrchestrationService special handling**: Orchestration methods coordinate multiple services - verify cascading effects
8. **Clean code**: Remove ALL dict wrapper construction code
9. **Use subagents**: One `tdd-implementor` per service (or per 2-3 small services)

---

## 4. Implementation Details

### Processing Order (recommended)

Start with the highest-impact services and work down:

1. **ProjectService** (25 wrappers) - Largest count in this tier
2. **OrchestrationService** (16 wrappers) - Complex coordination logic
3. **TaskService** (13 wrappers) - Important for MCP tools
4. **AuthService** (9 wrappers) - Security-sensitive, be careful
5. **MessageService** (8 wrappers) - Straightforward
6. **Remaining 6 services** - Can be batched (small count each)

### AuthService Special Considerations

AuthService methods often return tokens, session data, or user info in dicts. Be careful:
- `login()` may return `{"success": True, "token": "...", "user": {...}}`
- Create an `AuthResult` model if needed (or check if 0731a created one)
- NEVER expose raw password hashes in return types
- Preserve rate limiting and security logging

### OrchestrationService Special Considerations

Orchestration methods coordinate multiple services:
- Methods may call ProductService, ProjectService, TaskService
- After 0731b, those services already return typed values
- Update orchestration methods to handle typed returns instead of dicts
- Context tracking methods (`get_context_usage`, `update_context`) may need special handling

---

## 5. TDD Workflow

Same as 0731b. For each service method:
1. Update test to expect typed return / exception
2. Run test - it should FAIL
3. Modify service code
4. Run test - it should PASS
5. Run ALL service tests

---

## 6. Serena MCP Usage Requirements

Same as 0731b. REQUIRED for:
1. Getting current method signatures
2. Finding ALL callers before changing return types
3. Checking cross-service dependencies (OrchestrationService calls other services)
4. Efficient method body replacement

---

## 7. Testing Requirements

After each service:
```bash
pytest tests/services/test_<service_name>.py -v
```

After all services:
```bash
pytest tests/services/ -v  # All service tests
```

---

## 8. Definition of Done

- [ ] All 11 remaining services refactored with typed returns
- [ ] Tests updated FIRST (TDD) for each service
- [ ] All service tests passing
- [ ] Serena MCP tools used for caller discovery
- [ ] No regressions in existing tests
- [ ] Each service (or batch) committed separately
- [ ] Chain log updated with full list of endpoint impacts
- [ ] STOPPED - awaiting 0731d execution via chain

---

## 9. Git Commit Standards

Commit after each service or logical batch:

```bash
git commit -m "refactor(0731c): ProjectService typed returns - remove 25 dict wrappers

Replace dict[str, Any] returns with typed model returns and exception-based
error handling. Tests updated first per TDD workflow.

```

For small services, batch commits are acceptable:
```bash
git commit -m "refactor(0731c): Tier 3 services typed returns - Settings, Config, Vision, Consolidation

Remove remaining dict wrappers from 4 small services (7 total instances).

```

---

## 10. STOP Boundary

## CRITICAL: STOP AFTER COMPLETION

**DO NOT PROCEED TO 0731d WITHOUT COMPLETING THE CHAIN STEPS BELOW.**

This phase is complete when ALL service files have typed returns (zero `dict[str, Any]` return annotations remaining).
Update the chain log, then spawn the next terminal.

---

## Chain Execution Instructions

### Step 1: Read Chain Log
Read `prompts/0731_chain/chain_log.json`. Check 0731a and 0731b `notes_for_next`.
Verify 0731b status is `complete`. If not, STOP and report.
Mark your session as `"status": "in_progress", "started_at": "<timestamp>"`.

### Step 2: Execute Handover Tasks

**CRITICAL: Use Task tool to spawn subagents for this work. Do NOT do all work directly.**

Recommended: Spawn agents for batches:

Batch 1 - High-impact Tier 2:
```
Task(subagent_type="tdd-implementor", prompt="Refactor ProjectService in src/giljo_mcp/services/project_service.py. Replace all 25 dict[str, Any] returns with typed returns. Follow TDD: update tests first. Use Serena MCP to find callers. Use exceptions from src/giljo_mcp/exceptions.py. Use DeleteResult from src/giljo_mcp/schemas/service_responses.py. Reference: docs/architecture/service_response_models.md. Commit when done.")
```

Then similarly for OrchestrationService, TaskService, AuthService, MessageService.

Batch 2 - Small Tier 3 (can be one agent for all 6):
```
Task(subagent_type="tdd-implementor", prompt="Refactor 6 small services: TemplateService(4 wrappers), AgentJobManager, SettingsService(2), ConfigService(2), VisionSummarizer(2), ConsolidationService(1). Replace dict[str, Any] returns with typed returns. Follow TDD. Commit as one batch.")
```

### Step 3: Verify Zero Dict Wrappers Remain
```bash
grep -r "-> dict\[str, Any\]" src/giljo_mcp/services/ | wc -l
# Should be 0
```

### Step 4: Update Chain Log
Update `prompts/0731_chain/chain_log.json`:
- `tasks_completed`: Services refactored with counts
- `notes_for_next`: Full list of endpoint files that need updating (from all caller analyses across 0731b+c)
- `summary`: 2-3 sentences
- `status`: "complete"

### Step 5: Spawn Next Terminal
**Use Bash tool to EXECUTE this command (Don't Just Print It!):**

```powershell
powershell.exe -Command "Start-Process wt -ArgumentList '--title \"0731d - API Endpoints + Validation\" --tabColor \"#FF9800\" -d \"F:\GiljoAI_MCP\" cmd /k claude --dangerously-skip-permissions \"Execute handover 0731d. READ F:\GiljoAI_MCP\handovers\0731d_api_endpoints_validation.md for full instructions. Check chain log at F:\GiljoAI_MCP\prompts\0731_chain\chain_log.json first. Branch: feature/0731-typed-service-returns. Use Task subagents for the work.\"' -Verb RunAs"
```

**CRITICAL: DO NOT SPAWN DUPLICATE TERMINALS!**
