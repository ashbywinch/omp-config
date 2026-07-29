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
Check the current time with `date` — never assume. Propose a schedule:
- First session starts 15-30 min after check-in
- 15-min breaks every 45-75 minutes
- 60-min lunch break
- Match session count and length to energy level

Include Notion task IDs in calendar event descriptions.

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
