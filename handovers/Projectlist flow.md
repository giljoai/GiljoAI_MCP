## All products are tennanted per user
## All projects are tennanted per product
## (future, not addressed yet) All tasks are tennanted per user
## All agents (profiles) are tennanted per user
## the 6 seeded agent profiles are also tennanted per user but seed to all uers on account setup/login


# Only 1 active product at any given time

Implement:
- When activating an inactive product, warning should pop up (we have this).
- When activating an inactive products, then the currently active product and its active projects should both deactivate.
- Freeing up the user to work with the now activated product.

# Only 1 active project per active product at any given time

- When a project gets activated then this is the only project the MCP server and agents can communicate with within the tennanted user

- [View Deleted (#)] button should only show deleted projects as it relates to the active product, as projects are tennanted under products.

- An active project that gets deactivated, frees up the slot of an "Active project" and allows a new project to be activated. it Deletes all created missions, agent preprations (releasing agents), delets any existing MCP communicatoin history.  This essentially is the way to restart a project.  it also adheres to proper badge for deactivation.
- An active project that gets paused, keeps mission created by orchestrator, keeps assigned agents, keeps all context generated for the project, keeps all MCP communication in storage, also frees up a slot for an new "Active Project", With proper badge for being paused.  
- An active project that gets makred completed (will have procedures defined later) but for now is marked as completed. keeps mission crated by orchestrator, keeps assigned agents, keeps all context generated, all MCP chats, all historical data for that project is kept for the project.  We may link to any documents it writes as after action reports (to be determined)
- An Active project that gets deleted, deletes all mission created by orchestrator, assigned agents removed from project, deletes all context generated for the project and frees up the active slot.  All in a software way to start and then hard delete of all this data after the 10 day waiting periond.  the project appears in the view deleted bin/page/button (#) updates, no badge needed as it is removed form list.
- An Ative projet that gets cancelled, keeps mission crated by orchestrator, keeps assigned agents, keeps all context generated for the project, frees up a slot for a new active project and updates badge to cancel.

- A paused project follows the same guidlines above for all the options, with two exceptions A- When paused, will tell the user tha t the application will que an MCP message for all active agents to report into orchestrator to write a "current state" report so it can proceed later.  B- When resumed,  where it paused by reactivating the old orchestrator, asking it to read the old mission, read the "current state" report, and respawn new agents to continue the work.  Retiring the old agents in the project.

- A completed project see above in Active projet

- A camceled project from any state see above in Active project

- A deleted project see above in Active project

- A deactivated project see above in Active project


# Dashboard x.x.x.x/dashboard 

Implement:
The dashboard needs to have a drop down to select dashboard view on a per product basis, then per project basis for statistics.  Should also have a top aggregate view of all products and projects.

context: Its a statistics board for the developer.

- More integrations to be defined in future, no need to populate with data in this specific project, leave what is there allready.