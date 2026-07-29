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

ALL operations must go through this skill first. Never execute domain skills directly.

## User Profile Check

Before any routing, check if a user profile exists. If missing, create one first before proceeding.

## Routing Table

### Morning Check-in / Greetings
User says "good morning", "good afternoon", "hey", "hi" — any session-starting greeting:
1. Check the day plan / schedule
2. Identify next session based on current time and completion status
3. Coordinate session execution

### Inbox Processing
User requests inbox/insights processing:
- Route to `skill://notion-insights-processing`

### Backlog Grooming
User requests backlog grooming or work organization:
- Route to `skill://notion-work-backlog`

### Strategic / Big Picture
User expresses lack of direction, asks "what should I do?", wants to figure out goals:
- Route to Strategic Foundation: Vision → Mission → Strategy
- Then to `skill://notion-create-top-level-epic`

### Tactical / Execution
User has a strategy but needs next steps: "break this down", "what should I do first":
- Route to `skill://notion-create-epic` and `skill://notion-create-task`

### Create Artifact
User wants to create any business artifact:
- Route to the appropriate artifact creation skill/plan

### PR Creation
User requests pull request creation:
- Route to the PR workflow

### Schedule Changes
User requests schedule changes, day replanning:
- Route to Google Calendar coordination (`gcalcli`)

## Session Coordination Flow

1. Load the current day plan
2. Identify next session from schedule
3. Execute the session with the appropriate skill
4. Track completion and update state

## Success Criteria

- User requests are properly routed to appropriate skills
- Sessions execute in order
- Incomplete items are captured for future planning
- State is maintained across sessions
