# Project B: MCP Subagent Mode Integration Test

**Project Title:** MCP Subagent Mode Integration Test
**Product:** TinyTaskBoard
**Execution Mode:** Subagent (orchestrator spawns agents within a single CLI session)

---

## Project Description

*(Copy everything below this line into the Project Description field in the GiljoAI MCP dashboard)*

---

This is an integration test for the GiljoAI MCP toolchain running in subagent mode. The orchestrator runs in a single CLI session and spawns specialist agents as subagents within that same session. The working directory (TinyTaskBoard) is the sandbox -- the real subject under test is the MCP server, its tools, protocol injections, context delivery, and inter-agent communication when agents share a session with the orchestrator.

### Objective

Validate that the GiljoAI MCP platform correctly delivers context and coordinates agents when the orchestrator spawns subagents natively within a single CLI session, using the CLI's own subagent mechanism.

### Team Composition

Orchestrator + 2 specialist subagents (implementer, tester). The orchestrator spawns these using the CLI's native subagent capability. If the CLI supports parallel subagent execution, both may run concurrently. If the CLI only supports sequential subagents, agents should run one after the other.

### What Each Agent Should Do

All work is simulated. Agents are testing the MCP toolchain, not building TinyTaskBoard.

**Subagent 1 (Implementer):**
- Fetch its mission via MCP tools
- Simulate work by running a 30-second bash sleep command
- At the midpoint (~15 seconds), send a progress message to the orchestrator via MCP messaging
- On completion, send a message to the tester agent signaling that implementation is done
- Write a test report file to the working directory (see report template below)

**Subagent 2 (Tester):**
- Wait for the implementer's completion message before starting its own work (in sequential CLIs, this ordering happens naturally)
- Fetch its mission via MCP tools
- Simulate work by running a 20-second bash sleep command
- Send a broadcast message to all agents when starting its work
- On completion, send a message to the orchestrator signaling that testing is done
- Write a test report file to the working directory (see report template below)

### Orchestrator Responsibilities

- Execute the staging workflow: fetch product core, vision documents, tech stack, and architecture via MCP context tools
- Generate a mission from the product context and this project description
- Spawn subagents using the CLI's native subagent mechanism
- For CLIs supporting background execution: spawn both subagents in background mode and monitor their progress
- For CLIs with sequential-only execution: spawn the implementer first, wait for completion, then spawn the tester
- Confirm all subagents reach "completed" status before closing the project

### Required Status Transitions

Each subagent must move through these states visibly on the dashboard:

waiting --> working --> completed

Additionally, at least one subagent must simulate a blocked state:
- Call report_error with a simulated issue (e.g., "Simulated test environment failure for testing")
- Send a message to the orchestrator describing the block
- Wait for the orchestrator to respond with guidance
- After receiving guidance, resume work and proceed to completed

Note: In subagent mode, the orchestrator may need to actively check for blocked agents since subagents may not be able to interrupt the orchestrator's flow. The orchestrator should poll for error states if the CLI does not support asynchronous notifications from subagents.

### Agent Report Template

Each subagent writes a file named `agent-report-{role}.md` (e.g., `agent-report-implementer.md`) in the working directory. The report must cover:

1. **IDENTITY:** What role was I assigned? What is my agent ID and job ID?

2. **CONTEXT:** Did I receive enough context to understand my work? What MCP tools did I use to fetch context? Was the product and project context accurate?

3. **PROTOCOL INJECTION:** Did I receive clear instructions from the protocol injection (separate from the orchestrator's mission text)? Specifically:
   - Did it explain I am part of an MCP-coordinated workflow?
   - Did it explain I am running as a subagent within the orchestrator's CLI session?
   - Did it explain that I should use MCP messaging for communication even though I share a session with the orchestrator?
   - Did it explain the difference between talking to the orchestrator via MCP messages versus being inside the orchestrator's session?

4. **COMMUNICATION:** Was I able to send messages via MCP tools? Did I receive messages from other agents? Did I see any broadcast messages from the user? Did MCP messaging work correctly in subagent mode, or did the shared session cause any confusion or message delivery issues? List each message sent and received.

5. **ORCHESTRATOR:** Did I understand the orchestrator's role as coordinator? Were the orchestrator's instructions distinct from the protocol injection instructions? Was there any confusion about whether I was "talking to" the orchestrator directly (as a subagent) versus communicating via MCP messaging?

6. **COMPLETION PROTOCOL:** Did the protocol injection explain how to signal that I finished my work? Did it explain how to request user input if I needed it? Was the completion flow clear in subagent mode?

7. **MCP TOOL LOG:** List every MCP tool I called during this session. For each: tool name, whether it succeeded or failed, and any error messages returned.

8. **RECOMMENDATIONS:** What would improve this experience? Were there gaps in the protocol injection for subagent mode specifically? Did anything behave differently than expected compared to what the protocol described?

### Test Execution Notes

This project is designed to be run multiple times across different CLI platforms:

- Run 1: Claude Code (orchestrator spawns subagents via Agent tool, background mode)
- Run 2: Codex CLI (orchestrator spawns subagents via spawn_agent, parallel execution)
- Run 3: Gemini CLI (orchestrator delegates via delegate_to_agent, sequential execution)

**Expected platform differences:**
- Claude Code supports parallel background subagents and MCP tool inheritance
- Codex CLI supports parallel execution with configurable max_threads
- Gemini CLI currently runs subagents sequentially (blocking). The tester naturally waits for the implementer to finish. Expect this run to take longer and potentially surface MCP tool naming issues (qualified tool name format)

The project description does not reference any specific CLI tool. Platform-specific behavior comes from the protocol injection and prompt assembler, not from this description. Each run should produce directly comparable results, with expected variance in execution timing and subagent spawning behavior.

Between runs, cancel/reset the project and verify that agent jobs, messages, and mission data are cleanly cleared before re-staging.
