<template>
  <v-app>
    <v-main>
      <router-view />
    </v-main>
    <!--
      KYB footer: SaaS/Demo only. Loaded via import.meta.glob so the static
      import is absent in CE builds (saas/ directory is stripped by the CE
      export pipeline — the glob produces an empty map and kybFooterLoader
      is undefined, so the component never mounts). The component itself also
      gates on isSaasOrDemo as a second layer of defence.
      ADR-004: SaaS conditional lazy loading via import.meta.glob.
    -->
    <component :is="kybFooterComponent" v-if="kybFooterComponent" />
  </v-app>
</template>

<script setup>
import { shallowRef, onMounted } from 'vue'

const kybFooterComponent = shallowRef(null)

// CE-export safety via import.meta.glob (same pattern as main.js saas routes).
// In private/SaaS builds Vite finds the file and bundles it into a lazy chunk.
// In CE builds saas/ is deleted before `npm run build`; the glob resolves to
// an empty map and the loader is undefined — the footer silently does not mount.
const kybFooterLoaders = import.meta.glob('@/saas/components/KybFooter.vue')
const [kybFooterLoader] = Object.values(kybFooterLoaders)

onMounted(async () => {
  if (!kybFooterLoader) return
  try {
    const mod = await kybFooterLoader()
    kybFooterComponent.value = mod.default
  } catch {
    // Non-fatal: footer fails to load silently. Login flow continues.
  }
})
</script>

<style scoped>
/* Minimal styling - authentication pages handle their own layout */
</style>
