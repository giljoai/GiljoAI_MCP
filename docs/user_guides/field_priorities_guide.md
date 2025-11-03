# Field Priorities User Guide

**For**: End Users of GiljoAI MCP
**Goal**: Reduce AI API costs by 70% through smart configuration
**Difficulty**: Beginner
**Time to Complete**: 5 minutes

---

## What Are Field Priorities?

Field priorities let you control **which information** your AI agents receive and **how much detail** they get. This directly reduces your API costs while keeping mission quality high.

### Why This Matters

**Example Cost Savings**:
```
Without field priorities:
- 5 agents × 30,000 tokens each = 150,000 tokens
- Cost: $0.15 per project (at $0.001/1K tokens)

With field priorities (70% reduction):
- 5 agents × 9,000 tokens each = 45,000 tokens
- Cost: $0.045 per project
- Savings: $0.105 per project → $105/month for 1000 projects
```

---

## Quick Start

### Step 1: Open My Settings

1. Click your avatar (top-right corner)
2. Select **"My Settings"**
3. Click **"Field Priorities"** tab

### Step 2: Understand Priority Levels

| Priority | What It Means | Example |
|----------|---------------|---------|
| 10 | Full detail - agents see everything | Product vision (always keep high) |
| 7-9 | Important - slightly condensed | Project description |
| 4-6 | Useful - 50% summarized | Codebase structure |
| 1-3 | Optional - only key points (20% of original) | Architecture notes |
| 0 | Exclude - completely omitted | Deployment details |

### Step 3: Configure Your Priorities

**Recommended Starting Configuration**:

```
Product Vision:         10 (Full detail - critical)
Project Description:     8 (Full detail - important)
Codebase Summary:        4 (Abbreviated - 50% tokens)
Architecture:            2 (Minimal - 20% tokens)
Tech Stack:              6 (Abbreviated - useful context)
Features:                7 (Important for planning)
```

### Step 4: Enable Serena Integration (Optional)

Toggle **"Include Serena Codebase Context"** ON to add real codebase analysis to missions.

**When to enable**:
- Working on existing codebases
- Need file structure information
- Want accurate function/class references

**When to disable**:
- Greenfield projects (no existing code)
- Prefer faster mission generation
- Don't have Serena MCP configured

### Step 5: Set Token Budget

**Default**: 2000 tokens per mission
**Range**: 500 - 10,000 tokens

**Guidelines**:
- **Small projects**: 1000-1500 tokens
- **Medium projects**: 2000-3000 tokens
- **Large projects**: 4000-6000 tokens

### Step 6: Save and Test

1. Click **"Save Priorities"**
2. Go to a project and click **"Stage Project"**
3. Watch for **"Optimized for you"** badge on mission
4. Check token estimate below mission text

---

## Common Scenarios

### Scenario 1: Frontend-Focused Project

You're building a React UI with minimal backend.

**Configuration**:
```
Product Vision:           10
Project Description:       9
Tech Stack - Frontend:    10 (React is critical)
Tech Stack - Backend:      2 (Minimal - just API endpoints)
Codebase Summary:          6
Architecture:              4
```

**Result**: Agents focus on UI/UX, minimal backend noise. ~65% token reduction.

### Scenario 2: Backend-Heavy Microservice

Building a complex backend service with databases.

**Configuration**:
```
Product Vision:           10
Tech Stack - Backend:     10 (Critical)
Tech Stack - Database:    10 (Critical)
Architecture:              8 (Important patterns)
Codebase Summary:          7
Tech Stack - Frontend:     0 (Exclude - no UI)
```

**Result**: Agents focus on backend architecture. ~55% token reduction.

### Scenario 3: Maximum Token Reduction

You need minimal cost, willing to sacrifice some context.

**Configuration**:
```
Product Vision:            6 (Abbreviated)
Project Description:       6 (Abbreviated)
Codebase Summary:          2 (Minimal)
Architecture:              0 (Exclude)
Tech Stack:                4 (Abbreviated)
```

**Result**: Bare minimum context. ~80% token reduction. **Warning**: May reduce mission quality.

### Scenario 4: Full Context (No Reduction)

First-time project staging, want to see everything.

