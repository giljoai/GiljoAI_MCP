# Project 3.9.b: Template System Consolidation Plan

## Executive Summary

We have identified critical duplication issues caused by retrofitting Project 3.9.b into an existing codebase that already had template functionality from Project 3.4. This document provides a comprehensive plan to consolidate and unify the template system.

## Current State Analysis

### Duplicate Implementations Found

#### 1. Three Augmentation Functions

| Location                             | Function                     | Input Type                       | Supported Types                  | Issues                    |
| ------------------------------------ | ---------------------------- | -------------------------------- | -------------------------------- | ------------------------- |
| src/giljo_mcp/tools/template.py:860  | \_apply_augmentation         | TemplateAugmentation (DB object) | append, prepend, replace, inject | Database-specific         |
| src/giljo_mcp/tools/template.py:877  | \_apply_runtime_augmentation | Dict[str, Any]                   | append, prepend, replace, inject | Runtime-specific          |
| src/giljo_mcp/template_adapter.py:95 | \_apply_augmentation         | Dict[str, Any]                   | append, prepend, replace         | **Missing 'inject' type** |

#### 2. Two Template Systems

| System         | Location             | Purpose                    | Status                       |
| -------------- | -------------------- | -------------------------- | ---------------------------- |
| Original (3.4) | mission_templates.py | Hardcoded Python templates | Still in use by orchestrator |
| New (3.9.b)    | template.py + DB     | Database-backed templates  | Partially integrated         |
| Adapter Layer  | template_adapter.py  | Backward compatibility     | Bridge between systems       |

#### 3. Overlapping Components

- **orchestrator.py**: Uses both MissionTemplateGenerator and MissionTemplateGeneratorV2
- **AgentRole enum**: Defined in both mission_templates.py and orchestrator.py
- **Variable substitution**: Handled separately from augmentation in multiple places

## Root Cause

When we pivoted at Project 5.1 to leverage Claude Code sub-agents, we retroactively inserted Phase 3.9. This created overlapping implementations without proper cleanup of the original Project 3.4 deliverables.

## Consolidation Design

### 1. Unified Augmentation System

#### Single Polymorphic Function

```python
def apply_augmentation(
    content: str,
    augmentation: Union[TemplateAugmentation, Dict[str, Any]]
) -> str:
    """
    Apply augmentation to template content.
    Handles both database objects and runtime dictionaries.

    Args:
        content: Template content to augment
        augmentation: Either a DB TemplateAugmentation or dict with:
            - type/augmentation_type: append, prepend, replace, inject
            - content: Content to apply
            - target/target_section: Optional target for replace/inject

    Returns:
        Augmented content
    """
    # Normalize input to dict format
    if isinstance(augmentation, TemplateAugmentation):
        aug_type = augmentation.augmentation_type
        aug_content = augmentation.content
        target = augmentation.target_section
    else:
        aug_type = augmentation.get("type") or augmentation.get("augmentation_type", "append")
        aug_content = augmentation.get("content", "")
        target = augmentation.get("target") or augmentation.get("target_section", "")

    # Apply augmentation based on type
    if aug_type == "append":
        return content + "\n\n" + aug_content
    elif aug_type == "prepend":
        return aug_content + "\n\n" + content
    elif aug_type == "replace" and target:
        return content.replace(target, aug_content)
    elif aug_type == "inject" and target:
        index = content.find(target)
        if index != -1:
            end_index = index + len(target)
            return content[:end_index] + "\n" + aug_content + content[end_index:]

    return content
```

#### Variable Substitution Integration

