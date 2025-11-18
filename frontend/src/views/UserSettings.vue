<template>
  <v-container>
    <!-- Page Header -->
    <h1 class="text-h4 mb-2">My Settings</h1>
    <p class="text-subtitle-1 mb-4">Manage your personal preferences</p>

    <!-- Settings Tabs -->
    <v-tabs v-model="activeTab" class="mb-6">
      <v-tab value="general">
        <v-icon start>mdi-cog</v-icon>
        Setup
      </v-tab>
      <v-tab value="appearance">
        <v-icon start>mdi-palette</v-icon>
        Appearance
      </v-tab>
      <v-tab value="notifications">
        <v-icon start>mdi-bell</v-icon>
        Notifications
      </v-tab>
      <v-tab value="agents">
        <template #prepend>
          <v-img :src="theme.global.current.value.dark ? '/icons/Giljo_White_Face.svg' : '/icons/Giljo_Dark_Face.svg'" width="20" height="20" style="margin-right: 3px;" />
        </template>
        Agents
      </v-tab>
      <v-tab value="context">
        <v-icon start>mdi-layers-triple</v-icon>
        Context
      </v-tab>
      <v-tab value="api-keys">
        <v-icon start>mdi-key-variant</v-icon>
        API Keys
      </v-tab>
      <v-tab value="integrations">
        <v-icon start>mdi-puzzle</v-icon>
        Integrations
      </v-tab>
    </v-tabs>

    <!-- Tab Content -->
    <v-window v-model="activeTab" :touch="false" :reverse="false">
      <!-- Context Settings -->
      <v-window-item value="context">
        <!-- Context Sub-tabs -->
        <v-tabs v-model="contextTab" class="mb-4">
          <v-tab value="priority">Priority Configuration</v-tab>
          <v-tab value="depth">Depth Configuration</v-tab>
        </v-tabs>

        <!-- Context Windows -->
        <v-window v-model="contextTab" :touch="false" :reverse="false">
          <!-- Priority Configuration Tab -->
          <v-window-item value="priority">
            <v-card data-test="context-settings">
              <v-card-title>Context Priority Management</v-card-title>
              <v-card-text>

            <v-alert type="info" variant="tonal" density="compact" class="mb-4">
              <strong>v2.0 Context Priority System:</strong> Controls which context categories are fetched when generating
              AI agent missions. Categories are fetched in priority order: CRITICAL (1) → IMPORTANT (2) → NICE_TO_HAVE (3).
              EXCLUDED (4) categories are never fetched. Drag and drop categories between priority levels.
            </v-alert>

            <!-- Priority 1 Card -->
            <v-card variant="outlined" class="mb-4">
              <v-card-title class="d-flex align-center">
                <v-icon color="error" start>mdi-numeric-1-circle</v-icon>
                Priority 1 - CRITICAL (Always Fetch)
              </v-card-title>
              <v-card-subtitle class="text-caption">
                Always fetched, highest priority - essential for orchestrator operation
              </v-card-subtitle>
              <v-card-text>
                <draggable
                  v-model="priority1Fields"
                  group="fields"
                  item-key="id"
                  handle=".drag-handle"
                  @change="onPriorityChange"
                  class="d-flex flex-wrap"
                >
                  <template #item="{ element }">
                    <v-chip
                      class="ma-1 drag-handle"
                      closable
                      @click:close="removeField(element, 'priority_1')"
                      style="cursor: move;"
                      color="error"
                      variant="outlined"
                    >
                      <v-icon start size="small">mdi-drag-vertical</v-icon>
                      {{ getFieldLabel(element) }}
                    </v-chip>
                  </template>
                </draggable>
                <div v-if="priority1Fields.length === 0" class="text-caption text-medium-emphasis">
                  No categories assigned to CRITICAL priority
                </div>
              </v-card-text>
            </v-card>

            <!-- Priority 2 Card -->
            <v-card variant="outlined" class="mb-4">
              <v-card-title class="d-flex align-center">
                <v-icon color="warning" start>mdi-numeric-2-circle</v-icon>
                Priority 2 - IMPORTANT (Fetch if Budget Allows)
              </v-card-title>
              <v-card-subtitle class="text-caption">
                Fetched if token budget allows - critical product context
              </v-card-subtitle>
              <v-card-text>
                <draggable
                  v-model="priority2Fields"
                  group="fields"
                  item-key="id"
                  handle=".drag-handle"
                  @change="onPriorityChange"
                  class="d-flex flex-wrap"
                >
                  <template #item="{ element }">
                    <v-chip
                      class="ma-1 drag-handle"
                      closable
                      @click:close="removeField(element, 'priority_2')"
                      style="cursor: move;"
                      color="warning"
                      variant="outlined"
                    >
                      <v-icon start size="small">mdi-drag-vertical</v-icon>
                      {{ getFieldLabel(element) }}
                    </v-chip>
                  </template>
                </draggable>
                <div v-if="priority2Fields.length === 0" class="text-caption text-medium-emphasis">
                  No categories assigned to IMPORTANT priority
                </div>
              </v-card-text>
            </v-card>

            <!-- Priority 3 Card -->
            <v-card variant="outlined" class="mb-4">
              <v-card-title class="d-flex align-center">
                <v-icon color="info" start>mdi-numeric-3-circle</v-icon>
                Priority 3 - NICE_TO_HAVE (Fetch if Budget Remaining)
              </v-card-title>
              <v-card-subtitle class="text-caption">
                Fetched only if budget remaining - historical context
              </v-card-subtitle>
              <v-card-text>
                <draggable
                  v-model="priority3Fields"
                  group="fields"
                  item-key="id"
                  handle=".drag-handle"
                  @change="onPriorityChange"
                  class="d-flex flex-wrap"
                >
                  <template #item="{ element }">
                    <v-chip
                      class="ma-1 drag-handle"
                      closable
                      @click:close="removeField(element, 'priority_3')"
                      style="cursor: move;"
                      color="info"
                      variant="outlined"
                    >
                      <v-icon start size="small">mdi-drag-vertical</v-icon>
                      {{ getFieldLabel(element) }}
                    </v-chip>
                  </template>
                </draggable>
                <div v-if="priority3Fields.length === 0" class="text-caption text-medium-emphasis">
                  No categories assigned to NICE_TO_HAVE priority
                </div>
              </v-card-text>
            </v-card>

            <!-- Priority 4 - EXCLUDED (Never Fetch) Card -->
            <v-card variant="outlined" class="mb-4 excluded-card">
              <v-card-title class="d-flex align-center">
                <v-icon color="grey" start>mdi-numeric-4-circle</v-icon>
                Priority 4 - EXCLUDED (Never Fetch)
                <v-chip size="small" variant="outlined" color="grey" class="ml-2">
                  0 tokens
                </v-chip>
              </v-card-title>
              <v-card-subtitle class="text-caption">
                Categories not included in AI agent missions
              </v-card-subtitle>
              <v-card-text>
                <draggable
                  v-model="priority4Fields"
                  group="fields"
                  item-key="id"
                  handle=".drag-handle"
                  @change="onPriorityChange"
                  class="d-flex flex-wrap"
                >
                  <template #item="{ element }">
                    <v-chip
                      class="ma-1 drag-handle"
                      closable
                      @click:close="removeField(element, 'priority_4')"
                      style="cursor: move;"
                      color="grey"
                      variant="outlined"
                    >
                      <v-icon start size="small">mdi-drag-vertical</v-icon>
                      {{ getFieldLabel(element) }}
                    </v-chip>
                  </template>
                </draggable>
                <div v-if="priority4Fields.length === 0" class="text-caption text-medium-emphasis text-center py-4">
                  <v-icon size="large" color="grey-lighten-1" class="mb-2">mdi-check-circle-outline</v-icon>
                  <div>All categories are included (none excluded)</div>
                </div>
              </v-card-text>
            </v-card>

            <!-- Token Budget Indicator -->
            <v-card v-if="activeProductTokens" variant="tonal" :color="tokenIndicatorColor" class="mb-4">
              <v-card-text>
                <div class="d-flex align-center justify-space-between">
                  <div>
                    <div class="text-caption">Estimated Context Size for: {{ activeProductName }}</div>
                    <div class="text-h6">{{ estimatedTokens }} / {{ tokenBudget }} tokens</div>
                  </div>
                  <v-progress-circular
                    :model-value="tokenPercentage"
                    :color="tokenIndicatorColor"
                    size="64"
                  >
                    {{ tokenPercentage }}%
                  </v-progress-circular>
                </div>
              </v-card-text>
            </v-card>

            <!-- No Active Product Message -->
            <v-alert v-else type="info" variant="tonal" class="mb-4">
              No active product / Token estimation unavailable
            </v-alert>

            <!-- Action Buttons -->
            <div class="d-flex gap-2 mb-4">
              <v-btn
                color="primary"
                variant="flat"
                @click="saveFieldPriority"
                :loading="savingFieldPriority"
                :disabled="!fieldPriorityHasChanges"
              >
                <v-icon start>mdi-content-save</v-icon>
                Save Field Priority
              </v-btn>

              <v-btn
                variant="outlined"
                @click="resetFieldPriorityToDefaults"
                :disabled="savingFieldPriority"
              >
                <v-icon start>mdi-restore</v-icon>
                Reset to Defaults
              </v-btn>
            </div>
              </v-card-text>
            </v-card>
          </v-window-item>

          <!-- Depth Configuration Tab -->
          <v-window-item value="depth">
            <DepthConfiguration />
          </v-window-item>
        </v-window>
      </v-window-item>

      <!-- Agents -->
      <v-window-item value="agents">
        <TemplateManager />
      </v-window-item>

      <!-- Setup Settings -->
      <v-window-item value="general">
        <v-card data-test="general-settings">
          <v-card-title>Setup</v-card-title>
          <v-card-text>
            <v-alert type="info" variant="tonal" density="compact">
              This section is reserved for future setup settings.
            </v-alert>
          </v-card-text>
          <v-card-actions>
            <v-spacer />
            <v-btn variant="text" @click="resetGeneralSettings" data-test="reset-general-btn">Reset</v-btn>
            <v-btn color="primary" variant="flat" @click="saveGeneralSettings" data-test="save-general-btn">Save Changes</v-btn>
          </v-card-actions>
        </v-card>
      </v-window-item>

      <!-- Appearance Settings -->
      <v-window-item value="appearance">
        <v-card data-test="appearance-settings">
          <v-card-title>Appearance Settings</v-card-title>
          <v-card-text>
            <v-row>
              <v-col cols="12" md="6">
                <h3 class="text-h6 mb-4">Theme</h3>
                <v-radio-group v-model="settings.appearance.theme" data-test="theme-selector">
                  <v-radio label="Dark Theme" value="dark" />
                  <v-radio label="Light Theme" value="light" />
                  <v-radio label="System Default" value="system" />
                </v-radio-group>
              </v-col>

              <v-col cols="12" md="6">
                <h3 class="text-h6 mb-4">Mascot Preferences</h3>
                <v-switch
                  v-model="settings.appearance.showMascot"
                  label="Show mascot animations"
                  color="primary"
                  data-test="mascot-toggle"
                />
                <v-switch
                  v-model="settings.appearance.useBlueVariant"
                  label="Use blue mascot variant"
                  color="primary"
                />
              </v-col>
            </v-row>

            <v-divider class="my-6" />

            <h3 class="text-h6 mb-4">Display Options</h3>
            <v-row>
              <v-col cols="12" md="6">
                <v-switch
                  v-model="settings.appearance.compactMode"
                  label="Compact mode"
                  color="primary"
                />
                <v-switch
                  v-model="settings.appearance.showAnimations"
                  label="Enable animations"
                  color="primary"
                />
              </v-col>
              <v-col cols="12" md="6">
                <v-switch
                  v-model="settings.appearance.showTooltips"
                  label="Show tooltips"
                  color="primary"
                />
                <v-switch
                  v-model="settings.appearance.highContrast"
                  label="High contrast mode"
                  color="primary"
                />
              </v-col>
            </v-row>
          </v-card-text>
          <v-card-actions>
            <v-spacer />
            <v-btn variant="text" @click="resetAppearanceSettings" data-test="reset-appearance-btn">Reset</v-btn>
            <v-btn color="primary" variant="flat" @click="saveAppearanceSettings" data-test="save-appearance-btn"
              >Save Changes</v-btn
            >
          </v-card-actions>
        </v-card>
      </v-window-item>

      <!-- Notification Settings -->
      <v-window-item value="notifications">
        <v-card data-test="notification-settings">
          <v-card-title>Notification Settings</v-card-title>
          <v-card-text>
            <h3 class="text-h6 mb-4">Message Notifications</h3>
            <v-switch
              v-model="settings.notifications.newMessages"
              label="New message alerts"
              color="primary"
              data-test="new-messages-toggle"
            />
            <v-switch
              v-model="settings.notifications.urgentOnly"
              label="Urgent messages only"
              color="primary"
              :disabled="!settings.notifications.newMessages"
            />

            <v-divider class="my-6" />

            <h3 class="text-h6 mb-4">Agent Notifications</h3>
            <v-switch
              v-model="settings.notifications.agentStatus"
              label="Agent status changes"
              color="primary"
            />
            <v-switch
              v-model="settings.notifications.agentErrors"
              label="Agent errors"
              color="primary"
            />

            <v-divider class="my-6" />

            <h3 class="text-h6 mb-4">Task Notifications</h3>
            <v-switch
              v-model="settings.notifications.taskComplete"
              label="Task completions"
              color="primary"
            />
            <v-switch
              v-model="settings.notifications.taskOverdue"
              label="Overdue task alerts"
              color="primary"
            />

            <v-divider class="my-6" />

            <h3 class="text-h6 mb-4">Notification Display</h3>
            <v-select
              v-model="settings.notifications.position"
              :items="[
                'top-left',
                'top-center',
                'top-right',
                'bottom-left',
                'bottom-center',
                'bottom-right',
              ]"
              label="Notification position"
              variant="outlined"
              data-test="notification-position-select"
            />
            <v-slider
              v-model="settings.notifications.duration"
              :min="2"
              :max="10"
              :step="1"
              label="Display duration (seconds)"
              thumb-label
              class="mt-4"
            />
          </v-card-text>
          <v-card-actions>
            <v-spacer />
            <v-btn variant="text" @click="resetNotificationSettings" data-test="reset-notification-btn">Reset</v-btn>
            <v-btn color="primary" variant="flat" @click="saveNotificationSettings" data-test="save-notification-btn"
              >Save Changes</v-btn
            >
          </v-card-actions>
        </v-card>
      </v-window-item>

      <!-- API Keys -->
      <v-window-item value="api-keys">
        <!-- Removed outer card title/subtitle - ApiKeyManager has its own -->
        <ApiKeyManager />
      </v-window-item>

      <!-- Integrations -->
      <v-window-item value="integrations">
        <v-card>
          <v-card-title>Integrations</v-card-title>
          <v-card-subtitle>Configure MCP tools and integrations</v-card-subtitle>
          <v-card-text>
            <!-- GiljoAI MCP Integration -->
            <v-card variant="outlined" class="mb-4">
              <v-card-text>
                <div class="d-flex align-center mb-3">
                  <v-avatar size="40" rounded="0" class="mr-2">
                    <v-img :src="theme.global.current.value.dark ? '/giljo_YW_Face.svg' : '/icons/Giljo_BY_Face.svg'" alt="GiljoAI MCP" />
                  </v-avatar>
                  <h3 class="text-h6 mb-0">GiljoAI MCP Integration</h3>
                </div>
                <p class="text-body-2 text-medium-emphasis mb-4">
                  Connect your AI coding tool to GiljoAI orchestration. Supports Claude Code, Codex CLI, and Gemini CLI.
                </p>

                <!-- MCP Configuration Tool -->
                <v-card variant="tonal" class="mb-0">
                  <v-card-text class="pa-3">
                    <div class="d-flex align-center justify-between">
                      <div class="flex-grow-1">
                        <div class="text-subtitle-2 font-weight-medium">MCP Configuration Tool</div>
                        <div class="text-body-2 text-medium-emphasis">
                          Creates MCP integration CLI command for your coding agent of choice
                        </div>
                      </div>
                      <AiToolConfigWizard />
                    </div>
                  </v-card-text>
                </v-card>
              </v-card-text>
            </v-card>

            <!-- Slash Command Setup -->
            <SlashCommandSetup />

            <!-- Claude Code Agent Export -->
            <ClaudeCodeExport />

            <!-- Serena MCP Integration -->
            <v-card variant="outlined" class="mb-4">
              <v-card-text>
                <div class="d-flex align-center mb-3">
                  <v-avatar size="40" rounded="0" class="mr-2">
                    <v-img src="/Serena.png" alt="Serena MCP" />
                  </v-avatar>
                  <div class="flex-grow-1">
                    <div class="d-flex align-center">
                      <h3 class="text-h6 mb-0 mr-2">Serena MCP</h3>
                      <v-tooltip location="top" max-width="400">
                        <template #activator="{ props }">
                          <v-icon v-bind="props" size="small" color="medium-emphasis">mdi-help-circle-outline</v-icon>
                        </template>
                        <div>
                          <strong>Intelligent codebase understanding and navigation</strong>
                          <p class="mt-2 mb-0">
                            Serena provides deep semantic code analysis, intelligent symbol navigation, and contextual 
                            understanding of your codebase. It enables agents to efficiently explore and understand 
                            project structure without reading unnecessary code, significantly improving performance 
                            and reducing token usage.
                          </p>
                          <p class="mt-2 mb-0 text-caption">
                            <strong>Note:</strong> Serena must be installed separately in your AI coding tool.
                          </p>
                        </div>
                      </v-tooltip>
                    </div>
                    <p class="text-caption text-medium-emphasis mb-0">Intelligent codebase understanding and navigation</p>
                  </div>
                </div>

                <p class="text-body-2 text-medium-emphasis mb-3">
                  Enabling adds Serena tool instructions to agent prompts. Disabling removes them from agent tool startup.
                </p>

                <div class="d-flex align-center mb-3">
                  <v-btn variant="text" size="small" color="light-blue" href="https://github.com/oraios/serena" target="_blank">
                    <v-icon start>mdi-github</v-icon>
                    GitHub Repository
                  </v-btn>
                  <span class="text-caption text-medium-emphasis ml-3">
                    Credit: Oraios
                  </span>
                </div>

                <!-- Serena Controls -->
                <v-card variant="tonal" class="mb-0">
                  <v-card-text class="pa-3">
                    <div class="d-flex align-center justify-between">
                      <div class="flex-grow-1 d-flex align-center">
                        <div class="text-subtitle-2 font-weight-medium mr-4">Enable Serena MCP</div>
                        <v-switch
                          v-model="serenaEnabled"
                          @update:model-value="toggleSerena"
                          :loading="toggling"
                          hide-details
                          density="compact"
                          class="serena-toggle-inline"
                        />
                      </div>
                      <v-btn
                        color="primary"
                        variant="flat"
                        size="small"
                        width="120"
                        @click="openSerenaAdvanced"
                        :disabled="toggling"
                      >
                        Advanced
                      </v-btn>
                    </div>
                  </v-card-text>
                </v-card>
              </v-card-text>
            </v-card>

            <!-- Git + 360 Memory Integration (Handover 013B) -->
            <v-card variant="outlined" class="mb-4">
              <v-card-text>
                <div class="d-flex align-center mb-3">
                  <v-avatar size="40" rounded="0" class="mr-2" color="grey-darken-2">
                    <v-icon size="28" color="white">mdi-github</v-icon>
                  </v-avatar>
                  <div class="flex-grow-1">
                    <div class="d-flex align-center">
                      <h3 class="text-h6 mb-0 mr-2">Git + 360 Memory</h3>
                      <v-tooltip location="top" max-width="400">
                        <template #activator="{ props }">
                          <v-icon v-bind="props" size="small" color="medium-emphasis">mdi-help-circle-outline</v-icon>
                        </template>
                        <div>
                          <strong>Cumulative product knowledge tracking</strong>
                          <p class="mt-2 mb-0">
                            When enabled, GiljoAI captures git commit history at project closeout
                            and stores it in 360 Memory. This provides orchestrators with cumulative
                            context across all projects, including what was built, decisions made,
                            and implementation patterns used.
                          </p>
                          <p class="mt-2 mb-0 text-caption">
                            <strong>Note:</strong> Git must be configured on your system with access
                            to your repositories.
                          </p>
                        </div>
                      </v-tooltip>
                    </div>
                    <p class="text-caption text-medium-emphasis mb-0">Track git commits in 360 Memory for orchestrator context</p>
                  </div>
                </div>

                <p class="text-body-2 text-medium-emphasis mb-3">
                  Enable to automatically include git commit history in project summaries. Commits are stored in product memory for future orchestrator reference.
                </p>

                <div class="d-flex align-center mb-3">
                  <v-btn
                    variant="text"
                    size="small"
                    color="light-blue"
                    href="https://docs.github.com/en/get-started/quickstart/set-up-git"
                    target="_blank"
                  >
                    <v-icon start>mdi-book-open-variant</v-icon>
                    GitHub Setup Guide
                  </v-btn>
                </div>

                <!-- Git Integration Controls -->
                <v-card variant="tonal" class="mb-0">
                  <v-card-text class="pa-3">
                    <div class="d-flex align-center justify-between mb-3">
                      <div class="flex-grow-1 d-flex align-center">
                        <div class="text-subtitle-2 font-weight-medium mr-4">Enable Git Integration</div>
                        <v-switch
                          v-model="gitIntegration.enabled"
                          @update:model-value="onGitToggle"
                          :loading="savingGitIntegration"
                          hide-details
                          density="compact"
                          class="git-toggle-inline"
                        />
                      </div>
                      <v-btn
                        color="primary"
                        variant="flat"
                        size="small"
                        width="120"
                        @click="saveGitIntegration"
                        :disabled="savingGitIntegration"
                        :loading="savingGitIntegration"
                      >
                        Save
                      </v-btn>
                    </div>

                    <!-- Info Alert (shown when enabled) -->
                    <v-alert
                      v-if="gitIntegration.enabled"
                      type="info"
                      variant="tonal"
                      density="compact"
                      class="mb-3"
                    >
                      <div class="text-body-2">
                        <strong>Requirement:</strong> Git must be configured with access to your repositories
                        on your system (Windows/Linux/macOS). GiljoAI uses your local git
                        credentials - no server-side authentication needed.
                      </div>
                    </v-alert>

                    <!-- Advanced Settings (collapsible) -->
                    <v-expansion-panels v-if="gitIntegration.enabled" variant="accordion" class="mt-0">
                      <v-expansion-panel>
                        <v-expansion-panel-title>
                          <v-icon start size="small">mdi-cog</v-icon>
                          Advanced Settings
                        </v-expansion-panel-title>
                        <v-expansion-panel-text>
                          <v-text-field
                            v-model.number="gitIntegration.commit_limit"
                            label="Commit Limit"
                            type="number"
                            min="1"
                            max="100"
                            hint="Number of commits to include in orchestrator prompts"
                            persistent-hint
                            density="compact"
                            class="mb-3"
                          />
                          <v-text-field
                            v-model="gitIntegration.default_branch"
                            label="Default Branch"
                            placeholder="e.g., main, master, develop"
                            hint="Leave empty for repository default"
                            persistent-hint
                            density="compact"
                          />
                        </v-expansion-panel-text>
                      </v-expansion-panel>
                    </v-expansion-panels>
                  </v-card-text>
                </v-card>
              </v-card-text>
            </v-card>
          </v-card-text>
        </v-card>
      </v-window-item>
    </v-window>

    

    <!-- Serena Advanced Settings Dialog -->
    <SerenaAdvancedSettingsDialog
      v-model="showSerenaAdvanced"
      :value="serenaConfig"
      @save="saveSerenaConfig"
    />
  </v-container>
