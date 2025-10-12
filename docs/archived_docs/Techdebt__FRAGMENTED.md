# Technical Debt and Future Enhancements - Consolidated

> **Note**: This document consolidates three separate tech debt documents into a single source of truth.
> Last consolidated: October 5, 2025

---

# Technical Debt Report - September 2025

## Executive Summary

GiljoAI-MCP is positioned to replace AKE-MCP with an improved UI, easier installation, and better theming. However, several advertised features are currently unimplemented "config flags" - settings that exist in configuration files but have no actual code behind them.

**Release Status:**

- ✅ **Developer Profile**: Ready for release
- ⚠️ **Team Profile**: 85% ready - needs WebSocket completion
- ❌ **Enterprise Profile**: Not ready - many features unimplemented
- ❌ **Research Profile**: Not ready - most features are placeholders

## 1. Comparison with AKE-MCP

### What GiljoAI-MCP Should Provide (per requirements):

- ✅ Multi-agent orchestration
- ✅ MCP protocol support
- ✅ Database persistence (PostgreSQL/PostgreSQL)
- ✅ Project/Agent/Message/Task management
- ✅ Easy installer with dependency management
- ⚠️ Real-time updates via WebSocket (partial)
- ⚠️ Web dashboard UI (partial - Vue 3 app exists but incomplete)
- ✅ Better theming matching GiljoAI design guidelines
- ✅ Uninstaller capability

### Current Gaps vs AKE-MCP:

1. **WebSocket Implementation**: Partially implemented, missing real-time event handlers
2. **Frontend Completion**: Vue 3 dashboard exists but missing critical views
3. **Integration Testing**: Components work individually but full integration untested

## 2. Feature Implementation Status

### ✅ WORKING FEATURES

#### Core Infrastructure

- **MCP Server**: FastMCP implementation with 20+ tools
- **REST API**: FastAPI with all major endpoints
- **Database Layer**: SQLAlchemy with PostgreSQL/PostgreSQL support
- **Authentication**: API key authentication functional
- **Multi-tenancy**: Project isolation via tenant keys
- **Message Queue**: Database-backed with acknowledgment
- **Logging System**: Comprehensive logging throughout codebase
- **Debug Mode**: Sets appropriate log levels

#### Installer Features

- **GUI Installer**: Cross-platform Tkinter interface
- **Dependency Installation**: Actually installs PostgreSQL, Redis, Docker
- **Service Management**: Creates OS services (Windows/Mac/Linux)
- **Profile System**: 4 deployment profiles with different configurations
- **Config Generation**: Creates proper .env files

#### Development Tools

- **Vision Chunking**: 100K+ token documents, 20M tokens/sec
- **Template Manager**: Database-backed mission templates
- **Tool Accessor**: Bridge pattern for MCP-API integration
- **Example Projects**: 3 demo projects in /examples

### ⚠️ PARTIALLY IMPLEMENTED

#### WebSocket System (60% Complete)

- ✅ WebSocket server setup
- ✅ Connection management
- ✅ Basic message routing
- ❌ Real-time event handlers incomplete
- ❌ Sub-agent spawn notifications
- ❌ Progress updates broadcasting

#### Frontend Dashboard (40% Complete)

- ✅ Vue 3 + Vuetify 3 setup
- ✅ Router configuration
- ✅ Theme system (dark/light)
- ✅ Navigation structure
- ❌ Project management views
- ❌ Agent monitoring dashboard
- ❌ Message queue visualization
- ❌ Real-time WebSocket integration

### ❌ UNIMPLEMENTED FEATURES (Config Flags Only)

These features have configuration settings but **NO actual implementation**:

#### Developer Profile "Features"

- **Hot-reload support** - `HOT_RELOAD=true` does nothing
- **Mock external services** - `MOCK_EXTERNAL_SERVICES=true` does nothing

#### Enterprise Profile "Features"

- **LDAP integration** - `LDAP_ENABLED=true` does nothing
- **Audit logging** - `AUDIT_LOGGING=true` does nothing
- **Compliance modes** - `COMPLIANCE_MODE=SOC2` does nothing
- **OAuth2** - Requires manual configuration even when enabled

#### Research Profile "Features"

- **Experiment mode** - `EXPERIMENT_MODE=true` does nothing
- **Data collection/telemetry** - `DATA_COLLECTION=true` does nothing
- **GPU acceleration** - `GPU_ENABLED=true` does nothing
- **Educational resources** - Mentioned but don't exist beyond 3 examples

