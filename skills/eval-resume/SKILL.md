---
name: eval-resume
description: Resume a long evaluation (eval) from the phase that failed — checkpoint the typed input at phase boundaries, then re-run only the failing unit
---

# Eval Resume

An eval (evaluation) is an automated test that runs a model over many inputs.
Some of our evals run as phases. A phase takes a typed input — a spec, a case
list, a config — and produces the next one.

Checkpoint that input at the phase boundary. A failure then costs one phase
instead of a full rerun. The next phase depends on that input, not on how the
previous phase produced it.

## Why not replay the transcript

A transcript is text. The harness's state is a call stack plus typed objects:
the phase that follows a conversation takes the conversation's *result*, not
its words. A replay therefore repeats every earlier phase and pays for it
again. Checkpoint the result instead, and start the phase that failed from it.
If the failure is inside a phase, restart that phase from its input. The
conversation it runs is then fresh, as the next run's would be.

## When to checkpoint

Add a checkpoint only when all three hold.

- The phase is expensive — minutes, many tokens, or many independent units
  (the cases the phase runs).
- Its input is a typed object (a spec, a list of cases, a config), not the chat.
- The phase can run on that input alone.

A single atomic conversation, or an eval whose input is already a fixture, does
not need one. Do not checkpoint every eval; checkpoint where a failure would
otherwise force a full rerun.

## What to save

Save the phase's input and the names of its units. Never save the message
history. The conversation is the previous phase's implementation detail; the
typed input is the contract between phases.

Write the checkpoint before the assertion that can fail. A failed run then
still leaves one. Keep it in a scratch or evidence directory, not in the repository.

## How to resume

Add a small test. The test:

1. reads the checkpoint (path from an environment variable, with a default);
2. optionally filters to the failing units (comma-separated environment
   variable);
3. runs only that phase for those units;
4. collects every failure instead of stopping at the first.

Run it through the project's normal test target, with the same model and
provider settings as the eval. Keep the end-to-end eval unchanged and blocking. The
resume test is for iteration, not a replacement for the gate.

## Rules

- The checkpoint is a dev aid. It must never let the gate pass on a partial
  build. The end-to-end test still asserts that every unit succeeded.
- A resume test with no checkpoint skips; it does not fail the suite.
- Use the same simulated user (the bot that plays the user), persona, and
  model config as the full eval, defined once and shared. A different user in the resume test exercises a
  different scenario.
- Resume one unit at a time when a unit takes minutes. Several units do not
  fit one time budget just because the full eval eventually did.
- When the checkpoint is missing, extract the typed input from the saved
  transcript or evidence if it is there. With no evidence, add the checkpoint
  and take one full run to seed it.
- Fix the cause, then re-run the smallest phase that proves it. Run the full
  eval only when the small ones are green.

## Placement

This skill describes the pattern. The concrete checkpoint path, test target,
and environment variable names are repo-specific. Put them in that repo's testing docs, and
reference this skill for the principle.

