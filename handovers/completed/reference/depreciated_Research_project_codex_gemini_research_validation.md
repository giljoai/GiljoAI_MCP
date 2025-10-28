# Handover 0068: Codex & Gemini CLI Integration Research Validation

**Date**: 2025-10-27
**Status**: Research Complete - Implementation Planning
**Related**: Handovers 0066 (Codex), 0067 (Gemini), 0060 (MCP Tool Exposure)

---

## Executive Summary

Research validation of Codex CLI and Gemini CLI integration capabilities reveals that:

1. **Both tools have full MCP support** (native HTTP transport) as of 2025
2. **Current GiljoAI HTTP MCP architecture is optimal** for passive orchestration platform
3. **Handovers 0066/0067 proposed approaches are overcomplicated** - simpler paths exist
4. **Key gap**: Configuration automation, not architectural changes needed

### Critical Insight

GiljoAI is a **passive communication platform**, not an autonomous orchestrator. Users (developers) maintain control while the platform bridges CLI coding tools to project/product management roles. The platform facilitates coordination but does NOT run agents autonomously.

---

## 1. Research File Validation

### CODEX_SUBAGENTS_COMMUNICATION.md
**Status**: ✅ **Accurate**

**Validated Claims**:
- Codex CLI supports MCP server and client modes (confirmed 2025 docs)
- Three communication patterns: MCP server, MCP client, process-level (verified)
- Uses AGENTS.md files for agent configuration (standard format)
- JSON-RPC over stdio and HTTP transport (MCP specification)

**Key Features Confirmed**:
```bash
# Codex as MCP Client
codex mcp add --transport http giljo-mcp http://SERVER:7272/mcp --header "X-API-Key: KEY"

# Config file approach
# ~/.codex/config.toml
[mcp_servers.giljoai]
url = "https://SERVER:7272/mcp"
bearer_token_env_var = "GILJO_API_KEY"
```

### GEMINI_SUBAGENTS_COMMUNICATION.md
**Status**: ⚠️ **Partially Outdated**

**Outdated Claims**:
- "No official Gemini CLI from Google" - **Incorrect**: Released June 2025, 1M+ users by October 2025
- JavaScript SDK required - **Partially true**: SDK exists but CLI has native MCP via extensions

**Validated Capabilities** (2025):
```bash
# Gemini CLI with MCP
gemini mcp add --transport http giljo-mcp http://SERVER:7272/mcp --header "X-API-Key: KEY"

# Headless mode for automation
gemini --headless --output-format json "Task description"
```

---

## 2. Current GiljoAI Implementation Analysis

### What We Have (Already Working)

#### A. HTTP MCP Endpoint
**File**: `api/endpoints/mcp_http.py`

**Features**:
- Clean JSON-RPC 2.0 implementation
- Stateful sessions with PostgreSQL
- X-API-Key authentication
- Multi-tenant isolation
- Works with Claude Code, Codex CLI, Gemini CLI

**Architecture Strength**: Universal protocol, single endpoint serves all tools

#### B. Configuration Generator
**File**: `api/endpoints/ai_tools.py`

**Current State**:
```python
AIToolInfo(
    id="codex",
    name="Codex CLI",
    supported=False,  # ❌ Should be True
    config_format="command"
),
AIToolInfo(
    id="gemini",
    name="Gemini CLI",
    supported=False,  # ❌ Should be True
    config_format="command"
)
```

**Generates Commands**:
```bash
codex mcp add --transport http giljo-mcp http://IP:7272/mcp --header "X-API-Key: KEY"
gemini mcp add --transport http giljo-mcp http://IP:7272/mcp --header "X-API-Key: KEY"
```

#### C. UI Wizard
**File**: `frontend/src/components/AiToolConfigWizard.vue`

**Current UX**: Shows command, user copies and pastes into terminal

**Gap**: Marked as "coming soon" when actually functional now

### What's Missing

1. **Status flags**: Codex/Gemini marked unsupported when they work via MCP
2. **Config file export**: No TOML generation for direct Codex config file
3. **Documentation**: Usage patterns not documented for non-Claude tools

---

## 3. Multi-Agent Orchestration Capabilities

### Claude Code (Baseline for Comparison)

**Native Subagent Architecture**:
- Task tool spawns subagents
- Up to 10 parallel agents
- Structured message passing
- Independent context windows
- **Limitation**: Subagents cannot spawn subagents

**Performance**: 90.2% better than single-agent on research tasks

### Codex CLI (2025 Capabilities)

**MCP Client Support**:
```toml
[mcp_servers.giljoai]
url = "https://YOUR_HOST:7272/mcp"
bearer_token_env_var = "GILJO_API_KEY"
tool_timeout_sec = 90
```

**Process-Level Execution**:
```bash
# Non-interactive mode for automation
codex exec --profile implementer --json "Complete task X"
```

**AGENTS.md Hierarchies**:
- Global: `~/.codex/AGENTS.md`
- Project: `/project/AGENTS.md`
- Feature: `/project/feature/AGENTS.md`
- Templates merge top-down

