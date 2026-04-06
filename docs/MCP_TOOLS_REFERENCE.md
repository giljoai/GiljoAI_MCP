# GiljoAI MCP: Tools Reference

## Overview

GiljoAI MCP exposes 29 tools to connected AI coding tools. Every tool requires a
valid API key passed as a Bearer token. Tenant isolation is enforced server-side;
agents cannot cross tenant boundaries.

Tools are organized by category below. Tool names match the exact MCP registrations.

---

## Discovery

### health_check

**Description:** Check MCP server health status.

**Parameters:** None.

**Returns:** Server status and connectivity details.

---

### discovery

**Description:** Discover available system categories and configuration for the
current tenant. Call this before creating projects to see valid `project_type` values.

**Parameters:**

| Parameter | Type | Required | Description |
|-----------|------|----------|-------------|
| category | str | Yes | What to look up. Valid value: `project_types`. |

**Returns:** List of items with `abbreviation`, `label`, and `color` fields.

---

## Project Management

### create_project

**Description:** Create a new project bound to the active product. Projects are
classified by taxonomy: `project_type` plus `series_number` form a serial such as
`FE-0001`. Call `discovery(category='project_types')` first to see valid types.
The project is created as inactive; activate it from the web dashboard.

**Parameters:**

| Parameter | Type | Required | Description |
|-----------|------|----------|-------------|
| name | str | Yes | Project name. |
| description | str | Yes | Human-written project description (user requirements). |
| project_type | str | No | Taxonomy type abbreviation (e.g. `FE`, `BE`, `INFRA`, `DOCS`). Must match a pre-existing category. If unrecognized, the project is created without taxonomy. |
| series_number | int | No | Sequential number within the type series (1-9999). Use 0 for auto-assign. |

**Returns:** Created project record including `project_id` and serial.

---

### update_project_mission

**Description:** Save the orchestrator's mission plan to the database. Called by the
orchestrator after creating an execution strategy. The project `description` holds
user requirements (input); `mission` holds the orchestrator's plan (output). Triggers
a `project:mission_updated` WebSocket event.

**Parameters:**

| Parameter | Type | Required | Description |
|-----------|------|----------|-------------|
| project_id | str | Yes | ID of the project to update. |
| mission | str | Yes | Orchestrator's execution plan. |

**Returns:** Updated project record.

---

### close_project_and_update_memory

**Description:** Close a project and write a 360 Memory entry with a sequential
history entry. Called by the orchestrator at project completion. Triggers a
`product_memory_updated` WebSocket event.

**Parameters:**

| Parameter | Type | Required | Description |
|-----------|------|----------|-------------|
| project_id | str | Yes | ID of the project to close. |
| summary | str | Yes | Narrative summary of what was accomplished. |
| key_outcomes | list[str] | Yes | List of concrete outcomes delivered. |
| decisions_made | list[str] | Yes | List of architectural or design decisions made. |
| force | bool | No | Close even if agents are still active. Default: `false`. |

**Returns:** Confirmation of project closure and memory update.

---

## Agent Lifecycle

### spawn_agent_job

**Description:** Create a specialist agent job for execution. Called by the
orchestrator during staging to delegate work. Returns a `job_id` and a thin prompt
(approximately 10 lines). The agent calls `get_agent_mission()` to fetch the full
mission. Creates a database record linking the agent to the project.

**Parameters:**

| Parameter | Type | Required | Description |
|-----------|------|----------|-------------|
| agent_display_name | str | Yes | Human-readable agent name shown in the dashboard. |
| agent_name | str | Yes | Internal agent identifier matching an agent template. |
| mission | str | Yes | The specific task this agent must accomplish. |
| project_id | str | Yes | ID of the parent project. |
| phase | int | No | Execution phase number for ordering. |
| predecessor_job_id | str | No | `job_id` of the job that must complete before this one starts. |

**Returns:** `job_id` and thin spawn prompt for the agent.

---

### get_pending_jobs

**Description:** Get pending jobs for an agent type with multi-tenant isolation.
Used by agents checking for new work.

**Parameters:**

| Parameter | Type | Required | Description |
|-----------|------|----------|-------------|
| agent_display_name | str | Yes | Display name of the agent type to query. |

**Returns:** List of pending job records for the agent type.

---

### get_agent_mission

**Description:** Fetch agent-specific mission and context. Called by any agent
immediately after receiving a thin prompt from `spawn_agent_job`. This is the
agent's first action. Returns the targeted mission for this specific agent, not
the full project vision. Idempotent.

**Parameters:**

| Parameter | Type | Required | Description |
|-----------|------|----------|-------------|
| job_id | str | Yes | The job ID from the spawn prompt. |

