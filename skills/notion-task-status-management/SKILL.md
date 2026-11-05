---
name: notion-task-status-management
description: |
  Manage Notion task status transitions — Draft→Ready→In Progress→
  Completed, with Superseded reachable from any status — validation gates
  and Epic progress tracking.
---

# Task Status Management

Manage Task status transitions in Notion.

## Prerequisites

- `ntn` CLI installed and authenticated (see `skill://notion-database-management`)
- Tasks Database ID: `20d3122e-1a13-813a-9231-e7e086b2b86f`

## Status Definitions

What each status means is defined in `skill://task-quality-standard`. This skill covers the moves
between them.

## Transition Logic

Each transition requires specific validation before updating.

Use PATCH to update the Status property on the task page (see `skill://notion-database-management` for syntax).

| From | To | Validate |
|---|---|---|
| Draft | Ready | Scope, desired outcome and success criteria are settled |
| Ready | In Progress | Owner actively working, environment set up |
| In Progress | Completed | All success criteria met, handoff done |
| In Progress | Ready (pause) | Work state saved, resumption plan clear |
| Any | Superseded | Say what made it moot; link the replacement only if one exists |

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
