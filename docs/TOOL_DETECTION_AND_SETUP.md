# Tool Detection and Setup Architecture

## Overview

GiljoAI MCP uses a two-phase approach to separate system installation from user configuration:

1. **Phase 1: Installation** - System-level setup (DB, dependencies, services)
2. **Phase 2: First-Run Wizard** - User-level configuration (tool selection, agent templates)

This architecture supports:
- ✅ Multiple users with different tool preferences (server mode)
- ✅ Easy tool switching without reinstallation
- ✅ Clean separation of concerns
- ✅ GUI-based configuration (better UX than CLI)

---

## Phase 1: Installation (System Setup)

### Scope

**What Installation Handles:**
- PostgreSQL database setup
- Python dependencies (`pip install -r requirements.txt`)
- Frontend dependencies (`npm install`)
- Environment file creation (`.env`)
- Configuration file creation (`config.yaml`)
- Initial admin credentials (server mode)
- Firewall rules (server mode)
- Service registration (optional)

**What Installation DOES NOT Handle:**
- ❌ User tool preferences
- ❌ Agent template installation
- ❌ Tool detection
- ❌ User-specific configuration

### Installation Flow

```bash
# CLI Installer
python installer/cli/install.py

Steps:
1. Detect platform (Windows/Linux/Mac)
2. Check PostgreSQL 18
3. Create database
4. Run migrations
5. Install Python dependencies
6. Install frontend dependencies
7. Build frontend
8. Create config.yaml (with sensible defaults)
9. Create .env file
10. Setup admin user (if server mode)
11. Display completion message

Output:
✓ Installation complete!
✓ Database: giljo_mcp (PostgreSQL 18)
✓ API Server: http://localhost:7272
✓ Frontend: http://localhost:7274

Next Steps:
1. Start services: python start_giljo.py
2. Open browser: http://localhost:7274
3. Complete first-run wizard to configure your AI tool
```

**Key Point:** Installation is FAST and focused. No interactive questions about tools.

---

## Phase 2: First-Run Wizard

### When It Runs

**Localhost Mode:**
- First time user accesses http://localhost:7274
- Triggered by: `user_profile.setup_completed = false`

**Server Mode:**
- Each user's first login
- Triggered by: `user_profile.setup_completed = false` per user

### Wizard Flow

```
Step 1: Welcome
└─ Intro to GiljoAI MCP
   Purpose: Multi-agent orchestration
   Next: Tool detection

Step 2: Tool Detection
└─ Auto-scan for installed tools
   Detected: Claude Code ✓, Cursor ✓
   Not Found: Gemini CLI, Aider, Codex, Windsurf
   Next: Tool selection

Step 3: Tool Selection
└─ User chooses primary tool
   Options:
   ├─ Detected tools (recommended)
   ├─ Manual selection (all tools)
   └─ Skip (configure later)

Step 4: Tool Configuration
└─ Tool-specific setup
   If Claude Code:
     → Install agent templates to ~/.claude/agents/
   If Gemini CLI:
     → Configure subagent paths
   If Cursor:
     → Setup worktree preferences
   If Aider/Codex/Windsurf:
     → Configure clipboard workflow

Step 5: Validation
└─ Test tool accessibility
   Run: claude code --version (or equivalent)
   Test: MCP connection
   Verify: Agent templates installed

Step 6: Completion
└─ Setup summary
   Ready to create projects!
```

### Wizard UI Components

**Step 1: Welcome**

```vue
<template>
  <v-card>
    <v-card-title>Welcome to GiljoAI MCP! 🎉</v-card-title>
    <v-card-text>
      <p>
        GiljoAI MCP transforms AI coding assistants into coordinated
        development teams. Before we begin, let's configure your setup.
      </p>

      <v-alert type="info" class="mt-4">
        This wizard will:
        <ul>
          <li>Detect your installed AI coding tools</li>
          <li>Install optimized agent templates</li>
          <li>Configure your workspace</li>
          <li>Validate your setup</li>
        </ul>
      </v-alert>
    </v-card-text>

    <v-card-actions>
      <v-spacer />
      <v-btn color="primary" @click="nextStep">
        Get Started
      </v-btn>
    </v-card-actions>
  </v-card>
</template>
```

