---
name: google-calendar
description: Decide whether and when an event may be written — gather the day's context, ask for a time with that context in front of the user, check the slot is free, and only then write it.
---

# Google Calendar

The rules for putting something on a calendar. None of them are specific to a
tool.

## Choosing the time

1. **Look at the day before asking anything.** Read the events and the
   free/busy for the range. Asking "what time?" without the day in front of you
   wastes the user's only turn.
2. **Offer the day's shape with the question.** "You're busy 3–4, then free from
   5 — put it in the gap or at 5?" is answerable; "what time?" is not.
3. **Never invent a time.** A time comes from the user, or from an event it is
   deliberately attached to (the notes after the visit they follow). Anything
   else is a guess wearing a timetable.
4. **Check the slot is free before writing**, not after.

## Writing

- **Never** schedule in the past — `date '+%Y-%m-%d %H:%M'` first.
- **Never** write without approval of that specific event: title, day, time,
  calendar. A plan being approved is not this event being approved.
- **Never** put an event on a calendar without knowing who reads it — the
  account is part of the decision, and a workspace with more than one records
  which is which.
- **Never** create an event that stands for work without its Notion task ID when
  a task exists. Detail longer than a few lines belongs in Notion, with the
  event pointing at it; detail that fits in a few lines goes in the description.
- Moving or deleting an event is a write like any other.

## Tools

The rules above hold whatever writes the event.

- **`gcalcli`** — commands, flags and their traps: `skill://gcalcli`.
- **MCP** — where a workspace grants calendar scope, its Google Workspace server
  exposes `list_calendars`, `get_events`, `query_freebusy` and `manage_event`
  (create/update/delete/rsvp). Use the one the workspace provides; `manage_event`
  can also delete, which is a write like any other.
