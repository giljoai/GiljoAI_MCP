# Handover: 0765s — Final Remediation (Release-Grade Cleanup)

## Context
This is the FINAL remediation session before merge. The 0765r audit scored 8.35/10 with 36 findings. This session fixes all security issues, runtime crashes, and removes all dead code that a community reviewer would notice. After this, the branch is merge-ready.

Branch: `0760-perfect-score`
Tests baseline: 1453 passed, 0 skipped, 0 failed

---

## PRIORITY 1: Security Fixes (non-negotiable)

### S-1: Cross-Tenant Slash Command Bypass [CRITICAL]
- **File:** `api/endpoints/slash_commands.py:26,69`
- **Bug:** `SlashCommandRequest` accepts user-supplied `tenant_key`. Handler uses `request.tenant_key` instead of `current_user.tenant_key`.
- **Fix:** Replace `request.tenant_key` with `current_user.tenant_key` in both handler functions. Remove `tenant_key` field from `SlashCommandRequest` schema if it exists there.

### S-2: WebSocket Subscribe Tenant Bypass [HIGH]
- **File:** `api/app.py:548-560`, `api/auth_utils.py:280`
- **Bug:** Subscribe handler only resolves tenant_key for `entity_type == "project"`. For agent/message entities, tenant_key stays None and `check_subscription_permission()` returns True.
- **Fix:** Resolve tenant_key for ALL entity types by looking up the entity's owning project/tenant. If tenant can't be resolved, deny the subscription.

## PRIORITY 2: Runtime Crash Fixes

### H-2: git.py TypeError
- **File:** `api/endpoints/git.py:131`
- **Bug:** `current_user['username']` — User is an ORM object, not a dict.
- **Fix:** Change to `current_user.username`

### H-3: auth.py Pydantic ValidationError
- **File:** `api/endpoints/auth.py:756-765`
- **Bug:** `RegisterUserResponse` constructor receives `full_name` and `is_active` fields not in model definition. Pydantic v2 rejects extra fields.
- **Fix:** Either add those fields to the response model or remove them from the constructor call.

### H-1: git.py Wrong Auth Dependency
- **File:** `api/endpoints/git.py:14,48,105,142`
- **Bug:** Uses `get_current_user` instead of `get_current_active_user`. Deactivated users can modify git settings.
- **Fix:** Replace with `get_current_active_user` in all 4 endpoint signatures.

## PRIORITY 3: Dead Backend Methods (~1,100 lines)

Delete these 24 verified-dead methods (all have zero references per 0765r audit):

| File | Method | ~Lines |
|------|--------|--------|
| `json_context_builder.py` | Entire `JSONContextBuilder` class | 248 |
| `tools/agent_coordination.py` | `get_agent_status` | 136 |
| `services/message_service.py` | `acknowledge_message` | 110 |
| `services/agent_job_manager.py` | `update_agent_status` | 82 |
| `services/agent_job_manager.py` | `update_agent_progress` | 60 |
| `services/project_service.py` | `switch_project` | 55 |
| `services/product_service.py` | `update_quality_standards` | ~55 |
| `models/agents.py` | `Job` + `AgentInteraction` models | 68 |
| `context_management/manager.py` | `delete_product_context` | 15 |
| `context_management/manager.py` | `create_condensed_mission` | 17 |
| `repositories/context_repository.py` | `get_summary_by_id` | 19 |
| `repositories/vision_document_repository.py` | `get_by_type`, `set_active_status`, `update_display_order` | 69 |
| `tenant.py` | `batch_validate_keys`, `export_tenant_metadata`, `register_test_tenant`, `clear_cache` | 45 |
| `services/task_service.py` | `assign_task`, `complete_task`, `can_modify_task` | 58 |
| `database.py` | `get_tenant_filter`, `with_tenant` | 19 |
| `auth_manager.py` | `_get_client_ip` | 25 |

**CRITICAL**: Verify each method truly has zero references using grep before deletion. The 0725 audit had 75% false positives. Do NOT blindly trust this list.

## PRIORITY 4: Dead Test Infrastructure (~2,500 lines)

