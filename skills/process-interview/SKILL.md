---
name: process-interview
description: |
  Elaborate the requirements for a process by trying it for real and
  interviewing the user through the attempt — build a working skeleton,
  run it against real material, ask one question at a time, and turn every
  demonstrated failure into a rule with a test. Distill the overarching
  principles at the end and record them in the standards, not the skill.
---

# Process Interview

You cannot spec a process you have not tried. Requirements for a flow —
an import, a capture, a review, a migration — are discovered by **doing it
with real material and interviewing the user through the experience**, not
by design on a whiteboard. The attempt is the interview.

## The loop

1. **Build a working skeleton early.** The smallest honest end-to-end path
   through the process — real material, real rules, real output. It will be
   wrong; that is the point. Do not polish it; the interview will rewrite
   it.
2. **Try it with real material.** Never invented content: the demo hides
   the real failures, and invented artifacts become permanent lies once
   they ship. If the domain has no real material yet, say so and
   proceed with the closest honest stand-in — but flag it.
3. **Interview the user through it.** Present what the attempt produced,
   one question at a time. Never dump a wall of questions.
4. **Turn failures into rules.** Every rule is written AFTER a demonstrated
   failure, never before. Name each rule and record the incident that
   motivated it.
5. **Enforce with tests.** Failing tests first, for rules and for the
   process. During the interview, the prototype's checks run over the
   small dataset the prototype itself creates — a rule without a test is
   a hope (see "Enforcing with tests" for the prototype-only boundary).
6. **Distill the principles.** When the rules stop changing, step back and
   write the few overarching principles the rules instantiate — and record
   them where they belong: usually the feature's PRD or flow spec; only
   genuinely repo-wide principles go in the standards. A session that
   produces only rules has not finished.

## The interview discipline

- **The user's corrections are the highest-value input.** They are the
  spec's amendments. Actively solicit them — "what did we get wrong?" —
  and record each one verbatim with its date. The user will catch things
  no analysis will: a claimed precision that was never checked, an
  edge case the rules exclude, a category that was mis-typed, an
  assertion made without evidence, a question the process never asked.
- **Verify every claim before acting.** The user's description can be a
  misreading (a date reported from a neighbouring label; a detail
  mis-attributed). Investigate, state what you found, and correct the
  record — but never dismiss the report: behind every misreading is
  usually a real problem with the presentation or the data.
- **Ask about edge cases explicitly.** Corner uses the user mentions in
  passing (an occurrence that can coincide with its capture; material
  that doesn't fit the obvious category) are real requirements. Follow
  them to their conclusion — they usually amend the rule.
- **Track pending questions in the record.** Unresolved items live in the
  session log, visibly, and are surfaced — one at a time — until answered.

## Turning failures into rules

- **A rule without a stage is a trap.** Specify the mechanism, not just
  the principle: "the reviewer verifies the output" is nothing; "the
  review stage presents each item — accept / adjust / drop — before it
  ships" is a rule. The principle-only version silently never runs.
- **Rules generalise.** After the specific fix, rephrase the rule so the
  next instance is caught: a one-off misattribution becomes "a known
  category is disambiguated, never guessed".
- **The user's model instinct is a signal, not a rule.** When they say a
  thing is "probably not a different type, but a flag", explore that
  framing — but a new type is right when the thing has its own structure
  or behaviour, not just a different kind; don't shoehorn. Similarly
  "calculated not stored": prefer deriving the facts a derivation can
  express, and state the rest.

## Enforcing with tests

- **Failing tests first**, for every rule — including the process's own
  data quality. Each rule's test is the rule's enforcement point.
- **During the interview, the prototype's checks run over the small
  dataset the prototype itself creates** — one guard per rule, failing
  the build with the offending records named, exercising the rules
  against real material. That is the point of the prototype: it is the
  data's first consumer. **This is prototype-only.** Outside this
  interview's throwaway prototype, never run unit tests or evals against
  production, real, or live data — normal development tests against
  fixtures and test data, always.
- **Fail loudly.** A guard that degrades silently is not a guard. Design
  the pipeline so a violation refuses to build — and let it catch real
  violations during the session (it will).
- **Fixtures obey the model.** When a rule changes, rewrite its tests with
  the rule, failing first — a test that pins the old behaviour is a bug
  in the tests.

## Where decisions land

Know where every decision belongs, and update as you go, not at the end:

| Decision | Home |
|---|---|
| User-visible requirements (incl. presentation) | the requirements doc |
| Mechanics — flags, seams, validation, algorithms, evals | the design/spec doc |
| A flow's rules | the flow spec for that flow |
| Visual/interaction conventions | the conventions doc |
| Findings, statuses, open items | the working log (never normative) |

There is no separate "UX requirements" category — presentation
requirements belong in the requirements doc; conventions in the
conventions doc; working notes in the log. **The domain principles the
interview surfaces land where they belong** (step 6) — usually the
feature's PRD or flow spec; only genuinely repo-wide principles go in the
standards — see `skill://learn-from-this-session`'s strip checklist for
the audit.

## The session record

Keep an interview log: every decision with its date, every rule with its
motivating incident, every pending question. Append-only.
It is what makes the session reproducible for the next agent and
reviewable by the user.

## Working with other skills

- `skill://learn-from-this-session` — run the reflection when the process
  rules stop changing.
- `skill://user-interviews` — primary research when the process needs
  facts nobody has stated.
- `skill://ux-process` — when the process has a UI, loop it like any
  surface.
- `skill://write-documentation` — the standards docs (coding, testing,
  documentation) for the specs the interview produces.
