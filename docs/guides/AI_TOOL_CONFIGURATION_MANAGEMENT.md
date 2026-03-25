# AI Coding Agent Configuration Management

**Document Version**: 10_13_2025  
**Status**: Single Source of Truth  
**Last Updated**: October 13, 2025

---

## Overview

GiljoAI MCP v3.0 implements **AI-agnostic integration** that supports multiple AI coding agents including Claude Code, CODEX CLI, and Gemini CLI. The system provides a **user-friendly configuration generator** that creates ready-to-use MCP configuration files for seamless integration across platforms.

### Quick MCP Commands (0069)

Use native CLI commands to register the GiljoAI MCP server over HTTP:

```bash
# Codex CLI (Bearer token)
export GILJO_API_KEY="<your_api_key>"
codex mcp add --url http://localhost:7272/mcp --bearer-token-env-var GILJO_API_KEY giljoai

# Gemini CLI (HTTP + header)
gemini mcp add -t http -H "X-API-Key: <your_api_key>" giljoai http://localhost:7272/mcp

# Verify
codex mcp list
gemini mcp list
```

Notes:
- Replace `http://localhost:7272` with your server URL.
- API key is generated per tenant; see Settings → API & Integrations.

### Token‑Efficient Downloads (0101)

Download ZIPs instead of writing large files via MCP to reduce tokens by ~97%:

```
GET /api/download/slash-commands.zip
GET /api/download/agent-templates.zip
GET /api/download/install-script.{sh|ps1}?type=slash-commands|agent-templates
```

- MCP tools `/gil_import_*` use these endpoints automatically when available.
- Integrations UI exposes one‑click download buttons for ZIPs and install scripts.

### Bearer Auth Support for Codex & Gemini (0092)

Where CLI supports it, you may use Bearer tokens instead of `X-API-Key` headers. Example requests:

```bash
# Using Bearer token
curl -H "Authorization: Bearer $GILJO_BEARER_TOKEN" \
  http://localhost:7272/api/download/slash-commands.zip -o slash-commands.zip

# Codex/Gemini CLI may accept header flags; otherwise use API key header:
curl -H "X-API-Key: $GILJO_API_KEY" \
  http://localhost:7272/api/download/agent-templates.zip -o agent-templates.zip
```

Notes:
- Bearer tokens are project/user scoped; API keys are tenant scoped.
- The server accepts either `Authorization: Bearer …` or `X-API-Key: …` depending on your deployment pattern.

### Key Features

- **Multi-AI Coding Agent Support**: Claude Code, CODEX, Gemini CLI
- **Configuration Generator API**: Automated MCP config creation
- **Cross-Platform Setup**: Windows, Linux, macOS compatibility
- **User-Friendly Interface**: Copy-paste and download workflows
- **Tenant-Specific Configs**: Multi-tenant configuration isolation
- **Template-Level Preferences**: AI coding agent selection per agent template

---

## Supported AI Coding Agents

### Claude Code CLI
**Status**: Primary integration  
**Capabilities**: Sub-agent spawning, real-time orchestration  
**Configuration**: Automatic MCP server setup

### CODEX CLI (OpenAI)
**Status**: Supported  
**Capabilities**: MCP over HTTP, native CLI registration  
**Configuration**: `codex mcp add --transport http ...` (see Quick MCP Commands)

### Gemini CLI (Google)
**Status**: Supported  
**Capabilities**: MCP over HTTP, native CLI registration  
**Configuration**: `gemini mcp add --transport http ...` (see Quick MCP Commands)

---

## Architecture Components

### 1. AI Coding Agent Configuration API

**Location**: `api/endpoints/ai_tools.py` (425 lines)

**Key Endpoints**:
```python
GET  /api/ai-tools/supported          # List available AI coding agents
GET  /api/ai-tools/config-generator/{tool}  # Generate tool-specific config
POST /api/ai-tools/validate-config   # Validate configuration syntax
```

**Configuration Generation**:
```python
@router.get("/config-generator/{tool}")
async def generate_ai_tool_config(
    tool: str,
    tenant_key: str = Depends(get_current_tenant),
    server_url: str = Query(None),
    deployment_mode: str = Query("localhost")
):
    """Generate AI coding agent-specific MCP configuration"""
    
    config_generator = AIToolConfigGenerator()
    config = config_generator.generate_config(
        tool=tool,
        tenant_key=tenant_key,
        server_url=server_url or f"http://localhost:7272",
        deployment_mode=deployment_mode
    )
    
    return {
        "tool": tool,
        "config_format": config["format"],
        "config_content": config["content"],
        "installation_guide": config["guide"],
        "download_filename": config["filename"]
    }
```

### 2. Frontend Configuration Interface

