# Handover 0084: Agent Export Copy-Command Interface

**Date**: 2025-11-02  
**Type**: Feature Implementation  
**Priority**: High  
**Status**: Pending Implementation  

## Problem Statement

The current agent export functionality fails when users try to export agent templates to Claude Code format. The web-based export attempts to write to relative paths like `./.claude/agents` but the backend cannot resolve these paths without project context, resulting in 400 errors and failed exports.

**Current Error Flow**:
1. User navigates to Settings → Agent Templates → Export
2. Selects "Project Directory" option (`./.claude/agents`)
3. Clicks export button
4. Backend receives `export_path: "./.claude/agents"` but cannot resolve relative path
5. Export fails with 400 Bad Request error

**Root Cause**: GiljoAI web application has no knowledge of user's local file system or Claude Code project directory context.

## Proposed Solution: Copy-Command Interface

Replace the current web-based file export with a copy-paste MCP command interface that leverages Claude Code's terminal context for path resolution.

### Key Design Principles
1. **Zero Configuration Friction**: Simple copy-paste workflow
2. **Context Awareness**: Commands run in user's actual working environment
3. **Clear Separation**: Product agents vs Personal agents with distinct workflows
4. **Database Integrity**: Required product path for validation and future features

## Technical Requirements

### 1. Database Schema Changes

#### Product Model Enhancement
```python
# Add to src/giljo_mcp/models.py - Product class
project_path = Column(
    String(500), 
    nullable=False,
    comment="File system path to product folder (required for agent export)"
)
```

#### Migration Required
- Create Alembic migration to add `project_path` column
- Handle existing products (require manual path entry or migration script)

### 2. Frontend UI Changes

#### ClaudeCodeExport.vue Modifications
Replace current export implementation with copy-command interface:

```vue
<!-- Replace export path radio buttons with copy command buttons -->
<div class="export-commands mb-4">
  <h4 class="text-subtitle-1 font-weight-medium mb-2">Export Commands</h4>
  
  <!-- Product Agents Command -->
  <v-card variant="outlined" class="mb-3">
    <v-card-text class="d-flex align-center justify-between">
      <div>
        <div class="text-subtitle-2 font-weight-medium">Product Agents</div>
        <div class="text-body-2 text-medium-emphasis">
          Install agents in your product's .claude/agents folder
        </div>
      </div>
      <v-btn
        color="primary"
        variant="outlined"
        :disabled="!selectedProduct?.project_path"
        @click="copyProductCommand"
        prepend-icon="mdi-content-copy"
      >
        Copy Command
      </v-btn>
    </v-card-text>
  </v-card>
  
  <!-- Personal Agents Command -->
  <v-card variant="outlined">
    <v-card-text class="d-flex align-center justify-between">
      <div>
        <div class="text-subtitle-2 font-weight-medium">Personal Agents</div>
        <div class="text-body-2 text-medium-emphasis">
          Install agents in your user profile (~/.claude/agents)
        </div>
      </div>
      <v-btn
        color="primary"
        variant="outlined"
        @click="copyPersonalCommand"
        prepend-icon="mdi-content-copy"
      >
        Copy Command
      </v-btn>
    </v-card-text>
  </v-card>
</div>

<!-- Product Selection Dropdown (if multiple products) -->
<v-select
  v-if="availableProducts.length > 1"
  v-model="selectedProduct"
  :items="availableProducts"
  item-title="name"
  item-value="id"
  label="Select Product"
  class="mb-4"
/>
```

#### Command Generation Logic
```javascript
// Methods to add to ClaudeCodeExport.vue
methods: {
  copyProductCommand() {
    if (!this.selectedProduct?.project_path) return;
    
    const command = `mcp_giljo_export_agents --product-path "${this.selectedProduct.project_path}/.claude/agents"`;
    navigator.clipboard.writeText(command);
    this.showCopyFeedback('Product command copied!');
  },
  
  copyPersonalCommand() {
    const command = `mcp_giljo_export_agents --personal`;
    navigator.clipboard.writeText(command);
    this.showCopyFeedback('Personal command copied!');
  },
  
  showCopyFeedback(message) {
    // Show temporary success notification
    this.$emit('show-notification', { type: 'success', message });
  }
}
```

