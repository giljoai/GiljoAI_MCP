# Agent Prompt Modifications Summary

## ✅ Changes Applied to AGENT_PROMPT_USER_MANAGEMENT_AND_WIZARD.md

### **Modification 1: Future MCP Clients Notice**

**Location:** Step 4 - MCP Tool Configuration (LAN/WAN mode)

**What was added:**
- Standalone API key display with copy button (shown before the full config)
- Note about future MCP clients: "Codex CLI (Coming Soon), Gemini CLI (Coming Soon)"
- Improved UI layout showing API key separately from config

**Implementation:**
```vue
<!-- API Key Display -->
<v-alert type="info" class="mb-4">
  <strong>Your Admin API Key:</strong>
  <v-text-field :value="apiKey" readonly>
    <template #append-inner>
      <v-btn icon="mdi-content-copy" @click="copyApiKey" />
    </template>
  </v-text-field>
</v-alert>

<!-- Future Clients Note -->
<v-alert type="info" variant="tonal" class="mt-4">
  <strong>Future MCP Clients:</strong>
  <ul class="mt-2">
    <li>Codex CLI (Coming Soon)</li>
    <li>Gemini CLI (Coming Soon)</li>
  </ul>
</v-alert>
```

---

### **Modification 2: Serena Separate Installation Notice**

**Location:** Step 5 - Serena Configuration

**What was added:**
- Warning alert explaining Serena must be installed separately
- Link to Serena GitHub repository: https://github.com/oraios/serena
- Updated checkbox label to clarify user must install separately

**Implementation:**
```vue
<!-- IMPORTANT: Installation Required -->
<v-alert type="warning" variant="tonal" class="mb-4">
  <strong>⚠️ Serena MCP must be installed separately</strong>
  <p class="mt-2">
    Serena is a separate MCP server that needs to be installed on your system.
  </p>
  <v-btn
    href="https://github.com/oraios/serena"
    target="_blank"
    variant="outlined"
    size="small"
    class="mt-2"
  >
    <v-icon start>mdi-github</v-icon>
    Install Serena MCP
  </v-btn>
</v-alert>

<v-checkbox
  v-model="serenaEnabled"
  label="Enable Serena (I have installed it separately)"
/>
```

---

## 🎯 Ready for Agent Execution

The agent prompt document **AGENT_PROMPT_USER_MANAGEMENT_AND_WIZARD.md** is now updated with both modifications and ready to be given to the next agent.

**Key Updates:**
1. ✅ API key shown separately with copy button in MCP Tool Config step
2. ✅ Future MCP clients notice (Codex CLI, Gemini CLI)
3. ✅ Serena installation warning with GitHub link
4. ✅ Clear checkbox label indicating separate installation required

**Next Step:** Point your next agent to this prompt document to begin implementation!
