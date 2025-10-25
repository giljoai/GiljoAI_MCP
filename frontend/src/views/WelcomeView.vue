<template>
  <v-container fluid class="fill-height welcome-container">
    <v-row align="center" justify="center">
      <v-col cols="12" md="8" lg="6">
        <v-card elevation="0" class="text-center pa-8">
          <v-img
            :src="theme.global.current.value.dark ? '/Giljo_YW.svg' : '/Giljo_BY.svg'"
            alt="GiljoAI"
            height="120"
            contain
            class="mb-6"
          ></v-img>

          <h1 class="text-h3 mb-4 font-weight-bold">
            Welcome to GiljoAI Agent Orchestration MCP Server
          </h1>

          <p class="text-h6 text-medium-emphasis mb-8">
            Intelligent multi-agent coordination for complex software development
          </p>

          <v-divider class="my-6"></v-divider>

          <v-row class="mt-8">
            <v-col cols="12" md="4">
              <v-btn
                to="/Dashboard"
                color="primary"
                size="large"
                block
                prepend-icon="mdi-view-dashboard"
              >
                Dashboard
              </v-btn>
            </v-col>
            <v-col cols="12" md="4">
              <v-btn
                to="/Products"
                color="primary"
                variant="outlined"
                size="large"
                block
                prepend-icon="mdi-package-variant"
              >
                Products
              </v-btn>
            </v-col>
            <v-col cols="12" md="4">
              <v-btn
                to="/Projects"
                color="primary"
                variant="outlined"
                size="large"
                block
                prepend-icon="mdi-folder-multiple"
              >
                Projects
              </v-btn>
            </v-col>
          </v-row>
        </v-card>
      </v-col>
    </v-row>
  </v-container>
</template>

<script setup>
import { useTheme } from 'vuetify'

const theme = useTheme()
</script>

<style scoped>
.welcome-container {
  background: linear-gradient(
    135deg,
    rgba(var(--v-theme-primary), 0.05) 0%,
    rgba(var(--v-theme-surface), 1) 100%
  );
}
</style>
