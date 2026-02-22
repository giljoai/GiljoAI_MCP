<template>
  <div class="agent-tips-trigger">
    <v-tooltip location="bottom">
      <template #activator="{ props: tooltipProps }">
        <v-btn
          v-bind="tooltipProps"
          icon
          size="small"
          variant="text"
          class="tips-btn"
          @click="showDialog = true"
        >
          <v-icon size="20">mdi-book-open-page-variant-outline</v-icon>
        </v-btn>
      </template>
      <span>Agent Tips</span>
    </v-tooltip>

    <v-dialog v-model="showDialog" max-width="650" scrollable>
      <v-card v-draggable class="tips-dialog-card">
        <v-card-title class="d-flex align-center tips-header">
          <v-icon class="mr-2" size="22">mdi-book-open-page-variant-outline</v-icon>
          <span>Agent Tips</span>
          <v-spacer />
          <v-btn icon="mdi-close" variant="text" size="small" @click="showDialog = false" />
        </v-card-title>

        <v-divider />

        <v-card-text class="tips-content pa-4">
          <v-expansion-panels variant="accordion" class="tips-panels">
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
                  <div class="tip-label">Add to project description:</div>
                  <code class="tip-code">
After staging, monitor all agents by polling their status every 30 seconds
using bash sleep. Check for status changes, new messages, and blocked agents.
Report a summary after each poll cycle.
                  </code>
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

                <div class="tip-box mb-3">
                  <div class="tip-label">Spawn command (PowerShell):</div>
                  <code class="tip-code">
powershell.exe -Command "Start-Process wt -ArgumentList
  '--title ""TITLE"" --tabColor ""#HEX"" -d ""WORKDIR""
  cmd /k claude --dangerously-skip-permissions ""PROMPT""'
  -Verb RunAs"
                  </code>
                </div>

                <div class="tip-section mb-2">
                  <div class="tip-subtitle">Key tips:</div>
                  <ul class="tip-list">
                    <li>Keep launch prompts slim &mdash; point to the handover document</li>
                    <li>Include "Use Bash tool to RUN" to prevent agents from just printing commands</li>
                    <li>Use <code>--dangerously-skip-permissions</code> for autonomous execution</li>
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
                <p class="mb-3">
                  Copy these into your project description or agent missions to enhance behavior.
                </p>

                <div class="tip-box mb-3">
                  <div class="tip-label">Subagent delegation:</div>
                  <code class="tip-code">
Use the Task tool to spawn specialized subagents for each phase.
Do NOT do all work directly &mdash; delegate to database-expert,
tdd-implementor, frontend-tester, etc. as appropriate.
                  </code>
                  <v-btn
                    size="x-small"
                    variant="text"
                    class="copy-btn"
                    @click="copyText('Use the Task tool to spawn specialized subagents for each phase. Do NOT do all work directly - delegate to database-expert, tdd-implementor, frontend-tester, etc. as appropriate.')"
                  >
                    <v-icon size="14">mdi-content-copy</v-icon>
                  </v-btn>
                </div>

                <div class="tip-box mb-3">
                  <div class="tip-label">Prerequisite check:</div>
                  <code class="tip-code">
Before starting work, verify that all prerequisites from the
previous phase are complete. Read the chain log and check
git status for expected changes.
                  </code>
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
                  <code class="tip-code">
Before reporting completion: 1) Run all tests, 2) Check for
lint errors, 3) Verify no untracked files left behind,
4) Update the chain log with your results.
                  </code>
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
import { ref } from 'vue'

const showDialog = ref(false)
const showCopied = ref(false)

async function copyText(text) {
  try {
    await navigator.clipboard.writeText(text)
    showCopied.value = true
  } catch {
    // Fallback for non-HTTPS contexts
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
.agent-tips-trigger {
  display: inline-flex;
  align-items: center;
}

.tips-btn {
  color: rgba(var(--v-theme-on-surface), 0.5);
  transition: color 0.2s ease;

  &:hover {
    color: #ffc300;
  }
}

.tips-dialog-card {
  background: rgb(var(--v-theme-surface));
}

.tips-header {
  font-size: 1rem;
  font-weight: 600;
}

.tips-content {
  max-height: 70vh;
  overflow-y: auto;
}

.tips-panels {
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
</style>
