<template>
  <v-container>
    <!-- Page Header -->
    <h1 class="text-h4 mb-2">Admin Settings</h1>
    <p class="text-subtitle-1 mb-4">Configure server and system-wide settings (Admin only)</p>

    <!-- Settings Tabs -->
    <v-tabs v-model="activeTab" class="mb-6">
      <v-tab value="network">
        <v-icon start>mdi-network-outline</v-icon>
        Network
      </v-tab>
      <v-tab value="database">
        <v-icon start>mdi-database</v-icon>
        Database
      </v-tab>
      <v-tab value="integrations">
        <v-icon start>mdi-api</v-icon>
        Integrations
      </v-tab>

      <v-tab value="security">
        <v-icon start>mdi-shield-lock</v-icon>
        Security
      </v-tab>
    </v-tabs>

    <!-- Tab Content -->
    <v-window v-model="activeTab">
      <!-- Network Settings -->
      <v-window-item value="network">
        <v-card>
          <v-card-title>Network Configuration</v-card-title>
          <v-card-subtitle>Server network settings (configured during installation)</v-card-subtitle>

          <v-card-text>
            <!-- Unified Architecture Info -->
            <v-alert type="info" variant="tonal" class="mb-4" data-test="v3-unified-alert" :icon="false">
              <div class="d-flex align-center">
                <v-icon start>mdi-information</v-icon>
                <div>
                  <strong>Unified Architecture:</strong> Server binds to all interfaces with authentication always enabled.
                  OS firewall controls network access (defense in depth).
                </div>
              </div>
            </v-alert>

            <!-- Server Configuration -->
            <h3 class="text-h6 mb-3">Server Configuration</h3>

            <v-text-field
              :model-value="networkSettings.externalHost"
              label="External Host"
              variant="outlined"
              readonly
              hint="Host/IP configured during installation for external access"
              persistent-hint
              class="mb-4"
              data-test="external-host-field"
            >
              <template v-slot:append>
                <v-btn
                  icon="mdi-content-copy"
                  size="small"
                  variant="text"
                  @click="copyExternalHost"
                  title="Copy External Host"
                  data-test="copy-external-host-btn"
                />
              </template>
            </v-text-field>

            <v-text-field
              :model-value="networkSettings.apiPort"
              label="API Port"
              variant="outlined"
              readonly
              hint="Default: 7272"
              persistent-hint
              class="mb-4"
              data-test="api-port-field"
            />

            <v-text-field
              :model-value="networkSettings.frontendPort"
              label="Frontend Port"
              variant="outlined"
              readonly
              hint="Default: 7274"
              persistent-hint
              class="mb-4"
              data-test="frontend-port-field"
            />

            <!-- CORS Origins Management -->
            <v-divider class="my-6" />

            <h3 class="text-h6 mb-3">CORS Allowed Origins</h3>

            <p class="text-body-2 mb-3">
              Manage which origins can make cross-origin requests to the API server.
              Add frontend URLs hosted on different domains or ports.
            </p>

            <div data-test="cors-origins-section">
              <v-list v-if="corsOrigins.length > 0" density="compact" class="mb-4">
                <v-list-item v-for="(origin, index) in corsOrigins" :key="index">
                  <v-list-item-title>{{ origin }}</v-list-item-title>

                  <template v-slot:append>
                    <v-btn
                      icon="mdi-content-copy"
                      size="small"
                      variant="text"
                      @click="copyOrigin(origin)"
                      title="Copy Origin"
                    />
                    <v-btn
                      v-if="!isDefaultOrigin(origin)"
                      icon="mdi-delete"
                      size="small"
                      variant="text"
                      color="error"
                      @click="removeOrigin(index)"
                      title="Remove Origin"
                    />
                  </template>
                </v-list-item>
              </v-list>

              <v-alert v-else type="info" variant="outlined" class="mb-4">
                No CORS origins configured. Add origins to enable cross-origin API access.
              </v-alert>

              <v-text-field
                v-model="newOrigin"
                label="Add New Origin"
                variant="outlined"
                placeholder="http://192.168.1.100:7274"
                hint="Format: http://hostname:port or http://ip:port"
                persistent-hint
                :append-icon="'mdi-plus'"
                @click:append="addOrigin"
                @keyup.enter="addOrigin"
              />
            </div>

            <!-- Network Configuration Info -->
            <v-divider class="my-6" />

            <h3 class="text-h6 mb-3">Configuration Notes</h3>

            <v-alert type="info" variant="tonal" class="mb-0">
              <div class="mb-2">
                <strong>Network settings are configured during installation.</strong>
              </div>
              <div class="text-body-2">
                To modify the external host or ports, update <code>config.yaml</code> and restart the server.
                Authentication is always enabled for all connections (local and remote).
                Use OS firewall to control network access.
              </div>
            </v-alert>
          </v-card-text>

          <v-card-actions>
            <v-spacer />
            <v-btn variant="text" @click="loadNetworkSettings">
              <v-icon start>mdi-refresh</v-icon>
              Reload
            </v-btn>
            <v-btn color="primary" :disabled="!networkSettingsChanged" @click="saveNetworkSettings">
              Save Changes
            </v-btn>
          </v-card-actions>
        </v-card>
      </v-window-item>

      <!-- Database Settings -->
      <v-window-item value="database">
        <DatabaseConnection
          :readonly="true"
          :show-title="true"
          title="PostgreSQL Database Configuration"
          :show-info-banner="true"
          info-banner-text="Database settings are configured during installation"
          :show-test-button="true"
          test-button-text="Test Connection"
          @connection-success="handleDatabaseSuccess"
          @connection-error="handleDatabaseError"
        >
          <template #actions>
            <v-btn variant="text" @click="loadDatabaseSettings">
              <v-icon start>mdi-refresh</v-icon>
              Reload from Config
            </v-btn>
          </template>
        </DatabaseConnection>
      </v-window-item>

      <!-- Integrations -->
      <v-window-item value="integrations">
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
                  My Settings → MCP Configuration
                </router-link>.
                This section provides an admin overview of available integrations.
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
                    <p class="text-caption text-medium-emphasis mb-0">AI-powered development with MCP integration</p>
                  </div>
                </div>

                <p class="text-body-2 mb-3">
                  GiljoAI Agent Orchestration MCP Server integrates seamlessly with Claude Code CLI, leveraging MCP
                  configuration via a single command‑line setup in each user’s
                  <router-link to="/settings" class="text-primary font-weight-bold">My Settings → API and Integrations → MCP Configuration</router-link>.
                </p>

                <p class="text-body-2 mb-3">
                  <strong>Sub-agent Architecture:</strong> Claude Code integration utilizes Claude Code native sub‑agent tools. This application
                  will copy templated agents, or user‑customized agents, into the Claude Code agents folder (either on a per‑user or per‑project basis).
                  The user can choose to also launch each agent in its own Claude Code terminal window. Agent integration can be found under
                  <strong>My Settings → API and Integrations → Integrations</strong>, in the <strong>Claude Code Agent Export</strong> section.
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
                      :style="{ color: theme.global.current.value.dark ? '#ffffff' : '#000000', width: '53px', height: '53px' }"
                    />
                  </v-avatar>
                  <div>
                    <h3 class="text-h6">Codex CLI</h3>
                    <p class="text-caption text-medium-emphasis mb-0">Advanced code generation and analysis</p>
                  </div>
                </div>

                <p class="text-body-2 mb-3">
                  Codex CLI integrates with our sub-agent architecture to provide powerful code generation and 
                  analysis capabilities. Sub-agents coordinate through GiljoAI MCP for complex development workflows, 
                  maintaining context and state across multiple coding sessions.
                </p>
                <p class="text-body-2 mb-3">
                  <strong>Integration model:</strong> Multiple terminal windows, one per agent. The user runs an
                  orchestrator session in one Codex CLI terminal and starts each agent in its own terminal using our
                  prepared activation prompts. This allows each agent to work autonomously and stay focused while
                  coordinating through MCP messages.
                </p>

                <!-- Configuration instructions removed; see user help files in the future -->
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
                    <p class="text-caption text-medium-emphasis mb-0">Google's advanced AI development platform</p>
                  </div>
                </div>

                <p class="text-body-2 mb-3">
                  Google Gemini CLI integrates with our sub-agent architecture to provide powerful AI-driven
                  development capabilities. Sub-agents coordinate through GiljoAI MCP for advanced development
                  workflows with enhanced reasoning and multi-modal capabilities.
                </p>
                <p class="text-body-2 mb-3">
                  <strong>Integration model:</strong> Multiple terminal windows, one per agent. The user runs an
                  orchestrator session in one Gemini CLI terminal and starts each agent in its own terminal using our
                  prepared activation prompts. This allows each agent to work autonomously and stay focused while
                  coordinating through MCP messages.
                </p>

                <!-- Configuration instructions removed; see user help files in the future -->
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
                    <p class="text-caption text-medium-emphasis mb-0">Intelligent codebase understanding and navigation</p>
                  </div>
                </div>

                <p class="text-body-2 mb-3">
                  Serena provides deep semantic code analysis, intelligent symbol navigation, and contextual 
                  understanding of your codebase. It enables agents to efficiently explore and understand 
                  project structure without reading unnecessary code, significantly improving performance 
                  and reducing token usage.
                </p>

                <div class="d-flex align-center mb-3">
                  <v-btn variant="text" size="small" color="primary" href="https://github.com/oraios/serena" target="_blank">
                    <v-icon start>mdi-github</v-icon>
                    GitHub Repository
                  </v-btn>
                  <span class="text-caption text-medium-emphasis ml-3">
                    Credit: Oraios
                  </span>
                </div>

                <v-alert type="info" variant="tonal" class="mb-0">
                  <v-icon start>mdi-account-cog</v-icon>
                  <strong>User Configuration:</strong> Each user enables Serena under User Settings → Integrations
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
      </v-window-item>