**Location**: `frontend/src/components/AIToolSetup.vue` (243 lines)

**Key Features**:
- Tool selection dropdown with logos
- Configuration preview with syntax highlighting
- One-click copy to clipboard
- Download configuration files
- Installation guide display

**Component Structure**:
```vue
<template>
  <v-dialog v-model="dialog" max-width="800px" persistent>
    <v-card>
      <v-card-title>
        🔗 Connect AI Tools
        <v-spacer></v-spacer>
        <v-btn icon @click="dialog = false">
          <v-icon>mdi-close</v-icon>
        </v-btn>
      </v-card-title>
      
      <v-card-text>
        <!-- Tool Selection -->
        <v-select
          v-model="selectedTool"
          :items="availableTools"
          label="Select AI Tool"
          item-title="name"
          item-value="key"
          @update:model-value="generateConfig"
        >
          <template v-slot:item="{ props, item }">
            <v-list-item v-bind="props">
              <template v-slot:prepend>
                <v-avatar :color="item.raw.color" size="24">
                  <v-icon :icon="item.raw.icon" size="16"></v-icon>
                </v-avatar>
              </template>
            </v-list-item>
          </template>
        </v-select>
        
        <!-- Configuration Preview -->
        <v-card v-if="generatedConfig" class="mt-4">
          <v-card-title class="text-h6">
            {{ generatedConfig.tool }} Configuration
          </v-card-title>
          
          <v-card-text>
            <v-code class="config-preview">
              {{ generatedConfig.config_content }}
            </v-code>
            
            <div class="mt-4 d-flex gap-2">
              <v-btn 
                color="primary" 
                @click="copyToClipboard"
                prepend-icon="mdi-content-copy"
              >
                Copy Config
              </v-btn>
              
              <v-btn 
                color="success" 
                @click="downloadConfig"
                prepend-icon="mdi-download"
              >
                Download File
              </v-btn>
            </div>
          </v-card-text>
        </v-card>
        
        <!-- Installation Guide -->
        <v-expansion-panels v-if="generatedConfig" class="mt-4">
          <v-expansion-panel>
            <v-expansion-panel-title>
              📚 Installation Guide
            </v-expansion-panel-title>
            <v-expansion-panel-text>
              <div v-html="generatedConfig.installation_guide"></div>
            </v-expansion-panel-text>
          </v-expansion-panel>
        </v-expansion-panels>
      </v-card-text>
    </v-card>
  </v-dialog>
</template>
```

### 3. Configuration Generator Backend

**Core Logic**:
```python
class AIToolConfigGenerator:
    """Generate AI coding agent-specific MCP configurations"""
    
    SUPPORTED_TOOLS = {
        "claude": {
            "name": "Claude Code CLI",
            "description": "Anthropic's Claude Code CLI with sub-agent support",
            "config_format": "json",
            "config_file": ".claude.json"
        },
        "codex": {
            "name": "CODEX CLI (OpenAI)",  
            "description": "OpenAI's CODEX CLI with manual orchestration",
            "config_format": "json",
            "config_file": ".codex.json"
        },
        "gemini": {
            "name": "Gemini CLI (Google)",
            "description": "Google's Gemini CLI with configuration templates", 
            "config_format": "yaml",
            "config_file": ".gemini.yml"
        }
    }
    
    def generate_config(self, tool: str, tenant_key: str, server_url: str, deployment_mode: str):
        """Generate tool-specific configuration"""
        
        if tool == "claude":
            return self._generate_claude_config(tenant_key, server_url)
        elif tool == "codex":  
            return self._generate_codex_config(tenant_key, server_url)
        elif tool == "gemini":
            return self._generate_gemini_config(tenant_key, server_url)
        else:
            raise ValueError(f"Unsupported tool: {tool}")
    
    def _generate_claude_config(self, tenant_key: str, server_url: str):
        """Generate Claude Code CLI configuration"""
        
        config = {
            "mcpServers": {
                "giljo-mcp": {
                    "command": "uvx",
                    "args": ["giljo-mcp-client"],
                    "env": {
                        "GILJO_SERVER_URL": server_url,
                        "GILJO_TENANT_KEY": tenant_key
                    }
                }
            }
        }
        
        return {
            "format": "json",
            "content": json.dumps(config, indent=2),
            "filename": f"claude_mcp_config_{tenant_key}.json",
            "guide": self._get_claude_installation_guide()
        }
```

---

## Configuration Generation

### Claude Code CLI Configuration

**Generated Config** (`.claude.json`):
```json
{
  "mcpServers": {
    "giljo-mcp": {
      "command": "uvx",
      "args": ["giljo-mcp-client"],
      "env": {
        "GILJO_SERVER_URL": "http://localhost:7272",
        "GILJO_TENANT_KEY": "default"
      }
    }
  }
}
```