</template>

<script setup>
import { ref, onMounted, computed, watch } from 'vue'
import { useSettingsStore } from '@/stores/settings'
import { useTheme } from 'vuetify'
import { useRouter } from 'vue-router'
import TemplateManager from '@/components/TemplateManager.vue'
import ApiKeyManager from '@/components/ApiKeyManager.vue'
import AiToolConfigWizard from '@/components/AiToolConfigWizard.vue'
import ClaudeCodeExport from '@/components/ClaudeCodeExport.vue'
import SlashCommandSetup from '@/components/SlashCommandSetup.vue'
import SerenaAdvancedSettingsDialog from '@/components/SerenaAdvancedSettingsDialog.vue'
import DepthConfiguration from '@/components/settings/DepthConfiguration.vue'
import draggable from 'vuedraggable'
import setupService from '@/services/setupService'
import api from '@/services/api'
import { useWebSocketStore } from '@/stores/websocket'

// Field Priority Constants (Handover 0313: v2.0 Priority System Refactor)
// v1.0: Priority = token reduction level (10/7/4/0)
// v2.0: Priority = fetch order / mandatory flag (1/2/3/4)
const PRIORITY_CRITICAL = 1      // v2.0: Always fetch, highest priority
const PRIORITY_IMPORTANT = 2     // v2.0: Fetch if budget allows
const PRIORITY_NICE = 3          // v2.0: Fetch if budget remaining
const PRIORITY_EXCLUDED = 4      // v2.0: Never fetch

