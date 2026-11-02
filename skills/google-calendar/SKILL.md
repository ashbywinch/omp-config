---
name: google-calendar
description: Read and schedule Google Calendar events — the rules that decide whether an event may be written, where it goes and what it must carry, plus the gcalcli commands and their traps.
---

# Google Calendar

Scheduling is a write with a time and an audience. The rules below are the
whole job; the commands at the end are mechanics. `gcalcli` is the primary
interface here; the workspace MCP servers can also read and write calendar, and
every rule applies equally to both. Repairing a broken `gcalcli` token is
`skill://gcalcli-auth`.

## Rules

- **Never** write an event without checking the target day first
  (`gcalcli agenda <from> <to>`, or free/busy). Two events in one slot is a
  defect you created, and the calendar cannot tell you afterwards which one was
  wanted.
- **Never** schedule in the past. Run `date '+%Y-%m-%d %H:%M'` first.
- **Never** write without approval of the specific event: title, day, time,
  calendar. Approval of the plan is not approval of the event.
- **Never** derive a time from an unrelated event. Related work runs
  back-to-back deliberately — a visit and the notes from that visit belong in
  sequence. "Both are evening things" is not a relationship.
- **Never** put a work block in the calendar without its Notion task ID when one
  exists. If the full detail is longer than a few lines it belongs in Notion and
  the event references it; detail that fits in a few lines goes in the
  description.
- **Never** put an event on a calendar without knowing who reads it. Which
  account and calendar an event belongs on is a decision, not a default — a
  workspace with more than one account records it in its own calendar skill.

## Common operations

`gcalcli` needs `--calendar` on writes; without it, it prompts and fails.

```bash
date '+%Y-%m-%d %H:%M'                       # before anything scheduled
gcalcli list                                 # calendars available
gcalcli agenda 2026-11-07 2026-11-08         # what is already there
gcalcli search "keyword"                     # find an event
gcalcli add --calendar "Home" --title "Session" \
  --when "2026-11-07 10:00" --duration 120 --noprompt
```

`--duration` is **minutes** (`--duration 90`, never `"1:30"`).

## Deleting and moving

`gcalcli delete` by search text deletes **every** match in the date range. Use
unique text, never a generic word like "Break", and pass a narrow range.

To reschedule: check the current time, propose the revised slot, get approval,
delete the old events by unique text, then add the new ones. Do not edit in
place when the move is large enough that a stale event would confuse the day.

## Via the MCP tools

Where a workspace grants calendar scope, the Google Workspace MCP servers expose
`list_calendars`, `get_events`, `query_freebusy` and `manage_event`
(create/update/delete/rsvp). Same rules: check the day, propose, then write.
`manage_event` can also delete — that is a write like any other.
