---
name: google-calendar
description: |
  Google Calendar operations via the `gcalcli` CLI — view schedules, check
  availability, create events, manage the day plan.
---

# Google Calendar

Calendar operations via `gcalcli` — usable from bash commands.

## Prerequisites

- `gcalcli` installed (`~/.local/bin/gcalcli`)
- Authenticated: `gcalcli init` (OAuth browser flow, one-time setup)

Add `~/.local/bin` to PATH if needed.

## Before Scheduling

**Always check the current time first:**
```bash
date '+%H:%M'
```
Never schedule events in the past. If a proposed start time has already passed, adjust the plan forward accordingly.

**Never add events without user approval first.** Present the proposed schedule and get explicit confirmation before writing to the calendar.

**REQUIRED: Notion task IDs in every calendar event.** Every work block event MUST include the relevant Notion task ID(s) or epic ID(s) in its description. Never create a work event without a Notion ID — it breaks traceability back to the work items in Notion.

## Rescheduling Flow

When a schedule needs to change (user couldn't start on time, plan shifted):

1. Check current time with `date '+%H:%M'`
2. Present the revised schedule for user approval
3. Once approved, delete the **old** events by search (use specific search text to avoid deleting correct events)
4. Add the new events with task references

## Common Pitfalls

- **Delete is broad**: `gcalcli delete` by search text deletes ALL matching events in the date range. Use specific, unique search terms — not generic words like "Break" or "Lunch" that might hit other days' events.
- **Duration is minutes**: `--duration 90` not `--duration "1:30"`.
- **Calendar name required**: Always pass `--calendar "Home"`. Without it, gcalcli prompts interactively and fails.
- **Task IDs in descriptions**: Every work block needs the Notion task/epic ID so the trace is clear.
- **Check time first**: Never assume what time it is. Run `date`.

## Common Operations

### List calendars
```bash
gcalcli list
```

### View today's agenda
```bash
gcalcli agenda
```

### View a specific date range
```bash
gcalcli agenda "2026-07-28" "2026-07-30"
```

### Quick-add an event
```bash
gcalcli quick "Meeting with team tomorrow 3pm"
```

### Delete events by search
```bash
gcalcli delete --calendar "Home" "Search Text" "2026-07-29" "2026-07-30" --iamaexpert
```
The `--iamaexpert` flag skips the confirmation prompt. Without it, delete is interactive.

### Add a detailed event
```bash
gcalcli add --calendar "Home" --title "Session" \
  --when "2026-07-29 10:00" --duration 120 --noprompt
```
`--duration` takes **minutes** as an integer (e.g. `60` for 1 hour, `30` for 30 minutes).
`--calendar` specifies which calendar to use. Use `gcalcli list` to see available calendars.
`--noprompt` skips interactive prompts for unfilled fields.

### Search for events
```bash
gcalcli search "keyword"
```

## Integration with PA Coordination

The PA Coordination skill uses this for:
- Checking the day plan / schedule
- Adding sessions to the calendar
- Replanning / rescheduling events
- Morning check-in agenda review
