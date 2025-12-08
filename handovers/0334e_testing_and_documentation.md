# Handover 0334e: Testing & Documentation - Claude Code Plugin Integration

**Date:** 2025-12-07
**From Agent:** Documentation Manager (Orchestrator Session)
**To Agent:** TDD Implementor + Backend Integration Tester
**Priority:** Medium
**Estimated Complexity:** 4-6 hours
**Status:** Ready for Implementation
**Parent Handover:** 0334 (Claude Code Plugin - Agent Template Bridge)

---

## Executive Summary

This handover completes the Claude Code Plugin implementation (0334 series) by providing comprehensive end-to-end integration tests, user documentation, and troubleshooting guides. The goal is to ensure users can successfully install, configure, and use the plugin while maintaining multi-tenant isolation and handling edge cases gracefully.

**Expected Outcome:** A fully tested and documented plugin system with clear user guides, integration tests validating the complete workflow, and troubleshooting documentation for common issues.

---

## Context and Background

### How We Got Here

The 0334 series implements a Claude Code Plugin that eliminates local `.md` template file management:

- **0334a**: Backend API endpoint (`/api/v1/agent-templates/plugin`)
- **0334b**: Plugin package (manifest, provider, README)
- **0334c**: User profile setup UI (My Settings → Integrations)
- **0334d**: Staging prompt integration (environment pre-flight checks)
- **0334e** (THIS HANDOVER): Testing and documentation

### Why Comprehensive Testing Is Critical

1. **Multi-Tenant Isolation**: Must verify tenant_key filtering prevents cross-tenant data leaks
2. **Plugin Lifecycle**: Installation, configuration, and agent discovery must work seamlessly
3. **Conflict Detection**: Local `.md` files can override plugin agents - users must be warned
4. **Real-Time Updates**: Template changes in UI must reflect immediately on next plugin fetch
5. **Error Handling**: Network failures, invalid keys, and rate limiting must fail gracefully

### Documentation Goals

1. **User Guide**: Step-by-step plugin setup with verification steps
2. **Troubleshooting**: Common issues and resolutions
3. **Integration Tests**: Automated validation of the complete workflow
4. **Manual Testing Checklist**: QA guide for human verification

---

## The Complete User Flow (What We're Testing)

```
┌─────────────────────────────────────────────────────────────────┐
│ PHASE 1: ONE-TIME PLUGIN SETUP                                 │
├─────────────────────────────────────────────────────────────────┤
│ 1. User logs into GiljoAI dashboard                            │
│ 2. Navigate to My Settings → Integrations → Claude Code Setup  │
│ 3. Copy install command (includes tenant_key and server URL)   │
│ 4. Open Claude Code terminal                                   │
│ 5. Paste and run install command                               │
│ 6. Plugin installed permanently                                │
│ 7. Verify: Run /plugins list → see "giljoai-agents"           │
│ 8. Verify: Run /agents → see managed templates                │
└─────────────────────────────────────────────────────────────────┘

┌─────────────────────────────────────────────────────────────────┐
│ PHASE 2: PER-PROJECT STAGING (EVERY PROJECT)                   │
├─────────────────────────────────────────────────────────────────┤
│ 9. User creates project in GiljoAI                             │
│ 10. Toggle "Claude Code CLI" mode on Launch tab                │
│ 11. Click "Stage Project" and copy prompt                      │
│ 12. Paste in Claude Code                                       │
│ 13. Orchestrator runs environment pre-flight checks:           │
│     - Check for local .md file conflicts                       │
│     - Verify plugin installed                                  │
│     - List available agents from /agents                       │
│ 14. Orchestrator spawns agents using Task tool                 │
│ 15. Plugin fetches agent instructions from GiljoAI server      │
│ 16. Agents execute with fresh template data                    │
└─────────────────────────────────────────────────────────────────┘
```

---

## Implementation Requirements

### 1. End-to-End Integration Tests

**File:** `tests/integration/test_claude_code_plugin_e2e.py`

**Purpose:** Automated validation of the complete plugin workflow from API to user experience.

**Test Scenarios:**

#### Scenario 1: Plugin API Accessibility