**Step 2: Tool Detection**

```vue
<template>
  <v-card>
    <v-card-title>Detecting AI Coding Tools...</v-card-title>

    <v-card-text>
      <v-progress-linear
        v-if="scanning"
        indeterminate
        color="primary"
      />

      <v-list class="mt-4">
        <v-list-item
          v-for="tool in allTools"
          :key="tool.id"
        >
          <template v-slot:prepend>
            <v-icon
              :color="tool.detected ? 'success' : 'grey'"
              :icon="tool.detected ? 'mdi-check-circle' : 'mdi-help-circle'"
            />
          </template>

          <v-list-item-title>{{ tool.name }}</v-list-item-title>

          <v-list-item-subtitle>
            <span v-if="tool.detected">
              ✓ Detected at {{ tool.path }}
            </span>
            <span v-else class="text-grey">
              Not installed
            </span>
          </v-list-item-subtitle>

          <template v-slot:append>
            <v-chip
              v-if="tool.detected"
              :color="tool.multiAgent ? 'success' : 'warning'"
              size="small"
            >
              {{ tool.multiAgent ? 'Multi-Agent' : 'Single-Agent' }}
            </v-chip>
          </template>
        </v-list-item>
      </v-list>

      <v-alert
        v-if="detectedTools.length === 0"
        type="warning"
        class="mt-4"
      >
        No AI coding tools detected. You can:
        <ul>
          <li>Install a tool and re-run this wizard</li>
          <li>Manually select a tool you'll install later</li>
          <li>Skip for now and configure in Settings</li>
        </ul>
      </v-alert>
    </v-card-text>

    <v-card-actions>
      <v-btn @click="rescan">
        <v-icon left>mdi-refresh</v-icon>
        Re-scan
      </v-btn>
      <v-spacer />
      <v-btn @click="previousStep">Back</v-btn>
      <v-btn
        color="primary"
        @click="nextStep"
        :disabled="detectedTools.length === 0 && !allowSkip"
      >
        Next
      </v-btn>
    </v-card-actions>
  </v-card>
</template>

<script>
export default {
  data() {
    return {
      scanning: true,
      allTools: [
        {
          id: 'claude_code',
          name: 'Claude Code',
          multiAgent: true,
          detected: false,
          path: null
        },
        {
          id: 'gemini_cli',
          name: 'Gemini CLI',
          multiAgent: true,
          detected: false,
          path: null
        },
        {
          id: 'cursor',
          name: 'Cursor',
          multiAgent: true,
          detected: false,
          path: null
        },
        {
          id: 'continue',
          name: 'Continue.dev',
          multiAgent: true,
          detected: false,
          path: null
        },
        {
          id: 'windsurf',
          name: 'Windsurf',
          multiAgent: false,
          detected: false,
          path: null
        },
        {
          id: 'codex',
          name: 'Codex CLI',
          multiAgent: false,
          detected: false,
          path: null
        },
        {
          id: 'aider',
          name: 'Aider',
          multiAgent: false,
          detected: false,
          path: null
        }
      ]
    }
  },

  computed: {
    detectedTools() {
      return this.allTools.filter(t => t.detected)
    }
  },

  mounted() {
    this.scanTools()
  },

  methods: {
    async scanTools() {
      this.scanning = true

      // Call backend to detect tools
      const response = await fetch('/api/setup/detect-tools')
      const detected = await response.json()

      // Update tool detection status
      this.allTools.forEach(tool => {
        const found = detected.tools.find(t => t.id === tool.id)
        if (found) {
          tool.detected = true
          tool.path = found.path
          tool.version = found.version
        }
      })

      this.scanning = false
    },

    async rescan() {
      await this.scanTools()
    }
  }
}
</script>
```

**Step 3: Tool Selection**