<!-- Security Settings -->
      <v-window-item value="security">
        <v-card>
          <v-card-title>Security Settings</v-card-title>
          <v-card-subtitle>Manage authentication and cross-origin security</v-card-subtitle>

          <v-card-text>
            <!-- Cookie Domain Whitelist Section -->
            <h3 class="text-h6 mb-3">Cookie Domain Whitelist</h3>

            <p class="text-body-2 mb-3">
              Configure which domain names are allowed for cross-port authentication cookies.
              This enables secure authentication when accessing the dashboard from different ports
              or subdomains on the same machine.
            </p>

            <v-alert type="info" variant="tonal" class="mb-4" :icon="false">
              <v-icon start>mdi-information</v-icon>
              IP addresses are automatically allowed. Only add domain names here (e.g., app.example.com, localhost).
            </v-alert>

            <!-- Domain List -->
            <div v-if="cookieDomains.length > 0" class="mb-4">
              <v-list density="compact" class="mb-3">
                <v-list-item
                  v-for="domain in cookieDomains"
                  :key="domain"
                  :title="domain"
                >
                  <template v-slot:append>
                    <v-btn
                      icon="mdi-delete"
                      size="small"
                      variant="text"
                      color="error"
                      @click="removeCookieDomain(domain)"
                      :aria-label="`Delete domain ${domain}`"
                    />
                  </template>
                </v-list-item>
              </v-list>
            </div>

            <!-- Empty State -->
            <v-alert
              v-else
              type="info"
              variant="outlined"
              class="mb-4"
            >
              No domain names configured. IP-based access only.
            </v-alert>

            <!-- Add Domain Form -->
            <v-text-field
              v-model="newDomain"
              label="Add Domain Name"
              variant="outlined"
              placeholder="app.example.com"
              hint="Enter a domain name (no IP addresses)"
              persistent-hint
              :rules="[validateDomain]"
              :error-messages="domainError"
              @keyup.enter="addCookieDomain"
              class="mb-2"
            >
              <template v-slot:append>
                <v-btn
                  icon="mdi-plus"
                  color="primary"
                  variant="text"
                  @click="addCookieDomain"
                  :disabled="!newDomain || !!domainError"
                  aria-label="Add domain"
                />
              </template>
            </v-text-field>

            <!-- Success/Error Feedback -->
            <v-alert
              v-if="cookieDomainFeedback"
              :type="cookieDomainFeedback.type"
              variant="tonal"
              class="mb-4"
              closable
              @click:close="cookieDomainFeedback = null"
            >
              {{ cookieDomainFeedback.message }}
            </v-alert>
          </v-card-text>

          <v-card-actions>
            <v-spacer />
            <v-btn variant="text" @click="loadCookieDomains">
              <v-icon start>mdi-refresh</v-icon>
              Reload
            </v-btn>
          </v-card-actions>
        </v-card>
      </v-window-item>
    </v-window>

    <!-- Claude Code Configuration Modal -->
    <v-dialog v-model="showClaudeConfigModal" max-width="800" scrollable>
      <v-card>
        <v-card-title class="d-flex align-center">
          <v-icon start color="primary">mdi-robot-outline</v-icon>
          How to Configure Claude Code
        </v-card-title>
        
        <v-card-text>
          <v-alert type="info" variant="tonal" class="mb-4">
            <v-icon start>mdi-information</v-icon>
            First, generate an API key under your User Profile → Settings → API and Integrations
          </v-alert>

          <v-tabs v-model="claudeConfigTab" class="mb-4">
            <v-tab value="marketplace">Marketplace Configuration</v-tab>
            <v-tab value="manual">Manual Configuration</v-tab>
            <v-tab value="download">Download Instructions</v-tab>
          </v-tabs>

          <v-window v-model="claudeConfigTab">
            <!-- Marketplace Configuration -->
            <v-window-item value="marketplace">
              <h3 class="text-h6 mb-3">Claude Code Marketplace Configuration</h3>
              <ol class="text-body-2 mb-3">
                <li class="mb-2">Open Claude Code and navigate to the MCP Tools Marketplace</li>
                <li class="mb-2">Search for "GiljoAI Agent Orchestration MCP Server"</li>
                <li class="mb-2">Click "Install" and follow the marketplace prompts</li>
                <li class="mb-2">When prompted for the API endpoint, enter: <code>http://your-server-ip:7272</code></li>
                <li class="mb-2">Enter your API key from your user profile</li>
                <li class="mb-2">Test the connection and confirm installation</li>
              </ol>
            </v-window-item>

            <!-- Manual Configuration -->
            <v-window-item value="manual">
              <h3 class="text-h6 mb-3">Manual Configuration</h3>
              <p class="text-body-2 mb-3">
                Add the following to your Claude Code MCP configuration file. 
                See <a href="https://docs.claude.com/en/docs/claude-code/mcp" target="_blank" class="text-primary">Claude Code MCP Documentation</a> for complete setup instructions.
              </p>
              
              <v-alert type="info" variant="tonal" class="mb-3" density="compact">
                <v-icon start size="small">mdi-file-document</v-icon>
                <strong>Configuration File Location:</strong>
                <br>• macOS/Linux: <code>~/.claude.json</code>
                <br>• Windows: <code>%USERPROFILE%\.claude.json</code>
              </v-alert>
              
              <v-card variant="outlined" class="mb-3">
                <v-card-text>
                  <pre class="text-caption"><code>{
  "servers": {
    "giljo-mcp": {
      "command": "mcp-client",
      "args": [
        "--server-url", "http://your-server-ip:7272",
        "--api-key", "{your-api-key-here}"
      ],
      "description": "GiljoAI Agent Orchestration MCP Server"
    }
  }
}</code></pre>
                </v-card-text>
                <v-card-actions>
                  <v-btn variant="text" size="small" @click="copyClaudeConfig">
                    <v-icon start>mdi-content-copy</v-icon>
                    Copy Configuration
                  </v-btn>
                </v-card-actions>
              </v-card>

              <p class="text-body-2">
                Replace <code>{your-api-key-here}</code> with your actual API key from your user profile.
              </p>
            </v-window-item>

            <!-- Download Instructions -->
            <v-window-item value="download">
              <h3 class="text-h6 mb-3">Download Configuration Instructions</h3>
              <p class="text-body-2 mb-3">
                Download a complete setup guide with your server-specific configuration:
              </p>
              
              <v-btn variant="outlined" color="primary" @click="downloadClaudeInstructions">
                <v-icon start>mdi-download</v-icon>
                Download Claude Code Setup Guide
              </v-btn>
            </v-window-item>
          </v-window>
        </v-card-text>

        <v-card-actions>
          <v-spacer />
          <v-btn variant="text" @click="showClaudeConfigModal = false">Close</v-btn>
        </v-card-actions>
      </v-card>
    </v-dialog>

    <!-- Codex Configuration Modal -->
    <v-dialog v-model="showCodexConfigModal" max-width="800" scrollable>
      <v-card>
        <v-card-title class="d-flex align-center">
          <v-icon start color="secondary">mdi-code-braces</v-icon>
          How to Configure Codex CLI
        </v-card-title>
        
        <v-card-text>
          <v-alert type="info" variant="tonal" class="mb-4">
            <v-icon start>mdi-information</v-icon>
            First, generate an API key under your User Profile → Settings → API and Integrations
          </v-alert>

          <v-tabs v-model="codexConfigTab" class="mb-4">
            <v-tab value="manual">Manual Configuration</v-tab>
            <v-tab value="download">Download Instructions</v-tab>
          </v-tabs>

          <v-window v-model="codexConfigTab">
            <!-- Manual Configuration -->
            <v-window-item value="manual">
              <h3 class="text-h6 mb-3">Manual Configuration</h3>
              <p class="text-body-2 mb-3">
                Add the following to your Codex CLI configuration file. 
                See <a href="https://developers.openai.com/codex/local-config#cli" target="_blank" class="text-primary">Codex CLI Configuration</a> 
                and <a href="https://developers.openai.com/codex/mcp" target="_blank" class="text-primary">Codex MCP Documentation</a> for complete setup instructions.
              </p>
              
              <v-alert type="info" variant="tonal" class="mb-3" density="compact">
                <v-icon start size="small">mdi-file-document</v-icon>
                <strong>Configuration File Location:</strong>
                <br>• macOS/Linux: <code>~/.codex/config.toml</code>
                <br>• Windows: <code>%USERPROFILE%\\.codex\\config.toml</code>
              </v-alert>
              
              <v-card variant="outlined" class="mb-3">
                <v-card-text>
                  <pre class="text-caption"><code>[giljo-mcp]
