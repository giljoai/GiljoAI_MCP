# Gemini CLI subagents remain experimental in March 2026

**Custom user-defined subagents in Gemini CLI have not reached general availability.** As of v0.34.0 (released March 17, 2026), all official documentation, the configuration schema, and the `/agents` command explicitly label the subagent framework as experimental. However, a critical nuance exists: **built-in agents work without any experimental flag**, while custom and remote agents technically require it — though the flag now defaults to `true`, meaning most users never need to set it manually.

## The experimental flag persists but defaults to enabled

The `experimental.enableAgents` setting was introduced on **December 3, 2025** via PR #14371 on the google-gemini/gemini-cli repository. It controls activation of both local custom agents (defined as `.md` files in `.gemini/agents/`) and remote agents using the A2A protocol. The setting remains nested under the `experimental` object in `settings.json`:

```json
{
  "experimental": { "enableAgents": true }
}
```

At some point between its introduction and the current documentation, **the default value was changed from `false` to `true`**. The official configuration reference at geminicli.com now states: "Enable local and remote subagents. Default: true. Requires restart: Yes." The subagents documentation page echoes this, noting custom agents must be enabled but adding the parenthetical "(enabled by default)."

This creates a somewhat confusing situation. The feature is labeled experimental and lives under the `experimental` namespace, yet it ships enabled out of the box. Users don't need to add anything to their `settings.json` for custom agents to work — but the framework is still officially unstable, and the configuration path signals that clearly.

## Built-in agents bypass the experimental gate entirely

There is a **firm architectural distinction** between built-in and custom agents regarding the experimental flag. GitHub Issue #20436 states directly: "built-in subagents are not guarded behind the experimental flag." The three primary built-in agents — **codebase_investigator**, **cli_help**, and **generalist_agent** — are hardcoded modules imported directly in the `AgentRegistry` class (`packages/core/src/agents/registry.ts`), not loaded from the filesystem like custom agents.

| Agent type | Examples | Requires experimental flag? | Status |
|---|---|---|---|
| Built-in | codebase_investigator, cli_help, generalist_agent | **No** — always available | Stable, enabled by default |
| Browser agent | browser_agent | Separate flag required | Preview, disabled by default |
| Custom local | User `.md` files in `.gemini/agents/` | Yes (defaults to `true`) | Experimental |
| Remote (A2A) | External agent services | Yes (defaults to `true`) | Experimental |

This explains why users often observe built-in agents working seamlessly while custom agents appear to require additional configuration. In practice, since the flag now defaults to `true`, both work out of the box in fresh installations — but the underlying code paths differ.

## No GA promotion despite rapid development

Across **12 releases from v0.23.0 through v0.34.0** (January–March 2026), no changelog entry, release note, or pull request documents a transition of the subagent framework from experimental to stable. The documentation sidebar consistently marks both "Subagents 🔬" and "Remote subagents 🔬" with the experimental microscope icon.

Notably, a related feature — the `--experimental-acp` flag — *was* graduated to `--acp` in v0.33.0 (March 11, 2026, PR #21171), proving Google does explicitly promote features out of experimental status when ready. No equivalent change has been made for `enableAgents`. A separate but often confused feature, **Agent Skills** (`.gemini/skills/`), was promoted to stable and enabled by default in v0.26.0 (January 27, 2026) — but skills and subagents are distinct features.

GitHub Discussion #12832, titled "Prioritize and Expose the Experimental Agent Framework," directly asked the team about a GA roadmap. No official response with a timeline was posted. Maintainers in Discussion #18106 characterize the feature as under "active development."

## Active development signals eventual graduation

The velocity of agent-related changes suggests the team is building toward stability. Recent milestones include **subagent tool isolation** (PR #22708 in v0.34.0), an **AgentSession abstraction** (PR #22270), **memory and JIT context injection into subagents**, HTTP authentication for A2A remote agents (v0.33.0), and a policy engine for subagents. Known bugs like agents hanging indefinitely (Issue #18064) and subagents failing to call MCP tools (Issue #17005) likely contribute to the experimental label persisting.

Custom agents are defined as **Markdown files with YAML frontmatter**, placed at either the project level (`.gemini/agents/*.md`) or user level (`~/.gemini/agents/*.md`). Earlier TOML-based definitions have been superseded. Folder trust verification is enforced for project-level agents, adding a security layer that further explains the cautious rollout.

## Conclusion

The practical impact of the experimental label is minimal for most users today — **custom subagents work by default** since `enableAgents` defaults to `true` as of recent versions. The distinction matters primarily for stability guarantees: the API surface for defining custom agents, the YAML frontmatter schema, and the agent execution model may all change without notice. Built-in agents like codebase_investigator and cli_help operate on a separate, stable code path and have never required the experimental flag. For teams building workflows around custom agents, the key risk is not that the feature will be removed but that its interface may shift as it matures toward an eventual GA release — which, based on development velocity, appears likely in a future 2026 release but has no announced timeline.