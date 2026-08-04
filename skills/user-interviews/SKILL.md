---
name: user-interviews
description: |
  Run user interviews and observation sessions for a product — prepare,
  conduct, and record primary research, and fold the findings into the PRD
  with the user's agreement. References docs/ux-standards.md; does not
  restate it.
---

# User Interviews

Use when the product's user needs, JTBD, or personas are unknown or
unverified. The output is raw material for the PRD's JTBD and personas
(`docs/ux-standards.md` says what the PRD must contain — this skill is how
you get there).

## Prepare — research first, then ask

- **Observe before interviewing.** Discovery instruments (inventory, effort
  math, walkthroughs) answer what people *do*; an interview answers *why*.
  Do the observation first — "watch, don't ask" — so the interview asks
  about observed behaviour, not abstractions.
- **Know what you don't know.** Read the existing artifacts (the collection,
  the logs, prior research) before the session; a question answerable from
  artifacts is not an interview question.
- **Know the narrator's world.** One narrator, one session, conversational —
  ten questions at most, one at a time.

## Conduct

- **One question at a time**, conversational, in the narrator's language.
- **Open-ended → closure → targeted.** Start open ("tell me about…"), let
  the account run, then close gaps with bounded, specific follow-ups.
- **Why, always.** Every concrete answer gets its "why" — the reason is the
  requirement; the anecdote is the colour.
- **Questions are skippable and never interrogations.** A question the
  narrator doesn't want to answer is dropped, not pushed.
- **Preserve the voice.** Verbatim quotes matter — they are the raw material
  for the product's copy and for what gets stored. Note them exactly.

## Record

- **Verbatim, attributed, dated.** The record distinguishes the narrator's
  words from your paraphrase, and names who said what when.
- **Quotes are raw material, not decisions.** A quote becomes a requirement
  only when the user says so (see below).

## After — fold in only with the user's agreement

- **Propose, don't decree.** Draft the findings as proposed changes to the
  PRD (JTBD, personas, constraints) and get the user's agreement before
  they land — the same propose/confirm seam as the rest of the house rules.
- **Decide what NOT to store.** Not everything a user says belongs in the
  requirements: product commentary, descriptions of artifacts, and opinions
  may stay out. Record that decision too, so it is deliberate.
- **Disputed or sensitive material** stays attributed to its source and is
  never presented as fact; the app arranges evidence, it never adjudicates.

## Outputs

- The PRD's JTBD + persona sections, updated with user agreement.
- The session record (verbatim, attributed, dated) as the traceable raw
  material.
- New UX decisions recorded in the repo's UX decisions doc
  (`skill://ux-process` — the decisions doc is shared).
