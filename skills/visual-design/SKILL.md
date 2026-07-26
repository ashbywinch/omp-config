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

**Existing features are evidence of user needs, but don't guess what those needs are — ask the user.** The features were built for reasons, but only the user can tell you what those reasons are and which ones still matter.

**The list vs detail split is about density, not removal.** Commute quality, school quality, and affordability badges belong on list cards — just condensed. The detail page gets full breakdowns.

**Wireframes must have working navigation.** No hidden CSS pages.

**Watch the thinking trace for fixation.** If the designer repeats the same sentence, it's stuck.

## Phase 0 — Discovery Conversation (main agent + user)

Ask ONE question at a time. Start with: **"What problem are you trying to solve?"**

Follow-ups (one at a time):
- "Who uses this?"
- "Walk me through a typical session."
- "What information do you need at each step to make a decision?"
- "What's frustrating?"

After you have a picture of their workflow, reference specific features from the code and ASK what they're for:
- "I see the cards show commute times — how do you use those when scanning?"
- "There are Save/Dismiss/Seen buttons — what does each one mean in your process?"
- "There's a financial line with a monthly cost and a delta — what do you look for there?"
- "I see comments per person — when do you use those?"

Do NOT guess what features are for. Ask. The user knows their own needs.

**Write findings as a personas doc and check it in. The personas doc must contain ONLY:**
- Who the users are and what they care about
- What they need to accomplish at each stage
- What they need to know to make decisions
- What frustrates them

**The personas doc must NEVER contain:**
- Design decisions ("there should be a button for X")
- Layout suggestions ("the list page should show Y")
- UI patterns ("one tap to Z", "provenance on every value")

If you catch yourself writing implementation details, stop and rephrase as a user need. "The user needs to understand how a number was calculated" not "there should be a provenance icon on every value."
## Phase 1 — Gather Context & Catalog Existing Features

Read every relevant source file. Build a feature inventory. For each feature, note:
- What it does
- What file it lives in
- Your hypothesis about what need it serves (to be verified in Phase 0)

## Phase 2 — Capture Screenshots

Browser at 375px and 1280px. `/tmp/page-name-1280.png`

## Phase 3 — Designer Task

The task MUST include:
1. Screenshots as absolute file mentions (`@/tmp/...`)
2. Personas & workflow from Phase 0 (including what the user said each feature is for)
3. Project context from Phase 1
4. The feature inventory framed as:
   - "These features exist today. Here's what the user told me each one is for: [user's own words]."
   - "You may redesign, replace, or remove any feature. If you remove something, explain what user need it was meeting and how your design addresses that need differently."
   - "The goal is to meet user needs better, not to preserve specific UI."
5. Instruction that list cards need condensed indicators for rapid scanning
6. Working navigation between pages

Do NOT include biased statements like "cards have too much info."

## Phase 4 — Present & Iterate

Show analysis + wireframe. Get feedback. Iterate.

## Phase 5 — Implement

Convert to production components once approved.
