# PRD — omp-config: the house conventions

The conventions repo: the standards, skills, rules, and system-prompt
append that make every repo we build consistent, plus the scaffolding that
carries them into new repos. Its product is **how we write code everywhere
else** — every principle below is a requirement on the conventions
themselves.

## Overarching goal

All code produced under these conventions is consistently:

1. **Easy to understand and work with for new agents and humans** — a fresh
   agent or a new human opens any repo and knows how to work in it; the
   conventions read as one coherent system, not an accumulated pile.
2. **Anti-fragile** — correct by construction; failures are visible,
   recoverable, and the system gets stronger with use (lessons become
   conventions).
3. **Token efficient** — every loaded document earns its context; density
   rules and size ceilings exist so a session's token cost stays
   proportional to the work.
4. **Effectively bot-reviewable against these goals, as cheaply as
   possible** — the review bot enforces the goals at PR time, and its own
   cost (context, latency, iteration count) is a budgeted quantity.
5. **Using best practices from all relevant fields** — UX, security,
   testing, the specific language, documentation — adopted deliberately,
   never cargo-culted.

## JTBD

1. When I am a new agent dropped into a repo, I want to understand how to
   work there quickly and correctly, so my first changes fit the house style
   without a human correcting them.
2. When I am a human maintainer, I want every repo to look like one system,
   so I can move between them without re-learning conventions.
3. When a lesson is learned — something went wrong, or something worked — I
   want it codified into the conventions, so the mistake does not recur and
   the good pattern propagates.
4. When a PR is opened, I want a bot to check it against every relevant
   standard cheaply, so violations are caught before merge without a human
   review pass for style.
5. When a new repo is started, I want it to inherit all the conventions
   automatically, so compliance is the default, not an effort.
6. When a standard changes, I want every repo's copy to follow, so the
   family does not drift.
7. *(emotional)* When I look at the codebase in five years, I want it to
   feel like the same careful hand wrote it all — conventions are how a
   family of repos stays coherent across time and people.

## User requirements

The outcomes the JTBDs above imply, written as user outcomes:

- **A new agent** can make a first change that fits the house style
  without a human correcting it.
- **A human maintainer** can move between repos without re-learning
  conventions.
- **A lesson learned** is codified, so the mistake does not recur and the
  good pattern propagates.
- **A PR** is checked against every relevant standard before merge,
  without a human review pass for style.
- **A new repo** inherits all conventions automatically, so compliance is
  the default, not an effort.
- **A standard change** reaches every repo's copy, so the family does not
  drift.
- **In five years**, the codebase feels like the same careful hand wrote
  it all.

## Personas

- **New agent** (no context): opens any repo, reads AGENTS.md, must be able
  to do correct work immediately. Decision-useful: AGENTS.md is a
  bootloader, not an OS — only 100%-relevant content, every doc reachable
  from it.
- **Human maintainer**: reviews PRs, writes standards, moves between repos.
  Decision-useful: one formatter per artifact, the standard doc set, the
  density ceilings, decisions recorded with dates and reasons.
- **Review bot** (PR-Agent): reads `repo_context_files`, flags violations.
  Decision-useful: standards are materialized into repos (the bot enforces
  only what it reads), written as named anti-patterns with checkable forms,
  and explicitly instructed to flag them as findings, not style notes; the
  bot sees **all** relevant standards docs.
- **The scaffold**: the agent that builds new repos from the scaffold skill.
  Decision-useful: conventions are copied (never linked) into repos;
  language-specific rules need generic equivalents; the repo that defines
  the standards passes its own checks.

## Constraints

- **Cost to run.** Token cost is a first-class budget: always-loaded docs
  ≤ ~150–200 lines; the bot's findings cap (50) and context list are
  bounded; a review iteration costs minutes, so pushes are consolidated.
  Evidence (2026-08-04): a truncated findings cap forced a redo of a large
  review — the cap was raised so one review covers a whole PR.
- **Longevity.** Conventions must stay coherent for decades — the 2060
  test: a reader in 2060 can follow them without the original authors;
  decisions are dated and reasoned; data that matters is append-only.
- **Backups.** Git is the backup; history is never rewritten casually
  (branch + PR, protected main).
- **Monitoring/tracing in production.** The closest analogue for a
  conventions repo is the review feedback loop: bot findings are the
  telemetry that the conventions are working. A bot that is silent is a
  gap, not a success — the 2026-08-04 silence on missed classes and
  separation-of-concerns violations exposed rules that were not checkable.
- **Access/auth.** Public repo, PR-gated protected main. Secrets never in
  the repo — placeholders only; real keys live in the shell environment.
- **Scale at phases.** Phase 1: a handful of repos, one maintainer.
  Phase 2: the whole code tree under conventions, more contributors.
  Phase 3: the conventions outlive any individual repo. Each phase raises
  what must be enforced automatically vs. reviewed by hand.
- **Hosting.** GitHub only; the conventions repo hosts no runtime services.

## Requirements learned this session (2026-08-04)

- **R1 — The reviewer enforces only what it reads.** Standards must be
  materialized into each repo's `docs/` (`repo_context_files`), never left
  in a skill the bot cannot see.
- **R2 — Reviewable rules are named, checkable, finding-framed.** "Prefer
  classes" stays silent; "three or more free functions sharing the same
  record is a finding" gets flagged. Effective rules state the anti-pattern,
  give a heuristic, and are explicitly classed as findings, not style notes.
- **R3 — The bot sees all relevant standards.** `repo_context_files` lists
  every standards doc a repo carries (PRD, coding, testing, documentation,
  UX, plus project docs) and the bot reports a Compliance section per doc.
- **R4 — Language-specific rules have generic equivalents.** pint/Money get
  generic rules in the global standard and library choices in the language
  layer, so a new language follows suit instead of inventing its own rules.
- **R5 — AGENTS.md is a bootloader, not an OS.** Only 100%-relevant content
  lives there; every doc is discoverable from it (directly or one link
  deep); an undiscoverable doc is a finding. Skills are exempt from
  reachability — a harness discovers them through its own mechanism
  (decision 2026-08-07; rationale and scope in
  docs/documentation-structure.md).
- **R6 — Convergence over churn.** Standards and UX changes land against
  baselines and recorded decisions, with user agreement; the decisions doc
  is the loop's memory, so the loop converges instead of going in circles.
- **R7 — One formatter per artifact, decided in the scaffold.**
  Machine-generated files are formatted by their generator; a second
  formatter over generated output is a churn bug.
- **R8 — Real content never lives in code.** Data is data; code is the
  pipeline. Secrets are the sharpest case (environment only).
- **R9 — The doc set is required and quality-gated.** PRD, TECHSPEC, UX
  spec, PLAN exist with mandated structure (JTBD first, user
  requirements, personas, constraints; choices/spikes/diagrams; UX spec
  meeting every PRD requirement; phase gates) and are themselves held to
  the documentation-quality checklist.
- **R10 — The conventions repo passes its own checks.** omp-config runs the
  scaffold's self-checks on itself: doc links resolve, skills are
  well-formed, CI delegates to make, hooks run the fast checks.
