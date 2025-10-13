# HANDOVER 0008 - AI-Agnostic Integration Implementation

**Handover ID**: 0008  
**Parent**: 0007  
**Created**: 2025-10-13  
**Status**: ACTIVE  
**Type**: BUILD  
**Priority**: CRITICAL  

## Problem Statement

**Current State**: GiljoAI MCP only integrates with Claude Code CLI, limiting adoption.  
**Vision**: Universal AI tool support - Claude, CODEX, Gemini CLI with unified protocol.  
**Gap**: **COMPLETE MISSING IMPLEMENTATION** - no CODEX/Gemini support found in codebase.

## Technical Analysis

### Evidence of Missing Implementation
- **Search Results**: Zero references to "CODEX" or "Gemini" in `src/**/*.py`
- **Partial Infrastructure**: `preferred_tool` field exists in `models.py:579` but unused
- **Claude-Only**: All current integration code is Claude Code specific

### Existing Foundation to Build Upon
```python
# From src/giljo_mcp/models.py:579
preferred_tool = Column(String(50), default="claude")  # Ready for expansion
```

```python
# From src/giljo_mcp/tools/claude_code_integration.py:40-51
CLAUDE_CODE_AGENT_TYPES = {
    "database": "database-expert",
    "backend": "tdd-implementor", 
    # ... existing mappings
}
```

## Implementation Plan

### Phase 1: Universal Agent Protocol Design

**Create**: `src/giljo_mcp/ai_tools/universal_protocol.py`

```python
from abc import ABC, abstractmethod
from typing import Dict, List, Optional, Any
from enum import Enum

class AIToolCapability(Enum):
    SUB_AGENTS = "sub_agents"           # Modern tools with sub-agent spawn
    MANUAL_ORCHESTRATION = "manual"     # Copy-paste workflow
    CONTEXT_OPTIMIZATION = "context"    # Token optimization features

class AITool(ABC):
    """Abstract base class for AI tool integrations"""
    
    @abstractmethod
    def get_capabilities(self) -> List[AIToolCapability]:
        pass
    
    @abstractmethod 
    def spawn_agent(self, agent_type: str, mission: str) -> Dict:
        pass
        
    @abstractmethod
    def generate_orchestration_prompt(self, project_data: Dict) -> str:
        pass

class ClaudeCodeTool(AITool):
    """Claude Code CLI integration with sub-agents"""
    
    def get_capabilities(self) -> List[AIToolCapability]:
        return [
            AIToolCapability.SUB_AGENTS,
            AIToolCapability.CONTEXT_OPTIMIZATION
        ]
    
    def spawn_agent(self, agent_type: str, mission: str) -> Dict:
        # Existing claude_code_integration.py logic
        pass

class CodexTool(AITool):
    """CODEX integration - manual orchestration"""
    
    def get_capabilities(self) -> List[AIToolCapability]:
        return [AIToolCapability.MANUAL_ORCHESTRATION]
    
    def spawn_agent(self, agent_type: str, mission: str) -> Dict:
        return {
            "type": "manual",
            "instructions": self._generate_copy_paste_instructions(agent_type, mission),
            "tracking_id": f"codex_{uuid4()}"
        }

class GeminiTool(AITool):
    """Gemini CLI integration - manual orchestration"""
    
    def get_capabilities(self) -> List[AIToolCapability]:
        return [AIToolCapability.MANUAL_ORCHESTRATION] 
```

### Phase 2: Tool Detection & Registry

**Create**: `src/giljo_mcp/ai_tools/tool_registry.py`

```python
class AIToolRegistry:
    """Registry for available AI tools with runtime detection"""
    
    def __init__(self):
        self.tools = {}
        self._detect_available_tools()
    
    def _detect_available_tools(self):
        """Detect which AI tools are available on system"""
        
        # Claude Code detection
        if self._is_claude_available():
            self.tools["claude"] = ClaudeCodeTool()
            
        # CODEX detection  
        if self._is_codex_available():
            self.tools["codex"] = CodexTool()
            
        # Gemini detection
        if self._is_gemini_available():
            self.tools["gemini"] = GeminiTool()
    
    def get_preferred_tool(self, tenant_key: str) -> Optional[AITool]:
        """Get user's preferred AI tool or best available"""
        # Check tenant preferences from database
        # Fallback to best available capability
        pass
        
    def get_tool_by_name(self, name: str) -> Optional[AITool]:
        return self.tools.get(name)
```

### Phase 3: Dual Strategy Orchestration

**Modify**: `src/giljo_mcp/orchestrator.py` 

```python
class ProjectOrchestrator:
    def __init__(self, db_manager):
        self.db_manager = db_manager
        self.tool_registry = AIToolRegistry()  # NEW
        
    async def spawn_agent(self, agent_role: str, mission: str, tenant_key: str):
        """Enhanced agent spawning with AI tool selection"""
        
        # Get preferred AI tool for tenant
        ai_tool = self.tool_registry.get_preferred_tool(tenant_key)
        
        if not ai_tool:
            return {"error": "No AI tools available"}
            
        capabilities = ai_tool.get_capabilities()
        
        if AIToolCapability.SUB_AGENTS in capabilities:
            # Modern sub-agent approach  
            return await self._spawn_sub_agent(ai_tool, agent_role, mission)
        else:
            # Manual orchestration approach
            return await self._create_manual_instructions(ai_tool, agent_role, mission)
    
    async def _spawn_sub_agent(self, ai_tool: AITool, role: str, mission: str):
        """Claude Code style sub-agent spawning"""
        result = ai_tool.spawn_agent(role, mission)
        
        # Store agent spawn request in database
        await self._track_agent_spawn(result, "sub_agent")
        return result
        
    async def _create_manual_instructions(self, ai_tool: AITool, role: str, mission: str):
        """Manual copy-paste workflow"""
        result = ai_tool.spawn_agent(role, mission)
        
        # Store manual instructions in database
        await self._track_agent_spawn(result, "manual")
        return result
```