**Configuration**:
```
All fields: 10 (Full detail)
```

**Result**: Agents get complete context. 0% reduction. Useful for complex or unclear projects.

---

## Understanding "Optimized for You"

When you see this badge on a mission:

✅ **Your field priorities were applied**
✅ **Token reduction achieved**
✅ **Cost savings active**

If you DON'T see the badge:
- Using default priorities (not customized)
- No user configuration found
- Logged out when staging

---

## Tips for Effective Configuration

### DO:
- ✅ Keep Product Vision priority high (8-10)
- ✅ Set priorities based on project focus
- ✅ Experiment with different configurations
- ✅ Monitor token estimates after each change
- ✅ Use Serena for existing codebases

### DON'T:
- ❌ Set all fields to 10 (defeats the purpose)
- ❌ Set all fields to 0 (agents need context)
- ❌ Change priorities mid-project without re-staging
- ❌ Exclude critical technical stack information

### Pro Tips:
1. **Start Conservative**: Begin with priorities 6-8, then reduce
2. **Monitor Quality**: If agents seem confused, increase priorities
3. **Project Templates**: Save configurations for project types
4. **Iterate**: Adjust based on agent performance
5. **Balance**: 50-70% reduction is the sweet spot

---

## Troubleshooting

### "Agents aren't getting enough context"

**Symptoms**: Agents ask for missing information, produce generic code

**Fix**: Increase priorities for key fields (7-10 range)

### "Still seeing high token counts"

**Symptoms**: Token estimate shows 20K+ tokens

**Fix**:
1. Verify priorities saved (check My Settings)
2. Ensure "Optimized for you" badge shows
3. Try more aggressive reduction (priorities 4-6)

### "Serena context not appearing"

**Symptoms**: Toggle ON but no codebase info in mission

**Fix**:
1. Check Serena MCP is configured (Admin Settings → Integrations)
2. Verify project has codebase path set
3. Serena may be unavailable (graceful degradation - normal)

---

## Advanced: Understanding Token Metrics

### How Tokens Are Counted

1 token ≈ 4 characters of English text

**Example**:
```
"Build a user authentication system" = 8 tokens
10,000 characters ≈ 2,500 tokens
```

### Vision Document Breakdown

Typical 20K token vision document:
- **Section headers**: 500 tokens
- **Core features**: 5,000 tokens
- **Technical details**: 8,000 tokens
- **Architecture**: 3,000 tokens
- **Deployment**: 2,500 tokens
- **Examples/Notes**: 1,000 tokens

### Reduction Examples

**Priority 10 (Full)**:
- Input: 20,000 tokens
- Output: 20,000 tokens
- Reduction: 0%

**Priority 6 (Abbreviated)**:
- Input: 20,000 tokens
- Output: 10,000 tokens (headers + key bullets)
- Reduction: 50%

**Priority 2 (Minimal)**:
- Input: 20,000 tokens
- Output: 4,000 tokens (headers + first sentence)
- Reduction: 80%

---

## FAQ

**Q: Will this reduce mission quality?**
A: Not if configured correctly. Agents get the information they need, just more condensed.

**Q: Can I change priorities after staging?**
A: Yes, but you'll need to re-stage the project to apply new priorities.

**Q: Do different projects need different priorities?**
A: Often yes. Frontend projects prioritize UI stack, backend projects prioritize architecture.

**Q: What happens if I set everything to 0?**
A: Mission generation will fail. At least one field must have priority > 0.

**Q: Does this work for all AI tools?**
A: Yes. Field priorities work with Claude Code, Codex, Gemini CLI - any tool using GiljoAI MCP.

**Q: How do I reset to defaults?**
A: Click "Reset to Defaults" button in My Settings → Field Priorities tab.

---

## Related Documentation

- [Technical Documentation](../technical/FIELD_PRIORITIES_SYSTEM.md) - Deep dive into how it works
- [Stage Project Feature](../STAGE_PROJECT_FEATURE.md) - Complete feature overview
- [WebSocket Events Guide](../developer_guides/websocket_events_guide.md) - For developers

---

**Last Updated**: 2024-11-02
**Version**: 3.0.0
**Need Help?**: Check logs in `F:\GiljoAI_MCP\logs\` or contact support
