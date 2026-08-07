# Testing Standards

Standards for testing: what to test, how to write tests, and how the test
suite is organised.

## Type checking is a first-class gate

The language's type checker is configured (strict where the toolchain allows)
and runs in the test gate — errors fail the build, never suppressed.
A `# type: ignore` requires a comment explaining why, and a suppression is
itself a finding.

## Write the test before the code

Follow test-driven development: a failing test first, then the code that
makes it pass (`rule://test-first`). For LLM behaviour, write evals instead
(real AND fictional fixtures, running the production path exactly once).

## Test properties

- Tests mirror module paths.
- Deterministic: no wall-clock, network, or order dependence; seeded randoms.
- Assert behaviour, not implementation.
- Sort file listings before processing — `glob` order is filesystem-dependent.
- A test that cannot fail on a plausible bug is not a test (no tautological
  fixtures — validate real artifacts).

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