```vue
<template>
  <v-card>
    <v-card-title>Select Your Primary AI Tool</v-card-title>

    <v-card-text>
      <p>
        Choose the AI coding tool you'll use most often. You can add
        additional tools later in Settings.
      </p>

      <!-- Detected Tools (Recommended) -->
      <v-card
        v-if="detectedTools.length > 0"
        class="mt-4 pa-4 bg-success-lighten-5"
      >
        <v-card-title class="text-subtitle-1">
          Recommended (Detected on your system)
        </v-card-title>

        <v-radio-group v-model="selectedTool">
          <v-radio
            v-for="tool in detectedTools"
            :key="tool.id"
            :value="tool.id"
          >
            <template v-slot:label>
              <div>
                <strong>{{ tool.name }}</strong>
                <v-chip
                  :color="tool.multiAgent ? 'success' : 'warning'"
                  size="small"
                  class="ml-2"
                >
                  {{ tool.multiAgent ? 'Multi-Agent' : 'Single-Agent' }}
                </v-chip>
                <br>
                <small class="text-grey">{{ tool.path }}</small>
              </div>
            </template>
          </v-radio>
        </v-radio-group>
      </v-card>

      <!-- All Tools (Manual Selection) -->
      <v-expansion-panels class="mt-4">
        <v-expansion-panel>
          <v-expansion-panel-title>
            Show all available tools (manual selection)
          </v-expansion-panel-title>

          <v-expansion-panel-text>
            <v-radio-group v-model="selectedTool">
              <v-radio
                v-for="tool in allTools"
                :key="tool.id"
                :value="tool.id"
                :disabled="tool.detected === false"
              >
                <template v-slot:label>
                  <div>
                    <strong>{{ tool.name }}</strong>
                    <v-chip
                      v-if="!tool.detected"
                      color="grey"
                      size="small"
                      class="ml-2"
                    >
                      Not Installed
                    </v-chip>
                    <br>
                    <small>{{ tool.description }}</small>
                  </div>
                </template>
              </v-radio>
            </v-radio-group>
          </v-expansion-panel-text>
        </v-expansion-panel>
      </v-expansion-panels>

      <!-- Skip Option -->
      <v-checkbox
        v-model="skipSetup"
        label="Skip tool setup (configure later in Settings)"
        class="mt-4"
      />
    </v-card-text>

    <v-card-actions>
      <v-btn @click="previousStep">Back</v-btn>
      <v-spacer />
      <v-btn
        color="primary"
        @click="nextStep"
        :disabled="!selectedTool && !skipSetup"
      >
        Next
      </v-btn>
    </v-card-actions>
  </v-card>
</template>
```

**Step 4: Tool Configuration**

