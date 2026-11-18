# Testing Standards

Standards for testing: what to test, how to write tests, and how the test
suite is organised.

## Type checking is a first-class gate

The language's type checker is configured (strict where the toolchain allows)
and runs in the test gate — a type-checking error fails the build unless
its suppression comment carries a valid written justification (criteria in
the next section); a suppression without one is a finding that fails the
gate.

## Never silence a diagnostic without a VALID justification

Never suppress an error or warning from any tool (type checker, linter,
formatter — `# type: ignore`, `# noqa`, `# pylint: disable`, ruff `# noqa`,
pyrefly ignore, eslint-disable, …) without a VALID written justification in
the suppression comment — a reason that states why THIS occurrence is
genuinely justified. Filler ("this is fine", "later", a restatement of the
rule) is a finding, as is a stale suppression (the diagnostic no longer
fires) — delete it. The test gate detects staleness by running each tool
with unused-suppression checks (e.g., lucidlint `stale-suppression`), and
the review bot checks every suppression comment for a valid justification.

*(Policy change 2026-08-21: a suppression is no longer a finding per se;
an unjustified or stale suppression is. Reason: the previous rule made
every suppression a finding, which discouraged legitimate, explained
suppressions and punished correct use of the mechanism.)*

## Write the test before the code
Follow test-driven development: a failing test first, then the code that
makes it pass (`rule://test-first`). For LLM behaviour, write evals instead
(real AND fictional fixtures, running the production path exactly once).

## Verify behaviour, not render — for UI, exercise the interactions

A UI change is done when its interactions work, not when it renders (see
P14 in `ux-standards.md`). Exercise each
changed interaction and assert the observable outcome, not the DOM's
existence: a scrollable pane's `scrollTop` must actually move (the flexbox
`min-height: 0` bug renders perfectly and never scrolls); a pannable/zoomable
view must actually pan and zoom; a button must produce its consequence. A
static check (screenshot, element present, computed style) never proves a
scroll works, a drag behaves, or a control responds.

## Test properties

- Tests mirror module paths.
- Deterministic: no wall-clock, network, or order dependence. Randomness: **fake RNG is fixed-seeded** (test doubles over `random`/fakers — a failure reproduces on every machine and hash seed); **real RNG is never seeded** (crypto, tokens, ids — seeding a production path is a security bug). Never assert iteration order of sets, or of dicts built from sets or other hash-dependent iteration — hash order varies with `PYTHONHASHSEED` (a set-order test passed locally and failed in CI on a different seed).
- Assert behaviour, not implementation.
- Sort file listings before processing — `glob` order is filesystem-dependent.
- A test that cannot fail on a plausible bug is not a test (no tautological
  fixtures — validate real artifacts).

## When a real-model eval fails

A red eval means the rule it checks is ambiguous. Fix the rule, not the eval.

An eval runs fixture inputs through the prompt and checks each answer against a
rule.

A rule that lists the cases it decides grows by one clause per case. Write the
rule as the test that decides every case, then delete the clauses the test
replaces.

✗ "Refunds, deliveries and invoices are not urgent."

✓ "Urgent: the sender must act today to avoid a loss."

The ✗ rule decides three cases by name and says nothing about the next one. The
✓ rule states the test, so a new case needs no new clause.

- **Never fix one failing case with an example.** Fix the rule the case exposes.
- **Never add an example without checking the whole list.** Examples accumulate
  and contradict each other. When a new example disagrees with one already
  there, rewrite the list as one set.
- **Never state a rule without its reason.** The model follows a rule it
  understands and guesses at one it memorised.
- **Never keep two rules for one decision.** Delete the weaker one.

**Replace a rule that fails in both directions.** No wording fix resolves both
errors. Every case has one expected answer: the rule accepts the case or
rejects it. A rule fails in both directions when it rejects a case it should
accept and accepts a case it should reject. Correcting one error then causes
the other, and more cases only choose which error ships.

Run the eval after every change to the prompt or to the code. That run is how
you verify the fix.

| Never | Because |
|---|---|
| Re-run the eval with nothing changed | a pass on the same input is luck, not a fix |
| Run more cases until one passes, or keep the best of several runs | a vote only chooses which error ships |
| Weaken an assertion that is correct | it hides the defect |
| Keep an assertion that is wrong | it demands the wrong answer |
| Drop the eval from the required checks | a check that does not block the release protects nothing |

Never ask the user to choose between re-running the eval with nothing changed,
running more cases, weakening the assertion, and dropping the check. Fix the
prompt yourself.

**A rule that leaves its answer open blocks the release.** The eval is a required
check whose verdict is pass or fail, so an open answer decides the release by
chance. A red eval on a change that did not touch the prompt shows the rule
leaves the answer open. Never dismiss that red eval as a flake.

## Never skip tests for a missing environment