endpoint = "http://your-server-ip:7272"
api_key = "{your-api-key-here}"
description = "GiljoAI Agent Orchestration MCP Server"

[agents]
orchestrator_enabled = true
subagent_coordination = true
context_sharing = true</code></pre>
                </v-card-text>
                <v-card-actions>
                  <v-btn variant="text" size="small" @click="copyCodexConfig">
                    <v-icon start>mdi-content-copy</v-icon>
                    Copy Configuration
                  </v-btn>
                </v-card-actions>
              </v-card>

              <p class="text-body-2">
                Replace <code>{your-api-key-here}</code> with your actual API key from your user profile.
              </p>
            </v-window-item>

            <!-- Download Instructions -->
            <v-window-item value="download">
              <h3 class="text-h6 mb-3">Download Configuration Instructions</h3>
              <p class="text-body-2 mb-3">
                Download a complete setup guide with your server-specific configuration:
              </p>
              
              <v-btn variant="outlined" color="secondary" @click="downloadCodexInstructions">
                <v-icon start>mdi-download</v-icon>
                Download Codex CLI Setup Guide
              </v-btn>
            </v-window-item>
          </v-window>
        </v-card-text>

        <v-card-actions>
          <v-spacer />
          <v-btn variant="text" @click="showCodexConfigModal = false">Close</v-btn>
        </v-card-actions>
      </v-card>
    </v-dialog>

    <!-- Gemini CLI Configuration Modal -->
    <v-dialog v-model="showGeminiConfigModal" max-width="800" scrollable>
      <v-card>
        <v-card-title class="d-flex align-center">
          <v-icon start color="success">mdi-sparkles</v-icon>
          How to Configure Gemini CLI
        </v-card-title>

        <v-card-text>
          <v-alert type="info" variant="tonal" class="mb-4">
            <v-icon start>mdi-information</v-icon>
            First, generate an API key under your User Profile → Settings → API and Integrations
          </v-alert>

          <v-tabs v-model="geminiConfigTab" class="mb-4">
            <v-tab value="manual">Manual Configuration</v-tab>
            <v-tab value="download">Download Instructions</v-tab>
          </v-tabs>

          <v-window v-model="geminiConfigTab">
            <!-- Manual Configuration -->
            <v-window-item value="manual">
              <h3 class="text-h6 mb-3">Manual Configuration</h3>
              <p class="text-body-2 mb-3">
                Add the following to your Gemini CLI settings file.
                See <a href="https://github.com/google-gemini/gemini-cli" target="_blank" class="text-primary">Gemini CLI Documentation</a> for complete setup instructions.
              </p>

              <v-alert type="info" variant="tonal" class="mb-3" density="compact">
                <v-icon start size="small">mdi-file-document</v-icon>
                <strong>Configuration File Location:</strong>
                <br>• All platforms: <code>~/.gemini/settings.json</code>
              </v-alert>

              <v-card variant="outlined" class="mb-3">
                <v-card-text>
                  <pre class="text-caption"><code>{
  "mcpServers": {
    "giljo-mcp": {
      "url": "http://your-server-ip:7272",
      "apiKey": "{your-api-key-here}",
      "description": "GiljoAI Agent Orchestration MCP Server",
      "capabilities": [
        "agent_coordination",
        "context_sharing",
        "memory_persistence"
      ]
    }
  }
}</code></pre>
                </v-card-text>
                <v-card-actions>
                  <v-btn variant="text" size="small" @click="copyGeminiConfig">
                    <v-icon start>mdi-content-copy</v-icon>
                    Copy Configuration
                  </v-btn>
                </v-card-actions>
              </v-card>

              <p class="text-body-2">
                Replace <code>{your-api-key-here}</code> with your actual API key from your user profile.
              </p>
            </v-window-item>

            <!-- Download Instructions -->
            <v-window-item value="download">
              <h3 class="text-h6 mb-3">Download Configuration Instructions</h3>
              <p class="text-body-2 mb-3">
                Download a complete setup guide with your server-specific configuration:
              </p>

              <v-btn variant="outlined" color="success" @click="downloadGeminiInstructions">
                <v-icon start>mdi-download</v-icon>
                Download Gemini CLI Setup Guide
              </v-btn>
            </v-window-item>
          </v-window>
        </v-card-text>

        <v-card-actions>
          <v-spacer />
          <v-btn variant="text" @click="showGeminiConfigModal = false">Close</v-btn>
        </v-card-actions>
      </v-card>
    </v-dialog>
  </v-container>
