---
name: task-quality-standard
description: Required fields and validation rules for a Task.
---

# Task Quality Standard

A Task is a single execution unit with a clear deliverable and success criteria, linked to a parent Epic.

**One task is one action.** If a task's outcome needs two things done — and especially if they happen on
different days — it is two tasks. A task that can only be closed by doing something on Monday and
something else on Wednesday cannot be completed, scheduled, or chased as one thing.

## Required Fields

| Field | Type | Notes |
|---|---|---|
| Task (Title) | title | Action-oriented "Verb + Object" pattern, e.g. "Create Vision Document" |
| Status | select | Draft = not fully described yet; Ready = fully described and startable, whether or not it is waiting on something; then In Progress → Completed, or Superseded |
| Related to Epics (Related Tasks) | relation | Links to the parent Epic |
| Desired Outcome | rich_text | Specific deliverable, e.g. "Execute [skill/plan] to create [artifact]" |
| Dependencies | relation | Prerequisite task IDs |
| Related Business Goal | rich_text | Strategic context from the Epic |
| Relevant Deadlines | date | Target completion timeline |
| Scope Boundaries | (in task body) | Explicit inclusions and exclusions |

## Validation Checklist

- [ ] Title is action-oriented ("Verb + Object")
- [ ] Status is set appropriately
- [ ] Parent Epic is linked via "Related to Epics"
- [ ] Desired Outcome is specific and measurable
- [ ] Dependencies are explicitly documented (or empty if none)
- [ ] Success criteria are objective, not subjective
- [ ] When scheduled on the calendar, the event description must include the task's Notion ID
- [ ] Task is immediately executable without clarification
