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