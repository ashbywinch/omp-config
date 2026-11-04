---
name: morning-checkin
description: |
  Morning check-in flow — conversational opening, energy assessment, inbox
  triage, day planning with breaks, and user approval of the schedule.
---

# Morning Check-in

Sets up a productive, energy-aligned workday.

## Process

### 1. Conversational Opening
Ask "Good morning! How are you feeling today?" — wait for their response.

### 2. Notion Inbox Triage
Query the Insights DB for urgent items (see `skill://notion-database-management`). Identify urgent items for day planning.

### 3. Energy Assessment
Based on user's response, assess energy level:
- High: 4-5 hours focused work
- Medium: 2-3 hours
- Low: ≤1 hour

### 4. Day Plan Creation
Hand the day to `skill://day-planning` once the energy is known. The routine does
not compose the schedule itself: the layout rules, the break structure and the
day plan file all live there, so that a day planned outside a check-in and a day
planned inside one come out the same.

### 5. Presentation & Approval
Present in this format:
```
# Day Plan: [Date]
**Energy Level (X hours total)**

**Time** - Session Name (Duration)
*Context*
```

**Wait for explicit user approval** before writing anything to the calendar or day plan file.

### 6. Process Improvement
Check for any TODOs or improvements noted during the session. Apply them.

### 7. Complete
Write the approved day plan. Morning check-in does NOT include running work sessions — that's next.
