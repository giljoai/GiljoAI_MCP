# Kanban page (proposed hame Job Manager)

# Kanban board window
as per your description here is where the columns of the kanban board appears.
- The initial board starts with an empty message center and all agents start in WAITING column and here is where the copy prompt button appears. With instructions [COPY PROMPT] it says for CODEX AND GEMINI in individual Terminal windows.
- Orchestrator should appear here too, and say [COPY PROMPT] for Claude Code only (becuase in clude code the orchestrator can launch subagents in its own terminal window).
- As agents start working they move along the kanban board
- The message center should show the agents talking and communicating
- at the bottom of the message center the user should be able to send MCP messages to a specific agent or broadcast to all agents.
- the projet summary panel at the bottom is where the orchestrator should sum up the poroject when finished, and a project closeout prompt for when the user thinks the project is done, this copy button is a prompt that defines for orchestrator closeout proceduers (To be determined in details, but should be committ, push, document, mark project as completed and close out the agents) the user should not press this until done, they could go back to the cli window and ask orehcstrator to reactivate the old agents (and their agent ID's) to continue work.   
- when agents move to completed state, it should have a tool tip, that if the project needs to continue (someting is not satisfactory by the developer) then the dveloper can either message them in their own CLI window, but can also send MCP messages via message center (for audit and loggin of messages0 and THEN go to the CLI window and ask each agent to read their messages waiting for them)