```python
@pytest.mark.asyncio
async def test_plugin_api_returns_templates_for_valid_tenant(
    db_session: AsyncSession,
    test_client: TestClient
):
    """
    INTEGRATION: Plugin API returns templates for valid tenant_key

    GIVEN: A tenant with active agent templates
    WHEN: Calling /api/v1/agent-templates/plugin?tenant_key=tk_xxx
    THEN: Response is 200 OK
    AND: Response includes templates array
    AND: Each template has required fields (name, description, full_instructions)
    AND: Only active templates are returned
    """
    # ARRANGE
    tenant_key = "test_tenant_plugin"

    # Create product
    product = Product(
        id="prod-plugin-test",
        name="Plugin Test Product",
        tenant_key=tenant_key
    )
    db_session.add(product)

    # Create active template
    active_template = AgentTemplate(
        id="tmpl-active",
        product_id=product.id,
        tenant_key=tenant_key,
        name="implementer",
        role="Code Implementation Specialist",
        description="Implements features following TDD",
        full_instructions="You are an implementer agent. Your role is to...",
        meta_data={"capabilities": ["code_generation", "testing"]},
        is_active=True
    )
    db_session.add(active_template)

    # Create inactive template (should NOT appear)
    inactive_template = AgentTemplate(
        id="tmpl-inactive",
        product_id=product.id,
        tenant_key=tenant_key,
        name="legacy-agent",
        role="Legacy Agent",
        description="Deprecated agent",
        full_instructions="...",
        is_active=False
    )
    db_session.add(inactive_template)

    await db_session.commit()

    # ACT
    response = test_client.get(
        f"/api/v1/agent-templates/plugin?tenant_key={tenant_key}"
    )

    # ASSERT
    assert response.status_code == 200
    data = response.json()

    assert "templates" in data
    assert "tenant_key" in data
    assert "count" in data
    assert "cache_ttl" in data

    assert data["tenant_key"] == tenant_key
    assert data["count"] == 1  # Only active template
    assert data["cache_ttl"] == 300  # 5 minutes

    templates = data["templates"]
    assert len(templates) == 1

    template = templates[0]
    assert template["name"] == "implementer"
    assert template["role"] == "Code Implementation Specialist"
    assert template["description"] == "Implements features following TDD"
    assert "You are an implementer agent" in template["full_instructions"]
    assert template["capabilities"] == ["code_generation", "testing"]
    assert template["is_active"] is True
```

#### Scenario 2: Multi-Tenant Isolation

```python
@pytest.mark.asyncio
async def test_plugin_api_enforces_tenant_isolation(
    db_session: AsyncSession,
    test_client: TestClient
):
    """
    INTEGRATION: Plugin API enforces strict multi-tenant isolation

    GIVEN: Two tenants (A and B) each with their own templates
    WHEN: Tenant A queries the plugin API
    THEN: Only tenant A templates are returned
    AND: Tenant B templates are NOT visible
    AND: Same for tenant B query (only sees their own)
    """
    # ARRANGE
    tenant_a = "tenant_alpha"
    tenant_b = "tenant_beta"

    # Create products for both tenants
    product_a = Product(id="prod-a", name="Product A", tenant_key=tenant_a)
    product_b = Product(id="prod-b", name="Product B", tenant_key=tenant_b)
    db_session.add_all([product_a, product_b])

    # Create templates for tenant A
    template_a1 = AgentTemplate(
        id="tmpl-a1",
        product_id=product_a.id,
        tenant_key=tenant_a,
        name="implementer-a",
        role="Tenant A Implementer",
        description="Tenant A implementation specialist",
        full_instructions="Tenant A instructions",
        is_active=True
    )
    db_session.add(template_a1)

    # Create templates for tenant B
    template_b1 = AgentTemplate(
        id="tmpl-b1",
        product_id=product_b.id,
        tenant_key=tenant_b,
        name="implementer-b",
        role="Tenant B Implementer",
        description="Tenant B implementation specialist",
        full_instructions="Tenant B instructions",
        is_active=True
    )
    db_session.add(template_b1)

    await db_session.commit()

    # ACT - Query as tenant A
    response_a = test_client.get(
        f"/api/v1/agent-templates/plugin?tenant_key={tenant_a}"
    )

    # ASSERT - Tenant A only sees their templates
    assert response_a.status_code == 200
    data_a = response_a.json()
    assert data_a["count"] == 1
    assert data_a["templates"][0]["name"] == "implementer-a"
    assert "Tenant A" in data_a["templates"][0]["full_instructions"]

    # ACT - Query as tenant B
    response_b = test_client.get(
        f"/api/v1/agent-templates/plugin?tenant_key={tenant_b}"
    )

    # ASSERT - Tenant B only sees their templates
    assert response_b.status_code == 200
    data_b = response_b.json()
    assert data_b["count"] == 1
    assert data_b["templates"][0]["name"] == "implementer-b"
    assert "Tenant B" in data_b["templates"][0]["full_instructions"]

    # ASSERT - No cross-tenant contamination
    assert data_a["templates"] != data_b["templates"]
```

#### Scenario 3: Plugin Install Flow Simulation

