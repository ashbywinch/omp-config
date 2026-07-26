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

**Don't pre-bias the designer.** If you say "cards have too much info" the designer will remove everything. Frame neutrally.

**Existing features are evidence of user needs, not a sacred list.** Each feature was built because someone needed it. The designer should understand the underlying need, then decide whether to keep, change, or replace the feature. The goal is to meet the need better, not to preserve specific UI.

**The list vs detail split is about density, not removal.** Commute quality, school quality, and affordability badges belong on list cards — just condensed. The detail page gets full breakdowns.

**Wireframes must have working navigation.** No hidden CSS pages.

**Watch the thinking trace for fixation.** If the designer repeats the same sentence, it's stuck.

## Phase 0 — Discovery Conversation (main agent + user)

Ask ONE question at a time. Start with: **"What problem are you trying to solve?"**

Follow-ups:
- "Who uses this?"
- "Walk me through a typical session."
- "What information do you need at each step to make a decision?"
- "What's frustrating?"

Write findings as a personas doc and check it in.

## Phase 1 — Gather Context & Catalog Existing Features

Read every relevant source file. Build a feature inventory — for each feature, note what user need it likely serves.

Include in the inventory: every data field, interaction, state, and navigation element. Note what user problem each one solves.

## Phase 2 — Capture Screenshots

Browser at 375px and 1280px. `/tmp/page-name-1280.png`

## Phase 3 — Designer Task

The task MUST include:
1. Screenshots as absolute file mentions (`@/tmp/...`)
2. Personas & workflow from Phase 0
3. Project context from Phase 1
4. The feature inventory from Phase 1, framed as:
   - "These features exist today and are evidence of user needs. For each one, consider what user need it serves."
   - "You may redesign, replace, or remove any feature. If you remove something, explain what user need it was meeting and how your design addresses that need differently."
   - "The goal is to meet user needs better, not to preserve specific UI."
5. Instruction that list cards need condensed indicators for rapid scanning
6. Working navigation between pages

Do NOT include biased statements like "cards have too much info."

## Phase 4 — Present & Iterate

Show analysis + wireframe. Get feedback. Iterate.

## Phase 5 — Implement

Convert to production components once approved.
