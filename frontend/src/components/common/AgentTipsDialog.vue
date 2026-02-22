<template>
  <div class="agent-lab-trigger">
    <v-tooltip location="bottom">
      <template #activator="{ props: tooltipProps }">
        <v-btn
          v-bind="tooltipProps"
          icon
          size="small"
          variant="text"
          class="lab-btn"
          @click="showDialog = true"
        >
          <v-icon size="23">mdi-flask-outline</v-icon>
        </v-btn>
      </template>
      <span>Agent Lab</span>
    </v-tooltip>

    <v-dialog v-model="showDialog" max-width="680" scrollable>
      <v-card v-draggable class="lab-dialog-card">
        <v-card-title class="d-flex align-center lab-header">
          <v-icon class="mr-2" size="22" color="#ffc300">mdi-flask-outline</v-icon>
          <span>Agent Lab</span>
          <v-spacer />
          <v-btn icon="mdi-close" variant="text" size="small" @click="showDialog = false" />
        </v-card-title>

        <v-divider />

        <v-card-text class="lab-content pa-4">
          <!-- Manual paste disclaimer -->
          <v-alert type="info" variant="tonal" density="compact" class="mb-4">
            <strong>Manual integration only.</strong> These are suggestions you copy-paste
            into your <strong>project description</strong> or agent missions. Nothing here
            is auto-applied.
          </v-alert>

          <v-expansion-panels variant="accordion" class="lab-panels">
            <!-- Chapter 1: Monitoring Agents -->
            <v-expansion-panel>
              <v-expansion-panel-title>
                <v-icon size="18" class="mr-2">mdi-eye-outline</v-icon>
                Monitoring Agents
              </v-expansion-panel-title>
              <v-expansion-panel-text>
                <p class="mb-3">
                  By default, the orchestrator stages agents and exits. To have it actively
                  monitor agent status and interactions, add polling instructions to your
                  <strong>project description</strong>.
                </p>

                <div class="tip-box mb-3">
                  <div class="tip-label">Paste into project description:</div>
                  <code class="tip-code">After staging, monitor all agents by polling their status every 30 seconds using bash sleep. Check for status changes, new messages, and blocked agents. Report a summary after each poll cycle.</code>
                  <v-btn
                    size="x-small"
                    variant="text"
                    class="copy-btn"
                    @click="copyText('After staging, monitor all agents by polling their status every 30 seconds using bash sleep. Check for status changes, new messages, and blocked agents. Report a summary after each poll cycle.')"
                  >
                    <v-icon size="14">mdi-content-copy</v-icon>
                  </v-btn>
                </div>

                <v-alert type="warning" variant="tonal" density="compact" class="mb-2">
                  <strong>Token cost:</strong> Each poll cycle uses ~14K tokens (~12% of budget).
                  Use sparingly for long-running projects.
                </v-alert>

                <p class="text-caption text-medium-emphasis">
                  Works in both single-terminal (subagent) and multi-terminal mode.
                  All major CLI agents (Claude Code, Codex, Gemini) support bash sleep polling.
                </p>
              </v-expansion-panel-text>
            </v-expansion-panel>

            <!-- Chapter 2: Multi-Terminal Chain Execution -->
            <v-expansion-panel>
              <v-expansion-panel-title>
                <v-icon size="18" class="mr-2">mdi-monitor-multiple</v-icon>
                Multi-Terminal Chains
              </v-expansion-panel-title>
              <v-expansion-panel-text>
                <p class="mb-3">
                  Chain multiple terminal sessions that execute sequentially, each spawning
                  the next upon completion. Useful for large projects with distinct phases.
                </p>

                <div class="tip-section mb-3">
                  <div class="tip-subtitle">How it works:</div>
                  <ol class="tip-list">
                    <li>Each terminal runs one handover with a colored tab for visual tracking</li>
                    <li>A chain log JSON file passes context between sessions</li>
                    <li>On completion, the agent spawns the next terminal automatically</li>
                  </ol>
                </div>

                <div class="tip-section mb-3">
                  <div class="tip-subtitle">Color scheme:</div>
                  <div class="color-chips">
                    <span class="color-chip" style="background: #4CAF50;">DB</span>
                    <span class="color-chip" style="background: #2196F3;">Backend</span>
                    <span class="color-chip" style="background: #9C27B0;">Frontend</span>
                    <span class="color-chip" style="background: #FF9800;">Testing</span>
                    <span class="color-chip" style="background: #F44336;">Final</span>
                  </div>
                </div>

                <!-- Tool selector -->
                <div class="tool-selector mb-3">
                  <div class="tip-subtitle">CLI tool:</div>
                  <v-chip-group v-model="selectedTool" mandatory selected-class="tool-chip-active">
                    <v-chip size="small" value="claude" variant="outlined">Claude Code</v-chip>
                    <v-chip size="small" value="codex" variant="outlined">Codex</v-chip>
                    <v-chip size="small" value="gemini" variant="outlined">
                      Gemini
                      <v-icon size="12" color="warning" class="ml-1">mdi-alert-circle</v-icon>
                    </v-chip>
                  </v-chip-group>
                </div>

                <!-- Claude Code spawn -->
                <div v-if="selectedTool === 'claude'" class="tip-box mb-3">
                  <div class="tip-label">Spawn command (PowerShell):</div>
                  <code class="tip-code">powershell.exe -Command "Start-Process wt -ArgumentList '--title ""TITLE"" --tabColor ""#HEX"" -d ""WORKDIR"" cmd /k claude -p ""PROMPT"" --dangerously-skip-permissions' -Verb RunAs"</code>
                </div>

                <!-- Codex spawn -->
                <div v-if="selectedTool === 'codex'" class="tip-box mb-3">
                  <div class="tip-label">Spawn command (PowerShell):</div>
                  <code class="tip-code">powershell.exe -Command "Start-Process wt -ArgumentList '--title ""TITLE"" --tabColor ""#HEX"" -d ""WORKDIR"" cmd /k codex exec ""PROMPT"" --yolo' -Verb RunAs"</code>
                  <p class="text-caption text-medium-emphasis mt-2 mb-0">
                    Codex sandbox is experimental on Windows. WSL2 recommended for reliability.
                  </p>
                </div>

                <!-- Gemini spawn -->
                <div v-if="selectedTool === 'gemini'" class="tip-box mb-3">
                  <div class="tip-label">Spawn command (PowerShell):</div>
                  <code class="tip-code">powershell.exe -Command "Start-Process wt -ArgumentList '--title ""TITLE"" --tabColor ""#HEX"" -d ""WORKDIR"" cmd /k gemini -p ""PROMPT"" --yolo' -Verb RunAs"</code>
                  <v-alert type="warning" variant="tonal" density="compact" class="mt-2">
                    <strong>Known bug:</strong> Gemini's <code>--yolo</code> flag still prompts
                    for plan approval despite being enabled (issue #13561). Not reliable for
                    unattended chains yet.
                  </v-alert>
                </div>

                <div class="tip-section mb-2">
                  <div class="tip-subtitle">Key tips:</div>
                  <ul class="tip-list">
                    <li>Keep launch prompts slim &mdash; point to the handover document</li>
                    <li>Include "Use Bash tool to RUN" to prevent agents from just printing commands</li>
                    <li>
                      Auto-approve flag:
                      <code v-if="selectedTool === 'claude'">--dangerously-skip-permissions</code>
                      <code v-else-if="selectedTool === 'codex'">--yolo</code>
                      <code v-else>--yolo</code>
                    </li>
                    <li>Store chain logs in <code>prompts/{project}_chain/chain_log.json</code></li>
                  </ul>
                </div>
              </v-expansion-panel-text>
            </v-expansion-panel>

            <!-- Chapter 3: Sample Prompts -->
            <v-expansion-panel>
              <v-expansion-panel-title>
                <v-icon size="18" class="mr-2">mdi-text-box-outline</v-icon>
                Sample Prompts
              </v-expansion-panel-title>
              <v-expansion-panel-text>
                <p class="mb-3 text-medium-emphasis">
                  Copy these into your <strong>project description</strong> or agent missions.
                  These are not auto-applied &mdash; paste them manually where needed.
                </p>

                <!-- Tool selector for prompts -->
                <div class="tool-selector mb-3">
                  <div class="tip-subtitle">Adapt for:</div>
                  <v-chip-group v-model="selectedPromptTool" mandatory selected-class="tool-chip-active">
                    <v-chip size="small" value="claude" variant="outlined">Claude Code</v-chip>
                    <v-chip size="small" value="codex" variant="outlined">Codex</v-chip>
                    <v-chip size="small" value="gemini" variant="outlined">Gemini</v-chip>
                  </v-chip-group>
                </div>

                <div class="tip-box mb-3">
                  <div class="tip-label">Subagent delegation:</div>
                  <code class="tip-code">{{ subagentPrompt }}</code>
                  <v-btn
                    size="x-small"
                    variant="text"
                    class="copy-btn"
                    @click="copyText(subagentPrompt)"
                  >
                    <v-icon size="14">mdi-content-copy</v-icon>
                  </v-btn>
                </div>

                <div class="tip-box mb-3">
                  <div class="tip-label">Prerequisite check:</div>
                  <code class="tip-code">Before starting work, verify that all prerequisites from the previous phase are complete. Read the chain log and check git status for expected changes.</code>
                  <v-btn
                    size="x-small"
                    variant="text"
                    class="copy-btn"
                    @click="copyText('Before starting work, verify that all prerequisites from the previous phase are complete. Read the chain log and check git status for expected changes.')"
                  >
                    <v-icon size="14">mdi-content-copy</v-icon>
                  </v-btn>
                </div>

                <div class="tip-box mb-2">
                  <div class="tip-label">Completion checklist:</div>
                  <code class="tip-code">Before reporting completion: 1) Run all tests, 2) Check for lint errors, 3) Verify no untracked files left behind, 4) Update the chain log with your results.</code>
                  <v-btn
                    size="x-small"
                    variant="text"
                    class="copy-btn"
                    @click="copyText('Before reporting completion: 1) Run all tests, 2) Check for lint errors, 3) Verify no untracked files left behind, 4) Update the chain log with your results.')"
                  >
                    <v-icon size="14">mdi-content-copy</v-icon>
                  </v-btn>
                </div>
              </v-expansion-panel-text>
            </v-expansion-panel>

            <!-- Chapter 4: CLI Quick Reference -->
            <v-expansion-panel>
              <v-expansion-panel-title>
                <v-icon size="18" class="mr-2">mdi-console</v-icon>
                CLI Quick Reference
              </v-expansion-panel-title>
              <v-expansion-panel-text>
                <table class="ref-table">
                  <thead>
                    <tr>
                      <th></th>
                      <th>Claude Code</th>
                      <th>Codex</th>
                      <th>Gemini</th>
                    </tr>
                  </thead>
                  <tbody>
                    <tr>
                      <td class="ref-label">Prompt</td>
                      <td><code>-p "..."</code></td>
                      <td><code>exec "..."</code></td>
                      <td><code>-p "..."</code></td>
                    </tr>
                    <tr>
                      <td class="ref-label">Auto-approve</td>
                      <td><code>--dangerously-skip-permissions</code></td>
                      <td><code>--yolo</code></td>
                      <td><code>--yolo</code> *</td>
                    </tr>
                    <tr>
                      <td class="ref-label">Model</td>
                      <td><code>--model sonnet</code></td>
                      <td><code>--model gpt-5-codex</code></td>
                      <td><code>-m gemini-2.5-pro</code></td>
                    </tr>
                    <tr>
                      <td class="ref-label">Turn limit</td>
                      <td><code>--max-turns N</code></td>
                      <td>config-based</td>
                      <td>N/A</td>
                    </tr>
                    <tr>
                      <td class="ref-label">Windows</td>
                      <td>Stable</td>
                      <td>Experimental</td>
                      <td>npm</td>
                    </tr>
                  </tbody>
                </table>
                <p class="text-caption text-medium-emphasis mt-2">
                  * Gemini <code>--yolo</code> has a known bug &mdash; may still prompt for approval.
                </p>
              </v-expansion-panel-text>
            </v-expansion-panel>
          </v-expansion-panels>
        </v-card-text>
      </v-card>
    </v-dialog>

    <!-- Copy success snackbar -->
    <v-snackbar v-model="showCopied" :timeout="1500" color="success" location="top">
      <v-icon start size="small">mdi-check</v-icon>
      Copied to clipboard
    </v-snackbar>
  </div>