**Installation Guide**:
```markdown
# Claude Code CLI Setup

1. **Install uvx** (if not already installed):
   ```bash
   pip install uvx
   ```

2. **Install GiljoAI MCP Client**:
   ```bash
   uvx install giljo-mcp-client
   ```

3. **Copy Configuration**:
   - Copy the generated JSON configuration
   - Save to `~/.claude.json` (create if doesn't exist)
   - Merge with existing configuration if needed

4. **Verify Setup**:
   - Restart Claude Code CLI
   - Check that "giljo-mcp" server appears in available tools
   - Test with: `/mcp list-servers`

5. **Test Connection**:
   ```
   /mcp giljo-mcp get_projects
   ```
```

### CODEX CLI Configuration

**Generated Config** (`.codex.json`):
```json
{
  "mcp_servers": {
    "giljo-mcp": {
      "server_url": "http://localhost:7272",
      "tenant_key": "default",
      "api_endpoints": {
        "projects": "/api/projects",
        "agents": "/api/agents", 
        "tasks": "/api/tasks",
        "messages": "/api/messages"
      },
      "authentication": {
        "type": "bearer_token",
        "token_endpoint": "/api/auth/login"
      }
    }
  }
}
```

**Installation Guide**:
```markdown
# CODEX CLI Setup

1. **Install CODEX CLI** (if not already installed):
   ```bash
   pip install codex-cli
   ```

2. **Configure MCP Integration**:
   - Copy the generated JSON configuration
   - Save to `~/.codex.json`
   - Update authentication token as needed

3. **Manual Orchestration Workflow**:
   - Use CODEX for agent-specific implementations
   - Coordinate through GiljoAI MCP dashboard
   - Copy orchestration instructions between tools

4. **Test Integration**:
   ```bash
   codex mcp test-connection giljo-mcp
   ```
```

### Gemini CLI Configuration

**Generated Config** (`.gemini.yml`):
```yaml
mcp_integrations:
  giljo_mcp:
    server_url: "http://localhost:7272"
    tenant_key: "default"
    protocol: "http"
    
    endpoints:
      projects: "/api/projects"
      agents: "/api/agents"
      orchestration: "/api/orchestration"
    
    authentication:
      type: "jwt"
      login_endpoint: "/api/auth/login"
    
    features:
      agent_spawning: false    # Manual orchestration only
      context_sharing: true
      template_access: true
```

**Installation Guide**:
```markdown
# Gemini CLI Setup

1. **Install Gemini CLI**:
   ```bash
   pip install google-gemini-cli
   ```

2. **Configure MCP Integration**:
   - Copy the generated YAML configuration  
   - Save to `~/.gemini.yml`
   - Adjust authentication settings as needed

3. **Integration Workflow**:
   - Use Gemini for specialized analysis and implementation
   - Coordinate manually through GiljoAI MCP interface
   - Share context through copy-paste workflows

4. **Verify Setup**:
   ```bash
   gemini config validate
   gemini mcp test giljo_mcp
   ```
```

---

## User Experience Workflow

### Step 1: Access AI Coding Agent Setup

**From Settings Page**:
```
Settings → API and Integrations → [Connect AI Coding Agents]
```

**From Dashboard Quick Actions**:
```
Dashboard → Quick Actions → [Setup AI Coding Agents]
```

### Step 2: Tool Selection

**Available Options**:
```
┌─────────────────────────────────────────┐
│ Select AI Coding Agent:  [Claude Code CLI ▼]   │
├─────────────────────────────────────────┤
│ 🤖 Claude Code CLI (Recommended)       │
│    Sub-agent spawning, real-time sync   │
│                                         │
│ 💻 CODEX CLI (OpenAI)                  │
│    Manual orchestration, API access     │
│                                         │
│ 🧠 Gemini CLI (Google)                 │
│    Experimental, configuration guide    │
└─────────────────────────────────────────┘
```

### Step 3: Configuration Generation

**Generated Display**:
```
┌─────────────────────────────────────────┐
│ Claude Code CLI Configuration           │
├─────────────────────────────────────────┤
│ {                                       │
│   "mcpServers": {                       │
│     "giljo-mcp": {                      │
│       "command": "uvx",                 │
│       "args": ["giljo-mcp-client"],     │
│       "env": {                          │
│         "GILJO_SERVER_URL": "http://... │
│         "GILJO_TENANT_KEY": "default"   │
│       }                                 │
│     }                                   │
│   }                                     │
│ }                                       │
├─────────────────────────────────────────┤
│ [📋 Copy Config] [📥 Download Guide]    │
└─────────────────────────────────────────┘
```

### Step 4: Installation Actions