### 3. Product Setup Flow Enhancement

#### Product Creation/Edit Forms
Add required project path field to product setup:

```vue
<!-- Add to product creation/edit form -->
<v-text-field
  v-model="productForm.project_path"
  label="Product Path *"
  hint="File system path to your product folder (e.g., /Users/me/projects/my-product)"
  persistent-hint
  required
  :rules="[rules.required, rules.validPath]"
>
  <template #append>
    <v-btn
      icon="mdi-folder-open"
      variant="text"
      @click="browseForPath"
      aria-label="Browse for folder"
    />
  </template>
</v-text-field>
```

#### Validation Rules
```javascript
rules: {
  required: value => !!value || 'Product path is required',
  validPath: value => {
    // Basic path validation (platform-agnostic)
    return /^[a-zA-Z]:|\//i.test(value) || 'Enter a valid file system path'
  }
}
```

### 4. MCP Command Implementation

#### New MCP Tool: `export_agents`
Create `src/giljo_mcp/tools/claude_export.py`:

```python
"""
MCP Tool: Export Agent Templates to Claude Code Format

Provides command-line interface for exporting agent templates directly
from user's terminal context, solving path resolution issues.
"""

import os
import argparse
from pathlib import Path
from typing import Optional, List, Dict, Any

async def export_agents_command(
    product_path: Optional[str] = None,
    personal: bool = False,
    tenant_key: str = None
) -> Dict[str, Any]:
    """
    Export agent templates via MCP command.
    
    Args:
        product_path: Path to product's .claude/agents directory
        personal: Export to user's personal ~/.claude/agents
        tenant_key: User's tenant for multi-tenant isolation
        
    Returns:
        Export result dictionary
    """
    
    if personal:
        # Export to user's personal directory
        export_path = Path.home() / ".claude" / "agents"
    elif product_path:
        # Export to specified product path
        export_path = Path(product_path)
    else:
        raise ValueError("Must specify either --product-path or --personal")
    
    # Ensure directory exists
    export_path.mkdir(parents=True, exist_ok=True)
    
    # Use existing export_templates_to_claude_code function
    from src.giljo_mcp.api.endpoints.claude_export import export_templates_to_claude_code
    from src.giljo_mcp.auth.dependencies import get_user_by_tenant
    
    # Get user context
    user = await get_user_by_tenant(tenant_key)
    if not user:
        raise ValueError(f"User not found for tenant: {tenant_key}")
    
    # Perform export
    result = await export_templates_to_claude_code(
        db=db_session,
        current_user=user,
        export_path=str(export_path)
    )
    
    return result
```

#### MCP Tool Registration
Add to `src/giljo_mcp/tools/tool_accessor.py`:

```python
# Add export_agents tool to MCP tool registry
@self.mcp_server.tool("export_agents")
async def export_agents_tool(
    product_path: Optional[str] = None,
    personal: bool = False
) -> str:
    """Export agent templates to Claude Code format."""
    
    # Get tenant context from MCP session
    tenant_key = self.get_current_tenant_key()
    
    result = await export_agents_command(
        product_path=product_path,
        personal=personal,
        tenant_key=tenant_key
    )
    
    if result["success"]:
        return f"✅ Exported {result['exported_count']} agents to {product_path or '~/.claude/agents'}"
    else:
        return f"❌ Export failed: {result.get('message', 'Unknown error')}"
```

### 5. Backend API Cleanup

#### Remove/Deprecate Web Export Endpoint
- Keep existing `/export/claude-code` endpoint for backward compatibility
- Add deprecation warning in API documentation
- Update endpoint to handle new project_path-based exports

#### Product API Enhancement
```python
# Add to product creation/update endpoints
@router.post("/products")
async def create_product(
    product_data: ProductCreate,
    current_user: User = Depends(get_current_active_user),
    db: AsyncSession = Depends(get_db_session)
):
    # Validate project_path if provided
    if product_data.project_path:
        path = Path(product_data.project_path).expanduser()
        if not path.exists():
            raise HTTPException(400, f"Project path does not exist: {path}")
        if not path.is_dir():
            raise HTTPException(400, f"Project path is not a directory: {path}")
    
    # Create product with project_path
    # ... existing logic
```

