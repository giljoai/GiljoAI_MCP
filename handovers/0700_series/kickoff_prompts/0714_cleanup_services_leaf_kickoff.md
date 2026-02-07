# Kickoff: Handover 0714 - Cleanup Services Leaf

**Series:** 0700 Code Cleanup Series
**Risk Level:** MEDIUM
**Estimated Effort:** 3-4 hours

---

## CRITICAL: Large File Handling

**Files over 500 lines MUST be read in 200-line batches.** Never skip large files.

---

## Required Reads

1. **Your Spec**: `handovers/0700_series/0714_cleanup_services_leaf.md`
2. **Protocol**: `handovers/0700_series/WORKER_PROTOCOL.md`
3. **Comms**: `handovers/0700_series/comms_log.json`

---

## Mission

Clean up leaf-level services with limited dependents:
- `git_service.py`
- `serena_detector.py`
- `template_service.py`
- `task_service.py`
- `message_service.py`

---

## Phase 0: Validation Research (MANDATORY)

```bash
# Count markers per service file
for f in git_service serena_detector template_service task_service message_service; do
  echo "=== $f.py ==="
  grep -c "DEPRECATED\|TODO" src/giljo_mcp/services/${f}.py 2>/dev/null || echo "0"
done

# Verify message_service uses counters (not JSONB)
grep -n "messages_.*_count" src/giljo_mcp/services/message_service.py | head -5
```

---

## Execution Priority

1. **message_service.py** - Verify counter-based only (no JSONB)
2. **template_service.py** - Verify no mission_templates.py refs
3. Resolve TODO/DEPRECATED in all files
4. Run service tests

---

## Success Criteria

- [ ] 0 TODO/DEPRECATED markers in scope
- [ ] No references to deprecated patterns
- [ ] All service tests pass
- [ ] Committed

---

## Communication

```json
{
  "from_handover": "0714",
  "to_handovers": ["0715"],
  "type": "info",
  "subject": "Services Leaf cleanup complete"
}
```
