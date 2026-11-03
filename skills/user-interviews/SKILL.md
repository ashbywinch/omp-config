---
name: user-interviews
description: |
  Run user interviews — prepare, conduct, and record primary research, and
  fold the findings into the PRD with the user's agreement. References
  docs/ux-standards.md; does not restate it.
---

# User Interviews

Use when the product's user needs, JTBD, or personas are unknown or
unverified. The output is raw material for the PRD's JTBD and personas
(`docs/ux-standards.md` says what the PRD must contain — this skill is how
you get there).

## Prepare — research first, then ask

- **Know what you don't know.** Read the existing artifacts (the collection,
  the logs, prior research) before the session; a question answerable from
  artifacts is not an interview question.
- **Know the narrator's world.** One narrator, one session, conversational.

## Conduct

- **One question at a time**, conversational, in the narrator's language.
- **As many questions as are necessary, and no more.** Ask until the JTBD
  and personas are grounded; stop when the answers stop changing the
  picture. Don't pad an interview to a fixed length, and don't cut it short
  while a JTBD is still vague.
- **Open-ended → closure → targeted.** Start open ("tell me about…"), let
  the account run, then close gaps with bounded, specific follow-ups.
- **Why, always — and know what good looks like.** Every concrete answer
  gets its "why": ask the narrator what outcomes they are hoping for from a
  specific JTBD, and what would characterise a really excellent outcome.
  Their answer is the "why" — the requirement is the outcome they want, not
  just the task they do. Push until you can picture the difference between a
  mediocre and an excellent result in their terms.
- **Questions are skippable and never interrogations.** A question the
  narrator doesn't want to answer is dropped, not pushed.
- **Preserve the voice.** Verbatim quotes matter — they are the raw material
  for the product's copy and for what gets stored. Note them exactly.

## Record

- **Verbatim, attributed, dated.** The record distinguishes the narrator's
  words from your paraphrase, and names who said what when.
- **Quotes are raw material, not decisions.** A quote becomes a requirement
  only when the user says so (see below).
- **Never rewrite an answer into a substitute.** If the narrator said the
  tree view is for spotting gaps, the record says gap-spotting; it does not
  become "keeping the structure of their commitments visible" because that
  reads better in a requirements list. A paraphrase is legitimate only while
  it preserves the claim; where it changes the claim it is a fabrication,
  however plausible it sounds — and worse than a gap, because the narrator
  cannot tell their own view from yours.
- **Never supply a why the narrator did not give.** An absent reason stays
  absent, or you ask for one. Marking an invented reason as yours does not
  make it acceptable — it reads as background fact and gets built on.

## After — fold in only with the user's agreement

- **Propose, don't decree.** Draft the findings as proposed changes to the
  PRD (JTBD, personas, constraints) and get the user's agreement before
  they land — the same propose/confirm seam as the rest of the house rules.
- **Audit every claim against the transcript first.** For each requirement,
  each reason and each "they want X", point at the words that support it.
  Anything unbacked is deleted, or the question is asked again — no label
  makes an unsupported claim acceptable.
- **A correction is a deletion, not a softening.** When the narrator
  corrects a claim, the claim goes. Restating it in milder form keeps the
  fabrication and adds an argument about it.
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