</template>

<script setup>
import { ref, computed } from 'vue'

const showDialog = ref(false)
const showCopied = ref(false)
const selectedTool = ref('claude')
const selectedPromptTool = ref('claude')

const subagentPrompts = {
  claude: 'Use the Task tool to spawn specialized subagents for each phase. Do NOT do all work directly - delegate to database-expert, tdd-implementor, frontend-tester, etc. as appropriate.',
  codex: 'Break the work into focused subtasks. Use multiple targeted prompts rather than one large prompt. Delegate distinct phases (database, backend, frontend, testing) to separate Codex sessions.',
  gemini: 'Break the work into focused subtasks. Use separate Gemini sessions for distinct phases (database, backend, frontend, testing) to keep context clean and focused.',
}

const subagentPrompt = computed(() => subagentPrompts[selectedPromptTool.value])

async function copyText(text) {
  try {
    await navigator.clipboard.writeText(text)
    showCopied.value = true
  } catch {
    const textarea = document.createElement('textarea')
    textarea.value = text
    document.body.appendChild(textarea)
    textarea.select()
    document.execCommand('copy')
    document.body.removeChild(textarea)
    showCopied.value = true
  }
}
</script>

<style scoped lang="scss">
.agent-lab-trigger {
  display: inline-flex;
  align-items: center;
}

