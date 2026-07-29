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
