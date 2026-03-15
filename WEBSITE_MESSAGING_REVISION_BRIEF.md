# GiljoAI.com — Website Messaging Revision Brief

**Date:** 2026-03-13
**Purpose:** Section-by-section messaging revision guide for `index.html`
**Format:** Current → Proposed → Rationale for each section
**Audience:** Patrik (decision-maker) + Claude Code agents (implementers)

---

## CRITICAL FIXES (Do these first, regardless of creative decisions)

### FIX-1: License Language — 7 locations

The site says "MIT Licensed" or "open source" in multiple places. The actual license is **GiljoAI Community License v1.0** (free for single user, commercial license required for 2+ users). CLAUDE.md explicitly prohibits using "MIT," "open source," or "open core."

| Location | Line(s) | Current Text | Replacement |
|----------|---------|-------------|-------------|
| Hero badge | ~1633 | `Open Source MCP Server` | `Free Community Edition` |
| Hero trust row | ~1647 | `MIT Licensed` | `Free for Individual Use` |
| CE edition card | ~1989 | `MIT Licensed` (list item) | `GiljoAI Community License` |
| CE edition card (Products tab) | ~2210 | `Community Edition — Free, MIT Licensed` | `Community Edition — Free` |
| About tab Principles | ~2124-2125 | `Open Source First` / `Community edition is MIT licensed` | `Source Available` / `Community Edition is free under the GiljoAI Community License. Full source code. Contribute, fork, customize.` |
| About tab Our Approach | ~2094 | `Community Edition is open source and self-hosted` | `Community Edition is free and self-hosted` |
| Footer | ~2322 | `Open source under MIT License.` | `© 2026 GiljoAI LLC. Community Edition free under GiljoAI Community License.` |

### FIX-2: sales@giljoai.com

Line ~2009: The SaaS edition CTA links to `sales@giljoai.com`. Verify this email exists and is monitored, or change to `info@giljo.ai` (which is in the footer).

### FIX-3: "Project Management Appliance" status

Lines ~2244-2252: Listed as "In Development" but this is not an active initiative in current project docs. Change badge to `Exploring` or `Planned` to avoid setting expectations.

---

## TAB 1: PRODUCT — Section-by-Section Revision

### SECTION 1: Hero (lines ~1622–1695)

**Current:**
- Badge: "Open Source MCP Server"
- Headline: "Define Once. Orchestrate Everything."
- Subheadline: "Centralized context turns isolated AI tools into coordinated development teams. Your agents already know the plan."
- Trust row: MIT Licensed | Self-Hosted | Privacy First

**What's wrong:** Leads with WHAT (orchestration mechanics) instead of WHY (the pain it solves). "Define Once. Orchestrate Everything." is technically accurate but emotionally flat — it reads like infrastructure middleware, not a tool that changes how you work. The visitor has to already understand multi-agent orchestration to care.

**Proposed:**

- Badge: `Free Community Edition`
- Headline: `Your AI Agents Forget Everything.` / `Every. Single. Time.`
- Subheadline: `GiljoAI MCP gives them a persistent brain. Define your product once — vision, architecture, decisions — and every agent inherits it. Across tools. Across sessions. Getting smarter each time.`
- Trust row: `Free for Individual Use` | `Self-Hosted` | `Privacy First`

**Rationale:** The headline names the felt pain that every Claude Code / Codex / Gemini user already experiences. "Every. Single. Time." adds emotional weight. The subheadline resolves the pain with the product, and introduces the compounding intelligence angle (360 Memory) immediately. "Define Once. Orchestrate Everything." moves to a section header later in the page where it can do structural work rather than emotional work.

**Alternative headline option (less aggressive):**
`Stop Re-Explaining Your Project to AI.`
Subheadline: `GiljoAI MCP is the persistent context layer for AI-assisted development. Define your product once. Every agent — Claude Code, Codex, Gemini — inherits the full picture.`

**Terminal mockup (lines ~1664–1691):** Keep as-is. It's clean and functional.

---

### SECTION 2: Works With strip (lines ~1697–1727)

**Current:** "Works seamlessly with" + Claude Code, Codex CLI, Gemini, Any MCP Client

