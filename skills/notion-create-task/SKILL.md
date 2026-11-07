---
name: notion-create-task
description: |
  Create properly structured Tasks in the Notion Tasks Database with parent
  Epic linkage, dependency mapping, and validation against `skill://task-quality-standard`.
---

# Create Task

Create a properly structured Task that is immediately executable.

## Prerequisites

- `ntn` CLI installed and authenticated (see `skill://notion-database-management`)
- Epic exists in Notion (the task's parent)
- Tasks Database ID: `20d3122e-1a13-813a-9231-e7e086b2b86f`

## The write gate, for tasks

A task is an external record, and this has gone wrong often enough to be stated
in the skill rather than assumed:

- **Show the exact title and desired outcome, and get a yes, before the page
  exists.** Not a summary of the plan, not a list of intended tasks — the words
  that will be written. One approval covers the set you showed; nothing beyond it.
- **A correction is a write too.** Changing a task you already created needs the
  same approval as creating it. "I had already told you the plan" is not approval
  of different words.
- **Never archive or trash a page as part of the workflow.** Trash is not a
  correction mechanism and not a tidy-up: it is invisible to every later reader
  and it is not yours to use. If a task is wrong, edit it in place. If it must
  go, say so and let the user remove it.
- **If you discover you wrote something unapproved, stop and say so.** Do not fix
  it with another unapproved write; do not delete the evidence of your mistake.
- **Never create a task whose provenance you cannot state**: which epic, which
  evidence, and which words the user approved.

## Process

### 1. Epic Context Analysis
Review the parent Epic in Notion (see `skill://notion-database-management` for reading pages). Identify the task's specific contribution to Epic completion.

### 2. Define Task
- **Name**: Action-oriented "Verb + Object" pattern (e.g., "Create Vision Document")
- **Desired Outcome**: Specific deliverable — reference the applicable quality standard in the task definition (e.g. `skill://task-quality-standard`). For code deliverables, the desired outcome should be clearly documented within the task itself.
- **Scope Boundaries**: Explicit inclusions and exclusions

### 3. Create in Notion
Create a page in the Tasks database (see `skill://notion-database-management` for page creation syntax).

Set these properties:
- **Task (Title)**: Action-oriented name
- **Status**: Ready
- **Related to Epics**: Link to parent Epic (relation)
- **Desired Outcome**: Rich text
- **Dependencies**: Any prerequisite task IDs
- **Related Business Goal**: Epic's strategic objective

### 4. Validate
- [ ] Task appears in Epic's Related Tasks view
- [ ] All required fields populated per `skill://task-quality-standard`
- [ ] Dependencies explicitly documented
- [ ] Success criteria are objective and measurable
- [ ] Task is immediately executable
