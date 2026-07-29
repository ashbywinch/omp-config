---
name: epic-quality-standard
description: Required fields and validation rules for an Epic.
---

# Epic Quality Standard

An Epic is a tactical work package that converts a Top Level Epic into actionable development work.

## Status Lifecycle

**Draft** → Initial state after conversion from Top Level Epic. Strategic scope, sized for quarters.

**Refined** → Development-ready. Detailed scope, sized for weeks/months, with binary dependencies.

## Required Fields

| Field | Type | Notes |
|---|---|---|
| Epic Name | title | Format: "Epic [Number]: [Title]" |
| Status | select | Draft or Refined |
| Epic ID | number | Numeric identifier (top-level only; children use dotted titles) |
| Description | rich_text | Overview connecting to business purpose |
| Component | rich_text | Which component delivers the primary artifact |
| Parent Epic | relation | Hierarchical parent (empty for top-level) |
| Dependencies | relation | Blocking relationships (not hierarchical) |
| Insights | relation | Linked insight items |

## Validation Checklist

- [ ] Epic Name follows "Epic [N]: [Title]" formatting
- [ ] Status reflects readiness (Draft / Refined)
- [ ] Component mapping identifies exactly one component with a primary artifact
- [ ] Dependencies are **blocking** relationships, not hierarchical
- [ ] Dependencies are **binary** (complete/not complete)
- [ ] Scope is sized appropriately (Draft: quarters / Refined: weeks-months)
- [ ] Parent Epic field is cleared for top-level epics
- [ ] Insights use the "Insights" relation field (not legacy text field)