## 3. Critical vs Nice-to-Have Analysis

### 🔴 CRITICAL (Blocks Release for Team Profile)

1. **Complete WebSocket Implementation**

   - Required for real-time collaboration
   - Agent status updates
   - Message notifications
   - Progress broadcasting

2. **Complete Frontend Core Views**

   - Project management interface
   - Agent monitoring dashboard
   - Message queue viewer
   - Basic task management

3. **Integration Testing**
   - End-to-end testing of MCP → API → Frontend flow
   - Multi-agent coordination testing
   - Error recovery testing

### 🟡 IMPORTANT (Should implement soon)

1. **Better Error Handling**

   - Graceful degradation
   - User-friendly error messages
   - Recovery mechanisms

2. **Documentation**

   - User guide
   - API documentation
   - Deployment guide

3. **Performance Monitoring**
   - Resource usage tracking
   - Response time metrics
   - Agent performance stats

### 🟢 NICE-TO-HAVE (Can be "Coming Soon")

All the unimplemented config flags:

- Hot-reload support
- Mock external services
- LDAP/OAuth2 integration
- Audit logging
- Compliance modes
- GPU acceleration
- Telemetry/data collection
- Experiment mode
- Extended educational resources

## 4. Profile-Specific Release Readiness

### Developer Profile ✅ READY TO RELEASE

**Status**: Fully functional for single-developer use

**Working**:

- PostgreSQL database (zero config)
- Up to 5 concurrent agents
- API key authentication
- Debug logging
- All core MCP tools
- Local deployment

**Acceptable Missing Features**:

- Hot-reload (developers can restart manually)
- Mock services (not critical)

**Verdict**: Ready for community release

### Team Profile ⚠️ NEEDS WORK

**Status**: 85% ready - critical features missing

**Working**:

- PostgreSQL + Redis
- Up to 20 concurrent agents
- Network accessibility
- API key authentication
- Multi-user support

**Blocking Issues**:

- WebSocket incomplete (breaks real-time collaboration)
- Frontend missing key views (no UI for team features)

**Verdict**: Needs 1-2 weeks of development

### Enterprise Profile ❌ NOT READY

**Status**: Core works but enterprise features are placeholders

**Reality Check**:

- No LDAP integration
- No audit logging
- No compliance features
- OAuth2 requires manual setup
- No high availability features

**Verdict**: Should be marked "Beta" or "Coming 2026"

### Research Profile ❌ NOT READY

**Status**: Mostly marketing, little substance

**Reality Check**:

- No experiment mode functionality
- No data collection/telemetry
- No GPU integration
- No special educational resources
- Just higher agent limits and no auth

**Verdict**: Should be marked "Experimental" with disclaimers

## 5. Recommended Actions

### Immediate (For Community Release)

1. **Update GUI Installer Descriptions** ✅ DONE

   - Marked unimplemented features as "(Coming Soon)"
   - Set honest expectations

2. **Update CLI Installer Profile Selection** ✅ DONE (Sept 28, 2025)

   - Disabled Team, Enterprise, and Research profiles in CLI installer
   - Only Developer profile is now selectable in CLI mode
   - Matches GUI installer behavior which grays out unavailable profiles
   - Rationale: Prevents users from selecting non-functional profiles
   - Code remains commented for future re-enablement when features are implemented

3. **Simplify to Reality** ✅ DONE (Sept 28, 2025)

   - **Removed fake profiles**: Replaced 4 fake profiles with 2 real deployment modes
   - **Local Development Mode**: PostgreSQL, no auth, localhost only
   - **Server Deployment Mode**: PostgreSQL/PostgreSQL, API key auth, network accessible
   - **Removed unimplemented config flags**:
     - HOT_RELOAD (no implementation)
     - MOCK_EXTERNAL_SERVICES (no implementation)
     - LDAP_ENABLED (no implementation)
     - AUDIT_LOGGING (no implementation)
     - COMPLIANCE_MODE (no implementation)
     - EXPERIMENT_MODE (no implementation)
     - DATA_COLLECTION (no implementation)
     - GPU_ENABLED (no implementation)
   - **Removed Redis**: Not actually implemented, only in-memory caching exists
   - **Updated files**:
     - setup.py: Simplified to Local/Server modes
     - setup_gui.py: Simplified to Local/Server modes
     - requirements.txt: Removed redis dependency
     - config_manager.py: Removed fake config flags
     - config.yaml.template: Removed features section
     - docker-compose files: Removed HOT_RELOAD flags

