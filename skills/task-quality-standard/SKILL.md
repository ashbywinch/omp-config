---
name: task-quality-standard
description: Required fields, status meanings and validation rules for a Task.
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
| Status | select | Draft, Ready, In Progress, Completed or Superseded — defined directly below |
| Related to Epics (Related Tasks) | relation | Links to the parent Epic |
| Desired Outcome | rich_text | Specific deliverable, e.g. "Execute [skill/plan] to create [artifact]" |
| Dependencies | relation | Prerequisite task IDs |
| Related Business Goal | rich_text | Strategic context from the Epic |
| Relevant Deadlines | date | Target completion timeline |
| Scope Boundaries | (in task body) | Explicit inclusions and exclusions |

## Status

| Status | What it means |
|---|---|
| **Draft** | The task's scope, desired outcome or success criteria are still being worked out. It is not described well enough for anyone to pick up and do. |
| **Ready** | The task is fully described: what "done" looks like is settled, and someone could start. If it is waiting on something else, that waiting is a dependency; it does not change the status. |
| **In Progress** | Someone is working on it now. |
| **Completed** | The deliverable exists and meets the task's success criteria. |
| **Superseded** | Something made it moot — the plan changed, a decision went another way, the work happened elsewhere, or it was a duplicate. It is not to be worked on further, and nothing has to have replaced it. |

## Do not invent the purpose

A task title names an activity. It does not say what the outcome is for, and the
two are not the same thing. "Make a task to triage the red rows" says what to do;
it says nothing about what the result has to answer, who will read it, or what
"done" looks like.

- **The Desired Outcome is the user's stated purpose, in their terms.** If they
  said why — "so we can prove we were responsible custodians of the funds",
  "so a random accuser has nothing to point at" — that reason *is* the outcome,
  and it goes in, quoted.
- **If the purpose is not stated, ask before writing the task.** One question:
  what is this for, and what would let you say it is finished? Do not fill the
  gap with the most plausible reading of the title.
- **Do not infer the deliverable from the field's usual shape.** A task called
  "find the POA documents" might want the documents, links to them, a written
  summary of the powers, or a decision about who may sign. Four different tasks.
- **Do not upgrade the user's shorthand into something tidier.** If they said
  "triage", write triage; do not silently widen it into "remediate", or narrow it
  into "count".
- **The test**: put the outcome text in front of the user and wait for them to say
  "yes, that is what I wanted". Not a reading of it you imagine — the text itself,
  under the external-writes rule (APPEND_SYSTEM.md).
- **When in doubt, leave it Draft** with the open question in the task body,
  rather than Ready with an invented purpose.

## Validation Checklist

- [ ] Title is action-oriented ("Verb + Object")
- [ ] Status is set appropriately
- [ ] Parent Epic is linked via "Related to Epics"
- [ ] Desired Outcome is specific and measurable
- [ ] Desired Outcome states the purpose the user gave — not one inferred from the title
- [ ] Dependencies are explicitly documented (or empty if none)
- [ ] Success criteria are objective, not subjective
- [ ] When scheduled on the calendar, the event description must include the task's Notion ID
- [ ] Task is immediately executable without clarification
