# Context Configuration Guide

This guide explains how to configure context management in GiljoAI.

## Overview
GiljoAI gives you fine-grained control over what context your orchestrators receive using a 2-dimensional model:
- **Toggles** (WHAT to fetch) - On/off per category
- **Depth** (HOW MUCH detail) - Controls token usage per source

## Configuring Toggles

**Location**: My Settings → Context Configuration

**Steps**:
1. Navigate to My Settings
2. Click "Context" tab
3. Toggle each field group on or off

**Toggle States**:
- **Enabled** (toggle on) - Category included in orchestrator context
- **Disabled** (toggle off) - Category excluded entirely

**Example**:
- Enable "Tech Stack" if every orchestrator needs it
- Disable "Git History" if it's not useful for your current workflow
- Disable unused fields to keep context lean

## Configuring Depth

**Location**: My Settings → Context Configuration (depth controls per source)

**Steps**:
1. Navigate to My Settings
2. Click "Context" tab
3. Adjust depth controls for each enabled source

**Depth Controls**:

| Source | Options | Token Impact |
|--------|---------|--------------|
| Vision Documents | none/light/moderate/heavy | 0-24K tokens |
| 360 Memory | 1/3/5/10 projects | 500-5K tokens |
| Git History | 10/25/50/100 commits | 500-5K tokens |
| Agent Templates | minimal/standard/full | 400-2.4K tokens |
| Tech Stack | required/all | 200-400 tokens |
| Architecture | overview/detailed | 300-1.5K tokens |

**Tips**:
- Start with moderate/standard settings
- Increase depth if orchestrators lack context
- Decrease depth if hitting token limits
- Monitor token estimates in real-time

## Context Sources Explained

### 1. Product Context
**What**: Product name, description, core features
**When to use**: Always (keep enabled)
**Depth control**: On/Off toggle

### 2. Vision Documents
**What**: Uploaded vision documents (chunked)
**When to use**: For long-term product vision
**Depth control**: Chunking level (none to heavy)

### 3. Tech Stack
**What**: Programming languages, frameworks, databases
**When to use**: For technical decision-making
**Depth control**: Required only or all details

### 4. Architecture
**What**: Architecture patterns, API style, design patterns
**When to use**: For architectural decisions
**Depth control**: Overview or detailed

### 5. Testing Configuration
**What**: Quality standards, testing strategy, frameworks
**When to use**: For test-related tasks
**Depth control**: On/Off toggle

### 6. 360 Memory
**What**: Project closeout summaries and key outcomes
**When to use**: For learning from past projects
**Depth control**: Number of recent projects (1-10)

### 7. Git History
**What**: Aggregated git commits from all projects
**When to use**: For understanding code evolution
**Depth control**: Number of commits (10-100)

### 8. Agent Templates
**What**: Available agent templates
**When to use**: For agent selection decisions
**Depth control**: Detail level (minimal to full)

### 9. Project Context
**What**: Current project name, description, mission
**When to use**: Always (keep enabled)
**Depth control**: On/Off toggle

## Best Practices

1. **Keep Core Context Enabled**:
   - Product Context
   - Project Context
   - Tech Stack

2. **Enable Domain-Specific Sources As Needed**:
   - Architecture (for design work)
   - Testing (for QA tasks)
   - Vision Documents (for strategic work)

3. **Disable What You Don't Need**:
   - 360 Memory (if no past projects)
   - Git History (if not relevant)

4. **Adjust Depth Based on Task**:
   - High-level tasks: Lower depth (overview)
   - Detailed tasks: Higher depth (full details)

5. **Monitor Token Usage**:
   - Watch real-time estimates
   - Adjust if approaching limits
   - Balance detail vs. performance

## Troubleshooting

**Problem**: Orchestrator lacks important context
**Solution**: Enable the relevant source and increase depth

**Problem**: Hitting token limits frequently
**Solution**: Decrease depth settings, especially for Vision and 360 Memory

**Problem**: Orchestrator fetching irrelevant context
**Solution**: Disable unnecessary sources

**Problem**: Slow orchestrator startup
**Solution**: Reduce depth for large sources (Vision, 360 Memory, Git History)

## Advanced: Per-Project Configuration

Context configuration is currently user-level (applies to all projects). Future versions may support per-project overrides.
