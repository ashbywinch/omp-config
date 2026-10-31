---
name: ux-process
description: |
  The UX test-and-loop: a fake user of a PRD persona walks the live app in
  one subtask (verbose impressions, reasoning, confusions — screenshots of
  every screen), then a UX subagent turns the transcript and screenshots
  into a UX problems list and recommendations. Maintain a UX decisions doc
  and converge — changes land only with user agreement and when re-walking
  stops finding the targeted problems. References docs/ux-standards.md;
  does not restate it.
---

# UX Process

The loop that keeps the UI honest: **test → record → agree → re-test**.
Standards and decisions live in documents, never in the loop's memory — that
is what stops the loop from going round in circles.

## This file is for you, the main agent

The walker subtask never reads this skill. Nothing here reaches it unless you
copy it into the walker's prompt. The walker also gets no implementation
context from you. **Craft the prompt from the template below; do not
paraphrase the hard rules.**

### Before spawning the walker

1. **Pick a model that can see images.** If the walker model cannot accept
   image attachments, do not spawn it. A blind walker is not a usability
   test; it will cheat by reading code and waste the run.
2. Fill in the template. Do not add feature names, screen names,
   architecture, intended flow, or hints.
3. After it starts, check its first message: it must describe the first
   screenshot. If it says it cannot see, cancel the run and fix the model.
   Never let a blind walker continue.
4. You may read the implementation freely while building and fixing. Never
   put that knowledge into the walker prompt or use it to justify the
   walker's claims.

### Walker prompt template (copy verbatim, fill the brackets)

```text
You are [persona name, age, situation]. You are a human user of a website,
not a developer.

You have: [URL]
Your task: [task in user language]. [Write policy: "You may save and
complete the task" or "You are read-only — never save or submit".]

You see only what a person sees: rendered screenshots and visible controls.

Hard rules:
- NEVER read or inspect page source, HTML, DOM, JavaScript, CSS, the
  accessibility tree, network requests, console output, storage, cookies,
  application state, or devtools.
- NEVER use browser helpers that read markup or evaluate page code (html,
  text, attr, count, evaluate, run, --dump-dom).
- You may locate a visible control by its visible label and interact with
  it. You may not enumerate or read the page.
- Screenshots are your only evidence. Every observation and every claim
  about state must trace to a screenshot (or text visibly rendered in one).
- Before doing anything else, take a screenshot and describe what you see.
  If you cannot actually see the image, reply exactly "I cannot see the
  screen" with the reason and stop. Do not substitute code or DOM reading.

Work as this user would, on a phone if the persona uses one. Think aloud,
verbosely, in the first person: what you are trying to do, what you expect
before each action, what happened, and exactly what confuses you. Say when
something is missing, ambiguous, or unreadable. Do not propose fixes.

Take a screenshot of every distinct screen and before/after each action;
save under [screenshot dir] in visit order with descriptive names and a
manifest: path | what it shows | what you were trying to do.

If you give up, say exactly where and why.

Output: (1) the full first-person transcript; (2) the screenshot manifest;
(3) final state — what you achieved, what you gave up on, where you
stopped, and whether anything was saved.
```

## The loop

1. **Adopt a persona.** Pick one persona from the PRD — specific enough to
   drive decisions (docs/ux-standards.md). The persona's world, language,
   and goal are the test's frame.

2. **Subtask 1 — the fake user walks the app.** Launch a subtask with browser
   access that plays the persona attempting a real task from the PRD. Two
   rules about information:
   - Give the fake user **only what a real user of that persona would
     have**: the task, the persona's situation and goal, the app URL. No
     internal knowledge — no architecture, no intended design, no hint of
     what they "should" find or how the app "works". They discover it like
     any user.
   - **State the write policy explicitly**: "you are read-only — observe and
     navigate, never save, PATCH, submit, or toggle anything persistent", or
     for tasks that genuinely require it, "you may complete the task fully,
     including saving" — say which, don't leave it ambiguous.
   - **Take a screenshot of every screen you see**, stored in a shared
     location (e.g. `/tmp/ux-walkthrough/`), named in visit order.
   - **Be verbose, in the persona's voice**, about first impressions,
     reasoning, confusions (grounded in the exact label or location),
     and whether and why they give up (and at what point).
   - **The walker rules above are the operational form of P14–P18 in
     `ux-standards.md`** — the principles are there; the rules
     here are the walker's checklist. See also the "How reviewers
     interact" section below for the reviewer's single rule.
   - The transcript is the raw material; do not let the fake user
     self-diagnose or propose fixes — they report experience, not design.

