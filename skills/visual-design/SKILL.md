---
name: visual-design
description: |
  Use when the task involves screenshots, UI mockups, visual references,
  redesigning an existing UI, wireframing, UX review, or making the UI
  "look better". Provides a structured pipeline for screenshot-to-wireframe
  using the designer subagent's vision capability.
triggers: screenshot, wireframe, mockup, redesign, UI polish, visual fix, looks bad, make it pretty, design review, UX review, UI audit, improve the UI, make it look better
---

## Phase 2 — Capture Screenshots

Use `browser` at 375px and 1280px viewport widths.

**Wait for the page to actually render before screenshotting.** Don't use fixed timeouts. Wait for specific content elements: the card list on the list page, the section content on the detail page. If the page loads data from an API, wait for that data to appear.

For detail pages, navigate via the list page (click a card) rather than constructing URLs — this ensures the app state is properly initialized.

Name descriptively: `/tmp/page-name-1280.png`

**Critical: verify the screenshots are usable before proceeding.** A screenshot that's under 50KB for a desktop viewport is likely blank or mostly whitespace — the vision model won't be able to read it. Re-capture if needed.
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
