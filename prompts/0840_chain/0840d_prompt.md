# Terminal Session: 0840d - User Settings Normalization

## Mission
Execute Handover 0840d (Part 4/6 of JSONB Normalization Series).

## Handover Document
**READ THIS FIRST**: `F:\GiljoAI_MCP\handovers\0840d_user_settings_normalization.md`

## Chain Log
**READ AND UPDATE**: `F:\GiljoAI_MCP\prompts\0840_chain\chain_log.json`
- Check `orchestrator_instructions` field — if non-null, follow those instructions
- Verify 0840c is `complete`
- Read ALL previous `notes_for_next` — especially 0840c re: Product Info rename status

## Branch
`feature/0840-jsonb-normalization`

## CRITICAL: Use Subagents
- `database-expert` — Migration, user_field_priorities table, depth columns
- `tdd-implementor` — Service rewrite, test updates

## Key Context
- "Product Info" and "Project Description" are ALWAYS ON — no toggle row in user_field_priorities
- 7 toggleable categories: tech_stack, architecture, testing, vision_documents, memory_360, git_history, agent_templates
- Check if 0840c already renamed "Basic Info" → "Product Info" in frontend

## On Completion
**Use Bash tool to EXECUTE the spawn command from the handover document Step 6.**
