---
name: ux-process
description: |
  The UX test-and-loop: test the live app against the standards by adopting
  a PRD persona and attempting a task (via a read-only browser subtask),
  maintain a UX decisions doc, and converge — changes land only with user
  agreement and when the walkthrough stops finding the targeted confusions.
  References docs/ux-standards.md; does not restate it.
---

# UX Process

The loop that keeps the UI honest: **test → record → agree → re-test**.
Standards and decisions live in documents, never in the loop's memory — that
is what stops the loop from going round in circles.

## The loop

1. **Adopt a persona.** Pick one persona from the PRD — specific enough to
   drive decisions (docs/ux-standards.md). The persona's world, language,
   and goal are the test's frame.
2. **Test via a read-only subtask.** Launch a subtask with browser access
   that walks the LIVE app as the persona attempting a real task, READ-ONLY
   (observe and navigate, never save/PATCH/submit). It tests what it sees
   against `docs/ux-standards.md` (principles P1–P13) and the repo's
   usability-requirements baseline, and reports:
   - **Confusions** — every point the persona would be confused, stalled,
     or misled, in the persona's voice ("Where do I put my new office?"),
     each grounded in the exact URL/label it saw; a thing it could not find
     is a finding.
   - **Recommendations** — the concrete change, where it goes, which
     confusion it resolves.
3. **Record.** Every accepted change lands in the repo's **UX decisions
   doc** (the `docs/ux-fixes-plan.md` pattern): the decision, the
   requirement or principle it resolves, the confusions it targets, and the
   implementation specifics. The doc is the memory of the loop.
4. **Agree.** Decisions and PRD updates land only with the **user's
   agreement** — the same propose/confirm seam as everything else. A change
   without a stated reason and a named user sign-off is not a decision; it
   is churn.
5. **Re-test.** Acceptance is re-walking the scenario (P13): a usability
   change is done when the walkthrough no longer produces the confusions it
   targeted. Unit tests prove mechanics; the walkthrough proves the
   experience.

## The anti-loop guard

- **Changes converge against the standards, not against taste.** A finding
  is valid only if it violates a principle (P1–P13) or a stated requirement
  from the PRD. "I don't like it" is not a finding; "P2: this number
  misleads at a glance" is.
- **The decisions doc is the loop's memory.** Before changing anything,
  read it: if the change reverses an earlier decision, the earlier decision
  must be wrong *now* — state why, and get the user's agreement. A loop
  that keeps flipping the same control is a missing decision, not a UX
  problem.
- **Refer to the PRD's high-level user needs.** Every decision traces to a
  JTBD, persona, or constraint in the PRD; when you learn something that
  contradicts the PRD, propose the PRD change (user agreement), then the UX
  change follows. Update the PRD first; the UI is downstream of it.
- **Update the standards only when the principle is wrong.** A repeated
  confusion that no principle covers means the standards have a gap — that
  is a standards change (proposed to the user), not a per-screen patch.

## Working with the other skills

- `skill://user-interviews` — when the loop surfaces an unknown user need,
  run primary research before guessing.
- `skill://visual-design` — wireframes/mockups for the recommendations the
  loop produces.
- Standards: `docs/ux-standards.md` (principles), the repo's
  usability-requirements baseline and UX decisions doc (repo specifics).