4. **Complete WebSocket Implementation** (1 week)

   - Add real-time event handlers
   - Implement progress broadcasting
   - Test with multiple concurrent connections

5. **Complete Minimum Frontend Views** (1 week)

   - Project list and creation
   - Agent status dashboard
   - Message queue viewer
   - Basic task management

6. **Integration Testing** (3 days)
   - End-to-end workflow testing
   - Multi-agent coordination
   - Error scenarios

### Short Term (Post-Release)

1. **Automatic Dependency Update System** (2 days)

   - Detect requirements.txt changes on startup
   - Prompt user to update dependencies
   - Implement safe rollback mechanism if update fails
   - Create venv snapshot/backup before updates
   - Auto-recovery to previous state on failure
   - Progress indicator during update process

2. **Documentation** (1 week)

   - Quick start guide
   - API documentation
   - Troubleshooting guide

3. **Performance Monitoring** (3 days)

   - Add metrics collection
   - Create performance dashboard

4. **Enhanced Error Handling** (3 days)
   - Better error messages
   - Recovery mechanisms

### Long Term (Future Releases)

1. **Enterprise Features** (Q1 2026)

   - Real LDAP integration
   - Audit logging implementation
   - Compliance frameworks

2. **Research Features** (Q2 2026)

   - Experiment mode design
   - Telemetry system
   - Educational content creation

3. **Developer Experience** (Ongoing)
   - Hot-reload implementation
   - Mock service framework
   - Development tools

## 6. Configuration Flags to Remove/Update

These settings should either be:

- Removed from the installer
- Marked clearly as "Coming Soon"
- Implemented before release

```python
# Developer Profile
HOT_RELOAD=true  # No implementation
MOCK_EXTERNAL_SERVICES=true  # No implementation

# Enterprise Profile
LDAP_ENABLED=true  # No implementation
AUDIT_LOGGING=true  # No implementation
COMPLIANCE_MODE=SOC2  # No implementation

# Research Profile
EXPERIMENT_MODE=true  # No implementation
DATA_COLLECTION=true  # No implementation
GPU_ENABLED=true  # No implementation
```

## 7. Release Timeline Recommendation

### Week 1 (Current)

- ✅ Update installer descriptions (DONE)
- Complete WebSocket implementation
- Begin frontend completion

### Week 2

- Complete frontend core views
- Integration testing
- Bug fixes from testing

### Release Ready (End of Week 2)

- **Developer Profile**: Full release
- **Team Profile**: Full release
- **Enterprise**: Beta/Preview
- **Research**: Experimental

## 8. Success Criteria for Release

### Must Have (Release Blockers)

- [ ] WebSocket real-time updates working
- [ ] Frontend can create/view projects
- [ ] Frontend can monitor agents
- [ ] Frontend can view messages
- [ ] End-to-end testing passed
- [ ] Installer works on Windows/Mac/Linux

### Should Have (Improve Experience)

- [ ] Basic documentation
- [ ] Error recovery tested
- [ ] Performance acceptable (<1s response times)

### Nice to Have (Post-Release)

- [ ] All config flags have real implementations
- [ ] Comprehensive documentation
- [ ] Performance monitoring dashboard
- [ ] Educational resources

## Conclusion

GiljoAI-MCP has a solid foundation with working MCP tools, database layer, and authentication. The installer is impressive and actually installs dependencies. However, the WebSocket implementation and frontend need completion before the Team Profile can be considered production-ready.

**Recommended Release Strategy**:

1. Focus on completing WebSocket and minimal frontend
2. Release Developer and Team profiles as "1.0"
3. Mark Enterprise/Research as "Coming Soon"
4. Be transparent about which features are placeholders
5. Iterate based on community feedback

The core value proposition - replacing AKE-MCP with better UI and easier installation - is achievable with 1-2 weeks of focused development on the critical missing pieces.

---

# Merged from root TECHDEBT.md (Dated: October 2, 2025 23:00)

## Current Architecture Limitations

### Multi-Agent CLI Tool Support

**Current State (v1.0):**
- **Claude Code Only**: Full support with native subagent orchestration
- Built exclusively for Claude Code's subagent spawning capability
- Direct, synchronous agent coordination through Claude's reasoning engine

**Why Claude Code Only?**