**Returns:** Full agent mission, project context, and operating instructions.

---

### update_agent_mission

**Description:** Update an agent's mission or execution plan. Called by the
orchestrator during staging to persist its own execution plan. Enables fresh-session
orchestrators to retrieve their plan via `get_agent_mission()` in a later session.

**Parameters:**

| Parameter | Type | Required | Description |
|-----------|------|----------|-------------|
| job_id | str | Yes | The orchestrator's own job ID. |
| mission | str | Yes | Updated mission or execution plan text. |

**Returns:** Updated job record.

---

### set_agent_status

**Description:** Set agent status. Use `blocked` when the agent needs help, `idle`
when monitoring other agents, or `sleeping` for periodic check-in. Replaces the
former `report_error` tool.

**Parameters:**

| Parameter | Type | Required | Description |
|-----------|------|----------|-------------|
| job_id | str | Yes | The agent's job ID. |
| status | str | Yes | One of: `blocked`, `idle`, `sleeping`. |
| reason | str | No | Human-readable explanation of the status. |
| wake_in_minutes | int | No | For `sleeping` status: minutes until the agent should wake. |

**Returns:** Updated job status record.

---

### report_progress

**Description:** Report incremental progress. Send a `todo_items` array and the
backend calculates percent and step counts automatically.

**Parameters:**

| Parameter | Type | Required | Description |
|-----------|------|----------|-------------|
| job_id | str | Yes | The agent's job ID. |
| todo_items | list[dict] | No | Full replacement list of to-do items. Each item has `title` and `done` fields. |
| todo_append | list[dict] | No | Items to append to the existing list without overwriting completed steps. |

**Returns:** Updated progress record.

---

### complete_job

**Description:** Mark a job as completed with results. The agent stores a structured
result that the orchestrator can retrieve via `get_agent_result()`.

**Parameters:**

| Parameter | Type | Required | Description |
|-----------|------|----------|-------------|
| job_id | str | Yes | The agent's job ID. |
| result | dict | Yes | Structured result containing `summary`, `artifacts`, and `commits`. |

**Returns:** Confirmation of job completion.

---

### get_agent_result

**Description:** Fetch the completion result of a finished agent job. Returns the
structured result stored when the agent called `complete_job`. Use this to read what
a predecessor agent accomplished.

**Parameters:**

| Parameter | Type | Required | Description |
|-----------|------|----------|-------------|
| job_id | str | Yes | The job ID of the completed agent. |

**Returns:** Structured result dict from the completed job.

---

### get_workflow_status

**Description:** Monitor workflow progress across all project agents. Returns counts
of agents by status and a `progress_percent` value from 0 to 100. Use
`exclude_job_id` to omit the calling orchestrator's own job from the counts.

**Parameters:**

