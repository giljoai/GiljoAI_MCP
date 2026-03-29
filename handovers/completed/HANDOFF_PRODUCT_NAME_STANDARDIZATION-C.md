# Product Name & Functional Description Standardization

**Date:** 2026-03-24  
**Priority:** High (pre-launch)  
**Scope:** Website, frontend app, project docs  
**Commit prefix:** [shared]

---

## Naming Rules (apply everywhere)

| Context | Use this | Example |
|---|---|---|
| Product name (all contexts) | **GiljoAI MCP** | "GiljoAI MCP gives your AI tools a shared memory." |
| Company/brand | **GiljoAI** | "© 2026 GiljoAI LLC" |
| LICENSE file only | **GiljoAI MCP Coding Orchestrator** | Keep as-is — legal specificity required |
| Informal shorthand in prose (after first mention) | **the MCP server** (lowercase "server") | "The MCP server runs on your machine." |

### Kill list — these forms are retired:

- ~~GiljoAI MCP Coding Orchestrator~~ (except LICENSE)
- ~~GiljoAI Orchestrator~~
- ~~Giljo MCP~~
- ~~MCP Orchestrator~~
- ~~GiljoAI MCP Server~~ (as a product name — "the MCP server" as shorthand is fine)

---

## Functional Description Rules

| Term | When to use |
|---|---|
| **context engineering platform** | Primary functional descriptor. Use in headlines, one-liners, README first paragraph, meta tags, Products page lead. |
| **passive orchestrator** | Technical clarification only. Use where the "no AI inference" distinction matters: getting-started docs, architecture sections, BYOAI disclaimers. Always with context, never as a standalone label. |

### Kill list — these functional descriptions are retired:

- ~~passive orchestration platform~~
- ~~persistent context layer~~

---

## Fix List: Website (index.html)

8 fixes where "GiljoAI" alone refers to the product (not the company):

1. "connects to GiljoAI via MCP" → "connects to **GiljoAI MCP** via MCP" (appears in Steps section and getting-started.html)
2. "GiljoAI assembles..." → "**GiljoAI MCP** assembles..." (landing page BYOAI note and getting-started.html)

Apply the same pattern to all 8 instances flagged in the audit. Context: any sentence where "GiljoAI" is the subject of a technical verb (assembles, provides, connects, does not call) refers to the product, not the company. Add "MCP" after "GiljoAI" in those cases.

### Website: "GiljoAI MCP Server" heading on Products page

The Products section uses "GiljoAI MCP Server" as a heading. Change to **"GiljoAI MCP"**. The word "server" can appear in surrounding prose as lowercase descriptive text, not as part of the product name.

### Website: Functional description consistency

- Replace "passive orchestration platform" (1x) with "context engineering platform"
- Replace "persistent context layer" (1x) with "context engineering platform"  
- Keep "passive orchestrator" (2x) where it appears in technical context (getting-started prerequisites, BYOAI disclaimer) — these are correct usage
- Verify "context engineering platform" appears as the lead descriptor on the Products page (already correct, 3x)

### Website: About section "The MCP Server" shorthand (6x)

**No change needed.** These read naturally as shorthand within narrative prose. Confirm they use lowercase "server" (not capitalized as a product name). If any are capitalized as "The MCP Server," lowercase to "the MCP server."

---

## Fix List: Frontend App (4 fixes)

1. `StartupQuickStart.vue`: "Giljo MCP" → **"GiljoAI MCP"**
2. Router (page title suffix): "MCP Orchestrator" → **"GiljoAI MCP"**
3. `AppBar`: "GiljoAI MCP Orchestrator" → **"GiljoAI MCP"**
4. `ServerDownView`: "GiljoAI MCP Coding Orchestrator" → **"GiljoAI MCP"**

---

## Fix List: Docs (12 fixes)

All instances across 8 files:

- "Giljo MCP" (1x) → **"GiljoAI MCP"**
- "GiljoAI Orchestrator" (1x) → **"GiljoAI MCP"**
- "GiljoAI MCP Coding Orchestrator" (10x) → **"GiljoAI MCP"**

**Exception:** Do NOT change the LICENSE file. Line 7 reads `"Software" means the GiljoAI MCP Coding Orchestrator source code` — this stays as-is.

---

## Fix List: getting-started.html (6 fixes from audit)

Same rule as index.html: where "GiljoAI" is the subject of a technical verb, it refers to the product. Add "MCP":

1. "GiljoAI provides..." → "GiljoAI MCP provides..."
2. "GiljoAI assembles..." → "GiljoAI MCP assembles..."
3. "GiljoAI does not call..." → "GiljoAI MCP does not call..."
4. "connects to GiljoAI via MCP" → "connects to GiljoAI MCP via MCP"
5. "GiljoAI's dashboard" → "the GiljoAI MCP dashboard" (or "the dashboard" if context is clear)
6. "GiljoAI assembles context..." → "GiljoAI MCP assembles context..."

---

## Verification Checklist

After all fixes:

- [ ] `grep -ri "GiljoAI MCP Coding Orchestrator"` returns only the LICENSE file
- [ ] `grep -ri "Giljo MCP"` (without "AI") returns zero results
- [ ] `grep -ri "GiljoAI Orchestrator"` returns zero results  
- [ ] `grep -ri "MCP Orchestrator"` returns zero results (except where preceded by "GiljoAI")
- [ ] `grep -ri "passive orchestration platform"` returns zero results
- [ ] `grep -ri "persistent context layer"` returns zero results
- [ ] Landing page: "context engineering platform" appears as the primary functional descriptor
- [ ] LICENSE file line 7 unchanged
- [ ] Frontend builds without errors
- [ ] Website renders correctly (check all pages: index, getting-started, privacy, terms)

---

## Do NOT change

- LICENSE file (line 7: legal name stays as "GiljoAI MCP Coding Orchestrator")
- Any instance of "GiljoAI" that clearly refers to the company (copyright notices, "GiljoAI LLC", "GiljoAI builds tools...", logo alt text)
- "Passive orchestrator" in technical/architectural contexts where the no-inference distinction matters
- "The MCP server" as lowercase shorthand in prose (About section, getting-started) — this is correct editorial usage