**Copy to Clipboard**:
- One-click copy of complete configuration
- Automatic formatting for target tool
- Success notification with next steps

**Download Configuration File**:
- Platform-specific filename generation
- Proper file extensions (.json, .yml)
- Includes installation instructions

**Installation Guide**:
- Expandable step-by-step instructions
- Platform-specific commands (Windows/Linux/macOS)
- Verification and testing procedures

---

## Multi-Tenant Configuration

### Tenant-Specific Settings

Each tenant receives **isolated configurations**:

```json
{
  "mcpServers": {
    "giljo-mcp": {
      "command": "uvx",
      "args": ["giljo-mcp-client"],
      "env": {
        "GILJO_SERVER_URL": "http://localhost:7272",
        "GILJO_TENANT_KEY": "tenant-abc-123",  ← Unique per tenant
        "GILJO_API_PREFIX": "/api/tenant/tenant-abc-123"
      }
    }
  }
}
```

### Network Deployment Configurations

**Localhost Configuration**:
```json
{
  "env": {
    "GILJO_SERVER_URL": "http://localhost:7272",
    "GILJO_TENANT_KEY": "default"
  }
}
```

**LAN Configuration**:
```json  
{
  "env": {
    "GILJO_SERVER_URL": "http://192.168.1.100:7272",
    "GILJO_TENANT_KEY": "default"
  }
}
```

**WAN/Production Configuration**:
```json
{
  "env": {
    "GILJO_SERVER_URL": "https://api.yourdomain.com",
    "GILJO_TENANT_KEY": "production-tenant",
    "GILJO_API_KEY": "secure-api-key-here"
  }
}
```

---

## Template-Level AI Coding Agent Preferences

### Database Schema Enhancement

**AgentTemplate Model** (enhanced):
```python
class AgentTemplate(Base):
    __tablename__ = 'agent_templates'
    
    id = Column(String(36), primary_key=True)
    tenant_key = Column(String(36), nullable=False, index=True)
    name = Column(String(255), nullable=False)
    role = Column(String(100), nullable=False)
    
    # AI Coding Agent Preference (NEW)
    preferred_tool = Column(String(50), default="claude")  # claude, codex, gemini
    
    # Template content
    system_prompt = Column(Text, nullable=False)
    context_filters = Column(JSON, default=list)
    tools_enabled = Column(JSON, default=list)
```

### Template Creation with Tool Preference

**API Endpoint**:
```python
@router.post("/templates")
async def create_template(
    template: TemplateCreateRequest,
    current_user: User = Depends(get_current_user)
):
    """Create new agent template with AI coding agent preference"""
    
    new_template = AgentTemplate(
        id=str(uuid.uuid4()),
        tenant_key=current_user.tenant_key,
        name=template.name,
        role=template.role,
        preferred_tool=template.preferred_tool,  # claude, codex, gemini
        system_prompt=template.system_prompt,
        context_filters=template.context_filters,
        tools_enabled=template.tools_enabled
    )
    
    session.add(new_template)
    await session.commit()
    
    return new_template
```

### Template Usage with Tool Selection

**Agent Spawning Logic**:
```python
async def spawn_agent_with_tool_preference(
    template_name: str,
    mission: str,
    tenant_key: str
):
    """Spawn agent using template's preferred AI coding agent"""
    
    template = await get_template(template_name, tenant_key)
    preferred_tool = template.preferred_tool or "claude"
    
    if preferred_tool == "claude":
        return await spawn_claude_agent(template, mission)
    elif preferred_tool == "codex":
        return await generate_codex_instructions(template, mission)
    elif preferred_tool == "gemini":
        return await generate_gemini_workflow(template, mission)
```

---

## Security & Authentication

### User API Key Management

**Implementation Status**: COMPLETE (as of 2025-10-13)

GiljoAI MCP v3.0 implements a comprehensive user API key management system that integrates seamlessly with AI coding agent configuration generation.

**Key Features**:
- Per-user API key generation and management
- Automatic integration with MCP configuration generator
- Bcrypt hashing for secure storage (cost factor 12)
- One-time plaintext display (security best practice)
- Complete multi-tenant isolation
- Individual key revocation without affecting other users

---

### API Key Generation Flow

**Step 1: User Accesses Settings**
```
Settings → API and Integrations → Personal API Keys
```

**Step 2: Generate New Key**
```javascript
// Frontend: ApiKeyManager.vue
async generateApiKey(name) {
  const response = await api.post('/api/auth/api-keys/', {
    name: name,  // e.g., "Claude Code - 10/13/2025"
    scopes: ['mcp_config', 'projects:read', 'agents:write']
  })

  // Backend returns plaintext key ONCE
  return {
    key: 'gk_xxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxx',  // 32-char random
    key_id: 'uuid',
    key_preview: 'gk_xxxxx...',
    created_at: '2025-10-13T10:00:00Z'
  }
}
```

