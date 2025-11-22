# Handover 0241: EMERGENCY GUI Fix - Match Exact Screenshots

**Status**: 🚨 CRITICAL - Current implementation does NOT match design
**Priority**: P0 (Blocker)
**Estimated Effort**: 8-12 hours
**Tool**: 🌐 CCW (Cloud)
**Dependencies**: Must fix immediately before deployment

---

## 🚨 CRITICAL PROBLEM

**Current implementation (0240a + 0240b) does NOT match the reference screenshots.**

The GUI redesign was implemented based on a different PDF document and **completely missed the actual design requirements** shown in the reference screenshots:
- `F:\GiljoAI_MCP\handovers\Launch-Jobs_panels2\Launch Tab.jpg` (Slide 1A)
- `F:\GiljoAI_MCP\handovers\Launch-Jobs_panels2\IMplement tab.jpg` (Slide 3A)

---

## ❌ What's Wrong - Launch Tab

### Current Implementation (WRONG)
- 3 separate card columns side by side
- Stage button inside left column
- Launch button inside left column
- Panels have elevation shadows
- No unified container
- Agent cards in horizontal scroll

### Required Design (Slide 1A)
- **Single large rounded container** with light border encompassing everything
- **"Stage project" button** in **TOP LEFT corner** (yellow outlined, rounded)
- **"Launch jobs" button** in **TOP RIGHT corner** (greyed when disabled, yellow when ready)
- **"Waiting:"** status text in **center top** (yellow italic text)
- **3 panels inside container**: Project Description | Orchestrator Mission | Default Agent
- **Document icon** centered in empty Orchestrator Mission panel
- **Orchestrator card**: "Or" avatar (tan/beige color), "Orchestrator" text, lock icon, info icon on right
- **Agent Team**: Empty state below Orchestrator with scrollbar on right edge

---

## ❌ What's Wrong - Implement Tab

### Current Implementation (WRONG)
- Horizontal agent card grid
- Wrong table structure
- Wrong action icon layout
- Message input integrated into component

### Required Design (Slide 3A)
- **"Claude Subagents" toggle** in **TOP LEFT** with green dot indicator when ON
- **Pure table layout** (NO cards)
- **Table columns** (exact order):
  1. Agent Type (avatar + name)
  2. Agent ID (full UUID text, not truncated)
  3. Agent Status (yellow italic "Waiting." text)
  4. Job Read (checkmark column)
  5. Job Acknowledged (checkmark column)
  6. Messages Sent (numeric)
  7. Messages waiting (numeric)
  8. Messages Read (numeric)
  9. **Action icons on far right**: Yellow Play ▶ | Yellow Folder 📁 | White Info ℹ️
- **Message composer at BOTTOM**:
  - Dropdown button ("Orchestrator" selected) on left
  - "Broadcast" button next to dropdown
  - Text input field (dark with light border)
  - Yellow Send button (▶) on right

---

## ✅ Required Changes

### Launch Tab - Complete Redesign

**1. Container Structure**
```vue
<div class="launch-tab-container">
  <!-- Top Action Bar -->
  <div class="top-action-bar">
    <v-btn class="stage-button">Stage project</v-btn>
    <span class="status-text">Waiting:</span>
    <v-btn class="launch-button" disabled>Launch jobs</v-btn>
  </div>

  <!-- Main Content Area (single large rounded container) -->
  <div class="main-content-container">
    <!-- 3 Panels Row -->
    <div class="three-panels">
      <!-- Project Description Panel -->
      <div class="panel project-description">
        <div class="panel-header">Project Description</div>
        <div class="panel-content">
          {{ project.description }}
          <v-icon class="edit-icon">mdi-pencil</v-icon>
        </div>
      </div>

      <!-- Orchestrator Mission Panel -->
      <div class="panel orchestrator-mission">
        <div class="panel-header">Orchestrator Generated Mission</div>
        <div class="panel-content">
          <!-- Empty state: document icon -->
          <v-icon size="80" class="empty-icon">mdi-file-document-outline</v-icon>
        </div>
      </div>

      <!-- Default Agent Panel -->
      <div class="panel default-agent">
        <div class="panel-header">Default agent</div>
        <div class="panel-content">
          <!-- Orchestrator Card -->
          <div class="orchestrator-card">
            <v-avatar color="tan" class="agent-avatar">Or</v-avatar>
            <span class="agent-name">Orchestrator</span>
            <v-icon class="lock-icon">mdi-lock</v-icon>
            <v-icon class="info-icon">mdi-information</v-icon>
          </div>

          <!-- Agent Team Section -->
          <div class="agent-team-section">
            <div class="agent-team-header">Agent Team</div>
            <div class="agent-team-list">
              <!-- Empty state or agent list -->
            </div>
          </div>
        </div>
      </div>
    </div>
  </div>
</div>
```