```vue
<template>
  <v-card>
    <v-card-title>Configure {{ toolName }}</v-card-title>

    <v-card-text>
      <!-- Claude Code Configuration -->
      <div v-if="selectedTool === 'claude_code'">
        <p>
          We'll install optimized agent templates to your Claude Code
          agents directory.
        </p>

        <v-text-field
          v-model="agentPath"
          label="Agent Templates Path"
          hint="Default: ~/.claude/agents"
          persistent-hint
          readonly
        />

        <v-list class="mt-4">
          <v-list-subheader>Agent Templates to Install</v-list-subheader>
          <v-list-item
            v-for="agent in agentTemplates"
            :key="agent.name"
          >
            <template v-slot:prepend>
              <v-icon
                :color="agent.installed ? 'success' : 'grey'"
                :icon="agent.installed ? 'mdi-check' : 'mdi-file'"
              />
            </template>

            <v-list-item-title>{{ agent.name }}</v-list-item-title>
            <v-list-item-subtitle>{{ agent.description }}</v-list-item-subtitle>
          </v-list-item>
        </v-list>

        <v-btn
          color="primary"
          @click="installAgents"
          :loading="installing"
          class="mt-4"
        >
          Install Agent Templates
        </v-btn>
      </div>

      <!-- Aider Configuration -->
      <div v-else-if="selectedTool === 'aider'">
        <p>
          Aider uses a clipboard-based workflow. No agent templates needed.
        </p>

        <v-alert type="info">
          When you activate projects, you'll see ready-to-copy prompts
          in the dashboard. Simply paste them into Aider terminals.
        </v-alert>

        <v-select
          v-model="aiderModel"
          :items="aiderModels"
          label="Default Model"
          hint="Which LLM should Aider use?"
        />
      </div>

      <!-- Other tools... -->
    </v-card-text>

    <v-card-actions>
      <v-btn @click="previousStep">Back</v-btn>
      <v-spacer />
      <v-btn
        color="primary"
        @click="nextStep"
        :disabled="!configurationComplete"
      >
        Next
      </v-btn>
    </v-card-actions>
  </v-card>
</template>

<script>
export default {
  data() {
    return {
      agentPath: '~/.claude/agents',
      installing: false,
      agentTemplates: [
        { name: 'giljo-orchestrator.md', description: 'Multi-agent coordinator', installed: false },
        { name: 'giljo-database-expert.md', description: 'PostgreSQL specialist', installed: false },
        { name: 'giljo-backend-dev.md', description: 'API implementation', installed: false },
        { name: 'giljo-tester.md', description: 'Integration testing', installed: false },
        { name: 'giljo-security-auditor.md', description: 'Security review', installed: false },
        { name: 'giljo-researcher.md', description: 'Research & discovery', installed: false },
        { name: 'giljo-architect.md', description: 'System architecture', installed: false },
        { name: 'giljo-documenter.md', description: 'Documentation', installed: false }
      ],
      aiderModel: 'claude-3.7-sonnet',
      aiderModels: [
        'claude-3.7-sonnet',
        'gpt-4o',
        'deepseek-chat-v3',
        'deepseek-r1'
      ]
    }
  },

  computed: {
    configurationComplete() {
      if (this.selectedTool === 'claude_code') {
        return this.agentTemplates.every(a => a.installed)
      }
      return true
    }
  },

  methods: {
    async installAgents() {
      this.installing = true

      try {
        const response = await fetch('/api/setup/install-agents', {
          method: 'POST',
          headers: { 'Content-Type': 'application/json' },
          body: JSON.stringify({
            tool: this.selectedTool,
            path: this.agentPath
          })
        })

        const result = await response.json()

        // Update installation status
        result.installed.forEach(agentName => {
          const agent = this.agentTemplates.find(a => a.name === agentName)
          if (agent) agent.installed = true
        })

        this.$toast.success('Agent templates installed successfully!')
      } catch (error) {
        this.$toast.error('Failed to install agent templates')
      } finally {
        this.installing = false
      }
    }
  }
}
</script>
```

**Step 5: Validation**

