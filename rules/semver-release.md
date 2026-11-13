---
description: House releases are semver (vMAJOR.MINOR.PATCH); before any version bump, classify the changes since the last tag and compute the increment yourself — never ask the user which number.
---

# Semver Releases — compute the increment, don't ask

Every house repo versions with [Semantic Versioning](https://semver.org/):
`vMAJOR.MINOR.PATCH` tags. The repo's release workflow builds and publishes the
bundles or wheels from the tag.

## Compute the increment yourself

1. `LAST=$(git tag --merged HEAD --sort=-v:refname | head -1)` — the current
   published version. Empty means the first release ever.
   # The expansion drops the range argument entirely when LAST is empty
   # (plain `git log --oneline`); with LAST set it is one quoted argument.
2. `git log ${LAST:+"$LAST..HEAD"} --oneline` — classify every change:
   - A **breaking** change is a removed or changed CLI/API contract, a
     scan-schema or wire-format change, or a behavior a caller relies on that
     flips. A changed default that alters a command's output is an example.
     Bump **MAJOR**.
   - A backwards-compatible **feature** — a new rule, fix kind, option, or
     command — bumps **MINOR**.
   - **Bug fixes only** bump **PATCH**.
   Precedence is strict: a breaking change beats any feature (MAJOR), a
   feature beats fix-only (MINOR), and only then does PATCH apply. The
   increment is a classification of the diff, never a question for the user.
3. Find the repo's version sources. The README's "Versioning" section names
   them — commonly `pyproject.toml` plus the Rust crate, pinned equal by a
   test. The CLI and the LSP (the editor language server) report the version
   from those, never a hardcoded literal. Bump all of them to the same number.
4. Run the repo's full battery: its `make test` and self-check. Commit the
   bump, tag `git tag -a vX.Y.Z -m "..."`, then push the branch **and** the
   tag: `git push origin <branch> && git push origin vX.Y.Z`. A tag pushed on
   its own leaves the bump commit local, so the next release computes its range
   from a branch that never saw it.
5. Verify the published release's assets exist (bundles, wheels,
   SHA256SUMS) before reporting done.

## Never

- Hardcode the version in code or docs — derive it from the version sources,
  and keep examples version-less (`<version>` placeholders).
- Bump only one source (a pyproject/Cargo mismatch is a broken wheel).
- Ask the user which number to use — compute it from the diff classification.