**Real-Time Monitoring**:
- JSONL streaming output
- Programmatic progress tracking
- Better than Claude's "black box" approach

### Gemini CLI (2025 Capabilities)

**Headless Mode**:
```bash
gemini --headless --output-format json "Task description"
```

**Agent Spawning**:
```bash
gemini -e coder-agent -p "You are coder-agent. Task: ..."
```

**YOLO Mode**: Auto-approval for autonomous operation

**Orchestrator-Worker Pattern**:
- Strategist agent coordinates
- Specialist agents execute
- Identity via explicit prompts

---

## 4. Comparison Matrix

| Capability | Claude Code | GiljoAI + Codex | GiljoAI + Gemini |
|------------|------------|-----------------|------------------|
| **Native subagents** | ✅ Task tool | ⚠️ Via exec | ⚠️ Via spawn |
| **Parallel execution** | ✅ 10 max | ✅ Unlimited | ✅ Unlimited |
| **Cross-tool orchestration** | ❌ No | ✅ Yes | ✅ Yes |
| **Progress monitoring** | ❌ Black box | ✅ Via MCP | ✅ Via MCP |
| **Inter-agent comms** | ✅ Internal | ✅ MCP jobs/msgs | ✅ MCP jobs/msgs |
| **Multi-tenant** | ❌ No | ✅ Yes | ✅ Yes |
| **MCP integration** | ✅ Native | ✅ Native | ⚠️ Via extensions |
| **User control** | ⚠️ Limited | ✅ Full | ✅ Full |

---

## 5. Architecture Assessment

### Current Approach: Passive Communication Platform

**GiljoAI's Role**:
```
User → Creates product/project → Defines vision → Platform generates mission
      ↓
Platform creates job in database with mission details
      ↓
User opens CLI tool (Claude/Codex/Gemini) → Tool connects to MCP → Pulls job
      ↓
Developer monitors progress → CLI tool works → Reports back via MCP
      ↓
User marks completed in dashboard
```

**Key Characteristic**: Platform is **facilitator**, not orchestrator

### Why This Architecture is Optimal

**Strengths**:
1. ✅ **Developer maintains control** - No autonomous agents running
2. ✅ **Universal protocol** - Works with any MCP-compatible tool
3. ✅ **Multi-tenant isolation** - Enterprise-ready security
4. ✅ **Cross-tool coordination** - Unique capability (Claude + Codex + Gemini)
5. ✅ **No GPU/LLM required** - Server doesn't need AI processing
6. ✅ **Passive state management** - Job queue + message queue