.lab-btn {
  color: #ffc300;
  transition: opacity 0.2s ease;

  &:hover {
    opacity: 0.8;
  }
}

.lab-dialog-card {
  background: rgb(var(--v-theme-surface));
}

.lab-header {
  font-size: 1rem;
  font-weight: 600;
}

.lab-content {
  max-height: 70vh;
  overflow-y: auto;
}

.lab-panels {
  :deep(.v-expansion-panel-title) {
    font-size: 0.875rem;
    font-weight: 600;
    min-height: 44px;
    padding: 8px 16px;
  }

  :deep(.v-expansion-panel-text__wrapper) {
    padding: 12px 16px;
  }
}

.tool-selector {
  .tool-chip-active {
    background: rgba(255, 195, 0, 0.15) !important;
    border-color: #ffc300 !important;
    color: #ffc300 !important;
  }
}

.tip-box {
  position: relative;
  background: rgba(var(--v-theme-on-surface), 0.06);
  border-radius: 6px;
  padding: 10px 12px;
  padding-right: 36px;

  .tip-label {
    font-size: 0.75rem;
    font-weight: 600;
    color: rgba(var(--v-theme-on-surface), 0.6);
    margin-bottom: 4px;
    text-transform: uppercase;
    letter-spacing: 0.5px;
  }

  .tip-code {
    display: block;
    font-size: 0.8rem;
    line-height: 1.5;
    white-space: pre-wrap;
    word-break: break-word;
    color: rgba(var(--v-theme-on-surface), 0.85);
  }

  .copy-btn {
    position: absolute;
    top: 6px;
    right: 4px;
    color: rgba(var(--v-theme-on-surface), 0.4);

    &:hover {
      color: #ffc300;
    }
  }
}

