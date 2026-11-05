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

### 2. Deal with what has arrived
Before anything is planned, bring the record up to date. Run
`skill://check-what-arrived` — the inbox project's sweep of mail, calendar, phone
files, call log and WhatsApp, for both accounts, since the last sweep. Each thing
is proposed, agreed and recorded before moving on.

Do not proceed until every discovered item is logged or the user has agreed to
ignore it, every action item is identified, and every action item has a task.

### 3. Notion Inbox Triage
Triage through `skill://notion-insights-processing`: each item is categorised and
routed to its value stream or epic. The urgent ones are what the day gets planned
around.

### 4. Energy Assessment
Based on user's response, assess energy level:
- High: 4-5 hours focused work
- Medium: 2-3 hours
- Low: ≤1 hour

### 5. Day Plan Creation
Hand the day to `skill://day-planning` with the assessed hours as its budget: it
owns the layout, the breaks and the day plan file.

### 6. Presentation & Approval
Present in this format:
```
# Day Plan: [Date]
**Energy Level (X hours total)**

**Time** - Session Name (Duration)
*Context*
```

**Wait for explicit user approval** before writing anything to the calendar or day plan file.

### 7. Process Improvement
Check for any TODOs or improvements noted during the session. Apply them.

### 8. Complete
Write the approved day plan. Morning check-in does NOT include running work sessions — that's next.
