---
name: notion-create-epic
description: |
  Convert a Top Level Epic into a Draft Epic in Notion — component mapping,
  strategic scope, dependencies, parent-child hierarchy.
---

# Create Epic

Creates a Draft Epic from a Top Level Epic.

## Prerequisites

- `ntn` CLI installed and authenticated (see `skill://notion-database-management`)
- Top Level Epic exists in the Epics database
- User approval before any Notion write

## First: Epic or Value Stream?

**Decide before creating** — the definition, examples, and "does this work ever end?" test live in `skill://epic-quality-standard`:

- **Has a done point** (finishable work) → Epic, in the Epics database
- **No done point** (ongoing area of activity) → Value Stream, in the Value Streams database — NOT the Epics database. A value stream hosts finishable work as **child epics** (linked via the epic's Parent Value Stream).

**A value stream can never be under an epic.** If the item is a value stream and its would-be parent is an epic, that parent is also a mislabeled value stream — convert the parent chain first (see below), then place the new VS under the converted VS.

Database IDs and page-creation syntax: `skill://notion-database-management`.

When converting an existing epic into a value stream (it was misclassified, or its nature is ongoing):
1. Create the Value Stream page (same name, Value Stream ID next free)
2. Re-point the old epic's children: each child epic gets **Parent Value Stream** = the new VS (and its Parent Epic cleared, unless it also has an epic parent)
3. Move the old epic's Insights to the VS's **Key Insights 2** relation
4. Mark the old epic **Superseded** (never delete — traceability)
5. Repeat for any epic parent of the converted epic — it is likewise a mislabeled VS and must be converted bottom-up

## Process

### 1. Validate Input
- Confirm Top Level Epic is valid and complete
- Review strategic objectives

### 2. Determine Component Mapping
- Identify which component delivers the primary artifact
- Verify the component has a quality standard and associated skills/plans

### 3. Define Epic Scope (User-Validated)
- Convert strategic objectives into tactical work boundaries
- Size for strategic planning horizons (quarters, not weeks)
- **SHOW FIRST, CREATE LATER**: Present to user before Notion creation
- **NO INVENTION**: Do not create fictional components

### 4. Create in Notion (Only After User Approval)
Create a page in the Epics database with Status: Draft (see `skill://notion-database-management` for page creation syntax).

Set **exactly one** parent field on the child page:

- Parent is a value stream → `Parent Value Stream`
- Parent is an epic → `Parent Epic`

```json
"Parent Epic": {"relation": [{"id": "<PARENT_EPIC_ID>"}]}
```
```json
"Parent Value Stream": {"relation": [{"id": "<VALUE_STREAM_ID>"}]}
```

**Never set both.** The parent is always written on the CHILD page (the child points up). Relation write mechanics (read-modify-write, parent-field mirroring): `skill://notion-database-management`.

### 5. Validate
- [ ] Traceable from Top Level Epic to Draft Epic
- [ ] Single component with primary artifact
- [ ] Scope sized for strategic planning
- [ ] Dependencies are blocking, not hierarchical
- [ ] User approved before Notion write
- [ ] Exactly one of Parent Epic / Parent Value Stream set (never both)

## Hierarchy Rules

| Field | Use Case |
|---|---|
| **Parent Epic** | Hierarchical breakdown under another epic |
| **Parent Value Stream** | This epic is hosted under a value stream |
| **Dependencies** | Blocking relationships |
| **Both** | An epic can have a parent AND dependencies, but NEVER both parent fields |

Relation mechanics (read-modify-write, mirroring): `skill://notion-database-management`.
