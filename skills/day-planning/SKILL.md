---
name: day-planning
description: |
  Compose a day's schedule from the work that belongs in it — size it to the
  energy available, fit it around fixed commitments and breaks, propose the whole
  day for one approval, then write the day plan and its calendar events. Use when
  starting a day, or when asked to lay one out.
---

# Day planning

Composing a day is not the same as picking the work, and not the same as placing
one event. Where the work comes from is whoever chose it — the morning check-in,
a backlog grooming, or the user. How one event gets its time, and whether it may
be written, is `skill://google-calendar`; the commands are `skill://gcalcli`.

## Do not

- **Do not plan into the past.** Check the time with `date` first. A session that
  started ten minutes ago is not a plan, it is a reproach.
- **Do not exceed the energy.** High is four to five hours of focused work,
  medium two to three, low one at most. A plan the person cannot finish is worse
  than a shorter one, because it also costs the failure.
- **Do not bury the fixed things.** Calendar commitments are immovable; place
  them first and fit work around them, not the other way round.
- **Do not schedule the same block twice.** One session, one subject, one time.
- **Do not write anything before the whole day is approved.** The plan and its
  calendar events are proposed together and agreed together.
- **Do not invent work to fill a slot.** An empty half-hour is honest; a made-up
  task is not.

## Do

1. **Check the time.** `date '+%Y-%m-%d %H:%M'`.
2. **Read the calendar** for the day's fixed commitments and what is already
   booked (`skill://google-calendar`).
3. **Gather the work** that belongs in the day, in the order it should be done.
4. **Size the budget** from the energy: total focused hours, and what counts as
   substantial.
5. **Lay it out**:
   - the first session starts 15 to 30 minutes after the planning finishes;
   - a 15-minute break every 45 to 75 minutes of work;
   - 60 minutes for lunch;
   - session count and length come from the budget, not from the list.
6. **Propose the whole day** — every session, its time and its tasks — and wait
   for one approval.
7. **Write it**: the day plan file, then the calendar events.

## The day plan

`~/.config/omp/dayplans/Day plan.md`, rewritten whole each time:

```markdown
# Day Plan: 2026-07-30

**Energy: Medium-High (~5 hours)**

| Time | Session | Tasks |
|---|---|---|
| 11:20–13:00 | Provenance fixes | Remove Duplicated Provenance Items (3ac3122e-…), Redesign Provenance Component UX (3ac3122e-…) |
| 13:00–14:00 | Lunch | |
| 14:00–15:15 | Scraper: Search setup | Define Rightmove Saved Search (3ac3122e-…), Build Search Result Enumeration (3ac3122e-…) |
```

- **Every task is named with its Notion id**, so the session can find it.
- **A break is a row.** Lunch is a row. Time the person is not working is part
  of the plan, not an absence from it.
- **One day per file.** Yesterday's plan is gone once today's exists; the record
  of what was done belongs in Notion, not here.
