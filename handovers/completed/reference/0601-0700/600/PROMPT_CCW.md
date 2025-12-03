# CCW Agent Launch Prompt (Cloud Execution with Branches)

**Use this prompt when running agents in Claude Code Web (CCW) for parallel branch development.**

---

## Copy-Paste Prompt Template

```
You are working on Project 600 (Complete System Restoration & Validation) for the GiljoAI MCP codebase.

**Your Handover**: handovers/600/[HANDOVER_NUMBER]_[HANDOVER_NAME].md

**Required Reading** (in this order):
1. handovers/600/AGENT_REFERENCE_GUIDE.md - Read this FIRST for universal project context
2. Your specific handover file - Contains all objectives, tasks, success criteria, validation steps

**Execution Mode**: CCW (Cloud, Branch Development)
- Branch name: [HANDOVER_NUMBER]-[BRANCH_NAME] (create this branch)
- No database access: Mock database/fixtures as needed for tests
- File system: Read/write in branch only
- Git: Create Pull Request when complete (do NOT merge)
- Testing: Use mocked fixtures, pytest without real database

**Your Tasks**:
1. Read AGENT_REFERENCE_GUIDE.md to understand the project
2. Read your handover file completely
3. Create branch: [HANDOVER_NUMBER]-[BRANCH_NAME]
4. Execute all tasks in sequence as specified
5. Create all deliverables (code, tests, docs)
6. Run tests with mocked fixtures (no real DB)
7. Create Pull Request with:
   - Test results in PR description
   - Coverage report snippet
   - List of files created/modified
   - Success criteria checklist

**Quality Standards**:
- Follow all patterns from AGENT_REFERENCE_GUIDE.md
- No placeholders or TODOs
- All tests must pass (with mocks)
- Production-grade code only
- Comprehensive error handling

**Important**:
- Do NOT merge the PR - it will be merged locally after all parallel branches complete
- Include test run output in PR description
- Document any assumptions made due to lack of DB access

Execute the handover specification. Do not ask for permission - the handover file contains complete instructions. use subagents
```

---

## Usage Instructions

1. **Copy the prompt above**
2. **Replace placeholders**:
   - `[HANDOVER_NUMBER]` → e.g., `0603`, `0604`, `0609`, etc.
   - `[HANDOVER_NAME]` → e.g., `product_service_validation`, `projects_api_validation`, etc.
   - `[BRANCH_NAME]` → e.g., `product-service-tests`, `projects-api-tests`, etc.
3. **Paste into Claude Code Web (CCW)**
4. **Agent will create branch and execute**

---

## Examples

### Example 1: Handover 0603 (ProductService Validation)
```
You are working on Project 600 (Complete System Restoration & Validation) for the GiljoAI MCP codebase.

**Your Handover**: handovers/600/0603_product_service_validation.md

**Required Reading** (in this order):
1. handovers/600/AGENT_REFERENCE_GUIDE.md - Read this FIRST for universal project context
2. Your specific handover file - Contains all objectives, tasks, success criteria, validation steps

**Execution Mode**: CCW (Cloud, Branch Development)
- Branch name: 0603-product-service-tests (create this branch)
- No database access: Mock database/fixtures as needed for tests
- File system: Read/write in branch only
- Git: Create Pull Request when complete (do NOT merge)
- Testing: Use mocked fixtures, pytest without real database

**Your Tasks**:
1. Read AGENT_REFERENCE_GUIDE.md to understand the project
2. Read your handover file completely
3. Create branch: 0603-product-service-tests
4. Execute all tasks in sequence as specified
5. Create all deliverables (code, tests, docs)
6. Run tests with mocked fixtures (no real DB)
7. Create Pull Request with:
   - Test results in PR description
   - Coverage report snippet
   - List of files created/modified
   - Success criteria checklist

**Quality Standards**:
- Follow all patterns from AGENT_REFERENCE_GUIDE.md
- No placeholders or TODOs
- All tests must pass (with mocks)
- Production-grade code only
- Comprehensive error handling

**Important**:
- Do NOT merge the PR - it will be merged locally after all parallel branches complete
- Include test run output in PR description
- Document any assumptions made due to lack of DB access

Execute the handover specification. Do not ask for permission - the handover file contains complete instructions. use subagents
```

