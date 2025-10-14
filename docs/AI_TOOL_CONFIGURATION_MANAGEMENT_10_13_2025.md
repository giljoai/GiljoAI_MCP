# AI Tool Configuration Management

**Document Version**: 10_13_2025  
**Status**: Single Source of Truth  
**Last Updated**: October 13, 2025

---

## Overview

GiljoAI MCP v3.0 implements **AI-agnostic integration** that supports multiple AI development tools including Claude Code, CODEX CLI, and Gemini CLI. The system provides a **user-friendly configuration generator** that creates ready-to-use MCP configuration files for seamless integration across platforms.

### Key Features

- **Multi-AI Tool Support**: Claude Code, CODEX, Gemini CLI
- **Configuration Generator API**: Automated MCP config creation
- **Cross-Platform Setup**: Windows, Linux, macOS compatibility
- **User-Friendly Interface**: Copy-paste and download workflows
- **Tenant-Specific Configs**: Multi-tenant configuration isolation
- **Template-Level Preferences**: AI tool selection per agent template

---

## Supported AI Development Tools

### Claude Code CLI
**Status**: Primary integration  
**Capabilities**: Sub-agent spawning, real-time orchestration  
**Configuration**: Automatic MCP server setup

### CODEX CLI (OpenAI)
**Status**: Community integration  
**Capabilities**: Manual orchestration, copy-paste workflows  
**Configuration**: Generated MCP config files

### Gemini CLI (Google)
**Status**: Experimental support  
**Capabilities**: Manual orchestration, configuration templates  
**Configuration**: Generated setup guides

---

## Architecture Components

### 1. AI Tool Configuration API

**Location**: `api/endpoints/ai_tools.py` (425 lines)

**Key Endpoints**:
```python
GET  /api/ai-tools/supported          # List available AI tools
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
    """Generate AI tool-specific MCP configuration"""
    
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
    """Generate AI tool-specific MCP configurations"""
    
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

### Step 1: Access AI Tools Setup

**From Settings Page**:
```
Settings → API and Integrations → [Connect AI Tools]
```

**From Dashboard Quick Actions**:
```
Dashboard → Quick Actions → [Setup AI Tools]
```

### Step 2: Tool Selection

**Available Options**:
```
┌─────────────────────────────────────────┐
│ Select AI Tool:  [Claude Code CLI ▼]   │
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

## Template-Level AI Tool Preferences

### Database Schema Enhancement

**AgentTemplate Model** (enhanced):
```python
class AgentTemplate(Base):
    __tablename__ = 'agent_templates'
    
    id = Column(String(36), primary_key=True)
    tenant_key = Column(String(36), nullable=False, index=True)
    name = Column(String(255), nullable=False)
    role = Column(String(100), nullable=False)
    
    # AI Tool Preference (NEW)
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
    """Create new agent template with AI tool preference"""
    
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
    """Spawn agent using template's preferred AI tool"""
    
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

### API Key Management

**For Network Deployments**:
```python
@router.post("/ai-tools/generate-api-key")
async def generate_api_key(
    current_user: User = Depends(get_current_user),
    scope: str = Body(...),
    expires_days: int = Body(30)
):
    """Generate API key for AI tool integration"""
    
    api_key = ApiKey(
        id=str(uuid.uuid4()),
        user_id=current_user.id,
        tenant_key=current_user.tenant_key,
        name=f"AI Tool Integration ({scope})",
        key_hash=hash_api_key(generate_api_key()),
        scope=scope,  # "ai_tools", "read_only", "full_access"
        expires_at=datetime.utcnow() + timedelta(days=expires_days)
    )
    
    session.add(api_key)
    await session.commit()
    
    return {
        "api_key": api_key.key_value,  # Only returned once
        "key_id": api_key.id,
        "expires_at": api_key.expires_at,
        "scope": api_key.scope
    }
```

### Configuration Security

**Secure Configuration Generation**:
- API keys included only for WAN deployments
- Tenant keys validated against user permissions
- Server URLs validated for security (no internal IPs in production)
- Configuration files include security warnings

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
    """Test suite for AI tool configuration generation"""
    
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
- Automatic discovery of installed AI tools
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
- [GiljoAI MCP Purpose](GILJOAI_MCP_PURPOSE_10_13_2025.md) - Understanding multi-agent orchestration
- [Server Architecture & Tech Stack](SERVER_ARCHITECTURE_TECH_STACK_10_13_2025.md) - Technical implementation details
- [First Launch Experience](FIRST_LAUNCH_EXPERIENCE_10_13_2025.md) - Setup wizard integration
- [User Structures & Tenants](USER_STRUCTURES_TENANTS_10_13_2025.md) - Multi-tenant configuration

---

*This document provides comprehensive coverage of GiljoAI MCP's AI tool configuration management as the single source of truth for the October 13, 2025 documentation harmonization.*