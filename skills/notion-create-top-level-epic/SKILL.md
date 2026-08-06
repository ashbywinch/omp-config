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
- Database IDs (Epics, Value Streams): `skill://notion-database-management`

## Epic or Value Stream?

**Check for a done point first** — the definition and test live in `skill://epic-quality-standard`:

- Finishable work → Epic (Epics database)
- **No done point** — an ongoing area of activity (e.g. Lifelong Learning, Marketing, Personal News & Trends, Standards, Accessibility) → **Value Stream** in the Value Streams database, not an epic. It hosts finishable work as **child epics** (linked from the child epic via Parent Value Stream).

A "top level" ongoing goal is a value stream (optionally under a parent value stream), not a top-level epic.

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

### 4. Set Parent (if hierarchical breakdown)
Set **exactly one** of these on the child page — never both:

- Parent is an epic → `Parent Epic` relation
- Parent is a value stream → `Parent Value Stream` relation

See `skill://notion-database-management` for relation syntax.

### 5. Validate
- [ ] Connects to documented business goals
- [ ] Scope sized for quarterly/annual planning
- [ ] Created as database entry (not sub-page)
- [ ] Parent-child relationships correctly set
- [ ] Exactly one of Parent Epic / Parent Value Stream set (never both)
- [ ] If no done point → this should be a Value Stream, not an epic

## Hierarchy Rules

| Field | Purpose |
|---|---|
| **Parent Epic** | Hierarchical breakdown (Y is part of X, X is an epic) |
| **Parent Value Stream** | Epic hosted under a value stream |
| **Dependencies** | Blocking relationships (X must finish before Y) |

- Child epics are database entries, not sub-pages
- Unique IDs per child (e.g., Epic 1.1, 1.2)
- An epic can have both a parent and dependencies, but never both parent fields
- Relation mechanics (read-modify-write, mirroring): `skill://notion-database-management`
