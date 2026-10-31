---
name: lucidlint-lsp-update
description: |
  Updating the installed lucidlint LSP server — download the release
  bundle, replace the binary, restart running clients, verify the SERVED
  version with a handshake. Read when asked to update, upgrade, or install
  the lucidlint LSP.
---

# lucidlint LSP update

lucidlint (github.com/ashbywinch/lucidlint) is both a gate and an LSP
server: the same binary runs `lucidlint --lsp` over stdio. The installed
server the editors and omp agents use lives at
`~/.local/share/lucidlint/bin/lucidlint` — an old binary there keeps
serving old rules until replaced AND its running clients are killed.

## Update in one pass

Run `lucidlint-lsp-update.sh`, installed on PATH from this repo's `tools/` by
`make install`:

```sh
lucidlint-lsp-update.sh            # latest release
lucidlint-lsp-update.sh v0.6.9     # pin a release
```

It downloads the asset for the machine's architecture, replaces
`~/.local/share/lucidlint/bin/lucidlint`, kills the clients still serving the
old rules, and prints what a stdio `initialize` handshake answers.

## Verify what is SERVED, not just that a file moved

State the script's served version as the proof that clients load the new rules.
A replaced file proves nothing: a running client keeps answering with the
version it started with, and the handshake is the only output that names the
binary actually serving.

## Gotchas (each cost a real session)

- **`~/.local/bin/lucid-lint` (hyphenated) is a different tool** — a
  prose-accessibility linter. It is not lucidlint; do not update,
  replace, or measure it. A `grep -ri lucid` sweep hits it; read its
  `--help` before treating anything as lucidlint.
- **Running clients survive a binary swap** — `lucidlint-lsp-update.sh` kills
  them after replacing the binary; omp respawns on the next request. A client
  left running keeps serving the old rules indefinitely.
- **Gate staleness is a separate guard**: the orchestrator refuses a
  local build older than the scanner sources (`make scanner-check`) —
  that guard protects pytest/the gate; this skill protects the installed
  LSP.
