---
name: google-calendar
description: Put one event on a Google Calendar — read the day, check the slot, decide who reads that calendar, then write, move or delete it. Composing a whole day is skill://day-planning; repairing gcalcli is skill://gcalcli-auth.
---

# Google Calendar

One event at a time. Planning a day's schedule is `skill://day-planning`;
a broken `gcalcli` token is `skill://gcalcli-auth`.

## Rules

- **Never** schedule in the past. `date '+%Y-%m-%d %H:%M'` first.
- **Never** write without checking the slot: `gcalcli agenda <from> <to>` or
  free/busy. A collision you created is yours, and the calendar cannot later
  tell you which of the two was wanted.
- **Never** write without approval of that specific event: title, day, time,
  calendar. Approval of something else is not approval of this.
- **Never** derive a time from an unrelated event. Related work runs
  back-to-back deliberately — a visit and the notes from that visit belong in
  sequence. "Both are evening things" is not a relationship.
- **Never** put an event on a calendar without knowing who reads it. Which
  account and calendar an event belongs on is the workspace's own fact, recorded
  in its calendar skill.
- **Never** create an event that stands for work without its Notion task ID when
  a task exists — detail longer than a few lines lives in Notion and the event
  references it (`skill://day-planning`).

## Commands

`gcalcli` needs `--calendar` on writes; without it, it prompts and fails.

```bash
date '+%Y-%m-%d %H:%M'                        # before anything scheduled
gcalcli list                                  # calendars available
gcalcli agenda 2026-11-07 2026-11-08          # what is already there
gcalcli search "keyword"                      # find an event
gcalcli add --calendar "Home" --title "Session" \
  --when "2026-11-07 10:00" --duration 45 --noprompt
```

`--duration` is **minutes** (`--duration 90`, never `"1:30"`).

`gcalcli delete` by search text deletes **every** match in the date range: use
unique text, a narrow range, and never a generic word like "Break".

## Via the MCP tools

Where a workspace grants calendar scope, the Google Workspace MCP servers expose
`list_calendars`, `get_events`, `query_freebusy` and `manage_event`
(create/update/delete/rsvp). Same rules; `manage_event` can also delete, which
is a write like any other.
