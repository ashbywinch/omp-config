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

These are mistakes made in previous passes — don't repeat them.

**Don't pre-bias the designer.** If you say "cards have too much info" the designer will remove everything, including info the user needs for skimming. Frame the question neutrally: "what information belongs at each stage of the workflow?" Let the designer discover the right balance.

**Preserve existing functionality unless there's a specific reason to remove it.** The designer doesn't know what features the user relies on. Explicitly instruct: "do not remove existing features (comments, provenance, triage buttons, commute breakdowns, etc.) unless you explain why they don't serve the workflow."

**The list vs detail split is about density, not removal.** Commute quality, school quality, and affordability ARE needed on the list page — just in condensed form (good/warn/bad badges rather than full breakdowns). The detail page should have the FULL breakdowns.

**Wireframes must have working navigation between pages.** Static pages hidden behind CSS display:none with no way to reach them are not useful.

**The designer's thinking trace shows when it gets stuck in a loop.** If the designer repeats the same sentence multiple times in its thinking, it's fixated. Cancel and retry with a clearer task.

## Common failure modes

1. **"Strip everything from cards"** — the designer interprets "reduce cognitive load" as "remove all data." Prevent by listing what MUST stay on cards (commute quality indicators, affordability, school quality, triage status).
2. **"Remove existing features"** — the designer doesn't know which features are important. Name them explicitly: provenance icons, comments, per-person commute breakdowns, triage buttons (save/dismiss/mark seen).
3. **"Detail page is incomplete"** — the designer focuses on the list and half-finishes the detail page. Ask for a complete wireframe for ALL pages.
4. **"No navigation"** — the designer creates separate pages in one HTML but no way to move between them. Require links or tabs.

## Phase 0 — Discovery Conversation (main agent + user)

Before any code or screenshots, learn about the problem space. Ask ONE question at a time, wait for the answer, then follow up.

Start with: **"What problem are you trying to solve? What's the bigger goal this tool supports?"**

Follow-up questions (one at a time):

**Understanding the users:**
- "Who uses this? Just you, or are there other people involved?"
- "When you're using it, what does a typical session look like?"

**Mapping the flow:**
- "What triggers you to open this tool?"
- "What do you need to accomplish before you close it again?"
- "Is there a step that takes too long or feels frustrating?"

**What info is needed at each step:**
- "When you're scanning the list, what information do you need to make a quick yes/no/maybe decision?"
- "What can wait until you open the detail page?"
- "Are there existing features you rely on that must be preserved?"

Write the findings as a personas doc and check it in.

## Phase 1 — Gather Context

Read the codebase: framework, design tokens, components, page structure, existing features.

List every existing feature the designer must preserve (comments, triage buttons, provenance, commute breakdowns, school data, etc.).

## Phase 2 — Capture Screenshots

Browser at 375px and 1280px. `/tmp/page-name-1280.png`

## Phase 3 — Designer Task

Spawn the designer with screenshots, personas, context, and the critical instructions below.

```
task agent=designer
     task="""UX/UI review and wireframe for [pages].

Your model is Gemini and can see images directly. The screenshots are attached.

## Attached screenshots
@/tmp/page-1280.png
@/tmp/page-375.png

## Personas & User Journeys
[From Phase 0 — include what info each person needs at the scan stage vs the evaluation stage]

## Project context
[Framework, tokens, components, existing features from Phase 1]

## Critical instructions
- Do NOT remove existing features unless you explain why. Existing features include: [list them].
- The list page needs ENOUGH info for rapid decision-making. Commute quality, affordability, and school quality must be visible on list cards in condensed form (e.g. good/warn/bad badges).
- The list vs detail split is about DENSITY not about removing data. Full breakdowns go on the detail page.
- Wireframes MUST have working navigation between pages (click card → detail, or tabs).
- All pages must be complete — don't focus on one page and leave others half-finished.

## Your task
1. UX/UI review of current pages — what's working, what's not, what information belongs at each workflow stage
2. Initial HTML/CSS wireframe addressing the issues

## Wireframe requirements
- Standalone HTML/CSS with design system (CSS variables)
- Responsive (375px and 1280px)
- Hover and focus states
- Preserves existing functionality described above
- Working navigation between pages

## Output format
### Analysis
[UX findings + UI findings + what's working + what was removed and why]

### Wireframe
[Complete HTML file(s)]"""
```

## Phase 4 — Present & Iterate

Show analysis + wireframe to user. Get feedback. Iterate.

## Phase 5 — Implement

Convert to production components once approved.
