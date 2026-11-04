---
name: notion-task-status-management
description: |
  Manage Notion task status transitions — Draft→Ready→In Progress→
  Completed→Superseded with validation gates and Epic progress tracking.
---

# Task Status Management

Manage Task status transitions in Notion.

## Prerequisites

- `ntn` CLI installed and authenticated (see `skill://notion-database-management`)
- Tasks Database ID: `20d3122e-1a13-813a-9231-e7e086b2b86f`

## Status Definitions

| Status | What it means |
|---|---|
| **Draft** | The task's scope, desired outcome or success criteria are still being worked out. It is not described well enough for anyone to pick up and do. |
| **Ready** | The task is fully described: what "done" looks like is settled, and someone could start. If it is waiting on something else, that waiting is a dependency; it does not change the status. |
| **In Progress** | Someone is working on it now. |
| **Completed** | The deliverable exists and meets the task's success criteria. |
| **Superseded** | It was replaced, and the replacement exists. |

## Transition Logic

Each transition requires specific validation before updating.

Use PATCH to update the Status property on the task page (see `skill://notion-database-management` for syntax).

| From | To | Validate |
|---|---|---|
| Draft | Ready | Scope, desired outcome and success criteria are settled |
| Ready | In Progress | Owner actively working, environment set up |
| In Progress | Completed | All success criteria met, handoff done |
| In Progress | Ready (pause) | Work state saved, resumption plan clear |
| Any | Superseded | Business justification, replacement task created if needed |

## Epic Progress Calculation

Query all tasks related to an Epic (see `skill://notion-database-management` for query patterns).

```
Completed % = (Completed Tasks / Total Required Tasks) × 100
```

- **Completed** → counts toward completion
- **In Progress** → tracked as active work
- **Ready** → available for execution
- **Draft** → does NOT count until Ready
- **Superseded** → removed from calculation
