---
name: visual-design
description: |
  Use when the task involves screenshots, UI mockups, visual references,
  redesigning an existing UI, wireframing, UX review, or making the UI
  "look better". Provides a structured pipeline for screenshot-to-wireframe
  using the designer subagent's vision capability.
triggers: screenshot, wireframe, mockup, redesign, UI polish, visual fix, looks bad, make it pretty, design review, UX review, UI audit, improve the UI, make it look better
---

# Visual Design Pipeline

Uses the `designer` subagent (must be configured to a vision-capable model via `modelRoles.designer` in config.yml). Screenshots passed as file mentions (`@/tmp/file.png`) resolve to inline images the model sees directly.

## Critical Lessons (read before every use)

**Don't pre-bias the designer.** If you say "cards have too much info" the designer will remove everything. Frame neutrally: "what information belongs at each stage?" Let it discover the balance.

**Catalog existing features from code, then tell the designer what to preserve.** Read every component file, list every data field, interaction, and state. Pass that list explicitly in the task. If you don't name a feature, the designer won't know it exists and will likely omit it.

**The list vs detail split is about density, not removal.** Commute quality, school quality, and affordability badges belong on list cards — just condensed. The detail page gets full breakdowns.

**Wireframes must have working navigation.** No hidden CSS pages.

**Watch the thinking trace for fixation.** If the designer repeats the same sentence, it's stuck in a loop.

## Phase 0 — Discovery Conversation (main agent + user)

Ask ONE question at a time. Start with: **"What problem are you trying to solve?"**

Follow-ups:
- "Who uses this?"
- "Walk me through a typical session."
- "What information do you need at each step to make a decision?"
- "What existing features do you rely on?"
- "What's frustrating?"

Write the findings as a personas doc and check it in.

## Phase 1 — Gather Context & Catalog Existing Features

Read every relevant source file. Build a concrete feature inventory — do not guess.

For each component file, document:
- Every data field displayed (badges, pills, icons, text values)
- Every interaction (clicks, hovers, toggles, cycles, drills-down)
- Every state (loading, empty, error, active, disabled)
- Every navigation element

Compile a section titled "Existing Features to Preserve" with the full list. This goes directly into the designer's task description.

## Phase 2 — Capture Screenshots

Browser at 375px and 1280px. `/tmp/page-name-1280.png`

## Phase 3 — Designer Task

The task MUST include:
1. Screenshots as absolute file mentions (`@/tmp/...`)
2. Personas & workflow from Phase 0
3. Project context from Phase 1
4. **The "Existing Features to Preserve" list from Phase 1**
5. Explicit instruction that the list card needs condensed commute/school/affordability indicators
6. Requirement for working navigation between pages

Do NOT include statements like "cards have too much info" or "X belongs on the detail page." Let the designer decide where things go, guided by the personas and the preservation list.

## Phase 4 — Present & Iterate

Show analysis + wireframe to user. Get feedback. Iterate.

## Phase 5 — Implement

Convert to production components once approved.