```python
@pytest.mark.asyncio
async def test_plugin_install_command_generation(
    db_session: AsyncSession,
    test_client: TestClient,
    test_user
):
    """
    INTEGRATION: UI generates correct plugin install command

    GIVEN: A logged-in user with tenant_key
    WHEN: User requests plugin setup info from UI endpoint
    THEN: Response includes properly formatted install command
    AND: Command includes correct server_url
    AND: Command includes user's tenant_key
    AND: Command is copy-paste ready
    """
    # ARRANGE
    tenant_key = test_user.tenant_key

    # ACT - Request plugin setup info (this endpoint should be created in 0334c)
    response = test_client.get(
        "/api/v1/settings/claude-code-setup",
        headers={"Authorization": f"Bearer {test_user.api_key}"}
    )

    # ASSERT
    assert response.status_code == 200
    data = response.json()

    assert "install_command" in data
    assert "server_url" in data
    assert "tenant_key" in data

    install_cmd = data["install_command"]

    # Verify command format
    assert "claude plugins install giljoai-agents" in install_cmd
    assert f"--config server_url={data['server_url']}" in install_cmd
    assert f"--config tenant_key={tenant_key}" in install_cmd

    # Verify server URL is accessible
    assert data["server_url"].startswith("http")
    assert data["tenant_key"] == tenant_key
```

#### Scenario 4: Staging Prompt Generation (CLI Mode)

```python
@pytest.mark.asyncio
async def test_staging_prompt_includes_environment_checks(
    db_session: AsyncSession,
    test_user
):
    """
    INTEGRATION: CLI mode staging prompt includes pre-flight checks

    GIVEN: A project configured for Claude Code CLI mode
    WHEN: Generating staging prompt
    THEN: Prompt includes environment pre-flight checks
    AND: Prompt includes instructions to verify plugin installed
    AND: Prompt includes conflict detection for local .md files
    AND: Prompt includes /agents verification step
    """
    # ARRANGE
    project = Project(
        id="proj-cli-test",
        name="CLI Mode Test Project",
        product_id=test_user.active_product_id,
        tenant_key=test_user.tenant_key,
        is_claude_code_mode=True  # CLI mode enabled
    )
    db_session.add(project)
    await db_session.commit()

    # ACT
    generator = ThinClientPromptGenerator()
    prompt = await generator.generate_staging_prompt(
        project_id=project.id,
        tenant_key=test_user.tenant_key,
        db_session=db_session
    )

    # ASSERT - Environment checks present
    assert "ENVIRONMENT PRE-FLIGHT" in prompt
    assert "CHECK FOR LOCAL OVERRIDES" in prompt
    assert "~/.claude/agents/*.md" in prompt
    assert ".claude/agents/*.md" in prompt

    # ASSERT - Plugin verification
    assert "VERIFY PLUGIN INSTALLED" in prompt
    assert "/plugins list" in prompt
    assert "giljoai-agents" in prompt

    # ASSERT - Agent listing
    assert "LIST AVAILABLE AGENTS" in prompt
    assert "/agents" in prompt

    # ASSERT - Proceed conditions
    assert "PROCEED ONLY when:" in prompt
    assert "No local .md overrides exist" in prompt
    assert "Plugin is installed" in prompt
    assert "/agents shows your templates" in prompt
```

#### Scenario 5: Agent Template Changes Reflect Immediately

```python
@pytest.mark.asyncio
async def test_template_changes_reflect_in_plugin_immediately(
    db_session: AsyncSession,
    test_client: TestClient
):
    """
    INTEGRATION: Template updates are visible immediately via plugin API

    GIVEN: An existing agent template
    WHEN: Template is updated via UI
    AND: Plugin API is queried again
    THEN: Updated template data is returned
    AND: Changes are visible without server restart
    """
    # ARRANGE
    tenant_key = "test_tenant_updates"

    product = Product(id="prod-updates", name="Update Test", tenant_key=tenant_key)
    db_session.add(product)

    template = AgentTemplate(
        id="tmpl-update-test",
        product_id=product.id,
        tenant_key=tenant_key,
        name="implementer",
        role="Original Role",
        description="Original description",
        full_instructions="Original instructions v1",
        is_active=True
    )
    db_session.add(template)
    await db_session.commit()

    # ACT - Initial fetch
    response1 = test_client.get(
        f"/api/v1/agent-templates/plugin?tenant_key={tenant_key}"
    )
    data1 = response1.json()

    # ASSERT - Original data
    assert data1["templates"][0]["description"] == "Original description"
    assert "v1" in data1["templates"][0]["full_instructions"]

    # ACT - Update template
    template.description = "Updated description after edit"
    template.full_instructions = "Updated instructions v2"
    await db_session.commit()

    # ACT - Fetch again
    response2 = test_client.get(
        f"/api/v1/agent-templates/plugin?tenant_key={tenant_key}"
    )
    data2 = response2.json()

    # ASSERT - Changes reflected
    assert data2["templates"][0]["description"] == "Updated description after edit"
    assert "v2" in data2["templates"][0]["full_instructions"]
    assert "v1" not in data2["templates"][0]["full_instructions"]
```

#### Scenario 6: Error Handling

