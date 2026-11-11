---
name: prompt-craft
description: |
  Write instructions an LLM agent will actually follow — skills, rules,
  task prompts, system prompts, and the prose in a spec. Grounded in the
  empirical findings on agent rule-files (Guardrails Beat Guidance,
  arXiv:2604.11088; UnderSpecBench, arXiv:2607.02294; ContractEval, ACL
  2026). Companion to write-documentation (docs for humans and agents)
  and tech-spec-writing (mechanics) — this skill is the instruction form
  itself, not the content.
---

# Writing prompts and instructions agents follow

When asked to write a prompt, skill, rule, task description, or system
prompt, apply these principles. They come from controlled studies of how
coding agents respond to instructions — not from intuition about which
phrasing "reads well".

## The three findings that drive everything

1. **Polarity beats content.** In 5,000+ agent runs, rule *content* was a
   weak lever — random rules matched expert-curated ones — while *polarity*
   was decisive: every individually beneficial rule was a negative
   constraint ("do not refactor unrelated code"); every individually
   harmful one was a positive directive ("write clear code"). Positive
   exhortations often do nothing and can regress behaviour
   ([arXiv:2604.11088](https://arxiv.org/abs/2604.11088)).
2. **Under-specified instructions make agents guess, not ask.** Agents
   cross an action boundary in 55–68% of runs under benign underspecification;
   wrong-target behaviour is dominated by **target ambiguity**
   ([arXiv:2607.02294](https://arxiv.org/abs/2607.02294)). Name the action,
   name the exact target, name the scope.
3. **A described contract is not an enforced contract.** The rule's
   checkable form and its ContractEval citation live in the
   coding-standards rule of the same name — link, don't restate:
   [A described contract is not an enforced
   contract](../../standards/coding-standards.md#a-described-contract-is-not-an-enforced-contract)
   (the canonical global copy; repos carry the materialized copy at
   `docs/coding-standards.md`, per tech-spec-writing's materialization).

## Guardrails before guidance

State what must **not** happen, then let the agent find the path. A
constraint that only activates when the agent is about to err changes
behaviour; an exhortation to "be good" does not.

- ✗ "Structure the code well and use an object model."
- ✓ "Do not leave domain content inside `sync_record()` — if the record's
  truth is only visible once it is flushed, split the parse from the I/O."

The reliable instruction is the negative: it names the failure the agent
can check for. Keep positive statements only when they name a concrete,
checkable shape (a type, a seam, a method signature) — not a virtue.

## A prompt is a spec: action + target + scope

Every requirement must unambiguously state three things, or the agent
guesses:

- **Action** — what to do ("re-transcribe this page verbatim", "add the
  relationship edge").
- **Target** — the exact object, named so no other candidate matches ("the
  person `p-richard-william-ellis`", "the upright page 4 image"), never
  "the old one" or "the relevant file".
- **Scope** — how far the change reaches and what must be left untouched
  ("change only the transcription asset; do not touch the person table").

If you cannot state all three, the instruction is under-specified and the
agent will guess — the dominant source of wrong actions.

## Enforce, don't instruct

A rule the agent must *remember* is a rule the agent will drop. For shape
rules and their checks, follow the conversion specified in the
coding-standards rule "A described contract is not an enforced contract"
(linked in Finding 3 above). When a rule cannot be structurally enforced,
write it as a **negative constraint** in the prompt — the last-resort
encoding — and name the test or eval that catches its failure.

## Few, minimal, non-overlapping

Rules prime the agent's framing and excess rules add an unaudited
regression channel — badly-chosen rulesets measurably degrade capability,
so keep rulesets small and distinct:

- each rule names a different failure; two rules that overlap dilute both;
- prefer ~half a dozen sharp rules over a wall of prose;
- revisit and prune: a rule that has never fired is noise.

## The mechanics come from the doc standard

The density rules (explicit negatives, commands over prose, canonical
✗/✓ pairs, task-shaped sections) live in
`docs/writing-documentation.md` — link to them, don't restate them. The
instruction-form consequences are covered above: polarity in "Guardrails
before guidance", target naming in "A prompt is a spec".

## When the instruction is for a skill or a rule

- A skill body's procedure, size ceiling, and discoverability rules live in
  `skill://write-documentation` — link to it, don't restate them.
- A rule that must hold in a code repo belongs in that repo's
  standards docs (which the review bot enforces) — write it as a named
  anti-pattern with a checkable form, not a preference.
- The machine rules materialize into `docs/coding-standards.md` so the
  bot reads them (`skill://tech-spec-writing`, Materialization).

## Before you ship a prompt, check

- [ ] No requirement ships without an exact action, target, and scope
- [ ] No rule ships as a positive exhortation when a negative constraint
      would name the failure
- [ ] No normative rule ships without a structural check named beside it
- [ ] No rule set ships larger than ~half a dozen rules
- [ ] No two rules overlap
- [ ] No target named ambiguously — nothing is "the old one"
