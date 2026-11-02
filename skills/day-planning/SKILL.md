---
name: day-planning
description: Compose or revise a day's schedule from the work in it — gather the tasks, fit them without collisions or compressed breaks, propose the whole plan for one approval, then run the reschedule loop when the day slips.
---

# Day planning

Building a day out of the work that belongs in it, and repairing one that has
slipped. Placing a single event is `skill://google-calendar`; the commands and
their traps live there.

## Compose

1. **Check the time**: `date '+%Y-%m-%d %H:%M'`. A plan that starts in the past
   is not a plan.
2. **Gather the work**: the Notion tasks for the day — ID, size, priority — and
   the fixed events already on the calendar.
3. **Size it honestly**. If the work does not fit, say so and propose what to
   cut. Never fit a day by shortening breaks or by overlapping blocks.
4. **Place it**: fixed events are immovable; related work runs back-to-back
   deliberately; breaks are real entries, not gaps left over.
5. **Propose the whole plan** — every event, one message: title, start,
   duration, calendar, task ID. One approval covers the set. A changed plan
   needs a fresh approval.
6. **Write it**: one event per block. The description carries the task ID, and
   the detail that runs past a few lines stays in Notion with the event pointing
   at it.
7. **Read it back**: list the day and confirm no two events collide and every
   task got a block or an explicit decision not to.

## Revise

1. Check the time again.
2. Propose the revised plan and get approval.
3. Delete the old blocks — unique search text or event id, narrow date range,
   never a generic word; `gcalcli delete` removes every match.
4. Add the new blocks.
5. **Never** leave the old and new blocks side by side.

## Rules

- **Never** compress a day by eating breaks.
- **Never** create a work block without its Notion task ID when the task exists.
- **Never** schedule in the past, and never silently drop a task from the plan.
- **Never** treat "the plan was approved before" as approval for a revision.
