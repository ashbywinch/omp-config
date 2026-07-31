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

## Process

### 1. Epic Context Analysis
Review the parent Epic in Notion (see `skill://notion-database-management` for reading pages). Identify the task's specific contribution to Epic completion.

### 2. Define Task
- **Name**: Action-oriented "Verb + Object" pattern (e.g., "Create Vision Document")
- **Desired Outcome**: Specific deliverable — reference the applicable quality standard in the task definition (e.g. `skill://vision-quality-standard`). For code deliverables, the desired outcome should be clearly documented within the task itself.
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