```python
@pytest.mark.asyncio
async def test_plugin_api_error_handling(
    test_client: TestClient
):
    """
    INTEGRATION: Plugin API handles errors gracefully

    GIVEN: Various invalid request scenarios
    WHEN: Making requests with invalid parameters
    THEN: Appropriate HTTP status codes returned
    AND: Error messages are clear and actionable
    """
    # TEST 1: Missing tenant_key returns 400
    response_no_key = test_client.get("/api/v1/agent-templates/plugin")
    assert response_no_key.status_code == 400
    assert "tenant_key" in response_no_key.json()["detail"].lower()

    # TEST 2: Invalid tenant_key returns empty array (not error)
    response_invalid = test_client.get(
        "/api/v1/agent-templates/plugin?tenant_key=invalid_tenant_xyz"
    )
    assert response_invalid.status_code == 200
    data_invalid = response_invalid.json()
    assert data_invalid["count"] == 0
    assert data_invalid["templates"] == []

    # TEST 3: Rate limiting (requires configured rate limiter)
    # Make 100 requests in rapid succession
    tenant_key = "rate_limit_test"
    responses = []
    for _ in range(100):
        r = test_client.get(
            f"/api/v1/agent-templates/plugin?tenant_key={tenant_key}"
        )
        responses.append(r.status_code)

    # Should eventually hit 429 (if rate limiting enabled)
    # Note: This test may need adjustment based on actual rate limit config
    assert 429 in responses or all(r == 200 for r in responses)
```

---

### 2. Manual Testing Checklist

**Purpose:** Human verification of the complete workflow, including UI interactions and Claude Code terminal operations.

**File:** `docs/testing/claude_code_plugin_manual_test_checklist.md`

```markdown
# Claude Code Plugin - Manual Testing Checklist

**Tester Name:** ___________________
**Date:** ___________________
**GiljoAI Version:** ___________________
**Claude Code Version:** ___________________

---

## PHASE 1: Plugin Setup via UI

### Test 1.1: Navigate to Setup Page
- [ ] Log into GiljoAI dashboard
- [ ] Click avatar (top-right corner)
- [ ] Select "My Settings"
- [ ] Find "Integrations" tab
- [ ] Locate "Claude Code CLI Setup" section

**Expected Result:** Setup section is visible with install command

---

### Test 1.2: Install Command Format
- [ ] Verify install command is displayed
- [ ] Command contains "claude plugins install giljoai-agents"
- [ ] Command includes "--config server_url=..."
- [ ] Command includes "--config tenant_key=tk_..."
- [ ] Server URL matches current GiljoAI instance
- [ ] Tenant key is unique to your user

**Expected Result:** Command is well-formatted and includes correct values

---

### Test 1.3: Copy Install Command
- [ ] Click "Copy" button next to install command
- [ ] Paste into notepad to verify clipboard
- [ ] Command pastes correctly

**Expected Result:** Clipboard contains full install command

---

### Test 1.4: Connection Test Button (Optional)
- [ ] Click "Test Connection" button
- [ ] Wait for response
- [ ] Verify success indicator appears

**Expected Result:** Connection test succeeds

---

## PHASE 2: Plugin Installation (Claude Code Terminal)

### Test 2.1: Install Plugin
- [ ] Open terminal where Claude Code is available
- [ ] Paste install command
- [ ] Press Enter and wait for completion
- [ ] Verify no error messages

**Expected Result:** Plugin installs successfully

---

### Test 2.2: Verify Plugin Installed
- [ ] Run command: `/plugins list`
- [ ] Scroll through plugin list
- [ ] Find "giljoai-agents"

**Expected Result:** giljoai-agents appears in plugin list

---

### Test 2.3: List Available Agents
- [ ] Run command: `/agents`
- [ ] Review agent list
- [ ] Verify your GiljoAI templates appear

**Expected Result:** Your managed agents are listed (e.g., implementer, tester, documenter)

---

## PHASE 3: Conflict Detection

### Test 3.1: Create Local Override File
- [ ] Create file: `~/.claude/agents/test-override.md`
- [ ] Add content: "# Test Override\nThis is a test."
- [ ] Save file

---

### Test 3.2: Stage Project with Conflict
- [ ] In GiljoAI, create a test project
- [ ] Enable "Claude Code CLI" mode on Launch tab
- [ ] Click "Stage Project"
- [ ] Copy staging prompt
- [ ] Paste in Claude Code

**Expected Result:** Orchestrator detects local file and displays warning:
```
WARNING: User agents found at ~/.claude/agents/test-override.md
```

---

### Test 3.3: Remove Local Override
- [ ] Delete `~/.claude/agents/test-override.md`
- [ ] Stage project again
- [ ] Verify no warning appears

**Expected Result:** No conflict warning; environment is clean

---

## PHASE 4: Agent Spawning

### Test 4.1: Stage Project Successfully
- [ ] Ensure no local .md files exist
- [ ] Create project in GiljoAI with tasks
- [ ] Enable CLI mode
- [ ] Stage project and copy prompt
- [ ] Paste in Claude Code

**Expected Result:** Orchestrator runs environment checks and proceeds

---

### Test 4.2: Spawn Agent via Task Tool
- [ ] Orchestrator spawns agent (e.g., "@implementer")
- [ ] Verify agent starts in background
- [ ] Check GiljoAI dashboard → Jobs tab
- [ ] Verify agent appears in job list

**Expected Result:** Agent spawned and visible in dashboard

---

### Test 4.3: Agent Receives Correct Instructions
- [ ] Wait for agent to complete initial setup
- [ ] In GiljoAI, click agent job to view details
- [ ] Check agent's mission/instructions
- [ ] Verify instructions match template in UI

**Expected Result:** Agent has full template instructions from database

---

## PHASE 5: Real-Time Updates

### Test 5.1: Update Template in UI
- [ ] Go to My Settings → Agent Templates
- [ ] Edit an existing template (e.g., change description)
- [ ] Save changes

---

### Test 5.2: Verify Update Reflects in Plugin
- [ ] In Claude Code terminal, run: `/agents`
- [ ] Find the updated template
- [ ] Verify description shows new value

**Expected Result:** Changes appear immediately (no cache delay)

---

## PHASE 6: Multi-Tenant Isolation (Requires Second Account)

### Test 6.1: Create Second User Account
- [ ] Log out of GiljoAI
- [ ] Register new user account
- [ ] Create a product and agent template
- [ ] Note the agent template name

---

### Test 6.2: Install Plugin as Second User
- [ ] Copy install command for second user
- [ ] Install plugin in separate Claude Code instance (or uninstall/reinstall)

---

### Test 6.3: Verify Isolation
- [ ] Run `/agents` as second user
- [ ] Verify ONLY second user's templates appear
- [ ] Verify first user's templates do NOT appear

**Expected Result:** Complete tenant isolation; no cross-tenant visibility

---

## PHASE 7: Error Scenarios

### Test 7.1: Invalid Tenant Key
- [ ] Manually edit plugin config to use invalid tenant_key
- [ ] Run `/agents`

**Expected Result:** Empty agent list (or error message)

---

### Test 7.2: Server Unreachable
- [ ] Stop GiljoAI server
- [ ] Run `/agents`

**Expected Result:** Error message about connection failure

---

### Test 7.3: Restart Server
- [ ] Restart GiljoAI server
- [ ] Run `/agents` again

**Expected Result:** Agents load successfully after reconnection

---

## Sign-Off

**All Tests Passed:** [ ] YES  [ ] NO

**Issues Found:**
- ___________________________________________________________
- ___________________________________________________________
- ___________________________________________________________

**Tester Signature:** ___________________  **Date:** ___________
```