</template>

<script setup>
import { ref, onMounted, computed } from 'vue'
import { useTheme } from 'vuetify'
import CodexMarkIcon from '@/components/icons/CodexMarkIcon.vue'
import { useRouter } from 'vue-router'
import DatabaseConnection from '@/components/DatabaseConnection.vue'
import { API_CONFIG } from '@/config/api'
import api from '@/services/api'

// Router
const router = useRouter()
const theme = useTheme()

// State
const activeTab = ref('network')

// Network settings state
const networkSettings = ref({
  externalHost: 'localhost',
  apiPort: 7272,
  frontendPort: 7274,
})
const corsOrigins = ref([])
const newOrigin = ref('')
const networkSettingsChanged = ref(false)

// Configuration modal state
const showClaudeConfigModal = ref(false)
const showCodexConfigModal = ref(false)
const showGeminiConfigModal = ref(false)
const claudeConfigTab = ref('marketplace')
const codexConfigTab = ref('manual')
const geminiConfigTab = ref('manual')

// Cookie Domain Whitelist state
const cookieDomains = ref([])
const newDomain = ref('')
const domainError = ref('')
const cookieDomainFeedback = ref(null)

// Network Settings Methods
async function loadNetworkSettings() {
  try {
    // Load from /api/v1/config endpoint only
    const response = await fetch(`${API_CONFIG.REST_API.baseURL}/api/v1/config`, {
      credentials: 'include',
      timeout: 5000,
    })

    if (!response.ok) {
      throw new Error(`Config endpoint failed: ${response.statusText}`)
    }

    const config = await response.json()

    // Set external host (configured during installation)
    networkSettings.value.externalHost = config.services?.external_host || 'localhost'

    // Set API port
    networkSettings.value.apiPort = config.services?.api?.port || 7272

    // Set Frontend port
    networkSettings.value.frontendPort = config.services?.frontend?.port || 7274

    // Set CORS origins
    corsOrigins.value = config.security?.cors?.allowed_origins || []

    console.log('[SYSTEM SETTINGS] Network settings loaded successfully')
  } catch (error) {
    console.error('[SYSTEM SETTINGS] Failed to load network settings:', error)

    // Fallback to defaults
    networkSettings.value.externalHost = 'localhost'
    networkSettings.value.apiPort = 7272
    networkSettings.value.frontendPort = 7274
    corsOrigins.value = []
  }
}