**Step 3: Key Stored Securely**
```python
# Backend: api/endpoints/auth.py
@router.post("/api/auth/api-keys/")
async def create_api_key(
    request: APIKeyCreateRequest,
    current_user: User = Depends(get_current_user)
):
    """Generate new API key for authenticated user"""

    # Generate cryptographically secure random key
    raw_key = f"gk_{secrets.token_urlsafe(32)}"

    # Hash with bcrypt (cost factor 12)
    key_hash = bcrypt.hashpw(
        raw_key.encode('utf-8'),
        bcrypt.gensalt(rounds=12)
    )

    api_key = APIKey(
        id=str(uuid.uuid4()),
        user_id=current_user.id,
        tenant_key=current_user.tenant_key,  # ← TENANT ISOLATION
        name=request.name,
        key_hash=key_hash.decode('utf-8'),
        key_preview=f"{raw_key[:8]}...",
        scopes=request.scopes,
        is_active=True
    )

    session.add(api_key)
    await session.commit()

    return {
        "key": raw_key,  # ← ONLY RETURNED ONCE
        "key_id": api_key.id,
        "key_preview": api_key.key_preview,
        "created_at": api_key.created_at
    }
```

---

### Automatic API Key Integration in AI Coding Agents

**AIToolSetup.vue Integration** (as of 2025-10-13):

When users generate MCP configurations, the system now automatically:
1. Generates a new API key with descriptive name
2. Embeds the key in the configuration
3. Displays security warnings about key storage

**Implementation**:
```javascript
// Frontend: components/AIToolSetup.vue
async generateConfigWithApiKey() {
  try {
    // Step 1: Generate new API key for this AI coding agent
    const keyName = `${this.selectedTool} - ${new Date().toLocaleDateString()}`
    const apiKeyResponse = await api.post('/api/auth/api-keys/', {
      name: keyName,
      scopes: ['mcp_config', 'projects:read', 'agents:write']
    })

    // Step 2: Generate configuration with embedded API key
    const configResponse = await api.get(
      `/api/ai-tools/config-generator/${this.selectedTool}`
    )

    // Step 3: Embed API key in configuration
    const config = JSON.parse(configResponse.data.config_content)
    config.mcpServers['giljo-mcp'].env.GILJO_API_KEY = apiKeyResponse.data.key

    // Step 4: Display configuration with security warnings
    this.generatedConfig = {
      ...configResponse.data,
      config_content: JSON.stringify(config, null, 2),
      api_key_preview: apiKeyResponse.data.key_preview
    }

    // Step 5: Show security warning
    this.showSecurityWarning(
      'API key generated and embedded. Store this configuration securely - ' +
      'the key will not be shown again.'
    )
  } catch (error) {
    this.handleError('Failed to generate configuration with API key', error)
  }
}
```

**Generated Configuration Example**:
```json
{
  "mcpServers": {
    "giljo-mcp": {
      "command": "uvx",
      "args": ["giljo-mcp-client"],
      "env": {
        "GILJO_SERVER_URL": "http://localhost:7272",
        "GILJO_TENANT_KEY": "user-tenant-key",
        "GILJO_API_KEY": "gk_xxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxx"
      }
    }
  }
}
```

---

### Database Schema

**APIKey Model**:
```python
class APIKey(Base):
    __tablename__ = 'api_keys'

    id = Column(String(36), primary_key=True)
    user_id = Column(String(36), ForeignKey('users.id'), nullable=False)
    tenant_key = Column(String(36), ForeignKey('tenants.tenant_key'), nullable=False)

    name = Column(String(255), nullable=False)
    key_hash = Column(String(255), nullable=False)  # bcrypt hashed
    key_preview = Column(String(20), nullable=False)  # gk_xxxxx...

    scopes = Column(JSON, default=['read'])

    created_at = Column(DateTime, default=datetime.utcnow)
    last_used_at = Column(DateTime, nullable=True)
    is_active = Column(Boolean, default=True)

    # Multi-tenant isolation
    __table_args__ = (
        Index('idx_api_keys_tenant_user', 'tenant_key', 'user_id'),
    )
```

**Query Example** (automatic tenant filtering):
```python
async def get_user_api_keys(user_id: str, tenant_key: str):
    """Get API keys for user (automatically filtered by tenant)"""
    stmt = select(APIKey).where(
        APIKey.user_id == user_id,
        APIKey.tenant_key == tenant_key,  # ← TENANT ISOLATION
        APIKey.is_active == True
    )
    result = await session.execute(stmt)
    return result.scalars().all()
```

---

### API Endpoints

