# Handover 0016-D: Unified Dashboard Experience (Phase 4)

**Date:** 2025-10-14 (New)
**From Agent:** UX Designer + Frontend Integrator
**To Agent:** Frontend Developer + UX Designer
**Priority:** Medium
**Estimated Complexity:** 3-4 hours
**Status:** Not Started
**Depends On:** Handover 0016-B (Universal) + 0016-C (Plugin Marketplace)
**Blocks:** None

---

## Task Summary

**Create unified dashboard experience** that intelligently presents the best MCP configuration option for each user, tracks multi-tool adoption, and provides comprehensive status monitoring across all three configuration tiers.

**Strategic Goal:** Seamless user experience that automatically guides users to their optimal configuration method while providing visibility into the entire AI tool ecosystem.

**Expected Outcome:**
- Smart configuration recommendations based on user context
- Real-time status monitoring across all AI tools
- Adoption analytics and usage insights
- Unified troubleshooting and support

---

## Context and Integration Strategy

### The Complete Three-Tier System

After Phases 1-3, users have three distinct configuration paths:

**🥇 Tier 1: Claude Code Plugin** (30 seconds)
```
/plugin marketplace add http://server/api/claude-plugins
/plugin install mcp-connector@giljo-server
/connect [api-key]
```

**🥈 Tier 2: Universal Agent-Driven** (60-90 seconds)
```
"Visit http://server/setup/ai-tools and configure yourself"
AI reads instructions → Self-configures → User provides API key
```

**🥉 Tier 3: Manual Configuration** (90+ seconds)
```
Settings → API & Integrations → Copy JSON → Paste → Restart
```

### Dashboard's Role: Intelligent Routing

**Smart Detection & Recommendations:**
- Detect if user has Claude Code (recommend Tier 1)
- Detect if user has other AI tools (recommend Tier 2)
- Always provide Tier 3 as fallback
- Track adoption across all tiers
- Monitor active connections from all methods

---

## Technical Architecture

### Multi-Tier Status Detection System

**Enhanced Status Tracking:**
```python
# Extend existing status API to track all configuration methods
{
  "status": "active",  # Overall MCP status
  "methods": {
    "plugin_marketplace": {
      "available": true,
      "installations": 15,
      "last_used": "2025-10-14T10:30:00Z"
    },
    "agent_driven": {
      "available": true,
      "completions": 42,
      "success_rate": 0.89
    },
    "manual_config": {
      "available": true,
      "attempts": 8,
      "success_rate": 0.75
    }
  },
  "connected_tools": [
    {
      "tool": "claude-code",
      "method": "plugin_marketplace",
      "status": "active",
      "last_seen": "2025-10-14T10:28:00Z"
    },
    {
      "tool": "codex",
      "method": "agent_driven", 
      "status": "inactive",
      "last_seen": "2025-10-13T15:20:00Z"
    }
  ]
}
```

### Smart Recommendation Engine

**User Context Detection:**
```javascript
// Detect user's optimal configuration method
async function detectOptimalMethod() {
  const userAgent = navigator.userAgent
  const availableEndpoints = await checkEndpointAvailability()
  const userHistory = await getUserConfigHistory()
  
  if (userAgent.includes('Claude') && availableEndpoints.pluginMarketplace) {
    return 'plugin_marketplace'
  } else if (availableEndpoints.agentDriven) {
    return 'agent_driven'
  } else {
    return 'manual_config'
  }
}
```

---

## Implementation Plan

### Phase 4A: Enhanced Backend Analytics (1.5 hours)

#### 4A.1 Multi-Method Status Tracking

**Update:** `api/endpoints/mcp_tools.py`

Add comprehensive analytics tracking:

```python
from sqlalchemy import func, case
from src.giljo_mcp.models import User, APIKey, MCPConnection  # New model

# New model for tracking MCP connections
class MCPConnection(Base):
    __tablename__ = "mcp_connections"
    
    id = Column(Integer, primary_key=True)
    user_id = Column(Integer, ForeignKey("users.id"), nullable=False)
    ai_tool = Column(String, nullable=False)  # claude-code, codex, gemini, etc
    connection_method = Column(String, nullable=False)  # plugin, agent, manual
    configured_at = Column(DateTime, nullable=False, default=datetime.utcnow)
    last_used = Column(DateTime, nullable=True)
    status = Column(String, nullable=False, default="active")  # active, inactive, error
    
    user = relationship("User", back_populates="mcp_connections")

@router.get("/analytics")
async def get_mcp_analytics(
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db)
) -> dict:
    """
    Get comprehensive MCP configuration analytics.
    Includes method adoption, success rates, and tool usage.
    """
    
    # Method adoption stats
    method_stats = db.execute(
        select(
            MCPConnection.connection_method,
            func.count(MCPConnection.id).label('total'),
            func.count(case((MCPConnection.status == 'active', 1))).label('active'),
            func.avg(case((MCPConnection.last_used.isnot(None), 1.0), else_=0.0)).label('success_rate')
        )
        .group_by(MCPConnection.connection_method)
    ).fetchall()
    
    # AI tool distribution
    tool_stats = db.execute(
        select(
            MCPConnection.ai_tool,
            func.count(MCPConnection.id).label('count'),
            func.max(MCPConnection.last_used).label('last_active')
        )
        .where(MCPConnection.status == 'active')
        .group_by(MCPConnection.ai_tool)
    ).fetchall()
    
    # User's connections
    user_connections = db.execute(
        select(MCPConnection)
        .where(MCPConnection.user_id == current_user.id)
        .order_by(MCPConnection.configured_at.desc())
    ).scalars().all()
    
    return {
        "method_adoption": {
            row.connection_method: {
                "total_users": row.total,
                "active_users": row.active,
                "success_rate": float(row.success_rate)
            }
            for row in method_stats
        },
        "ai_tool_distribution": {
            row.ai_tool: {
                "active_connections": row.count,
                "last_active": row.last_active.isoformat() if row.last_active else None
            }
            for row in tool_stats
        },
        "user_connections": [
            {
                "ai_tool": conn.ai_tool,
                "method": conn.connection_method,
                "status": conn.status,
                "configured_at": conn.configured_at.isoformat(),
                "last_used": conn.last_used.isoformat() if conn.last_used else None
            }
            for conn in user_connections
        ],
        "recommendations": generate_user_recommendations(current_user, user_connections)
    }

def generate_user_recommendations(user: User, connections: list) -> dict:
    """Generate personalized configuration recommendations"""
    
    has_claude_code = any(conn.ai_tool == 'claude-code' for conn in connections)
    has_active_connections = any(conn.status == 'active' for conn in connections)
    
    if not connections:
        # New user - recommend based on detection
        return {
            "primary": "plugin_marketplace",
            "fallback": "agent_driven",
            "message": "New user - recommend starting with Claude Code plugin for best experience"
        }
    elif has_claude_code and not has_active_connections:
        return {
            "primary": "plugin_marketplace",
            "fallback": "manual_config",
            "message": "Claude Code detected but not active - try plugin reconnection"
        }
    elif not has_active_connections:
        return {
            "primary": "agent_driven",
            "fallback": "manual_config", 
            "message": "Recommend agent-driven setup for your AI tool"
        }
    else:
        return {
            "primary": "maintenance",
            "message": "All connections active - focus on usage optimization"
        }

@router.post("/track-connection")
async def track_mcp_connection(
    ai_tool: str,
    connection_method: str,
    status: str = "active",
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db)
) -> dict:
    """Track a new MCP connection configuration"""
    
    # Check if connection already exists
    existing = db.execute(
        select(MCPConnection)
        .where(MCPConnection.user_id == current_user.id)
        .where(MCPConnection.ai_tool == ai_tool)
        .where(MCPConnection.connection_method == connection_method)
    ).scalar_one_or_none()
    
    if existing:
        # Update existing connection
        existing.status = status
        existing.last_used = datetime.utcnow() if status == 'active' else existing.last_used
    else:
        # Create new connection record
        connection = MCPConnection(
            user_id=current_user.id,
            ai_tool=ai_tool,
            connection_method=connection_method,
            status=status
        )
        db.add(connection)
    
    db.commit()
    
    return {"success": True, "connection_tracked": True}
```

---

#### 4A.2 Smart Endpoint Availability Detection

**New:** `api/endpoints/system_status.py`