function copyExternalHost() {
  if (networkSettings.value.externalHost) {
    navigator.clipboard.writeText(networkSettings.value.externalHost)
    console.log('[SYSTEM SETTINGS] External host copied to clipboard:', networkSettings.value.externalHost)
  }
}

function isDefaultOrigin(origin) {
  return origin.includes('localhost') || origin.includes('127.0.0.1')
}

function copyOrigin(origin) {
  navigator.clipboard.writeText(origin)
  console.log('[SYSTEM SETTINGS] Origin copied to clipboard:', origin)
}

function addOrigin() {
  if (!newOrigin.value) return

  // Validate origin format
  try {
    new URL(newOrigin.value)
    if (!corsOrigins.value.includes(newOrigin.value)) {
      corsOrigins.value.push(newOrigin.value)
      newOrigin.value = ''
      networkSettingsChanged.value = true
      console.log('[SYSTEM SETTINGS] Origin added successfully')
    }
  } catch (error) {
    console.error('Invalid origin format:', error)
  }
}

function removeOrigin(index) {
  corsOrigins.value.splice(index, 1)
  networkSettingsChanged.value = true
  console.log('[SYSTEM SETTINGS] Origin removed')
}

async function saveNetworkSettings() {
  try {
    // Save CORS origins back to config
    const response = await fetch(`${API_CONFIG.REST_API.baseURL}/api/v1/config`, {
      method: 'PATCH',
      credentials: 'include',
      headers: { 'Content-Type': 'application/json' },
      body: JSON.stringify({
        security: {
          cors: {
            allowed_origins: corsOrigins.value,
          },
        },
      }),
    })

    if (response.ok) {
      networkSettingsChanged.value = false
      console.log('[SYSTEM SETTINGS] Network settings saved successfully')
    }
  } catch (error) {
    console.error('Failed to save network settings:', error)
  }
}

