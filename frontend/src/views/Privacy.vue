<template>
  <v-container class="legal-container py-8" max-width="900">
    <v-card class="legal-card smooth-border pa-6 pa-md-8">
      <header class="mb-6">
        <h1 class="text-h4 font-weight-bold mb-2">Privacy Policy</h1>
        <p class="legal-meta mb-0">
          Last updated: 2026-05-07 — GiljoAI LLC
        </p>
      </header>

      <!-- PATRIK: review wording — this is a starter scaffold; legal review required before public launch. -->

      <section class="mb-6">
        <h2 class="text-h6 mb-2">1. Who we are</h2>
        <p class="legal-body">
          This service is operated by GiljoAI LLC ("we", "us"). It is licensed
          under the {{ licenseName }}. This Privacy Policy describes what data
          the hosted service collects, why, and how it is stored.
        </p>
      </section>

      <section class="mb-6">
        <h2 class="text-h6 mb-2">2. What we collect</h2>
        <ul class="legal-list">
          <li><strong>Account data</strong> — your email, display name, and authentication metadata (password hashes, session tokens).</li>
          <li><strong>Product data</strong> — projects, tasks, agent missions, and messages you create inside the platform.</li>
          <li><strong>Operational logs</strong> — request logs, error traces, and audit events. <!-- PATRIK: review wording — confirm retention window before launch. --></li>
          <li><strong>Browser metadata</strong> — IP address and user-agent, used for rate-limiting and security.</li>
        </ul>
      </section>

      <section class="mb-6">
        <h2 class="text-h6 mb-2">3. Where data is stored</h2>
        <p class="legal-body">
          All product data is stored in <strong>PostgreSQL</strong> on
          infrastructure operated by GiljoAI LLC. Data is scoped per tenant —
          each organization's records are isolated by tenant key on every query.
        </p>
      </section>

      <section class="mb-6">
        <h2 class="text-h6 mb-2">4. Sub-processors</h2>
        <p class="legal-body">We use the following third parties to operate the service:</p>
        <ul class="legal-list">
          <li><strong>Resend</strong> — transactional email (registration, password reset, account-deletion confirmation).</li>
          <li><strong>Cloudflare</strong> — DNS, CDN, and DDoS protection in front of the hosted edition.</li>
          <li><strong>PostgreSQL</strong> — primary data store, hosted on GiljoAI LLC infrastructure.</li>
        </ul>
        <!-- PATRIK: review wording — add Paddle (Merchant of Record) as the billing processor here when payments go live; Paddle handles tax compliance globally. -->
      </section>

      <section class="mb-6">
        <h2 class="text-h6 mb-2">5. How we use your data</h2>
        <p class="legal-body">
          We use account and product data only to operate the service you have
          asked us to operate. We do not sell your data and we do not use it
          for advertising. Aggregated, anonymized usage statistics may be used
          to improve the platform.
          <!-- PATRIK: review wording — confirm whether aggregated stats clause is acceptable for the EU launch. -->
        </p>
      </section>

      <section class="mb-6">
        <h2 class="text-h6 mb-2">6. Your rights</h2>
        <p class="legal-body">
          You can request export or permanent deletion of your account data at
          any time from <em>Account → Danger Zone</em> inside the app, or by
          emailing
          <a class="legal-link" href="mailto:privacy@giljo.ai">privacy@giljo.ai</a>.
          Confirmed deletions are purged 30 days after confirmation.
        </p>
      </section>

      <section class="mb-6">
        <h2 class="text-h6 mb-2">7. Self-hosted (CE) users</h2>
        <p class="legal-body">
          If you run GiljoAI MCP on your own infrastructure under the
          {{ licenseName }}, this Privacy Policy does not apply — your data
          stays on your hardware and we have no access to it. This document
          covers only the hosted demo and SaaS editions.
        </p>
      </section>

      <section class="mb-6">
        <h2 class="text-h6 mb-2">8. Contact</h2>
        <p class="legal-body">
          Questions about this policy:
          <a class="legal-link" href="mailto:privacy@giljo.ai">privacy@giljo.ai</a>.
        </p>
      </section>

      <footer class="legal-footer mt-6 pt-4">
        <router-link class="legal-link" to="/terms">Terms of Service</router-link>
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