// Stores and Theme
const settingsStore = useSettingsStore()
const wsStore = useWebSocketStore()
const theme = useTheme()
const router = useRouter()

// State
const activeTab = ref('general')
const contextTab = ref('priority')  // Sub-tab for Context section (priority/depth)
const integrationsSubTab = ref('mcp-config')
const generalForm = ref(null)
const serenaEnabled = ref(false)
const toggling = ref(false)

const showSerenaAdvanced = ref(false)
const serenaConfig = ref({
  use_in_prompts: true,
  tailor_by_mission: true,
  dynamic_catalog: true,
  prefer_ranges: true,
  max_range_lines: 180,
  context_halo: 12,
})

// Git Integration state (Handover 013B)
const gitIntegration = ref({
  enabled: false,
  commit_limit: 20,
  default_branch: 'main'
})
const savingGitIntegration = ref(false)

// Field Priority Configuration state (Handover 0313: v2.0)
const priority1Fields = ref([])  // CRITICAL
const priority2Fields = ref([])  // IMPORTANT
const priority3Fields = ref([])  // NICE_TO_HAVE
const priority4Fields = ref([])  // EXCLUDED (replaces unassignedFields)
const savingFieldPriority = ref(false)
const fieldPriorityHasChanges = ref(false)

// All available fields (Handover 0313: v2.0 - 6 categories)
const ALL_AVAILABLE_FIELDS = [
  'product_core',
  'vision_documents',
  'agent_templates',
  'project_context',
  'memory_360',
  'git_history'
]