### Phase 4: CODEX-Specific Implementation

**Create**: `src/giljo_mcp/ai_tools/codex_integration.py`

```python
class CodexTool(AITool):
    """CODEX CLI integration with manual orchestration"""
    
    CODEX_AGENT_ROLES = {
        "database": "Database Specialist",
        "backend": "Backend Developer", 
        "frontend": "Frontend Developer",
        "tester": "QA Engineer",
        # ... complete mapping
    }
    
    def generate_orchestration_prompt(self, project_data: Dict) -> str:
        """Generate CODEX-specific orchestration prompt"""
        
        prompt = f"""# CODEX Multi-Agent Project: {project_data['name']}

## Project Mission
{project_data['mission']}

## Your Role: Project Orchestrator
You are coordinating multiple specialist agents to complete this project. 

## Available Specialists
"""
        
        for agent in project_data['agents']:
            role = self.CODEX_AGENT_ROLES.get(agent['role'], agent['role'])
            prompt += f"""
### {role}
**Instructions**: {agent['mission']}
**Context Budget**: {agent.get('context_budget', 50000)} tokens
**Status**: Ready for assignment

To activate this specialist:
1. Copy the mission above
2. Start new CODEX session 
3. Paste: "You are a {role} working on {project_data['name']}. {agent['mission']}"
4. Report back with: "Agent {agent['id']} active and ready"
"""

        prompt += """

## Coordination Protocol
1. Activate each specialist in separate CODEX sessions
2. Coordinate their work through this orchestration session
3. Use /mcp-giljo tools to update agent status and communicate results
4. Handle handoffs when agents reach context limits

Begin orchestration by activating the first required specialist.
"""
        
        return prompt
```

### Phase 5: Gemini-Specific Implementation

**Create**: `src/giljo_mcp/ai_tools/gemini_integration.py`

Similar structure to CODEX but with Gemini-specific prompt patterns and capabilities.

### Phase 6: MCP Tools Extension

**Modify**: `src/giljo_mcp/tools/agent.py`

```python
@mcp.tool()
async def set_preferred_ai_tool(tenant_key: str, tool_name: str) -> Dict:
    """Set preferred AI tool for tenant"""
    
    registry = AIToolRegistry()
    if tool_name not in registry.tools:
        return {"error": f"Tool {tool_name} not available"}
        
    # Update tenant preferences in database
    async with db_manager.get_session_async() as session:
        # Update tenant AI tool preference
        pass
        
    return {"success": True, "preferred_tool": tool_name}

@mcp.tool() 
async def list_available_ai_tools() -> Dict:
    """List available AI tools and their capabilities"""
    
    registry = AIToolRegistry()
    tools_info = {}
    
    for name, tool in registry.tools.items():
        tools_info[name] = {
            "capabilities": [cap.value for cap in tool.get_capabilities()],
            "available": True
        }
        
    return {"tools": tools_info}
```

## Testing Strategy

### Unit Tests
```python
# tests/test_ai_tools/test_universal_protocol.py
def test_claude_code_tool_capabilities():
    tool = ClaudeCodeTool()
    caps = tool.get_capabilities()
    assert AIToolCapability.SUB_AGENTS in caps

def test_codex_tool_manual_instructions():
    tool = CodexTool()
    result = tool.spawn_agent("database", "Design user tables")
    assert result["type"] == "manual"
    assert "instructions" in result
```

### Integration Tests
```python
# tests/integration/test_ai_tool_orchestration.py
async def test_multi_tool_project():
    """Test project with mixed AI tool usage"""
    
    orchestrator = ProjectOrchestrator(db_manager)
    
    # Simulate Claude Code available for some agents
    # Simulate CODEX for others
    # Verify coordination works across tools
```

## Migration Strategy

### Phase 1: Backward Compatibility
- Keep existing Claude Code integration working
- Add new universal protocol alongside

### Phase 2: Gradual Migration  
- Update orchestrator to use new protocol
- Maintain fallbacks to old system

### Phase 3: Full Integration
- Remove deprecated Claude-only code
- Complete testing across all AI tools

## Success Metrics

1. **Multi-Tool Support**: Successfully spawn agents in Claude, CODEX, Gemini
2. **Graceful Degradation**: System works with any single AI tool available
3. **Protocol Consistency**: Same project data works across all tools
4. **User Experience**: Seamless switching between AI tools per tenant preference

## Risks & Mitigations

**Risk**: CODEX/Gemini CLI interfaces may change  
**Mitigation**: Abstract interface layer, adapter pattern

**Risk**: Manual orchestration less efficient than sub-agents  
**Mitigation**: Enhanced manual workflow with better tracking and coordination

**Risk**: Increased complexity  
**Mitigation**: Thorough testing, clear documentation, gradual rollout

## Dependencies

- Access to CODEX and Gemini CLI tools for testing
- Updated database schema for AI tool preferences
- Integration testing environment

## Estimated Timeline

- **Phase 1-2**: 1 week (Protocol + Registry)  
- **Phase 3**: 1 week (Orchestration Integration)
- **Phase 4-5**: 1 week (CODEX + Gemini Implementation)
- **Phase 6**: 3 days (MCP Tools Extension)
- **Testing**: 2 days

**Total**: ~3 weeks

---

**Next Actions**:
1. Create universal protocol base classes
2. Implement tool detection logic
3. Test with available AI tools
4. Iterate based on real-world usage

This implementation delivers the vision's AI-agnostic promise while maintaining backward compatibility and providing graceful degradation.