// Database Methods
async function loadDatabaseSettings() {
  try {
    // Fetch database config from API
    const response = await fetch(`${API_CONFIG.REST_API.baseURL}/api/v1/config/database`, {
      credentials: 'include',
    })
    const config = await response.json()

    console.log('Database settings reloaded from config')
  } catch (error) {
    console.error('Failed to load database settings:', error)
  }
}

function handleDatabaseSuccess(result) {
  console.log('Database connection successful:', result)
}

function handleDatabaseError(error) {
  console.error('Database connection failed:', error)
}

// Configuration Modal Methods
const copyClaudeConfig = () => {
  const config = `{
  "servers": {
    "giljo-mcp": {
      "command": "mcp-client",
      "args": [
        "--server-url", "http://your-server-ip:7272",
        "--api-key", "{your-api-key-here}"
      ],
      "description": "GiljoAI Agent Orchestration MCP Server"
    }
  }
}`
  navigator.clipboard.writeText(config)
  console.log('[INTEGRATIONS] Claude configuration copied to clipboard')
}

const copyCodexConfig = () => {
  const config = `[giljo-mcp]
endpoint = "http://your-server-ip:7272"
api_key = "{your-api-key-here}"
description = "GiljoAI Agent Orchestration MCP Server"

[agents]
orchestrator_enabled = true
subagent_coordination = true
context_sharing = true`
  navigator.clipboard.writeText(config)
  console.log('[INTEGRATIONS] Codex configuration copied to clipboard')
}