```vue
<template>
  <v-card>
    <v-card-title>Validating Setup...</v-card-title>

    <v-card-text>
      <v-list>
        <v-list-item>
          <template v-slot:prepend>
            <v-progress-circular
              v-if="checks.tool.status === 'running'"
              indeterminate
              size="24"
            />
            <v-icon
              v-else
              :color="checks.tool.status === 'success' ? 'success' : 'error'"
              :icon="checks.tool.status === 'success' ? 'mdi-check-circle' : 'mdi-alert-circle'"
            />
          </template>

          <v-list-item-title>Tool Accessibility</v-list-item-title>
          <v-list-item-subtitle>{{ checks.tool.message }}</v-list-item-subtitle>
        </v-list-item>

        <v-list-item>
          <template v-slot:prepend>
            <v-progress-circular
              v-if="checks.mcp.status === 'running'"
              indeterminate
              size="24"
            />
            <v-icon
              v-else
              :color="checks.mcp.status === 'success' ? 'success' : 'error'"
              :icon="checks.mcp.status === 'success' ? 'mdi-check-circle' : 'mdi-alert-circle'"
            />
          </template>

          <v-list-item-title>MCP Connection</v-list-item-title>
          <v-list-item-subtitle>{{ checks.mcp.message }}</v-list-item-subtitle>
        </v-list-item>

        <v-list-item v-if="selectedTool === 'claude_code'">
          <template v-slot:prepend>
            <v-progress-circular
              v-if="checks.agents.status === 'running'"
              indeterminate
              size="24"
            />
            <v-icon
              v-else
              :color="checks.agents.status === 'success' ? 'success' : 'error'"
              :icon="checks.agents.status === 'success' ? 'mdi-check-circle' : 'mdi-alert-circle'"
            />
          </template>

          <v-list-item-title>Agent Templates</v-list-item-title>
          <v-list-item-subtitle>{{ checks.agents.message }}</v-list-item-subtitle>
        </v-list-item>
      </v-list>

      <v-alert
        v-if="allChecksComplete && allChecksPassed"
        type="success"
        class="mt-4"
      >
        ✓ All checks passed! Your setup is ready.
      </v-alert>

      <v-alert
        v-else-if="allChecksComplete && !allChecksPassed"
        type="error"
        class="mt-4"
      >
        Some checks failed. Please review the errors above and try again.
      </v-alert>
    </v-card-text>

    <v-card-actions>
      <v-btn
        v-if="!allChecksPassed"
        @click="retryValidation"
      >
        Retry
      </v-btn>
      <v-spacer />
      <v-btn
        color="primary"
        @click="nextStep"
        :disabled="!allChecksPassed"
      >
        Complete Setup
      </v-btn>
    </v-card-actions>
  </v-card>
</template>

<script>
export default {
  data() {
    return {
      checks: {
        tool: { status: 'pending', message: '' },
        mcp: { status: 'pending', message: '' },
        agents: { status: 'pending', message: '' }
      }
    }
  },

  computed: {
    allChecksComplete() {
      return Object.values(this.checks).every(c =>
        c.status === 'success' || c.status === 'error'
      )
    },

    allChecksPassed() {
      return Object.values(this.checks).every(c => c.status === 'success')
    }
  },

  mounted() {
    this.runValidation()
  },

  methods: {
    async runValidation() {
      // Check 1: Tool accessibility
      this.checks.tool.status = 'running'
      try {
        const response = await fetch('/api/setup/validate-tool', {
          method: 'POST',
          headers: { 'Content-Type': 'application/json' },
          body: JSON.stringify({ tool: this.selectedTool })
        })
        const result = await response.json()

        this.checks.tool.status = result.success ? 'success' : 'error'
        this.checks.tool.message = result.message
      } catch (error) {
        this.checks.tool.status = 'error'
        this.checks.tool.message = 'Failed to validate tool'
      }

      // Check 2: MCP connection
      this.checks.mcp.status = 'running'
      try {
        const response = await fetch('/api/health')
        this.checks.mcp.status = response.ok ? 'success' : 'error'
        this.checks.mcp.message = response.ok
          ? 'MCP server is running'
          : 'MCP server not responding'
      } catch (error) {
        this.checks.mcp.status = 'error'
        this.checks.mcp.message = 'Cannot connect to MCP server'
      }

      // Check 3: Agent templates (if applicable)
      if (this.selectedTool === 'claude_code') {
        this.checks.agents.status = 'running'
        try {
          const response = await fetch('/api/setup/verify-agents')
          const result = await response.json()

          this.checks.agents.status = result.all_installed ? 'success' : 'error'
          this.checks.agents.message = `${result.installed_count}/${result.total_count} templates installed`
        } catch (error) {
          this.checks.agents.status = 'error'
          this.checks.agents.message = 'Failed to verify agent templates'
        }
      }
    },

    retryValidation() {
      Object.keys(this.checks).forEach(key => {
        this.checks[key].status = 'pending'
      })
      this.runValidation()
    }
  }
}
</script>
```

---

## Backend Implementation

### API Endpoints

**File:** `api/endpoints/setup.py`