**User API Key Management**:
```python
# List user's API keys
GET  /api/auth/api-keys/
# Returns: [{ id, name, key_preview, created_at, last_used_at, scopes }]

# Generate new API key
POST /api/auth/api-keys/
# Body: { name: str, scopes: list[str] }
# Returns: { key, key_id, key_preview, created_at }

# Revoke API key
DELETE /api/auth/api-keys/{key_id}
# Returns: { success: true, message: "API key revoked" }

# Update API key metadata
PATCH /api/auth/api-keys/{key_id}
# Body: { name: str }
# Returns: { success: true, api_key: {...} }
```

---

### Security Features

**Bcrypt Hashing**:
- Cost factor: 12 (high security)
- Salt automatically generated
- One-way hashing (cannot recover plaintext)

**One-Time Display**:
- Plaintext key returned only once during generation
- Never stored in plaintext
- Key preview shown for identification (gk_xxxxx...)

**Multi-Tenant Isolation**:
- All API keys scoped to tenant_key
- Users can only access their own tenant's keys
- Database queries automatically filtered

**httpOnly Cookie Authentication**:
- Session token stored in httpOnly cookie
- JavaScript cannot access (XSS protection)
- SameSite=lax prevents CSRF attacks
- Browser automatically includes in requests

**Scope-Based Permissions** (future enhancement):
```json
{
  "scopes": [
    "projects:read",
    "projects:write",
    "agents:read",
    "agents:write",
    "mcp_config"
  ]
}
```

---

### User Experience

**API Key Manager Interface**:
```
┌───────────────────────────────────────────────────────┐
│ Personal API Keys                                     │
├───────────────────────────────────────────────────────┤
│ Manage your API keys for MCP configuration           │
│                                                       │
│ [+ Generate New Key]                                  │
│                                                       │
│ ┌─────────────────────────────────────────────────┐  │
│ │ Name                │ Key       │ Created │ ... │  │
│ ├─────────────────────────────────────────────────┤  │
│ │ Claude Code - 10/13 │ gk_xxxx.. │ 2 days  │ ⚙   │  │
│ │ CODEX CLI - 10/10   │ gk_yyyy.. │ 5 days  │ ⚙   │  │
│ └─────────────────────────────────────────────────┘  │
└───────────────────────────────────────────────────────┘
```

**AI Coding Agent Configuration Flow**:
```
1. User selects AI coding agent (Claude Code, CODEX, Gemini)
2. System automatically generates API key
3. Key embedded in generated configuration
4. Security warning displayed
5. User copies/downloads configuration
6. Key stored securely (never shown again)
```

---

### Configuration Security

**Secure Configuration Generation**:
- User-specific API keys embedded automatically
- Tenant keys validated against user permissions
- Server URLs validated for security (no internal IPs in production)
- Configuration files include security warnings
- One-time plaintext display enforced

**Network Deployment Security**:
```json
{
  "mcpServers": {
    "giljo-mcp": {
      "command": "uvx",
      "args": ["giljo-mcp-client"],
      "env": {
        "GILJO_SERVER_URL": "https://api.yourdomain.com",  // ← HTTPS
        "GILJO_TENANT_KEY": "production-tenant",
        "GILJO_API_KEY": "gk_xxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxx"  // ← User key
      }
    }
  }
}
```

**Security Best Practices**:
- Always use HTTPS for WAN deployments
- Rotate API keys regularly (30-90 days)
- Revoke unused keys immediately
- Never commit API keys to version control
- Store keys in secure credential management systems

---

## Cross-Platform Integration

### Windows Integration

**PowerShell Setup Script** (generated):
```powershell
# GiljoAI MCP Windows Setup
# Generated for tenant: default

$ConfigPath = "$env:USERPROFILE\.claude.json"
$Config = @{
    mcpServers = @{
        "giljo-mcp" = @{
            command = "uvx"
            args = @("giljo-mcp-client")
            env = @{
                GILJO_SERVER_URL = "http://localhost:7272"
                GILJO_TENANT_KEY = "default"
            }
        }
    }
} | ConvertTo-Json -Depth 3

$Config | Out-File -FilePath $ConfigPath -Encoding UTF8
Write-Host "✅ GiljoAI MCP configuration saved to $ConfigPath"
```

### Linux/macOS Integration

**Bash Setup Script** (generated):
```bash
#!/bin/bash
# GiljoAI MCP Linux/macOS Setup
# Generated for tenant: default

CONFIG_FILE="$HOME/.claude.json"
CONFIG_CONTENT='
{
  "mcpServers": {
    "giljo-mcp": {
      "command": "uvx",
      "args": ["giljo-mcp-client"],
      "env": {
        "GILJO_SERVER_URL": "http://localhost:7272",
        "GILJO_TENANT_KEY": "default"
      }
    }
  }
}'

echo "$CONFIG_CONTENT" > "$CONFIG_FILE"
echo "✅ GiljoAI MCP configuration saved to $CONFIG_FILE"

# Verify uvx installation
if ! command -v uvx &> /dev/null; then
    echo "⚠️  uvx not found. Install with: pip install uvx"
fi
```