// Real-time token calculation state (Handover 0049)
const activeProductTokens = ref(null)
const loadingTokenEstimate = ref(false)

// Field labels mapping for display (Handover 0313: v2.0)
const fieldLabels = {
  'product_core': 'Product Core',
  'vision_documents': 'Vision Documents',
  'agent_templates': 'Agent Templates',
  'project_context': 'Project Context',
  'memory_360': '360 Memory',
  'git_history': 'Git History'
}

// Field descriptions (Handover 0313: v2.0)
const fieldDescriptions = {
  'product_core': 'Product description and tech stack (languages, backend, frontend, database, infrastructure)',
  'vision_documents': 'Chunked vision document uploads (product vision, features, roadmap)',
  'agent_templates': 'Active agent behavior configurations',
  'project_context': 'Project description, user notes, architecture notes',
  'memory_360': 'Cumulative project history (learnings, decisions, sequential closeouts)',
  'git_history': 'Recent commits from git integration (optional)'
}

// Settings object
const settings = ref({
  general: {
    // Handover 0052: Removed unused projectName field (had broken save function)
  },
  appearance: {
    theme: 'dark',
    showMascot: true,
    useBlueVariant: false,
    compactMode: false,
    showAnimations: true,
    showTooltips: true,
    highContrast: false,
  },
  notifications: {
    newMessages: true,
    urgentOnly: false,
    agentStatus: true,
    agentErrors: true,
    taskComplete: true,
    taskOverdue: true,
    position: 'bottom-right',
    duration: 5,
  },
})