---

### 3. User Documentation

**File:** `docs/user_guides/claude_code_plugin_setup.md`

**Purpose:** Comprehensive guide for end users to install and use the Claude Code plugin.

```markdown
# Claude Code Plugin Setup Guide

**For:** GiljoAI Users
**Goal:** Install and configure the Claude Code plugin for dynamic agent management
**Difficulty:** Beginner
**Time to Complete:** 5-10 minutes

---

## Table of Contents

1. [Introduction](#introduction)
2. [Prerequisites](#prerequisites)
3. [Installation](#installation)
4. [Verification](#verification)
5. [Using Managed Agents](#using-managed-agents)
6. [Troubleshooting](#troubleshooting)
7. [FAQ](#faq)

---

## Introduction

### What is the Claude Code Plugin?

The GiljoAI Claude Code plugin enables **dynamic agent management** directly from your GiljoAI dashboard. Instead of manually maintaining `.md` template files on your local machine, your agents are fetched in real-time from the GiljoAI server.

### Why Use the Plugin?

**Benefits:**
- **Always Up-to-Date**: Template changes in the UI immediately reflect in Claude Code
- **No Manual Syncing**: No need to export/import template files
- **Multi-Tenant Safe**: Your agents are isolated from other users
- **Centralized Management**: Manage all templates from the dashboard

**Traditional Workflow (Without Plugin):**
```
1. Create template in GiljoAI
2. Export template to .md file
3. Copy file to ~/.claude/agents/
4. Repeat for every template change
```

**Plugin Workflow:**
```
1. Create template in GiljoAI
2. Done! Plugin fetches automatically
```

---

## Prerequisites

Before starting, ensure you have:

1. **GiljoAI MCP Server** running and accessible (e.g., http://localhost:7272)
2. **Claude Code CLI** installed on your machine
3. **A GiljoAI account** with agent templates configured
4. **Network access** from your machine to the GiljoAI server

**Check Claude Code Version:**
```bash
claude --version
```
Minimum required version: 1.0.0 (adjust based on actual requirements)

---

## Installation

### Step 1: Get Your Install Command

1. Log into the **GiljoAI dashboard**
2. Click your **avatar** (top-right corner)
3. Select **"My Settings"**
4. Navigate to the **"Integrations"** tab
5. Find the **"Claude Code CLI Setup"** section

You'll see a command like this:
```bash
claude plugins install giljoai-agents \
  --config server_url=http://localhost:7272 \
  --config tenant_key=tk_your_unique_key_here
