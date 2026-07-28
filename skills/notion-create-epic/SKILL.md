---
name: notion-create-epic
description: |
  Convert a Top Level Epic into a Draft Epic in Notion — component mapping,
  strategic scope, dependencies, parent-child hierarchy.
---

# Create Epic

Creates a Draft Epic from a Top Level Epic.

## Prerequisites

- `ntn` CLI installed and authenticated (see `skill://notion-workbook`)
- Top Level Epic exists in the Epics database
- User approval before any Notion write

## Process

### 1. Validate Input
- Confirm Top Level Epic is valid and complete
- Review strategic objectives

### 2. Determine Component Mapping
- Identify which component delivers the primary artifact
- Verify component has DQS and playbooks

### 3. Define Epic Scope (User-Validated)
- Convert strategic objectives into tactical work boundaries
- Size for strategic planning horizons (quarters, not weeks)
- **SHOW FIRST, CREATE LATER**: Present to user before Notion creation
- **NO INVENTION**: Do not create fictional components

### 4. Create in Notion (Only After User Approval)
Create a page in the Epics database with Status: Draft (see `skill://notion-workbook` for page creation syntax).

Set the **Parent Epic** relation to link to the source Top Level Epic.

```json
"Parent Epic": {"relation": [{"id": "<TOP_LEVEL_EPIC_ID>"}]}
```

### 5. Validate
- [ ] Traceable from Top Level Epic to Draft Epic
- [ ] Single component with primary artifact
- [ ] Scope sized for strategic planning
- [ ] Dependencies are blocking, not hierarchical
- [ ] User approved before Notion write

## Hierarchy Rules

| Field | Use Case |
|---|---|
| **Parent Epic** | Hierarchical breakdown |
| **Dependencies** | Blocking relationships |
| **Both** | An epic can have both |

Each child epic maps to exactly one component.