// Methods
async function saveGeneralSettings() {
  try {
    await settingsStore.updateSettings({ general: settings.value.general })
    console.log('General settings saved')
  } catch (error) {
    console.error('Failed to save general settings:', error)
  }
}

async function saveAppearanceSettings() {
  try {
    // Apply theme immediately
    if (settings.value.appearance.theme !== 'system') {
      theme.global.name.value = settings.value.appearance.theme  // TODO: Upgrade to theme.change() after Vuetify 3.7+
      document.documentElement.setAttribute('data-theme', settings.value.appearance.theme)
      localStorage.setItem('theme-preference', settings.value.appearance.theme)
    }

    await settingsStore.updateSettings({ appearance: settings.value.appearance })
    console.log('Appearance settings saved')
  } catch (error) {
    console.error('Failed to save appearance settings:', error)
  }
}

async function saveNotificationSettings() {
  try {
    await settingsStore.updateSettings({ notifications: settings.value.notifications })
    console.log('Notification settings saved')
  } catch (error) {
    console.error('Failed to save notification settings:', error)
  }
}

function resetGeneralSettings() {
  // Handover 0052: General settings are empty after projectName field removal
  settings.value.general = {}
}

function resetAppearanceSettings() {
  settings.value.appearance = {
    theme: 'dark',
    showMascot: true,
    useBlueVariant: false,
    compactMode: false,
    showAnimations: true,
    showTooltips: true,
    highContrast: false,
  }
}