```python
from fastapi import APIRouter, Depends
from pathlib import Path
import subprocess
import shutil
from typing import Dict, List

router = APIRouter(prefix="/api/setup", tags=["setup"])


@router.get("/detect-tools")
async def detect_tools() -> Dict:
    """
    Scan system for installed AI coding tools.
    """
    tools = []

    # Check Claude Code
    try:
        result = subprocess.run(
            ["claude", "code", "--version"],
            capture_output=True,
            text=True,
            timeout=5
        )
        if result.returncode == 0:
            tools.append({
                "id": "claude_code",
                "name": "Claude Code",
                "detected": True,
                "path": shutil.which("claude"),
                "version": result.stdout.strip(),
                "multi_agent": True
            })
    except Exception:
        pass

    # Check Gemini CLI
    try:
        result = subprocess.run(
            ["gemini-cli", "--version"],
            capture_output=True,
            text=True,
            timeout=5
        )
        if result.returncode == 0:
            tools.append({
                "id": "gemini_cli",
                "name": "Gemini CLI",
                "detected": True,
                "path": shutil.which("gemini-cli"),
                "version": result.stdout.strip(),
                "multi_agent": True
            })
    except Exception:
        pass

    # Check Cursor
    cursor_paths = [
        "cursor",  # Linux/Mac
        "C:\\Users\\{user}\\AppData\\Local\\Programs\\cursor\\Cursor.exe"  # Windows
    ]
    for cursor_path in cursor_paths:
        if shutil.which(cursor_path) or Path(cursor_path).exists():
            tools.append({
                "id": "cursor",
                "name": "Cursor",
                "detected": True,
                "path": cursor_path,
                "multi_agent": True
            })
            break

    # Check Aider
    try:
        result = subprocess.run(
            ["aider", "--version"],
            capture_output=True,
            text=True,
            timeout=5
        )
        if result.returncode == 0:
            tools.append({
                "id": "aider",
                "name": "Aider",
                "detected": True,
                "path": shutil.which("aider"),
                "version": result.stdout.strip(),
                "multi_agent": False
            })
    except Exception:
        pass

    # Check Codex
    try:
        result = subprocess.run(
            ["codex", "--version"],
            capture_output=True,
            text=True,
            timeout=5
        )
        if result.returncode == 0:
            tools.append({
                "id": "codex",
                "name": "Codex CLI",
                "detected": True,
                "path": shutil.which("codex"),
                "version": result.stdout.strip(),
                "multi_agent": False
            })
    except Exception:
        pass

    return {"tools": tools}


@router.post("/install-agents")
async def install_agents(request: Dict) -> Dict:
    """
    Install agent templates for selected tool.
    """
    tool = request.get("tool")
    target_path = request.get("path", "~/.claude/agents")

    # Expand user path
    target_path = Path(target_path).expanduser()
    target_path.mkdir(parents=True, exist_ok=True)

    # Source agent templates
    source_path = Path("claude_agents/")

    installed = []
    errors = []

    for agent_file in source_path.glob("giljo-*.md"):
        try:
            dest = target_path / agent_file.name
            shutil.copy(agent_file, dest)
            installed.append(agent_file.name)
        except Exception as e:
            errors.append({"file": agent_file.name, "error": str(e)})

    return {
        "success": len(errors) == 0,
        "installed": installed,
        "errors": errors,
        "count": len(installed)
    }


@router.post("/validate-tool")
async def validate_tool(request: Dict) -> Dict:
    """
    Validate that tool is accessible and working.
    """
    tool = request.get("tool")

    validation_commands = {
        "claude_code": ["claude", "code", "--version"],
        "gemini_cli": ["gemini-cli", "--version"],
        "aider": ["aider", "--version"],
        "codex": ["codex", "--version"]
    }

    command = validation_commands.get(tool)
    if not command:
        return {
            "success": False,
            "message": f"Unknown tool: {tool}"
        }

    try:
        result = subprocess.run(
            command,
            capture_output=True,
            text=True,
            timeout=5
        )

        if result.returncode == 0:
            return {
                "success": True,
                "message": f"{tool} is accessible (version: {result.stdout.strip()})"
            }
        else:
            return {
                "success": False,
                "message": f"{tool} command failed: {result.stderr}"
            }
    except FileNotFoundError:
        return {
            "success": False,
            "message": f"{tool} not found in PATH"
        }
    except Exception as e:
        return {
            "success": False,
            "message": f"Validation error: {str(e)}"
        }


@router.get("/verify-agents")
async def verify_agents() -> Dict:
    """
    Verify agent templates are installed.
    """
    agent_path = Path.home() / ".claude" / "agents"

    expected_agents = [
        "giljo-orchestrator.md",
        "giljo-database-expert.md",
        "giljo-backend-dev.md",
        "giljo-tester.md",
        "giljo-security-auditor.md",
        "giljo-researcher.md",
        "giljo-architect.md",
        "giljo-documenter.md"
    ]

    installed = []
    for agent_name in expected_agents:
        if (agent_path / agent_name).exists():
            installed.append(agent_name)

    return {
        "all_installed": len(installed) == len(expected_agents),
        "installed_count": len(installed),
        "total_count": len(expected_agents),
        "missing": list(set(expected_agents) - set(installed))
    }
```

