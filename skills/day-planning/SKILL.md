---
name: day-planning
description: Compose a whole day's schedule from the work in it — gather the tasks, fit them honestly around fixed events and breaks, propose the set for a single approval. To repair a day that has slipped, use `skill://day-updating`.
---

# Day planning

Laying out a day from the work that belongs in it. Repairing a day that has
already slipped is a different job and lives in `skill://day-updating`. How a
single event gets its time, and whether it may be written, is
`skill://google-calendar`; the commands are `skill://gcalcli`.

## Choosing what to work on

Before laying out a day, decide which work belongs in it.

- **Importance comes from the value stream** the work sits under and the goal
  it advances — not from how loudly it was asked for.
- **Urgency comes from deadlines**, internal or external.
- **Inside one value stream, prefer the item with no blockers or
  dependencies.**
- **Priority is dynamic.** An item that nobody has to chase can become urgent
  simply by being left long enough; recompute rather than trust a stored
  order.
- **One substantive item is a day's capacity** when the person's budget is
  that small: present the one, not the backlog.

## Compose

1. **Check the time**: `date '+%Y-%m-%d %H:%M'`. A plan that starts in the past
   is not a plan.
2. **Gather the work**: the Notion tasks for the day (ID, size, priority) and
   the fixed events already in the calendar.
   - **The admin item comes from the picker, not from here.** Where the workspace
     has one — `skill://choose-the-days-item` in the inbox desk — ask it for the
     day's one substantive admin item, and schedule what it gives you. This skill
     lays out the day; it does not decide what the day is for.
3. **Size it honestly**. If the work does not fit, say so and propose what to
   cut. Never fit a day by eating breaks or by overlapping blocks.
4. **Place it**: fixed events are immovable, related work runs back-to-back
   deliberately, and breaks are real entries rather than gaps left over.
5. **Propose the whole plan in one message** — every block with title, start,
   duration, calendar and task ID, including the admin item. One approval covers
   the set.
6. **Write it**: one event per block, description carrying the task ID. Detail
   that runs past a few lines stays in Notion, with the event pointing at it.
7. **Read it back**: list the day, confirm no two blocks collide, and confirm
   every task either has a block or was explicitly set aside.

## Rules

- **Never** create a work block without its Notion task ID when the task exists.
- **Never** compress a day by eating breaks.
- **Never** schedule in the past.
