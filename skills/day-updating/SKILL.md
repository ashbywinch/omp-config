---
name: day-updating
description: |
  Replan the rest of a day that has slipped — the session ran long, something
  arrived, energy dropped — without pretending the morning went as planned. Use
  mid-day, or when the user says the plan is no longer true.
---

# Day updating

This is not planning a day. It is repairing one, from now to the end, and it
carries one rule the plan did not need: **what has already happened cannot be
replanned, only recorded.**

## Do not

- **Do not rewrite the whole day.** The morning is history. Replace the part that
  has not happened yet and leave what did.
- **Do not move a session that is already running.** Finish it or stop it, then
  replan from there.
- **Do not drop unfinished work silently.** Anything that fell off goes back as
  unfinished, with what state it reached — it will be picked up again, not
  forgotten because its slot passed.
- **Do not shrink the breaks to recover lost time.** That is how one slip becomes
  two.
- **Do not recompose the budget upwards** because it is now the afternoon. The
  remaining hours are the budget.
- **Do not write calendar events before the revised day is approved.**

## Do

1. **Check the time.** `date '+%Y-%m-%d %H:%M'`.
2. **Establish what stands**: what was done, what was partly done, what never
   started.
3. **Recount the remaining budget** from the energy actually left, not the
   morning's estimate.
4. **Recompose from now**: the same layout rules as `skill://day-planning` —
   breaks, lunch if it has not happened, sessions sized to what remains.
5. **Propose the revised remainder** and wait for approval.
6. **Write it**: replace the day plan file's remaining rows, move the calendar
   events, and put unfinished work back where it came from.

## What gets said out loud

A slip is information, not a failure to conceal: say what was lost, what it costs
and what is now not happening today. Then let the user choose between a shorter
day and a later one.
