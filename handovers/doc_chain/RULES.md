# Doc Chain - Shared Rules for All Agents

**Project**: Token Estimation Documentation Cleanup
**Date**: 2026-03-18
**Chain Type**: Parallel (all sessions run simultaneously)

---

## CRITICAL: YOU MUST ACTUALLY EDIT FILES

**This is not a planning exercise. You must USE THE EDIT TOOL to modify documentation files.**

- Read each file FIRST, then use the Edit tool to make changes
- After editing a file, use `git diff <filepath>` via Bash to VERIFY your changes exist on disk
- If git diff shows no changes, your edit failed — try again
- Do NOT just report what you would do — DO IT
- Do NOT delete the `handovers/doc_chain/` directory or any files in it
- Update chain_log.json LAST, only after verifying all edits via git diff

---

## Context

GiljoAI MCP is a **passive MCP server**. We do NOT perform token estimation, token budgeting, or token reduction as a system feature. The only legitimate token-related functionality is:

1. **Vision document chunking** (tiktoken + SUMI) to stay within Claude Code CLI's 25K ingest limit
2. **User-controlled context depth** via toggle cards in Settings (vision depth, 360 memory count, git commit count, agent detail level)
3. **360 memory write limits** (`token_estimate` field on `product_memory_entries`)
4. **Protocol builder guidance** (comments telling the orchestrator AI approximate sizes)

Everything else referencing "token estimation", "token budgets per agent", "token reduction percentages", "real-time token tracking", or the old `/token-estimate` endpoint is DEAD documentation from a system that was never fully built or has been removed.

---

## STRIP Rules (REMOVE these references)

1. **Dead Token Estimation API**: Any reference to `/api/products/{product_id}/token-estimate` or `GET /products/active/token-estimate`
2. **MissionResponse/SpawnResult token fields**: `estimated_tokens`, `prompt_tokens`, `mission_tokens`, `total_tokens` in spawn/mission responses
3. **Per-agent-type token budgets**: Tables showing "Backend: 8000 tokens, Frontend: 7000 tokens" etc.
4. **Token reduction percentages**: "70% token reduction", "85% reduction", "60-90% reduction" as system claims
5. **Real-time token tracking**: "Real-time token usage monitoring", "token metrics", "token usage tracking"
6. **Token Budgeting as a feature**: "Token Budgeting: Real-time estimation prevents context overflow"
7. **`DynamicContextLoader` role-based selection**: This class exists but is DEAD CODE — nothing calls it through the API layer
8. **Handover 0020 Token Reduction Strategy**: The 4-point strategy about orchestrator reading full vision
9. **SerenaOptimizer token tracking**: References to Serena reducing token consumption
10. **`estimated_prompt_tokens`** in API response examples (the field still exists in code but is informational — strip from docs that frame it as a "feature")
11. **Context budget system**: `context_budget: 200000`, `context_used: 0` fields and the succession-based-on-token-limit concept
12. **TOKEN_REDUCTION_ARCHITECTURE.md** links — this doc is being deleted

## KEEP Rules (DO NOT remove these)

1. **Vision chunking**: tiktoken, SUMI, `VisionDocumentChunker`, 25K limit, `EnhancedChunker`, chunk_count, total_tokens on vision documents
2. **User-controlled depth settings**: Toggle cards, depth controls (none/light/medium/full), `ContextPriorityConfig`
3. **`fetch_context` tool dispatcher**: The tool and its category-based single-call enforcement (Handover 0351)
4. **Individual context tools**: `get_vision_document`, `get_tech_stack`, `get_architecture`, etc.
5. **Protocol builder guidance**: Comments like "~180 tokens", "<5K tokens target" in protocol_builder.py — these are operational hints for the AI
6. **JWT/auth tokens**: All references to JWT, Bearer, CSRF, auth_token, download tokens
7. **CSS design tokens**: Handover 0765c (completely unrelated)
8. **Database columns for vision**: `total_tokens`, `original_token_count`, `token_count` on vision/chunk/summary tables
9. **360 memory `token_estimate`**: Column on `product_memory_entries`
10. **Thin prompt size reporting**: The fact that `estimated_prompt_tokens` exists in code is fine — just don't document it as a "Token Estimation System"
11. **Serena symbolic read savings**: References to Serena's approach of reading symbols vs full files saving tokens — this is a real technique, KEEP

## REFRAME Rules (change language, keep concept)

When a concept is valid but framed as "token reduction":
- "Token reduction" -> "Context management" or "context depth control"
- "Token budget per agent" -> "Context depth settings"
- "70% token reduction" -> "Focused context delivery" or just remove the percentage
- "Token optimization" -> "Context optimization" or "lean context delivery"
- "Reduces token usage by X%" -> "Delivers focused, relevant context"
- "Within token limits (24K max per call)" -> "Within Claude Code's 25K ingest limit" (this is a chunking constraint)

## DELETE Rules

If a document is >80% dead token estimation content with no salvageable sections, DELETE the file content and replace with a stub:
```markdown
# [Title] - RETIRED
This document has been retired. See [relevant replacement doc] for current information.
```

## Workflow for Each Agent

1. Read your work order file (path given in your launch prompt)
2. Read `handovers/doc_chain/chain_log.json` and update your session status to `"in_progress"` using the Edit tool
3. For each document in your assignment:
   a. Read the document fully using the Read tool
   b. Verify claims against codebase using Grep/Glob (check if endpoints/classes exist)
   c. Apply STRIP/KEEP/REFRAME/DELETE rules
   d. **Use the Edit tool to actually modify the file**
   e. **Run `git diff <filepath>` via Bash to confirm your edits are on disk**
   f. If git diff shows no changes, your edit failed — retry
4. After ALL files are edited and verified:
   - Update chain_log.json: set status to `"complete"`, fill `summary` and `tasks_completed`
5. **DO NOT commit** — user will review all changes and commit manually

## Important Notes

- Do NOT add AI signatures to any file
- Do NOT create new documentation files unless replacing a deleted one with a stub
- Do NOT touch code files — this chain is DOCS ONLY
- Do NOT delete the `handovers/doc_chain/` directory or any files within it
- Preserve document structure where possible — surgical edits over full rewrites
- When in doubt, STRIP rather than keep (the user wants minimal token references)
- Completed handovers in `handovers/completed/` are HISTORICAL — do not edit them
- Files in `docs/archive/` are HISTORICAL — do not edit them
- Backup SQL files in `backups/` are immutable — do not edit them