Claude Code provides native subagent spawning that enables:
- Synchronous control and coordination
- Direct handoffs between specialized agents
- No polling or message checking required
- Built-in reasoning for task prioritization
- Zero additional infrastructure needed

**Technical Limitation:**

Other AI coding tools (Cursor, Windsurf, Gemini, Codeium) do NOT have equivalent subagent capabilities. They operate as single-agent systems, which breaks our multi-agent orchestration model.

**Problem Example:**
```
Agent A (Cursor terminal) → sends message to queue
Agent B (Cursor terminal) → ❌ Cannot auto-check messages
                           ❌ No subagent API
                           ❌ Requires manual user prompts
```

---

## Expansion Proposal: Multi-Agent Support for Non-Claude Tools

### Phase 1: Current Implementation (Completed)
- ✅ Claude Code native subagent orchestration
- ✅ PostgreSQL message queue
- ✅ Multi-tenant project management
- ✅ WebSocket dashboard for real-time monitoring

### Phase 2: Hybrid Priority Orchestrator (Future)

**Goal:** Enable Cursor, Windsurf, Gemini, and other CLI tools to participate in multi-agent workflows.

**Architecture:**

```
┌──────────────────────────────────────────────────┐
│  GiljoAI Server                                  │
│  ┌────────────────────────────────────────────┐  │
│  │  Hybrid Priority Manager                   │  │
│  │  ┌──────────────┐  ┌───────────────────┐  │  │
│  │  │ Rules Engine │  │ Claude Haiku API  │  │  │
│  │  │ (Free/Fast)  │  │ (Smart/Cheap)     │  │  │
│  │  │              │  │ $0.75/month       │  │  │
│  │  └──────────────┘  └───────────────────┘  │  │
│  └────────────────────────────────────────────┘  │
│                                                   │
│  Background Services:                             │
│  - Message polling (every 30 seconds)             │
│  - Priority evaluation                            │
│  - Dashboard notifications via WebSocket          │
└──────────────────────────────────────────────────┘
```

**Components:**

1. **Rules Engine (Free, Instant)**
   - Handles 80% of priority decisions
   - Simple, fast heuristics:
     - Security issues interrupt everything
     - FIFO for low priority tasks
     - Single-agent-with-messages = immediate priority

2. **LLM Fallback (Claude Haiku API)**
   - Handles complex priority decisions
   - Multi-agent conflict resolution
   - Dynamic task re-ordering
   - Cost: ~$0.75/month for typical usage

3. **Message Polling Service**
   ```python
   async def poll_and_notify():
       """Runs every 30 seconds"""
       while True:
           agents_with_messages = await get_agents_with_unread()

           for agent in agents_with_messages:
               priority = await decide_priority(agent, context)

               await broadcast_to_dashboard({
                   "type": "agent_needs_attention",
                   "agent": agent.name,
                   "message_count": len(agent.messages),
                   "priority": priority,
                   "suggested_prompt": generate_prompt(agent)
               })

           await asyncio.sleep(30)
   ```

4. **Dashboard Integration**
   - Real-time priority queue visualization
   - "Prompt Agent" buttons with pre-filled prompts
   - Copy-to-clipboard for easy agent prompting
   - Visual indicators for high and critical priority tasks

**User Experience:**

```
Dashboard shows:
┌─────────────────────────────────────────────┐
│ 🎯 Priority Queue                           │
├─────────────────────────────────────────────┤
│ 1. Implementation Agent (URGENT)            │
│    💬 3 messages: Security vulnerability    │
│    [Copy Prompt] [View Messages]            │
├─────────────────────────────────────────────┤
│ 2. Test Agent                               │
│    💬 1 message: Ready for integration test │
│    [Copy Prompt] [View Messages]            │
└─────────────────────────────────────────────┘

User clicks "Copy Prompt" →
Clipboard: "Check your pending messages using check_messages tool and address the security vulnerability in JWT validation."

User switches to Implementation Agent terminal →
Pastes prompt →
Agent processes messages and acts
```

### Phase 3: Advanced Automation (Optional)

**Investigation needed:** Can we programmatically send prompts to:
- Cursor API (if available)
- Windsurf API (if available)
- Gemini API (if available)

If APIs exist, we could achieve near-Claude Code level automation for other tools.

---

## Implementation Estimates

