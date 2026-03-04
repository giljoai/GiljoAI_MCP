<template>
  <v-card>
    <v-card-title>Integrations</v-card-title>
    <v-card-subtitle>Agent coding tools and native integrations (Admin overview)</v-card-subtitle>

    <v-card-text>
      <!-- AI Tool Configuration Redirect Alert (single info icon, tonal like cookie-domain alert) -->
      <v-alert type="info" variant="tonal" class="mb-6" :icon="false">
        <v-icon start>mdi-information</v-icon>
        <strong>Configure AI Coding Tools</strong>
        <div class="mt-2">
          Users configure their AI coding tools (Claude Code, Codex CLI, Gemini CLI) in
          <router-link to="/settings" class="text-primary font-weight-bold">
            My Settings -> MCP Configuration </router-link
          >. This section provides an admin overview of available integrations.
        </div>
      </v-alert>

      <!-- Agent Coding Tools Section -->
      <h2 class="text-h5 mb-4">Agent Coding Tools</h2>

      <!-- Claude Code CLI -->
      <v-card variant="outlined" class="mb-4">
        <v-card-text>
          <div class="d-flex align-center mb-3">
            <v-avatar size="48" class="mr-4">
              <v-img src="/claude_pix.svg" alt="Claude Code CLI" />
            </v-avatar>
            <div>
              <h3 class="text-h6">Claude Code CLI</h3>
              <p class="text-caption text-medium-emphasis mb-0">
                AI-powered development with MCP integration
              </p>
            </div>
          </div>

          <p class="text-body-2 mb-3">
            GiljoAI Agent Orchestration MCP Server integrates seamlessly with Claude Code CLI,
            leveraging MCP configuration via a single command-line setup in each user's
            <router-link to="/settings" class="text-primary font-weight-bold"
              >My Settings -> API and Integrations -> MCP Configuration</router-link
            >.
          </p>

          <p class="text-body-2 mb-3">
            <strong>Sub-agent Architecture:</strong> Claude Code integration utilizes Claude Code
            native sub-agent tools. This application will copy templated agents, or user-customized
            agents, into the Claude Code agents folder (either on a per-user or per-project basis).
            The user can choose to also launch each agent in its own Claude Code terminal window.
            Agent integration can be found under
            <strong>My Settings -> API and Integrations -> Integrations</strong>, in the
            <strong>Claude Code Agent Export</strong> section.
          </p>
        </v-card-text>
      </v-card>

      <!-- Codex CLI -->
      <v-card variant="outlined" class="mb-4">
        <v-card-text>
          <div class="d-flex align-center mb-3">
            <v-avatar size="48" class="mr-4">
              <CodexMarkIcon
                class="codex-mark"
                :style="{
                  color: 'white',
                  width: '53px',
                  height: '53px',
                }"
              />
            </v-avatar>
            <div>
              <h3 class="text-h6">Codex CLI</h3>
              <p class="text-caption text-medium-emphasis mb-0">
                Advanced code generation and analysis
              </p>
            </div>
          </div>

          <p class="text-body-2 mb-3">
            Codex CLI integrates with our sub-agent architecture to provide powerful code generation
            and analysis capabilities. Sub-agents coordinate through GiljoAI MCP for complex
            development workflows, maintaining context and state across multiple coding sessions.
          </p>
          <p class="text-body-2 mb-3">
            <strong>Integration model:</strong> Multiple terminal windows, one per agent. The user
            runs an orchestrator session in one Codex CLI terminal and starts each agent in its own
            terminal using our prepared activation prompts. This allows each agent to work
            autonomously and stay focused while coordinating through MCP messages.
          </p>
        </v-card-text>
      </v-card>

      <!-- Gemini CLI -->
      <v-card variant="outlined" class="mb-6">
        <v-card-text>
          <div class="d-flex align-center mb-3">
            <v-avatar size="48" class="mr-4">
              <v-img src="/gemini-icon.svg" alt="Gemini CLI" />
            </v-avatar>
            <div>
              <h3 class="text-h6">Gemini CLI</h3>
              <p class="text-caption text-medium-emphasis mb-0">
                Google's advanced AI development platform
              </p>
            </div>
          </div>

          <p class="text-body-2 mb-3">
            Google Gemini CLI integrates with our sub-agent architecture to provide powerful
            AI-driven development capabilities. Sub-agents coordinate through GiljoAI MCP for
            advanced development workflows with enhanced reasoning and multi-modal capabilities.
          </p>
          <p class="text-body-2 mb-3">
            <strong>Integration model:</strong> Multiple terminal windows, one per agent. The user
            runs an orchestrator session in one Gemini CLI terminal and starts each agent in its own
            terminal using our prepared activation prompts. This allows each agent to work
            autonomously and stay focused while coordinating through MCP messages.
          </p>
        </v-card-text>
      </v-card>

      <!-- Native Integrations Section -->
      <v-divider class="my-6"></v-divider>

      <h2 class="text-h5 mb-4">Native Integrations</h2>

      <!-- Serena Integration -->
      <v-card variant="outlined" class="mb-4">
        <v-card-text>
          <div class="d-flex align-center mb-3">
            <v-avatar size="48" class="mr-4">
              <v-img src="/Serena.png" alt="Serena MCP" />
            </v-avatar>
            <div>
              <h3 class="text-h6">Serena MCP</h3>
              <p class="text-caption text-medium-emphasis mb-0">
                Intelligent codebase understanding and navigation
              </p>
            </div>
          </div>

          <p class="text-body-2 mb-3">
            Serena provides deep semantic code analysis, intelligent symbol navigation, and
            contextual understanding of your codebase. It enables agents to efficiently explore and
            understand project structure without reading unnecessary code, significantly improving
            performance and reducing token usage.
          </p>

          <div class="d-flex align-center mb-3">
            <v-btn
              variant="text"
              size="small"
              color="light-blue"
              href="https://github.com/oraios/serena"
              target="_blank"
            >
              <v-icon start>mdi-github</v-icon>
              GitHub Repository
            </v-btn>
            <span class="text-caption text-medium-emphasis ml-3"> Credit: Oraios </span>
          </div>

          <v-alert type="info" variant="tonal" class="mb-0">
            <v-icon start>mdi-account-cog</v-icon>
            <strong>User Configuration:</strong> Each user enables Serena under User Settings ->
            Integrations
          </v-alert>
        </v-card-text>
      </v-card>

      <!-- More Coming Soon -->
      <v-card variant="outlined" color="surface-variant">
        <v-card-text class="text-center py-6">
          <v-icon size="48" color="medium-emphasis" class="mb-3">mdi-plus-circle-outline</v-icon>
          <h3 class="text-h6 text-medium-emphasis mb-2">More Integrations Coming Soon</h3>
          <p class="text-body-2 text-medium-emphasis mb-0">
            Additional native integrations and agent tools will be added in future releases
          </p>
        </v-card-text>
      </v-card>
    </v-card-text>
  </v-card>
</template>

<script setup>
import CodexMarkIcon from '@/components/icons/CodexMarkIcon.vue'
</script>
