> **Note (2026-03-07):** This is an informal developer vision document. The project now uses the GiljoAI Community License v1.1 (single-user free, multi-user requires commercial license). Strategy: one repo now, Community Edition + SaaS fork later. See LICENSING_AND_COMMERCIALIZATION_PHILOSOPHY.md for details.
>
> **Last Updated:** 2026-03-08

 this changes alot, ok so based on all this information, let me describe how I would like things to work.  as we
know the this MCP server app, is a context communication frame work.  The developer creates a "produt" uploads a
vision or product proposal, fills out fields like tech stack , behaviors or project guidlines for the ai agents.
etc.  this is "single source of truth".  We have serena MCP integration as a tool for the agents help in their jobs.
  as developer begins to build the product, he creates projets,  the projects are the "missions" the orchestrator
manages.  as a project gets activated, (in the old system) the orchestrator would read the project description,
someting typed by the developer.  It would harmonize the request based on the product and all knowledge (single
source of truth), from there it would create the mission.  as part of creating the mission, the orchestrator would
pick agent personas (or create them, in the old version we did not have tempalted agents I beleive or very light
ones [see AKe-MCP on f drive])  it would assign parts of the mission to these agents and give them prompts the user
would copy into new terminals and hit enter.  this would trigger the agents and they talk over the MCP server .
This was done in several shell terminals in windows or git terminals.  user had to often toggle between the terminal
 windows and nudge them along or remind them ot read new messages as other agents ould do their pahse etc.  IN this
product we determine to use claude code subagents to do this, becaue they natively interact and would go back to the
 main claude prompt for it to work as the "orchestrator" and trigger the next ageint.   So what I want, is the exact
 same flow product->user defeind projects (or sometimes I would ask the orchestrator to create a project if we found
 a cap so we could fix someting later while staing focuse do a current task) -> spawn orchestrator -> context
analysis and creation of the mission -> select agents -> launch agents -> have protocols for how the agents
communicate and work, go back to orchestrator for more context if needed - > orchestrator is the main interace to
the user, but hte user sees on a dashboard agetns work, what they are doing, how they are chatting, etc etc.  I
think wit this product, we are extremely close to be functional (need validation) but with intent to work in a git
bash terminal, still requireing things like "add agents" restart terminal "copy paste prompt" now the agent starts,
if we can build this all into a terminal window then that would be such a pleasant user experience. lets discuss,we
need to talk this through and ensure we are close with our build to implement someting like this.


 think what we have now is this, (I hope this is what we are building): Product[with context] -> predefined agents
  -> predefined orchestator agent -> user creats project descirption -> clicks "create mission" -> a prompt is created
  for orhectrator to read all context and build the mission -> user pastes the prompt into terminal of choice ->
  claude code goes towork and via MCP documents the missoin into the project (user can see in the project their
  original projec trequest, and now the mission prompt) -> orchesrator also selectes agents for the job, it builds a
  prompt for each agent base on their skill and based onthe mission it defined -> agent cards start populating in the
  project with a copy button -> user copyies and pastes each prompt for each agent in its own terminal window -> agent
  uses MCP to collect their mission and rules, protocols andinstructions and starts working -> it communicates back
  to other agents vai MCP -> user sees this on thier message dashboard and when the user sees there is a message
  waiting for a specific agent, they clikc on that tab and tell them "you have a message waiting".  This was the old
  way, now add subagent features in cluade code and codex,.   Replace the "copy each prompt for each agent", instead
  there is a list of agent cards but only one prompt, for the main prompt of claude code "the orchestrator", the main
  prompt sais to go to MCP get the mission and spawn the selected subagents as defined during the mission creation /
  planning phase. now the agents communiate in claud code but have instrucitons to also communicate same message to
  the MCP server so the use can see what they are doing.   the one thing I have not figured out however, is HOW do I
  get the agent personas into claude code, unless, the user, Priot to launching the mission (mission has been created
  and is awaiting execution) the user  gets a "Agnets are stageed copy this prompt to install the agents in your ai
  tool", or use /giljo fetch_project slash command, to fetch agents, it fetches the staged agents MD files, then
  cluade says "you must restart me", user restarts cluade " now agents are loaded, and finally the user can copy paste
  the promp to launch the project or write /giljo start_project and it uses MCp to get going, the slash command can
  make the copy paste need lower, but this is still so extremly cumbersom,e?