## User Experience Flow

### New User Journey
1. **Product Setup**: User creates product, enters project path (required field)
2. **Agent Configuration**: User activates desired agent templates
3. **Export Process**:
   - Navigate to Settings → Agent Templates → Export
   - Choose "Product Agents" or "Personal Agents"
   - Click "Copy Command" button
   - Paste command in Claude Code terminal
   - Agents appear in appropriate directory

### Command Examples
```bash
# Product agents (copies to clipboard)
mcp_giljo_export_agents --product-path "/Users/me/projects/my-ai-app/.claude/agents"

# Personal agents (copies to clipboard)
mcp_giljo_export_agents --personal
```

## Migration Strategy

### Phase 1: Database Migration
1. Add `project_path` column to products table
2. Create migration script for existing products
3. Update Product model and validation

### Phase 2: Frontend Updates
1. Update ClaudeCodeExport.vue with copy-command interface
2. Modify product creation/edit forms
3. Add product selection logic for export

### Phase 3: Backend Implementation
1. Implement MCP export command
2. Register tool in MCP server
3. Add API validation for project paths

### Phase 4: Testing & Rollout
1. Test copy-paste workflow in Claude Code
2. Validate multi-tenant isolation
3. Update documentation and user guides

## Success Criteria

### Functional Requirements
- [ ] Users can copy MCP commands for both product and personal agent export
- [ ] Commands successfully export agents when pasted in Claude Code terminal
- [ ] Product path is required during product creation
- [ ] Multi-tenant isolation maintained
- [ ] Existing export API remains functional (backward compatibility)

### User Experience Requirements
- [ ] One-click copy to clipboard
- [ ] Clear visual feedback when command copied
- [ ] Intuitive product vs personal agent distinction
- [ ] Error handling for missing product paths
- [ ] Tooltips and help text for user guidance

### Technical Requirements
- [ ] MCP command handles path resolution correctly
- [ ] Cross-platform compatibility (Windows/Mac/Linux)
- [ ] Proper error handling and user feedback
- [ ] Database migration completes without data loss
- [ ] No breaking changes to existing API contracts

## Testing Strategy

### Unit Tests
- Product model validation with project_path
- MCP command path resolution logic
- Copy-to-clipboard functionality

### Integration Tests
- End-to-end export workflow
- Multi-tenant data isolation
- Product creation with path validation

### User Acceptance Tests
- Copy-paste workflow in actual Claude Code environment
- Both product and personal agent export scenarios
- Error handling for invalid paths

## Risk Mitigation

### Technical Risks
- **Path Resolution Failures**: Extensive cross-platform testing
- **MCP Command Registration**: Fallback to web export if MCP unavailable
- **Database Migration Issues**: Comprehensive backup and rollback plan

### User Experience Risks
- **Copy-Paste Confusion**: Clear instructions and visual feedback
- **Product Path Entry Errors**: Validation and browse button assistance
- **Command Execution Issues**: Detailed error messages and troubleshooting guide

## Dependencies

### Internal Dependencies
- Existing MCP server infrastructure
- Product model and database schema
- Agent template management system
- Authentication and multi-tenancy

### External Dependencies
- Claude Code MCP client support
- User's terminal environment
- Operating system clipboard functionality

## Future Enhancements

### Potential Improvements
- Auto-detection of Claude Code project directories
- Batch export commands for multiple products
- Integration with Git hooks for automatic agent updates
- Claude Code extension for one-click agent import

### Monitoring & Analytics
- Track export command usage (product vs personal)
- Monitor export success/failure rates
- Analyze user path configuration patterns

---

## Implementation Notes

This handover provides a complete roadmap for replacing the broken web-based agent export with an elegant copy-command interface. The solution maintains database integrity through required product paths while leveraging Claude Code's terminal context for seamless path resolution.

The copy-paste approach aligns with developer expectations and eliminates the complex file system access issues that plague the current implementation. Users get a simple, reliable workflow that works consistently across all platforms.

**Ready for implementation by fresh agents with full context and technical specifications.**