3. **Subtask 2 — the UX subagent analyses.** A separate subtask reads the
   transcript and screenshots and produces:
   - **UX problems** — the numbered list of what went wrong for this user,
     ordered by severity, each grounded in the transcript or a screenshot
     (quote the user's words; reference the screen).
   - **Recommendations** — the concrete change, where it goes, which problem
     it resolves, and what a better experience would look like from this
     user's point of view.
   The subagent may reference `ux-standards.md` and the repo's
   usability baseline, but must not be limited by them: the desired outcome
   is a great experience for this user, not compliance with a guideline. A
   recommendation that serves the user even where a principle is silent is
   valid; a guideline that would make this user's experience worse is
   overruled by the user's experience.

4. **Record.** Every accepted change lands in the repo's **UX decisions
   doc** (the `docs/ux-fixes-plan.md` pattern): the decision, the problem it
   resolves, the persona it was tested with, and the implementation
   specifics. The doc is the memory of the loop.

5. **Agree.** Decisions and PRD updates land only with the **user's
   agreement** — the same propose/confirm seam as everything else. A change
   without a stated reason and a named user sign-off is not a decision; it
   is churn.

6. **Re-test.** Acceptance is re-walking the scenario: a change is done when
   the fake user no longer hits the problems it targeted. Unit tests prove
   mechanics; the walkthrough proves the experience.

## The walker has human senses only

**Scope:** this constrains the **participant subtask** (and the evaluator
when judging the participant's experience). The main agent may read code,
DOM, logs, network, storage, and application state freely to build, debug,
and fix the app — it simply must not put that knowledge into the walker's
briefing, nor use it to excuse the walker's evidence. The walker's world is
the rendered screen; the builder's world is the implementation.

A real user perceives **rendered pixels** and interacts with **visible
controls**. The walker must behave the same way. These are hard rules for the
walker, not style preferences:

- **Never read the implementation.** Do not open or inspect page source,
  HTML, DOM, JavaScript, CSS, the accessibility tree, network requests,
  console output, local/session storage, cookies, or application state.
  Do not use browser helpers that read markup or evaluate page code
  (`html`, `text`, `attr`, `count`, `evaluate`, `run`, devtools). Finding a
  control by its **visible label** is allowed; enumerating or reading the
  page is not.
- **No vision, no walk.** The walker model must actually receive and see the
  screenshots. If it cannot (no image input, screenshots omitted, images
  unreadable), it must **stop immediately** and report "I cannot see the
  screen" with the reason. Continuing by reading code or DOM is cheating
  and invalidates the run.
- **Screenshots are the only evidence.** Every observation, every confusion,
  and every claim about state must trace to a screenshot (or to text
  visibly rendered in one). "I could not find X" is a finding; "I read in
  the source that X exists" is not.
- **If a screen is unreadable, say so.** P16 applies: unreadable means the
  task is impossible for that user, and that is the finding.

Phase 1 must fail loudly rather than produce a fabricated walk. A blind
walker's transcript is worthless; do not spend tokens producing one.


## How reviewers interact (one rule)

The reviewer interacts with a site exactly as the persona could — see the
walker rules above. A reviewer must NEVER correct, inspect, or reason from
the implementation. If the persona cannot see it, it does not exist for the
test.

## The anti-loop guard

- **The user's experience is the measure, not the guidelines.** Findings
  don't have to cite a principle to be valid; a real confusion from a real
  persona walk is a finding. Guidelines are a shortcut to good UX, not a
  ceiling on it.
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
  problem that no principle covers means the standards have a gap — that is
  a standards change (proposed to the user), not a per-screen patch.

## Working with the other skills

- `skill://user-interviews` — when the loop surfaces an unknown user need,
  run primary research before guessing.
- `skill://visual-design` — wireframes/mockups for the recommendations the
  loop produces.
- Standards: `ux-standards.md` (principles), the repo's
  usability-requirements baseline and UX decisions doc (repo specifics).