---

## Testing & Quality Assurance

### Integration Test Suite

**Test Coverage** (`tests/api/test_ai_tools_config_generator.py` - 366 lines):

```python
class TestAIToolsConfigGenerator:
    """Test suite for AI coding agent configuration generation"""
    
    async def test_claude_config_generation(self):
        """Test Claude Code CLI configuration generation"""
        response = await client.get(
            "/api/ai-tools/config-generator/claude?tenant_key=test_tenant"
        )
        
        assert response.status_code == 200
        config = response.json()
        
        assert config["tool"] == "claude"
        assert config["config_format"] == "json"
        assert "mcpServers" in json.loads(config["config_content"])
        
    async def test_codex_config_generation(self):
        """Test CODEX CLI configuration generation"""
        response = await client.get(
            "/api/ai-tools/config-generator/codex?tenant_key=test_tenant"
        )
        
        assert response.status_code == 200
        config = response.json()
        
        assert config["tool"] == "codex"
        assert "mcp_servers" in json.loads(config["config_content"])
        
    async def test_tenant_isolation(self):
        """Test tenant-specific configuration isolation"""
        tenant_a_response = await client.get(
            "/api/ai-tools/config-generator/claude?tenant_key=tenant_a"
        )
        tenant_b_response = await client.get(
            "/api/ai-tools/config-generator/claude?tenant_key=tenant_b"  
        )
        
        config_a = json.loads(tenant_a_response.json()["config_content"])
        config_b = json.loads(tenant_b_response.json()["config_content"])
        
        assert config_a["mcpServers"]["giljo-mcp"]["env"]["GILJO_TENANT_KEY"] == "tenant_a"
        assert config_b["mcpServers"]["giljo-mcp"]["env"]["GILJO_TENANT_KEY"] == "tenant_b"
```

### Frontend Component Testing

**Vue Test Coverage**:
```javascript
describe('AIToolSetup Component', () => {
  test('renders tool selection dropdown', () => {
    const wrapper = mount(AIToolSetup)
    expect(wrapper.find('.tool-selector').exists()).toBe(true)
  })
  
  test('generates configuration on tool selection', async () => {
    const wrapper = mount(AIToolSetup)
    await wrapper.find('select').setValue('claude')
    
    expect(wrapper.vm.generatedConfig).toBeTruthy()
    expect(wrapper.vm.generatedConfig.tool).toBe('claude')
  })
  
  test('copies configuration to clipboard', async () => {
    Object.assign(navigator, {
      clipboard: { writeText: jest.fn() }
    })
    
    const wrapper = mount(AIToolSetup)
    await wrapper.find('.copy-button').trigger('click')
    
    expect(navigator.clipboard.writeText).toHaveBeenCalled()
  })
})
```

---

## Troubleshooting

### Common Configuration Issues

**Issue: MCP server not detected in Claude Code CLI**

**Solution**:
```markdown
1. Verify configuration file location:
   - Windows: `%USERPROFILE%\.claude.json`
   - Linux/macOS: `~/.claude.json`

2. Check configuration syntax:
   ```bash
   python -m json.tool ~/.claude.json
   ```

3. Restart Claude Code CLI completely

4. Test connection:
   ```
   /mcp list-servers
   /mcp test-connection giljo-mcp
   ```
```

**Issue: Authentication failures**

**Solution**:
```markdown
1. Verify server URL accessibility:
   ```bash
   curl http://localhost:7272/health
   ```

2. Check tenant key validity:
   - Ensure tenant exists in database
   - Verify tenant key matches user's tenant

3. For network deployments, verify API key:
   - Generate new API key from Settings
   - Update configuration with valid key
```

**Issue: Cross-platform path issues**

**Solution**:
```markdown
1. Use absolute paths in configuration:
   - Windows: `C:\Users\username\.claude.json`
   - Linux: `/home/username/.claude.json`
   - macOS: `/Users/username/.claude.json`

2. Verify file permissions:
   ```bash
   ls -la ~/.claude.json  # Should be readable
   ```

3. Check environment variables:
   ```bash
   echo $GILJO_SERVER_URL
   echo $GILJO_TENANT_KEY
   ```
```

---

## Future Enhancements

### Planned Features

**Advanced Tool Detection**:
- Automatic discovery of installed AI coding agents
- Version compatibility checking
- Configuration validation

