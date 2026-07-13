# giljo-status — Cloudflare Pages status page

`status.giljo.ai` (INF-5083). An on-brand static status page that polls the
GiljoAI app's health and shows **Operational / Degraded / Down**.

This is a **NEW, SEPARATE** Cloudflare Pages project. It is **not** the
`giljo-app-fallback` Worker (`infra/cloudflare-fallback`) and never touches it.

---

## How it works

```
Browser ──► status site (Pages)
              │  GET /api/health   (same-origin, no CORS)
              ▼
        [functions/api/health.js]  ── server-side fetch ──► https://app.giljo.ai/health
              │
              ▼  classifies and returns JSON { state, httpStatus, latencyMs, detail, checkedAt }
```

The static page (`public/index.html`) polls `/api/health` every 30 seconds and
renders the verdict. Because the probe is a Pages Function on the **same origin**
as the page, the browser never makes a cross-origin request — so the app's strict
no-wildcard CORS allowlist is irrelevant.

**Up/down classification** accounts for the live fallback Worker, which masks an
origin outage as `200 + static HTML`:

| Origin response to `/health`                       | Verdict     |
|----------------------------------------------------|-------------|
| `200` + JSON `{"status":"healthy"}`                | Operational |
| `200` + JSON `{"status":"degraded"}`               | Degraded    |
| `200` but **not** JSON (Worker serving fallback)   | Down        |
| non-`200`, timeout, or network error               | Down        |

Brand colors mirror `frontend/src/styles/design-tokens.scss` (declared as CSS
custom properties — a standalone Pages asset can't import the SCSS, same approach
the fallback Worker uses).

---

## Layout

```
infra/cloudflare-status-page/
├── public/
│   └── index.html              # static status page (polls /api/health)
├── functions/
│   └── api/
│       └── health.js           # Pages Function: server-side /health probe
├── wrangler.toml               # Pages project config (name, output dir)
├── package.json                # wrangler devDep + deploy/dev scripts
└── README.md
```

---

## Deploy

### Isolated preview (safe — proves it works)

Deploying this NEW project to its default `*.pages.dev` URL is isolated and
harmless: it does not touch `app.giljo.ai`, the fallback Worker, or any DNS.

```bash
cd infra/cloudflare-status-page
npm install
# CLOUDFLARE_API_TOKEN must be in the environment (account-scoped token).
npx wrangler pages deploy public --project-name giljo-status
```

wrangler prints the deployment URL, e.g. `https://<hash>.giljo-status.pages.dev`.
Open it and confirm the page shows the live app status.

### Local preview

```bash
cd infra/cloudflare-status-page
npx wrangler pages dev public
```

---

## GATED — custom domain (EM + Patrik only)

Attaching `status.giljo.ai` to this project and creating/cutting over its DNS
record is **production-facing** and is **NOT** done from here. It is an EM +
Patrik step:

1. Workers & Pages → **giljo-status** → Custom domains → add `status.giljo.ai`.
2. Approve the DNS record Cloudflare proposes (a `CNAME` to the project).

Until then, the page is reachable only at its isolated `*.pages.dev` URL.
The fallback page already links to `https://status.giljo.ai`, so that link goes
live the moment the custom domain is attached.