**vs Autonomous Orchestrators**:
- Autonomous systems run agents in background (requires GPU/LLM)
- GiljoAI hands off to external CLI tools (user's compute)
- User stays in control loop

---

## 6. Handover 0066/0067 Assessment

### Proposed Approach (Overcomplicated)

**Handover 0066 (Codex)**:
- Python wrapper with OpenAI API integration
- Direct API calls to GPT-5-Codex
- Custom process management
- Complexity: High

**Handover 0067 (Gemini)**:
- Node.js bridge service
- WebSocket coordination
- Process lifecycle management
- Complexity: Very High

### Why Not Recommended

1. **Reinvents MCP**: Duplicates what MCP protocol already provides
2. **Maintenance burden**: Tool-specific code for each AI provider
3. **Bypasses strengths**: Ignores native MCP support both tools now have
4. **Requires compute**: Would need server-side LLM processing
5. **Loses user control**: Moves toward autonomous (counter to vision)

---

## 7. Recommended Enhancements

### Tier 1: Status & Configuration (30 minutes)

**Goal**: Enable developers to connect tools more easily

**Changes**:
1. Mark Codex/Gemini as `supported=True` in `ai_tools.py`
2. Add TOML config file export for Codex
3. Remove "coming soon" warnings from UI
4. Update documentation

**User Experience**:
```
Before: Copy command → Paste in terminal → Run
After:  Export config → Add to ~/.codex/config.toml → Tools auto-connect
```

**Outcome**: Direct MCP connection without manual commands

### Tier 2: Configuration Templates (2-3 hours)

**Goal**: Provide ready-to-use config files

**New Features**:
1. Generate `codex-config.toml` with MCP server pre-configured
2. Generate `gemini-startup.sh` with connection instructions
3. Add download buttons in UI for config files
4. Include API key, server URL, timeout settings

**User Experience**:
```
1. Click "Download Codex Config"
2. Copy to ~/.codex/config.toml
3. Launch Codex → MCP tools appear automatically
```

### Tier 3: Documentation & Examples (1 day)

**Goal**: Help developers understand workflow

**Documentation**:
1. Multi-tool workflow guide
2. Example projects using Claude + Codex + Gemini
3. Best practices for agent coordination
4. Troubleshooting guide

**Location**: `docs/MULTI_TOOL_ORCHESTRATION.md`

---

## 8. What "Automation" Means for GiljoAI

### Misconception to Avoid

**NOT THIS** (Autonomous orchestration requiring GPU/LLM):
```
Platform runs autonomous agents → Agents spawn subagents →
Platform coordinates via internal AI → All happens in background
```

**THIS** (Passive facilitation with reduced friction):
```
Platform stores job specs → Developer connects CLI tool →
Tool pulls job via MCP → Developer monitors → Reports back
```

### Reducing Friction != Running Agents

**Current Friction Points**:
1. Manual command copy-paste (Tier 1 fixes this)
2. Typing mission details to CLI (MCP job system fixes this)
3. Switching between tools and dashboard (Already solved)
4. Tracking progress across tools (Message queue solves this)

**GiljoAI's Value Proposition**:
- Developer describes vision in detail (product/project setup)
- Platform structures it into missions
- CLI tools pull missions automatically
- Developer stays in control loop
- Platform bridges product manager → project manager → coder roles

### What We Don't Need

1. ❌ Local LLM for orchestration (not passive platform's role)
2. ❌ Autonomous agent spawning (breaks user control)
3. ❌ Background job execution (violates passive architecture)
4. ❌ Complex wrappers (MCP already does this)

### What We Should Add

1. ✅ Config file generation (reduces setup friction)
2. ✅ Direct MCP connection options (fewer manual steps)
3. ✅ Better progress visibility (message queue enhancements)
4. ✅ Mission template improvements (clearer instructions for CLI tools)

---

## 9. Control Mechanisms for Developers

### Current Control Points

**Developer maintains control via**:
1. **Manual CLI launch** - Agents only run when developer starts them
2. **Job acceptance** - CLI tool can refuse/skip jobs
3. **Process termination** - Developer can Ctrl+C anytime
4. **Dashboard monitoring** - Real-time visibility into all activity
5. **Manual completion** - User marks jobs done (platform doesn't auto-complete)

### Headless Mode Clarification

**What "headless" means**:
- CLI tool runs without interactive prompts (not "background daemon")
- Still visible in terminal window
- Still controllable (Ctrl+C works)
- Just auto-approves actions (YOLO mode)

**Example**:
```bash
# Interactive mode (default)
gemini "Write tests"
> "I will create test_auth.py. Proceed? [y/n]"
> User types: y

# Headless mode (YOLO)
gemini --headless --yolo "Write tests"
> Creates test_auth.py immediately
> User can still Ctrl+C to stop
```

**Use Case**: Developer wants CLI tool to execute mission without constant approval prompts

### YOLO Mode Best Practices

**When to use**:
- Well-defined missions (clear scope)
- Trusted agent templates
- Development environments (not production)
- Time-saving for repetitive tasks

**Safety mechanisms**:
- Git integration (easy rollback)
- Confined to project directory
- User monitors in real-time
- Can terminate anytime

---

## 10. Recommendations Summary

### Do Implement

1. **Mark Codex/Gemini as supported** (5 min)
2. **Generate config files for direct MCP connection** (30 min)
3. **Improve mission template clarity** (2 hours)
4. **Document multi-tool workflows** (1 day)

### Don't Implement

1. ❌ **Handover 0066 Python wrapper** (unnecessary complexity)
2. ❌ **Handover 0067 Node.js bridge** (unnecessary complexity)
3. ❌ **Autonomous background agents** (violates passive architecture)
4. ❌ **Server-side LLM orchestration** (not needed for v1-v3)

### Architecture Validated

✅ **Current HTTP MCP approach is optimal** for passive communication platform
✅ **No major refactoring needed** - minor enhancements only
✅ **Developer control preserved** - platform facilitates, doesn't dictate
✅ **Cross-tool coordination** - unique value proposition confirmed

---

## 11. Next Steps

### Immediate (This Week)
1. Update `ai_tools.py` to mark Codex/Gemini supported
2. Add config file export endpoints
3. Update UI to show "Direct Connect" option
4. Test with actual Codex/Gemini CLI tools

### Short-term (Next Sprint)
1. Enhance mission templates with CLI-specific instructions
2. Document multi-tool workflow patterns
3. Create example projects
4. Add progress monitoring enhancements

### Long-term (Future Versions)
1. Agent template library for specific mission types
2. Mission success criteria validation
3. Cross-tool collaboration patterns
4. Advanced telemetry and analytics

---

## Conclusion

Research validates that GiljoAI's **passive communication platform architecture is sound** and requires only minor enhancements (config file generation) rather than major refactoring.

The platform's strength is its **role as facilitator** - bridging product vision to project execution to code implementation - while keeping developers in control. This is the correct architectural choice for a platform that doesn't run autonomous agents.

**Key Takeaway**: We're not building an autonomous orchestrator (which would need GPU/LLM). We're building a coordination platform that hands off to external CLI tools, maintaining developer control while reducing friction.

---

**References**:
- Codex CLI Documentation (2025)
- Gemini CLI Release Notes (June 2025)
- MCP Protocol Specification
- Claude Code Subagent Architecture
- Community orchestration frameworks (CAO, Claude Squad, CCSwarm)
