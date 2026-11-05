---
name: day-updating
description: |
  Repair a day that has slipped — a meeting overran, a task took longer, the
  start was late — by replacing only the part that has not happened yet, and
  stating what is lost rather than deleting it. Use when a plan already exists and
  reality has diverged from it.
---

# Day updating

This only applies when a plan already exists and reality has diverged from it.
Laying out a day from scratch is `skill://day-planning`; how an event is written
or moved is `skill://google-calendar`.

The rule that makes this a separate job: **what has already happened can only be
recorded, not replanned.** The rules for writing or moving an event — the current
time, the Notion id, approval before writing — are `skill://google-calendar`'s,
and the layout rules are `skill://day-planning`'s. Neither is repeated here.

## Do not

- **Do not rewrite the whole day.** The morning is history. Replace what has not
  happened and leave what did.
- **Do not carry the original approval over.** The revised plan is a new set and
  needs its own approval.
- **Do not silently drop a task.** A task with no time left is a decision to
  state, not a deletion to perform.
- **Do not recompose the budget upwards** because it is now the afternoon. The
  remaining hours are the budget.
- **Do not leave the old and the new versions of a block side by side.**

## Do

1. Check the time again: `date '+%Y-%m-%d %H:%M'`.
2. Establish what stands — what was done, what was partly done, what never
   started.
3. Recount the remaining budget from the energy actually left, not the morning's
   estimate.
4. Propose the revised remainder and get approval **for the revision**.
5. Delete the superseded blocks: by event id when you have one, otherwise an
   exact title plus a narrow date range — `gcalcli delete` removes every match,
   including ones you did not mean.
6. Add the replacement blocks.
7. Say out loud what was lost, what it costs and what is now not happening today,
   then let the user choose between a shorter day and a later one.