```

6. Click the **"Copy"** button to copy the full command

**Important Notes:**
- The `server_url` must match your GiljoAI server location
- The `tenant_key` is unique to your user (do not share)
- If your server uses HTTPS, the URL will start with `https://`

---

### Step 2: Install the Plugin

1. Open your **terminal** (Command Prompt, PowerShell, or Terminal app)
2. Paste the install command
3. Press **Enter**
4. Wait for installation to complete (typically 5-15 seconds)

**Example Output:**
```
Installing plugin: giljoai-agents
Fetching from registry...
Configuring plugin with:
  - server_url: http://localhost:7272
  - tenant_key: tk_abc123xyz
Installation complete!
```

---

### Step 3: Verify Installation

**Test 1: Check Plugin is Listed**
```bash
/plugins list
```

You should see `giljoai-agents` in the list:
```
Installed Plugins:
- giljoai-agents (v1.0.0) - Dynamic agent templates from GiljoAI MCP Server
- [other plugins...]
```

**Test 2: Check Agents Are Available**
```bash
/agents
```

You should see your GiljoAI templates:
```
Available Agents:
- implementer - Code Implementation Specialist
- tester - Quality Assurance Specialist
- documenter - Documentation Manager
- [your other templates...]
```

**If agents don't appear:** See [Troubleshooting](#troubleshooting) section

---

## Verification

### Optional: Test Connection from UI

Back in the GiljoAI dashboard:

1. Go to **My Settings → Integrations → Claude Code CLI Setup**
2. Click the **"Test Connection"** button
3. Wait for response

**Success Indicator:**
- Green checkmark appears
- Message: "Plugin connection verified"

**Failure Indicator:**
- Red X appears
- Message: "Cannot reach plugin" or "Plugin not installed"

**If test fails:** Verify plugin is actually installed using `/plugins list`

---

## Using Managed Agents

### Creating Projects with CLI Mode

1. In GiljoAI dashboard, create a **new project**
2. On the **Launch** tab, toggle **"Claude Code CLI"** mode **ON**
3. Click **"Stage Project"**
4. Copy the generated staging prompt
5. Paste into Claude Code terminal

### Environment Pre-Flight Checks

When you paste the staging prompt, the orchestrator automatically:

1. **Checks for local file conflicts** (warns if `.md` files exist locally)
2. **Verifies plugin installed** (confirms `/plugins list` shows giljoai-agents)
3. **Lists available agents** (runs `/agents` to show your templates)

**If any check fails, the orchestrator will pause and provide instructions.**

### Spawning Agents

The orchestrator spawns agents using the **Task tool**:

```python
# Orchestrator spawns implementer agent
Task(
    subagent_type="implementer",  # Must match name from /agents exactly
    prompt="Build the authentication module with JWT support"
)
```

**Key Points:**
- `subagent_type` must match agent name from `/agents` exactly (case-sensitive)
- Agent receives full instructions automatically from plugin
- Agent appears in GiljoAI dashboard → Jobs tab
- Progress is tracked in real-time

---

## Troubleshooting

### Issue 1: Plugin Not Installing

**Symptoms:**
- Installation command hangs or fails
- Error: "Plugin not found in registry"

**Solutions:**

1. **Check Claude Code version:**
   ```bash
   claude --version
   ```
   Ensure version is 1.0.0 or higher

2. **Check network connectivity to GiljoAI server:**
   ```bash
   curl http://localhost:7272/health
   ```
   Should return: `{"status": "healthy"}`

3. **Verify server URL is correct:**
   - If GiljoAI runs on different port, update URL
   - Example: `http://192.168.1.100:7272` for network server

4. **Try uninstalling and reinstalling:**
   ```bash
   /plugins uninstall giljoai-agents
   # Then run install command again
   ```

---

### Issue 2: Agents Not Appearing

**Symptoms:**
- `/agents` returns empty list
- `/agents` returns error

**Solutions:**

1. **Verify tenant_key is correct:**
   - Go to GiljoAI → My Settings → Integrations
   - Compare tenant_key in install command with plugin config

2. **Check if templates are active:**
   - Go to GiljoAI → My Settings → Agent Templates
   - Ensure templates have "Active" status (toggle ON)

3. **Test API directly:**
   ```bash
   curl "http://localhost:7272/api/v1/agent-templates/plugin?tenant_key=tk_your_key"
   ```
   Should return JSON with your templates

4. **Check plugin configuration:**
   ```bash
   /plugins config giljoai-agents
   ```
   Verify server_url and tenant_key are set correctly

---

### Issue 3: Local Files Overriding Plugin

**Symptoms:**
- Staging prompt warns about local files
- Agent uses old instructions instead of updated ones

