<template>
  <v-container class="legal-container py-8" max-width="900">
    <v-card class="legal-card smooth-border pa-6 pa-md-8">
      <header class="mb-6">
        <h1 class="text-headline-large font-weight-bold mb-2">Terms of Service</h1>
        <p class="legal-meta mb-0">
          Last updated: 2026-05-24 — GiljoAI LLC
        </p>
      </header>

      <section class="mb-6">
        <h2 class="text-title-large mb-2">1. Acceptance</h2>
        <p class="legal-body">
          By creating an account or otherwise using this hosted service, you
          agree to these Terms of Service and to the
          <router-link class="legal-link" to="/privacy">Privacy Policy</router-link>.
          The underlying software is provided under the {{ licenseName }};
          these Terms govern your use of the hosted edition operated by
          GiljoAI LLC.
        </p>
      </section>

      <section class="mb-6">
        <h2 class="text-title-large mb-2">2. License framing per edition</h2>
        <ul class="legal-list">
          <li><strong>Community Edition (CE)</strong> — self-hosted. Free under the {{ licenseName }}. Run it yourself, run it for your team, run it inside your company. The license restricts only: providing the software to third parties as a hosted/managed service, tampering with license-key functionality, and removing or altering license/copyright notices.</li>
          <li><strong>Demo</strong> — hosted by GiljoAI LLC. Read-mostly, may be reset or rate-limited at any time. Intended for evaluation only.</li>
          <li><strong>Solo (SaaS)</strong> — hosted commercial subscriptions provided by GiljoAI LLC. These Terms of Service and the <router-link class="legal-link" to="/privacy">Privacy Policy</router-link> govern your subscription. Additional tiers (e.g. Team) may be offered in the future.</li>
        </ul>
      </section>

      <section class="mb-6">
        <h2 class="text-title-large mb-2">3. Acceptable use</h2>
        <p class="legal-body">You agree not to:</p>
        <ul class="legal-list">
          <li>Use the service to violate applicable law.</li>
          <li>Attempt to gain unauthorized access to other tenants' data.</li>
          <li>Probe, scan, or load-test the hosted infrastructure without written permission.</li>
          <li>Resell or sub-license access without a Commercial License.</li>
        </ul>
      </section>

      <section class="mb-6">
        <h2 class="text-title-large mb-2">4. Account responsibilities</h2>
        <p class="legal-body">
          You are responsible for safeguarding your credentials and for all
          activity that occurs under your account. Notify us at
          <a class="legal-link" href="mailto:admin@giljo.ai">admin@giljo.ai</a>
          if you suspect unauthorized access.
        </p>
      </section>

      <section class="mb-6">
        <h2 class="text-title-large mb-2">5. Service availability</h2>
        <p class="legal-body">
          The hosted demo and SaaS editions are provided on an "as is" basis.
          We make a reasonable effort to keep the service running but do not
          guarantee uninterrupted availability.
        </p>
      </section>

      <section class="mb-6">
        <h2 class="text-title-large mb-2">6. Sub-processors</h2>
        <p class="legal-body">
          We use a <strong>billing provider</strong> as Merchant of Record
          for paid subscriptions, <strong>Resend</strong> for transactional
          email, <strong>Cloudflare</strong> for DNS / CDN / DDoS protection,
          and <strong>PostgreSQL</strong> as the data store. See the
          <router-link class="legal-link" to="/privacy">Privacy Policy</router-link>
          for more detail.
        </p>
      </section>

      <section class="mb-6">
        <h2 class="text-title-large mb-2">7. Billing and refunds</h2>
        <p class="legal-body">
          Paid subscriptions are billed by our billing provider as Merchant
          of Record. The provider handles payment
          collection, invoicing, applicable taxes, payment methods, and
          refunds, subject to the provider's refund policy. EU/UK customers retain
          statutory withdrawal rights where applicable. Outside of statutory
          rights, past charges are generally non-refundable; exceptional
          cases are handled on a per-request basis through
          <a class="legal-link" href="mailto:support@giljo.ai">support@giljo.ai</a>.
        </p>
      </section>

      <section class="mb-6">
        <h2 class="text-title-large mb-2">8. Termination</h2>
        <p class="legal-body">
          You may delete your account at any time from <em>Account → Danger
          Zone</em>. Deletion requires email confirmation; at confirmation you
          choose immediate deletion or an optional 30-day grace period. If you
          have an active paid subscription, confirming deletion cancels it —
          your access ends with deletion and no further charges occur, and any
          remaining paid time is forfeited and is not refunded. We may suspend
          or terminate access in the event of material breach of these Terms
          or to protect the platform.
        </p>
      </section>

      <section class="mb-6">
        <h2 class="text-title-large mb-2">9. Governing law</h2>
        <p class="legal-body">
          These Terms are governed by the laws of the jurisdiction in which
          GiljoAI LLC is registered. Disputes will be resolved in that
          jurisdiction unless otherwise required by mandatory consumer law.
        </p>
      </section>

      <section class="mb-6">
        <h2 class="text-title-large mb-2">10. Changes</h2>
        <p class="legal-body">
          We may update these Terms. Material changes will be announced in-app
          and / or by email to the address on file at least 14 days before they
          take effect.
        </p>
      </section>

      <section class="mb-6">
        <h2 class="text-title-large mb-2">11. Contact</h2>
        <p class="legal-body">
          Questions about these Terms:
          <a class="legal-link" href="mailto:admin@giljo.ai">admin@giljo.ai</a>.
        </p>
      </section>

      <footer class="legal-footer mt-6 pt-4">
        <router-link class="legal-link" to="/privacy">Privacy Policy</router-link>
        <span class="mx-2">·</span>
        <router-link class="legal-link" to="/login">Back to sign in</router-link>
      </footer>
    </v-card>
  </v-container>
</template>

<script setup>
import { LICENSE_NAME_FULL } from '@/i18n/licenseCopy'

const licenseName = LICENSE_NAME_FULL
</script>

<style lang="scss" scoped>
@use '@/styles/legal-typography' as legal;
@include legal.legal-typography-page;
</style>
