# Single Source of Truth (SSoT) Documents - Master Index

**Purpose**: This index tracks all authoritative Single Source of Truth documents in the GiljoAI MCP documentation.

**SSoT Definition**: A document marked as SSoT is the **authoritative reference** for its topic. When conflicts arise between documentation, the SSoT document takes precedence.

**Last Updated**: 2025-11-17

---

## Active SSoT Documents

### 1. Orchestrator Context Flow SSoT

**File**: [ORCHESTRATOR_CONTEXT_FLOW_SSoT.md](ORCHESTRATOR_CONTEXT_FLOW_SSoT.md)

**Topic**: Complete orchestrator context flow from user setup to agent execution

**Scope**:
- The 13 context priority cards (user configuration)
- Complete orchestrator launch flow (step-by-step)
- Priority-based context extraction (9 context sources)
- Context prioritization metrics (77% reduction, 3,500 tokens vs 15K-30K baseline)
- Agent-specific context re-prioritization
- Complete flow diagram (user → orchestrator → agents → completion)

**Handovers Covered**: 0301, 0302, 0303, 0305, 0306, 0311, 0135-0139, 013B

**Version**: 1.0
**Last Verified**: 2025-11-17

**When to Use**:
- Understanding the complete orchestrator workflow
- Debugging context building issues
- Explaining context prioritization to stakeholders
- Training new developers on context management
- Designing new context sources

---

## SSoT Document Criteria

A document qualifies as SSoT when it meets ALL of these criteria:

1. **Comprehensive**: Covers topic completely, no critical gaps
2. **Authoritative**: Designated as the primary reference for the topic
3. **Maintained**: Regularly updated with version tracking
4. **Verified**: Last verified date within 90 days
5. **Cross-Referenced**: Linked from other related documentation
6. **Conflict Resolution**: Takes precedence when conflicts arise

---

## SSoT Maintenance Schedule

| Document | Next Review Date | Review Frequency | Owner |
|----------|------------------|------------------|-------|
| ORCHESTRATOR_CONTEXT_FLOW_SSoT.md | 2025-12-17 | Monthly (first 3 months), then quarterly | Documentation Manager Agent |

---

## How to Create a New SSoT Document

**Step 1**: Identify Documentation Gap
- Multiple scattered documents on same topic
- Frequent conflicts between documentation
- No authoritative reference for critical workflow

**Step 2**: Create Comprehensive Document
- Cover ALL aspects of the topic
- Include examples, code snippets, diagrams
- Cross-reference related handovers and docs
- Add version history table

**Step 3**: Designate as SSoT
- Add "**Status**: Production Documentation - Single Source of Truth" header
- Add "Last Verified" date
- Add to this index (SSoT_INDEX.md)
- Update README_FIRST.md with SSoT section link

**Step 4**: Maintain and Verify
- Review regularly (monthly for first 3 months, then quarterly)
- Update when related features change
- Bump version number and update changelog
- Update "Last Verified" date after review

---

## Related Documentation

- [README_FIRST.md](README_FIRST.md) - Main documentation hub (includes SSoT section)
- [ORCHESTRATOR.md](ORCHESTRATOR.md) - Orchestrator architecture (referenced by SSoT)
- [CONTEXT_MANAGEMENT_SYSTEM.md](CONTEXT_MANAGEMENT_SYSTEM.md) - Context extraction details
- [SERVICES.md](SERVICES.md) - Service layer API reference

---

**Document Version**: 1.0
**Created**: 2025-11-17
**Maintained By**: Documentation Manager Agent