```python
"""
System Status and Capability Detection
Provides real-time status of all MCP configuration methods
"""
from fastapi import APIRouter, Request
from typing import Dict, Any
import asyncio
import aiohttp

router = APIRouter(prefix="/api/system", tags=["system-status"])

@router.get("/capabilities")
async def get_system_capabilities(request: Request) -> Dict[str, Any]:
    """
    Detect which MCP configuration methods are available.
    Used by frontend to show appropriate options.
    """
    
    server_url = f"{request.url.scheme}://{request.url.netloc}"
    
    capabilities = {
        "plugin_marketplace": await check_plugin_marketplace(server_url),
        "agent_driven": await check_agent_driven_setup(server_url),
        "manual_config": True,  # Always available
        "server_info": {
            "url": server_url,
            "version": "3.0.0",
            "tools_available": 47
        }
    }
    
    return capabilities

async def check_plugin_marketplace(server_url: str) -> Dict[str, Any]:
    """Check if Claude Code plugin marketplace is functional"""
    try:
        async with aiohttp.ClientSession() as session:
            async with session.get(f"{server_url}/api/claude-plugins", timeout=5) as response:
                if response.status == 200:
                    data = await response.json()
                    return {
                        "available": True,
                        "plugins_count": len(data.get("plugins", [])),
                        "marketplace_url": f"{server_url}/api/claude-plugins"
                    }
    except Exception:
        pass
    
    return {"available": False, "error": "Plugin marketplace not accessible"}

async def check_agent_driven_setup(server_url: str) -> Dict[str, Any]:
    """Check if agent-driven setup endpoint is functional"""
    try:
        async with aiohttp.ClientSession() as session:
            async with session.get(f"{server_url}/setup/ai-tools", timeout=5) as response:
                if response.status == 200:
                    content = await response.text()
                    return {
                        "available": True,
                        "supports_tools": ["claude-code", "codex", "gemini", "cursor", "universal"],
                        "setup_url": f"{server_url}/setup/ai-tools"
                    }
    except Exception:
        pass
    
    return {"available": False, "error": "Agent setup endpoint not accessible"}
```

---

### Phase 4B: Unified Dashboard Frontend (2 hours)

#### 4B.1 Smart Configuration Selector Component

**New:** `frontend/src/components/dashboard/SmartMcpConfigurator.vue`