| Parameter | Type | Required | Description |
|-----------|------|----------|-------------|
| project_id | str | Yes | ID of the project to monitor. |
| exclude_job_id | str | No | Job ID to exclude from counts (typically the orchestrator's own ID). |

**Returns:** Agent counts by status and overall `progress_percent`.

---

### reactivate_job

**Description:** Resume work on a completed job after receiving a follow-up message.
Only works when the job status is `blocked` (automatically set when a message arrives
for a completed agent). After reactivating, use `report_progress` with `todo_append`
to add new steps without overwriting completed ones.

**Parameters:**

| Parameter | Type | Required | Description |
|-----------|------|----------|-------------|
| job_id | str | Yes | The job ID to reactivate. |
| reason | str | No | Explanation of why work is resuming. |

**Returns:** Updated job record with new status.

---

### dismiss_reactivation

**Description:** Acknowledge a post-completion message without resuming work. Returns
the job to `complete` status. Use when the incoming message is informational and
requires no action.

**Parameters:**

| Parameter | Type | Required | Description |
|-----------|------|----------|-------------|
| job_id | str | Yes | The job ID to dismiss. |
| reason | str | No | Explanation of why no action was taken. |

**Returns:** Updated job record.

---

## Messaging

### send_message

**Description:** Send a message to one or more agents. Use `to_agents=["all"]` for
broadcast.

**Parameters:**

| Parameter | Type | Required | Description |
|-----------|------|----------|-------------|
| to_agents | list[str] | Yes | List of agent IDs to address. Use `["all"]` for broadcast. |
| content | str | Yes | Message body. |
| project_id | str | Yes | Project context for the message. |
| from_agent | str | Yes | Sender identifier. |
| message_type | str | No | Message classification. Default: `direct`. |
| priority | str | No | Message priority. Default: `normal`. |

**Returns:** Created message record.

---

### receive_messages

**Description:** Receive pending messages for the current agent with optional
filtering.

**Parameters:**

| Parameter | Type | Required | Description |
|-----------|------|----------|-------------|
| agent_id | str | No | Filter messages to a specific agent ID. |
| limit | int | No | Maximum number of messages to return. Default: `10`. |
| exclude_self | bool | No | Exclude messages sent by this agent. Default: `true`. |
| exclude_progress | bool | No | Exclude progress-report messages. Default: `true`. |
| message_types | list[str] | No | Filter to specific message type strings. |

**Returns:** List of pending message records.

---

### list_messages

**Description:** List messages with optional filters. Broader than `receive_messages`;
returns all matching messages regardless of read state.

**Parameters:**

| Parameter | Type | Required | Description |
|-----------|------|----------|-------------|
| agent_id | str | No | Filter by agent ID. |
| status | str | No | Filter by message status string. |
| limit | int | No | Maximum number of messages to return. Default: `50`. |

**Returns:** List of message records matching the filters.

---

## Context and Memory

### fetch_context

**Description:** Unified context fetcher. Retrieves product and project context by
category with depth control. A single call to this tool replaces nine individual
context tools. Categories and their approximate token costs:

- `product_core`: ~100 tokens
- `vision_documents`: 0-24K tokens
- `tech_stack`: 200-400 tokens
- `architecture`: 300-1.5K tokens
- `testing`: 0-400 tokens
- `memory_360`: 500-5K tokens
- `git_history`: 500-5K tokens
- `agent_templates`: 400-2.4K tokens
- `project`: ~300 tokens
- `self_identity`: agent template content

**Parameters:**

| Parameter | Type | Required | Description |
|-----------|------|----------|-------------|
| product_id | str | Yes | ID of the product to fetch context for. |
| project_id | str | No | ID of a specific project for project-scoped context. |
| agent_name | str | No | Agent name for `self_identity` category. |
| categories | list[str] | No | List of category strings. Defaults to all categories. |
| depth_config | dict | No | Per-category depth overrides. |
| output_format | str | No | Response format. Default: `structured`. |

**Returns:** Structured context object keyed by category.

---

### write_360_memory

**Description:** Write a 360 memory entry for project completion or agent transition.
Appends to the product's `sequential_history`. Called by the orchestrator on
completion or by agents when passing work to another agent.

**Parameters:**

| Parameter | Type | Required | Description |
|-----------|------|----------|-------------|
| project_id | str | Yes | ID of the project being recorded. |
| summary | str | Yes | Narrative summary of the work done. |
| key_outcomes | list[str] | Yes | Concrete outcomes delivered. |
| decisions_made | list[str] | Yes | Architectural or design decisions made. |
| entry_type | str | No | Type of entry. Default: `project_completion`. |
| author_job_id | str | No | Job ID of the agent writing the entry. |

**Returns:** Confirmation that the memory entry was appended.

---

## Vision Documents

### gil_get_vision_doc

**Description:** Retrieve a product's vision document with extraction instructions.
Call without `chunk` first to get metadata (`total_chunks`, `extraction_instructions`).
Then call with `chunk=1`, `chunk=2`, and so on to retrieve each chunk's content one
at a time. Read all chunks before calling `gil_write_product`.

**Parameters:**

| Parameter | Type | Required | Description |
|-----------|------|----------|-------------|
| product_id | str | Yes | ID of the product whose vision document to retrieve. |
| chunk | int | No | Chunk index to fetch. Omit on first call to get metadata only. |

**Returns:** On first call: metadata with `total_chunks` and `extraction_instructions`.
On subsequent calls: the text content of the requested chunk.

---

### gil_write_product

**Description:** Write structured product fields extracted from vision document
analysis. Performs a merge-write: only fields that are provided are updated. Creates
child table rows (`tech_stack`, `architecture`, `test_config`) on the first write.
`target_platforms` must be from: `windows`, `linux`, `macos`, `android`, `ios`,
`web`, `all`.

**Parameters:**

| Parameter | Type | Required | Description |
|-----------|------|----------|-------------|
| product_id | str | Yes | ID of the product to update. |
| product_name | str | No | Product name. |
| product_description | str | No | Short product description. |
| core_features | str | No | Key features of the product. |
| programming_languages | str | No | Primary programming languages. |
| frontend_frameworks | str | No | Frontend frameworks in use. |
| backend_frameworks | str | No | Backend frameworks in use. |
| databases | str | No | Databases in use. |
| infrastructure | str | No | Infrastructure and hosting description. |
| target_platforms | list[str] | No | Target platform identifiers. |
| architecture_pattern | str | No | High-level architecture pattern. |
| design_patterns | str | No | Design patterns applied. |
| api_style | str | No | API style (e.g. REST, GraphQL). |
| architecture_notes | str | No | Additional architecture notes. |
| quality_standards | str | No | Quality and coding standards. |
| testing_strategy | str | No | Overall testing approach. |
| testing_frameworks | str | No | Testing frameworks in use. |
| test_coverage_target | int | No | Target test coverage percentage. |
| summary_33 | str | No | AI-generated summary at 33% compression. |
| summary_66 | str | No | AI-generated summary at 66% compression. |

**Returns:** Updated product record.

---

## Tasks

### create_task

**Description:** Create a new task bound to the active product. Requires an active
product to be set.

**Parameters:**

| Parameter | Type | Required | Description |
|-----------|------|----------|-------------|
| title | str | Yes | Task title. |
| description | str | Yes | Detailed task description. |
| priority | str | No | Priority level. Default: `medium`. |
| category | str | No | Task category for grouping. |
| assigned_to | str | No | Agent or user to assign the task to. |

**Returns:** Created task record.

---

## Setup and Export

### giljo_setup

**Description:** First-time setup. Downloads slash commands and agent templates as a
ZIP and installs them with default models. Run once after connecting. To customize
models later, run `/gil_get_agents` (or `$gil-get-agents` for Codex CLI).

**Parameters:**

| Parameter | Type | Required | Description |
|-----------|------|----------|-------------|
| platform | str | No | Target platform: `claude_code`, `codex_cli`, `gemini_cli`. Default: `auto` (detects from MCP client info). |

**Returns:** Installation result and confirmation. Emits `setup:bootstrap_complete` WebSocket event.

---

### generate_download_token

**Description:** Generate a one-time download URL for agent templates or slash
commands. The URL is valid for 15 minutes.

**Parameters:**

| Parameter | Type | Required | Description |
|-----------|------|----------|-------------|
| content_type | str | Yes | What to generate a download URL for (e.g. `agent_templates`, `slash_commands`). |
| platform | str | No | Target platform. Default: `claude_code`. |

**Returns:** One-time download URL and expiry time.

---

### get_agent_templates_for_export

**Description:** Export agent templates formatted for the target CLI platform.
Returns pre-assembled files for Claude Code and Gemini CLI, or structured data
for Codex CLI. Emits a `setup:agents_downloaded` WebSocket event.

**Parameters:**

| Parameter | Type | Required | Description |
|-----------|------|----------|-------------|
| platform | str | Yes | Target platform: `claude_code`, `codex_cli`, `gemini_cli`. |

**Returns:** Agent template files or structured data ready for the target platform.

---

### submit_tuning_review

**Description:** Submit product context tuning proposals after comparing current
product context against recent project history. Call this after analyzing the tuning
comparison prompt.

**Parameters:**

| Parameter | Type | Required | Description |
|-----------|------|----------|-------------|
| product_id | str | Yes | ID of the product to tune. |
| proposals | list[dict] | Yes | List of tuning proposals. Each proposal identifies a field and a suggested change. |
| overall_summary | str | No | Narrative summary of the tuning analysis. |

**Returns:** Confirmation that proposals were recorded.

---

## Orchestrator Context

### get_orchestrator_instructions

**Description:** Fetch context for the orchestrator to create a mission plan. Called
by the orchestrator at project start (Step 1 of the staging workflow) or during the
implementation phase to refresh context. Returns the project description (user
requirements), prioritized context fields, and an `agent_templates` list for
discovering specialists. The orchestrator analyzes this input and creates an execution
plan. Token estimate: approximately 4,500 with context exclusions applied.

**Parameters:**

| Parameter | Type | Required | Description |
|-----------|------|----------|-------------|
| job_id | str | Yes | The orchestrator's own job ID. |

**Returns:** Project description, context fields, and available agent templates.

---

## Tool Count Summary

| Category | Tools |
|----------|-------|
| Discovery | health_check, discovery |
| Project Management | create_project, update_project_mission, close_project_and_update_memory |
| Agent Lifecycle | spawn_agent_job, get_pending_jobs, get_agent_mission, update_agent_mission, set_agent_status, report_progress, complete_job, get_agent_result, get_workflow_status, reactivate_job, dismiss_reactivation |
| Messaging | send_message, receive_messages, list_messages |
| Context and Memory | fetch_context, write_360_memory |
| Vision Documents | gil_get_vision_doc, gil_write_product |
| Tasks | create_task |
| Setup and Export | giljo_setup, generate_download_token, get_agent_templates_for_export, submit_tuning_review |
| Orchestrator Context | get_orchestrator_instructions |
| **Total** | **29** |