**Enhanced Integration**:
- Real-time configuration sync
- Multi-tool orchestration workflows  
- Template-level tool assignment

**Enterprise Features**:
- Centralized configuration management
- Team-level tool assignments
- Usage analytics and monitoring

### Experimental Integrations

**GitHub Copilot Integration**:
- MCP protocol support for Copilot
- GiljoAI orchestration through VS Code
- Context sharing between tools

**Local LLM Integration**:
- Ollama and LocalAI support
- Privacy-focused deployments  
- Custom model integration

---

**See Also**:
- [GiljoAI MCP Purpose](GILJOAI_MCP_PURPOSE.md) - Understanding multi-agent orchestration
- [Server Architecture & Tech Stack](SERVER_ARCHITECTURE_TECH_STACK.md) - Technical implementation details
- [First Launch Experience](FIRST_LAUNCH_EXPERIENCE.md) - Setup wizard integration
- [User Structures & Tenants](USER_STRUCTURES_TENANTS.md) - Multi-tenant configuration

---

## HANDOVER 0015 - User API Key Management (COMPLETE)

**Implementation Status**: ✅ **COMPLETE** - User-specific API key generation and management for secure MCP server access

**Problem Solved**: Multi-user setup now provides individual API key management for isolated, secure MCP configuration. Each user gets personal API keys instead of sharing system-wide keys.

**Implementation Details**:

### Frontend Components Delivered
- **`ApiKeyManager.vue`** (266 lines) - Full-featured user API key management component
- **`ApiKeyWizard.vue`** - Modal for generating new API keys with descriptive names
- **Integration**: Added to `UserSettings.vue` → "API and Integrations" tab
- **Professional UI**: Data table with sorting, key preview, delete confirmations, loading states

### AI Coding Agent Integration Enhanced
- **`AIToolSetup.vue`** - Automatic API key generation during configuration
- **Workflow**: When generating AI coding agent configs, automatically creates user API keys
- **Key Naming**: Auto-generates descriptive names (e.g., "Claude Code - 10/13/2025")
- **Security**: One-time plaintext display, bcrypt hashing for storage

### Security Improvements
- **Per-User Access Control**: Individual API keys for audit and isolation
- **Tenant-Specific**: All API key queries filtered by `tenant_key`
- **httpOnly Cookie Authentication**: XSS protection, automatic browser management
- **API Key Lifecycle**: Full CRUD operations (generate, list, revoke)

### Multi-Tenant MCP Configuration
**Before**: Single shared API key for all users
```json
{
  "GILJO_API_KEY": "shared-system-key"  // Security risk
}
```

**After**: User-specific API keys with tenant isolation
```json
{
  "mcpServers": {
    "giljo-mcp": {
      "command": "uvx",
      "args": ["giljo-mcp-client"],
      "env": {
        "GILJO_SERVER_URL": "http://10.1.0.164:7272",
        "GILJO_TENANT_KEY": "usr_abc123",        // User-specific
        "GILJO_API_KEY": "gk_user_xyz789..."    // User-specific API key
      }
    }
  }
}
```

### Features Delivered
- ✅ **User API Key Generation**: Each user can generate personal API keys in Settings
- ✅ **MCP Config Integration**: AI coding agent setup uses user's API keys automatically
- ✅ **Multi-Tenant Isolation**: Users only see their own keys and projects
- ✅ **Authentication Fixed**: Resolved 401 errors with httpOnly cookie documentation
- ✅ **Professional UI/UX**: Full-featured key management with security best practices

### Database Schema
```sql
-- User API keys table (already existed, now fully integrated)
CREATE TABLE user_api_keys (
    id UUID PRIMARY KEY,
    user_id UUID REFERENCES users(id),
    tenant_key VARCHAR REFERENCES tenants(tenant_key),
    key_hash VARCHAR NOT NULL,     -- Hashed API key (bcrypt)
    key_preview VARCHAR NOT NULL,  -- First 8 + last 4 chars for display
    name VARCHAR,                  -- User-friendly name
    created_at TIMESTAMP,
    last_used_at TIMESTAMP,
    is_active BOOLEAN DEFAULT TRUE
);
```

### Implementation Quality
- **Test Coverage**: 15 unit tests for AIToolSetup component (all passing)
- **Error Handling**: Graceful 401 handling with authentication prompts
- **Security Best Practices**: Key preview only, secure deletion confirmation
- **Cross-Platform**: Works on Windows, Linux, macOS

**Archive Status**: Moved to `handovers/completed/harmonized/HANDOVER_0015_USER_API_KEY_MANAGEMENT-C.md`

---

*This document provides comprehensive coverage of GiljoAI MCP's AI coding agent configuration management as the single source of truth for the October 13, 2025 documentation harmonization.*