```vue
<template>
  <v-card class="smart-configurator">
    <v-card-title class="d-flex align-center">
      <v-icon start size="large" color="primary">mdi-connection</v-icon>
      <div>
        <div class="text-h5">AI Tool Integration</div>
        <div class="text-subtitle-1 text-medium-emphasis">
          {{ statusSummary }}
        </div>
      </div>
      <v-spacer />
      <v-chip 
        :color="overallStatusColor" 
        variant="elevated"
        prepend-icon="mdi-circle"
      >
        {{ overallStatus }}
      </v-chip>
    </v-card-title>

    <!-- Smart Recommendation Banner -->
    <v-card-text v-if="recommendation && !hasActiveConnections">
      <v-alert 
        :type="recommendation.primary === 'plugin_marketplace' ? 'success' : 'info'"
        variant="tonal"
        prominent
      >
        <v-alert-title class="d-flex align-center">
          <v-icon start>{{ recommendationIcon }}</v-icon>
          Recommended for You
        </v-alert-title>
        
        <p class="mt-2 mb-3">{{ recommendation.message }}</p>
        
        <div class="d-flex gap-3">
          <v-btn
            :color="recommendation.primary === 'plugin_marketplace' ? 'success' : 'primary'"
            @click="navigateToMethod(recommendation.primary)"
            prepend-icon="mdi-rocket-launch"
          >
            {{ getMethodDisplayName(recommendation.primary) }}
          </v-btn>
          
          <v-btn
            variant="outlined"
            @click="navigateToMethod(recommendation.fallback)"
          >
            {{ getMethodDisplayName(recommendation.fallback) }}
          </v-btn>
        </div>
      </v-alert>
    </v-card-text>

    <!-- Active Connections Overview -->
    <v-card-text v-if="hasActiveConnections">
      <v-row>
        <!-- Connected AI Tools -->
        <v-col cols="12" md="6">
          <v-card variant="outlined" class="h-100">
            <v-card-title class="text-h6">
              <v-icon start>mdi-check-circle</v-icon>
              Connected Tools
            </v-card-title>
            <v-card-text>
              <v-list density="compact">
                <v-list-item 
                  v-for="tool in activeTools" 
                  :key="tool.ai_tool"
                  :prepend-icon="getToolIcon(tool.ai_tool)"
                >
                  <v-list-item-title>{{ getToolDisplayName(tool.ai_tool) }}</v-list-item-title>
                  <v-list-item-subtitle>
                    via {{ getMethodDisplayName(tool.method) }} • 
                    {{ formatDistanceToNow(new Date(tool.last_used || tool.configured_at)) }} ago
                  </v-list-item-subtitle>
                  <template v-slot:append>
                    <v-chip 
                      :color="tool.status === 'active' ? 'success' : 'warning'"
                      size="small"
                    >
                      {{ tool.status }}
                    </v-chip>
                  </template>
                </v-list-item>
              </v-list>
            </v-card-text>
          </v-card>
        </v-col>

        <!-- Configuration Methods Stats -->
        <v-col cols="12" md="6">
          <v-card variant="outlined" class="h-100">
            <v-card-title class="text-h6">
              <v-icon start>mdi-chart-arc</v-icon>
              Method Usage
            </v-card-title>
            <v-card-text>
              <div v-for="(stats, method) in methodStats" :key="method" class="mb-3">
                <div class="d-flex justify-space-between align-center mb-1">
                  <span class="text-body-2">{{ getMethodDisplayName(method) }}</span>
                  <span class="text-caption">{{ stats.active_users }}/{{ stats.total_users }}</span>
                </div>
                <v-progress-linear
                  :model-value="(stats.active_users / stats.total_users) * 100"
                  :color="getMethodColor(method)"
                  height="8"
                  rounded
                />
                <div class="text-caption text-medium-emphasis mt-1">
                  {{ Math.round(stats.success_rate * 100) }}% success rate
                </div>
              </div>
            </v-card-text>
          </v-card>
        </v-col>
      </v-row>
    </v-card-text>

    <!-- Configuration Options -->
    <v-card-text>
      <v-row>
        <!-- Plugin Marketplace Option -->
        <v-col cols="12" md="4">
          <v-card 
            :variant="capabilities.plugin_marketplace?.available ? 'outlined' : 'tonal'"
            :color="capabilities.plugin_marketplace?.available ? 'primary' : 'surface-variant'"
            class="h-100 configuration-option"
            @click="navigateToMethod('plugin_marketplace')"
            :disabled="!capabilities.plugin_marketplace?.available"
          >
            <v-card-title class="text-center">
              <v-icon 
                size="48" 
                :color="capabilities.plugin_marketplace?.available ? 'primary' : 'disabled'"
                class="mb-2"
              >
                mdi-puzzle
              </v-icon>
              <div class="text-h6">Claude Code Plugin</div>
            </v-card-title>
            <v-card-text class="text-center">
              <div class="text-body-2 mb-3">
                One-click installation for Claude Code users
              </div>
              <v-chip 
                :color="capabilities.plugin_marketplace?.available ? 'success' : 'error'"
                size="small"
              >
                {{ capabilities.plugin_marketplace?.available ? 'Available' : 'Unavailable' }}
              </v-chip>
              <div class="text-caption mt-2">
                ~30 seconds setup time
              </div>
            </v-card-text>
          </v-card>
        </v-col>

        <!-- Agent-Driven Option -->
        <v-col cols="12" md="4">
          <v-card 
            :variant="capabilities.agent_driven?.available ? 'outlined' : 'tonal'"
            :color="capabilities.agent_driven?.available ? 'secondary' : 'surface-variant'"
            class="h-100 configuration-option"
            @click="navigateToMethod('agent_driven')"
            :disabled="!capabilities.agent_driven?.available"
          >
            <v-card-title class="text-center">
              <v-icon 
                size="48" 
                :color="capabilities.agent_driven?.available ? 'secondary' : 'disabled'"
                class="mb-2"
              >
                mdi-robot-excited
              </v-icon>
              <div class="text-h6">AI Self-Configuration</div>
            </v-card-title>
            <v-card-text class="text-center">
              <div class="text-body-2 mb-3">
                Universal method for any AI coding tool
              </div>
              <v-chip 
                :color="capabilities.agent_driven?.available ? 'success' : 'error'"
                size="small"
              >
                {{ capabilities.agent_driven?.available ? 'Available' : 'Unavailable' }}
              </v-chip>
              <div class="text-caption mt-2">
                ~60 seconds setup time
              </div>
            </v-card-text>
          </v-card>
        </v-col>

        <!-- Manual Configuration Option -->
        <v-col cols="12" md="4">
          <v-card 
            variant="outlined"
            color="surface"
            class="h-100 configuration-option"
            @click="navigateToMethod('manual_config')"
          >
            <v-card-title class="text-center">
              <v-icon size="48" color="surface" class="mb-2">mdi-cog</v-icon>
              <div class="text-h6">Manual Setup</div>
            </v-card-title>
            <v-card-text class="text-center">
              <div class="text-body-2 mb-3">
                Traditional copy-paste configuration
              </div>
              <v-chip color="warning" size="small">Always Available</v-chip>
              <div class="text-caption mt-2">
                ~90+ seconds setup time
              </div>
            </v-card-text>
          </v-card>
        </v-col>
      </v-row>
    </v-card-text>

    <!-- Quick Actions -->
    <v-card-actions class="justify-center">
      <v-btn
        variant="outlined"
        prepend-icon="mdi-help-circle"
        @click="showTroubleshooting = true"
      >
        Troubleshooting
      </v-btn>
      
      <v-btn
        variant="outlined"
        prepend-icon="mdi-refresh"
        @click="refreshData"
        :loading="loading"
      >
        Refresh Status
      </v-btn>
      
      <v-btn
        variant="outlined"
        prepend-icon="mdi-chart-line"
        @click="$router.push('/analytics/mcp')"
      >
        View Analytics
      </v-btn>
    </v-card-actions>

    <!-- Troubleshooting Dialog -->
    <v-dialog v-model="showTroubleshooting" max-width="600">
      <v-card>
        <v-card-title>MCP Troubleshooting</v-card-title>
        <v-card-text>
          <McpTroubleshootingGuide :user-connections="userConnections" />
        </v-card-text>
        <v-card-actions>
          <v-spacer />
          <v-btn @click="showTroubleshooting = false">Close</v-btn>
        </v-card-actions>
      </v-card>
    </v-dialog>
  </v-card>
</template>

<script setup>
import { ref, computed, onMounted } from 'vue'
import { useRouter } from 'vue-router'
import { formatDistanceToNow } from 'date-fns'
import api from '@/services/api'
import McpTroubleshootingGuide from '@/components/mcp/McpTroubleshootingGuide.vue'

const router = useRouter()

// State
const loading = ref(false)
const showTroubleshooting = ref(false)
const analytics = ref(null)
const capabilities = ref({})

// Computed properties
const hasActiveConnections = computed(() => {
  return analytics.value?.user_connections?.some(conn => conn.status === 'active') || false
})

const activeTools = computed(() => {
  return analytics.value?.user_connections?.filter(conn => conn.status === 'active') || []
})

const overallStatus = computed(() => {
  if (!analytics.value) return 'Unknown'
  
  const activeCount = activeTools.value.length
  if (activeCount === 0) return 'Not Connected'
  if (activeCount === 1) return 'Connected'
  return `${activeCount} Tools Connected`
})

const overallStatusColor = computed(() => {
  const activeCount = activeTools.value.length
  if (activeCount === 0) return 'error'
  if (activeCount === 1) return 'success'
  return 'primary'
})

const statusSummary = computed(() => {
  if (!analytics.value) return 'Loading status...'
  
  const totalConnections = analytics.value.user_connections?.length || 0
  const activeCount = activeTools.value.length
  
  if (totalConnections === 0) {
    return 'No AI tools configured yet'
  } else if (activeCount === 0) {
    return `${totalConnections} tool(s) configured but inactive`
  } else {
    return `${activeCount} of ${totalConnections} tools active`
  }
})

const recommendation = computed(() => {
  return analytics.value?.recommendations || null
})

const recommendationIcon = computed(() => {
  if (!recommendation.value) return 'mdi-lightbulb'
  
  const iconMap = {
    plugin_marketplace: 'mdi-puzzle',
    agent_driven: 'mdi-robot-excited',
    manual_config: 'mdi-cog',
    maintenance: 'mdi-wrench'
  }
  
  return iconMap[recommendation.value.primary] || 'mdi-lightbulb'
})

const methodStats = computed(() => {
  return analytics.value?.method_adoption || {}
})

const userConnections = computed(() => {
  return analytics.value?.user_connections || []
})

// Methods
onMounted(async () => {
  await refreshData()
})

async function refreshData() {
  loading.value = true
  try {
    const [analyticsResponse, capabilitiesResponse] = await Promise.all([
      api.get('/api/mcp-tools/analytics'),
      api.get('/api/system/capabilities')
    ])
    
    analytics.value = analyticsResponse.data
    capabilities.value = capabilitiesResponse.data
  } catch (error) {
    console.error('Failed to fetch MCP data:', error)
  } finally {
    loading.value = false
  }
}

function navigateToMethod(method) {
  const routes = {
    plugin_marketplace: '/settings/integrations?method=plugin',
    agent_driven: '/settings/integrations?method=agent',
    manual_config: '/settings/integrations?method=manual'
  }
  
  router.push(routes[method] || '/settings/integrations')
}

function getMethodDisplayName(method) {
  const names = {
    plugin_marketplace: 'Claude Code Plugin',
    agent_driven: 'AI Self-Config',
    manual_config: 'Manual Setup',
    maintenance: 'Maintenance Mode'
  }
  
  return names[method] || method
}

function getMethodColor(method) {
  const colors = {
    plugin_marketplace: 'primary',
    agent_driven: 'secondary',
    manual_config: 'warning'
  }
  
  return colors[method] || 'grey'
}

function getToolDisplayName(tool) {
  const names = {
    'claude-code': 'Claude Code',
    'codex': 'GitHub Codex',
    'gemini': 'Gemini Code Assist',
    'cursor': 'Cursor',
    'continue': 'Continue.dev'
  }
  
  return names[tool] || tool
}

function getToolIcon(tool) {
  const icons = {
    'claude-code': 'mdi-robot',
    'codex': 'mdi-github',
    'gemini': 'mdi-google',
    'cursor': 'mdi-cursor-default',
    'continue': 'mdi-play-circle'
  }
  
  return icons[tool] || 'mdi-robot-outline'
}
</script>

<style scoped>
.configuration-option {
  cursor: pointer;
  transition: all 0.2s ease;
}

.configuration-option:hover:not([disabled]) {
  transform: translateY(-2px);
  box-shadow: 0 4px 12px rgba(0, 0, 0, 0.15);
}

.configuration-option[disabled] {
  opacity: 0.6;
  cursor: not-allowed;
}

.smart-configurator {
  background: linear-gradient(135deg, rgba(var(--v-theme-primary), 0.05) 0%, rgba(var(--v-theme-secondary), 0.05) 100%);
}
</style>
```