**Proposed:** No copy changes needed. This is effective social proof. Consider adding logo tooltips or brief one-liners if you add more integrations later.

---

### SECTION 3: Problem-Solution (lines ~1729–1774)

**Current:**
- Header: "AI Tools Are Powerful. But Isolated."
- Body: "Every AI coding assistant hits the same wall. No memory between sessions. No coordination between tasks. Every prompt starts from scratch..."
- Three cards: Persistent Project Memory, Coordinated Agent Teams, Deploy Your Way

**What's wrong:** This is arguably the strongest copy on the entire page, but it's below the fold, after the hero and the Works With strip. It should be the *emotional opening*, not a mid-page section. If you adopt the pain-first hero above, this section becomes the "how we solve it" expansion rather than the problem statement.

**Proposed restructuring:**

Move the problem statement energy into the hero (done above). Repurpose this section as **"Three Things That Change"** — the concrete outcomes, not just features:

- Header: `What Changes When Your Agents Have Context`
- Card 1: **"Nothing Is Lost Between Sessions"** → `Every project writes to 360 Memory automatically. Architecture decisions, patterns, what worked, what didn't. Your fifth project starts with the intelligence of the first four. Optionally enrich with git commit history for the complete picture.`
- Card 2: **"Six Agents, One Mission"** → `An Orchestrator reads your product definition, generates a plan, and assigns focused missions to five specialist agents — Analyzer, Implementer, Tester, Reviewer, Documenter. They coordinate through structured handoffs. You monitor from a live dashboard.`
- Card 3: **"Your Infrastructure, Your Rules"** → `Community Edition runs entirely on your machine. No telemetry. No cloud dependency. Full source code. SaaS Edition adds team features when you're ready.`

**Rationale:** "Deploy Your Way" is a weak third card — deployment model is a feature, not an outcome. Framing it as "Your Infrastructure, Your Rules" makes it about control, which resonates with both the privacy-conscious developer and the enterprise evaluator. Card 1 now integrates both 360 Memory AND the GitHub integration as a layered intelligence story. Card 2 surfaces the orchestration workflow more concretely.

---

### SECTION 4: How It Works (lines ~1777–1821)

**Current:** 4 steps: Install → Connect → Describe → Orchestrate

**What's wrong:** Steps 3 and 4 skip the magic moment. Between "describe what you're building" and "agents spawn" there's a missing beat — the system generates a mission plan, compiles context, and produces a ready-to-paste prompt. That's the "wow" moment that differentiates GiljoAI from everything else.

**Proposed: 5 steps**

1. **Install** → `One command: python startup.py. Dependencies, migrations, and a setup wizard handle the rest.`
2. **Define Your Product** → `Upload your vision document. Describe your tech stack, architecture, and guidelines. This becomes the single source of truth every agent reads from.`
3. **Launch a Project** → `Write a human description of what you want done. The system generates a detailed mission plan from your full product context. Click Stage — a ready-to-paste prompt hits your clipboard.`
4. **Paste and Go** → `Paste the prompt into Claude Code, Codex, or Gemini. The orchestrator spawns specialized agents, each with role-specific missions drawn from your product definition.`
5. **Monitor and Close** → `Watch progress on the real-time dashboard. When the project completes, the system writes a closeout summary to 360 Memory. Your next project starts smarter.`

**Rationale:** The current 4-step flow hides the two things that make GiljoAI unique: (a) the prompt generation / clipboard moment, and (b) the closeout-to-memory loop. Adding these steps tells the full story of a development cycle, not just setup.

---

### SECTION 5: Capabilities grid (lines ~1823–1898)

**Current:** "Built for Serious Development" / "Not a prototype. Not a wrapper." / 6 cards

**What's wrong:** "Not a prototype. Not a wrapper." is defensive positioning — it tells visitors what you're NOT, which implies they might think you are. The 6 cards are feature-dense but treat all capabilities as equal weight. 360 Memory (the actual differentiator) lives in the Integrations section below, not here.

**Proposed revision:**

- Header: `Built for Production` (drop the defensive "not a prototype" language)
- Subheader: `380+ tests. Sub-100ms response times. 61 tenant isolation regression tests. The same infrastructure we use to build our own products.`

