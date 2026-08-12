---
name: epic-quality-standard
description: Required fields and validation rules for an Epic.
---

# Epic Quality Standard

An Epic is a tactical work package that converts a Top Level Epic into actionable development work.

## Epic vs Value Stream

| | Epic | Value Stream |
|---|---|---|
| **Definition** | A finishable piece of work with a done point | An ongoing area of activity with **no "done" point** — not a piece of work you can finish |
| **Contains** | Tasks (finishable) | Child **epics** (finishable work) and child value streams |
| **Scope** | Scoped / scope-able | Cannot contain scoped or scope-able work itself — it hosts it as child epics (that's the whole point) |
| **Examples** | "Side-by-Side Russian Reading", "Custom RSS Aggregator" | "Lifelong Learning", "Learning Russian", "Personal News & Trends", "Marketing", "Standards", "Accessibility" |

**Test**: "Does this work ever end?" If yes → Epic. If no → Value Stream.

**Where they live**: Epics live in the Epics database; Value Streams live in the **Value Streams** database (separate). A value stream "containing" an epic is expressed on the epic's **Parent Value Stream** relation.

**No top-level epics**: an epic is never a top-level page — every epic has exactly one parent, either an epic or a value stream. Top-level pages in the tree are value streams only: a life goal or a C-suite responsibility of the business. A product is never top-level — see `skill://business-org-model` for who owns what (product GMs report to the CTO).

**Value streams need KPIs**: a value stream must be able to have KPIs — the name should describe a measurable, ongoing outcome ("Connection to Roots"), not a vague area ("Home and Family").

**Hierarchy validity**: a value stream can NEVER be a child of an epic (an epic is finishable work; an ongoing value stream cannot be "part of" a finishable package). A value stream's parent, if any, is itself a value stream (or a mission). If a would-be epic turns out to be a value stream, any epic parent in its chain is likewise mislabeled and must be converted first.

## Status Lifecycle

**Draft** → Initial state after conversion from Top Level Epic. Strategic scope, sized for quarters.

**Refined** → Development-ready. Detailed scope, sized for weeks/months, with binary dependencies.

**Superseded** → Replaced (e.g. converted into a value stream — the VS page replaces the epic; children are re-pointed to the VS, then the old epic is marked Superseded for traceability).

## Required Fields

| Field | Type | Notes |
|---|---|---|
| Epic Name | title | Format: "Epic [Number]: [Title]" |
| Status | select | Draft, Refined, Ready, In Progress, Completed, or Superseded |
| Epic ID | number | Numeric identifier (top-level only; children use dotted titles) |
| Description | rich_text | Overview connecting to business purpose |
| Component | rich_text | Which component delivers the primary artifact |
| Parent Epic | relation | Hierarchical parent — **exactly one of Parent Epic / Parent Value Stream, never both** (empty for top-level epics) |
| Parent Value Stream | relation | The value stream this epic is under — **exactly one of Parent Epic / Parent Value Stream, never both** |
| Dependencies | relation | Blocking relationships (not hierarchical) |
| Insights | relation | Linked insight items |

## Validation Checklist

- [ ] Epic Name follows "Epic [N]: [Title]" formatting
- [ ] Status reflects readiness (Draft / Refined)
- [ ] Component mapping identifies exactly one component with a primary artifact
- [ ] Dependencies are **blocking** relationships, not hierarchical
- [ ] Dependencies are **binary** (complete/not complete)
- [ ] Scope is sized appropriately (Draft: quarters / Refined: weeks-months)
- [ ] **This is a finishable work package — if it has no done point it belongs in the Value Streams database, not here**
- [ ] Exactly ONE of Parent Epic / Parent Value Stream is set (never both, never neither except top-level)
- [ ] Insights use the "Insights" relation field (not legacy text field)
- [ ] When an epic's work is scheduled on the calendar, event descriptions must reference the epic or task ID

## Relation Write Rule

Relation mechanics (read-modify-write, parent-field mirroring) live in `skill://notion-database-management` — follow those when writing any relation (Insights, Parent Epic, Parent Value Stream, Dependencies).
