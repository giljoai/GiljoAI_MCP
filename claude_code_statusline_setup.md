# Claude Code Status Line Setup

Instructions for configuring a custom status line below the chat input in Claude Code CLI.

## Prerequisites

- Claude Code CLI installed
- `jq` installed (`sudo apt install jq`)
- `bc` installed (`sudo apt install bc`)

## Step 1: Create the status line script

Create `~/.claude/statusline.sh` with the following content and make it executable:

```bash
chmod +x ~/.claude/statusline.sh
```

### Script content (`~/.claude/statusline.sh`)

```bash
#!/bin/bash
# Claude Code Status Line - Shows model, directory, git branch, context usage, tokens, cost, duration, lines changed
input=$(cat)

MODEL=$(echo "$input" | jq -r '.model.display_name // "?"')
DIR=$(echo "$input" | jq -r '.workspace.current_dir // "?"')
PROJ_DIR=$(echo "$input" | jq -r '.workspace.project_dir // ""')
COST=$(echo "$input" | jq -r '.cost.total_cost_usd // 0')
PCT=$(echo "$input" | jq -r '.context_window.used_percentage // 0' | cut -d. -f1)
CTX_SIZE=$(echo "$input" | jq -r '.context_window.context_window_size // 0')
INPUT_TOKENS=$(echo "$input" | jq -r '.context_window.total_input_tokens // 0')
OUTPUT_TOKENS=$(echo "$input" | jq -r '.context_window.total_output_tokens // 0')
DURATION_MS=$(echo "$input" | jq -r '.cost.total_duration_ms // 0')
LINES_ADD=$(echo "$input" | jq -r '.cost.total_lines_added // 0')
LINES_DEL=$(echo "$input" | jq -r '.cost.total_lines_removed // 0')

# Colors
CYAN='\033[36m'
GREEN='\033[32m'
YELLOW='\033[33m'
RED='\033[31m'
DIM='\033[2m'
BOLD='\033[1m'
RESET='\033[0m'

# Context bar color based on usage
if [ "$PCT" -ge 90 ]; then BAR_COLOR="$RED"
elif [ "$PCT" -ge 70 ]; then BAR_COLOR="$YELLOW"
else BAR_COLOR="$GREEN"; fi

# Build progress bar (20 chars wide)
FILLED=$((PCT / 5))
EMPTY=$((20 - FILLED))
printf -v FILL "%${FILLED}s"
printf -v PAD "%${EMPTY}s"
BAR="${FILL// /█}${PAD// /░}"

# Format cost
COST_FMT=$(printf '$%.4f' "$COST")

# Format duration
MINS=$((DURATION_MS / 60000))
SECS=$(((DURATION_MS % 60000) / 1000))

# Format context window size (e.g., 200K, 1M)
if [ "$CTX_SIZE" -ge 1000000 ]; then
    CTX_LABEL="$(( CTX_SIZE / 1000000 ))M"
elif [ "$CTX_SIZE" -gt 0 ]; then
    CTX_LABEL="$(( CTX_SIZE / 1000 ))K"
else
    CTX_LABEL="?"
fi

# Format token counts with K/M suffix
format_tokens() {
    local t=$1
    if [ "$t" -ge 1000000 ]; then
        printf "%.1fM" "$(echo "scale=1; $t / 1000000" | bc)"
    elif [ "$t" -ge 1000 ]; then
        printf "%.1fK" "$(echo "scale=1; $t / 1000" | bc)"
    else
        echo "$t"
    fi
}

IN_FMT=$(format_tokens "$INPUT_TOKENS")
OUT_FMT=$(format_tokens "$OUTPUT_TOKENS")
TOTAL_TOKENS=$((INPUT_TOKENS + OUTPUT_TOKENS))
TOTAL_FMT=$(format_tokens "$TOTAL_TOKENS")

# Git branch
BRANCH=""
if git rev-parse --git-dir > /dev/null 2>&1; then
    BRANCH=$(git branch --show-current 2>/dev/null)
fi

# Shorten directory path
SHORT_DIR="${DIR/#$HOME/~}"

# Line 1: Model, directory, git branch
LINE1="${CYAN}${BOLD}[${MODEL}]${RESET} ${SHORT_DIR}"
if [ -n "$BRANCH" ]; then
    LINE1="${LINE1} ${DIM}|${RESET} ${GREEN}${BRANCH}${RESET}"
fi

# Line 2: Context bar, tokens, cost, duration, lines changed
LINE2="${BAR_COLOR}${BAR}${RESET} ${PCT}%/${CTX_LABEL}"
LINE2="${LINE2} ${DIM}|${RESET} ${BOLD}${TOTAL_FMT}${RESET} ${DIM}(in:${IN_FMT} out:${OUT_FMT})${RESET}"
LINE2="${LINE2} ${DIM}|${RESET} ${YELLOW}${COST_FMT}${RESET}"
LINE2="${LINE2} ${DIM}|${RESET} ${MINS}m${SECS}s"
if [ "$LINES_ADD" -gt 0 ] || [ "$LINES_DEL" -gt 0 ]; then
    LINE2="${LINE2} ${DIM}|${RESET} ${GREEN}+${LINES_ADD}${RESET}/${RED}-${LINES_DEL}${RESET}"
fi

echo -e "$LINE1"
echo -e "$LINE2"
```

## Step 2: Configure Claude Code settings

Edit `~/.claude/settings.json` and add (or merge) the `statusLine` block:

```json
{
  "statusLine": {
    "type": "command",
    "command": "~/.claude/statusline.sh",
    "padding": 1
  }
}
```

If the file already has other settings, just add the `"statusLine"` key alongside them.

## Step 3: Restart Claude Code

Close and reopen Claude Code. The status line will appear below the input area showing two lines:

```
[Opus 4.6] ~/projects/my-repo | master
████████████░░░░░░░░ 60%/1M | 245.3K (in:220.1K out:25.2K) | $0.1234 | 3m22s | +42/-7
```

### What each field shows

| Field | Description |
|---|---|
| `[Model]` | Active model name (cyan, bold) |
| Path | Working directory (shortened with `~`) |
| Branch | Current git branch (green) |
| Progress bar | Context window usage — green (<70%), yellow (70-89%), red (90%+) |
| `%/size` | Percentage used / context window size |
| Tokens | Total tokens with input/output breakdown |
| Cost | Session cost in USD |
| Duration | Session time elapsed |
| `+N/-N` | Lines added/removed (only shown if > 0) |

## How it works

Claude Code pipes a JSON object with session metadata into the script's stdin. The script parses it with `jq`, formats the values, and outputs ANSI-colored text. Claude Code renders whatever the script prints as the status line.

The JSON input includes fields under `.model`, `.workspace`, `.cost`, and `.context_window` — the script extracts what it needs from each.
