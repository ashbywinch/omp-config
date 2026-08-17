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

## The loop

1. **Adopt a persona.** Pick one persona from the PRD — specific enough to
   drive decisions (docs/ux-standards.md). The persona's world, language,
   and goal are the test's frame.

2. **Subtask 1 — the fake user walks the app.** Launch a subtask with
   browser access that plays the persona attempting a real task from the
   PRD. Two rules about information:
   - Give the fake user **only what a real user of that persona would
     have**: the task, the persona's situation and goal, the app URL. No
     internal knowledge — no architecture, no intended design, no hint of
     what they "should" find or how the app "works". They discover it like
     any user.
   - **State the write policy explicitly**: "you are read-only — observe and
     navigate, never save, PATCH, submit, or toggle anything persistent", or
     for tasks that genuinely require it, "you may complete the task fully,
     including saving" — say which, don't leave it ambiguous.
   - **Navigate by LOOKING, like a human — never by inspecting the page.**
     The fake user decides what to do from what is visible: the rendered
     page and its screenshots. They never read the DOM, never query the
     console, never inspect source, and never use the developer tools to
     discover state or actions. If a step cannot be done without inspecting
     the page internals, that is a finding — the interface failed to show
     the way. (2026-08-16: a walk that "cheats" via the DOM tests the DOM,
     not the user's experience.)
   - **Take a screenshot of every screen you see**, stored in a shared
     location the next agent can read (e.g. `/tmp/ux-walkthrough/`), named
     in visit order. Screenshots are the evidence; the transcript is the
     reasoning.
   - **Success is perceptual, never operational.** The walk passes only when
     the persona could complete the task from what they could SEE and
     UNDERSTAND — never because the records changed. If the walker cannot
     see or read the content a real user needs (the letter, the image, the
     result), the walk FAILS at that point and reports it: the persona must
     not press on using knowledge of the underlying data or the intended
     design that a real user would not have. A walk that updates records
     while the persona could not see the material is a FALSE PASS, not a
     success. (2026-08-16: a persona walk "completed" a transcription
     review — confirmed decisions, records updated — while the letter was a
     microscopic unreadable strip. The walker knew what the flow should do
     and pressed through; no real user could have.)
   - **Exercise the interactions with the persona's REAL input — never just
     look.** A screenshot proves a screen rendered, not that it works. The
     walk must scroll the scrollable panes, pan and zoom the pannable views,
     tap the buttons, and submit the forms — with the input a real user of
     that device would use (touch on a phone, not mouse) — and observe each
     outcome. When an interaction silently fails (a pane that won't scroll,
     a drag that does nothing, a control that doesn't respond), that failure
     is a FINDING — the persona must not happily use an interface whose
     interactions a real user could not. (2026-08-16: three production bugs —
     an unscrollable pane, an initial view showing blank paper, an upstream
     library's drag collapse — passed every static check and were only found
     by exercising the interactions.)
   - **Walk at the REAL devices the PRD names — never a default desktop
     viewport.** Set the browser to the persona's actual sizes and
     orientations: the primary posture (e.g. tablet landscape) AND the
     secondary (phone portrait + phone landscape), AND the transitions
     between them (portrait → landscape — the rotate-prompt path is a real
     journey, and a view that fits at one size can break when the device is
     turned). A screen that only looks right at 1024×768 has not been
     tested. (2026-08-16: desktop-only walks missed a microscopic letter,
     a silly three-column header, and broken zoom controls that the user
     found on a real phone in minutes.)
   - Be **verbose, in the persona's voice**, about:
     - first impressions of each screen (what jumps out, what feels
       welcoming or off),
     - reasoning about how to do the task (what they try, what they expect
       to happen, what they look for),
     - confusions and frustrations, grounded in the exact label or location
       ("the button says 'Save' but I'm not saving anything yet"),
     - whether and why they give up, and at what point.
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
   The subagent may reference `docs/ux-standards.md` and the repo's
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

## The only valid way to interact with a site (reviewers)

**There is exactly one valid way to interact with a site for review: the
way the persona would.** The reviewer is a human at the device, not an
operator of the page.

- **Interact through the visible surface only.** Every decision comes from
  what a human could see: the rendered page, at the persona's real device
  size and orientation, with the persona's real input (touch on a touch
  device, mouse on desktop). Never the DOM, never the console, never the
  network tab, never the source, never the data files, never the
  application state — and never a keyboard/mouse substitute for the touch
  the persona would use.
- **See only what the persona sees.** Screenshots are the ground truth.
  Anything the persona could not see (a canvas that renders nothing, an
  image that fails to paint, text too small to read) is invisible to the
  reviewer too — and reporting it is the finding.
- **Never infer unperceivable content from the task.** The task text gives
  the persona's situation and goal — not the content of the document, not
  what the interface "should" say. If the reviewer knows a word the
  persona could not have seen, they are cheating.
- **No correction without visible evidence.** A reviewer must NEVER
  correct, confirm, or complete a review item whose material is not
  visibly rendered on the surface. A correction made without the material
  in view is a fabrication — however plausible the text-level reasoning.
  If the material cannot be seen, the walk FAILS at that point and says
  so; it never presses through to a finished-looking result.
- **The pixels are the ground truth; the structure channel lies.** This is
  not just discipline — it is a documented model failure mode: multimodal
  agents' textual state beliefs defer to a conflicting DOM/accessibility
  tree even when their pixel perception is correct (the Perception-Fusion
  Gap is positive for every model tested, arXiv:2607.04334; coordinate
  action output keeps beliefs pixel-bound). Any structural channel
  silently overrides what the pixels show. The reviewer's belief about the
  interface must be sourced from the pixels, never from structure.
- **Screenshot after every interaction, and evaluate in the persona's
  words.** After each step, capture the screen and state the outcome a
  real user would perceive ("I see the letter at a readable size" /
  "the pane is still blank"). An outcome you cannot state from the
  screen is an outcome you have not verified.
- **Capture for the model's eyes, not the monitor's.** The vision model
  receives a downscaled, tokenized image: feed it a whole-view at roughly
  1280×720 for layout judgments, and 2–4× zoomed crops of any region whose
  detail matters (the resolution curse: full-page screenshots make small
  text unreadable and hallucination-prone; cropping recovers it —
  GUI-Lens/AdaZoom/UI-Zoomer, Anthropic's computer-use guidance). A
  finding about a detail requires the crop, not the whole view.
- **The evidence channel is part of the finding.** Screenshots must come
  from a browser that composites the real rendered pixels (headed, or
  headless=new with GPU — real Chromium composites canvas/WebGL content;
  an environment whose captures show blank regions where content should
  render is a tooling defect to fix, never a pass or a "the app is
  broken" conclusion). When the capture channel cannot show content, the
  fallback evidence protocol is: canvas pixel-reads for content presence
  and geometry, and crops of the source image at the viewport region for
  content — and every finding that relied on the fallback names the
  channel it used.
- **A finding cites its screen.** Every finding names the screenshot (or
  the fallback evidence) it came from; "could not see X" is a finding,
  never a skip.
- **Verify outcomes by what is perceivable.** A scroll worked when the
  content visibly moved; a zoom worked when the content visibly changed
  size; a save worked when the interface showed the saved state. System
  state (records, storage, responses) is not an outcome the user can
  perceive.

The rest of this skill's walker rules are the details of this one rule.

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
- Standards: `docs/ux-standards.md` (principles), the repo's
  usability-requirements baseline and UX decisions doc (repo specifics).