```python
def process_template(
    content: str,
    variables: Optional[Dict[str, Any]] = None,
    augmentations: Optional[List[Union[TemplateAugmentation, Dict]]] = None,
    substitute_first: bool = False
) -> str:
    """
    Process a template with variables and augmentations.

    Args:
        content: Base template content
        variables: Variables to substitute
        augmentations: List of augmentations to apply
        substitute_first: If True, substitute variables before augmentations

    Returns:
        Processed template content
    """
    # Option to substitute variables first (for augmentations that need resolved variables)
    if substitute_first and variables:
        for key, value in variables.items():
            content = content.replace(f"{{{key}}}", str(value))

    # Apply augmentations
    if augmentations:
        for aug in augmentations:
            content = apply_augmentation(content, aug)

    # Substitute variables after augmentations (default behavior)
    if not substitute_first and variables:
        for key, value in variables.items():
            content = content.replace(f"{{{key}}}", str(value))

    return content
```

### 2. Unified Template Management

#### Single Source of Truth

```python
class UnifiedTemplateManager:
    """
    Unified template manager combining database and legacy support.
    Single source of truth for all template operations.
    """

    def __init__(self, db_manager: Optional[DatabaseManager] = None):
        self.db_manager = db_manager
        self._legacy_templates = {}  # Cache for migrated legacy templates
        self._template_cache = {}
        self._load_legacy_templates()

    async def get_template(
        self,
        name: str,
        role: Optional[str] = None,
        variables: Optional[Dict[str, Any]] = None,
        augmentations: Optional[List[Union[TemplateAugmentation, Dict]]] = None,
        product_id: Optional[str] = None
    ) -> str:
        """
        Get a template by name or role, with full processing.

        Priority order:
        1. Database templates (if available)
        2. Legacy templates (fallback)
        3. Error message
        """
        template_content = None

        # Try database first
        if self.db_manager:
            template_content = await self._get_db_template(name, role, product_id)

        # Fallback to legacy
        if not template_content:
            template_content = self._get_legacy_template(name, role)

        # Process if found
        if template_content:
            return process_template(template_content, variables, augmentations)

        # Not found
        return f"Template not found: {name or role}"

    def _load_legacy_templates(self):
        """Load templates from mission_templates.py for backward compatibility"""
        from .mission_templates import MissionTemplateGenerator
        gen = MissionTemplateGenerator()

        # Map legacy templates
        self._legacy_templates = {
            "orchestrator": gen.ORCHESTRATOR_TEMPLATE,
            "analyzer": gen.ANALYZER_TEMPLATE,
            "implementer": gen.IMPLEMENTER_TEMPLATE,
            "tester": gen.TESTER_TEMPLATE,
            "reviewer": gen.REVIEWER_TEMPLATE
        }
```

### 3. Migration Path

#### Phase 1: Create Unified Components (Immediate)

1. Create `src/giljo_mcp/template_manager.py` with unified functions
2. Move `apply_augmentation` and `process_template` to this module
3. Create `UnifiedTemplateManager` class

#### Phase 2: Update Existing Code (Next)

1. Replace all augmentation function calls with unified version
2. Update `orchestrator.py` to use `UnifiedTemplateManager` only
3. Update `template.py` MCP tools to use unified functions
4. Remove duplicate functions from `template.py` and `template_adapter.py`

#### Phase 3: Consolidate Enums (After)

1. Move `AgentRole` and `ProjectType` to `src/giljo_mcp/enums.py`
2. Update all imports to use single source
3. Remove duplicate definitions

#### Phase 4: Database Migration (Final)

1. Run migration script to load legacy templates into database
2. Set `is_default=True` for standard roles
3. Archive original templates for rollback capability

### 4. File Structure After Consolidation

```
src/giljo_mcp/
├── enums.py                 # Single source for all enums
├── template_manager.py       # Unified template management
├── models.py                # Database models (including template tables)
├── orchestrator.py          # Uses UnifiedTemplateManager
├── tools/
│   └── template.py          # MCP tools using unified functions
├── legacy/
│   └── mission_templates.py # Moved here, kept for reference only
└── [REMOVED] template_adapter.py  # No longer needed
```

### 5. Implementation Checklist for Implementer

#### Immediate Actions

