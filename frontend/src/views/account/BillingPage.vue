<template>
  <v-card variant="flat" class="smooth-border billing-card" data-test="billing-stub">
    <v-card-text class="pa-6 text-center">
      <v-icon size="48" color="primary" class="mb-3">mdi-credit-card-outline</v-icon>
      <h2 class="text-h6 mb-2">Plan management coming with Solo launch</h2>
      <p class="text-body-2 text-muted-a11y">
        Billing, plan upgrades, and invoice history will appear here when the Solo plan ships.
        Until then, every workspace runs on the free tier.
      </p>
    </v-card-text>
  </v-card>
</template>

<script setup>
// Stub view -- intentionally empty. FE-0017 will wire Stripe billing here.
</script>

<style lang="scss" scoped>
.billing-card {
  max-width: 640px;
  margin: 0 auto;
}
</style>
