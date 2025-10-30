[Developer note] I need to truly go through this document and harmonize that when I talk about product I mean the product as a activity in this application and then when I talk about project I'm talking about a project under the product and then I'm talking tasks as tasks within the product Jobs Their jobs are the execution phases of a project Essentially I need to clearly differentiate but I'm talking about the application that we're building and products projects tasks and jobs as functions in the application I may have missed this somewhere in all this text.

### Product vision realized?

This MCP server is intended to help developers using CLI coding tools terminal based in Windows or Linux or Mac such as claude codex and gemini. One of the major problems is the tracking of context the tracking of technology stack the tools the dependency and everything else when vibe and context coders are building products particularly as a singular developer where you have to track a lot of these things.

The purpose was to create a form and field based documentation of a product to make sure that all bases are covered but that the developer doesn't always have to remember them when he vibe or coat context codes.

So the very first thing that this product does is allows a developer to create a product under that product is project and then these projects get executed with some aggregation of context and preparation of agents and summarization of a mission etc I will go into more of those details later in this post/

The other thing I'm trying to solve with this product is that while you're interacting with the Gentex CLI coding tools ideas pop up and it's very easy to get sidetracked and distracted and in order to stay disciplined and not loose Good ideas when they happen is to be able to quickly punt them over or flip them over into a task list to be addressed later And that's where the task list comes in in this product.

Much of this worked in my earlier MCP Lab Develop application and now I decided to build it more commercial friendly.

Meaning I want it to be shared and hopefully get some traction on Github where people can keep building on it But I also wanted a downloadable from our business web page to show show that we like to share in our progress as a company particularly around tools and our openness and showing the commitments to the AI development community.

I also wanted to build a product to be ready to be a potential SaaS in the future if somebody did not want to run it on their laptop or on a LAN server but rather have it hosted because this is MCP over HTTP.

So I'm hoping that the foundations for all what I've described is there and now I will go into some more detail.

## Tennancy and Heirachy

For the product to support initial multi user functions as a server we created tenancies the tenancies are built around a user.  This I believe is going to serve as a foundation should we make a Saas application out of this.

In the future I see expanding the product where multiple developers can use AI agentic coding tools and collaborate on the same product sharing projects for accelerated development.  But for right now we've isolated it to one developer with his or her multiple products.

From a hierarchy perspective a product is the top of the hierarchy and under that falls projects, also within the product are tasks. Once a product is activated all the projects created belong to that product and tasks that the developer flips into the task list also belong to that product. Tasks can be converted to products at any time.

- All projects are tennanted per product
- All tasks , when a product is active, belong to the product
- Tasks can be added with no active product, and if so have a NULL value and appear under all products until assigned.

Customized agents are also under each user tenant, When the user account is created a default set of six agents are created but the user can add and customize more agents.

* We need to add/consider that only six types Of agents can be active at any given time. [developer note] I told Claude that "more agent of the same type may be used but six types Or what is your recommendation? Do you think there might be more than six variation of agents needed between implementer database expert UX designer
tester researcher etc? We today have six templates defaulted in the application do we need more but keeping in mind that the user can also create more customized agents if they want.

# Agents

All agents are tenanted under each user and are spawned as 6 default templates as a user gets created.  The user can also create customized or modify the agent as they need.

* We need to add/consider that only six types Of agents can be active at any given time. [developer note] I told Claude that "more agent of the same type may be used but six types Or what is your recommendation? Do you think there might be more than six variation of agents needed between implementer database expert UX designer
tester researcher etc? We today have six templates defaulted in the application do we need more but keeping in mind that the user can also create more customized agents if they want.

We have one primary and important agent called the Orchestrator, The orchestrator is a well prompted and templated staging agents in this application and as a project gets launched its job is to aggregate all contexts around the product and the project description harmonize the mission Divide up the jobs and assign it to the proper agents.  The orchestrator is also or should also be the primary interface for the developer and all other subagents should report to the orchestrator.

The key restriction we have in this application is the lack of automation The closest we have is the MCP message communications but that only works while the agents are active.  so there will always be in need for the developer to nudge agents along in their various terminal windows to read messagesi  In the future states it would be amazing if that could be automated and perhaps we build the terminal into the application or find ways to inject commands into active terminals.

Claude stands out in this because with Claude we can end one prompt launch the orchestrator and it could spawn subagents through its own internal communications protocol So this will always work a little bit smoother with Claude but there's nothing preventing the developer to even with Claude just like Codex and Gemini work in multiple CLI terminal windows copy prompts to trigger the agents and then regularly nudge them along to communicate and do the job.

The tool an agent export template function for Claude Code specifically that allows the user to export agents into Claude code.