### Phase 2: Hybrid Orchestrator
- **Time:** 2-3 weeks
- **Complexity:** Medium
- **Dependencies:**
  - Claude API key (for Haiku)
  - Background task infrastructure (already have with FastAPI)
  - Dashboard enhancements (Vue components)

### Phase 3: API Integrations
- **Time:** 1 week per tool (if APIs exist)
- **Complexity:** Low-Medium
- **Dependencies:** Tool vendor API documentation

---

## Cost Analysis

### Claude Code (Current)
- **Cost:** $0 (uses user's Claude subscription)
- **Infrastructure:** None
- **Maintenance:** Low

### Hybrid Orchestrator (Future)
- **Cost:** ~$0.75/month (Claude Haiku API)
- **Infrastructure:** Background polling service (already have)
- **Maintenance:** Medium
- **Benefit:** Support for all CLI tools

---

## Risks and Mitigation

### Risk 1: Other tools may never support native subagents
**Mitigation:** Hybrid orchestrator provides acceptable UX through dashboard notifications + copy-prompt workflow

### Risk 2: Priority decisions via small LLM may be lower quality
**Mitigation:** Use hybrid approach (rules + Claude API) for best quality at low cost

### Risk 3: User fatigue from manual prompting
**Mitigation:**
- Make prompts as easy as possible (one-click copy)
- Investigate tool APIs for automation
- Provide excellent priority visibility in dashboard

---

## Decision: Start with Claude Code Only

**Rationale:**
1. Native subagent support provides best UX
2. Zero additional infrastructure/cost
3. Get to market faster
4. Validate multi-agent orchestration concept
5. Expand to other tools based on user demand

**Migration Path:**
- Keep architecture designed for multi-tool support
- Comment out non-Claude integrations (keep code for future)
- Document expansion plan for future phases
- Re-enable other tools when orchestrator is ready

---

# Merged from docs/Techdebt.md (Previous Version - Dated: October 2, 2025 23:00)

**Note**: This section was previously retired with a note: "THIS DOCUMENT IS NOW RETIRED AS WE HAVE A PLAN IN PROJECT_PROPOSAL_CONTINUED.md" - preserved here for historical context.

## Enterprise SaaS Features

### PROJECT SAAS AUTHENTICATION & SUBSCRIPTION MANAGEMENT

- **Description**: Lightweight MCP installer with OAuth-based subscription validation for SaaS deployment
- **Implementation Strategy**:
  1. **Installer Flow**:
     - User signs up at giljoai.com
     - Downloads lightweight installer
     - Authenticates with email/password
     - Backend generates unique API key per device/installation
     - Installer auto-configures .mcp.json with credentials

  2. **Architecture Components**:
     - OAuth login during installation (no manual key handling)
     - Per-device API keys for granular tracking
     - Regional endpoint selection (us-east, eu-west, ap-south)
     - Subscription tier enforcement at MCP protocol level
     - Usage tracking and limits per tier

  3. **Client Proxy Approach**:
     ```javascript
     // @giljoai/mcp-proxy npm package
     - Validates subscription on startup
     - Proxies MCP requests to SaaS backend
     - Handles rate limiting locally
     - Auto-updates proxy version
     - Caches subscription status
     ```

  4. **Subscription Tiers**:
     - Free: 2 agents, 1 project, 100 calls/day
     - Starter ($29): 5 agents, 3 projects, 1000 calls/day
     - Pro ($99): 50 agents, unlimited projects, 10000 calls/day
     - Enterprise (custom): Unlimited everything

  5. **Security Benefits**:
     - No API keys visible to users
     - Per-device revocation capability
     - Anomaly detection (multiple IPs per key)
     - Auto-rotation of credentials
     - Team management with role-based access

- **Priority**: HIGH - Critical for monetization
- **Compatibility**: Works with any MCP client (Claude, Codex, Gemini CLI)

## Phase 3 (Post-MVP) Advanced Template Features

### PROJECT TEMPLATE MARKETPLACE

- **Description**: Create template sharing marketplace where users can share successful agent templates
- **Features**:
  - Public/private template sharing
  - Template ratings and reviews
  - Template categories and tags
  - Import/export templates between products
- **Priority**: LOW - Nice to have for community building

### PROJECT AI-POWERED TEMPLATE SUGGESTIONS

- **Description**: Use AI to suggest optimal templates based on task description
- **Features**:
  - Embeddings-based template matching
  - Learning from successful template usage
  - Auto-suggest template augmentations
  - Template composition (combining multiple templates)
- **Priority**: MEDIUM - Significant value add

### PROJECT TEMPLATE PERFORMANCE ANALYTICS

- **Description**: Advanced analytics dashboard for template effectiveness
- **Features**:
  - Token usage by template over time
  - Success rate tracking
  - Template evolution visualization
  - A/B testing different template versions
  - ROI calculations per template
- **Priority**: MEDIUM - Helps optimize template usage

**CONTEXT**: This MCP server depends on subscription based CLI code tools like claude code or gemini CLI. the problem is that the users is using a CLI based coding agent tool like Gemini CLI and Claude code. Those tools execute a task and then sit inactive so the user has to trigger them all the time and remind them to read messages and act when other agents are leaving messages in the MCp server. I would like this MCP tool to automate the "engagement" by triggering a CLI windows in windows 11 to trigger periodical checks for new messages. I dont know how to solve this with multiple "terminal windows" in windows/linux/mac running a separate agent.

## PROJECT MINOR FIXES
Minor Issues (Non-blocking) if they still exist:

1. Model field naming: metadata field conflicts with SQLAlchemy reserved word
   - Recommendation: Rename to doc_metadata
2. Terminology: Implementation uses chunk_number/total_chunks vs part/total_parts - No functional impact
   3 - add in timers and CLI terminal if needed.

## PROJECT SERENA FIXES
Minor Issues to Fix (5-minute fixes)

1. SerenaHooks Initialization Parameters
   - Issue: Missing required parameters in SerenaHooks.init()
   - Fix: Add db_manager and tenant_manager parameters to the init method
   - Location: src/giljo_mcp/discovery.py - SerenaHooks class
2. Windows Path Separator Normalization
   - Issue: Path separators not consistently normalized for Windows
   - Fix: Use Path() objects consistently or normalize with .replace('\\', '/')
   - Location: Throughout discovery.py and context.py
3. One Remaining Hardcoded Path
   - Issue: Path("CLAUDE.md") still hardcoded
   - Fix: Replace with PathResolver.resolve_path("claude_md")
   - Location: src/giljo_mcp/tools/context.py line 575
4. Test File Path Resolution
   - Issue: Tests fail when run from tests/ directory due to relative paths
   - Fix: Use absolute paths or properly resolve relative to project root
   - Location: Test files in tests/ directory

- These are all quick fixes that don't affect the core functionality of the Dynamic Discovery System. The system is working and
  production-ready despite these minor issues.

## PROJECT MULTIAGENT COMMS AND INTERACTION
investigate bashing in claude code or doing built in terminal with waiting and comms etc. how to leverage sub agents in claude code.
The other alternative is the TERMINAL MUX proposal below.

## PROJECT CLAUDE AGENT SDK INTEGRATION
- **Description**: Integrate Claude Agent SDK capabilities to enhance GiljoAI MCP orchestration
- **Strategic Value**: Creates two-tier orchestration system leveraging native Claude capabilities
- **Implementation Strategy**:
  1. **Hybrid Agent Architecture**:
     - SDK handles low-level agent behaviors and tool execution
     - GiljoAI MCP provides high-level coordination and persistence
     - Message queue routes between SDK subagents and GiljoAI agents

  2. **Enhanced Capabilities**:
     - **Context Management**: SDK's context compaction + GiljoAI's database persistence = infinite memory
     - **Subagent Hierarchy**: SDK subagents for immediate tasks, GiljoAI for long-running teams
     - **Unified Tools**: 40+ tools working in harmony (20+ from GiljoAI, 20+ from SDK)
     - **Dual Communication**: SDK for immediate, GiljoAI for persistent messaging

  3. **Integration Points**:
     ```python
     # Enhanced orchestrator detecting SDK capabilities
     class SDKEnhancedOrchestrator(ProjectOrchestrator):
         def spawn_agent(self, mission):
             if sdk_available:
                 return SDKEnhancedAgent(mission, self.message_queue)
             return StandardAgent(mission, self.message_queue)
     ```

  4. **Template System Enhancement**:
     - Templates generate SDK-compatible missions
     - SDK agents execute autonomously
     - Results persist in GiljoAI database

  5. **Discovery System Synergy**:
     - SDK's agentic search for active exploration
     - GiljoAI caches and indexes discoveries
     - Future agents start with pre-mapped codebase

- **Benefits for Users**:
  - Break ALL context limits through compaction + persistence
  - Enterprise-ready with development agility
  - Single MCP connection for coordinated teams
  - Real-time monitoring through Vue dashboard

- **Implementation Tasks**:
  - Update MCP tools to detect SDK agent capabilities
  - Enhance message queue for SDK/GiljoAI routing
  - Extend templates with SDK-specific missions
  - Add WebSocket events for SDK agent status

- **Priority**: HIGH - Positions GiljoAI as enterprise orchestration layer on Claude's foundation

## PROJECT PRODUCT ISOLATION
making tasks product specific, so they can be converted to projects within the product as the intent of tasks is ideas during dev, and potential technical debt or as reminder for the dev to do someting within the Product.

## PROJECT DASHBOARD TOTALS
ensure totals on dashboards under mesages , etc, stays within the context of the active product.
Manbye create a main page with all data listed by product, its projects its tasks

## PROJECT BETTER MESSAGE REVIEW
I need ideas on how to create an eloquent message "forum" like a MS teams or REddit post like interface where I can see the agent talk and look back how they are communcating. However, in a project not everything is linear so the solution needs to be almost "tree based" with branches in the communcations. Almost like topic tracking. I.e orchestrator: I am launching agents, = branches out to all the agents and their tasks. Agent 1: talks to Agent 2, follow that branch, but may also be responding to orchestrator. etc. how do we make this a logical interface, like a node_red "if this then that" workflow visualization? click on any agent and then see "its personal" communication branch workflow?

## PROJECT POPUP
Ensure windows for fields and input "popups" do not close when clicked accidentally in the background.

## PROJECT TOKENWASTE
wastefull communications and token use when agents finish a taks, simply telling the other agents that "thinks went well", often from the tester or validator agent. Agents that work in serial, should tell the next agent they are done so it can proceeed, but they dont need to tell everyone they are done. They need to tell the orchestrator they finished their task as a reporting function, and as I said, tell the next agant to proceed when their own task is done. The final agent in the chain, SHOULD tell the orchestrator only it is finished.

## PROJECT GITHUB
adding github comitts if used by user to update github automatically after each project completion with proper notes. Should this replace a local devlog or keep both?

## PROJECT TERMINAL MUXing
Tmux like experience:

-Tmux can do the below, someting similar but with loops would be great for GiljoAi-MCP.
The tmux MCP server can run multiple persistent windows (each with its own long-running command) and your AI client can control them. It doesn't include a scheduler, so "periodic checks" happen by starting a loop or watcher inside those tmux windows (or via cron/Task Scheduler).
npm

- Here's how this maps to your use case:

- Multiple agents in parallel
  Create one tmux window per agent and start each CLI with run_command(...). You can list windows, send keys (e.g., Ctrl-C), and scrape output with regex via get_output(...). That gives you durable panes your assistant can poke any time.
  npm

- Auto-engagement / periodic polling
  Start a window that runs a simple loop, e.g.:

while true; do
<YOUR_AGENT_CHECK_CMD> || true
sleep 30
done

- Or run an event watcher (e.g., inotifywait) that fires when new files/messages appear. The MCP server just keeps those processes alive and lets your assistant monitor/interact with them. There's no built-in timer—you launch the loop with run_command and it keeps ticking.
  npm

- Windows 11 reality check
  tmux is Unix-only. On Windows you'll run this under WSL2 (Ubuntu), install tmux + Node/Bun there, and have your MCP client spawn the server through wsl.exe. Example MCP entry:

{
"mcpServers": {
"tmux-shell": {
"command": "C:\\\\Windows\\\\System32\\\\wsl.exe",
"args": ["-e","bash","-lc","bunx @hughescr/tmux-mcp-server"]
}
}
}

(You can swap bunx for npx.)
brainhack-princeton.github.io
+1

- Parent-session mode (nice quality-of-life)
  If you launch the server from inside tmux, it reuses the current session (no extra sessions, windows show up alongside yours). Handy if you "live in tmux."
  npm

- Safety. This gives your assistant a real shell with your privileges—no sandbox, no allowlist. Use low-priv users/containers for anything you care about.
  npm

---

## Related Documentation
- See `docs/PROJECT_ORCHESTRATION_PLAN.md` for subagent integration details
- See `README.md` for current tool support status
- See `CLAUDE.md` for Claude Code-specific features

---

**Last Updated:** October 5, 2025
**Status:** Consolidated document - all tech debt items merged into single source of truth