**Explanation:**
Claude Code has a priority hierarchy:
1. Project agents (`.claude/agents/`) - **HIGHEST**
2. User agents (`~/.claude/agents/`) - **MEDIUM**
3. Plugin agents (from giljoai-agents) - **LOWEST**

**Solution:**

1. **Check for local files:**
   ```bash
   ls ~/.claude/agents/*.md
   ls .claude/agents/*.md
   ```

2. **Remove conflicting files:**
   - Delete or rename local `.md` files
   - Or move them to a backup directory

3. **Verify cleanup:**
   - Stage project again
   - Warning should disappear

**When to keep local files:**
- If you intentionally want to override a specific agent
- For testing modified templates before committing to database

---

### Issue 4: "Connection Refused" Error

**Symptoms:**
- `/agents` returns network error
- Error: "ECONNREFUSED" or "Cannot reach server"

**Solutions:**

1. **Verify GiljoAI server is running:**
   ```bash
   # Windows (PowerShell)
   Get-Process | Where-Object {$_.ProcessName -like "*python*"}

   # Linux/Mac
   ps aux | grep python
   ```

2. **Check server logs:**
   - Look for errors in `logs/server.log`
   - Verify server started successfully

3. **Test server health endpoint:**
   ```bash
   curl http://localhost:7272/health
   ```

4. **Check firewall settings:**
   - Ensure port 7272 (or your custom port) is open
   - Allow Python through firewall

---

### Issue 5: Rate Limiting Errors

**Symptoms:**
- Error: "429 Too Many Requests"
- Plugin stops responding after many requests

**Explanation:**
The plugin API has rate limiting to prevent abuse (default: 100 requests per 5 minutes).

**Solutions:**

1. **Wait 5 minutes and try again**
2. **Contact admin** if limit is too restrictive for your workflow
3. **Check for loops** in code that might be fetching agents repeatedly

---

## FAQ

### Q1: Do I need to reinstall the plugin for each project?

**A:** No! The plugin is installed **once per user** on your machine. It works for all GiljoAI projects automatically.

---

### Q2: What happens if I update a template in the UI?

**A:** Changes are reflected **immediately** on the next `/agents` call. The plugin fetches fresh data from the database every time.

---

### Q3: Can I use both local `.md` files and the plugin?

**A:** Yes, but local files take priority. If you have a local `implementer.md` file, it will override the plugin's `implementer` template. Remove local files to use plugin templates.

---

### Q4: Is my tenant_key secret?

**A:** The tenant_key is a **partition identifier**, not a secret credential. It identifies which data belongs to you but doesn't grant authentication. Keep it private but it's less sensitive than a password.

---

### Q5: Can other users see my templates?

**A:** No. Multi-tenant isolation ensures each tenant_key only sees their own templates. Other users cannot access your data.

---

### Q6: What if my GiljoAI server URL changes?

**A:** Reinstall the plugin with the new URL:
```bash
/plugins uninstall giljoai-agents
# Then copy new install command from UI and run
```

---

### Q7: Can I use the plugin offline?

**A:** No. The plugin requires network access to the GiljoAI server to fetch templates. Offline mode is not supported.

---

### Q8: How do I uninstall the plugin?

**A:**
```bash
/plugins uninstall giljoai-agents
```

To reinstall later, just run the install command from the UI again.

---

### Q9: Does the plugin work with self-hosted GiljoAI?

**A:** Yes! Just ensure:
- The `server_url` in the install command matches your server's address
- Your machine can reach the server over the network
- Firewalls allow the connection

---

### Q10: What happens if the server is down when I run `/agents`?

**A:** You'll see an error message:
```
Error: Cannot connect to GiljoAI server at http://localhost:7272
Please verify the server is running and accessible.
```

Start the server and try again.

---

## Related Documentation

- [Claude Code CLI Mode Guide](./claude_code_cli_mode.md)
- [Agent Template Management](./agent_template_management.md)
- [Multi-Tenant Isolation](../architecture/multi_tenant_isolation.md)

---

## Support

