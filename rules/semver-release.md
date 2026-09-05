---
description: House releases are semver (vMAJOR.MINOR.PATCH); before any version bump, classify the changes since the last tag and compute the increment yourself — never ask the user which number.
---

# Semver Releases — compute the increment, don't ask

Every house repo versions with [Semantic Versioning](https://semver.org/):
`vMAJOR.MINOR.PATCH` tags; the repo's release workflow builds and publishes
the bundles/wheels from the tag.

## Compute the increment yourself

1. `LAST=$(git tag --merged HEAD --sort=-v:refname | head -1)` — the current
   published version; empty means the first release ever.
2. `git log ${LAST:+"$LAST..HEAD"} --oneline` — classify every change (with
   `LAST` empty this is plain `git log --oneline`: the whole history):
   - any **breaking** change — a removed or changed CLI/API contract, a scan-
     schema or wire-format change, a behavior a caller relies on that flips
     (e.g., a changed default that alters a command's output) → bump **MAJOR**.
   - a backwards-compatible **feature** (a new rule, fix kind, option, or
     command) → bump **MINOR**.
   - **bug fixes only** → bump **PATCH**.
   Tie-breakers: the presence of ANY feature = MINOR; a breaking change beats
   everything = MAJOR. The increment is a classification of the diff, never
   a question for the user.
3. Find the repo's version sources — the README's "Versioning" section names
   them (common shape: `pyproject.toml` + the Rust crate, pinned equal by a
   test; the CLI and the LSP derive their reported version from those, never
   a hardcoded literal). Bump ALL of them to the same number.
4. Run the repo's full battery (its `make test` + self-check), commit the
   bump, tag `git tag -a vX.Y.Z -m "..."`, push the tag — the release
   workflow publishes.
5. Verify the published release's assets exist (bundles, wheels,
   SHA256SUMS) before reporting done.

## Never

- Hardcode the version in code or docs — derive it from the version sources,
  and keep examples version-less (`<version>` placeholders).
- Bump only one source (a pyproject/Cargo mismatch is a broken wheel).
- Ask the user which number to use — compute it from the diff classification.
