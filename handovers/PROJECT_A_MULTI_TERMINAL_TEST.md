# Project A: MCP Multi-Terminal Integration Test

**Project Title:** MCP Multi-Terminal Integration Test
**Product:** TinyTaskBoard
**Execution Mode:** Multi-terminal (each agent in a separate terminal session)

---

## Project Description

*(Copy everything below this line into the Project Description field in the GiljoAI MCP dashboard)*

---

This is an integration test for the GiljoAI MCP toolchain running in multi-terminal mode. The orchestrator and each agent run in separate terminal sessions. The working directory (TinyTaskBoard) is the sandbox -- the real subject under test is the MCP server, its tools, protocol injections, context delivery, and inter-agent communication.

### Objective

Validate that the GiljoAI MCP platform correctly coordinates agents across independent terminal sessions regardless of which CLI tool is running each role.

### Team Composition

Orchestrator + 2 specialist agents (implementer, tester). If fewer than 2 specialist templates are available, duplicate any available template with a unique display name.

### What Each Agent Should Do

All work is simulated. Agents are testing the MCP toolchain, not building TinyTaskBoard.

**Agent 1 (Implementer):**
- Fetch its mission via MCP tools
- Simulate work by running a 30-second bash sleep command
- At the midpoint (~15 seconds), send a progress message to the orchestrator
- On completion, send a message to the tester agent signaling that implementation is done
- Write a test report file to the working directory (see report template below)

**Agent 2 (Tester):**
- Wait for the implementer's completion message before starting its own work
- Fetch its mission via MCP tools
- Simulate work by running a 20-second bash sleep command
- Send a broadcast message to all agents when starting its work
- On completion, send a message to the orchestrator signaling that testing is done
- Write a test report file to the working directory (see report template below)

### Orchestrator Responsibilities

- Execute the staging workflow: fetch product core, vision documents, tech stack, and architecture via MCP context tools
- Generate a mission from the product context and this project description
- Spawn agent jobs with initial status "waiting"
- Monitor agent progress at approximately 15-second intervals
- If any agent reports a block or error, respond with guidance to clear it
- Confirm all agents reach "completed" status before closing the project

### Required Status Transitions

Each agent must move through these states visibly on the dashboard:

waiting --> working --> completed

Additionally, at least one agent must simulate a blocked state:
- Call report_error with a simulated issue (e.g., "Simulated dependency conflict for testing")
- Send a message to the orchestrator describing the block
- Wait for the orchestrator to respond with guidance
- After receiving guidance, resume work and proceed to completed

### Agent Report Template

Each agent writes a file named `agent-report-{role}.md` (e.g., `agent-report-implementer.md`) in the working directory. The report must cover:

1. **IDENTITY:** What role was I assigned? What is my agent ID and job ID?

2. **CONTEXT:** Did I receive enough context to understand my work? What MCP tools did I use to fetch context? Was the product and project context accurate?

3. **PROTOCOL INJECTION:** Did I receive clear instructions from the protocol injection (separate from the orchestrator's mission text)? Specifically:
   - Did it explain I am part of an MCP-coordinated workflow?
   - Did it explain I am running in my own terminal session, independently?
   - Did it explain that other agents in this project may be running in different CLI tools?
   - Did it explain how to use MCP messaging to communicate?

4. **COMMUNICATION:** Was I able to send messages? Did I receive messages from other agents? Did I see any broadcast messages from the user? List each message sent and received with timestamps if available.

5. **ORCHESTRATOR:** Did I understand the orchestrator's role as coordinator? Were the orchestrator's instructions distinct from the protocol injection instructions?

6. **COMPLETION PROTOCOL:** Did the protocol injection explain how to signal that I finished my work? Did it explain how to request user input if I needed it?

7. **MCP TOOL LOG:** List every MCP tool I called during this session. For each: tool name, whether it succeeded or failed, and any error messages returned.

8. **RECOMMENDATIONS:** What would improve this experience? Were there gaps in the protocol injection, missing context, or confusing instructions?

### Test Execution Notes

This project is designed to be run multiple times across different CLI platforms:

- Run 1: Orchestrator on Claude Code, agents on Claude Code + Codex
- Run 2: Orchestrator on Codex CLI, agents on Codex + Claude Code
- Run 3: Orchestrator on Gemini CLI, agents on Gemini + Claude Code

The project description does not reference any specific CLI tool. Platform-specific behavior comes from the protocol injection and prompt assembler, not from this description. Each run should produce directly comparable results.

Between runs, cancel/reset the project and verify that agent jobs, messages, and mission data are cleanly cleared before re-staging.