**Need help?**
- Check [Troubleshooting](#troubleshooting) section above
- Review [FAQ](#faq)
- Contact your GiljoAI administrator
- File a bug report in the issue tracker

---

**Last Updated:** 2025-12-07
**Plugin Version:** 1.0.0
**GiljoAI Version:** v3.2+
```

---

## Files Summary

### New Files Created

1. **`tests/integration/test_claude_code_plugin_e2e.py`**
   - End-to-end integration tests (6 scenarios)
   - Multi-tenant isolation validation
   - Error handling verification

2. **`docs/user_guides/claude_code_plugin_setup.md`**
   - Complete installation guide
   - Step-by-step verification
   - Troubleshooting section
   - Comprehensive FAQ

3. **`docs/testing/claude_code_plugin_manual_test_checklist.md`**
   - Manual QA checklist
   - 7 test phases
   - Sign-off template

### Modified Files

None (this handover only adds new test and documentation files)

---

## Success Criteria Checklist

Before marking this handover complete, verify:

### Integration Tests
- [ ] All 6 test scenarios pass
- [ ] Multi-tenant isolation validated
- [ ] Error handling covers edge cases
- [ ] Tests run in CI/CD pipeline

### Manual Testing
- [ ] Manual checklist completed by human tester
- [ ] All 7 phases verified
- [ ] Issues documented and resolved

### Documentation
- [ ] User guide is clear and comprehensive
- [ ] Installation steps are accurate
- [ ] Troubleshooting covers common issues
- [ ] FAQ addresses user questions
- [ ] Screenshots added (if applicable)

### End-to-End Workflow
- [ ] User can install plugin from UI command
- [ ] `/plugins list` shows giljoai-agents
- [ ] `/agents` shows user's templates
- [ ] Template updates reflect immediately
- [ ] Multi-tenant isolation enforced
- [ ] Conflict detection warns about local files
- [ ] Staging prompt includes environment checks
- [ ] Agents spawn successfully with correct instructions

---

## Dependencies

This handover depends on:

- **0334a**: Backend API endpoint must be implemented
- **0334b**: Plugin package must be created and published
- **0334c**: User profile setup UI must be functional
- **0334d**: Staging prompt must include environment checks

**Blocking:** This handover CANNOT proceed until 0334a-d are complete.

---

## Definition of Done

The 0334 series (Claude Code Plugin) is **100% complete** when:

1. ✅ Backend API returns templates correctly (0334a)
2. ✅ Plugin can be installed via command (0334b)
3. ✅ UI shows setup section with working test button (0334c)
4. ✅ Staging prompt includes environment checks (0334d)
5. ✅ **All integration tests pass (0334e - THIS HANDOVER)**
6. ✅ **Manual testing checklist completed (0334e - THIS HANDOVER)**
7. ✅ **User guide published (0334e - THIS HANDOVER)**
8. ✅ **Troubleshooting documented (0334e - THIS HANDOVER)**

---

## Rollback Plan

If testing reveals critical issues:

1. **Disable plugin setup UI** via feature flag
2. **Keep existing local template export** working
3. **Document known issues** for users
4. **Plan remediation** in follow-up handover

No database changes required for rollback.

---

## Related Handovers

- **0334**: Claude Code Plugin - Agent Template Bridge (parent)
- **0334a**: Backend API Endpoint
- **0334b**: Plugin Package Creation
- **0334c**: User Profile Setup UI
- **0334d**: Staging Prompt Integration
- **0333**: Staging Prompt Architecture Correction
- **0260**: Claude Code CLI Mode

---

## Estimated Effort Breakdown

| Task | Effort | Notes |
|------|--------|-------|
| Write integration tests (6 scenarios) | 3-4 hours | Complex multi-tenant validation |
| Create manual test checklist | 1 hour | QA documentation |
| Write user guide | 2-3 hours | Comprehensive with troubleshooting |
| Run tests and fix issues | 1-2 hours | Iteration on failing tests |
| **Total** | **4-6 hours** | - |

---

## Implementation Notes for AI Coding Agent

### Testing Framework Setup

```python
# tests/integration/test_claude_code_plugin_e2e.py

import pytest
from fastapi.testclient import TestClient
from sqlalchemy.ext.asyncio import AsyncSession

from api.app import app
from src.giljo_mcp.models import Product, AgentTemplate, Project, User
from src.giljo_mcp.thin_prompt_generator import ThinClientPromptGenerator


@pytest.fixture
def test_client():
    """FastAPI test client fixture"""
    return TestClient(app)


@pytest.fixture
async def test_user(db_session: AsyncSession):
    """Create test user with tenant_key"""
    user = User(
        id="user-test",
        username="test_user",
        tenant_key="test_tenant_e2e",
        active_product_id="prod-test"
    )
    db_session.add(user)
    await db_session.commit()
    return user
```

### Running Tests

```bash
# Run all plugin tests
pytest tests/integration/test_claude_code_plugin_e2e.py -v

# Run specific test scenario
pytest tests/integration/test_claude_code_plugin_e2e.py::test_plugin_api_returns_templates_for_valid_tenant -v

# Run with coverage
pytest tests/integration/test_claude_code_plugin_e2e.py --cov=api.endpoints.agent_templates --cov-report=html
```

### Documentation Location

Place user guide at: `docs/user_guides/claude_code_plugin_setup.md`
Place manual checklist at: `docs/testing/claude_code_plugin_manual_test_checklist.md`

### Verification Commands

After implementation:
1. Run pytest: `pytest tests/integration/test_claude_code_plugin_e2e.py`
2. Review coverage: Open `htmlcov/index.html`
3. Read user guide: Check for clarity and completeness
4. Execute manual checklist: Complete at least once manually

---

**END OF HANDOVER 0334e**