**2. Critical Styling**
```scss
.launch-tab-container {
  padding: 20px;
  background: #0e1c2d; // Dark background

  .top-action-bar {
    display: flex;
    justify-content: space-between;
    align-items: center;
    margin-bottom: 20px;

    .stage-button {
      background: transparent;
      border: 2px solid #ffd700; // Yellow outlined
      color: #ffd700;
      border-radius: 8px;
      padding: 8px 16px;
      text-transform: none;
    }

    .status-text {
      color: #ffd700; // Yellow
      font-style: italic;
      font-size: 18px;
    }

    .launch-button {
      background: #666; // Grey when disabled
      color: #999;
      border-radius: 8px;
      padding: 8px 16px;
      text-transform: none;

      &:not(:disabled) {
        background: #ffd700; // Yellow when enabled
        color: #000;
      }
    }
  }

  .main-content-container {
    border: 2px solid rgba(255, 255, 255, 0.2); // Light border
    border-radius: 16px;
    padding: 30px;
    background: rgba(14, 28, 45, 0.5);

    .three-panels {
      display: grid;
      grid-template-columns: 1fr 1fr 1fr;
      gap: 20px;

      .panel {
        .panel-header {
          font-size: 14px;
          margin-bottom: 10px;
          color: #ccc;
          text-transform: none; // NOT uppercase
        }

        .panel-content {
          background: rgba(20, 35, 50, 0.8);
          border-radius: 8px;
          padding: 16px;
          min-height: 400px;
          color: #e0e0e0;
          position: relative;

          .edit-icon {
            position: absolute;
            bottom: 16px;
            right: 16px;
            color: #ccc;
            cursor: pointer;
          }

          .empty-icon {
            position: absolute;
            top: 50%;
            left: 50%;
            transform: translate(-50%, -50%);
            color: rgba(255, 255, 255, 0.15);
          }
        }
      }
    }
  }
}

.orchestrator-card {
  display: flex;
  align-items: center;
  background: rgba(255, 255, 255, 0.05);
  border: 1px solid rgba(255, 255, 255, 0.1);
  border-radius: 24px;
  padding: 8px 16px;
  margin-bottom: 20px;

  .agent-avatar {
    width: 32px;
    height: 32px;
    background: tan !important;
    color: #000;
    font-weight: bold;
    margin-right: 12px;
  }

  .agent-name {
    flex: 1;
    color: #fff;
  }

  .lock-icon, .info-icon {
    margin-left: 8px;
    color: #ccc;
  }
}
```

---

### Implement Tab - Complete Redesign

**1. Table Structure**
```vue
<div class="implement-tab-container">
  <!-- Claude Subagents Toggle -->
  <div class="claude-toggle-bar">
    <span>Claude Subagents</span>
    <div class="toggle-indicator" :class="{ active: claudeMode }"></div>
  </div>

  <!-- Agent Table Container -->
  <div class="table-container">
    <table class="agents-table">
      <thead>
        <tr>
          <th>Agent Type</th>
          <th>Agent ID</th>
          <th>Agent Status</th>
          <th>Job Read</th>
          <th>Job Acknowledged</th>
          <th>Messages Sent</th>
          <th>Messages waiting</th>
          <th>Messages Read</th>
          <th></th> <!-- Actions -->
        </tr>
      </thead>
      <tbody>
        <tr v-for="agent in agents" :key="agent.job_id">
          <!-- Agent Type: Avatar + Name -->
          <td>
            <v-avatar :color="getAgentColor(agent.type)" size="32">
              {{ getAgentAbbr(agent.type) }}
            </v-avatar>
            <span>{{ agent.type }}</span>
          </td>

          <!-- Agent ID: FULL UUID -->
          <td class="agent-id">{{ agent.job_id }}</td>

          <!-- Agent Status: Yellow italic "Waiting." -->
          <td class="status-text">Waiting.</td>

          <!-- Job Read: Checkmark or empty -->
          <td><v-icon v-if="agent.job_read">mdi-check</v-icon></td>

          <!-- Job Acknowledged: Checkmark or empty -->
          <td><v-icon v-if="agent.job_acknowledged">mdi-check</v-icon></td>

          <!-- Messages Sent -->
          <td>{{ agent.messages_sent || '' }}</td>

          <!-- Messages Waiting -->
          <td>{{ agent.messages_waiting || '' }}</td>

          <!-- Messages Read -->
          <td>{{ agent.messages_read || '' }}</td>

          <!-- Actions -->
          <td class="actions-cell">
            <v-btn icon="mdi-play" color="yellow" size="small"></v-btn>
            <v-btn icon="mdi-folder" color="yellow" size="small"></v-btn>
            <v-btn icon="mdi-information" color="white" size="small"></v-btn>
          </td>
        </tr>
      </tbody>
    </table>
  </div>

  <!-- Message Composer (Bottom) -->
  <div class="message-composer">
    <v-btn class="recipient-button">Orchestrator</v-btn>
    <v-btn class="broadcast-button">Broadcast</v-btn>
    <input type="text" class="message-input" placeholder="Type message..." />
    <v-btn icon="mdi-play" color="yellow" class="send-button"></v-btn>
  </div>
</div>
```

