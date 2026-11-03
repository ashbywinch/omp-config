---
name: task-quality-standard
description: Required fields and validation rules for a Task.
---

# Task Quality Standard

A Task is a single execution unit with a clear deliverable and success criteria, linked to a parent Epic.

## Required Fields

| Field | Type | Notes |
|---|---|---|
| Task (Title) | title | Action-oriented "Verb + Object" pattern, e.g. "Create Vision Document" |
| Status | select | Draft → Ready → In Progress → Completed → Superseded |
| Related to Epics (Related Tasks) | relation | Links to the parent Epic |
| Desired Outcome | rich_text | Specific deliverable, e.g. "Execute [skill/plan] to create [artifact]" |
| Dependencies | relation | Prerequisite task IDs |
| Related Business Goal | rich_text | Strategic context from the Epic |
| Relevant Deadlines | date | Target completion timeline |
| Scope Boundaries | (in task body) | Explicit inclusions and exclusions |

## No Invented Requirements

The Desired Outcome and Scope Boundaries contain only what the user asked for. Never add:

- a form of confirmation they didn't ask for ("written confirmation", "a signed copy")
- exception handling they didn't ask for ("what to do if a dose is missed")
- documentation or artefacts they didn't ask for ("a checklist", "notes in Drive")
- extra approvals, review steps or sign-offs

Each of those is a requirement, and writing one into a ticket puts work in front of the user that they never asked for. If a task looks incomplete, ask — do not fill the gap yourself.

Titles too: record the objective in the user's own terms. Replacing "contact X to tell them Y" with a more analytical "decide whether to contact X" changes what the task is, and drops the action the user asked for.

When restoring an item you wrongly dropped, re-read everything the user said about it and carry all of it. Restoring the headline action while dropping the conditions attached to it is the same error twice.

## Validation Checklist

- [ ] Title is action-oriented ("Verb + Object")
- [ ] Status is set appropriately
- [ ] Parent Epic is linked via "Related to Epics"
- [ ] Desired Outcome is specific and measurable
- [ ] Dependencies are explicitly documented (or empty if none)
- [ ] Success criteria are objective, not subjective
- [ ] When scheduled on the calendar, the event description must include the task's Notion ID
- [ ] Desired Outcome and Scope Boundaries contain only what the user asked for — no invented confirmations, exception handling, artefacts or approvals
- [ ] Task is immediately executable without clarification
