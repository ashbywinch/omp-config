---
name: notion-refine-epic
description: |
  Refine a Draft Epic to development-ready (Refined) status with detailed
  scope, binary dependencies, and validation against `skill://epic-quality-standard`.
---

# Refine Epic

Transform a Draft Epic into a Refined (development-ready) Epic.

## Prerequisites

- `ntn` CLI installed and authenticated (see `skill://notion-database-management`)
- Draft Epic exists in the Epics database

## Process

### 1. Component Artifact Validation
- Confirm the Epic maps to exactly **one** component with a primary artifact
- Verify the component has a quality standard
- Ensure the artifact is significant enough for Epic-level planning

### 2. Load the Draft Epic
See `skill://notion-database-management` for reading a page's properties.

### 3. Update Epic Status and Properties
Change Status to **Refined**. Set Desired Outcome, Scope boundaries.

See `skill://notion-database-management` for PATCH syntax.

### 4. Link Insights via Relation
Use the **"Insights"** relation field (not the legacy "Key Insights" text field).

See `skill://notion-database-management` for relation property syntax.

### 5. Validate
- [ ] All required sections per `skill://epic-quality-standard`
- [ ] Component artifact clearly specified
- [ ] Business justification references actual business docs
- [ ] Scope boundaries realistic
- [ ] Epic sized for weeks/months, not days

## Key Rules

- **Binary Dependencies**: Complete or not complete — no "in progress"
- **Component Mapping**: One epic, one primary component artifact
- **Insights link via relations**, not by copying text into the page body
