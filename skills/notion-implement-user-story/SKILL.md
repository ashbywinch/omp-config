---
name: notion-implement-user-story
description: |
  Execute a software development Epic from Notion — load task details via
  ntn, plan using TDD, create pull requests, track completion.
---

# Implement User Story

Execute a software development Epic by reading task details from Notion, implementing with TDD, and creating a pull request.

## Prerequisites

- `ntn` CLI installed and authenticated (see `skill://notion-workbook`)
- Epic or Task ID referencing a Notion record
- Target codebase with development tools

## Process

### 1. Load Epic/Task from Notion
- **⚠️ ALL task IDs refer to Notion tasks — do not search local codebase**

For a Task ID:
```bash
ntn api v1/pages/<TASK_ID> | jq '.properties'
```

For an Epic:
```bash
ntn api v1/pages/<EPIC_ID> | jq '.properties'
```

If searching by name, query the Epics database (see `skill://notion-workbook`).

Focus on: description, acceptance criteria, architecture references, dependencies, technical specs.

### 2. Plan
- Create task breakdown based on Epic requirements
- Review codebase structure
- **Mandatory user approval** before code changes

### 3. Implement using Strict TDD
**One failing test at a time:**
1. **Red**: Write ONE test for ONE behavior — verify it fails
2. **Green**: Write minimal code to make it pass
3. **Refactor**: Clean up while keeping tests passing
4. Every 3-5 cycles, architectural review

### 4. Quality Assurance
- Full test suite (no regressions)
- Formatters and linters
- Verify acceptance criteria from Notion

### 5. Review with User
- Demonstrate acceptance criteria met
- User reviews code
- Make modifications

### 6. Create Pull Request
- Clean repo state
- PR with comprehensive description
- Link to original Epic/requirements

### 7. Update Task Status
Mark the task as Completed in Notion (see `skill://notion-workbook` for PATCH syntax).

## Key Rules

- All task IDs are Notion tasks — don't search local files
- User approval required before code changes
- TDD is mandatory
- PR must reference the original Notion Epic
