# Agent Template Management - User Guide

**Version**: 3.0.0
**Last Updated**: 2025-10-24
**Audience**: GiljoAI MCP End Users, Project Managers, Team Leads

---

## Table of Contents

1. [Introduction](#introduction)
2. [Accessing Template Management](#accessing-template-management)
3. [Understanding Agent Templates](#understanding-agent-templates)
4. [Template Customization Workflows](#template-customization-workflows)
5. [Best Practices](#best-practices)
6. [Troubleshooting](#troubleshooting)
7. [FAQ](#faq)

---

## Introduction

### What Are Agent Templates?

Agent templates are the "DNA" of AI agents in GiljoAI MCP. They define:

- **Identity**: Who the agent is (role, specialization)
- **Behavior**: How the agent approaches tasks (rules, constraints)
- **Success Criteria**: What constitutes successful task completion
- **Tool Preferences**: Which AI tools the agent prefers (Claude, Codex, Gemini)

Think of templates as instruction manuals that guide agent behavior. By customizing templates, you can:
- Tailor agents to your team's coding standards
- Enforce specific workflows or methodologies
- Adapt agents to your tech stack and architecture
- Improve agent performance for your specific use cases

### Why Customize Templates?

**Default templates** work well for general software development, but customization provides:

- **Higher Quality**: Agents produce code aligned with your standards
- **Better Consistency**: All agents follow your team's conventions
- **Faster Results**: Agents know your preferred tools and patterns
- **Reduced Rework**: Fewer iterations needed to meet requirements

**Example**: If your team uses TypeScript exclusively, you can customize the Implementer template to always generate TypeScript code and never suggest JavaScript.

### Template Hierarchy

Templates are resolved in priority order:

```
1. Product-Specific Template (highest priority)
   ↓ (if not found)
2. Tenant-Specific Template (your customizations)
   ↓ (if not found)
3. System Default Template (GiljoAI defaults)
   ↓ (always available)
4. Legacy Fallback (hard-coded templates)
```

**What This Means**:
- Create a tenant-level template → Applies to all your projects
- Create a product-specific template → Applies only to that project
- Reset to default → Copies system template to your tenant
- Delete your template → Falls back to system default

---

## Accessing Template Management

### Step 1: Log In to Dashboard

1. Open your browser and navigate to the GiljoAI MCP dashboard:
   - **Local**: `http://localhost:7272`
   - **Network**: `http://<server-ip>:7272` (e.g., `http://192.168.1.100:7272`)

2. Log in with your credentials:
   - Enter username and password
   - Click "Login"

### Step 2: Navigate to Templates

1. From the main dashboard, click on the **"Templates"** tab in the left sidebar
2. The Template Manager component will load, showing all available templates

**What You'll See**:
- List of 6 default agent templates (or your customized versions)
- Search bar for filtering templates
- Action buttons: Create, Edit, Delete, Reset
- Template details: name, role, usage count, last updated

---

## Understanding Agent Templates

### The Six Agent Roles

GiljoAI MCP uses six specialized agent roles:

#### 1. Orchestrator
**Purpose**: Project coordination and team management

**Responsibilities**:
- Read and understand project vision documents
- Break down projects into missions
- Delegate tasks to specialized agents
- Coordinate agent collaboration
- Create project documentation

**When to Customize**:
- Your team uses specific project management methodologies (Scrum, Kanban, etc.)
- You have custom documentation requirements
- You want to enforce specific delegation rules

#### 2. Analyzer
**Purpose**: Requirements analysis and architecture design

**Responsibilities**:
- Analyze requirements and specifications
- Design system architecture
- Identify risks and dependencies
- Document technical decisions
- Create specifications for implementers

**When to Customize**:
- Your team follows specific architecture patterns (microservices, monolith, etc.)
- You have standardized design documentation formats
- You want to enforce specific analysis methodologies

#### 3. Implementer
**Purpose**: Code implementation and feature development

**Responsibilities**:
- Write production-quality code
- Follow project specifications exactly
- Use symbolic operations for precise edits
- Test changes incrementally
- Maintain code quality standards

**When to Customize**:
- Your team uses specific coding standards or style guides
- You have preferred libraries or frameworks
- You want to enforce specific design patterns
- You need language-specific optimizations (TypeScript, Python, etc.)

#### 4. Tester
**Purpose**: Test creation and quality assurance

**Responsibilities**:
- Create comprehensive test coverage
- Validate against requirements
- Document defects clearly
- Ensure tests follow project standards
- Verify edge cases and error handling

**When to Customize**:
- Your team uses specific testing frameworks (Jest, Pytest, etc.)
- You have coverage requirements (e.g., >80%)
- You want specific test naming conventions
- You need integration or E2E test patterns

#### 5. Reviewer
**Purpose**: Code review and security validation

**Responsibilities**:
- Review code objectively and constructively
- Check security best practices
- Validate architectural compliance
- Provide actionable feedback
- Ensure quality standards

**When to Customize**:
- Your team has specific security requirements
- You want to enforce code review checklists
- You have compliance requirements (GDPR, HIPAA, etc.)
- You need to check for specific anti-patterns

#### 6. Documenter
**Purpose**: Documentation creation and maintenance

**Responsibilities**:
- Create clear, comprehensive documentation
- Provide usage examples and guides
- Update all relevant artifacts
- Focus on implemented features only
- Follow documentation style guides

**When to Customize**:
- Your team uses specific documentation formats (Markdown, AsciiDoc, etc.)
- You have documentation standards (API docs, README templates)
- You need to generate specific artifacts (OpenAPI specs, etc.)
- You want to enforce documentation coverage

### Template Anatomy

Each template contains the following sections:

```markdown
# Agent Identity
Role: {role}
Specialization: {specialization}
Preferred Tool: {tool}

# Behavioral Rules
1. [Rule 1 - What the agent MUST do]
2. [Rule 2 - What the agent MUST NOT do]
3. [Rule 3 - How the agent should approach tasks]
...

# Success Criteria
1. [Criterion 1 - Measurable outcome]
2. [Criterion 2 - Quality standard]
3. [Criterion 3 - Validation requirement]
...

# Variables
{project_name} - Name of the project
{mission} - Specific mission assigned to agent
{custom_augmentation} - Additional context or requirements
...

# Mission Template
[The actual prompt template used to generate agent missions]
```

**Key Concepts**:

- **Variables**: Placeholders like `{project_name}` that get replaced with actual values
- **Behavioral Rules**: Hard constraints the agent must follow
- **Success Criteria**: How the agent knows it's done a good job
- **Mission Template**: The actual prompt sent to the AI model

---

## Template Customization Workflows

### Workflow 1: View and Explore Templates

**Use Case**: You want to understand what templates are available and how they're configured.

**Steps**:

1. Navigate to the Templates tab
2. Browse the list of templates in the data table
3. Use the search bar to filter by name or role (e.g., type "implementer")
4. Click on a template row to see details
5. Review template content, variables, and metadata

**What You'll See**:
- Template name and role
- Last updated timestamp
- Usage count (how many times this template has been used)
- Content preview
- Behavioral rules and success criteria

### Workflow 2: Customize an Existing Template

**Use Case**: You want to modify a default template to match your team's standards.

**Steps**:

1. **Open Template for Editing**:
   - Find the template you want to customize (e.g., "Implementer")
   - Click the "Edit" button (pencil icon)
   - Edit dialog opens with Monaco editor

2. **Review Current Content**:
   - Read through the template content
   - Identify sections you want to modify
   - Note the variables being used (e.g., `{project_name}`, `{mission}`)

3. **Make Your Changes**:
   - Edit behavioral rules to match your workflow
   - Add or modify success criteria
   - Update mission template with your standards
   - **Preserve variables**: Don't remove `{variable}` placeholders (agents need these)

4. **Validate Your Changes**:
   - Click the "Preview" tab to see how variables will be substituted
   - Enter sample values for variables (e.g., `project_name = "MyApp"`)
   - Review the rendered template output
   - Check for syntax errors or missing placeholders

5. **Compare with System Default** (Optional):
   - Click the "Show Diff" button
   - Review what you've changed compared to the system default
   - Verify changes are intentional
   - See summary statistics (lines added, removed, changed)

6. **Save Template**:
   - Click "Save" to commit your changes
   - Template is automatically versioned
   - Previous version is archived (you can restore later)
   - All users in your tenant will see the updated template immediately (via WebSocket)

**Example Customization** (Implementer Template):

**Before**:
```markdown
# Behavioral Rules
1. Write clean, maintainable code
2. Follow project specifications exactly
3. Use Serena MCP symbolic operations for edits
4. Test changes incrementally
```

**After** (for TypeScript team):
```markdown
# Behavioral Rules
1. Write clean, maintainable TypeScript code (strict mode enabled)
2. Follow project specifications exactly
3. Use Serena MCP symbolic operations for edits
4. Test changes incrementally with Jest
5. Use functional programming patterns (avoid classes unless necessary)
6. All functions must have JSDoc comments
7. Use eslint and prettier for code formatting
```

### Workflow 3: Reset Template to System Default

**Use Case**: You've made changes that broke something, or you want to start fresh with the default template.

**Steps**:

1. **Locate Template**:
   - Find the template you want to reset (e.g., "Implementer")
   - Click the "Actions" menu (three dots)

2. **Initiate Reset**:
   - Select "Reset to Default" from the menu
   - Confirmation dialog appears

3. **Review Changes**:
   - Dialog shows what will change:
     - Current content (your customizations)
     - System default content
     - Diff highlighting differences
   - Review to ensure you understand what you're losing

4. **Confirm Reset**:
   - Click "Confirm Reset" to proceed
   - Your customizations are archived (not lost!)
   - Template is replaced with system default
   - Version number increments
   - All users in your tenant see the reset immediately

5. **Verify**:
   - Template list refreshes automatically
   - Check that template content matches system default
   - If needed, restore your previous version from history

**When to Reset**:
- Template stopped working after customizations
- You want to start fresh with defaults
- System defaults have been updated and you want the new version
- You're troubleshooting agent behavior issues

### Workflow 4: Create a Product-Specific Template

**Use Case**: You want a custom template for one specific project, without affecting other projects.

**Steps**:

1. **Initiate Creation**:
   - Click "Create Template" button (+ icon)
   - Template creation dialog opens

2. **Configure Template**:
   - **Name**: Descriptive name (e.g., "Implementer - MyApp TypeScript")
   - **Category**: Select "role"
   - **Role**: Select the agent role (e.g., "implementer")
   - **Product**: Select the specific product/project
   - **Preferred Tool**: Choose AI tool (Claude, Codex, Gemini)

3. **Write Template Content**:
   - Copy system default as starting point (optional)
   - Add product-specific instructions
   - Include product-specific variables (e.g., `{api_key}`, `{database_url}`)
   - Define behavioral rules specific to this product
   - Set success criteria for this project

4. **Add Metadata**:
   - **Description**: Explain what this template is for
   - **Tags**: Add tags for searchability (e.g., "typescript", "backend", "api")
   - **Behavioral Rules**: List specific rules (added to template content)
   - **Success Criteria**: Define what "done" means for this project

5. **Preview and Validate**:
   - Click "Preview" to test variable substitution
   - Enter sample values for all variables
   - Verify rendered output makes sense

6. **Save Template**:
   - Click "Create" to save
   - Template is immediately available for the selected product
   - Template takes priority over tenant-level and system templates

**Product-Specific Template Priority**:

When an agent is spawned for a project with a product-specific template:
1. System checks for product-specific template → **FOUND** → Use it ✅
2. (Skips tenant-level template)
3. (Skips system default template)

When an agent is spawned for a project without a product-specific template:
1. System checks for product-specific template → Not found
2. System checks for tenant-level template → **FOUND** → Use it ✅
3. (Skips system default)

### Workflow 5: View Template History and Restore

**Use Case**: You want to see what changed in a template over time, or restore a previous version.

**Steps**:

1. **Open Template History**:
   - Find the template (e.g., "Implementer")
   - Click "Actions" → "View History"
   - History dialog opens with timeline

2. **Browse Version History**:
   - See all previous versions in chronological order
   - Each version shows:
     - Version number (e.g., v3.2.1)
     - Timestamp (when change was made)
     - Changed by (user who made the change)
     - Reason (edit, reset, delete)
     - Content preview

3. **Compare Versions**:
   - Select two versions to compare
   - Click "Show Diff"
   - Side-by-side diff view shows changes
   - Added lines highlighted in green
   - Removed lines highlighted in red
   - Changed lines highlighted in yellow

4. **Restore Previous Version**:
   - Find the version you want to restore
   - Click "Restore This Version"
   - Confirmation dialog appears
   - Click "Confirm Restore"
   - Template content is replaced with the selected version
   - New version is created (doesn't delete current version)
   - All users see the restored template immediately

**Version Numbering**:
- Major version: Reset to default (e.g., v3.0.0 → v4.0.0)
- Minor version: Edit template (e.g., v3.1.0 → v3.2.0)
- Patch version: Small fixes (e.g., v3.1.1 → v3.1.2)

### Workflow 6: Delete a Template

**Use Case**: You no longer need a custom template and want to fall back to the default.

**Steps**:

1. **Locate Template**:
   - Find the template you want to delete
   - Click "Actions" → "Delete"

2. **Confirm Deletion**:
   - Confirmation dialog explains what happens:
     - Template is soft-deleted (not permanently removed)
     - Template is marked as `is_active = false`
     - System will fall back to the next priority template
     - You can restore the template later from history
   - Click "Confirm Delete"

3. **Verify Fallback**:
   - Template list refreshes (deleted template hidden by default)
   - System now uses the fallback template (system default or tenant-level)
   - Spawn an agent to verify it uses the correct template

**Important Notes**:
- Templates are **soft-deleted** (not permanently removed)
- You can restore deleted templates from history
- Deleting a product-specific template falls back to tenant-level template
- Deleting a tenant-level template falls back to system default
- You **cannot** delete system default templates (read-only)

---

## Best Practices

### 1. Start Small, Iterate

**Don't** try to perfect the template on the first try.

**Do**:
1. Make small, incremental changes
2. Test each change with a real agent task
3. Observe agent behavior and output quality
4. Refine based on results
5. Repeat until satisfied

**Example Iteration**:
- **Iteration 1**: Add "Use TypeScript" to behavioral rules → Test → Works!
- **Iteration 2**: Add "Use functional patterns" → Test → Too strict, agents struggle
- **Iteration 3**: Change to "Prefer functional patterns when appropriate" → Test → Perfect!

### 2. Preserve Variables

**Critical**: Always preserve variable placeholders (e.g., `{project_name}`, `{mission}`).

**Why**: Agents rely on these variables to receive context about the task. Removing them breaks mission generation.

**Safe**:
```markdown
You are working on the {project_name} project.
Your mission: {mission}
```

**Unsafe**:
```markdown
You are working on the MyApp project.  ❌ (removed {project_name})
Your mission: Implement features.         ❌ (removed {mission})
```

**Adding New Variables**:
- Use `{variable_name}` syntax
- Document what the variable means
- Ensure the variable is provided when agents are spawned

### 3. Test Before Deploying

**Always** test template changes with a real agent before relying on them for production work.

**Testing Workflow**:
1. Edit template in staging/test environment (or use product-specific template for a test project)
2. Spawn an agent with a simple task
3. Observe agent behavior (does it follow new rules?)
4. Check output quality (is it better/worse?)
5. If good → Deploy to production
6. If bad → Iterate or reset to default

### 4. Document Your Changes

**Why**: Future you (or your teammates) will thank you.

**How**:
- Use the **Description** field to explain why you customized the template
- Add comments in the template content (use Markdown comments: `<!-- comment -->`)
- Tag templates with relevant keywords (e.g., "typescript", "strict-mode", "2024-update")

**Example**:
```markdown
<!--
  Customization: 2024-10-24 by Alice
  Reason: Enforce TypeScript strict mode for better type safety
  Changes: Added strict mode rules, removed JavaScript suggestions
-->

# Behavioral Rules
1. Always use TypeScript with strict mode enabled
2. Never suggest JavaScript alternatives
...
```

### 5. Use Product-Specific Templates Sparingly

**When to Use Tenant-Level Templates** (most common):
- Standards apply to all your projects
- You want consistency across all work
- You manage a single product or small portfolio

**When to Use Product-Specific Templates** (special cases):
- One project has unique requirements (e.g., uses a different language)
- One project has stricter security requirements
- One project is experimental and needs different rules
- You manage many diverse projects with different tech stacks

**Example**:
- **Tenant-level Implementer**: "Use TypeScript, functional patterns, Jest testing"
- **Product-specific Implementer for Legacy Project**: "Use JavaScript ES5, no TypeScript, Mocha testing"

### 6. Review System Default Updates

**Periodically** (every few months), check if system defaults have been updated:

1. View your customized template
2. Click "Show Diff" → Select "Compare with System Default"
3. Review what's changed in the system default
4. Decide if you want to incorporate those changes
5. If yes → Manually merge improvements into your template
6. If no → Keep your customizations as-is

**Why**: GiljoAI improves default templates based on user feedback. You might benefit from these improvements.

### 7. Monitor Template Usage

**Track which templates are used most**:

1. Go to Templates tab
2. Sort by "Usage Count" column (descending)
3. Identify most-used templates
4. Focus optimization efforts on high-usage templates

**Why**: Optimizing templates that are rarely used has minimal impact. Focus on high-traffic templates first.

### 8. Backup Before Major Changes

**Before** making significant template changes:

1. View current template content
2. Copy content to a text file or note (manual backup)
3. Make your changes
4. Test thoroughly
5. If it breaks → Restore from backup or history

**Why**: While templates have version history, having a manual backup provides extra safety.

---

## Troubleshooting

### Issue: Agent Behavior Didn't Change After Template Update

**Symptoms**: You edited a template, but agents still behave the old way.

**Possible Causes**:
1. **Cache not invalidated**: Cache still serving old template
2. **Wrong template**: Agent is using a different template (product-specific vs tenant-level)
3. **Template not saved**: Changes weren't committed

**Solutions**:

**Check Template Save**:
1. Navigate to Templates tab
2. Find the template you edited
3. Check "Last Updated" timestamp → Should match your edit time
4. If not → Re-edit and click "Save"

**Verify Template Resolution**:
1. Spawn an agent for a test task
2. Check agent mission output (visible in logs or dashboard)
3. Verify mission content matches your template
4. If not → Check template hierarchy (product-specific > tenant > system)

**Invalidate Cache** (if needed):
1. Restart GiljoAI MCP server (clears all caches)
2. OR: Wait 1 hour (Redis cache TTL expires)
3. OR: Contact admin to manually invalidate cache

**Check Behavioral Rules Format**:
- Ensure rules are clear and actionable
- Avoid vague language (e.g., "sometimes" → "always" or "never")
- Test with a simple, measurable task

### Issue: Template Preview Shows Errors

**Symptoms**: When you click "Preview", you see errors or warnings.

**Possible Causes**:
1. **Missing variables**: You removed a required variable
2. **Invalid syntax**: Malformed `{variable}` placeholders
3. **Size limit exceeded**: Template > 100KB

**Solutions**:

**Check Variable Syntax**:
- Variables must be `{variable_name}` (curly braces, alphanumeric + underscore)
- Invalid: `${variable}`, `<variable>`, `[variable]`
- Valid: `{project_name}`, `{mission}`, `{custom_var_123}`

**Verify Required Variables**:
- All default variables must be preserved:
  - `{project_name}` (or `{product_name}`)
  - `{mission}` (or `{custom_mission}`)
  - Agent-specific variables (see template documentation)

**Check Template Size**:
1. View template content
2. If very long → Click "Check Size" button
3. If > 100KB → Reduce content:
   - Remove redundant examples
   - Shorten behavioral rules
   - Link to external documentation instead of including full text

**Test with Sample Variables**:
1. In Preview tab, enter sample values for all variables
2. Click "Render"
3. Review output for placeholders that weren't substituted
4. Add missing variables to template or fix syntax

### Issue: Reset to Default Doesn't Work

**Symptoms**: You click "Reset to Default", but template content doesn't change.

**Possible Causes**:
1. **No system default exists**: Template doesn't have a system default to reset to
2. **Permission issue**: You don't have permission to modify this template
3. **System template**: You're trying to reset a system template (not allowed)

**Solutions**:

**Check Template Type**:
1. View template details
2. Check "Tenant Key" field:
   - If `tenant_key = "system"` → This is a system template (cannot reset)
   - If `tenant_key = <your_tenant>` → This is your tenant template (can reset)

**Verify System Default Exists**:
1. Click "Show Diff" → "Compare with System Default"
2. If error: "No system default found" → System default doesn't exist for this template
3. Solution: Contact admin to seed system defaults, or manually edit template

**Check Permissions**:
1. Ensure you're logged in with correct account
2. Check that you're not trying to modify another tenant's template
3. If 403 Forbidden error → Contact admin for permissions

### Issue: WebSocket Updates Not Showing

**Symptoms**: You make changes, but other users don't see updates immediately.

**Possible Causes**:
1. **WebSocket connection lost**: Client disconnected from WebSocket
2. **Browser tab inactive**: Browser paused WebSocket for inactive tab
3. **Firewall blocking WebSocket**: Corporate firewall blocks WS traffic

**Solutions**:

**Check WebSocket Connection**:
1. Open browser DevTools (F12)
2. Go to "Network" tab
3. Filter by "WS" (WebSocket)
4. Look for `ws://localhost:7272/ws` or similar
5. Status should be "101 Switching Protocols" (connected)
6. If "Failed" or "Closed" → WebSocket not working

**Refresh Browser**:
1. Press F5 to refresh the page
2. WebSocket reconnects automatically
3. Template list should refresh with latest data

**Check Firewall** (network deployment):
1. Ensure port 7272 (or your configured port) allows WebSocket connections
2. Test from local machine first (should always work)
3. If local works but network doesn't → Firewall issue
4. Contact IT to allow WebSocket traffic on port 7272

**Manual Refresh**:
- If WebSocket doesn't work, click the "Refresh" button manually
- Templates will reload via REST API (no WebSocket needed)

### Issue: Template Size Limit Exceeded

**Symptoms**: Error when saving: "Template content exceeds maximum size of 100KB"

**Possible Causes**:
1. **Very long template**: Template content is genuinely > 100KB
2. **Large examples included**: Template includes many code examples
3. **Copied external content**: Pasted large documentation into template

**Solutions**:

**Check Template Size**:
1. Copy template content to text editor
2. Check file size (should be < 100KB = 102,400 bytes)
3. If close to limit → Look for areas to reduce

**Reduce Template Size**:
1. **Remove redundant examples**: Keep only 1-2 most important examples
2. **Link to external docs**: Instead of including full docs, link to them:
   ```markdown
   For TypeScript best practices, see: https://your-docs.com/typescript
   ```
3. **Shorten behavioral rules**: Combine similar rules, remove verbose explanations
4. **Use concise language**: Replace long sentences with bullet points

**Split into Multiple Templates**:
- If template is for multiple agent roles → Create separate templates per role
- If template has product-specific + tenant-level rules → Split into two templates

**Contact Admin**:
- If 100KB limit is genuinely too small for your use case
- Admin can increase limit in configuration (not recommended, affects performance)

---

## FAQ

### Q1: Can I customize templates for individual agents, or just agent roles?

**A**: Templates are defined per **agent role** (orchestrator, implementer, etc.), not per individual agent instance.

When you customize the "Implementer" template, all Implementer agents spawned for your tenant will use the customized template.

**Workaround for agent-specific instructions**:
- Use the `{custom_augmentation}` variable in templates
- When spawning an agent, provide agent-specific instructions via augmentation
- Agent receives both template + augmentation

### Q2: What happens if I delete all my templates?

**A**: The system will gracefully fall back to system defaults and legacy hard-coded templates.

**Fallback Order**:
1. Your deleted tenant-level template → Falls back to system default
2. System default → Falls back to legacy hard-coded template
3. Legacy hard-coded template → Always exists, cannot be deleted

**You cannot break the system by deleting templates.** There's always a fallback.

### Q3: Can I see who made changes to a template?

**A**: Yes, via the version history.

**Steps**:
1. Open template → Actions → View History
2. Each version shows:
   - **Changed By**: Username of person who made the change
   - **Timestamp**: When the change was made
   - **Reason**: Why the change was made (edit, reset, delete)

**Audit Trail**: All changes are logged and cannot be deleted (referential integrity).

### Q4: How do I share templates between tenants?

**A**: Currently, templates are isolated per tenant (multi-tenant security).

**Workarounds**:
1. **Export/Import** (manual):
   - Copy template content from Tenant A
   - Create new template in Tenant B with same content
2. **System Defaults** (admin only):
   - Ask admin to create a system default template
   - All tenants can use it (read-only, can copy to customize)

**Future Feature** (not yet implemented):
- Template marketplace for sharing community templates
- Export/import functionality in UI

### Q5: What's the difference between "Reset to Default" and "Delete"?

**Reset to Default**:
- Replaces your customizations with the system default template
- Your previous version is archived (can restore later)
- Template remains active
- Version number increments

**Delete**:
- Marks template as inactive (`is_active = false`)
- Template hidden from UI (unless you show inactive templates)
- System falls back to next priority template (system default or legacy)
- Can be restored from history

**Use Reset** when you want to start fresh with system defaults.
**Use Delete** when you no longer need the template at all.

### Q6: How often should I review and update my templates?

**Recommended Schedule**:

- **Monthly**: Review template usage stats, identify optimization opportunities
- **Quarterly**: Compare your templates with system defaults for improvements
- **After major project**: Update templates based on learnings from the project
- **When standards change**: Update immediately if your team adopts new coding standards

**Signs It's Time to Update**:
- Agents consistently violate a rule (rule is unclear or unrealistic)
- Output quality has degraded (template no longer matches current needs)
- System defaults have been updated (new improvements available)
- Team has adopted new tools or methodologies

### Q7: Can I use Markdown formatting in templates?

**A**: Yes, templates support full Markdown syntax.

**Supported Formatting**:
- Headers: `# H1`, `## H2`, `### H3`
- Bold: `**bold**`
- Italic: `*italic*`
- Lists: `- item` or `1. item`
- Code blocks: ` ```code``` `
- Links: `[text](url)`
- Blockquotes: `> quote`
- Comments: `<!-- comment -->`

**Best Practice**: Use Markdown to structure templates clearly (headers, lists, code examples).

### Q8: What's the "Preferred Tool" setting?

**A**: The `preferred_tool` field specifies which AI tool the agent should use.

**Options**:
- **claude** (default): Anthropic's Claude (Sonnet, Opus)
- **codex**: OpenAI's Codex (GPT-4 with code specialization)
- **gemini**: Google's Gemini Code Assist

**When to Change**:
- Your team has licenses for specific AI tools
- Certain tasks perform better on specific tools (e.g., Gemini for Google Cloud projects)
- You want to test different tools for quality comparison

**Note**: Tool availability depends on your GiljoAI MCP server configuration and licenses.

### Q9: Can I preview how a template will look before saving?

**A**: Yes, use the **Preview** tab in the template editor.

**How to Preview**:
1. Edit template → Click "Preview" tab
2. Enter sample values for all variables (e.g., `project_name = "TestApp"`)
3. Click "Render"
4. View fully rendered template with variables substituted

**What Preview Shows**:
- Final template content sent to AI agent
- All variables replaced with your sample values
- Markdown formatting rendered (if preview supports it)

**Use Preview** to test variable substitution and ensure template makes sense.

### Q10: What happens if my template has syntax errors?

**A**: The system will attempt to use the template, but agent behavior may be unpredictable.

**Prevention**:
1. **Use Preview** to test template before saving
2. **Validate variables**: Ensure all `{variables}` have matching closing braces
3. **Test with agent**: Spawn a test agent to verify behavior
4. **Check logs**: Review agent mission generation logs for errors

**Recovery**:
- If agents behave erratically → Review template for errors
- Use "Reset to Default" to restore working template
- Restore previous version from history

**Best Practice**: Always preview and test templates before relying on them for production work.

---

## Conclusion

Congratulations! You now know how to:
- ✅ Access and explore agent templates
- ✅ Customize templates to match your team's standards
- ✅ Reset templates to system defaults
- ✅ Create product-specific templates
- ✅ View version history and restore previous versions
- ✅ Troubleshoot common issues

### Next Steps

1. **Explore Default Templates**: Review the 6 default templates to understand their structure
2. **Make Your First Customization**: Start with a small change (e.g., add a behavioral rule)
3. **Test with a Real Agent**: Spawn an agent and verify the template change worked
4. **Iterate**: Refine based on results
5. **Share Learnings**: Document what works well for your team

### Additional Resources

- [Developer Guide](./DEVELOPER_GUIDE.md) - API details, architecture, advanced customization
- [Deployment Guide](./DEPLOYMENT_GUIDE.md) - Production deployment, monitoring, best practices
- [Implementation Summary](./IMPLEMENTATION_SUMMARY.md) - Technical overview, performance metrics
- [CLAUDE.md](../../CLAUDE.md) - Quick reference for GiljoAI MCP

### Support

If you encounter issues or have questions:
- Check the [Troubleshooting](#troubleshooting) section
- Review the [FAQ](#faq)
- Contact support: support@giljo.ai

---

**Document Version**: 1.0
**Last Updated**: 2025-10-24
**Feedback**: Please report errors or suggest improvements to support@giljo.ai
