#!/bin/bash

# Create 0612 - Templates API
cat > 0612_templates_api_validation.md << 'EOF'
# Handover 0612: Templates API Validation

**Phase**: 2 | **Tool**: CCW | **Agent**: api-tester | **Duration**: 4h
**Parallel Group**: B (APIs) | **Depends On**: 0603-0608

## Endpoints (13 total)
1-5: CRUD, 6-7: Reset/Diff, 8-9: Preview/History, 10-13: Restore/Archive

**Test Coverage**: 50+ tests - CRUD, template resolution cascade, cache invalidation, Monaco editor integration

**Success**: All 13 endpoints tested, 401/403 verified, 50+ tests pass, PR `0612-templates-api-tests`

**Deliverable**: `tests/api/test_templates_api.py`

**Document Control**: 0612 | 2025-11-14
EOF

# Create 0613 - Agent Jobs API
cat > 0613_agent_jobs_api_validation.md << 'EOF'
# Handover 0613: Agent Jobs API Validation

**Phase**: 2 | **Tool**: CCW | **Agent**: api-tester | **Duration**: 4h
**Parallel Group**: B (APIs) | **Depends On**: 0603-0608

## Endpoints (13 total)
1-5: CRUD, 6-8: Acknowledge/Complete/Fail, 9-10: Messages, 11-13: Succession/Status/Cancel

**Test Coverage**: 50+ tests - Job lifecycle, WebSocket events, succession triggers, AgentJobManager integration

**Success**: All 13 endpoints tested, WebSocket verified, 50+ tests pass, PR `0613-agent-jobs-api-tests`

**Deliverable**: `tests/api/test_agent_jobs_api.py`

**Document Control**: 0613 | 2025-11-14
EOF

# Create 0614 - Settings API
cat > 0614_settings_api_validation.md << 'EOF'
# Handover 0614: Settings API Validation

**Phase**: 2 | **Tool**: CCW | **Agent**: api-tester | **Duration**: 3h
**Parallel Group**: B (APIs) | **Depends On**: 0603-0608

## Endpoints (7 total)
1-2: User settings (get/update), 3-7: Admin settings tabs (Network/Database/Integrations/Users/System)

**Test Coverage**: 30+ tests - User preferences, admin settings, multi-tab validation

**Success**: All 7 endpoints tested, admin-only verified, 30+ tests pass, PR `0614-settings-api-tests`

**Deliverable**: `tests/api/test_settings_api.py`

**Document Control**: 0614 | 2025-11-14
EOF

# Create 0615 - Users API
cat > 0615_users_api_validation.md << 'EOF'
# Handover 0615: Users API Validation

**Phase**: 2 | **Tool**: CCW | **Agent**: api-tester | **Duration**: 3h
**Parallel Group**: B (APIs) | **Depends On**: 0603-0608

## Endpoints (6 total)
1-5: CRUD, 6: Password reset (PIN recovery system)

**Test Coverage**: 28+ tests - User management, password reset PIN, role validation, multi-tenant

**Success**: All 6 endpoints tested, PIN reset verified, 28+ tests pass, PR `0615-users-api-tests`

**Deliverable**: `tests/api/test_users_api.py`

**Document Control**: 0615 | 2025-11-14
EOF

# Create 0616 - Slash Commands API
cat > 0616_slash_commands_api_validation.md << 'EOF'
# Handover 0616: Slash Commands API Validation

**Phase**: 2 | **Tool**: CCW | **Agent**: api-tester | **Duration**: 2h
**Parallel Group**: B (APIs) | **Depends On**: 0603-0608

## Endpoints (4 total)
1: POST /api/v1/slash-commands/execute - Execute slash command
2: POST /api/v1/slash-commands/gil_handover - Trigger succession
3: GET /api/v1/slash-commands/list - List available commands
4: GET /api/v1/slash-commands/{name}/help - Get command help

**Test Coverage**: 18+ tests - Command execution, /gil_handover trigger, command discovery

**Success**: All 4 endpoints tested, succession trigger verified, 18+ tests pass, PR `0616-slash-commands-api-tests`

**Deliverable**: `tests/api/test_slash_commands_api.py`

**Document Control**: 0616 | 2025-11-14
EOF

# Create 0617 - Messages API
cat > 0617_messages_api_validation.md << 'EOF'
# Handover 0617: Messages API Validation

**Phase**: 2 | **Tool**: CCW | **Agent**: api-tester | **Duration**: 3h
**Parallel Group**: B (APIs) | **Depends On**: 0603-0608

## Endpoints (5 total)
1-3: Send/Get/List messages, 4: Mark read, 5: JSONB search

**Test Coverage**: 25+ tests - JSONB handling, agent-to-agent messaging, queue operations

**Success**: All 5 endpoints tested, JSONB search verified, 25+ tests pass, PR `0617-messages-api-tests`

**Deliverable**: `tests/api/test_messages_api.py`

**Document Control**: 0617 | 2025-11-14
EOF

# Create 0618 - Health/Status API
cat > 0618_health_status_api_validation.md << 'EOF'
# Handover 0618: Health/Status API Validation

**Phase**: 2 | **Tool**: CCW | **Agent**: api-tester | **Duration**: 2h
**Parallel Group**: B (APIs) | **Depends On**: 0603-0608

## Endpoints (5 total)
1: GET /api/v1/health - Health check
2: GET /api/v1/status - System status
3: GET /api/v1/metrics - Metrics
4: GET /api/v1/database/status - DB status
5: GET /api/v1/version - Version info

**Test Coverage**: 20+ tests - Health checks, database connectivity, metrics collection

**Success**: All 5 endpoints tested, DB status verified, 20+ tests pass, PR `0618-health-status-api-tests`

**Deliverable**: `tests/api/test_health_status_api.py`

**Document Control**: 0618 | 2025-11-14
EOF

echo "Phase 2 API validation files created"
