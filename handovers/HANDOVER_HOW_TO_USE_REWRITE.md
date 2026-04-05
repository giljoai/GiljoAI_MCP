# Handover: Rewrite "How to Use GiljoAI MCP" and Retire "What is GiljoAI MCP?"

**Date:** 2026-04-04
**Priority:** High
**Estimated Complexity:** 3-5 hours
**Status:** Not Started

## Task Summary

Rewrite the "How to Use GiljoAI MCP" learning modal. Expand from 5 chapters to 6. Replace all content with the exact text specified below. Then locate and remove all code, components, and references related to the old 8-screen "What is GiljoAI MCP?" onboarding modal, which is being retired permanently.

## Context

The current "How to Use GiljoAI MCP" has five chapters with four bullets each, organized as feature categories. The revised version has six chapters with three bullets each, organized as a user journey. The restructure adds a dedicated chapter for 360 Memory (a core product behavior that was previously absent) and redistributes content so each chapter is shorter and more focused.

The old "What is GiljoAI MCP?" was an 8-screen introductory modal. It is being fully retired and all related code deleted.

## Part 1: Rewrite "How to Use GiljoAI MCP"

Replace the current content with the exact text below. Add one chapter (from 5 to 6). Reduce bullets per chapter from 4 to 3. Use the text exactly as written. Do not use emdashes anywhere.

Add a closing line after the last chapter, outside the chapter structure: "You can reopen this guide any time from User Settings."

---

### CHAPTER 1

**Title:** How GiljoAI Works

**Bullet 1:** GiljoAI MCP is a passive context server. Your AI coding tool does all reasoning and coding using your own subscription. GiljoAI stores product knowledge, generates focused prompts, and serves coordination data so your agents stay aligned.

**Bullet 2:** Your AI tool connects to GiljoAI as an MCP server over HTTP. Each tool gets its own API key and connection.

**Bullet 3:** Use Claude Code, Codex CLI, Gemini CLI, or any MCP-compatible tool simultaneously. If it can connect to an MCP server, GiljoAI accepts it.

---

### CHAPTER 2

**Title:** Define Your Product

**Bullet 1:** Create a Product to represent the software you are building. Fill in context fields: description, tech stack, architecture, testing strategy, constraints, and more.

**Bullet 2:** Enter context manually, or use a pre-generated prompt that lets your AI coding tool suggest what to include based on a vision document or product proposal.

**Bullet 3:** Context settings let you toggle fields on or off and adjust depth per source. Keep prompts lean for simple tasks or load full detail for complex missions.

---

### CHAPTER 3

**Title:** Projects and Missions

**Bullet 1:** Create Projects inside a product. Each project is a focused unit of work such as a feature, sprint, or scaffolding effort. Stage a series of projects and activate one at a time.

**Bullet 2:** Activate a project and GiljoAI generates a bootstrap prompt. Paste it into your CLI tool to kick off the orchestrator, which plans the mission and assigns agents from your templates.

**Bullet 3:** Context is assembled per session from your product fields, 360 Memory, and optional integrations. Each agent gets exactly what it needs for its role.

**AGENT VALIDATION (do not render in UI):** Verify that "activate a project" is the correct user action that triggers the bootstrap prompt. Check the project activation flow in the frontend. If activation first creates a Job and the bootstrap prompt generates from the Job view, adjust Bullet 2 wording to reflect the actual sequence.

---

### CHAPTER 4

**Title:** Skills and Agent Templates

**Bullet 1:** Two skills are installed on your machine during setup: /gil_add and /gil_get_agents (Claude Code, Gemini CLI) or $gil-add and $gil-get-agents (Codex CLI).

**Bullet 2:** Use /gil_add to capture tasks or create projects mid-session without breaking flow. Use /gil_get_agents to fetch agent templates into your workspace for subagent spawning.

**Bullet 3:** The Agent Template Manager lets you browse, customize, and create agent profiles with roles, expertise, and chain strategies. Templates export automatically for the right platform.

---

### CHAPTER 5

**Title:** 360 Memory

**Bullet 1:** Each completed project writes to 360 Memory automatically: what was built, key decisions, patterns discovered, what worked. This is not a plugin or integration. It is a core product behavior.

**Bullet 2:** Your next project starts with accumulated context from previous ones. The orchestrator reads past memories alongside your product context and project description to plan each mission.

**Bullet 3:** You control how many memories back agents read through the context settings. Optionally enrich memory with git commit history for the complete development timeline.

---

### CHAPTER 6

**Title:** Dashboard and Monitoring

**Bullet 1:** The Products, Projects, Tasks, and Jobs pages let you manage your work and track technical debt across all products.

**Bullet 2:** The Jobs page is where staging begins and agents execute. Watch their planning, to-do lists, and messages in real time.

**Bullet 3:** A message inbox lets you talk directly to the orchestrator or broadcast to the entire agent team. All messages are logged in the MCP message system for auditability.

---

**Closing line (render outside the chapter structure, at the bottom of the modal):**
You can reopen this guide any time from User Settings.

---

## Part 2: Retire "What is GiljoAI MCP?"

Search the codebase for all components, routes, data, and references related to the "What is GiljoAI MCP?" modal. This was an 8-screen onboarding modal. Look for:

- Vue components that render the 8 screens (search for text fragments: "Your orchestration server", "The problem: context limits and drift", "The solution: persistent missions", "Two working styles", "Orchestrator workflow", "Tasks keep you disciplined", "Optional power-ups", "Next: run the Setup Wizard")
- Any router entries, navigation guards, or conditional logic that triggers this modal
- Any images or assets used exclusively by this modal (including the orchestrator workflow screenshot)
- Any user preference flags or localStorage keys that track whether this modal has been shown

Delete all of it. Do not comment it out. If an image or asset is shared with other features, leave it alone; only remove assets exclusive to this modal.

## Implementation Notes

- The "How to Use" content lives in the frontend. Locate the current component that renders the 5-chapter version and replace its content with the 6-chapter version above.
- The current UI renders chapters as numbered sections with bullet items underneath. Extend this pattern to accommodate the 6th chapter.
- Preserve existing styling and component architecture. This is a content change, not a UI redesign.
- The modal auto-launches after setup completion and is also accessible from User Settings. Do not change this behavior.
- Do not add any new dependencies.

## Testing

1. Launch the application and trigger the "How to Use" modal (via fresh setup or User Settings).
2. Verify all 6 chapters render with the correct content.
3. Verify the closing line appears at the bottom outside the chapter structure.
4. Verify the old "What is GiljoAI MCP?" modal no longer appears anywhere.
5. Verify no console errors from missing components or assets after the deletion.
6. Verify the "How to Use" modal still auto-launches after setup wizard completion.
7. Verify it is re-openable from User Settings.

## Success Criteria

- The modal contains exactly 6 chapters with 3 bullets each, matching the text in this handover.
- The closing line renders at the bottom of the modal.
- All "What is GiljoAI MCP?" code, components, routes, and exclusive assets are deleted.
- No broken references, no console errors, no orphaned imports.
- The learning modal behaves identically to before (auto-launch timing, re-openable) with the new content and structure.