function resetNotificationSettings() {
  settings.value.notifications = {
    newMessages: true,
    urgentOnly: false,
    agentStatus: true,
    agentErrors: true,
    taskComplete: true,
    taskOverdue: true,
    position: 'bottom-right',
    duration: 5,
  }
}

// Serena MCP Methods
async function checkSerenaStatus() {
  try {
    const status = await setupService.getSerenaStatus()
    serenaEnabled.value = status.enabled || false
    console.log('[USER SETTINGS] Serena prompt injection status:', serenaEnabled.value)
  } catch (error) {
    console.error('[USER SETTINGS] Failed to check Serena status:', error)
    serenaEnabled.value = false
  }
}

async function toggleSerena(enabled) {
  toggling.value = true
  try {
    const result = await setupService.toggleSerena(enabled)
    if (result.success) {
      serenaEnabled.value = result.enabled
      console.log('[USER SETTINGS] Serena prompt injection toggled:', result.enabled)
    } else {
      // Revert on failure
      serenaEnabled.value = !enabled
      console.error('[USER SETTINGS] Failed to toggle Serena:', result.message)
    }
  } catch (error) {
    console.error('[USER SETTINGS] Error toggling Serena:', error)
    // Revert on error
    serenaEnabled.value = !enabled
  } finally {
    toggling.value = false
  }
}

// Real-time token calculation computed properties (Handover 0049)
const activeProductName = computed(() => {
  return activeProductTokens.value?.name || 'No Active Product'
})

// Field Priority Configuration computed properties (Handover 0313: v2.0)
const estimatedTokens = computed(() => {
  if (activeProductTokens.value?.total_tokens !== undefined) {
    return activeProductTokens.value.total_tokens
  }
  // Fallback calculation based on category counts
  const p1 = priority1Fields.value.length * 80   // CRITICAL categories have more content
  const p2 = priority2Fields.value.length * 60   // IMPORTANT categories
  const p3 = priority3Fields.value.length * 40   // NICE_TO_HAVE categories
  // priority4 (EXCLUDED) contributes 0 tokens
  return p1 + p2 + p3 + 500 // +500 for mission overhead
})

const tokenBudget = computed(() => {
  return activeProductTokens.value?.token_budget || 2000
})

const tokenPercentage = computed(() => {
  return Math.min(Math.round((estimatedTokens.value / tokenBudget.value) * 100), 100)
})

const tokenIndicatorColor = computed(() => {
  if (tokenPercentage.value > 90) return 'error'
  if (tokenPercentage.value > 70) return 'warning'
  return 'success'
})

// Field Priority Configuration Methods (Handover 0313: v2.0)
function getFieldLabel(fieldPath) {
  return fieldLabels[fieldPath] || fieldPath
}

function getFieldDescription(fieldPath) {
  return fieldDescriptions[fieldPath] || ''
}

function onPriorityChange() {
  fieldPriorityHasChanges.value = true
}

function removeField(field, priority) {
  let removed = false

  if (priority === 'priority_1') {
    const index = priority1Fields.value.indexOf(field)
    if (index > -1) {
      priority1Fields.value.splice(index, 1)
      removed = true
    }
  } else if (priority === 'priority_2') {
    const index = priority2Fields.value.indexOf(field)
    if (index > -1) {
      priority2Fields.value.splice(index, 1)
      removed = true
    }
  } else if (priority === 'priority_3') {
    const index = priority3Fields.value.indexOf(field)
    if (index > -1) {
      priority3Fields.value.splice(index, 1)
      removed = true
    }
  } else if (priority === 'priority_4') {
    const index = priority4Fields.value.indexOf(field)
    if (index > -1) {
      priority4Fields.value.splice(index, 1)
      removed = true
    }
  }

  // Handover 0313: Move to EXCLUDED (priority_4) instead of deleting
  if (removed && priority !== 'priority_4') {
    if (!priority4Fields.value.includes(field)) {
      priority4Fields.value.push(field)
    }
  }

  if (removed) {
    fieldPriorityHasChanges.value = true
  }
}

