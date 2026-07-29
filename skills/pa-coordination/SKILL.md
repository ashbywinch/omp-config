---
name: pa-coordination
description: |
  Entry point for sessions. Routes user intents to the appropriate skills —
  morning check-ins, inbox processing, backlog grooming, strategic/tactical
  planning, and session coordination.
---

# PA Coordination Operations

Entry point for all coordination activities. Routes user triggers to the appropriate skills.

## Critical Rule

ALL operations MUST go through `skill://session`. Never execute domain skills directly. Route like this: `skill://session` with Session Type="Backlog Grooming" → session executes `skill://notion-work-backlog`.

## User Profile Check

Before any routing, check if a User Profile exists at `Operational Planning/PA Coordination/User Profile.md`. If missing, create one first.

## Operational Triggers

| When user says... | Route to `skill://session` with Session Type... |
|---|---|
| "good morning" / greeting | `"Morning Check-in"` |
| "start scheduled session" | Type from day plan |
| "inbox processing" | `"Inbox Processing"` (which runs `skill://notion-insights-processing`) |
| "backlog grooming" / work organization | `"Backlog Grooming"` (which runs `skill://notion-work-backlog`) |
| "update the day plan" / "replan the day" | `"Day Planning"` (which runs `skill://google-calendar`) |
| "create a PR" | `"PR Workflow"` |
| "create [artifact]" | `"Artifact Creation"` |

## Strategic Request Routing

### Strategic Foundation (life direction, big picture)
User expresses lack of direction, asks "what should I do?", lacks vision/mission:
- Route to Vision → Mission → Strategy, then to `skill://notion-create-top-level-epic`

### Subjective Evaluation (choose between options)
User has options to compare, needs criteria to decide:
- Route to subjective evaluation process

### Business Development (what to work on next)
User needs strategic guidance, completed a milestone, unsure of sequence:
- Route to business development sequencing

### Tactical Planning (break it down)
User has strategy but needs next steps:
- Route to `skill://notion-create-epic` and `skill://notion-create-task`

## Anti-Patterns (do NOT route here)

| Request type | Use instead |
|---|---|
| Simple lookup ("What is X?") | Knowledge/document lookup |
| Procedural ("How do I configure Y?") | Instruction/guide lookup |
| Binary decision with clear criteria | Direct analysis |
| Already has defined criteria | Standard evaluation |

## Critical Lessons (NEVER REPEAT)

- **Complete all scheduled sessions** — do not skip scheduled work
- **Finish task splitting** — if breaking down work, finish ALL splitting before ending
- **Capture incomplete items** — any unfinished work MUST go to the Notion inbox
- **Process in order** — urgent items before grooming before planning

## Session Flow

1. Check user profile exists
2. Load the day plan from `Operational Planning/PA Coordination/Day plan.md`
3. Identify next session based on current time and completion status
4. Present plan to user for approval before executing
5. Execute session using the appropriate skill
6. Track completion and update state
7. Capture any incomplete items to the inbox

## Subcomponents

- **Work Preferences**: Check for work style preferences
- **Daily Schedule**: Calendar management via `skill://google-calendar`
- **Session**: Session tracking and state management
- **Inbox**: Processing via `skill://notion-insights-processing`

## State Management

- Track current coordination state
- Manage cross-session dependencies
- Handle error recovery and state restoration
