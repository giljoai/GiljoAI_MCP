# Migration History Archive - Pre-Reset (2025-12-21)

## Why This Reset Was Needed

The migration chain had accumulated schema mismatches between the baseline migration
and the SQLAlchemy models. Fresh installs were failing because:

1. **Baseline was incomplete** - Missing columns that existed in models:
   - `messages.result`
   - `mcp_agent_jobs.mission_acknowledged_at`

2. **Migrations referenced non-existent columns**:
   - `d5a6385e1ff2` tried to DROP `mission_read_at` (not in baseline)
   - `7983bf9c91c9` tried to ALTER `messages.result` (not in baseline)

3. **Orphaned migration** - `0260_add_execution_mode.py` had `down_revision = None`

## Original Migration Chain

```
f504ea46e988 (baseline_schema_all_27_tables)
    |
f4121f77a2d9 (add_product_memory_column_handover_0135)
    |
583c4b97e1ae (add_quality_standards_to_product)
    |
807c85a49438 (add_template_id_to_mcpagentjob_for_handover_0244a)
    |
c972fded3b0e (convert_message_json_to_jsonb_for_containment_operators)
    |
    +---> d5a6385e1ff2 (simplify_job_signaling)
    |
    +---> 0260_execution_mode (add_execution_mode - was orphaned, fixed to branch from c972fded3b0e)
    |
ad91f3ce8c9b (merge_heads_before_0335)
    |
7983bf9c91c9 (add_last_exported_at_to_agent_templates_handover_0335)
    |
e2afa1851965 (add_vision_summarization_columns_handover_0345b)
    |
946b857e8eb1 (add_multi_level_vision_summaries)
```

## Archived Migration Files

The following files were moved to `migrations/archive/versions_pre_reset/`:

| File | Revision ID | Description |
|------|-------------|-------------|
| f504ea46e988_baseline_schema_all_27_tables.py | f504ea46e988 | Original baseline with 27 tables |
| f4121f77a2d9_add_product_memory_column_handover_0135.py | f4121f77a2d9 | Added product_memory JSONB column |
| 583c4b97e1ae_add_quality_standards_to_product.py | 583c4b97e1ae | Added quality_standards to products |
| 807c85a49438_add_template_id_to_mcpagentjob_for_.py | 807c85a49438 | Added template_id to MCPAgentJob |
| c972fded3b0e_convert_message_json_to_jsonb_for_.py | c972fded3b0e | Converted JSON columns to JSONB |
| d5a6385e1ff2_simplify_job_signaling.py | d5a6385e1ff2 | Removed acknowledged/mission_read_at |
| 0260_add_execution_mode.py | 0260_execution_mode | Added execution_mode to projects |
| ad91f3ce8c9b_merge_heads_before_0335.py | ad91f3ce8c9b | Merge migration |
| 7983bf9c91c9_add_last_exported_at_to_agent_templates_.py | 7983bf9c91c9 | Added last_exported_at, indexes |
| e2afa1851965_add_vision_summarization_columns_.py | e2afa1851965 | Added LSA summarization columns |
| 946b857e8eb1_add_multi_level_vision_summaries.py | 946b857e8eb1 | Added multi-level summary columns |

## Recovery Instructions

If you need to restore these migrations:

```bash
# Move archived migrations back
mv migrations/archive/versions_pre_reset/*.py migrations/versions/

# Drop current database and re-run with old migrations
# (requires compatible database state)
```

## New Baseline

After this reset, a single baseline migration was generated from the current
SQLAlchemy models using:

```bash
alembic revision --autogenerate -m "unified_baseline_from_models"
```

This ensures the migration matches the actual model definitions exactly.

## Related Handovers

- This reset was performed during work on Handover 0360/0361
- No schema changes were pending - only tool enhancements and documentation