---

#### 4B.2 Enhanced Settings Integration View

**Update:** `frontend/src/views/Settings/IntegrationsView.vue`

```vue
<template>
  <v-container>
    <h1 class="text-h4 mb-6">AI Tool Integrations</h1>
    
    <!-- Method selector based on query params -->
    <v-tabs
      v-model="selectedMethod"
      class="mb-6"
      color="primary"
      align-tabs="center"
    >
      <v-tab value="smart">
        <v-icon start>mdi-auto-fix</v-icon>
        Smart Setup
      </v-tab>
      <v-tab value="plugin" :disabled="!capabilities.plugin_marketplace?.available">
        <v-icon start>mdi-puzzle</v-icon>
        Claude Code Plugin
      </v-tab>
      <v-tab value="agent" :disabled="!capabilities.agent_driven?.available">
        <v-icon start>mdi-robot-excited</v-icon>
        AI Self-Config
      </v-tab>
      <v-tab value="manual">
        <v-icon start>mdi-cog</v-icon>
        Manual Setup
      </v-tab>
    </v-tabs>

    <v-window v-model="selectedMethod">
      <!-- Smart Setup Tab -->
      <v-window-item value="smart">
        <SmartMcpConfigurator />
      </v-window-item>

      <!-- Plugin Marketplace Tab -->
      <v-window-item value="plugin">
        <PluginMarketplaceConfig />
      </v-window-item>

      <!-- Agent-Driven Tab -->
      <v-window-item value="agent">
        <AgentDrivenConfig />
      </v-window-item>

      <!-- Manual Configuration Tab -->
      <v-window-item value="manual">
        <McpConfigComponent />
      </v-window-item>
    </v-window>
  </v-container>
</template>

<script setup>
import { ref, computed, onMounted, watch } from 'vue'
import { useRoute, useRouter } from 'vue-router'
import api from '@/services/api'
import SmartMcpConfigurator from '@/components/dashboard/SmartMcpConfigurator.vue'
import PluginMarketplaceConfig from '@/components/mcp/PluginMarketplaceConfig.vue'
import AgentDrivenConfig from '@/components/mcp/AgentDrivenConfig.vue'
import McpConfigComponent from '@/components/mcp/McpConfigComponent.vue'

const route = useRoute()
const router = useRouter()

const selectedMethod = ref('smart')
const capabilities = ref({})

onMounted(async () => {
  // Load system capabilities
  try {
    const response = await api.get('/api/system/capabilities')
    capabilities.value = response.data
  } catch (error) {
    console.error('Failed to load capabilities:', error)
  }

  // Set initial tab based on query param
  const method = route.query.method
  if (method && ['smart', 'plugin', 'agent', 'manual'].includes(method)) {
    selectedMethod.value = method
  }
})

// Update URL when tab changes
watch(selectedMethod, (newMethod) => {
  router.push({ query: { method: newMethod } })
})
</script>
```

