---
name: notion-work-backlog
description: |
  Create and maintain organized Work Backlogs in Notion — organize epics,
  tasks, and insights with scope boundaries and execution plans.
---

# Work Backlog

Create and maintain organized Work Backlog documents.

## Prerequisites

- `ntn` CLI installed and authenticated (see `skill://notion-database-management`)

## Process

### 1. Review Current State
Query the Epics and Tasks databases to see existing work (see `skill://notion-database-management` for query patterns).

### 2. Strategic Alignment
- Review top level epics to understand business priorities
- Map components that deliver strategic outcomes

### 3. Epic Organization
- Convert top level epics into component-mapped epics
- Document dependencies and sequencing
- Rank by strategic importance

### 4. Task Breakdown
- Break epics into actionable tasks
- Create tasks in Notion (see `skill://notion-create-task`)
- Link each task to its parent Epic via "Related to Epics"

### 5. Insight Integration
- Query the Insights DB for unprocessed items
- Link insights to epics via the "Insights" relation field (not text copying)

### 6. Scope Boundary Management
- Define what is/isn't included in each container
- Verify all work items fit appropriate containers

## Key Rules

- Every epic maps to a component with a primary artifact
- Scope boundaries must be explicit
- Insights link via Notion relations, not text copying
- Tasks link to parent Epics via "Related to Epics" relation