Agents should have strict prompting to regularly check in and communicate via MCP and that should be in their agent profiles today.

* [Developer note] I don't think we have created an integration where the application reads the currently deployed agents that Claude has nor have we implemented how the user can modify agents we only have one time all agent integration function so we need to explore this.

# Products

There can only be one active product at any given time and within the product 1 active project at any given time in the current state We do this just to scale for some simplicity but I don't think there's a necessary restriction because all the agents have unique ID's the project has a unique ID and the product has a unique ID so for all sense and purposes I don't see an issue with any ton of cross communications but we're keeping it simple by isolating it for now.

The developer should be motivated to fill out as much documentation as possible around the product it would help with the context.

# Projects 

As mentioned earlier projects could be created from tasks, The tasks could flipped from an active chat in the Agentic CLI tool or be a human entry.  It is important when it's converted into a project that it keeps its name and the text and the text field becomes a description.  

Projects are also all human entered This is where the developer describes what they want to get done and gives it a title When the orchestrator first kicks off is when it merges all the context debth, Knowledge of the code the tech stack the formalities the dependencies etc and builds a mission and divides it up between agents.

Projects can have various states like I mentioned earlier only one project may be active at any time If the user or developer creates multiple projects they will remain inactive They can have canceled projects they can have completed projects and they can delete the projects.

A deleted project should be a soft delete that firmly deletes after 10 days and can be restored until then.

Note when a user shifts from one product to the other all active projects should switch to inactive state as again only one active product and only one active project can be valid at any given time.

When a project is activated a launch button appears this redirects the user to a project launch preview.


# Project Launch Preview

The project launch preview is where the templated instructions for the orchestrator shows up as the first agents to be activated.  It also shows the human description of the project being worked on.

The orchestrator can be activated By clicking the copy prompt button and pasting it into the CLI tool to get working.  The first thing the orchestrator does is builds out the mission which populates in the screen for the user to see and review and continues to assign agents, based on the active agent templates in the application.

We also have a token counter based on the mission prompts and the agent prompts as a totality I don't have all the details yet of how we have implemented the counter but it's there and will require some tuning.

We we also have a projects during the launch phase which restores the project to a blank slate and returns it to the project list removing any created mission and any assigned agents and immediately deletes them.

Once the developer is happy with the initial staging they go activate the actual work and moves on to the Jobs pane.

# Jobs

 To get the project going, there is a variation depending on Claude code or Codex/Gemini.  In the jobs pane the agents will be listed as Waiting, with ready to go prompts.  For calude only one Prompt needs to be copied into the same window as the prior orchestrator and that orchestrator will then launch the subagent function in clawed code so the agents can begin their work.  

If Codex or Gemini is used, it will require multiple copy pastes from the various agents into their own terminal windows to fulfill the execution.

At this stage the agents are communicating over the MCP message hub as needed and the user will be able to see this in the message pane.  As the agents finish or have questions or need more directions the user will have to in the application today go into each terminal window and nudge the agents along it should be encouraged to only speak to the orchestrator's terminal window for the orchestrator to create messages either as a broadcast or to a specific agent because this allows a clawed code user to again leverage the sub agent capability and the user of codecs and Gemini all they have to do is copy paste a quick message And I mean a hand type copy paste not a button in the app to read their message or say that they have a message pending as the communications for audit and history occurs through the MCP message center.

Once the user is satisfied there is a closeout function at the bottom of the jobs pane to decommission all the agents to wrap up the project to handle git commits documentation etc.

# Tokens

We do have a token counting function in the application and the main purpose is to try to keep the product context reasonable as we know Claude Codes specifically has a limit of 25,000 tokens for input so we need to when we create the templated prom to launch the first orchestrator for to create the mission to try and limit the mission prompt sub 25,000 tokens That's why we put a limit of 2000 tokens for overall product context which we might have to modify overtime.

Once the mission is created in the Jobs pane it will also show an aggregate token count of the mission there I don't know that this is a deal breaker but it shows that we concerned and Committ to be effective but this will require a lot of tuning over time and will likely help a lot once we learn much more how we can integrate this application into terminal windows or if we end up building terminal windows right into this application.

# MCP integration

I believe we have created a smooth way to integrate MCP servers for all three products and I believe they are command lines that you run at root of the project before you start the agenda CLI tool I know we did this for Claude but we need to verify for the others I am 75% sure we did this because this is going to be a huge necessity because we are tenant based and need the API key function for it we are also documenting for the user the manual way of doing it if they want.

# API key

We have an API key function in the application for future integrations but it's primarily used today for integrating the MCP communications over HTTP and assuring that the communications go to the right tenant.

# Installation

Because this is a intended shared and downloadable products To flow from the install.py File is critical and must work in a multi OS environment between windows Linux and Mac OS this application should be ground up built for all three Oses with paths and functions.