### User Profile Storage

**File:** `src/giljo_mcp/models.py` (additions)

```python
class UserProfile(Base):
    """
    User-specific configuration and preferences.
    """
    __tablename__ = "user_profiles"

    id = Column(String(36), primary_key=True, default=generate_uuid)
    user_id = Column(String(36), ForeignKey("users.id"), nullable=False)

    # Tool preferences
    preferred_tool = Column(String(50), nullable=True)  # claude_code, gemini_cli, etc.
    tool_config = Column(JSON, default=dict)

    # Setup status
    setup_completed = Column(Boolean, default=False)
    setup_completed_at = Column(DateTime(timezone=True), nullable=True)

    # Wizard state (in case user exits mid-wizard)
    wizard_step = Column(Integer, default=0)
    wizard_data = Column(JSON, default=dict)

    created_at = Column(DateTime(timezone=True), server_default=func.now())
    updated_at = Column(DateTime(timezone=True), onupdate=func.now())

    # Relationships
    user = relationship("User", back_populates="profile")
```

---

## Settings UI (Re-run Wizard)

**File:** `frontend/src/views/SettingsView.vue`

```vue
<template>
  <v-container>
    <v-row>
      <v-col cols="12">
        <v-card>
          <v-card-title>AI Tool Configuration</v-card-title>

          <v-card-text>
            <v-list>
              <v-list-item>
                <v-list-item-title>Current Tool</v-list-item-title>
                <v-list-item-subtitle>
                  {{ profile.preferred_tool || 'Not configured' }}
                </v-list-item-subtitle>

                <template v-slot:append>
                  <v-btn
                    color="primary"
                    variant="outlined"
                    @click="showWizard = true"
                  >
                    Change Tool
                  </v-btn>
                </template>
              </v-list-item>

              <v-list-item v-if="profile.tool_config">
                <v-list-item-title>Agent Templates</v-list-item-title>
                <v-list-item-subtitle>
                  {{ profile.tool_config.templates_installed ? 'Installed' : 'Not installed' }}
                </v-list-item-subtitle>

                <template v-slot:append>
                  <v-btn
                    variant="outlined"
                    @click="reinstallAgents"
                  >
                    Reinstall
                  </v-btn>
                </template>
              </v-list-item>
            </v-list>
          </v-card-text>
        </v-card>
      </v-col>
    </v-row>

    <!-- Wizard Dialog -->
    <v-dialog
      v-model="showWizard"
      fullscreen
      persistent
    >
      <FirstRunWizard
        @complete="onWizardComplete"
        @cancel="showWizard = false"
      />
    </v-dialog>
  </v-container>
</template>
```

---

## Summary

### ✅ Your Architecture is CORRECT

**Separation of Concerns:**
- Installation = System setup (fast, scriptable)
- First-run wizard = User configuration (interactive, GUI)

**Multi-User Support:**
- Each user gets own tool preference (stored in user_profile)
- Server mode: User A uses Claude Code, User B uses Aider

**Flexibility:**
- Change tools without reinstalling
- Re-run wizard anytime in Settings
- Support multiple tools per user (advanced)

### 🎯 Recommended Implementation Order

1. **Phase 1**: Update installer to skip tool questions
2. **Phase 2**: Create UserProfile model with tool preferences
3. **Phase 3**: Build first-run wizard (Vue components)
4. **Phase 4**: Implement tool detection backend
5. **Phase 5**: Add agent template installation
6. **Phase 6**: Settings page for re-running wizard

### 💡 This is NOT Complicated - It's SMART

You've designed:
- Clean installation experience
- Multi-user friendly architecture
- Tool-agnostic orchestration platform
- Flexibility to adapt as tools evolve

**This is production-grade architecture.** Ship it! 🚀
