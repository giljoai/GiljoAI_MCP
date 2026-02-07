# Kickoff: Handover 0710 - Cleanup Models Agents

**Series:** 0700 Code Cleanup Series
**Risk Level:** CRITICAL
**Estimated Effort:** 4-6 hours

---

## CRITICAL: Large File Handling

**Files over 500 lines MUST be read in 200-line batches.** Never skip large files.

```python
Read(file_path, offset=0, limit=200)    # Lines 1-200
Read(file_path, offset=200, limit=200)  # Lines 201-400
```

---

## Required Reads

1. **Your Spec**: `handovers/0700_series/0710_cleanup_models_agents.md`
2. **Protocol**: `handovers/0700_series/WORKER_PROTOCOL.md`
3. **Prior Work**: `handovers/0700_series/0706b_investigation_report.md` (agent_identity.py is HEALTHY)

---

## Mission

Clean up agent model files - resolve DEPRECATED/TODO markers in `agent_identity.py` and `agents.py`.

**NOTE**: 0706b already verified architecture is HEALTHY. Focus on code quality, not restructuring.

---

## Phase 0: Validation Research (MANDATORY)

```bash
# Count DEPRECATED markers
grep -rn "DEPRECATED" src/giljo_mcp/models/agent_identity.py src/giljo_mcp/models/agents.py

# Count TODO markers
grep -rn "TODO" src/giljo_mcp/models/agent_identity.py src/giljo_mcp/models/agents.py

# Verify messages JSONB status (should be deprecated already)
grep -n "messages" src/giljo_mcp/models/agent_identity.py | head -10
```

---

## Execution Priority

1. Resolve DEPRECATED markers (remove code or document timeline)
2. Resolve TODO markers (fix, create issue, or remove if obsolete)
3. Add type hints if missing
4. Run tests

---

## Success Criteria

- [ ] 0 actionable DEPRECATED markers
- [ ] 0 TODO markers
- [ ] All agent/orchestration tests pass
- [ ] Committed

---

## Communication

```json
{
  "from_handover": "0710",
  "to_handovers": ["0714"],
  "type": "info",
  "subject": "Models Agents cleanup complete"
}
```
