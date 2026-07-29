---
name: notion-execute-task
description: |
  Execute a Notion task with quality gates — dependency verification, status
  tracking, deliverable creation, DQS validation, and handoff.
---

# Execute Task

Execute a defined Task systematically with quality gates.

## Prerequisites

- `ntn` CLI installed and authenticated (see `skill://notion-database-management`)
- Task in Notion with "Ready" status
- All dependencies satisfied

## Process

### 1. Load Task Details
Read the task page in Notion (see `skill://notion-database-management`). Review deliverables, success criteria, dependencies.

### 2. Verify Dependencies
Check each dependency's Status property.

### 3. Start Execution
Update Status to **"In Progress"** via PATCH (see `skill://notion-database-management`).

### 4. Create Deliverable
Follow the referenced playbook or DQS.

### 5. Quality Validation
- DQS compliance
- Success criteria met

### 6. Complete and Handoff
Update Status to **"Completed"**. Then update the parent Epic's progress (query all tasks related to the Epic, count Completed vs total).

See `skill://notion-database-management` for PATCH syntax and query patterns.

## Escalation

| Issue | Action |
|---|---|
| Scope needs clarification | Escalate to Epic owner |
| Resource unavailable | Escalate to planning |
| Can't meet DQS | Escalate before proceeding |
