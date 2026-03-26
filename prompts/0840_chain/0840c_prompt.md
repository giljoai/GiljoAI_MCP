# Terminal Session: 0840c - Product Config Normalization

## Mission
Execute Handover 0840c (Part 3/6 of JSONB Normalization Series).

## Handover Document
**READ THIS FIRST**: `F:\GiljoAI_MCP\handovers\0840c_product_config_normalization.md`

## Chain Log
**READ AND UPDATE**: `F:\GiljoAI_MCP\prompts\0840_chain\chain_log.json`
- Check `orchestrator_instructions` field — if non-null, follow those instructions
- Verify 0840b is `complete`
- Read ALL previous `notes_for_next`

## Branch
`feature/0840-jsonb-normalization`

## CRITICAL: Use Subagents
- `database-expert` — Migration, related tables, backfill
- `tdd-implementor` — Service rewrite, context tools, tests
- `ux-designer` — Frontend form restructuring, Product Info tab rename, platform toggles

## Key Decisions This Agent Must Make
1. Whether to normalize `product_memory` JSONB (check what's left after sequential_history migration)
2. Whether to normalize `tuning_state` JSONB (assess if it's a legitimate config blob)
3. Document decisions in chain log `notes_for_next`

## STOP CONDITIONS
- `product_memory` contains actively needed data beyond git_integration
- `tuning_state` normalization would break tuning flow
- Frontend has undocumented component dependencies

## On Completion
**Use Bash tool to EXECUTE the spawn command from the handover document Step 6.**
