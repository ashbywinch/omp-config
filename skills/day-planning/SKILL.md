---
name: day-planning
description: Compose or revise a whole day's schedule from the work in it — gather the tasks, fit them honestly around fixed events and breaks, propose the set for a single approval, then replan when the day slips.
---

# Day planning

Laying out a day from the work that belongs in it, and repairing one that has
slipped. How a single event gets its time, and whether it may be written, is
`skill://google-calendar`; the commands are `skill://gcalcli`.

## Choosing what to work on

Before laying out a day, decide which work belongs in it.

- **Importance comes from the value stream** the work sits under and the goal
  it advances — not from how loudly it was asked for.
- **Urgency comes from deadlines**, internal or external.
- **Blocked work is not a candidate.** Inside one value stream, prefer the
  item that unblocks other work, other factors being equal.
- **Priority is dynamic.** An item that nobody has to chase can become urgent
  simply by being left long enough; recompute rather than trust a stored
  order.

## Compose

1. **Check the time**: `date '+%Y-%m-%d %H:%M'`. A plan that starts in the past
   is not a plan.
2. **Gather the work**: the Notion tasks for the day (ID, size, priority) and
   the fixed events already in the calendar.
3. **Size it honestly**. If the work does not fit, say so and propose what to
   cut. Never fit a day by eating breaks or by overlapping blocks.
4. **Place it**: fixed events are immovable, related work runs back-to-back
   deliberately, and breaks are real entries rather than gaps left over.
5. **Propose the whole plan in one message** — every block with title, start,
   duration, calendar and task ID. One approval covers the set.
6. **Write it**: one event per block, description carrying the task ID. Detail
   that runs past a few lines stays in Notion, with the event pointing at it.
7. **Read it back**: list the day, confirm no two blocks collide, and confirm
   every task either has a block or was explicitly set aside.

## Replanning a day that has slipped

This is the second procedure, and it only applies when a plan already exists and
reality has diverged from it — a meeting overran, a task took longer, the start
was late.

1. Check the time again.
2. Propose the revised plan and get approval **for the revision**; the original
   approval does not carry over.
3. Delete the superseded blocks: unique search text or event id, narrow date
   range — `gcalcli delete` removes every match.
4. Add the replacement blocks.
5. Never leave the old and new versions of a block side by side.
6. Never silently drop a task while replanning: a task with no time left is a
   decision to state, not a deletion to perform.

## Rules

- **Never** create a work block without its Notion task ID when the task exists.
- **Never** compress a day by eating breaks.
- **Never** schedule in the past.
