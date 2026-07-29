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
| Related to Epics | relation | Links to the parent Epic |
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
- [ ] Task is immediately executable without clarification