### Example 2: Handover 0609 (Products API Validation)
```
You are working on Project 600 (Complete System Restoration & Validation) for the GiljoAI MCP codebase.

**Your Handover**: handovers/600/0609_products_api_validation.md

**Required Reading** (in this order):
1. handovers/600/AGENT_REFERENCE_GUIDE.md - Read this FIRST for universal project context
2. Your specific handover file - Contains all objectives, tasks, success criteria, validation steps

**Execution Mode**: CCW (Cloud, Branch Development)
- Branch name: 0609-products-api-tests (create this branch)
- No database access: Mock database/fixtures as needed for tests
- File system: Read/write in branch only
- Git: Create Pull Request when complete (do NOT merge)
- Testing: Use mocked fixtures, pytest without real database

**Your Tasks**:
1. Read AGENT_REFERENCE_GUIDE.md to understand the project
2. Read your handover file completely
3. Create branch: 0609-products-api-tests
4. Execute all tasks in sequence as specified
5. Create all deliverables (code, tests, docs)
6. Run tests with mocked fixtures (no real DB)
7. Create Pull Request with:
   - Test results in PR description
   - Coverage report snippet
   - List of files created/modified
   - Success criteria checklist

**Quality Standards**:
- Follow all patterns from AGENT_REFERENCE_GUIDE.md
- No placeholders or TODOs
- All tests must pass (with mocks)
- Production-grade code only
- Comprehensive error handling

**Important**:
- Do NOT merge the PR - it will be merged locally after all parallel branches complete
- Include test run output in PR description
- Document any assumptions made due to lack of DB access

Execute the handover specification. Do not ask for permission - the handover file contains complete instructions. use subagents
```

---

## CCW Handovers List (21 Parallel Branches)

### Phase 1 - Services (6 parallel branches)
- **0603**-product-service-tests: 0603_product_service_validation.md
- **0604**-project-service-tests: 0604_project_service_validation.md
- **0605**-task-service-tests: 0605_task_service_validation.md
- **0606**-message-service-tests: 0606_message_service_validation.md
- **0607**-context-service-tests: 0607_context_service_validation.md
- **0608**-orchestration-service-tests: 0608_orchestration_service_validation.md

### Phase 2 - APIs (10 parallel branches)
- **0609**-products-api-tests: 0609_products_api_validation.md
- **0610**-projects-api-tests: 0610_projects_api_validation.md
- **0611**-tasks-api-tests: 0611_tasks_api_validation.md
- **0612**-templates-api-tests: 0612_templates_api_validation.md
- **0613**-agent-jobs-api-tests: 0613_agent_jobs_api_validation.md
- **0614**-settings-api-tests: 0614_settings_api_validation.md
- **0615**-users-api-tests: 0615_users_api_validation.md
- **0616**-slash-commands-api-tests: 0616_slash_commands_api_validation.md
- **0617**-messages-api-tests: 0617_messages_api_validation.md
- **0618**-health-status-api-tests: 0618_health_status_api_validation.md

### Phase 6 - Documentation (5 parallel branches)
- **0627**-update-claude-md: 0627_update_claude_md.md
- **0628**-developer-guides: 0628_create_developer_guides.md
- **0629**-user-guides: 0629_create_user_guides.md
- **0630**-completion-report: 0630_create_completion_report.md
- **0631**-readme-cleanup: 0631_update_readme_cleanup.md

---

## Merge Protocol (After Parallel Branches Complete)

### After Phase 1 (6 branches):
```bash
# Locally, merge all 6 branches
git fetch origin
git merge origin/0603-product-service-tests
git merge origin/0604-project-service-tests
git merge origin/0605-task-service-tests
git merge origin/0606-message-service-tests
git merge origin/0607-context-service-tests
git merge origin/0608-orchestration-service-tests

# Run tests to verify
pytest tests/unit/test_*_service.py tests/integration/test_*_service.py -v

# If all pass, push to master
git push origin master
```

### After Phase 2 (10 branches):
```bash
# Locally, merge all 10 branches
git fetch origin
for branch in 0609-products-api-tests 0610-projects-api-tests 0611-tasks-api-tests 0612-templates-api-tests 0613-agent-jobs-api-tests 0614-settings-api-tests 0615-users-api-tests 0616-slash-commands-api-tests 0617-messages-api-tests 0618-health-status-api-tests; do
  git merge origin/$branch
done

# Run API tests to verify
pytest tests/api/ -v

# If all pass, push to master
git push origin master
```

### After Phase 6 (5 branches):
```bash
# Locally, merge all 5 branches
git fetch origin
git merge origin/0627-update-claude-md
git merge origin/0628-developer-guides
git merge origin/0629-user-guides
git merge origin/0630-completion-report
git merge origin/0631-readme-cleanup

# Verify no broken links
# (manual check or run link checker)

# Push to master
git push origin master
```

---

**Document Control**:
- **File**: PROMPT_CCW.md
- **Purpose**: Standard prompt template for CCW cloud agent execution with branch development
- **Usage**: Copy-paste for each CCW handover, replace placeholders
- **Created**: 2025-11-14