Keep 6 cards but reorder by user value, not technical category:

1. **Smart Context Delivery** — `10 context categories with tiered depth control. Each agent gets exactly what they need — product specs, architecture, vision docs, testing strategy — sized to their role and mission. 70-85% token reduction versus loading everything.`
2. **Multi-Agent Orchestration** — (keep current copy, it's solid)
3. **Real-Time Dashboard** — (keep current copy)
4. **Agent Template System** — (keep current copy but drop "per tenant" — that's SaaS language for a CE audience)
5. **Multi-Tenant Isolation** — (keep current copy)
6. **MCP-over-HTTP** — (keep, but consider moving to a "Technical Details" expandable section for advanced users)

**Rationale:** Leading with Smart Context Delivery — and including the 70-85% token reduction number — puts your actual technical innovation front and center. That number is concrete, memorable, and directly translates to cost savings (fewer tokens = cheaper API bills).

---

### SECTION 6: Integrations & Built-in Tools (lines ~1901–1964)

**Current:** 3 built-in cards (360 Memory, Context Configurator, Agent Template Manager) + 2 optional (Serena, GitHub Context Query)

**What's wrong:** 360 Memory is buried as one of three "built-in" integrations, presented at the same visual weight as Context Configurator. It deserves more prominence — this is the compounding intelligence feature that nobody else has.

**Proposed:**

Elevate 360 Memory to its own section ABOVE the integrations grid. Give it a dedicated block:

**New section: "Projects Get Smarter Over Time"**
> `Every completed project writes a memory entry: what was built, key decisions, patterns discovered, what worked. Your tenth project starts with the accumulated intelligence of the first nine. This is 360 Memory — persistent, automatic, cumulative. Optionally enrich it with git commit history for the complete development timeline.`

Then keep Context Configurator and Agent Template Manager as the "Built-in Tools" row, and Serena + GitHub as "Optional Integrations."

**Rationale:** 360 Memory is not an "integration" — it's a core product behavior. Presenting it alongside a context configurator and a template editor undersells it dramatically. It's the difference between "we have a settings panel" and "your AI agents develop institutional knowledge."

---

### SECTION 7: Editions (lines ~1967–2013)

**Current:** Community Edition (Free Forever) vs SaaS Edition (Contact for Pricing)

**Proposed changes:**

- CE card: Replace "MIT Licensed" with "GiljoAI Community License" (see FIX-1)
- CE card: Add `Source code included` as a list item to replace the MIT line
- SaaS card: Change CTA from "Contact Sales" to "Join the Waitlist" (it's not available yet — "Contact Sales" implies you can buy it today)
- SaaS card: Verify `sales@giljoai.com` exists (see FIX-2)
- Consider adding a line under the SaaS card: `SaaS Edition is a deployment mode of the same engine, not a separate product.` — this reinforces your buyer-based edition philosophy

---

### SECTION 8: Tech Stack pills (lines ~2015–2032)

**Current:** Python, FastAPI, PostgreSQL 18, Vue 3, Vuetify 3, WebSocket, MCP Protocol, SQLAlchemy

**Proposed:** Keep as-is. This is well-executed trust signaling for technical evaluators. No changes needed.

---

### SECTION 9: Bottom CTA (lines ~2034–2059)

**Current:** "Ready to orchestrate?" / "Get started in under 10 minutes."

**Proposed:**
- Bubble: `Ready to stop re-explaining your project?`
- Sub: `Install in under 10 minutes. Define your product. Let your agents do the rest.`

**Rationale:** Echoes the hero's pain-first framing and bookends the page with the same emotional thread. "Ready to orchestrate?" assumes the visitor has bought into orchestration as a concept — but at the bottom of the page, you want to reconnect with the original motivation.

---

## TAB 2: ABOUT — Section-by-Section

### About Hero (lines ~2069–2073)

**Current:** "What We're Building" / "GiljoAI builds tools that organize knowledge so people, and AI, can do their best work."

**Proposed:** Keep. This is strong and appropriately broad for the About page.

### Problem / Approach cards (lines ~2084–2096)

**Current copy is solid.** Two edits:
- Remove "open source" from the Our Approach card (line ~2094): change to "free and self-hosted"
- The Problem card's second paragraph — "Developers end up spending as much time managing their AI tools as actually building" — is excellent. Consider promoting a version of this to the Product tab hero area.

### Beyond Developer Tools (lines ~2100–2112)

**Current copy is strong.** One edit: "We're also developing a project management appliance" — soften to "We're exploring" unless this is an active initiative.

### Principles (lines ~2115–2137)

See FIX-1 for the "Open Source First" → "Source Available" change. Consider renaming the card to **"Transparency First"** — this preserves the spirit while avoiding the "open source" term.

### Founder's Note (lines ~2141–2152)

**Do not touch this.** It's the best writing on the site. The emotional arc from "tired of re-explaining" to "families, caregivers, anyone who could use a system that remembers when remembering gets hard" is genuinely moving and authentic.

---

## TAB 3: PRODUCTS — Section-by-Section

### Products header (lines ~2164–2167)

**Current:** Keep as-is. Clean and effective.

### MCP Server card (lines ~2169–2220)

**Proposed changes:**
- Fix "MIT Licensed" in CE edition box (line ~2210)
- The "Key Capabilities" 2x3 grid repeats the Product tab content almost verbatim. Consider condensing to 3 capabilities instead of 6, and linking to the Product tab for details: "See full capabilities →"
- Add a concrete number: `30+ MCP tools | 6 agent templates | 380+ tests`

### What's Next teasers (lines ~2225–2255)

- Memory Assistant: Keep. The "In Development" badge is accurate per project docs.
- PM Appliance: Change badge to "Exploring" or "Planned" (see FIX-3).

---

## FOOTER (lines ~2264–2325)

### Fix required:
- Line ~2322: Change `Open source under MIT License.` to `© 2026 GiljoAI LLC. Community Edition free under GiljoAI Community License.`

### Observation:
The tagline "Imagine having a conversation with everything you know." is beautiful — but it belongs to the Memory Assistant, not the MCP Server. Right now it's floating in the footer with no connection to anything on the page. Two options:
1. Keep it as a brand-level aspiration (works if you think of GiljoAI as the umbrella brand)
2. Save it for the Memory Assistant product page when that launches (where it will have maximum emotional impact)

I'd lean toward option 1 — it works as a brand statement and plants a seed for visitors who explore your About page.

---

## META TAGS & SEO (lines ~6–21)

Update to match new messaging:

```html
<meta name="description" content="GiljoAI MCP — the persistent context layer for AI-assisted development. Define your product once. Every AI agent inherits the full picture. Works with Claude Code, Codex, Gemini.">
<meta property="og:title" content="GiljoAI MCP — Your AI Agents Forget Everything. We Fix That.">
<meta property="og:description" content="Persistent context, coordinated agent teams, 360 Memory that makes every project smarter. Free Community Edition. Self-hosted.">
<meta name="twitter:title" content="GiljoAI MCP — Your AI Agents Forget Everything. We Fix That.">
<meta name="twitter:description" content="Persistent context, coordinated agent teams, 360 Memory. Free. Self-hosted. Works with Claude Code, Codex, Gemini.">
```

Also update `<title>` tag (line ~22):
```html
<title>GiljoAI MCP — AI Agents That Remember Your Project</title>
```

---

## STRUCTURAL RECOMMENDATIONS (Optional, higher effort)

### ADD: Industry Context Section (new, between Hero and Problem-Solution)

A brief "why now" section that connects GiljoAI to the industry shift from vibe coding to agentic engineering. This is NOT marketing fluff — it's context that helps visitors understand where your product sits in the landscape.

> **The developer's job just changed.**
> AI coding tools are everywhere. But using them well — defining products clearly enough for AI to execute, coordinating multiple agents, maintaining knowledge across sessions — that's a new discipline. Some call it agentic engineering. Some call it context engineering. We call it the reason we built GiljoAI MCP.

**Rationale:** The terminology research shows the industry is actively searching for vocabulary around this shift. Naming it positions you as informed and ahead of the curve without being jargon-heavy.

### ADD: "Who This Is For" Section (new, after Problem-Solution)

Two persona cards that acknowledge the dual audience:

**For the builder with a vision:**
> You know what you want to build. You don't have a dev team. AI tools are powerful but chaotic — every session starts over, context is lost, nothing connects. GiljoAI gives you the structure: define your product once, and AI agents execute with full context, every time.

**For the experienced developer:**
> Your job description just expanded. You're the architect, the PM, and the agent coordinator. You need infrastructure that handles multi-agent orchestration, persistent context, and session continuity — so you can focus on direction, not repetition.

**Rationale:** The messaging research identified these two personas. The current site speaks to neither explicitly. This section tells each visitor "yes, this is for you" within the first few seconds.

---

## VISUAL DESIGN: LAYOUT & SCREENSHOT PLACEMENT

> **Note:** All recommendations below work within the existing brand system — colors, fonts, glassmorphism, gradients, and component styles are unchanged. These are layout structure and content placement recommendations only.

### The Core Problem: No Visual Proof

The rendered page is approximately 6 full viewport scrolls of text, icons, and cards without a single screenshot of the actual product. A visitor reads about multi-agent orchestration, real-time dashboards, 360 Memory, and agent templates — but never *sees* any of it. The terminal mockup showing `python startup.py` is the only visual, and it shows setup, not the product.

This is the single highest-impact visual change available: add product screenshots at strategic points in the scroll flow.

### Screenshot Placement Plan (3 primary + 1 optional)

**PLACEMENT 1: Between "How It Works" and "Built for Serious Development"**
- **Screenshot:** Staging view (the three-column layout — `jobss_stagingpng.png`)
- **Why here:** This is the natural "proof moment." The visitor has just read the 4-5 step workflow. Now show them what that workflow actually looks like. The staging view captures the entire product story in one frame: human description on the left, generated mission in the center, agent team on the right.
- **Implementation:** Full-width within the `.container` (max 1200px). Use existing `.glass-card` styling as a frame with subtle border. Add a brief caption below: *"The Staging view: your description becomes a mission. Agents are assigned automatically."*
- **Layout pattern:** Single image, centered, with generous vertical padding above and below. No grid — let it breathe.

**PLACEMENT 2: Inside the elevated 360 Memory section (new section per messaging brief)**
- **Screenshot:** Context Priority Configuration (`context_manager.png`)
- **Why here:** This screenshot visually proves the "you control what context agents receive" claim. The tiered priority toggles (CRITICAL / IMPORTANT / REFERENCE) and depth controls (Vision Documents, 360 Memory at "3 projects", Git History at "25 commits") are immediately readable and impressive.
- **Implementation:** Place to the right of the 360 Memory text block in a two-column layout. Text left, screenshot right — mirrors the hero section's text-left / terminal-right pattern.
- **Layout pattern:** `.hero-grid` style (1fr 1fr) reused. Screenshot in a container with the existing terminal styling (dark background, subtle border, dot header).

**PLACEMENT 3: Inside the "Built for Production" capabilities section**
- **Screenshot:** Implementation view — completed project (`jobs_implement.png`)
- **Why here:** Seven agents all showing green "Complete" with durations and step counts is visual proof of production readiness. It backs up the "380+ tests, sub-100ms" claim with a real completed run.
- **Implementation:** Place above the 6 capability cards as a section lead image. Full-width within container. Frame with existing card styling.
- **Layout pattern:** Single image above the grid, same width as the grid below it. Creates a visual anchor before the cards.

**PLACEMENT 4 (OPTIONAL): In "How It Works" Step 2 — "Define Your Product"**
- **Screenshot:** Edit Product / Tech Stack tab (`Product_mgmt_add_product.png`)
- **Why here:** Shows the tabbed product definition form with actual data. Proves the "define your product in rich detail" claim. The "Used as context source by orchestrator" note in green connects definition to execution.
- **Implementation:** Smaller format — approximately 60% width, right-aligned, alongside the step text. Or as an expandable/hover detail.
- **Layout pattern:** This is a supporting detail, not a hero image. Keep it secondary to Placements 1-3.

### Layout Rhythm Improvements (No Brand Changes)

**Break up the card grid monotony.**
Currently the page flows: 3 cards → 4 steps → 6 cards → 3 cards + 2 cards → 2 cards. Every section is a grid of same-weight elements. Two approaches to add variety without changing the design system:

- **Alternate section layouts:** After a 3-column card grid, use a 2-column text+image layout (screenshot placement 2 does this). After that, return to a grid. The alternation creates visual rhythm — Loopr.ai does this with their scrolling capability numbers that break up their card sections.
- **Lead card emphasis:** In the 6-card capabilities grid, make the first card (Smart Context Delivery or Multi-Agent Orchestration) span 2 columns instead of 1. Uses the same `.glass-card` styling but at double width, signaling "this is the most important capability." The remaining 5 cards fill the grid below it as 3+2 or in a continued 3-column flow.

**Add a full-bleed visual break.**
Between the Problem-Solution section and the How It Works section, consider a full-width product screenshot (Placement 1 candidate) that breaks edge to edge — not constrained by `.container`. This creates a "moment of arrival" that interrupts the text flow in a good way. The Anthropic product page uses this pattern — large visual moments between text sections that let the reader breathe.

**The CTA section needs more weight.**
The bottom CTA ("Ready to orchestrate?") currently feels like a quiet ending after a long page. Two options:
1. Add the completed project screenshot (Placement 3) here instead of or in addition to the capabilities section — showing "this is what success looks like" as the final image before the button.
2. Increase the vertical padding and add a second line of social proof (test count, agent count, or a user quote when available).

### Screenshot Preparation Notes for Implementation

- All screenshots show the product name "TinyContacts" — this is fine for launch (real usage data looks authentic), but consider whether you want to create a demo product with a more aspirational name for marketing screenshots later.
- Screenshots are dark-themed, matching the site perfectly. No visual clash.
- Crop screenshots to remove browser chrome if present. Show just the application UI.
- For retina/high-DPI displays, ensure screenshots are at least 2x the display size (e.g., if displaying at 1200px wide, the source image should be 2400px wide).
- Add subtle rounded corners and a thin border (using existing `--glass-border` variable) to frame screenshots consistently with the card design language.

### Design Patterns Referenced

**Loopr.ai scroll-triggered capability numbering:** Their capabilities page uses large numbers (01, 02, 03, 04) that animate on scroll, with each capability getting a distinct visual block rather than equal-weight cards. This is more effort to implement but creates strong visual hierarchy. A simpler version: use the existing step-number gradient circles as section markers for key features, creating a numbered "tour" through the product.

**Anthropic/Claude product page pattern:** Uses generous whitespace, alternating text-left/image-right and text-right/image-left layouts, and large product screenshots as section dividers. The "contemporary doodle" feel comes from hand-drawn illustration accents — something the Giljo mascot already provides at a basic level. Consider using the mascot face as a recurring visual accent (you already do this in the CTA bubble) in other sections to maintain that warmth.

**Key principle for a solo operator:** You don't need custom illustrations or animation. Clean screenshots in your existing card frames, placed at the right moments in the scroll flow, will do more for conversion than any amount of design polish. The screenshots you already have are high quality and perfectly themed.

---

## IMPLEMENTATION PRIORITY

1. **FIX-1 through FIX-3** — License and factual corrections. Non-negotiable. Do first.
2. **Hero revision** — Highest-impact single change. Pain-first headline.
3. **Screenshot Placement 1** — Staging view between How It Works and Capabilities. Biggest visual impact for least effort.
4. **360 Memory elevation + Screenshot Placement 2** — New section with Context Configuration screenshot alongside.
5. **How It Works expansion** — Add the prompt generation and closeout steps.
6. **Problem-Solution reframe** — Shift from problem statement to outcomes.
7. **Screenshot Placement 3** — Completed project view in capabilities section.
8. **Meta tags / SEO** — Quick win, high leverage for discoverability.
9. **Structural additions** (industry context, personas, layout rhythm) — Higher effort, do if time allows before CE launch.

---

## WHAT THIS DOCUMENT IS NOT

This is a messaging brief, not final HTML. It provides:
- Exact text replacements where the change is surgical
- Directional copy where the change requires creative judgment
- Structural recommendations where sections should move, merge, or be added

The implementing agent should use the line references to locate sections but should read surrounding HTML context before making changes, as line numbers may shift during edits.
