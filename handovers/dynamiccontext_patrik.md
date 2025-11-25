Complete Discovery Overview: Dynamic Agent Discovery System

  I've completed a comprehensive discovery and design analysis for implementing dynamic agent discovery in the GiljoAI MCP Server. Here's the
  complete overview:

  🎯 Core Problem Solved

  Transforming the orchestrator from a 600-token fat prompt with embedded agent templates to a 450-token thin prompt with dynamic MCP-based
  agent discovery, while supporting both Claude Code CLI mode (single terminal with subagents) and Legacy CLI mode (multiple terminals).

  📊 Current State Analysis

  Token Budget Breakdown:
  - Current orchestrator prompt: ~600 tokens
  - Agent templates inline: ~150 tokens (25% of prompt)
  - After optimization: ~450 tokens (25% reduction)

  Key Discoveries:
  1. Infrastructure Already Exists: The get_orchestrator_instructions() MCP tool already returns agent templates
  ## QUESTION - how does this differ between Claude Code CLI with subagent mode vs General mode with each agent using its won Terminal window
  2. UI Toggle Non-Functional: Frontend has the toggle but it's hardcoded to false
  ## QUestion - Investigate deeper, this was working at some point, or atleast the toggle was, lets make sure we do not have orphan or zombie code / functions
  3. Database Ready: Agent templates table supports tenant-specific configurations
  ## Question - To confirm, this means that each tennant (user tennant not ORG tennant right?) has their own agents?
  4. Thin Client Active: System already uses ThinClientPromptGenerator

  🏗️ Architectural Design

  Two Execution Modes:
  1. Claude Code CLI Mode
    - Uses Task tool with subagents
    - Single terminal execution
    - Orchestrator coordinates via MCP


- {MCP agent instructions}

  2. Legacy CLI Mode
    - Manual agent launch in separate terminals
    - Direct MCP communication
    - Traditional orchestration pattern

    ## Question - As state above we have two terminal model behaviours. Does our instructions waiting on the MCP server (regardless of mode) for the orchestrator to tell the orcestrator (based on 'Agent Template Manager toggles'), what agents are available as subagents to help the project/mission?

    **CONTEXT and Behaviour** Claude code has two types of agents.  User or project agents. They are located in either ~\.claude\agents (= what claude code CLI calls user agents) or {project_folder_from_where_claude_CLI_was_launched}\.claude\agents (= what claude code CLI calls project agents)? We do not need to know which type of agent the user has configured in Claude code CLI. The instructional prompt should be encompassing for either mode when the user toggles "use Claude code CLI subagents". Ecompassing means that if the user has enabled implementor" in the templte manager, then the orchestrator should assume this agent exists as a user or project agent and thus write a mission for this agent.  Similarly, the orchestrator should write the exactly the same mission for a general CLI mode agent (legacy above).  
    
    The difference is in once the project is staged, mission is created and agens are spawned.  Now the prompt will differ for the next 'prompt copy' for the orchestrator.  This is in the implement tab vue, and the 'play button' which now copies a dynamic prompt.  
    
    - If Claude Code CLI toggle is toggled on, the prompt will tell the orchestrator to use built in subagents (either user or project) and thus launch in one terminal window
    - If Claude Code cli IS NOT toggled, the promot will tell the orchdstrator it will work in a multi terminal environment requiring the user to copy and paste the other agents starting prompts individually. 
    
   **Discussion and additional reacsearch check point** I am not sure today how Claude code CLI selects which agents to use if the user has both (can you explain)? I also have no answer yet for if the user modifies the agent teamplate in our MCP server, how we confirm that this latest template is matching/not matching based on these folder paths.  A concept is that when the agent teplates are exported from GiljoAI_MCP we put a date om the agent Name. (we have a suffix field allready in the configurator, but that is reserved for the user, thus an agent named 'Implmentor' the suffix allows the user to suffix it to read 'Implementor_TDD' or 'Implementor_My-cool-app', we could now add MMDDYYYY{version} and this way there could be a check for "your agent templates are not matching, please import new agents from 'My Settings' ")

#### My vision for the Prompt flow on [Stage porject] button press:
- Give identity: You are Orchestrator, your agent ID is {UUID}
- Give product ID: You are working on Product {name}, product ID {UUID}
- Give project ID: You are working on Project {name}, project ID {UUID}
- Your first task is to check MCP health {MCP Command}
- Your second task is to check your project enviornment, read Claude.MD in the project folder
- Your third task is to understand your agent enviornment {MCP agent instructions, fetch available agents, their names, their capabilites,etc}
- - OPtional / consideration: {MCP agent intructions has now provided agent names, with date(? see above) If agent_name not matching subagent in claude code THEN tell user, "You seem to have updated agent templates on the MCP server, or you are missing agent types in Claude Code CLI please import them". }
- Your fourth task is to fetch your mission instructions {MCP command, read context prioritizatoin rules, fetch_context, use Serena MCP of toggled on by user (assumes user has installed Serena MCP), read Serena MCP parameters if user configured advanced options, github is enabled (assuming github is installed on the machine if user toggles this on), create_mission, spawn_agents , write_agent_prompts(including your own, tell each agent where to get more context, tell each agent that Serena MCP is available, tell each agent that Serena MCp advanced options or where to get them, tell each agent Github is enabled if needed, tell each agent what the fellow agents will be working on this, any other rules I may be forgetting)}
- Your fifth task is to activate the jobs {MCP command for toggling various states} enabling the [Launch Jobs] button

