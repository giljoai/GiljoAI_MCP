<template>
  <v-container class="legal-container py-8" max-width="900">
    <v-card class="legal-card smooth-border pa-6 pa-md-8">
      <header class="mb-6">
        <h1 class="text-h4 font-weight-bold mb-2">Terms of Service</h1>
        <p class="legal-meta mb-0">
          Last updated: 2026-05-07 — GiljoAI LLC
        </p>
      </header>

      <!-- PATRIK: review wording — this is a starter scaffold; legal review required before public launch. -->

      <section class="mb-6">
        <h2 class="text-h6 mb-2">1. Acceptance</h2>
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
        <h2 class="text-h6 mb-2">2. License framing per edition</h2>
        <ul class="legal-list">
          <li><strong>Community Edition (CE)</strong> — self-hosted. Free under the {{ licenseName }}. Run it yourself, run it for your team, run it inside your company. The license restricts only: providing the software to third parties as a hosted/managed service, tampering with license-key functionality, and removing or altering license/copyright notices.</li>
          <li><strong>Demo</strong> — hosted by GiljoAI LLC. Read-mostly, may be reset or rate-limited at any time. Intended for evaluation only.</li>
          <li><strong>Solo / Team (SaaS)</strong> — hosted commercial subscriptions provided by GiljoAI LLC under a separate Commercial License. Subject to the subscription terms accepted at sign-up. <!-- PATRIK: review wording — confirm subscription terms reference once Stripe/Polar is live. --></li>
        </ul>
      </section>

      <section class="mb-6">
        <h2 class="text-h6 mb-2">3. Acceptable use</h2>
        <p class="legal-body">You agree not to:</p>
        <ul class="legal-list">
          <li>Use the service to violate applicable law.</li>
          <li>Attempt to gain unauthorized access to other tenants' data.</li>
          <li>Probe, scan, or load-test the hosted infrastructure without written permission.</li>
          <li>Resell or sub-license access without a Commercial License.</li>
        </ul>
      </section>

      <section class="mb-6">
        <h2 class="text-h6 mb-2">4. Account responsibilities</h2>
        <p class="legal-body">
          You are responsible for safeguarding your credentials and for all
          activity that occurs under your account. Notify us at
          <a class="legal-link" href="mailto:security@giljo.ai">security@giljo.ai</a>
          if you suspect unauthorized access.
        </p>
      </section>

      <section class="mb-6">
        <h2 class="text-h6 mb-2">5. Service availability</h2>
        <p class="legal-body">
          The hosted demo and SaaS editions are provided on an "as is" basis.
          We make a reasonable effort to keep the service running but do not
          guarantee uninterrupted availability.
          <!-- PATRIK: review wording — adjust SLA language once Solo/Team contracts are finalized. -->
        </p>
      </section>

      <section class="mb-6">
        <h2 class="text-h6 mb-2">6. Sub-processors</h2>
        <p class="legal-body">
          We use <strong>Resend</strong> for transactional email,
          <strong>Cloudflare</strong> for DNS / CDN / DDoS protection, and
          <strong>PostgreSQL</strong> as the data store. See the
          <router-link class="legal-link" to="/privacy">Privacy Policy</router-link>
          for more detail.
        </p>
      </section>

      <section class="mb-6">
        <h2 class="text-h6 mb-2">7. Termination</h2>
        <p class="legal-body">
          You may delete your account at any time from <em>Account → Danger
          Zone</em>. We may suspend or terminate access in the event of
          material breach of these Terms or to protect the platform.
        </p>
      </section>

      <section class="mb-6">
        <h2 class="text-h6 mb-2">8. Governing law</h2>
        <p class="legal-body">
          <!-- PATRIK: review wording — pick jurisdiction (DE / EU / US) before public launch. -->
          These Terms are governed by the laws of the jurisdiction in which
          GiljoAI LLC is registered. Disputes will be resolved in that
          jurisdiction unless otherwise required by mandatory consumer law.
        </p>
      </section>

      <section class="mb-6">
        <h2 class="text-h6 mb-2">9. Changes</h2>
        <p class="legal-body">
          We may update these Terms. Material changes will be announced in-app
          and / or by email to the address on file at least 14 days before they
          take effect.
        </p>
      </section>

      <section class="mb-6">
        <h2 class="text-h6 mb-2">10. Contact</h2>
        <p class="legal-body">
          Questions about these Terms:
          <a class="legal-link" href="mailto:legal@giljo.ai">legal@giljo.ai</a>.
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
.legal-container {
  max-width: 900px;
  margin: 0 auto;
}

.legal-card {
  background: rgb(var(--v-theme-surface));
}

.legal-meta {
  color: var(--text-muted);
  font-size: 0.85rem;
}

.legal-body {
  color: var(--text-secondary);
  line-height: 1.65;
  font-size: 0.95rem;
}

.legal-list {
  color: var(--text-secondary);
  line-height: 1.65;
  font-size: 0.95rem;
  padding-left: 20px;
  margin: 0 0 8px;
}

.legal-list li {
  margin-bottom: 4px;
}

.legal-link {
  color: rgb(var(--v-theme-primary));
  text-decoration: none;
}

.legal-link:hover {
  text-decoration: underline;
}

.legal-footer {
  border-top: 1px solid rgba(255, 255, 255, 0.08);
  color: var(--text-muted);
  font-size: 0.85rem;
}
</style>
