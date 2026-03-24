# How CLI coding agents visually identify their subagents

**Claude Code is the only tool that assigns distinct per-subagent colors, but its implementation has regressed.** All three major CLI coding agents—Claude Code, Codex CLI, and Gemini CLI—now support multi-agent architectures, yet they take fundamentally different approaches to visually distinguishing subagent activity in the terminal. Claude Code offers user-assignable background colors per subagent but lost its colored badge system in a prompt optimization. Codex CLI uses status-based color coding (cyan, green, red) with botanical nicknames. Gemini CLI treats subagents as ordinary tool calls with no dedicated color differentiation at all.

## Claude Code pioneered per-agent colors, then partially lost them

Claude Code's custom subagent system (defined as Markdown files in `.claude/agents/*.md`) supports an explicit **`color` frontmatter field** with eight named options: red, blue, green, yellow, purple, orange, pink, and cyan. When creating a subagent via the `/agents` wizard, users are prompted to "Pick a background color for the subagent." This color renders as a **background color indicator** when the subagent is active, helping users identify which agent is running.

The more prominent visual feature—**colored badge pills** that wrapped agent names in their assigned color—was functional through v2.0.10 but was **removed in v2.0.11** (October 8, 2025). The root cause was a system prompt optimization that reduced prompt size by 1,400 tokens, inadvertently stripping the badge rendering instructions. GitHub issues #9272 and #9319 documented the regression; both were closed as duplicates, indicating Anthropic is aware but has not restored the feature as of v2.1.81 (March 2026).

In the current terminal UI, subagent outputs are **collapsed by default** behind a spinner showing the task description (e.g., `⏺ task(analyzing repository structure...)`). Users press **Ctrl+O** to expand the full subagent transcript. In expanded views, subagent messages appear **dimmed with a `↳` prefix**. The Agent Teams feature, which spawns teammates in tmux panes, assigns **bright ANSI colors** to each teammate's tmux status bar and pane border via the `--agent-color` flag, though these colors are not user-configurable. A newer `/color` command (v2.1.75, March 13, 2026) lets users set session-level prompt bar colors for distinguishing multiple parallel sessions.

## Codex CLI uses status colors and botanical nicknames, not per-agent hues

OpenAI's Codex CLI has a mature multi-agent system internally codenamed **"Collab,"** completely rebuilt in version 0.105.0 (February 2026). Its visual approach differs fundamentally from Claude Code's: rather than assigning a unique color to each subagent, Codex uses **status-dependent colors** applied uniformly across all agents.

The specific color mapping, implemented through Rust's `ratatui` framework, is:

- **Cyan bold** for running agents
- **Green** for completed agents (with a 240-character response preview)
- **Red** for errored agents (with a 160-character error preview)
- **Dim gray** for shutdown or pending agents

Agent identity is conveyed through **light blue bold nicknames** drawn from a pool of **87 botanical names** (Ash, Elm, Yew, Fir, Oak, Pine, Spruce, Cedar, and so on) paired with **dim gray bracketed roles** like `[explorer]` or `[worker]`. In the parent thread, subagent activity appears as summary cells with bullet points (`•`) and tree connector characters (`└`) creating visual hierarchy. A dedicated **Agent Picker** (accessed via `/agent` or Ctrl+A) displays all threads with green circle (🟢) or black circle (⚫) status dots.

The key distinction from Claude Code is that **Codex does not assign unique colors per subagent identity.** Two running agents named "Ash" and "Elm" both appear in cyan bold. Color encodes state, not identity. Users switch between full agent conversations through the Agent Picker, where each child thread renders as a complete, independent chat interface identical in styling to the main agent's view.

## Gemini CLI treats subagents as ordinary tool calls

Google's Gemini CLI takes the most minimalist approach. Despite having a full subagent system—including built-in agents like `codebase_investigator`, `cli_help`, `generalist_agent`, and `browser_agent`—it **does not use any color-based visual identification** to distinguish subagent output from main agent output.

Subagents are exposed to the main agent as tools, and their invocations appear in the terminal as **standard tool call UI elements**: a header with the subagent's name, wrapped in a collapsible `ToolGroupMessage` component using the theme's `border.default` and `border.focused` colors. The theme system offers customizable colors across text, background, border, status, and UI categories, but **no dedicated subagent color property exists**. All tool calls—whether `read_file`, `run_shell_command`, or `codebase_investigator`—share the same visual treatment.

The sole exception is the experimental **browser agent**, which received a **pulsating blue border overlay** (PR #21173) to indicate active browser automation. Subagent result display was improved in v0.34.0 (PR #20378) for readability, and subagent "trajectory" (internal execution history) is tracked and manageable through the UI, but these improvements operate within the same visual framework as all other tool calls.

## A three-way comparison reveals divergent design philosophies

| Feature | Claude Code | Codex CLI | Gemini CLI |
|---|---|---|---|
| **Per-agent color assignment** | Yes (8 named colors via frontmatter) | No | No |
| **Status-based coloring** | Limited (spinner) | Yes (cyan/green/red/gray) | Standard tool call status only |
| **Agent nicknames** | User-defined names | Auto-assigned botanical names | Tool/agent name from definition |
| **Subagent output display** | Collapsed with spinner; Ctrl+O to expand | Summary cells in parent; full replay in child thread | Collapsible tool call groups |
| **Agent switching** | N/A (inline display) | Agent Picker with thread switching | N/A (inline display) |
| **TUI framework** | React/Ink (Node.js) | ratatui (Rust) | React/Ink (Node.js) |
| **Multi-pane support** | Agent Teams via tmux with ANSI-colored panes | Single-pane with thread switching | Single-pane |

The three tools reflect different design priorities. Claude Code treats subagent identity as a first-class visual concept—each agent can have its own color, reflecting a model where users might run diverse specialized agents simultaneously and need to track "who said what." Codex CLI prioritizes **workflow state awareness**—knowing whether agents are running, done, or failed matters more than distinguishing one from another, and the thread-switching model means you view one agent at a time anyway. Gemini CLI prioritizes **simplicity and uniformity**, treating subagents as just another tool in the system rather than elevating them to a distinct visual tier.

## Conclusion

**Color-based per-subagent visual identification remains unique to Claude Code CLI** among the three major tools, though its implementation is incomplete—the most visible colored badge feature was removed in October 2025 and has not been restored. Codex CLI's February 2026 overhaul introduced the most structured subagent UI with status-based colors and nickname systems, but deliberately avoided per-agent color assignment. Gemini CLI's subagent display remains visually indistinguishable from any other tool call. For users who need to visually track multiple concurrent agents by identity, Claude Code's `color` frontmatter field and Agent Teams tmux coloring remain the closest thing available—but the broader trend across all three tools is toward structural differentiation (collapsing, threading, nicknames) over chromatic differentiation.