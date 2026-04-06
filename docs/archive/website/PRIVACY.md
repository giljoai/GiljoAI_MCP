# GiljoAI — Privacy Policy

**Effective Date:** April 5, 2026
**Last Updated:** April 5, 2026

---

## The Short Version

GiljoAI MCP Community Edition runs entirely on your machine. We cannot see, access, or collect your data. There is no telemetry, no analytics, no phone-home behavior. Your products, projects, agent configurations, and 360 Memory entries never leave your local system.

The giljo.ai website is a standard informational site with minimal data practices.

---

## 1. What GiljoAI MCP Stores (On Your Machine)

When you use the Community Edition, the following data is stored in **your local PostgreSQL database** on hardware you control:

- **Account data**: Username, bcrypt-hashed password, recovery PIN (hashed), API keys (hashed)
- **Product definitions**: Product name, description, tech stack, architecture, testing configuration
- **Vision documents**: Uploaded `.md` and `.txt` files, with auto-generated summaries
- **Project data**: Project names, descriptions, generated missions, status, taxonomy
- **Agent data**: Agent templates, job records, execution history, inter-agent messages
- **360 Memory**: Accumulated project knowledge — summaries, decisions, outcomes, patterns
- **Git history**: Commit references (if GitHub integration is enabled by you)
- **Session data**: MCP session records, JWT tokens

**All of this data resides on your machine, in your database.** GiljoAI LLC has no access to it. We do not operate any server that your installation connects to.

---

## 2. What GiljoAI MCP Does NOT Do

- **No telemetry**: The software does not send usage data, error reports, or analytics to GiljoAI or any third party
- **No cloud dependency**: No internet connection is required to run the software after installation
- **No data collection**: We do not collect, store, or process any data from your GiljoAI MCP installation
- **No tracking**: No cookies, pixels, or identifiers are placed by the GiljoAI MCP application
- **No account registration with GiljoAI**: Your admin account is local to your installation. We don't know it exists.

---

## 3. Third-Party AI Coding Agents

GiljoAI MCP coordinates with AI coding agents (Claude Code, Codex CLI, Gemini CLI) that you configure and connect yourself. When your AI coding agent connects to GiljoAI MCP via MCP protocol:

- Your AI coding agent sends requests to your local GiljoAI MCP server
- GiljoAI MCP responds with context, tool results, and coordination data
- Your AI coding agent then communicates with its own AI model provider (Anthropic, OpenAI, Google, etc.)

**The data your AI coding agent sends to its model provider is governed by that provider's privacy policy, not ours.** GiljoAI MCP has no control over and no visibility into what your AI coding agent transmits to its backend.

We recommend reviewing:
- [Anthropic's Privacy Policy](https://www.anthropic.com/privacy) (Claude Code)
- [OpenAI's Privacy Policy](https://openai.com/privacy) (Codex)
- [Google's Privacy Policy](https://policies.google.com/privacy) (Gemini)

---

## 4. The giljo.ai Website

The giljo.ai website is a static informational site. When you visit it:

- **Server logs**: Our hosting provider may log your IP address, browser type, and pages visited as part of standard web server operation
- **No analytics**: We do not use Google Analytics, Mixpanel, or similar tracking services
- **No cookies**: The website does not set cookies
- **No accounts**: The website does not require or offer user account creation

**Contact forms and email**: If you contact us at info@giljo.ai, we retain your email and message content for the purpose of responding to your inquiry. We do not add you to marketing lists without your explicit consent.

---

## 5. SaaS Edition (Future)

When the SaaS Edition launches, it will involve GiljoAI-hosted infrastructure. At that time, this Privacy Policy will be updated to cover:

- What data the SaaS Edition stores on GiljoAI-operated servers
- How that data is protected, encrypted, and isolated between tenants
- Data retention and deletion policies
- Your rights regarding your data
- Sub-processor disclosures

The SaaS Edition will have its own, more detailed privacy policy appropriate to a hosted service. This current policy covers only the Community Edition and the giljo.ai website.

---

## 6. Children's Privacy

GiljoAI MCP is a developer tool not intended for use by children under 13. We do not knowingly collect information from children.

---

## 7. Changes to This Policy

We may update this Privacy Policy from time to time. Changes will be posted on this page with an updated "Last Updated" date. For material changes, we will make reasonable efforts to provide notice through the GitHub repository or website.

---

## 8. Your Rights

Since GiljoAI MCP Community Edition stores all data locally on your machine, you have complete control over your data at all times. You can:

- **Access** any data by querying your PostgreSQL database directly
- **Modify** any data through the application or database
- **Delete** any data by removing records, projects, or products (soft delete with 10-day recovery, then permanent purge)
- **Export** your data at any time from your own database
- **Uninstall** the software and delete the database entirely

No request to GiljoAI is needed to exercise any of these rights. Your data is yours.

---

## 9. Contact

Questions about this Privacy Policy:

- **Email**: info@giljo.ai
- **Address**: GiljoAI LLC, Nashua, NH 03063, United States

---

## Summary Table

| Question | Answer |
|----------|--------|
| Does GiljoAI collect my data? | No. Community Edition is fully local. |
| Does the software phone home? | No. Zero telemetry, zero analytics. |
| Where is my data stored? | In your local PostgreSQL database, on your machine. |
| Can GiljoAI access my data? | No. We have no connection to your installation. |
| What about my AI coding agent? | Your AI coding agent's data practices are governed by that agent's provider. |
| Does the website track me? | No cookies, no analytics. Standard server logs only. |
| What about SaaS Edition? | Will have its own privacy policy when launched. |