- Delete `tests/benchmark_tools.py` (~261 lines)
- Delete `tests/mock_websocket_server.py` (if exists and dead)
- Delete `tests/unit/test_tool_accessor.py` (empty placeholder)
- Delete dead smoke/ directory contents (if gutted/empty)
- Delete 11 standalone runner scripts with broken imports (verify each is not invoked by CI — check for references in any Makefile, tox.ini, CI config, or scripts/)
- Clean 22 dead imports across test files
- Remove `tests/setup_test_report.json` artifact

## PRIORITY 5: Dead Frontend Exports (33 dead store exports)

Remove dead exports from these stores (verify each has zero imports before removal):
- `agents.js`: 7 dead (currentAgent, healthData, fetchAgent, createAgent, fetchAgentHealth, assignJob, updateAgentStatus)
- `messages.js`: 1 dead (currentMessage)
- `projects.js`: 2 dead (activeProjects, completeProject)
- `settings.js`: 3 dead (saveSettings, updateSetting, resetSettings)
- `tasks.js`: 3 dead (fetchTask, changeTaskStatus, fetchTaskSummary)
- `notifications.js`: 3 dead (agentHealthNotifications, removeNotification, clearAll)
- `products.js`: 4 dead (productMetrics, productCount, setCurrentProduct, initializeFromStorage)
- `systemStore.js`: 1 dead (notificationCount)
- `websocket.js`: 1 dead (subscriptionsCount)
- Plus 5 dead utility/service exports (CLI_TOOL_COLORS, errorMessages default, api.js re-exports, ConfigService class, __resetWebsocketEventRouterForTests)

## PRIORITY 6: Remove Unused SCSS Tokens

### `frontend/src/styles/design-tokens.scss`
Remove all SCSS variables that have zero consumers. The design system lives in JavaScript (agentColors.js, statusConfig.js, Vuetify theme config). Keep ONLY tokens that are actually imported/used by other SCSS files or Vue components.

To find what's actually used: `grep -r` each `$variable-name` across `frontend/src/`. If zero hits outside the definition file, delete it.

### `frontend/src/styles/agent-colors.scss`
Same approach — remove CSS custom properties that are never referenced. Keep only the 3 that are consumed (`--agent-orchestrator-primary`, `--status-waiting`, `--status-blocked`).

## Commit Strategy
- Commit 1: `security(0765s): Fix cross-tenant slash command bypass + WebSocket subscribe + 3 crash bugs`
- Commit 2: `cleanup(0765s): Delete dead backend methods (~1,100 lines)`
- Commit 3: `cleanup(0765s): Delete dead test infrastructure (~2,500 lines)`
- Commit 4: `cleanup(0765s): Remove dead frontend exports + unused SCSS tokens`

## Verification After Each Commit
- `python -m pytest tests/ -x -q --tb=short` — 1453 passed, 0 skipped
- `python -m ruff check src/ api/` — 0 issues
- `npm run build` (in frontend/) — builds clean

## What NOT to Fix (out of scope)
- mcp_http.py being 1,098 lines (pre-existing, handler registry pattern)
- 56 test markdown files (process documentation, harmless)
- 3 console.logs behind debug flags
- 2 v-html warnings (legitimate template rendering)
- statistics.py hardcoded None metrics (pre-existing)
- database_setup.py post-setup access (setup-only endpoints, acceptable)

---

## Chain Execution Instructions

### Step 1: Read Chain Log
Read `prompts/0765_chain/chain_log.json` — verify 0765r audit is complete.

### Step 2: Mark Session Started
Update 0765s: `"status": "in_progress", "started_at": "<timestamp>"`

### Step 3: Execute Tasks
Use subagents to preserve context budget:

| Task | Subagent Type | What to Delegate |
|------|---------------|-----------------|
| Security fixes (S-1, S-2, H-1, H-2, H-3) | `backend-tester` | Fix and verify no regressions |
| Dead backend methods | `deep-researcher` | Verify zero refs then delete |
| Dead test infrastructure | `backend-tester` | Delete files, verify tests pass |
| Dead frontend exports + SCSS | `frontend-tester` | Remove dead exports, remove unused tokens |

### Step 4: Update Chain Log
Set 0765s to `complete` with full results.

### Step 5: Commit and Done
Do NOT spawn another terminal. Do NOT run another audit. Report completion via chain log.