const downloadClaudeInstructions = () => {
  const instructions = `# Claude Code Setup Guide for GiljoAI MCP Server

## Prerequisites
1. Generate an API key from your user profile in GiljoAI dashboard
2. Ensure Claude Code is installed and configured

## Marketplace Configuration (Recommended)
1. Open Claude Code
2. Navigate to MCP Tools Marketplace
3. Search for "GiljoAI Agent Orchestration MCP Server"
4. Click "Install"
5. Enter endpoint: http://your-server-ip:7272
6. Enter your API key
7. Test connection

## Manual Configuration

**Configuration File Location:**
- macOS/Linux: ~/.claude.json
- Windows: %USERPROFILE%\\.claude.json

**Documentation:** https://docs.claude.com/en/docs/claude-code/mcp

Add the following to your Claude Code MCP configuration file:

{
  "servers": {
    "giljo-mcp": {
      "command": "mcp-client",
      "args": [
        "--server-url", "http://your-server-ip:7272",
        "--api-key", "YOUR_API_KEY_HERE"
      ],
      "description": "GiljoAI Agent Orchestration MCP Server"
    }
  }
}

## Verification
- Restart Claude Code
- Verify GiljoAI MCP tools are available
- Test agent coordination functionality

## Support
Visit your GiljoAI dashboard for additional configuration help.`

  const blob = new Blob([instructions], { type: 'text/plain' })
  const url = URL.createObjectURL(blob)
  const a = document.createElement('a')
  a.href = url
  a.download = 'claude-code-giljo-mcp-setup.txt'
  a.click()
  URL.revokeObjectURL(url)
  console.log('[INTEGRATIONS] Claude setup instructions downloaded')
}

const downloadCodexInstructions = () => {
  const instructions = `# Codex CLI Setup Guide for GiljoAI MCP Server

## Prerequisites
1. Generate an API key from your user profile in GiljoAI dashboard
2. Ensure Codex CLI is installed and configured

## Configuration
**Configuration File Location:**
- macOS/Linux: ~/.codex/config.toml
- Windows: %USERPROFILE%\\.codex\\config.toml

**Documentation:** 
- MCP Integration: https://developers.openai.com/codex/mcp
- CLI Configuration: https://developers.openai.com/codex/local-config#cli

Add to your Codex CLI configuration file:

[giljo-mcp]
endpoint = "http://your-server-ip:7272"
api_key = "YOUR_API_KEY_HERE"
description = "GiljoAI Agent Orchestration MCP Server"

[agents]
orchestrator_enabled = true
subagent_coordination = true
context_sharing = true

## Sub-Agent Workflow
1. Codex spawns specialized sub-agents for different tasks
2. GiljoAI MCP coordinates agent state and memory
3. Context sharing enables seamless handoffs
4. 70% token reduction through intelligent coordination

## Verification
- Restart Codex CLI
- Verify GiljoAI MCP connection
- Test sub-agent coordination

## Support
Visit your GiljoAI dashboard for additional configuration help.`

  const blob = new Blob([instructions], { type: 'text/plain' })
  const url = URL.createObjectURL(blob)
  const a = document.createElement('a')
  a.href = url
  a.download = 'codex-cli-giljo-mcp-setup.txt'
  a.click()
  URL.revokeObjectURL(url)
  console.log('[INTEGRATIONS] Codex setup instructions downloaded')
}

const copyGeminiConfig = () => {
  const config = `{
  "mcpServers": {
    "giljo-mcp": {
      "url": "http://your-server-ip:7272",
      "apiKey": "{your-api-key-here}",
      "description": "GiljoAI Agent Orchestration MCP Server",
      "capabilities": [
        "agent_coordination",
        "context_sharing",
        "memory_persistence"
      ]
    }
  }
}`
  navigator.clipboard.writeText(config)
  console.log('[INTEGRATIONS] Gemini configuration copied to clipboard')
}

