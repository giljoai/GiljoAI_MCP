<template>
  <v-card variant="outlined" class="mb-4">
    <v-card-text>
      <div class="d-flex align-center mb-3">
        <v-avatar size="40" rounded="0" class="mr-2">
          <v-img src="/icons/codex_mark_white.svg" alt="Codex CLI" />
        </v-avatar>
        <h3 class="text-h6 mb-0">Codex CLI Integration</h3>
      </div>

      <p class="text-body-2 text-medium-emphasis mb-4">
        Step 1 of 2: Download the GiljoAI MCP proxy package so Codex can talk to the GiljoAI MCP
        server. After download, install it with pip from your local terminal (for example:
        <code>python -m pip install path/to/file.whl</code>).
      </p>

      <v-card variant="tonal" class="mb-3">
        <v-card-text class="pa-3">
          <div class="text-subtitle-2 font-weight-medium mb-2">Install via pip</div>
          <p class="text-body-2 text-medium-emphasis mb-2">
            1. Click the button below to download the proxy wheel.<br />
            2. In your terminal, install it with pip.<br />
            3. Then proceed to Step 2 (MCP Integration configurator) to register the MCP server.
          </p>
          <v-btn
            :href="proxyWheelUrl"
            color="primary"
            size="small"
            variant="flat"
          >
            Download MCP Proxy Package (.whl)
          </v-btn>
        </v-card-text>
      </v-card>
    </v-card-text>
  </v-card>
</template>

<script setup>
const proxyWheelUrl = '/api/mcp-installer/proxy-wheel'
</script>

<style scoped>
</style>
After the installer finishes, ask the user to restart Codex so it picks up the GiljoAI MCP server configuration.`
