---
name: day-planning
description: Compose a whole day's schedule from the work in it — gather the tasks, fit them honestly around fixed events and breaks, propose the set for a single approval. To repair a day that has slipped, use `skill://day-updating`.
---

# Day planning

Lay out a day from the work that belongs in it. How a single event gets its
time, and whether it may be written, is `skill://google-calendar`; the commands
are `skill://gcalcli`.

## Choosing what to work on

Before laying out a day, decide which work belongs in it.

- **Importance comes from the value stream** the work sits under and the goal
  it advances — not from how loudly it was asked for.
- **Urgency comes from deadlines**, internal or external.
- **Inside one value stream, prefer the item that unblocks the most other
  work.**
- **Priority is dynamic.** An item that nobody has to chase can become urgent
  simply by being left long enough; recompute rather than trust a stored
  order.
- **An admin item — phone calls, email, meetings — is the day's capacity for
  admin.** Other work fills the time around it.

## Compose

1. **Check the time**: `date '+%Y-%m-%d %H:%M'`. A plan that starts in the past
   is not a plan.
2. **Gather the work**: the Notion tasks that could belong in the day (ID, size,
   priority) — including ones nobody has given a date — and the fixed events
   already in the calendar.
   - **Admin work comes from the picker.** Ask `skill://choose-the-days-item` —
     the inbox project's pick of the day's one substantive admin item — and
     schedule what it returns. Day planning decides the layout, not what the day
     is for.
3. **Size it honestly** against the hours the day actually has — the budget it
   was handed, or the real remaining hours if it was not. If the work does not
   fit, say so and propose what to cut. Never fit a day by eating breaks or by
   overlapping blocks.
4. **Place it**: fixed events are immovable, related work runs back-to-back
   deliberately, and breaks are real entries rather than gaps left over — 15
   minutes after every 45–75 minutes of work, and an hour for lunch.
5. **Propose the whole plan in one message** — every block with title, start,
   duration, calendar and task ID, including the admin item. One approval covers
   the set.
6. **Check it against the day**: no two blocks overlap, and every task either has
   a block or was explicitly set aside.
7. **Write it**: one event per block, description carrying the task ID. Detail
   that runs past a few lines stays in Notion, with the event pointing at it.
   Then list the day to confirm every block landed.

## Rules

- **Never** create a work block without its Notion task ID when the task exists.
- **Never** compress a day by eating breaks.
- **Never** schedule in the past.
