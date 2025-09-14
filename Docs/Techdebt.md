THIS DOCUMENT IS NOW RETIRED AS WE HAVE A PLAN IN PROJECT_PROPOSAL_CONTINUED.md

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


CONTEXT:  This MCP server depends on subscription based CLI code tools like claude code or gemini CLI.  the problem is that the users is using a CLI based coding agent tool like Gemini CLI and Claude code. Those tools execute a task and then sit inactive so the user has to trigger them all the time and remind them to read messages and act when other agents are leaving messages in the MCp server. I would like this MCP tool to automate the "engagement" by triggering a CLI windows in windows 11 to trigger periodical checks for new messages.  I dont know how to solve this with multiple "terminal windows" in windows/linux/mac running a separate agent.


PROJECT MINOR FIXES
Minor Issues (Non-blocking) if they still exist:

1. Model field naming: metadata field conflicts with SQLAlchemy reserved word
    - Recommendation: Rename to doc_metadata
2. Terminology: Implementation uses chunk_number/total_chunks vs part/total_parts
    - No functional impact
3 - add in timers and CLI terminal if needed.


PROJECT SERENA FIXES
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

PROJECT MULTIAGENT COMMS AND INTERACTION
investigate bashing in claude code or doing built in terminal with waiting and comms etc. how to leverage sub agents in claude code.
The other alternative is the TERMINAL MUX proposal below.

PROJECT PRODUCT ISOLATION
making tasks product specific, so they can be converted to projects within the product as the intent of tasks is ideas during dev, and potential technical debt or as reminder for the dev to do someting within the Product.  

PROJECT DASHBOARD TOTALS
ensure totals on dashboards under mesages , etc, stays within the context of the active product.  
Manbye create a main page with all data listed by product, its projects its tasks

PROJECT BETTER MESSAGE REVIEW
I need ideas on how to create an eloquent message "forum" like a MS teams or REddit post like interface where I can see the agent talk and look back how they are communcating.  However, in a project not everything is linear so the solution needs to be almost "tree based" with branches in the communcations.  Almost like topic tracking.  I.e  orchestrator: I am launching agents, = branches out to all the agents and their tasks.  Agent 1: talks to Agent 2, follow that branch, but may also be responding to orchestrator.  etc.  how do we make this a logical interface, like a node_red "if this then that" workflow visualization?  click on any agent and then see "its personal" communication branch workflow? 

PROJECT POPUP
Ensure windows for fields and input "popups" do not close when clicked accidentally in the background.

PROJECT TOKENWASTE
wastefull communications and token use when agents finish a taks, simply telling the other agents that "thinks went well", often from the tester or validator agent.  Agents that work in serial, should tell the next agent they are done so it can proceeed, but they dont need to tell everyone they are done.  They need to tell the orchestrator they finished their task as a reporting function, and as I said, tell the next agant to proceed when their own task is done.  The final agent in the chain, SHOULD tell the orchestrator only it is finished.

PROJECT GITHUB
adding github comitts if used by user to update github automatically after each project completion with proper notes.  Should this replace a local devlog or keep both?

PROJECT TERMINAL MUXing
Tmux like experience:

-Tmux can do the below, someting similar but with loops would be great for GiljoAi-MCP.
The tmux MCP server can run multiple persistent windows (each with its own long-running command) and your AI client can control them. It doesn’t include a scheduler, so “periodic checks” happen by starting a loop or watcher inside those tmux windows (or via cron/Task Scheduler). 
npm

- Here’s how this maps to your use case:

- Multiple agents in parallel
Create one tmux window per agent and start each CLI with run_command(...). You can list windows, send keys (e.g., Ctrl-C), and scrape output with regex via get_output(...). That gives you durable panes your assistant can poke any time. 
npm

- Auto-engagement / periodic polling
Start a window that runs a simple loop, e.g.:

while true; do
  <YOUR_AGENT_CHECK_CMD> || true
  sleep 30
done
- Or run an event watcher (e.g., inotifywait) that fires when new files/messages appear. The MCP server just keeps those processes alive and lets your assistant monitor/interact with them. There’s no built-in timer—you launch the loop with run_command and it keeps ticking. 
npm

- Windows 11 reality check
tmux is Unix-only. On Windows you’ll run this under WSL2 (Ubuntu), install tmux + Node/Bun there, and have your MCP client spawn the server through wsl.exe. Example MCP entry:

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
If you launch the server from inside tmux, it reuses the current session (no extra sessions, windows show up alongside yours). Handy if you “live in tmux.” 
npm

- Safety. This gives your assistant a real shell with your privileges—no sandbox, no allowlist. Use low-priv users/containers for anything you care about. 
npm