---

### Phase 4C: Analytics and Insights (0.5 hours)

#### 4C.1 MCP Analytics Dashboard

**New:** `frontend/src/views/Analytics/McpAnalytics.vue`

```vue
<template>
  <v-container>
    <h1 class="text-h4 mb-6">MCP Integration Analytics</h1>

    <v-row>
      <!-- Method Adoption Chart -->
      <v-col cols="12" md="6">
        <v-card>
          <v-card-title>Configuration Method Adoption</v-card-title>
          <v-card-text>
            <canvas ref="methodChart"></canvas>
          </v-card-text>
        </v-card>
      </v-col>

      <!-- AI Tool Distribution -->
      <v-col cols="12" md="6">
        <v-card>
          <v-card-title>Connected AI Tools</v-card-title>
          <v-card-text>
            <canvas ref="toolChart"></canvas>
          </v-card-text>
        </v-card>
      </v-col>
    </v-row>

    <!-- Success Rate Trends -->
    <v-row>
      <v-col cols="12">
        <v-card>
          <v-card-title>Success Rate Trends</v-card-title>
          <v-card-text>
            <canvas ref="trendsChart"></canvas>
          </v-card-text>
        </v-card>
      </v-col>
    </v-row>
  </v-container>
</template>

<script setup>
import { ref, onMounted } from 'vue'
import Chart from 'chart.js/auto'
import api from '@/services/api'

const methodChart = ref(null)
const toolChart = ref(null)
const trendsChart = ref(null)

onMounted(async () => {
  const analytics = await loadAnalytics()
  
  if (analytics) {
    createMethodChart(analytics.method_adoption)
    createToolChart(analytics.ai_tool_distribution)
    createTrendsChart(analytics)
  }
})

async function loadAnalytics() {
  try {
    const response = await api.get('/api/mcp-tools/analytics')
    return response.data
  } catch (error) {
    console.error('Failed to load analytics:', error)
    return null
  }
}

function createMethodChart(methodData) {
  new Chart(methodChart.value, {
    type: 'doughnut',
    data: {
      labels: Object.keys(methodData).map(method => 
        method.replace('_', ' ').replace(/\b\w/g, l => l.toUpperCase())
      ),
      datasets: [{
        data: Object.values(methodData).map(stats => stats.total_users),
        backgroundColor: [
          '#1976D2', // Primary
          '#7C4DFF', // Secondary  
          '#FF9800', // Warning
        ]
      }]
    },
    options: {
      responsive: true,
      plugins: {
        legend: {
          position: 'bottom'
        }
      }
    }
  })
}

function createToolChart(toolData) {
  new Chart(toolChart.value, {
    type: 'bar',
    data: {
      labels: Object.keys(toolData),
      datasets: [{
        label: 'Active Connections',
        data: Object.values(toolData).map(stats => stats.active_connections),
        backgroundColor: '#4CAF50'
      }]
    },
    options: {
      responsive: true,
      scales: {
        y: {
          beginAtZero: true
        }
      }
    }
  })
}

function createTrendsChart(analytics) {
  // Mock trend data - would come from backend in real implementation
  new Chart(trendsChart.value, {
    type: 'line',
    data: {
      labels: ['Week 1', 'Week 2', 'Week 3', 'Week 4'],
      datasets: [
        {
          label: 'Plugin Marketplace',
          data: [85, 88, 90, 92],
          borderColor: '#1976D2',
          fill: false
        },
        {
          label: 'Agent-Driven',
          data: [78, 82, 85, 89],
          borderColor: '#7C4DFF',
          fill: false
        },
        {
          label: 'Manual Config',
          data: [65, 68, 72, 75],
          borderColor: '#FF9800',
          fill: false
        }
      ]
    },
    options: {
      responsive: true,
      scales: {
        y: {
          beginAtZero: true,
          max: 100,
          title: {
            display: true,
            text: 'Success Rate (%)'
          }
        }
      }
    }
  })
}
</script>
```

