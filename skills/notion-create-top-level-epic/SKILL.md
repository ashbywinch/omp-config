---
name: notion-create-top-level-epic
description: |
  Create high-level strategic Epics in Notion from business goals, with
  parent-child hierarchy, component mapping, and database entry setup.
---

# Create Top Level Epic

High-level strategic work packages from business goals.

## Prerequisites

- `ntn` CLI installed and authenticated (see `skill://notion-database-management`)
- Business goal or strategic objective
- Epics database ID: `20d3122e-1a13-81a1-8388-de5cebd1acb2`

## Process

### 1. Analyze Business Goal
- Review strategic context and business case
- Identify what work is needed
- Assess strategic impact

### 2. Conceptualize the Epic
- Define broad strategic scope (quarters, not weeks)
- Identify which component delivers the primary artifact
- Set priority level

### 3. Create in Notion
Create a page in the Epics database with Status: Draft (see `skill://notion-database-management` for page creation syntax).

Include these properties:
- **Epic Name**: `Epic [N]: [Strategic Title]`
- **Status**: Draft
- **Description**: Strategic overview, desired outcome, business justification

**Top-level epics must have Parent Epic explicitly cleared:**
```json
"Parent Epic": {"relation": []}
```

### 4. Set Parent Epic (if hierarchical breakdown)
Use the Parent Epic relation field. See `skill://notion-database-management` for relation syntax.

### 5. Validate
- [ ] Connects to documented business goals
- [ ] Scope sized for quarterly/annual planning
- [ ] Created as database entry (not sub-page)
- [ ] Parent-child relationships correctly set

## Hierarchy Rules

| Field | Purpose |
|---|---|
| **Parent Epic** | Hierarchical breakdown (Y is part of X) |
| **Dependencies** | Blocking relationships (X must finish before Y) |

- Child epics are database entries, not sub-pages
- Unique IDs per child (e.g., Epic 1.1, 1.2)
- An epic can have both a parent and dependencies
