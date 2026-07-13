## Chain Projects

A **chain** links several projects together and runs them one after another under a single overarching goal. It is the tool for work that is too big for one project but has a natural order — for example, scaffold a service, then build the feature on top of it, then add tests. A chain is multi-project and single-user: it coordinates your own projects; it is not a shared-team feature.

Each project in a chain keeps its own description, agents, and 360 Memory entry. What the chain adds is a coordinator that launches them in order so you do not have to start each one by hand.

### Linking Projects

Linking is the act of attaching projects together into a chain.

1. Go to **Projects** in the left navigation.
2. Click the chain-link button in the toolbar (**"Link projects (chain mode)"**). A **Linked** checkbox column appears in the project table.
3. Tick the projects you want in the chain. A chain holds **2 to 5 projects** — a hint appears if you have selected too few or too many.

The order you want the projects to run in is the order they carry in the table. Projects already locked into a running chain are shown as unavailable so you cannot double-book them.

### Launching a Chain

Once you have linked 2 to 5 projects, an action bar appears at the top of the project list with a launch button (labeled **"Run sequential"**, with a count such as 3/5). Click it to start the chain. From that point the **conductor** takes over: it stages and launches the first project, waits for it to finish, then advances to the next, until every linked project is complete.

### The Conductor

The **conductor** — also called the chain orchestrator or master orchestrator — is the coordinator that drives the chain. It is a dedicated agent that owns no project of its own; its only job is to run the chain in order: launch each project, watch for completion, and advance to the next. During staging you see it as the **Chain Conductor** card, showing its identity and current status (Waiting, Running, Done).

### The Chain Mission

The **chain mission** is the overarching goal for the whole chain — the single objective that all the linked projects serve together. It is distinct from each project's own per-project mission. During staging, the chain mission appears in its own window above the project tabs so the goal of the entire run stays visible while individual projects execute.

### Monitoring a Chain

While a chain runs, the **Jobs** page shows a **Multi project mode** indicator and an **N/M counter** — the number of projects completed out of the total in the chain. The counter advances as each project closes out. You monitor the currently running project exactly as you would a solo project: agent status, step progress, and messages all work the same way.

### Stopping a Chain

To stop a chain and return its projects to their prior state, use **Deactivate Chain** on the Projects page. This rewinds all linked projects out of the run; you can re-link and relaunch when you are ready. Completed projects keep their results and 360 Memory entries.

For guidance on *whether* a chain is the right choice versus a single project, see **When to Use What**.