---

## Testing Requirements

### Integration Testing

**Test 1: Smart Recommendation Engine**
1. New user visits dashboard → Should recommend plugin marketplace if Claude Code detected
2. User with failed connections → Should recommend troubleshooting
3. User with multiple tools → Should show comprehensive status

**Test 2: Method Navigation**
1. Click "Claude Code Plugin" → Should navigate to plugin setup
2. Click "AI Self-Config" → Should navigate to agent instructions  
3. Click "Manual Setup" → Should navigate to traditional UI

**Test 3: Analytics Dashboard**
1. View method adoption charts → Should show real data
2. View AI tool distribution → Should reflect actual connections
3. Success rate trends → Should show meaningful metrics

### User Experience Testing

**Test 4: Cross-Method Status Consistency**
1. Configure via plugin → Status should update across all views
2. Configure via agent → Should be reflected in analytics
3. Manual configuration → Should be tracked properly

**Test 5: Recommendation Accuracy**
1. Test with different User-Agent strings
2. Verify recommendations match user context
3. Ensure fallback options are always provided

---

## Success Criteria

### Technical Requirements
- [ ] Smart recommendation engine provides contextual guidance
- [ ] Multi-method status tracking works correctly
- [ ] Analytics provide meaningful insights into adoption
- [ ] All three configuration tiers integrate seamlessly
- [ ] Cross-platform compatibility maintained

