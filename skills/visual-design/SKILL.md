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

Designer subagent must be configured to a vision-capable model via `modelRoles.designer`. Screenshots passed as file mentions (`@/tmp/file.png`) resolve to inline images.

## Phase 0 — Discovery Conversation

Ask ONE question at a time. Start with: "What problem are you trying to solve?"

Follow-ups:
- "Who uses this?"
- "Walk me through a typical session."
- "What information do you need at each step to make a decision?"
- "What's frustrating?"

After you understand the workflow, go through every feature found in the code and ASK the user what it's for. Do not guess.

Write a personas doc and check it in. It must contain ONLY user needs, never implementation details.

## Phase 1 — Gather Context

Read the codebase: framework, design tokens, components, page structure.

## Phase 2 — Capture Screenshots

Browser at 375px and 1280px. `/tmp/page-name-1280.png`

## Phase 3 — Designer Task

Include: screenshots, personas, project context, feature inventory (in user's own words). Frame features as evidence of user needs, not sacred UI.

DO NOT include biased statements like "cards have too much info."

## Phase 4 — Iteration

When the designer returns a wireframe:

1. **Open it in the browser** and screenshot it at 375px and 1280px
2. Get feedback from the user about what's wrong
3. **Spawn the designer again with the wireframe screenshots** (not the HTML source) plus specific clarifications about what needs to change and why

This is faster because:
- The designer sees its own work as images, not source code
- No re-reading the full HTML on every pass
- Aligns with how the vision model works naturally

If the feedback is complex, include both the wireframe screenshots AND the previous analysis so the designer has full context without re-parsing HTML.

## Phase 5 — Implement

Convert to production components once approved.