A test that needs an external dependency — a store, a service, an API key,
a database — never skips when the dependency is absent. Fake it: a fixture
builds a minimal stand-in (a tmp store with synthetic data, a stub server,
recorded responses) so the test runs identically everywhere, CI included.
`@pytest.mark.skipif` on environment presence is forbidden: a skipped test
rots silently and the coverage gate lies about what is exercised.

Only the E2E suite may skip — a real external API is the one dependency
that cannot be faked faithfully (`@pytest.mark.e2e`, skipped by default;
see Organisation). Everything else fakes, with the fake injected per the
Mocking section (parameter injection first — never `monkeypatch` a module
constant to point at a tmp dir; make the dependency a parameter).

## Organisation

- **Unit tests:** one function/module in isolation, no API calls.
- **Integration tests:** full pipeline with fakes.
- **E2E tests:** real external APIs, one consolidated suite per API, skipped
  by default (`@pytest.mark.e2e`).
- Shared test infrastructure (fixtures, fakes) is extracted once, not
  copy-pasted per file.
- **Never let a derived artifact drift from a fresh run.** When something
  is both committed and derived (a projection, an index, a store a producer
  fills), its shape rule is enforced per [A described contract is not an
  enforced contract](coding-standards.md#a-described-contract-is-not-an-enforced-contract)
  — verified here against regeneration. Three tests:
  - the committed version equals a fresh run, compared on a defined stable
    form implemented as a normalizing function declared alongside the
    producer (canonical ordering, no timestamps, paths relative to the
    repo root, locale-independent) — never raw output, so a
    non-deterministic producer cannot make the test flaky; pin the
    normalizer itself with a unit test for determinism and environment
    independence;
  - re-running the producer changes nothing (idempotent), compared on the
    same defined stable form — incidental raw-output nondeterminism
    (ordering, timestamps) is not drift;
  - the invariant is asserted on the producer's declared inputs and
    outputs (a unit-level check, no live state required) and separately
    on the fresh-run result using the same defined stable form; both
    assertions must pass.
  Hand-patching the committed output hides a producer bug that resurfaces
  on every fresh build. Regenerability is a claim, verified not assumed.

## Precompute, materialise — unless the test is the round trip

Expensive derived data is precomputed once — and if it is stable, it is
materialised as a committed artifact so tests never recompute it at all.
The S1 finding is the pattern: the sampled phases were derived from the
live sessions once, committed as s1_dump.jsonl, and the tests read the
committed evidence.

- **Materialise when it saves time and the artifact is small enough for
  git** — a derived fixture (a dump, a snapshot, a generated corpus) is
  computed during development, committed, and read by the tests.
- **Do not materialise a gratuitously massive dataset** — a huge artifact
  bloats the repo and the clone; the tradeoff is a real cost, not a
  preference. When the dataset would be huge, rewrite the test to not
  need it: shrink the fixture to a representative subset, or restructure
  what is being tested.
- **Never materialise the output of a round trip the test exists to
  verify** — if the whole point of the test is that the current code can
  round-trip something (serialize → parse → compare, write → read →
  compare), the test runs the current code; a committed artifact would
  compare against a stale snapshot and the round trip would go
  unexercised. Materialise the input if helpful; never the round-trip
  output.

Within a test run the same principle applies at fixture scope: a
session-scoped fixture, a module constant, a parsed-once structure —
never recompute the same derived data per test. The suite's runtime is a
property, and a test that rebuilds what a sibling already built is wasted
work.

## Fake the filesystem before touching the real one

File I/O in tests uses pyfakefs wherever possible (add `pyfakefs` to dev
deps; it bundles the pytest `fs` fixture and the
`fake_filesystem_unittest` base for unittest suites): in-memory,
deterministic, no disk churn, no teardown.

- Write to fixed fake paths (`/store`, `/labels.jsonl`) — not pytest's
  `tmp_path`, which breaks under the fs patch (`Path.relative_to` fails);
  fake paths need no cleanup anyway.
- Committed artifacts stay readable by mounting their real directories
  (`fs.add_real_paths([...])`), never by copying or by falling back to
  the real FS.
- Reach a real `tmp_path` only when the code under test needs real
  filesystem semantics (subprocess interop, symlinks, OS-specific
  behaviour) — and comment why.

## Mocking and dependency injection

Inject the dependency (service, output path, fake) — never
`monkeypatch`/`patch` global state. If something isn't reachable through DI,
refactor the code to accept a dependency. Fakes subclass the real protocol so
the type checker still holds at edit time.

Injection patterns, in order:
- **Parameter injection** for leaf-level dependencies (underscore-prefixed
  optional param falling back to the real implementation).
- **Services container** for deep call chains.
- **ContextVars** for request-scoped singletons.

Forbidden: `monkeypatch`/`unittest.mock.patch`, module-level mutable state,
lazy imports, and abstract base classes with a single concrete
implementation.

Pure functions need no mocking. Function-param injection is next. Containers
after that. Global patching is a last resort and a smell.