# database

The database uses PostgresSQL With intended operation on the same machine as the application.  This is how it's been built over local host communications but there is technically no limitations to have the database elsewhere but that's not for MVP.

# Dependancies

At some point we need to harmonize dependencies and make sure we're not installing and wasting time with dependencies that we do not need anymore.

# LAN/WAN/HOSTED

The application as such should work on the same machine as a developer with local host if they want and over land and Wan with IP address out the gate I'm not quite sure how it works with DNS and host name but we should investigate this in the future.  We will also begin building it as a SaaS Service in the next quarter or so.

# Mini LLM

It would be wonderful to expand the orchestration portion to be ran as CPU or GPU micro LLM to trigger agents or activate agents on the user's workstation but we may have to end up in an Electron app or something similar in the future instead.

# Integrations

Today we have a Serena MCP integration and is a wonderful tool and we must make sure we promote it properly in settings It really helps this application do its work and the agents do their work.  Another potential is to allow for local LLM potentially through climb or even through Ollama LMStudo Or other tools.

* [Developer note] 
We need to ensure that the Serena integration is built into the prompting of all the agents

# Automations

We have discussed and explored the possibility to run background bash jobs with clawed code to regularly have orchestrator paying for new messages and check and nudge agents along and to "go to sleep" Forcing the user to remind Claude that has messages waiting but I'm not quite 100 percent sure how this would be executed practically yet.

# Dev Control Panel

The dev control panel has been a lifesaver and I'm not sure yet how to build that in to the application as administrator tool in some capacity that is something to be considered.

# How a user would work with the product

let's go through an entire user journey with the product.
The user creates an account and logs in
Agent templates are populated in their user settings
User finds their way to MCP integrations and copies the command for their agentic CLI tool of choice and that links and attaches itself to the MCP server
The user then pushes the agent's templates to their folder of choice either under the user or project if they're using clawed code
The user creates a product and defines it and uploads division slash product description
The user now creates the first project perhaps Asking the tool to prepare the foundational layout for the overall product
Perhaps in their agentic CLI tool discussing options with the AI tool and using the task function to add tasks because they don't know quite yet what decisions they want to make or how they want to use the things discussed
 what decisions they want to make or how they want to use the things discussed what decisions they want to make or how they want to use the things discussed The user decides to activate the first project and gets a launch button
 This takes them to project launch dashboard or panel where they get a prompt for the orchestrator sees their handwritten project description and copy the prompt
 They paste the prompt in the CLI tool which has been started in the project folder and the orchestrator being the first agent begins building the mission by compiling the context and the project description
 The Mission field in the Project launch window populates with the mission and Agent cards start showing up which the orchestrator has started selecting
 The user reviews everything and can choose to cancel or to proceed
 When they proceed they get to the jobs pain and in the jobs pain they will see a prompt for orchestrator for Claude code which they will copy and paste into cloud code For clawed code this will spawn subagents and they will match they already displayed agent cards on the screen which show various status and information If the orchestrator is now communicating with these agents that will start showing up in the message center
 If he's using other agentic coding tools like Codex or CLI not only does the orchestrator have a copy prompt but all the agent cards also have copy prompts and the user copies all of them individually to CLI windows to activate the agents and as the agents start working and if they are communicating that shows up in the message pane
 The user can view the progress either in the terminal CLI windows or glance at the dashboard as it keeps updating while the agents are communicating and progressing with their work
 Should the user see something he wants to address or get a notification from the orchestrator the user can either broadcast a message to all agents using the message center or queue a message for the orchestrator but naturally the user can also just chat with the orchestrator in the terminal window the benefit of doing it through the message center of MCP means that they'll be an audit and history log if the user wants it
 At some point everybody will be finished and report in that they're finished and a user can choose to closeout the project which will follow a closeout protocol such as git commits git push documentation decommissioning agents etc
 Now the user can move on to the next project that they wish
 At anytime they can go to the dashboard and sort historically by product by projects or by everything Things have been happening and if they zoom in to a project they can even see the communications that occurred between the agents and have a link to the summary document and what happened during this session They get commit references etcetera

# Welcome and Tutorial

We need to create some sort of workflow tutorial with screenshots that takes the US through how to use the product in the welcome screen.

# Notificatoins

We need to determine what type of notifications we need in the notifications bar we might even explore some sort of gamification if the user uses the product a lot that could be fun but that's just an extremely nice to have at some point messages could for when agents such as the orchestrator or other specifically wants the user's attention or if there is a in the product I'm not quite sure yet

# Password recovery

At some point we have to improve the capability of password recovery to work via email to make the authentication more secure instead of the recovery PIN

