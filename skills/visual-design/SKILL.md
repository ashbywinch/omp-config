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

**Key lessons from actual use:**
- File mentions MUST use absolute paths (`@/tmp/file.png`), not relative — subagent CWD differs
- The designer subagent may use `inspect_image` as a fallback — this is fine when the model is the same
- Don't fight the tools the agent chooses. `inspect_image` uses the same @vision model if configured
- Write a personas doc first and check it in — it structures the conversation and gives the designer context

## Phase 0 — Discovery Conversation (main agent + user)

Before any code or screenshots, learn about the problem space. Ask ONE question at a time, wait for the answer, then follow up. Do not list multiple questions in one message.

Start with: **"What problem are you trying to solve? What's the bigger goal this tool supports?"**

Follow-up questions (one at a time, drawn from below):

**Understanding the users:**
- "Who uses this? Just you, or are there other people involved?"
- "When you're using it, what does a typical session look like? Walk me through it."
- "What's the first thing you want to know when you open it? What's the second?"

**Mapping the flow:**
- "What triggers you to open this tool? A new property? A decision point?"
- "What do you need to accomplish before you close it again?"
- "Is there a step that takes too long or feels frustrating?"

**Finding priorities:**
- "If you could change one thing about how it works today, what would it be?"
- "What information matters most at the very start? What can wait?"
- "Is there anything the current version does well that you don't want to lose?"

Write the findings as a personas doc and check it in before proceeding. This structures the designer's context and gives future readers a reference.

## Phase 1 — Gather Context

Read the codebase: framework, design tokens, components, page structure.

## Phase 2 — Capture Screenshots

Browser at 375px and 1280px. `/tmp/page-name-1280.png`

## Phase 3 — Designer: Analysis + Initial Wireframe

Spawn the designer with screenshots, personas, and context. The designer returns BOTH the analysis AND an initial wireframe in one response. The wireframe MUST have working navigation between pages — either separate HTML files per page, or proper interactive navigation (click card → detail, tabs to switch views). No hidden CSS toggle with no way to reach the other page.

```
task agent=designer
     task="""UX/UI review and initial wireframe for [page/screen names].

Your model is Gemini and can see images directly. The screenshots are attached as inline images.

## Attached screenshots
@/tmp/page-1280.png
@/tmp/page-375.png

## Personas & User Journeys
[From Phase 0 discussion — concise persona descriptions and workflow]

## Project context
[Framework, tokens, components from Phase 1]

## Your task
1. UX/UI review of current pages (what's working, what's not)
2. Initial HTML/CSS wireframe addressing the issues you found

## Wireframe requirements
- Standalone HTML/CSS with design system (CSS variables)
- Responsive (375px and 1280px)
- Hover and focus states
- Preserves functionality from the personas
- **Navigation between pages MUST work** — either separate HTML files linked together, or interactive navigation within one file (click card → detail, tabs to switch). Do NOT hide pages behind CSS display:none with no way to reach them.

## Output format
### Analysis
[UX findings + UI findings + what's working]

### Wireframe
[Complete HTML file(s)]"""
```

## Phase 4 — Present & Iterate

Show analysis + wireframe to user. Get feedback. If the wireframe needs changes, either:
- Spawn the designer again with updated requirements
- Or render the wireframe, screenshot it, and have the designer self-review (spawn again with screenshots of the rendered output)

## Phase 5 — Implement

Convert to production components once approved.