async function saveFieldPriority() {
  savingFieldPriority.value = true
  try {
    // Handover 0313: v2.0 schema uses 'priorities' dict (not 'fields')
    const prioritiesConfig = {}
    priority1Fields.value.forEach(field => {
      prioritiesConfig[field] = PRIORITY_CRITICAL  // 1
    })
    priority2Fields.value.forEach(field => {
      prioritiesConfig[field] = PRIORITY_IMPORTANT  // 2
    })
    priority3Fields.value.forEach(field => {
      prioritiesConfig[field] = PRIORITY_NICE  // 3
    })
    priority4Fields.value.forEach(field => {
      prioritiesConfig[field] = PRIORITY_EXCLUDED  // 4
    })

    const config = {
      version: '2.0',
      priorities: prioritiesConfig  // v2.0: 'priorities' not 'fields'
      // No token_budget in v2.0 (moved to depth controls in Handover 0314)
    }

    await settingsStore.updateFieldPriorityConfig(config)
    fieldPriorityHasChanges.value = false
    console.log('[USER SETTINGS] Field priority config saved successfully (v2.0)')

    await fetchActiveProductTokenEstimate()
  } catch (error) {
    console.error('[USER SETTINGS] Failed to save field priority config:', error)
  } finally {
    savingFieldPriority.value = false
  }
}

async function resetFieldPriorityToDefaults() {
  savingFieldPriority.value = true
  try {
    await settingsStore.resetFieldPriorityConfig()
    await loadFieldPriorityConfig()
    fieldPriorityHasChanges.value = false
    console.log('[USER SETTINGS] Field priority config reset to defaults (v2.0)')

    // Handover 0052: Refresh token estimate from active product after reset
    await fetchActiveProductTokenEstimate()
  } catch (error) {
    console.error('[USER SETTINGS] Failed to reset field priority config:', error)
  } finally {
    savingFieldPriority.value = false
  }
}

async function loadFieldPriorityConfig() {
  try {
    await settingsStore.fetchFieldPriorityConfig()
    const config = settingsStore.fieldPriorityConfig

    if (config) {
      // Handover 0313: v2.0 schema uses 'priorities' dict
      priority1Fields.value = []
      priority2Fields.value = []
      priority3Fields.value = []
      priority4Fields.value = []

      Object.entries(config.priorities || {}).forEach(([field, priority]) => {
        if (priority === 1) {
          priority1Fields.value.push(field)
        } else if (priority === 2) {
          priority2Fields.value.push(field)
        } else if (priority === 3) {
          priority3Fields.value.push(field)
        } else if (priority === 4) {
          priority4Fields.value.push(field)
        }
      })

      // Compute EXCLUDED fields (those not assigned to 1/2/3)
      const assignedSet = new Set([
        ...priority1Fields.value,
        ...priority2Fields.value,
        ...priority3Fields.value,
        ...priority4Fields.value,
      ])

      // Any fields not explicitly set default to EXCLUDED
      const unassignedFields = ALL_AVAILABLE_FIELDS.filter(
        field => !assignedSet.has(field)
      )
      priority4Fields.value.push(...unassignedFields)

      fieldPriorityHasChanges.value = false
      console.log('[USER SETTINGS] Field priority config loaded successfully (v2.0)')
      console.log(`[USER SETTINGS] EXCLUDED fields: ${priority4Fields.value.length}`)
    }
  } catch (error) {
    console.error('[USER SETTINGS] Failed to load field priority config:', error)
  }
}

// Real-time token calculation method (Handover 0049)
async function fetchActiveProductTokenEstimate() {
  loadingTokenEstimate.value = true
  try {
    const response = await api.products.getActiveProductTokenEstimate()
    if (response.data) {
      activeProductTokens.value = response.data
      console.log('[USER SETTINGS] Active product token estimate loaded:', activeProductTokens.value)
    }
  } catch (error) {
    // Suppress noisy 500 error from v1.0 endpoint with v2.0 data (Handover 0313)
    if (error.response?.status === 500) {
      console.log('[USER SETTINGS] Token estimate not available (v1.0 endpoint, v2.0 data) - using fallback')
    } else {
      console.warn('[USER SETTINGS] Failed to fetch active product token estimate:', error.response?.status || error.message)
    }
    // Graceful fallback: use generic calculation (already implemented in computed property)
    activeProductTokens.value = null
    console.log('[USER SETTINGS] Using fallback generic token calculation')
  } finally {
    loadingTokenEstimate.value = false
  }
}

// Lifecycle
onMounted(async () => {
  // Check for tab parameter in query string
  const route = router.currentRoute.value

  if (route.query.tab) {

    activeTab.value = route.query.tab
  }

  // Check Serena MCP status
  await checkSerenaStatus()

  // Load settings from store
  const storedSettings = await settingsStore.loadSettings()
  if (storedSettings) {
    Object.assign(settings.value, storedSettings)
  }

  // Initialize theme from current Vuetify theme AFTER loading stored settings
  // This ensures UI reflects actual current theme (restored in main.js from localStorage)
  settings.value.appearance.theme = theme.global.name.value

  // Load field priority configuration (Handover 0048)
  await loadFieldPriorityConfig()

  // Fetch real-time token estimate from active product (Handover 0049)
  await fetchActiveProductTokenEstimate()

  // Load git integration settings (Handover 013B)
  await loadGitIntegration()

  // Handover 0313: WebSocket listener for real-time priority config updates
  wsStore.on('priority_config_updated', handlePriorityConfigUpdate)
})