**2. Critical Styling**
```scss
.implement-tab-container {
  padding: 20px;

  .claude-toggle-bar {
    display: flex;
    align-items: center;
    gap: 12px;
    margin-bottom: 20px;
    color: #ccc;

    .toggle-indicator {
      width: 16px;
      height: 16px;
      border-radius: 50%;
      background: #666;

      &.active {
        background: #00ff00; // Green dot
      }
    }
  }

  .table-container {
    border: 2px solid rgba(255, 255, 255, 0.2);
    border-radius: 16px;
    padding: 20px;
    background: rgba(14, 28, 45, 0.5);
    margin-bottom: 20px;

    .agents-table {
      width: 100%;
      border-collapse: collapse;

      thead th {
        text-align: left;
        padding: 12px;
        color: #ccc;
        font-size: 13px;
        border-bottom: 1px solid rgba(255, 255, 255, 0.1);
      }

      tbody td {
        padding: 16px 12px;
        color: #e0e0e0;
        border-bottom: 1px solid rgba(255, 255, 255, 0.05);

        &.agent-id {
          color: #999;
          font-family: monospace;
          font-size: 11px;
        }

        &.status-text {
          color: #ffd700; // Yellow
          font-style: italic;
        }

        &.actions-cell {
          text-align: right;

          .v-btn {
            margin-left: 8px;
          }
        }
      }
    }
  }

  .message-composer {
    display: flex;
    gap: 12px;
    align-items: center;

    .recipient-button, .broadcast-button {
      background: transparent;
      border: 2px solid rgba(255, 255, 255, 0.3);
      color: #ccc;
      border-radius: 8px;
      padding: 8px 16px;
    }

    .message-input {
      flex: 1;
      background: rgba(20, 35, 50, 0.8);
      border: 2px solid rgba(255, 255, 255, 0.2);
      border-radius: 8px;
      padding: 12px 16px;
      color: #fff;
      font-size: 14px;

      &::placeholder {
        color: #666;
      }
    }

    .send-button {
      background: #ffd700;
      color: #000;
    }
  }
}
```

---

## 📋 Implementation Tasks

### Task 1: Launch Tab Complete Rewrite (4-6 hours)
- [ ] Remove current 3-column card layout
- [ ] Create single container with light border
- [ ] Position "Stage project" button in top left
- [ ] Position "Launch jobs" button in top right
- [ ] Add "Waiting:" status text in center top
- [ ] Create 3 equal-width panels inside container
- [ ] Add document icon to empty Orchestrator Mission
- [ ] Style Orchestrator card: tan avatar, lock icon, info icon
- [ ] Create Agent Team section below Orchestrator
- [ ] Add edit pencil icon to Project Description panel
- [ ] Match exact colors, borders, spacing from screenshot
- [ ] Test responsive behavior

### Task 2: Implement Tab Complete Rewrite (4-6 hours)
- [ ] Remove agent card grid completely
- [ ] Create pure table layout
- [ ] Add "Claude Subagents" toggle in top left
- [ ] Create table with exact column order from screenshot
- [ ] Display FULL Agent UUID (not truncated)
- [ ] Style Agent Status as yellow italic "Waiting."
- [ ] Add action icons: Yellow Play, Yellow Folder, White Info
- [ ] Position actions in far right column
- [ ] Create message composer at bottom
- [ ] Style dropdown/broadcast buttons with borders
- [ ] Add text input with dark background and light border
- [ ] Add yellow send button with play icon
- [ ] Match exact colors, spacing, borders from screenshot
- [ ] Test responsive behavior

---

## ✅ Success Criteria

**Launch Tab**:
- [ ] Matches screenshot Slide 1A pixel-perfect
- [ ] Single container with light rounded border
- [ ] Buttons in correct corners (top left, top right)
- [ ] "Waiting:" text centered at top
- [ ] 3 equal panels inside container
- [ ] Document icon in empty Orchestrator panel
- [ ] Orchestrator card styled exactly as shown
- [ ] Agent Team section below Orchestrator

**Implement Tab**:
- [ ] Matches screenshot Slide 3A pixel-perfect
- [ ] Claude Subagents toggle in top left
- [ ] Pure table layout (no cards)
- [ ] FULL UUID displayed in Agent ID column
- [ ] Yellow italic "Waiting." in Agent Status
- [ ] Action icons: Play, Folder, Info (yellow/white)
- [ ] Message composer at bottom
- [ ] Dropdown + Broadcast + Input + Send button

---

## 🚀 Execution Plan

**Tool**: CCW (Cloud) - Pure frontend styling work

**Approach**: Complete rewrite of both tabs to match exact screenshots

**Timeline**: 8-12 hours (4-6 hours per tab)

**Testing**: Side-by-side screenshot comparison after implementation

---

## 🎯 Critical Notes

1. **Ignore previous PDF** - Use ONLY the JPG screenshots as reference
2. **Pixel-perfect matching** - Colors, spacing, borders must match exactly
3. **No guessing** - If unsure about any detail, refer to screenshot
4. **Test with screenshots open** - Side-by-side comparison during development

---

**This is a P0 blocker. Current implementation cannot ship.**