.tip-section {
  .tip-subtitle {
    font-size: 0.8rem;
    font-weight: 600;
    margin-bottom: 6px;
    color: rgba(var(--v-theme-on-surface), 0.7);
  }
}

.tip-list {
  margin: 0;
  padding-left: 20px;
  font-size: 0.825rem;
  line-height: 1.7;
  color: rgba(var(--v-theme-on-surface), 0.85);

  code {
    font-size: 0.75rem;
    background: rgba(var(--v-theme-on-surface), 0.08);
    padding: 1px 4px;
    border-radius: 3px;
  }
}

.color-chips {
  display: flex;
  gap: 8px;
  flex-wrap: wrap;

  .color-chip {
    padding: 3px 10px;
    border-radius: 12px;
    font-size: 0.7rem;
    font-weight: 600;
    color: white;
  }
}

.ref-table {
  width: 100%;
  border-collapse: collapse;
  font-size: 0.78rem;

  th, td {
    padding: 6px 8px;
    text-align: left;
    border-bottom: 1px solid rgba(var(--v-theme-on-surface), 0.1);
  }

  th {
    font-weight: 600;
    color: rgba(var(--v-theme-on-surface), 0.6);
    font-size: 0.72rem;
    text-transform: uppercase;
    letter-spacing: 0.5px;
  }

  .ref-label {
    font-weight: 600;
    color: rgba(var(--v-theme-on-surface), 0.6);
    white-space: nowrap;
  }

  code {
    font-size: 0.7rem;
    background: rgba(var(--v-theme-on-surface), 0.08);
    padding: 1px 4px;
    border-radius: 3px;
    word-break: break-all;
  }
}
</style>
