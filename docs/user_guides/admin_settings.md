# Admin Settings

Admin Settings provides system administrators with centralized control over workspace configuration, team management, and system-wide settings for the GiljoAI MCP server.

## Access

- **Who**: Administrator users only (Admin or Owner role required)
- **Where**: Click your avatar in the top-right corner → Admin Settings
- **Route**: `/system-settings`

If you don't see the Admin Settings option, you may not have administrative privileges. Contact your workspace owner to request access.

---

## Identity Tab

The Identity tab consolidates workspace and team member management in one place. This is the first tab you'll see when opening Admin Settings.

### Workspace Details

Configure your workspace's identity:

| Field | Description | Editable |
|-------|-------------|----------|
| **Workspace Name** | The display name for your organization (e.g., "Acme Corp Engineering") | Owner/Admin only |
| **Slug** | URL-friendly identifier (e.g., "acme-corp-eng") | No (set at creation) |

**To update workspace name:**
1. Edit the "Workspace Name" field
2. Click **Save Changes**
3. Click **Reset** to discard changes

### Members

View and manage team members with role-based access control.

#### Available Roles

| Role | Permissions |
|------|-------------|
| **Owner** | Full control including organization deletion and ownership transfer |
| **Admin** | Manage members, change settings, configure integrations |
| **Member** | Standard workspace access to products and projects |
| **Viewer** | Read-only access to workspace content |

#### Member Management Actions

| Action | Required Role | Description |
|--------|---------------|-------------|
| **View members** | Any role | See list of all workspace members with their roles |
| **Invite member** | Owner or Admin | Send invitation to new team member via email |
| **Change role** | Owner or Admin | Promote or demote existing members |
| **Remove member** | Owner or Admin | Remove user from workspace (doesn't delete account) |
| **Transfer ownership** | Owner only | Transfer workspace ownership to another member |

**To invite a new member:**
1. Click **Invite** button in the Members card
2. Enter the user's email address
3. Select their initial role
4. Click **Send Invitation**

**To change a member's role:**
1. Locate the member in the list
2. Click the role dropdown next to their name
3. Select the new role
4. Confirm the change

**To remove a member:**
1. Locate the member in the list
2. Click the remove icon (trash can)
3. Confirm the removal

**To transfer ownership:**
1. You must be the current owner
2. Locate the member who will become the new owner
3. Click the transfer ownership icon
4. Confirm the transfer (this action is irreversible)

---

## Network Tab

Configure network settings for external access and CORS policies.

### External Host

The hostname or IP address that clients use to access the GiljoAI MCP server.

- **Configured during**: Installation
- **Default**: `localhost`
- **Use case**: Change to your server's public IP or domain name for network access

### Ports

| Port | Service | Default |
|------|---------|---------|
| **API Port** | Backend API server | 7272 |
| **Frontend Port** | Vue dashboard | 7274 |

Ports are configured during installation and displayed here for reference.

### CORS Origins

Specify which domains are allowed to make cross-origin requests to the API.

**Common patterns:**
- `http://localhost:7274` (local development)
- `https://your-domain.com` (production)
- `https://subdomain.example.com` (subdomains)

**To add a CORS origin:**
1. Enter the full URL (including protocol)
2. Click **Add**
3. Click **Save** to persist changes

---

## Database Tab

View PostgreSQL database configuration (read-only).

### Configuration Display

Shows your current database connection settings:
- Host
- Port
- Database name
- Username

These settings are configured during installation and cannot be modified through the UI for security reasons.

### Actions

| Action | Description |
|--------|-------------|
| **Test Connection** | Verify database connectivity |
| **Reload from Config** | Refresh displayed settings from `config.yaml` |

**Note**: Database settings are stored in `config.yaml` and require manual file editing to change.

---

## Integrations Tab

Manage API keys for AI service integrations.

### Supported Services

| Service | Provider | Purpose |
|---------|----------|---------|
| **Claude** | Anthropic | Claude AI models (via API) |
| **Codex** | OpenAI | GPT models and code generation |
| **Gemini** | Google | Google AI models |

### Configuration

Each integration requires:
- **API Key**: Your service-specific API key
- **Organization ID** (optional): For multi-org accounts

**To configure an integration:**
1. Click the service card (Claude, Codex, or Gemini)
2. Enter your API key
3. (Optional) Enter organization ID
4. Click **Save**
5. The system will validate the key

**Security notes:**
- API keys are encrypted at rest
- Keys are never displayed in full after saving
- Only administrators can view or modify keys

---

## Security Tab

Configure security policies and access controls.

### Cookie Domain Whitelist

Specify which domains can set authentication cookies.

**Purpose**: Prevent unauthorized domains from accessing user sessions.

**Format**: Domain names without protocol
- ✅ Correct: `example.com`, `app.example.com`
- ❌ Incorrect: `https://example.com`, `example.com/path`

**To add a domain:**
1. Enter the domain name in the text field
2. Click **Add**
3. The domain is saved immediately

**To remove a domain:**
1. Click the remove icon (trash can) next to the domain
2. Confirm the removal

**Common domains to whitelist:**
- Your production domain
- Staging/testing domains
- Local development domains (if needed)

---

## Prompts Tab

Configure the orchestrator system prompt used when launching orchestrator agents.

### System Prompt

The system prompt defines the orchestrator's behavior, capabilities, and guidelines.

**What it controls:**
- Agent spawning logic
- Task delegation strategies
- Communication patterns
- Error handling behavior

**Editing the prompt:**
1. Modify the prompt text in the editor
2. Click **Save** to persist changes
3. New orchestrators will use the updated prompt
4. Existing orchestrators continue using their original prompt

**Best practices:**
- Test prompt changes with non-critical projects first
- Document major changes for your team
- Keep a backup of working prompts
- Avoid removing critical instructions (agent discovery, error handling)

**Default behavior**: The system ships with a production-tested prompt. Only modify if you have specific customization needs.

---

## Troubleshooting

### "Access Denied" when opening Admin Settings

**Cause**: You don't have administrative privileges.

**Solution**: Contact your workspace owner to grant you Admin or Owner role.

### Network settings won't save

**Cause**: Backend configuration file may be read-only.

**Solution**: Check file permissions on `config.yaml` and ensure the API server has write access.

### Database connection test fails

**Possible causes:**
- PostgreSQL service not running
- Incorrect credentials in `config.yaml`
- Network firewall blocking connection
- Database server not accepting connections

**Solution**:
1. Verify PostgreSQL is running: `systemctl status postgresql` (Linux) or check Services (Windows)
2. Test connection manually: `psql -U postgres -d giljo_mcp`
3. Review `config.yaml` for typos in connection settings

### API key validation fails

**Possible causes:**
- Invalid or expired API key
- Network connectivity issues
- Service provider outage
- Incorrect organization ID

**Solution**:
1. Verify API key is correct (copy from provider dashboard)
2. Check provider's service status page
3. Try a test API call outside of GiljoAI
4. Contact provider support if key should be valid

---

## Related Documentation

- [Installation Guide](INSTALLATION_FLOW_PROCESS.md) - Initial setup and configuration
- [User Management](user_management.md) - Detailed user and role management
- [Network Configuration](../architecture/network_configuration.md) - Advanced networking setup
- [Security Best Practices](../security/best_practices.md) - Securing your installation

---

## Notes

- All changes in Admin Settings are system-wide and affect all workspace members
- Some settings require server restart to take effect (check specific tab documentation)
- Admin Settings is only accessible to users with Admin or Owner role
- Regular members and viewers will not see the Admin Settings menu option