const downloadGeminiInstructions = () => {
  const instructions = `# Gemini CLI Setup Guide for GiljoAI MCP Server

## Prerequisites
1. Generate an API key from your user profile in GiljoAI dashboard
2. Install Gemini CLI following official instructions
3. Ensure Gemini CLI is properly configured

## Installation
Install Gemini CLI using one of these methods:
- NPX: npx https://github.com/google-gemini/gemini-cli
- NPM global: npm install -g @google/gemini-cli
- Homebrew: brew install gemini-cli

## Configuration
**Configuration File Location:**
- All platforms: ~/.gemini/settings.json

**Documentation:**
- Gemini CLI: https://github.com/google-gemini/gemini-cli

Add to your Gemini CLI settings.json file:

{
  "mcpServers": {
    "giljo-mcp": {
      "url": "http://your-server-ip:7272",
      "apiKey": "YOUR_API_KEY_HERE",
      "description": "GiljoAI Agent Orchestration MCP Server",
      "capabilities": [
        "agent_coordination",
        "context_sharing",
        "memory_persistence"
      ]
    }
  }
}

## Sub-Agent Workflow
1. Gemini CLI spawns specialized sub-agents for different tasks
2. GiljoAI MCP coordinates agent state and memory
3. Enhanced reasoning with multi-modal capabilities
4. Context sharing enables seamless handoffs
5. 70% token reduction through intelligent coordination

## Multi-Modal Features
- Code analysis with visual diagrams
- Image processing for UI development
- Document analysis and generation
- Advanced reasoning capabilities

## Verification
- Restart Gemini CLI
- Verify GiljoAI MCP connection
- Test sub-agent coordination
- Validate multi-modal capabilities

## Support
Visit your GiljoAI dashboard for additional configuration help.`

  const blob = new Blob([instructions], { type: 'text/plain' })
  const url = URL.createObjectURL(blob)
  const a = document.createElement('a')
  a.href = url
  a.download = 'gemini-cli-giljo-mcp-setup.txt'
  a.click()
  URL.revokeObjectURL(url)
  console.log('[INTEGRATIONS] Gemini setup instructions downloaded')
}

// Cookie Domain Whitelist Methods
async function loadCookieDomains() {
  try {
    const response = await api.settings.getCookieDomains()
    cookieDomains.value = response.data.domains || []
    console.log('[SECURITY] Cookie domains loaded:', cookieDomains.value.length)
  } catch (error) {
    console.error('[SECURITY] Failed to load cookie domains:', error)
    cookieDomainFeedback.value = {
      type: 'error',
      message: 'Failed to load cookie domains. Please try again.'
    }
  }
}

function validateDomain(value) {
  if (!value) {
    return true // Empty is valid (optional field)
  }

  const trimmed = value.trim()

  // Check for IP address pattern (reject IPs)
  const ipPattern = /^(\d{1,3}\.){3}\d{1,3}$/
  if (ipPattern.test(trimmed)) {
    domainError.value = 'IP addresses are not allowed. Use domain names only.'
    return false
  }

  // Validate domain format
  const domainPattern = /^[a-zA-Z0-9]([a-zA-Z0-9-]{0,61}[a-zA-Z0-9])?(\.[a-zA-Z0-9]([a-zA-Z0-9-]{0,61}[a-zA-Z0-9])?)*$/
  if (!domainPattern.test(trimmed)) {
    domainError.value = 'Invalid domain format. Example: app.example.com'
    return false
  }

  domainError.value = ''
  return true
}

async function addCookieDomain() {
  const trimmed = newDomain.value.trim()

  if (!trimmed) {
    return
  }

  // Validate before submitting
  if (!validateDomain(trimmed)) {
    return
  }

  // Check for duplicates
  if (cookieDomains.value.includes(trimmed)) {
    cookieDomainFeedback.value = {
      type: 'warning',
      message: `Domain "${trimmed}" is already in the whitelist.`
    }
    return
  }

  try {
    await api.settings.addCookieDomain(trimmed)
    cookieDomains.value.push(trimmed)
    newDomain.value = ''
    domainError.value = ''
    cookieDomainFeedback.value = {
      type: 'success',
      message: `Domain "${trimmed}" added successfully.`
    }
    console.log('[SECURITY] Cookie domain added:', trimmed)
  } catch (error) {
    console.error('[SECURITY] Failed to add cookie domain:', error)
    cookieDomainFeedback.value = {
      type: 'error',
      message: error.response?.data?.detail || 'Failed to add domain. Please try again.'
    }
  }
}

async function removeCookieDomain(domain) {
  try {
    await api.settings.removeCookieDomain(domain)
    cookieDomains.value = cookieDomains.value.filter(d => d !== domain)
    cookieDomainFeedback.value = {
      type: 'success',
      message: `Domain "${domain}" removed successfully.`
    }
    console.log('[SECURITY] Cookie domain removed:', domain)
  } catch (error) {
    console.error('[SECURITY] Failed to remove cookie domain:', error)
    cookieDomainFeedback.value = {
      type: 'error',
      message: error.response?.data?.detail || 'Failed to remove domain. Please try again.'
    }
  }
}

// Lifecycle
onMounted(async () => {
  // Load database settings from config on mount
  await loadDatabaseSettings()

  // Load network settings from config on mount
  await loadNetworkSettings()

  // Load cookie domains
  await loadCookieDomains()
})
</script>

<style scoped>
</style>