#### My vision for Prompt flow on IMplementation vue Tab when user presses 'play button' IN CLAUDE CLI MODE
- Orcestrator prompt to paste
- - You are Orchestrator, Agent_ID, working on Product_ID and project_ID.
- - Instructions for what to do next on {MCP command} = read the orchestrators {job_ID, Coordination role, spawn agents instructions, how to give each agent instructions to get their individual instructions {MCP Command to read their prompt and other behaviours form the MCP server} Note: many agent instructions are part of their templates (MD FILES) like their MCP commands, to this subagent prompt is mainly the job to be done for the project} 

#### My vision for Prompt flow in Implementation vue tab when user presses 'play button' IN GENERAL MODE (COdex and Gemini and generic)
 - Orcestrator prompt to paste
- - You are Orchestrator, Agent_ID, working on Product_ID and project_ID.
- - Instructions for what to do next on {MCP command} = read the orchestrators {job_ID, Coordination role}
- - If questions THEN ask user/developer.
- - Close out and decommission rules when users tell orchestrator
 - Each agent gets their own prompt to paste
- Give identity: You are xxxxxx agnet, your agent ID is {UUID}
- Give product ID: You are working on Product {name}, product ID {UUID}
- Give project ID: You are working on Project {name}, project ID {UUID}
- Your first task is to check MCP health {MCP Command}
- Your second task is to check your project enviornment, read Claude.MD in the project folder. "You are working in an individual terminal window and you can only communicate with the orchestrator and your agent team via MCP {MCP command = understand_agent_team}"
- Your third task is to fetch your job instructions {MCP command, communications rules, read job, IF question THEN ask orchestrator, use Serena MCP of toggled on by user (assumes user has installed Serena MCP), read Serena MCP parameters if user configured advanced options, github is enabled (assuming github is installed on the machine if user toggles this on), (note are there other rules I may be forgetting??)  Tell MCp serer  you are Begining work, start work.}



  Mode State Machine:
  CONFIGURATION → STAGING → EXECUTION → COMPLETION
       ↓            ↓          ↓           ↓
    (mutable)    (locked)   (locked)    (locked)

  ⚠️ Critical Edge Cases Identified

  1. Orchestrator Succession Risk: Mode changes during handover could break compatibility
  ## Question - What does the above mean? example? 
  2. Template Version Conflicts: Runtime updates could cause agent behavior inconsistencies
    ## Question - What does the above mean? example? 
  3. WebSocket Protocol Impact: Dynamic discovery might disrupt real-time UI updates
    ## Question - What does the above mean? example? 
  4. Security Vulnerabilities: Dynamic fetching introduces code injection risks
    ## Question - What does the above mean? example?
  5. Job State Management: Mode switching could orphan in-progress jobs
    ## Question - What does the above mean? example?

  🛡️ Security & Safeguards

  Required Protections:
  - Template signature verification
  ## Questoin: Why?
  - Tenant boundary enforcement
  ## Question: Dont we allready ahve this?
  - Rate limiting on discovery requests
  ## Question: please explain
  - Audit logging for all template changes
  ## allready in place? 
  - Sandboxed execution for dynamic agents
  ## why this explain? un needed complexity?

  📋 Implementation Roadmap

  10-Phase Migration Plan:
  1. Database Schema - Add discovery tables with backward compatibility
  ## We are in developer mode, the product is not released, no need for backwards, we can blow anything away that we need
  2. Service Layer - Create AgentDiscoveryService with multi-tenant isolation
  ## explain?
  3. API Endpoints - 5 new REST endpoints for discovery operations
  4. MCP Tools - 3 new tools for agent self-registration
  5. Frontend Components - Vue 3 components with Pinia state management
  6. Testing Suite - 70+ tests covering unit, integration, and E2E
  7. Documentation - Complete API and user documentation
  8. Staging Deployment - Feature flags for gradual rollout
  ## we are in dev mode, we can what evern we want, no product to disrupt
  9. Production Migration - Zero-downtime deployment
  10. Monitoring & Optimization - Performance targets and metrics

  📈 Performance Targets

  - Agent registration: <50ms (P95)
  - Discovery queries: <100ms for 1000 agents
  - Prompt size reduction: 25% (600→450 tokens)
  - Backward compatibility: 100% maintained

  🔄 Migration Strategy

  Zero-Downtime Approach:
  1. Deploy with feature flag disabled
  2. Test with 10% of users
  3. Monitor for 24 hours
  4. Gradual rollout to 100%
  5. Keep rollback ready for 7 days

  📝 Key Technical Details

  Database Changes:
  - New agent_discovery table
  - Enhanced mcp_agent_jobs with discovery fields
  - Versioned template tracking

  Service Architecture:
  - AgentDiscoveryService manages lifecycle
  - WebSocket events for real-time updates
  - Automatic expiration and cleanup

  Frontend Updates:
  - DiscoveredAgentsTable.vue component
  - Pinia store for state management
  - Real-time WebSocket integration

  ✅ Success Criteria

  1. Orchestrator prompt reduced to <450 tokens
  2. Both execution modes fully functional
  3. Zero breaking changes to existing workflows
  4. All security vulnerabilities addressed
  5. Performance targets met or exceeded

  🚀 Next Steps When Ready

  The discovery and design phase is complete. The system is ready for implementation following the 10-phase migration plan. Each phase has been
  designed with:
  - Specific technical requirements
  - Testing strategies
  - Rollback procedures
  - Performance benchmarks

  This comprehensive overview provides everything needed to understand the current system, the target architecture, and the safe migration path
  between them.
