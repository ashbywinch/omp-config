---
name: backlog-grooming
description: |
  Backlog grooming session — review processed insights, organise epics into
  themed sub-epics, clarify ambiguous tickets, break down epics into tasks,
  prioritise the work backlog.
---

# Backlog Grooming

Transform work items into an actionable, organised backlog.

## Process

### 1. Review Current State
Query the Epics and Tasks databases (see `skill://notion-database-management`) to see existing work.

### 2. Identify Work Items
Review any recently created epics or insights that need task breakdown.

### 3. Epic Organization & Clarification
For each epic that has accumulated processed insights, before task breakdown:
- **Survey the epic fully**: its `Insights 1`, `Related Tasks`, and `Child Epics` (mechanics: `skill://notion-database-management`).
- **Read every insight in full** — never propose structure from a truncated preview.
- **Group into themed sub-epics** when the epic mixes unrelated concerns. Name sub-epics after a phase with a concrete deliverable (`Epic X.Y: <Title>`), parent them at creation (see `skill://epic-quality-standard`), and move insights per the relation write rule (see `skill://notion-database-management`).
- **Flag anything unimplementable** — an insight you could not implement correctly from its text alone. Ask the user one ticket at a time; append the clarification to the ticket's `Content`, keeping the original text. Never guess.
- **Surface dependencies in dedicated fields** — an insight whose work depends on another's becomes an epic-level `Dependencies` relation (or a task dependency at breakdown, see `skill://task-quality-standard`). Never store dependencies in Processing Notes.
- **Order the clusters by priority** (urgent items first) before breaking into tasks.

**Group so each group is executable as a whole** — no half blue-sky, no internal dependency pauses; the tree should encode execution order (phases as epics), so a group can be run end-to-end without stopping.

**Every epic needs a purpose-in-life Definition of Done beyond its ticket list** — what are we actually trying to achieve? The purpose may surface extra tickets not yet thought of; a DoD that just lists the subtickets is not a DoD.

**Never create tickets for making tickets.** Make the correct tickets in the first place — no "we'll make tickets later", no "until a future VS exists". If work is future-gated, the gating ticket is a real ticket with real content.

**Placement of per-repo implementation work** follows `skill://business-org-model` (under the repo's own app value stream, never the enablement tree).

### 4. Task Breakdown
For each epic or work item:
- Break into actionable tasks
- Create tasks in Notion (see `skill://notion-create-task`)
- Link each to its parent Epic

### 5. Organisation & Prioritisation
- Validate dependencies and sequencing
- Check scope boundaries
- Prioritise based on strategic importance

### 6. Integration Validation
Verify new tasks are properly linked and the backlog is coherent.

## Scope

**In scope:** Converting epics and insights into structured tasks, prioritising, organizing.

**Out of scope:** Processing raw inbox items (handled by `skill://notion-insights-processing`), strategic planning (handled by epic creation skills).