// WebSocket event handler for priority_config_updated (Handover 0313: v2.0)
function handlePriorityConfigUpdate(data) {
  console.log('[USER SETTINGS] Received priority_config_updated event:', data)

  // Reload field priority config from server to ensure UI is in sync
  loadFieldPriorityConfig()

  // Refresh token estimate to reflect new configuration
  fetchActiveProductTokenEstimate()

  console.log('[USER SETTINGS] Field priority config reloaded from WebSocket event')
}

// Watch priority fields for changes and recalculate tokens with debounce (Handover 0313: v2.0)
let tokenCalculationTimeout
watch(
  () => [priority1Fields.value, priority2Fields.value, priority3Fields.value, priority4Fields.value],
  () => {
    if (tokenCalculationTimeout) {
      clearTimeout(tokenCalculationTimeout)
    }

    tokenCalculationTimeout = setTimeout(() => {
      console.log('[USER SETTINGS] Token estimate recalculated (debounced)')
    }, 500)
  },
  { deep: true }
)

// Serena Advanced dialog handlers
async function openSerenaAdvanced() {
  try {
    const cfg = await setupService.getSerenaConfig()
    serenaConfig.value = cfg
    // keep main toggle in sync
    serenaEnabled.value = !!cfg.use_in_prompts
    showSerenaAdvanced.value = true
  } catch (error) {
    console.error('[USER SETTINGS] Failed to load Serena config:', error)
  }
}

async function saveSerenaConfig(payload, done) {
  try {
    const updated = await setupService.updateSerenaConfig(payload)
    serenaConfig.value = updated
    serenaEnabled.value = !!updated.use_in_prompts
    showSerenaAdvanced.value = false
  } catch (error) {
    console.error('[USER SETTINGS] Failed to save Serena config:', error)
  } finally {
    if (typeof done === 'function') done()
  }
}

// Git Integration handlers (Handover 013B)
async function loadGitIntegration() {
  try {
    // Load product info to get the active product ID
    await settingsStore.loadProductInfo()

    if (!settingsStore.productInfo?.id) {
      console.warn('[USER SETTINGS] No active product found - git integration disabled')
      return
    }

    const response = await api.products.getGitIntegration(settingsStore.productInfo.id)
    gitIntegration.value = {
      enabled: response.data.enabled || false,
      commit_limit: response.data.commit_limit || 20,
      default_branch: response.data.default_branch || 'main'
    }
    console.log('[USER SETTINGS] Git integration loaded:', gitIntegration.value)
  } catch (error) {
    console.error('[USER SETTINGS] Failed to load git integration:', error)
    // Set defaults on error
    gitIntegration.value = {
      enabled: false,
      commit_limit: 20,
      default_branch: 'main'
    }
  }
}

function onGitToggle(enabled) {
  console.log('[USER SETTINGS] Git integration toggled:', enabled)
  // If disabled, reset to defaults
  if (!enabled) {
    gitIntegration.value.commit_limit = 20
    gitIntegration.value.default_branch = 'main'
  }
}

async function saveGitIntegration() {
  if (!settingsStore.productInfo?.id) {
    console.error('[USER SETTINGS] No active product - cannot save git integration')
    return
  }

  savingGitIntegration.value = true
  try {
    const response = await api.products.updateGitIntegration(
      settingsStore.productInfo.id,
      {
        enabled: gitIntegration.value.enabled,
        commit_limit: gitIntegration.value.commit_limit || 20,
        default_branch: gitIntegration.value.default_branch || 'main'
      }
    )

    // Update local state with response
    gitIntegration.value = {
      enabled: response.data.enabled,
      commit_limit: response.data.commit_limit,
      default_branch: response.data.default_branch
    }

    console.log('[USER SETTINGS] Git integration saved successfully')

    // Show success notification (you can add toast notification here if available)
    console.log('[USER SETTINGS] ✓ Git integration settings saved')

  } catch (error) {
    console.error('[USER SETTINGS] Failed to save git integration:', error)
    // Show error notification
    console.error('[USER SETTINGS] ✗ Failed to save git integration:', error.message)
  } finally {
    savingGitIntegration.value = false
  }
}
</script>

<style scoped>
/* Integrations section divider should follow theme */
.integrations-divider {
  --v-theme-overlay-multiplier: 1; /* ensure visibility */
  border-color: var(--v-theme-on-surface) !important;
  opacity: 0.3 !important;
}
/* Make Serena toggle inline */
.serena-toggle-inline {
  flex: 0 0 auto;
}

/* Make Git toggle inline (Handover 013B) */
.git-toggle-inline {
  flex: 0 0 auto;
}

/* Field Priority drag-and-drop styling (Handover 0048) */
.drag-handle {
  touch-action: none;
  user-select: none;
  min-height: 48px; /* WCAG touch target size */
}

.drag-handle:hover {
  opacity: 0.9;
}

.drag-handle:focus {
  outline: 2px solid currentColor;
  outline-offset: 2px;
}

/* Mobile responsive adjustments */
@media (max-width: 600px) {
  .drag-handle {
    min-height: 56px; /* Larger touch targets on mobile */
    font-size: 14px;
  }
}

/* Handover 0052: Unassigned card styling */
.excluded-card {
  border-style: dashed !important;
  border-width: 2px;
  border-color: rgba(var(--v-theme-on-surface), 0.3);
  background-color: rgba(var(--v-theme-surface-variant), 0.05);
}

.excluded-card .v-card-title {
  color: rgba(var(--v-theme-on-surface), 0.7);
}

/* Disable sliding transitions, use simple fade instead */
:deep(.v-window__container) {
  overflow: visible !important;
}
:deep(.v-window-item) {
  transition: none !important;
  transform: none !important;
}
:deep(.v-window-item--active) {
  animation: fade-in 0.2s ease-in !important;
}

@keyframes fade-in {
  from {
    opacity: 0;
  }
  to {
    opacity: 1;
  }
}
</style>