- [ ] Create `src/giljo_mcp/template_manager.py` with unified functions
- [ ] Create `src/giljo_mcp/enums.py` consolidating all enums
- [ ] Implement `apply_augmentation` polymorphic function
- [ ] Implement `process_template` with variable substitution
- [ ] Implement `UnifiedTemplateManager` class

#### Refactoring Actions

- [ ] Update `orchestrator.py` line 111 to use `UnifiedTemplateManager`
- [ ] Update `tools/template.py` to import from `template_manager`
- [ ] Remove `_apply_augmentation` from line 860
- [ ] Remove `_apply_runtime_augmentation` from line 877
- [ ] Update all MCP tool functions to use unified manager

#### Cleanup Actions

- [ ] Delete `template_adapter.py` after migration
- [ ] Move `mission_templates.py` to `legacy/` folder
- [ ] Remove duplicate `AgentRole` from `orchestrator.py` line 37
- [ ] Update all imports to use new structure

#### Testing Requirements

- [ ] Test polymorphic augmentation with both DB objects and dicts
- [ ] Test variable substitution order (before/after augmentations)
- [ ] Test backward compatibility with legacy templates
- [ ] Test all 4 augmentation types (append, prepend, replace, inject)
- [ ] Test template caching and performance (<0.1ms target)

### 6. Backward Compatibility Guarantee

The unified system will maintain 100% backward compatibility:

1. Existing API signatures preserved
2. Legacy templates auto-migrated on first use
3. Both DB objects and dicts supported
4. All augmentation types supported
5. Variable substitution order configurable

### 7. Performance Improvements

#### Caching Strategy

- In-memory cache with TTL for frequently used templates
- Lazy loading of legacy templates only when needed
- Batch database queries for related templates
- Pre-compiled regex for variable substitution

#### Expected Performance

- Template retrieval: <10ms (from cache: <0.1ms)
- Augmentation application: <1ms per augmentation
- Variable substitution: <1ms for typical template
- Total generation time: <15ms worst case, <1ms typical

## Answers to Tester's Questions

### Q1: Why do we have two separate functions?

**A:** Historical artifact from retrofitting Project 3.9.b into existing 3.4 codebase. One handles database objects (new system), other handles dictionaries (runtime/legacy).

### Q2: Should we consolidate into one polymorphic function?

**A:** Yes. The consolidation plan provides a single `apply_augmentation` function that handles both types.

### Q3: Are there other duplications in the codebase?

**A:** Yes:

- `AgentRole` enum duplicated in 2 places
- Template systems (mission_templates.py vs template.py)
- Template generator classes (MissionTemplateGenerator vs MissionTemplateGeneratorV2)

### Q4: Which one should be used for variable substitution?

**A:** Neither augmentation function handles variable substitution - it's done separately. The new `process_template` function will handle both in the correct order.

## Success Criteria

1. ✅ Single augmentation function handling all types
2. ✅ No duplicate enums or template definitions
3. ✅ Unified template manager as single source of truth
4. ✅ All tests passing with new structure
5. ✅ Performance targets met (<0.1ms cache, <15ms generation)
6. ✅ 100% backward compatibility maintained
7. ✅ Clean file structure with no redundancy

## Timeline

- **Hour 1**: Create unified components (template_manager.py, enums.py)
- **Hour 2**: Refactor existing code to use unified components
- **Hour 3**: Remove duplicates and clean up structure
- **Hour 4**: Run tests and fix any issues
- **Hour 5**: Database migration and final validation

## Risk Mitigation

1. **Risk**: Breaking existing functionality

   - **Mitigation**: Comprehensive test suite before changes
   - **Mitigation**: Feature flag for gradual rollout

2. **Risk**: Performance degradation

   - **Mitigation**: Benchmark before/after
   - **Mitigation**: Aggressive caching strategy

3. **Risk**: Data loss during migration
   - **Mitigation**: Archive all templates before migration
   - **Mitigation**: Reversible migration scripts

## Conclusion

This consolidation plan addresses all identified duplication issues while maintaining backward compatibility and improving performance. The implementer should follow the checklist sequentially to ensure smooth migration.