### User Experience Requirements
- [ ] Dashboard automatically guides users to optimal method
- [ ] Status visibility across all configuration approaches
- [ ] Troubleshooting provides actionable guidance
- [ ] Analytics help understand ecosystem adoption
- [ ] Seamless transitions between different setup methods

### Strategic Goals
- [ ] Increased overall configuration success rate (>90%)
- [ ] Clear analytics on which methods users prefer
- [ ] Foundation for future AI tool integrations
- [ ] Demonstration of GiljoAI's integration sophistication

---

## Dependencies and Future Enhancements

### Dependencies
- ✅ Phase B (Universal agent configuration)
- ✅ Phase C (Plugin marketplace)
- ✅ Chart.js for analytics visualization
- ✅ Vue router for navigation

### Future Enhancements
- **Real-time connection monitoring:** WebSocket status updates
- **Automated health checks:** Periodic connection testing
- **Usage optimization suggestions:** AI-powered recommendations
- **Enterprise features:** Team-wide configuration management
- **Integration marketplace:** Third-party AI tool plugins

---

## Timeline

- **Phase 4A (Analytics Backend):** 1.5 hours
- **Phase 4B (Dashboard Frontend):** 2 hours  
- **Phase 4C (Analytics Views):** 0.5 hours

**Total:** 4 hours for unified dashboard experience

---

**This completes the revolutionary four-phase MCP configuration system, providing users with intelligent guidance, multiple configuration paths, and comprehensive insights into their AI tool ecosystem.**